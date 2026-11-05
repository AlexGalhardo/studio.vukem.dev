#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa.py — confere o render CONTRA O BRUTO, em quadro e em som. É o verificador que não acredita no render.

Uso:
  qa.py render/x_decupado.mp4 --edl cortes/edl.json [--fonte bruto/x.mp4] [--saida qa/] [--sem-imagem]

O que mede:
  1. especificação  ffprobe do bruto × da saída (codec, tamanho, fps, pix_fmt, cor) e nº de quadros × esperado
  2. quadro a quadro PSNR e SSIM da saída contra OS MESMOS quadros do bruto (média e mínimo; um quadro trocado
                     derruba o mínimo). PSNR acima de 45 dB e SSIM acima de 0,99 = visualmente idêntico
  3. som            correlação cruzada entre o áudio da saída e a montagem feita a partir do bruto → atraso em ms
  4. junções        o último quadro antes e o primeiro depois de cada emenda, lado a lado em qa/juncoes/, com o
                     salto visual e a energia das duas pontas (é aqui que se vê corte no meio da palavra)

Sai: qa/relatorio.md, qa/relatorio.json e qa/juncoes/*.jpg
Códigos: 0 passou · 1 reprovou (a lista diz o quê) · 2 falta insumo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum as C  # noqa: E402
from render import cortes_em_quadros, grafo_select  # noqa: E402

MIN_PSNR = 45.0
MIN_SSIM = 0.985
MAX_ATRASO_MS = 20.0
MAX_SALTO = 12.0     # diferença média de luz entre os dois quadros da emenda (0 = idênticos)


def ffprobe_fluxo(midia, tipo):
    d = json.loads(C.rodar([C.programa("ffprobe"), "-v", "error", "-show_streams", "-of", "json", str(midia)],
                           captura=True, trava=False).decode("utf-8", "replace"))
    return next((s for s in d["streams"] if s.get("codec_type") == tipo), {})


def fidelidade(saida, fonte, quadros, fps_fracao, trabalho):
    """PSNR e SSIM da saída contra os mesmos quadros do bruto."""
    import numpy as np
    psnr_log, ssim_log = trabalho / "psnr.log", trabalho / "ssim.log"
    num = int((fps_fracao or "30/1").split("/")[0])
    den = int((fps_fracao or "30/1").split("/")[1] if "/" in (fps_fracao or "") else 1)
    fc = (grafo_select(quadros, "1:v", "ref", fps_fracao) +
          f";[0:v]settb=1/{num},setpts=N*{den},split[d1][d2];[ref]split[r1][r2];"
          f"[d1][r1]psnr=stats_file={psnr_log.as_posix()};"
          f"[d2][r2]ssim=stats_file={ssim_log.as_posix()}")
    C.rodar([C.programa("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-i", str(saida), "-i", str(fonte),
             "-filter_complex", fc, "-f", "null", "-"])
    ps = [99.0 if m.group(1) == "inf" else float(m.group(1))
          for m in re.finditer(r"psnr_avg:(\S+)", psnr_log.read_text(encoding="utf-8", errors="replace"))]
    ss = [float(m.group(1)) for m in re.finditer(r"All:(\S+)", ssim_log.read_text(encoding="utf-8", errors="replace"))]
    if not ps or not ss:
        raise C.Erro("o ffmpeg não devolveu PSNR/SSIM (os dois arquivos têm o mesmo tamanho de quadro?).")
    ps, ss = np.array(ps), np.array(ss)
    return {"quadros_comparados": len(ps), "psnr_media": round(float(ps.mean()), 2),
            "psnr_minimo": round(float(ps.min()), 2), "psnr_pior_quadro": int(ps.argmin()),
            "ssim_media": round(float(ss.mean()), 5), "ssim_minimo": round(float(ss.min()), 5),
            "ssim_pior_quadro": int(ss.argmin())}


def sincronia(saida, fonte, cortes):
    """Atraso entre o áudio da saída e a montagem de referência, por correlação cruzada no meio do vídeo."""
    import numpy as np
    ref = C.montar_audio(C.pcm(fonte, canais=1), cortes, sr=C.SR)[:, 0]
    bruto = C.rodar([C.programa("ffmpeg"), "-v", "error", "-i", str(saida), "-vn", "-ac", "1",
                     "-ar", str(C.SR), "-f", "f32le", "-"], captura=True)
    y = np.frombuffer(bruto, np.float32)
    n = min(len(y), len(ref))
    if n < C.SR:
        raise C.Erro("áudio curto demais para medir sincronia.")
    meio, janela = n // 2, min(C.SR * 4, n // 2)
    a, b = y[meio - janela:meio + janela], ref[meio - janela:meio + janela]
    L = 2 * janela
    c = np.fft.irfft(np.fft.rfft(a, 2 * L) * np.conj(np.fft.rfft(b, 2 * L)))
    atraso = int(np.argmax(np.abs(c)))
    if atraso > L:
        atraso -= 2 * L
    return {"duracao_saida_s": round(len(y) / C.SR, 3), "duracao_montagem_s": round(len(ref) / C.SR, 3),
            "atraso_ms": round(atraso * 1000.0 / C.SR, 2),
            "rms_saida_dbfs": round(float(20 * np.log10(np.sqrt((y[:n] ** 2).mean()) + 1e-12)), 1),
            "rms_montagem_dbfs": round(float(20 * np.log10(np.sqrt((ref[:n] ** 2).mean()) + 1e-12)), 1)}


def quadros_jpg(midia, indices, pasta, altura=360):
    """Tira num passo só os quadros pedidos (por índice) e devolve {índice: caminho}."""
    if not indices:
        return {}
    pasta.mkdir(parents=True, exist_ok=True)
    sel = "+".join(f"eq(n\\,{k})" for k in sorted(set(indices)))
    C.rodar([C.programa("ffmpeg"), "-v", "error", "-y", "-i", str(midia), "-vf",
             f"select='{sel}',scale=-2:{altura}", "-vsync", "0", "-q:v", "3",
             str(pasta / "q%04d.jpg")])
    arquivos = sorted(pasta.glob("q*.jpg"))
    return dict(zip(sorted(set(indices)), arquivos))


def juncoes(fonte, cortes, fps, pasta, db, lim, blocos=None):
    """Imagem lado a lado de cada emenda + salto visual + energia nas duas pontas.

    Com `blocos` (as palavras cronometradas) quem manda é a BORDA DA PALAVRA: só é defeito o corte que cai
    DENTRO de uma palavra. Sem as palavras sobra a energia, que acusa qualquer corte em fala contínua — e
    corte de retomada é sempre em fala contínua, então ali ela grita à toa."""
    from PIL import Image, ImageDraw
    import numpy as np
    pasta.mkdir(parents=True, exist_ok=True)
    g = C.Grade(fps)
    pares = [(int(round(cortes[i]["src1"] * fps)) - 1, g.quadro(cortes[i + 1]["src0"] + 1e-9))
             for i in range(len(cortes) - 1)]
    tmp = pasta / "_quadros"
    mapa = quadros_jpg(fonte, [k for p in pares for k in p], tmp)
    saida = []
    for i, (ko, ki) in enumerate(pares):
        ia, ib = mapa.get(ko), mapa.get(ki)
        linha = {"juncao": f"J{i:02d}", "sai_s": round(cortes[i]["src1"], 3),
                 "entra_s": round(cortes[i + 1]["src0"], 3),
                 "db_saida": round(C.db_em(db, cortes[i]["src1"], C.CRUZADO), 1),
                 "db_entrada": round(C.db_em(db, cortes[i + 1]["src0"], C.CRUZADO), 1)}
        if ia and ib and ia.exists() and ib.exists():
            a, b = Image.open(ia).convert("RGB"), Image.open(ib).convert("RGB")
            ga = np.asarray(a.convert("L").resize((160, 90)), np.float32)
            gb = np.asarray(b.convert("L").resize((160, 90)), np.float32)
            linha["salto_visual"] = round(float(np.abs(ga - gb).mean()), 1)
            folha = Image.new("RGB", (a.width + b.width + 8, a.height + 22), (200, 30, 30))
            folha.paste(a, (0, 22))
            folha.paste(b, (a.width + 8, 22))
            d = ImageDraw.Draw(folha)
            d.rectangle([0, 0, folha.width, 21], fill=(0, 0, 0))
            d.text((6, 6), f"J{i:02d}  SAI q{ko} ({ko / fps:.3f}s)", fill=(255, 255, 255))
            d.text((a.width + 14, 6), f"ENTRA q{ki} ({ki / fps:.3f}s)  salto {linha['salto_visual']}",
                   fill=(255, 255, 255))
            arq = pasta / f"J{i:02d}.jpg"
            folha.save(arq, quality=86)
            linha["imagem"] = str(arq)
        linha["risco"] = []
        if blocos:
            linha["folga_saida_ms"] = round(1000 * C.folga_palavra(cortes[i]["src1"], blocos, fps), 1)
            linha["folga_entrada_ms"] = round(1000 * C.folga_palavra(cortes[i + 1]["src0"], blocos, fps), 1)
            if linha["folga_saida_ms"] < 0:
                linha["risco"].append(f"SAI DENTRO DA PALAVRA ({linha['folga_saida_ms']} ms)")
            if linha["folga_entrada_ms"] < 0:
                linha["risco"].append(f"ENTRA DENTRO DA PALAVRA ({linha['folga_entrada_ms']} ms)")
        else:
            if linha["db_saida"] > lim:
                linha["risco"].append("sai dentro de fala")
            if linha["db_entrada"] > lim:
                linha["risco"].append("entra dentro de fala")
        if linha.get("salto_visual", 0) > MAX_SALTO:
            linha["risco"].append("salto visual grande")
        saida.append(linha)
    for f in tmp.glob("*.jpg"):
        f.unlink()
    tmp.rmdir()
    return saida


def main():
    ap = argparse.ArgumentParser(description="Confere o render contra o bruto.")
    ap.add_argument("render")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--fonte")
    ap.add_argument("--saida", default="qa")
    ap.add_argument("--palavras", help="transcricao/palavras.json: com ele a conferência das junções usa a "
                                       "borda da palavra em vez da energia (menos alarme falso)")
    ap.add_argument("--sem-imagem", action="store_true", help="pula PSNR/SSIM e as imagens das junções")
    o = ap.parse_args()

    edl_f, saida_f = Path(o.edl), Path(o.render)
    if not saida_f.is_file():
        raise C.Erro(f"render não encontrado: {saida_f}", "Rode antes o render.py.", 2)
    edl = C.ler_edl(edl_f)
    fonte = Path(o.fonte) if o.fonte else Path(edl["fonte"])
    if not fonte.is_file():
        alt = edl_f.resolve().parent.parent / edl["fonte"]
        fonte = alt if alt.is_file() else fonte
    if not fonte.is_file():
        raise C.Erro(f"não achei o bruto: {edl['fonte']}", "Passe o caminho com --fonte.", 2)

    f, fs = C.ficha(fonte), C.ficha(saida_f)
    cortes = edl["cortes"]
    quadros = cortes_em_quadros(cortes, f["fps"])
    nq = sum(b - a for a, b in quadros)
    pasta = Path(o.saida)
    pasta.mkdir(parents=True, exist_ok=True)

    db = C.energia_db(C.pcm(fonte, canais=1))
    lim = C.limiar_fala(db)
    rel = {"bruto": str(fonte), "render": str(saida_f), "edl": str(edl_f),
           "quadros_esperados": nq, "duracao_esperada_s": round(nq / f["fps"], 3), "reprovacoes": []}
    rel["especificacao"] = {k: {"bruto": f.get(k), "saida": fs.get(k)} for k in
                            ("codec", "perfil", "largura", "altura", "fps_fracao", "pix_fmt", "faixa",
                             "espaco", "primarias", "transferencia", "taxa_video")}
    rel["especificacao"]["quadros"] = {"bruto": f.get("quadros"), "saida": fs.get("quadros")}
    rel["audio"] = {"bruto": f.get("audio"), "saida": fs.get("audio")}

    for k in ("largura", "altura", "pix_fmt", "fps_fracao"):
        if f.get(k) != fs.get(k):
            rel["reprovacoes"].append(f"{k}: bruto {f.get(k)} × saída {fs.get(k)}")
    if fs.get("quadros") and abs(fs["quadros"] - nq) > 1:
        rel["reprovacoes"].append(f"quadros: esperava {nq}, saíram {fs['quadros']}")

    trabalho = Path(tempfile.mkdtemp(prefix="qa_decupagem_"))
    try:
        if not o.sem_imagem:
            rel["fidelidade"] = fidelidade(saida_f, fonte, quadros, f["fps_fracao"], trabalho)
            if rel["fidelidade"]["psnr_minimo"] < MIN_PSNR:
                rel["reprovacoes"].append(f"PSNR mínimo {rel['fidelidade']['psnr_minimo']} dB "
                                          f"(abaixo de {MIN_PSNR}: quadro trocado ou perda visível)")
            if rel["fidelidade"]["ssim_minimo"] < MIN_SSIM:
                rel["reprovacoes"].append(f"SSIM mínimo {rel['fidelidade']['ssim_minimo']} (abaixo de {MIN_SSIM})")
        rel["sincronia"] = sincronia(saida_f, fonte, cortes)
        if abs(rel["sincronia"]["atraso_ms"]) > MAX_ATRASO_MS:
            rel["reprovacoes"].append(f"áudio deslocado {rel['sincronia']['atraso_ms']} ms")
        blocos = C.blocos_de_palavras(C.ler_palavras(o.palavras)) if o.palavras else None
        rel["juncoes"] = (juncoes(fonte, cortes, f["fps"], pasta / "juncoes", db, lim, blocos)
                          if not o.sem_imagem else [])
    finally:
        for p in sorted(trabalho.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        trabalho.rmdir()

    arriscadas = [j for j in rel["juncoes"] if j["risco"]]
    if arriscadas:
        rel["reprovacoes"].append(f"{len(arriscadas)} junção(ões) com risco: "
                                  + "; ".join(f"{j['juncao']} ({', '.join(j['risco'])})" for j in arriscadas[:6]))

    L = [f"# QA da decupagem — {saida_f.name}", "",
         ("**REPROVADO**" if rel["reprovacoes"] else "**PASSOU**") +
         f" · {nq} quadros esperados ({C.mmss(nq / f['fps'])}) · limiar de fala {lim:.1f} dBFS", ""]
    if rel["reprovacoes"]:
        L += ["## O que reprovou", ""] + [f"- {r}" for r in rel["reprovacoes"]] + [""]
    L += ["## Especificação", "", "| campo | bruto | saída |", "|---|---|---|"]
    for k, v in rel["especificacao"].items():
        L.append(f"| {k} | {v['bruto']} | {v['saida']} |")
    if "fidelidade" in rel:
        d = rel["fidelidade"]
        L += ["", "## Fidelidade do quadro (saída × os mesmos quadros do bruto)", "",
              f"{d['quadros_comparados']} quadros comparados · PSNR média {d['psnr_media']} dB, "
              f"mínimo {d['psnr_minimo']} dB (quadro {d['psnr_pior_quadro']}) · "
              f"SSIM média {d['ssim_media']}, mínimo {d['ssim_minimo']} (quadro {d['ssim_pior_quadro']})"]
    d = rel["sincronia"]
    L += ["", "## Som", "",
          f"saída {d['duracao_saida_s']} s × montagem {d['duracao_montagem_s']} s · "
          f"atraso no meio do vídeo {d['atraso_ms']} ms (positivo = áudio atrasado) · "
          f"RMS {d['rms_saida_dbfs']} × {d['rms_montagem_dbfs']} dBFS"]
    if rel["juncoes"]:
        L += ["", "## Junções", "", "| junção | sai | dB | folga | entra | dB | folga | salto | risco | imagem |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for j in rel["juncoes"]:
            fs = f"{j['folga_saida_ms']} ms" if "folga_saida_ms" in j else "-"
            fe = f"{j['folga_entrada_ms']} ms" if "folga_entrada_ms" in j else "-"
            L.append(f"| {j['juncao']} | {C.mmss(j['sai_s'])} | {j['db_saida']} | {fs} "
                     f"| {C.mmss(j['entra_s'])} | {j['db_entrada']} | {fe} "
                     f"| {j.get('salto_visual', '-')} | {', '.join(j['risco']) or 'ok'} "
                     f"| {Path(j.get('imagem', '')).name} |")
        if any("folga_saida_ms" in j for j in rel["juncoes"]):
            L += ["", "folga = distância do corte até a borda da palavra mais perto (0 = em cima da borda; "
                  "negativo = corte dentro da palavra, defeito)."]
    C.gravar_texto(pasta / "relatorio.md", "\n".join(L))
    C.gravar_json(pasta / "relatorio.json", rel)

    print(("REPROVADO" if rel["reprovacoes"] else "PASSOU") + f" · {pasta / 'relatorio.md'}")
    for r in rel["reprovacoes"]:
        print(f"  ✗ {r}")
    if "fidelidade" in rel:
        d = rel["fidelidade"]
        print(f"  PSNR {d['psnr_media']} dB (mín {d['psnr_minimo']}) · SSIM {d['ssim_media']} (mín {d['ssim_minimo']})")
    print(f"  atraso do áudio {rel['sincronia']['atraso_ms']} ms")
    return 1 if rel["reprovacoes"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except C.Erro as e:
        sys.exit(C.sair_com_erro(e))
