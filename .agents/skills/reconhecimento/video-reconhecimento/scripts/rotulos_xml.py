#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rotulos_xml.py — lê o XML (xmeml/FCP7, o que o Premiere exporta) de uma sequência em que o editor marcou os
clipes com ETIQUETA VERDE nos trechos em que a pessoa olha para a câmera, e devolve essas faixas em segundos
do BRUTO (os <in>/<out> do clipe, não o tempo da timeline).

Uso direto (para conferir o que ele leu):
  rotulos_xml.py <sequencia.xml> [mídia do bruto]
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.dont_write_bytecode = True
VERDES = ("verde", "green", "forest")


def _fps(no):
    r = no.find("rate")
    if r is None or not r.findtext("timebase"):
        return None
    fps = float(r.findtext("timebase"))
    if (r.findtext("ntsc") or "").strip().upper() == "TRUE":
        fps = fps * 1000.0 / 1001.0
    return fps


def _etiqueta(ci):
    lab = ci.find("labels")
    if lab is None:
        return ""
    return " ".join(t.text or "" for t in lab).strip().lower()


def trechos_rotulados(xml, midia=None):
    """Devolve (verdes, outros): listas de (src0, src1) em segundos do bruto."""
    xml = Path(xml)
    if not xml.is_file():
        raise FileNotFoundError(f"XML não encontrado: {xml}")
    raiz = ET.parse(str(xml)).getroot()
    seq = raiz.find(".//sequence")
    fps_seq = _fps(seq) if seq is not None else None
    verdes, outros = [], []
    for tr in raiz.findall(".//media/video/track"):
        achou = False
        for ci in tr.findall("clipitem"):
            arq = ci.find("file")
            caminho = ""
            if arq is not None and arq.findtext("pathurl"):
                caminho = unquote(urlparse(arq.findtext("pathurl")).path)
            if midia and caminho and Path(caminho).name.lower() != Path(midia).name.lower():
                continue
            fps = _fps(ci) or fps_seq or 30.0
            try:
                a, b = int(ci.findtext("in")) / fps, int(ci.findtext("out")) / fps
            except (TypeError, ValueError):
                continue
            if b <= a:
                continue
            achou = True
            etiqueta = _etiqueta(ci)
            (verdes if any(v in etiqueta for v in VERDES) else outros).append((a, b))
        if achou:
            break
    return sorted(verdes), sorted(outros)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 64
    v, o = trechos_rotulados(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"verdes (olhando para a câmera): {len(v)}")
    for a, b in v:
        print(f"  {a:8.2f}–{b:8.2f}")
    print(f"outros: {len(o)}")
    for a, b in o[:20]:
        print(f"  {a:8.2f}–{b:8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
