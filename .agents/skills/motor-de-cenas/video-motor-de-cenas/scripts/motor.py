#!/usr/bin/env python3
"""motor.py — CLI do motor de cenas: lê `animacoes/cenas.json` (cada cena ancorada por um TRECHO DA FALA),
resolve as âncoras contra `transcricao/palavras.json`, renderiza pelo kit de direção de arte e escreve os
eventos de som.

  python3 motor.py resolver "<projeto>"            âncora → tempo; grava animacoes/cenas.resolvidas.json
  python3 motor.py prova    "<projeto>"            1 PNG por cena em qa/ (metade da resolução) — OLHE ANTES
  python3 motor.py render   "<projeto>"            renderiza as cenas em animacoes/
  python3 motor.py eventos  "<projeto>"            som/eventos_motor.json a partir dos carimbos
  python3 motor.py tudo     "<projeto>"            resolver + render + eventos

Códigos de saída: 0 ok · 1 falhou · 2 projeto sem direção de arte · 64 uso incorreto.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import ancoras as anc
import catalogo as cat_mod
import comum
from comum import Erro, Parser, diz, gravar_json, ler_json, mmss, nome_de_arquivo, projeto, rodar

PARECIDO_BOM = 0.90                 # abaixo disto a âncora casou "mais ou menos": sai aviso com o que casou
RESPIRO = 0.15                      # dois eventos de som a menos que isto um do outro: fica só o primeiro
SOM_PADRAO = {"entrada": ("whoosh", -20), "enfase": ("impacto", -18), "saida": ("whoosh", -22),
              "texto": ("datilografia", -26), "numero": ("tick", -24)}
TIPOS_DISCRETOS = ("entrada", "enfase")      # o que entra no eventos_motor.json sem --todos


# ────────────────────────────────────────────────────────────── ler o pedido ──
def ler_pedido(proj: Path, arquivo=None) -> dict:
    """animacoes/cenas.json normalizado: {transcricao, formato, som, cenas:[...]}."""
    alvo = Path(arquivo) if arquivo else proj / "animacoes" / "cenas.json"
    if not alvo.is_absolute():
        alvo = proj / alvo
    dados = ler_json(alvo, "roteiro de cenas (animacoes/cenas.json)")
    if isinstance(dados, list):
        dados = {"cenas": dados}
    if not isinstance(dados, dict) or not isinstance(dados.get("cenas"), list) or not dados["cenas"]:
        raise Erro(f"{alvo} não tem a lista `cenas`.",
                   'Formato: {"cenas": [{"id": "c01", "tipo": "texto", "ancora": "o que ele fala aqui", "params": {…}}]}',
                   comum.SAIDA_USO)
    dados["_arquivo"] = alvo
    return dados


def _caminho_palavras(proj: Path, pedido: dict) -> Path:
    p = Path(pedido.get("transcricao") or "transcricao/palavras.json")
    p = p if p.is_absolute() else proj / p
    if not p.is_file():
        raise Erro(f"não achei a transcrição palavra a palavra em {p}.",
                   "Rode a skill video-transcricao primeiro: sem os tempos das palavras não há âncora que resolva.")
    return p


# ──────────────────────────────────────────────────── âncoras dentro de params ──
def _trocar_ancoras(valor, regra: dict, resolver, caminho: str, avisos: list):
    """Param numérico escrito como "@trecho da fala" vira segundos DENTRO da cena (0 = começo dela).

    Só vale onde a cena declara `numero`/`inteiro` — ali uma string já seria inválida, então não há ambiguidade
    com um texto que por acaso comece por @."""
    tipo = (regra or {}).get("tipo")
    if tipo in ("numero", "inteiro") and isinstance(valor, str) and valor.startswith("@"):
        return resolver(valor[1:].strip(), caminho)
    if tipo == "lista" and isinstance(valor, list) and (regra or {}).get("itens"):
        return [_trocar_ancoras(v, regra["itens"], resolver, f"{caminho}[{i}]", avisos) for i, v in enumerate(valor)]
    if tipo == "objeto" and isinstance(valor, dict) and (regra or {}).get("campos"):
        return {k: _trocar_ancoras(v, regra["campos"].get(k, {}), resolver, f"{caminho}.{k}", avisos)
                for k, v in valor.items()}
    return valor


# ───────────────────────────────────────────────────────────────── resolver ──
def resolver(proj: Path, arquivo=None, formato=None) -> dict:
    """Resolve toda âncora em tempo e devolve o plano {cenas, avisos}. Não renderiza nada."""
    pedido = ler_pedido(proj, arquivo)
    palavras = anc.carregar_palavras(_caminho_palavras(proj, pedido))
    cat = cat_mod.carregar()
    fmt_geral = formato or pedido.get("formato") or "horizontal"
    avisos, saida, desde = [], [], 0.0

    for n, bruta in enumerate(pedido["cenas"], 1):
        ident = str(bruta.get("id") or f"c{n:02d}")
        tipo = bruta.get("tipo") or bruta.get("cena")
        if not tipo:
            raise Erro(f"cena {ident}: faltou `tipo` (qual cena da biblioteca). Veja: catalogo.py", codigo=comum.SAIDA_USO)
        meta = cat_mod.meta_de(cat, tipo)
        if bruta.get("desde") is not None:
            desde = float(bruta["desde"])

        # 1. quando a cena começa
        casou = parecido = None
        if bruta.get("t0") is not None:
            t0 = float(bruta["t0"])
        else:
            texto = bruta.get("ancora")
            if not texto:
                raise Erro(f"cena {ident} ({tipo}): faltou `ancora` (o trecho da fala) ou `t0`.", codigo=comum.SAIDA_USO)
            r = anc.resolver(texto, palavras, desde)
            if not r:
                raise Erro(f"cena {ident} ({tipo}): não achei na fala o trecho {texto!r} a partir de {mmss(desde)}.",
                           "Confira a transcrição (transcricao/texto.txt). A âncora é o que a pessoa FALA, não o "
                           "texto que vai na tela; copie 4 a 8 palavras seguidas.")
            t0 = r["t1"] if bruta.get("em") == "fim" else r["t0"]
            casou, parecido, desde = r["casou"], r["parecido"], r["t1"]
            if parecido < PARECIDO_BOM:
                avisos.append(f"{ident}: âncora {texto!r} casou por aproximação ({parecido:.2f}) com {casou!r} "
                              f"em {mmss(r['t0'])} — confira.")
        t0 = max(0.0, t0 + float(bruta.get("folga") or 0))

        # 2. quanto dura
        if bruta.get("ate"):
            r2 = anc.resolver(bruta["ate"], palavras, max(desde, t0))
            if not r2:
                raise Erro(f"cena {ident} ({tipo}): não achei na fala o trecho de `ate` ({bruta['ate']!r}).")
            dur = round(r2["t0"] - t0, 3)
            desde = r2["t0"]
        else:
            dur = float(bruta.get("dur") or meta.get("dur_padrao") or 4)
        if dur < 1.0:
            avisos.append(f"{ident}: duração de {dur:.2f} s — curta demais para a cena entrar e sair; usei 1,0 s.")
            dur = 1.0

        # 3. parâmetros (com as âncoras dentro deles) e conferência contra o catálogo
        regras = meta.get("params") or {}
        params = dict(bruta.get("params") or {})

        def dentro_da_cena(texto_ancora: str, onde: str, ident=ident, t0=t0):
            """"@trecho" dentro de um param: procurado a partir do começo da cena (meio segundo de folga)."""
            r3 = anc.resolver(texto_ancora, palavras, max(0.0, t0 - 0.5))
            if not r3:
                raise Erro(f"cena {ident}: em {onde}, não achei na fala o trecho {texto_ancora!r}.")
            return max(0.0, round(r3["t0"] - t0, 3))

        for chave, valor in list(params.items()):
            if chave in regras:
                params[chave] = _trocar_ancoras(valor, regras[chave], dentro_da_cena, chave, avisos)
        problemas = cat_mod.conferir_params(cat, tipo, params, raiz=proj)
        if problemas:
            raise Erro(f"cena {ident} ({tipo}): " + "; ".join(problemas[:4]),
                       f"Parâmetros desta cena: python3 catalogo.py {tipo}", comum.SAIDA_USO)

        alfa = bool(bruta["alfa"]) if bruta.get("alfa") is not None else bool(meta.get("alfa_padrao"))
        base = f"{nome_de_arquivo(ident, 12)}-{nome_de_arquivo(tipo, 20)}"
        saida.append({
            "id": ident, "tipo": tipo, "arquivo_cena": str((cat["pasta"] / meta["arquivo"]).resolve()),
            "t0": round(t0, 3), "t1": round(t0 + dur, 3), "dur": round(dur, 3),
            "ancora": bruta.get("ancora"), "casou": casou, "parecido": parecido,
            "formato": bruta.get("formato") or fmt_geral, "alfa": alfa, "params": params,
            "saida": f"animacoes/{base}{'.mov' if alfa else '.mp4'}",
            "prova": f"qa/_prova-{base}.png", "som": bruta.get("som") or {},
        })

    # 4. cenas que se atropelam (duas telas cheias ao mesmo tempo é erro de roteiro; overlay com alfa, não)
    cheias = [c for c in saida if not c["alfa"]]
    for a, b in zip(cheias, cheias[1:]):
        if b["t0"] < a["t1"] - 0.01:
            avisos.append(f"{b['id']} começa em {mmss(b['t0'])}, antes de {a['id']} acabar ({mmss(a['t1'])}): "
                          f"{a['t1'] - b['t0']:.2f} s de sobreposição entre duas cenas opacas.")
    return {"projeto": str(proj), "transcricao": str(_caminho_palavras(proj, pedido)), "formato": fmt_geral,
            "som": pedido.get("som") or {}, "cenas": saida, "avisos": avisos}


def _tabela(plano: dict) -> None:
    diz(f"{'id':10} {'cena':16} {'entra':>9} {'dur':>7}  âncora")
    for c in plano["cenas"]:
        marca = "" if c["parecido"] is None else ("  (~%.2f)" % c["parecido"] if c["parecido"] < PARECIDO_BOM else "")
        diz(f"{c['id']:10} {c['tipo']:16} {mmss(c['t0']):>9} {c['dur']:6.2f}s  {(c['casou'] or c['ancora'] or '—')[:48]}{marca}")
    for a in plano["avisos"]:
        diz(f"! {a}", erro=True)


# ───────────────────────────────────────────────────────────────── renderizar ──
def _plano_do_disco(proj: Path) -> dict:
    return ler_json(proj / "animacoes" / "cenas.resolvidas.json", "plano resolvido (rode `motor.py resolver` antes)")


def _jobs(plano: dict, proj: Path, so=None, prova: bool = False, escala: float | None = None) -> list[dict]:
    """Jobs da fila do motor. `saida` vai ABSOLUTA: na fila, caminho relativo conta a partir da pasta do
    próprio fila.json (animacoes/), e `qa/x.png` cairia em animacoes/qa/."""
    jobs = []
    for c in plano["cenas"]:
        if so and c["id"] not in so:
            continue
        rel = c["prova"] if prova else c["saida"]
        job = {"_id": c["id"], "_rel": rel, "cena": c["arquivo_cena"], "formato": c["formato"],
               "dur": c["dur"], "params": c["params"], "saida": str((proj / rel).resolve())}
        if prova:
            # um instante depois da entrada e antes da saída: é onde a cena está "cheia"
            job.update({"quadro": round(c["dur"] * 0.72, 3), "escala": escala or 0.5, "alfa": False})
        else:
            job["alfa"] = c["alfa"]
            if c["alfa"]:
                job["codec"] = "prores4444"
            if escala:
                job["escala"] = escala
        jobs.append(job)
    if not jobs:
        raise Erro("nenhuma cena selecionada." + (f" Ids do plano: {', '.join(c['id'] for c in plano['cenas'])}" if so else ""),
                   codigo=comum.SAIDA_USO)
    return jobs


def renderizar(proj: Path, plano: dict, so=None, prova: bool = False, escala=None, refazer: bool = False) -> dict:
    """Renderiza pela fila do kit (um browser só) e devolve {feitas, falhas, segundos}."""
    jobs = _jobs(plano, proj, so, prova, escala)
    if not refazer:
        fonte = max((f.stat().st_mtime for f in [proj / "animacoes" / "cenas.json",
                                                 proj / "animacoes" / "cenas.resolvidas.json"] if f.is_file()), default=0)
        pendentes = [j for j in jobs if not ((proj / j["_rel"]).is_file() and (proj / j["_rel"]).stat().st_mtime >= fonte)]
        if len(pendentes) < len(jobs):
            diz(f"{len(jobs) - len(pendentes)} cena(s) já estão em dia (use --refazer para refazer todas).")
        jobs = pendentes
        if not jobs:
            return {"feitas": [], "falhas": [], "segundos": 0.0}

    fila = gravar_json(proj / "animacoes" / "_fila_motor.json", jobs)
    cmd = [comum.python_do_kit(), comum.kit() / "da.py", "--de", proj, "render", "--fila", fila]
    diz(f"renderizando {len(jobs)} cena(s) pelo motor da direção de arte…")
    inicio = time.monotonic()
    r = comum.rodar_programa(cmd, cwd=proj, capturar=False)
    gasto = time.monotonic() - inicio
    if r.returncode == comum.SAIDA_SEM_DA:
        raise Erro("o kit não achou a direção de arte do projeto.", codigo=comum.SAIDA_SEM_DA)
    feitas = [j for j in jobs if (proj / j["_rel"]).is_file()]
    prontos = {j["_id"] for j in feitas}
    falhas = [j["_id"] for j in jobs if j["_id"] not in prontos]
    if r.returncode not in (0, 1):
        raise Erro(f"o motor do kit saiu com código {r.returncode}.",
                   "Erro de uso (64) é parâmetro inválido: confira a cena apontada acima.", comum.SAIDA_ERRO)
    if r.returncode == 1 and not falhas:
        # o motor reprovou algo mas o arquivo antigo continua no disco: não é um render novo
        diz("! o motor reprovou pelo menos uma cena (veja o RESUMO acima); o arquivo no disco é o anterior.", erro=True)
        falhas = ["(veja o RESUMO do motor)"]
    return {"feitas": [j["_id"] for j in feitas], "falhas": falhas, "segundos": round(gasto, 1),
            "arquivos": [j["_rel"] for j in feitas]}


# ────────────────────────────────────────────────────────────── som ──
def eventos(proj: Path, plano: dict, todos: bool = False) -> list[dict]:
    """[{t, som, db}] a partir das âncoras que cada cena carimbou, em tempo do VÍDEO (t0 da cena + t local)."""
    som_geral = plano.get("som") or {}
    brutos, sem_carimbo = [], []
    for c in plano["cenas"]:
        carimbo = proj / (c["saida"] + ".da.json")
        if not carimbo.is_file():
            sem_carimbo.append(c["id"])
            continue
        dados = ler_json(carimbo, f"carimbo de {c['id']}")
        local = {**som_geral, **(c.get("som") or {})}
        for a in (dados.get("parametros") or {}).get("ancoras") or []:
            tipo = a.get("tipo") or "enfase"
            if not todos and tipo not in TIPOS_DISCRETOS:
                continue
            nome, db = SOM_PADRAO.get(tipo, ("tick", -24))
            escolha = local.get(tipo) or local.get(a.get("nome"))
            if isinstance(escolha, dict):
                nome, db = escolha.get("som", nome), escolha.get("db", db)
            elif isinstance(escolha, str):
                nome = escolha
            if local.get("db") is not None and not isinstance(escolha, dict):
                db = local["db"]
            if nome in ("", "nenhum", None):
                continue
            brutos.append({"t": round(c["t0"] + float(a.get("t") or 0), 3), "som": nome, "db": float(db)})
    brutos.sort(key=lambda e: e["t"])

    # "respira": dois sons colados viram ruído — fica o primeiro (a skill de SFX ainda faz a dela)
    saida, caiu = [], 0
    for e in brutos:
        if saida and e["t"] - saida[-1]["t"] < RESPIRO:
            caiu += 1
            continue
        saida.append(e)
    if caiu:
        diz(f"{caiu} evento(s) caíram por estarem a menos de {RESPIRO:.2f} s do anterior.")
    if sem_carimbo:
        diz(f"! sem carimbo (não renderizadas ainda): {', '.join(sem_carimbo)}", erro=True)
    return saida


# ────────────────────────────────────────────────────────────────────── CLI ──
def main() -> int:
    p = Parser(prog="motor.py", description="motor de cenas: âncora na fala → cena renderizada na direção de arte")
    p.add_argument("comando", choices=["resolver", "prova", "render", "eventos", "tudo", "catalogo"])
    p.add_argument("projeto", nargs="?", help="pasta do projeto (padrão: a pasta atual)")
    p.add_argument("--cenas", help="outro roteiro de cenas (padrão: animacoes/cenas.json)")
    p.add_argument("--so", help="só estas cenas, por id, separadas por vírgula")
    p.add_argument("--formato", help="horizontal, vertical, quadrado ou LxA (padrão: o do cenas.json)")
    p.add_argument("--escala", type=float, help="fração da resolução (0.5 = metade; prévia)")
    p.add_argument("--refazer", action="store_true", help="renderiza de novo mesmo o que já está em dia")
    p.add_argument("--todos-os-sons", action="store_true", help="eventos de som também para texto e números")
    args = p.parse_args()

    if args.comando == "catalogo":
        return cat_mod.main()
    proj = projeto(args.projeto)
    so = [s.strip() for s in args.so.split(",") if s.strip()] if args.so else None

    if args.comando in ("resolver", "tudo") or not (proj / "animacoes" / "cenas.resolvidas.json").is_file():
        plano = resolver(proj, args.cenas, args.formato)
        gravar_json(proj / "animacoes" / "cenas.resolvidas.json", plano)
        _tabela(plano)
        diz(f"\n{len(plano['cenas'])} cena(s) resolvidas → animacoes/cenas.resolvidas.json")
        if args.comando == "resolver":
            diz("Agora olhe as prévias antes de renderizar: motor.py prova \"<projeto>\"")
            return 0
    else:
        plano = _plano_do_disco(proj)

    if args.comando == "prova":
        r = renderizar(proj, plano, so, prova=True, escala=args.escala, refazer=True)
        diz(f"{len(r['feitas'])} prévia(s) em {proj / 'qa'} ({r['segundos']} s). ABRA e mostre ao usuário antes do render.")
        return 1 if r["falhas"] else 0

    falhou = False
    if args.comando in ("render", "tudo"):
        r = renderizar(proj, plano, so, escala=args.escala, refazer=args.refazer)
        falhou = bool(r["falhas"])
        diz(f"{len(r['feitas'])} cena(s) renderizadas em {r['segundos']} s"
            + (f"; FALHARAM: {', '.join(r['falhas'])}" if falhou else ""))

    ev = eventos(proj, plano, args.todos_os_sons)
    gravar_json(proj / "som" / "eventos_motor.json", ev)
    diz(f"{len(ev)} evento(s) de som → som/eventos_motor.json (video-efeitos-sonoros sintetiza e mede o nível)")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(rodar(main))
