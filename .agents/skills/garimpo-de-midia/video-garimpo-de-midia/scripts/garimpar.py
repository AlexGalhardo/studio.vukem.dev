#!/usr/bin/env python3
"""garimpar.py — garimpo de mídia POR NECESSIDADE em bancos livres, numa ordem de preferência configurável.

    garimpar.py necessidades                      # lê roteiro/pauta.json e monta a lista de necessidades
    garimpar.py necessidades --nova "foto de retrato de alguém" --en "portrait" --tipo imagem --pessoa "Nome Sobrenome"
    garimpar.py fontes [--ordem wikimedia,nasa,archive,openverse,pexels,pixabay] [--pausa 2]
    garimpar.py buscar [N001 N002 …] [--pausa 2] [--bastam 4] [--folha]
    garimpar.py listar [--json]
    garimpar.py escolher N001 --numeros 2,5       # registra a escolha do usuário e IMPRIME o comando de download
    garimpar.py citar N004 --url https://… --t0 1:10 --t1 1:18      # plano de citação do YouTube (≤ 10 s, sem som)
    garimpar.py creditos                          # broll/garimpo/creditos.md com licença e crédito de tudo

Esta skill é FINA de propósito: quem fala com os provedores é a video-broll (scripts/buscar.py e baixar.py) e quem
guarda licença é broll/licencas.json. Aqui moram o que falta: a necessidade, a ordem das fontes, a pausa entre
pedidos, a conferência de identidade da pessoa na foto e a regra de que NADA é baixado sem o «sim» do usuário.

Nenhum subcomando baixa mídia. `buscar --folha` baixa só as miniaturas da folha de contato (como a video-broll).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import base  # noqa: E402
import identidade  # noqa: E402

NECESSIDADES = base.PASTA / "necessidades.json"
FONTES = base.PASTA / "fontes.json"
CREDITOS = base.PASTA / "creditos.md"
GENEROS = ("pessoa", "lugar", "documento", "evento", "objeto", "ambiente")
# ordem padrão: primeiro o que é de acervo público e tem crédito rastreável; os bancos de stock fecham a fila
ORDEM_PADRAO = ["wikimedia", "nasa", "archive", "openverse", "pexels", "pixabay"]
ORDEM_POR_GENERO = {
    "pessoa": ["wikimedia", "openverse", "archive"],                 # banco de stock não tem pessoa nomeada
    "documento": ["wikimedia", "archive", "openverse"],
    "evento": ["wikimedia", "archive", "openverse", "nasa"],
    "lugar": ["wikimedia", "nasa", "openverse", "pexels", "pixabay", "archive"],
    "ambiente": ["pexels", "pixabay", "nasa", "wikimedia", "openverse", "archive"],
    "objeto": ["pexels", "pixabay", "wikimedia", "openverse", "archive"],
}
PADRAO_CFG = {"versao": 1, "ordem": list(ORDEM_PADRAO), "por_genero": {k: list(v) for k, v in ORDEM_POR_GENERO.items()},
              "pausa_s": 2.0, "por_fonte": 6, "bastam": 4,
              "youtube": {"so_citacao": True, "max_s": 10, "sem_som": True, "exige_credito": True}}


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────── configuração ──
def cfg_carregar(raiz: Path) -> dict:
    c = dict(PADRAO_CFG)
    gravado = base.ler_json(raiz / FONTES) or {}
    for k, v in gravado.items():
        if k in c:
            c[k] = v
    c["ordem"] = [f for f in c["ordem"] if isinstance(f, str)]
    if not c["ordem"]:
        raise base.Erro(f"{FONTES.as_posix()}: a lista `ordem` está vazia.", "Rode garimpar.py fontes --ordem wikimedia,nasa,archive,openverse,pexels,pixabay")
    return c


def ordem_da(nec: dict, cfg: dict) -> list[str]:
    """Ordem de preferência desta necessidade: a dela, a do gênero, ou a geral."""
    if nec.get("ordem"):
        return [f for f in nec["ordem"] if f]
    por_genero = (cfg.get("por_genero") or {}).get(nec.get("genero") or "")
    fila = list(por_genero or cfg["ordem"])
    for f in cfg["ordem"]:                               # o que a ordem geral tem e a do gênero não, entra no fim
        if f not in fila:
            fila.append(f)
    return fila


# ───────────────────────────────────────────────────────────────── necessidades ──
def _slug_id(n: int) -> str:
    return f"N{n:03d}"


def _da_pauta(raiz: Path) -> list[dict]:
    """Pedidos de roteiro/pauta.json (video-pauta-midia) que o garimpo atende: banco e imagem_web."""
    pauta = base.ler_json(raiz / "roteiro" / "pauta.json") or {}
    saida = []
    for p in pauta.get("pedidos") or []:
        tipo = p.get("tipo")
        if tipo not in ("banco", "imagem_web", "video_youtube"):
            continue
        if p.get("status") in ("baixado", "tratado", "descartado"):
            continue
        texto = (p.get("o_que") or p.get("texto") or p.get("pedido") or "").strip()
        if not texto:
            continue
        saida.append({"pedido_id": p.get("id"), "o_que": texto, "tipo": "video" if tipo != "imagem_web" else "imagem",
                      "so_citacao": tipo == "video_youtube", "trecho": p.get("trecho") or p.get("ancora")})
    return saida


def nova_necessidade(dados: dict, n: int) -> dict:
    g = dados.get("genero") or ("pessoa" if dados.get("pessoa") else "ambiente")
    if g not in GENEROS:
        raise base.Erro(f"gênero {g!r} inválido.", f"Use um de: {', '.join(GENEROS)}.", base.USO)
    return {"id": _slug_id(n), "pedido_id": dados.get("pedido_id"), "o_que": dados["o_que"], "en": dados.get("en"),
            "genero": g, "pessoa": dados.get("pessoa"), "tipo": dados.get("tipo") or "imagem",
            "orientacao": dados.get("orientacao") or "qualquer", "min_duracao": dados.get("min_duracao"),
            "so_citacao": bool(dados.get("so_citacao")), "ordem": dados.get("ordem") or None,
            "status": "pendente", "fontes_tentadas": [], "candidatos": [], "a_conferir": [],
            "escolhidos": [], "citacao": None, "criado_em": agora()}


def carregar_necessidades(raiz: Path) -> dict:
    d = base.ler_json(raiz / NECESSIDADES)
    if not d:
        return {"versao": 1, "feito_em": agora(), "necessidades": []}
    d.setdefault("necessidades", [])
    return d


def achar(doc: dict, id_: str) -> dict:
    for n in doc["necessidades"]:
        if n["id"].lower() == str(id_).lower():
            return n
    conhecidos = ", ".join(n["id"] for n in doc["necessidades"]) or "(nenhuma)"
    raise base.Erro(f"não achei a necessidade {id_!r}.", f"Necessidades: {conhecidos}. Monte a lista com garimpar.py necessidades.", base.USO)


# ──────────────────────────────────────────────────────────────────── a busca ──
def _buscar_fonte(d, nec: dict, fonte: str, cfg: dict, http, avisar):
    """UMA consulta a UMA fonte, pela video-broll. É o único ponto desta skill que fala com a rede."""
    _comum, _prov, buscar_mod, _baixar = base.broll()
    return buscar_mod.buscar(d, nec["o_que"], nec.get("en"), nec.get("tipo") or "imagem",
                             nec.get("orientacao") or "qualquer", [fonte], int(cfg["por_fonte"]),
                             nec.get("min_duracao"), 600.0, None, None, "permitidas", False, True,
                             nec.get("pedido_id"), http, avisar)


def _resumir(c: dict, slug: str, rotulo: str) -> dict:
    """O candidato como o garimpo o guarda: o bastante para mostrar, creditar e mandar baixar depois."""
    return {"fonte": c.get("fonte"), "busca": slug, "n_na_busca": c.get("n"), "tipo": c.get("tipo"),
            "titulo": c.get("titulo"), "autor": c.get("autor"), "pagina_url": c.get("pagina_url"),
            "miniatura_url": c.get("miniatura_url"), "largura": c.get("largura"), "altura": c.get("altura"),
            "duracao": c.get("duracao"), "licenca": c.get("licenca"), "licenca_id": c.get("licenca_id"),
            "licenca_url": c.get("licenca_url"), "exige_atribuicao": c.get("exige_atribuicao"),
            "rotulo_licenca": rotulo, "descricao": c.get("descricao"), "legenda": identidade.legenda_do_candidato(c)}


def buscar_necessidade(d, nec: dict, cfg: dict, http=None, avisar=None, folha: bool = False) -> dict:
    """Percorre as fontes na ordem de preferência, com pausa entre pedidos, e para quando já basta.
    Para necessidade de PESSOA, confere a identidade pela legenda antes de propor."""
    _comum, _prov, buscar_mod, _baixar = base.broll()
    avisar = avisar or (lambda m: base.diz(m))
    if nec.get("so_citacao"):
        nec["status"] = "citacao"
        avisar(f"  {nec['id']}: é pedido de vídeo de terceiro — vai por citação (garimpar.py citar), não por banco.")
        return nec
    http = http or _comum.Http()
    pausa = float(cfg.get("pausa_s") or 0)
    bastam = int(cfg.get("bastam") or 4)
    fila = ordem_da(nec, cfg)
    achados, a_conferir, tentadas, folhas = [], [], [], []
    for fonte in fila:
        if fonte not in _prov.PROVEDORES:
            avisar(f"  · fonte desconhecida, pulada: {fonte}")
            continue
        base.respirar(pausa, f"{nec['id']} → {fonte}", avisar)
        try:
            r = _buscar_fonte(d, nec, fonte, cfg, http, lambda m: avisar(f"  {m}"))
        except _comum.Erro as e:
            tentadas.append({"fonte": fonte, "achados": 0, "erro": _comum.mascarar(e.mensagem)})
            avisar(f"  · {fonte}: {e.mensagem}")
            if e.codigo == _comum.SAIDA_SEM_REDE:
                break
            continue
        cands = r.get("candidatos") or []
        if folha and cands:
            try:
                folhas.append(str(buscar_mod.folha(d, r, colunas=4, http=http)))
            except Exception as e:                        # a folha é conforto: falhar nela não derruba a busca
                avisar(f"  · folha de contato não saiu ({e})")
        resumidos = [_resumir(c, r["slug"], buscar_mod.rotulo_licenca(c)[0]) for c in cands]
        if nec.get("pessoa"):
            for res, cru in zip(resumidos, cands):
                res["identidade"] = identidade.conferir(nec["pessoa"], cru)
            bons = [c for c in resumidos if c["identidade"]["veredito"] == "confere"]
            a_conferir += [c for c in resumidos if c["identidade"]["veredito"] != "confere"]
            resumidos = bons
        tentadas.append({"fonte": fonte, "achados": len(resumidos), "vistos": len(cands), "busca": r["slug"], "erro": None})
        achados += resumidos
        avisar(f"  · {fonte}: {len(resumidos)} candidato(s) de {len(cands)} visto(s)"
               + (" — já basta" if len(achados) >= bastam else ""))
        if len(achados) >= bastam:
            break
    for i, c in enumerate(achados, 1):
        c["n"] = i
    for i, c in enumerate(a_conferir, 1):
        c["n"] = f"x{i}"
    nec["candidatos"], nec["a_conferir"], nec["fontes_tentadas"] = achados, a_conferir, tentadas
    nec["folhas"] = folhas
    nec["buscado_em"] = agora()
    nec["status"] = "candidatos" if achados else ("sem_candidato" if not a_conferir else "a_conferir")
    return nec


# ───────────────────────────────────────────────────────────────────── saídas ──
def linha_candidato(c: dict) -> str:
    dims = f"{c['largura']}×{c['altura']}" if c.get("largura") and c.get("altura") else "?"
    ident = ""
    if c.get("identidade"):
        ident = f"  [identidade: {c['identidade']['veredito']} — {c['identidade']['porque']}]"
    return (f"   {str(c['n']):>3}  {c['fonte']:10} {('vídeo' if c['tipo'] == 'video' else 'imagem'):6} {dims:>11}  "
            f"{c.get('rotulo_licenca') or c.get('licenca') or '?'}\n"
            f"        {(c.get('titulo') or '(sem título)')[:86]}\n        {c.get('pagina_url') or ''}{ident}")


def imprimir(doc: dict, raiz: Path) -> None:
    for n in doc["necessidades"]:
        marca = {"pendente": "·", "candidatos": "✓", "escolhido": "★", "sem_candidato": "!", "a_conferir": "?", "citacao": "»"}.get(n["status"], "·")
        pessoa = f" · pessoa: {n['pessoa']}" if n.get("pessoa") else ""
        base.diz(f"{marca} {n['id']}  {n['o_que']}  ({n['genero']} · {n['tipo']}{pessoa})  [{n['status']}]")
        for c in n.get("candidatos") or []:
            base.diz(linha_candidato(c))
        if n.get("a_conferir"):
            base.diz(f"      {len(n['a_conferir'])} candidato(s) com identidade NÃO confirmada (não entram na proposta):")
            for c in n["a_conferir"][:3]:
                base.diz(linha_candidato(c))
        for f in n.get("folhas") or []:
            base.diz(f"      folha de contato: {f}")


def creditos_md(raiz: Path, doc: dict) -> Path:
    """Licença e crédito de tudo que o garimpo propôs ou o usuário escolheu — antes mesmo de baixar."""
    linhas = ["# Créditos do garimpo", "",
              "Licença e crédito de cada mídia candidata, como a FONTE declarou. Depois do download, o registro oficial",
              "é `broll/licencas.json` (video-broll) e o texto público é `broll/creditos.md`.", ""]
    total = 0
    for n in doc["necessidades"]:
        escolhidos = {c for c in (n.get("escolhidos") or [])}
        lista = [c for c in (n.get("candidatos") or []) if not escolhidos or c["n"] in escolhidos]
        if not lista and not n.get("citacao"):
            continue
        linhas.append(f"## {n['id']} — {n['o_que']}")
        for c in lista:
            total += 1
            estrela = " **(escolhida)**" if c["n"] in escolhidos else ""
            atrib = "crédito obrigatório" if c.get("exige_atribuicao") else "crédito opcional"
            linhas.append(f"- `{n['id']}-{c['n']}`{estrela} · {c.get('titulo') or '(sem título)'} — {c.get('autor') or 'autor não informado'} · "
                          f"{c.get('licenca') or 'licença não informada'} ({atrib})")
            linhas.append(f"  - fonte: {c['fonte']} · {c.get('pagina_url') or ''}")
            if c.get("identidade"):
                linhas.append(f"  - identidade: {c['identidade']['veredito']} — {c['identidade']['porque']}")
        if n.get("citacao"):
            cit = n["citacao"]
            total += 1
            linhas.append(f"- **citação** · {cit['url']} · {cit['t0']}–{cit['t1']} ({cit['duracao_s']:.1f} s, sem som) — "
                          f"crédito na tela: {cit['credito']}")
        linhas.append("")
    linhas.append(f"_{total} item(ns) · gerado por video-garimpo-de-midia em {agora()}_")
    return base.gravar_texto(raiz / CREDITOS, "\n".join(linhas) + "\n")


# ──────────────────────────────────────────────────────────────────────── CLI ──
def _numeros(texto: str) -> list[int]:
    saida = []
    for parte in re.split(r"[,\s]+", str(texto).strip()):
        if not parte:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", parte)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            saida += list(range(min(a, b), max(a, b) + 1))
        elif parte.isdigit():
            saida.append(int(parte))
        else:
            raise base.Erro(f"número de candidato inválido: {parte!r}", "Use algo como 2,5 ou 1-3.", base.USO)
    return sorted(dict.fromkeys(saida))


def _tempo(v) -> float:
    t = str(v).strip()
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{2}(?:\.\d+)?)", t)
    if not m:
        raise base.Erro(f"tempo inválido: {v!r}", "Use segundos (12.5), mm:ss (1:10) ou hh:mm:ss.", base.USO)
    return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main(argv=None) -> int:
    ap = base.Parser(prog="garimpar.py", description="Garimpo de mídia por necessidade em bancos livres, na ordem de preferência. "
                     "Não baixa nada: propõe, confere licença e identidade, e imprime o comando de download para depois do «sim».")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("necessidades", help="monta ou acrescenta necessidades (lê roteiro/pauta.json)")
    p.add_argument("--nova", metavar="TEXTO", help="acrescenta uma necessidade à mão (o conceito visual, em português)")
    p.add_argument("--en", metavar="TEXTO", help="a mesma coisa em inglês (é onde os acervos rendem)")
    p.add_argument("--genero", choices=GENEROS, help="padrão: ambiente (ou pessoa, se vier --pessoa)")
    p.add_argument("--pessoa", metavar="NOME", help="nome de quem precisa aparecer na foto (liga a conferência de identidade)")
    p.add_argument("--tipo", choices=("imagem", "video", "ambos"), default="imagem")
    p.add_argument("--orientacao", choices=("horizontal", "vertical", "quadrado", "qualquer"), default="qualquer")
    p.add_argument("--min-duracao", type=float, metavar="S")
    p.add_argument("--so-citacao", action="store_true", help="material de terceiro: entra só como citação (YouTube ≤ 10 s, sem som)")
    p.add_argument("--ordem", metavar="A,B", help="ordem de fontes só desta necessidade")

    p = sub.add_parser("fontes", help="mostra ou muda a ordem de preferência e a pausa")
    p.add_argument("--ordem", metavar="A,B", help=f"ordem geral (padrão: {','.join(ORDEM_PADRAO)})")
    p.add_argument("--pausa", type=float, metavar="S", help="segundos entre pedidos (padrão 2)")
    p.add_argument("--por-fonte", type=int, metavar="N", help="resultados por fonte (padrão 6)")
    p.add_argument("--bastam", type=int, metavar="N", help="quantos candidatos bons encerram a fila de fontes (padrão 4)")

    p = sub.add_parser("buscar", help="busca os candidatos das necessidades pendentes (não baixa mídia)")
    p.add_argument("ids", nargs="*", metavar="N001", help="padrão: todas as pendentes")
    p.add_argument("--pausa", type=float, metavar="S")
    p.add_argument("--bastam", type=int, metavar="N")
    p.add_argument("--folha", action="store_true", help="gera a folha de contato da video-broll (baixa só as miniaturas)")
    p.add_argument("--refazer", action="store_true", help="busca de novo o que já tem candidato")

    p = sub.add_parser("listar", help="o estado de cada necessidade")

    p = sub.add_parser("escolher", help="registra a escolha do usuário e imprime o comando de download")
    p.add_argument("id", metavar="N001")
    p.add_argument("--numeros", required=True, metavar="N,N", help="números dos candidatos (ex.: 2,5 ou 1-3)")

    p = sub.add_parser("citar", help="plano de citação de vídeo de terceiro (YouTube): ≤ 10 s, sem som, com crédito")
    p.add_argument("id", metavar="N004")
    p.add_argument("--url", required=True)
    p.add_argument("--t0", required=True, help="início (segundos ou mm:ss)")
    p.add_argument("--t1", required=True, help="fim")
    p.add_argument("--credito", help="crédito que vai na tela (padrão: «Reprodução» + o canal, a preencher)")
    p.add_argument("--porque", help="por que o trecho é citado (vira a nota da base legal)")

    sub.add_parser("creditos", help="grava broll/garimpo/creditos.md com licença e crédito de tudo")

    for s in sub.choices.values():
        s.add_argument("--projeto", metavar="PASTA", help="raiz do projeto (padrão: acha pela pasta atual)")
        s.add_argument("--json", action="store_true", help="saída em JSON")
    a = ap.parse_args(argv)
    raiz = base.achar_projeto(a.projeto)
    doc = carregar_necessidades(raiz)
    cfg = cfg_carregar(raiz)

    if a.cmd == "fontes":
        if a.ordem:
            cfg["ordem"] = [f.strip() for f in a.ordem.split(",") if f.strip()]
        for campo, valor in (("pausa_s", a.pausa), ("por_fonte", a.por_fonte), ("bastam", a.bastam)):
            if valor is not None:
                cfg[campo] = valor
        base.gravar_json(raiz / FONTES, cfg)
        if a.json:
            print(json.dumps(cfg, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"Ordem de preferência: {' → '.join(cfg['ordem'])}")
        for g, o in (cfg.get("por_genero") or {}).items():
            base.diz(f"  {g:10} {' → '.join(o)}")
        base.diz(f"Pausa entre pedidos: {cfg['pausa_s']:g} s · {cfg['por_fonte']} resultado(s) por fonte · "
                 f"{cfg['bastam']} candidato(s) bons encerram a fila")
        base.diz(f"YouTube: só citação de até {cfg['youtube']['max_s']:g} s, sem som, com crédito na tela")
        base.diz(f"Gravado em {raiz / FONTES}")
        return 0

    if a.cmd == "necessidades":
        n_ini = len(doc["necessidades"])
        vistos = {(n["o_que"].strip().lower(), n.get("pedido_id")) for n in doc["necessidades"]}
        novas = []
        if a.nova:
            novas.append({"o_que": a.nova, "en": a.en, "genero": a.genero, "pessoa": a.pessoa, "tipo": a.tipo,
                          "orientacao": a.orientacao, "min_duracao": a.min_duracao, "so_citacao": a.so_citacao,
                          "ordem": [f.strip() for f in a.ordem.split(",")] if a.ordem else None})
        else:
            novas += _da_pauta(raiz)
        for nova in novas:
            chave = (nova["o_que"].strip().lower(), nova.get("pedido_id"))
            if chave in vistos:
                continue
            vistos.add(chave)
            doc["necessidades"].append(nova_necessidade(nova, len(doc["necessidades"]) + 1))
        doc["feito_em"] = agora()
        base.gravar_json(raiz / NECESSIDADES, doc)
        if a.json:
            print(json.dumps(doc, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"{len(doc['necessidades']) - n_ini} necessidade(s) nova(s); {len(doc['necessidades'])} no total.")
        if not doc["necessidades"]:
            base.diz("Nenhuma necessidade: a pauta (roteiro/pauta.json) não tem pedido de banco ou de imagem da web em aberto.\n"
                     "Acrescente à mão: garimpar.py necessidades --nova \"sala de servidores\" --en \"server room\" --tipo video")
            return 1
        imprimir(doc, raiz)
        base.diz(f"\nGravado em {raiz / NECESSIDADES}\nAgora: garimpar.py buscar")
        return 0

    if a.cmd == "buscar":
        alvos = [achar(doc, i) for i in a.ids] if a.ids else [n for n in doc["necessidades"]
                                                              if a.refazer or n["status"] in ("pendente", "sem_candidato", "a_conferir")]
        if not alvos:
            base.diz("Nada pendente. `garimpar.py listar` mostra o estado; --refazer busca de novo.")
            return 0
        for campo, valor in (("pausa_s", a.pausa), ("bastam", a.bastam)):
            if valor is not None:
                cfg[campo] = valor
        _comum, _prov, _buscar, _baixar = base.broll()
        d, _da = _comum.carregar_da(str(raiz))                     # Passo 0: sem DA, código 2
        http = _comum.Http()
        base.diz(f"Garimpo de {len(alvos)} necessidade(s) · pausa {cfg['pausa_s']:g} s · ordem padrão {' → '.join(cfg['ordem'])}\n")
        for nec in alvos:
            base.diz(f"{nec['id']}  «{nec['o_que']}»" + (f" / «{nec['en']}»" if nec.get("en") else "")
                     + f"  ({nec['genero']})  fontes: {' → '.join(ordem_da(nec, cfg))}")
            buscar_necessidade(d, nec, cfg, http, base.diz, folha=a.folha)
        doc["feito_em"] = agora()
        base.gravar_json(raiz / NECESSIDADES, doc)
        creditos_md(raiz, doc)
        if a.json:
            print(json.dumps(doc, ensure_ascii=False, indent=1))
            return 0
        base.diz("")
        imprimir(doc, raiz)
        base.diz(f"\nGravado em {raiz / NECESSIDADES} · créditos em {raiz / CREDITOS}")
        base.diz("MOSTRE os candidatos (ou a folha de contato) ao usuário. Nada é baixado antes do «sim» dele:\n"
                 "  garimpar.py escolher N001 --numeros 2,5    → imprime o comando de download")
        return 0 if any(n.get("candidatos") for n in alvos) else 1

    if a.cmd == "listar":
        if a.json:
            print(json.dumps(doc, ensure_ascii=False, indent=1))
            return 0
        if not doc["necessidades"]:
            base.diz("Nenhuma necessidade ainda. Rode garimpar.py necessidades.")
            return 1
        imprimir(doc, raiz)
        return 0

    if a.cmd == "escolher":
        nec = achar(doc, a.id)
        nums = _numeros(a.numeros)
        por_n = {c["n"]: c for c in (nec.get("candidatos") or []) if isinstance(c.get("n"), int)}
        faltam = [n for n in nums if n not in por_n]
        if faltam:
            raise base.Erro(f"{nec['id']} não tem o(s) candidato(s) {faltam}.",
                            f"Números disponíveis: {sorted(por_n) or '(nenhum — rode garimpar.py buscar)'}.", base.USO)
        nec["escolhidos"] = nums
        nec["status"] = "escolhido"
        doc["feito_em"] = agora()
        base.gravar_json(raiz / NECESSIDADES, doc)
        creditos_md(raiz, doc)
        # agrupa por busca: baixar.py recebe os números DAQUELA busca
        por_busca: dict[str, list[int]] = {}
        for n in nums:
            c = por_n[n]
            por_busca.setdefault(c["busca"], []).append(c["n_na_busca"])
        comandos = [f'python3 <skills>/video-broll/scripts/baixar.py --busca "{slug}" --escolher {",".join(str(x) for x in sorted(ns))}'
                    + (f' --pedido {nec["pedido_id"]}' if nec.get("pedido_id") else "") for slug, ns in por_busca.items()]
        saida = {"necessidade": nec["id"], "escolhidos": [{"codigo": f"{nec['id']}-{n}", **por_n[n]} for n in nums], "comandos": comandos}
        if a.json:
            print(json.dumps(saida, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"{nec['id']}: {len(nums)} escolhido(s).")
        for n in nums:
            c = por_n[n]
            base.diz(f"  {nec['id']}-{n}  {c.get('titulo') or ''}  [{c.get('rotulo_licenca')}]")
            if c.get("identidade"):
                base.diz(f"      identidade: {c['identidade']['veredito']} — {c['identidade']['porque']}")
        base.diz("\nCom o «sim» do usuário, o download é da video-broll (ela monta o plano e só baixa com --confirmar):")
        for c in comandos:
            base.diz(f"  {c}")
        base.diz("\nO registro de licença e crédito é automático lá (broll/licencas.json + broll/creditos.md).")
        return 0

    if a.cmd == "citar":
        nec = achar(doc, a.id)
        t0, t1 = _tempo(a.t0), _tempo(a.t1)
        teto = float(cfg["youtube"]["max_s"])
        if t1 <= t0:
            raise base.Erro("o fim da citação tem de ser depois do começo.", f"Veio t0={a.t0} e t1={a.t1}.", base.USO)
        if t1 - t0 > teto:
            raise base.Erro(f"citação de {t1 - t0:.1f} s passa do teto de {teto:g} s desta política.",
                            f"Encurte o trecho (ou mude o teto em {FONTES.as_posix()}, sabendo o que está fazendo).", base.USO)
        nec["citacao"] = {"url": a.url, "t0": a.t0, "t1": a.t1, "duracao_s": round(t1 - t0, 2), "sem_som": bool(cfg["youtube"]["sem_som"]),
                          "credito": a.credito or "Reprodução · <canal> (preencher)",
                          "porque": a.porque or "citação de trecho curto para comentar o que foi dito",
                          "planejado_em": agora()}
        nec["status"] = "citacao"
        doc["feito_em"] = agora()
        base.gravar_json(raiz / NECESSIDADES, doc)
        creditos_md(raiz, doc)
        cmd = (f'python3 <skills>/video-pauta-midia/scripts/youtube.py baixar "{a.url}" --t0 {a.t0} --t1 {a.t1} '
               f'--base-legal citacao --nota "{nec["citacao"]["porque"]}"'
               + (f' --pedido {nec["pedido_id"]}' if nec.get("pedido_id") else ""))
        if a.json:
            print(json.dumps({"necessidade": nec["id"], "citacao": nec["citacao"], "comando": cmd}, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"{nec['id']}: citação de {t1 - t0:.1f} s planejada (teto {teto:g} s).")
        base.diz(f"  trecho: {a.t0} → {a.t1} · SEM SOM na montagem · crédito na tela: {nec['citacao']['credito']}")
        base.diz("\nCom o «sim» do usuário (e o crédito preenchido), o download do trecho é da video-pauta-midia:")
        base.diz(f"  {cmd}")
        base.diz("  (ela imprime o plano; só baixa com --confirmar)")
        base.diz("Na montagem: mudo, com o crédito na tela durante todo o trecho.")
        return 0

    if a.cmd == "creditos":
        arq = creditos_md(raiz, doc)
        if a.json:
            print(json.dumps({"arquivo": str(arq)}, ensure_ascii=False))
            return 0
        base.diz(f"Créditos em {arq}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(base.rodar(main))
