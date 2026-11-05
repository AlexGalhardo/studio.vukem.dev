#!/usr/bin/env python3
"""estilo.py — mede o jeito de falar de uma pessoa a partir de várias transcrições.

    estilo.py <transcrição…> --saida roteiro/ [--nome "Apresentador"] [--min-repeticoes 3] [--json]

Entra: `.palavras.json` (formato da casa: [{"w","t0","t1","p"}], também aceita "a"/"b"), `segmentos.json`
([{"t0","t1","texto"}]), `.txt`/`.md` (só texto, sem tempo) ou uma pasta com qualquer um deles.
Sai: `<saida>/estilo-de-fala.json` (números) e `<saida>/estilo-de-fala.md` (a ficha que o roteirista lê).

Mede: palavras por minuto (corridas e sem as pausas), tamanho de frase, ritmo das pausas, muletas,
bordões (sequências que a pessoa repete), aberturas e fechos, perguntas, números e um orçamento de
palavras por duração. Só biblioteca padrão. Códigos de saída: 0 ok · 1 erro · 2 falta insumo · 64 uso.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

OK, ERRO, SEM_INSUMO, USO = 0, 1, 2, 64
PAUSA_CURTA = 0.6          # s: a partir daqui o intervalo entre duas palavras conta como pausa
PAUSA_LONGA = 1.2          # s: pausa de respiração/virada de assunto
N_GRAMA = (3, 4, 5, 6)     # tamanhos de sequência procurados para os bordões
EXTENSOES = {".json", ".txt", ".md"}

# Muletas do português falado. Cada uma é uma sequência de palavras já normalizadas.
MULETAS = [
    "né", "tipo", "assim", "então", "aí", "cara", "mano", "gente", "sabe", "olha", "olha só",
    "quer dizer", "ou seja", "digamos", "enfim", "na verdade", "na real", "basicamente",
    "literalmente", "simplesmente", "praticamente", "meio que", "um pouco", "uma coisa assim",
    "entendeu", "beleza", "tá", "bom", "pois é", "veja bem", "deixa eu", "é isso",
]
# Viradas: o que a pessoa usa para mudar de direção dentro do texto (vale ouro para o roteirista).
VIRADAS = [
    "só que", "mas", "porém", "no entanto", "o problema é que", "acontece que", "agora",
    "repara", "veja", "e aqui", "e é aí que", "a questão é", "a verdade é que", "e não para por aí",
]
PALAVRAS_VAZIAS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das", "e", "é", "em",
    "no", "na", "nos", "nas", "que", "para", "pra", "por", "com", "se", "ao", "aos", "à", "às", "mas",
    "mais", "como", "ou", "isso", "isto", "esse", "essa", "este", "esta", "ele", "ela", "eles", "elas",
    "eu", "você", "voce", "vocês", "nós", "a gente", "já", "não", "sim", "foi", "era", "são", "ser",
    "tem", "ter", "está", "tá", "muito", "também", "aqui", "ali", "lá", "quando", "onde", "porque",
    "pelo", "pela", "num", "numa", "sobre", "entre", "até", "depois", "antes", "então", "aí", "né",
    "do", "dele", "dela", "seu", "sua", "meu", "minha", "nosso", "nossa", "vai", "vou", "fazer", "faz",
}


class Erro(Exception):
    def __init__(self, mensagem: str, dica: str | None = None, codigo: int = ERRO):
        super().__init__(mensagem)
        self.mensagem, self.dica, self.codigo = mensagem, dica, codigo


# ───────────────────────────────────────────────────────────────── leitura ──
def _n(texto: str) -> str:
    """Palavra normalizada para contagem: minúscula, sem pontuação de borda, acento preservado."""
    t = texto.strip().lower()
    t = re.sub(r"^[^0-9a-zà-ÿ]+|[^0-9a-zà-ÿ%]+$", "", t, flags=re.I)
    return t


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _campo(item: dict, *nomes):
    for nome in nomes:
        if nome in item and item[nome] is not None:
            return item[nome]
    return None


def _palavras_de_segmentos(segmentos: list) -> list[dict]:
    """Reparte o tempo de cada segmento entre as palavras dele, proporcional ao tamanho de cada uma."""
    saida = []
    for s in segmentos:
        texto = str(_campo(s, "texto", "text") or "")
        t0, t1 = _campo(s, "t0", "a", "start"), _campo(s, "t1", "b", "end")
        partes = [p for p in texto.split() if p]
        if not partes:
            continue
        if t0 is None or t1 is None or float(t1) <= float(t0):
            saida += [{"w": p, "t0": None, "t1": None} for p in partes]
            continue
        t0, t1 = float(t0), float(t1)
        total = sum(len(p) for p in partes) or 1
        andado = 0
        for p in partes:
            ini = t0 + (t1 - t0) * andado / total
            andado += len(p)
            saida.append({"w": p, "t0": round(ini, 3), "t1": round(t0 + (t1 - t0) * andado / total, 3)})
    return saida


def ler_transcricao(arq: Path) -> dict:
    """{'arquivo', 'palavras': [{'w','t0','t1'}], 'tempos': 'medidos'|'estimados'|None}."""
    if arq.suffix.lower() in (".txt", ".md"):
        texto = arq.read_text(encoding="utf-8", errors="replace")
        texto = re.sub(r"^#.*$|^\s*[-*|].*$", " ", texto, flags=re.M)        # título e tabela não são fala
        return {"arquivo": arq, "palavras": [{"w": p, "t0": None, "t1": None} for p in texto.split()],
                "tempos": None}
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise Erro(f"{arq.name}: não consegui ler o JSON ({e}).",
                   "Use um palavras.json ([{\"w\",\"t0\",\"t1\"}]), um segmentos.json ([{\"t0\",\"t1\",\"texto\"}]) ou um .txt.")
    if isinstance(dados, dict):
        for chave in ("palavras", "words", "segmentos", "segments"):
            if isinstance(dados.get(chave), list):
                dados = dados[chave]
                break
    if not isinstance(dados, list) or not dados:
        raise Erro(f"{arq.name}: o JSON não tem uma lista de palavras nem de segmentos.", codigo=SEM_INSUMO)
    primeiro = dados[0] if isinstance(dados[0], dict) else {}
    if _campo(primeiro, "texto", "text") is not None and _campo(primeiro, "w", "word") is None:
        return {"arquivo": arq, "palavras": _palavras_de_segmentos(dados), "tempos": "estimados"}
    palavras, com_tempo = [], 0
    for item in dados:
        if not isinstance(item, dict):
            continue
        w = _campo(item, "w", "word", "palavra")
        if not w:
            continue
        t0, t1 = _campo(item, "t0", "a", "start"), _campo(item, "t1", "b", "end")
        try:
            t0, t1 = (float(t0) if t0 is not None else None), (float(t1) if t1 is not None else None)
        except (TypeError, ValueError):
            t0 = t1 = None
        com_tempo += t0 is not None and t1 is not None
        palavras.append({"w": str(w), "t0": t0, "t1": t1})
    if not palavras:
        raise Erro(f"{arq.name}: nenhuma palavra legível.", codigo=SEM_INSUMO)
    return {"arquivo": arq, "palavras": palavras, "tempos": "medidos" if com_tempo > len(palavras) * 0.8 else None}


def juntar_entradas(caminhos: list[str]) -> list[Path]:
    arqs: list[Path] = []
    for c in caminhos:
        p = Path(c).expanduser()
        if p.is_dir():
            arqs += [f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in EXTENSOES
                     and not f.name.startswith(("_", "."))]
        elif p.is_file():
            arqs.append(p)
        else:
            raise Erro(f"não achei {p}.", "Passe o caminho de um palavras.json, de um .txt ou de uma pasta.", SEM_INSUMO)
    vistos, unicos = set(), []
    for a in arqs:
        if a.resolve() not in vistos:
            vistos.add(a.resolve())
            unicos.append(a)
    if not unicos:
        raise Erro("nenhuma transcrição nas entradas.", "Aponte para arquivos .palavras.json, .txt ou .md.", SEM_INSUMO)
    return unicos


# ───────────────────────────────────────────────────────────────── medidas ──
FIM_DE_FRASE = re.compile(r"[.!?…]+[\"'»)\]]*$")


def frases(palavras: list[dict]) -> tuple[list[list[dict]], str]:
    """Divide em frases pela pontuação; se a transcrição não tem pontuação, divide pelas pausas."""
    por_pontuacao: list[list[dict]] = []
    atual: list[dict] = []
    for p in palavras:
        atual.append(p)
        if FIM_DE_FRASE.search(p["w"]):
            por_pontuacao.append(atual)
            atual = []
    if atual:
        por_pontuacao.append(atual)
    if len(por_pontuacao) >= max(2, len(palavras) / 45):
        return por_pontuacao, "pontuação"
    por_pausa: list[list[dict]] = []
    atual = []
    anterior = None
    for p in palavras:
        if atual and anterior is not None and p["t0"] is not None and p["t0"] - anterior >= PAUSA_LONGA:
            por_pausa.append(atual)
            atual = []
        atual.append(p)
        anterior = p["t1"] if p["t1"] is not None else anterior
    if atual:
        por_pausa.append(atual)
    return (por_pausa, "pausa") if len(por_pausa) > 1 else (por_pontuacao, "pontuação")


def tempos(palavras: list[dict]) -> dict:
    """Duração, pausas e palavras por minuto. Só conta quem tem tempo medido."""
    com = [p for p in palavras if p["t0"] is not None and p["t1"] is not None]
    if len(com) < 2:
        return {"palavras_com_tempo": len(com), "duracao_s": None, "pausas": None}
    duracao = round(com[-1]["t1"] - com[0]["t0"], 3)
    intervalos = [round(b["t0"] - a["t1"], 3) for a, b in zip(com, com[1:]) if b["t0"] - a["t1"] > 0]
    curtas = [i for i in intervalos if i >= PAUSA_CURTA]
    longas = [i for i in intervalos if i >= PAUSA_LONGA]
    em_pausa = round(sum(curtas), 3)
    falando = round(max(duracao - em_pausa, 0.001), 3)
    minutos = duracao / 60
    return {
        "palavras_com_tempo": len(com), "duracao_s": duracao,
        "tempo_em_pausa_s": em_pausa, "tempo_de_fala_s": falando,
        "ppm": round(len(com) / minutos, 1),
        "ppm_sem_pausa": round(len(com) / (falando / 60), 1),
        "pausas": {"de_06s": len(curtas), "de_12s": len(longas),
                   "por_minuto_06s": round(len(curtas) / minutos, 1) if minutos else None,
                   "por_minuto_12s": round(len(longas) / minutos, 1) if minutos else None,
                   "mediana_s": round(sorted(curtas)[len(curtas) // 2], 2) if curtas else None,
                   "maior_s": round(max(intervalos), 2) if intervalos else None},
    }


def _sequencias(tokens: list[str], n: int):
    for i in range(len(tokens) - n + 1):
        yield " ".join(tokens[i:i + n])


def bordoes(por_arquivo: list[list[str]], minimo: int) -> list[dict]:
    """Sequências de 3 a 6 palavras que a pessoa repete. Vale mais a que aparece em mais de um arquivo."""
    contas: dict[str, Counter] = {}
    for i, tokens in enumerate(por_arquivo):
        for n in N_GRAMA:
            for seq in _sequencias(tokens, n):
                contas.setdefault(seq, Counter())[i] += 1
    achados = []
    for seq, c in contas.items():
        total = sum(c.values())
        if total < minimo:
            continue
        palavras = seq.split()
        if all(p in PALAVRAS_VAZIAS for p in palavras):
            continue
        achados.append({"frase": seq, "vezes": total, "arquivos": len(c), "palavras": len(palavras)})
    achados.sort(key=lambda a: (-a["arquivos"], -a["vezes"] * a["palavras"], a["frase"]))
    # tira a sequência curta que só existe dentro de uma mais longa com a mesma contagem
    final = []
    for a in achados:
        if any(a["frase"] in b["frase"] and a["frase"] != b["frase"] and b["vezes"] >= a["vezes"] for b in final):
            continue
        final.append(a)
    return final[:25]


def contar_expressoes(tokens: list[str], lista: list[str]) -> list[dict]:
    texto = " " + " ".join(tokens) + " "
    saida = []
    for exp in lista:
        vezes = len(re.findall(r"(?<= )" + re.escape(exp) + r"(?= )", texto))
        if vezes:
            saida.append({"expressao": exp, "vezes": vezes})
    saida.sort(key=lambda d: -d["vezes"])
    return saida


def texto_da_frase(frase: list[dict]) -> str:
    return " ".join(p["w"] for p in frase).strip()


def medir(arquivos: list[Path], minimo: int) -> dict:
    fichas, tokens_por_arquivo, todas_frases = [], [], []
    todos_tokens: list[str] = []
    for arq in arquivos:
        t = ler_transcricao(arq)
        fs, modo = frases(t["palavras"])
        tok = [x for x in (_n(p["w"]) for p in t["palavras"]) if x]
        tokens_por_arquivo.append(tok)
        todos_tokens += tok
        todas_frases += fs
        tam = sorted(len([p for p in f if _n(p["w"])]) for f in fs)
        fichas.append({
            "arquivo": arq.name, "tempos": t["tempos"], "palavras": len(tok), "frases": len(fs),
            "frases_divididas_por": modo,
            "palavras_por_frase": round(len(tok) / len(fs), 1) if fs else None,
            "medidas_de_tempo": tempos(t["palavras"]),
            "abertura": texto_da_frase(fs[0])[:220] if fs else "",
            "fecho": texto_da_frase(fs[-1])[:220] if fs else "",
        })
    tamanhos = sorted(len([p for p in f if _n(p["w"])]) for f in todas_frases)
    def pct(q):
        return tamanhos[min(len(tamanhos) - 1, int(q * (len(tamanhos) - 1)))] if tamanhos else None
    com_tempo = [f for f in fichas if (f["medidas_de_tempo"] or {}).get("duracao_s")]
    dur = sum(f["medidas_de_tempo"]["duracao_s"] for f in com_tempo)
    pal = sum(f["medidas_de_tempo"]["palavras_com_tempo"] for f in com_tempo)
    falando = sum(f["medidas_de_tempo"]["tempo_de_fala_s"] for f in com_tempo)
    ppm = round(pal / (dur / 60), 1) if dur else None
    conteudo = Counter(t for t in todos_tokens if t not in PALAVRAS_VAZIAS and len(t) > 3)
    perguntas = sum(1 for f in todas_frases if texto_da_frase(f).rstrip().endswith("?"))
    numerais = sum(1 for t in todos_tokens if re.search(r"\d", t))
    resumo = {
        "arquivos": len(arquivos), "palavras": len(todos_tokens), "frases": len(todas_frases),
        "duracao_medida_s": round(dur, 2) if dur else None,
        "ppm": ppm,
        "ppm_sem_pausa": round(pal / (falando / 60), 1) if falando else None,
        "palavras_por_frase": {
            "media": round(len(todos_tokens) / len(todas_frases), 1) if todas_frases else None,
            "mediana": pct(0.5), "curta_p10": pct(0.10), "longa_p90": pct(0.90),
            "maior": tamanhos[-1] if tamanhos else None},
        "perguntas_por_100_frases": round(perguntas * 100 / len(todas_frases), 1) if todas_frases else None,
        "numeros_por_1000_palavras": round(numerais * 1000 / len(todos_tokens), 1) if todos_tokens else None,
        "vocabulario": {"palavras_diferentes": len(set(todos_tokens)),
                        "variedade": round(len(set(todos_tokens)) / len(todos_tokens), 3) if todos_tokens else None,
                        "tamanho_medio_da_palavra": round(sum(len(t) for t in todos_tokens) / len(todos_tokens), 2)
                        if todos_tokens else None},
    }
    muletas = contar_expressoes(todos_tokens, MULETAS)
    for m in muletas:
        m["por_1000_palavras"] = round(m["vezes"] * 1000 / len(todos_tokens), 1) if todos_tokens else None
    orcamento = {}
    if ppm:
        for rotulo, seg in (("15 s", 15), ("30 s", 30), ("1 min", 60), ("5 min", 300), ("10 min", 600)):
            orcamento[rotulo] = round(ppm * seg / 60)
    return {
        "versao": 1, "resumo": resumo, "por_arquivo": fichas,
        "muletas": muletas,
        "viradas": contar_expressoes(todos_tokens, VIRADAS),
        "bordoes": bordoes(tokens_por_arquivo, minimo),
        "aberturas": [f["abertura"] for f in fichas if f["abertura"]],
        "fechos": [f["fecho"] for f in fichas if f["fecho"]],
        "comecos_de_frase": [{"inicio": k, "vezes": v} for k, v in
                             Counter(" ".join([x for x in (_n(p["w"]) for p in f[:2]) if x])
                                     for f in todas_frases if f).most_common(12) if v > 1],
        "palavras_de_conteudo": [{"palavra": k, "vezes": v} for k, v in conteudo.most_common(25)],
        "orcamento_de_palavras": orcamento,
    }


# ───────────────────────────────────────────────────────────────── relatório ──
def para_md(d: dict, nome: str) -> str:
    r = d["resumo"]
    L = [f"# Estilo de fala — {nome}", ""]
    L.append(f"Medido em {r['arquivos']} transcrição(ões), {r['palavras']} palavras, {r['frases']} frases"
             + (f", {r['duracao_medida_s']:.0f} s de fala medida." if r["duracao_medida_s"] else "."))
    L.append("")
    L.append("## O que o roteirista precisa acertar")
    L.append("")
    if r["ppm"]:
        L.append(f"- **Ritmo: {r['ppm']:.0f} palavras por minuto** corridos ({r['ppm_sem_pausa']:.0f} sem contar as pausas). "
                 "Escreva pelo orçamento de palavras abaixo, não pelo número de linhas.")
    f = r["palavras_por_frase"]
    if f["media"]:
        L.append(f"- **Frase de {f['media']:.0f} palavras em média** (mediana {f['mediana']}; as curtas têm {f['curta_p10']}, "
                 f"as longas {f['longa_p90']}, a maior tem {f['maior']}). Alterne: duas ou três médias e uma curta.")
    if r["perguntas_por_100_frases"]:
        L.append(f"- **{r['perguntas_por_100_frases']:.0f} perguntas a cada 100 frases.** Pergunta é a forma dele de virar de assunto.")
    if r["numeros_por_1000_palavras"]:
        L.append(f"- **{r['numeros_por_1000_palavras']:.0f} números a cada 1000 palavras.** Número concreto vence termo vago; "
                 "cada um precisa estar na pesquisa.")
    L.append(f"- **Vocabulário:** {r['vocabulario']['palavras_diferentes']} palavras diferentes, "
             f"variedade {r['vocabulario']['variedade']}, palavra média de {r['vocabulario']['tamanho_medio_da_palavra']} letras.")
    L.append("")
    if d["orcamento_de_palavras"]:
        L.append("## Orçamento de palavras")
        L.append("")
        L.append("| Duração | Palavras |")
        L.append("|---|---|")
        for k, v in d["orcamento_de_palavras"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
    def tabela(titulo, itens, colunas, chaves, nota=""):
        if not itens:
            return
        L.append(f"## {titulo}")
        L.append("")
        if nota:
            L.append(nota)
            L.append("")
        L.append("| " + " | ".join(colunas) + " |")
        L.append("|" + "---|" * len(colunas))
        for it in itens:
            L.append("| " + " | ".join(str(it.get(c, "")) for c in chaves) + " |")
        L.append("")
    tabela("Muletas (mantenha algumas: é o que soa humano)", d["muletas"][:15],
           ["expressão", "vezes", "por 1000 palavras"], ["expressao", "vezes", "por_1000_palavras"],
           "Deixe as duas ou três mais usadas no texto, nas viradas. Tirar todas deixa a fala com cara de IA; "
           "repetir em toda frase cansa.")
    tabela("Viradas (como ele muda de direção)", d["viradas"][:12], ["expressão", "vezes"], ["expressao", "vezes"])
    tabela("Bordões (sequências que ele repete)", d["bordoes"][:15],
           ["frase", "vezes", "em quantos arquivos"], ["frase", "vezes", "arquivos"],
           "Bordão que aparece em mais de um arquivo é marca registrada: use 1 ou 2 por vídeo, nunca em sequência.")
    tabela("Começos de frase repetidos", d["comecos_de_frase"][:10], ["início", "vezes"], ["inicio", "vezes"])
    tabela("Palavras de conteúdo mais usadas", d["palavras_de_conteudo"][:15], ["palavra", "vezes"], ["palavra", "vezes"])
    if d["aberturas"]:
        L.append("## Como ele abre")
        L.append("")
        for a in d["aberturas"][:8]:
            L.append(f"- “{a}”")
        L.append("")
    if d["fechos"]:
        L.append("## Como ele fecha")
        L.append("")
        for a in d["fechos"][:8]:
            L.append(f"- “{a}”")
        L.append("")
    L.append("## Por transcrição")
    L.append("")
    L.append("| arquivo | palavras | frases | palavras/frase | ppm | pausas ≥ 0,6 s por min | tempos |")
    L.append("|---|---|---|---|---|---|---|")
    for fa in d["por_arquivo"]:
        m = fa["medidas_de_tempo"] or {}
        pz = (m.get("pausas") or {}).get("por_minuto_06s")
        L.append(f"| {fa['arquivo']} | {fa['palavras']} | {fa['frases']} | {fa['palavras_por_frase']} | "
                 f"{m.get('ppm', '—')} | {pz if pz is not None else '—'} | {fa['tempos'] or 'sem tempo'} |")
    L.append("")
    L.append("> Esta ficha mede COMO ele fala, não O QUE ele diz. O conteúdo vem da pesquisa; o que é fato "
             "precisa estar na ficha de fatos do projeto.")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mede o jeito de falar a partir de várias transcrições.")
    ap.add_argument("transcricoes", nargs="+", help="palavras.json, segmentos.json, .txt/.md ou pasta")
    ap.add_argument("--saida", default="roteiro", help="pasta de saída (padrão: roteiro/)")
    ap.add_argument("--nome", default="apresentador", help="nome que aparece no título da ficha")
    ap.add_argument("--min-repeticoes", type=int, default=3, help="repetições para uma sequência virar bordão (padrão: 3)")
    ap.add_argument("--json", action="store_true", help="imprime o JSON no stdout além de gravar")
    a = ap.parse_args(argv)
    try:
        arquivos = juntar_entradas(a.transcricoes)
        if a.min_repeticoes < 2:
            raise Erro("--min-repeticoes precisa ser 2 ou mais.", codigo=USO)
        d = medir(arquivos, a.min_repeticoes)
    except Erro as e:
        print(f"estilo.py: {e.mensagem}", file=sys.stderr)
        if e.dica:
            print(f"  → {e.dica}", file=sys.stderr)
        return e.codigo
    saida = Path(a.saida).expanduser()
    saida.mkdir(parents=True, exist_ok=True)
    bruto = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    (saida / "estilo-de-fala.json").write_text(bruto, encoding="utf-8", newline="\n")
    ficha = para_md(d, a.nome)
    (saida / "estilo-de-fala.md").write_text(ficha, encoding="utf-8", newline="\n")
    r = d["resumo"]
    print(f"{r['arquivos']} transcrição(ões) · {r['palavras']} palavras · {r['frases']} frases"
          + (f" · {r['duracao_medida_s']:.2f} s medidos" if r["duracao_medida_s"] else ""))
    if r["ppm"]:
        print(f"ppm {r['ppm']} (sem pausa {r['ppm_sem_pausa']}) · frase média {r['palavras_por_frase']['media']} palavras")
    print(f"→ {saida / 'estilo-de-fala.json'}")
    print(f"→ {saida / 'estilo-de-fala.md'}")
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    return OK


if __name__ == "__main__":
    sys.exit(main())
