"""Som do estilo pelúcia: caixinha de música macia em loop + efeitos de feltro, tudo sintetizado em numpy.
uso: python3 <skill>/scripts/som.py <pasta-do-projeto> <prefixo-do-video>
Lê videos/<nome>/cues.json (gravado pelo render.mjs) e grava audio/<nome>.wav.
O áudio é CIRCULAR: tudo que passa do fim (caudas) volta para o começo → o vídeo funciona em loop sem emenda.
Cues conhecidas: m:loop, vira, pof, fofo, sacola, sino, clique, pop, chiado (d=duração). Opções: gain (dB), pan (-1..1).
"""
import json, sys, os, glob
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
R = np.random.default_rng(7)
def N(d): return max(1, int(round(d * SR)))
def tt(d): return np.arange(N(d)) / SR
def db(x): return 10 ** (x / 20)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def sos(kind, f, o=2): return signal.butter(o, f, btype=kind, fs=SR, output='sos')
def lp(x, f, o=2): return signal.sosfilt(sos('lowpass', min(f, SR * .45), o), x)
def hp(x, f, o=2): return signal.sosfilt(sos('highpass', f, o), x)
def bp(x, lo, hi, o=2): return signal.sosfilt(sos('bandpass', [lo, min(hi, SR * .45)], o), x)
def noise(d): return R.standard_normal(N(d))

# ── instrumentos ──
def caixinha(m, d=1.6, vel=1.):           # caixinha de música / celesta: senoide + parcial inarmônico, ataque de feltro
    t = tt(d); f = mtof(m)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / .55) + .35 * np.sin(2 * np.pi * f * 4.02 * t) * np.exp(-t / .12) + .12 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / .3)
    return x * np.clip(t / .004, 0, 1) * vel
def pad(ms, d, a=.6, r=1.2):              # pad de triângulo filtrado, bem macio
    t = tt(d + r); x = sum(signal.sawtooth(2 * np.pi * mtof(m) * t * (1 + dt), .5) for m in ms for dt in (-.002, .002))
    e = np.minimum(np.clip(t / a, 0, 1), np.clip((d + r - t) / r, 0, 1)); return lp(x, 1400) * e / len(ms) * .5
def baixo(m, d):
    t = tt(d); return np.sin(2 * np.pi * mtof(m) * t) * np.minimum(np.clip(t / .02, 0, 1), np.exp(-t / 1.2))
def bumbo_feltro(d=.35):
    t = tt(d); return np.sin(2 * np.pi * (55 + 60 * np.exp(-t / .03)) * t) * np.exp(-t / .12)
def escovinha(d=.18):
    t = tt(d); return bp(noise(d), 3000, 9000) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2 * .35

# ── efeitos de feltro ──
def fx_vira():     # espátula levanta a carne: "fuíp" de tecido
    d = .32; t = tt(d); x = bp(noise(d), 700, 5000) * np.sin(np.pi * t / d) ** 2
    return x * .5 + .4 * np.sin(2 * np.pi * (380 + 500 * t / d) * t) * np.exp(-t / .06)
def fx_pof():      # carne de pelúcia cai na chapa
    d = .4; t = tt(d); return np.sin(2 * np.pi * (70 + 90 * np.exp(-t / .02)) * t) * np.exp(-t / .09) + .3 * lp(noise(d), 900) * np.exp(-t / .03)
def fx_fofo():     # bandeja passando de mão em mão: sopro macio
    d = .7; t = tt(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2; f = 400 + 1600 * np.sin(np.pi * np.clip(t / d, 0, 1))
    x = noise(d); y = np.zeros_like(x)
    for i in range(0, len(x), 1024): y[i:i + 1024] = bp(x[i:i + 1024], max(100, f[i] * .5), f[i] * 1.6)
    return lp(y, 4000) * e * .8
def fx_sacola():   # papel kraft amassando
    d = .55; t = tt(d); g = (R.random(N(d)) < .004).astype(float); g = np.convolve(g, np.exp(-np.arange(400) / 60), 'same')
    return bp(noise(d), 1500, 7000) * (.25 + g) * np.sin(np.pi * t / d) * .7
def fx_sino():     # campainha de balcão: "plim"
    d = 2.2; t = tt(d); f = 1975.5
    return (np.sin(2 * np.pi * f * t + 2.2 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .25)) * np.exp(-t / .7)) * np.clip(t / .002, 0, 1) * .6
def fx_clique():
    d = .05; t = tt(d); return bp(noise(d), 2500, 8000) * np.exp(-t / .004) * .6
def fx_pop():
    d = .18; t = tt(d); return np.sin(2 * np.pi * (300 + 900 * t / d) * t) * np.exp(-t / .05) * .6
def fx_chiado(d):  # chapa chiando baixinho: estalinhos + chiado filtrado (circular)
    t = tt(d); x = hp(noise(d), 3000) * .05 * (1 + .3 * np.sin(2 * np.pi * t * 1.3))
    c = (R.random(N(d)) < .0012).astype(float) * R.random(N(d)); return x + hp(np.convolve(c, np.exp(-np.arange(200) / 25), 'same'), 2000) * .5

class Mix:
    def __init__(s, dur): s.L = N(dur); s.x = np.zeros((2, s.L))
    def add(s, t, y, g=1., pan=0.):
        i0 = int(round(t * SR)) % s.L; idx = (i0 + np.arange(len(y))) % s.L   # circular: caudas voltam ao começo
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        np.add.at(s.x[0], idx, y * g * l * 1.414); np.add.at(s.x[1], idx, y * g * r * 1.414)

def musica(m, dur, bpm, raiz=65):   # F
    b = 60 / bpm; nb = int(round(dur / b))
    acordes = [[0, 4, 7, 11], [5, 9, 12, 16]]          # Fmaj7 → Bbmaj7 (meio ciclo cada)
    for ci, ac in enumerate(acordes):
        t0 = ci * dur / 2; m.add(t0, pad([raiz - 12 + n for n in ac], dur / 2), db(-15))
        m.add(t0, baixo(raiz - 24 + ac[0], dur / 2), db(-14))
    mel = [12, 16, 19, 16, 21, 19, 16, 14, 17, 21, 24, 21, 26, 24, 21, 19]   # colcheias, pentatônica sobre os acordes
    for i, n in enumerate(mel[:nb * 2]): m.add(i * b / 2, caixinha(raiz + n, vel=.9 if i % 2 == 0 else .6), db(-16), pan=-.25 + .5 * (i % 2))
    for k in range(nb):
        if k % 4 == 0: m.add(k * b, bumbo_feltro(), db(-12))
        m.add(k * b + b / 2, escovinha(), db(-18), pan=.3)

def main():
    pre = sys.argv[1] if len(sys.argv) > 1 else ''
    for cj in sorted(glob.glob(f'videos/{pre}*/cues.json')):
        nome = os.path.basename(os.path.dirname(cj)); C = json.loads(open(cj, encoding='utf-8').read()); dur = C['dur']; m = Mix(dur)
        FX = {'vira': fx_vira, 'pof': fx_pof, 'fofo': fx_fofo, 'sacola': fx_sacola, 'sino': fx_sino, 'clique': fx_clique, 'pop': fx_pop}
        for c in C['cues']:
            g, pan = db(c.get('gain', 0)), c.get('pan', 0)
            if c['type'] == 'm:loop': musica(m, dur, C.get('bpm') or 96)
            elif c['type'] == 'chiado': m.add(c['t'], fx_chiado(c.get('d', dur)), g * db(-8), pan=-.4)
            elif c['type'] in FX: m.add(c['t'], FX[c['type']](), g * db(-6), pan)
        x = m.x; x = x - x.mean(axis=1, keepdims=True)
        rms = np.sqrt(np.mean(x ** 2)); x *= db(-19) / max(rms, 1e-9)       # ~ -16 LUFS para peça curta
        pk = np.max(np.abs(x)); x *= min(1, db(-1.5) / pk)
        wavfile.write(f'audio/{nome}.wav', SR, (x.T * 32767).astype(np.int16)); print(nome, f'{dur}s ok')

if __name__ == '__main__': main()
