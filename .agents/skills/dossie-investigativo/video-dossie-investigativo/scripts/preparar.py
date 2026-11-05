#!/usr/bin/env python3
"""preparar.py: autoinstalação das skills da crIAbr (o mesmo arquivo vai em todas as skills).

Uso:
  python3 <skill>/scripts/preparar.py                      confere e lista o que falta (não muda nada)
  python3 <skill>/scripts/preparar.py --instalar           instala o que falta (peça o ok do usuário antes)
  python3 <skill>/scripts/preparar.py --instalar --atualizar   também substitui skills já instaladas

O que ele cuida, lendo scripts/requisitos.json da skill e das skills de que ela depende:
  - a skill (e as dependências que vieram no mesmo zip) em ~/.claude/skills/
  - programas (ffmpeg, node, whisper-cli) pelo gerenciador do sistema (brew, apt, winget)
  - bibliotecas Python num ambiente próprio (~/.criabr/venv) quando o Python atual não as tem
  - modelo do Whisper e Chromium do motor, baixados uma vez
Códigos de saída: 0 pronto · 3 falta algo (a lista diz o quê) · 1 erro.
No fim imprime PYTHON=<caminho>: rode os scripts da skill com esse Python. O estado fica em ~/.criabr/ambiente.json.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

for _f in (sys.stdout, sys.stderr):  # no Windows o console é cp1252 e engasga nos acentos
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
CASA = Path(os.environ.get("CRIABR_CASA", Path.home() / ".criabr"))
VENV = CASA / "venv"
DESTINO = Path(os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills"))
SISTEMA = platform.system()
PACOTES = {
    "ffmpeg": {"brew": "ffmpeg", "apt": "ffmpeg", "winget": "Gyan.FFmpeg"},
    "ffprobe": {"brew": "ffmpeg", "apt": "ffmpeg", "winget": "Gyan.FFmpeg"},
    "node": {"brew": "node", "apt": "nodejs", "winget": "OpenJS.NodeJS.LTS"},
    "whisper-cli": {"brew": "whisper-cpp"},
}
MODELO = "ggml-large-v3-turbo.bin"
URL_MODELO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/" + MODELO
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def ler_req(pasta):
    f = pasta / "scripts" / "requisitos.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def achar_skill(nome):
    for c in (SKILL.parent / nome, DESTINO / nome):
        if (c / "SKILL.md").exists():
            return c
    return None


def juntar_requisitos():
    """Requisitos da skill + das dependências (recursivo). Devolve (req, pastas por nome, faltando)."""
    req = {"programas": set(), "python": {}, "whisper": False, "node": [], "chaves": set()}
    pastas, faltando, fila = {}, [], [SKILL.name]
    while fila:
        nome = fila.pop()
        if nome in pastas:
            continue
        p = SKILL if nome == SKILL.name else achar_skill(nome)
        if not p:
            faltando.append(nome)
            continue
        pastas[nome] = p
        r = ler_req(p)
        req["programas"] |= set(r.get("programas", []))
        req["python"].update(r.get("python", {}))
        req["whisper"] |= bool(r.get("whisper"))
        req["chaves"] |= set(r.get("chaves", []))
        if r.get("node"):
            req["node"].append((nome, r["node"]))
        fila += r.get("depende", [])
    if req["whisper"] and SISTEMA != "Darwin":
        req["python"]["faster_whisper"] = "faster-whisper"
    elif req["whisper"]:
        req["programas"].add("whisper-cli")
    if req["node"]:
        req["programas"].add("node")
    return req, pastas, faltando


def achar_programa(nome):
    c = shutil.which(nome)
    if c:
        return c
    extras = [Path("/opt/homebrew/bin") / nome, Path("/usr/local/bin") / nome]
    if nome == "node":
        extras += sorted(Path.home().glob(".nvm/versions/node/*/bin/node"), reverse=True)
    return next((str(e) for e in extras if e.exists()), None)


def py_do_venv():
    return VENV / ("Scripts/python.exe" if SISTEMA == "Windows" else "bin/python")


def python_bom(mods):
    """Primeiro Python 3.10+ que importa todos os módulos (o do venv, o atual, o do PATH)."""
    cands = [py_do_venv(), Path(sys.executable)] + [Path(p) for p in (achar_programa("python3"),) if p]
    for py in cands:
        if not py.exists():
            continue
        teste = "import sys; assert sys.version_info >= (3, 10)\n" + "".join(f"import {m}\n" for m in mods)
        if subprocess.run([str(py), "-c", teste], capture_output=True).returncode == 0:
            return str(py)
    return None


def achar_modelo():
    env = os.environ.get("WHISPER_MODELO")
    for c in ([Path(env)] if env else []) + [CASA / "modelos" / MODELO, Path.home() / "whisper-models" / MODELO]:
        if c.exists() and c.stat().st_size > 1e9:
            return str(c)
    return None


def chromium_ok():
    bases = [Path.home() / "Library/Caches/ms-playwright", Path.home() / ".cache/ms-playwright",
             Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"]
    return bool(os.environ.get("VIDEO_OPS_CHROME")) or any(
        b.exists() and any(b.glob("chromium*")) for b in bases)


def gerenciador():
    for g in ("brew", "apt-get", "winget"):
        if achar_programa(g):
            return g
    return None


def rodar(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], **kw).returncode == 0


def baixar(url, saida):
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_suffix(".parcial")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total, feito, ultimo = int(r.headers.get("Content-Length", 0)), 0, 0
        while bloco := r.read(1 << 20):
            f.write(bloco)
            feito += len(bloco)
            if total and time.time() - ultimo > 5:
                print(f"  baixando {saida.name}: {feito * 100 // total}%", flush=True)
                ultimo = time.time()
    tmp.rename(saida)


def main():
    instalar, atualizar = "--instalar" in sys.argv, "--atualizar" in sys.argv
    req, pastas, faltando_skill = juntar_requisitos()
    faltas, voce = [], []
    if faltando_skill:
        voce.append(f"skills de que esta depende e que não vieram no zip: {', '.join(faltando_skill)} (baixe na crIAbr)")

    # 1. a skill e as dependências em ~/.claude/skills
    for nome, p in pastas.items():
        alvo = DESTINO / nome
        if p.resolve() == alvo.resolve():
            continue
        if alvo.exists() and not atualizar:
            print(f"· {nome}: já instalada em {alvo} (mantida; --atualizar substitui)")
            continue
        faltas.append(f"copiar a skill {nome} para {alvo}")
        if instalar:
            if alvo.exists():
                guarda = CASA / "antigas" / f"{nome}-{time.strftime('%Y%m%d-%H%M%S')}"
                guarda.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(alvo), str(guarda))
                print(f"  versão anterior guardada em {guarda}")
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(p, alvo, ignore=IGNORAR)
    if instalar:  # daqui em diante vale a cópia instalada
        pastas = {n: (DESTINO / n if (DESTINO / n / "SKILL.md").exists() else p) for n, p in pastas.items()}

    # 2. programas
    g = gerenciador()
    for prog in sorted(req["programas"]):
        if achar_programa(prog):
            continue
        pac = PACOTES.get(prog, {}).get({"apt-get": "apt"}.get(g, g))
        if not pac:
            voce.append(f"instalar {prog} (sem pacote automático para este sistema)")
            continue
        faltas.append(f"instalar {prog} ({g} {pac})")
        if instalar:
            cmd = {"brew": ["brew", "install", pac], "apt-get": ["sudo", "-n", "apt-get", "install", "-y", pac],
                   "winget": ["winget", "install", "-e", "--id", pac]}[g]
            if not rodar(cmd):
                voce.append(f"rodar no terminal: {' '.join(cmd).replace(' -n', '')}")
    if req["programas"] and not g and any(not achar_programa(p) for p in req["programas"]):
        voce.append("instalar um gerenciador de pacotes: no Mac, o Homebrew (https://brew.sh)")

    # 3. Python e bibliotecas
    mods = req["python"] or {"json": "json"}
    py = python_bom(mods)
    if not py:
        faltas.append(f"criar {VENV} com {', '.join(mods.values())}")
        if instalar:
            base = sys.executable if sys.version_info >= (3, 10) else achar_programa("python3")
            if not py_do_venv().exists():
                rodar([base, "-m", "venv", "--system-site-packages", VENV], check=False)
            rodar([py_do_venv(), "-m", "pip", "install", "-q", "--upgrade", "pip"])
            rodar([py_do_venv(), "-m", "pip", "install", "-q", *mods.values()])
            py = python_bom(mods)

    # 4. Whisper (Mac: whisper-cli + modelo ggml; outros: faster-whisper, que baixa o modelo no 1º uso)
    modelo = achar_modelo() if req["whisper"] and SISTEMA == "Darwin" else None
    if req["whisper"] and SISTEMA == "Darwin" and not modelo:
        faltas.append(f"baixar o modelo do Whisper ({MODELO}, 1,6 GB) para {CASA / 'modelos'}")
        if instalar:
            baixar(URL_MODELO, CASA / "modelos" / MODELO)
            modelo = achar_modelo()

    # 5. Node e Chromium do motor (o kit traz o playwright-core em node_modules)
    node = achar_programa("node")
    for nome, cfg in req["node"]:
        kit = pastas[nome] / cfg.get("dir", ".")
        if not (kit / "node_modules").exists():
            faltas.append(f"instalar as dependências Node de {nome}")
            npm = achar_programa("npm") or achar_programa("npm.cmd")  # no Windows o npm é um .cmd
            if instalar and node and npm:
                rodar([npm, "install", "--omit=dev"], cwd=kit)
        if cfg.get("chromium") and not chromium_ok():
            faltas.append("baixar o Chromium headless do motor (~100 MB)")
            if instalar and node:
                rodar([node, kit / "node_modules/playwright-core/cli.js", "install", "chromium-headless-shell"], cwd=kit)

    # 6. chaves opcionais: só avisa
    arqs = [Path.home() / ".config/video-ops/chaves.env", CASA / "chaves.env"]
    texto = "".join(a.read_text(encoding="utf-8", errors="ignore") for a in arqs if a.exists())
    for ch in sorted(req["chaves"]):
        if not os.environ.get(ch) and f"{ch}=" not in texto:
            print(f"· chave opcional {ch} não configurada (ponha em {CASA / 'chaves.env'} se for usar)")

    CASA.mkdir(parents=True, exist_ok=True)
    amb_f = CASA / "ambiente.json"
    amb = json.loads(amb_f.read_text(encoding="utf-8")) if amb_f.exists() else {}
    amb.update({k: v for k, v in {"python": py, "whisper_modelo": modelo, "node": node}.items() if v})
    amb_f.write_text(json.dumps(amb, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")

    if instalar:  # confere de novo depois de instalar
        _, _, _ = juntar_requisitos()
        faltas = [f for f in faltas if "copiar a skill" not in f]
        faltas = [f for f in faltas if not (f.startswith("instalar ") and achar_programa(f.split()[1]))]
        faltas = [f for f in faltas if not (f.startswith("criar ") and py)]
        faltas = [f for f in faltas if not (f.startswith("baixar o modelo") and modelo)]
        faltas = [f for f in faltas if not (f.startswith("baixar o Chromium") and chromium_ok())]
        faltas = [f for f in faltas if not (f.startswith("instalar as dependências Node") and
                                            all((pastas[n] / c.get("dir", ".") / "node_modules").exists() for n, c in req["node"]))]
    print(f"PYTHON={py or ''}")
    if modelo:
        print(f"WHISPER_MODELO={modelo}")
    if faltas or voce:
        print("\nFalta:" if not instalar else "\nAinda falta:")
        for f in faltas:
            print(f"  - {f}" + ("" if instalar else "  (automático com --instalar)"))
        for v in voce:
            print(f"  - {v}  (precisa de você)")
        sys.exit(3)
    print(f"Pronto: {SKILL.name} instalada e com tudo de que precisa.")


if __name__ == "__main__":
    main()
