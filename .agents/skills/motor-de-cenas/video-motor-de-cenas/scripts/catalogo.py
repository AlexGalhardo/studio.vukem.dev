#!/usr/bin/env python3
"""catalogo.py — leitor do catálogo da biblioteca de cenas: diz que cenas existem, que parâmetros cada uma
aceita e confere um pedido ANTES de abrir o browser (erro apontando a cena do cenas.json, não um job sem nome).

  python3 catalogo.py                      tabela das cenas (nome, duração padrão, parâmetros obrigatórios)
  python3 catalogo.py texto numero         só essas, com todos os parâmetros
  python3 catalogo.py --json | --md        o catálogo inteiro em JSON ou em markdown

O conteúdo vem de `cenas/*.js` (o `meta` de cada módulo), lido por `scripts/catalogo.mjs` no Node e guardado
em cache em ~/.criabr/cache/ enquanto nenhum arquivo de cenas/ mudar.
"""
from __future__ import annotations

import hashlib
import json
import sys
from difflib import get_close_matches
from pathlib import Path

import comum
from comum import Erro, Parser, SKILL, diz, rodar

CENAS = SKILL / "cenas"
TIPOS_SIMPLES = {"texto": str, "numero": (int, float), "inteiro": int, "booleano": bool}


# ───────────────────────────────────────────────────────────────── carregar ──
def _assinatura(pasta: Path) -> str:
    """Identidade da pasta de cenas: nome, tamanho e mtime de cada .js (muda → o cache é refeito)."""
    arquivos = sorted(pasta.glob("*.js")) + [SKILL / "scripts" / "catalogo.mjs"]
    partes = [f"{f.name}:{f.stat().st_size}:{int(f.stat().st_mtime)}" for f in arquivos if f.is_file()]
    return f"{comum.VERSAO}|" + "|".join(partes)


def carregar(pasta=None, sem_cache: bool = False) -> dict:
    """{'pasta', 'cenas': {nome: meta}} da biblioteca. Roda o Node só quando o cache está velho."""
    pasta = Path(pasta).expanduser().resolve() if pasta else CENAS
    if not pasta.is_dir():
        raise Erro(f"não achei a biblioteca de cenas em {pasta}.", "A skill foi copiada pela metade?")
    assinatura = _assinatura(pasta)
    chave = hashlib.sha256(str(pasta).encode("utf-8")).hexdigest()[:12]
    cache = comum.casa_criabr() / "cache" / f"motor-de-cenas-{chave}.json"
    if not sem_cache:
        try:
            guardado = json.loads(cache.read_text(encoding="utf-8"))
            if guardado.get("assinatura") == assinatura:
                return {"pasta": pasta, "cenas": guardado["cenas"]}
        except (OSError, ValueError, KeyError):
            pass

    r = comum.rodar_programa([comum.node(), SKILL / "scripts" / "catalogo.mjs", pasta])
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise Erro(f"o Node não conseguiu ler a biblioteca de cenas em {pasta}: "
                   f"{(r.stderr or r.stdout or 'sem saída').strip().splitlines()[-1][:300]}")
    dados = json.loads(r.stdout)
    if dados.get("falhas"):
        f = dados["falhas"][0]
        raise Erro(f"a cena {f['arquivo']} não carrega: {f['erro']}")
    cenas = {c["nome"]: c for c in dados["cenas"]}
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        corpo = json.dumps({"assinatura": assinatura, "cenas": cenas}, ensure_ascii=False)
        cache.write_text(corpo, encoding="utf-8", newline="\n")
    except OSError:
        pass                                     # cache é conforto, não requisito
    return {"pasta": pasta, "cenas": cenas}


def meta_de(cat: dict, tipo: str) -> dict:
    """O `meta` da cena, ou Erro com sugestão quando o nome não existe."""
    if tipo in cat["cenas"]:
        return cat["cenas"][tipo]
    perto = get_close_matches(str(tipo), list(cat["cenas"]), n=1, cutoff=0.5)
    raise Erro(f"não existe cena {tipo!r}." + (f" Quis dizer {perto[0]!r}?" if perto else ""),
               "Cenas da biblioteca: " + ", ".join(sorted(cat["cenas"])), comum.SAIDA_USO)


# ───────────────────────────────────────────────────────────────── conferir ──
def _confere_valor(nome: str, valor, regra: dict, raiz: Path | None, problemas: list) -> None:
    tipo = regra.get("tipo") or "texto"
    if valor is None:
        return
    if tipo in TIPOS_SIMPLES:
        esperado = TIPOS_SIMPLES[tipo]
        if tipo != "booleano" and isinstance(valor, bool):
            problemas.append(f"{nome}: esperado {tipo}, veio booleano")
        elif not isinstance(valor, esperado):
            problemas.append(f"{nome}: esperado {tipo}, veio {json.dumps(valor, ensure_ascii=False)[:40]}")
        elif tipo in ("numero", "inteiro"):
            if regra.get("min") is not None and valor < regra["min"]:
                problemas.append(f"{nome}: {valor} é menor que o mínimo {regra['min']}")
            if regra.get("max") is not None and valor > regra["max"]:
                problemas.append(f"{nome}: {valor} é maior que o máximo {regra['max']}")
    elif tipo == "opcao":
        opcoes = regra.get("opcoes") or []
        if opcoes and valor not in opcoes:
            perto = get_close_matches(str(valor), [str(o) for o in opcoes], n=1, cutoff=0.5)
            problemas.append(f"{nome}: {valor!r} não é opção válida ({', '.join(map(str, opcoes))})"
                             + (f" — quis dizer {perto[0]!r}?" if perto else ""))
    elif tipo == "lista":
        if not isinstance(valor, list):
            problemas.append(f"{nome}: esperado lista")
            return
        if regra.get("min") is not None and len(valor) < regra["min"]:
            problemas.append(f"{nome}: a lista precisa de pelo menos {regra['min']} item(ns)")
        if regra.get("max") is not None and len(valor) > regra["max"]:
            problemas.append(f"{nome}: a lista aceita no máximo {regra['max']} item(ns), vieram {len(valor)}")
        for i, item in enumerate(valor):
            if item is None:
                problemas.append(f"{nome}[{i}]: item vazio (null) na lista")
            elif regra.get("itens"):
                _confere_valor(f"{nome}[{i}]", item, regra["itens"], raiz, problemas)
    elif tipo == "objeto":
        if not isinstance(valor, dict):
            problemas.append(f"{nome}: esperado objeto")
            return
        campos = regra.get("campos") or {}
        for chave, sub in campos.items():
            if sub.get("obrigatorio") and valor.get(chave) is None:
                problemas.append(f"{nome}.{chave}: faltou (obrigatório)")
            if chave in valor:
                _confere_valor(f"{nome}.{chave}", valor[chave], sub, raiz, problemas)
        for chave in valor:
            if campos and chave not in campos:
                perto = get_close_matches(chave, list(campos), n=1, cutoff=0.5)
                problemas.append(f"{nome}.{chave}: campo desconhecido" + (f" — quis dizer {perto[0]!r}?" if perto else ""))
    elif tipo == "arquivo":
        if not isinstance(valor, str):
            problemas.append(f"{nome}: esperado caminho de arquivo")
        elif raiz is not None and not (raiz / valor).is_file() and not Path(valor).is_file():
            problemas.append(f"{nome}: o arquivo não existe ({valor})")


def conferir_params(cat: dict, tipo: str, params: dict, raiz: Path | None = None) -> list[str]:
    """Problemas do pedido (lista vazia = passou). Cor, papel e plataforma ficam para o motor, que conhece a DA."""
    meta = meta_de(cat, tipo)
    regras = meta.get("params") or {}
    params = params or {}
    problemas = []
    if not isinstance(params, dict):
        return ["params devia ser um objeto {nome: valor}"]
    for chave, regra in regras.items():
        if regra.get("obrigatorio") and params.get(chave) is None:
            problemas.append(f"{chave}: faltou (obrigatório) — {regra.get('descricao') or regra.get('tipo')}")
    for chave, valor in params.items():
        if chave not in regras:
            perto = get_close_matches(chave, list(regras), n=1, cutoff=0.5)
            problemas.append(f"{chave}: parâmetro desconhecido em {tipo}" + (f" — quis dizer {perto[0]!r}?" if perto else ""))
            continue
        _confere_valor(chave, valor, regras[chave], raiz, problemas)
    return problemas


# ─────────────────────────────────────────────────────────────────── saídas ──
def _linha_param(chave: str, r: dict, nivel: int = 0) -> str:
    """Uma linha por parâmetro; lista com `itens` e objeto com `campos` descem indentados."""
    recuo = "  " + "    " * nivel
    marca = "obrigatório" if r.get("obrigatorio") else f"padrão {json.dumps(r.get('padrao'), ensure_ascii=False)}"
    opcoes = f" [{', '.join(map(str, r['opcoes']))}]" if r.get("opcoes") else ""
    faixa = ""
    if r.get("min") is not None or r.get("max") is not None:
        faixa = f" ({r.get('min', '')}…{r.get('max', '')})"
    linhas = [f"{recuo}- {chave} ({r.get('tipo')}{faixa}, {marca}){opcoes}"
              + (f" — {r['descricao']}" if r.get("descricao") else "")]
    if r.get("itens"):
        if r["itens"].get("campos"):
            for k, sub in r["itens"]["campos"].items():
                linhas.append(_linha_param(k, sub, nivel + 1))
        else:
            linhas.append(_linha_param("cada item", r["itens"], nivel + 1))
    for k, sub in (r.get("campos") or {}).items():
        linhas.append(_linha_param(k, sub, nivel + 1))
    return "\n".join(linhas)


def como_markdown(cat: dict) -> str:
    linhas = ["# Catálogo de cenas do motor", "",
              "Gerado por `scripts/catalogo.py --md`. Todas aceitam, além do que está aqui: `palco`",
              "(cartao·cheia·abre·fecha), `camera` (parada·aproxima·afasta), `chapeu`, `fonte`, `plataforma`",
              "e `reservar_legenda`.", ""]
    for nome in sorted(cat["cenas"]):
        m = cat["cenas"][nome]
        linhas += [f"## {nome}", "", m.get("descricao", ""), "",
                   f"- duração padrão: {m.get('dur_padrao')} s · alfa: {'sim' if m.get('alfa_padrao') else 'não'}", ""]
        for chave, r in (m.get("params") or {}).items():
            if chave in ("palco", "camera", "chapeu", "fonte", "plataforma", "reservar_legenda"):
                continue
            linhas.append(_linha_param(chave, r))
        linhas.append("")
    return "\n".join(linhas)


def main() -> int:
    p = Parser(prog="catalogo.py", description="o que a biblioteca de cenas do motor oferece")
    p.add_argument("nomes", nargs="*", help="cenas a detalhar (padrão: tabela de todas)")
    p.add_argument("--pasta", help="outra biblioteca de cenas (padrão: a desta skill)")
    p.add_argument("--json", action="store_true", help="imprime o catálogo em JSON")
    p.add_argument("--md", action="store_true", help="imprime o catálogo em markdown")
    p.add_argument("--sem-cache", action="store_true", help="relê os .js mesmo com cache válido")
    args = p.parse_args()

    cat = carregar(args.pasta, sem_cache=args.sem_cache)
    if args.json:
        diz(json.dumps({"pasta": str(cat["pasta"]), "cenas": cat["cenas"]}, ensure_ascii=False, indent=1))
        return 0
    if args.md:
        diz(como_markdown(cat))
        return 0
    nomes = args.nomes or sorted(cat["cenas"])
    for nome in nomes:
        m = meta_de(cat, nome)
        obrig = [k for k, r in (m.get("params") or {}).items() if r.get("obrigatorio")]
        diz(f"{nome:16} {str(m.get('dur_padrao')) + ' s':>6}  {'alfa' if m.get('alfa_padrao') else '    '}  "
            f"{m.get('descricao', '')}")
        if args.nomes:
            for chave, r in (m.get("params") or {}).items():
                diz(_linha_param(chave, r))
        elif obrig:
            diz(f"{'':16} {'':6}        obrigatórios: {', '.join(obrig)}")
    if not args.nomes:
        diz(f"\n{len(nomes)} cenas em {cat['pasta']}. Detalhe uma: catalogo.py <nome>")
    return 0


if __name__ == "__main__":
    sys.exit(rodar(main))
