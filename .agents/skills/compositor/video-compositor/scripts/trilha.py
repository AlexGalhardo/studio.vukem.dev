#!/usr/bin/env python3
"""trilha.py: trilha original feita por código — contrabaixo, bateria e teclado, em numpy puro.

Nada de amostra ou loop de terceiros: a música é sintetizada aqui, nota por nota, então não há o que
licenciar e o tema é seu. São três instrumentos, sempre os mesmos:

  contrabaixo  corda dedilhada (modelo de harmônicos com o ponto do dedo a 22% do cavalete)
  bateria      bumbo afinado, caixa com esteira de ruído e chimbal abafado
  teclado      piano elétrico Rhodes (FM de razão 1, índice que cai) com tremolo estéreo por nível

Duas versões saem de uma vez:
  trilha.wav       a música inteira, pico em −3 dBFS
  trilha_cama.wav  a mesma música "aberta" para a voz: −6,5 dB entre 300 Hz e 3 kHz, teclado e chimbal
                   mais baixos e um pouco mais escura. É a que entra na mixagem sob a locução.

Clima e bpm são configuráveis; o clima escolhe a tonalidade, a progressão, a batida e o brilho.
Estéreo só por nível (mono-safe), começo e fim em zero, fade de entrada e de saída.

Uso:
  python3 trilha.py --bpm 92 --clima tenso --dur 180 --saida som/
  python3 trilha.py --clima claro --dur 45 --saida som/ --nome abertura
  python3 trilha.py --climas                 lista os climas, com bpm sugerido e a cara de cada um
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio import SR, db, gravar  # noqa: E402

# ─────────────────────────────────────────────────────────────── climas ──
# progressao: (nota do baixo, acorde do teclado) em MIDI, um por 2 compassos
# bateria: tempos do bumbo e da caixa (em semínimas) e a grade do chimbal
# brilho_hz: corte geral · niveis_db: baixo, bateria, teclado · piano_por_compasso: ataques do Rhodes
CLIMAS = {
    "tenso": {
        "bpm": 86, "cara": "ré menor contido: baixo grave, caixa fraca, Rhodes raro e escuro",
        "progressao": [(38, [50, 57, 60, 65]), (34, [46, 53, 57, 62]),
                       (31, [43, 50, 53, 58]), (33, [45, 52, 55, 60])],
        "bumbo": [0, 2.5], "caixa": [2], "chimbal": "semicolcheia_fantasma", "chimbal_g": 0.10,
        "brilho_hz": 3000, "niveis_db": (-1.0, -3.0, -8.0), "piano_por_compasso": 1, "sub": True,
    },
    "neutro": {
        "bpm": 100, "cara": "ré maior sereno: a cama padrão de vídeo falado",
        "progressao": [(38, [50, 57, 61, 66]), (35, [47, 54, 57, 62]),
                       (43, [55, 59, 62, 66]), (45, [57, 61, 64, 66])],
        "bumbo": [0, 2], "caixa": [1, 3], "chimbal": "colcheia", "chimbal_g": 0.16,
        "brilho_hz": 4200, "niveis_db": (-1.5, 0.0, -5.5), "piano_por_compasso": 2, "sub": False,
    },
    "claro": {
        "bpm": 110, "cara": "dó maior aberto: Rhodes mais presente, chimbal em colcheias",
        "progressao": [(36, [48, 55, 59, 64]), (33, [45, 52, 55, 60]),
                       (41, [53, 57, 60, 65]), (43, [55, 59, 62, 64])],
        "bumbo": [0, 2], "caixa": [1, 3], "chimbal": "colcheia", "chimbal_g": 0.20,
        "brilho_hz": 5000, "niveis_db": (-2.0, -0.5, -4.0), "piano_por_compasso": 3, "sub": False,
    },
    "grave": {
        "bpm": 76, "cara": "mi menor em meio-tempo: quase só baixo e bumbo, para trecho pesado",
        "progressao": [(40, [52, 55, 59, 62]), (36, [48, 52, 55, 59]),
                       (33, [45, 52, 55, 60]), (35, [47, 54, 57, 62])],
        "bumbo": [0], "caixa": [2], "chimbal": "off", "chimbal_g": 0.0,
        "brilho_hz": 2400, "niveis_db": (0.0, -2.0, -10.0), "piano_por_compasso": 1, "sub": True,
    },
    "pulsante": {
        "bpm": 112, "cara": "lá menor motor: baixo em colcheias, chimbal miúdo, andamento constante",
        "progressao": [(33, [45, 52, 57, 60]), (29, [41, 48, 53, 57]),
                       (36, [48, 52, 55, 60]), (31, [43, 50, 55, 59])],
        "bumbo": [0, 1, 2, 3], "caixa": [1, 3], "chimbal": "semicolcheia", "chimbal_g": 0.11,
        "brilho_hz": 4000, "niveis_db": (-1.0, -1.0, -7.0), "piano_por_compasso": 2, "sub": False,
        "baixo_colcheias": True,
    },
}

# a cama: quanto cada coisa muda para a voz caber na frente
CAMA = {"entalhe_db": -6.5, "entalhe_lo": 300.0, "entalhe_hi": 3000.0,
        "teclado_db": -4.0, "chimbal_db": -6.0, "brilho_fator": 0.72}


# ────────────────────────────────────────────────────────────────── DSP ──
def hz(midi):
    return 440.0 * 2 ** ((float(midi) - 69) / 12)


def mascara(freqs, lo, hi, slope=0.4):
    lf = np.log2(np.maximum(freqs, 1.0))
    m = np.ones_like(freqs)
    for d in (np.log2(lo) - lf, lf - np.log2(hi)):
        k = d > 0
        m[k] *= np.where(d[k] < slope, 0.5 * (1 + np.cos(np.pi * d[k] / slope)), 0.0)
    return m


def banda(x, lo, hi, slope=0.4):
    X = np.fft.rfft(x) * mascara(np.fft.rfftfreq(len(x), 1 / SR), lo, hi, slope)
    return np.fft.irfft(X, len(x))


def filtro_fft(x, ganho, nfft=16384):
    """Filtro de fase zero por sobreposição-soma: roda em trilha longa sem estourar a memória. Hann com
    salto nfft/4, que é onde Σ hann² é constante (1,5). `ganho` tem o tamanho de rfftfreq(nfft)."""
    x = np.asarray(x, dtype=np.float64)
    hop = nfft // 4
    win = np.hanning(nfft + 1)[:-1]
    xp = np.concatenate([np.zeros(nfft), x, np.zeros(2 * nfft)])
    out = np.zeros(len(xp))
    for i in range(0, len(xp) - nfft + 1, hop):
        out[i:i + nfft] += np.fft.irfft(np.fft.rfft(xp[i:i + nfft] * win) * ganho, nfft) * win
    return (out / 1.5)[nfft:nfft + len(x)]


def subida(n, k):
    e = np.ones(n)
    k = max(1, min(n, int(k)))
    e[:k] = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    return e


def soltar(e, k):
    k = max(1, min(len(e), int(k)))
    e[-k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(k) / k)
    return e


def env(t, ataque, tau):
    return subida(len(t), ataque * SR) * np.exp(-np.maximum(t - ataque, 0) / tau)


def portao(n, fim, solta):
    """1 até `fim` (s), cai em cosseno em `solta` s e fica em zero."""
    g = np.ones(n)
    i, k = int(fim * SR), max(1, int(solta * SR))
    if i < n:
        g[i:i + k] = (0.5 + 0.5 * np.cos(np.pi * np.arange(1, k + 1) / k))[:max(0, min(k, n - i))]
        g[i + k:] = 0
    return g


def soma(buf, ini_s, x, gl=1.0, gr=1.0):
    i = int(round(ini_s * SR))
    if i >= len(buf) or i + len(x) <= 0:
        return
    a, b = max(i, 0), min(len(buf), i + len(x))
    buf[a:b, 0] += x[a - i:b - i] * gl
    buf[a:b, 1] += x[a - i:b - i] * gr


# ──────────────────────────────────────────────────────── instrumentos ──
def nota_baixo(midi, dur, vel=1.0, semente=0):
    """Contrabaixo dedilhado: harmônicos de corda com o ponto do dedo a 22% do cavalete, os agudos morrendo
    antes, um "tum" de dedo abaixo de 700 Hz e saturação leve para arredondar."""
    r = np.random.default_rng(semente)
    n = int((dur + 0.12) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    y = np.zeros(n)
    for h in range(1, 11):
        y += abs(np.sin(np.pi * h * 0.22)) / h * np.sin(2 * np.pi * h * f * t) * np.exp(-t / (0.9 / (1 + 0.45 * (h - 1))))
    y /= np.max(np.abs(y)) + 1e-12
    tum = banda(r.standard_normal(n), 120, 700, 0.8)
    y += 0.12 * tum / (np.std(tum) + 1e-12) * env(t, 0.003, 0.012)
    y *= subida(n, 0.004 * SR) * portao(n, max(dur - 0.03, 0.05), 0.06)
    return vel * np.tanh(1.3 * y) / np.tanh(1.3)


def bumbo(r, sub=False):
    t = np.arange(int(0.5 * SR)) / SR
    f = (44 if sub else 50) + 70 * np.exp(-t / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.002, 0.24 if sub else 0.2)
    feltro = banda(r.standard_normal(len(t)), 100, 1000, 0.8)
    y += 0.08 * feltro / (np.std(feltro) + 1e-12) * env(t, 0.002, 0.008)
    return np.tanh(1.4 * y) / np.tanh(1.4)


def caixa(r, vel=1.0):
    t = np.arange(int(0.35 * SR)) / SR
    corpo = 0.6 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) + 0.3 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.03)
    esteira = banda(r.standard_normal(len(t)), 300, 3500, 0.8)
    return vel * (corpo * subida(len(t), 0.002 * SR) + 0.5 * esteira / (np.std(esteira) + 1e-12) * env(t, 0.002, 0.07))


def chimbal(r, vel):
    t = np.arange(int(0.12 * SR)) / SR
    x = banda(r.standard_normal(len(t)), 2200, 5200, 0.6)
    return vel * x / (np.max(np.abs(x)) + 1e-12) * env(t, 0.002, 0.022)


def rhodes(midi, dur, vel=1.0):
    """Piano elétrico: FM de razão 1 com índice que cai (ataque mais claro, depois redondo) e um toque de
    "tine" que some em 50 ms."""
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    indice = 0.25 + 1.0 * np.exp(-t / 0.25)
    y = np.sin(2 * np.pi * f * t + indice * np.sin(2 * np.pi * f * t))
    y += 0.08 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.05)
    return vel * y * subida(n, 0.004 * SR) * np.exp(-t / 1.4) * portao(n, dur, 0.14)


def acorde(notas, dur, vel=0.85):
    """Dedilha de leve: 12 ms entre as notas, as de cima um pouco mais fracas."""
    n = int((dur + 0.8) * SR)
    y = np.zeros(n)
    for k, m in enumerate(notas):
        s = rhodes(m, dur - k * 0.012, vel * (1 - 0.05 * k))
        i = int(k * 0.012 * SR)
        j = min(n, i + len(s))
        y[i:j] += s[:j - i]
    return y


# ──────────────────────────────────────────────────────────── arranjo ──
def montar(clima, bpm, dur, semente=7):
    """Monta a trilha (n, 2) em float64. Retorna também os dados do arranjo."""
    c = CLIMAS[clima]
    T = 60.0 / float(bpm)
    comp = 4 * T
    n = int(dur * SR)
    bat = np.zeros((n + int(2 * SR), 2))
    grave = np.zeros_like(bat)
    tecl = np.zeros_like(bat)
    r = np.random.default_rng(semente)
    prog = c["progressao"]
    compassos = int(np.ceil(dur / comp)) + 1
    arranjo = []
    for b in range(compassos):
        t0 = b * comp
        if t0 > dur + comp:
            break
        raiz, notas = prog[(b // 2) % len(prog)]
        arranjo.append({"compasso": b, "t": round(t0, 3), "baixo_midi": raiz, "acorde_midi": list(notas)})
        abertura = min(b / 2.0, 1.0)                        # os dois primeiros compassos entram abrindo
        # bateria
        for k in c["bumbo"]:
            soma(bat, t0 + k * T, bumbo(r, c.get("sub", False)) * (1.0 if k == 0 else 0.85))
        for k in c["caixa"]:
            soma(bat, t0 + k * T, caixa(r, 0.55 * abertura))
        grade = {"colcheia": 8, "semicolcheia": 16, "semicolcheia_fantasma": 8, "off": 0}[c["chimbal"]]
        for j in range(grade):
            passo = 4 * T / grade
            vel = c["chimbal_g"] * (1.0 if j % 2 == 0 else 0.62) * abertura
            g = (1.0, 0.84) if j % 2 == 0 else (0.84, 1.0)  # chimbal levemente aberto, só por nível
            soma(bat, t0 + j * passo, chimbal(r, vel), *g)
        # contrabaixo: semínimas (raiz · quinta · raiz · quinta) ou colcheias no clima pulsante
        quinta = raiz + 7
        if c.get("baixo_colcheias"):
            for j in range(8):
                m = raiz if j % 4 in (0, 1, 2) else quinta
                soma(grave, t0 + j * T / 2, nota_baixo(m, T / 2 * 0.78, 0.95 if j % 2 == 0 else 0.72, semente=b * 10 + j))
        else:
            for j, (m, v) in enumerate(((raiz, 1.0), (quinta, 0.82), (raiz + 12, 0.78), (quinta, 0.8))):
                soma(grave, t0 + j * T, nota_baixo(m, T * 0.82, v, semente=b * 10 + j))
        # teclado: o acorde no tempo 1 e, quando o clima pede, notas soltas do acorde
        soma(tecl, t0, acorde(notas, 2 * T, 0.85 * abertura), 1.0, 1.0)
        for k in range(1, int(c["piano_por_compasso"])):
            nota = notas[(b + k) % len(notas)] + (12 if r.random() < 0.3 else 0)
            lado = (1.0, 0.78) if k % 2 else (0.78, 1.0)
            soma(tecl, t0 + (1 + k) * T, rhodes(nota, T * 0.9, 0.34 * abertura), *lado)
    return bat[:n], grave[:n], tecl[:n], arranjo, {"T": T, "compasso_s": comp, "compassos": compassos}


def tremolo(x, hz_mod=4.5, prof=0.10):
    """Tremolo estéreo por nível: a soma mono fica constante (mono-safe)."""
    t = np.arange(len(x)) / SR
    m = prof * np.sin(2 * np.pi * hz_mod * t)
    return np.stack([x[:, 0] * (1 + m), x[:, 1] * (1 - m)], axis=1)


def abrir_para_voz(x, lo, hi, corte_db):
    """Entalhe suave na faixa da voz (a "cama"), por sobreposição-soma."""
    f = np.fft.rfftfreq(16384, 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    desce = np.clip((lf - np.log2(lo / 2)) / 1.0, 0, 1)
    sobe = np.clip((lf - np.log2(hi)) / (np.log2(hi * 1.7) - np.log2(hi)), 0, 1)
    g = 10 ** (corte_db * (desce * (1 - sobe)) / 20)
    return np.stack([filtro_fft(x[:, ch], g) for ch in range(2)], axis=1)


def gerar(saida, clima="neutro", bpm=None, dur=120.0, nome="trilha", semente=7, com_cama=True):
    if clima not in CLIMAS:
        raise SystemExit(f"clima desconhecido: {clima!r}. Use {', '.join(CLIMAS)}.")
    bpm = float(bpm or CLIMAS[clima]["bpm"])
    if not 50 <= bpm <= 180:
        raise SystemExit("bpm fora da faixa útil (50 a 180).")
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    c = CLIMAS[clima]
    n_baixo, n_bat, n_tecl = c["niveis_db"]

    bat, grave, tecl, arranjo, m = montar(clima, bpm, float(dur), semente)
    tecl = tremolo(tecl)
    rel = {"nome": nome, "clima": clima, "cara": c["cara"], "bpm": round(bpm, 2), "duracao_s": round(dur, 3),
           "compasso_s": round(m["compasso_s"], 3), "compassos": m["compassos"], "semente": semente,
           "instrumentos": ["contrabaixo", "bateria", "teclado"],
           "progressao_midi": [{"baixo": a, "acorde": b} for a, b in c["progressao"]],
           "niveis_db": {"contrabaixo": n_baixo, "bateria": n_bat, "teclado": n_tecl}}

    arquivos = {}
    for versao in (["trilha", "cama"] if com_cama else ["trilha"]):
        cama = versao == "cama"
        x = (grave * 10 ** (n_baixo / 20) + bat * 10 ** (n_bat / 20)
             + tecl * 10 ** ((n_tecl + (CAMA["teclado_db"] if cama else 0)) / 20))
        brilho = c["brilho_hz"] * (CAMA["brilho_fator"] if cama else 1.0)
        x = np.stack([banda(x[:, ch], 30, brilho, 0.7) for ch in range(2)], axis=1)
        if cama:
            x = abrir_para_voz(x, CAMA["entalhe_lo"], CAMA["entalhe_hi"], CAMA["entalhe_db"])
        f_in, f_out = int(0.6 * SR), int(1.8 * SR)
        x[:f_in] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(f_in) / f_in))[:, None]
        x[-f_out:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(1, f_out + 1) / f_out))[:, None]
        x *= 10 ** (-3 / 20) / (np.max(np.abs(x)) + 1e-12)
        arq = saida / (f"{nome}_cama.wav" if cama else f"{nome}.wav")
        gravar(arq, x)
        mono = x.mean(axis=1)
        rel[versao] = {"arquivo": str(arq), "pico_dbfs": round(db(np.max(np.abs(x))), 2),
                       "rms_dbfs": round(db(np.sqrt(np.mean(x ** 2))), 2),
                       "correlacao_lr": round(float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]), 3),
                       "perda_mono_db": round(10 * np.log10(np.mean(x ** 2) / (np.mean(mono ** 2) + 1e-20)), 2)}
        arquivos[versao] = arq
        print(f"{arq.name}: {dur:.1f} s, {bpm:.0f} bpm, clima {clima}, pico {rel[versao]['pico_dbfs']} dBFS, "
              f"RMS {rel[versao]['rms_dbfs']} dBFS, corr L/R {rel[versao]['correlacao_lr']}")
        del x
    rel["arranjo"] = arranjo[:48]
    texto = json.dumps(rel, ensure_ascii=False, indent=1) + "\n"
    (saida / f"{nome}.json").write_text(texto, encoding="utf-8", newline="\n")
    return rel


def main():
    ap = argparse.ArgumentParser(description="Trilha original por código (contrabaixo, bateria, teclado).")
    ap.add_argument("--saida", default="som/", help="pasta de saída (padrão som/)")
    ap.add_argument("--clima", default="neutro", help=f"{', '.join(CLIMAS)}")
    ap.add_argument("--bpm", type=float, help="batidas por minuto (padrão: o do clima)")
    ap.add_argument("--dur", type=float, default=120.0, help="duração em segundos")
    ap.add_argument("--nome", default="trilha", help="nome base dos arquivos (padrão trilha)")
    ap.add_argument("--semente", type=int, default=7, help="muda os detalhes sem mudar a música")
    ap.add_argument("--sem-cama", action="store_true", help="não gera a versão cama")
    ap.add_argument("--climas", action="store_true", help="lista os climas e sai")
    a = ap.parse_args()
    if a.climas:
        for nome, c in CLIMAS.items():
            print(f"{nome:10s} {c['bpm']:>4.0f} bpm  {c['cara']}")
        return
    gerar(a.saida, a.clima, a.bpm, a.dur, a.nome, a.semente, com_cama=not a.sem_cama)


if __name__ == "__main__":
    main()
