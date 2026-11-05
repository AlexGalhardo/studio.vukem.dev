#!/usr/bin/env python3
"""Roda o motor de render (render.mjs) com o Node certo e pela trava de memória.

Da pasta do projeto:
  python3 tools/renderizar.py <prefixo> --preview=6        folha de conferência em previews/
  python3 tools/renderizar.py <prefixo> --at=0.4,2.1,3.3   quadros nos instantes pedidos
  python3 tools/renderizar.py <prefixo>                    vídeo inteiro em out/
  python3 tools/renderizar.py <prefixo> --fmt=16x9         um formato só

O motor e as bibliotecas Node ficam dentro da skill; a pasta do projeto só tem lib/, videos/ e audio/
(o render.mjs serve o node_modules da skill para a página). Saídas: 0 ok · 1 falhou · 3 falta dependência.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import achar_node, com_trava, rodar  # noqa: E402


def achar_motor():
    """render.mjs: na skill ao lado deste script ou na skill nomeada em tools/skill.txt."""
    aqui = Path(__file__).resolve().parent
    cands = [aqui.parent / "assets" / "projeto" / "render.mjs"]     # este script rodando de dentro da skill
    marca = aqui / "skill.txt"
    if marca.exists():                                               # tools/ copiado para o projeto do usuário
        skills = Path(os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills"))
        nome = marca.read_text(encoding="utf-8").strip()
        cands.insert(0, skills / nome / "assets" / "projeto" / "render.mjs")
    return next((c for c in cands if c.exists()), None)


def main():
    motor = achar_motor()
    if not motor:
        print("Falta: a skill instalada em ~/.claude/skills (rode o preparar.py dela com --instalar)")
        sys.exit(3)
    node = achar_node()
    if not node:
        print("Falta: Node >= 20 (rode o preparar.py da skill com --instalar)")
        sys.exit(3)
    if not (motor.parent / "node_modules").exists():
        print("Falta: as bibliotecas Node da skill (rode o preparar.py dela com --instalar)")
        sys.exit(3)
    sys.exit(rodar(com_trava([node, str(motor), *sys.argv[1:]]), cwd=Path.cwd()).returncode)


if __name__ == "__main__":
    main()
