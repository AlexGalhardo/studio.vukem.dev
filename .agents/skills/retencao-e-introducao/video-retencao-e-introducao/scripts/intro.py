#!/usr/bin/env python3
"""intro.py — a introdução do vídeo, feita POR ÚLTIMO, com as melhores mídias do vídeo inteiro.

    intro.py planejar --midias broll/tratado --fala transcricao/palavras.json --t0 0 --t1 112 --bpm 120
    intro.py planejar --midias lista.txt --dur 15 --min 1.0 --max 2.0 --semente 7
    intro.py montar [--prévia] [--sem-som]
    intro.py checklist [--medir render/intro.mp4]

A intro é uma rajada: tomada curta atrás de tomada curta, troca a cada 1–2 s **no ritmo da fala e da música**,
com chicotes, flashes brancos e zooms entre elas. O plano sai em `animacoes/intro/plano.json`, o vídeo em
`render/intro.mp4`, os eventos de som em `som/eventos_intro.json` e o checklist de retenção em
`qa/retencao-intro.md`.

Detalhe que custou caro: cada clipe entra na cadeia de xfade com **folga no fim** (`tpad=stop_mode=clone`) e a
cadeia inteira é cortada no fim (`trim=duration=<total>`). Sem a folga, um corte de 1 quadro encerra a cadeia
antes da hora e o vídeo sai curto; sem o corte no fim, ele sai com o rabo da última folga."""
from __future__ import annotations

import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import base  # noqa: E402

PLANO = base.PASTA / "plano.json"
TRAB = base.PASTA / "_trab"
EVENTOS = Path("som") / "eventos_intro.json"
CHECKLIST = Path("qa") / "retencao-intro.md"
SAIDA = Path("render") / "intro.mp4"
IMAGENS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
VIDEOS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

# transição → filtro do xfade, duração e som (o mapa que o projeto de referência deixou pronto)
# ARMADILHA CARA: o `zoomin` do xfade só presta SAINDO DE PEÇA GRÁFICA. Saindo de footage (câmera, foto, rajada)
# ele amplia tanto no meio da transição que o quadro vira uma mancha chapada de uma cor só. Por isso `zoom` já
# nasce `circleopen` e, mesmo que alguém escreva `zoom_duro` na mão no plano, `encadear` troca o zoomin por
# circleopen quando o clipe que SAI não é peça gráfica (a mesma guarda do projeto de referência).
XFADE = {"corte": "fade", "chicote": "smoothleft", "chicote_dir": "smoothright", "branco": "fadewhite",
         "zoom": "circleopen", "zoom_duro": "zoomin", "empurra": "slideleft", "fade": "fade"}
DUR_T = {"corte": None, "chicote": 0.22, "chicote_dir": 0.22, "branco": 0.3, "zoom": 0.36, "zoom_duro": 0.36,
         "empurra": 0.32, "fade": 0.3}
SOM_T = {"chicote": ("whoosh", -18), "chicote_dir": ("whoosh", -18), "branco": ("impacto", -16),
         "zoom": ("zoom_in", -20), "zoom_duro": ("zoom_in", -20), "empurra": ("whoosh", -20)}


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────── as mídias ──
def listar_midias(raiz: Path, alvo: str | None) -> list[Path]:
    """As melhores mídias do vídeo: uma pasta, um arquivo de lista (um caminho por linha) ou o padrão
    (broll/tratado, depois broll/bruto)."""
    candidatos: list[Path] = []
    if alvo:
        p = Path(alvo).expanduser()
        p = p if p.is_absolute() or p.exists() else raiz / alvo
        if p.is_file() and p.suffix.lower() not in IMAGENS | VIDEOS:
            for linha in p.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha and not linha.startswith("#"):
                    q = Path(linha).expanduser()
                    candidatos.append(q if q.is_absolute() else raiz / q)
        elif p.is_dir():
            candidatos = sorted(x for x in p.rglob("*") if x.suffix.lower() in IMAGENS | VIDEOS)
        elif p.is_file():
            candidatos = [p]
        else:
            raise base.Erro(f"não achei as mídias em {alvo!r}.", "Passe uma pasta, um arquivo de lista ou um arquivo de mídia.", base.USO)
    else:
        for sub in ("broll/tratado", "broll/bruto", "bruto"):
            candidatos += sorted(x for x in (raiz / sub).rglob("*") if x.suffix.lower() in IMAGENS | VIDEOS) if (raiz / sub).is_dir() else []
    vistos, saida = set(), []
    for c in candidatos:
        chave = str(c.resolve())
        if chave not in vistos and c.is_file():
            vistos.add(chave)
            saida.append(c)
    if not saida:
        raise base.Erro("não achei nenhuma mídia para a intro.",
                        "Aponte a pasta com --midias (a intro é feita por último, com o melhor do vídeo pronto).", base.USO)
    return saida


# ────────────────────────────────────────────────────── as âncoras do ritmo ──
def ancoras_da_fala(arq: Path, t0: float, t1: float) -> list[dict]:
    """Começo de cada palavra entre t0 e t1 (tempo relativo a t0), com o tamanho da pausa antes dela.
    Pausa grande = lugar natural de flash; palavra = lugar natural de corte."""
    dados = base.ler_json(arq, [])
    if isinstance(dados, dict):
        dados = dados.get("palavras") or dados.get("itens") or []
    saida, fim_anterior = [], None
    for p in dados:
        a, b = p.get("t0", p.get("a")), p.get("t1", p.get("b"))
        if a is None:
            continue
        a, b = float(a), float(b if b is not None else a)
        if a < t0 or a > t1:
            fim_anterior = b
            continue
        saida.append({"t": round(a - t0, 3), "pausa": round(a - fim_anterior, 3) if fim_anterior is not None else 0.0,
                      "w": str(p.get("w", ""))})
        fim_anterior = b
    return saida


def ancoras_da_musica(bpm: float, dur: float, compasso: int = 4) -> list[dict]:
    """Batidas da música até `dur`, marcando a primeira de cada compasso (é onde a troca pesa mais)."""
    if not bpm or bpm <= 0:
        return []
    passo = 60.0 / bpm
    n = int(dur / passo) + 1
    return [{"t": round(i * passo, 3), "forte": i % compasso == 0} for i in range(n)]


def _mais_perto(alvo: float, ancoras: list[dict], tolerancia: float):
    melhor, dist = None, tolerancia
    for a in ancoras:
        d = abs(a["t"] - alvo)
        if d <= dist:
            melhor, dist = a, d
    return melhor


# ─────────────────────────────────────────────────────────────── o plano ──
def e_grafico(raiz: Path, arq: Path) -> bool:
    """Peça gráfica (cartela, animação, render da DA) × footage (câmera, foto, banco). Só a peça gráfica aguenta
    o `zoomin` do xfade; em footage ele vira mancha chapada."""
    try:
        rel = arq.resolve().relative_to(raiz.resolve()).as_posix()
    except (ValueError, OSError):
        return False
    return rel.split("/")[0] in ("animacoes", "da", "render", "legendas")


def planejar(raiz: Path, midias: list[Path], dur: float, fala: list[dict], musica: list[dict],
             minimo: float = 1.0, maximo: float = 2.0, semente: int = 1, formato=(1920, 1080), fps: float = 30.0) -> dict:
    """Corta a intro em tomadas de `minimo`–`maximo` segundos, encostando cada corte na âncora mais próxima
    (palavra ou batida), e escolhe a transição de cada troca."""
    rnd = random.Random(semente)
    ritmo = random.Random(semente * 977 + 13)
    tolerancia = (maximo - minimo) / 2.0
    pausas = [a for a in fala if a["pausa"] >= 0.25]
    fortes = [a for a in musica if a.get("forte")]
    cortes, t = [0.0], 0.0
    while True:
        alvo = t + ritmo.uniform(minimo, maximo)       # o ritmo respira: nem toda tomada tem a mesma duração
        if dur - alvo < minimo * 0.6:                  # a última tomada fica com o que sobrou
            break
        # a fala manda primeiro (pausa = lugar natural de troca), depois a batida forte, depois qualquer batida
        ancora = (_mais_perto(alvo, pausas, tolerancia * 0.9) or _mais_perto(alvo, fortes, tolerancia)
                  or _mais_perto(alvo, musica, tolerancia * 0.6) or _mais_perto(alvo, fala, tolerancia * 0.7))
        novo = round(ancora["t"], 3) if ancora else round(alvo, 3)
        if novo - t < minimo * 0.75:                   # âncora perto demais da anterior: segue o ideal
            novo = round(alvo, 3)
        cortes.append(min(novo, dur))
        t = cortes[-1]
    cortes.append(round(dur, 3))
    cortes = sorted(dict.fromkeys(round(c, 3) for c in cortes))

    fichas = {}
    tomadas = []
    for i in range(len(cortes) - 1):
        t0, t1 = cortes[i], cortes[i + 1]
        n = round(t1 - t0, 3)
        if n <= 0.04:
            continue
        arq = midias[len(tomadas) % len(midias)]
        if str(arq) not in fichas:
            fichas[str(arq)] = base.ffprobe(arq)
        f = fichas[str(arq)]
        # transição de ENTRADA desta tomada (a primeira entra em corte seco)
        if not tomadas:
            entra = "corte"
        else:
            pausa = _mais_perto(t0, [a for a in fala if a["pausa"] >= 0.3], 0.18)
            forte = _mais_perto(t0, [a for a in musica if a.get("forte")], 0.08)
            if pausa is not None:
                entra = "branco"
            elif len(tomadas) % 8 == 7:
                entra = "zoom"
            elif forte is not None and len(tomadas) % 2 == 1:
                entra = "chicote" if len(tomadas) % 4 == 1 else "chicote_dir"
            else:
                entra = "corte"
        # de onde sai o trecho da mídia: o miolo, nunca o comecinho (onde mora o pior quadro)
        dentro = 0.0
        if f.get("tem_video") and (f.get("duracao") or 0) > n + 0.4:
            sobra = f["duracao"] - n
            dentro = round(min(sobra, max(0.0, sobra * (0.25 + 0.5 * rnd.random()))), 3)
        z0 = round(1.0 + 0.02 * rnd.random(), 4)
        z1 = round(z0 + (0.06 + 0.05 * rnd.random()) * (1 if len(tomadas) % 2 == 0 else -1), 4)
        tomadas.append({"n": len(tomadas) + 1, "arquivo": str(arq), "t": round(t0, 3), "dur": n, "dentro": dentro,
                        "entra": entra, "imagem": not f.get("tem_video") or arq.suffix.lower() in IMAGENS,
                        "grafico": e_grafico(raiz, arq),
                        "zoom": [{"t": 0.0, "z": z0}, {"t": n, "z": max(1.0, z1)}]})
    for i, u in enumerate(tomadas):                      # a folga de cada clipe é a transição do PRÓXIMO
        prox = tomadas[i + 1] if i + 1 < len(tomadas) else None
        u["folga"] = round(DUR_T.get(prox["entra"]) or (1.0 / fps), 3) if prox else 0.0
    eventos = []
    for u in tomadas:
        som = SOM_T.get(u["entra"])
        if som:
            eventos.append({"t": round(max(0.0, u["t"] - 0.06), 3), "som": som[0], "db": som[1]})
    plano = {"versao": 1, "feito_em": agora(), "formato": list(formato), "fps": round(fps, 4),
             "dur_planejada": round(sum(u["dur"] for u in tomadas), 3), "dur_pedida": round(dur, 3),
             "min_s": minimo, "max_s": maximo, "semente": semente,
             "ritmo": {"palavras": len(fala), "batidas": len(musica), "bpm": None},
             "midias": sorted({u["arquivo"] for u in tomadas}), "tomadas": tomadas, "eventos": eventos}
    return plano


# ──────────────────────────────────────────────────────────────── montagem ──
def expr_zoom(chaves, dur: float) -> str:
    """z(it) por chaves [{t, z}], com suavização (smoothstep) entre elas."""
    ch = sorted(chaves or [{"t": 0, "z": 1.0}, {"t": dur, "z": 1.06}], key=lambda c: c["t"])
    termos = [f"lt(it,{ch[0]['t']:.3f})*{ch[0]['z']:.4f}"]
    for a, b in zip(ch, ch[1:]):
        d = max(0.01, b["t"] - a["t"])
        s = f"(clip((it-{a['t']:.3f})/{d:.3f},0,1))"
        termos.append(f"between(it,{a['t']:.3f},{b['t']:.3f})*({a['z']:.4f}+({b['z'] - a['z']:.4f})*{s}*{s}*(3-2*{s}))")
    termos.append(f"gt(it,{ch[-1]['t']:.3f})*{ch[-1]['z']:.4f}")
    return "max(1,(" + "+".join(termos) + "))"


def montar_clipe(u: dict, L: int, A: int, fps_txt: str, destino: Path, refazer: bool = False) -> Path:
    """Uma tomada: recorta, enquadra no formato da DA, aplica o zoom e dura `dur + folga`."""
    if destino.is_file() and not refazer:
        return destino
    D = round(u["dur"] + u["folga"], 3)
    entrada = ["-loop", "1", "-t", f"{D + 0.2:.3f}", "-i", u["arquivo"]] if u["imagem"] else \
              ["-ss", f"{u['dentro']:.3f}", "-t", f"{D + 0.2:.3f}", "-i", u["arquivo"]]
    enquadra = f"scale={L}:{A}:force_original_aspect_ratio=increase,crop={L}:{A}"
    if u.get("zoom"):
        # o zoompan trabalha numa cópia maior: assim o zoom não perde definição
        fc = (f"[0:v]{enquadra},scale={int(L * 1.5)}:{int(A * 1.5)},setsar=1,"
              f"zoompan=z='{expr_zoom(u['zoom'], u['dur'])}':d=1:s={L}x{A}:fps={fps_txt}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',")
    else:
        fc = f"[0:v]{enquadra},fps={fps_txt},"
    fc += f"setsar=1,tpad=stop_mode=clone:stop_duration=2,trim=duration={D:.3f},setpts=PTS-STARTPTS,format=yuv420p[vo]"
    destino.parent.mkdir(parents=True, exist_ok=True)
    base.ffmpeg(["-nostdin", *entrada, "-filter_complex", fc, "-map", "[vo]", "-r", fps_txt,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", str(destino)])
    return destino


def encadear(tomadas: list[dict], clipes: list[Path], saida: Path, fps: float, fps_txt: str) -> Path:
    """A cadeia de xfade. Aqui mora o detalhe que custou caro: cada clipe ganha folga no fim (tpad) e a cadeia
    inteira é cortada no fim (trim) — sem isso, a cadeia encerra antes da hora ou sobra rabo."""
    if len(clipes) == 1:
        base.ffmpeg(["-i", str(clipes[0]), "-c", "copy", str(saida)])
        return saida
    entradas = []
    for c in clipes:
        entradas += ["-i", str(c)]
    tb = f"1/{int(round(fps * 1000))}"
    fc = [f"[{i}:v]tpad=stop_mode=clone:stop_duration=0.15,settb={tb}[p{i}]" for i in range(len(clipes))]
    cur, acum = "p0", 0.0
    for i in range(1, len(tomadas)):
        acum += tomadas[i - 1]["dur"]
        xf = XFADE.get(tomadas[i]["entra"], "fade")
        if xf == "zoomin" and not tomadas[i - 1].get("grafico"):
            xf = "circleopen"                       # saindo de footage o zoomin chapa o quadro (ver XFADE)
        d = max(tomadas[i - 1]["folga"], 2.0 / fps)
        fc.append(f"[{cur}][p{i}]xfade=transition={xf}:duration={d:.4f}:offset={acum:.4f}[x{i}]")
        cur = f"x{i}"
    total = sum(u["dur"] for u in tomadas)
    fc.append(f"[{cur}]trim=duration={total:.4f},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[vout]")
    saida.parent.mkdir(parents=True, exist_ok=True)
    base.ffmpeg(["-nostdin", *entradas, "-filter_complex", ";".join(fc), "-map", "[vout]", "-r", fps_txt,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", str(saida)])
    return saida


# ──────────────────────────────────────────────────────── checklist de retenção ──
def medir(plano: dict, arquivo: Path | None) -> dict:
    tomadas = plano["tomadas"]
    duracoes = [u["dur"] for u in tomadas]
    conta = {}
    for u in tomadas:
        conta[u["entra"]] = conta.get(u["entra"], 0) + 1
    repetidas = sum(1 for a, b in zip(tomadas, tomadas[1:]) if a["arquivo"] == b["arquivo"])
    m = {"tomadas": len(tomadas), "midias_distintas": len(set(u["arquivo"] for u in tomadas)),
         "dur_planejada": round(sum(duracoes), 3), "media_s": round(sum(duracoes) / max(1, len(duracoes)), 3),
         "menor_s": round(min(duracoes), 3) if duracoes else 0, "maior_s": round(max(duracoes), 3) if duracoes else 0,
         "primeira_troca_s": round(duracoes[0], 3) if duracoes else 0, "transicoes": conta,
         "repetidas_em_sequencia": repetidas, "eventos_de_som": len(plano.get("eventos") or [])}
    if arquivo and Path(arquivo).is_file():
        f = base.ffprobe(arquivo)
        m["dur_medida"] = round(f["duracao"] or 0, 3)
        m["erro_s"] = round((f["duracao"] or 0) - m["dur_planejada"], 3)
        m["quadros"] = f.get("quadros")
        m["formato_medido"] = f"{f.get('largura')}×{f.get('altura')}"
    return m


def checklist(plano: dict, m: dict, creditos_faltando: list[str]) -> str:
    def marca(ok, texto, detalhe=""):
        return f"- [{'x' if ok else ' '}] {texto}{(' — ' + detalhe) if detalhe else ''}"
    linhas = [f"# Checklist de retenção — introdução", "",
              f"{m['tomadas']} tomadas · {m['midias_distintas']} mídia(s) distinta(s) · "
              f"{m['dur_planejada']:.1f} s planejados"
              + (f" · {m['dur_medida']:.1f} s medidos (erro {m['erro_s']:+.2f} s)" if "dur_medida" in m else " · ainda não renderizada"), "",
              "## O ritmo", "",
              marca(m["media_s"] <= 2.2, f"troca a cada 1–2 s", f"média de {m['media_s']:.2f} s por mídia"),
              marca(m["maior_s"] <= 2.6, "nenhuma tomada parada tempo demais", f"a mais longa tem {m['maior_s']:.2f} s"),
              marca(m["primeira_troca_s"] <= 2.0, "a primeira troca acontece logo", f"em {m['primeira_troca_s']:.2f} s"),
              marca(m["repetidas_em_sequencia"] == 0, "nenhuma mídia repetida em sequência",
                    f"{m['repetidas_em_sequencia']} repetição(ões)" if m["repetidas_em_sequencia"] else ""),
              marca(sum(v for k, v in m["transicoes"].items() if k != "corte") >= max(1, m["tomadas"] // 6),
                    "chicotes, flashes e zooms suficientes",
                    ", ".join(f"{k} {v}" for k, v in sorted(m["transicoes"].items()))),
              marca(m["eventos_de_som"] > 0, "cada transição forte tem som", f"{m['eventos_de_som']} evento(s) em som/eventos_intro.json"),
              "", "## O conteúdo (confira com o olho)", "",
              "- [ ] a primeira imagem é a mais forte do vídeo inteiro",
              "- [ ] a promessa do vídeo aparece nos primeiros 5 s (dita ou escrita)",
              "- [ ] nenhuma tomada entrega o desfecho antes da hora",
              "- [ ] nenhuma imagem exige leitura (texto pequeno some em 1 s)",
              "- [ ] a intro é a última coisa montada: ela usa o melhor do vídeo pronto",
              "", "## Direitos", ""]
    if creditos_faltando:
        linhas.append(marca(False, "toda mídia da intro tem licença registrada",
                            f"{len(creditos_faltando)} sem registro: " + ", ".join(Path(x).name for x in creditos_faltando[:6])))
    else:
        linhas.append(marca(True, "toda mídia da intro tem licença registrada em broll/licencas.json"))
    linhas += ["- [ ] os créditos obrigatórios estão na tela ou na descrição", ""]
    if "dur_medida" in m:
        linhas += ["## Medido no arquivo", "",
                   f"- duração: **{m['dur_medida']:.2f} s** (planejado {m['dur_planejada']:.2f} s, erro {m['erro_s']:+.2f} s)",
                   f"- quadros: {m.get('quadros')} · formato: {m.get('formato_medido')}", ""]
    linhas.append(f"_gerado por video-retencao-e-introducao em {agora()}_")
    return "\n".join(linhas) + "\n"


def creditos_faltando(raiz: Path, plano: dict) -> list[str]:
    """Mídias da intro que não estão em broll/licencas.json (nem como arquivo, nem como tratado)."""
    dados = base.ler_json(raiz / "broll" / "licencas.json")
    if not dados:
        return []
    conhecidos = set()
    for it in dados.get("itens") or []:
        for campo in ("arquivo",):
            if it.get(campo):
                conhecidos.add(Path(it[campo]).name)
        for t in it.get("tratados") or []:
            conhecidos.add(Path(t).name)
    return [a for a in plano["midias"] if Path(a).name not in conhecidos]


# ──────────────────────────────────────────────────────────────────── CLI ──
def main(argv=None) -> int:
    ap = base.Parser(prog="intro.py", description="A introdução do vídeo: rajada de 1–2 s no ritmo da fala e da música, "
                     "com chicotes, flashes e zooms, renderizada na direção de arte, com eventos de som e checklist de retenção.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("planejar", help="monta animacoes/intro/plano.json (não renderiza)")
    p.add_argument("--midias", metavar="PASTA|LISTA", help="pasta, arquivo de lista ou mídia (padrão: broll/tratado e broll/bruto)")
    p.add_argument("--fala", metavar="ARQ", help="transcricao/palavras.json da narração da intro")
    p.add_argument("--t0", default="0", help="começo da narração da intro na transcrição (padrão 0)")
    p.add_argument("--t1", help="fim da narração da intro (padrão: a duração pedida)")
    p.add_argument("--dur", type=float, metavar="S", help="duração da intro (padrão: o trecho de fala, ou 60 s)")
    p.add_argument("--bpm", type=float, metavar="N", help="andamento da música (põe as trocas na batida)")
    p.add_argument("--compasso", type=int, default=4, metavar="N", help="batidas por compasso (padrão 4)")
    p.add_argument("--min", type=float, default=1.0, dest="minimo", metavar="S", help="tomada mais curta (padrão 1 s)")
    p.add_argument("--max", type=float, default=2.0, dest="maximo", metavar="S", help="tomada mais longa (padrão 2 s)")
    p.add_argument("--semente", type=int, default=1, help="o mesmo número dá o mesmo plano (padrão 1)")

    p = sub.add_parser("montar", help="renderiza render/intro.mp4 a partir do plano")
    p.add_argument("--refazer", action="store_true", help="refaz os clipes intermediários")
    p.add_argument("--saida", metavar="ARQ", help=f"padrão: {SAIDA.as_posix()}")
    p.add_argument("--previa", action="store_true", help="renderiza em 960×540 para olhar rápido")

    p = sub.add_parser("checklist", help="grava qa/retencao-intro.md")
    p.add_argument("--medir", metavar="ARQ", help="mede o arquivo renderizado e compara com o plano")

    for s in sub.choices.values():
        s.add_argument("--projeto", metavar="PASTA")
        s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    raiz = base.achar_projeto(a.projeto)
    da_mod, _texto = base.kit()
    try:
        d = da_mod.carregar(str(raiz))
    except Exception as e:
        raise base.Erro(str(getattr(e, "mensagem", e)),
                        "A intro é peça do vídeo: ela obedece à direção de arte. Crie a DA com a skill video-direcao-de-arte.",
                        base.SEM_DA)
    L, A = d.dimensoes("horizontal")
    fmt = d["formatos"]["horizontal"]
    fps = float(fmt.get("fps_float") or 30.0)
    fps_txt = str(fmt.get("fps") or "30")

    if a.cmd == "planejar":
        midias = listar_midias(raiz, a.midias)
        t0 = base.segundos(a.t0) or 0.0
        fala = ancoras_da_fala(Path(a.fala).expanduser() if Path(a.fala).expanduser().is_file() else raiz / a.fala,
                               t0, base.segundos(a.t1) if a.t1 else 1e9) if a.fala else []
        dur = a.dur or (round(max(x["t"] for x in fala) + 0.8, 2) if fala else 60.0)
        musica = ancoras_da_musica(a.bpm, dur, a.compasso) if a.bpm else []
        plano = planejar(raiz, midias, dur, fala, musica, a.minimo, a.maximo, a.semente, (L, A), fps)
        plano["ritmo"]["bpm"] = a.bpm
        plano["midias_disponiveis"] = len(midias)
        base.gravar_json(raiz / PLANO, plano)
        base.gravar_json(raiz / EVENTOS, plano["eventos"])
        if a.json:
            print(json.dumps(plano, ensure_ascii=False, indent=1))
            return 0
        m = medir(plano, None)
        base.diz(f"{m['tomadas']} tomadas · {m['dur_planejada']:.2f} s · média {m['media_s']:.2f} s "
                 f"(de {m['menor_s']:.2f} a {m['maior_s']:.2f}) · {len(midias)} mídia(s) disponíveis")
        base.diz("  transições: " + ", ".join(f"{k} {v}" for k, v in sorted(m["transicoes"].items())))
        base.diz(f"  ritmo: {len(fala)} palavra(s)" + (f" · {len(musica)} batida(s) a {a.bpm:g} bpm" if musica else " · sem música"))
        base.diz(f"\n{raiz / PLANO}\n{raiz / EVENTOS}  ({len(plano['eventos'])} evento(s) de som)")
        base.diz("\nAgora: intro.py montar")
        return 0

    plano = base.ler_json(raiz / PLANO)
    if not plano:
        raise base.Erro(f"não achei {PLANO.as_posix()}.", "Rode intro.py planejar primeiro.", base.USO)

    if a.cmd == "montar":
        if a.previa:
            L, A = L // 2, A // 2
        trab = raiz / TRAB
        trab.mkdir(parents=True, exist_ok=True)
        clipes = []
        base.diz(f"Montando {len(plano['tomadas'])} tomada(s) em {L}×{A} a {fps:.3f} qps…")
        for u in plano["tomadas"]:
            destino = trab / f"c{u['n']:03d}.mp4"
            montar_clipe(u, L, A, fps_txt, destino, a.refazer)
            clipes.append(destino)
            if u["n"] % 10 == 0 or u["n"] == len(plano["tomadas"]):
                base.diz(f"  {u['n']}/{len(plano['tomadas'])} clipes")
        saida = Path(a.saida).expanduser() if a.saida else raiz / SAIDA
        if not saida.is_absolute():
            saida = raiz / saida
        encadear(plano["tomadas"], clipes, saida, fps, fps_txt)
        f = base.ffprobe(saida)
        try:
            d.carimbar(str(saida), "render", f"{L}x{A}", {"peca": "intro", "tomadas": len(plano["tomadas"])},
                       insumos=plano["midias"])
        except Exception as e:                       # o carimbo é da DA; falhar nele não perde o render
            base.diz(f"! carimbo não saiu ({e})", erro=True)
        base.gravar_json(raiz / EVENTOS, plano["eventos"])
        if a.json:
            print(json.dumps({"saida": str(saida), **f}, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"\n{saida}")
        base.diz(f"  {f['duracao']:.2f} s medidos · planejado {plano['dur_planejada']:.2f} s "
                 f"(erro {(f['duracao'] or 0) - plano['dur_planejada']:+.2f} s) · {f.get('quadros')} quadros · "
                 f"{f.get('largura')}×{f.get('altura')}")
        base.diz(f"  {len(plano['eventos'])} evento(s) de som em {EVENTOS.as_posix()}")
        base.diz("\nAgora: intro.py checklist --medir " + str(saida.relative_to(raiz) if saida.is_relative_to(raiz) else saida))
        return 0

    if a.cmd == "checklist":
        arq = None
        if a.medir:
            arq = Path(a.medir).expanduser()
            arq = arq if arq.is_absolute() else raiz / a.medir
        elif (raiz / SAIDA).is_file():
            arq = raiz / SAIDA
        m = medir(plano, arq)
        texto = checklist(plano, m, creditos_faltando(raiz, plano))
        base.gravar_texto(raiz / CHECKLIST, texto)
        if a.json:
            print(json.dumps(m, ensure_ascii=False, indent=1))
            return 0
        base.diz(texto)
        base.diz(f"{raiz / CHECKLIST}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(base.rodar(main))
