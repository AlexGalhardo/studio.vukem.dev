#!/usr/bin/env python3
"""mapa.py: da transcrição (+ roteiro + banco de nomes) ao mapa mecânico da fala.

  python3 mapa.py [--projeto .] [--roteiro roteiro/roteiro.md] [--nomes roteiro/nomes.json]

Grava `transcricao/mapa/`: blocos.json, pessoas.json, coisas.json, numeros.json, relogio.json,
tropecos.json, roteiro.json e mapa.md (tudo com mm:ss).

O script faz só a parte MECÂNICA: separar, casar, contar e medir. Ele não diz quem é importante, se a prova
prova, se o improviso melhorou nem o que entra no vídeo — isso é leitura, e é do Claude, a partir destes
arquivos. Tudo que sai daqui é CANDIDATO.

Códigos de saída: 0 ok · 1 falhou · 2 falta insumo (sem transcrição).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402

P = C.modulo_palavras()

PAUSA_BLOCO = 1.2      # segundos de silêncio que fecham um bloco de contexto
MAX_BLOCO_S = 45.0
MAX_BLOCO_PAL = 130
LIMIAR_NOME = 0.82     # semelhança fonética para casar nome escrito errado
SILENCIO = 1.5         # segundos: a partir daqui é pausa digna de nota
RX_DATA = re.compile(r"^\d{1,2}[/.-]\d{1,2}([/.-]\d{2,4})?$")
RX_NUM = re.compile(r"\d")


# --------------------------------------------------------------------------- blocos de contexto
def blocos(pal):
    saida, cur = [], []

    def fecha():
        if cur:
            i0, i1 = cur[0], cur[-1]
            t0, t1 = pal[i0]["t0"], pal[i1]["t1"]
            seg = max(0.001, t1 - t0)
            saida.append({"id": f"B{len(saida) + 1:03d}", "i0": i0, "i1": i1,
                          "t0": round(t0, 2), "t1": round(t1, 2), "mmss": P.mmss(t0),
                          "palavras": len(cur), "segundos": round(seg, 2),
                          "ppm": round(len(cur) / seg * 60, 1),
                          "texto": " ".join(pal[i]["w"] for i in cur)})
            cur.clear()

    for i, p in enumerate(pal):
        if cur:
            gap = p["t0"] - pal[cur[-1]]["t1"]
            longo = (p["t1"] - pal[cur[0]]["t0"]) > MAX_BLOCO_S or len(cur) >= MAX_BLOCO_PAL
            if (gap >= PAUSA_BLOCO and len(cur) >= 6) or (longo and gap >= 0.35) or len(cur) >= MAX_BLOCO_PAL * 1.5:
                fecha()
        cur.append(i)
    fecha()
    return saida


def bloco_de(bls, i):
    for b in bls:
        if b["i0"] <= i <= b["i1"]:
            return b["id"]
    return None


# --------------------------------------------------------------------------- pessoas e coisas
def ocorrencias(nome, variantes, pal, toks, bls):
    """Onde um nome do banco aparece na fala: escrito igual ou com a pronúncia parecida.

    A ordem importa: primeiro o nome inteiro escrito igual, depois o nome inteiro pela pronúncia e só então
    as variantes. Ao contrário, a variante curta («Marina») casa primeiro e esconde o nome inteiro que o
    Whisper escreveu errado («Marina Vascondelos») — que é justamente o que se quer ver.
    """
    saida, usados = [], set()

    def exato(forma):
        alvo = P.normalizar(forma).split()
        if not alvo:
            return
        n = len(alvo)
        for i in range(len(toks) - n + 1):
            if toks[i:i + n] == alvo and not (usados & set(range(i, i + n))):
                usados.update(range(i, i + n))
                saida.append({"t0": round(pal[i]["t0"], 2), "mmss": P.mmss(pal[i]["t0"]),
                              "como_foi_dito": " ".join(pal[j]["w"] for j in range(i, i + n)),
                              "casou_com": forma, "tipo": "exato", "semelhanca": 1.0,
                              "bloco": bloco_de(bls, i)})

    exato(nome)
    for s, i0, i1 in P.ocorrencias_aproximadas(nome, pal, LIMIAR_NOME, toks):
        if usados & set(range(i0, i1 + 1)):
            continue
        usados.update(range(i0, i1 + 1))
        saida.append({"t0": round(pal[i0]["t0"], 2), "mmss": P.mmss(pal[i0]["t0"]),
                      "como_foi_dito": " ".join(pal[j]["w"] for j in range(i0, i1 + 1)),
                      "casou_com": nome, "tipo": "parecido", "semelhanca": s, "bloco": bloco_de(bls, i0)})
    for v in variantes:
        exato(v)
    return sorted(saida, key=lambda o: o["t0"])


def do_banco(itens, pal, toks, bls):
    saida = []
    for it in itens:
        oc = ocorrencias(it["nome"], it["variantes"], pal, toks, bls)
        saida.append({"nome": it["nome"], "papel": it.get("papel", ""), "vezes": len(oc),
                      "grafias": sorted({o["como_foi_dito"] for o in oc if o["tipo"] == "parecido"}),
                      "blocos": sorted({o["bloco"] for o in oc if o["bloco"]}), "ocorrencias": oc})
    return sorted(saida, key=lambda x: -x["vezes"])


def fora_do_banco(pal, bls, banco, casados=()):
    """Nome próprio que o Whisper escreveu com maiúscula e não está no banco: ou falta no banco, ou é erro.

    O que já casou com o banco (inclusive pela pronúncia) sai daqui: senão «Instituto Farrol» apareceria
    nas duas listas e pareceria um nome novo.
    """
    conhecidos = set(casados)
    for grupo in banco.values():
        for it in grupo:
            for forma in [it["nome"]] + it["variantes"]:
                conhecidos |= set(P.normalizar(forma).split())
    texto = " ".join(p["w"] for p in pal)
    saida = []
    for nome in P.nomes_do_texto(texto, minimo=1):
        toks_n = P.normalizar(nome).split()
        if not toks_n or set(toks_n) <= conhecidos:
            continue
        i = next((k for k in range(len(pal) - len(toks_n) + 1)
                  if [P.normalizar(pal[j]["w"]) for j in range(k, k + len(toks_n))] == toks_n), None)
        if i is None:
            continue
        saida.append({"nome": nome, "mmss": P.mmss(pal[i]["t0"]), "t0": round(pal[i]["t0"], 2),
                      "bloco": bloco_de(bls, i)})
    return saida


def tokens_casados(*listas):
    """Palavras da fala que já casaram com algum nome do banco (para não aparecerem como nome novo)."""
    s = set()
    for lista in listas:
        for item in lista:
            for o in item["ocorrencias"]:
                s |= set(P.normalizar(o["como_foi_dito"]).split())
    return s


def coisas(pal, bls, banco, pes):
    """Objetos, provas e lugares citados: palavra do léxico + as 6 palavras em volta, para o Claude ler."""
    achados = []
    for i, p in enumerate(pal):
        n = P.normalizar(p["w"])
        for lex, tipo in ((C.PROVAS, "prova"), (C.LUGARES, "lugar")):
            if n in {P.normalizar(x) for x in lex}:
                a, b = max(0, i - 6), min(len(pal), i + 7)
                achados.append({"tipo": tipo, "termo": p["w"].strip(".,;:!?"), "t0": round(p["t0"], 2),
                                "mmss": P.mmss(p["t0"]), "bloco": bloco_de(bls, i),
                                "trecho": " ".join(q["w"] for q in pal[a:b])})
                break
    toks = [P.normalizar(p["w"]) for p in pal]
    orgs = do_banco(banco.get("organizacoes", []), pal, toks, bls)
    lugares = do_banco(banco.get("lugares", []), pal, toks, bls)
    return {"citados": achados,
            "nomes_fora_do_banco": fora_do_banco(pal, bls, banco, tokens_casados(pes, orgs, lugares)),
            "organizacoes": orgs, "lugares": lugares}


# --------------------------------------------------------------------------- números e datas
def tipo_do_numero(contexto, cabeca, bruto):
    """Classifica pela vizinhança (3 palavras antes, 5 depois): só a cara do número não basta."""
    j = " " + " ".join(contexto) + " "
    if "%" in bruto or " por cento " in j or " porcento " in j:
        return "percentual"
    if re.search(r"r\$|us\$|\s(reais|real|dolar|dolares|euros?|centavos)\s", j):
        return "dinheiro"
    if re.search(r"\s(horas?|minutos?)\s", j):
        return "hora"
    if any(f" {P.normalizar(m)} " in j for m in C.MESES) or RX_DATA.search(bruto.strip(".,;:")):
        return "data"
    if re.fullmatch(r"(19|20)\d{2}", cabeca):
        return "ano"
    return "numero"


def numeros(pal, bls):
    num_pal = {P.normalizar(x) for x in C.NUM_PALAVRA} - {"um", "uma"}
    emenda = num_pal | {"e", "mil", "por", "cento"}
    saida, visto = [], -9
    for i, p in enumerate(pal):
        bruto = p["w"]
        n = P.normalizar(bruto)
        if not (RX_NUM.search(bruto) or n in num_pal or "%" in bruto):
            continue
        if i <= visto:                                   # "20 mil reais" é um número só
            continue
        a, b = max(0, i - 3), min(len(pal), i + 6)
        contexto = [P.normalizar(q["w"]) for q in pal[a:b]]
        visto = i
        while visto + 1 < len(pal) and P.normalizar(pal[visto + 1]["w"]) in emenda:
            visto += 1
        saida.append({"tipo": tipo_do_numero(contexto, n, bruto),
                      "valor": " ".join(q["w"] for q in pal[i:visto + 1]),
                      "t0": round(p["t0"], 2), "mmss": P.mmss(p["t0"]), "bloco": bloco_de(bls, i),
                      "trecho": " ".join(q["w"] for q in pal[a:b])})
    return saida


# --------------------------------------------------------------------------- relógio, tropeços, silêncios
def relogio(pal, bls):
    ppms = sorted(b["ppm"] for b in bls) or [0]
    med = ppms[len(ppms) // 2]
    por_bloco = []
    for b in bls:
        marca = "corrido" if b["ppm"] > med * 1.15 else ("arrastado" if b["ppm"] < med * 0.85 else "no ritmo")
        por_bloco.append({"bloco": b["id"], "mmss": b["mmss"], "ppm": b["ppm"], "ritmo": marca,
                          "palavras": b["palavras"], "segundos": b["segundos"]})
    minutos, m = [], 0
    while pal and m * 60 < pal[-1]["t1"]:
        dentro = [p for p in pal if m * 60 <= p["t0"] < (m + 1) * 60]
        minutos.append({"minuto": m, "mmss": P.mmss(m * 60), "palavras": len(dentro),
                        "ppm": round(len(dentro) * 60 / 60.0, 1)})
        m += 1
    return {"ppm_mediano": med, "ppm_medio": round(sum(b["ppm"] for b in bls) / max(1, len(bls)), 1),
            "por_bloco": por_bloco, "por_minuto": minutos}


def tropecos(pal, bls):
    muletas_set = {P.normalizar(x) for x in C.MULETAS}
    toks = [P.normalizar(p["w"]) for p in pal]
    rep, mul, sil, fim_retomada = [], {}, [], 0
    for i, p in enumerate(pal):
        if toks[i] in muletas_set:
            mul.setdefault(p["w"].strip(".,;:!?…"), []).append({"t0": round(p["t0"], 2),
                                                                "mmss": P.mmss(p["t0"])})
        if i + 1 < len(pal) and toks[i] and toks[i] == toks[i + 1] and pal[i + 1]["t0"] - p["t1"] < 1.5:
            rep.append({"tipo": "palavra repetida", "o_que": pal[i]["w"], "t0": round(p["t0"], 2),
                        "mmss": P.mmss(p["t0"]), "bloco": bloco_de(bls, i)})
        elif (i + 1 < len(pal) and len(toks[i]) >= 2 and toks[i] != toks[i + 1]
              and toks[i + 1].startswith(toks[i]) and pal[i + 1]["t0"] - p["t1"] < 0.4):
            rep.append({"tipo": "gaguejo", "o_que": f"{pal[i]['w']} {pal[i + 1]['w']}",
                        "t0": round(p["t0"], 2), "mmss": P.mmss(p["t0"]), "bloco": bloco_de(bls, i)})
        for n in (4, 3, 2):     # retomada: o trecho inteiro recomeçado ("a gente recebeu a gente recebeu")
            if i >= fim_retomada and i + 2 * n <= len(pal) and all(toks[i:i + n]) \
                    and toks[i:i + n] == toks[i + n:i + 2 * n] \
                    and pal[i + n]["t0"] - pal[i + n - 1]["t1"] < 2.0:
                rep.append({"tipo": "retomada", "o_que": " ".join(pal[j]["w"] for j in range(i, i + 2 * n)),
                            "t0": round(p["t0"], 2), "mmss": P.mmss(p["t0"]), "bloco": bloco_de(bls, i)})
                fim_retomada = i + 2 * n
                break
        if i + 1 < len(pal):
            g = pal[i + 1]["t0"] - p["t1"]
            if g >= SILENCIO:
                sil.append({"t0": round(p["t1"], 2), "mmss": P.mmss(p["t1"]), "segundos": round(g, 2),
                            "antes": pal[i]["w"], "depois": pal[i + 1]["w"], "bloco": bloco_de(bls, i)})
    muletas = sorted(({"muleta": k, "vezes": len(v), "por_minuto":
                       round(len(v) / max(0.001, (pal[-1]["t1"] - pal[0]["t0"])) * 60, 2), "quando": v[:60]}
                      for k, v in mul.items()), key=lambda x: -x["vezes"])
    return {"repeticoes": rep, "silencios": sil, "muletas": muletas}


# --------------------------------------------------------------------------- fala × roteiro
def _fluxo(pal):
    f = []
    for i, p in enumerate(pal):
        for t in P.normalizar(p["w"]).split():
            f.append((t, i))
    return f


def _achar(fluxo, alvo, k0, k1, minimo=0.55):
    if not alvo:
        return None, 0.0
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(alvo)
    melhor = (None, 0.0)
    for k in range(k0, max(k0 + 1, min(k1, len(fluxo)))):
        jan = [t for t, _ in fluxo[k:k + len(alvo) + 2]]
        if not jan:
            break
        if jan[0] != alvo[0] and (len(alvo) < 2 or alvo[1] not in jan[:3]):
            continue
        sm.set_seq1(jan)
        r = sm.ratio()
        if r > melhor[1]:
            melhor = (k, r)
    return melhor if melhor[1] >= minimo else (None, melhor[1])


def contra_roteiro(pal, texto, janela=2500):
    """Casa cada frase do roteiro com um trecho da fala; o que sobra na fala é improviso."""
    fluxo = _fluxo(pal)
    frases = C.frases_do_roteiro(texto)
    cursor, casadas, nao_ditas = 0, [], []
    for linha, frase in frases:
        alvo = P.normalizar(frase).split()[:14]
        k, r = _achar(fluxo, alvo, cursor, cursor + janela)
        if k is None:
            nao_ditas.append({"linha": linha, "frase": frase, "semelhanca": round(r, 2)})
            continue
        for _ in range(3):      # o melhor trecho pode ter começado uma palavra antes do primeiro token
            if fluxo[k][0] != alvo[0] and k + 1 < len(fluxo) and \
                    (fluxo[k + 1][0] == alvo[0] or (len(alvo) > 1 and fluxo[k + 1][0] == alvo[1])):
                k += 1
        todos = P.normalizar(frase).split()
        i0 = fluxo[k][1]
        fim = min(len(fluxo) - 1, k + len(todos) - 1)
        i1 = max(i0, fluxo[fim][1])
        while i1 + 1 < len(pal) and todos and P.normalizar(pal[i1 + 1]["w"]) == todos[-1]:
            i1 += 1
        casadas.append({"linha": linha, "frase": frase, "t0": round(pal[i0]["t0"], 2),
                        "t1": round(pal[i1]["t1"], 2), "mmss": P.mmss(pal[i0]["t0"]),
                        "semelhanca": round(r, 2), "i0": i0, "i1": i1,
                        "como_foi_dito": " ".join(pal[j]["w"] for j in range(i0, i1 + 1))})
        cursor = max(cursor, fim - 1)
    cobertos = set()
    for c in casadas:
        cobertos |= set(range(c["i0"], c["i1"] + 1))
    improvisos, cur = [], []
    for i in range(len(pal)):
        if i in cobertos:
            if len(cur) >= 6 and pal[cur[-1]]["t1"] - pal[cur[0]]["t0"] >= 2.0:
                improvisos.append({"t0": round(pal[cur[0]]["t0"], 2), "t1": round(pal[cur[-1]]["t1"], 2),
                                   "mmss": P.mmss(pal[cur[0]]["t0"]), "palavras": len(cur),
                                   "texto": " ".join(pal[j]["w"] for j in cur)})
            cur = []
        else:
            cur.append(i)
    if len(cur) >= 6:
        improvisos.append({"t0": round(pal[cur[0]]["t0"], 2), "t1": round(pal[cur[-1]]["t1"], 2),
                           "mmss": P.mmss(pal[cur[0]]["t0"]), "palavras": len(cur),
                           "texto": " ".join(pal[j]["w"] for j in cur)})
    return {"frases_do_roteiro": len(frases), "faladas": len(casadas), "nao_faladas": nao_ditas,
            "cobertura_das_palavras": round(len(cobertos) / max(1, len(pal)), 3),
            "casadas": casadas, "improvisos": improvisos}


# --------------------------------------------------------------------------- mapa.md
def escrever_md(caminho, bls, pes, cois, nums, rel, trop, rot):
    L = [f"# Mapa de fala", "",
         f"{len(bls)} blocos de contexto · {sum(b['palavras'] for b in bls)} palavras · "
         f"{rel['ppm_mediano']} palavras por minuto (mediana).", "",
         "Tudo aqui é **candidato mecânico**: quem decide o que é relevante é a leitura, não o script.", ""]
    L += ["## Blocos de contexto", ""]
    for b in bls:
        L.append(f"- `{b['mmss']}` **{b['id']}** ({b['segundos']:.0f}s, {b['palavras']} pal., {b['ppm']} ppm) "
                 f"{b['texto'][:160]}{'…' if len(b['texto']) > 160 else ''}")
    L += ["", "## Pessoas citadas", ""]
    if not pes:
        L.append("- (sem banco de nomes: rode o `nomes.py` e passe `--nomes`)")
    for p in pes:
        if not p["vezes"]:
            continue
        extra = f" · grafias do Whisper: {', '.join(p['grafias'])}" if p["grafias"] else ""
        L.append(f"- **{p['nome']}**{' — ' + p['papel'] if p['papel'] else ''}: {p['vezes']}× "
                 f"({', '.join(o['mmss'] for o in p['ocorrencias'][:12])}){extra}")
    faltam = [p for p in pes if not p["vezes"]]
    if faltam:
        L.append(f"- *no banco e não citados*: {', '.join(p['nome'] for p in faltam)}")
    if cois["nomes_fora_do_banco"]:
        L += ["", "### Nome próprio dito e fora do banco (completar ou corrigir)", ""]
        L += [f"- `{x['mmss']}` {x['nome']}" for x in cois["nomes_fora_do_banco"][:60]]
    L += ["", "## Objetos, provas e lugares", ""]
    for c in cois["citados"][:120]:
        L.append(f"- `{c['mmss']}` [{c['tipo']}] **{c['termo']}** — …{c['trecho']}…")
    L += ["", "## Números e datas", ""]
    for n in nums[:150]:
        L.append(f"- `{n['mmss']}` [{n['tipo']}] **{n['valor']}** — …{n['trecho']}…")
    L += ["", "## Relógio das palavras", ""]
    for r in rel["por_bloco"]:
        if r["ritmo"] != "no ritmo":
            L.append(f"- `{r['mmss']}` {r['bloco']}: {r['ppm']} ppm ({r['ritmo']})")
    L += ["", "## Repetições, tropeços e silêncios", ""]
    for t in trop["repeticoes"][:80]:
        L.append(f"- `{t['mmss']}` [{t['tipo']}] {t['o_que']}")
    for s in trop["silencios"][:40]:
        L.append(f"- `{s['mmss']}` [silêncio] {s['segundos']:.1f}s entre «{s['antes']}» e «{s['depois']}»")
    if trop["muletas"]:
        L.append("- muletas: " + ", ".join(f"{m['muleta']} {m['vezes']}×" for m in trop["muletas"][:12]))
    if rot:
        L += ["", "## Fala × roteiro", "",
              f"{rot['faladas']} de {rot['frases_do_roteiro']} frases do roteiro foram ditas; "
              f"{rot['cobertura_das_palavras']:.0%} das palavras da fala vêm do roteiro.", ""]
        if rot["nao_faladas"]:
            L.append("**Frases do roteiro que não foram ditas**")
            L += [f"- linha {x['linha']}: {x['frase'][:140]}" for x in rot["nao_faladas"][:40]]
            L.append("")
        if rot["improvisos"]:
            L.append("**Improvisos (fala fora do roteiro)**")
            L += [f"- `{x['mmss']}` ({x['palavras']} pal.) {x['texto'][:200]}" for x in rot["improvisos"][:40]]
    C.gravar_md(caminho, L)


# --------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description="Mapa mecânico da fala a partir da transcrição.")
    ap.add_argument("--projeto", help="pasta do projeto (padrão: a que tiver transcricao/)")
    ap.add_argument("--palavras", help="transcricao/palavras.json (padrão: o do projeto)")
    ap.add_argument("--roteiro", help="roteiro/roteiro.md (padrão: o do projeto, se houver)")
    ap.add_argument("--nomes", help="roteiro/nomes.json (padrão: o do projeto, se houver)")
    ap.add_argument("--saida", help="pasta de saída (padrão: <projeto>/transcricao/mapa)")
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

    f_nomes = Path(a.nomes) if a.nomes else raiz / "roteiro" / "nomes.json"
    banco = C.carregar_banco(f_nomes) if Path(f_nomes).exists() else {}
    f_rot = Path(a.roteiro) if a.roteiro else raiz / "roteiro" / "roteiro.md"
    saida = Path(a.saida) if a.saida else Path(f_pal).resolve().parent / "mapa"

    toks = [P.normalizar(p["w"]) for p in pal]
    bls = blocos(pal)
    pes = do_banco(banco.get("pessoas", []), pal, toks, bls) if banco else []
    cois = coisas(pal, bls, banco, pes)
    nums = numeros(pal, bls)
    rel = relogio(pal, bls)
    trop = tropecos(pal, bls)
    rot = contra_roteiro(pal, C.ler_texto(f_rot)) if Path(f_rot).exists() else None

    P.gravar_json(saida / "blocos.json", bls)
    P.gravar_json(saida / "pessoas.json", pes)
    P.gravar_json(saida / "coisas.json", cois)
    P.gravar_json(saida / "numeros.json", nums)
    P.gravar_json(saida / "relogio.json", rel)
    P.gravar_json(saida / "tropecos.json", trop)
    if rot:
        P.gravar_json(saida / "roteiro.json", rot)
    escrever_md(saida / "mapa.md", bls, pes, cois, nums, rel, trop, rot)

    print(f"{saida}/")
    print(f"  blocos {len(bls)} · pessoas citadas {sum(1 for p in pes if p['vezes'])}/{len(pes)} do banco"
          f" · nomes fora do banco {len(cois['nomes_fora_do_banco'])}")
    print(f"  provas e lugares {len(cois['citados'])} · números e datas {len(nums)}"
          f" · {rel['ppm_mediano']} ppm (mediana)")
    print(f"  repetições e tropeços {len(trop['repeticoes'])} · silêncios ≥ {SILENCIO}s "
          f"{len(trop['silencios'])} · muletas {sum(m['vezes'] for m in trop['muletas'])}")
    if rot:
        print(f"  roteiro: {rot['faladas']}/{rot['frases_do_roteiro']} frases ditas, "
              f"{len(rot['improvisos'])} improviso(s), {rot['cobertura_das_palavras']:.0%} da fala vem do roteiro")
    else:
        print("  (sem roteiro: a seção fala × roteiro não foi gerada)")
    if not banco:
        print("  (sem banco de nomes: rode o nomes.py para achar nome que o Whisper escreveu errado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
