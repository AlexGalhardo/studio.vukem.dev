#!/usr/bin/env python3
"""mixar.py: mixagem final — voz na frente, trilha com ducking, efeitos — a −14 LUFS / −1 dBTP, com stems.

A ordem é sempre esta:

1. VOZ. Corte de graves em 70 Hz, −2 dB no abafado (250 Hz), +1,5 dB de presença (3,5 kHz), +1,2 dB de ar
   (5,2 kHz), de-esser e um limiter leve. A MESMA voz tratada vira a chave do ducking: a música abaixa
   exatamente quando ele fala, não quando o medidor acha que sim.
2. EFEITOS. Entram a 0 dB: o som/efeitos.wav da skill video-efeitos-sonoros já sai calibrado contra a sua voz.
3. TRILHA. Entra em laço a partir de `--inicio-trilha` (útil quando você mixa um trecho de um vídeo longo e
   quer a música coerente com o resto), com ganho automático para ficar cerca de 20 dB abaixo da fala
   DURANTE a fala, e ducking por sidechain para abrir nos vãos. Use a versão "cama". O sidechain
   tira cerca de 8,6 dB enquanto ele fala; o que o --diagnostico mede é a música SUBINDO nos vãos,
   e esse número é menor (~6 dB numa fala corrida), porque o release de 450 ms não abre por
   completo em vão curto. Abaixo de 3 dB, a música não está abrindo.
4. SOMA. amix sem normalizar, limiter de barramento (teto inicial de −1,7 dBFS, que desce sozinho se o
   pico real do arquivo passar do alvo) e loudnorm medindo e aplicando com linear=true: ganho
   estático, que preserva a mixagem em vez de comprimi-la.

Uso:
  python3 mixar.py som/voz.wav --trilha som/trilha_cama.wav --efeitos som/efeitos.wav --saida som/mix_final.wav
  python3 mixar.py som/voz.wav --trilha som/trilha_cama.wav --stems som/stems/ --diagnostico --ajustar
  python3 mixar.py som/voz.wav --alvo -16 --tp -1.5 --saida som/mix_curto.wav     (peça curta)

--diagnostico mede a música contra a voz: quantos dB ela fica abaixo da fala e quantos o sidechain tira.
--ajustar usa essa medida para corrigir o ganho da música e mixar de novo (uma vez).
--stems grava voz.wav, efeitos.wav, musica.wav e mix.wav com o MESMO ganho da mix, de modo que a soma dos
três dá a mix (a menos do limiter de barramento, medido e informado). É o que vai para o XML do editor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio import (ALVO_LUFS, ALVO_TP, SR, db, ebur128, faltou, ffmpeg, gravar, info_wav, ler,  # noqa: E402
                   para_wav, rms_fala)

# LRA é o ALVO de faixa dinâmica do loudnorm, não um teto de segurança: quando o material tem LRA maior
# que este número, o ffmpeg RECUSA o modo linear e comprime a mixagem para caber. Fica no máximo que ele
# aceita, de propósito — quem controla a dinâmica aqui é a cadeia de voz e o limiter de barramento.
LRA_ALVO = 20.0
MUSICA_ABAIXO_DA_FALA = 20.0     # dB abaixo da fala, durante a fala: música presente, voz na frente
DUCK_ESPERADO = 8.6              # o que o sidechain costuma tirar durante a fala (medido)
CORRECAO_ESTIMADOR = 2.1         # a estimativa global fica ~2 dB abaixo da medida por janela de fala
TETO_BUS_DB = -1.7               # teto do limiter de barramento, em dBFS (desce sozinho se o pico real passar)
BLOCO = 30 * SR

CADEIA_VOZ = ("highpass=f=70,"
              "equalizer=f=250:t=q:w=1.4:g=-2,"
              "equalizer=f=3500:t=q:w=1.2:g=1.5,"
              "equalizer=f=5200:t=q:w=1.4:g=1.2,"
              "deesser=i=0.35:m=0.5:f=0.5,"
              "alimiter=limit=0.92:level=disabled:latency=1")
DUCKING = "sidechaincompress=threshold=0.03:ratio=4:attack=20:release=450:makeup=1"
FORMATO = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"


# ───────────────────────────────────────────────────────── utilidades ──
def preparar_wav(caminho, trabalho):
    """Devolve um WAV 48 kHz PCM 16-bit do material (converte se precisar)."""
    caminho = Path(caminho)
    sr, _ch, sw, _n = (0, 0, 0, 0)
    try:
        sr, _ch, sw, _n = info_wav(caminho)
    except Exception:
        pass
    if sr == SR and sw == 2:
        return caminho
    return para_wav(caminho, Path(trabalho) / f"_{caminho.stem}_48k.wav")


def regravar(origem, destino, n, ganho=1.0):
    """Copia WAV para WAV 16-bit estéreo 48 kHz com exatamente `n` amostras (corta ou completa com
    silêncio) e um ganho linear opcional, em blocos."""
    origem, destino = Path(origem), Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f"{destino.stem}.parcial2{destino.suffix}")
    _sr, ch, _sw, n_orig = info_wav(origem)
    with wave.open(str(origem), "rb") as r, wave.open(str(tmp), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        feito = 0
        while feito < n:
            k = min(BLOCO, n - feito)
            if feito < n_orig:
                x = np.frombuffer(r.readframes(min(k, n_orig - feito)), dtype="<i2").reshape(-1, ch)
                x = np.repeat(x, 2, axis=1) if ch == 1 else x[:, :2]
            else:
                x = np.zeros((0, 2), dtype="<i2")
            if len(x) < k:
                x = np.concatenate([x, np.zeros((k - len(x), 2), dtype="<i2")])
            if ganho != 1.0:
                x = np.clip(np.round(x.astype(np.float64) * ganho), -32768, 32767).astype("<i2")
            w.writeframes(x.astype("<i2").tobytes())
            feito += k
    os.replace(tmp, destino)


def json_loudnorm(stderr):
    ini, fim = stderr.rfind("{"), stderr.rfind("}")
    if ini < 0 or fim < ini:
        raise RuntimeError("loudnorm não devolveu o JSON de medida:\n" + stderr[-800:])
    return json.loads(stderr[ini:fim + 1])


def rms_arquivo(caminho):
    soma, total = 0.0, 0
    with wave.open(str(caminho), "rb") as r:
        ch, n = r.getnchannels(), r.getnframes()
        while total < n:
            x = np.frombuffer(r.readframes(min(BLOCO, n - total)), dtype="<i2").astype(np.float64) / 32768
            soma += float(np.sum(x ** 2))
            total += len(x) // ch
    return db(np.sqrt(soma / max(total * ch, 1)))


def voz_x_musica(voz_wav, mus_wav):
    """Relação voz/música em janelas de FALA (env > 0,02) e de VÃO (env < 0,005), janelas de 100 ms.
    É a prova do ducking: `ducking_db` é quanto a música sobe nos vãos em relação à fala."""
    v = ler(voz_wav).mean(axis=1)
    m = ler(mus_wav).mean(axis=1)
    n = min(len(v), len(m)) // 4800 * 4800
    ev = np.sqrt(np.mean(v[:n].reshape(-1, 4800) ** 2, axis=1))
    em = np.sqrt(np.mean(m[:n].reshape(-1, 4800) ** 2, axis=1))
    fala, vao = ev > 0.02, ev < 0.005
    out = {"janelas_fala": int(fala.sum()), "janelas_vao": int(vao.sum())}
    if fala.any():
        out["musica_abaixo_da_fala_db"] = round(db(np.sqrt(np.mean(ev[fala] ** 2)))
                                                - db(np.sqrt(np.mean(em[fala] ** 2))), 1)
        out["musica_rms_na_fala_dbfs"] = round(db(np.sqrt(np.mean(em[fala] ** 2))), 1)
    if fala.any() and vao.any():
        out["musica_rms_no_vao_dbfs"] = round(db(np.sqrt(np.mean(em[vao] ** 2))), 1)
        out["ducking_db"] = round(out["musica_rms_no_vao_dbfs"] - out["musica_rms_na_fala_dbfs"], 1)
    return out


def comparar_stems(pasta, janela=0.4):
    """voz + efeitos + musica contra mix, em blocos: diferença de nível, resto, pior janela e saturação."""
    arqs = [Path(pasta) / f"{k}.wav" for k in ("voz", "efeitos", "musica", "mix")]
    n = min(info_wav(a)[3] for a in arqs)
    nj = int(janela * SR)
    s_mm = s_ss = s_ms = s_dd = 0.0
    pico_d = pico_m = 0.0
    jan = []
    clip = {a.stem: 0 for a in arqs[:3]}
    leitores = [wave.open(str(a), "rb") for a in arqs]
    try:
        feito = 0
        while feito < n:
            k = min(BLOCO, n - feito)
            k -= k % nj if k > nj else 0
            blocos = []
            for a, r in zip(arqs, leitores):
                x = np.frombuffer(r.readframes(k), dtype="<i2").reshape(-1, 2)
                if a.stem in clip:
                    clip[a.stem] += int(np.count_nonzero((x == 32767) | (x == -32768)))
                blocos.append(x.astype(np.float64) / 32768)
            s, mix = blocos[0] + blocos[1] + blocos[2], blocos[3]
            d = s - mix
            s_mm += float(np.sum(mix ** 2))
            s_ss += float(np.sum(s ** 2))
            s_ms += float(np.sum(mix * s))
            s_dd += float(np.sum(d ** 2))
            pico_d = max(pico_d, float(np.max(np.abs(d))))
            pico_m = max(pico_m, float(np.max(np.abs(mix))))
            m = len(mix) // nj
            if m:
                rm = np.sqrt(np.mean(mix[:m * nj].reshape(m, nj, 2) ** 2, axis=(1, 2)))
                rs = np.sqrt(np.mean(s[:m * nj].reshape(m, nj, 2) ** 2, axis=(1, 2)))
                ok = rm > 10 ** (-50 / 20)
                jan += list(20 * np.log10(rs[ok] / rm[ok]))
            feito += k
    finally:
        for r in leitores:
            r.close()
    j = np.abs(np.array(jan)) if jan else np.zeros(1)
    return {"diferenca_de_nivel_db": round(10 * np.log10(s_ss / max(s_mm, 1e-20)), 3),
            "ajuste_de_ganho_db": round(20 * np.log10(max(s_ms, 1e-20) / max(s_ss, 1e-20)), 3),
            "resto_rms_db": round(10 * np.log10(s_dd / max(s_mm, 1e-20) + 1e-20), 1),
            "resto_pico_dbfs": round(db(pico_d), 1), "mix_pico_dbfs": round(db(pico_m), 1),
            "pior_janela_400ms_db": round(float(j.max()), 3),
            "janelas_acima_0_1db": int(np.count_nonzero(j > 0.1)), "janelas_com_sinal": int(len(jan)),
            "amostras_saturadas": clip}


# ───────────────────────────────────────────────────────────── grafo ──
def grafo(dur, ganho_trilha_db, ini_trilha, com_trilha, pre_db, loudnorm, diag=False, stems_db=None,
          teto_bus_db=TETO_BUS_DB):
    g = [f"[0:a]{FORMATO},{CADEIA_VOZ}[voz]"]
    if com_trilha:
        g += ["[voz]asplit=2[v_out][v_key]",
              f"[1:a]{FORMATO},atrim=start={ini_trilha:.6f}:duration={dur:.6f},asetpts=PTS-STARTPTS,"
              f"volume={ganho_trilha_db:.3f}dB[m0]",
              f"[m0][v_key]{DUCKING}[mus]", f"[2:a]{FORMATO}[sfx]"]
        barras = {"v": "v_out", "m": "mus", "s": "sfx"}
    else:
        g += ["[voz]anull[v_out]", f"[1:a]{FORMATO}[sfx]"]
        barras = {"v": "v_out", "s": "sfx"}
    na_mix = {}
    for b, rot in barras.items():
        usos = ["mix"] + (["diag"] if diag and b in ("v", "m") else []) + (["st"] if stems_db is not None else [])
        if len(usos) == 1:
            na_mix[b] = rot
            continue
        g.append(f"[{rot}]asplit={len(usos)}" + "".join(f"[{b}_{u}]" for u in usos))
        na_mix[b] = f"{b}_mix"
        if stems_db is not None:
            nome = {"v": "st_voz", "m": "st_mus", "s": "st_sfx"}[b]
            g.append(f"[{b}_st]volume={stems_db:.6f}dB[{nome}]")
    entradas = "".join(f"[{na_mix[b]}]" for b in barras)
    limite = 10 ** (teto_bus_db / 20)
    g.append(f"{entradas}amix=inputs={len(barras)}:duration=first:normalize=0,volume={pre_db:.3f}dB,"
             f"alimiter=limit={limite:.5f}:level=disabled:latency=1,{loudnorm},aresample={SR}[out]")
    return ";".join(g)


def _ln_medir(alvo, tp):
    return f"loudnorm=I={alvo}:TP={tp}:LRA={LRA_ALVO}:print_format=json"


def _ln_aplicar(m, alvo, tp):
    return (f"loudnorm=I={alvo}:TP={tp}:LRA={LRA_ALVO}:linear=true:print_format=json:"
            f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
            f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}")


# ───────────────────────────────────────────────────────────── mixar ──
def mixar(voz, saida, trilha=None, efeitos=None, inicio_trilha=0.0, trilha_db=0.0, alvo=ALVO_LUFS,
          tp=ALVO_TP, stems=None, diagnostico=False, trabalho=None):
    """Mixa e grava `saida` (WAV 48 kHz estéreo 16-bit). Devolve o relatório com as medidas."""
    saida = Path(saida)
    trabalho = Path(trabalho) if trabalho else saida.parent / "_trabalho"
    trabalho.mkdir(parents=True, exist_ok=True)
    voz_wav = preparar_wav(voz, trabalho)
    _sr, _ch, _sw, n_voz = info_wav(voz_wav)
    dur = n_voz / SR
    sufixo = hashlib.md5(str(saida.resolve()).encode()).hexdigest()[:6]
    base = f"_{saida.stem}_{sufixo}"
    rel = {"voz": str(voz), "saida": str(saida), "duracao_s": round(dur, 3),
           "alvo_lufs": alvo, "alvo_pico_real_dbtp": tp}

    fala = rms_fala(voz_wav)
    rel["fala_rms_entrada_dbfs"] = round(fala, 2)

    # barramento de efeitos do tamanho exato da voz
    sfx_wav = trabalho / f"{base}_sfx.wav"
    if efeitos:
        regravar(preparar_wav(efeitos, trabalho), sfx_wav, n_voz)
        rel["efeitos"] = str(efeitos)
    else:
        gravar(sfx_wav, np.zeros((n_voz, 2), dtype=np.float32))
        rel["efeitos"] = None

    com_trilha = trilha is not None
    ganho_trilha = ini_trilha = 0.0
    entradas = ["-i", voz_wav]
    if com_trilha:
        trilha_w = preparar_wav(trilha, trabalho)
        sr_t, _c, _s, n_t = info_wav(trilha_w)
        ini_trilha = float(inicio_trilha) % (n_t / sr_t)
        alvo_pre_duck = fala - (MUSICA_ABAIXO_DA_FALA - DUCK_ESPERADO) + CORRECAO_ESTIMADOR
        ganho_trilha = alvo_pre_duck - rms_arquivo(trilha_w) + float(trilha_db)
        entradas += ["-stream_loop", "-1", "-i", trilha_w]
        rel["trilha"] = {"arquivo": str(trilha), "inicio_s": round(ini_trilha, 3),
                         "ganho_db": round(ganho_trilha, 2), "ajuste_pedido_db": round(float(trilha_db), 2),
                         "alvo_abaixo_da_fala_db": MUSICA_ABAIXO_DA_FALA}
    entradas += ["-i", sfx_wav]

    st_brutos, teto = {}, TETO_BUS_DB

    def passada(pre_db, loudnorm, dest=None, diag=False, stems_db=None):
        g = grafo(dur, ganho_trilha, ini_trilha, com_trilha, pre_db, loudnorm, diag, stems_db, teto)
        args = ["-v", "info", *entradas, "-filter_complex", g, "-map", "[out]"]
        tmp = None
        if dest is None:
            args += ["-f", "null", "-"]
        else:
            tmp = dest.with_name(f"{dest.stem}.parcial{dest.suffix}")
            args += ["-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", tmp]
        diag_arqs = {}
        if diag:
            diag_arqs["voz"] = trabalho / f"{base}_diag_voz.wav"
            args += ["-map", "[v_diag]", "-c:a", "pcm_s16le", diag_arqs["voz"]]
            if com_trilha:
                diag_arqs["musica"] = trabalho / f"{base}_diag_musica.wav"
                args += ["-map", "[m_diag]", "-c:a", "pcm_s16le", diag_arqs["musica"]]
        if stems_db is not None:
            for rot, arq in st_brutos.items():
                if rot != "st_mus" or com_trilha:
                    args += ["-map", f"[{rot}]", "-c:a", "pcm_s16le", arq]
        err = ffmpeg(*args, rotulo=f"mixar {saida.name}")
        if tmp is not None:
            os.replace(tmp, dest)
        return json_loudnorm(err), diag_arqs

    m1, diag_arqs = passada(0.0, _ln_medir(alvo, tp), diag=diagnostico)
    passadas = [{"etapa": "medida", "pre_db": 0.0, "input_i": m1["input_i"], "input_tp": m1["input_tp"],
                 "input_lra": m1.get("input_lra")}]
    # O loudnorm só fica no modo LINEAR — ganho estático, que preserva a mixagem e faz a soma dos stems
    # bater com a mix — quando o ganho que ainda falta cabe abaixo do pico alvo. Quando não cabe, o ganho
    # é adiantado ANTES do limiter de barramento e a soma é medida de novo. O limiter come parte desse
    # ganho, então uma passada só não resolve: repete até faltar pouco (no máximo 3 medidas).
    pre, medida = 0.0, m1
    for _ in range(3):
        falta = alvo - float(medida["input_i"])
        if abs(falta) < 0.05 or float(medida["input_tp"]) + falta <= tp - 0.2:
            break
        pre = round(pre + falta, 2)
        medida, _ = passada(pre, _ln_medir(alvo, tp))
        passadas.append({"etapa": "medida com ganho", "pre_db": pre, "input_i": medida["input_i"],
                         "input_tp": medida["input_tp"], "input_lra": medida.get("input_lra")})

    saida.parent.mkdir(parents=True, exist_ok=True)
    ganho_stems = None
    if stems is not None:
        Path(stems).mkdir(parents=True, exist_ok=True)
        ganho_stems = pre + (alvo - float(medida["input_i"]))
        st_brutos = {"st_voz": trabalho / f"{base}_st_voz.wav", "st_mus": trabalho / f"{base}_st_mus.wav",
                     "st_sfx": trabalho / f"{base}_st_sfx.wav"}
    def aplicar():
        m, _ = passada(pre, _ln_aplicar(medida, alvo, tp), dest=saida, stems_db=ganho_stems)
        if info_wav(saida)[3] != n_voz:            # o loudnorm passa por 192 kHz e pode sobrar amostra
            regravar(saida, saida, n_voz)
        passadas.append({"etapa": "aplicação", "pre_db": pre, "teto_bus_dbfs": round(teto, 2),
                         "tipo": m.get("normalization_type"), "output_i": m.get("output_i"),
                         "output_tp": m.get("output_tp")})
        return m, ebur128(saida)

    m2, final = aplicar()
    # O loudnorm mede o pico real no seu próprio reamostrador e o arquivo gravado costuma sair alguns
    # décimos acima. Quando passa do alvo, o teto do limiter de barramento desce exatamente a sobra e a
    # aplicação é refeita uma vez: só os picos mudam, o loudness fica.
    if final["pico_real_dbtp"] > tp:
        teto -= (final["pico_real_dbtp"] - tp) + 0.1
        m2, final = aplicar()
    rel["passadas"] = passadas
    rel["teto_bus_dbfs"] = round(teto, 2)
    if m2.get("normalization_type") != "linear":
        print(f"AVISO: o loudnorm caiu no modo dinâmico e comprimiu a mixagem "
              f"(soma medida: {medida['input_i']} LUFS, pico {medida['input_tp']} dBTP, "
              f"LRA {medida.get('input_lra')} contra alvo {LRA_ALVO}).", file=sys.stderr)

    ganho_total = pre + float(m2["output_i"]) - float(m2["input_i"])
    rel["ganho_pos_soma_db"] = round(ganho_total, 2)
    rel["fala_rms_saida_estimada_dbfs"] = round(fala + ganho_total, 2)

    final["ok"] = bool(abs(final["lufs"] - alvo) <= 0.5 and final["pico_real_dbtp"] <= tp + 0.05)
    rel["final"] = final

    if diagnostico and "musica" in diag_arqs:
        rel["trilha"].update(voz_x_musica(diag_arqs["voz"], diag_arqs["musica"]))
        for a in diag_arqs.values():
            Path(a).unlink(missing_ok=True)

    if stems is not None:
        rel["stems"] = finalizar_stems(Path(stems), st_brutos, saida, n_voz, ganho_stems, com_trilha)
    return rel


def finalizar_stems(pasta, brutos, mix_wav, n, ganho_db, com_trilha):
    destino = {"st_voz": pasta / "voz.wav", "st_sfx": pasta / "efeitos.wav", "st_mus": pasta / "musica.wav"}
    for rot, arq in destino.items():
        if rot == "st_mus" and not com_trilha:
            gravar(arq, np.zeros((n, 2), dtype=np.float32))
        else:
            regravar(brutos[rot], arq, n)
            Path(brutos[rot]).unlink(missing_ok=True)
    regravar(mix_wav, pasta / "mix.wav", n)
    med = comparar_stems(pasta)
    ajuste = med["ajuste_de_ganho_db"]
    if abs(ajuste) > 0.02:                         # resto de ganho (arredondamento do loudnorm)
        for arq in destino.values():
            regravar(arq, arq, n, ganho=10 ** (ajuste / 20))
        med = {**comparar_stems(pasta), "ajuste_aplicado_db": round(ajuste, 3)}
    med["ganho_aplicado_db"] = round(ganho_db + med.get("ajuste_aplicado_db", 0.0), 3)
    med["arquivos"] = {k: str(pasta / f"{k}.wav") for k in ("voz", "efeitos", "musica", "mix")}
    return med


def main():
    ap = argparse.ArgumentParser(description="Mixagem final: voz + trilha com ducking + efeitos.")
    ap.add_argument("voz", help="WAV ou mídia com a fala")
    ap.add_argument("--trilha", help="WAV da trilha (use a versão cama); sem isso, mixa sem música")
    ap.add_argument("--efeitos", help="som/efeitos.wav da skill video-efeitos-sonoros")
    ap.add_argument("--saida", default="som/mix_final.wav")
    ap.add_argument("--inicio-trilha", type=float, default=0.0, help="segundo da trilha em que o trecho começa")
    ap.add_argument("--trilha-db", type=float, default=0.0, help="ajuste fino da música sobre o automático")
    ap.add_argument("--alvo", type=float, default=ALVO_LUFS, help="LUFS integrado (padrão −14, YouTube)")
    ap.add_argument("--tp", type=float, default=ALVO_TP, help="pico real em dBTP (padrão −1)")
    ap.add_argument("--stems", help="pasta para voz/efeitos/musica/mix do editor")
    ap.add_argument("--diagnostico", action="store_true", help="mede música × voz e prova o ducking")
    ap.add_argument("--ajustar", action="store_true", help="com --diagnostico: corrige a música e remixa")
    ap.add_argument("--relatorio", help="grava o relatório em JSON (padrão: ao lado da saída)")
    a = ap.parse_args()
    if not Path(a.voz).is_file():
        faltou(f"não achei a voz em {a.voz}.")
    if a.efeitos and not Path(a.efeitos).is_file():
        faltou(f"não achei os efeitos em {a.efeitos}.")

    rel = mixar(a.voz, a.saida, a.trilha, a.efeitos, a.inicio_trilha, a.trilha_db, a.alvo, a.tp,
                a.stems, a.diagnostico)
    if a.ajustar and a.trilha and rel.get("trilha", {}).get("musica_abaixo_da_fala_db") is not None:
        erro = rel["trilha"]["musica_abaixo_da_fala_db"] - MUSICA_ABAIXO_DA_FALA
        if abs(erro) > 0.7:
            print(f"ajustando a música em {erro:+.1f} dB e mixando de novo…")
            rel = mixar(a.voz, a.saida, a.trilha, a.efeitos, a.inicio_trilha, a.trilha_db + erro,
                        a.alvo, a.tp, a.stems, True)
            rel["trilha"]["ajuste_automatico_db"] = round(erro, 2)

    f = Path(a.relatorio) if a.relatorio else Path(a.saida).with_suffix(".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(rel, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texto, encoding="utf-8", newline="\n")
    fi = rel["final"]
    print(f"\n{a.saida}: {rel['duracao_s']:.1f} s · {fi['lufs']:.1f} LUFS · pico real {fi['pico_real_dbtp']:.1f} dBTP "
          f"· LRA {fi['lra']:.1f} · {'dentro do alvo' if fi['ok'] else 'FORA DO ALVO'}")
    if rel.get("trilha", {}).get("ducking_db") is not None:
        t = rel["trilha"]
        print(f"trilha: {t['musica_abaixo_da_fala_db']} dB abaixo da fala durante a fala; "
              f"o ducking abre {t['ducking_db']} dB nos vãos "
              f"(fala {t['musica_rms_na_fala_dbfs']} dBFS, vão {t['musica_rms_no_vao_dbfs']} dBFS)")
    if rel.get("stems"):
        s = rel["stems"]
        print(f"stems: soma − mix = {s['resto_rms_db']} dB RMS, pior janela {s['pior_janela_400ms_db']} dB")
    print(f"relatório: {f}")
    sys.exit(0 if fi["ok"] else 1)


if __name__ == "__main__":
    main()
