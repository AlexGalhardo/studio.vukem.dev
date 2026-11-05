#!/usr/bin/env python3
"""Ferramentas do estilo "ilustração explicativa".

uso (da raiz do projeto):
  <PYTHON> -I tools/ilustra.py foto img/x.jpg img/x_pb.jpg [--largura 900] [--prop 1.5] [--foco .5,.5]
      → foto P&B levemente sépia e de contraste baixo (como as fotos de arquivo das cantoneiras),
        cortada na proporção pedida (largura/altura) em volta do ponto de foco (0–1, 0–1).
  <PYTHON> -I tools/ilustra.py terra land.geojson lib/terra.js [--paises countries.geojson --destaque BRA]
      → contornos de continentes (Natural Earth, domínio público) em graus com 1 casa decimal, para
        o globo projetado em JS (IL.globo). Com --paises, inclui o contorno do país destacado.
        Baixe: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

def foto(a):
    im = ImageOps.exif_transpose(Image.open(a.entrada)).convert('RGB')
    W, H = im.size; fx, fy = (float(v) for v in a.foco.split(','))
    if W / H > a.prop: cw, ch = int(H * a.prop), H
    else: cw, ch = W, int(W / a.prop)
    x0 = min(max(0, int(fx * W - cw / 2)), W - cw); y0 = min(max(0, int(fy * H - ch / 2)), H - ch)
    im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((a.largura, round(a.largura / a.prop)), Image.LANCZOS)
    g = ImageOps.autocontrast(im.convert('L'), cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(a.contraste)
    # duotone quente: sombra marrom-quase-preta → luz creme acinzentada (as fotos da referência)
    out = ImageOps.colorize(g, black=(34, 30, 26), white=(236, 230, 218), mid=(140, 134, 124))
    out.save(a.saida, quality=88)
    print(f'{a.saida} {out.size[0]}×{out.size[1]}')

def anel(c):
    pts, last = [], None
    for lon, lat in c:
        p = [round(lon, 1), round(lat, 1)]
        if p != last: pts.append(p); last = p
    return pts if len(pts) >= 4 else None

def poligonos(geom):
    if geom['type'] == 'Polygon': return [geom['coordinates'][0]]
    if geom['type'] == 'MultiPolygon': return [p[0] for p in geom['coordinates']]
    return []

def terra(a):
    land = json.loads(Path(a.land).read_text(encoding='utf-8'))
    out = {'land': [r for f in land['features'] for c in poligonos(f['geometry']) if (r := anel(c))]}
    if a.paises:
        for f in json.loads(Path(a.paises).read_text(encoding='utf-8'))['features']:
            if f['properties'].get('ADM0_A3') == a.destaque or f['properties'].get('ISO_A3') == a.destaque:
                out['pais'] = [r for c in poligonos(f['geometry']) if (r := anel(c))]
    js = '// contornos Natural Earth 110m (domínio público) — gerado por tools/ilustra.py terra\nwindow.TERRA=' + json.dumps(out, separators=(',', ':')) + ';\n'
    Path(a.saida).write_text(js, encoding='utf-8', newline='\n')
    print(f'{a.saida}: {len(out["land"])} polígonos, {sum(len(r) for r in out["land"])} pontos, {len(js) // 1024} KB')

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
p = sp.add_parser('foto'); p.add_argument('entrada'); p.add_argument('saida'); p.add_argument('--largura', type=int, default=900)
p.add_argument('--prop', type=float, default=1.5); p.add_argument('--foco', default='.5,.5'); p.add_argument('--contraste', type=float, default=.92)
p = sp.add_parser('terra'); p.add_argument('land'); p.add_argument('saida'); p.add_argument('--paises'); p.add_argument('--destaque', default='BRA')
a = ap.parse_args(); {'foto': foto, 'terra': terra}[a.cmd](a)
