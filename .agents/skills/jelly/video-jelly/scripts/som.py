#!/usr/bin/env python3
"""Sintetiza a trilha e os efeitos do vídeo a partir de videos/<nome>/cues.json → audio/<nome>.wav.

uso:
  python3 <skill>/scripts/som.py <pasta-do-projeto> [prefixos do vídeo]

Rode DEPOIS de uma prévia (é ela que grava o cues.json) e ANTES do render final, que junta o wav.
Precisa de um Python com numpy e scipy (o preparar.py cuida disso) e do ffmpeg (normalização).
Códigos de saída: 0 ok · 2 falta insumo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

USO = "uso: python3 <skill>/scripts/som.py <pasta-do-projeto> [prefixos do vídeo]"


def main():
    destino, resto = comum.projeto(sys.argv[1:], USO)
    py = comum.achar_python()
    if not py:
        print("falta um Python com numpy e scipy — rode scripts/preparar.py --instalar")
        return 2
    if not comum.achar_ffmpeg():
        print("falta ffmpeg — rode scripts/preparar.py --instalar")
        return 2
    return comum.rodar([py, str(Path("audio") / "synth.py")] + resto, cwd=destino)


if __name__ == "__main__":
    sys.exit(main())
