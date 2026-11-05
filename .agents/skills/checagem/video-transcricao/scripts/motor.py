#!/usr/bin/env python3
"""motor.py: fala com o Whisper (whisper.cpp no Mac, faster-whisper nos outros sistemas) e devolve palavras
com tempo. Usado por transcrever.py; não roda sozinho.

Nada aqui conhece o projeto do usuário: recebe um WAV 16 kHz mono e devolve
[{"w": "palavra", "t0": s, "t1": s, "p": confiança}] em tempo relativo ao WAV.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palavras as P  # noqa: E402

MODELO_PADRAO = "ggml-large-v3-turbo.bin"
NOME_FASTER = "large-v3-turbo"


def com_trava(cmd):
    """Devolve o comando, pela trava da máquina quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude" / "skills" / "video-direcao-de-arte" / "kit" / "trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--silencioso", "--inatividade", "900", "--"] + list(cmd)
    return list(cmd)


def achar_whisper_cli():
    amb = P.ambiente()
    for c in (amb.get("whisper_cli"), "whisper-cli", "whisper-cpp", "main"):
        if not c:
            continue
        exe = shutil.which(c) if not Path(str(c)).is_absolute() else (c if Path(c).exists() else None)
        if exe:
            return str(exe)
    return None


def achar_modelo():
    amb = P.ambiente()
    cands = [amb.get("whisper_modelo"), os.environ.get("WHISPER_MODELO")]
    cands += [P.casa_dir() / "modelos" / MODELO_PADRAO, Path.home() / "whisper-models" / MODELO_PADRAO]
    for c in cands:
        if not c:
            continue
        p = Path(c).expanduser()
        if p.exists() and p.stat().st_size > 1_000_000_000:
            return str(p)
    return None


def motor_disponivel():
    """('whisper-cpp', exe, modelo) · ('faster-whisper', None, nome) · (None, None, None)."""
    exe, mod = achar_whisper_cli(), achar_modelo()
    if exe and mod:
        return "whisper-cpp", exe, mod
    try:
        import faster_whisper  # noqa: F401
        return "faster-whisper", None, os.environ.get("WHISPER_MODELO") or NOME_FASTER
    except ImportError:
        return None, None, None


def _limpar(texto):
    t = str(texto).strip()
    return "" if not t or t.startswith("[") else t


def _rodar_cli(exe, modelo, wav, base, prompt, idioma, por_palavra):
    cmd = [exe, "-m", str(modelo), "-l", idioma, "-ojf", "-np", "-of", str(base), "-f", str(wav)]
    if por_palavra:
        cmd += ["-ml", "1", "-sow"]
    if prompt:
        cmd += ["--prompt", prompt]
    r = subprocess.run(com_trava(cmd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    saida = Path(str(base) + ".json")
    if r.returncode != 0 or not saida.exists():
        raise RuntimeError(f"whisper falhou (código {r.returncode}): {(r.stderr or '')[-600:]}")
    dados = json.loads(saida.read_text(encoding="utf-8"))["transcription"]
    saida.unlink()
    out = []
    for s in dados:
        t = _limpar(s.get("text", ""))
        if not t:
            continue
        toks = [k for k in s.get("tokens", []) if not str(k.get("text", "")).startswith("[_")]
        ps = [k["p"] for k in toks if isinstance(k.get("p"), (int, float))]
        out.append({"w": t, "t0": s["offsets"]["from"] / 1000.0, "t1": s["offsets"]["to"] / 1000.0,
                    "p": round(sum(ps) / len(ps), 3) if ps else None})
    return out


def _rodar_faster(nome_modelo, wav, prompt, idioma, por_palavra):
    from faster_whisper import WhisperModel
    chave = (nome_modelo, idioma)
    if getattr(_rodar_faster, "_cache", (None,))[0] != chave:
        _rodar_faster._cache = (chave, WhisperModel(nome_modelo, device="auto", compute_type="int8"))
    modelo = _rodar_faster._cache[1]
    segs, _ = modelo.transcribe(str(wav), language=idioma, initial_prompt=prompt or None,
                                word_timestamps=True, vad_filter=False)
    out = []
    for s in segs:
        if por_palavra:
            for w in (s.words or []):
                t = _limpar(w.word)
                if t:
                    out.append({"w": t, "t0": float(w.start), "t1": float(w.end),
                                "p": round(float(w.probability), 3)})
        else:
            t = _limpar(s.text)
            if t:
                out.append({"w": t, "t0": float(s.start), "t1": float(s.end),
                            "p": round(float(getattr(s, "avg_logprob", 0.0)), 3)})
    return out


def transcrever_wav(wav, base_tmp, prompt="", idioma="pt", por_palavra=True, motor=None):
    """WAV 16 kHz mono → lista de palavras (ou de segmentos, com por_palavra=False), em tempo do WAV."""
    nome, exe, modelo = motor or motor_disponivel()
    if nome == "whisper-cpp":
        return _rodar_cli(exe, modelo, wav, base_tmp, prompt, idioma, por_palavra)
    if nome == "faster-whisper":
        return _rodar_faster(modelo, wav, prompt, idioma, por_palavra)
    raise RuntimeError("nenhum motor de transcrição disponível: rode o preparar.py desta skill")
