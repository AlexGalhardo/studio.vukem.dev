#!/usr/bin/env python3
"""Cria (ou completa) a pasta de trabalho deste estilo, pronta para renderizar.

  python3 <skill>/scripts/projeto.py <pasta-do-projeto>
  python3 <skill>/scripts/projeto.py <pasta-do-projeto> --novo 02-nome   duplica o exemplo numa pasta nova

Copia o modelo (lib/, videos/, audio/) para a pasta, confere Node >= 20, ffmpeg e Python com numpy/scipy,
e instala as dependências Node da skill na primeira vez (npm install + Chromium do Playwright, uma vez por
máquina — ficam dentro da skill, não em cada projeto). Vale em Mac, Linux e Windows.
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
FERRAMENTAS = ("comum.py", "renderizar.py", "referencia.py", "commons.py", "recortar.py", "texturas.py")
IGNORAR = {"__pycache__", "node_modules", ".venv", "out", "previews"}


def copiar_modelo(dest):
    """Copia o modelo sem passar por cima do que o usuário já editou (só completa o que falta)."""
    novo = not (dest / "videos").exists()
    for nome in COPIAR:
        origem = PROJETO / nome
        if not origem.exists():
            continue
        for f in origem.rglob("*"):
            rel = f.relative_to(origem)
            if (set(rel.parts) & IGNORAR) or f.name == ".DS_Store":
                continue
            alvo = dest / nome / rel
            if f.is_dir():
                alvo.mkdir(parents=True, exist_ok=True)
            elif not alvo.exists():
                alvo.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, alvo)
    for nome in ("out", "previews", "tools"):
        (dest / nome).mkdir(parents=True, exist_ok=True)
    for f in FERRAMENTAS:
        if (SKILL / "scripts" / f).exists():
            shutil.copy2(SKILL / "scripts" / f, dest / "tools" / f)
    (dest / "tools" / "skill.txt").write_text(SKILL.name + "\n", encoding="utf-8", newline="\n")
    return novo


def duplicar_exemplo(dest, nome):
    """Cópia da pasta do exemplo para começar um vídeo novo (no lugar de `cp -R`, que não existe no Windows)."""
    exemplos = sorted(p for p in (dest / "videos").iterdir() if (p / "index.html").exists())
    origem = next((p for p in exemplos if p.name.startswith("exemplo")), exemplos[0] if exemplos else None)
    if origem is None:
        sys.exit("não achei nenhum exemplo em videos/ para duplicar")
    alvo = dest / "videos" / nome
    if alvo.exists():
        sys.exit(f"já existe: {alvo}")
    shutil.copytree(origem, alvo, ignore=shutil.ignore_patterns(*IGNORAR, "cues.json", ".DS_Store"))
    print(f"videos/{nome} criado a partir de videos/{origem.name}")


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


def cutout_do_mac(dest):
    """Recorte pelo Vision: existe só no Mac e só com o swiftc. Nos outros sistemas o recortar.py
    usa o modo 'fundo' (Pillow + numpy), que não depende de nada além do que já está instalado."""
    fonte = SKILL / "scripts" / "cutout.swift"
    if not fonte.exists():
        return
    binario = dest / "tools" / "cutout"
    if platform.system() != "Darwin":
        print("aviso: o recorte pelo Vision é do macOS; aqui o tools/recortar.py usa --modo fundo")
        return
    if binario.exists():
        return
    swiftc = shutil.which("swiftc")
    if not swiftc:
        print("aviso: sem swiftc (xcode-select --install) — o tools/recortar.py vai usar --modo fundo")
        return
    rodar([swiftc, "-O", str(fonte), "-o", str(binario)])


def chromium_ok():
    """Chromium do Playwright já baixado? (uma vez por máquina, nos três sistemas)"""
    bases = [Path.home() / ".cache/ms-playwright",                        # Linux
             Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright",  # Windows
             Path.home() / "Library/Caches/ms-playwright"]                # só-mac
    return any(b.exists() and any(b.glob("chromium*")) for b in bases)


def main():
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("--"):
        sys.exit("uso: python3 <skill>/scripts/projeto.py <pasta-do-projeto> [--novo <nome>]")
    dest = Path(argv[0]).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    faltas = []
    for prog in ("ffmpeg", "ffprobe"):
        if not achar_programa(prog):
            faltas.append(f"{prog} (rode o preparar.py da skill)")
    node = achar_node()
    if not node:
        faltas.append("Node >= 20 (rode o preparar.py da skill)")
    py = achar_python(("numpy", "scipy"))
    if not py:
        faltas.append("Python 3.10+ com numpy e scipy (rode o preparar.py da skill) — sem ele não sai o áudio")

    novo = copiar_modelo(dest)
    if "--novo" in argv:
        duplicar_exemplo(dest, argv[argv.index("--novo") + 1])
    cutout_do_mac(dest)
    faltas += node_da_skill(node, instalar="--sem-instalar" not in argv)

    print(f"\nprojeto {'criado' if novo else 'atualizado'} em {dest}")
    print(f"NODE={node or ''}")
    print(f"PYTHON={py or ''}")
    exemplos = sorted(p.name for p in (dest / "videos").iterdir() if (p / "index.html").exists())
    if exemplos:
        print(f"\npróximo passo (da pasta do projeto):\n  python3 tools/renderizar.py {exemplos[0]} --preview=6")
    if faltas:
        print("\nFalta:")
        for f in faltas:
            print(f"  - {f}")
        sys.exit(3)
    print("\nPronto: dá para renderizar.")


if __name__ == "__main__":
    main()
