#!/usr/bin/env python3
"""comum.py — o que catalogo.py e motor.py dividem: achar o kit de direção de arte, o Python e o Node da
crIAbr, ler e gravar JSON em utf-8 e falar erro em uma linha. Não é para ser chamado direto."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
shutil.rmtree(Path(__file__).resolve().parent / "__pycache__", ignore_errors=True)

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
VERSAO = (SKILL / "VERSAO").read_text(encoding="utf-8").strip() if (SKILL / "VERSAO").is_file() else "1.0.0"
SAIDA_OK, SAIDA_ERRO, SAIDA_SEM_DA, SAIDA_USO = 0, 1, 2, 64
WINDOWS = platform.system() == "Windows"


class Erro(Exception):
    """Erro com mensagem acionável: o que houve + `dica` (o que fazer) + código de saída."""

    def __init__(self, mensagem: str, dica: str | None = None, codigo: int = SAIDA_ERRO):
        super().__init__(mensagem)
        self.mensagem, self.dica, self.codigo = mensagem, dica, codigo

    def __str__(self) -> str:
        return self.mensagem if not self.dica else f"{self.mensagem}\n{self.dica}"


def diz(*partes, erro: bool = False) -> None:
    print(*partes, file=sys.stderr if erro else sys.stdout, flush=True)


# ──────────────────────────────────────────────────────────── kit, python, node ──
def kit() -> Path:
    """Pasta do kit de direção de arte, achada pela posição desta skill (nunca por caminho embutido).

    Vale primeiro o kit COMPLETO (com o node_modules do motor): uma cópia pela metade ao lado desta skill não
    pode ganhar da instalada em ~/.claude/skills, senão o render morre dizendo que falta o playwright."""
    achados = [k for k in (SKILL.parent / "video-direcao-de-arte" / "kit",
                           Path("~/.claude/skills/video-direcao-de-arte/kit").expanduser())
               if (k / "da.py").is_file()]
    for k in achados:
        if (k / "node_modules" / "playwright-core").is_dir():
            return k
    if achados:
        return achados[0]
    raise Erro("não achei o kit de direção de arte (video-direcao-de-arte/kit/da.py) ao lado desta skill.",
               "Instale a skill video-direcao-de-arte (ela vem no mesmo zip): sem ela nada é renderizado.",
               SAIDA_SEM_DA)


def casa_criabr() -> Path:
    """Pasta da crIAbr (~/.criabr; CRIABR_CASA muda): ambiente.json escrito pelo preparar.py."""
    return Path(os.environ.get("CRIABR_CASA") or Path.home() / ".criabr").expanduser()


def _ambiente() -> dict:
    try:
        return json.loads((casa_criabr() / "ambiente.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def python_do_kit() -> str:
    """Python 3.10+ com Pillow e numpy (o que o kit exige): o de ~/.criabr/ambiente.json, senão o venv da
    crIAbr, senão este mesmo interpretador."""
    venv = casa_criabr() / "venv" / ("Scripts" if WINDOWS else "bin") / ("python.exe" if WINDOWS else "python")
    for c in (_ambiente().get("python"), venv):
        if c and Path(c).is_file():
            return str(c)
    return sys.executable


def node() -> str:
    """Node ≥ 20 (lê o catálogo das cenas). Erro acionável quando não há."""
    n = _ambiente().get("node")
    if n and Path(n).is_file():
        return str(n)
    n = shutil.which("node")
    if not n:
        raise Erro("não achei o Node (preciso dele para ler o catálogo das cenas).",
                   "Rode o preparar.py desta skill (com --instalar, depois do ok do usuário).")
    return n


# ────────────────────────────────────────────────────────────────── projeto ──
PASTAS = ("animacoes", "transcricao", "som", "qa", "da")


def projeto(caminho=None) -> Path:
    """Pasta do projeto do usuário (a que tem da/da.json). Sem argumento, a pasta atual."""
    p = Path(caminho).expanduser().resolve() if caminho else Path.cwd().resolve()
    if not p.is_dir():
        raise Erro(f"a pasta do projeto não existe: {p}", codigo=SAIDA_USO)
    if not (p / "da" / "da.json").is_file():
        raise Erro(f"{p} não tem direção de arte (da/da.json).",
                   "Crie-a com a skill video-direcao-de-arte antes de desenhar qualquer cena.", SAIDA_SEM_DA)
    return p


def ler_json(caminho: Path, oque: str = "arquivo"):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Erro(f"não achei o {oque}: {caminho}")
    except json.JSONDecodeError as e:
        raise Erro(f"{oque} com JSON inválido ({caminho}): linha {e.lineno}, coluna {e.colno}: {e.msg}")


def gravar_json(caminho: Path, dados) -> Path:
    """Grava JSON em utf-8 com quebra \\n (nunca CRLF) e acento de verdade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    corpo = json.dumps(dados, ensure_ascii=False, indent=1) + "\n"
    caminho.write_text(corpo, encoding="utf-8", newline="\n")
    return caminho


def rodar_programa(cmd, cwd=None, capturar: bool = True) -> subprocess.CompletedProcess:
    """subprocess.run com LISTA de argumentos e texto em utf-8 — nunca pelo shell do sistema."""
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, check=False,
                          capture_output=capturar, text=True, encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────── pequenas utilidades ──
_ILEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def nome_de_arquivo(texto: str, maximo: int = 40) -> str:
    """Nome de arquivo que serve nos três sistemas: sem acento, sem maiúscula e sem : ? * " < > |."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    s = _ILEGAL.sub("-", s)
    return (re.sub(r"[^a-z0-9._-]+", "-", s).strip("-._") or "cena")[:maximo].strip("-._")


def mmss(s) -> str:
    s = max(0.0, float(s or 0))
    return f"{int(s // 60):02d}:{s % 60:05.2f}"


_ARGPARSE_PT = (("the following arguments are required", "faltou informar"), ("unrecognized arguments", "opção desconhecida"),
                ("invalid choice", "valor inválido"), ("choose from", "opções"), ("expected one argument", "faltou o valor"),
                ("invalid float value", "número inválido"), ("invalid int value", "número inteiro inválido"),
                ("argument ", "argumento "), ("is required", "é obrigatório"))


class Parser(argparse.ArgumentParser):
    """argparse com erro de uso em português, código 64 e sem traceback."""

    def error(self, message):
        for en, pt in _ARGPARSE_PT:
            message = message.replace(en, pt)
        print(f"erro de uso: {message}\nVeja: {self.prog} --help", file=sys.stderr)
        sys.exit(SAIDA_USO)

    def format_help(self):
        return super().format_help().replace("usage:", "uso:").replace("positional arguments:", "argumentos:") \
            .replace("options:", "opções:").replace("show this help message and exit", "mostra esta ajuda e sai")


def rodar(principal) -> int:
    """Executa a função principal de um script traduzindo exceção em mensagem de uma linha + código de saída."""
    try:
        return int(principal() or 0)
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        return e.codigo
    except KeyboardInterrupt:
        print("interrompido.", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
    except Exception as e:
        if os.environ.get("DA_DEBUG") == "1":
            raise
        print(f"erro interno: {type(e).__name__}: {e} (DA_DEBUG=1 mostra o traceback)", file=sys.stderr)
        return SAIDA_ERRO
