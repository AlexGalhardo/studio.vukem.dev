#!/usr/bin/env python3
"""Recorta o objeto principal de uma foto e entrega um PNG com alfa, já cortado na caixa do objeto,
com a borda do alfa endurecida para o contorno de adesivo (.stk) não fazer halo.

Dois modos, e o padrão escolhe sozinho:
  vision  o recorte do macOS (tools/cutout, compilado pelo projeto.py). Melhor resultado; só no Mac.
  fundo   derruba o fundo pela cor das bordas (Pillow + numpy). Roda em qualquer sistema e serve
          quando a foto tem fundo liso e contrastado — que é o tipo de foto que este estilo pede.

uso (da raiz do projeto):
  <PYTHON> tools/recortar.py img/bicho.jpg img/bicho_cut.png [--max 1400] [--pad 10]
  <PYTHON> tools/recortar.py img/foto.jpg img/foto_cut.png --caixa 0.1,0.2,0.8,0.95
      --caixa x0,y0,x1,y1 (frações 0–1) recorta a foto ANTES do recorte — útil quando há dois objetos
      e você só quer um, ou quando o objeto é pequeno no quadro.
  <PYTHON> tools/recortar.py img/foto.jpg img/foto_cut.png --modo fundo --tolerancia 38
"""
import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

AQUI = Path(__file__).resolve().parent


def por_vision(entrada, binario):
    """Máscara do Vision (macOS). Devolve a imagem RGBA ou None quando não dá para usar."""
    if platform.system() != "Darwin" or not Path(binario).exists():
        return None
    saida = Path(tempfile.mkdtemp()) / "mask.png"
    r = subprocess.run([str(binario), str(entrada), str(saida)], capture_output=True, text=True, encoding="utf-8")
    if r.stdout:
        print(r.stdout.strip())
    if r.returncode or not saida.exists():
        return None
    return Image.open(saida).convert("RGBA")


def por_fundo(entrada, tolerancia):
    """Derruba o fundo pela cor das bordas: pega as quatro faixas da borda como amostra do fundo,
    marca como transparente todo pixel perto dessa cor e mantém só a mancha central ligada."""
    im = Image.open(entrada).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    h, w, _ = a.shape
    faixa = max(2, min(h, w) // 40)
    borda = np.concatenate([a[:faixa].reshape(-1, 3), a[-faixa:].reshape(-1, 3),
                            a[:, :faixa].reshape(-1, 3), a[:, -faixa:].reshape(-1, 3)])
    fundo = np.median(borda, axis=0)
    dist = np.sqrt(((a - fundo) ** 2).sum(axis=2))
    objeto = dist > tolerancia

    # só o que encosta na borda é fundo de verdade: espalha a marca a partir das bordas (inundação por dilatação)
    fora = ~objeto
    marca = np.zeros_like(fora)
    marca[0], marca[-1], marca[:, 0], marca[:, -1] = fora[0], fora[-1], fora[:, 0], fora[:, -1]
    for _ in range(max(h, w)):
        novo = marca.copy()
        novo[1:] |= marca[:-1]
        novo[:-1] |= marca[1:]
        novo[:, 1:] |= marca[:, :-1]
        novo[:, :-1] |= marca[:, 1:]
        novo &= fora
        if novo.sum() == marca.sum():
            break
        marca = novo

    alfa = Image.fromarray(np.where(marca, 0, 255).astype(np.uint8), "L")
    alfa = alfa.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA")
    rgba.putalpha(alfa)
    return rgba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--max", type=int, default=1400, help="largura máxima do PNG final (px)")
    ap.add_argument("--pad", type=int, default=10, help="margem transparente em volta do objeto (px)")
    ap.add_argument("--caixa", help="x0,y0,x1,y1 em frações: recorta a foto antes de separar o objeto")
    ap.add_argument("--modo", choices=("auto", "vision", "fundo"), default="auto")
    ap.add_argument("--tolerancia", type=float, default=42, help="modo fundo: distância de cor que ainda é fundo")
    ap.add_argument("--bin", default=str(AQUI / "cutout"), help="binário compilado de cutout.swift (macOS)")
    a = ap.parse_args()

    src = Path(a.entrada)
    if not src.exists():
        sys.exit(f"não achei {src}")
    if a.caixa:
        x0, y0, x1, y1 = (float(v) for v in a.caixa.split(","))
        im = Image.open(src).convert("RGB")
        W, H = im.size
        src = Path(tempfile.mkdtemp()) / "caixa.png"
        im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))).save(src)

    im = None
    if a.modo in ("auto", "vision"):
        im = por_vision(src, a.bin)
        if im is None and a.modo == "vision":
            sys.exit("o recorte do Vision não rodou (precisa de macOS e de tools/cutout) — use --modo fundo")
    if im is None:
        if a.modo == "auto":
            print("recorte pela cor do fundo (o Vision não está disponível aqui) — confira a prova com atenção")
        im = por_fundo(src, a.tolerancia)

    al = im.getchannel("A")
    # endurece a borda: some com o véu semitransparente que vira halo sob drop-shadow
    al = al.point(lambda v: 0 if v < 24 else min(255, int((v - 24) * 255 / 200)))
    im.putalpha(al)
    box = al.point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        sys.exit("máscara vazia — tente outra foto (objeto inteiro, fundo simples) ou --caixa")
    W, H = im.size
    frac = (box[2] - box[0]) * (box[3] - box[1]) / (W * H)
    p = a.pad
    im = im.crop((max(0, box[0] - p), max(0, box[1] - p), min(W, box[2] + p), min(H, box[3] + p)))
    if im.width > a.max:
        im = im.resize((a.max, round(im.height * a.max / im.width)), Image.LANCZOS)
    destino = Path(a.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, optimize=True)

    cob = sum(im.getchannel("A").histogram()[129:]) / (im.width * im.height)
    print(f"{destino}: {im.width}×{im.height}  (objeto ocupava {frac:.0%} da foto; preenche {cob:.0%} do recorte)")
    if frac < .04:
        print("  aviso: objeto pequeno na foto — o recorte vai ficar com pouca resolução; prefira outra foto ou --caixa")
    if cob < .25:
        print("  aviso: recorte muito vazado — confira se não pegou só um pedaço (abra o PNG e olhe)")
    # prova sobre fundo verde: abra esta imagem pra conferir o contorno
    provas = Path("previews")
    provas.mkdir(parents=True, exist_ok=True)
    prova = provas / ("recorte-" + destino.stem + ".jpg")
    bg = Image.new("RGBA", im.size, (40, 160, 90, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(prova, quality=85)
    print(f"  prova: {prova} — confira; o recorte costuma perder partes finas (rabo, antena, bigode, pernas finas).")


if __name__ == "__main__":
    main()
