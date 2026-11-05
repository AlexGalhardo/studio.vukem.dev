#!/usr/bin/env python3
"""nomes.py: monta (ou completa) o banco de nomes do projeto a partir do roteiro, da pesquisa e da transcrição.

  python3 nomes.py [--projeto .] [--roteiro roteiro/] [--fatos pesquisa/fatos.json] [--saida roteiro/nomes.json]

Grava `roteiro/nomes.json`:
  {"versao": 1, "pessoas": [{"nome", "papel", "variantes": []}], "organizacoes": [...], "lugares": [...], "outros": [...]}

A separação entre pessoa, organização e lugar é por palavra-chave e por formato: é um CHUTE mecânico. Quem
confere e preenche o `papel` (e junta "Marina" com "Marina Vasconcelos" em `variantes`) é o Claude, lendo o
roteiro. O banco é o que faz o mapa de fala achar o nome que o Whisper escreveu errado.

Rodar de novo não apaga nada: só acrescenta nome que ainda não está lá.
Códigos de saída: 0 ok · 1 falhou · 2 falta insumo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402

P = C.modulo_palavras()

ORG = ("instituto", "fundacao", "ministerio", "secretaria", "tribunal", "banco", "empresa", "associacao",
       "partido", "agencia", "universidade", "faculdade", "hospital", "prefeitura", "camara", "assembleia",
       "companhia", "construtora", "grupo", "holding", "sindicato", "federacao", "confederacao", "conselho",
       "comissao", "cpi", "delegacia", "policia", "exercito", "marinha", "aeronautica", "forum", "cartorio",
       "editora", "jornal", "revista", "radio", "canal", "clube", "cooperativa", "fabrica", "industria",
       "supermercado", "loja", "seguradora", "financeira", "corretora", "escritorio", "igreja", "ong")
LUGAR = ("rua", "avenida", "praca", "bairro", "vila", "porto", "serra", "lago", "rio", "cidade", "estado",
         "municipio", "distrito", "zona", "regiao", "parque", "morro", "ilha", "estrada", "rodovia",
         "aeroporto", "terminal", "condominio", "residencial", "jardim", "alto", "baixo", "campo", "lagoa")


def classificar(nome):
    toks = P.normalizar(nome).split()
    if any(t in ORG for t in toks) or re.fullmatch(r"[A-ZÀ-Ý]{2,6}s?", nome):
        return "organizacoes"
    if toks and toks[0] in LUGAR:
        return "lugares"
    return "pessoas" if len(toks) >= 2 else "outros"


def nomes_de(caminhos):
    saida = []
    for c in caminhos:
        p = Path(c).expanduser()
        if not p.exists():
            continue
        arquivos = (sorted(p.rglob("*.md")) + sorted(p.rglob("*.txt"))) if p.is_dir() else [p]
        for f in arquivos:
            saida += [(n, f.name) for n in P.nomes_do_texto(C.limpar_roteiro(C.ler_texto(f)))]
    return saida


def nomes_dos_fatos(caminho):
    """Nomes citados na ficha de fatos da skill video-pesquisa-ia (campo `termos` e editor das fontes)."""
    p = Path(caminho).expanduser()
    if not p.exists():
        return []
    try:
        ficha = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return []
    saida = []
    for f in ficha.get("fatos", []):
        saida += [(t, "fatos.json") for t in f.get("termos", []) if isinstance(t, str)]
        for s in f.get("fontes", []):
            if s.get("editor"):
                saida.append((s["editor"], "fatos.json"))
    return saida


def main():
    ap = argparse.ArgumentParser(description="Monta o banco de nomes do projeto.")
    ap.add_argument("--projeto", help="pasta do projeto (padrão: a que tiver transcricao/)")
    ap.add_argument("--roteiro", nargs="*", default=None, help="arquivos ou pastas de roteiro")
    ap.add_argument("--fatos", default=None, help="pesquisa/fatos.json (skill video-pesquisa-ia)")
    ap.add_argument("--transcricao", action="store_true",
                    help="usa também os nomes próprios que o Whisper já escreveu em transcricao/texto.txt")
    ap.add_argument("--saida", default=None, help="padrão: <projeto>/roteiro/nomes.json")
    a = ap.parse_args()

    raiz = C.raiz_do_projeto(a.projeto)
    fontes = a.roteiro if a.roteiro is not None else [raiz / "roteiro"]
    achados = nomes_de(fontes)
    achados += nomes_dos_fatos(a.fatos or raiz / "pesquisa" / "fatos.json")
    if a.transcricao and (raiz / "transcricao" / "texto.txt").exists():
        achados += [(n, "texto.txt") for n in P.nomes_do_texto(C.ler_texto(raiz / "transcricao" / "texto.txt"))]
    if not achados:
        print("falta insumo: não achei nome próprio nenhum. Passe --roteiro com o arquivo do roteiro.",
              file=sys.stderr)
        return 2

    saida = Path(a.saida) if a.saida else raiz / "roteiro" / "nomes.json"
    banco = C.carregar_banco(saida) if saida.exists() else {}
    banco = {g: banco.get(g, []) for g in ("pessoas", "organizacoes", "lugares", "outros")}
    ja = {P.normalizar(i["nome"]) for g in banco.values() for i in g}
    ja |= {P.normalizar(v) for g in banco.values() for i in g for v in i["variantes"]}

    novos = 0
    for nome, fonte in achados:
        n = P.normalizar(nome)
        if not n or n in ja:
            continue
        ja.add(n)
        banco[classificar(nome)].append({"nome": nome, "papel": "", "variantes": [], "visto_em": fonte})
        novos += 1

    doc = {"versao": 1}
    doc.update(banco)
    P.gravar_json(saida, doc)
    print(f"{saida}: {novos} nome(s) novo(s) · "
          + " · ".join(f"{g} {len(banco[g])}" for g in ("pessoas", "organizacoes", "lugares", "outros")))
    print("Confira a separação e preencha `papel` e `variantes` (apelido, primeiro nome) antes de rodar o mapa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
