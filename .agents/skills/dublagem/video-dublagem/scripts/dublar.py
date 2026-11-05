#!/usr/bin/env python3
"""dublar.py: troca SÓ o trecho errado da fala por outra gravação, com a emenda casada.

A promessa é pequena de propósito: o resto do áudio não é tocado. O que entra no lugar é ajustado ao que
está em volta em quatro frentes, e a emenda é feita onde a onda cruza o zero.

1. NÍVEL      o RMS de fala do novo trecho vai para o RMS de fala da vizinhança (±4 s em volta do buraco).
2. TIMBRE     a cor do novo trecho é puxada para a do entorno por um EQ de bandas de 1/3 de oitava,
              suavizado e limitado a ±6 dB — o bastante para o mesmo microfone e a mesma sala, nunca tanto
              que vire outra voz.
3. SALA       o chão de ruído da gravação original (as janelas mais silenciosas do entorno) entra por baixo
              do novo trecho, para o silêncio entre as palavras não ficar "surdo".
4. DURAÇÃO    se o novo trecho não couber no buraco, `atempo` estica ou encolhe no MÁXIMO ±8%. Além disso a
              voz fica artificial: a skill mantém a duração natural, empurra o resto da linha do tempo e
              AVISA no relatório — a boca não vai bater e o trecho precisa ser coberto.

A emenda tem 25 ms de cruzamento, alinhado no cruzamento por zero mais próximo dos dois lados, e o
relatório mede o salto entre amostras vizinhas nos 20 ms da junção contra os saltos normais em volta: é
assim que se prova que não ficou clique.

Esta skill só roda com consentimento registrado (som/dublagem/consentimento.json) — código 2 sem ele.

Uso:
  python3 dublar.py som/voz.wav --t0 12.30 --t1 15.80 --novo som/dublagem/trecho.wav \\
      --saida som/dublagem/voz_dublada.wav --tipo texto
  python3 dublar.py som/voz.wav --t0 12.30 --t1 15.80 --novo x.wav --manter-duracao
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consentimento as consent  # noqa: E402
from audio import SR, db, ebur128, faltou, ffmpeg, gravar, ler, rms_fala  # noqa: E402

CRUZAMENTO_S = 0.025        # cruzamento da emenda
ATEMPO_MAX = 0.08           # ±8%: além disso a voz fica artificial
EQ_MAX_DB = 6.0             # teto da correção de timbre por banda
VIZINHANCA_S = 4.0          # quanto do entorno serve de referência
FOLGA_BOCA_S = 0.08         # diferença de duração a partir da qual a boca não bate mais


# ───────────────────────────────────────────────────────── ferramentas ──
def mono(x):
    return x.mean(axis=1) if np.ndim(x) == 2 else np.asarray(x, dtype=np.float64)


def bandas_terco(lo=80.0, hi=9000.0):
    """Centros de 1/3 de oitava entre lo e hi."""
    c, out = lo, []
    while c <= hi:
        out.append(c)
        c *= 2 ** (1 / 3)
    return np.array(out)


def espectro_bandas(x, centros):
    """Energia média (dB) por banda de 1/3 de oitava do sinal inteiro."""
    X = np.abs(np.fft.rfft(mono(x))) ** 2
    f = np.fft.rfftfreq(len(mono(x)), 1 / SR)
    out = []
    for c in centros:
        k = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        out.append(db(np.sqrt(X[k].mean())) if k.any() else -120.0)
    return np.array(out)


def casar_timbre(novo, referencia):
    """EQ corretivo: puxa a cor de `novo` para a de `referencia`, por bandas de 1/3 de oitava.
    A curva é suavizada (média móvel de 3 bandas) e limitada a ±EQ_MAX_DB. Devolve (sinal, curva)."""
    centros = bandas_terco()
    dif = espectro_bandas(referencia, centros) - espectro_bandas(novo, centros)
    dif -= np.median(dif)                       # 1º tira o nível global (é tratado à parte)…
    dif = np.convolve(dif, np.ones(3) / 3, mode="same")
    dif = np.clip(dif, -EQ_MAX_DB, EQ_MAX_DB)   # …e só então limita, senão a curva satura e vira reta
    n = len(novo)
    f = np.fft.rfftfreq(n, 1 / SR)
    ganho = 10 ** (np.interp(np.log2(np.maximum(f, 1.0)), np.log2(centros), dif,
                             left=dif[0], right=dif[-1]) / 20)
    saida = np.stack([np.fft.irfft(np.fft.rfft(novo[:, ch]) * ganho, n) for ch in range(novo.shape[1])], axis=1)
    return saida, {f"{int(c)}Hz": round(float(d), 2) for c, d in zip(centros, dif)}


def chao_de_ruido(entorno, janela=0.05, fatia=0.08):
    """Pega as janelas mais silenciosas do entorno (o ruído de sala) e devolve um bloco emendável delas."""
    m = mono(entorno)
    nj = int(janela * SR)
    k = len(m) // nj
    if k < 8:
        return None, -120.0
    r = np.sqrt(np.mean(m[:k * nj].reshape(k, nj) ** 2, axis=1))
    quietas = np.argsort(r)[:max(3, int(k * fatia))]
    bloco = np.concatenate([entorno[i * nj:(i + 1) * nj] for i in sorted(quietas)], axis=0)
    f = int(0.004 * SR)                          # micro-fades para as emendas internas não estalarem
    for i in range(0, len(bloco), nj):
        bloco[i:i + f] *= np.linspace(0, 1, min(f, len(bloco) - i))[:, None]
        j = min(i + nj, len(bloco))
        bloco[j - f:j] *= np.linspace(1, 0, min(f, j - max(i, j - f)))[:, None]
    return bloco, db(np.sqrt(np.mean(mono(bloco) ** 2)))


def sala_por_baixo(novo, bloco):
    """Repete o chão de ruído sob o novo trecho, só onde ele está quieto (o resto é mascarado)."""
    if bloco is None or len(bloco) < SR // 10:
        return novo, False
    rep = int(np.ceil(len(novo) / len(bloco)))
    cama = np.tile(bloco, (rep, 1))[:len(novo)]
    m = np.abs(mono(novo))
    k = int(0.02 * SR)
    envel = np.convolve(m, np.ones(k) / k, mode="same")
    peso = np.clip(1.0 - envel / (np.percentile(envel, 90) + 1e-9), 0, 1)[:, None] ** 2
    return novo + cama * peso, True


def zero_mais_perto(x, i, raio_s=0.012):
    """Índice do cruzamento por zero mais perto de i (busca em ±raio)."""
    m = mono(x)
    r = int(raio_s * SR)
    a, b = max(1, i - r), min(len(m) - 1, i + r)
    if b <= a:
        return int(np.clip(i, 0, max(len(m) - 1, 0)))
    cruz = np.nonzero(np.signbit(m[a:b]) != np.signbit(m[a + 1:b + 1]))[0]
    return int(a + cruz[np.argmin(np.abs(cruz + a - i))]) if len(cruz) else int(i)


def emendar(a, b, n_cross):
    """Cola b depois de a com um cruzamento de n_cross amostras (seno² — soma de potência constante)."""
    n = min(n_cross, len(a), len(b))
    if n <= 1:
        return np.concatenate([a, b], axis=0)
    r = (np.sin(0.5 * np.pi * np.arange(n) / n) ** 2)[:, None]
    meio = a[-n:] * (1 - r) + b[:n] * r
    return np.concatenate([a[:-n], meio, b[n:]], axis=0)


def salto_na_juncao(x, i, raio_s=0.010):
    """Maior salto entre amostras vizinhas nos ±raio da junção, contra o p99,9 dos saltos em ±0,25 s."""
    m = mono(x)
    r, viz = int(raio_s * SR), int(0.25 * SR)
    a, b = max(0, i - r), min(len(m), i + r)
    d = np.abs(np.diff(m[a:b]))
    dv = np.abs(np.diff(m[max(0, i - viz):min(len(m), i + viz)]))
    return (float(d.max()) if len(d) else 0.0,
            float(np.percentile(dv, 99.9)) if len(dv) else 0.0)


def esticar(wav_novo, fator, trabalho):
    """atempo pelo ffmpeg (fator = duração nova / duração desejada); encadeia se sair da faixa 0,5–2."""
    cadeia, f = [], float(fator)
    while f > 2.0 or f < 0.5:
        passo = 2.0 if f > 2.0 else 0.5
        cadeia.append(passo)
        f /= passo
    cadeia.append(f)
    destino = Path(trabalho) / "_esticado.wav"
    ffmpeg("-v", "error", "-i", wav_novo, "-filter:a", ",".join(f"atempo={c:.6f}" for c in cadeia),
           "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", destino, rotulo="atempo")
    return destino


# ──────────────────────────────────────────────────────────── dublagem ──
def dublar(voz, t0, t1, novo, saida, tipo="texto", manter_duracao=True, projeto=".", trabalho=None):
    c = consent.exigir(projeto)
    voz, saida = Path(voz), Path(saida)
    trabalho = Path(trabalho) if trabalho else saida.parent / "_trabalho"
    trabalho.mkdir(parents=True, exist_ok=True)

    orig = ler(voz, trabalho=trabalho)
    i0, i1 = int(round(float(t0) * SR)), int(round(float(t1) * SR))
    if not 0 <= i0 < i1 <= len(orig):
        faltou(f"trecho fora do áudio: {t0}–{t1} s em {len(orig) / SR:.2f} s.")
    ia, ib = zero_mais_perto(orig, i0), zero_mais_perto(orig, i1)   # corta onde a onda cruza o zero
    buraco_s = (ib - ia) / SR
    viz = int(VIZINHANCA_S * SR)
    entorno = np.concatenate([orig[max(0, ia - viz):ia], orig[ib:min(len(orig), ib + viz)]], axis=0)
    if len(entorno) < SR // 2:
        entorno = np.concatenate([orig[:ia], orig[ib:]], axis=0)

    x = ler(novo, trabalho=trabalho)
    rel = {"voz": str(voz), "novo": str(novo), "saida": str(saida), "tipo": tipo,
           "consentimento": {k: c.get(k) for k in ("voz_de", "quem_autorizou", "data", "escopo")},
           "trecho": {"t0": round(float(t0), 3), "t1": round(float(t1), 3),
                      "corte_em_zero_s": [round(ia / SR, 4), round(ib / SR, 4)],
                      "duracao_s": round(buraco_s, 3)},
           "novo_duracao_s": round(len(x) / SR, 3)}

    # 1. duração
    natural = len(x) / SR
    fator = natural / buraco_s if buraco_s > 0 else 1.0
    atempo_aplicado, duracao_sobrou = 1.0, 0.0
    if manter_duracao and abs(fator - 1.0) > 1e-4:
        if abs(fator - 1.0) <= ATEMPO_MAX:
            x = ler(esticar(novo, fator, trabalho), trabalho=trabalho)
            atempo_aplicado = fator
            x = x[:ib - ia] if len(x) > ib - ia else np.concatenate(
                [x, np.zeros((ib - ia - len(x), 2))], axis=0)
        else:
            limite = 1 + np.sign(fator - 1) * ATEMPO_MAX
            x = ler(esticar(novo, float(fator / limite), trabalho), trabalho=trabalho)
            atempo_aplicado = float(fator / limite)
            duracao_sobrou = len(x) / SR - buraco_s
    else:
        duracao_sobrou = natural - buraco_s
    rel["atempo"] = {"fator_necessario": round(fator, 4), "fator_aplicado": round(atempo_aplicado, 4),
                     "limite": 1 + ATEMPO_MAX, "sobra_s": round(duracao_sobrou, 3)}

    # 2. timbre, 3. nível, 4. sala
    x, curva = casar_timbre(x, entorno)
    rel["eq_timbre_db"] = curva
    alvo_rms = rms_fala(entorno)
    ganho = alvo_rms - rms_fala(x)
    x = x * 10 ** (ganho / 20)
    rel["nivel"] = {"rms_fala_entorno_dbfs": round(alvo_rms, 2), "ganho_aplicado_db": round(ganho, 2)}
    bloco, chao_db = chao_de_ruido(entorno)
    x, pos = sala_por_baixo(x, bloco)
    rel["sala"] = {"chao_de_ruido_dbfs": round(chao_db, 1), "aplicado": bool(pos)}

    # 5. emenda em cruzamento por zero. O cruzamento SOBREPÕE as caudas do original (antes leva n_cross
    # amostras além do corte, depois começa n_cross antes), de modo que a duração final só muda o que o
    # trecho novo realmente mudou — a emenda em si não encurta nada.
    n_cross = int(CRUZAMENTO_S * SR)
    miolo = x.copy()
    f3 = int(0.003 * SR)                         # 3 ms de fade nas pontas do novo: começa e termina em zero
    miolo[:f3] *= np.linspace(0, 1, f3)[:, None]
    miolo[-f3:] *= np.linspace(1, 0, f3)[:, None]
    antes = orig[:min(ia + n_cross, len(orig))]
    depois = orig[max(ib - n_cross, 0):]
    y = emendar(emendar(antes, miolo, n_cross), depois, n_cross)
    gravar(saida, y)

    j1 = ia + n_cross // 2
    j2 = ia + len(miolo) - n_cross // 2
    emendas = []
    for nome, j in (("entrada", j1), ("saida", j2)):
        salto, normal = salto_na_juncao(y, j)
        emendas.append({"onde": nome, "t_s": round(j / SR, 3), "maior_salto": round(salto, 5),
                        "p99_9_na_vizinhanca": round(normal, 5),
                        "sem_clique": bool(salto <= max(normal * 1.5, 1e-4))})
    rel["emendas"] = emendas

    # 6. medidas do resultado
    def trecho_wav(nome, a, b):
        f = trabalho / f"_med_{nome}.wav"
        gravar(f, y[max(a, 0):min(b, len(y))])
        return ebur128(f)
    n_novo = len(miolo)
    a0 = ia
    rel["loudness"] = {
        "trecho_dublado": trecho_wav("dublado", a0, a0 + n_novo),
        "antes": trecho_wav("antes", max(0, a0 - viz), a0),
        "depois": trecho_wav("depois", a0 + n_novo, a0 + n_novo + viz),
    }
    lv = [rel["loudness"][k]["lufs"] for k in ("antes", "depois") if rel["loudness"][k]["lufs"] > -70]
    if lv:
        rel["loudness"]["diferenca_para_o_entorno_lufs"] = round(
            rel["loudness"]["trecho_dublado"]["lufs"] - float(np.mean(lv)), 2)

    # 7. a boca vai bater?
    motivos = []
    if abs(duracao_sobrou) > FOLGA_BOCA_S:
        motivos.append(f"a duração mudou {duracao_sobrou * 1000:+.0f} ms: o resto do vídeo anda e a boca sai do lugar")
    if abs(atempo_aplicado - 1.0) > 0.02:
        motivos.append(f"o trecho foi esticado {((atempo_aplicado - 1) * 100):+.1f}%: as sílabas não caem mais onde a boca abre")
    if tipo == "texto":
        motivos.append("texto→fala: as palavras mudaram, então a boca nunca vai bater neste trecho")
    rel["boca"] = {"bate": not motivos, "motivos": motivos,
                   "o_que_fazer": ("nada: dá para deixar o apresentador em tela" if not motivos else
                                   "cubra este trecho inteiro (b-roll, animação, cartela ou corte de retomada) "
                                   "do primeiro ao último quadro")}
    rel["duracao_final_s"] = round(len(y) / SR, 3)
    rel["deslocamento_depois_do_trecho_s"] = round(len(y) / SR - len(orig) / SR, 3)

    f = saida.with_suffix(".json")
    texto = json.dumps(rel, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texto, encoding="utf-8", newline="\n")
    return rel


def main():
    ap = argparse.ArgumentParser(description="Troca só o trecho errado da fala, casando a emenda.")
    ap.add_argument("voz", help="áudio original inteiro (WAV ou mídia)")
    ap.add_argument("--t0", type=float, required=True, help="início do trecho a trocar, em segundos")
    ap.add_argument("--t1", type=float, required=True, help="fim do trecho a trocar, em segundos")
    ap.add_argument("--novo", required=True, help="WAV com a fala que entra no lugar")
    ap.add_argument("--saida", default="som/dublagem/voz_dublada.wav")
    ap.add_argument("--tipo", default="texto", choices=["texto", "fala"],
                    help="texto = texto→fala (palavras novas); fala = fala→fala (mesma performance)")
    ap.add_argument("--manter-duracao", dest="manter", action="store_true", default=True,
                    help="encaixa no buraco com atempo de no máximo ±8%% (padrão)")
    ap.add_argument("--duracao-natural", dest="manter", action="store_false",
                    help="não estica: deixa a duração natural e empurra o resto da linha do tempo")
    ap.add_argument("--projeto", default=".", help="pasta do projeto (onde está som/dublagem/)")
    a = ap.parse_args()
    for arq in (a.voz, a.novo):
        if not Path(arq).is_file():
            faltou(f"não achei {arq}.")
    rel = dublar(a.voz, a.t0, a.t1, a.novo, a.saida, a.tipo, a.manter, a.projeto)
    L = rel["loudness"]
    print(f"{rel['saida']}: trecho {rel['trecho']['t0']}–{rel['trecho']['t1']} s trocado.")
    print(f"  nível: entorno {rel['nivel']['rms_fala_entorno_dbfs']} dBFS RMS, ganho {rel['nivel']['ganho_aplicado_db']:+.2f} dB; "
          f"LUFS do trecho {L['trecho_dublado']['lufs']:.1f} contra {L.get('diferenca_para_o_entorno_lufs', 0):+.2f} do entorno")
    print(f"  atempo: {rel['atempo']['fator_aplicado']:.4f} (precisava de {rel['atempo']['fator_necessario']:.4f}); "
          f"sobra {rel['atempo']['sobra_s'] * 1000:+.0f} ms")
    for e in rel["emendas"]:
        print(f"  emenda {e['onde']} em {e['t_s']} s: salto {e['maior_salto']:.5f} contra {e['p99_9_na_vizinhanca']:.5f} "
              f"normal — {'sem clique' if e['sem_clique'] else 'CLIQUE: confira a forma de onda'}")
    print(f"  boca: {'bate' if rel['boca']['bate'] else 'NÃO BATE'} — {rel['boca']['o_que_fazer']}")
    for m in rel["boca"]["motivos"]:
        print(f"     · {m}")
    print(f"  relatório: {Path(rel['saida']).with_suffix('.json')}")
    sys.exit(0 if all(e["sem_clique"] for e in rel["emendas"]) else 1)


if __name__ == "__main__":
    main()
