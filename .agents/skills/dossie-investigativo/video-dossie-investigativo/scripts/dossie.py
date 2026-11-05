#!/usr/bin/env python3
"""Ferramentas do estilo "dossiê investigativo".

uso (da raiz do projeto, com o venv):
  audio/.venv/bin/python tools/dossie.py xerox <foto> <saida.png> [--largura 520] [--proporcao 3x4] [--foco .5,.42]
        [--modo xerox|meiotom|limiar] [--contraste 1.7] [--gama 1.0] [--grao .26] [--toner .22] [--borrao .8]
        [--riscos 3] [--reticula 5] [--seed 1]
      → transforma a foto do usuário em fotocópia P&B de alto contraste, já no tamanho de uso (DS.foto({src:…})).
        modo xerox  = grão + toner empelotado + riscos verticais (o padrão do estilo)
        modo meiotom = retícula de pontos a 45° (jornal)
        modo limiar = preto e branco puros (cópia da cópia)
  audio/.venv/bin/python tools/dossie.py folha <video.mp4> <saida.jpg> [--n 9] [--largura 360] [--refs a.jpg b.jpg …]
      → folha de contato do vídeo; com --refs, as referências vão numa fileira embaixo para comparar a pegada.

Use só foto fornecida pelo usuário ou de domínio público/licença livre (com crédito no rodapé do vídeo).
"""
import argparse, io, json, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter, ImageOps

def recorta(im, prop, foco):
    if prop == 'livre': return im
    a, b = (float(v) for v in prop.lower().split('x')); alvo = a / b; w, h = im.size; fx, fy = foco
    if w / h > alvo: nw, nh = int(round(h * alvo)), h
    else: nw, nh = w, int(round(w / alvo))
    x0 = int(min(max(fx * w - nw / 2, 0), w - nw)); y0 = int(min(max(fy * h - nh / 2, 0), h - nh))
    return im.crop((x0, y0, x0 + nw, y0 + nh))

def xerox(a):
    im = ImageOps.exif_transpose(Image.open(a.entrada)).convert('RGB')
    im = recorta(im, a.proporcao, tuple(float(v) for v in a.foco.split(',')))
    w = a.largura; h = int(round(im.height * w / im.width)); im = im.resize((w, h), Image.LANCZOS)
    g = ImageOps.autocontrast(im.convert('L'), cutoff=1)
    if a.borrao > 0: g = g.filter(ImageFilter.GaussianBlur(a.borrao * w / 520))
    v = np.asarray(g, np.float32) / 255; rng = np.random.default_rng(a.seed)
    v = np.clip(v, 0, 1) ** a.gama; v = (v - .5) * a.contraste + .5
    yy, xx = np.mgrid[0:h, 0:w]
    v *= 1 + .07 * np.sin(yy / h * 9 + a.seed) * np.sin(yy / h * 23 + 1.3)              # bandas suaves de scanner
    if a.modo == 'meiotom':
        s = np.pi / a.reticula; ra, rb = (xx + yy) * s * .7071, (xx - yy) * s * .7071
        v = np.where(v + np.cos(ra) * np.cos(rb) * .32 > .5, .93, .07) + rng.normal(0, a.grao * .25, v.shape)
    elif a.modo == 'limiar':
        v = np.where(v > .5 + rng.normal(0, .09, v.shape), .95, .05)
    else:
        duro = np.where(v > .5 + (rng.random(v.shape) - .5) * .3, .96, .04)               # toner empelotado
        v = v * (1 - a.toner) + duro * a.toner + (rng.random(v.shape) + rng.random(v.shape) - 1) * a.grao
    for _ in range(a.riscos):                                                             # riscos verticais do cilindro
        x0 = int(rng.integers(0, w)); v[:, x0:x0 + int(rng.integers(1, 3))] += .1 + rng.random() * .2
    out = Image.fromarray((14 + np.clip(v, 0, 1) * 222).astype(np.uint8), 'L')
    out.save(a.saida); print(f'{a.saida}: {w}×{h} ({a.modo}). Na página: DS.foto(pai, {{src: "img/…", w: {w}, h: {h}}}); ajuste a tarja com F.olhos({{y: …, h: …}}).')

def quadro(v, t, w):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', v, '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(raw)).convert('RGB')

def folha(a):
    d = float(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', a.video], capture_output=True, text=True, check=True).stdout)['format']['duration'])
    qs = [quadro(a.video, d * (i + .5) / a.n, a.largura) for i in range(a.n)]; cols = min(a.n, 5); lin = -(-a.n // cols); p = 6
    w, h = qs[0].size; refs = [Image.open(r).convert('RGB') for r in (a.refs or [])]; rh = h if refs else 0
    refs = [r.resize((max(1, int(r.width * rh / r.height)), rh), Image.LANCZOS) for r in refs]
    W = max(cols * (w + p) + p, sum(r.width + p for r in refs) + p); H = lin * (h + p) + p + (rh + p if refs else 0)
    out = Image.new('RGB', (W, H), (70, 70, 70))
    for i, q in enumerate(qs): out.paste(q, (p + (i % cols) * (w + p), p + (i // cols) * (h + p)))
    x = p
    for r in refs: out.paste(r, (x, lin * (h + p) + p)); x += r.width + p
    out.save(a.saida, quality=88); print(f'{a.saida}: {a.n} quadros de {d:.1f} s' + (f' + {len(refs)} referências' if refs else ''))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sp = ap.add_subparsers(dest='cmd', required=True)
    x = sp.add_parser('xerox'); x.add_argument('entrada'); x.add_argument('saida'); x.add_argument('--largura', type=int, default=520); x.add_argument('--proporcao', default='3x4')
    x.add_argument('--foco', default='.5,.42'); x.add_argument('--modo', choices=['xerox', 'meiotom', 'limiar'], default='xerox'); x.add_argument('--contraste', type=float, default=1.7)
    x.add_argument('--gama', type=float, default=1.0); x.add_argument('--grao', type=float, default=.26); x.add_argument('--toner', type=float, default=.22); x.add_argument('--borrao', type=float, default=.8)
    x.add_argument('--riscos', type=int, default=3); x.add_argument('--reticula', type=float, default=5); x.add_argument('--seed', type=int, default=1); x.set_defaults(fn=xerox)
    f = sp.add_parser('folha'); f.add_argument('video'); f.add_argument('saida'); f.add_argument('--n', type=int, default=9); f.add_argument('--largura', type=int, default=360); f.add_argument('--refs', nargs='*'); f.set_defaults(fn=folha)
    a = ap.parse_args(); a.fn(a)
