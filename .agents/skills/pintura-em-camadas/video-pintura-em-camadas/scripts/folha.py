#!/usr/bin/env python3
"""Junta quadros de preview numa folha (lado a lado, com o instante escrito).
uso: audio/.venv/bin/python tools/folha.py previews/01-x previews/folha.jpg [--col 4] [--larg 360]"""
import argparse, glob, os
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument('pasta'); ap.add_argument('saida'); ap.add_argument('--col', type=int, default=4); ap.add_argument('--larg', type=int, default=360); ap.add_argument('--rotulos', default='')
a = ap.parse_args()
fs = sorted(glob.glob(os.path.join(a.pasta, '*.jpg'))); rot = a.rotulos.split(',') if a.rotulos else []
ims = [Image.open(f).convert('RGB') for f in fs]; w = a.larg; h = round(ims[0].height * w / ims[0].width)
rows = -(-len(ims) // a.col); s = Image.new('RGB', (w * a.col, h * rows), '#111'); d = ImageDraw.Draw(s); fn = ImageFont.load_default(size=18)
for i, im in enumerate(ims):
    x, y = (i % a.col) * w, (i // a.col) * h; s.paste(im.resize((w, h), Image.LANCZOS), (x, y))
    d.text((x + 8, y + 6), rot[i] if i < len(rot) else os.path.basename(fs[i]), fill='yellow', font=fn, stroke_width=2, stroke_fill='black')
s.save(a.saida, quality=88); print(a.saida, s.size)
