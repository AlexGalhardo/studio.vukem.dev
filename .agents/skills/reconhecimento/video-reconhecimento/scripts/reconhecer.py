#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconhecer.py — por trecho do vídeo: a pessoa está OLHANDO PARA A CÂMERA, LENDO ou SEM ROSTO.

Uso:
  reconhecer.py <mídia> --saida transcricao/ [--fps 1] [--calibrar <xml rotulado>]
                [--grupo-camera A|B] [--trecho-min S] [--inicio S] [--fim S] [--folha]

Como decide:
  1. mede cada amostra (rosto, giro da cabeça, para onde apontam os olhos) — no Mac pelo Vision da Apple
     (olhar.swift, compilado uma vez); nos outros sistemas pelo OpenCV (olhar_cv.py);
  2. separa as amostras COM rosto em DOIS GRUPOS pelo próprio material (k-médias determinístico);
  3. diz qual grupo é "câmera": pelo XML rotulado de --calibrar (clipe com etiqueta VERDE = olhando para a
     câmera), pelo --grupo-camera que o usuário escolher, ou, sem nenhum dos dois, pelo palpite do grupo com a
     cabeça mais parada e os olhos mais centrados — e avisa que é palpite.
  4. junta amostras em trechos, alisando o que pisca (--trecho-min).

Sai em <saida>/:
  olhar.json        {"trechos":[{"t0","t1","estado","confianca","amostras"}], "amostras":[...], "grupos":{...}}
  olhar.md          leitura humana em mm:ss
  olhar_grupos.jpg  (com --folha) quadros de cada grupo, para o usuário dizer qual é qual

Códigos: 0 ok · 1 falhou · 2 falta insumo (nenhum detector nesta máquina).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
CASA = Path(os.environ.get("CRIABR_CASA", Path.home() / ".criabr"))

ESTADOS = ("camera", "lendo", "sem_rosto")
BLOCO = 120.0        # segundos de vídeo por chamada ao detector (o Vision trava se for aquecido demais)
PAUSA_BLOCO = 1.0    # respiro entre blocos
INATIVIDADE = 120.0   # segundos sem progresso que o vigia da trava aceita antes de matar o detector
MARGEM_TEMPO = 1800.0  # prazo final do nosso lado. É generoso de propósito: a ESPERA NA FILA da trava conta
                       # aqui, e numa máquina ocupada ela passa de 10 min. Quem mata detector travado de
                       # verdade é o vigia da trava (INATIVIDADE), que não conta fila.


class Erro(Exception):
    def __init__(self, mensagem, dica=None, codigo=1):
        super().__init__(mensagem)
        self.dica, self.codigo = dica, codigo


def com_trava(cmd):
    """Devolve o comando, pela trava quando ela existe e o sistema não é Windows.

    `--inatividade` entrega ao vigia da trava o papel de matar o detector travado: ele conta só o tempo em
    que o comando JÁ ESTÁ rodando sem progresso, não o tempo na fila. Sem isso, numa máquina ocupada o
    prazo do reconhecer.py dispara na fila e um detector saudável vira "travado"."""
    t = Path.home() / ".claude/skills/video-direcao-de-arte/kit/trava.py"
    if t.exists() and platform.system() != "Windows":
        return [sys.executable, str(t), "--inatividade", str(INATIVIDADE), "--"] + list(cmd)
    return list(cmd)


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


def duracao(midia):
    ff = shutil.which("ffprobe")
    if not ff:
        raise Erro("não encontrei o ffprobe.", "Rode o preparar.py desta skill com --instalar.", 127)
    r = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(midia)],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        raise Erro(f"não consegui ler a duração de {Path(midia).name}.")


# ------------------------------------------------------------------ detector

def binario_vision():
    """Compila o olhar.swift uma vez (fica em ~/.criabr/bin) e devolve o caminho. None se não dá no sistema."""
    if platform.system() != "Darwin":
        return None
    fonte = AQUI / "olhar.swift"
    swiftc = shutil.which("swiftc")
    if not fonte.is_file() or not swiftc:
        return None
    alvo = CASA / "bin" / "olhar"
    if alvo.exists() and alvo.stat().st_mtime >= fonte.stat().st_mtime:
        return alvo
    alvo.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(com_trava([swiftc, "-O", "-o", str(alvo), str(fonte)]),
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not alvo.exists():
        print(f"aviso: não consegui compilar o olhar.swift ({(r.stderr or '')[-300:]})", file=sys.stderr)
        return None
    return alvo


def medir_bloco(midia, t0, t1, fps, trabalho, n):
    """Mede um bloco do vídeo. Devolve a lista de amostras ou None se o detector travou."""
    saida = trabalho / f"bloco{n:04d}.json"
    binario = binario_vision()
    limite = (t1 - t0) * max(1.0, fps) * 2.0 + MARGEM_TEMPO
    if binario:
        cmd = [str(binario), str(midia), str(saida), "--fps", str(fps), "--inicio", f"{t0}", "--fim", f"{t1}"]
    else:
        cv = AQUI / "olhar_cv.py"
        if not cv.is_file():
            raise Erro("não há detector de rosto nesta máquina.",
                       "No Mac: instale as ferramentas de linha de comando do Xcode (precisa do swiftc). "
                       "No Linux/Windows: rode o preparar.py desta skill com --instalar (instala o OpenCV).", 2)
        cmd = [sys.executable, str(cv), str(midia), str(saida), "--fps", str(fps),
               "--inicio", f"{t0}", "--fim", f"{t1}"]
    try:
        r = subprocess.run(com_trava(cmd), capture_output=True, text=True, encoding="utf-8", timeout=limite)
    except subprocess.TimeoutExpired:
        print(f"aviso: o detector travou no bloco {mmss(t0)}–{mmss(t1)} e foi encerrado.", file=sys.stderr)
        return None
    if r.returncode != 0 or not saida.exists():
        print(f"aviso: bloco {mmss(t0)}–{mmss(t1)} falhou: {(r.stderr or '').strip()[-200:]}", file=sys.stderr)
        return None
    d = json.loads(saida.read_text(encoding="utf-8"))
    saida.unlink(missing_ok=True)
    return d


def medir(midia, fps, inicio, fim, trabalho):
    """Varre o vídeo em blocos. O Vision trava quando é aquecido demais: cada bloco tem prazo, e um bloco que
    trava é tentado uma vez com metade da taxa antes de virar 'não medido'."""
    amostras, meta, naomedidos = [], None, []
    t, n = inicio, 0
    while t < fim - 1e-6:
        t1 = min(fim, t + BLOCO)
        d = medir_bloco(midia, t, t1, fps, trabalho, n)
        if d is None:
            time.sleep(3.0)
            d = medir_bloco(midia, t, t1, max(0.3, fps / 2), trabalho, n)
        if d is None:
            naomedidos.append([round(t, 2), round(t1, 2)])
        else:
            meta = meta or d
            amostras += d.get("amostras", [])
        t, n = t1, n + 1
        if t < fim:
            time.sleep(PAUSA_BLOCO)
    if not amostras:
        raise Erro("o detector não conseguiu medir nenhum quadro.",
                   "Confira se a mídia abre e se há rosto nela; tente --fps 0.5.", 2)
    return amostras, (meta or {}), naomedidos


# ------------------------------------------------------------------ pessoa principal

def pessoa_principal(amostras, tolerancia=0.18):
    """Com mais de um rosto na cena, segue UM: o que aparece mais vezes perto da mesma posição.
    Devolve, por amostra, o rosto dessa pessoa (ou None)."""
    centros = [(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2, r["w"])
               for a in amostras for r in a.get("rostos", [])]
    if not centros:
        return [None] * len(amostras)
    grade = {}
    for cx, cy, w in centros:
        k = (round(cx / tolerancia), round(cy / tolerancia))
        grade.setdefault(k, []).append((cx, cy, w))
    melhor = max(grade.values(), key=len)
    ax = sum(c[0] for c in melhor) / len(melhor)
    ay = sum(c[1] for c in melhor) / len(melhor)
    saida = []
    for a in amostras:
        cand = []
        for r in a.get("rostos", []):
            d = abs(r["x"] + r["w"] / 2 - ax) + abs(r["y"] + r["h"] / 2 - ay)
            cand.append((d, r))
        cand.sort(key=lambda p: p[0])
        saida.append(cand[0][1] if cand and cand[0][0] <= tolerancia * 2.5 else None)
    return saida


# ------------------------------------------------------------------ dois grupos

CAMPOS = ("yaw", "pitch", "olho_y", "olho_x", "roll")


def vetores(rostos):
    import numpy as np
    linhas, indices = [], []
    for i, r in enumerate(rostos):
        if r is None:
            continue
        linhas.append([float(r.get(c) or 0.0) for c in CAMPOS])
        indices.append(i)
    if not linhas:
        return np.zeros((0, len(CAMPOS))), []
    v = np.array(linhas, dtype=np.float64)
    mediana = np.median(v, axis=0)
    escala = np.median(np.abs(v - mediana), axis=0) * 1.4826
    escala[escala < 1e-3] = 1e-3
    return (v - mediana) / escala, indices


def duas_turmas(v, voltas=40):
    """k-médias com k=2, semente determinística (os dois pontos mais distantes no eixo de maior variação)."""
    import numpy as np
    if len(v) < 4:
        return np.zeros(len(v), dtype=int), 0.0
    eixo = int(np.argmax(v.var(axis=0)))
    c = np.array([v[int(np.argmin(v[:, eixo]))], v[int(np.argmax(v[:, eixo]))]], dtype=np.float64)
    rotulo = np.zeros(len(v), dtype=int)
    for _ in range(voltas):
        d = np.linalg.norm(v[:, None, :] - c[None, :, :], axis=2)
        novo = d.argmin(axis=1)
        if (novo == rotulo).all():
            break
        rotulo = novo
        for k in (0, 1):
            if (rotulo == k).any():
                c[k] = v[rotulo == k].mean(axis=0)
    d = np.linalg.norm(v[:, None, :] - c[None, :, :], axis=2)
    perto, longe = np.sort(d, axis=1)[:, 0], np.sort(d, axis=1)[:, 1]
    silhueta = float(np.mean((longe - perto) / np.maximum(longe, 1e-6)))
    return rotulo, silhueta


def palpite_camera(rostos, rotulo_amostra):
    """Sem calibração: o grupo da câmera é o que tem a cabeça e a pupila mais perto do ZERO ABSOLUTO — `yaw`,
    `pitch` e `olho_y` medem desvio em relação a olhar de frente, e olhar de frente é 0.

    Aqui entra o valor CRU, nunca o normalizado: normalizar põe a mediana DO VÍDEO no zero, e num vídeo em
    que a pessoa passa a maior parte do tempo lendo a mediana É o jeito de ler. Medido numa amostra de 24
    quadros: com o valor normalizado o palpite saiu invertido (chamou de "câmera" o grupo de cabeça baixa);
    com o valor cru, acertou. Continua sendo palpite — a skill avisa e pede confirmação."""
    import numpy as np
    nota = {}
    for k in (0, 1):
        linhas = [[abs(float(r.get(c) or 0.0)) for c in ("yaw", "pitch", "olho_y")]
                  for r, g in zip(rostos, rotulo_amostra) if r is not None and g == k]
        nota[k] = float(np.median(np.array(linhas), axis=0).sum()) if linhas else 1e9
    return 0 if nota[0] <= nota[1] else 1


# ------------------------------------------------------------------ calibração pelo XML

def calibrar_xml(xml, midia, tempos, rotulo_de_amostra):
    """XML do Premiere com os clipes rotulados: etiqueta VERDE = olhando para a câmera. Devolve qual grupo é
    o da câmera e o acerto medido contra o rótulo do editor."""
    sys.path.insert(0, str(AQUI))
    from rotulos_xml import trechos_rotulados
    verdes, outros = trechos_rotulados(xml, midia)
    if not verdes:
        raise Erro(f"{Path(xml).name} não tem nenhum clipe com etiqueta verde.",
                   "No Premiere, marque de VERDE os clipes em que a pessoa olha para a câmera e exporte "
                   "Arquivo → Exportar → Final Cut Pro XML.", 2)

    def dentro(t, faixas):
        return any(a <= t < b for a, b in faixas)

    acertos = {0: 0, 1: 0}
    total = 0
    for t, k in zip(tempos, rotulo_de_amostra):
        if k is None:
            continue
        verde = dentro(t, verdes)
        if not verde and not dentro(t, outros):
            continue
        total += 1
        for g in (0, 1):
            if (k == g) == verde:
                acertos[g] += 1
    if not total:
        raise Erro("nenhuma amostra caiu dentro dos clipes do XML.",
                   "O XML é da mesma mídia? Os tempos dos clipes batem com o bruto?", 2)
    grupo = 0 if acertos[0] >= acertos[1] else 1
    return grupo, {"amostras_comparadas": total, "acerto": round(max(acertos.values()) / total, 3),
                   "trechos_verdes": len(verdes), "trechos_outros": len(outros)}


# ------------------------------------------------------------------ trechos

def alisar(estados, minimo_amostras):
    """Tira o que pisca: uma ilha de estado menor que `minimo_amostras` vira o estado dos vizinhos."""
    if minimo_amostras <= 1 or not estados:
        return list(estados)
    e = list(estados)
    i = 0
    while i < len(e):
        j = i
        while j < len(e) and e[j] == e[i]:
            j += 1
        if j - i < minimo_amostras and (i > 0 or j < len(e)):
            vizinho = e[i - 1] if i > 0 else e[j]
            if i > 0 and j < len(e) and e[i - 1] != e[j]:
                vizinho = e[i - 1] if (i) >= (len(e) - j) else e[j]
            for k in range(i, j):
                e[k] = vizinho
            i = 0
            continue
        i = j
    return e


def em_trechos(tempos, estados, passo, fim):
    trechos = []
    i = 0
    while i < len(estados):
        j = i
        while j < len(estados) and estados[j] == estados[i]:
            j += 1
        t0 = tempos[i]
        t1 = tempos[j] if j < len(tempos) else min(fim, tempos[j - 1] + passo)
        trechos.append({"t0": round(t0, 2), "t1": round(t1, 2), "estado": estados[i], "amostras": j - i})
        i = j
    return trechos


# ------------------------------------------------------------------ folha de contato

def folha_de_grupos(midia, tempos, rotulo, saida, por_grupo=6):
    """Quadros de cada grupo lado a lado, para o usuário dizer qual é 'olhando para a câmera'."""
    from PIL import Image, ImageDraw
    ff = shutil.which("ffmpeg")
    if not ff:
        return None
    # espalha as escolhas pelo vídeo INTEIRO (pegar as primeiras esconde o que acontece no fim)
    escolhidos = {}
    for k in (0, 1):
        ts = [t for t, g in zip(tempos, rotulo) if g == k]
        passo = max(1, len(ts) // por_grupo)
        escolhidos[k] = ts[::passo][:por_grupo]
    tmp = Path(saida).parent / "_grupos"
    tmp.mkdir(parents=True, exist_ok=True)
    imagens = {0: [], 1: []}
    for k, ts in escolhidos.items():
        for n, t in enumerate(ts):
            p = tmp / f"g{k}_{n}.jpg"
            subprocess.run(com_trava([ff, "-v", "error", "-y", "-ss", f"{t}", "-i", str(midia),
                                      "-frames:v", "1", "-vf", "scale=-2:200", "-q:v", "4", str(p)]),
                           capture_output=True)
            if p.exists():
                imagens[k].append(p)
    if not imagens[0] and not imagens[1]:
        return None
    larg = max(sum(Image.open(p).width for p in imagens[k]) or 1 for k in (0, 1))
    folha = Image.new("RGB", (larg + 8, 2 * (200 + 26) + 8), (18, 18, 18))
    d = ImageDraw.Draw(folha)
    for k in (0, 1):
        y = k * (200 + 26) + 4
        d.text((6, y + 4), f"GRUPO {'AB'[k]} — {len([1 for r in rotulo if r == k])} amostras", fill=(255, 220, 0))
        x = 4
        for p in imagens[k]:
            im = Image.open(p)
            folha.paste(im, (x, y + 22))
            x += im.width + 2
    folha.save(saida, quality=85)
    for p in tmp.glob("*.jpg"):
        p.unlink()
    tmp.rmdir()
    return saida


# ------------------------------------------------------------------ principal

def main():
    ap = argparse.ArgumentParser(description="Diz, por trecho, se a pessoa olha para a câmera, lê ou sumiu.")
    ap.add_argument("midia")
    ap.add_argument("--saida", default="transcricao", help="pasta de saída (padrão: transcricao/)")
    ap.add_argument("--fps", type=float, default=1.0, help="amostras por segundo (padrão 1; não use quadro a quadro)")
    ap.add_argument("--calibrar", help="XML do Premiere rotulado (etiqueta verde = olhando para a câmera)")
    ap.add_argument("--grupo-camera", choices=("A", "B"), help="qual dos dois grupos é o da câmera")
    ap.add_argument("--trecho-min", type=float, default=1.5, help="trecho menor que isto é absorvido (s)")
    ap.add_argument("--inicio", type=float, default=0.0)
    ap.add_argument("--fim", type=float)
    ap.add_argument("--folha", action="store_true", help="grava olhar_grupos.jpg com quadros de cada grupo")
    ap.add_argument("--conf-min", type=float, default=0.25, help="confiança mínima do rosto")
    ap.add_argument("--grupo-min", type=int, default=10,
                    help="grupo menor que isto (e com menos de 8%% das amostras) é ruído, não um 2º jeito "
                         "de olhar: o vídeo vira 'um jeito só'. 0 desliga a proteção")
    o = ap.parse_args()

    import numpy as np
    midia = Path(o.midia)
    if not midia.is_file():
        raise Erro(f"mídia não encontrada: {midia}")
    fim = o.fim if o.fim is not None else duracao(midia)
    pasta = Path(o.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    trabalho = pasta / "_olhar"
    trabalho.mkdir(parents=True, exist_ok=True)
    try:
        amostras, meta, naomedidos = medir(midia, o.fps, o.inicio, fim, trabalho)
    finally:
        for p in trabalho.glob("*"):
            p.unlink(missing_ok=True)
        trabalho.rmdir()

    tempos = [float(a["t"]) for a in amostras]
    rostos = pessoa_principal(amostras)
    rostos = [r if (r and float(r.get("conf", 1)) >= o.conf_min) else None for r in rostos]
    v, indices = vetores(rostos)
    rotulo_amostra = [None] * len(rostos)
    grupos_info = {"silhueta": 0.0}
    if len(v) >= 4:
        rot, sil = duas_turmas(v)
        for i, k in zip(indices, rot):
            rotulo_amostra[i] = int(k)
        grupos_info["silhueta"] = round(sil, 3)
    else:
        for i in indices:
            rotulo_amostra[i] = 0

    origem, calib = "palpite", None
    grupo_camera = palpite_camera(rostos, rotulo_amostra) if len(v) >= 4 else 0
    if o.calibrar:
        grupo_camera, calib = calibrar_xml(o.calibrar, midia, tempos, rotulo_amostra)
        origem = "xml"
    elif o.grupo_camera:
        grupo_camera = "AB".index(o.grupo_camera)
        origem = "usuario"

    # UM JEITO DE OLHAR SÓ: o k-médias é obrigado a devolver dois grupos, então num vídeo em que a pessoa
    # nunca desvia o olhar ele separa dois ou três quadros atípicos (piscada, cabeça virando) e chama de
    # "lendo". Medido: 1 amostra de 40 e 3 de 76 — era falso. Quando o grupo menor é pequeno nas DUAS contas
    # (menos de 8% e menos de `grupo_min` amostras) e ninguém disse o contrário, tudo vira o grupo maior.
    grupo_unico = False
    n_grupo = {k: sum(1 for x in rotulo_amostra if x == k) for k in (0, 1)}
    menor = min(n_grupo, key=lambda k: n_grupo[k])
    total_rosto = n_grupo[0] + n_grupo[1]
    if (origem == "palpite" and total_rosto
            and n_grupo[menor] < o.grupo_min and n_grupo[menor] / total_rosto < 0.08):
        grupo_unico = True
        grupo_camera = 1 - menor
        origem = "grupo único"
        rotulo_amostra = [None if k is None else grupo_camera for k in rotulo_amostra]

    estados = []
    for r, k in zip(rostos, rotulo_amostra):
        if r is None or k is None:
            estados.append("sem_rosto")
        else:
            estados.append("camera" if k == grupo_camera else "lendo")
    passo = 1.0 / max(o.fps, 1e-6)
    minimo = max(1, int(round(o.trecho_min * o.fps)))
    alisados = alisar(estados, minimo)
    trechos = em_trechos(tempos, alisados, passo, fim)
    # confiança do trecho: fração de amostras cruas que já concordavam com o estado final
    for t in trechos:
        cru = [e for tt, e in zip(tempos, estados) if t["t0"] <= tt < t["t1"]]
        t["confianca"] = round(sum(1 for e in cru if e == t["estado"]) / max(len(cru), 1), 2)

    por_estado = {e: round(sum(t["t1"] - t["t0"] for t in trechos if t["estado"] == e), 2) for e in ESTADOS}
    doc = {"fonte": str(midia).replace("\\", "/"), "detector": meta.get("detector", "?"),
           "fps_amostra": o.fps, "duracao_s": round(fim, 2),
           "grupo_camera": "AB"[grupo_camera], "origem_do_rotulo": origem, "um_jeito_de_olhar": grupo_unico,
           "grupos": {**grupos_info, "A": sum(1 for k in rotulo_amostra if k == 0),
                      "B": sum(1 for k in rotulo_amostra if k == 1)},
           "calibracao": calib, "nao_medido": naomedidos, "segundos_por_estado": por_estado,
           "trechos": trechos,
           # `estado` é o FINAL (o mesmo dos trechos, depois do alisamento) e `estado_cru` é o que o detector
           # disse antes dele. Guardar só o cru fazia a amostra discordar do trecho que a contém.
           "amostras": [{"t": t, "estado": e, "estado_cru": c0, "grupo": (None if k is None else "AB"[k]),
                         **({c: r.get(c) for c in CAMPOS if r.get(c) is not None} if r else {})}
                        for t, e, c0, k, r in zip(tempos, alisados, estados, rotulo_amostra, rostos)]}
    gravar_json(pasta / "olhar.json", doc)

    L = [f"# Olhar — {midia.name}", "",
         f"{len(trechos)} trecho(s) · câmera {mmss(por_estado['camera'])} · lendo {mmss(por_estado['lendo'])} · "
         f"sem rosto {mmss(por_estado['sem_rosto'])} · detector: {doc['detector']}", "",
         f"Grupo da câmera: **{doc['grupo_camera']}** (definido por: {origem}"
         + (f", acerto medido {calib['acerto']:.0%} em {calib['amostras_comparadas']} amostras" if calib else "")
         + f"). Separação dos dois grupos: {grupos_info['silhueta']} (0 = colados, 1 = bem separados).", ""]
    if grupo_unico:
        L += [f"> **Um jeito de olhar só.** O grupo menor tinha {n_grupo[menor]} amostra(s) de {total_rosto} "
              "— ruído, não um segundo jeito de olhar. Tudo com rosto virou «camera» e NÃO há «lendo» a "
              "declarar. Se você sabe que há trecho lido, aumente `--fps`, baixe `--grupo-min` ou calibre "
              "com `--calibrar <xml rotulado>`.", ""]
    elif origem == "palpite":
        L += ["> O rótulo é PALPITE. Rode com `--folha`, olhe o `olhar_grupos.jpg` e confirme com "
              "`--grupo-camera A` ou `B`; ou calibre com `--calibrar <xml rotulado>`.", ""]
    if naomedidos:
        L += [f"> {len(naomedidos)} bloco(s) não puderam ser medidos (detector travado): "
              + ", ".join(f"{mmss(a)}–{mmss(b)}" for a, b in naomedidos[:8]), ""]
    L += ["| trecho | dur | estado | confiança |", "|---|---|---|---|"]
    for t in trechos:
        L.append(f"| {mmss(t['t0'])}–{mmss(t['t1'])} | {t['t1'] - t['t0']:.1f} s | {t['estado']} "
                 f"| {t['confianca']:.0%} |")
    gravar_texto(pasta / "olhar.md", "\n".join(L))

    if o.folha:
        f = folha_de_grupos(midia, tempos, rotulo_amostra, pasta / "olhar_grupos.jpg")
        if f:
            print(f"folha dos grupos: {f}")

    print(f"{len(trechos)} trecho(s) · câmera {mmss(por_estado['camera'])} · lendo {mmss(por_estado['lendo'])} · "
          f"sem rosto {mmss(por_estado['sem_rosto'])}")
    print(f"grupo da câmera: {doc['grupo_camera']} ({origem})" +
          (f" · acerto {calib['acerto']:.0%}" if calib else ""))
    print(f"{pasta / 'olhar.json'} · {pasta / 'olhar.md'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Erro as e:
        print(f"erro: {e}", file=sys.stderr)
        if e.dica:
            print(f"  → {e.dica}", file=sys.stderr)
        sys.exit(e.codigo)
