#!/usr/bin/env python3
"""Cria (ou completa) um projeto do estilo pelúcia pronto para renderizar.

uso:
  python3 <skill>/scripts/novo_projeto.py <pasta-do-projeto> [--node-modules <pasta>]

Copia assets/projeto para a pasta do usuário (sem node_modules), liga as bibliotecas Node
(symlink; cópia quando o sistema não deixa criar link) e confere ffmpeg, Node >= 20 e o
Python com numpy e scipy.
Códigos de saída: 0 pronto · 2 falta insumo (rode scripts/preparar.py --instalar) · 1 erro.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
MODELO = SKILL / "assets" / "projeto"
IGNORAR = shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc", ".DS_Store", "out", "previews")
USO = "uso: python3 <skill>/scripts/novo_projeto.py <pasta-do-projeto> [--node-modules <pasta>]"


def ligar_bibliotecas(destino, origem):
    """node_modules do projeto: link para o da skill (ou para o que o usuário apontou)."""
    alvo = destino / "node_modules"
    if alvo.exists():
        return "já estava lá"
    if not origem or not origem.is_dir():
        return None
    try:
        alvo.symlink_to(origem.resolve(), target_is_directory=True)
        return "ligado por symlink a %s" % origem
    except (OSError, NotImplementedError):
        shutil.copytree(origem, alvo, ignore=IGNORAR)
        return "copiado de %s" % origem


def main():
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        print(USO)
        return 1
    destino = Path(argv[0]).expanduser().resolve()
    origem = None
    if "--node-modules" in argv:
        origem = Path(argv[argv.index("--node-modules") + 1]).expanduser().resolve()
    elif (MODELO / "node_modules").is_dir():
        origem = MODELO / "node_modules"

    if not (destino / "render.mjs").exists():
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copytree(MODELO, destino, ignore=IGNORAR, dirs_exist_ok=True)
        print("projeto criado em %s" % destino)
    else:
        print("projeto já existe em %s (nada foi sobrescrito)" % destino)
    for p in ("out", "previews"):
        (destino / p).mkdir(exist_ok=True)

    print("node_modules: %s" % (ligar_bibliotecas(destino, origem) or "FALTA"))

    faltas = []
    if not comum.achar_ffmpeg():
        faltas.append("ffmpeg")
    node = comum.achar_node()
    if not node:
        faltas.append("Node >= %d" % comum.NODE_MINIMO)
    py = comum.achar_python()
    if not py:
        faltas.append("Python com numpy e scipy")
    if not (destino / "node_modules" / "three").is_dir():
        faltas.append("bibliotecas Node (three, gsap, playwright)")
    if faltas:
        print("\nFalta: %s" % ", ".join(faltas))
        print("Rode: python3 %s --instalar" % (SKILL / "scripts" / "preparar.py"))
        return 2

    print("\nPronto. Prévia:")
    print('  python3 "%s" "%s" 01 --at=0.3,1.6,3,4.2' % (SKILL / "scripts" / "renderizar.py", destino))
    print("Depois: som.py e renderizar.py sem --at para o mp4 final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
