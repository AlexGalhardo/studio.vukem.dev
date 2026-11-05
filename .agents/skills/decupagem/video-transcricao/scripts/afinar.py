#!/usr/bin/env python3
"""afinar.py: corrige o começo de cada palavra pela energia do áudio.

O Whisper marca o início das palavras com 1 a 2 décimos de erro. Quando uma palavra vem depois de um respiro
(≥ 60 ms abaixo do limiar de fala), o início dela passa para o ataque real da onda dentro de ±0,2 s. Palavra
colada na anterior (sem respiro) fica como está: ali não há ataque para medir.

O transcrever.py já chama este módulo. Rode à mão quando o áudio mudou (depois de uma decupagem, por exemplo):
  python3 afinar.py transcricao/palavras.json <áudio ou vídeo> [--saida transcricao/palavras.json]
Códigos de saída: 0 ok · 1 falhou · 2 falta insumo.
"""
import argparse
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import onda as O  # noqa: E402
import palavras as P  # noqa: E402

JANELA = 0.20      # o ataque procurado fica a até 0,2 s do início que o Whisper deu
RESPIRO = 6        # quadros de 10 ms abaixo do limiar antes do ataque (60 ms)


def ataques(x, sr):
    """Instantes (s) em que a voz sobe depois de um respiro, e o limiar usado (dB)."""
    db = O.energia_db(x, sr, 0.01)
    lim = float(np.percentile(db, 10) + 10)
    acima = db >= lim
    abaixo = np.convolve(~acima, np.ones(RESPIRO), "full")[: len(db)] >= RESPIRO
    idx = np.where(acima[1:] & abaixo[:-1])[0] + 1
    return idx / 100.0, lim


def afinar(palavras, x, sr):
    """Devolve (novas palavras, estatística). Não muda a ordem nem o texto."""
    at, lim = ataques(x, sr)
    novo, mov = [], []
    for i, p in enumerate(palavras):
        q = dict(p)
        t0 = p["t0"]
        # teto: o ataque não pode passar do início que o Whisper deu à palavra SEGUINTE — senão as duas
        # trocam de lugar na ordem do tempo e quem lê ordenando por t0 recebe a frase embaralhada.
        teto = min(t0 + JANELA, (palavras[i + 1]["t0"] if i + 1 < len(palavras) else float("inf")) - 0.02)
        c = at[(at >= t0 - JANELA) & (at <= teto)]
        if len(c):
            o = float(c[np.argmin(np.abs(c - t0))])
            if novo and o < novo[-1]["t0"] + 0.04:
                o = t0
            if abs(o - t0) > 0.005:
                mov.append(o - t0)
                q["t0"] = round(o, 3)
                q["t1"] = round(max(q["t1"], q["t0"] + 0.06), 3)
                if novo and novo[-1]["t1"] > q["t0"]:
                    novo[-1]["t1"] = round(max(novo[-1]["t0"] + 0.04, q["t0"]), 3)
        novo.append(q)
    for i in range(1, len(novo)):                       # garante tempo não decrescente
        if novo[i]["t0"] < novo[i - 1]["t0"]:
            novo[i]["t0"] = round(novo[i - 1]["t0"] + 0.01, 3)
            novo[i]["t1"] = round(max(novo[i]["t1"], novo[i]["t0"] + 0.04), 3)
    m = np.array(mov) if mov else np.zeros(1)
    est = {"palavras": len(palavras), "afinadas": len(mov), "limiar_db": round(lim, 1),
           "deslocamento_mediano_s": round(float(np.median(m)), 3) if mov else 0.0,
           "deslocamento_abs_mediano_s": round(float(np.median(np.abs(m))), 3) if mov else 0.0,
           "deslocamento_abs_p90_s": round(float(np.percentile(np.abs(m), 90)), 3) if mov else 0.0,
           "deslocamento_abs_max_s": round(float(np.abs(m).max()), 3) if mov else 0.0}
    return novo, est


def onda_de(midia):
    """(sinal mono, taxa) de um WAV; qualquer outra mídia passa antes pelo ffmpeg, num arquivo temporário."""
    try:
        return O.ler_wav_mono(midia)
    except (wave.Error, EOFError):
        with tempfile.TemporaryDirectory(prefix="criabr-afinar-") as d:
            tmp = Path(d) / "a16k.wav"
            O.extrair_wav16k(midia, tmp)
            return O.ler_wav_mono(tmp)


def main():
    ap = argparse.ArgumentParser(description="Afina o início das palavras pela energia do áudio.")
    ap.add_argument("palavras", help="palavras.json")
    ap.add_argument("audio", help="o áudio ou vídeo com o MESMO tempo das palavras")
    ap.add_argument("--saida", help="onde gravar (padrão: sobrescreve o palavras.json)")
    a = ap.parse_args()
    if not Path(a.palavras).exists() or not Path(a.audio).exists():
        print("falta insumo: confira o palavras.json e o áudio", file=sys.stderr)
        sys.exit(2)
    pal = P.carregar(a.palavras)
    try:
        x, sr = onda_de(a.audio)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    novo, est = afinar(pal, x, sr)
    P.gravar_json(a.saida or a.palavras, novo)
    print(f"{est['palavras']} palavras, {est['afinadas']} afinadas pela onda; deslocamento mediano "
          f"{est['deslocamento_mediano_s']:+.3f} s, |mediano| {est['deslocamento_abs_mediano_s']:.3f} s, "
          f"máx {est['deslocamento_abs_max_s']:.2f} s")


if __name__ == "__main__":
    main()
