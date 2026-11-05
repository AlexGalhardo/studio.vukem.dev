#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render.py — monta o vídeo decupado NA ESPECIFICAÇÃO DO BRUTO, com corte na fronteira exata de quadro e
microfade de áudio em cada junção.

Uso:
  render.py cortes/edl.json --saida render/ [--fonte bruto/x.mp4] [--modo auto|copia|preciso]
            [--crf N] [--preset P] [--so-audio] [--nome arquivo.mp4]

Dois caminhos, escolhidos sozinhos (--modo auto):
  copia    todos os pontos de corte caem em quadro-chave → o vídeo sai bit a bit igual ao bruto (-c:v copy).
  preciso  (quase sempre) decodifica tudo e escolhe os quadros por ÍNDICE (select=between(n,a,b-1)), refazendo
           a base de tempo. Nunca usa -ss para posicionar: em MP4 vindo de HLS o -ss erra o quadro.
O áudio é SEMPRE remontado amostra a amostra do bruto, com crossfade de potência constante de 24 ms centrado em
cada junção (não muda a duração e não estala), e só então codificado.

Códigos: 0 ok · 1 falhou · 2 falta insumo.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402

# codec do bruto → (codificador preferido, argumentos de qualidade). O primeiro que existir no ffmpeg vence.
CODIFICADORES = {
    "h264": [("libx264", ["-preset", "medium", "-crf", "12"])],
    "hevc": [("hevc_videotoolbox", ["-q:v", "88", "-tag:v", "hvc1"]),
             ("libx265", ["-preset", "medium", "-crf", "16", "-tag:v", "hvc1"])],
    "vp9": [("libvpx-vp9", ["-crf", "12", "-b:v", "0", "-row-mt", "1"])],
    "av1": [("libsvtav1", ["-crf", "20", "-preset", "6"]), ("libaom-av1", ["-crf", "20", "-b:v", "0"])],
    "mpeg4": [("libx264", ["-preset", "medium", "-crf", "12"])],
    "prores": [("prores_ks", ["-profile:v", "3"])],
}
PADRAO_CODIFICADOR = [("libx264", ["-preset", "medium", "-crf", "12"])]


def codificadores_disponiveis():
    bruto = C.rodar([C.programa("ffmpeg"), "-hide_banner", "-encoders"], captura=True, trava=False)
    return set(l.split()[1] for l in bruto.decode("utf-8", "replace").splitlines()
               if l.startswith(" ") and len(l.split()) > 1)


def escolher_codificador(f, crf, preset):
    tem = codificadores_disponiveis()
    for nome, args in CODIFICADORES.get(f["codec"], PADRAO_CODIFICADOR) + PADRAO_CODIFICADOR:
        if nome in tem:
            args = list(args)
            if crf is not None and "-crf" in args:
                args[args.index("-crf") + 1] = str(crf)
            if preset and "-preset" in args:
                args[args.index("-preset") + 1] = preset
            return nome, args
    raise C.Erro("o ffmpeg desta máquina não tem nenhum codificador de vídeo conhecido.")


def cortes_em_quadros(cortes, fps):
    """Cada corte vira [quadro_inicial, quadro_final) — é por índice que o render seleciona."""
    g = C.Grade(fps)
    saida = []
    for c in cortes:
        a, b = g.quadro(c["src0"] + 1e-9), int(round(c["src1"] * fps))
        if b <= a:
            b = a + 1
        saida.append((a, b))
    return saida


def cai_em_chave(cortes, chaves, fps):
    """Todos os pontos de ENTRADA caem em quadro-chave? (a saída pode cair em qualquer quadro)."""
    if not chaves:
        return False, []
    meio = 0.5 / fps
    fora = []
    for c in cortes:
        if c["src0"] > 1e-6 and min(abs(c["src0"] - k) for k in chaves) > meio:
            fora.append(round(c["src0"], 3))
    return not fora, fora


def grafo_select(quadros, entrada="0:v", saida="v", fps_fracao="30000/1001"):
    """Seleção por índice de quadro + base de tempo refeita, para a saída ter exatamente os quadros do bruto."""
    num, den = (fps_fracao or "30/1").split("/")
    num, den = int(num), int(den or 1)
    sel = "+".join(f"between(n\\,{a}\\,{b - 1})" for a, b in quadros)
    return f"[{entrada}]select='{sel}',settb=1/{num},setpts=N*{den}[{saida}]"


def render_audio(fonte, cortes, wav, ficha):
    """Remonta o áudio do bruto com os microfades e grava um WAV de trabalho (sem perda)."""
    import numpy as np
    canais = (ficha["audio"] or {}).get("canais", 2) or 2
    x = C.pcm(fonte, sr=C.SR, canais=min(2, canais))
    y = C.montar_audio(x, cortes, sr=C.SR)
    cru = Path(str(wav) + ".f32")
    y.astype(np.float32).tofile(cru)
    try:
        C.rodar([C.programa("ffmpeg"), "-v", "error", "-y", "-f", "f32le", "-ar", str(C.SR),
                 "-ac", str(y.shape[1]), "-i", str(cru), "-c:a", "pcm_s24le", str(wav)])
    finally:
        cru.unlink(missing_ok=True)
    return len(y) / C.SR


def args_cor(f):
    a = []
    for chave, valor in (("-color_primaries", f["primarias"]), ("-color_trc", f["transferencia"]),
                         ("-colorspace", f["espaco"]), ("-color_range", f["faixa"])):
        if valor and valor != "unknown":
            a += [chave, valor]
    return a


def render_copia(fonte, quadros, f, wav, saida, trabalho):
    """Caminho sem perda: recorta por quadro-chave com -c:v copy e emenda com o concat demuxer."""
    partes, lista = [], trabalho / "partes.txt"
    linhas = []
    for i, (a, b) in enumerate(quadros):
        p = trabalho / f"parte{i:03d}.mp4"
        C.rodar([C.programa("ffmpeg"), "-v", "error", "-y", "-ss", f"{a / f['fps']:.6f}",
                 "-i", str(fonte), "-t", f"{(b - a) / f['fps']:.6f}", "-an", "-c:v", "copy",
                 "-avoid_negative_ts", "make_zero", str(p)])
        partes.append(p)
        linhas.append(f"file '{p.as_posix()}'")
    C.gravar_texto(lista, "\n".join(linhas))
    C.rodar([C.programa("ffmpeg"), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
             "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "320k", "-ar", str(C.SR), "-shortest",
             "-movflags", "+faststart", str(saida)])


def render_preciso(fonte, quadros, f, wav, saida, codificador, args_q, nq):
    cmd = [C.programa("ffmpeg"), "-hide_banner", "-v", "error", "-stats", "-y",
           "-i", str(fonte), "-i", str(wav),
           "-filter_complex", grafo_select(quadros, "0:v", "v", f["fps_fracao"]),
           "-map", "[v]", "-map", "1:a:0", "-c:v", codificador] + args_q
    if f["pix_fmt"]:
        cmd += ["-pix_fmt", f["pix_fmt"]]
    if codificador == "libx264":
        cmd += ["-x264-params", f"keyint={max(2, int(round(f['fps'] * 2)))}:min-keyint=1:aq-mode=3"]
        if f["perfil"]:
            cmd += ["-profile:v", str(f["perfil"]).lower().replace(" ", "")]
    elif codificador == "libx265":
        cmd += ["-x265-params", f"keyint={max(2, int(round(f['fps'] * 2)))}:min-keyint=1:log-level=error"]
    cmd += args_cor(f)
    cmd += ["-r", f["fps_fracao"] or f"{f['fps']}", "-fps_mode", "cfr",
            "-video_track_timescale", str(int(round(f["fps"] * 1000)) if "/" not in (f["fps_fracao"] or "") else int((f["fps_fracao"] or "30/1").split("/")[0])),
            "-c:a", "aac", "-b:a", "320k", "-ar", str(C.SR), "-frames:v", str(nq),
            "-movflags", "+faststart", str(saida)]
    C.rodar(cmd)


def main():
    ap = argparse.ArgumentParser(description="Renderiza a EDL na especificação do bruto.")
    ap.add_argument("edl")
    ap.add_argument("--saida", default="render", help="pasta de saída (padrão: render/)")
    ap.add_argument("--fonte", help="mídia do bruto (padrão: a 'fonte' da EDL)")
    ap.add_argument("--modo", choices=("auto", "copia", "preciso"), default="auto")
    ap.add_argument("--crf", type=int, help="qualidade do codificador (menor = melhor; padrão 12 em H.264)")
    ap.add_argument("--preset", help="preset do codificador (padrão: medium)")
    ap.add_argument("--so-audio", action="store_true", help="só o WAV montado, sem vídeo")
    ap.add_argument("--nome", help="nome do arquivo de saída")
    o = ap.parse_args()

    edl_f = Path(o.edl)
    edl = C.ler_edl(edl_f)
    fonte = Path(o.fonte) if o.fonte else Path(edl["fonte"])
    if not fonte.is_file():
        alt = edl_f.resolve().parent.parent / edl["fonte"]
        if alt.is_file():
            fonte = alt
    if not fonte.is_file():
        raise C.Erro(f"não achei o bruto: {edl['fonte']}", "Passe o caminho com --fonte.", 2)

    f = C.ficha(fonte)
    cortes = edl["cortes"]
    saida_dir = Path(o.saida)
    saida_dir.mkdir(parents=True, exist_ok=True)
    base = o.nome or (fonte.stem + "_decupado.mp4")
    saida = saida_dir / base
    wav = saida_dir / (Path(base).stem + "_audio.wav")

    dur = render_audio(fonte, cortes, wav, f)
    if o.so_audio:
        print(f"{wav} · {C.mmss(dur)}")
        return 0

    quadros = cortes_em_quadros(cortes, f["fps"])
    nq = sum(b - a for a, b in quadros)
    chaves = C.keyframes(fonte)
    pode_copiar, fora = cai_em_chave(cortes, chaves, f["fps"])
    modo = o.modo
    if modo == "auto":
        modo = "copia" if pode_copiar else "preciso"
    if modo == "copia" and not pode_copiar:
        print(f"aviso: {len(fora)} entrada(s) não caem em quadro-chave ({fora[:5]}); "
              f"com -c copy elas pulariam para o quadro-chave anterior. Use --modo preciso.", file=sys.stderr)

    codificador, args_q = (None, [])
    trabalho = Path(tempfile.mkdtemp(prefix="decupagem_"))
    try:
        if modo == "copia":
            render_copia(fonte, quadros, f, wav, saida, trabalho)
        else:
            codificador, args_q = escolher_codificador(f, o.crf, o.preset)
            render_preciso(fonte, quadros, f, wav, saida, codificador, args_q, nq)
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    fs = C.ficha(saida)
    C.gravar_json(saida_dir / "render.json", {
        "fonte": str(fonte), "edl": str(edl_f), "arquivo": str(saida), "audio_wav": str(wav),
        "modo": modo, "codificador": codificador, "qualidade": args_q,
        "quadros_esperados": nq, "duracao_esperada_s": round(nq / f["fps"], 3),
        "pontos_fora_de_quadro_chave": fora if modo == "preciso" else [],
        "bruto": f, "saida": fs})
    print(f"{saida} · modo {modo}" + (f" ({codificador})" if codificador else "") +
          f" · {len(cortes)} trecho(s), {nq} quadros ({C.mmss(nq / f['fps'])})")
    print(f"  bruto : {f['codec']} {f['largura']}x{f['altura']} {f['fps_fracao']} {f['pix_fmt']} "
          f"{(f['taxa_video'] or 0) // 1000} kbps")
    print(f"  saída : {fs['codec']} {fs['largura']}x{fs['altura']} {fs['fps_fracao']} {fs['pix_fmt']} "
          f"{(fs['taxa_video'] or 0) // 1000} kbps · {fs['quadros'] or '?'} quadros")
    if (fs["quadros"] or nq) != nq:
        print(f"  ATENÇÃO: saíram {fs['quadros']} quadros, esperava {nq}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except C.Erro as e:
        sys.exit(C.sair_com_erro(e))
    except subprocess.CalledProcessError as e:
        sys.exit(C.sair_com_erro(C.Erro(str(e))))
