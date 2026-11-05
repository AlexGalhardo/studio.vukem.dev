#!/usr/bin/env python3
"""Ajudas comuns dos scripts desta skill: achar o Node e o Python certos e rodar pela trava.

Nada aqui é específico de sistema: Mac, Linux e Windows usam o mesmo código.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

CASA = Path(os.environ.get("CRIABR_CASA", Path.home() / ".criabr"))
NODE_MINIMO = 20


def ambiente():
    """O que o preparar.py gravou em ~/.criabr/ambiente.json (python, node, ...)."""
    f = CASA / "ambiente.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude" / "skills" / "video-direcao-de-arte" / "kit" / "trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def saida(cmd):
    """Roda e devolve a saída de texto, ou None se não deu."""
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def achar_node():
    """Caminho de um Node >= 20 (o Playwright exige), ou None."""
    candidatos = [ambiente().get("node"), shutil.which("node")]
    candidatos += [str(p) for p in sorted(Path.home().glob(".nvm/versions/node/*/bin/node"), reverse=True)]
    for c in candidatos:
        if not c or not Path(c).exists():
            continue
        v = saida([c, "-v"]) or ""
        try:
            if int(v.lstrip("v").split(".")[0]) >= NODE_MINIMO:
                return c
        except (ValueError, IndexError):
            continue
    return None


def achar_python(modulos=("numpy", "scipy")):
    """Primeiro Python que importa os módulos pedidos (o do preparar.py, o atual, o do PATH)."""
    candidatos = [ambiente().get("python"), sys.executable, shutil.which("python3"), shutil.which("python")]
    teste = "".join("import %s\n" % m for m in modulos)
    for c in candidatos:
        if not c or not Path(c).exists():
            continue
        if subprocess.run([c, "-c", teste], capture_output=True).returncode == 0:
            return c
    return None


def achar_ffmpeg():
    return shutil.which("ffmpeg")


def rodar(cmd, cwd=None, trava=True):
    """Roda o comando (lista de argumentos, nunca shell) e devolve o código de saída."""
    cmd = [str(c) for c in cmd]
    if trava:
        cmd = com_trava(cmd)
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode


def projeto(argv, uso):
    """Primeiro argumento = pasta do projeto; o resto vai adiante."""
    if not argv or argv[0].startswith("-"):
        print(uso)
        sys.exit(1)
    p = Path(argv[0]).expanduser().resolve()
    if not (p / "render.mjs").exists():
        print("não é um projeto deste estilo (falta render.mjs): %s" % p)
        print("crie com: python3 <skill>/scripts/novo_projeto.py \"%s\"" % p)
        sys.exit(2)
    return p, argv[1:]
