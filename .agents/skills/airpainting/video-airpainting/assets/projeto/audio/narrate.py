#!/usr/bin/env python3
"""Narração em pt-BR com a voz que o sistema já tem (nada é baixado).

Lê videos/<nome>/narration.src.json → gera audio/narr/<nome>/*.wav e escreve
videos/<nome>/narration.json com início e duração de cada fala (a linha do tempo do vídeo segue a narração).

uso (da raiz do projeto):  <PYTHON> audio/narrate.py <nome>

Voz por sistema, sempre a do próprio sistema:
  macOS    o sintetizador do sistema (vozes em Português do Brasil no Ajustes → Acessibilidade → Conteúdo falado)
  Windows  SAPI (System.Speech), a voz pt-BR instalada no Windows
  Linux    espeak-ng ou espeak, se estiverem instalados
Sem nenhuma dessas, o script explica o que falta e sai com 3 — a narração é opcional nestes estilos.
"""
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SISTEMA = platform.system()


def falar(texto, destino, voz, velocidade):
    """Grava `texto` em WAV 48 kHz mono no caminho `destino`. Devolve o programa usado, ou None."""
    if SISTEMA == "Darwin":
        prog = shutil.which("say")  # ok-windows: só entra neste ramo quando o sistema é macOS
        if prog:
            cmd = [prog, "-r", str(velocidade), "--file-format=WAVE", "--data-format=LEI16@48000",
                   "-o", str(destino), texto]
            if voz:
                cmd[1:1] = ["-v", voz]
            subprocess.run(cmd, check=True, encoding="utf-8")
            return "say"
    elif SISTEMA == "Windows":
        prog = shutil.which("powershell") or shutil.which("pwsh")
        if prog:
            script = Path(tempfile.gettempdir()) / "criabr_narrar.ps1"
            script.write_text(
                "param($Texto,$Arquivo,$Voz,$Taxa)\n"
                "Add-Type -AssemblyName System.Speech\n"
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
                "if ($Voz) { try { $s.SelectVoice($Voz) } catch {} }\n"
                "else { $v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'pt*' } | "
                "Select-Object -First 1; if ($v) { $s.SelectVoice($v.VoiceInfo.Name) } }\n"
                "$s.Rate = [int]$Taxa\n"
                "$s.SetOutputToWaveFile($Arquivo)\n"
                "$s.Speak($Texto)\n"
                "$s.Dispose()\n", encoding="utf-8", newline="\n")
            taxa = max(-10, min(10, round((velocidade - 180) / 18)))  # palavras/min → escala -10..10 do SAPI
            subprocess.run([prog, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                            "-Texto", texto, "-Arquivo", str(destino), "-Voz", voz or "", "-Taxa", str(taxa)],
                           check=True, encoding="utf-8")
            return "SAPI"
    else:
        prog = shutil.which("espeak-ng") or shutil.which("espeak")
        if prog:
            subprocess.run([prog, "-v", voz or "pt-br", "-s", str(velocidade), "-w", str(destino), texto],
                           check=True, encoding="utf-8")
            return "espeak"
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit("uso: <PYTHON> audio/narrate.py <nome-do-video>")
    nome = sys.argv[1]
    fonte = RAIZ / "videos" / nome / "narration.src.json"
    if not fonte.exists():
        sys.exit(f"não achei {fonte} — escreva a narração antes (veja references/audio.md)")
    src = json.loads(fonte.read_text(encoding="utf-8"))
    voz, velocidade, t = src.get("voz") or src.get("voice") or "", src.get("rate", 182), src.get("start", .6)

    saida = RAIZ / "audio" / "narr" / nome
    saida.mkdir(parents=True, exist_ok=True)
    falas, usado = [], None
    for i, s in enumerate(src["segments"]):
        t += s.get("gap", .35)
        f = saida / f"{i:02d}.wav"
        usado = falar(s["say"], f, voz, velocidade)
        if not usado:
            print("Falta uma voz do sistema: no Windows instale uma voz pt-BR em Configurações → Hora e idioma → "
                  "Fala; no Linux instale o espeak-ng. A narração é opcional: o synth.py roda sem ela.")
            sys.exit(3)
        with wave.open(str(f)) as w:
            d = w.getnframes() / w.getframerate()
        falas.append({"id": s["id"], "text": s.get("text", s["say"]), "start": round(t, 3),
                      "dur": round(d, 3), "file": f"audio/narr/{nome}/{i:02d}.wav"})
        t += d

    alvo = RAIZ / "videos" / nome / "narration.json"
    alvo.write_text(json.dumps({"segments": falas, "end": round(t, 3)}, ensure_ascii=False, indent=1),
                    encoding="utf-8", newline="\n")
    for o in falas:
        print(f"{o['start']:6.2f} +{o['dur']:.2f}  {o['text']}")
    print(f"fim {round(t, 2)}  (voz: {usado})")


if __name__ == "__main__":
    main()
