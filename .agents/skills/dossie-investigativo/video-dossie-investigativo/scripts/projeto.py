#!/usr/bin/env python3
"""projeto.py — cria (ou completa) uma pasta de projeto no estilo «dossiê investigativo».

    python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>

Copia o projeto-modelo de assets/projeto, cria tools/, previews/, out/ e audio/, leva dossie.py e
analisar.py para tools/ e imprime NODE= e PYTHON= — os dois executáveis que os comandos do SKILL.md usam.
Substitui os antigos setup.sh e node.sh: roda igual no macOS, no Linux e no Windows, só com a biblioteca
padrão. Quem instala programa e biblioteca é o scripts/preparar.py.

Códigos de saída: 0 pronto · 1 erro · 3 falta alguma coisa (a lista diz o quê).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
MODELO = SKILL / "assets" / "projeto"
NODE_MINIMO = 20
PASTAS = ("tools", "previews", "out", "audio", "videos", "img")


def casa() -> Path:
    return Path(os.environ.get("CRIABR_CASA") or (Path.home() / ".criabr"))


def ambiente() -> dict:
    arq = casa() / "ambiente.json"
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def _executavel(caminho) -> str | None:
    p = Path(caminho) if caminho else None
    return str(p) if p and p.is_file() else None


def achar_node(amb: dict) -> tuple[str | None, int]:
    """(caminho do node, versão maior). Procura: VIDEO_OPS_NODE → ambiente.json → PATH → nvm → /usr/local/bin."""
    candidatos = [os.environ.get("VIDEO_OPS_NODE"), amb.get("node"), shutil.which("node")]
    candidatos += sorted((str(p) for p in Path.home().glob(".nvm/versions/node/*/bin/node")), reverse=True)
    candidatos.append(str(Path(os.sep, "usr", "local", "bin", "node")))
    melhor, maior = None, 0
    for c in candidatos:
        c = _executavel(c)
        if not c:
            continue
        try:
            r = subprocess.run([c, "-v"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        try:
            v = int(r.stdout.strip().lstrip("v").split(".")[0])
        except (ValueError, IndexError):
            continue
        if v > maior:
            melhor, maior = c, v
        if maior >= NODE_MINIMO:
            break
    return melhor, maior


def achar_python(amb: dict) -> str:
    """Python com numpy, scipy e Pillow (o que o preparar.py gravou; senão, o que está rodando)."""
    venv = casa() / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    for c in (os.environ.get("VIDEO_OPS_PYTHON"), amb.get("python"), str(venv), sys.executable):
        c = _executavel(c)
        if not c:
            continue
        teste = "import numpy, scipy, PIL"
        if subprocess.run([c, "-c", teste], capture_output=True).returncode == 0:
            return c
    return sys.executable


def copiar(destino: Path) -> list[str]:
    """Copia o modelo para `destino` sem apagar nada do que já existe lá. Devolve o que foi criado."""
    novos = []
    for origem in sorted(MODELO.rglob("*")):
        rel = origem.relative_to(MODELO)
        if "node_modules" in rel.parts or rel.name in (".DS_Store", "__pycache__"):
            continue
        alvo = destino / rel
        if origem.is_dir():
            alvo.mkdir(parents=True, exist_ok=True)
        elif not alvo.exists():
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, alvo)
            novos.append(str(rel))
    for p in PASTAS:
        (destino / p).mkdir(parents=True, exist_ok=True)
    for f in ("dossie.py", "analisar.py"):
        origem = SKILL / "scripts" / f
        if origem.is_file():
            shutil.copy2(origem, destino / "tools" / f)
    return novos


def dependencias_node(destino: Path, node: str | None) -> str | None:
    """node_modules na pasta do projeto: copia o da skill (já instalado) ou roda npm install. Devolve o que falta."""
    if (destino / "node_modules").is_dir():
        return None
    pronto = MODELO / "node_modules"
    if pronto.is_dir():
        shutil.copytree(pronto, destino / "node_modules", symlinks=True, dirs_exist_ok=True)
        return None
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if node and npm:
        print(f"  $ {npm} install --omit=dev   (em {destino})", flush=True)
        if subprocess.run([npm, "install", "--omit=dev"], cwd=str(destino)).returncode == 0:
            return None
    return ("instalar as dependências Node do projeto (gsap e playwright): rode o scripts/preparar.py desta "
            "skill com --instalar, ou `npm install` dentro da pasta do projeto")


def main() -> int:
    ap = argparse.ArgumentParser(description="Cria ou completa um projeto no estilo dossiê investigativo.")
    ap.add_argument("pasta", help="pasta do projeto (criada se não existir)")
    a = ap.parse_args()
    destino = Path(a.pasta).expanduser().resolve()
    if not MODELO.is_dir():
        print(f"projeto.py: não achei o modelo em {MODELO} (a skill veio pela metade?)", file=sys.stderr)
        return 1
    destino.mkdir(parents=True, exist_ok=True)
    novos = copiar(destino)
    print(f"projeto em {destino}" + (f" ({len(novos)} arquivo(s) copiado(s))" if novos else " (já existia; nada sobrescrito)"))

    amb = ambiente()
    faltas = []
    node, versao = achar_node(amb)
    if not node:
        faltas.append("instalar o Node 20 ou mais novo (o render usa Playwright)")
    elif versao < NODE_MINIMO:
        faltas.append(f"o Node encontrado é a versão {versao}; o render precisa da {NODE_MINIMO} ou mais nova")
    for prog in ("ffmpeg", "ffprobe"):
        if not shutil.which(prog) and not os.environ.get("VIDEO_OPS_" + prog.upper()):
            faltas.append(f"instalar o {prog}")
    python = achar_python(amb)
    if subprocess.run([python, "-c", "import numpy, scipy, PIL"], capture_output=True).returncode != 0:
        faltas.append("um Python 3.10+ com numpy, scipy e Pillow (o preparar.py monta um em ~/.criabr/venv)")
    falta_node = dependencias_node(destino, node) if node else None
    if falta_node:
        faltas.append(falta_node)

    print(f"NODE={node or ''}")
    print(f"PYTHON={python}")
    if faltas:
        print("\nFalta:")
        for f in faltas:
            print(f"  - {f}")
        print("\nRode `python3 <pasta desta skill>/scripts/preparar.py` (e, com o ok do usuário, com --instalar).")
        return 3
    print(f'\nPronto. Prévia: "{node}" render.mjs exemplo --preview=12   (de dentro de {destino})')
    return 0


if __name__ == "__main__":
    sys.exit(main())
