#!/usr/bin/env python3
"""onda.py: o áudio em si — extrair o WAV 16 kHz mono, medir a fala por energia e recortar blocos.

Usado por transcrever.py e afinar.py. O recorte de bloco é feito aqui, pelo módulo `wave`, e não pelo
ffmpeg: um vídeo de 1 h vira dezenas de blocos e chamar o ffmpeg para cada um custa mais que a leitura.
"""
import platform
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np


def com_trava(cmd):
    """Devolve o comando, pela trava da máquina quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude" / "skills" / "video-direcao-de-arte" / "kit" / "trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--silencioso", "--inatividade", "600", "--"] + list(cmd)
    return list(cmd)


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg não encontrado: rode o preparar.py desta skill")
    return exe


def extrair_wav16k(midia, destino):
    """Qualquer mídia → WAV 16 kHz mono pcm_s16le (a entrada canônica do Whisper)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg(), "-v", "error", "-y", "-i", str(midia), "-vn", "-ac", "1", "-ar", "16000",
           "-c:a", "pcm_s16le", str(destino)]
    r = subprocess.run(com_trava(cmd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not destino.exists():
        raise RuntimeError(f"ffmpeg não conseguiu extrair o áudio: {(r.stderr or '')[-400:]}")
    return destino


def ler_wav_mono(caminho):
    """WAV PCM 16 bits → (float32 mono em -1..1, taxa)."""
    with wave.open(str(caminho)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x / 32768.0, sr


def energia_db(x, sr, passo=0.01):
    """RMS em dB por janela de `passo` segundos."""
    h = max(1, int(sr * passo))
    n = max(1, len(x) // h)
    r = np.sqrt((x[: n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(r)


def span_fala(x, sr, abaixo_do_pico=35.0):
    """(início, fim, pico em dBFS) da fala: primeira e última janela a menos de `abaixo_do_pico` dB do pico."""
    db = energia_db(x, sr, 0.02)
    pico = float(db.max())
    idx = np.where(db > pico - abaixo_do_pico)[0]
    if not len(idx):
        return 0.0, len(x) / sr, pico
    return float(idx[0] * 0.02), float((idx[-1] + 1) * 0.02), pico


def fatiar_wav(origem, destino, t0, t1):
    """Recorta [t0, t1) de um WAV mono para outro WAV. Devolve o início real (s) do pedaço gravado."""
    with wave.open(str(origem)) as w:
        sr, n = w.getframerate(), w.getnframes()
        a = max(0, int(round(t0 * sr)))
        b = min(n, int(round(t1 * sr)))
        w.setpos(a)
        dados = w.readframes(max(0, b - a))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(sr)
        o.writeframes(dados)
    return a / sr


def duracao_wav(caminho):
    with wave.open(str(caminho)) as w:
        return w.getnframes() / w.getframerate()
