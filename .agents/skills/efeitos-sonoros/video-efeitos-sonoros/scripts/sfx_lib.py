#!/usr/bin/env python3
"""sfx_lib.py: biblioteca de efeitos sonoros sintetizada do zero em numpy (sem amostra de terceiros).

Estética "elegante": transientes macios (ataque em cosseno de 2 a 8 ms), energia entre 150 Hz e 3 kHz, nada
de chiado acima de 6 kHz, efeitos tonais afinados no tom da trilha (padrão Ré maior) e uma sala pequena comum a
todos, para soarem como uma família. Estéreo só por nível (mono-safe, sem delay Haas).

Nível: o PICO de cada arquivo é o destino absoluto dentro da mix final a −14 LUFS, em que a fala tem RMS mediano
de −16,4 dBFS. Na timeline, use os efeitos a 0 dB; o posicionar.py corrige pelo nível real da voz.

Uso:
  python3 sfx_lib.py --saida som/sfx                       gera a biblioteca inteira + manifest.json + _amostra.wav
  python3 sfx_lib.py --saida som/sfx --so zoom_in,papel    só alguns
  python3 sfx_lib.py --saida som/sfx --tom A               afina os tonais em Lá (padrão: D)
  python3 sfx_lib.py --saida som/sfx --extra som/receitas_extra.py   inclui receitas novas escritas no projeto
  python3 sfx_lib.py --listar                              nomes, classe e uso
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio import FALA_REF, SR, gravar, ler  # noqa: E402

# ───────────────────────────────────────────────────────────── afinação ──
NOTAS = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7,
         "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
_BASE = {"D3": 146.83, "A3": 220.0, "D4": 293.66, "E4": 329.63, "FS4": 369.99, "A4": 440.0, "B4": 493.88,
         "D5": 587.33, "E5": 659.26, "FS5": 739.99, "A5": 880.0, "B5": 987.77, "D6": 1174.66, "FS6": 1479.98,
         "A6": 1760.0}
D3 = A3 = D4 = E4 = FS4 = A4 = B4 = D5 = E5 = FS5 = A5 = B5 = D6 = FS6 = A6 = 0.0


def afinar(tom="D"):
    """Transpõe as notas dos efeitos tonais (escritas em Ré maior) para `tom`, no máximo ±6 semitons."""
    k = (NOTAS[tom.upper().replace("♯", "#")] - 2) % 12
    k = k - 12 if k > 6 else k
    g = globals()
    for nome, f in _BASE.items():
        g[nome] = f * 2 ** (k / 12)
    return k


afinar("D")


# ──────────────────────────────────────────────────────────────── DSP ──
def tempo(dur):
    return np.arange(int(round(dur * SR))) / SR


def ruido(n, rng, cor="branco"):
    x = rng.standard_normal(n)
    if cor == "branco":
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    X /= np.sqrt(f) if cor == "rosa" else f
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-12)


def mascara(freqs, lo, hi, slope):
    """1 dentro de [lo, hi]; borda em cosseno de `slope` oitavas fora (escala log2)."""
    lf = np.log2(np.maximum(freqs, 1.0))
    m = np.ones_like(freqs)
    for d in (np.log2(lo) - lf, lf - np.log2(hi)):
        k = d > 0
        m[k] *= np.where(d[k] < slope, 0.5 * (1 + np.cos(np.pi * d[k] / slope)), 0.0)
    return m


def banda(x, lo, hi, slope=0.35):
    """Passa-faixa fixo pela FFT do sinal inteiro."""
    X = np.fft.rfft(x) * mascara(np.fft.rfftfreq(len(x), 1 / SR), lo, hi, slope)
    return np.fft.irfft(X, len(x))


def stft_filter(x, lo_fn, hi_fn, nfft=1024, slope_oct=0.35):
    """Passa-faixa variável no tempo por STFT (Hann, hop nfft/2), overlap-add dividido por Σwin²."""
    lo_f = lo_fn if callable(lo_fn) else (lambda _t, v=lo_fn: v)
    hi_f = hi_fn if callable(hi_fn) else (lambda _t, v=hi_fn: v)
    hop = nfft // 2
    win = np.hanning(nfft + 1)[:-1]
    xp = np.concatenate([np.zeros(nfft), x, np.zeros(nfft)])
    out, norm = np.zeros_like(xp), np.zeros_like(xp)
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    for i in range(0, len(xp) - nfft + 1, hop):
        tc = (i + nfft / 2 - nfft) / SR
        m = mascara(freqs, lo_f(tc), hi_f(tc), slope_oct)
        out[i:i + nfft] += np.fft.irfft(np.fft.rfft(xp[i:i + nfft] * win) * m, nfft) * win
        norm[i:i + nfft] += win * win
    norm[norm < 1e-6] = 1.0
    return (out / norm)[nfft:nfft + len(x)]


def convolve(a, b):
    n = len(a) + len(b) - 1
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, nf) * np.fft.rfft(b, nf), nf)[:n]


def subida(n, amostras):
    """Rampa de ataque em cosseno levantado (sem clique)."""
    e = np.ones(n)
    k = min(n, max(1, int(amostras)))
    e[:k] = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    return e


def sobe_desce(t, dur, pico, exp_desce=1.5):
    """Envelope em sino assimétrico: sin² até `pico` (fração da duração), cosseno até o fim."""
    tp = pico * dur
    return np.where(t < tp, np.sin(0.5 * np.pi * np.clip(t / tp, 0, 1)) ** 2,
                    np.cos(0.5 * np.pi * np.clip((t - tp) / (dur - tp), 0, 1)) ** exp_desce)


def seno_glide(t, f_fn):
    return np.sin(2 * np.pi * np.cumsum(f_fn(t)) / SR)


def svf_passa_baixa(x, fc, q=0.707):
    """Filtro de estado variável (TPT), passa-baixa com corte variável por amostra."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    g = np.tan(np.pi * np.clip(fc, 20, SR * 0.45) / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    a2, a3 = g * a1, g * g * a1
    y = np.empty_like(x)
    ic1 = ic2 = 0.0
    for i in range(len(x)):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1, ic2 = 2 * v1 - ic1, 2 * v2 - ic2
        y[i] = v2
    return y


def varre_lados(n, de_esq=True, abertura=0.25):
    """Panorâmica de nível que atravessa a tela: L 1,0→0,75 e R 0,75→1,0 (≈2,5 dB)."""
    s = np.linspace(0, 1, n)
    s = s * s * (3 - 2 * s)
    if not de_esq:
        s = 1 - s
    return 1 - abertura * s, (1 - abertura) + abertura * s


def lp(x, fc, slope=1.0):
    """Passa-baixa suave (borda em cosseno de `slope` oitavas acima de fc); tira também o DC."""
    pad = 4096
    xp = np.concatenate([np.zeros(pad), np.asarray(x, dtype=float), np.zeros(pad)])
    return banda(xp, 25, fc, slope)[pad:pad + len(x)]


def env(t, ataque, tau):
    """Ataque em cosseno (2 a 8 ms) e decaimento exponencial."""
    return subida(len(t), ataque * SR) * np.exp(-np.maximum(t - ataque, 0) / tau)


def mono2(x, gl=1.0, gr=1.0):
    return np.stack([x * gl, x * gr], axis=1)


def em(t_total, *partes):
    """Soma partes [(início_s, sinal)] num buffer mono."""
    y = np.zeros(int(t_total * SR))
    for ini, s in partes:
        i = int(ini * SR)
        j = min(len(y), i + len(s))
        y[i:j] += s[:j - i]
    return y


def _ir_sala():
    """Placa pequena comum a toda a biblioteca: 0,45 s, 180 Hz–3,5 kHz, L e R 80% comuns."""
    dur = 0.45
    n = int(dur * SR)
    t = np.arange(n) / SR
    caida = np.exp(-6.9 * t / dur)
    pre = int(0.007 * SR)
    com = banda(np.random.default_rng(777).standard_normal(n), 180, 3500, 1.0) * caida
    irs = []
    for semente, atrasos in ((1, (0.011, 0.019, 0.027)), (2, (0.013, 0.021, 0.031))):
        ind = banda(np.random.default_rng(semente).standard_normal(n), 180, 3500, 1.0) * caida
        ir = np.concatenate([np.zeros(pre), com + 0.5 * ind])
        for k, a in enumerate(atrasos):                       # primeiras reflexões, macias
            i = int(a * SR)
            ir[i:i + 64] += (0.5 - 0.12 * k) * np.hanning(64) * 0.08
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    return irs


SALA = _ir_sala()


def com_sala(st, mix):
    """Soma a sala comum (alimentada pela soma mono) ao som estéreo seco."""
    st = np.asarray(st, dtype=float)
    if st.ndim == 1:
        st = mono2(st)
    m = st.mean(axis=1)
    n = len(st) + len(SALA[0])
    out = np.zeros((n, 2))
    out[:len(st)] = st
    ref = np.sqrt(np.mean(m ** 2)) + 1e-12
    for ch in range(2):
        w = convolve(m, SALA[ch])[:n]
        w *= ref / (np.sqrt(np.mean(w[:len(st)] ** 2)) + 1e-12)
        out[:len(w), ch] += mix * w
    return out


def finalizar(x, pico_db):
    """Corta o rabo abaixo de −70 dB do pico, fade de 3 ms no início e 25 ms no fim (começa e termina em
    zero), normaliza pelo pico e satura em ±1. Ordem obrigatória: fade → normaliza → clip."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = mono2(x)
    a = np.max(np.abs(x), axis=1)
    ult = int(np.nonzero(a > a.max() * 10 ** (-70 / 20))[0][-1]) + 1
    x = x[:min(len(x), ult + int(0.01 * SR))].copy()
    fi, fo = int(0.003 * SR), int(0.025 * SR)
    x[:fi] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(fi) / fi))[:, None]
    x[-fo:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(1, fo + 1) / fo))[:, None]
    x *= 10 ** (pico_db / 20) / (np.max(np.abs(x)) + 1e-12)
    return np.clip(x, -1, 1)


# ──────────────────────────────────────────────────── vozes da família ──
def thock(t, f0, tau=0.014, corpo=None, tau_corpo=0.03, sopro=0.2, ataque=0.0025, semente=0):
    """Madeira ou plástico macio: modos de barra livre (1; 2,76; 5,4), corpo grave opcional e um sopro de ruído
    abaixo de 1,4 kHz. Ataque em cosseno: nada de clique."""
    r = np.random.default_rng(semente)
    y = (np.sin(2 * np.pi * f0 * t) * np.exp(-t / tau)
         + 0.3 * np.sin(2 * np.pi * 2.76 * f0 * t) * np.exp(-t / (tau / 2.5))
         + 0.08 * np.sin(2 * np.pi * 5.4 * f0 * t) * np.exp(-t / (tau / 5)))
    if corpo:
        y += 0.7 * np.sin(2 * np.pi * corpo * t) * np.exp(-t / tau_corpo)
    nz = banda(r.standard_normal(len(t)), 150, 1400, 0.8)
    y += sopro * nz / (np.std(nz) + 1e-12) * np.exp(-t / 0.006)
    return y * subida(len(t), ataque * SR)


def malho(t, f, tau, indice=0.3, razao=4.0, ataque=0.003):
    """Sino/marimba suave: senoide com FM de índice baixo que some em 30 ms."""
    i = indice * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * f * t + i * np.sin(2 * np.pi * razao * f * t)) * env(t, ataque, tau)


def ar(dur, fc_fn, pico, corpo=0.5, semente=1, de_esq=True, tom=None, mix_sala=0.12, exp_desce=1.6):
    """Whoosh elegante: ar (ruído rosa) com passa-baixa varrendo (corte ≤ 3 kHz), corpo grave e, se pedido,
    um glide tonal suave."""
    r = np.random.default_rng(semente)
    t = tempo(dur)
    n = len(t)
    y = stft_filter(ruido(n, r, "rosa"), 70, lambda tt: min(fc_fn(tt), 3000.0), nfft=1024, slope_oct=0.9)
    y /= np.std(y) + 1e-12
    grave = banda(ruido(n, r, "marrom"), 60, 380, 0.8)
    y += corpo * grave / (np.std(grave) + 1e-12)
    if tom is not None:
        f_fn, m = tom
        y += m * 3.0 * seno_glide(t, f_fn)
    y *= sobe_desce(t, dur, pico, exp_desce)
    y = lp(y, 2800, 1.0)
    gl, gr = varre_lados(n, de_esq)
    return com_sala(mono2(y, gl, gr), mix_sala)


def exp_glide(a, b, d):
    return lambda tt: a * (b / a) ** np.clip(tt / d, 0, 1)


# ──────────────────────────────────────────────────────────── receitas ──
def fx_whoosh_curto():
    return ar(0.36, lambda tt: 450 * (2600 / 450) ** np.sin(0.5 * np.pi * min(tt / 0.2, 1.0)), 0.42, semente=11)


def fx_whoosh_longo():
    d = 0.72

    def fc(tt):
        u = np.clip(tt / d, 0, 1)
        return 260 * (3000 / 260) ** np.sin(0.5 * np.pi * min(u / 0.55, 1.0)) * (1 - 0.6 * max(u - 0.55, 0) / 0.45)
    return ar(d, fc, 0.55, corpo=0.8, semente=12, de_esq=False, mix_sala=0.16)


def fx_swish(variante):
    if variante == "a":
        return ar(0.21, exp_glide(650, 2400, 0.21), 0.6, corpo=0.35, semente=34, mix_sala=0.1)
    if variante == "b":
        return ar(0.23, exp_glide(2400, 600, 0.23), 0.3, corpo=0.35, semente=35, de_esq=False, mix_sala=0.1)
    d = 0.27

    def fc(tt):
        u = np.clip(tt / d, 0, 1)
        return 500 * (2000 / 500) ** np.sin(0.5 * np.pi * min(u / 0.55, 1.0)) * (1 - 0.45 * max(u - 0.55, 0) / 0.45)
    return ar(d, fc, 0.5, corpo=0.35, semente=36, mix_sala=0.1)


def fx_whip():
    d = 0.3

    def fc(tt):
        u = np.clip(tt / d, 0, 1)
        return 380 * (3000 / 380) ** min(u / 0.36, 1.0) * (1 - 0.75 * max(u - 0.36, 0) / 0.64)
    return ar(d, fc, 0.36, corpo=0.6, semente=37, mix_sala=0.1, exp_desce=1.2)


def fx_zoom_in():
    return ar(0.5, exp_glide(400, 2800, 0.5), 0.8, corpo=0.4, semente=13, tom=(exp_glide(D4, A4, 0.5), 0.22))


def fx_zoom_out():
    return ar(0.5, exp_glide(2800, 400, 0.5), 0.2, corpo=0.4, semente=14, de_esq=False,
              tom=(exp_glide(A4, D4, 0.5), 0.22))


def fx_slam():
    r = np.random.default_rng(33)
    t = tempo(0.7)
    f = 54 + 62 * np.exp(-t / 0.028)                        # 116 → 54 Hz
    sub = np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.003, 0.17)) / np.tanh(1.5)
    madeira = (0.30 * np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.035)
               + 0.14 * np.sin(2 * np.pi * 580 * t) * np.exp(-t / 0.018)
               + 0.05 * np.sin(2 * np.pi * 1150 * t) * np.exp(-t / 0.009)) * subida(len(t), 0.002 * SR)
    feltro = banda(r.standard_normal(len(t)), 120, 900, 0.8)
    feltro = feltro / np.std(feltro) * env(t, 0.003, 0.012) * 0.08
    return com_sala(mono2(lp(sub + madeira + feltro, 2400, 1.0)), 0.08)


def fx_impacto():
    r = np.random.default_rng(25)
    t = tempo(1.4)
    f = 44 + 44 * np.exp(-t / 0.09)                         # 88 → 44 Hz
    boom = np.tanh(1.3 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.004, 0.38)) / np.tanh(1.3)
    nota = (0.30 * malho(t, D4, 0.55, indice=0.25, razao=2.0, ataque=0.006)
            + 0.24 * malho(t, D3, 0.65, indice=0.2, razao=2.0, ataque=0.006)
            + 0.10 * malho(t, A4, 0.45, indice=0.2, razao=2.0, ataque=0.006))
    feltro = banda(r.standard_normal(len(t)), 100, 700, 0.8)
    feltro = feltro / np.std(feltro) * env(t, 0.004, 0.02) * 0.06
    return com_sala(mono2(lp(boom + nota + feltro, 2600, 1.0)), 0.16)


def fx_pop():
    t = tempo(0.16)
    f = exp_glide(300, E5, 0.045)
    y = seno_glide(t, f) * env(t, 0.003, 0.042) + 0.08 * seno_glide(t, lambda tt: 2 * f(tt)) * env(t, 0.003, 0.025)
    return com_sala(mono2(lp(y, 2500, 1.0)), 0.08)


def fx_tick():
    return com_sala(mono2(lp(thock(tempo(0.09), D6, tau=0.011, sopro=0.1, ataque=0.002, semente=21), 3000, 1.0)), 0.08)


def fx_clique():
    t1 = tempo(0.1)
    y = em(0.16, (0.0, thock(t1, A5, tau=0.012, corpo=210, tau_corpo=0.022, sopro=0.25, semente=23)),
           (0.05, 0.38 * thock(t1, 1050, tau=0.009, sopro=0.15, semente=24)))
    return com_sala(mono2(lp(y, 2800, 1.0)), 0.08)


TECLAS = {1: (620, 215, 0.03), 2: (700, 245, 0.03), 3: (560, 190, 0.03), 4: (480, 140, 0.045)}


def tecla(k, semente):
    f0, corpo, tc = TECLAS[k]
    t = tempo(0.12)
    solta = 0.05 if k == 4 else 0.036
    return em(0.16, (0.0, thock(t, f0, tau=0.012, corpo=corpo, tau_corpo=tc, sopro=0.3, semente=semente)),
              (solta, 0.2 * thock(t, f0 * 1.1, tau=0.008, sopro=0.2, semente=semente + 1)))


def fx_tecla(k):
    return com_sala(mono2(lp(tecla(k, 50 + 2 * k), 2200, 1.0)), 0.06)


def fx_digitacao_suave():
    r = np.random.default_rng(24)
    dur = 2.0
    L = np.zeros(int(dur * SR))
    R = np.zeros_like(L)
    pos, k = 0.05, 0
    while pos < dur - 0.14:
        som = tecla(4 if k % 6 == 5 else int(r.integers(1, 4)), 60 + k)
        amp = r.uniform(0.55, 1.0)
        i = int(pos * SR)
        j = min(len(L), i + len(som))
        L[i:j] += amp * r.uniform(0.85, 1.0) * som[:j - i]
        R[i:j] += amp * r.uniform(0.85, 1.0) * som[:j - i]
        pos += 0.075 + r.exponential(0.045) + (0.16 if r.random() < 0.08 else 0.0)
        k += 1
    return com_sala(np.stack([lp(L, 2200, 1.0), lp(R, 2200, 1.0)], axis=1), 0.06)


def fx_contador():
    dur = 1.2
    t1 = tempo(0.05)
    instantes, pos = [], 0.0
    while pos < dur - 0.04:
        instantes.append(pos)
        pos += 0.034 + 0.075 * (pos / dur) ** 1.5           # desacelera (ease-out)
    partes = [(ini, 10 ** (-9 * (k / max(1, len(instantes) - 1)) / 20)
               * thock(t1, A5, tau=0.008, sopro=0.12, ataque=0.002, semente=70 + k)) for k, ini in enumerate(instantes)]
    return com_sala(mono2(lp(em(dur + 0.05, *partes), 2800, 1.0)), 0.08)


def fx_numero_tick_rapido():
    dur, t1 = 0.8, tempo(0.03)
    partes, ini, k = [], 0.0, 0
    while ini < dur - 0.03:
        nivel = 10 ** (-9 * ini / dur / 20) * (0.85 if k % 2 else 1.0)
        partes.append((ini, nivel * thock(t1, B5, tau=0.006, sopro=0.1, ataque=0.002, semente=90 + k)))
        ini += 0.033
        k += 1
    return com_sala(mono2(lp(em(dur + 0.03, *partes), 2800, 1.0)), 0.06)


def fx_ui_hover():
    t = tempo(0.16)
    f = exp_glide(FS5, A5, 0.06)
    y = seno_glide(t, f) * env(t, 0.008, 0.05) + 0.04 * seno_glide(t, lambda tt: 2 * f(tt)) * env(t, 0.008, 0.03)
    return com_sala(mono2(lp(y, 2500, 1.0)), 0.1)


def fx_ui_toggle():
    t = tempo(0.25)
    y = em(0.3, (0.0, thock(t, 620, tau=0.012, corpo=180, tau_corpo=0.02, sopro=0.2, semente=40)),
           (0.035, 0.6 * malho(t, A5, 0.06, indice=0.2, razao=2.0, ataque=0.003)))
    return com_sala(mono2(lp(y, 2800, 1.0)), 0.08)


def fx_blip():
    t = tempo(0.5)
    y = em(0.55, (0.0, malho(t, A5, 0.16, indice=0.3)), (0.05, 0.85 * malho(t, D6, 0.2, indice=0.3)))
    return com_sala(mono2(lp(y, 3500, 1.0)), 0.14)


def fx_sparkle():
    t = tempo(0.6)
    y = em(0.75, (0.0, 0.8 * malho(t, D6, 0.25, indice=0.2, razao=2.0)),
           (0.055, 0.7 * malho(t, FS6, 0.25, indice=0.2, razao=2.0)),
           (0.11, 0.6 * malho(t, A6, 0.3, indice=0.2, razao=2.0)))
    y = lp(y, 3800, 1.0)
    gl, gr = varre_lados(len(y), abertura=0.2)
    return com_sala(mono2(y, gl, gr), 0.2)


def _chk(t, f0, semente, amp):
    nz = banda(np.random.default_rng(semente).standard_normal(len(t)), 300, 2200, 0.8)
    nz = nz / np.std(nz) * env(t, 0.002, 0.008) * 0.45
    return amp * (thock(t, f0, tau=0.010, corpo=150, tau_corpo=0.015, sopro=0.0, semente=semente) + nz)


def fx_shutter():
    t = tempo(0.1)
    y = em(0.2, (0.004, _chk(t, 520, 381, 1.0)), (0.075, _chk(t, 430, 382, 0.7)))
    return com_sala(mono2(lp(y, 2400, 1.0)), 0.08)


def fx_flash():
    """Flash de câmera / clarão branco: um sopro que cresce e abre num acorde de sino curto."""
    sopro = ar(0.24, exp_glide(300, 2600, 0.24), 0.96, corpo=0.25, semente=41, mix_sala=0.0, exp_desce=3.0)
    t = tempo(0.7)
    sino = (0.5 * malho(t, D5, 0.18, indice=0.2, razao=2.0) + 0.4 * malho(t, A5, 0.16, indice=0.2, razao=2.0)
            + 0.25 * malho(t, D6, 0.12, indice=0.2, razao=2.0))
    y = np.zeros((int(0.95 * SR), 2))
    y[:len(sopro)] += 0.8 * sopro / (np.max(np.abs(sopro)) + 1e-12)
    i = int(0.22 * SR)
    y[i:i + len(t)] += mono2(lp(sino, 3500, 1.0) * 0.9)[:len(y) - i]
    return com_sala(y, 0.18)


def fx_carimbo():
    """Carimbo: descida curta, batida de madeira com feltro na mesa e um "tss" de tinta abafado."""
    r = np.random.default_rng(57)
    t = tempo(0.5)
    desce = banda(r.standard_normal(len(t)), 300, 1200, 0.8) * np.clip(t / 0.03, 0, 1) * (t < 0.03) * 0.25
    u = np.clip(t - 0.03, 0, None)
    on = t > 0.03
    corpo = np.sin(2 * np.pi * np.cumsum(64 + 90 * np.exp(-u / 0.012)) / SR) * np.exp(-u / 0.08)
    madeira = (0.35 * np.sin(2 * np.pi * 240 * t) * np.exp(-u / 0.03) + 0.12 * np.sin(2 * np.pi * 690 * t) * np.exp(-u / 0.014))
    feltro = banda(r.standard_normal(len(t)), 150, 1200, 0.8)
    feltro = 0.25 * feltro / np.std(feltro) * np.exp(-u / 0.012)
    tinta = banda(r.standard_normal(len(t)), 900, 2600, 0.8)
    tinta = 0.06 * tinta / np.std(tinta) * np.exp(-np.clip(t - 0.07, 0, None) / 0.03) * (t > 0.07)
    y = desce + on * subida(len(t), 0.032 * SR) * (np.tanh(1.4 * corpo) + madeira + feltro) + tinta
    return com_sala(mono2(lp(y, 2600, 1.0)), 0.08)


def fx_riser(dur, semente):
    r = np.random.default_rng(semente)
    t = tempo(dur)
    n = len(t)
    fc = lambda tt: 200 * (2500 / 200) ** (np.clip(tt / dur, 0, 1) ** 1.2)  # noqa: E731
    ar_ = stft_filter(ruido(n, r, "rosa"), 80, fc, nfft=1024, slope_oct=0.9)
    ar_ /= np.std(ar_) + 1e-12
    pad = np.zeros(n)
    for f, a in ((D3, 1.0), (A3, 0.8), (D4, 0.7), (FS4, 0.55)):          # acorde do tom, harmônicos suaves
        for cents in (-5, 5):
            ff = f * 2 ** (cents / 1200)
            for h in range(1, 5):
                pad += a / h ** 2 * np.sin(2 * np.pi * h * ff * t + r.random() * 6.28)
    pad = stft_filter(pad, 60, fc, nfft=1024, slope_oct=1.0)
    pad /= np.std(pad) + 1e-12
    y = 0.6 * ar_ + 0.8 * pad
    e = (t / dur) ** 1.8
    k = int(0.06 * dur * SR)                               # arredonda o fim: sem pico agressivo
    e[-k:] *= 1 - 0.3 * (0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k))
    f = int(0.025 * SR)
    e[-f:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, f + 1) / f)
    y = lp(y * e, 2800, 1.0)
    gl, gr = varre_lados(n)
    return com_sala(mono2(y, gl, gr), 0.16)


def fx_glitch():
    """Tape-stop curto e abafado: uma nota com quinta cuja afinação cai a zero em 0,3 s."""
    d = 0.3
    t = tempo(d)
    queda = np.clip(1 - t / d, 0, 1) ** 1.5
    y = np.zeros(len(t))
    for f0, a in ((D4, 1.0), (A4, 0.5)):
        fase = 2 * np.pi * np.cumsum(f0 * queda) / SR
        for h in range(1, 6):
            y += a / h ** 2 * np.sin(h * fase)
    y *= subida(len(t), 0.004 * SR) * np.clip(1 - t / d, 0, 1) ** 0.8
    return com_sala(mono2(banda(y, 60, 1800, 1.0)), 0.08)


def fx_papel():
    r = np.random.default_rng(27)
    t = tempo(1.0)
    base = banda(ruido(len(t), r, "rosa"), 500, 3800, 0.6)
    base /= np.std(base)
    gesto = sum(a * np.exp(-0.5 * ((t - c) / s) ** 2) for c, s, a in ((0.14, 0.06, 0.9), (0.42, 0.09, 1.0), (0.74, 0.07, 0.7)))
    gran = banda(r.standard_normal(len(t)), 20, 140, 0.5)
    y = base * gesto * np.clip(1 + 0.6 * gran / np.std(gran), 0, None)
    estalos = np.zeros(len(t))
    for _ in range(26):
        c = r.uniform(0.05, 0.95)
        i, n = int(c * SR), int(0.008 * SR)
        g = banda(r.standard_normal(n), 1500, 3500, 0.5) * env(np.arange(n) / SR, 0.0015, 0.0015)
        estalos[i:i + n] += r.uniform(0.3, 1.0) * np.exp(-0.5 * ((c - 0.45) / 0.3) ** 2) * g[:len(t) - i]
    y = y + 0.6 * estalos / (np.max(np.abs(estalos)) + 1e-12) * np.max(np.abs(y))
    return com_sala(mono2(lp(y, 4200, 0.6), 1.0, 0.92), 0.08)


def fx_caneta():
    r = np.random.default_rng(28)
    dur = 1.0
    t = tempo(dur)
    atrito = banda(r.standard_normal(len(t)), 900, 3600, 0.6)
    atrito /= np.std(atrito)
    asp = banda(r.standard_normal(len(t)), 150, 700, 0.5)
    asp = np.clip(1 + 0.7 * asp / np.std(asp), 0, None)
    tracos = np.zeros(len(t))
    pos = 0.04
    while pos < dur - 0.08:
        comp = r.uniform(0.07, 0.19)
        k = (t >= pos) & (t < pos + comp)
        u = (t[k] - pos) / comp
        tracos[k] += r.uniform(0.6, 1.0) * np.sin(np.pi * u) ** 0.7 * (0.75 + 0.25 * np.sin(2 * np.pi * u * r.uniform(1.5, 3)))
        pos += comp + r.uniform(0.03, 0.07)
    return com_sala(mono2(lp(atrito * asp * tracos, 4000, 0.6)), 0.06)


def fx_fogo():
    r = np.random.default_rng(29)
    dur = 1.0
    t = tempo(dur)
    ronco = banda(ruido(len(t), r, "marrom"), 70, 900, 0.6)
    ronco /= np.std(ronco)
    ondula = banda(r.standard_normal(len(t)), 1, 6, 0.6)
    ronco *= 0.75 + 0.25 * ondula / (np.max(np.abs(ondula)) + 1e-12)
    estalos = np.zeros(len(t))
    for _ in range(r.poisson(30)):
        i = int(r.uniform(0, dur - 0.012) * SR)
        n = int(r.uniform(0.004, 0.009) * SR)
        lo = r.uniform(700, 1500)
        g = banda(r.standard_normal(n * 4), lo, min(lo * 2.2, 3600), 0.5)[:n] * env(np.arange(n) / SR, 0.0015, n / SR / 4)
        estalos[i:i + n] += min(r.pareto(2.2) + 0.25, 2.5) * g
    estalos /= np.max(np.abs(estalos)) + 1e-12
    y = 0.3 * ronco / np.max(np.abs(ronco)) + 0.75 * estalos
    return com_sala(mono2(lp(y, 3800, 0.6), 1.0, 0.94), 0.08)


def fx_sintetizador():
    dur = 2.0
    t = tempo(dur)
    f0 = D3 / 2

    def serra(f):
        s = np.zeros(len(t))
        for h in range(1, int(5000 / f) + 1):
            s += np.sin(2 * np.pi * h * f * t) / h
        return s * 2 / np.pi
    a, b = serra(f0), serra(f0 * 1.006)
    sub = 0.3 * np.sin(np.pi * f0 * t)
    fc = 180 * (2400 / 180) ** (np.sin(np.pi * t / dur) ** 1.4)
    e = subida(len(t), 0.08 * SR)
    rel = int(0.35 * SR)
    e[-rel:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, rel + 1) / rel)
    L = lp(svf_passa_baixa(a + 0.8 * b + sub, fc, q=1.6) * e, 4500, 0.8)
    R = lp(svf_passa_baixa(0.8 * a + b + sub, fc, q=1.6) * e, 4500, 0.8)
    return com_sala(np.stack([L, R], axis=1), 0.1)


# nome: (receita, pico alvo dBFS, classe, uso). classe: "alta" (marcante, tem prioridade), "media", "baixa" (miúdo:
# sai quando encosta em outro). corpo_s: só onde o fim do gesto importa (riser termina no corte: ancora "fim").
BIBLIOTECA = {
    "whoosh_curto":       (fx_whoosh_curto, -27.0, "media", "entrada de cartão, imagem, chip ou GC"),
    "whoosh_longo":       (fx_whoosh_longo, -24.0, "alta", "troca de tela, wipe, transição de assunto"),
    "swish_a":            (lambda: fx_swish("a"), -28.0, "media", "cartão curto subindo"),
    "swish_b":            (lambda: fx_swish("b"), -28.0, "media", "cartão curto descendo"),
    "swish_c":            (lambda: fx_swish("c"), -28.0, "media", "cartão que passa e volta"),
    "whip":               (fx_whip, -26.0, "media", "chicote de câmera (whip pan) entre telas"),
    "zoom_in":            (fx_zoom_in, -27.0, "alta", "zoom entrando num painel ou interface (tom sobe)"),
    "zoom_out":           (fx_zoom_out, -27.0, "alta", "zoom saindo (tom desce)"),
    "riser_1s":           (lambda: fx_riser(1.0, 31), -27.0, "alta", "subida de 1 s que termina no corte (ancora fim)"),
    "riser_2s":           (lambda: fx_riser(2.0, 32), -27.0, "alta", "subida de 2 s antes de troca de seção (ancora fim)"),
    "impacto":            (fx_impacto, -22.0, "alta", "impacto grave: abertura de capítulo, cartela, revelação"),
    "slam":               (fx_slam, -22.0, "alta", "palavra-chave que bate na tela: batida sub redonda, sem rabo"),
    "pop":                (fx_pop, -28.0, "media", "cartão ou chip que salta e assenta"),
    "blip":               (fx_blip, -28.0, "media", "ênfase: grifo, palavra em destaque"),
    "sparkle":            (fx_sparkle, -30.0, "media", "brilho curto de destaque (check, selo)"),
    "flash":              (fx_flash, -27.0, "alta", "flash de câmera ou clarão branco de transição"),
    "tick":               (fx_tick, -32.0, "baixa", "palavra que acende no tempo da fala"),
    "clique":             (fx_clique, -29.0, "baixa", "clique de interface, botão, check"),
    "ui_hover":           (fx_ui_hover, -35.0, "baixa", "cursor passando sobre um botão"),
    "ui_toggle":          (fx_ui_toggle, -29.0, "baixa", "chave liga/desliga, troca de aba"),
    "shutter":            (fx_shutter, -28.0, "baixa", "clique de câmera, print de tela"),
    "glitch":             (fx_glitch, -34.0, "baixa", "troca de estado da interface (tape-stop abafado)"),
    "tecla_1":            (lambda: fx_tecla(1), -30.0, "baixa", "tecla avulsa suave"),
    "tecla_2":            (lambda: fx_tecla(2), -30.0, "baixa", "tecla avulsa suave"),
    "tecla_3":            (lambda: fx_tecla(3), -30.0, "baixa", "tecla avulsa suave"),
    "tecla_4":            (lambda: fx_tecla(4), -30.0, "baixa", "barra de espaço"),
    "digitacao_suave":    (fx_digitacao_suave, -30.0, "baixa", "texto sendo digitado (2 s; corte ou repita)"),
    "contador":           (fx_contador, -30.0, "baixa", "número contando, desacelerando (1,2 s)"),
    "numero_tick_rapido": (fx_numero_tick_rapido, -31.0, "baixa", "número correndo rápido (0,8 s)"),
    "papel":              (fx_papel, -27.0, "media", "papel virando, folha manuseada (1 s)"),
    "caneta":             (fx_caneta, -28.0, "media", "caneta marcando, riscando (1 s)"),
    "carimbo":            (fx_carimbo, -24.0, "alta", "carimbo batendo no papel"),
    "fogo":               (fx_fogo, -25.0, "media", "fogo queimando, crepitando (1 s)"),
    "sintetizador":       (fx_sintetizador, -28.0, "media", "varredura de sintetizador (2 s)"),
}
CORPO = {"riser_1s": 1.0, "riser_2s": 2.0}                 # duração do gesto antes da cauda da sala
ABRE = {"whoosh_curto", "whoosh_longo", "swish_a", "swish_b", "swish_c", "whip", "zoom_in", "zoom_out",
        "riser_1s", "riser_2s", "sparkle", "flash"}        # alternam o lado a cada ocorrência (só por nível)
TEXTURAS = {"papel", "caneta", "fogo", "digitacao_suave"}
APELIDOS = {"whoosh": "whoosh_curto", "swoosh": "whoosh_curto", "swish": "swish_a", "transicao": "whoosh_longo",
            "zoom": "zoom_in", "riser": "riser_1s", "subida": "riser_1s", "impacto_grave": "impacto",
            "impacto_cartela": "impacto", "boom": "impacto", "hit": "slam", "batida": "slam", "click": "clique",
            "clique_interface": "clique", "ui_click": "clique", "ui_blip": "blip", "ding": "blip", "brilho": "sparkle",
            "camera": "shutter", "print": "shutter", "clarao": "flash", "digitacao": "digitacao_suave",
            "datilografia": "digitacao_suave", "teclado": "digitacao_suave", "tecla": "tecla_1",
            "papel_virando": "papel", "pagina": "papel", "caneta_marcando": "caneta", "marcador": "caneta",
            "fogo_queimando": "fogo", "synth": "sintetizador", "carimbar": "carimbo", "stamp": "carimbo"}


def carregar_extra(arquivo):
    """Receitas novas escritas no projeto: o arquivo define EXTRA = {"nome": (receita, pico_dbfs, classe, uso)}
    e pode usar tudo daqui com `from sfx_lib import *`."""
    spec = importlib.util.spec_from_file_location("receitas_extra", arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    extra = getattr(mod, "EXTRA", {})
    for nome, v in extra.items():
        if not (isinstance(v, tuple) and len(v) == 4 and callable(v[0])):
            raise SystemExit(f"{arquivo}: EXTRA[{nome!r}] precisa ser (receita, pico_dbfs, classe, uso)")
    BIBLIOTECA.update(extra)
    for nome, v in getattr(mod, "CORPO", {}).items():
        CORPO[nome] = v
    ABRE.update(getattr(mod, "ABRE", set()))
    return list(extra)


# ───────────────────────────────────────────────────────────── análise ──
def analisar(x):
    m = x.mean(axis=1).astype(float)
    X = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    meio = X[(f >= 200) & (f < 3000)].sum() + 1e-20
    pico = float(np.max(np.abs(x)))
    return {"centroide_hz": float((X * f).sum() / (X.sum() + 1e-20)),
            "acima_6k_vs_meio_db": float(10 * np.log10(X[f > 6000].sum() / meio + 1e-20)),
            "pico_dbfs": float(20 * np.log10(pico + 1e-12)),
            "borda": float(max(np.abs(x[0]).max(), np.abs(x[-1]).max()) / (pico + 1e-12)),
            "correlacao_lr": float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) if np.std(x[:, 0]) > 0 else 1.0,
            "duracao_s": len(x) / SR}


def gerar(pasta, nomes=None, tom="D", amostra=True, extra=None):
    """Gera os efeitos em `pasta` (WAV 48 kHz estéreo 16-bit) e atualiza o manifest.json. Devolve o manifesto."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if extra:
        carregar_extra(extra)
    semitons = afinar(tom)
    arq_man = pasta / "manifest.json"
    manifest = json.loads(arq_man.read_text(encoding="utf-8")) if arq_man.is_file() else {}
    if manifest.get("tom") not in (None, tom):
        nomes = None                                        # tom mudou: refaz tudo para a família continuar afinada
        manifest["efeitos"] = {}
    manifest.update({"taxa": SR, "canais": 2, "bits": 16, "tom": tom, "referencia_fala_rms_dbfs": FALA_REF,
                     "nota": "pico = destino absoluto dentro da mix final a −14 LUFS (fala com RMS de −16,4 dBFS); "
                             "use a 0 dB e deixe o posicionar.py corrigir pelo nível real da voz"})
    manifest.setdefault("efeitos", {})
    falhas = []
    for nome in (nomes or list(BIBLIOTECA)):
        if nome not in BIBLIOTECA:
            raise SystemExit(f"efeito desconhecido: {nome!r}. Disponíveis: {', '.join(BIBLIOTECA)}")
        fn, alvo, classe, uso = BIBLIOTECA[nome]
        x = finalizar(fn(), alvo)
        arq = pasta / f"{nome}.wav"
        gravar(arq, x)
        a = analisar(ler(arq))
        teto = 4000 if nome in TEXTURAS else 2500
        ok = a["centroide_hz"] < teto and a["acima_6k_vs_meio_db"] <= -20 and a["borda"] < 1e-3
        if not ok:
            falhas.append(nome)
        manifest["efeitos"][nome] = {
            "arquivo": arq.name, "duracao_s": round(a["duracao_s"], 3), "pico_dbfs": round(a["pico_dbfs"], 2),
            "abaixo_da_fala_db": round(FALA_REF - a["pico_dbfs"], 1), "classe": classe,
            "corpo_s": CORPO.get(nome), "abre": nome in ABRE, "centroide_hz": round(a["centroide_hz"]),
            "acima_6k_vs_200_3k_db": round(a["acima_6k_vs_meio_db"], 1),
            "correlacao_lr": round(a["correlacao_lr"], 3), "elegante": ok, "uso": uso}
        print(f"{nome:20s} {a['duracao_s']:5.2f} s  pico {a['pico_dbfs']:6.1f} dBFS  centroide {a['centroide_hz']:5.0f} Hz"
              f"  >6k {a['acima_6k_vs_meio_db']:6.1f} dB  {'ok' if ok else 'FORA DA META'}")
    manifest["semitons_desde_re"] = semitons
    texto = json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"
    arq_man.write_text(texto, encoding="utf-8", newline="\n")
    if amostra:                     # todos em sequência, +10 dB, 0,7 s entre eles: para ouvir a biblioteca sozinha
        sil = np.zeros((int(0.7 * SR), 2))
        partes = []
        for nome in manifest["efeitos"]:
            if (pasta / f"{nome}.wav").is_file():
                partes += [ler(pasta / f"{nome}.wav"), sil]
        gravar(pasta / "_amostra.wav", np.concatenate(partes) * 10 ** (10 / 20))
    if falhas:
        print("fora da meta de elegância (centroide, agudo acima de 6 kHz ou borda):", ", ".join(falhas))
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Gera a biblioteca de efeitos sintetizados.")
    ap.add_argument("--saida", default="som/sfx", help="pasta da biblioteca (padrão som/sfx)")
    ap.add_argument("--so", help="só estes efeitos, separados por vírgula")
    ap.add_argument("--tom", default="D", help="tom da trilha para afinar os efeitos tonais (padrão D)")
    ap.add_argument("--extra", help="arquivo .py do projeto com EXTRA = {nome: (receita, pico, classe, uso)}")
    ap.add_argument("--sem-amostra", action="store_true", help="não grava o _amostra.wav")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    if a.extra:
        carregar_extra(a.extra)
    if a.listar:
        for nome, (_fn, pico, classe, uso) in BIBLIOTECA.items():
            print(f"{nome:20s} {classe:5s} {pico:6.1f} dBFS  {uso}")
        print("apelidos:", ", ".join(f"{k}→{v}" for k, v in APELIDOS.items()))
        return
    nomes = [APELIDOS.get(n.strip(), n.strip()) for n in a.so.split(",")] if a.so else None
    gerar(a.saida, nomes, a.tom.upper(), amostra=not a.sem_amostra)


if __name__ == "__main__":
    main()
