#!/usr/bin/env python3
"""ancoras.py — resolve âncora de texto da fala em tempo, contra transcricao/palavras.json.

A âncora é um trecho do que a pessoa fala ("quando ele diz isso"). Casa primeiro por texto exato
(sem acento, sem caixa, sem pontuação) e, se não achar, pela melhor janela de palavras parecida.

Uso direto (confere uma âncora sem renderizar nada):
    python3 ancoras.py transcricao/palavras.json "até o último centavo"
"""
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

MIN_PARECIDO = 0.72          # abaixo disto a âncora é considerada não encontrada


def normalizar(texto):
    """Minúsculas, sem acento e sem pontuação, com o índice de cada caractere no texto original."""
    saida, indices = [], []
    for i, c in enumerate(str(texto)):
        base = unicodedata.normalize("NFD", c)
        base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn").lower()
        for ch in base:
            if ch.isalnum() or ch.isspace():
                saida.append(ch)
                indices.append(i)
    return "".join(saida), indices


def so_palavras(texto):
    """Texto normalizado com os espaços colapsados — a forma usada na comparação."""
    base, _ = normalizar(texto)
    return re.sub(r"\s+", " ", base).strip()


def carregar_palavras(caminho):
    """Lê transcricao/palavras.json no formato da casa (aceita `a`/`b` do formato antigo)."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        dados = dados.get("palavras", dados.get("words", []))
    palavras = []
    for item in dados:
        w = str(item.get("w", item.get("word", ""))).strip()
        if not w:
            continue
        t0 = item.get("t0", item.get("a"))
        t1 = item.get("t1", item.get("b"))
        if t0 is None or t1 is None:
            continue
        palavras.append({"w": w, "t0": float(t0), "t1": float(t1), "p": float(item.get("p", 1.0)),
                         "n": so_palavras(w)})
    return palavras


def _texto_corrido(palavras):
    """Concatena as palavras normalizadas e devolve, para cada caractere, o índice da palavra."""
    pedacos, dono = [], []
    for i, p in enumerate(palavras):
        if not p["n"]:
            continue
        if pedacos:
            pedacos.append(" ")
            dono.append(i)
        pedacos.append(p["n"])
        dono.extend([i] * len(p["n"]))
    return "".join(pedacos), dono


def resolver(ancora, palavras, desde=0.0):
    """Devolve {t0, t1, i0, i1, casou, parecido} da melhor posição da âncora a partir de `desde` segundos.

    `casou` é o texto das palavras que casaram; `parecido` vai de 0 a 1 (1 = texto idêntico).
    Devolve None quando nada chega a MIN_PARECIDO.
    """
    alvo = so_palavras(ancora)
    if not alvo or not palavras:
        return None
    inicio = next((i for i, p in enumerate(palavras) if p["t1"] >= desde - 1e-9), len(palavras))
    janela = palavras[inicio:] or palavras
    deslocado = inicio if janela is not palavras else 0

    corrido, dono = _texto_corrido(janela)
    pos = corrido.find(alvo)
    if pos >= 0:
        i0, i1 = dono[pos], dono[pos + len(alvo) - 1]
        return _resposta(palavras, deslocado + i0, deslocado + i1, 1.0)

    # não achou igual: procura a janela de palavras mais parecida (fala tem tropeço, Whisper erra nome)
    n_alvo = max(1, len(alvo.split()))
    melhor = (0.0, None, None)
    for i in range(len(janela)):
        for extra in (-1, 0, 1, 2):
            j = i + n_alvo + extra
            if j <= i or j > len(janela):
                continue
            trecho = " ".join(p["n"] for p in janela[i:j] if p["n"])
            if not trecho:
                continue
            r = SequenceMatcher(None, alvo, trecho).ratio()
            if r > melhor[0]:
                melhor = (r, i, j - 1)
    if melhor[0] < MIN_PARECIDO:
        return None
    return _resposta(palavras, deslocado + melhor[1], deslocado + melhor[2], melhor[0])


def _resposta(palavras, i0, i1, parecido):
    i0 = max(0, min(i0, len(palavras) - 1))
    i1 = max(i0, min(i1, len(palavras) - 1))
    return {
        "t0": round(palavras[i0]["t0"], 3), "t1": round(palavras[i1]["t1"], 3),
        "i0": i0, "i1": i1, "parecido": round(parecido, 3),
        "casou": " ".join(p["w"] for p in palavras[i0:i1 + 1]),
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 64
    palavras = carregar_palavras(sys.argv[1])
    for ancora in sys.argv[2:]:
        r = resolver(ancora, palavras)
        if not r:
            print(f"não achei: {ancora!r}")
            continue
        print(f"{r['t0']:8.3f} → {r['t1']:8.3f}  parecido {r['parecido']:.2f}  {r['casou']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
