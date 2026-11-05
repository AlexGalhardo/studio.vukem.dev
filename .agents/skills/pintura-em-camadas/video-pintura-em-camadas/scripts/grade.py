#!/usr/bin/env python3
"""Grade de coordenadas sobre uma imagem (para desenhar polígonos de máscara à mão).
uso: audio/.venv/bin/python tools/grade.py img/pintura.jpg previews/grade.jpg [--largura 1600] [--caixa x0,y0,x1,y1] [--passo 50]
     --caixa em coordenadas da escala --largura; a saída mostra só a caixa, ampliada para ~1600 px."""
import argparse
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser(); ap.add_argument('img'); ap.add_argument('saida'); ap.add_argument('--largura', type=int, default=1600)
ap.add_argument('--caixa'); ap.add_argument('--passo', type=int, default=50); a = ap.parse_args()
im = Image.open(a.img).convert('RGB'); e = a.largura / im.width
x0, y0, x1, y1 = (0, 0, a.largura, round(im.height * e)) if not a.caixa else map(int, a.caixa.split(','))
z = 1600 / (x1 - x0)
c = im.crop((round(x0 / e), round(y0 / e), round(x1 / e), round(y1 / e))).resize((1600, round((y1 - y0) * z)), Image.LANCZOS)
d = ImageDraw.Draw(c, 'RGBA'); f = ImageFont.load_default(size=13)
for gx in range((x0 // a.passo) * a.passo, x1 + 1, a.passo):
    X = (gx - x0) * z; forte = gx % (a.passo * 2) == 0
    d.line([(X, 0), (X, c.height)], fill=(255, 255, 255, 110 if forte else 50), width=1)
    if forte: d.text((X + 2, 2), str(gx), fill=(255, 255, 0, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
for gy in range((y0 // a.passo) * a.passo, y1 + 1, a.passo):
    Y = (gy - y0) * z; forte = gy % (a.passo * 2) == 0
    d.line([(0, Y), (c.width, Y)], fill=(255, 255, 255, 110 if forte else 50), width=1)
    if forte: d.text((2, Y + 2), str(gy), fill=(0, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
c.save(a.saida, quality=88); print(a.saida, c.size)
