#!/usr/bin/env python3
"""decupar.py — o roteiro vira UNIDADES de edição numeradas (U001, U002…).

    decupar.py roteiro/roteiro-de-edicao.md [--palavras transcricao/palavras.json]
    decupar.py --auto roteiro/roteiro.md --palavras transcricao/palavras.json --alvo 10
    decupar.py listar [--json] [--so-midias]

Cada unidade sai com: tipo de tela, as palavras daquela unidade (as DITAS, quando há transcrição), as mídias
necessárias já com a orientação da direção de arte, uma linha de roteiro de edição legível e — no fim — as falas
que fugiram do roteiro (improviso), com o tempo.

Sai em roteiro/unidades.json, roteiro/roteiro-de-edicao.md e roteiro/fora-do-roteiro.md.

Formato que ele lê (markdown; tudo opcional menos a linha da unidade):

    ## Bloco 1 — Abertura
    ### 1. O item que abre
    **U** · 8 s · apresentador em tela cheia
    - Fala: o texto que vai ser falado
    - Tela: o que aparece
    - Mídia: foto de um telescópio em observatório · imagem · en: observatory telescope
    - Nota: observação para o editor

`**U**` numera sozinho (U001, U002…); `**U007**` fixa o número. Sem nenhuma linha `**U**`, use `--auto`: ele
corta a narração em unidades de ~`--alvo` segundos nas fronteiras de frase."""
from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import base  # noqa: E402

UNIDADES = Path("roteiro") / "unidades.json"
MD_EDICAO = Path("roteiro") / "roteiro-de-edicao.md"
MD_FORA = Path("roteiro") / "fora-do-roteiro.md"
PPM_PADRAO = 165.0                       # palavras por minuto, quando não há transcrição para medir

RE_BLOCO = re.compile(r"^#{1,2}\s+(.+?)\s*$")
RE_ITEM = re.compile(r"^#{3,4}\s+(.+?)\s*$")
RE_UNIDADE = re.compile(r"^\*\*(U\d*)\*\*\s*(?:·|-|—)?\s*(?:([\d.,]+)\s*s)?\s*(?:·|-|—)?\s*(.*)$")
RE_CAMPO = re.compile(r"^[-*]\s*(Fala|Tela|Texto|Mídia|Midia|Busca|Nota|Som)\s*:\s*(.*)$", re.I)
RE_FRASE = re.compile(r"(?<=[.!?…])\s+")
MODOS = (
    ("passagem", r"passagem|virada|transi[cç][aã]o de bloco|abre o bloco"),
    ("cartela", r"cartela|cart[aã]o|placa|t[ií]tulo cheio|tarja cheia"),
    ("misto", r"misto|janela|insert|\bpip\b|lado a lado|moldura|com o apresentador"),
    ("apresentador", r"apresentador|c[aâ]mera|talking.?head|tela cheia dele|rosto|em quadro|locutor"),
    ("ilustrado", r"ilustrad|anima|cobertura|b-?roll|m[ií]dia|imagem|v[ií]deo|infogr[aá]fico|mapa|documento|gr[aá]fico"),
)
TIPO_MIDIA = (("video", r"\bv[ií]deo\b|\bfootage\b|\bcena\b|\btomada\b|\bimagens? de arquivo\b|\btrecho\b"),
              ("imagem", r"\bfoto\b|\bimagem\b|\bretrato\b|\bmapa\b|\bdocumento\b|\bprint\b|\bcapa\b|\bgr[aá]fico\b"))


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def toks(s: str) -> list[str]:
    """Texto → tokens comparáveis (sem acento, sem pontuação, minúsculo)."""
    return [t for t in re.sub(r"[^a-z0-9 ]+", " ", sem_acento(s).lower()).split() if t]


def modo_de(tipo_tela: str) -> str:
    alvo = sem_acento(tipo_tela or "").lower()
    for modo, rx in MODOS:
        if re.search(rx, alvo):
            return modo
    return "ilustrado"


def tipo_da_midia(texto: str) -> str:
    alvo = sem_acento(texto or "").lower()
    for tipo, rx in TIPO_MIDIA:
        if re.search(rx, alvo):
            return tipo
    return "imagem"


# ──────────────────────────────────────────────────────────────── leitura do roteiro ──
def _midia(bruto: str) -> dict:
    """«foto de um telescópio · imagem · en: observatory telescope» → dict."""
    partes = [p.strip() for p in re.split(r"\s·\s|\s\|\s", bruto) if p.strip()]
    o_que, en, tipo = partes[0] if partes else bruto.strip(), None, None
    for p in partes[1:]:
        m = re.match(r"(?i)^en\s*[:=]\s*(.+)$", p)
        if m:
            en = m.group(1).strip()
        elif re.fullmatch(r"(?i)v[ií]deo|video|imagem|foto", p):
            tipo = "video" if sem_acento(p).lower().startswith("vid") else "imagem"
        elif re.fullmatch(r"(?i)horizontal|vertical|quadrado", p):
            tipo = tipo
    return {"o_que": o_que, "en": en, "tipo": tipo or tipo_da_midia(o_que)}


def ler_roteiro(texto: str) -> list[dict]:
    """Unidades do roteiro de edição, na ordem. Não numera ainda."""
    unidades, bloco, item, atual = [], None, None, None
    for linha in texto.replace("\r", "").split("\n"):
        m = RE_UNIDADE.match(linha.strip())
        if m:
            atual = {"id_pedido": m.group(1) if len(m.group(1)) > 1 else None,
                     "dur_estimada": float((m.group(2) or "0").replace(",", ".")) or None,
                     "tipo_tela": (m.group(3) or "").strip() or "ilustrado",
                     "bloco": bloco, "item": item, "texto_roteiro": "", "tela": "", "nota": "", "midias": []}
            unidades.append(atual)
            continue
        m = RE_CAMPO.match(linha.strip())
        if m and atual is not None:
            campo, valor = sem_acento(m.group(1)).lower(), m.group(2).strip()
            if campo == "fala":
                atual["texto_roteiro"] = (atual["texto_roteiro"] + " " + valor).strip()
            elif campo in ("tela", "texto"):
                atual["tela"] = (atual["tela"] + " " + valor).strip()
            elif campo == "midia":
                atual["midias"].append(_midia(valor))
            elif campo == "busca" and atual["midias"]:
                atual["midias"][-1]["en"] = valor
            elif campo in ("nota", "som"):
                atual["nota"] = (atual["nota"] + " " + valor).strip()
            continue
        m = RE_ITEM.match(linha)
        if m:
            item, atual = m.group(1), None
            continue
        m = RE_BLOCO.match(linha)
        if m:
            bloco, item, atual = m.group(1), None, None
            continue
        if atual is not None and linha.strip() and not linha.startswith(("#", "*", "-", "|", ">")):
            atual["texto_roteiro"] = (atual["texto_roteiro"] + " " + linha.strip()).strip()
    return unidades


def auto_unidades(texto: str, alvo_s: float, ppm: float = PPM_PADRAO) -> list[dict]:
    """Sem marcação de unidade: corta a narração em unidades de ~alvo_s segundos nas fronteiras de frase."""
    limite = max(3, int(round(alvo_s * ppm / 60.0)))
    unidades, bloco, item = [], None, None
    for paragrafo in [p.strip() for p in re.split(r"\n\s*\n", texto.replace("\r", "")) if p.strip()]:
        m = RE_BLOCO.match(paragrafo.split("\n")[0])
        if paragrafo.startswith("#"):
            if RE_ITEM.match(paragrafo.split("\n")[0]):
                item = RE_ITEM.match(paragrafo.split("\n")[0]).group(1)
            elif m:
                bloco, item = m.group(1), None
            continue
        if paragrafo.startswith(("-", "*", ">", "|")):
            continue
        atual = []
        for frase in [f.strip() for f in RE_FRASE.split(paragrafo) if f.strip()]:
            atual.append(frase)
            if len(toks(" ".join(atual))) >= limite:
                unidades.append({"id_pedido": None, "dur_estimada": None, "tipo_tela": "ilustrado", "bloco": bloco,
                                 "item": item, "texto_roteiro": " ".join(atual), "tela": "", "nota": "", "midias": []})
                atual = []
        if atual:
            unidades.append({"id_pedido": None, "dur_estimada": None, "tipo_tela": "ilustrado", "bloco": bloco,
                             "item": item, "texto_roteiro": " ".join(atual), "tela": "", "nota": "", "midias": []})
    return unidades


# ───────────────────────────────────────────────────────── alinhar com o que foi dito ──
def ler_palavras(arq: Path) -> list[dict]:
    dados = base.ler_json(arq, [])
    if isinstance(dados, dict):
        dados = dados.get("palavras") or dados.get("itens") or []
    saida = []
    for p in dados:
        t0 = p.get("t0", p.get("a"))
        t1 = p.get("t1", p.get("b"))
        if t0 is None:
            continue
        saida.append({"w": str(p.get("w", "")), "t0": float(t0), "t1": float(t1 if t1 is not None else t0)})
    saida.sort(key=lambda p: p["t0"])
    return saida


def alinhar(unidades: list[dict], palavras: list[dict], minimo: float = 0.35) -> list[dict]:
    """Acha cada unidade na fala (o apresentador parafraseia: casamento aproximado, sempre para a frente).
    Põe t0/t1/conf/palavras/texto_falado na unidade e devolve as falas que fugiram do roteiro."""
    T, T2p = [], []
    for i, p in enumerate(palavras):
        for t in toks(p["w"]):
            T.append(t)
            T2p.append(i)
    idx = defaultdict(list)
    for i in range(len(T) - 1):
        idx[(T[i], T[i + 1])].append(i)
    pos, fora, ultimo_fim = 0, [], 0
    for u in unidades:
        q = toks(u.get("texto_roteiro") or "")
        u["t0"] = u["t1"] = None
        u["conf"] = 0.0
        if len(q) < 2 or not T:
            continue
        votos = defaultdict(int)
        for j in range(len(q) - 1):
            for i in idx.get((q[j], q[j + 1]), []):
                if pos - 40 <= i - j <= pos + 2500:
                    votos[i - j] += 1
        melhor = None
        for st, _v in sorted(votos.items(), key=lambda x: -x[1])[:6]:
            lo, hi = max(0, st - 5), min(len(T), st + int(len(q) * 1.6) + 30)
            sm = difflib.SequenceMatcher(None, q, T[lo:hi], autojunk=False)
            blocos = [b for b in sm.get_matching_blocks() if b.size]
            if not blocos:
                continue
            pontos = sum(b.size for b in blocos) / len(q)
            ini, fim = lo + blocos[0].b, lo + blocos[-1].b + blocos[-1].size - 1
            chave = pontos - 0.0002 * max(0, ini - pos)
            if melhor is None or chave > melhor[0]:
                melhor = (chave, pontos, ini, fim, blocos, lo)
        if not melhor or melhor[1] < minimo:
            u["conf"] = round(melhor[1], 2) if melhor else 0.0
            continue
        _ch, pontos, ini, fim, blocos, _lo = melhor
        u["t0"] = round(palavras[T2p[ini]]["t0"], 3)
        u["t1"] = round(palavras[T2p[fim]]["t1"], 3)
        u["conf"] = round(pontos, 2)
        u["palavras"] = [{"w": p["w"], "t0": round(p["t0"], 3), "t1": round(p["t1"], 3)}
                         for p in palavras[T2p[ini]:T2p[fim] + 1]]
        u["texto_falado"] = " ".join(p["w"] for p in u["palavras"])
        # o que foi dito DENTRO da unidade e não estava no roteiro
        for a, b in zip(blocos, blocos[1:]):
            i0, i1 = _lo + a.b + a.size, _lo + b.b
            if i1 - i0 >= 4:
                fora.append({"unidade": u.get("id"), "onde": "dentro", "n_palavras": i1 - i0,
                             "t0": round(palavras[T2p[i0]]["t0"], 3), "t1": round(palavras[T2p[i1 - 1]]["t1"], 3),
                             "texto": " ".join(p["w"] for p in palavras[T2p[i0]:T2p[i1 - 1] + 1])})
        if ini - ultimo_fim >= 6:                     # o que foi dito ENTRE duas unidades
            fora.append({"unidade": u.get("id"), "onde": "antes", "n_palavras": ini - ultimo_fim,
                         "t0": round(palavras[T2p[ultimo_fim]]["t0"], 3), "t1": round(palavras[T2p[ini - 1]]["t1"], 3),
                         "texto": " ".join(p["w"] for p in palavras[T2p[ultimo_fim]:T2p[ini - 1] + 1])})
        pos, ultimo_fim = ini, max(ultimo_fim, fim + 1)
    if T and len(T) - ultimo_fim >= 6:
        fora.append({"unidade": None, "onde": "depois", "n_palavras": len(T) - ultimo_fim,
                     "t0": round(palavras[T2p[ultimo_fim]]["t0"], 3), "t1": round(palavras[-1]["t1"], 3),
                     "texto": " ".join(p["w"] for p in palavras[T2p[ultimo_fim]:])})
    return fora


# ────────────────────────────────────────────────────────── orientação da direção de arte ──
def orientacao_da_da(d) -> dict:
    """O que a DA manda sobre mídia de terceiro: formato, lado mínimo, tratamento e o que ela proíbe."""
    if d is None:
        return {"orientacao": "horizontal", "lado_minimo": 1080, "formato": "1920×1080 (padrão, sem DA no projeto)",
                "tratamento": "sem DA: o tratamento entra depois", "nao_faca": []}
    larg, alt = d.dimensoes("horizontal")
    trat = d["tratamento"] if "tratamento" in d else {}
    moldura = ((trat.get("moldura") or {}).get("estilo")) if isinstance(trat, dict) else None
    pedacos = []
    if moldura and moldura != "nenhuma":
        pedacos.append(f"moldura «{moldura}»")
    if isinstance(trat, dict) and (trat.get("grao") or {}).get("ativo"):
        pedacos.append("grão")
    if isinstance(trat, dict) and (trat.get("duotone") or {}).get("ativo"):
        pedacos.append("duotone")
    return {"orientacao": "horizontal" if larg >= alt else "vertical", "lado_minimo": min(larg, alt),
            "formato": f"{larg}×{alt}", "tratamento": ", ".join(pedacos) or "grade da DA",
            "nao_faca": list((d.get("conceito") or {}).get("nao_faca") or [])}


def alertas_da(texto: str, nao_faca: list[str]) -> list[str]:
    """Regras de conceito.nao_faca que o pedido de mídia parece contrariar (palavra de 4+ letras em comum)."""
    def palavras(s):
        fora = {"para", "como", "mais", "mesma", "tela", "outro", "cada", "sobre", "pela", "pelo", "meio", "coisa",
                "qualquer", "duas", "cores", "texto", "cima", "baixo", "fundo", "quadro", "sem", "com", "uma"}
        return {w for w in re.findall(r"[a-z]{4,}", sem_acento(s).lower())} - fora
    alvo = palavras(texto or "")
    return [r for r in nao_faca or [] if alvo & palavras(r)]


# ──────────────────────────────────────────────────────────────────────── saídas ──
def linha_de_edicao(u: dict) -> str:
    """Uma linha legível do que o editor faz nesta unidade."""
    quanto = f"{u['dur_falada']:.1f} s" if u.get("dur_falada") else (f"~{u['dur_estimada']:.0f} s" if u.get("dur_estimada") else "duração a medir")
    como = {"apresentador": "apresentador em quadro", "ilustrado": "100% cobertura (ele não aparece)",
            "misto": "apresentador com janela de mídia", "cartela": "cartela em tela cheia",
            "passagem": "passagem de bloco"}.get(u["modo"], u["modo"])
    midias = f" · {len(u['midias'])} mídia(s): " + "; ".join(m["o_que"] for m in u["midias"]) if u["midias"] else " · sem mídia"
    return f"{como} · {quanto}{midias}"


def md_edicao(doc: dict) -> str:
    linhas = [f"# Roteiro de edição — {doc.get('projeto') or 'projeto'}", "",
              f"{len(doc['unidades'])} unidades · gerado por video-prancha-de-referencia em {doc['feito_em']}.",
              f"Tempos: {'da fala transcrita (' + doc['alinhado_com'] + ')' if doc.get('alinhado_com') else 'estimados pelo roteiro (sem transcrição)'}.",
              "Mídia: cada código abaixo é o que a folha de contato numera e o que o usuário escolhe.", ""]
    bloco = object()
    for u in doc["unidades"]:
        if u.get("bloco") != bloco:
            bloco = u.get("bloco")
            linhas += ["", f"## {bloco or 'Sem bloco'}", ""]
        tempo = f"`{base.relogio(u.get('t0'))}–{base.relogio(u.get('t1'))}`"
        linhas.append(f"### {u['id']} · {tempo} · {u['tipo_tela']}")
        if u.get("item"):
            linhas.append(f"_{u['item']}_")
        linhas.append(f"- **Edição:** {linha_de_edicao(u)}")
        if u.get("texto_falado"):
            linhas.append(f"- **Fala (dita):** {u['texto_falado']}")
        elif u.get("texto_roteiro"):
            linhas.append(f"- **Fala (roteiro):** {u['texto_roteiro']}")
        if u.get("conf") is not None and u.get("t0") is None and u.get("texto_roteiro"):
            linhas.append(f"- **! não achei esta fala na transcrição** (confiança {u['conf']:.2f}): confira se foi cortada ou reescrita")
        if u.get("tela"):
            linhas.append(f"- **Tela:** {u['tela']}")
        for m in u["midias"]:
            alerta = f"  ⚠ a DA proíbe: {'; '.join(m['alerta_da'])}" if m.get("alerta_da") else ""
            linhas.append(f"- **`{m['codigo']}`** · {m['o_que']} · {m['tipo']} · {m['orientacao']} ≥ {m['lado_minimo']} px"
                          + (f" · busca em inglês: {m['en']}" if m.get("en") else "") + alerta)
        if u.get("nota"):
            linhas.append(f"- **Nota:** {u['nota']}")
        linhas.append("")
    return "\n".join(linhas) + "\n"


def md_fora(doc: dict) -> str:
    fora = doc.get("fora_do_roteiro") or []
    linhas = ["# Falas que fugiram do roteiro", "",
              "O que foi dito e não estava escrito: improviso, repetição, comentário. Cada trecho com o tempo da fala.",
              "Serve para decidir o que fica (e o que precisa de cobertura nova).", ""]
    if not fora:
        linhas.append("_Nada fora do roteiro: a fala seguiu o escrito._")
        return "\n".join(linhas) + "\n"
    for f in fora:
        onde = {"dentro": "dentro de", "antes": "antes de", "depois": "depois de"}.get(f["onde"], f["onde"])
        alvo = f.get("unidade") or "fim do vídeo"
        linhas.append(f"- `{base.relogio(f['t0'])}–{base.relogio(f['t1'])}` · {f['n_palavras']} palavras · {onde} {alvo}")
        linhas.append(f"  > {f['texto']}")
    linhas += ["", f"_{len(fora)} trecho(s) · {sum(f['n_palavras'] for f in fora)} palavras fora do roteiro._"]
    return "\n".join(linhas) + "\n"


# ──────────────────────────────────────────────────────────────────────── CLI ──
def montar(raiz: Path, arq_roteiro: Path, palavras_arq: Path | None, auto: bool, alvo: float, d) -> dict:
    texto = arq_roteiro.read_text(encoding="utf-8")
    unidades = [] if auto else ler_roteiro(texto)
    if not unidades:
        if not auto:
            base.diz("Nenhuma linha **U** no roteiro: cortando a narração sozinho (modo --auto).")
        unidades = auto_unidades(texto, alvo)
    if not unidades:
        raise base.Erro(f"{arq_roteiro}: não achei nem unidades (**U**) nem narração para cortar.",
                        "Confira o arquivo; o formato está no topo do decupar.py.", base.USO)
    usados, n = set(), 0
    for u in unidades:                                   # numeração: respeita o número fixado, preenche o resto
        if u.get("id_pedido"):
            u["id"] = u["id_pedido"].upper()
            usados.add(u["id"])
    for u in unidades:
        if not u.get("id"):
            n += 1
            while f"U{n:03d}" in usados:
                n += 1
            u["id"] = f"U{n:03d}"
            usados.add(u["id"])
    palavras = ler_palavras(palavras_arq) if palavras_arq and Path(palavras_arq).is_file() else []
    fora = alinhar(unidades, palavras) if palavras else []
    guia = orientacao_da_da(d)
    for u in unidades:
        u["modo"] = modo_de(u["tipo_tela"])
        u["dur_falada"] = round(u["t1"] - u["t0"], 2) if u.get("t0") is not None and u.get("t1") is not None else None
        if u["dur_falada"] is None and not u.get("dur_estimada"):
            u["dur_estimada"] = round(len(toks(u.get("texto_roteiro") or "")) / PPM_PADRAO * 60.0, 1) or None
        u.setdefault("palavras", [])
        u.setdefault("texto_falado", "")
        for i, m in enumerate(u["midias"], 1):
            m["codigo"] = f"{u['id']}-m{i}"
            m["orientacao"] = guia["orientacao"]
            m["lado_minimo"] = guia["lado_minimo"]
            m["tratamento_da"] = guia["tratamento"]
            m["alerta_da"] = alertas_da(f"{m['o_que']} {m.get('en') or ''}", guia["nao_faca"])
            m["status"] = "pendente"
        u.pop("id_pedido", None)
    doc = {"versao": 1, "feito_em": agora(), "projeto": (d["projeto"]["nome"] if d is not None else raiz.name),
           "fonte_roteiro": str(arq_roteiro), "alinhado_com": str(palavras_arq) if palavras else None,
           "da": guia, "unidades": unidades, "fora_do_roteiro": fora}
    doc["estatisticas"] = {
        "unidades": len(unidades),
        "por_modo": {m: sum(1 for u in unidades if u["modo"] == m) for m in sorted({u["modo"] for u in unidades})},
        "midias": sum(len(u["midias"]) for u in unidades),
        "localizadas": sum(1 for u in unidades if u.get("t0") is not None),
        "palavras_fora_do_roteiro": sum(f["n_palavras"] for f in fora),
        "duracao_s": round(max([u["t1"] for u in unidades if u.get("t1")] or [0]), 2)}
    return doc


def main(argv=None) -> int:
    ap = base.Parser(prog="decupar.py", description="O roteiro vira unidades de edição numeradas (U001…), com tipo de tela, "
                     "as palavras da unidade, as mídias necessárias com a orientação da DA e as falas fora do roteiro.")
    ap.add_argument("roteiro", nargs="?", help="o roteiro de edição (.md ou .txt); sem ele, só relê o que já foi decupado")
    ap.add_argument("--palavras", metavar="ARQ", help="transcricao/palavras.json (padrão: esse caminho, se existir)")
    ap.add_argument("--auto", action="store_true", help="ignora as marcações e corta a narração em unidades de ~--alvo segundos")
    ap.add_argument("--alvo", type=float, default=10.0, metavar="S", help="duração alvo da unidade no modo --auto (padrão 10 s)")
    ap.add_argument("--listar", action="store_true", help="só mostra o que já está em roteiro/unidades.json")
    ap.add_argument("--so-midias", action="store_true", help="na listagem, só as mídias pendentes")
    ap.add_argument("--sem-da", action="store_true", help="segue sem direção de arte (a orientação de mídia sai genérica)")
    ap.add_argument("--projeto", metavar="PASTA")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    raiz = base.achar_projeto(a.projeto)

    if a.listar or (not a.roteiro and a.roteiro != ""):
        doc = base.ler_json(raiz / UNIDADES)
        if not doc:
            raise base.Erro(f"não achei {UNIDADES.as_posix()} neste projeto.",
                            "Rode decupar.py <roteiro de edição> primeiro.", base.USO)
    else:
        arq = Path(a.roteiro).expanduser()
        if not arq.is_file():
            arq2 = raiz / a.roteiro
            if not arq2.is_file():
                raise base.Erro(f"não achei o roteiro: {a.roteiro}", "Passe o caminho do .md ou .txt do roteiro de edição.", base.USO)
            arq = arq2
        pal = Path(a.palavras).expanduser() if a.palavras else (raiz / "transcricao" / "palavras.json")
        d = None
        if not a.sem_da:
            da_mod, _texto = base.kit()
            try:
                d = da_mod.carregar(str(raiz))
            except Exception as e:                     # sem DA a decupagem continua: ela é planejamento, não peça
                base.diz(f"! sem direção de arte ({getattr(e, 'mensagem', e)}): a orientação de mídia sai genérica. "
                         "Crie a DA antes de buscar mídia.", erro=True)
        doc = montar(raiz, arq, pal, a.auto, a.alvo, d)
        base.gravar_json(raiz / UNIDADES, doc)
        base.gravar_texto(raiz / MD_EDICAO, md_edicao(doc))
        base.gravar_texto(raiz / MD_FORA, md_fora(doc))

    if a.json:
        print(json.dumps(doc, ensure_ascii=False, indent=1))
        return 0
    e = doc["estatisticas"]
    base.diz(f"{e['unidades']} unidades · {e['midias']} mídia(s) pedida(s) · {e['localizadas']} unidade(s) achadas na fala"
             + (f" · {e['duracao_s']:.0f} s" if e["duracao_s"] else ""))
    base.diz("  por modo: " + ", ".join(f"{k} {v}" for k, v in e["por_modo"].items()))
    for u in doc["unidades"]:
        if a.so_midias and not u["midias"]:
            continue
        base.diz(f"  {u['id']}  {base.relogio(u.get('t0'))}–{base.relogio(u.get('t1'))}  {u['modo']:12} {u['tipo_tela'][:44]}")
        for m in u["midias"]:
            base.diz(f"        {m['codigo']}  {m['tipo']:6} {m['o_que'][:60]}" + ("  ⚠ DA" if m.get("alerta_da") else ""))
    if doc.get("fora_do_roteiro"):
        base.diz(f"\n{len(doc['fora_do_roteiro'])} trecho(s) fora do roteiro ({e['palavras_fora_do_roteiro']} palavras) — "
                 f"veja {MD_FORA.as_posix()}")
    base.diz(f"\n{(raiz / UNIDADES)}\n{(raiz / MD_EDICAO)}\n{(raiz / MD_FORA)}")
    base.diz("\nAgora, a folha de contato de uma unidade:  folha.py montar U001")
    return 0


if __name__ == "__main__":
    sys.exit(base.rodar(main))
