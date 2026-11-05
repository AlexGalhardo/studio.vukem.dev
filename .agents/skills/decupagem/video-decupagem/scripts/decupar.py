#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decupar.py — acha o que sai do bruto (retomadas, repetições, gaguejos, pausas mortas, sobras de bastidor),
DEIXA A ÚLTIMA TENTATIVA e grava a EDL com os trechos que ficam.

Uso:
  decupar.py <mídia> --palavras transcricao/palavras.json --saida cortes/ [--rigido] [--calibrar <xml>]
             [--pausa-max S] [--respiro S] [--sem-repeticao] [--sem-pausa] [--manter A-B ...]

Sai em <saida>/:
  edl.json        {"fonte", "cortes":[{"src0","src1","motivo"}]} — os trechos que FICAM, em ordem (padrão da casa)
  removidos.json  cada trecho que saiu, com o motivo, o texto e a evidência (energia nas pontas, palavras)
  analise.json    o material dos analistas: ilhas de fala, pausas, repetições candidatas, palavras de baixa confiança
  relatorio.md    leitura humana em mm:ss

Códigos: 0 ok · 1 falhou · 2 falta insumo (transcrição, áudio).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402
import calibrar as CAL  # noqa: E402

# Padrões medidos nas decupagens manuais dos projetos (ver SKILL.md).
PADRAO = {"pausa_max": 0.60, "respiro": 0.12, "cabeca_cauda": True, "min_lcp": 3,
          "max_palavras_retomada": 40, "janela_retomada": 45, "pausa_recomeco": 0.12}
RIGIDO = {"pausa_max": 0.30, "respiro": 0.07, "cabeca_cauda": True, "min_lcp": 2,
          "max_palavras_retomada": 40, "janela_retomada": 45, "pausa_recomeco": 0.06}
MULETAS = {"e", "eh", "ah", "ahn", "hum", "han", "ha", "uhum", "entao", "tipo", "ne"}
MIN_TRECHO = 0.10          # trecho que fica menor que isto é descartado
BUSCA_VALE = 0.30          # até onde procurar o silêncio para encaixar o corte


# ----------------------------------------------------------------- fala na energia

def fim_som(db, lim, t, limite=1.5, passo=C.PASSO):
    """Anda para a frente enquanto houver som: a palavra costuma durar mais do que o whisper diz."""
    i, n = max(0, int(t / passo)), 0
    while i < len(db) and db[i] > lim and n * passo < limite:
        i += 1
        n += 1
    return i * passo


def ini_som(db, lim, t, limite=1.5, passo=C.PASSO):
    """Anda para trás enquanto houver som."""
    i, n = min(len(db) - 1, int(t / passo)), 0
    while i > 0 and db[i - 1] > lim and n * passo < limite:
        i -= 1
        n += 1
    return i * passo


# ----------------------------------------------------------------- analistas

def analista_retomadas(palavras, cfg, db, lim):
    """Retomada: o apresentador começa uma frase, abandona e RECOMEÇA com as mesmas palavras. Acha o maior
    começo repetido entre duas posições próximas e manda fora a tentativa de trás — fica a última.

    Cuidado que custou caro: o whisper FUNDE retomadas e apaga gaguejos. Por isso a conta é feita sobre as
    palavras do bruto (passada palavra a palavra), nunca sobre a retranscrição do resultado.
    """
    chaves = [C.chave(p["w"]) for p in palavras]
    n = len(chaves)
    achados = []
    for j in range(1, n):
        if not chaves[j]:
            continue
        # 1ª peneira: o apresentador PAROU antes de recomeçar? Repetição colada na fala anterior é ênfase
        # ("confere, cara, confere"), não retomada — e tirar ênfase estraga o vídeo.
        parou = ini_som(db, lim, palavras[j]["t0"]) - fim_som(db, lim, palavras[j - 1]["t1"])
        if parou < cfg["pausa_recomeco"]:
            continue
        # 2ª peneira: frase anterior terminada com ponto final é conteúdo, não tentativa abandonada
        if palavras[j - 1]["w"].rstrip("\"')»”’").endswith((".", "!", "?")):
            continue
        melhor = None
        i0 = max(0, j - cfg["janela_retomada"])
        for i in range(i0, j):
            k = 0
            while j + k < n and chaves[i + k] and chaves[i + k] == chaves[j + k] and i + k < j:
                k += 1
            if k < 2:
                continue
            letras = sum(len(chaves[i + m]) for m in range(k))
            forte = k >= cfg["min_lcp"] or (k >= 2 and letras >= 9)
            if forte and (melhor is None or k > melhor[1]):
                melhor = (i, k)
        if melhor is None:
            continue
        i, k = melhor
        # 3ª peneira: tentativa abandonada é curta em relação ao que foi recomeçado. Tirar 24 palavras
        # porque 4 se repetiram lá na frente apaga conteúdo (medido na amostra: foi o único falso positivo).
        if j - i > min(cfg["max_palavras_retomada"], max(12, 4 * k)):
            continue
        achados.append({"i": i, "j": j, "palavras_iguais": k,
                        "abandonada": " ".join(p["w"] for p in palavras[i:j]),
                        "ficou": " ".join(p["w"] for p in palavras[j:j + k]),
                        "pausa_no_recomeco_s": round(parou, 2),
                        "t0": palavras[i]["t0"], "t1": palavras[j]["t0"]})
    # tira os encaixados: se uma retomada já cobre a outra, fica a que cobre mais
    achados.sort(key=lambda a: (a["i"], -(a["j"] - a["i"])))
    saida = []
    for a in achados:
        if saida and a["j"] <= saida[-1]["j"]:
            continue
        if saida and a["i"] < saida[-1]["j"]:
            a = dict(a, i=saida[-1]["j"], t0=palavras[saida[-1]["j"]]["t0"])
            if a["i"] >= a["j"]:
                continue
        saida.append(a)
    return saida


def analista_gaguejos(palavras):
    """Gaguejo: a mesma palavra (ou o começo dela) duas vezes seguidas — 'que que', 'a a', 'pro… professor'.
    Sai a de trás."""
    chaves = [C.chave(p["w"]) for p in palavras]
    achados = []
    for k in range(len(chaves) - 1):
        a, b = chaves[k], chaves[k + 1]
        if not a or not b:
            continue
        igual = a == b and len(a) <= 6
        comeco = len(a) >= 2 and a != b and b.startswith(a) and len(b) - len(a) >= 2
        if igual or comeco:
            achados.append({"i": k, "j": k + 1, "tipo": "repetida" if igual else "começo da palavra",
                            "texto": f"{palavras[k]['w']} {palavras[k + 1]['w']}",
                            "t0": palavras[k]["t0"], "t1": palavras[k + 1]["t0"]})
    return achados


def analista_muletas(palavras, db, lim, cfg):
    """Muleta solta: 'é…', 'ãh', 'hum' sozinha entre duas pausas. Só sai no modo rígido."""
    achados = []
    for k, p in enumerate(palavras):
        if C.chave(p["w"]) not in MULETAS or len(C.chave(p["w"])) > 5:
            continue
        antes = p["t0"] - palavras[k - 1]["t1"] if k else 9.0
        depois = palavras[k + 1]["t0"] - p["t1"] if k + 1 < len(palavras) else 9.0
        if antes >= 0.20 and depois >= 0.20:
            achados.append({"i": k, "j": k + 1, "texto": p["w"], "t0": p["t0"], "t1": p["t1"],
                            "pausa_antes": round(antes, 2), "pausa_depois": round(depois, 2)})
    return achados


def analista_pausas(palavras, db, lim, cfg, dur):
    """Pausa morta entre duas palavras que ficam: sai o miolo, fica `respiro` de cada lado."""
    achados = []
    for k in range(1, len(palavras)):
        p, n = palavras[k - 1], palavras[k]
        if n["t0"] - p["t1"] < cfg["pausa_max"] * 0.6:
            continue
        s0, s1 = fim_som(db, lim, p["t1"]), ini_som(db, lim, n["t0"])
        if s1 - s0 <= cfg["pausa_max"]:
            continue
        r0, r1 = s0 + cfg["respiro"], s1 - cfg["respiro"]
        if r1 - r0 < MIN_TRECHO:
            continue
        achados.append({"t0": r0, "t1": r1, "pausa_s": round(s1 - s0, 2),
                        "fica_s": round(2 * cfg["respiro"], 2),
                        "entre": f"…{p['w']} ‖ {n['w']}…"})
    return achados


# ----------------------------------------------------------------- montador

def montar(midia, palavras, cfg, opcoes):
    """Junta o que os analistas acharam, encaixa cada ponta no silêncio e na fronteira de quadro, e devolve
    (cortes que ficam, removidos, análise)."""
    f = C.ficha(midia)
    grade = C.Grade(f["fps"])
    x = C.pcm(midia, canais=1)
    db = C.energia_db(x)
    lim = C.limiar_fala(db)
    dur = min(f["duracao"], len(db) * C.PASSO)
    ilhas = C.ilhas(db, lim)

    retomadas = [] if opcoes.sem_repeticao else analista_retomadas(palavras, cfg, db, lim)
    gaguejos = [] if opcoes.sem_repeticao else analista_gaguejos(palavras)
    muletas = analista_muletas(palavras, db, lim, cfg) if opcoes.rigido else []
    # palavras que já saem por retomada não entram de novo em gaguejo/muleta
    def dentro(k):
        return any(a["i"] <= k < a["j"] for a in retomadas)

    gaguejos = [a for a in gaguejos if not dentro(a["i"])]
    muletas = [a for a in muletas if not dentro(a["i"])]

    fora = []   # (t0, t1, motivo, detalhe)
    for a in retomadas:
        fora.append((a["t0"], a["t1"], "retomada",
                     f"{a['palavras_iguais']} palavras recomeçadas · sai «{a['abandonada'][:140]}»"))
    for a in gaguejos:
        fora.append((a["t0"], a["t1"], "gaguejo", f"{a['tipo']}: «{a['texto']}»"))
    for a in muletas:
        fora.append((a["t0"], a["t1"], "muleta", f"«{a['texto']}» solta entre pausas"))

    # cabeça e cauda: o que está fora do take
    if cfg["cabeca_cauda"] and palavras:
        p0 = ini_som(db, lim, palavras[0]["t0"]) - cfg["respiro"]
        if p0 > 0.12:
            fora.append((0.0, p0, "fora do take", "antes da primeira palavra (bastidor, espera)"))
        p1 = fim_som(db, lim, palavras[-1]["t1"]) + cfg["respiro"]
        if dur - p1 > 0.12:
            fora.append((p1, dur, "fora do take", "depois da última palavra"))

    if not opcoes.sem_pausa:
        for a in analista_pausas(palavras, db, lim, cfg, dur):
            fora.append((a["t0"], a["t1"], "pausa",
                         f"pausa de {a['pausa_s']} s → fica {a['fica_s']} s · {a['entre']}"))

    for a, b in opcoes.manter:
        fora = [t for t in fora if t[1] <= a or t[0] >= b]

    # encaixa cada ponta no vale de energia mais perto, já na fronteira de quadro e SEM SAIR DO VÃO ENTRE
    # PALAVRAS (fora do vão o corte parte a palavra ao meio: aconteceu, 27 ms dentro de «que»)
    blocos = C.blocos_de_palavras(palavras)
    ajustados = []
    for t0, t1, motivo, detalhe in sorted(fora):
        a = 0.0 if t0 <= 0.001 else grade.vale(db, t0, BUSCA_VALE, BUSCA_VALE, limites=C.vao(blocos, t0, dur))
        b = dur if t1 >= dur - 0.001 else grade.vale(db, t1, BUSCA_VALE, BUSCA_VALE, limites=C.vao(blocos, t1, dur))
        if b - a < MIN_TRECHO:
            continue
        ajustados.append({"t0": round(a, 4), "t1": round(b, 4), "motivo": motivo, "detalhe": detalhe,
                          "db_saida": round(C.db_em(db, a, C.CRUZADO), 1),
                          "db_entrada": round(C.db_em(db, b, C.CRUZADO), 1)})
    # une o que se sobrepõe
    unidos = []
    for r in ajustados:
        if unidos and r["t0"] <= unidos[-1]["t1"] + 1e-6:
            u = unidos[-1]
            u["t1"] = max(u["t1"], r["t1"])
            if r["motivo"] not in u["motivo"]:
                u["motivo"] += " + " + r["motivo"]
            u["detalhe"] += " | " + r["detalhe"]
            u["db_entrada"] = r["db_entrada"]
        else:
            unidos.append(dict(r))

    # complemento: o que FICA. Cada trecho guarda qual remoção vem logo ANTES dele (é a junção que o
    # verificador precisa conferir) — sem isso o relatório desalinha quando a primeira remoção é a cabeça.
    cortes, cursor, anterior = [], 0.0, None
    for r in unidos:
        if r["t0"] - cursor >= MIN_TRECHO:
            cortes.append({"src0": round(grade.encaixa(cursor), 4), "src1": round(r["t0"], 4), "antes": anterior})
        cursor = max(cursor, r["t1"])
        anterior = r
    if dur - cursor >= MIN_TRECHO:
        cortes.append({"src0": round(cursor, 4), "src1": round(grade.encaixa(dur), 4), "antes": anterior})
    if not cortes:
        raise C.Erro("a decupagem não deixou nenhum trecho.",
                     "Confira a transcrição (--palavras) e a mídia; com --sem-pausa --sem-repeticao sobra o take inteiro.")
    for i, c in enumerate(cortes):
        a = c["antes"]
        c["motivo"] = f"fala {i + 1}" + (f" (entra depois de: {a['motivo']})" if a else "")
        c["texto"] = " ".join(p["w"] for p in palavras if c["src0"] - 0.02 <= p["t0"] < c["src1"] - 0.02)

    folgas = []
    for i, c in enumerate(cortes):
        for campo in ("src0", "src1"):
            t = c[campo]
            if (i == 0 and campo == "src0") or (i == len(cortes) - 1 and campo == "src1"):
                continue          # pontas do arquivo, não são emenda
            folgas.append({"t": t, "campo": campo,
                           "folga_ms": round(1000 * C.folga_palavra(t, blocos, f["fps"]), 1)})

    analise = {"limiar_fala_dbfs": round(lim, 1), "duracao_bruto_s": round(dur, 2),
               "folga_ate_borda_de_palavra": {
                   "menor_ms": min((x["folga_ms"] for x in folgas), default=None),
                   "cortes_dentro_de_palavra": sum(1 for x in folgas if x["folga_ms"] < 0),
                   "por_corte": folgas},
               "fps": f["fps_fracao"], "ilhas_de_fala": len(ilhas),
               "parametros": cfg,
               "retomadas": retomadas, "gaguejos": gaguejos, "muletas": muletas,
               "baixa_confianca": [{"t0": p["t0"], "w": p["w"], "p": p["p"]} for p in palavras if p["p"] < 0.55],
               "pausas_mantidas": [{"t0": round(a[1], 2), "t1": round(b[0], 2), "dur": round(b[0] - a[1], 2)}
                                   for a, b in zip(ilhas, ilhas[1:]) if b[0] - a[1] >= 0.25]}
    return f, cortes, unidos, analise, db, lim


# ----------------------------------------------------------------- relatório

def relatorio(f, cortes, removidos, analise, cfg, rigido):
    dur_nova = sum(c["src1"] - c["src0"] for c in cortes)
    L = [f"# Decupagem — {Path(f['arquivo']).name}", "",
         f"**{C.mmss(dur_nova)}** de {C.mmss(analise['duracao_bruto_s'])} de bruto "
         f"({len(cortes)} trecho(s) ficam, {len(removidos)} saem, "
         f"−{C.mmss(analise['duracao_bruto_s'] - dur_nova)}). Modo {'rígido' if rigido else 'normal'}: "
         f"pausa máxima {cfg['pausa_max']} s, respiro {cfg['respiro']} s. "
         f"Limiar de fala medido no material: {analise['limiar_fala_dbfs']} dBFS.", ""]
    fo = analise.get("folga_ate_borda_de_palavra") or {}
    if fo.get("menor_ms") is not None:
        L += [f"Nenhum corte parte palavra: menor folga até a borda de palavra mais perto = "
              f"**{fo['menor_ms']:.1f} ms** ({fo['cortes_dentro_de_palavra']} corte(s) dentro de palavra)."
              if fo["cortes_dentro_de_palavra"] == 0 else
              f"ATENÇÃO: {fo['cortes_dentro_de_palavra']} corte(s) caem DENTRO de palavra "
              f"(menor folga {fo['menor_ms']:.1f} ms).", ""]
    L += [
         "## O que saiu", "", "| # | bruto | dur | motivo | o que se ouvia |", "|---|---|---|---|---|"]
    for i, r in enumerate(removidos, 1):
        L.append(f"| {i} | {C.mmss(r['t0'])}–{C.mmss(r['t1'])} | {r['t1'] - r['t0']:.2f} s | {r['motivo']} "
                 f"| {r['detalhe'][:200].replace('|', '/')} |")
    L += ["", "## O que ficou", "", "| # | novo | bruto | fala |", "|---|---|---|---|"]
    t = 0.0
    for i, c in enumerate(cortes, 1):
        d = c["src1"] - c["src0"]
        L.append(f"| {i} | {C.mmss(t)}–{C.mmss(t + d)} | {C.mmss(c['src0'])}–{C.mmss(c['src1'])} "
                 f"| {c.get('texto', '')[:220].replace('|', '/')} |")
        t += d
    L += ["", "## Junções (confira uma a uma)", "",
          "| junção | sai em | dB | entra em | dB | risco |", "|---|---|---|---|---|---|"]
    for i in range(1, len(cortes)):
        r = cortes[i].get("antes") or {}
        risco = []
        if r.get("db_saida", -99) > analise["limiar_fala_dbfs"]:
            risco.append("SAI DENTRO DE FALA")
        if r.get("db_entrada", -99) > analise["limiar_fala_dbfs"]:
            risco.append("ENTRA DENTRO DE FALA")
        L.append(f"| J{i - 1:02d} | {C.mmss(cortes[i - 1]['src1'])} | {r.get('db_saida')} | "
                 f"{C.mmss(cortes[i]['src0'])} | {r.get('db_entrada')} | {' · '.join(risco) or 'ok'} |")
    if analise["baixa_confianca"]:
        L += ["", f"## Palavras que o whisper ouviu mal ({len(analise['baixa_confianca'])}) — confira antes de cortar", "",
              " · ".join(f"{C.mmss(b['t0'])} «{b['w']}» p={b['p']:.2f}" for b in analise["baixa_confianca"][:40])]
    return "\n".join(L)


# ----------------------------------------------------------------- principal

def main():
    ap = argparse.ArgumentParser(description="Decupa o bruto pela energia do áudio e pelas palavras.")
    ap.add_argument("midia")
    ap.add_argument("--palavras", required=True, help="transcricao/palavras.json (skill video-transcricao)")
    ap.add_argument("--saida", default="cortes", help="pasta de saída (padrão: cortes/)")
    ap.add_argument("--rigido", action="store_true", help="corta pausa curta e muleta solta também")
    ap.add_argument("--calibrar", help="XML do Premiere de uma decupagem manual: mede os parâmetros do editor")
    ap.add_argument("--pausa-max", type=float, help="pausa maior que isto vira corte (s)")
    ap.add_argument("--respiro", type=float, help="sobra de silêncio de cada lado da fala (s)")
    ap.add_argument("--sem-repeticao", action="store_true", help="não tirar retomadas nem gaguejos")
    ap.add_argument("--sem-pausa", action="store_true", help="não encurtar pausas")
    ap.add_argument("--manter", action="append", default=[], metavar="A-B",
                    help="trecho do bruto que não pode ser tocado, em segundos (ex.: 12.0-19.5)")
    o = ap.parse_args()

    cfg = dict(RIGIDO if o.rigido else PADRAO)
    calib = None
    if o.calibrar:
        calib = CAL.calibrar(o.calibrar, o.midia)
        cfg.update({k: v for k, v in calib["parametros"].items() if v is not None})
    if o.pausa_max is not None:
        cfg["pausa_max"] = o.pausa_max
    if o.respiro is not None:
        cfg["respiro"] = o.respiro
    o.manter = [tuple(float(v) for v in m.replace(",", ".").split("-", 1)) for m in o.manter]

    palavras = C.ler_palavras(o.palavras)
    f, cortes, removidos, analise, db, lim = montar(o.midia, palavras, cfg, o)

    saida = Path(o.saida)
    fonte = Path(f["arquivo"])
    try:
        fonte_rel = fonte.relative_to(Path.cwd())
    except ValueError:
        fonte_rel = fonte
    C.gravar_json(saida / "edl.json", {
        "fonte": str(fonte_rel).replace("\\", "/"),
        "fps": f["fps_fracao"], "duracao_bruto_s": round(analise["duracao_bruto_s"], 3),
        "modo": "rigido" if o.rigido else "normal", "parametros": cfg,
        "cortes": [{"src0": c["src0"], "src1": c["src1"], "motivo": c["motivo"]} for c in cortes]})
    C.gravar_json(saida / "removidos.json", removidos)
    C.gravar_json(saida / "analise.json", analise)
    if calib:
        C.gravar_json(saida / "calibracao.json", calib)
    C.gravar_texto(saida / "relatorio.md", relatorio(f, cortes, removidos, analise, cfg, o.rigido))

    dur_nova = sum(c["src1"] - c["src0"] for c in cortes)
    print(f"{len(cortes)} trecho(s) ficam · {len(removidos)} sai(em) · "
          f"{C.mmss(dur_nova)} de {C.mmss(analise['duracao_bruto_s'])} "
          f"(−{100 * (1 - dur_nova / max(analise['duracao_bruto_s'], 1e-6)):.0f}%)")
    for m in ("retomada", "gaguejo", "muleta", "pausa", "fora do take"):
        n = sum(1 for r in removidos if m in r["motivo"])
        if n:
            print(f"  {m}: {n}")
    fo = analise["folga_ate_borda_de_palavra"]
    if fo["menor_ms"] is not None:
        print(f"  folga até a borda de palavra: menor {fo['menor_ms']:.1f} ms · "
              f"{fo['cortes_dentro_de_palavra']} corte(s) dentro de palavra")
    print(f"EDL: {saida / 'edl.json'} · relatório: {saida / 'relatorio.md'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except C.Erro as e:
        sys.exit(C.sair_com_erro(e))
