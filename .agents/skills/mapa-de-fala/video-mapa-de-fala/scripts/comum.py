#!/usr/bin/env python3
"""comum.py: o que mapa.py e nomes.py compartilham — achar o módulo de transcrição, o projeto e os léxicos.

Nada aqui decide nada sobre o conteúdo: só mede, conta e separa. A leitura (quem é a pessoa, o que a prova
prova, o que o improviso mudou) é do Claude, lendo o que estes arquivos trazem.
"""
import json
import os
import re
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
    """A pasta do projeto: a passada, ou a primeira acima daqui que tenha transcricao/."""
    if caminho:
        return Path(caminho).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / "transcricao").is_dir():
            return d
    return cwd


def ler_texto(caminho):
    return Path(caminho).read_text(encoding="utf-8", errors="replace")


def gravar_md(caminho, linhas):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(linhas) + "\n"
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def limpar_roteiro(texto):
    """Tira do roteiro o que não é fala: marcação de produção, cabeçalho, link, comentário."""
    texto = re.sub(r"\[[^\]]*\]|\{[^}]*\}|<!--.*?-->|https?://\S+", " ", texto, flags=re.S)
    linhas = []
    for linha in texto.splitlines():
        if re.match(r"^\s*(#{1,6}\s|>|\||```|---+\s*$)", linha):
            continue
        linha = re.sub(r"^\s*[-*+]\s+|^\s*\d+[.)]\s+", "", linha)
        linha = re.sub(r"\*\*|__|\*|`", "", linha)
        if re.match(r"^\s*[A-ZÀ-Ý][A-ZÀ-Ý \t]{1,30}:\s*", linha):        # rótulo de quem fala
            linha = re.sub(r"^\s*[A-ZÀ-Ý][A-ZÀ-Ý \t]{1,30}:\s*", "", linha)
        if linha.strip():
            linhas.append(linha.strip())
    return "\n".join(linhas)


def frases_do_roteiro(texto):
    """[(numero_da_linha, frase)] do roteiro limpo, uma frase por item."""
    saida = []
    for i, linha in enumerate(limpar_roteiro(texto).splitlines(), 1):
        for f in re.split(r"(?<=[.!?…])\s+", linha):
            f = f.strip()
            if len(re.findall(r"\w+", f)) >= 3:
                saida.append((i, f))
    return saida


# --------------------------------------------------------------------------- léxicos (candidatos, não verdades)
MULETAS = ("né", "tipo", "assim", "então", "aí", "cara", "tá", "sabe", "olha", "bom", "enfim", "véi", "mano",
           "basicamente", "literalmente", "obviamente", "inclusive", "beleza", "pô", "putz", "hum", "ah", "eh")

PROVAS = ("documento", "documentos", "planilha", "planilhas", "foto", "fotos", "vídeo", "vídeos", "áudio",
          "áudios", "print", "prints", "captura", "e-mail", "email", "mensagem", "mensagens", "contrato",
          "contratos", "nota", "notas", "recibo", "recibos", "extrato", "extratos", "relatório", "relatórios",
          "laudo", "laudos", "processo", "processos", "depoimento", "depoimentos", "gravação", "gravações",
          "ata", "atas", "edital", "editais", "parecer", "pareceres", "certidão", "certidões", "boletim",
          "ofício", "ofícios", "petição", "escritura", "registro", "registros", "comprovante", "comprovantes",
          "arquivo", "arquivos", "reportagem", "matéria", "entrevista", "transcrição", "print-screen")

LUGARES = ("rua", "avenida", "bairro", "cidade", "estado", "país", "praça", "prédio", "edifício", "sede",
           "escritório", "fábrica", "galpão", "loja", "hotel", "aeroporto", "porto", "fazenda", "sítio",
           "apartamento", "casa", "condomínio", "hospital", "escola", "universidade", "delegacia", "fórum",
           "tribunal", "câmara", "assembleia", "prefeitura", "ministério", "secretaria", "agência", "banco")

TEMPO_RELATIVO = ("ontem", "hoje", "amanhã", "semana", "mês", "ano", "década", "década", "véspera", "madrugada")

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")

NUM_PALAVRA = ("um", "uma", "dois", "duas", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
               "onze", "doze", "treze", "quatorze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito",
               "dezenove", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta",
               "noventa", "cem", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "mil",
               "milhão", "milhões", "bilhão", "bilhões", "trilhão", "trilhões", "metade", "dobro", "terço")

DINHEIRO = ("reais", "real", "dólar", "dólares", "euro", "euros", "centavos", "r$", "us$", "mil", "milhão",
            "milhões", "bilhão", "bilhões")

ACUSACAO = ("fraude", "fraudou", "fraudar", "corrupção", "corrupto", "propina", "desvio", "desviou", "roubo",
            "roubou", "furto", "lavagem", "caixa dois", "superfaturamento", "superfaturou", "crime",
            "criminoso", "esquema", "quadrilha", "organização criminosa", "mentiu", "mentira", "falsificou",
            "falsificação", "sonegou", "sonegação", "suborno", "subornou", "preso", "prisão", "condenado",
            "condenação", "indiciado", "denunciado", "réu", "acusado", "acusação", "investigado", "assédio",
            "agrediu", "agressão", "ameaçou", "ameaça", "golpe", "enganou", "ilegal", "ilícito", "irregular")


def tem_termo(texto_normalizado, termos, normaliza):
    """Quais `termos` aparecem no texto já normalizado (comparação por palavra inteira)."""
    achados = []
    for t in termos:
        n = normaliza(t)
        if n and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", texto_normalizado):
            achados.append(t)
    return achados


def carregar_banco(caminho):
    """Banco de nomes: lista de textos ou {"pessoas": [...], "organizacoes": [...], "lugares": [...]}."""
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if isinstance(d, list):
        d = {"pessoas": d}
    saida = {}
    for grupo in ("pessoas", "organizacoes", "lugares", "outros"):
        itens = []
        for x in d.get(grupo, []):
            if isinstance(x, str):
                itens.append({"nome": x, "variantes": [], "papel": ""})
            else:
                itens.append({"nome": x.get("nome", ""), "papel": x.get("papel", ""),
                              "variantes": list(x.get("variantes", []))})
        saida[grupo] = [i for i in itens if i["nome"]]
    return saida
