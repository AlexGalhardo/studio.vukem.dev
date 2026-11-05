#!/usr/bin/env python3
"""Trilha + efeitos do estilo Jelly, sintetizados a partir de videos/<nome>/cues.json → audio/<nome>.wav
48 kHz estéreo, −14 LUFS / −1,5 dBTP. Nada de samples. LOOP PERFEITO: tudo é gerado em dois ciclos e só o
segundo é mantido (as caudas de reverb e de efeito do fim reaparecem no começo).
uso: python3 <skill>/scripts/som.py <pasta-do-projeto> [prefixos...]
Música (VIDEO.music.style): 'jelly' (marimba + kalimba + baixo pizzicato + shaker, 8 tempos que fecham o loop).
Efeitos (cue tipo): martelo · passo · plop · massa · baque · boing · squish
"""
import json, os, sys, subprocess, re
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = np.random.default_rng(7)
NOTES = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]

def N(d): return max(1, int(round(d * SR)))
def tt(d): return np.arange(N(d)) / SR
def db(x): return 10 ** (x / 20)
def mtof(m): return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)
def peak(x): return float(np.max(np.abs(x))) + 1e-12
def _sos(kind, f, o=2): return signal.butter(o, f, btype=kind, fs=SR, output='sos')
def lp(x, f, o=2): return signal.sosfilt(_sos('lowpass', min(f, SR * .45), o), x)
def hp(x, f, o=2): return signal.sosfilt(_sos('highpass', max(f, 10), o), x)
def bp(x, lo, hi, o=2): return signal.sosfilt(_sos('bandpass', [max(lo, 10), min(hi, SR * .45)], o), x)
def noise(d): return R.standard_normal(N(d))
def sin_f(f, d): return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, (N(d),))) / SR)
def fade(x, a=.003, b=.01):
    n = len(x); x = x.copy(); x[:N(a)] *= np.linspace(0, 1, N(a)); x[n - N(b):] *= np.linspace(1, 0, N(b)); return x
def sat(x, k=1.5): return np.tanh(k * x) / np.tanh(k)

def ir(size=1.4):
    n = N(size); t = np.arange(n) / SR; e = np.exp(-t / (size / 6.5))
    return [lp(R.standard_normal(n), 6000) * e * .5 for _ in range(2)]
def reverb(x, size=1.4, mix=.22):
    L, Rr = ir(size); return np.stack([x * (1 - mix) + signal.fftconvolve(x, L)[:len(x)] * mix, x * (1 - mix) + signal.fftconvolve(x, Rr)[:len(x)] * mix])

class Bus:
    def __init__(self, d): self.x = np.zeros((2, N(d) + N(3)))
    def add(self, t, sig, g=1.0, pan=0.0):
        if np.ndim(sig) == 1: sig = np.stack([sig * min(1, 1 - pan), sig * min(1, 1 + pan)])
        i = N(t) if t > 0 else 0
        if t < 0: sig = sig[:, N(-t):]
        j = min(i + sig.shape[1], self.x.shape[1])
        if j > i: self.x[:, i:j] += sig[:, :j - i] * g

# ── instrumentos ──
def marimba(m, d=.7, vel=1.):
    t = tt(d); f = mtof(m); return vel * (np.sin(2 * np.pi * f * t) * np.exp(-t / .22) + .35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / .03) + .12 * np.sin(2 * np.pi * f * 10 * t) * np.exp(-t / .008))
def kalimba(m, d=1.2, vel=1.):
    t = tt(d); f = mtof(m); return vel * (np.sin(2 * np.pi * f * t) * np.exp(-t / .5) + .25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / .05)) * (1 - np.exp(-t / .002))
def pizz(m, d=.5):
    t = tt(d); f = mtof(m); x = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 for k in range(1, 7)); return lp(x, 900) * np.exp(-t / .16) * (1 - np.exp(-t / .004))
def shaker(d=.1): t = tt(d); return bp(noise(d), 5000, 12000) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2

def st_jelly(D, bpm, key):
    """marimba saltitante + kalimba + baixo pizzicato. 8 tempos = 1 ciclo (5 s a 96 bpm)."""
    b = 60 / bpm; r = 60 + NOTES.get(key, 5) - 12  # F3
    deg = lambda d, o=0: r + 12 * o + MAJOR[d % 7] + 12 * (d // 7)
    prog = [0, 5, 3, 4]  # I vi IV V
    mus = Bus(D); nb = int(round(D / b))
    for i in range(nb):
        c = prog[(i // 2) % 4]
        mus.add(i * b, pizz(deg(c, -1), .5), .9)
        for k, dd in enumerate([0, 2, 4, 2]):  # semicolcheias de marimba em arpejo
            if (i + k) % 3 == 2 and k: continue
            mus.add(i * b + k * b / 4, marimba(deg(c + dd, 1), .6, .55 if k else .8), 1., (-.3 if k % 2 else .3))
        mus.add(i * b + b / 2, shaker(), .25, .4); mus.add(i * b + 3 * b / 4, shaker(.07), .15, -.4)
    mel = [7, 9, 11, 9, 7, 4, 5, 6]  # graus da kalimba (uma por tempo, oitava de cima)
    for i in range(nb):
        if i % 2 == 0: mus.add(i * b + b / 2, kalimba(deg(mel[i % 8], 1), 1.0), .45, .2)
    x = mus.x
    return np.stack([reverb(x[0], 1.6, .25)[0], reverb(x[1], 1.6, .25)[1]])
STYLES = {'jelly': st_jelly}

# ── efeitos de gelatina ──
def wobble(f0=260, d=.5, vib=18, dec=.18, prof=.18):
    """'boing' de gelatina: senoide com vibrato rápido que morre (a mola do material)."""
    t = tt(d); f = f0 * (1 + prof * np.sin(2 * np.pi * vib * t) * np.exp(-t / dec)) * (1 + .3 * np.exp(-t / .02))
    return sin_f(f, d) * np.exp(-t / dec) * (1 - np.exp(-t / .003))
def fx_martelo(c):  # batida de martelo num tijolo de goma: toc seco + boing curto
    d = .5; t = tt(d); p = c.get('pitch', 1)
    toc = bp(noise(d), 1800 * p, 5200 * p) * np.exp(-t / .006) + .8 * np.sin(2 * np.pi * 1250 * p * t) * np.exp(-t / .012)
    return toc + .9 * wobble(330 * p, d, 22, .12, .22)
def fx_passo(c):  # pisada mole: 'pluf' grave
    d = .16; t = tt(d); p = c.get('pitch', 1)
    return sin_f(180 * p * (1 + 1.2 * np.exp(-t / .012)), d) * np.exp(-t / .04) + .3 * lp(noise(d), 700) * np.exp(-t / .02)
def fx_plop(c):  # tijolo de goma caindo: bolha que sobe + baque
    d = .35; t = tt(d); p = c.get('pitch', 1)
    return .9 * sin_f(220 * p + 900 * p * (t / .08).clip(0, 1) ** .6, d) * np.exp(-t / .05) + .7 * wobble(150 * p, d, 14, .15, .25)
def fx_massa(c):  # enxada na massa: arrasto úmido
    d = .4; t = tt(d); env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return bp(noise(d), 300, 2400) * env * (1 + .5 * np.sin(2 * np.pi * 30 * t)) * .8
def fx_baque(c):  # carrinho parando: baque + chacoalho + boing
    d = .7; t = tt(d); p = c.get('pitch', 1)
    return sin_f(90 * p * (1 + .8 * np.exp(-t / .02)), d) * np.exp(-t / .12) + .25 * bp(noise(d), 2500, 7000) * np.exp(-t / .03) + .7 * wobble(200 * p, d, 16, .2, .2)
def fx_boing(c): return wobble(300 * c.get('pitch', 1), .6, 16, .22, .25)
def fx_squish(c):
    d = .3; t = tt(d); return bp(noise(d), 600, 3000) * np.exp(-t / .06) * .6 + .6 * sin_f(400 * (1 - .5 * t / d), d) * np.exp(-t / .07)
SFX = {'martelo': (fx_martelo, -10), 'passo': (fx_passo, -20), 'plop': (fx_plop, -12), 'massa': (fx_massa, -20), 'baque': (fx_baque, -13), 'boing': (fx_boing, -14), 'squish': (fx_squish, -16)}

def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)

def build(name):
    vdir = os.path.join(ROOT, 'videos', name); cj = json.loads(open(os.path.join(vdir, 'cues.json'), encoding='utf-8').read())
    D, bpm = cj['dur'], cj.get('bpm', 96); music = cj.get('music') or {}; C = cj.get('cues', [])
    mix = Bus(2 * D)
    if music.get('style') in STYLES:
        mx = STYLES[music['style']](2 * D, bpm, music.get('key', 'F'))
        g = db(-21 - rms_db(mx[:, :N(2 * D)])) * db(music.get('gain', 0)); mix.x[:, :mx.shape[1]] += mx[:, :mix.x.shape[1]] * g
    side = 1
    for c in C:
        if c['type'] not in SFX: continue
        fn, tgt = SFX[c['type']]; s = fade(fn(c)); s = s / peak(s) * db(tgt + c.get('gain', 0) * .5)
        pan = c.get('pan', .2 * side); side = -side
        for rep in (0, D): mix.add(c['t'] + rep, s, 1.0, pan)
    x = mix.x[:, N(D):N(2 * D)]
    p = peak(x)
    if p > .95: x = x * .95 / p
    raw = os.path.join(ROOT, 'audio', name + '.raw.wav'); wavfile.write(raw, SR, (x.T * 32767).astype(np.int16))
    m = subprocess.run(['ffmpeg', '-hide_banner', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', af, '-ar', str(SR), '-c:a', 'pcm_s16le', os.path.join(ROOT, 'audio', name + '.wav')], check=True)
    os.remove(raw)
    print(f'{name}: {len(C)} cues, estilo={music.get("style")}, entrada {j["input_i"]} LUFS → −14 (loop de {D} s)')

if __name__ == '__main__':
    pre = sys.argv[1:]; names = sorted(d for d in os.listdir(os.path.join(ROOT, 'videos')) if os.path.exists(os.path.join(ROOT, 'videos', d, 'cues.json')))
    for n in names:
        if not pre or any(n.startswith(p) for p in pre): build(n)
