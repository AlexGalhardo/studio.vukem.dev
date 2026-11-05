#!/usr/bin/env python3
"""Separa uma pintura em camadas de profundidade (2.5D): máscaras por Vision + polígonos à mão,
fundo refeito por inpainting (push-pull), obra estendida para caber no 9:16 e camadas leves (webp com alfa).

uso (da pasta do projeto):
  <PYTHON> tools/camadas.py vision  videos/<v>/img/pintura.jpg videos/<v>/masc/frente.png --caixa .39,.48,.95,1
      → SÓ NO macOS: Vision dentro da caixa (frações 0–1); grava a máscara no tamanho da pintura inteira.
        A caixa precisa CONTER as figuras inteiras: onde ela corta, a máscara fica com uma borda reta.
        Fora do macOS este subcomando sai com código 2 e explica como entregar a máscara pronta.
  <PYTHON> tools/camadas.py prova   videos/<v>/img/pintura.jpg videos/<v>/masc/*.png --saida previews/mascaras.jpg
      → pinta cada máscara de uma cor sobre a pintura (confira braços, espadas, chapéus: partes finas somem)
  <PYTHON> tools/grade.py videos/<v>/img/pintura.jpg previews/grade.jpg [--caixa x0,y0,x1,y1 --passo 10]
      → grade numerada para desenhar polígonos (coordenadas na escala de 1600 px de largura)
  cd videos/<v> && <PYTHON> ../../tools/camadas.py montar camadas.json
      → lê o plano e grava em img/: <fundo>.jpg (obra limpa e estendida) + <camada>.webp + camadas-out.json

camadas.json (as camadas vão do FUNDO para a FRENTE; a 1ª é o fundo inteiro, sem máscara):
  pintura: "img/pintura.jpg"     saida: "img"      formato: "webp" | "png"     qualidade: 90
  extensao: {cima, baixo, lados}  px a acrescentar fora da obra (céu novo em cima; espelho desfocado nos lados/embaixo)
  limpar_borda: 8                 corta o fio escuro da digitalização (máscaras e polígonos acompanham)
  clarear_topo: [600, 1.17]       clareia o alto da obra antes de estender (verniz velho deixa uma faixa escura)
  camadas: [{ nome, K,            K = ampliação relativa ao plano de foco no fim do dolly (frente > 1 > fundo)
      mascara: "masc/x.png" | [...],      máscaras do Vision (uniões)
      mais: [polígono | {pts, suave}],     polígonos somados (braços, espadas, chão sob as figuras com borda esfumada)
      menos: [...], so: [...],             subtrai / restringe
      escala_pts: 2.4,                     pontos desenhados na grade de 1600 px → × 2.4 para a pintura de 3840 px
      suave: 1.5, dilatar, erodir,         borda do alfa (px)
      estender_baixo: 650, modo_baixo: "reflexo" | "esticar",   camada que encosta no pé da obra continua para baixo
      blur: px }]                          (opcional, lido pelo palco) desfoque fixo em vez do calculado por K

Por que o inpainting: atrás de cada recorte a camada de trás precisa ter CONTEÚDO, senão o parallax abre um
buraco. A placa de cada camada é a pintura com tudo o que está na frente dela apagado, de trás para a frente.
"""
import argparse, json, os, platform, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None

SEM_VISION = """As máscaras automáticas (Vision) não estão disponíveis neste sistema ({sistema}).

O subcomando `vision` usa o framework Vision da Apple (macOS 14+), que não tem equivalente no Windows nem
no Linux, e esta skill não baixa modelo de recorte nenhum. Todo o RESTO — `prova`, `montar`, o inpainting,
a extensão da obra, o render e o som — funciona normalmente.

Entregue cada máscara pronta, uma por figura, e siga para `prova` e `montar`:

  - PNG em tons de cinza DO MESMO TAMANHO da pintura (branco = figura, preto = resto);
  - recorte a figura em qualquer editor (GIMP, Photopea, Paint.NET, Photoshop, "Remover fundo" do
    Paint do Windows 11), cole o recorte sobre uma tela preta do tamanho da obra e salve;
  - grave em masc/<nome>.png e aponte no camadas.json pelo campo "mascara".

Sem editor nenhum dá para trabalhar só com polígonos: desenhe-os no campo "mais" do camadas.json usando as
coordenadas que o `tools/grade.py` imprime sobre a obra. É mais trabalhoso e a borda fica reta."""


def vision(a):
    if platform.system() != 'Darwin':
        print(SEM_VISION.format(sistema=platform.system() or 'desconhecido')); sys.exit(2)
    binario = AQUI / 'cutout'
    if not binario.exists():
        print(f'não achei {binario} — rode o projeto.py da skill (ele compila o cutout.swift; '
              'precisa de macOS 14+ e do swiftc das Xcode Command Line Tools).'); sys.exit(2)
    im = Image.open(a.pintura).convert('RGB'); W, H = im.size
    x0, y0, x1, y1 = map(float, a.caixa.split(','))
    bx = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
    tmp = Path(tempfile.mkdtemp(prefix='camadas-')); src = tmp / 'c.png'; out = tmp / 'm.png'
    im.crop(bx).save(src)
    r = subprocess.run([str(binario), str(src), str(out)], capture_output=True, text=True, encoding='utf-8')
    print((r.stdout or '').strip())
    if r.returncode or not out.exists(): sys.exit('Vision não achou objeto nessa caixa')
    al = Image.open(out).getchannel('A')
    m = Image.new('L', (W, H), 0); m.paste(al, bx[:2])
    saida = Path(a.saida); saida.parent.mkdir(parents=True, exist_ok=True); m.save(saida)
    print(saida, 'cobertura', round(np.asarray(m).mean() / 255, 3))


def prova(a):
    im = Image.open(a.pintura).convert('RGB')
    esc = 1600 / im.width; im = im.resize((1600, round(im.height * esc)), Image.LANCZOS)
    cores = [(255, 60, 60), (60, 200, 255), (255, 210, 40), (120, 255, 120), (230, 90, 255), (255, 140, 0)]
    out = np.asarray(im, float)
    for i, f in enumerate(a.mascaras):
        m = np.asarray(Image.open(f).convert('L').resize(im.size, Image.BILINEAR), float)[..., None] / 255
        out = out * (1 - m * .55) + np.array(cores[i % len(cores)]) * m * .55
    Image.fromarray(out.clip(0, 255).astype('uint8')).save(a.saida, quality=88); print(a.saida)


def poligono(W, H, pts, esc, b=0):
    """pts = [[x,y],…] ou {"pts":[…], "suave": raio} (borda própria, ex. saia de chão bem esfumada)."""
    suave = 0
    if isinstance(pts, dict): suave = pts.get('suave', 0); pts = pts['pts']
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon([(x * esc - b, y * esc - b) for x, y in pts], fill=255)
    if suave: m = m.filter(ImageFilter.GaussianBlur(suave * esc))
    return np.asarray(m, float) / 255


def mascara(c, W, H, base, b=0):
    """máscara final de uma camada: Vision (arquivo) ∪ polígonos 'mais' − polígonos 'menos', com dilatação/feather."""
    m = np.zeros((H, W))
    for f in ([c['mascara']] if isinstance(c.get('mascara'), str) else c.get('mascara', [])):   # uma ou várias máscaras do Vision
        v = np.asarray(Image.open(os.path.join(base, f)).convert('L'), float) / 255
        m = np.maximum(m, v[b:b + H, b:b + W])
    e = c.get('escala_pts', 1.0)              # os pontos podem vir numa escala de prova (ex. 2000 px de largura)
    for p in c.get('mais', []): m = np.maximum(m, poligono(W, H, p, e, b))
    for p in c.get('menos', []): m = np.minimum(m, 1 - poligono(W, H, p, e, b))
    if c.get('so', []):                         # restringe à união destes polígonos
        lim = np.zeros((H, W))
        for p in c['so']: lim = np.maximum(lim, poligono(W, H, p, e, b))
        m = m * lim
    mi = Image.fromarray((m * 255).astype('uint8'))
    if c.get('dilatar'): mi = mi.filter(ImageFilter.MaxFilter(int(c['dilatar']) * 2 + 1))
    if c.get('erodir'): mi = mi.filter(ImageFilter.MinFilter(int(c['erodir']) * 2 + 1))
    if c.get('suave', 1.5): mi = mi.filter(ImageFilter.GaussianBlur(c.get('suave', 1.5)))
    return np.asarray(mi, float) / 255


def puxa_empurra(rgb, peso):
    """preenchimento suave (push-pull): média ponderada em pirâmide, desce até cobrir o buraco e sobe
    interpolando. Dá campos de cor contínuos, sem as manchas em blocos do Telea em buracos grandes."""
    import cv2
    niveis = []
    c = rgb.astype(np.float32) * peso[..., None]; w = peso.astype(np.float32).copy()
    while min(w.shape) > 4:
        niveis.append((c, w))
        c = cv2.resize(cv2.GaussianBlur(c, (5, 5), 1), (max(1, c.shape[1] // 2), max(1, c.shape[0] // 2)), interpolation=cv2.INTER_AREA)
        w = cv2.resize(cv2.GaussianBlur(w, (5, 5), 1), (c.shape[1], c.shape[0]), interpolation=cv2.INTER_AREA)
    cor = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(niveis):
        up = cv2.resize(cor, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        k = np.clip(w * 4, 0, 1)[..., None]
        cor = (c / np.maximum(w, 1e-6)[..., None]) * k + up * (1 - k)
    return cor


def textura_tela(shape, seed=7, forca=1.0):
    """grão de pintura a óleo: ruído fino + pinceladas (ruído esticado na horizontal)."""
    import cv2
    r = np.random.default_rng(seed); h, w = shape
    fino = r.normal(0, 2.4, (h, w)).astype(np.float32)
    pinc = cv2.resize(r.normal(0, 1, (h // 5 + 1, w // 14 + 1)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC) * 3.2
    return (fino + pinc)[..., None] * forca


def inpaint(rgb, buraco, dil=21):
    """apaga a camada da frente da placa de trás: push-pull (cor contínua puxada das bordas) + grão de
    tela. O parallax revela só uma faixa atrás de cada recorte, e ela fica parecida com poeira/terra."""
    import cv2
    h = (buraco > .02).astype(np.uint8)
    h = cv2.dilate(h, np.ones((dil, dil), np.uint8))   # pega o contorno escuro e a sombra do recorte
    s = 2
    small = cv2.resize(rgb, (rgb.shape[1] // s, rgb.shape[0] // s), interpolation=cv2.INTER_AREA)
    hs = cv2.resize(h, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    fill = puxa_empurra(small, 1 - hs.astype(np.float32))
    fill = cv2.resize(fill, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC)
    fill = fill + textura_tela(fill.shape[:2])
    k = cv2.GaussianBlur(h.astype(np.float32), (0, 0), 2.5)[..., None]
    return np.clip(rgb * (1 - k) + fill * k, 0, 255).astype('uint8')


def hp_borda(x):
    """alta frequência (grão da tela) de uma faixa — para o trecho esfumado não ficar liso."""
    import cv2
    return (x - cv2.GaussianBlur(x, (0, 0), 2.5)) * .8


def estender(rgb, cima, baixo, lados, ceu=(112, 142, 172)):
    """estende a pintura para fora da moldura (o 9:16 mostra mais altura do que a obra tem):
    • cima: céu novo — a cor da borda de cima continua subindo (push-pull, sem emenda), vai para um azul
      mais fundo (ceu=RGB), ganha nuvens suaves de ruído e o grão/pincelada da própria tela;
    • lados e baixo: espelha e desfoca (o que passa da borda vira atmosfera fora de foco) e escurece embaixo."""
    import cv2
    H, W = rgb.shape[:2]
    src = rgb.astype(np.float32)
    out = cv2.copyMakeBorder(src, cima, baixo, lados, lados, cv2.BORDER_REFLECT_101)
    Ho, Wo = out.shape[:2]
    yy = np.arange(Ho, dtype=np.float32)[:, None] * np.ones((1, Wo), np.float32)
    xx = np.ones((Ho, 1), np.float32) * np.arange(Wo, dtype=np.float32)[None, :]
    dy = np.clip(yy - (cima + H), 0, None) / max(baixo, 1)
    dx = np.maximum(np.clip(lados - xx, 0, None) / max(lados, 1), np.clip(xx - (lados + W), 0, None) / max(lados, 1))
    d = np.maximum(dx, dy)[..., None]
    b1 = cv2.GaussianBlur(out, (0, 0), 14); b2 = cv2.GaussianBlur(out, (0, 0), 45)
    a1 = np.clip(d * 5, 0, 1); a2 = np.clip(d * 2 - .2, 0, 1)
    mix = out * (1 - a1) + b1 * a1
    mix = mix * (1 - a2) + b2 * a2
    if baixo:  # chão: escurece (primeiro plano na sombra)
        mix = mix * (1 - np.clip(dy, 0, 1)[..., None] * .45)
    if cima:
        # 1) continua a cor da borda para cima, sem emenda (push-pull em escala reduzida)
        s = 4; hh = (cima + 600) // s; ww = Wo // s
        faixa = cv2.resize(mix[:cima + 600], (ww, hh), interpolation=cv2.INTER_AREA)
        peso = np.zeros((hh, ww), np.float32); peso[cima // s:] = 1
        cont = puxa_empurra(faixa, peso)
        cont = cv2.GaussianBlur(cont, (0, 0), 6)
        cont = cv2.resize(cont, (Wo, cima + 600), interpolation=cv2.INTER_CUBIC)[:cima]
        u = np.clip((cima - yy[:cima]) / cima, 0, 1)[..., None]   # 0 na borda da obra → 1 no alto
        base = cont * (1 - u ** .9 * .8) + np.array(ceu, np.float32) * (u ** .9 * .8)
        # 2) nuvens suaves (ruído grande, mais claro) — mais presentes perto da obra
        r = np.random.default_rng(3)
        nuv = sum(cv2.resize(r.normal(0, 1, (max(2, cima // f), max(2, Wo // (f * 3)))).astype(np.float32), (Wo, cima),
                             interpolation=cv2.INTER_CUBIC) * a for f, a in ((260, 9), (110, 4.5), (40, 2)))
        base = base + nuv[..., None] * np.array([1, 1, .92], np.float32) * (1 - u * .4)
        # 3) a pincelada da tela atravessa a borda (reflexo da textura, sumindo em ~300 px)
        refl = src[1:cima + 1][::-1]
        refl = cv2.copyMakeBorder(refl, 0, max(0, cima - refl.shape[0]), lados, lados, cv2.BORDER_REFLECT_101)[:cima]
        hp = refl - cv2.GaussianBlur(refl, (0, 0), 3)
        dist = (cima - yy[:cima])[..., None]
        base = base + hp * np.clip(1 - dist / 320, 0, 1) * .9
        # 4) costura: logo acima da obra, a cor é a da PRÓPRIA borda (linha de cima, desfocada na horizontal)
        borda = cv2.GaussianBlur(out[cima:cima + 14].mean(0)[None], (0, 0), 30)[0][None]
        g = np.clip(dist / 260, 0, 1); g = g * g * (3 - 2 * g)
        base = (borda + hp * np.clip(1 - dist / 320, 0, 1) * .9) * (1 - g) + base * g
        mix[:cima] = base
        # 4b) esfuma a borda de cima da própria obra (manchas de verniz e o fio da borda somem na extensão)
        fx = 180; faixa = mix[cima:cima + fx]
        borr = cv2.GaussianBlur(mix[max(0, cima - 200):cima + fx + 200], (0, 0), 22)[cima - max(0, cima - 200):][:fx]
        w = (1 - np.arange(fx, dtype=np.float32) / fx)[:, None, None] ** 2 * .85
        mix[cima:cima + fx] = faixa * (1 - w) + (borr + hp_borda(faixa)) * w
        # 5) nivela a costura: tira o "vale" de cor/luz que sobra em volta da borda (verniz escuro no alto da tela)
        r0, r1 = max(0, cima - 380), min(Ho - 1, cima + 380)
        prof = cv2.GaussianBlur(mix[r0:r1 + 1].mean(1)[:, None, :], (0, 0), sigmaX=1, sigmaY=40)[:, 0, :]
        alvo = prof[0] + (prof[-1] - prof[0]) * np.linspace(0, 1, len(prof))[:, None]
        jan = np.hanning(len(prof))[:, None]
        mix[r0:r1 + 1] *= (1 + (alvo / np.maximum(prof, 1) - 1) * jan)[:, None, :]
    hp = out - cv2.GaussianBlur(out, (0, 0), 2.5)                 # grão da tela de volta nas bordas espelhadas
    mix = mix + hp * np.clip(d * 3, 0, 1) * .5
    fora = np.maximum(d, (yy < cima)[..., None].astype(np.float32))
    mix = mix + textura_tela((Ho, Wo), 11, .55) * fora
    return np.clip(mix, 0, 255).astype('uint8')


def pe_da_camada(rgba, n, modo):
    """estende para baixo uma camada que encosta na borda de baixo da obra.
    'reflexo': espelho escurecido com ondulação (beira d'água: o riacho reflete o que está na margem);
    'esticar': as últimas linhas esticadas e desfocadas (chão/mato fora de foco, escurecendo)."""
    import cv2
    h, w = rgba.shape[:2]; f = rgba.astype(np.float32)
    if modo == 'reflexo':
        pe = f[::-1][:n].copy()
        yy = np.arange(n, dtype=np.float32)
        r = np.random.default_rng(5)
        for i in range(n):                                       # ondulação: cada linha anda um pouco de lado
            dx = int(round((2 + i * .045) * np.sin(i * .21 + r.uniform(0, .6)) + r.normal(0, .4 + i * .01)))
            pe[i] = np.roll(pe[i], dx, axis=0)
        pe = cv2.GaussianBlur(pe, (0, 0), sigmaX=6, sigmaY=14)
        k = (.5 - .25 * yy / n)[:, None, None]
        agua = np.array([58, 56, 46], np.float32)
        pe[..., :3] = pe[..., :3] * k + agua * (1 - k) * .55
        pe[..., 3] = pe[..., 3] * np.clip(1 - yy / n * .25, 0, 1)[:, None]
    else:
        m = min(90, h)
        base = f[h - m:]
        pe = cv2.resize(base, (w, n), interpolation=cv2.INTER_LINEAR)
        pe = cv2.GaussianBlur(pe, (0, 0), sigmaX=18, sigmaY=10)
        pe[..., :3] *= np.linspace(.9, .5, n)[:, None, None]
    pe[..., :3] += textura_tela((n, w), 13, .7)
    # costura: as primeiras linhas misturam com a última linha real (sem degrau)
    return np.clip(pe, 0, 255).astype('uint8')


def montar(a):
    import cv2
    plano = json.loads(Path(a.plano).read_text(encoding='utf-8')); base = str(Path(a.plano).resolve().parent)
    im = np.array(Image.open(Path(base) / plano['pintura']).convert('RGB'))
    H, W = im.shape[:2]
    b = plano.get('limpar_borda', 0)                 # a borda da digitalização costuma ter um fio escuro: corta (e as máscaras junto)
    if b: im = im[b:-b, b:-b].copy(); H, W = im.shape[:2]
    ext = plano.get('extensao', {'cima': 0, 'baixo': 0, 'lados': 0})
    camadas = plano['camadas']                       # da FRENTE para trás? não: do FUNDO para a frente
    masks = [mascara(c, W, H, base, b) for c in camadas]
    saida = os.path.join(base, plano.get('saida', 'img'))
    os.makedirs(saida, exist_ok=True)
    out = {'pintura': [W, H], 'extensao': ext, 'camadas': []}
    # placa de cada camada = pintura com tudo o que está NA FRENTE dela apagado (inpaint)
    frente = np.zeros((H, W))
    placas = [None] * len(camadas)
    atual = im.copy()
    for i in range(len(camadas) - 1, -1, -1):      # da frente para o fundo
        placas[i] = atual
        if i > 0:
            buraco = np.clip(masks[i] * 1.0, 0, 1)
            frente = np.maximum(frente, buraco)
            atual = inpaint(atual, frente)
            frente = np.zeros((H, W))               # o inpaint já incorporou; próximo buraco é só da camada seguinte
    for i, c in enumerate(camadas):
        nome = c['nome']
        if i == 0:                                   # fundo: pintura limpa e estendida, sem alfa
            pl = placas[0]
            if plano.get('clarear_topo'):            # verniz velho escurece o alto da tela: clareia de leve antes de estender
                n, f = plano['clarear_topo']; g = (1 + (f - 1) * np.clip(1 - np.arange(H) / n, 0, 1) ** 1.5)[:, None, None]
                pl = np.clip(pl * g, 0, 255).astype('uint8')
            rgb = estender(pl, ext['cima'], ext['baixo'], ext['lados'])
            Image.fromarray(rgb).save(os.path.join(saida, nome + '.jpg'), quality=c.get('q', 90))
            out['camadas'].append({**{k: v for k, v in c.items() if k not in ('mais', 'menos', 'so')}, 'arquivo': nome + '.jpg',
                                   'x': -ext['lados'], 'y': -ext['cima'], 'w': rgb.shape[1], 'h': rgb.shape[0]})
            continue
        m = masks[i]
        ys, xs = np.where(m > .01)
        x0, y0, x1, y1 = max(0, xs.min() - 4), max(0, ys.min() - 4), min(W, xs.max() + 5), min(H, ys.max() + 5)
        rgb = placas[i][y0:y1, x0:x1]
        rgba = np.dstack([rgb, (m[y0:y1, x0:x1] * 255).astype('uint8')])
        if c.get('borrar'):                          # camada que vai ficar fora de foco o tempo todo: pré-desfoca (leve no render)
            rgba = np.asarray(Image.fromarray(rgba, 'RGBA').filter(ImageFilter.GaussianBlur(c['borrar'])))
        if c.get('estender_baixo'):                  # camada que encosta na borda de baixo: continua para fora da obra
            pe = pe_da_camada(rgba, c['estender_baixo'], c.get('modo_baixo', 'esticar'))
            rgba = np.concatenate([rgba, pe], 0); y1 += c['estender_baixo']
        fmt = plano.get('formato', 'webp')           # webp com alfa: ~10× menor que png e o Chromium lê direto
        arq = nome + ('.webp' if fmt == 'webp' else '.png')
        if fmt == 'webp': Image.fromarray(rgba, 'RGBA').save(os.path.join(saida, arq), quality=plano.get('qualidade', 90), method=6)
        else: Image.fromarray(rgba, 'RGBA').save(os.path.join(saida, arq), optimize=True)
        out['camadas'].append({**{k: v for k, v in c.items() if k not in ('mais', 'menos', 'so')}, 'arquivo': arq,
                               'x': int(x0), 'y': int(y0), 'w': int(x1 - x0), 'h': int(y1 - y0)})
        print(nome, (x0, y0, x1, y1))
    (Path(saida) / 'camadas-out.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                  encoding='utf-8', newline='\n')
    print('ok →', Path(saida) / 'camadas-out.json')


ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
p = sp.add_parser('vision'); p.add_argument('pintura'); p.add_argument('saida'); p.add_argument('--caixa', required=True); p.set_defaults(f=vision)
p = sp.add_parser('prova'); p.add_argument('pintura'); p.add_argument('mascaras', nargs='+'); p.add_argument('--saida', default='previews/mascaras.jpg'); p.set_defaults(f=prova)
p = sp.add_parser('montar'); p.add_argument('plano'); p.set_defaults(f=montar)
a = ap.parse_args(); a.f(a)
