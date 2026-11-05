#!/usr/bin/env python3
"""ancorar.py: transforma âncoras escritas em palavras da fala na lista de eventos de som.

Você escreve as âncoras pelo TEXTO que o apresentador fala, não por segundo — o tempo sai do
transcricao/palavras.json. Assim a sonorização sobrevive a um recorte novo da montagem: basta rodar de novo.

Arquivo de âncoras (JSON):

    [{"texto": "primeira etapa", "som": "impacto", "db": -26},
     {"texto": "e agora sim",    "som": "riser",   "alinhar": "termina"},
     {"texto": "oito",           "som": "tick", "onde": "fim", "atraso": 0.05, "ocorrencia": 2}]

  texto       trecho falado (sem acento e sem pontuação já basta: a busca ignora os dois)
  som         nome ou apelido da biblioteca
  db          pico absoluto desejado em dBFS (opcional)
  onde        "inicio" (padrão: começo da primeira palavra) ou "fim" (fim da última)
  alinhar     "comeca" (padrão) ou "termina": o efeito TERMINA na âncora (riser antes do corte)
  atraso      segundos somados ao tempo encontrado (pode ser negativo)
  ocorrencia  qual repetição do texto usar (1 = a primeira; -1 = a última)

Uso:
  python3 ancorar.py som/ancoras.json --palavras transcricao/palavras.json --saida som/eventos.json
  python3 ancorar.py --exemplo som/ancoras.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sfx_lib  # noqa: E402
from audio import faltou  # noqa: E402

EXEMPLO = [
    {"texto": "primeira parte", "som": "impacto", "db": -26, "nota": "cartela de capítulo"},
    {"texto": "e agora", "som": "riser", "alinhar": "termina", "nota": "sobe até o corte"},
    {"texto": "três exemplos", "som": "tick", "onde": "fim"},
    {"texto": "o documento", "som": "papel", "db": -30},
]


def normalizar(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def carregar_palavras(arquivo):
    """Lê transcricao/palavras.json no formato comum (aceita t0/t1 e o antigo a/b)."""
    dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        dados = dados.get("palavras") or dados.get("words") or []
    saida = []
    for p in dados:
        t0 = p.get("t0", p.get("a"))
        t1 = p.get("t1", p.get("b", t0))
        w = p.get("w", p.get("palavra", p.get("word", "")))
        if t0 is None:
            continue
        chaves = normalizar(w)
        saida.append({"w": w, "k": chaves[0] if chaves else "", "t0": float(t0), "t1": float(t1)})
    return saida


def achar(palavras, texto, ocorrencia=1):
    """Todas as posições de `texto` na sequência de palavras; devolve (t0, t1) da ocorrência pedida."""
    alvo = normalizar(texto)
    if not alvo:
        return None
    chaves = [p["k"] for p in palavras]
    achados = [i for i in range(len(chaves) - len(alvo) + 1) if chaves[i:i + len(alvo)] == alvo]
    if not achados:
        return None
    k = ocorrencia - 1 if ocorrencia > 0 else len(achados) + ocorrencia
    if not 0 <= k < len(achados):
        return None
    i = achados[k]
    return palavras[i]["t0"], palavras[i + len(alvo) - 1]["t1"], len(achados)


def ancorar(ancoras, palavras_json, saida=None):
    palavras = carregar_palavras(palavras_json)
    eventos, perdidas = [], []
    for a in ancoras:
        nome = str(a.get("som") or "").strip().lower().replace(" ", "_")
        nome = sfx_lib.APELIDOS.get(nome, nome)
        if nome not in sfx_lib.BIBLIOTECA:
            perdidas.append({**a, "motivo": f"som desconhecido: {a.get('som')!r}"})
            continue
        r = achar(palavras, a.get("texto", ""), int(a.get("ocorrencia", 1)))
        if r is None:
            perdidas.append({**a, "motivo": "texto não encontrado na transcrição"})
            continue
        t0, t1, quantas = r
        t = t1 if a.get("onde") == "fim" else t0
        if a.get("alinhar") == "termina":                 # o efeito TERMINA na âncora (riser antes do corte)
            corpo = sfx_lib.CORPO.get(nome)
            if corpo is None:
                dados = sfx_lib.BIBLIOTECA[nome]
                corpo = 0.35 if dados[2] != "alta" else 0.6
            t -= float(corpo)
        t += float(a.get("atraso", 0.0))
        ev = {"t": round(max(t, 0.0), 3), "som": nome}
        for campo in ("db", "ganho_db", "inverter", "nota"):
            if a.get(campo) is not None:
                ev[campo] = a[campo]
        ev["ancora"] = a.get("texto")
        if quantas > 1:
            aviso = f"{quantas} ocorrências do texto; usou a nº {a.get('ocorrencia', 1)}"
            ev["nota"] = f"{ev['nota']} ({aviso})" if ev.get("nota") else aviso
        eventos.append(ev)
    eventos.sort(key=lambda e: e["t"])
    if saida:
        f = Path(saida)
        f.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(eventos, ensure_ascii=False, indent=1) + "\n"
        f.write_text(texto, encoding="utf-8", newline="\n")
        print(f"{f}: {len(eventos)} evento(s) de {len(ancoras)} âncora(s).")
    for p in perdidas:
        print(f"   sem âncora: {p.get('texto')!r} — {p['motivo']}", file=sys.stderr)
    return eventos, perdidas


def main():
    ap = argparse.ArgumentParser(description="Âncoras por texto da fala → eventos de som.")
    ap.add_argument("ancoras", nargs="?", help="JSON com as âncoras")
    ap.add_argument("--palavras", default="transcricao/palavras.json")
    ap.add_argument("--saida", default="som/eventos.json")
    ap.add_argument("--exemplo", metavar="ARQUIVO", help="grava um arquivo de âncoras de exemplo e sai")
    a = ap.parse_args()
    if a.exemplo:
        f = Path(a.exemplo)
        f.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(EXEMPLO, ensure_ascii=False, indent=1) + "\n"
        f.write_text(texto, encoding="utf-8", newline="\n")
        print(f"exemplo gravado em {f}")
        return
    if not a.ancoras:
        ap.error("falta o arquivo de âncoras (ou use --exemplo)")
    if not Path(a.palavras).is_file():
        faltou(f"não achei {a.palavras}. Rode antes a skill video-transcricao.")
    _evs, perdidas = ancorar(json.loads(Path(a.ancoras).read_text(encoding="utf-8")), a.palavras, a.saida)
    sys.exit(0 if not perdidas else 1)


if __name__ == "__main__":
    main()
