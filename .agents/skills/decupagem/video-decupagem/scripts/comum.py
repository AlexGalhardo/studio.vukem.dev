#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comum.py — o que decupar.py, render.py e qa.py dividem: ffmpeg pela trava, ficha técnica do bruto,
energia do áudio a cada 10 ms, palavras da transcrição, grade de quadros e leitura/escrita da EDL.

Tempos SEMPRE em segundos do BRUTO. Todo corte cai numa fronteira de quadro.
"""
from __future__ import annotations

import json
import bisect
import math
import platform
import shutil
import subprocess
import sys
import unicodedata
import re
from pathlib import Path

sys.dont_write_bytecode = True

PASSO = 0.01          # janela da energia (10 ms)
CRUZADO = 0.012       # meia-largura do crossfade de áudio nas junções (s) → emenda de 24 ms
SR = 48000            # taxa do áudio de trabalho


class Erro(Exception):
    """Erro para o usuário: mensagem, dica (o que fazer) e código de saída."""

    def __init__(self, mensagem, dica=None, codigo=1):
        super().__init__(mensagem)
        self.dica, self.codigo = dica, codigo


def sair_com_erro(e):
    print(f"erro: {e}", file=sys.stderr)
    if getattr(e, "dica", None):
        print(f"  → {e.dica}", file=sys.stderr)
    return int(getattr(e, "codigo", 1) or 1)


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows."""
    t = Path.home() / ".claude/skills/video-direcao-de-arte/kit/trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--"] + list(cmd)
    return list(cmd)


def programa(nome):
    c = shutil.which(nome)
    if not c:
        raise Erro(f"não encontrei o {nome} nesta máquina.",
                   "Rode o preparar.py desta skill com --instalar.", 127)
    return c


def rodar(cmd, captura=False, trava=True, entrada=None):
    """Roda um comando externo (lista de argumentos, nunca shell)."""
    c = com_trava(cmd) if trava else list(cmd)
    r = subprocess.run([str(x) for x in c], capture_output=captura, input=entrada,
                       text=False if captura else None)
    if r.returncode != 0:
        saida = (r.stderr or b"")[-900:].decode("utf-8", "replace") if captura else ""
        raise Erro(f"{Path(str(cmd[0])).name} falhou (código {r.returncode}). {saida}".strip())
    return r.stdout if captura else None


# ---------------------------------------------------------------- ficha técnica

def ficha(midia):
    """ffprobe → dicionário com o que o render precisa para devolver a MESMA especificação do bruto."""
    midia = Path(midia)
    if not midia.is_file():
        raise Erro(f"mídia não encontrada: {midia}")
    bruto = rodar([programa("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(midia)],
                  captura=True, trava=False)
    d = json.loads(bruto.decode("utf-8", "replace"))
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        raise Erro(f"{midia.name} não tem trilha de vídeo.", "Esta skill decupa vídeo; para só áudio, use a EDL com render --so-audio.")
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    f = {"arquivo": str(midia), "fps": fps, "fps_fracao": v.get("r_frame_rate"),
         "duracao": float(d["format"].get("duration") or v.get("duration") or 0),
         "largura": int(v.get("width") or 0), "altura": int(v.get("height") or 0),
         "codec": v.get("codec_name"), "perfil": v.get("profile"), "pix_fmt": v.get("pix_fmt"),
         "nivel": v.get("level"), "faixa": v.get("color_range"), "espaco": v.get("color_space"),
         "primarias": v.get("color_primaries"), "transferencia": v.get("color_transfer"),
         "taxa_video": int(v.get("bit_rate") or 0), "quadros": int(v.get("nb_frames") or 0),
         "audio": None}
    if a is not None:
        f["audio"] = {"codec": a.get("codec_name"), "taxa": int(a.get("bit_rate") or 0),
                      "sr": int(a.get("sample_rate") or SR), "canais": int(a.get("channels") or 2)}
    return f


def keyframes(midia, ate=None):
    """Instantes dos quadros-chave (I-frames) do vídeo. É isso que decide se dá para cortar com -c copy."""
    cmd = [programa("ffprobe"), "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
           "-show_entries", "frame=pts_time", "-of", "csv=p=0"]
    if ate:
        cmd += ["-read_intervals", f"%{ate}"]
    cmd += [str(midia)]
    bruto = rodar(cmd, captura=True, trava=False).decode("utf-8", "replace")
    return sorted(float(x) for x in re.findall(r"^([0-9.]+)", bruto, re.M))


# ---------------------------------------------------------------- áudio e energia

def pcm(midia, sr=SR, canais=1):
    """Áudio do bruto como numpy float32 (n, canais), decodificado uma vez."""
    import numpy as np
    bruto = rodar([programa("ffmpeg"), "-v", "error", "-i", str(midia), "-vn",
                   "-ac", str(canais), "-ar", str(sr), "-f", "f32le", "-"], captura=True)
    x = np.frombuffer(bruto, dtype=np.float32)
    if x.size == 0:
        raise Erro(f"{Path(midia).name} não tem áudio decodificável.",
                   "A decupagem precisa do som para achar fala, pausa e ponto de corte limpo.", 2)
    return x.reshape(-1, canais)


def energia_db(x, sr=SR, passo=PASSO):
    """Envelope de energia em dBFS, uma amostra a cada `passo` segundos (a verdade sobre onde há fala)."""
    import numpy as np
    m = x.mean(axis=1) if x.ndim > 1 else x
    h = int(round(sr * passo))
    n = len(m) // h
    if n == 0:
        raise Erro("áudio curto demais para medir energia.")
    r = np.sqrt((m[:n * h].reshape(n, h) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(r)


def limiar_fala(db):
    """Limiar fala × sala, medido no próprio material: 34 dB abaixo do pico (percentil 99,5), nunca abaixo do
    fundo do arquivo (percentil 1 + 3 dB) nem acima da mediana − 2 dB.

    Por que o pico e não o piso: gravação com compressor (podcast, OBS com ganho alto) não tem silêncio de
    verdade — o percentil 10 já é fala, e um limiar tirado dele inventa pausa no meio da palavra. Medido nas
    amostras: material comprimido (piso −42 dBFS) fica com 99% de fala, que é a resposta certa; material com
    sala de verdade (piso −85 dBFS) fica com 76%."""
    import numpy as np
    pico, fundo, meio = (float(np.percentile(db, q)) for q in (99.5, 1, 50))
    return float(min(max(pico - 34.0, fundo + 3.0), meio - 2.0))


def ilhas(db, lim, passo=PASSO, junta=0.06, minimo=0.03):
    """Trechos com fala (energia acima do limiar), lacunas curtas fundidas. Devolve [(t0, t1, pico_db)]."""
    import numpy as np
    on = db > lim
    cru, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            cru.append([i, j])
            i = j
        else:
            i += 1
    juntas = []
    for s, e in cru:
        if juntas and (s - juntas[-1][1]) * passo < junta:
            juntas[-1][1] = e
        else:
            juntas.append([s, e])
    return [(s * passo, e * passo, float(db[s:e].max())) for s, e in juntas if (e - s) * passo >= minimo]


def db_em(db, t, meia=0.02, passo=PASSO):
    """Energia máxima numa janelinha em volta de t (serve para ver se o corte cai dentro de fala)."""
    a = max(0, int((t - meia) / passo))
    b = min(len(db), int((t + meia) / passo) + 1)
    return float(db[a:b].max()) if b > a else -120.0


# ---------------------------------------------------------------- grade de quadros

class Grade:
    """A grade de quadros do bruto. Quadro k ocupa [k/fps, (k+1)/fps)."""

    def __init__(self, fps):
        self.fps = float(fps)

    def quadro(self, t):
        return max(0, int(t * self.fps + 1e-6))

    def encaixa(self, t):
        """Fronteira de quadro mais próxima."""
        return round(t * self.fps) / self.fps

    def vale(self, db, t, antes=0.25, depois=0.25, passo=PASSO, limites=None):
        """Fronteira de quadro perto de t com MENOS som em volta (±12 ms), penalizando a distância de t
        (o tempo do whisper erra uns 0,2 s; a energia é que manda).

        `limites` = (lo, hi) fecha a busca no VÃO ENTRE PALAVRAS. Sem isso o corte escorrega para dentro da
        palavra vizinha atrás de energia baixa — numa rodada ele caiu 27 ms dentro de «que», bem no fecho da
        consoante, e a emenda deixou meio fonema no ar. Quando o vão é mais estreito que um quadro (o whisper
        costuma encostar o fim de uma palavra no começo da outra), cai na fronteira de quadro mais perto da
        borda: é o melhor que a grade de quadros permite."""
        lo, hi = t - antes, t + depois
        if limites is not None:
            lo, hi = max(lo, limites[0]), min(hi, limites[1])
            if hi < lo:
                lo = hi = min(max(t, limites[0]), limites[1])
        f0 = max(0, int(math.ceil(lo * self.fps - 1e-6)))
        f1 = int(math.floor(hi * self.fps + 1e-6))
        if f1 < f0:
            return round(min(max(t, lo), hi) * self.fps) / self.fps

        def custo(f):
            return db_em(db, f / self.fps, CRUZADO, passo) + 20.0 * abs(f / self.fps - t) / max(antes, depois, 0.05)

        return min(range(f0, f1 + 1), key=custo) / self.fps


# ---------------------------------------------------------------- palavras

def ler_palavras(caminho):
    """transcricao/palavras.json → [{"t0","t1","w","p"}] ordenado. Aceita t0/t1 e o formato antigo a/b."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise Erro(f"transcrição não encontrada: {caminho}",
                   "Gere com a skill video-transcricao: transcrever.py <mídia> --saida transcricao/", 2)
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Erro(f"{caminho.name} não é um JSON válido (linha {e.lineno}: {e.msg}).")
    if isinstance(bruto, dict):
        bruto = bruto.get("palavras") or bruto.get("words") or []
    saida = []
    for p in bruto:
        if not isinstance(p, dict):
            continue
        t0, t1 = p.get("t0", p.get("a")), p.get("t1", p.get("b"))
        w = str(p.get("w", "")).strip()
        if t0 is None or t1 is None or not w:
            continue
        saida.append({"t0": float(t0), "t1": max(float(t1), float(t0)), "w": w, "p": float(p.get("p", 1.0))})
    if not saida:
        raise Erro(f"{caminho.name} não tem palavras cronometradas no formato [{{t0, t1, w, p}}].",
                   "Gere a transcrição palavra a palavra com a skill video-transcricao.", 2)
    return sorted(saida, key=lambda p: p["t0"])


def chave(w):
    """Palavra sem acento, sem pontuação e em minúscula, para comparar repetição."""
    s = unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s)


def blocos_de_palavras(palavras):
    """O que cada palavra ocupa no tempo, UMA POR UMA, em ordem e sem sobreposição: [(t0, t1)].

    Nada de fundir palavras vizinhas: o whisper costuma encostar o fim de uma no começo da outra, e fundir
    transformaria uma frase inteira num bloco só — o corte fugiria da palavra certa para a ponta da frase."""
    blocos = []
    for p in sorted(palavras, key=lambda q: q["t0"]):
        lo = max(float(p["t0"]), blocos[-1][1] if blocos else 0.0)
        blocos.append([lo, max(float(p["t1"]), lo)])
    return [(a, b) for a, b in blocos]


def vao(blocos, t, dur=None):
    """O maior intervalo em volta de t que NÃO entra em palavra nenhuma: (lo, hi).

    É o espaço onde um corte pode cair sem partir palavra. Se t já cair dentro de uma palavra, devolve o vão
    da borda MAIS PERTO (nunca o miolo), para o corte sair para fora da palavra e não para dentro dela."""
    fim = dur if dur is not None else (blocos[-1][1] + 3600.0 if blocos else t + 3600.0)
    if not blocos:
        return (0.0, fim)
    fins = [b[1] for b in blocos]
    k = bisect.bisect_right(fins, t)          # 1º bloco que termina depois de t
    if k >= len(blocos):
        return (fins[-1], fim)
    a, b = blocos[k]
    antes = (fins[k - 1] if k else 0.0, a)
    if t <= a or (t - a) <= (b - t):          # antes do bloco, ou mais perto da borda de entrada
        return antes
    return (b, blocos[k + 1][0] if k + 1 < len(blocos) else fim)


def folga_palavra(t, blocos, fps):
    """Distância do corte até a borda de palavra mais perto, em segundos. NEGATIVA quando o corte cai dentro
    da palavra. Como o corte só pode existir em fronteira de quadro, a borda é medida na mesma grade: o quadro
    mais perto da borda conta como a própria borda (folga 0)."""
    if not blocos:
        return 0.0
    bordas = [x for bloco in blocos for x in bloco]
    k = min(range(len(bordas)), key=lambda i: abs(bordas[i] - t))
    perto = bordas[k]
    dentro = next(((a, b) for a, b in blocos if a < t < b), None)
    if dentro is None:
        return abs(t - perto)
    if round(perto * fps) == round(t * fps):       # o corte É o quadro que contém a borda
        return 0.0
    return -min(t - dentro[0], dentro[1] - t)


# ---------------------------------------------------------------- EDL

def ler_edl(caminho):
    """EDL do padrão da casa: {"fonte", "cortes":[{"src0","src1","motivo"}]} — os trechos que FICAM, em ordem."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise Erro(f"EDL não encontrada: {caminho}", "Rode antes o decupar.py.", 2)
    d = json.loads(caminho.read_text(encoding="utf-8"))
    if "cortes" not in d or not d["cortes"]:
        raise Erro(f"{caminho.name} não tem a lista 'cortes'.")
    cortes = []
    for i, c in enumerate(d["cortes"]):
        a, b = float(c["src0"]), float(c["src1"])
        if b <= a:
            raise Erro(f"{caminho.name}: corte {i} tem src1 <= src0 ({a} → {b}).")
        if cortes and a < cortes[-1]["src1"] - 1e-6:
            raise Erro(f"{caminho.name}: corte {i} começa antes do fim do anterior (sobreposição).")
        cortes.append({"src0": a, "src1": b, "motivo": c.get("motivo", "")})
    d["cortes"] = cortes
    return d


def gravar_json(caminho, obj):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return caminho


def gravar_texto(caminho, texto):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto if texto.endswith("\n") else texto + "\n")
    return caminho


def mmss(t):
    return f"{int(t // 60):d}:{t % 60:05.2f}".replace(".", ",")


def montar_audio(x, cortes, sr=SR, cruzado=CRUZADO, entra=0.08, sai=0.04):
    """Concatena os trechos com crossfade de potência constante de 2*cruzado centrado em cada junção, SEM mudar a
    duração: o áudio continua `cruzado` depois da saída e começa `cruzado` antes da entrada (alças do bruto).
    É o que faz a emenda não estalar."""
    import numpy as np
    canais = x.shape[1]
    h = int(round(cruzado * sr))
    pedacos = [(int(round(c["src0"] * sr)), int(round(c["src1"] * sr))) for c in cortes]
    total = sum(b - a for a, b in pedacos)
    y = np.zeros((total, canais), np.float32)
    th = np.linspace(0, np.pi / 2, 2 * h, endpoint=False) + np.pi / (4 * max(h, 1))
    fin, fout = np.sin(th)[:, None], np.cos(th)[:, None]
    pos = 0
    for i, (a, b) in enumerate(pedacos):
        n = b - a
        aa = a - (h if i > 0 else 0)
        bb = b + (h if i < len(pedacos) - 1 else 0)
        ac, bc = max(0, aa), min(len(x), bb)
        seg = np.zeros((bb - aa, canais), np.float32)
        seg[ac - aa: ac - aa + (bc - ac)] = x[ac:bc]
        if i > 0:
            seg[:2 * h] *= fin
        else:
            r = min(n, int(entra * sr))
            if r:
                seg[:r] *= np.linspace(0, 1, r, dtype=np.float32)[:, None]
        if i < len(pedacos) - 1:
            seg[-2 * h:] *= fout
        else:
            r = min(n, int(sai * sr))
            if r:
                seg[-r:] *= np.linspace(1, 0, r, dtype=np.float32)[:, None]
        d0 = pos - (h if i > 0 else 0)
        y[d0:d0 + len(seg)] += seg[:len(y) - d0]
        pos += n
    return y
