#!/usr/bin/env python3
"""Trilha e efeitos do estilo pixel art HD-2D, sintetizados a partir de videos/<nome>/cues.json → audio/<nome>.wav

uso: <PYTHON> audio/synth.py <prefixo-do-video>

Camadas: música curta em loop (violão dedilhado Karplus-Strong + pad suave + baixo, clima "vila de RPG" com bossa)
e ambiente de rua no fim de tarde (cigarras, passarinhos, cidade distante). Cues reconhecidas:
  amb:rua {d}            ambiente de rua (cigarra + sabiá + cidade ao longe)
  motor {d, para}        moto 150 cc: pulsos de combustão que caem para a marcha lenta em `para` (s)
  buzina                 "bi-bi" de moto
  latido                 latido curto de vira-lata
  respingo               pneu passando na poça
  placa                  sininho da placa de local
  chime {m}, blip        efeitos de interface
Todos aceitam gain (dB) e pan (-1..1).
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
def mtof(m): return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)
def sos(kind, f, o=2): return signal.butter(o, f, btype=kind, fs=SR, output='sos')
def lp(x, f, o=2): return signal.sosfilt(sos('lowpass', min(f, SR * .45), o), x)
def hp(x, f, o=2): return signal.sosfilt(sos('highpass', max(f, 10), o), x)
def bp(x, lo, hi, o=2): return signal.sosfilt(sos('bandpass', [max(lo, 10), min(hi, SR * .45)], o), x)
def env(d, a=.005, r=.05):
    n = N(d); e = np.ones(n); na, nr = min(n, N(a)), min(n, N(r))
    e[:na] = np.linspace(0, 1, na); e[n - nr:] *= np.linspace(1, 0, nr); return e
def pink(d):
    w = R.standard_normal(N(d)); b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 3
def reverb(x, size=1.4, mix=.22):
    n = N(size); t = np.arange(n) / SR; ir = R.standard_normal(n) * np.exp(-t / (size / 5)); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - mix) + signal.fftconvolve(x, ir)[:len(x)] * mix

def pluck(f, d=1.6, bright=.5):
    """violão de nylon (Karplus-Strong)"""
    n, p = N(d), max(2, int(SR / f)); buf = lp(R.uniform(-1, 1, p), 2500 + bright * 4000); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = .5 * (buf[i % p] + buf[(i + 1) % p]) * .996
    return lp(out, 3800) * env(d, .002, .3)

def pad(ms, d, cut=1400):
    t = tt(d); x = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .3 * t) * .3) + .3 * np.sin(2 * np.pi * 2 * f * t) for f in mtof(ms))
    return lp(x, cut) * env(d, .6, .8) / len(ms)

def musica(dur, bpm=96):
    """loop curto: Cmaj7 → Am7 → Dm7 → G7 (bossa de vila), dedilhado em colcheias"""
    b = 60 / bpm; out = np.zeros(N(dur) + N(3))
    acordes = [[48, 55, 59, 64, 67], [45, 52, 55, 60, 64], [50, 57, 60, 65, 69], [43, 53, 59, 62, 65]]
    padrao = [0, 3, 2, 4, 1, 3, 2, 4]
    for c in range(int(np.ceil(dur / (2 * b))) + 1):
        ac = acordes[c % 4]; t0 = c * 2 * b
        x = pad([m + 12 for m in ac[1:4]], 2 * b + .8) * .22; i0 = N(t0); out[i0:i0 + len(x)] += x[:len(out) - i0]
        bx = pluck(mtof(ac[0] - 12), 1.2, .1) * .9; out[i0:i0 + len(bx)] += bx[:len(out) - i0]
        for k, v in enumerate(padrao):
            ts = t0 + k * b / 4 * (1.0 if k % 2 == 0 else 1.08)
            nota = pluck(mtof(ac[v] + 12), 1.4, .45) * (.42 if k % 2 == 0 else .3); i = N(ts); out[i:i + len(nota)] += nota[:len(out) - i]
    m = reverb(out[:N(dur)], 1.6, .28)
    return m * env(dur, .25, .35)

def ambiente(d):
    t = tt(d); cid = lp(pink(d), 380) * .06
    cig = bp(R.standard_normal(N(d)), 4200, 6200, 4) * (.5 + .5 * np.sin(2 * np.pi * 38 * t)) * (.6 + .4 * np.sin(2 * np.pi * .23 * t + 1)) * .05
    aves = np.zeros(N(d))
    for t0, f0, f1, dd in [(.4, 2600, 3400, .18), (.62, 3300, 2500, .22), (1.9, 2900, 3800, .12), (2.05, 3800, 3000, .2), (3.2, 2400, 3100, .25), (4.4, 3100, 3600, .14), (4.55, 3600, 2800, .2)]:
        tc = tt(dd); f = np.linspace(f0, f1, len(tc)); ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph + 2 * np.sin(2 * np.pi * 28 * tc)) * np.sin(np.pi * tc / dd) ** 2 * .05; i = N(t0); aves[i:i + len(x)] += x[:len(aves) - i]
    return cid + cig + reverb(aves, 1.2, .35)

def motor(d, para):
    """moto 150 cc: frequência de explosão cai com a velocidade e estabiliza na marcha lenta"""
    t = tt(d); k = np.clip(t / para, 0, 1); v = (1 - k) * 2              # derivada de power2.out
    f = np.where(t < para, 26 + 30 * np.clip(v, 0, 1) ** .8, 24 + .6 * np.sin(2 * np.pi * 3 * t))
    ph = np.cumsum(f) / SR; pulso = np.exp(-((ph % 1) * 9)) * (1 + .25 * R.standard_normal(len(t)))
    x = lp(pulso, 700) + .35 * bp(pulso * R.standard_normal(len(t)), 900, 2600)
    x = np.tanh(2.2 * x) * (.55 + .45 * np.clip(v, 0, 1))
    return hp(x, 40) * .22

def buzina():
    d = .42; out = np.zeros(N(d))
    for t0 in (0, .2):
        tb = tt(.13); x = np.sign(np.sin(2 * np.pi * 415 * tb)) * .5 + np.sign(np.sin(2 * np.pi * 498 * tb)) * .5
        x = lp(x, 2400) * env(.13, .006, .02); i = N(t0); out[i:i + len(x)] += x
    return np.tanh(1.5 * out) * .3

def latido():
    d = .2; t = tt(d); f = 520 * np.exp(-t * 4); ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sign(np.sin(ph)) * .6 + R.standard_normal(len(t)) * .5) * np.exp(-t * 14) * env(d, .004, .05)
    return bp(x, 450, 2800) * .55

def respingo():
    d = .5; t = tt(d); x = bp(R.standard_normal(len(t)), 900, 6000) * np.exp(-t * 9) * .4
    for k in range(9):
        i = N(.03 + R.uniform(0, .35)); tc = tt(.03); g = np.sin(2 * np.pi * R.uniform(1400, 3200) * tc) * np.exp(-tc * 120) * .12; x[i:i + len(g)] += g[:len(x) - i]
    return x

def chime(m=88):
    d = 1.4; t = tt(d); f = mtof(m)
    return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 3) * .18

def main():
    nome = sys.argv[1]; dirs = sorted(d for d in glob.glob('videos/*') if os.path.basename(d).startswith(nome))
    if not dirs: sys.exit('vídeo não encontrado: ' + nome)
    d = dirs[0]; C = json.load(open(os.path.join(d, 'cues.json'))); dur = C['dur']
    L = np.zeros(N(dur) + N(2)); Rr = np.zeros_like(L)
    def mix(x, t0, gain=0, pan=0):
        x = x * db(gain); i = N(t0); n = min(len(x), len(L) - i)
        if n <= 0: return
        gl, gr = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2); L[i:i + n] += x[:n] * gl * 1.41; Rr[i:i + n] += x[:n] * gr * 1.41
    mus = musica(dur, C.get('bpm') or 96); mix(mus, 0, -5)
    for c in C['cues']:
        ty, t0, g, p = c['type'], c['t'], c.get('gain', 0), c.get('pan', 0)
        if ty == 'amb:rua': a = ambiente(c.get('d', dur)); mix(a, t0, g - 2, -.15); mix(np.roll(a, 2400), t0, g - 2, .15)
        elif ty == 'motor': mix(motor(c.get('d', dur), c.get('para', dur)), t0, g, p)
        elif ty == 'buzina': mix(buzina(), t0, g, .1)
        elif ty == 'latido': mix(latido(), t0, g - 3, .35)
        elif ty == 'respingo': mix(respingo(), t0, g, -.3)
        elif ty in ('placa', 'chime'): mix(chime(c.get('m', 88)), t0, g); mix(chime(c.get('m', 88) + 7), t0 + .09, g - 4)
        elif ty == 'blip': mix(chime(100)[:N(.15)], t0, g)
    s = np.stack([L, Rr], 1)[:N(dur)]
    s[-N(.08):] *= np.linspace(1, 0, N(.08))[:, None]; s[:N(.02)] *= np.linspace(0, 1, N(.02))[:, None]
    s *= db(-2.5) / (np.max(np.abs(s)) + 1e-9)          # pico −2,5 dBFS ≈ −14 LUFS nesta mixagem
    os.makedirs('audio', exist_ok=True); out = f'audio/{os.path.basename(d)}.wav'
    wavfile.write(out, SR, (s * 32767).astype(np.int16)); print('ok', out, f'{dur:.2f}s')

if __name__ == '__main__':
    main()
