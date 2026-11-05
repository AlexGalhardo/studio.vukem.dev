#!/usr/bin/env python3
"""Cria (ou completa) a pasta de trabalho deste estilo, pronta para renderizar.

  python3 <skill>/scripts/projeto.py <pasta-do-projeto>

Copia o modelo (lib/, videos/, audio/) para a pasta, deixa as ferramentas em tools/, confere Node >= 20,
ffmpeg e Python com numpy/scipy/Pillow, e instala as dependências Node da skill na primeira vez
(npm install + Chromium do Playwright, uma vez por máquina — ficam dentro da skill, não em cada projeto).
No macOS compila o recortador do Vision (cutout.swift) em tools/cutout; nos outros sistemas avisa que o
recorte tem de vir pronto de fora (ver tools/recortar.py).
Saídas: 0 pronto · 3 falta algo · 1 erro.
"""
import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import PROJETO, SKILL, achar_node, achar_programa, achar_python, rodar  # noqa: E402

COPIAR = ("lib", "videos", "audio")
NAO_SAO_FERRAMENTA = {"projeto.py", "preparar.py"}


def ferramentas():
    """Todo .py de scripts/ que o usuário roda da pasta do projeto (tools/)."""
    return sorted(f for f in (SKILL / "scripts").glob("*.py") if f.name not in NAO_SAO_FERRAMENTA)


def copiar_modelo(dest):
    """Copia o modelo sem passar por cima do que o usuário já editou (só completa o que falta)."""
    novo = not (dest / "videos").exists()
    for nome in COPIAR:
        origem = PROJETO / nome
        if not origem.exists():
            continue
        for f in origem.rglob("*"):
            rel = f.relative_to(origem)
            if set(rel.parts) & {"__pycache__", "node_modules", ".venv"} or f.name == ".DS_Store":
                continue
            alvo = dest / nome / rel
            if f.is_dir():
                alvo.mkdir(parents=True, exist_ok=True)
            elif not alvo.exists():
                alvo.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, alvo)
    for nome in ("out", "previews", "tools"):
        (dest / nome).mkdir(parents=True, exist_ok=True)
    for f in ferramentas():
        shutil.copy2(f, dest / "tools" / f.name)
    ne = SKILL / "scripts" / "ne"                      # vetores de domínio público (quem usa globo.py)
    if ne.is_dir():
        (dest / "tools" / "ne").mkdir(parents=True, exist_ok=True)
        for g in ne.glob("*.geojson"):
            shutil.copy2(g, dest / "tools" / "ne" / g.name)
    (dest / "tools" / "skill.txt").write_text(SKILL.name + "\n", encoding="utf-8", newline="\n")
    return novo


def cutout(dest):
    """Recortador por Vision: só existe no macOS. Devolve o aviso a mostrar, ou ''."""
    fonte = SKILL / "scripts" / "cutout.swift"
    if not fonte.exists():
        return ""
    alvo = dest / "tools" / ("cutout.exe" if platform.system() == "Windows" else "cutout")
    if platform.system() != "Darwin":
        return ("o recorte automático de imagem (Vision) só existe no macOS — "
                "recorte em outro programa e salve PNG com alfa (tools/recortar.py explica)")
    if alvo.exists():
        return ""
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return "swiftc (Xcode Command Line Tools) para compilar o recorte por Vision — sem ele, recorte por fora"
    rodar([swiftc, "-O", str(fonte), "-o", str(alvo)])
    return "" if alvo.exists() else "não consegui compilar o cutout.swift — recorte por fora"


def node_da_skill(node, instalar=True):
    """Garante node_modules e Chromium dentro da skill. Devolve a lista do que ainda falta."""
    faltas = []
    if not (PROJETO / "node_modules").exists():
        npm = achar_programa("npm") or shutil.which("npm.cmd")
        if instalar and node and npm:
            rodar([npm, "install", "--omit=dev", "--no-audit", "--no-fund"], cwd=PROJETO)
        if not (PROJETO / "node_modules").exists():
            faltas.append("as bibliotecas Node (gsap, playwright) — rode o preparar.py --instalar")
    cli = PROJETO / "node_modules" / "playwright-core" / "cli.js"
    if not chromium_ok():
        if instalar and node and cli.exists():
            rodar([node, str(cli), "install", "chromium-headless-shell"], cwd=PROJETO)
        if not chromium_ok():
            faltas.append("o Chromium do Playwright (~100 MB) — rode o preparar.py --instalar")
    return faltas


def chromium_ok():
    """Chromium do Playwright já baixado? (uma vez por máquina, nos três sistemas)"""
    bases = [Path.home() / ".cache/ms-playwright",                        # Linux
             Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright",  # Windows
             Path.home() / "Library/Caches/ms-playwright"]                # só-mac
    return any(b.exists() and any(b.glob("chromium*")) for b in bases)


def main():
    if len(sys.argv) < 2:
        sys.exit("uso: python3 <skill>/scripts/projeto.py <pasta-do-projeto>")
    dest = Path(sys.argv[1]).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    faltas = []
    for prog in ("ffmpeg", "ffprobe"):
        if not achar_programa(prog):
            faltas.append(f"{prog} (rode o preparar.py da skill)")
    node = achar_node()
    if not node:
        faltas.append("Node >= 20 (rode o preparar.py da skill)")
    py = achar_python(("numpy", "scipy", "PIL"))
    if not py:
        faltas.append("Python 3.10+ com numpy, scipy e Pillow (rode o preparar.py da skill)")

    novo = copiar_modelo(dest)
    faltas += node_da_skill(node, instalar="--sem-instalar" not in sys.argv)
    aviso = cutout(dest)

    print(f"\nprojeto {'criado' if novo else 'atualizado'} em {dest}")
    print(f"NODE={node or ''}")
    print(f"PYTHON={py or ''}")
    exemplos = sorted(p.name for p in (dest / "videos").iterdir() if (p / "index.html").exists())
    if exemplos:
        print(f"\npróximo passo (da pasta do projeto):\n  python3 tools/renderizar.py {exemplos[0]} --preview=6")
    if aviso:
        print(f"\nAviso: {aviso}")
    if faltas:
        print("\nFalta:")
        for f in faltas:
            print(f"  - {f}")
        sys.exit(3)
    print("\nPronto: dá para renderizar.")


if __name__ == "__main__":
    main()
