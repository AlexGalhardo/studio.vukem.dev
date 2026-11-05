#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calibrar.py — lê o XML (xmeml/FCP7, o que o Premiere exporta) de uma decupagem FEITA À MÃO e mede os
parâmetros do editor sobre o mesmo bruto: quanto de respiro ele deixa antes e depois da fala, que tamanho de
pausa ele aceita e quanto do material ele tirou. O decupar.py usa esses números em vez dos padrões.

Uso direto (só para ver os números):
  calibrar.py <decupagem.xml> <mídia do bruto>
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402


def _fps(no):
    """<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate> → 29,97."""
    r = no.find("rate")
    if r is None:
        return None
    tb = r.findtext("timebase")
    if not tb:
        return None
    fps = float(tb)
    if (r.findtext("ntsc") or "").strip().upper() == "TRUE":
        fps = fps * 1000.0 / 1001.0
    return fps


def trechos_do_xml(xml, nome_arquivo=None):
    """Trechos do BRUTO que o editor manteve: [(src0, src1)] em segundos, em ordem de timeline."""
    xml = Path(xml)
    if not xml.is_file():
        raise C.Erro(f"XML não encontrado: {xml}")
    try:
        raiz = ET.parse(str(xml)).getroot()
    except ET.ParseError as e:
        raise C.Erro(f"{xml.name} não é um XML válido: {e}.",
                     "Exporte do Premiere em Arquivo → Exportar → Final Cut Pro XML.")
    seq = raiz.find(".//sequence")
    fps_seq = _fps(seq) if seq is not None else None
    itens = []
    for tr in raiz.findall(".//media/video/track"):
        for ci in tr.findall("clipitem"):
            arq = ci.find("file")
            caminho = ""
            if arq is not None and arq.findtext("pathurl"):
                caminho = unquote(urlparse(arq.findtext("pathurl")).path)
            if nome_arquivo and caminho and Path(caminho).name.lower() != Path(nome_arquivo).name.lower():
                continue
            fps = _fps(ci) or fps_seq or 30.0
            try:
                ini, fim = int(ci.findtext("in")), int(ci.findtext("out"))
                tl = int(ci.findtext("start"))
            except (TypeError, ValueError):
                continue
            if fim <= ini or tl < 0:
                continue
            itens.append((tl, ini / fps, fim / fps, Path(caminho).name))
        if itens:
            break   # a primeira trilha de vídeo que tem clipes do bruto é a trilha da decupagem
    if not itens:
        raise C.Erro(f"{xml.name} não tem clipes de vídeo com in/out"
                     + (f" do arquivo {Path(nome_arquivo).name}." if nome_arquivo else "."),
                     "Confira se o XML é da sequência decupada e se aponta para o mesmo bruto.", 2)
    itens.sort()
    return [(a, b) for _, a, b, _ in itens]


def calibrar(xml, midia):
    """Mede os parâmetros do editor comparando os trechos mantidos com a energia do áudio do bruto."""
    import numpy as np
    trechos = trechos_do_xml(xml, midia)
    f = C.ficha(midia)
    db = C.energia_db(C.pcm(midia, canais=1))
    lim = C.limiar_fala(db)
    dur = min(f["duracao"], len(db) * C.PASSO)
    ilhas = C.ilhas(db, lim)

    respiro_ini, respiro_fim, pausas, dentro = [], [], [], 0.0
    for a, b in trechos:
        dentro += max(0.0, min(b, dur) - a)
        fala = [(s, e) for s, e, _ in ilhas if e > a + 0.01 and s < b - 0.01]
        if not fala:
            continue
        respiro_ini.append(max(0.0, fala[0][0] - a))
        respiro_fim.append(max(0.0, b - fala[-1][1]))
        for (_, e1), (s2, _) in zip(fala, fala[1:]):
            if s2 - e1 > 0.05:
                pausas.append(s2 - e1)

    def mediana(v, padrao):
        return round(float(np.median(v)), 3) if v else padrao

    p90 = round(float(np.percentile(pausas, 90)), 3) if pausas else None
    medidas = {
        "trechos_mantidos": len(trechos),
        "duracao_mantida_s": round(dentro, 2),
        "duracao_bruto_s": round(dur, 2),
        "removido_por_cento": round(100 * (1 - dentro / max(dur, 1e-6)), 1),
        "respiro_inicio_mediano_s": mediana(respiro_ini, None),
        "respiro_fim_mediano_s": mediana(respiro_fim, None),
        "pausa_interna_mediana_s": mediana(pausas, None),
        "pausa_interna_p90_s": p90,
        "pausa_interna_maxima_s": round(max(pausas), 3) if pausas else None,
        "limiar_fala_dbfs": round(lim, 1),
    }
    respiro = None
    if respiro_ini or respiro_fim:
        respiro = round(min(0.40, max(0.03, float(np.median((respiro_ini or [0]) + (respiro_fim or [0]))))), 3)
    pausa_max = round(min(2.0, max(0.12, p90)), 3) if p90 else None
    return {"xml": str(Path(xml).name), "medidas": medidas,
            "parametros": {"pausa_max": pausa_max, "respiro": respiro},
            "observacao": "pausa_max = percentil 90 das pausas que o editor MANTEVE; respiro = mediana do "
                          "silêncio que ele deixou nas pontas de cada trecho."}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 64
    import json
    c = calibrar(sys.argv[1], sys.argv[2])
    print(json.dumps(c, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except C.Erro as e:
        sys.exit(C.sair_com_erro(e))
