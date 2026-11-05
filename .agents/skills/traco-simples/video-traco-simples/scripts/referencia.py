#!/usr/bin/env python3
"""Lê um vídeo de referência para copiar estilo e movimento (não o conteúdo):
  - folhas de contato a N quadros por segundo (4 s por folha) para ler ritmo, entradas, saídas e trocas de fundo;
  - quadros-chave grandes nos instantes pedidos;
  - paleta dominante (as cores chapadas que mais aparecem), em hex, pronta para TR.usarPaleta.

uso: audio/.venv/bin/python tools/referencia.py <video> <pasta-saida> [--qps 8] [--cores 8] [--em 0.7,3.2,6.9]
"""
import argparse, json, math, os, subprocess, sys
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('saida')
ap.add_argument('--qps', type=float, default=8, help='quadros por segundo nas folhas (8 mostra bem o stop-motion)')
ap.add_argument('--cores', type=int, default=8, help='quantas cores dominantes listar')
ap.add_argument('--em', default='', help='instantes (s) para quadros-chave grandes, separados por vírgula')
a = ap.parse_args()
os.makedirs(a.saida, exist_ok=True)

def run(*c): subprocess.run(c, check=True, capture_output=True)
info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,r_frame_rate',
                                  '-select_streams', 'v:0', '-of', 'json', a.video], capture_output=True, text=True, check=True).stdout)
dur = float(info['format']['duration']); st = info['streams'][0]; W, H = st['width'], st['height']
print(f'{os.path.basename(a.video)}: {W}x{H}, {dur:.2f} s, {st["r_frame_rate"]} qps')

# folhas de contato: 4 s cada, 10 colunas
cols, per = 10, 4.0; rows = math.ceil(per * a.qps / cols); n = math.ceil(dur / per)
for i in range(n):
    out = os.path.join(a.saida, f'folha_{i:02d}_{i * per:04.1f}s.jpg')
    run('ffmpeg', '-v', 'error', '-y', '-ss', str(i * per), '-t', str(per), '-i', a.video, '-vf',
        f'fps={a.qps},scale=200:-1,tile={cols}x{rows}', '-frames:v', '1', out)
    print('folha', out, f'({i * per:.1f}–{min(dur, (i + 1) * per):.1f} s, {1 / a.qps:.3f} s por célula, leitura em linhas)')

# quadros-chave
for t in [float(x) for x in a.em.split(',') if x.strip()]:
    out = os.path.join(a.saida, f'quadro_{t:05.2f}s.jpg')
    run('ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', a.video, '-frames:v', '1', '-vf', 'scale=540:-1', out); print('quadro', out)

# paleta: 30 quadros espaçados, reduzidos, quantizados juntos
tmp = os.path.join(a.saida, '_amostra.png')
run('ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vf', f'fps={30 / dur},scale=120:-1,tile=30x1', '-frames:v', '1', tmp)
im = Image.open(tmp).convert('RGB'); os.remove(tmp)
q = im.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
pal = q.getpalette(); cnt = sorted(q.getcolors(), reverse=True); tot = sum(c for c, _ in cnt)
print('\npaleta dominante (% da área):')
ok = []
for c, idx in cnt:
    r, g, b = pal[idx * 3: idx * 3 + 3]
    if any(abs(r - R) + abs(g - G) + abs(b - B) < 40 for R, G, B in ok): continue   # junta tons quase iguais (JPEG)
    ok.append((r, g, b)); print(f'  #{r:02x}{g:02x}{b:02x}  {100 * c / tot:5.1f}%')
    if len(ok) >= a.cores: break
print('\ndica: o fundo mais frequente costuma ser o 1º; as cores de objeto são as de 3–15%. Monte TR.usarPaleta({k, L, R, V, M, G, W}).')
