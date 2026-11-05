#!/usr/bin/env python3
"""identidade.py — confere se a pessoa pedida é mesmo a pessoa da foto, pela LEGENDA DA FONTE.

Foto de pessoa é o garimpo que mais erra: o banco devolve «homem de terno» para o nome de alguém, ou a foto de um
xará. Esta conferência é de texto: só o que o provedor escreveu (título, descrição, nome do arquivo, categorias)
vale como prova. Reconhecimento facial não entra aqui — o garimpo não baixa nada para olhar.

    import identidade
    identidade.conferir("Maria Antunes Ribeiro", candidato)
    → {"veredito": "confere" | "duvida" | "nao_confere", "porque": "...", "trecho": "...", "pontos": 0.9}

Vereditos:
  confere      a legenda traz o nome completo (ou sobrenome + ao menos um nome), sem outra pessoa nomeada no lugar
  duvida       traz só o sobrenome, só o primeiro nome, ou traz marca de representação (ator, ilustração, sósia…)
  nao_confere  a legenda não traz o nome, ou nomeia outra pessoa

Só biblioteca padrão."""
from __future__ import annotations

import re
import unicodedata

# partículas e títulos que não identificam ninguém
PARTICULAS = {"de", "da", "do", "das", "dos", "e", "del", "della", "di", "van", "von", "der", "la", "le", "den", "bin", "al"}
TITULOS = {"dr", "dra", "sr", "sra", "prof", "profa", "eng", "min", "sen", "dep", "gov", "pres", "mr", "mrs", "ms"}
# a legenda diz que aquilo NÃO é a pessoa (ou é uma representação dela)
REPRESENTACAO = re.compile(
    r"(?i)\b(sosia|sósia|look-?alike|impersonator|ator|atriz|actor|actress|interpreta|interpretado|retrato falado|"
    r"ilustracao|ilustração|illustration|caricatura|caricature|estatua|estátua|statue|busto|bust|boneco|efigie|efígie|"
    r"desenho|drawing|pintura|painting|montagem|recriacao|recriação|reenactment|representacao|representação|"
    r"imagem ilustrativa|foto ilustrativa|generated|gerada por|ia generativa)\b")
# a legenda fala de uma pessoa qualquer, não de alguém nomeado
GENERICO = re.compile(r"(?i)\b(homem|mulher|pessoa|man|woman|person|people|businessman|businesswoman|executivo|modelo|model)\b")
RE_NOME = re.compile(r"\b([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][\wÀ-ÿ'’-]{1,})(?:\s+(?:de|da|do|das|dos|e|van|von|del|di|la|le)\s+|\s+)"
                     r"([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][\wÀ-ÿ'’-]{2,})(?:\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][\wÀ-ÿ'’-]{2,}))?")


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def normalizar(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", sem_acento(str(s)).lower())


def partes_do_nome(nome: str) -> list[str]:
    """Tokens que identificam: fora partículas, títulos e iniciais soltas ("J.")."""
    return [t for t in normalizar(nome).split() if len(t) > 1 and t not in PARTICULAS and t not in TITULOS]


def legenda_do_candidato(c: dict) -> str:
    """A legenda da FONTE: o que o provedor escreveu sobre o item. O autor (quem fotografou) fica de fora —
    confundir fotógrafo com retratado é como entra foto errada."""
    campos = (c.get("titulo"), c.get("descricao"), c.get("legenda"), c.get("nome_arquivo"),
              " ".join(c.get("categorias") or []) if isinstance(c.get("categorias"), list) else c.get("categorias"),
              " ".join(c.get("tags") or []) if isinstance(c.get("tags"), list) else c.get("tags"))
    return " · ".join(str(x).strip() for x in campos if x)


def _nomes_na_legenda(legenda: str) -> list[tuple[str, list[str]]]:
    """Nomes próprios completos escritos na legenda: (como está escrito, tokens que identificam)."""
    saida = []
    for m in RE_NOME.finditer(str(legenda)):
        escrito = " ".join(x for x in m.groups() if x)
        toks = partes_do_nome(escrito)
        if len(toks) >= 2:
            saida.append((escrito, toks))
    return saida


def conferir(nome: str, candidato: dict) -> dict:
    """Veredito sobre a identidade da pessoa no candidato, pela legenda da fonte."""
    partes = partes_do_nome(nome or "")
    legenda = legenda_do_candidato(candidato)
    alvo = normalizar(legenda)
    if not partes:
        return {"veredito": "duvida", "porque": "não veio nome para conferir", "trecho": legenda[:200], "pontos": 0.0}
    if not alvo.strip():
        return {"veredito": "nao_confere", "porque": "a fonte não publicou legenda nenhuma: não há como saber quem está na foto",
                "trecho": "", "pontos": 0.0}
    tokens = set(alvo.split())
    presentes = [p for p in partes if p in tokens]
    primeiro, sobrenome = partes[0], partes[-1]
    pontos = round(len(presentes) / len(partes), 2)
    marca = REPRESENTACAO.search(legenda)
    nomes = _nomes_na_legenda(legenda)
    # xará ou parente: a legenda escreve um nome completo com O MESMO SOBRENOME e OUTRO primeiro nome
    rivais = [escrito for escrito, n in nomes if sobrenome in n and n[0] != primeiro]
    estranhos = [escrito for escrito, n in nomes if not (set(n) & set(partes))]

    if len(presentes) == len(partes) or (primeiro in presentes and sobrenome in presentes):
        if marca:
            return {"veredito": "duvida", "porque": f"a legenda traz o nome, mas também «{marca.group(0)}»: pode ser representação, não a pessoa",
                    "trecho": legenda[:200], "pontos": pontos}
        if rivais:
            return {"veredito": "duvida", "porque": f"a legenda traz o nome pedido e também «{rivais[0]}»: confira quem é quem na foto",
                    "trecho": legenda[:200], "pontos": pontos}
        return {"veredito": "confere", "porque": f"a legenda da fonte traz {'o nome completo' if len(presentes) == len(partes) else 'o primeiro nome e o sobrenome'}",
                "trecho": legenda[:200], "pontos": pontos}
    if rivais:
        return {"veredito": "duvida", "porque": f"a legenda nomeia «{rivais[0]}», mesmo sobrenome e outro primeiro nome: xará ou parente",
                "trecho": legenda[:200], "pontos": pontos}
    if estranhos:
        return {"veredito": "nao_confere", "porque": f"a legenda nomeia outra pessoa: «{estranhos[0]}»", "trecho": legenda[:200], "pontos": pontos}
    if sobrenome in presentes:
        return {"veredito": "duvida", "porque": f"a legenda traz só o sobrenome «{sobrenome}»: pode ser xará ou parente",
                "trecho": legenda[:200], "pontos": pontos}
    if presentes:
        return {"veredito": "duvida", "porque": f"a legenda traz só «{presentes[0]}», sem o sobrenome", "trecho": legenda[:200], "pontos": pontos}
    if GENERICO.search(legenda):
        return {"veredito": "nao_confere", "porque": "a legenda descreve uma pessoa genérica, não a pessoa pedida",
                "trecho": legenda[:200], "pontos": 0.0}
    return {"veredito": "nao_confere", "porque": "o nome pedido não aparece na legenda da fonte", "trecho": legenda[:200], "pontos": 0.0}


def anotar(nome: str, candidatos: list[dict]) -> list[dict]:
    """Põe `identidade` em cada candidato e devolve a lista na ordem confere → duvida → nao_confere."""
    ordem = {"confere": 0, "duvida": 1, "nao_confere": 2}
    for c in candidatos:
        c["identidade"] = conferir(nome, c)
    return sorted(candidatos, key=lambda c: (ordem[c["identidade"]["veredito"]], -c["identidade"]["pontos"], c.get("n", 0)))


if __name__ == "__main__":                                   # conferência rápida pela linha de comando
    import json
    import sys
    if len(sys.argv) < 3:
        print('uso: identidade.py "Nome da Pessoa" "legenda da fonte"', file=sys.stderr)
        raise SystemExit(64)
    print(json.dumps(conferir(sys.argv[1], {"titulo": sys.argv[2]}), ensure_ascii=False, indent=1))
