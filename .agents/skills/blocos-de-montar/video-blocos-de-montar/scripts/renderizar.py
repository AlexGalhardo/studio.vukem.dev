#!/usr/bin/env python3
"""Renderiza um vídeo do estilo peças de montar (chama o render.mjs do projeto pelo Node, com a trava).

uso:
  python3 <skill>/scripts/renderizar.py <pasta-do-projeto> [argumentos do render.mjs]

exemplos:
  ... <projeto> 01 --at=0.6,1.8,3.1,4.0     prévia: previews/<v>.jpg, quadros em previews/<v>/ e videos/<v>/cues.json
  ... <projeto> 01                            render completo → out/<v>.mp4
  ... <projeto> 01 --fmt=9x16                 só um formato

Códigos de saída: 0 ok · 2 falta insumo · o que o render.mjs devolver.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

USO = "uso: python3 <skill>/scripts/renderizar.py <pasta-do-projeto> [argumentos do render.mjs]"


def main():
    destino, resto = comum.projeto(sys.argv[1:], USO)
    node = comum.achar_node()
    if not node:
        print("falta Node >= %d — rode scripts/preparar.py --instalar" % comum.NODE_MINIMO)
        return 2
    if not comum.achar_ffmpeg():
        print("falta ffmpeg — rode scripts/preparar.py --instalar")
        return 2
    if not (destino / "node_modules" / "three").is_dir():
        print("faltam as bibliotecas Node no projeto — rode scripts/novo_projeto.py")
        return 2
    return comum.rodar([node, "render.mjs"] + resto, cwd=destino)


if __name__ == "__main__":
    sys.exit(main())
