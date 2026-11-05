#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""olhar_cv.py — o MESMO trabalho do olhar.swift (amostrar quadros e medir o rosto), mas com OpenCV, para
Linux e Windows, onde não existe o Vision da Apple.

uso: olhar_cv.py <vídeo> <saida.json> [--fps 1] [--inicio S] [--fim S] [--lado 640] [--max-rostos 4]

Grava o mesmo formato do olhar.swift, para o reconhecer.py não precisar saber quem mediu:
  {"versao", "detector", "largura", "altura", "duracao", "fps", "falhas",
   "amostras": [{"t", "rostos": [{"x","y","w","h","conf","yaw","pitch","roll","olho_x","olho_y","abertura"}]}]}

Aviso honesto: aqui não há giro de cabeça de verdade (o OpenCV só devolve caixas). Os campos yaw/pitch/roll
são DEDUZIDOS da posição dos olhos dentro da caixa do rosto, e `olho_y` cresce quando os olhos somem — o que
acontece quando a pessoa baixa a cabeça para ler. É mais grosseiro que o Vision; por isso o reconhecer.py
separa em dois grupos e pede a confirmação de qual é qual em vez de usar limiar fixo.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def cascata(cv2, nome):
    c = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / nome))
    return None if c.empty() else c


def medir_rosto(cv2, cinza, x, y, w, h, olhos_c):
    """Deduz giro e abertura pela posição dos olhos dentro da caixa do rosto."""
    d = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "olho_x": 0.0, "olho_y": 1.0, "abertura": 0.0}
    if olhos_c is None:
        return d
    alto = cinza[y:y + int(h * 0.62), x:x + w]
    if alto.size == 0:
        return d
    olhos = olhos_c.detectMultiScale(alto, scaleFactor=1.1, minNeighbors=6,
                                     minSize=(max(8, w // 12), max(8, w // 14)))
    olhos = sorted(olhos, key=lambda o: -o[2] * o[3])[:2]
    if not len(olhos):
        return d
    centros = [(ox + ow / 2.0, oy + oh / 2.0, ow, oh) for ox, oy, ow, oh in olhos]
    cx = sum(c[0] for c in centros) / len(centros)
    cy = sum(c[1] for c in centros) / len(centros)
    d["yaw"] = round((cx / max(w, 1) - 0.5) * 2.0, 3)          # olhos deslocados = cabeça virada
    d["pitch"] = round((cy / max(h * 0.62, 1) - 0.5) * 2.0, 3)  # olhos mais baixos na caixa = cabeça baixa
    d["olho_y"] = round(1.0 - len(centros) / 2.0, 3)            # 0 = os dois olhos à vista, 1 = nenhum
    d["abertura"] = round(sum(c[3] for c in centros) / len(centros) / max(h, 1), 3)
    if len(centros) == 2:
        a, b = sorted(centros, key=lambda c: c[0])
        d["roll"] = round(math.atan2(b[1] - a[1], max(b[0] - a[0], 1e-6)), 3)
        d["olho_x"] = round(((a[0] + b[0]) / 2 / max(w, 1) - 0.5) * 2.0, 3)
    return d


def main():
    ap = argparse.ArgumentParser(description="Mede rosto e olhar com OpenCV (Linux/Windows).")
    ap.add_argument("video")
    ap.add_argument("saida")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--inicio", type=float, default=0.0)
    ap.add_argument("--fim", type=float)
    ap.add_argument("--lado", type=int, default=640)
    ap.add_argument("--max-rostos", type=int, default=4)
    o = ap.parse_args()
    try:
        import cv2
    except ImportError:
        print("olhar_cv: o OpenCV (opencv-python) não está instalado neste Python.", file=sys.stderr)
        return 2

    cap = cv2.VideoCapture(str(o.video))
    if not cap.isOpened():
        print(f"olhar_cv: não consegui abrir {o.video}", file=sys.stderr)
        return 1
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_quadros = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    largura = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0
    altura = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0
    dur = (n_quadros / fps_video) if fps_video else 0.0
    fim = min(o.fim if o.fim is not None else dur or 1e9, dur or 1e9)

    rostos_c = cascata(cv2, "haarcascade_frontalface_default.xml")
    perfil_c = cascata(cv2, "haarcascade_profileface.xml")
    olhos_c = cascata(cv2, "haarcascade_eye.xml")
    if rostos_c is None:
        print("olhar_cv: o OpenCV desta máquina não trouxe os classificadores Haar.", file=sys.stderr)
        return 2

    amostras, falhas, com_rosto = [], 0, 0
    t, passo = o.inicio, 1.0 / max(o.fps, 1e-6)
    while t < fim - 1e-6:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, quadro = cap.read()
        if not ok or quadro is None:
            falhas += 1
            amostras.append({"t": round(t, 3), "rostos": []})
            t += passo
            continue
        h0, w0 = quadro.shape[:2]
        escala = min(1.0, o.lado / max(w0, h0, 1))
        if escala < 1.0:
            quadro = cv2.resize(quadro, (int(w0 * escala), int(h0 * escala)), interpolation=cv2.INTER_AREA)
        cinza = cv2.equalizeHist(cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY))
        H, W = cinza.shape[:2]
        achados = rostos_c.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5,
                                            minSize=(max(30, W // 20), max(30, W // 20)))
        frontal = True
        if not len(achados) and perfil_c is not None:
            achados = perfil_c.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5,
                                                minSize=(max(30, W // 20), max(30, W // 20)))
            frontal = False   # só o perfil achou: a cabeça está virada
        lista = []
        for x, y, w, h in sorted(achados, key=lambda r: -r[2] * r[3])[:o.max_rostos]:
            d = {"x": round(x / W, 3), "y": round(y / H, 3), "w": round(w / W, 3), "h": round(h / H, 3),
                 "conf": 1.0 if frontal else 0.5}
            d.update(medir_rosto(cv2, cinza, x, y, w, h, olhos_c))
            if not frontal:
                d["yaw"] = d["yaw"] + 1.0          # perfil: cabeça virada, por definição
            lista.append(d)
        if lista:
            com_rosto += 1
        amostras.append({"t": round(t, 3), "rostos": lista})
        t += passo
    cap.release()
    if amostras and falhas == len(amostras):
        print(f"olhar_cv: nenhum quadro pôde ser lido ({falhas} falha(s))", file=sys.stderr)
        return 1

    doc = {"versao": 1, "detector": "OpenCV Haar (frontal+perfil+olhos)", "largura": largura, "altura": altura,
           "duracao": round(dur, 3), "fps": o.fps, "inicio": o.inicio, "fim": round(fim, 3),
           "falhas": falhas, "amostras": amostras}
    with open(o.saida, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False)
    print(f"olhar_cv: {len(amostras)} amostra(s), {com_rosto} com rosto, {falhas} falha(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
