#!/usr/bin/env python3
"""juntar.py — junta as partes escritas pelos agentes roteiristas e confere a emenda.

    juntar.py [--partes roteiro/partes] [--saida roteiro] [--so-conferir] [--json]

Cada agente roteirista entrega, na pasta das partes, dois arquivos com o MESMO prefixo `<nn>-<slug>`:

    roteiro/partes/03-regua-de-prova.fala.md      narração: `## <subseção>` e parágrafos de fala
    roteiro/partes/03-regua-de-prova.edicao.json  lista de blocos (contrato em references/formato-dos-roteiros.md)

Grava `roteiro/roteiro-fala.md` (só as falas), `roteiro/roteiro-edicao.md` (o que entra na tela, por
subseção) e `roteiro/edicao.json` (a mesma coisa legível por máquina, com um id por bloco).

Confere, e é por isso que ele existe: numeração das partes, subseção sem bloco (e bloco sem subseção),
`fala` do bloco que não existe na narração, frase repetida entre partes, vocabulário banido, fechamento
"Não é X, é Y", marcador de seção dentro da fala, número por extenso, código de tela desconhecido e o
orçamento de palavras contra o `estilo-de-fala.json`, se houver.

Códigos de saída: 0 tudo certo · 1 há problemas (listados) · 2 falta insumo · 64 uso.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

OK, ERRO, SEM_INSUMO, USO = 0, 1, 2, 64

TELAS_PADRAO = {
    "CAM": "apresentador em tela cheia",
    "CAM+": "apresentador com cartões e rótulos entrando",
    "VERT": "apresentador na moldura, conteúdo ao lado",
    "MOTION": "animação em tela cheia",
    "INSERT": "mídia de terceiro ou peça pronta num cartão",
    "DOC": "documento, print ou manchete na tela",
    "CARTELA": "abertura de bloco em cor chapada",
    "GC": "gerador de caracteres sobre o que estiver na tela",
    "BROLL": "imagem de cobertura de banco livre",
}
BANIDAS = ["clareza", "barulho", "propósito", "isso muda tudo", "nesse sentido", "em suma",
           "vale ressaltar", "é importante destacar", "no mundo de hoje", "mergulhe", "desvendar"]
MARCADORES = re.compile(r"\[\s*\d+\s*[-–]\s*\d+\s*s\s*\]|\b(HOOK|CTA|B-?ROLL|INTRO|OUTRO)\s*:", re.I)
ANTITESE = re.compile(r"\bn[ãa]o\s+é\s+[^.!?]{2,60}[,;]\s*é\s+[^.!?]{2,60}[.!?]\s*$", re.I)
EXTENSO = re.compile(r"\b(dois|três|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|quinze|vinte|"
                     r"trinta|quarenta|cinquenta|cem|duzentos|mil)\b", re.I)
FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")


class Erro(Exception):
    def __init__(self, mensagem: str, dica: str | None = None, codigo: int = ERRO):
        super().__init__(mensagem)
        self.mensagem, self.dica, self.codigo = mensagem, dica, codigo


def chave(texto: str) -> str:
    """Texto comparável: sem acento, sem pontuação, minúsculo, espaço único."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z ]+", " ", t)).strip()


def titulo_do_arquivo(arq: Path) -> str | None:
    """Título humano da parte: o primeiro `# …` do .fala.md, sem o «Parte NN —» da frente."""
    for linha in arq.read_text(encoding="utf-8").splitlines():
        cab = re.match(r"^#\s+(.*\S)\s*$", linha)
        if cab:
            return re.sub(r"^parte\s*\d+\s*[-–—:]\s*", "", cab.group(1).strip(), flags=re.I) or None
    return None


def ler_fala(arq: Path) -> list[dict]:
    """[{'subsecao', 'paragrafos': [str]}] a partir do .fala.md (cabeçalhos ## são as subseções)."""
    secoes, atual = [], None
    for linha in arq.read_text(encoding="utf-8").splitlines():
        cab = re.match(r"^#{2,3}\s+(.*\S)\s*$", linha)
        if cab:
            atual = {"subsecao": cab.group(1).strip(), "paragrafos": []}
            secoes.append(atual)
            continue
        if linha.startswith("#"):
            continue
        texto = linha.strip()
        if not texto or texto.startswith((">", "|", "-", "*")):
            continue
        if atual is None:
            atual = {"subsecao": arq.stem.split(".")[0], "paragrafos": []}
            secoes.append(atual)
        atual["paragrafos"].append(texto)
    return [s for s in secoes if s["paragrafos"]]


def ler_edicao(arq: Path) -> list[dict]:
    dados = json.loads(arq.read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        dados = dados.get("blocos") or dados.get("itens") or []
    if not isinstance(dados, list):
        raise Erro(f"{arq.name}: esperava uma lista de blocos.", codigo=SEM_INSUMO)
    return [b for b in dados if isinstance(b, dict)]


def carregar_partes(pasta: Path) -> list[dict]:
    if not pasta.is_dir():
        raise Erro(f"não achei a pasta das partes em {pasta}.",
                   "Cada roteirista grava `<nn>-<slug>.fala.md` e `<nn>-<slug>.edicao.json` ali.", SEM_INSUMO)
    falas = {f.name[:-len(".fala.md")]: f for f in sorted(pasta.glob("*.fala.md"))}
    edicoes = {f.name[:-len(".edicao.json")]: f for f in sorted(pasta.glob("*.edicao.json"))}
    if not falas:
        raise Erro(f"nenhum arquivo *.fala.md em {pasta}.", codigo=SEM_INSUMO)
    partes = []
    for prefixo in sorted(set(falas) | set(edicoes)):
        m = re.match(r"^(\d+)[-_]?(.*)$", prefixo)
        do_slug = (m.group(2).replace("-", " ").replace("_", " ").strip() if m else prefixo) or prefixo
        partes.append({
            "prefixo": prefixo, "numero": int(m.group(1)) if m else None,
            "titulo": (titulo_do_arquivo(falas[prefixo]) if prefixo in falas else None) or do_slug,
            "fala": falas.get(prefixo), "edicao": edicoes.get(prefixo),
            "secoes": ler_fala(falas[prefixo]) if prefixo in falas else [],
            "blocos": ler_edicao(edicoes[prefixo]) if prefixo in edicoes else [],
        })
    return partes


# ──────────────────────────────────────────────────────────────── conferência ──
def conferir(partes: list[dict], telas: dict, estilo: dict | None) -> list[dict]:
    p = []

    def anota(grau, onde, o_que, como_resolver):
        p.append({"grau": grau, "onde": onde, "o_que": o_que, "como_resolver": como_resolver})

    numeros = [x["numero"] for x in partes if x["numero"] is not None]
    if len(numeros) != len(partes):
        anota("erro", "partes", "parte sem número no começo do nome",
              "renomeie para `01-slug.fala.md`, `02-…` — a ordem do vídeo é a ordem dos números")
    for n, vezes in Counter(numeros).items():
        if vezes > 1:
            anota("erro", f"parte {n:02d}", f"{vezes} partes com o mesmo número",
                  "dois agentes gravaram o mesmo número; renumere antes de juntar")
    if numeros:
        faltando = sorted(set(range(min(numeros), max(numeros) + 1)) - set(numeros))
        if faltando:
            anota("erro", "partes", f"buraco na numeração: falta {', '.join(f'{x:02d}' for x in faltando)}",
                  "um agente roteirista não entregou, ou entregou com outro nome")

    frases_por_parte: dict[str, set] = {}
    for parte in partes:
        onde = parte["prefixo"]
        if parte["fala"] is None:
            anota("erro", onde, "tem edicao.json mas não tem fala.md", "o roteirista precisa entregar os dois arquivos")
            continue
        if parte["edicao"] is None:
            anota("erro", onde, "tem fala.md mas não tem edicao.json", "sem o arquivo de edição ninguém sabe o que vai na tela")
        texto_parte = " ".join(p_ for s in parte["secoes"] for p_ in s["paragrafos"])
        chave_parte = chave(texto_parte)
        parte["palavras"] = len(texto_parte.split())
        frases_por_parte[onde] = {chave(f) for f in FIM_DE_FRASE.split(texto_parte)
                                  if len(f.split()) >= 8}
        if not texto_parte.strip():
            anota("erro", onde, "fala.md sem narração", "o arquivo tem cabeçalho e nada mais")
        for banida in BANIDAS:
            if re.search(r"\b" + re.escape(chave(banida)) + r"\b", chave_parte):
                anota("aviso", onde, f"vocabulário banido: “{banida}”", "troque por uma palavra concreta do assunto")
        for s in parte["secoes"]:
            for par in s["paragrafos"]:
                if MARCADORES.search(par):
                    anota("erro", f"{onde} · {s['subsecao']}", "marcador de seção dentro da fala ([0-3s], HOOK, CTA…)",
                          "a narração é só o que sai da boca; marcação de tela vai no arquivo de edição")
                if ANTITESE.search(par.strip()):
                    anota("aviso", f"{onde} · {s['subsecao']}", "parágrafo fecha com “não é X, é Y”",
                          "é o fechamento mais reconhecível de texto de IA; reescreva afirmando")
                extenso = EXTENSO.findall(par)
                if extenso:
                    anota("aviso", f"{onde} · {s['subsecao']}", f"número por extenso: {', '.join(sorted(set(extenso))[:4])}",
                          "número concreto em algarismo (3 fontes, 40 minutos) soa mais forte na fala")
        nomes_secoes = {chave(s["subsecao"]): s for s in parte["secoes"]}
        com_bloco = set()
        for i, b in enumerate(parte["blocos"], 1):
            rot = f"{onde} · bloco {i}"
            sub = chave(str(b.get("subsecao") or ""))
            if not sub:
                anota("erro", rot, "bloco sem `subsecao`", "todo bloco diz a que subseção da narração ele pertence")
            elif sub not in nomes_secoes:
                anota("erro", rot, f"`subsecao` “{b.get('subsecao')}” não existe no fala.md",
                      "o texto do `##` da narração e o campo `subsecao` precisam ser iguais")
            else:
                com_bloco.add(sub)
                fala = chave(str(b.get("fala") or ""))
                if not fala:
                    anota("erro", rot, "bloco sem `fala`", "ponha as primeiras palavras da frase em que a tela entra")
                elif fala not in chave(" ".join(nomes_secoes[sub]["paragrafos"])):
                    anota("erro", rot, f"a `fala` do bloco não está na narração da subseção: “{str(b.get('fala'))[:60]}…”",
                          "copie literalmente um trecho da narração; é por ele que a montagem acha o ponto")
            tela = str(b.get("tela") or "").strip()
            if not tela:
                anota("erro", rot, "bloco sem `tela`", f"use um código da legenda: {', '.join(sorted(telas))}")
            elif tela.split()[0] not in telas:
                anota("aviso", rot, f"código de tela desconhecido: {tela}",
                      f"a legenda tem {', '.join(sorted(telas))}; para criar outro, grave roteiro/telas.json")
            if not str(b.get("midia") or "").strip():
                anota("aviso", rot, "bloco sem `midia`", "diga o que aparece; se for só o apresentador, escreva “—”")
            buscar = b.get("buscar")
            precisa = str(b.get("tela") or "").upper().startswith(("INSERT", "BROLL", "DOC"))
            if precisa and not (isinstance(buscar, dict) and (buscar.get("onde") or buscar.get("skill"))):
                anota("aviso", rot, "mídia de fora sem `buscar.onde`/`buscar.skill`",
                      "diga onde buscar (banco livre, YouTube, acervo) e qual skill atende")
        for nome, s in nomes_secoes.items():
            if nome not in com_bloco:
                anota("erro", f"{onde} · {s['subsecao']}", "subseção sem nenhum bloco de edição",
                      "toda subseção precisa de pelo menos uma linha dizendo o que aparece na tela")

    prefixos = list(frases_por_parte)
    for i, a in enumerate(prefixos):
        for b in prefixos[i + 1:]:
            for f in sorted(frases_por_parte[a] & frases_por_parte[b]):
                anota("erro", f"{a} × {b}", f"frase repetida nas duas partes: “{f[:70]}…”",
                      "dois roteiristas escreveram a mesma coisa; corte de uma das partes")

    ppm = ((estilo or {}).get("resumo") or {}).get("ppm")
    if ppm:
        for parte in partes:
            if parte.get("palavras"):
                parte["duracao_estimada_s"] = round(parte["palavras"] / ppm * 60, 1)
        total = sum(x.get("duracao_estimada_s") or 0 for x in partes)
        if total:
            anota("nota", "roteiro", f"{sum(x.get('palavras') or 0 for x in partes)} palavras ≈ "
                  f"{int(total // 60)} min {int(total % 60):02d} s a {ppm:.0f} palavras por minuto",
                  "compare com a duração combinada do vídeo antes de mandar gravar")
    else:
        anota("nota", "roteiro", "sem estilo-de-fala.json: não dá para estimar a duração",
              "rode o estilo.py nas transcrições do apresentador e grave em roteiro/")
    return p


# ──────────────────────────────────────────────────────────────────── saída ──
def montar(partes: list[dict], telas: dict) -> tuple[str, str, dict]:
    fala = ["# Roteiro de narração", "",
            "Só a fala, na ordem do vídeo. Nada de marcação de tela aqui: o que aparece está no roteiro de edição.", ""]
    edic = ["# Roteiro de edição", "",
            "Uma linha por entrada de tela, na ordem da narração. A coluna **Fala** é o trecho literal da narração "
            "em que a tela entra — é por ele que a montagem acha o ponto depois da gravação.", "", "## Legenda", "",
            "| Código | O que é na tela |", "|---|---|"]
    for k in sorted(telas):
        edic.append(f"| {k} | {telas[k]} |")
    edic.append("")
    blocos_json = []
    for parte in partes:
        titulo = parte["titulo"].strip() or parte["prefixo"]
        cab = f"## {parte['numero']:02d} · {titulo}" if parte["numero"] is not None else f"## {titulo}"
        fala.append(cab)
        fala.append("")
        edic.append(cab)
        edic.append("")
        n_bloco = 0
        raiz_id = f"{parte['numero']:02d}" if parte["numero"] is not None else parte["prefixo"]
        for s in parte["secoes"]:
            fala.append(f"### {s['subsecao']}")
            fala.append("")
            for par in s["paragrafos"]:
                fala.append(par)
                fala.append("")
            meus = [b for b in parte["blocos"] if chave(str(b.get("subsecao") or "")) == chave(s["subsecao"])]
            if not meus:
                continue
            edic.append(f"### {s['subsecao']}")
            edic.append("")
            edic.append("| id | Tela | Fala | Mídia | Onde buscar |")
            edic.append("|---|---|---|---|---|")
            for b in meus:
                n_bloco += 1
                bid = str(b.get("id") or f"{raiz_id}-{n_bloco:02d}")
                buscar = b.get("buscar") if isinstance(b.get("buscar"), dict) else {}
                onde = " · ".join(str(x) for x in (buscar.get("onde"), buscar.get("skill"), buscar.get("termo")) if x)
                edic.append(f"| {bid} | {b.get('tela', '')} | {str(b.get('fala', ''))[:70]} | "
                            f"{b.get('midia', '—')} | {onde or '—'} |")
                blocos_json.append({
                    "id": bid, "parte": parte["prefixo"], "subsecao": s["subsecao"],
                    "tela": b.get("tela", ""), "fala": b.get("fala", ""), "midia": b.get("midia", ""),
                    "buscar": buscar or None, "fatos": b.get("fatos") or [],
                    "skill": buscar.get("skill") or b.get("skill"),
                    "status": b.get("status", "pendente"), "notas": b.get("notas", ""),
                })
            edic.append("")
    dados = {"versao": 1, "telas": telas,
             "partes": [{"prefixo": x["prefixo"], "numero": x["numero"], "titulo": x["titulo"],
                         "palavras": x.get("palavras"), "duracao_estimada_s": x.get("duracao_estimada_s"),
                         "subsecoes": [s["subsecao"] for s in x["secoes"]]} for x in partes],
             "blocos": blocos_json}
    return "\n".join(fala).rstrip() + "\n", "\n".join(edic).rstrip() + "\n", dados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Junta as partes dos roteiristas e confere a emenda.")
    ap.add_argument("--partes", default="roteiro/partes", help="pasta com os <nn>-<slug>.fala.md / .edicao.json")
    ap.add_argument("--saida", default="roteiro", help="pasta onde gravar os três arquivos (padrão: roteiro/)")
    ap.add_argument("--so-conferir", action="store_true", help="confere e não grava nada")
    ap.add_argument("--json", action="store_true", help="imprime os problemas em JSON")
    a = ap.parse_args(argv)
    saida = Path(a.saida).expanduser()
    try:
        partes = carregar_partes(Path(a.partes).expanduser())
        telas = dict(TELAS_PADRAO)
        arq_telas = saida / "telas.json"
        if arq_telas.is_file():
            extra = json.loads(arq_telas.read_text(encoding="utf-8"))
            if isinstance(extra, dict):
                telas.update({str(k): str(v) for k, v in extra.items()})
        estilo = None
        arq_estilo = saida / "estilo-de-fala.json"
        if arq_estilo.is_file():
            estilo = json.loads(arq_estilo.read_text(encoding="utf-8"))
        problemas = conferir(partes, telas, estilo)
        texto_fala, texto_edic, dados = montar(partes, telas)
    except Erro as e:
        print(f"juntar.py: {e.mensagem}", file=sys.stderr)
        if e.dica:
            print(f"  → {e.dica}", file=sys.stderr)
        return e.codigo
    except (OSError, json.JSONDecodeError) as e:
        print(f"juntar.py: {e}", file=sys.stderr)
        return ERRO
    if not a.so_conferir:
        saida.mkdir(parents=True, exist_ok=True)
        (saida / "roteiro-fala.md").write_text(texto_fala, encoding="utf-8", newline="\n")
        (saida / "roteiro-edicao.md").write_text(texto_edic, encoding="utf-8", newline="\n")
        bruto = json.dumps(dados, ensure_ascii=False, indent=1) + "\n"
        (saida / "edicao.json").write_text(bruto, encoding="utf-8", newline="\n")
    if a.json:
        print(json.dumps({"partes": dados["partes"], "problemas": problemas}, ensure_ascii=False, indent=1))
    else:
        print(f"{len(partes)} parte(s) · {len(dados['blocos'])} bloco(s) de edição · "
              f"{sum(len(p['secoes']) for p in partes)} subseção(ões)")
        for grau in ("erro", "aviso", "nota"):
            for p in [x for x in problemas if x["grau"] == grau]:
                marca = {"erro": "✗", "aviso": "!", "nota": "·"}[grau]
                print(f"  {marca} [{p['onde']}] {p['o_que']}\n      → {p['como_resolver']}")
        if not a.so_conferir:
            for nome in ("roteiro-fala.md", "roteiro-edicao.md", "edicao.json"):
                print(f"→ {saida / nome}")
    return ERRO if any(p["grau"] == "erro" for p in problemas) else OK


if __name__ == "__main__":
    sys.exit(main())
