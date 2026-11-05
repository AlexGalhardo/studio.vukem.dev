#!/usr/bin/env python3
"""transcrever.py: áudio ou vídeo → transcrição palavra a palavra, com tempo, afinada pela onda.

  python3 transcrever.py <mídia> --saida transcricao/ [--nomes "Nome A, Nome B"] [--nomes-de roteiro/roteiro.md]

Grava em --saida: palavras.json (já afinado), segmentos.json, texto.txt e qa.json.
O tempo é SEMPRE o da mídia original: o silêncio do começo é cortado antes de transcrever (senão o Whisker
ancora a primeira palavra em 0 e a legenda vai adiantando) e o corte é somado de volta.
Áudio longo vira blocos com sobreposição, costurados pelo texto repetido da emenda.

Códigos de saída: 0 ok · 1 falhou · 2 falta insumo (mídia, ffmpeg ou Whisper).
"""
import argparse
import difflib
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afinar as A  # noqa: E402
import motor as M  # noqa: E402
import onda as O  # noqa: E402
import palavras as P  # noqa: E402

BLOCO = 600.0          # segundos de áudio por bloco (vídeo de 1 h = 6 blocos)
SOBREPOSICAO = 12.0    # segundos repetidos entre um bloco e o seguinte, para a costura ter onde casar
MARGEM_CORTE = 0.25    # o corte do silêncio inicial para esta folga antes da primeira palavra
MIN_CORTE = 1.0        # só corta se houver mais de 1 s de silêncio na frente
LIMITE_PROMPT = 600    # caracteres (o Whisper aceita 224 tokens de prompt)
CONFIANCA_BAIXA = 0.75


# --------------------------------------------------------------------------- prompt com nomes próprios
def montar_prompt(nomes, idioma="pt"):
    """Nomes próprios por vírgula, terminando em ponto: sem isso o Whisper escreve nome próprio de ouvido."""
    vistos, limpos = set(), []
    for n in nomes:
        n = " ".join(str(n).split()).strip(" ,.;")
        chave = P.normalizar(n)
        if n and chave and chave not in vistos:
            vistos.add(chave)
            limpos.append(n)
    if not limpos:
        return "", []
    cab = "Transcrição em português. Nomes próprios: " if idioma == "pt" else "Proper names: "
    p, usados = cab, []
    for n in limpos:
        if len(p) + len(n) + 2 > LIMITE_PROMPT:
            break
        p += n + ", "
        usados.append(n)
    return p.rstrip(", ") + ".", usados


def nomes_de_arquivos(caminhos):
    nomes = []
    for c in caminhos:
        p = Path(c).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"não achei {p}")
        for f in (sorted(p.rglob("*.md")) + sorted(p.rglob("*.txt"))) if p.is_dir() else [p]:
            nomes += P.nomes_do_texto(f.read_text(encoding="utf-8", errors="replace"))
    return nomes


# --------------------------------------------------------------------------- blocos e costura
def janelas(dur, bloco, sobreposicao):
    """[(t0, t1)] cobrindo 0..dur com sobreposição; a última janela nunca fica com menos de 1/4 do bloco."""
    if dur <= bloco:
        return [(0.0, dur)]
    passo = max(1.0, bloco - sobreposicao)
    saida, t = [], 0.0
    while True:
        fim = t + bloco
        if dur - fim < bloco / 4:
            saida.append((t, dur))
            break
        saida.append((t, fim))
        t += passo
    return saida


def _centro(p):
    return (p["t0"] + p["t1"]) / 2


def costurar(blocos):
    """Junta blocos de palavras já em tempo absoluto.

    Na emenda, os dois blocos transcreveram o MESMO trecho: casar os textos repetidos e cortar exatamente ali
    é o que evita a palavra duplicada (costura por tempo com limiar) e a palavra pulada (corte por índice fixo).
    Sem texto repetido reconhecível, cai para o meio da sobreposição, que nunca duplica nem pula mais de uma.
    """
    saida, diario = [], []
    for k, b in enumerate(blocos):
        pal = sorted(b["palavras"], key=lambda p: p["t0"])
        if not saida:
            saida = list(pal)
            continue
        ov0, ov1 = b["t0"], blocos[k - 1]["t1"]
        if ov1 <= ov0 + 0.05 or not pal:
            diario.append({"emenda": k, "metodo": "sem sobreposição", "descartadas": 0})
            saida += [p for p in pal if not saida or p["t0"] > saida[-1]["t0"]]
            continue
        ia = next((i for i, p in enumerate(saida) if _centro(p) >= ov0), len(saida))
        ib = max((j for j, p in enumerate(pal) if _centro(p) <= ov1), default=-1)
        toks_a = [P.normalizar(p["w"]) for p in saida[ia:]]
        toks_b = [P.normalizar(p["w"]) for p in pal[: ib + 1]]
        corte_a = corte_b = None
        melhor = None
        if toks_a and toks_b:
            sm = difflib.SequenceMatcher(None, toks_a, toks_b, autojunk=False)
            for i, j, n in sm.get_matching_blocks():
                if n < 2:
                    continue
                if abs(saida[ia + i]["t0"] - pal[j]["t0"]) > 1.0:   # casou texto, mas em outro lugar do tempo
                    continue
                if melhor is None or n > melhor[2]:
                    melhor = (i, j, n)
        if melhor:
            i, j, n = melhor
            corte_a, corte_b = ia + i + n, j + n
            diario.append({"emenda": k, "metodo": "texto repetido", "palavras_casadas": n,
                           "em_s": round(saida[ia + i]["t0"], 2)})
        else:
            meio = (ov0 + ov1) / 2
            corte_a = next((i for i, p in enumerate(saida) if _centro(p) >= meio), len(saida))
            corte_b = next((j for j, p in enumerate(pal) if _centro(p) >= meio), len(pal))
            diario.append({"emenda": k, "metodo": "meio da sobreposição", "em_s": round(meio, 2)})
        diario[-1]["descartadas"] = len(saida) - corte_a
        saida = saida[:corte_a] + pal[corte_b:]
    return limpar(saida), diario


def limpar(pal):
    """Ordem crescente, sem a mesma palavra repetida no mesmo instante (resto de emenda)."""
    pal = sorted(pal, key=lambda p: (p["t0"], p["t1"]))
    out = []
    for p in pal:
        if out and P.normalizar(p["w"]) == P.normalizar(out[-1]["w"]) and abs(p["t0"] - out[-1]["t0"]) < 0.12:
            continue
        if out and p["t0"] < out[-1]["t0"]:
            continue
        out.append(p)
    return out


# --------------------------------------------------------------------------- QA
def qualidade(pal, seg, fala0, fala1, dur):
    avisos = []
    ps = [p["p"] for p in pal if isinstance(p.get("p"), (int, float))]
    baixas = [{"mmss": P.mmss(p["t0"]), "t": round(p["t0"], 2), "w": p["w"], "p": p["p"]}
              for p in pal if isinstance(p.get("p"), (int, float)) and p["p"] < CONFIANCA_BAIXA]
    if not pal:
        avisos.append("nenhuma palavra reconhecida: confira se a mídia tem fala")
        return {"avisos": avisos}, avisos
    if pal[0]["t0"] - fala0 > 0.6:
        avisos.append(f"a fala começa em {fala0:.2f}s e a primeira palavra em {pal[0]['t0']:.2f}s: "
                      f"pode ter ficado fala de fora no começo")
    if fala1 - pal[-1]["t1"] > 0.6:
        avisos.append(f"a fala termina em {fala1:.2f}s e a última palavra em {pal[-1]['t1']:.2f}s: "
                      f"transcreva o fim isolado se houver fala ali")
    buracos = [(round(a["t1"], 2), round(b["t0"], 2)) for a, b in zip(pal, pal[1:]) if b["t0"] - a["t1"] > 5]
    if buracos:
        avisos.append(f"{len(buracos)} trecho(s) de mais de 5 s sem palavra (silêncio, música ou falha): "
                      + ", ".join(f"{P.mmss(a)}–{P.mmss(b)}" for a, b in buracos[:5]))
    if ps and sorted(ps)[len(ps) // 2] < 0.6:
        avisos.append("confiança mediana abaixo de 0,6: áudio ruim, idioma errado ou modelo pequeno")
    qa = {"duracao_s": round(dur, 2), "fala_ini_s": round(fala0, 2), "fala_fim_s": round(fala1, 2),
          "palavras": len(pal), "segmentos": len(seg),
          "primeira_palavra_s": round(pal[0]["t0"], 2), "ultima_palavra_s": round(pal[-1]["t1"], 2),
          "ppm": round(len(pal) / max(0.001, (pal[-1]["t1"] - pal[0]["t0"])) * 60, 1),
          "confianca_mediana": round(sorted(ps)[len(ps) // 2], 3) if ps else None,
          "palavras_abaixo_de_075": baixas[:200], "quantas_abaixo_de_075": len(baixas),
          "buracos_s": buracos[:50], "avisos": avisos}
    return qa, avisos


# --------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description="Transcreve áudio ou vídeo palavra a palavra, com tempo.")
    ap.add_argument("midia", help="o arquivo de áudio ou vídeo")
    ap.add_argument("--saida", default="transcricao", help="pasta de saída (padrão: transcricao/)")
    ap.add_argument("--nomes", default="", help='nomes próprios do vídeo, separados por vírgula')
    ap.add_argument("--nomes-de", nargs="+", default=[], metavar="ARQUIVO",
                    help="roteiro, pauta ou pasta de onde tirar os nomes próprios")
    ap.add_argument("--idioma", default="pt", help="idioma da fala (padrão: pt)")
    ap.add_argument("--bloco", type=float, default=BLOCO, help=f"segundos por bloco (padrão: {BLOCO:.0f})")
    ap.add_argument("--sobreposicao", type=float, default=SOBREPOSICAO,
                    help=f"segundos repetidos entre blocos (padrão: {SOBREPOSICAO:.0f})")
    ap.add_argument("--duas-passadas", action="store_true",
                    help="roda também a passada por segmento (texto de leitura melhor, dobra o tempo)")
    ap.add_argument("--sem-afinar", action="store_true", help="não corrige o início das palavras pela onda")
    ap.add_argument("--sem-corte", action="store_true", help="não corta o silêncio do começo")
    ap.add_argument("--refazer", action="store_true", help="ignora os blocos já transcritos e refaz tudo")
    a = ap.parse_args()

    midia = Path(a.midia).expanduser()
    if not midia.exists():
        print(f"falta insumo: não achei {midia}", file=sys.stderr)
        return 2
    nome_motor, exe, modelo = M.motor_disponivel()
    if not nome_motor:
        print("falta insumo: nenhum motor de transcrição instalado. Rode o preparar.py desta skill "
              "(Mac: whisper-cli + modelo ggml; Linux/Windows: faster-whisper).", file=sys.stderr)
        return 2

    saida = Path(a.saida).expanduser()
    trabalho = saida / "_trabalho"
    trabalho.mkdir(parents=True, exist_ok=True)

    # 1. áudio canônico e medida da fala
    try:
        wav = O.extrair_wav16k(midia, trabalho / "audio16k.wav")
    except RuntimeError as e:
        print(f"falta insumo: {e}", file=sys.stderr)
        return 2
    x, sr = O.ler_wav_mono(wav)
    dur = len(x) / sr
    fala0, fala1, pico = O.span_fala(x, sr)
    corte = 0.0 if (a.sem_corte or fala0 < MIN_CORTE) else max(0.0, fala0 - MARGEM_CORTE)

    # 2. prompt com os nomes próprios
    nomes = [n for n in a.nomes.split(",") if n.strip()]
    try:
        nomes += nomes_de_arquivos(a.nomes_de)
    except FileNotFoundError as e:
        print(f"falta insumo: {e}", file=sys.stderr)
        return 2
    prompt, usados = montar_prompt(nomes, a.idioma)

    # 3. blocos
    jan = janelas(dur - corte, max(20.0, a.bloco), max(2.0, a.sobreposicao))
    chave = hashlib.sha1((prompt + a.idioma + nome_motor + f"{corte:.3f}").encode("utf-8")).hexdigest()[:10]
    print(f"{midia.name}: {dur:.1f}s, fala de {fala0:.2f}s a {fala1:.2f}s, pico {pico:.1f} dBFS"
          + (f", corte de {corte:.2f}s no começo" if corte else "")
          + f" · {nome_motor} · {len(jan)} bloco(s)")

    blocos, t_ini = [], time.time()
    for i, (b0, b1) in enumerate(jan):
        cache = trabalho / f"bloco{i:03d}_{chave}.json"
        if cache.exists() and not a.refazer:
            d = json.loads(cache.read_text(encoding="utf-8"))
            print(f"  bloco {i + 1}/{len(jan)} {P.mmss(b0 + corte)}–{P.mmss(b1 + corte)}: "
                  f"{len(d['palavras'])} palavras (já estava pronto)")
        else:
            pedaco = trabalho / f"_bloco{i:03d}.wav"
            ini = O.fatiar_wav(wav, pedaco, corte + b0, corte + b1) if len(jan) > 1 or corte else None
            alvo = pedaco if ini is not None else wav
            desloca = (ini if ini is not None else 0.0)
            t0 = time.time()
            try:
                pal = M.transcrever_wav(alvo, trabalho / f"_w{i:03d}", prompt, a.idioma, True,
                                        (nome_motor, exe, modelo))
            except RuntimeError as e:
                print(f"falhou no bloco {i + 1}: {e}", file=sys.stderr)
                return 1
            finally:
                if ini is not None and pedaco.exists():
                    pedaco.unlink()
            d = {"t0": round(desloca, 3), "t1": round(desloca + (b1 - b0), 3),
                 "palavras": [{"w": p["w"], "t0": round(desloca + p["t0"], 3),
                               "t1": round(desloca + p["t1"], 3), "p": p["p"]} for p in pal]}
            bruto = json.dumps(d, ensure_ascii=False)
            cache.write_text(bruto, encoding="utf-8", newline="\n")
            print(f"  bloco {i + 1}/{len(jan)} {P.mmss(d['t0'])}–{P.mmss(d['t1'])}: "
                  f"{len(d['palavras'])} palavras ({time.time() - t0:.0f}s)")
        blocos.append(d)

    pal, diario = costurar(blocos)
    if not pal:
        print("nenhuma palavra reconhecida.", file=sys.stderr)
        return 1

    # 4. afinar pelo ataque da onda
    est = {}
    if not a.sem_afinar:
        pal, est = A.afinar(pal, x, sr)

    # 5. segmentos: agrupamento das próprias palavras (mesmos tempos) ou passada por segmento
    seg = [{"t0": f["t0"], "t1": f["t1"], "texto": f["texto"]} for f in P.frases(pal)]
    if a.duas_passadas:
        por_seg = []
        for i, (b0, b1) in enumerate(jan):
            pedaco = trabalho / f"_segbloco{i:03d}.wav"
            ini = O.fatiar_wav(wav, pedaco, corte + b0, corte + b1)
            try:
                s = M.transcrever_wav(pedaco, trabalho / f"_s{i:03d}", prompt, a.idioma, False,
                                      (nome_motor, exe, modelo))
            finally:
                pedaco.unlink()
            por_seg.append({"t0": ini, "t1": ini + (b1 - b0),
                            "palavras": [{"w": p["w"], "t0": ini + p["t0"], "t1": ini + p["t1"], "p": p["p"]}
                                         for p in s]})
        juntos, _ = costurar(por_seg)
        seg = [{"t0": round(s["t0"], 3), "t1": round(s["t1"], 3), "texto": s["w"]} for s in juntos]

    texto = "\n".join(s["texto"] for s in seg)
    qa, avisos = qualidade(pal, seg, fala0, fala1, dur)
    qa.update({"midia": str(midia), "motor": nome_motor, "modelo": Path(str(modelo)).name,
               "idioma": a.idioma, "prompt": prompt, "nomes_usados": usados,
               "corte_inicial_s": round(corte, 3), "pico_dbfs": round(pico, 1),
               "blocos": [{"i": i, "t0": b["t0"], "t1": b["t1"], "palavras": len(b["palavras"])}
                          for i, b in enumerate(blocos)],
               "sobreposicao_s": a.sobreposicao if len(jan) > 1 else 0, "costura": diario,
               "afinacao": est, "segundos_de_trabalho": round(time.time() - t_ini, 1)})

    P.gravar_json(saida / "palavras.json", pal)
    P.gravar_json(saida / "segmentos.json", seg)
    P.gravar_json(saida / "qa.json", qa)
    (saida / "texto.txt").write_text(texto + "\n", encoding="utf-8", newline="\n")

    print(f"{len(pal)} palavras, {len(seg)} segmentos, {qa['ppm']} palavras por minuto → {saida}/")
    if est:
        print(f"afinadas pela onda: {est['afinadas']} (|deslocamento| mediano "
              f"{est['deslocamento_abs_mediano_s']:.3f} s, máx {est['deslocamento_abs_max_s']:.2f} s)")
    for d in diario:
        print(f"emenda {d['emenda']}: {d['metodo']}"
              + (f", {d['palavras_casadas']} palavras casadas" if "palavras_casadas" in d else "")
              + f", {d['descartadas']} descartadas do bloco anterior")
    if qa.get("quantas_abaixo_de_075"):
        print(f"{qa['quantas_abaixo_de_075']} palavra(s) com confiança abaixo de 0,75 — veja qa.json "
              f"e confira ouvindo antes de corrigir")
    for av in avisos:
        print(f"atenção: {av}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
