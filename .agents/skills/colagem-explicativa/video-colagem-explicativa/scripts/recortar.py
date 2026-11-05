#!/usr/bin/env python3
"""Recorta o objeto principal de uma foto e entrega um PNG com alfa, já cortado na caixa do objeto,
com a borda do alfa endurecida para o contorno de adesivo não fazer halo.

O recorte automático usa o Vision da Apple (binário `cutout`, compilado pelo projeto.py no macOS).
FORA DO macOS não há recorte automático: o script sai com código 2 e explica o que entregar no lugar.

uso (da pasta do projeto):
  <PYTHON> tools/recortar.py img/predio.jpg img/predio_cut.png [--max 1400] [--pad 10]
  <PYTHON> tools/recortar.py img/foto.jpg img/foto_cut.png --caixa 0.1,0.2,0.8,0.95
      --caixa x0,y0,x1,y1 (frações 0–1) recorta a foto ANTES do Vision — útil quando há dois objetos
      e você só quer um, ou quando o objeto é pequeno no quadro.
"""
import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent

SEM_VISION = """O recorte automático não está disponível neste sistema ({sistema}).

Ele usa o framework Vision da Apple (macOS 14+), que não tem equivalente no Windows nem no Linux, e esta
skill não baixa modelo de recorte nenhum. O resto da skill funciona normalmente.

Faça o recorte à mão (uma vez por foto) em qualquer editor — Paint.NET, GIMP, Photopea, Photoshop,
Pixelmator, "Remover fundo" do Paint do Windows 11 ou do PowerPoint — e salve assim:

  - PNG com canal alfa (transparência de verdade, não fundo branco);
  - só o objeto, fundo 100% transparente, borda limpa (sem véu cinza em volta);
  - no máximo ~1400 px de largura, com uma margem transparente de uns 10 px em volta;
  - grave em img/<nome>_cut.png, que é o arquivo que os outros passos desta skill esperam.

Depois siga o fluxo do SKILL.md a partir do passo seguinte, usando esse _cut.png como entrada."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--max", type=int, default=1400, help="largura máxima do PNG final (px)")
    ap.add_argument("--pad", type=int, default=10, help="margem transparente em volta do objeto (px)")
    ap.add_argument("--caixa", help="x0,y0,x1,y1 em frações: recorta a foto antes de mandar pro Vision")
    ap.add_argument("--bin", help="binário compilado de cutout.swift (padrão: ao lado deste script)")
    a = ap.parse_args()

    binario = Path(a.bin) if a.bin else AQUI / ("cutout.exe" if platform.system() == "Windows" else "cutout")
    if platform.system() != "Darwin":
        print(SEM_VISION.format(sistema=platform.system() or "desconhecido"))
        sys.exit(2)
    if not binario.exists():
        print(f"não achei {binario} — rode o projeto.py da skill (ele compila o cutout.swift; "
              "precisa de macOS 14+ e do swiftc das Xcode Command Line Tools).")
        sys.exit(2)

    src = Path(a.entrada)
    tmpdir = Path(tempfile.mkdtemp(prefix="recorte-"))
    if a.caixa:
        x0, y0, x1, y1 = map(float, a.caixa.split(","))
        im = Image.open(src).convert("RGB")
        W, H = im.size
        src = tmpdir / "caixa.png"
        im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))).save(src)

    mask_png = tmpdir / "mask.png"
    r = subprocess.run([str(binario), str(src), str(mask_png)],
                       capture_output=True, text=True, encoding="utf-8")
    print((r.stdout or "").strip())
    if r.returncode or not mask_png.exists():
        sys.exit("o Vision não achou objeto em primeiro plano — tente outra foto "
                 "(objeto inteiro, fundo simples) ou use --caixa")

    im = Image.open(mask_png).convert("RGBA")
    al = im.getchannel("A")
    # endurece a borda: some com o véu semitransparente que vira halo sob drop-shadow
    al = al.point(lambda v: 0 if v < 24 else min(255, int((v - 24) * 255 / 200)))
    im.putalpha(al)
    box = al.point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        sys.exit("máscara vazia")
    W, H = im.size
    frac = (box[2] - box[0]) * (box[3] - box[1]) / (W * H)
    p = a.pad
    box = (max(0, box[0] - p), max(0, box[1] - p), min(W, box[2] + p), min(H, box[3] + p))
    im = im.crop(box)
    if im.width > a.max:
        im = im.resize((a.max, round(im.height * a.max / im.width)), Image.LANCZOS)
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    im.save(saida, optimize=True)
    cob = sum(im.getchannel("A").histogram()[129:]) / (im.width * im.height)
    print(f"{saida}: {im.width}×{im.height}  (objeto ocupava {frac:.0%} da foto; preenche {cob:.0%} do recorte)")
    if frac < .04:
        print("  aviso: objeto pequeno na foto — o recorte vai ficar com pouca resolução; "
              "prefira outra foto ou --caixa")
    if cob < .25:
        print("  aviso: recorte muito vazado — confira se não pegou só um pedaço (abra o PNG e olhe)")
    # prova sobre fundo verde: abra esta imagem pra conferir o contorno
    prova_dir = Path("previews")
    prova_dir.mkdir(parents=True, exist_ok=True)
    prova = prova_dir / ("recorte-" + saida.stem + ".jpg")
    bg = Image.new("RGBA", im.size, (40, 160, 90, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(prova, quality=85)
    print(f"  prova: {prova} — confira; o Vision costuma perder partes finas (rabo, antena, pernas finas).")


if __name__ == "__main__":
    main()
