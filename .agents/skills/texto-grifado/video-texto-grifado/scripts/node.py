#!/usr/bin/env python3
"""Imprime o caminho de um Node >= 20 (o Playwright exige). Serve no Mac, no Linux e no Windows.

uso:  python3 tools/node.py          → imprime o caminho (código 1 se não achar)
Em geral você não precisa dele: use `python3 tools/render.py`, que já acha o Node sozinho.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import achar_node, MIN_NODE  # noqa: E402

n = achar_node()
if not n:
    print(f"nenhum Node >= {MIN_NODE} encontrado — instale o Node LTS e rode de novo", file=sys.stderr)
    sys.exit(1)
print(n)
