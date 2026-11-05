# Trilha do estilo "peças de montar": milhares de cliques de plástico sintetizados (um por peça, lidos de cues.json),
# chacoalhar ao sair do monte, estalos ao soltar, chocalhar ao cair no monte, motor a ar, buzina, interruptor de farol, whoosh do estouro
# e uma marimba leve em loop. Tudo em numpy, determinístico, e EM LOOP (o que passa do fim volta para o começo).
# uso: python3 <skill>/scripts/som.py <pasta-do-projeto> 01   (lê videos/01-*/cues.json → grava audio/01-*.wav)
import json, sys, glob, os, wave
import numpy as np
from scipy.signal import butter, sosfilt, lfilter, resample_poly

SR = 48000
pref = sys.argv[1] if len(sys.argv) > 1 else '01'
pasta = sorted(d for d in glob.glob(f'videos/{pref}*') if os.path.exists(f'{d}/cues.json'))[0]
nome = os.path.basename(pasta)
C = json.loads(open(f'{pasta}/cues.json', encoding='utf-8').read())
DUR = C['dur']; N = int(round(DUR * SR)); BPM = C.get('bpm') or 120
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)

def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f / (SR / 2), 'low', output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f / (SR / 2), 'high', output='sos'), x)

def por(t0, x, g=1.0, pan=0.0):
    """soma x em (L, R) a partir de t0 (s), com pan de potência constante e volta ao início (loop)"""
    i0 = int(round(t0 * SR)) % N; n = len(x)
    a = (pan + 1) * np.pi / 4; gl, gr = np.cos(a) * g, np.sin(a) * g
    idx = (i0 + np.arange(n)) % N
    np.add.at(L, idx, x * gl); np.add.at(R, idx, x * gr)

def clique(tam=2, mat='abs', suave=False):
    """encaixe de peça: estalo curto + ressonância do plástico; peça maior = mais grave; vidro mais agudo; borracha abafada"""
    n = int(.05 * SR); t = np.arange(n) / SR
    base = 3300 / (max(tam, 1) ** .22) * (1 + .18 * (rng.random() - .5))
    if mat == 'vidro': base *= 1.35
    if mat == 'metal': base *= 1.15
    f2 = 760 + 420 * rng.random()
    tick = rng.standard_normal(n) * np.exp(-t / .0007)
    corpo = (np.sin(2 * np.pi * base * t + rng.random() * 6) * np.exp(-t / .0055)
             + .55 * np.sin(2 * np.pi * base * 1.71 * t) * np.exp(-t / .0035)
             + .5 * np.sin(2 * np.pi * f2 * t) * np.exp(-t / .011))
    x = .7 * hp(tick, 1500) + corpo
    if mat == 'borracha': x = lp(.5 * tick + np.sin(2 * np.pi * 220 * t) * np.exp(-t / .03), 900) * 1.6
    if suave: x = lp(x, 2600)
    return x

def chocalho(tam=2, mat='abs'):
    """peça caindo no monte: 2–3 batidinhas abafadas"""
    out = np.zeros(int(.12 * SR)); p = 0
    for k in range(1 + int(rng.integers(1, 3))):
        c = clique(tam * 1.6, mat, suave=True) * (.8 ** k)
        out[p:p + len(c)] += c[:len(out) - p]; p += int((.018 + .03 * rng.random()) * SR)
        if p >= len(out) - 10: break
    return out

def motor(dur=.5):
    """motor a ar: pulsos graves ~28 Hz com ronco de escape, sobe e assenta"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 26 + 22 * np.exp(-((t - .12) / .09) ** 2) + 4 * t / dur
    fase = 2 * np.pi * np.cumsum(f) / SR
    pulso = np.maximum(0, np.sin(fase)) ** 6
    ruido = lp(rng.standard_normal(n), 380) * 3
    x = pulso * (ruido + .8 * np.sin(fase * 2)) + .25 * np.sin(fase)
    env = np.minimum(1, t / .04) * np.minimum(1, (dur - t) / .12)
    return lp(x * env, 900) * .9

def buzina():
    """bi-bi: duas notas quadradas suavizadas (sem marca nenhuma)"""
    parts = []
    for d, g in [(.11, 1), (.06, 0), (.16, 1)]:
        n = int(d * SR); t = np.arange(n) / SR
        x = (np.sign(np.sin(2 * np.pi * 415 * t)) + .7 * np.sign(np.sin(2 * np.pi * 523 * t))) * g
        parts.append(x * np.minimum(1, t / .006) * np.minimum(1, (d - t) / .01))
    return bp(np.concatenate(parts), 300, 3200) * .35

def whoosh(dur=.55):
    dur = max(.1, dur)
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); out = np.zeros(n); seg = 1024
    for i in range(0, n, seg):
        k = i / n; out[i:i + seg] = bp(x[i:i + seg], 300 + 2800 * k, 900 + 5200 * k)[:min(seg, n - i)]
    return out * np.sin(np.pi * t / dur) ** 1.5 * .9

def interruptor():
    n = int(.03 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n) * np.exp(-t / .0015), 900) * .8 + np.sin(2 * np.pi * 1900 * t) * np.exp(-t / .004) * .4

# ── eventos ──
for c in C['cues']:
    ty, t0 = c['type'], c['t']; pan = c.get('pan', 0); g = c.get('g', 1)
    tam, mat = c.get('tam', 2), c.get('mat', 'abs')
    if ty == 'clique': por(t0, clique(tam, mat), .30 * g * (.75 + .5 * rng.random()), pan)
    elif ty == 'sai': por(t0, chocalho(tam * .8, mat), .09 * g * (.6 + .8 * rng.random()), pan)
    elif ty == 'solta': por(t0, clique(tam * .7, mat), .16 * g, pan)
    elif ty == 'cai': por(t0, chocalho(tam, mat), .2 * g * (.7 + .6 * rng.random()), pan)
    elif ty == 'motor': por(t0, motor(c.get('dur', .5)), .9, 0)
    elif ty == 'buzina': por(t0, buzina(), .8, .25)
    elif ty == 'whoosh': por(t0, whoosh(c.get('dur', .55)), .55 * g, 0)
    elif ty == 'farol': por(t0, interruptor(), .35, .3)

# ── marimba leve em loop (pentatônica, colcheias) ──
beat = 60 / BPM; nota = lambda m: 440 * 2 ** ((m - 69) / 12)
seq = [72, 76, 79, 84, 79, 76, 74, 79, 72, 76, 81, 79, 76, 74, 72, 67, 69, 72, 76, 74]
passo = beat / 2
for i in range(int(DUR / passo)):
    m = seq[i % len(seq)]; f = nota(m); n = int(.5 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / .22) + .25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / .03)) * np.minimum(1, t / .002)
    por(i * passo, x, .11 * (1.2 if i % 4 == 0 else .9), .3 * np.sin(i))
for i in range(int(DUR / beat)):                                        # baixo macio no tempo
    f = nota([48, 48, 53, 55][(i // 2) % 4]); n = int(.4 * SR); t = np.arange(n) / SR
    por(i * beat, np.sin(2 * np.pi * f * t) * np.exp(-t / .16) * np.minimum(1, t / .005), .16, 0)

# ── ambiente de rua (ruído grave bem baixo, em loop) ──
amb = lp(rng.standard_normal(N), 500) * .02
amb = amb * (1 - np.linspace(0, 1, N)) + np.roll(amb, N // 2) * np.linspace(0, 1, N)
L += amb; R += np.roll(amb, 997)

# ── master: passa-alta, loudness −14 LUFS (BS.1770, K-weighting) e limitador de pico verdadeiro a −1,5 dBTP ──
def lufs(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, .73248077421585]
    b2, a2 = [1., -2., 1.], [1, -1.99004745483398, .99007225036621]
    k = [lfilter(b2, a2, lfilter(b1, a1, c)) for c in x]
    return -.691 + 10 * np.log10(sum(np.mean(c ** 2) for c in k) + 1e-12)
def pico_db(x): return 20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=1)).max() + 1e-12)   # pico verdadeiro (4× sobreamostrado)
ALVO, TETO = -14.0, -2.0                                 # teto 0,5 dB abaixo de −1,5 dBTP: margem para o AAC
st = np.stack([hp(L, 35), hp(R, 35)])
lim = 10 ** (TETO / 20)
for _ in range(6):                                       # ganho → clip suave (tanh) no teto → re-mede
    st *= 10 ** ((ALVO - lufs(st)) / 20)
    st = lim * np.tanh(st / lim)
st *= min(1, 10 ** ((TETO - pico_db(st)) / 20))
print(f'loudness {lufs(st):.1f} LUFS · pico verdadeiro {pico_db(st):.1f} dBTP')
pcm = (st.T * 32767).astype('<i2')
with wave.open(f'audio/{nome}.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f'audio/{nome}.wav', f'{DUR:.2f}s', len(C['cues']), 'eventos')
