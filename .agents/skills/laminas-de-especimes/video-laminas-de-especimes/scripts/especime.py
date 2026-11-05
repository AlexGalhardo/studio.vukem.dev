#!/usr/bin/env python3
"""Lâminas de espécime: baixa fotos de museu (fundo liso) do Wikimedia Commons, tira o fundo
por distância de cor (mantém antenas e pernas finas, que o Vision perde), separa um exemplar
quando a foto tem dois (dorsal + ventral), gira com a cabeça para cima, tira o halo do fundo,
normaliza o tamanho pela área do corpo e grava WebP com alfa no tamanho final de tela.

uso (da raiz do projeto):
  $P -I tools/especime.py preparar videos/01-x/especimes.json
      → videos/01-x/img/esp/<id>.webp + videos/01-x/especimes.js (window.ESPECIMES) + creditos.json
      → previews/especimes.jpg (folha de conferência sobre o fundo creme, com id e nome)
  … preparar lista.json --so b07,b12      refaz só esses
  … preparar lista.json --fundo e6ebd7    cor do fundo da folha de conferência

lista.json = {"saida": "img/esp", "alvo": 560, "caixa": [900, 1150],
              "itens": [{"id": "b01", "t": "File:….png", "g": "besouros",
                         "rot": 90, "lado": "esq", "caixa": [x0,y0,x1,y1], "nome": "…", "alvo": 600}]}
  rot   giro em graus no sentido horário (90 = cabeça que estava à esquerda vai para cima)
  lado  "esq"/"dir": a foto tem dois exemplares lado a lado; fica com esse (padrão: o da esquerda)
  caixa recorte em frações antes de tudo; alvo = raiz da área do corpo em px de tela
Só aceita CC0, domínio público, CC BY e CC BY-SA (BY e BY-SA exigem crédito no vídeo).
"""
import argparse, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, html
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys
try:
    from scipy import ndimage as ndi
except ModuleNotFoundError:  # sem scipy esta skill nao desenha; avisa como as irmas, sem traceback
    print("Falta: Python 3.10+ com numpy e scipy (rode o preparar.py desta skill com --instalar).",
          file=sys.stderr)
    raise SystemExit(3)

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'video-laminas-de-especimes/1.0 (skill de video; https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)'

def get(url, tent=6):
    for i in range(tent):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tent - 1: raise
            time.sleep(4 * (i + 1))

def limpa(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()

def meta(title, largura):
    p = dict(action='query', format='json', formatversion=2, titles=title, prop='imageinfo',
             iiprop='url|extmetadata|size|mime', iiurlwidth=largura)
    d = json.loads(get(API + '?' + urllib.parse.urlencode(p)))
    ii = d['query']['pages'][0]['imageinfo'][0]; m = ii.get('extmetadata', {})
    lic = limpa(m.get('LicenseShortName', {}).get('value', '')); n = lic.lower()
    if re.search(r'\b(nc|nd)\b', n) or not (n.startswith('cc0') or 'public domain' in n or n.startswith('pd') or re.match(r'cc[ -]by(-sa)?\b', n)):
        sys.exit(f'{title}: licença não aceita ({lic})')
    url = ii['thumburl'] if ii['width'] > largura else ii['url']
    return url, {'title': title, 'license': lic, 'artist': limpa(m.get('Artist', {}).get('value', ''))[:120] or 'desconhecido',
                 'page': ii.get('descriptionurl')}

def nome_de(title):
    """'File:Phanaeus (Notiophanaeus) splendidulus (Fabricius, 1781) Male.png' → 'Phanaeus splendidulus'."""
    s = re.sub(r'^File:', '', title); s = re.sub(r'\.[a-zA-Z]+$', '', s)
    s = re.sub(r'^[A-Z][a-z]+(idae|inae)\s*-\s*', '', s)            # 'Buprestidae - Euchroma …'
    s = re.sub(r'^\([^)]*\)\s*', '', s)                              # '(Toulouse) …'
    w = s.split()
    if len(w) > 1 and w[1].startswith('('): w.pop(1)                 # subgênero
    return ' '.join(w[:2])

def mascara(im, t0=14, t1=46):
    """Alfa por distância ao fundo (mediana da borda). Devolve alfa 0–1, cor do fundo, máscara dura e a distância."""
    a = im.astype(np.float32); H, W, _ = a.shape; b = max(4, int(min(H, W) * .02))
    borda = np.concatenate([a[:b].reshape(-1, 3), a[-b:].reshape(-1, 3), a[:, :b].reshape(-1, 3), a[:, -b:].reshape(-1, 3)])
    bg = np.median(borda, 0)
    d = np.abs(a - bg).max(2)
    d = ndi.gaussian_filter(d, .7)
    alfa = np.clip((d - t0) / (t1 - t0), 0, 1)
    dura = d > (t0 + t1) / 2
    dura = ndi.binary_closing(dura, iterations=2)
    return alfa, bg, dura, d

def vision(im):
    """Máscara do Vision (macOS, tools/cutout) do mesmo tamanho da foto, ou None."""
    import subprocess, tempfile
    b = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cutout')
    if not os.path.exists(b): print('  (sem tools/cutout: ignorei "vision")'); return None
    d = tempfile.mkdtemp(); src, dst = os.path.join(d, 'a.png'), os.path.join(d, 'm.png'); im.save(src)
    subprocess.run([b, src, dst], capture_output=True)
    if not os.path.exists(dst): return None
    return np.asarray(Image.open(dst).convert('RGBA').getchannel('A').resize(im.size)).astype(np.float32) / 255

def isola(dura, lado, d=None, limiar=30):
    """Fica com o exemplar principal (ou o da esquerda/direita quando há dois) e o que está grudado nele."""
    lab, n = ndi.label(dura)
    if not n: sys.exit('máscara vazia')
    areas = ndi.sum(dura, lab, range(1, n + 1))
    grandes = [i + 1 for i, s in enumerate(areas) if s > .25 * areas.max()]
    if len(grandes) >= 2:
        cx = {i: ndi.center_of_mass(lab == i)[1] for i in grandes}
        alvo = (min if lado != 'dir' else max)(grandes, key=lambda i: cx[i])
    else:
        alvo = int(np.argmax(areas)) + 1
    corpo = lab == alvo
    # pedaços finos soltos (ponta de antena, tarso) perto do corpo continuam; escala e etiqueta longe somem
    H, W = dura.shape; r = max(6, int(.025 * max(H, W)))
    perto = ndi.binary_dilation(corpo, iterations=r)
    manter = np.isin(lab, [i for i in range(1, n + 1) if i == alvo or (np.any(perto & (lab == i)) and areas[i - 1] < .25 * areas.max())])
    # buracos: mancha clara do próprio corpo é preenchida; fundo preso dentro de antena/perna em laço continua fundo
    cheio = ndi.binary_fill_holes(manter); bur, nb = ndi.label(cheio & ~manter)
    if nb and d is not None:
        for i in range(1, nb + 1):
            m = bur == i
            if m.sum() > 4e-4 * m.size and np.median(d[m]) < limiar: cheio[m] = False
    return cheio

def processa(it, cfg, pasta_fontes, pasta_saida):
    url, cred = meta(it['t'], it.get('largura', 2600))
    fonte = os.path.join(pasta_fontes, it['id'] + os.path.splitext(url.split('?')[0])[1].lower().replace('.jpeg', '.jpg'))
    if not os.path.exists(fonte):
        open(fonte, 'wb').write(get(url)); time.sleep(.3)
    im = Image.open(fonte)
    if im.mode in ('RGBA', 'LA', 'P'):                      # PNG com alfa: achata sobre branco
        im = im.convert('RGBA'); fundo = Image.new('RGBA', im.size, (255, 255, 255, 255)); fundo.alpha_composite(im); im = fundo
    im = im.convert('RGB')
    if it.get('caixa'):
        x0, y0, x1, y1 = it['caixa']; W, H = im.size; im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    a = np.asarray(im).astype(np.float32)
    alfa, bg, dura, dist = mascara(a, it.get('t0', 14), it.get('t1', 46))
    if it.get('vision'):                       # sombra forte no fundo: corta pelo que o Vision acha que é o bicho
        v = vision(im)
        if v is not None: dura &= ndi.binary_dilation(v > .5, iterations=2); alfa *= ndi.gaussian_filter(v, 1.2)
    manter = isola(dura, it.get('lado', 'esq'), dist, (it.get('t0', 14) + it.get('t1', 46)) / 2)
    alfa = np.maximum(alfa, ndi.binary_erosion(manter, iterations=2)) * ndi.binary_dilation(manter, iterations=3)
    # tira o halo do fundo antigo: C = (I − (1−α)·fundo)/α
    al = alfa[..., None]
    cor = np.where(al > .02, (a - (1 - al) * bg) / np.maximum(al, .02), a)
    rgba = np.dstack([np.clip(cor, 0, 255), alfa * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, 'RGBA')
    if it.get('rot'): out = out.rotate(-it['rot'], resample=Image.BICUBIC, expand=True)
    out = out.crop(out.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox())
    # tamanho: raiz da área do exemplar → alvo; depois cabe na caixa
    A = np.asarray(out.getchannel('A')) / 255.
    k = it.get('alvo', cfg.get('alvo', 560)) / np.sqrt(A.sum())
    cw, ch = it.get('caixa_tela', cfg.get('caixa', [900, 1150]))
    k = min(k, cw / out.width, ch / out.height)
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)
    A = np.asarray(out.getchannel('A')) / 255.
    nucleo = ndi.binary_opening(A > .5, iterations=max(2, int(.04 * min(out.size))))   # sem pernas nem antenas
    cy, cx = ndi.center_of_mass(nucleo if nucleo.sum() > 50 else A)
    arq = os.path.join(pasta_saida, it['id'] + '.webp')
    out.save(arq, 'WEBP', quality=it.get('q', 90), method=6)
    return {'id': it['id'], 'src': os.path.relpath(arq, cfg['_raiz']).replace(os.sep, '/'), 'w': out.width, 'h': out.height,
            'cx': round(float(cx), 1), 'cy': round(float(cy), 1), 'g': it.get('g', ''), 'nome': it.get('nome') or nome_de(it['t'])}, cred

def folha(itens, raiz, fundo, saida):
    cols, cw, chh = 8, 230, 300
    rows = -(-len(itens) // cols)
    sh = Image.new('RGB', (cols * cw, rows * chh), fundo); dr = ImageDraw.Draw(sh)
    try: fnt = ImageFont.load_default(size=15)
    except TypeError: fnt = ImageFont.load_default()
    for i, e in enumerate(itens):
        im = Image.open(os.path.join(raiz, e['src'])).convert('RGBA')
        k = 1 / 5.2; im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))))
        x, y = (i % cols) * cw, (i // cols) * chh
        cx, cy = x + cw / 2, y + 125
        sh.paste(im, (int(cx - e['cx'] * k), int(cy - e['cy'] * k)), im)
        dr.text((x + 6, y + chh - 40), f"{e['id']} {e['nome'][:24]}", fill='#333', font=fnt)
        dr.text((x + 6, y + chh - 22), f"{e['w']}×{e['h']}", fill='#777', font=fnt)
    sh.save(saida, quality=88); print('folha:', saida)

def preparar(a):
    cfg = json.load(open(a.lista, encoding="utf-8")); raiz = os.path.dirname(os.path.abspath(a.lista)); cfg['_raiz'] = raiz
    pasta_saida = os.path.join(raiz, cfg.get('saida', 'img/esp')); pasta_fontes = os.path.join(raiz, 'fontes')
    os.makedirs(pasta_saida, exist_ok=True); os.makedirs(pasta_fontes, exist_ok=True)
    so = set(a.so.split(',')) if a.so else None
    dados_js = os.path.join(raiz, 'especimes.js'); credj = os.path.join(raiz, 'creditos.json')
    velho = {}
    if os.path.exists(dados_js):
        txt = open(dados_js, encoding="utf-8").read(); velho = {e['id']: e for e in json.loads(txt[txt.index('['):txt.rindex(']') + 1])}
    creds = {c['id']: c for c in json.load(open(credj, encoding="utf-8"))} if os.path.exists(credj) else {}
    res = []
    for it in cfg['itens']:
        if so and it['id'] not in so and it['id'] in velho: res.append(velho[it['id']]); continue
        try:
            e, c = processa(it, cfg, pasta_fontes, pasta_saida)
        except SystemExit as err:
            print(f"{it['id']}: {err}"); continue
        c['id'] = it['id']; creds[it['id']] = c; res.append(e)
        print(f"{e['id']:5s} {e['w']:4d}×{e['h']:<4d} {e['nome']:32s} {c['license']} · {c['artist'][:30]}")
    ids = {e['id'] for e in res}
    open(dados_js, 'w', encoding="utf-8", newline="\n").write('window.ESPECIMES = ' + json.dumps(res, ensure_ascii=False, indent=0) + ';\n')
    json.dump([creds[i] for i in [e['id'] for e in res]], open(credj, 'w', encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    folha(res, raiz, '#' + a.fundo, a.folha)
    print(f'{len(res)} exemplares → {os.path.relpath(dados_js)}')

def creditos(a):
    cred = json.load(open(a.arquivo, encoding="utf-8"))
    def lic(l): return 'domínio público' if 'public domain' in l.lower() or l.lower().startswith('pd') else l
    por = {}
    for c in cred:
        nome = re.sub(r'\s+from\s+.*$', '', c['artist']).strip()
        nome = {'URSchmidt': 'Udo Schmidt', 'Bennyboymothman': 'Ben Sale'}.get(nome, nome)
        nome = re.sub(r'^Sale, Ben$', 'Ben Sale', nome)
        por.setdefault(nome, set()).add(lic(c['license']))
    print(' · '.join(f"{n} ({', '.join(sorted(l))})" for n, l in por.items()))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('preparar'); p.add_argument('lista'); p.add_argument('--so'); p.add_argument('--fundo', default='e6ebd7')
    p.add_argument('--folha', default=os.path.join('previews', 'especimes.jpg'))
    c = sp.add_parser('creditos'); c.add_argument('arquivo')
    a = ap.parse_args(); {'preparar': preparar, 'creditos': creditos}[a.cmd](a)
