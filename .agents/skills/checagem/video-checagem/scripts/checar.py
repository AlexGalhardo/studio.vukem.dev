#!/usr/bin/env python3
"""checar.py: compara o que foi DITO com a pesquisa e os documentos.

  python3 checar.py [--projeto .] [--fatos pesquisa/fatos.json] [--documentos pesquisa/ docs/laudo.pdf]

Procura, com evidência e tempo (mm:ss): número que não bate com a fonte, citação que não existe na fonte,
fato que na fonte é de OUTRO caso, atribuição trocada (o dado é de X e foi dito de Y), afirmação sem apoio
nenhum, fato ainda não confirmado ou já vencido na ficha de pesquisa. Marca «sensível» todo trecho que junta
pessoa com acusação.

Grava `qa/checagem.json` e `qa/checagem.md`.

Isto é uma PENEIRA, não um veredito: tudo que sai daqui é suspeita com a evidência ao lado, para alguém abrir
a fonte e decidir. Nenhum item vira correção automática no texto nem no vídeo.

Códigos de saída: 0 nada a apontar · 1 há itens para resolver · 2 falta insumo.
"""
import argparse
import datetime as dt
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402
import corpus as K  # noqa: E402

P = C.modulo_palavras()

TOL = 0.005          # 0,5% de diferença ainda é o mesmo número
TOL_APROX = 0.10     # "cerca de", "quase": 10%
IGUAL_CITACAO = 0.85
MIN_CITACAO = 0.60
MIN_FRASE = 0.72     # semelhança da frase inteira com a passagem para considerar "é o mesmo assunto"
TIPOS_CHECAVEIS = ("dinheiro", "percentual", "ano", "data")
RX_ASPAS = re.compile(r"[\"“”«»]([^\"“”«»]{12,400})[\"“”«»]")

ACOES = {
    "numero_divergente": "abra a fonte e confira o número; se a fonte estiver certa, regrave ou corte a frase",
    "citacao_nao_encontrada": "ache a citação na fonte; sem o trecho literal, não vá ao ar com aspas",
    "citacao_diferente": "compare palavra por palavra: aspas só para o que está escrito na fonte",
    "fato_de_outro_caso": "confira de quem é o dado na fonte antes de usar nesta parte",
    "atribuicao_trocada": "o dado está na fonte, mas ligado a outro nome: conserte a atribuição",
    "sem_apoio": "não achei esse dado na pesquisa nem nos documentos: pesquise ou tire do vídeo",
    "pessoa_com_acusacao": "trecho sensível: só vai ao ar com fonte conferida e com a resposta do acusado",
    "fato_nao_confirmado": "o fato está na ficha como não confirmado: confirme ou tire a frase",
    "fato_vencido": "o fato venceu na ficha: revalide a fonte antes de publicar",
}
GRAVIDADE = {"numero_divergente": "alta", "citacao_nao_encontrada": "alta", "atribuicao_trocada": "alta",
             "fato_de_outro_caso": "alta", "fato_nao_confirmado": "alta", "citacao_diferente": "média",
             "sem_apoio": "média", "fato_vencido": "média", "pessoa_com_acusacao": "média"}


# --------------------------------------------------------------------------- comparações
def conteudo(tokens):
    return {t for t in tokens if len(t) >= 4 and t not in P.STOP}


def cobertura(alvo, tokens):
    """Quanto do `alvo` aparece em `tokens`, na ordem (0 a 1)."""
    if not alvo:
        return 0.0
    sm = difflib.SequenceMatcher(None, alvo, tokens, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(alvo)


def candidatas(tokens, passagens, idx, quantas=8):
    """As passagens que falam do mesmo assunto, por palavras de conteúdo em comum."""
    alvo = conteudo(tokens)
    if not alvo:
        return []
    contagem = {}
    for t in alvo:
        for i in idx.get(t, []):
            contagem[i] = contagem.get(i, 0) + 1
    ranking = sorted(contagem.items(), key=lambda x: -x[1])[:quantas]
    return [(passagens[i], n / len(alvo)) for i, n in ranking if n >= min(2, len(alvo))]


def mesmo_numero(a, b, aproximado):
    tol = TOL_APROX if aproximado else TOL
    return abs(a - b) <= max(abs(a), abs(b), 1.0) * tol


def nomes_normalizados(nomes):
    return {P.normalizar(n) for n in nomes if len(P.normalizar(n)) >= 4}


# --------------------------------------------------------------------------- a checagem de uma frase
def checar_frase(fr, passagens, idx, hoje, achados):
    tokens = P.normalizar(fr["texto"]).split()
    nums = [n for n in K.numeros_do_texto(fr["texto"])
            if n["tipo"] in TIPOS_CHECAVEIS or n["valor"] >= 10]
    nomes = P.nomes_do_texto(fr["texto"])
    acus = [a for a in C.ACUSACAO if re.search(r"(?<![a-zà-ÿ])" + re.escape(P.normalizar(a))
                                               + r"(?![a-zà-ÿ])", P.normalizar(fr["texto"]))]
    tem_citacao = bool(RX_ASPAS.search(fr["texto"])) or any(
        re.search(r"(?<![a-zà-ÿ])" + re.escape(P.normalizar(v)) + r"(?![a-zà-ÿ])", P.normalizar(fr["texto"]))
        for v in C.VERBOS_DIZER)
    if not (nums or (nomes and acus) or tem_citacao):
        return 0

    cands = candidatas(tokens, passagens, idx)
    base = {"t0": fr["t0"], "t1": fr["t1"], "mmss": P.mmss(fr["t0"]), "falado": fr["texto"],
            "sensivel": bool(nomes and acus),
            "pessoas_no_trecho": nomes[:6], "acusacoes_no_trecho": acus[:6]}
    antes = len(achados)

    # 1. números
    for n in nums:
        apoio, divergente = None, None
        for p, _ in cands:
            for m in p["numeros"]:
                if m["tipo"] != n["tipo"] and not (m["tipo"] == "numero" or n["tipo"] == "numero"):
                    continue
                if mesmo_numero(n["valor"], m["valor"], n["aproximado"] or m["aproximado"]):
                    apoio = (p, m)
                    break
                if m["tipo"] == n["tipo"] and divergente is None:
                    divergente = (p, m)
            if apoio:
                break
        if apoio:
            p, m = apoio
            nomes_p = nomes_normalizados(p["nomes"])
            nomes_f = nomes_normalizados(nomes)
            if nomes_f and nomes_p and not (nomes_f & nomes_p):
                achados.append(dict(base, tipo="atribuicao_trocada", valor_falado=n["bruto"],
                                    na_fonte=m["bruto"], de_quem_na_fonte=p["nomes"][:4],
                                    fonte=_fonte(p), trecho_da_fonte=p["texto"][:300]))
            continue
        if divergente:
            p, m = divergente
            achados.append(dict(base, tipo="numero_divergente", valor_falado=n["bruto"],
                                na_fonte=m["bruto"], fonte=_fonte(p), trecho_da_fonte=p["texto"][:300]))
        else:
            achados.append(dict(base, tipo="sem_apoio", valor_falado=n["bruto"],
                                fonte=None, trecho_da_fonte=None,
                                passagens_parecidas=[_fonte(p) for p, _ in cands[:3]]))

    # 2. citação
    if tem_citacao:
        m = RX_ASPAS.search(fr["texto"])
        citado = m.group(1) if m else fr["texto"]
        alvo = P.normalizar(citado).split()
        melhor, qual = 0.0, None
        for p, _ in cands:
            c = cobertura(alvo, p["tokens"])
            if c > melhor:
                melhor, qual = c, p
        if melhor < MIN_CITACAO:
            achados.append(dict(base, tipo="citacao_nao_encontrada", citado=citado, semelhanca=round(melhor, 2),
                                fonte=_fonte(qual) if qual else None,
                                trecho_da_fonte=qual["texto"][:300] if qual else None))
        elif melhor < IGUAL_CITACAO and m:
            achados.append(dict(base, tipo="citacao_diferente", citado=citado, semelhanca=round(melhor, 2),
                                fonte=_fonte(qual), trecho_da_fonte=qual["texto"][:300]))

    # 3. mesmo assunto, outro caso
    for p, _ in cands[:3]:
        if cobertura(tokens, p["tokens"]) < MIN_FRASE:
            continue
        nomes_p, nomes_f = nomes_normalizados(p["nomes"]), nomes_normalizados(nomes)
        if nomes_p and nomes_f and not (nomes_p & nomes_f):
            achados.append(dict(base, tipo="fato_de_outro_caso", na_fonte_sobre=p["nomes"][:4],
                                fonte=_fonte(p), trecho_da_fonte=p["texto"][:300]))
            break

    # 4. a ficha de fatos tem o que foi dito, mas em que estado?
    for p, prox in cands[:3]:
        if p["origem"] != "fatos" or prox < 0.5:
            continue
        if p.get("status") and p["status"] != "confirmado":
            achados.append(dict(base, tipo="fato_nao_confirmado", fonte=_fonte(p),
                                status_na_ficha=p["status"], trecho_da_fonte=p["texto"][:300]))
        venc = p.get("caduca_em")
        if venc and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(venc)) and str(venc) < hoje.isoformat():
            achados.append(dict(base, tipo="fato_vencido", fonte=_fonte(p), caduca_em=venc,
                                trecho_da_fonte=p["texto"][:300]))
        break

    # 5. pessoa + acusação sem nada apontado ainda
    if base["sensivel"] and len(achados) == antes:
        apoiada = any(prox >= 0.4 for _, prox in cands[:1])
        achados.append(dict(base, tipo="pessoa_com_acusacao",
                            fonte=_fonte(cands[0][0]) if cands else None,
                            trecho_da_fonte=cands[0][0]["texto"][:300] if cands else None,
                            tem_passagem_parecida=apoiada))
    return len(achados) - antes


def _fonte(p):
    if not p:
        return None
    return {"origem": p["origem"], "ref": p["ref"], "titulo": p.get("titulo") or "", "url": p.get("url") or ""}


# --------------------------------------------------------------------------- relatório
def escrever_md(caminho, itens, resumo):
    ordem = {"alta": 0, "média": 1, "baixa": 2}
    itens = sorted(itens, key=lambda x: (ordem.get(x["gravidade"], 3), x["t0"]))
    L = ["# Checagem da fala", "",
         f"{resumo['frases_checadas']} frases com dado checável · {len(itens)} ponto(s) a resolver "
         f"({resumo['por_gravidade'].get('alta', 0)} de gravidade alta, "
         f"{resumo['sensiveis']} trecho(s) sensível(is)).", "",
         f"Comparado com: {resumo['fatos']} fato(s) da pesquisa e {resumo['frases_de_documento']} frase(s) "
         f"de {len(resumo['documentos_lidos'])} documento(s).", "",
         "Cada item é **suspeita com evidência**, não veredito: abra a fonte antes de mudar qualquer coisa.", ""]
    if resumo["documentos_nao_lidos"]:
        L += ["> **Documentos que não consegui ler:** "
              + "; ".join(f"{d['arquivo']} ({d['porque']})" for d in resumo["documentos_nao_lidos"]), ""]
    if not itens:
        L.append("Nada a apontar nas frases com dado checável.")
    for it in itens:
        marca = " · **SENSÍVEL**" if it["sensivel"] else ""
        L += [f"## `{it['mmss']}` {it['tipo'].replace('_', ' ')} ({it['gravidade']}){marca}", "",
              f"**Foi dito:** {it['falado']}"]
        if it.get("valor_falado"):
            L.append(f"**Número falado:** {it['valor_falado']}"
                     + (f" · **na fonte:** {it['na_fonte']}" if it.get("na_fonte") else ""))
        if it.get("citado"):
            L.append(f"**Citação:** “{it['citado']}” (semelhança com a fonte: {it.get('semelhanca')})")
        if it.get("de_quem_na_fonte"):
            L.append(f"**Na fonte, o dado é de:** {', '.join(it['de_quem_na_fonte'])}")
        if it.get("na_fonte_sobre"):
            L.append(f"**A passagem parecida fala de:** {', '.join(it['na_fonte_sobre'])}")
        if it.get("status_na_ficha"):
            L.append(f"**Estado na ficha:** {it['status_na_ficha']}")
        if it.get("caduca_em"):
            L.append(f"**Caducou em:** {it['caduca_em']}")
        if it.get("fonte"):
            f = it["fonte"]
            L.append(f"**Fonte:** {f['origem']} `{f['ref']}`"
                     + (f" — {f['titulo']}" if f["titulo"] else "") + (f" <{f['url']}>" if f["url"] else ""))
        if it.get("trecho_da_fonte"):
            L.append(f"> {it['trecho_da_fonte']}")
        if it["sensivel"]:
            L.append(f"**Pessoa + acusação:** {', '.join(it['pessoas_no_trecho'])} / "
                     f"{', '.join(it['acusacoes_no_trecho'])}")
        L += ["", f"**O que fazer:** {ACOES.get(it['tipo'], 'confira a fonte')}", ""]
    C.gravar_md(caminho, L)


# --------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description="Compara a fala com a pesquisa e os documentos.")
    ap.add_argument("--projeto", help="pasta do projeto (padrão: a que tiver transcricao/ ou pesquisa/)")
    ap.add_argument("--palavras", help="transcricao/palavras.json")
    ap.add_argument("--fatos", help="pesquisa/fatos.json (skill video-pesquisa-ia)")
    ap.add_argument("--documentos", nargs="*", default=None, metavar="CAMINHO",
                    help=".md, .txt, .pdf ou pastas (padrão: pesquisa/ e documentos/ do projeto)")
    ap.add_argument("--saida", help="pasta de saída (padrão: <projeto>/qa)")
    ap.add_argument("--hoje", help="data de referência AAAA-MM-DD (para testar o vencimento)")
    a = ap.parse_args()

    raiz = C.raiz_do_projeto(a.projeto)
    f_pal = Path(a.palavras) if a.palavras else P.achar_palavras(raiz / "transcricao")
    if not Path(f_pal).exists():
        print(f"falta insumo: não achei {f_pal} — rode a skill video-transcricao antes", file=sys.stderr)
        return 2
    pal = P.carregar(f_pal)
    if not pal:
        print("falta insumo: o palavras.json está vazio", file=sys.stderr)
        return 2

    f_fatos = Path(a.fatos) if a.fatos else raiz / "pesquisa" / "fatos.json"
    passagens, ficha = K.da_ficha(f_fatos)
    n_fatos = len(ficha.get("fatos", [])) if ficha else 0
    alvos = a.documentos if a.documentos is not None else [raiz / "pesquisa", raiz / "documentos"]
    docs, lidos, falhou = K.dos_documentos(alvos)
    ficha_nome = Path(f_fatos).name          # a ficha não entra como documento: ela já virou passagens
    docs = [d for d in docs if Path(d["ref"].split(":")[0]).name != ficha_nome]
    lidos = [d for d in lidos if Path(d["arquivo"]).name != ficha_nome]
    passagens += docs
    if not passagens:
        print("falta insumo: não achei pesquisa/fatos.json nem documento nenhum para comparar.\n"
              "Passe --fatos e/ou --documentos (a skill video-pesquisa-ia produz a ficha de fatos).",
              file=sys.stderr)
        return 2

    idx = K.indexar(passagens)
    hoje = dt.date.fromisoformat(a.hoje) if a.hoje else dt.date.today()
    frases = P.frases(pal)
    achados, checadas = [], 0
    for fr in frases:
        n = checar_frase(fr, passagens, idx, hoje, achados)
        checadas += 1 if n or _tem_dado(fr) else 0
    achados = sem_repetir(achados)
    for i, it in enumerate(achados, 1):
        it["id"] = f"C{i:03d}"
        it["gravidade"] = GRAVIDADE.get(it["tipo"], "baixa")
        it["o_que_fazer"] = ACOES.get(it["tipo"], "confira a fonte")

    por_tipo, por_grav = {}, {}
    for it in achados:
        por_tipo[it["tipo"]] = por_tipo.get(it["tipo"], 0) + 1
        por_grav[it["gravidade"]] = por_grav.get(it["gravidade"], 0) + 1
    resumo = {"gerado_em": hoje.isoformat(), "palavras": len(pal), "frases": len(frases),
              "frases_checadas": checadas, "fatos": n_fatos, "frases_de_documento": len(docs),
              "documentos_lidos": lidos, "documentos_nao_lidos": falhou,
              "por_tipo": por_tipo, "por_gravidade": por_grav,
              "sensiveis": sum(1 for it in achados if it["sensivel"])}

    saida = Path(a.saida) if a.saida else raiz / "qa"
    P.gravar_json(saida / "checagem.json", {"versao": 1, "resumo": resumo, "itens": achados})
    escrever_md(saida / "checagem.md", achados, resumo)

    print(f"{saida}/checagem.json e checagem.md")
    print(f"  {checadas} frase(s) com dado checável · {len(achados)} ponto(s) a resolver"
          + (f" ({por_grav.get('alta', 0)} de gravidade alta)" if achados else ""))
    for t, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f"  {t.replace('_', ' ')}: {n}")
    if resumo["sensiveis"]:
        print(f"  {resumo['sensiveis']} trecho(s) SENSÍVEL(is): pessoa + acusação, só ao ar com fonte conferida")
    for d in falhou:
        print(f"  não consegui ler {d['arquivo']}: {d['porque']}")
    return 1 if achados else 0


def sem_repetir(achados):
    """Um mesmo apontamento, na mesma frase e na mesma fonte, aparece uma vez só."""
    visto, saida = set(), []
    for it in achados:
        chave = (it["tipo"], round(it["t0"], 2), (it.get("fonte") or {}).get("ref"))
        if chave in visto:
            continue
        visto.add(chave)
        saida.append(it)
    return saida


def _tem_dado(fr):
    return bool(K.numeros_do_texto(fr["texto"]) or RX_ASPAS.search(fr["texto"]))


if __name__ == "__main__":
    sys.exit(main())
