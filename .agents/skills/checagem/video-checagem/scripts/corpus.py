#!/usr/bin/env python3
"""corpus.py: o que a checagem tem para comparar — a ficha de fatos e os documentos.

Transforma `pesquisa/fatos.json` (contrato da skill video-pesquisa-ia) e os arquivos .md, .txt e .pdf numa
lista de PASSAGENS comparáveis:

    {"origem": "fatos" | "documento", "ref": "F003" | "relatorio.pdf:12", "titulo": …, "url": …,
     "texto": "…", "numeros": [...], "nomes": [...], "tokens": [...]}

Nada aqui julga nada: só lê, parte em frases e indexa.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comum as C  # noqa: E402

P = C.modulo_palavras()

EXTENSOES = (".md", ".txt", ".markdown", ".csv", ".json", ".pdf")

MULT = {"mil": 1e3, "milhao": 1e6, "milhoes": 1e6, "mi": 1e6, "bilhao": 1e9, "bilhoes": 1e9, "bi": 1e9,
        "trilhao": 1e12, "trilhoes": 1e12, "tri": 1e12}
EXTENSO = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
           "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
           "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
           "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
           "noventa": 90, "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
           "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800, "novecentos": 900,
           "meio": 0.5, "meia": 0.5, "metade": 0.5}
APROXIMA = ("cerca", "aproximadamente", "quase", "perto", "mais", "menos", "uns", "umas", "volta", "torno",
            "aproximado", "aproximada", "beirando", "girando")

RX_NUMERO = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")


def numeros_do_texto(texto):
    """[{"valor": float, "bruto": str, "tipo": str, "aproximado": bool, "posicao": int}] de um texto."""
    toks = re.findall(r"[^\W_]+(?:[.,][^\W_]+)*|%|R\$|US\$", texto, re.UNICODE)
    saida, i = [], 0
    while i < len(toks):
        t = toks[i]
        n = P.normalizar(t)
        valor = None
        if RX_NUMERO.fullmatch(t):
            valor = _para_float(t)
        elif n in EXTENSO:
            valor = float(EXTENSO[n])
        if valor is None:
            i += 1
            continue
        bruto, j = [t], i + 1
        while j < len(toks):
            m = P.normalizar(toks[j])
            if m in MULT:
                valor *= MULT[m]
                bruto.append(toks[j])
                j += 1
            elif m == "e" and j + 1 < len(toks) and P.normalizar(toks[j + 1]) in EXTENSO:
                valor += EXTENSO[P.normalizar(toks[j + 1])]
                bruto += [toks[j], toks[j + 1]]
                j += 2
            else:
                break
        volta = " ".join(P.normalizar(x) for x in toks[max(0, i - 4):i])
        frente = " ".join(P.normalizar(x) for x in toks[j:j + 3])
        saida.append({"valor": valor, "bruto": " ".join(bruto), "tipo": _tipo(volta, frente, t),
                      "aproximado": any(a in volta.split() for a in APROXIMA), "posicao": i})
        i = j
    return saida


def _para_float(t):
    t = t.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", t) else t
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _tipo(volta, frente, bruto):
    j = f" {volta} {frente} "
    if "%" in frente or "%" in bruto or " por cento " in j or " porcento " in j:
        return "percentual"
    if re.search(r"r\$|us\$|\s(reais|real|dolar|dolares|euros?|centavos)\s", j):
        return "dinheiro"
    if re.search(r"\s(horas?|minutos?)\s", j):
        return "hora"
    if any(f" {P.normalizar(m)} " in j for m in C.MESES):
        return "data"
    if re.fullmatch(r"(19|20)\d{2}", bruto):
        return "ano"
    return "numero"


def frases_do_texto(texto):
    """Parte um texto corrido em frases legíveis (mínimo 4 palavras)."""
    texto = re.sub(r"\s+", " ", re.sub(r"\r", "", texto))
    saida = []
    for f in re.split(r"(?<=[.!?…])\s+|\n{2,}|;\s", texto):
        f = f.strip(" -•\t")
        if len(re.findall(r"\w+", f)) >= 4:
            saida.append(f[:600])
    return saida


def ler_pdf(caminho):
    """Texto de um PDF: pypdf se estiver instalado, senão o pdftotext do sistema; senão, devolve None."""
    try:
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(caminho)).pages)
    except ImportError:
        pass
    except Exception:
        return None
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-enc", "UTF-8", str(caminho), "-"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def passagem(origem, ref, texto, titulo="", url=""):
    toks = P.normalizar(texto).split()
    return {"origem": origem, "ref": ref, "titulo": titulo, "url": url, "texto": texto,
            "tokens": toks, "numeros": numeros_do_texto(texto), "nomes": P.nomes_do_texto(texto)}


def da_ficha(caminho):
    """Passagens da ficha de fatos (uma por fato, mais uma por trecho de fonte)."""
    p = Path(caminho)
    if not p.exists():
        return [], None
    try:
        ficha = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"pesquisa/fatos.json inválido: {e}")
    saida = []
    for f in ficha.get("fatos", []):
        fid = f.get("id") or "F?"
        partes = [f.get("afirmacao") or "", f.get("como_dizer") or ""]
        if f.get("valor") is not None:
            partes.append(f"{f['valor']} {f.get('unidade') or ''}")
        partes += [t for t in f.get("termos", []) if isinstance(t, str)]
        fontes = f.get("fontes") or []
        pa = passagem("fatos", fid, " ".join(x for x in partes if x),
                      titulo=(fontes[0].get("titulo") if fontes else ""),
                      url=(fontes[0].get("url") if fontes else ""))
        pa.update({"fato": f, "status": f.get("status"), "caduca_em": f.get("caduca_em")})
        saida.append(pa)
        for k, s in enumerate(fontes):
            if s.get("trecho"):
                q = passagem("fatos", f"{fid}/fonte{k + 1}", s["trecho"], s.get("titulo", ""), s.get("url", ""))
                q.update({"fato": f, "status": f.get("status"), "caduca_em": f.get("caduca_em")})
                saida.append(q)
    return saida, ficha


def dos_documentos(caminhos):
    """Passagens dos documentos; devolve (passagens, lidos, nao_lidos)."""
    arquivos, saida, lidos, falhou = [], [], [], []
    for c in caminhos:
        p = Path(c).expanduser()
        if p.is_dir():
            arquivos += [f for f in sorted(p.rglob("*")) if f.suffix.lower() in EXTENSOES and f.is_file()
                         and not f.name.startswith("_")]
        elif p.is_file():
            arquivos.append(p)
    for f in arquivos:
        if f.suffix.lower() == ".pdf":
            texto = ler_pdf(f)
            if texto is None:
                falhou.append({"arquivo": str(f), "porque": "não consegui ler o PDF (instale o pypdf)"})
                continue
        else:
            try:
                texto = f.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                falhou.append({"arquivo": str(f), "porque": str(e)})
                continue
        frases = frases_do_texto(texto)
        for i, fr in enumerate(frases, 1):
            saida.append(passagem("documento", f"{f.name}:{i}", fr, titulo=f.name))
        lidos.append({"arquivo": str(f), "frases": len(frases)})
    return saida, lidos, falhou


def indexar(passagens):
    """Índice palavra → passagens, para achar a passagem comparável sem varrer tudo."""
    idx = {}
    for i, p in enumerate(passagens):
        for t in set(p["tokens"]):
            if len(t) >= 4 and t not in P.STOP:
                idx.setdefault(t, []).append(i)
    return idx
