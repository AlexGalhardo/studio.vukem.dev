#!/usr/bin/env python3
"""Cria (ou completa) um projeto deste estilo, pronto para renderizar. Serve no Mac, no Linux e no Windows.

uso:  python3 <pasta-da-skill>/scripts/setup.py <pasta-do-projeto>
      [--sem-navegador]  pula o download do Chromium do Playwright (se já tiver um)

Faz, em ordem: confere ffmpeg/ffprobe e um Node >= 20, copia assets/projeto para a pasta, roda
`npm install`, baixa o Chromium do Playwright, cria o venv em audio/.venv com numpy/scipy/pillow,
copia as ferramentas para tools/ e grava tools/ambiente.json com os caminhos encontrados.
Códigos de saída: 0 pronto · 1 falhou · 2 falta insumo (programa externo).
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import achar_node, com_trava, programa, venv_python  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
PIP = ["numpy", "scipy", "pillow"]


def roda(cmd, **k):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], **k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("destino", help="pasta do projeto (criada se não existir)")
    ap.add_argument("--sem-navegador", action="store_true", help="não baixa o Chromium do Playwright")
    a = ap.parse_args()
    dest = Path(a.destino).expanduser().resolve()

    faltam = [p for p in ("ffmpeg", "ffprobe") if not programa(p)]
    if faltam:
        print(f"falta instalar: {', '.join(faltam)}. Rode o preparar.py desta skill com --instalar.")
        return 2
    node = achar_node()
    if not node:
        print("nenhum Node >= 20 encontrado (o Playwright exige). Instale o Node LTS e rode de novo.")
        return 2

    if not (dest / "render.mjs").exists():
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL / "assets" / "projeto", dest, dirs_exist_ok=True)
        print(f"projeto criado em {dest}")
    for sub in ("tools", "previews", "out", "audio"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    npm = programa("npm")
    if not (dest / "node_modules" / "playwright").is_dir() or not (dest / "node_modules" / "gsap").is_dir():
        if not npm:
            print("não achei o npm (vem com o Node). Instale o Node LTS e rode de novo.")
            return 2
        if roda([npm, "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=dest).returncode:
            print("npm install falhou")
            return 1

    if not a.sem_navegador:
        cli = dest / "node_modules" / "playwright" / "cli.js"
        if cli.exists():
            roda(com_trava([node, str(cli), "install", "chromium"]), cwd=dest,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    py = venv_python(dest)
    if not py:
        if roda([sys.executable, "-m", "venv", str(dest / "audio" / ".venv")]).returncode:
            print("não consegui criar o venv em audio/.venv")
            return 1
        py = venv_python(dest)
    if py and roda([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", *PIP]).returncode:
        print(f"não consegui instalar {', '.join(PIP)} no venv")
        return 1

    for f in sorted((SKILL / "scripts").glob("*.py")):
        if f.name in ("setup.py", "preparar.py"):
            continue
        shutil.copy2(f, dest / "tools" / f.name)

    swift = SKILL / "scripts" / "cutout.swift"
    alvo = dest / "tools" / "cutout"
    if swift.exists() and platform.system() == "Darwin" and not alvo.exists():
        swiftc = programa("swiftc")
        if swiftc:
            roda([swiftc, "-O", str(swift), "-o", str(alvo)])
        else:
            print("aviso: sem swiftc — o recorte automático por Vision fica indisponível")
    elif swift.exists() and platform.system() != "Darwin":
        print("aviso: o recorte por Vision é só do macOS; use as alternativas em código "
              "(--poli no grifado.py, ou recorte em outro programa e salve PNG com alfa)")

    amb = {"node": node, "python": str(py) if py else None,
           "ffmpeg": programa("ffmpeg"), "ffprobe": programa("ffprobe"),
           "sistema": platform.system()}
    (dest / "tools" / "ambiente.json").write_text(
        json.dumps(amb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(f"\nPYTHON={py}\nNODE={node}")
    print(f'pronto: python3 "{dest / "tools" / "render.py"}" exemplo --preview=12')
    return 0


if __name__ == "__main__":
    sys.exit(main())
