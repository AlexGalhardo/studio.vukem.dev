"""Trilha ambiente sintetizada do estilo maquete-3d (numpy + scipy, nada baixado).
Camadas, todas em ciclo da duração do vídeo (o fim volta para o começo → loop sem emenda):
  - bossa: violão de nylon (Karplus-Strong) num ii-V com levada sincopada + baixo macio
  - salão: murmúrio de conversa (ruído rosa em banda de voz modulado em ritmo de sílaba)
  - chapa: chiado (ruído agudo) com estalos
  - panela: borbulhas graves
  - louça: tilintar de pratos/copos e o "plim" do caixa
uso: <PYTHON> audio/synth.py <video>   (lê videos/<video>/cues.json → grava audio/<video>.wav)
Parâmetros por vídeo: VIDEO.music = {acordes:[[midi...],...], bpm, ganho:{bossa,salao,chapa,panela,louca}} (opcional).
"""
import json, sys, glob, os
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
R = np.random.default_rng(7)
def n(d): return int(round(d * SR))
def mtof(m): return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)
def bp(x, lo, hi, o=2): return signal.sosfilt(signal.butter(o, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'lowpass', fs=SR, output='sos'), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, 'highpass', fs=SR, output='sos'), x)
def pink(N):
    X = np.fft.rfft(R.standard_normal(N)); f = np.arange(len(X)); f[0] = 1
    return np.fft.irfft(X / np.sqrt(f), N)

class Mix:
    """buffer estéreo com cauda; enrola a cauda no começo (loop perfeito)"""
    def __init__(self, dur, cauda=3.0): self.dur = dur; self.x = np.zeros((2, n(dur + cauda)))
    def add(self, t, sig, g=1.0, pan=0.0):
        i = n(t % self.dur); j = min(self.x.shape[1], i + len(sig)); s = sig[: j - i] * g
        self.x[0, i:j] += s * np.sqrt((1 - pan) / 2); self.x[1, i:j] += s * np.sqrt((1 + pan) / 2)
    def final(self):
        N = n(self.dur); y = self.x[:, :N].copy(); c = self.x[:, N:]
        while c.shape[1]: k = min(N, c.shape[1]); y[:, :k] += c[:, :k]; c = c[:, k:]
        return y

def violao(m, d=2.2, brilho=.5):
    """Karplus-Strong (corda de nylon): pulso filtrado num laço de atraso com perda"""
    f = float(mtof(m)); N = int(SR / f); L = n(d)
    exc = np.zeros(L); exc[:N] = lp(R.uniform(-1, 1, N), 1200 + 3000 * brilho)
    a = np.zeros(N + 2); a[0] = 1; a[N] = a[N + 1] = -.4985
    y = signal.lfilter([1], a, exc)
    y = lp(y, 2600) * np.exp(-np.arange(L) / (SR * d * .45))
    return y / (np.max(np.abs(y)) + 1e-9)

def baixo(m, d=.9):
    t = np.arange(n(d)) / SR; f = float(mtof(m))
    y = np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)
    return y * np.minimum(1, t / .01) * np.exp(-t / .35)

def sino(f, d=1.2, idx=2.5, ratio=3.01):
    t = np.arange(n(d)) / SR
    return np.sin(2 * np.pi * f * t + idx * np.exp(-t / .15) * np.sin(2 * np.pi * f * ratio * t)) * np.exp(-t / .35) * np.minimum(1, t / .002)

def main(nome):
    pasta = glob.glob(f'videos/{nome}*')[0]; nome = os.path.basename(pasta)
    C = json.load(open(f'{pasta}/cues.json')); dur = C['dur']; mus = C.get('music') or {}
    bpm = mus.get('bpm', C.get('bpm') or 96); b = 60 / bpm; G = {'bossa': 1, 'salao': 1, 'chapa': 1, 'panela': 1, 'louca': 1, **mus.get('ganho', {})}
    M = Mix(dur)
    # ── bossa: ii-V (Dm9 → G13) em 2 compassos, levada sincopada em colcheias
    acordes = mus.get('acordes', [[50, 53, 57, 60, 64], [43, 53, 57, 59, 64]])
    batidas = int(round(dur / b)); comp = max(1, batidas // len(acordes))
    levada = mus.get('levada', [0, 1.5, 2.5, 3.5])                       # ataques (em batidas) dentro de cada acorde
    for k, ac in enumerate(acordes):
        t0 = k * comp * b
        M.add(t0, baixo(ac[0] - 12 if ac[0] > 48 else ac[0]), .32 * G['bossa'])
        M.add(t0 + 2 * b, baixo(ac[0] - 5 if ac[0] > 48 else ac[0] + 7), .22 * G['bossa'])
        for p in [x for x in levada if x < comp]:
            for i, m in enumerate(ac[1:]):
                M.add(t0 + p * b + i * .012, violao(m, 1.6, .35 + .1 * (p % 1 > 0)), .07 * G['bossa'], pan=-.25 + .12 * i)
    # ── salão: murmúrio de conversa
    N = n(dur) + n(3); t = np.arange(N) / SR
    mur = bp(pink(N), 280, 2400, 2)
    env = .55 + .45 * np.abs(np.sin(2 * np.pi * 4.3 * t + 3 * np.sin(2 * np.pi * .41 * t))) * (.6 + .4 * np.sin(2 * np.pi * .23 * t + 1))
    mur = mur * env; mur /= np.max(np.abs(mur)) + 1e-9
    M.add(0, mur, .16 * G['salao'], pan=-.1); M.add(dur * .5, mur[::-1].copy(), .12 * G['salao'], pan=.3)
    # ── chapa: chiado com estalos
    chi = hp(R.standard_normal(N), 3500, 2) * (.7 + .3 * np.sin(2 * np.pi * .8 * t)); chi /= np.max(np.abs(chi))
    est = np.zeros(N); idx = R.integers(0, N, int(dur * 38)); est[idx] = R.uniform(.3, 1, len(idx)); est = hp(est, 2500)
    M.add(0, chi * .5 + est * .6, .07 * G['chapa'], pan=.35)
    # ── panela: borbulhas graves
    for k in range(int(dur * 5)):
        tb = R.uniform(0, dur); d = .09; tt = np.arange(n(d)) / SR; f = R.uniform(110, 240)
        M.add(tb, np.sin(2 * np.pi * f * (1 + 2.5 * tt) * tt) * np.exp(-tt / .025), .09 * G['panela'], pan=-.2)
    # ── louça e caixa
    for tb, f, g in [(.9, 2350, .05), (2.15, 2900, .04), (3.4, 2600, .05), (4.3, 3300, .035)]:
        M.add(tb, sino(f, .6, 1.6, 2.76), g * G['louca'], pan=R.uniform(-.5, .5))
    M.add(2.5, sino(1568, 1.3, 1.2, 2.0) + .6 * sino(2093, 1.3, 1.0, 2.0), .06 * G['louca'], pan=.4)
    y = M.final()
    y = hp(y, 40); rms = np.sqrt(np.mean(y ** 2)); y *= 10 ** (-19 / 20) / (rms + 1e-9)
    pk = np.max(np.abs(y)); y = np.tanh(y * 1.1) / np.tanh(1.1) if pk > .9 else y
    y *= .89 / max(.89, np.max(np.abs(y)))
    f = np.minimum(1, np.arange(y.shape[1]) / n(.02)); y *= np.minimum(f, f[::-1])   # micro-fade contra clique
    wavfile.write(f'audio/{nome}.wav', SR, (y.T * 32767).astype(np.int16))
    print('audio', f'audio/{nome}.wav', f'{dur}s', 'rms -19 dBFS')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '01')
