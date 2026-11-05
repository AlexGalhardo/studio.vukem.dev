#!/usr/bin/env python3
"""Roda o render.mjs com o Node certo e pela trava de máquina. Substitui `N=$($P tools/node.py)`.

uso (da raiz do projeto):
  python3 tools/render.py <nn>                      → out/<nn-nome>.mp4
  python3 tools/render.py <nn> --preview=12         → previews/<nn-nome>/ (folha de contato)
  python3 tools/render.py <nn> --at=0.4,1.2,3.6     → quadros nos instantes pedidos
Tudo o que vier depois do nome é repassado ao render.mjs sem mudança.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import com_trava, exigir, exigir_node  # noqa: E402

raiz = Path(__file__).resolve().parent.parent
mjs = raiz / "render.mjs"
if not mjs.exists():
    sys.exit(f"não achei {mjs} — rode o setup.py da skill apontando para esta pasta")
exigir("ffmpeg")
cmd = com_trava([exigir_node(), str(mjs), *sys.argv[1:]])
sys.exit(subprocess.run(cmd, cwd=raiz).returncode)
