#!/usr/bin/env python3
"""buscar.py: acha um termo ou uma frase dentro da transcrição e diz o minuto.

  python3 buscar.py transcricao/palavras.json "termo"
  python3 buscar.py transcricao/palavras.json "a frase inteira que eu quero achar" --contexto 12
  python3 buscar.py transcricao/ "nome próprio" --parecido     # também a grafia que o Whisper errou
  python3 buscar.py . "skill|agente" --regex --json

A busca ignora acento, caixa e pontuação. Sem `--parecido`, casa palavra por palavra (frase inteira raramente
casa: o reconhecimento erra uma palavra no meio — por isso o padrão aceita 80% das palavras da frase em ordem).
Códigos de saída: 0 achou · 1 não achou · 2 falta insumo.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palavras as P  # noqa: E402


def achar(pal, termo, parecido=False, regex=False, minimo=0.8):
    """[(i0, i1, score)] das ocorrências, sem sobreposição, em ordem de tempo."""
    toks = [P.normalizar(p["w"]) for p in pal]
    if regex:
        rx = re.compile(termo, re.I)
        return [(i, i, 1.0) for i, t in enumerate(toks) if t and rx.search(t)]
    alvo = P.normalizar(termo).split()
    if not alvo:
        return []
    if parecido:
        return sorted([(i0, i1, s) for s, i0, i1 in
                       P.ocorrencias_aproximadas(termo, pal, limiar=max(0.7, minimo), tokens=toks)],
                      key=lambda x: x[0])
    if len(alvo) == 1:
        return [(i, i, 1.0) for i, t in enumerate(toks) if t == alvo[0]]
    saida, n = [], len(alvo)
    for i in range(len(toks) - n + 1):
        if toks[i] != alvo[0]:
            continue
        for largura in range(n, n + 4):
            jan = toks[i:i + largura]
            if len(jan) < n:
                break
            j, bate = 0, 0
            for t in jan:
                if j < n and t == alvo[j]:
                    bate += 1
                    j += 1
                elif j + 1 < n and t == alvo[j + 1]:
                    bate += 1
                    j += 2
            if bate / n >= minimo:
                saida.append((i, i + largura - 1, round(bate / n, 2)))
                break
    livres, usados = [], set()
    for i0, i1, s in saida:
        if not usados & set(range(i0, i1 + 1)):
            livres.append((i0, i1, s))
            usados |= set(range(i0, i1 + 1))
    return sorted(livres)


def trecho(pal, i0, i1, contexto):
    a = max(0, i0 - contexto)
    b = min(len(pal), i1 + contexto + 1)
    antes = " ".join(p["w"] for p in pal[a:i0])
    meio = " ".join(p["w"] for p in pal[i0:i1 + 1])
    depois = " ".join(p["w"] for p in pal[i1 + 1:b])
    return antes, meio, depois


def main():
    ap = argparse.ArgumentParser(description="Acha um termo na transcrição e diz o minuto.")
    ap.add_argument("palavras", nargs="?", default=None, help="palavras.json, a pasta transcricao/ ou .")
    ap.add_argument("termo", help="palavra, frase, ou expressão regular com --regex")
    ap.add_argument("--contexto", type=int, default=8, help="palavras de contexto de cada lado (padrão: 8)")
    ap.add_argument("--parecido", action="store_true",
                    help="casa também pela pronúncia (nome que o Whisper escreveu errado)")
    ap.add_argument("--regex", action="store_true", help="o termo é uma expressão regular")
    ap.add_argument("--minimo", type=float, default=0.8, help="fração das palavras da frase que precisa bater")
    ap.add_argument("--json", action="store_true", help="imprime JSON em vez de texto")
    a = ap.parse_args()

    caminho = P.achar_palavras(a.palavras)
    if not Path(caminho).exists():
        print(f"falta insumo: não achei {caminho} — rode o transcrever.py antes", file=sys.stderr)
        return 2
    pal = P.carregar(caminho)
    try:
        achados = achar(pal, a.termo, a.parecido, a.regex, a.minimo)
    except re.error as e:
        print(f"expressão regular inválida: {e}", file=sys.stderr)
        return 2

    saida = []
    for i0, i1, s in achados:
        antes, meio, depois = trecho(pal, i0, i1, a.contexto)
        saida.append({"t0": round(pal[i0]["t0"], 2), "t1": round(pal[i1]["t1"], 2),
                      "mmss": P.mmss(pal[i0]["t0"]), "casou": meio, "semelhanca": s,
                      "antes": antes, "depois": depois})
    if a.json:
        print(json.dumps({"termo": a.termo, "arquivo": str(caminho), "ocorrencias": saida},
                         ensure_ascii=False, indent=1))
    elif not saida:
        print(f"«{a.termo}» não aparece em {caminho}"
              + ("" if a.parecido or a.regex else " — tente --parecido (pronúncia) ou --regex"))
    else:
        print(f"{len(saida)} ocorrência(s) de «{a.termo}» em {caminho}")
        for o in saida:
            marca = f" ({o['semelhanca']:.0%})" if o["semelhanca"] < 1 else ""
            print(f"\n{o['mmss']}  …{o['antes']} [{o['casou']}]{marca} {o['depois']}…")
    return 0 if saida else 1


if __name__ == "__main__":
    sys.exit(main())
