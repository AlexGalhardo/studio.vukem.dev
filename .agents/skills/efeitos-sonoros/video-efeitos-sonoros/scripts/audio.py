"""audio.py: leitura e gravação de WAV, chamada do ffmpeg e medidas de nível (comum às skills de som).

Tudo a 48 kHz. WAV PCM 16-bit é lido direto (módulo wave); qualquer outra mídia (mp4, mov, mp3, m4a) é
convertida antes pelo ffmpeg. O ffmpeg passa pela trava global do kit de direção de arte quando ela existe
e o sistema não é Windows (uma tarefa pesada por vez na máquina); senão roda direto.

Portável: Mac, Linux e Windows. Nenhum caminho absoluto, nenhum programa de sistema fora do ffmpeg.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
FALA_REF = -16.4          # RMS mediano da fala (dBFS) numa mix a −14 LUFS: a referência de todos os níveis
ALVO_LUFS = -14.0
ALVO_TP = -1.0


def casa():
    """Pasta de configuração da crIAbr (~/.criabr, ou CRIABR_CASA nos testes)."""
    return Path(os.environ.get("CRIABR_CASA") or (Path.home() / ".criabr"))


def ambiente():
    f = casa() / "ambiente.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}


def faltou(msg):
    """Falta um insumo (arquivo, transcrição, consentimento): mensagem no stderr e **código 2**.
    Erro de uso — nome de efeito errado, argumento inválido — continua saindo com código 1."""
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def programa(nome):
    """Caminho de um programa externo: PATH primeiro, depois o que o preparar.py anotou."""
    caminho = shutil.which(nome) or ambiente().get(nome)
    if not caminho:
        raise SystemExit(f"{nome} não encontrado. Rode o preparar.py desta skill (ele instala o que falta).")
    return str(caminho)


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows."""
    t = Path(os.environ.get("CLAUDE_SKILLS_DIR") or (Path.home() / ".claude" / "skills"))
    t = t / "video-direcao-de-arte" / "kit" / "trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def rodar(cmd, rotulo="ffmpeg"):
    """Roda um comando (pela trava, se houver) e devolve o stderr. Levanta RuntimeError se falhar."""
    cmd = [str(c) for c in cmd]
    p = subprocess.run(com_trava(cmd), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        raise RuntimeError(f"{rotulo} falhou (código {p.returncode}):\n{(p.stderr or '')[-1500:]}")
    return p.stderr or ""


def ffmpeg(*args, rotulo="ffmpeg"):
    return rodar([programa("ffmpeg"), "-hide_banner", "-nostdin", "-nostats", "-y", *args], rotulo)


# ───────────────────────────────────────────────────────────────── WAV ──
def info_wav(caminho):
    with wave.open(str(caminho), "rb") as w:
        return w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()


def e_wav_pronto(caminho):
    try:
        sr, _ch, sw, _n = info_wav(caminho)
        return sr == SR and sw == 2
    except Exception:
        return False


def para_wav(origem, destino, mono=False):
    """Converte qualquer mídia em WAV 48 kHz PCM 16-bit (estéreo, ou mono com mono=True)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-v", "error", "-i", origem, "-vn", "-ac", "1" if mono else "2", "-ar", str(SR),
           "-c:a", "pcm_s16le", destino, rotulo=f"converter {Path(origem).name}")
    return destino


def ler(caminho, ini=0, n=None, trabalho=None):
    """Lê áudio como float32 (n, 2) a 48 kHz. Mídia que não é WAV 48k/16-bit passa antes pelo ffmpeg."""
    caminho = Path(caminho)
    if not e_wav_pronto(caminho):
        pasta = Path(trabalho) if trabalho else caminho.parent / "_trabalho"
        tmp = pasta / f"_{caminho.stem}_48k.wav"
        if not tmp.exists() or tmp.stat().st_mtime < caminho.stat().st_mtime:
            para_wav(caminho, tmp)
        caminho = tmp
    with wave.open(str(caminho), "rb") as w:
        ch = w.getnchannels()
        w.setpos(int(ini))
        n = w.getnframes() - int(ini) if n is None else int(n)
        x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768
    x = x.reshape(-1, ch)
    return np.repeat(x, 2, axis=1) if ch == 1 else x[:, :2]


def gravar(caminho, x, canais=None):
    """Grava WAV 48 kHz PCM 16-bit (gravação atômica). x: (n,) mono ou (n, 2) estéreo."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    if canais == 2 and x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    tmp = caminho.with_name(f"{caminho.stem}.parcial{caminho.suffix}")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        bloco = 30 * SR
        for i in range(0, len(x), bloco):
            w.writeframes((np.clip(x[i:i + bloco], -1, 1) * 32767).round().astype("<i2").tobytes())
    os.replace(tmp, caminho)
    return caminho


# ─────────────────────────────────────────────────────────── medidas ──
def db(v):
    return float(20 * np.log10(max(float(v), 1e-12)))


def rms_fala(x, janela=0.5, sondas=300):
    """RMS mediano da fala (dBFS): janelas de 0,5 s espalhadas, descartando o quartil mais baixo (silêncio)."""
    if isinstance(x, (str, Path)):
        x = ler(x)
    m = np.asarray(x, dtype=np.float64)
    m = m.mean(axis=1) if m.ndim == 2 else m
    nj = int(janela * SR)
    if len(m) <= nj:
        return db(np.sqrt(np.mean(m ** 2)))
    inis = np.linspace(0, len(m) - nj, min(sondas, max(1, len(m) // nj))).astype(int)
    r = np.array([np.sqrt(np.mean(m[i:i + nj] ** 2)) for i in inis])
    r = r[r > np.percentile(r, 25)]
    return db(np.median(r)) if len(r) else db(0)


def ebur128(caminho):
    """LUFS integrado, LRA e pico real (dBTP) pelo ebur128 do ffmpeg."""
    err = ffmpeg("-v", "info", "-i", caminho, "-af", "ebur128=peak=true", "-f", "null", "-",
                 rotulo=f"ebur128 {Path(caminho).name}")
    resumo = err[err.rfind("Summary:"):]

    def pega(rotulo):
        m = re.search(rf"{rotulo}:\s+(-?[\d.]+|-inf)", resumo)
        return float(m.group(1)) if m and m.group(1) != "-inf" else float("-inf")
    return {"lufs": pega("I"), "lra": pega("LRA"), "pico_real_dbtp": pega("Peak")}


def astats(caminho):
    """Pico e RMS (dBFS) do arquivo inteiro, pelo astats do ffmpeg."""
    err = ffmpeg("-v", "info", "-i", caminho, "-af", "astats=measure_perchannel=none", "-f", "null", "-",
                 rotulo=f"astats {Path(caminho).name}")

    def pega(rotulo):
        m = re.search(rf"{rotulo}:\s+(-?[\d.]+|-?inf)", err)
        if not m:
            return float("-inf")
        v = m.group(1)
        return float("-inf") if "inf" in v else float(v)
    return {"pico_dbfs": pega("Peak level dB"), "rms_dbfs": pega("RMS level dB")}


def ler_da(projeto):
    """Bloco "som" da direção de arte do projeto (da/da.json), se houver; {} se não houver."""
    p = Path(projeto).resolve()
    for d in [p, *p.parents]:
        f = d / "da" / "da.json"
        if f.is_file():
            try:
                return json.loads(f.read_text(encoding="utf-8")).get("som") or {}
            except Exception:
                return {}
    return {}
