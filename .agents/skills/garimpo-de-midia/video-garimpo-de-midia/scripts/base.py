#!/usr/bin/env python3
"""base.py — o que os scripts do garimpo dividem: erro com dica, raiz do projeto, módulos das skills vizinhas
(video-broll e video-pauta-midia, achados pela POSIÇÃO desta pasta) e a pausa entre pedidos.

Só biblioteca padrão. Nada aqui baixa coisa alguma."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
SKILLS = AQUI.parents[1]
VERSAO = "1.0.0"
OK, ERRO, SEM_DA, USO, SEM_REDE = 0, 1, 2, 64, 75
PASTA = Path("broll") / "garimpo"


class Erro(Exception):
    """Erro com mensagem (o que houve) e dica (o que fazer)."""

    def __init__(self, mensagem: str, dica: str | None = None, codigo: int = ERRO):
        super().__init__(mensagem)
        self.mensagem, self.dica, self.codigo = mensagem, dica, codigo


def diz(*partes, erro: bool = False) -> None:
    print(*partes, file=sys.stderr if erro else sys.stdout, flush=True)


# ─────────────────────────────────────────────────────────────── skills vizinhas ──
def _vizinha(skill: str, sub: str, arquivo: str) -> Path:
    """A pasta <skill>/<sub> que tem <arquivo>, ao lado desta skill ou em ~/.claude/skills."""
    for raiz in (SKILLS, Path("~/.claude/skills").expanduser()):
        pasta = raiz / skill / sub
        if (pasta / arquivo).is_file():
            return pasta
    raise Erro(f"não achei {skill}/{sub}/{arquivo} ao lado desta skill.",
               f"Instale a skill {skill} em ~/.claude/skills/ — o garimpo não reimplementa provedor: ele chama a {skill}.")


def broll():
    """Módulos da video-broll: (comum, provedores, buscar, baixar). É quem fala com os provedores."""
    pasta = str(_vizinha("video-broll", "scripts", "buscar.py"))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    import baixar
    import buscar
    import comum
    import provedores
    return comum, provedores, buscar, baixar


def registro():
    """Módulo registro.py da video-broll (dono de broll/licencas.json e broll/creditos.md)."""
    pasta = str(_vizinha("video-broll", "scripts", "registro.py"))
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    try:
        import registro as modulo
    except ImportError as e:                      # registro.py ainda usa trava de arquivo de Unix
        raise Erro(f"o registro de licenças da video-broll não importou neste sistema ({e}).",
                   "Atualize a skill video-broll; até lá, registre as licenças pela própria video-broll "
                   "(scripts/registro.py) na máquina em que ela roda.")
    return modulo


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude/skills/video-direcao-de-arte/kit/trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def programa(nome: str) -> str:
    exe = shutil.which(nome)
    if not exe:
        raise Erro(f"não achei o programa {nome} no PATH.", "Rode o preparar.py desta skill (e --instalar com o ok do usuário).")
    return exe


# ───────────────────────────────────────────────────────────────────── projeto ──
def achar_projeto(arg=None) -> Path:
    """--projeto, ou a primeira pasta acima da atual com da/da.json, broll/licencas.json ou roteiro/pauta.json."""
    if arg:
        p = Path(str(arg)).expanduser()
        if not p.is_dir():
            raise Erro(f"a pasta do projeto não existe: {p}", "Passe a raiz do projeto em --projeto.", SEM_DA)
        return p.resolve()
    aqui = Path.cwd().resolve()
    for p in (aqui, *aqui.parents):
        if any((p / x).is_file() for x in ("da/da.json", "broll/licencas.json", "roteiro/pauta.json")):
            return p
    return aqui


def ler_json(arq: Path, padrao=None):
    if not Path(arq).is_file():
        return padrao
    try:
        return json.loads(Path(arq).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Erro(f"{arq}: JSON inválido ({e}).", "Conserte o arquivo à mão ou apague-o para recomeçar.")


def gravar_json(arq: Path, dados) -> Path:
    arq = Path(arq)
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".parcial")
    texto = json.dumps(dados, ensure_ascii=False, indent=1) + "\n"
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    tmp.replace(arq)
    return arq


def gravar_texto(arq: Path, texto: str) -> Path:
    arq = Path(arq)
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".parcial")
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    tmp.replace(arq)
    return arq


# ───────────────────────────────────────────────────────────── pausa entre pedidos ──
_ULTIMO = [0.0]


def respirar(segundos: float, motivo: str = "", avisar=None) -> float:
    """Espera `segundos` desde o pedido anterior. É o que evita bloqueio por excesso de consultas.
    Devolve quanto esperou de fato (0 quando já tinha passado tempo suficiente)."""
    if segundos <= 0:
        _ULTIMO[0] = time.monotonic()
        return 0.0
    falta = segundos - (time.monotonic() - _ULTIMO[0]) if _ULTIMO[0] else 0.0
    if falta > 0:
        if avisar and falta >= 1.0:
            avisar(f"  · pausa de {falta:.1f} s antes do próximo pedido{(' (' + motivo + ')') if motivo else ''}")
        time.sleep(falta)
    _ULTIMO[0] = time.monotonic()
    return max(0.0, falta)


# ───────────────────────────────────────────────────────────────────────── CLI ──
class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        diz(f"{self.prog}: {message}", erro=True)
        sys.exit(USO)


def rodar(principal) -> int:
    try:
        return principal() or OK
    except Erro as e:
        diz(f"ERRO: {e.mensagem}", erro=True)
        if e.dica:
            diz(f"→ {e.dica}", erro=True)
        return e.codigo
    except KeyboardInterrupt:
        diz("\ninterrompido.", erro=True)
        return 130


def ambiente(nome: str) -> str | None:
    v = os.environ.get(nome)
    return v.strip() or None if isinstance(v, str) else None
