#!/usr/bin/env python3
"""posicionar.py: põe os eventos de som na linha do tempo e grava som/efeitos.wav calibrado pela voz.

Entrada: a lista de eventos no formato comum das skills de vídeo:

    [{"t": 3.2, "som": "whoosh", "db": -18}]

`t` em segundos, `som` é um nome da biblioteca (ou um apelido: whoosh, zoom, boom, click, papel…) e `db`,
opcional, é o PICO ABSOLUTO desejado em dBFS dentro da mix final a −14 LUFS. Sem `db`, vale o pico que a
biblioteca já traz para aquele efeito. Campos opcionais: "ganho_db" (nuance de ±3 dB sobre o alvo),
"inverter" (troca o lado) e "nota" (comentário que volta no relatório).

Três coisas acontecem aqui, nesta ordem:

1. PERFIL. `discreto` é o padrão e é a regra da casa para vídeo longo: poucos efeitos, baixos, agudo macio
   (−5 dB em tudo, teto de −26 dBFS de pico, respiro de 0,35 s e no máximo 8 efeitos por minuto).
   `normal` e `marcante` afrouxam, nessa ordem.
2. RESPIRO. Efeito a menos de `--respiro` segundos de outro ou cai fora, ou desce 3 dB: desce quando é mais
   importante que o vizinho (classe alta > média > baixa), cai fora quando não é. Depois disso, a densidade
   por minuto é cortada pela classe. Tudo volta explicado em som/efeitos.json.
3. NÍVEL. A biblioteca é calibrada para uma fala com RMS mediano de −16,4 dBFS. Com `--voz`, o script mede o
   RMS real da sua fala e desloca a biblioteca inteira pela diferença, de modo que, depois da mixagem, cada
   efeito fique exatamente no pico que você pediu, contra a SUA voz.

Uso:
  python3 posicionar.py som/eventos.json --voz som/voz.wav --saida som/efeitos.wav
  python3 posicionar.py som/eventos.json --dur 180 --perfil normal --saida som/efeitos.wav
  python3 posicionar.py --exemplo som/eventos.json        grava um arquivo de eventos de exemplo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sfx_lib  # noqa: E402
from audio import FALA_REF, SR, db, faltou, gravar, ler, rms_fala  # noqa: E402

PRIORIDADE = {"alta": 3, "media": 2, "baixa": 1}

# ganho_db · teto de pico dBFS · respiro em s · efeitos por minuto · classes aceitas
PERFIS = {
    "discreto": {"ganho_db": -5.0, "teto_dbfs": -26.0, "respiro_s": 0.35, "por_minuto": 8,
                 "descricao": "vídeo longo: o efeito é detalhe — poucos, baixos, agudo macio"},
    "normal":   {"ganho_db": 0.0, "teto_dbfs": -20.0, "respiro_s": 0.20, "por_minuto": 20,
                 "descricao": "peça média: os efeitos aparecem sem roubar a fala"},
    "marcante": {"ganho_db": 3.0, "teto_dbfs": -14.0, "respiro_s": 0.15, "por_minuto": 40,
                 "descricao": "abertura, intro, corte vertical: efeito em primeiro plano"},
}
GUARDA_DBFS = -3.0          # teto do barramento somado; acima disso tudo desce junto, com aviso

EXEMPLO = [
    {"t": 0.8, "som": "whoosh", "db": -28, "nota": "cartão de abertura entra"},
    {"t": 2.4, "som": "impacto", "nota": "palavra-chave bate na tela"},
    {"t": 5.1, "som": "papel", "db": -30, "nota": "documento virando"},
    {"t": 7.6, "som": "tick", "nota": "número acende"},
    {"t": 9.0, "som": "whoosh_longo", "nota": "troca de assunto"},
]


# ────────────────────────────────────────────────────── biblioteca ──
def biblioteca(pasta_sfx, nomes, tom="D"):
    """Garante que os WAV de `nomes` existem em `pasta_sfx` e devolve {nome: (sinal, pico_dbfs, classe)}."""
    pasta_sfx = Path(pasta_sfx)
    faltam = [n for n in nomes if not (pasta_sfx / f"{n}.wav").is_file()]
    if faltam:
        print(f"gerando {len(faltam)} efeito(s) da biblioteca em {pasta_sfx}…")
        sfx_lib.gerar(pasta_sfx, faltam, tom, amostra=False)
    out = {}
    for n in nomes:
        x = ler(pasta_sfx / f"{n}.wav")
        classe = sfx_lib.BIBLIOTECA[n][2] if n in sfx_lib.BIBLIOTECA else "media"
        out[n] = (x, db(np.max(np.abs(x))), classe)
    return out


def resolver(nome):
    """Nome da biblioteca a partir do nome ou apelido pedido."""
    n = str(nome).strip().lower().replace(" ", "_")
    n = sfx_lib.APELIDOS.get(n, n)
    if n not in sfx_lib.BIBLIOTECA:
        raise SystemExit(f"som desconhecido: {nome!r}.\nDisponíveis: {', '.join(sorted(sfx_lib.BIBLIOTECA))}\n"
                         f"Apelidos: {', '.join(sorted(sfx_lib.APELIDOS))}")
    return n


# ─────────────────────────────────────────────────────────── respiro ──
def respirar(eventos, respiro_s, por_minuto):
    """Aplica o respiro e o teto de densidade. Devolve (ficam, saem); `ficam` ganha "desceu_db"."""
    evs = sorted(eventos, key=lambda e: float(e["t"]))
    ficam, saem, anterior = [], [], None
    for ev in evs:
        ev = dict(ev, desceu_db=0.0)
        if anterior is not None:
            gap = float(ev["t"]) - float(anterior["t"])
            if gap < respiro_s:
                p_novo = PRIORIDADE.get(ev["_classe"], 2)
                p_ant = PRIORIDADE.get(anterior["_classe"], 2)
                if p_novo > p_ant:
                    ev["desceu_db"] = -3.0
                    ev["motivo"] = f"respiro: {gap:.2f} s depois de {anterior['_som']}, desceu 3 dB"
                else:
                    saem.append({**ev, "motivo": f"respiro: {gap:.2f} s depois de {anterior['_som']}"})
                    continue
        ficam.append(ev)
        anterior = ev
    if por_minuto:
        por_min = {}
        for ev in ficam:
            por_min.setdefault(int(float(ev["t"]) // 60), []).append(ev)
        corta = set()
        for minuto, lista in por_min.items():
            if len(lista) > por_minuto:
                # ficam os mais importantes do minuto; empate pela ordem na linha do tempo
                ordem = sorted(lista, key=lambda e: (-PRIORIDADE.get(e["_classe"], 2), float(e["t"])))
                for ev in ordem[por_minuto:]:
                    corta.add(id(ev))
                    saem.append({**ev, "motivo": f"densidade: mais de {por_minuto} efeitos no minuto {minuto}"})
        ficam = [e for e in ficam if id(e) not in corta]
    return ficam, sorted(saem, key=lambda e: float(e["t"]))


# ───────────────────────────────────────────────────────── montagem ──
def posicionar(eventos, saida, voz=None, dur=None, perfil="discreto", pasta_sfx=None, tom="D",
               respiro_s=None, por_minuto=None):
    """Monta o barramento de efeitos e grava `saida`. Devolve o relatório."""
    if perfil not in PERFIS:
        raise SystemExit(f"perfil desconhecido: {perfil!r}. Use {', '.join(PERFIS)}.")
    p = PERFIS[perfil]
    respiro_s = p["respiro_s"] if respiro_s is None else float(respiro_s)
    por_minuto = p["por_minuto"] if por_minuto is None else (int(por_minuto) or None)
    saida = Path(saida)
    pasta_sfx = Path(pasta_sfx) if pasta_sfx else saida.parent / "sfx"

    # duração e calibração pela voz
    deslocamento, fala = 0.0, None
    if voz is not None:
        x = ler(voz)
        fala = rms_fala(x)
        deslocamento = fala - FALA_REF
        n_total = len(x)
        del x
    elif dur:
        n_total = int(float(dur) * SR)
    else:
        n_total = int((max(float(e["t"]) for e in eventos) + 3.0) * SR) if eventos else SR

    # resolve nomes e classes antes do respiro
    evs = []
    for ev in eventos:
        nome = resolver(ev.get("som") or ev.get("sfx") or "")
        evs.append({**ev, "_som": nome, "_classe": sfx_lib.BIBLIOTECA[nome][2]})
    ficam, saem = respirar(evs, respiro_s, por_minuto)

    amostras = biblioteca(pasta_sfx, sorted({e["_som"] for e in ficam}), tom)
    bus = np.zeros((n_total, 2), dtype=np.float32)
    colocados, lado = [], {}
    for ev in ficam:
        nome = ev["_som"]
        som, pico_lib, _classe = amostras[nome]
        alvo = float(ev["db"]) if ev.get("db") is not None else pico_lib
        alvo = min(alvo + p["ganho_db"] + float(ev.get("ganho_db", 0.0)), p["teto_dbfs"]) + ev["desceu_db"]
        i = int(round(float(ev["t"]) * SR))
        if i < 0 or i >= n_total:
            saem.append({**{k: v for k, v in ev.items() if not k.startswith("_")},
                         "motivo": "fora da duração do material"})
            continue
        g = 10 ** ((alvo - pico_lib + deslocamento) / 20)
        trecho = (som[:n_total - i] * g).astype(np.float32)
        if nome in sfx_lib.ABRE:                       # entradas alternam o lado, só por nível (mono-safe)
            k = lado.get(nome, 0)
            lado[nome] = k + 1
            if (k % 2) ^ bool(ev.get("inverter")):
                trecho = trecho[:, ::-1]
        elif ev.get("inverter"):
            trecho = trecho[:, ::-1]
        if len(trecho) < len(som):                     # cortado no fim: fade de 15 ms contra clique
            f = min(len(trecho), int(0.015 * SR))
            trecho = trecho.copy()
            trecho[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
        bus[i:i + len(trecho)] += trecho
        colocados.append({"t": round(float(ev["t"]), 3), "som": nome, "classe": ev["_classe"],
                          "pico_alvo_dbfs": round(alvo + deslocamento, 1),
                          "pico_medido_dbfs": round(db(np.max(np.abs(trecho))), 1),
                          "desceu_db": ev["desceu_db"], "nota": ev.get("nota"),
                          **({"motivo": ev["motivo"]} if ev.get("motivo") else {})})

    guarda = 0.0
    pico_bus = float(np.max(np.abs(bus))) if len(bus) else 0.0
    if db(pico_bus) > GUARDA_DBFS:
        guarda = GUARDA_DBFS - db(pico_bus)
        bus *= 10 ** (guarda / 20)
        print(f"AVISO: efeitos empilhados demais; o barramento inteiro desceu {guarda:.1f} dB "
              "(a calibração por evento se perdeu). Tire eventos ou use o perfil discreto.", file=sys.stderr)
    gravar(saida, bus)

    rel = {
        "saida": str(saida), "duracao_s": round(n_total / SR, 3), "perfil": perfil,
        "perfil_descricao": p["descricao"], "perfil_parametros": {**p, "respiro_s": respiro_s,
                                                                  "por_minuto": por_minuto},
        "voz": str(voz) if voz else None,
        "fala_rms_dbfs": round(fala, 2) if fala is not None else None,
        "deslocamento_db": round(deslocamento, 2),
        "referencia_fala_dbfs": FALA_REF,
        "pico_barramento_dbfs": round(db(pico_bus), 1), "guarda_db": round(guarda, 1),
        "pedidos": len(eventos), "colocados": colocados,
        "fora": [{k: v for k, v in e.items() if not k.startswith("_")} for e in saem],
        "por_minuto_medio": round(len(colocados) / max(n_total / SR / 60, 1e-6), 1),
    }
    rel_arq = saida.with_suffix(".json")
    texto = json.dumps(rel, ensure_ascii=False, indent=1) + "\n"
    rel_arq.write_text(texto, encoding="utf-8", newline="\n")
    print(f"{saida}: {len(colocados)} de {len(eventos)} efeito(s) em {n_total / SR:.1f} s "
          f"({rel['por_minuto_medio']}/min, perfil {perfil}); pico do barramento "
          f"{rel['pico_barramento_dbfs']} dBFS. Relatório: {rel_arq}")
    for e in rel["fora"]:
        print(f"   fora  t={e['t']:>7.2f}  {e.get('som', e.get('sfx'))}: {e['motivo']}")
    return rel


def main():
    ap = argparse.ArgumentParser(description="Posiciona os eventos de som e grava som/efeitos.wav.")
    ap.add_argument("eventos", nargs="?", help="JSON com [{'t':…, 'som':…, 'db':…}]")
    ap.add_argument("--voz", help="WAV/mídia da fala: define a duração e calibra o nível (recomendado)")
    ap.add_argument("--dur", type=float, help="duração em segundos, quando não houver voz")
    ap.add_argument("--saida", default="som/efeitos.wav")
    ap.add_argument("--perfil", default="discreto", choices=sorted(PERFIS),
                    help="discreto (padrão, vídeo longo), normal ou marcante")
    ap.add_argument("--sfx", help="pasta da biblioteca (padrão: <saída>/../sfx)")
    ap.add_argument("--tom", default="D", help="tom da trilha para afinar os efeitos tonais")
    ap.add_argument("--respiro", type=float, help="segundos mínimos entre dois efeitos (sobrepõe o perfil)")
    ap.add_argument("--por-minuto", type=int, help="teto de efeitos por minuto (0 = sem teto)")
    ap.add_argument("--exemplo", metavar="ARQUIVO", help="grava um arquivo de eventos de exemplo e sai")
    a = ap.parse_args()
    if a.exemplo:
        f = Path(a.exemplo)
        f.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(EXEMPLO, ensure_ascii=False, indent=1) + "\n"
        f.write_text(texto, encoding="utf-8", newline="\n")
        print(f"exemplo gravado em {f}")
        return
    if not a.eventos:
        ap.error("falta o arquivo de eventos (ou use --exemplo)")
    arq = Path(a.eventos)
    if not arq.is_file():
        faltou(f"não achei {arq}. Gere um modelo com --exemplo {arq}.")
    dados = json.loads(arq.read_text(encoding="utf-8"))
    eventos = dados["eventos"] if isinstance(dados, dict) else dados
    posicionar(eventos, a.saida, voz=a.voz, dur=a.dur, perfil=a.perfil, pasta_sfx=a.sfx, tom=a.tom,
               respiro_s=a.respiro, por_minuto=a.por_minuto)


if __name__ == "__main__":
    main()
