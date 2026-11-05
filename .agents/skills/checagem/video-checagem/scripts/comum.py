#!/usr/bin/env python3
"""comum.py: o que corpus.py e checar.py compartilham — achar o módulo de transcrição, o projeto e os léxicos."""
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def modulo_palavras():
    """Importa o módulo `palavras` da skill video-transcricao (ao lado desta skill ou já instalada)."""
    cands = [AQUI.parents[1] / "video-transcricao" / "scripts"]
    env = os.environ.get("CLAUDE_SKILLS_DIR")
    if env:
        cands.append(Path(env) / "video-transcricao" / "scripts")
    cands.append(Path.home() / ".claude" / "skills" / "video-transcricao" / "scripts")
    for c in cands:
        if (c / "palavras.py").exists():
            sys.path.insert(0, str(c))
            import palavras
            return palavras
    raise SystemExit("falta insumo: a skill video-transcricao não está instalada "
                     "(rode o preparar.py desta skill)")


def raiz_do_projeto(caminho=None):
    if caminho:
        return Path(caminho).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / "transcricao").is_dir() or (d / "pesquisa").is_dir():
            return d
    return cwd


def gravar_md(caminho, linhas):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(linhas) + "\n"
    caminho.write_text(texto, encoding="utf-8", newline="\n")


MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")

# Palavras que transformam uma frase em acusação sobre alguém. Fora de contexto nenhuma delas prova nada:
# servem só para marcar o trecho como SENSÍVEL, isto é, que não vai ao ar sem fonte conferida.
ACUSACAO = ("fraude", "fraudou", "fraudar", "fraudulento", "corrupção", "corrupto", "propina", "desvio",
            "desviou", "desviar", "roubo", "roubou", "furto", "furtou", "lavagem", "superfaturamento",
            "superfaturou", "crime", "criminoso", "esquema", "quadrilha", "mentiu", "mentira", "mentiroso",
            "falsificou", "falsificação", "sonegou", "sonegação", "suborno", "subornou", "preso", "prisão",
            "condenado", "condenação", "indiciado", "denunciado", "réu", "acusado", "acusação", "acusa",
            "investigado", "investigação", "assédio", "assediou", "agrediu", "agressão", "ameaçou", "ameaça",
            "golpe", "golpista", "enganou", "ilegal", "ilícito", "irregular", "irregularidade", "caixa dois",
            "nepotismo", "laranja", "propinoduto", "traficante", "milícia", "pedofilia", "estupro", "racista")

# "Ele disse que…", "segundo o relatório…": marcam uma citação, que tem de existir na fonte.
VERBOS_DIZER = ("disse", "dizia", "afirmou", "afirmava", "declarou", "contou", "falou", "garantiu", "admitiu",
                "confessou", "escreveu", "respondeu", "revelou", "negou", "confirmou", "informou", "relatou",
                "apontou", "concluiu", "sustentou", "alegou", "prometeu", "anunciou")
MARCAS_CITACAO = ("segundo", "conforme", "de acordo com", "nas palavras de", "citando", "segundo o",
                  "no documento", "no relatório", "na reportagem", "no processo", "no depoimento")
