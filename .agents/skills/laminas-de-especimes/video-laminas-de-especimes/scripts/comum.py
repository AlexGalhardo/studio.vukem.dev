#!/usr/bin/env python3
"""Peças comuns das ferramentas do estilo: trava de máquina, Node >= 20 e ambiente do projeto.

Serve no macOS, no Linux e no Windows: nada de bash, de `which`, de caminho do Homebrew.
Importe (`from comum import com_trava, achar_node`) ou rode para ver o que foi encontrado:
    python3 tools/comum.py
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIN_NODE = 20


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude/skills/video-direcao-de-arte/kit/trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def programa(nome):
    """Caminho de um programa externo (acha o .exe sozinho no Windows) ou None."""
    return shutil.which(nome)


def exigir(*nomes):
    """Sai com código 2 listando o que falta."""
    faltam = [n for n in nomes if not programa(n)]
    if faltam:
        sys.exit(f"falta instalar: {', '.join(faltam)} — rode o preparar.py da skill com --instalar")
    return [programa(n) for n in nomes]


def _versao_node(exe):
    try:
        r = subprocess.run([exe, "-v"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return 0
    m = re.match(r"v?(\d+)", (r.stdout or "").strip())
    return int(m.group(1)) if m else 0


def achar_node():
    """Caminho de um Node >= 20 (o Playwright exige) ou None. PATH primeiro, depois os nvm."""
    candidatos = []
    no_path = shutil.which("node")
    if no_path:
        candidatos.append(Path(no_path))
    for raiz in (Path.home() / ".nvm" / "versions" / "node",
                 Path(os.environ.get("NVM_SYMLINK", "")) if os.environ.get("NVM_SYMLINK") else None,
                 Path(os.environ.get("ProgramFiles", "")) / "nodejs" if os.name == "nt" else None):
        if not raiz or not raiz.exists():
            continue
        if (raiz / "node.exe").exists() or (raiz / "node").exists():
            candidatos.append(raiz / ("node.exe" if os.name == "nt" else "node"))
            continue
        for v in sorted(raiz.iterdir(), reverse=True):
            for rel in ("bin/node", "node.exe", "node"):
                exe = v / rel
                if exe.exists():
                    candidatos.append(exe)
    for c in candidatos:
        if _versao_node(str(c)) >= MIN_NODE:
            return str(c)
    return None


def exigir_node():
    n = achar_node()
    if not n:
        sys.exit(f"nenhum Node >= {MIN_NODE} encontrado — instale o Node LTS "
                 "(nodejs.org, nvm, ou o gerenciador do seu sistema) e rode de novo")
    return n


def venv_python(projeto):
    """Caminho do python do venv do projeto (audio/.venv), em qualquer sistema."""
    p = Path(projeto) / "audio" / ".venv"
    exe = p / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return exe if exe.exists() else None


def ambiente(projeto):
    """Lê tools/ambiente.json do projeto (gravado pelo setup.py)."""
    f = Path(projeto) / "tools" / "ambiente.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


if __name__ == "__main__":
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(f"sistema : {platform.system()}")
    print(f"node    : {achar_node() or '(nenhum >= 20)'}")
    print(f"ffmpeg  : {programa('ffmpeg') or '(não achei)'}")
    print(f"ffprobe : {programa('ffprobe') or '(não achei)'}")
    print(f"python  : {venv_python(raiz) or '(venv do projeto não criado)'}")
    print(f"trava   : {'sim' if com_trava(['x'])[0] != 'x' else 'não (Windows ou sem a DA)'}")
