#!/usr/bin/env python3
"""Peças comuns das skills de estilo 3D/mapa: achar programas, Node, Python e a trava de memória.

Vale em Mac, Linux e Windows: nada de caminho fixo, nada de shell, texto sempre em utf-8.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent          # <skill>/
PROJETO = SKILL / "assets" / "projeto"                   # modelo de projeto que vai para o usuário
CASA = Path(os.environ.get("CRIABR_CASA", Path.home() / ".criabr"))


def ambiente():
    """Lê ~/.criabr/ambiente.json (gravado pelo preparar.py). Devolve {} se não existir."""
    f = CASA / "ambiente.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def achar_programa(nome):
    """Caminho de um programa externo, pelo PATH (acha o .exe no Windows) ou pelo ambiente.json."""
    c = ambiente().get(nome)
    if c and Path(c).exists():
        return c
    return shutil.which(nome)


def achar_node():
    """Caminho de um Node >= 20 (o Playwright exige). PATH, ambiente.json e, por fim, o nvm."""
    candidatos = [ambiente().get("node"), shutil.which("node")]
    candidatos += [str(p) for p in sorted(Path.home().glob(".nvm/versions/node/*/bin/node"), reverse=True)]
    for c in candidatos:
        if not c or not Path(c).exists():
            continue
        try:
            v = subprocess.run([c, "-v"], capture_output=True, text=True, encoding="utf-8", timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if v.startswith("v") and v[1:].split(".")[0].isdigit() and int(v[1:].split(".")[0]) >= 20:
            return c
    return None


def achar_python(modulos=("numpy",)):
    """Primeiro Python 3.10+ que importa os módulos pedidos (o do preparar.py, este, o do PATH)."""
    venv = CASA / ("venv/Scripts/python.exe" if platform.system() == "Windows" else "venv/bin/python")
    cands = [ambiente().get("python"), str(venv), sys.executable, shutil.which("python3"), shutil.which("python")]
    teste = "import sys; assert sys.version_info >= (3, 10)\n" + "".join(f"import {m}\n" for m in modulos)
    for c in cands:
        if c and Path(c).exists() and subprocess.run([c, "-c", teste], capture_output=True).returncode == 0:
            return c
    return None


def com_trava(cmd):
    """Devolve o comando, pela trava de memória quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude/skills/video-direcao-de-arte/kit/trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def rodar(cmd, **kw):
    """subprocess.run com lista de argumentos (nunca shell) e texto em utf-8."""
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], **kw)
