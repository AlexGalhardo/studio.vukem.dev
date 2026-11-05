#!/usr/bin/env python3
"""Coleção de espécimes do Wikimedia Commons (fotos de museu em fundo claro).

uso (da raiz do projeto):
  $P -I tools/colecao.py buscar "termo 1" "termo 2" … [--n 30] [--folha previews/busca/x.jpg]
      → lista numerada (só CC0, PD, CC BY, CC BY-SA) + folha de contato; guarda em previews/colecao-ultima.json
  $P -I tools/colecao.py titulos lista.txt [--folha …]
      → mesma folha a partir de títulos "File:…" (um por linha)
"""
import argparse, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, html
API = 'https://commons.wikimedia.org/w/api.php'
UA = 'video-laminas-de-especimes/1.0 (skill de video; https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)'
CACHE = os.path.join('previews', 'colecao-ultima.json')

def get(url, tent=6):
    import time
    for i in range(tent):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=90) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tent - 1: raise
            time.sleep(3 * (i + 1))

def api(**p):
    p.update(action='query', format='json', formatversion=2)
    return json.loads(get(API + '?' + urllib.parse.urlencode(p)))

def limpa(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()

def licenca(meta):
    nome = limpa(meta.get('LicenseShortName', {}).get('value', '')); n = nome.lower()
    if re.search(r'\b(nc|nd)\b', n): return nome, None
    if n.startswith('cc0') or 'public domain' in n or n.startswith('pd') or 'no restrictions' in n: return nome, 'livre'
    if re.match(r'cc[ -]by(-sa)?\b', n): return nome, 'atribuir'
    return nome, None

def info(page):
    ii = (page.get('imageinfo') or [{}])[0]; meta = ii.get('extmetadata', {})
    nome, tipo = licenca(meta)
    desc = limpa(meta.get('ImageDescription', {}).get('value', ''))
    cats = limpa(meta.get('Categories', {}).get('value', ''))
    return {'title': page['title'], 'license': nome, 'tipo': tipo, 'desc': desc[:400], 'cats': cats[:400],
            'brasil': bool(re.search(r'bra[sz]il|brésil|brasilien', (page['title'] + desc + cats).lower())),
            'artist': limpa(meta.get('Artist', {}).get('value', ''))[:120] or 'desconhecido',
            'w': ii.get('width'), 'h': ii.get('height'), 'mime': ii.get('mime'),
            'thumb': ii.get('thumburl') or ii.get('url'), 'page': ii.get('descriptionurl')}

def por_titulos(titulos):
    out = []
    for i in range(0, len(titulos), 40):
        d = api(titles='|'.join(titulos[i:i+40]), prop='imageinfo', iiprop='url|extmetadata|size|mime', iiurlwidth=330)
        pg = {p['title']: p for p in d['query']['pages']}
        for t in titulos[i:i+40]:
            t2 = t.replace('_', ' ')
            for k, p in pg.items():
                if k == t2 and 'imageinfo' in p: out.append(info(p))
    return out

def busca(termo, n):
    out, off = [], 0
    while len(out) < n:
        d = api(generator='search', gsrsearch=termo, gsrnamespace=6, gsrlimit=min(50, n - len(out)), gsroffset=off,
                prop='imageinfo', iiprop='url|extmetadata|size|mime', iiurlwidth=330)
        pages = sorted(d.get('query', {}).get('pages', []), key=lambda p: p.get('index', 0))
        out += [info(p) for p in pages]
        off = d.get('continue', {}).get('gsroffset')
        if off is None or not pages: break
    return out

def folha(res, out):
    from PIL import Image, ImageDraw, ImageFont
    cols, cw, ch = 6, 300, 250; rows = -(-len(res) // cols)
    sheet = Image.new('RGB', (cols * cw, rows * (ch + 30)), '#222'); dr = ImageDraw.Draw(sheet)
    try: fnt = ImageFont.load_default(size=17)
    except TypeError: fnt = ImageFont.load_default()
    for i, r in enumerate(res):
        x, y = (i % cols) * cw, (i // cols) * (ch + 30)
        try:
            time.sleep(.1); im = Image.open(io.BytesIO(get(r['thumb']))).convert('RGB'); im.thumbnail((cw - 6, ch - 6))
            sheet.paste(im, (x + (cw - im.width) // 2, y + (ch - im.height) // 2))
        except Exception as e: dr.text((x + 10, y + 10), f'erro: {e}'[:40], fill='#f66', font=fnt)
        dr.text((x + 6, y + ch + 4), f"{i + 1}.{'BR' if r['brasil'] else ''} {r['title'][5:26]}", fill='#fff', font=fnt)
    os.makedirs(os.path.dirname(out), exist_ok=True); sheet.save(out, quality=86); print('folha:', out)

def fundo(r):
    """Brilho e uniformidade da borda da miniatura: fundo de estúdio claro → (alto, baixo)."""
    from PIL import Image
    import numpy as np
    try:
        im = np.asarray(Image.open(io.BytesIO(get(r['thumb']))).convert('RGB')).astype(float)
    except Exception: return 0, 99
    b = np.concatenate([im[:6].reshape(-1, 3), im[-6:].reshape(-1, 3), im[:, :6].reshape(-1, 3), im[:, -6:].reshape(-1, 3)])
    return float(b.mean()), float(b.std())

def mostrar(res, a):
    res = [r for r in res if r['tipo'] and (r['mime'] or '').startswith('image/')]
    if getattr(a, 'claro', False):
        ok = []
        for r in res:
            m, sd = fundo(r); r['fundo'] = [round(m), round(sd)]
            if m > a.min_brilho and sd < 22: ok.append(r)
            time.sleep(.15)
        res = ok
    vistos, uniq = set(), []
    for r in res:
        if r['title'] not in vistos: vistos.add(r['title']); uniq.append(r)
    res = uniq
    json.dump(res, open(a.json or CACHE, 'w', encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    for i, r in enumerate(res, 1):
        print(f"{i:3d}. {'BR ' if r['brasil'] else '   '}{r['title'][5:][:78]:78s} {r['w']}×{r['h']} {r['license']} · {r['artist'][:24]}")
    if a.folha: folha(res, a.folha)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('buscar'); b.add_argument('termos', nargs='+'); b.add_argument('--n', type=int, default=30); b.add_argument('--folha'); b.add_argument('--json'); b.add_argument('--claro', action='store_true', help='só fundo de estúdio claro'); b.add_argument('--min-brilho', type=float, default=200)
    t = sp.add_parser('titulos'); t.add_argument('lista'); t.add_argument('--folha'); t.add_argument('--json'); t.add_argument('--claro', action='store_true'); t.add_argument('--min-brilho', type=float, default=200)
    a = ap.parse_args()
    if a.cmd == 'buscar':
        res = []
        for termo in a.termos: res += busca(termo, a.n)
        mostrar(res, a)
    else:
        tit = [l.strip() for l in open(a.lista, encoding="utf-8") if l.strip()]
        mostrar(por_titulos(tit), a)
