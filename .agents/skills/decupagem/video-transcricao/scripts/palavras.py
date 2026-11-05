#!/usr/bin/env python3
"""palavras.py: o formato de transcrição da casa e utilidades de texto (as skills video-mapa-de-fala e
video-checagem importam este módulo).

transcricao/palavras.json   [{"w": "palavra", "t0": 1.23, "t1": 1.51, "p": 0.93}]   segundos; p = confiança
transcricao/segmentos.json  [{"t0": 0.0, "t1": 4.2, "texto": "..."}]
Quem lê aceita também a/b e ini/fim no lugar de t0/t1 (formatos antigos).
"""
import difflib
import json
import os
import re
import unicodedata
from pathlib import Path

# palavras comuns do português (fora da busca de nomes próprios e do peso dos termos)
STOP = set("""a o as os um uma uns umas de da do das dos em no na nos nas num numa para pra pro pros pras por pelo pela
pelos pelas com sem sob sobre entre ate desde ao aos e ou mas nem que se porque pois como quando onde quem qual quais
quanto quanta quantos quantas cujo cuja ja nao sim so tambem ainda mais menos muito muita muitos muitas pouco pouca
tudo nada algo alguem ninguem todo toda todos todas outro outra outros outras mesmo mesma esse essa esses essas este
esta estes estas aquele aquela aqueles aquelas isso isto aquilo aqui ali la ai entao assim agora hoje ontem depois
antes sempre nunca tipo ne eu tu ele ela nos vos eles elas voce voces me te lhe lhes meu minha meus minhas teu tua
seu sua seus suas nosso nossa nossos nossas dele dela deles delas ser sou e era foi foram sera seria sao estar esta
estou estava estao ter tem tinha tive teve tiveram ha havia vai vou vamos vao fazer faz fez fazendo dizer diz disse
falar fala falou ver vi viu pode podem poder deve devem bem bom boa la cada qualquer outra vez vezes coisa coisas
gente cara olha veja sabe sabia acho acha""".split())

CONECTORES = {"de", "da", "do", "dos", "das", "e", "van", "von", "del", "di", "du", "la", "le"}


def normalizar(s) -> str:
    """Sem acento, sem caixa, só letras e dígitos separados por espaço."""
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fonetica(s) -> str:
    """Chave aproximada de pronúncia em português (para casar nome que o Whisper escreveu errado)."""
    s = normalizar(str(s).lower().replace("ç", "s")).replace(" ", "")
    s = re.sub(r"c([ei])", r"s\1", s)
    for a, b in (("ph", "f"), ("th", "t"), ("sch", "x"), ("sh", "x"), ("ch", "x"), ("lh", "li"), ("nh", "ni"),
                 ("qu", "k"), ("gue", "ge"), ("gui", "gi"), ("ck", "k"), ("c", "k"), ("y", "i"), ("w", "v"),
                 ("z", "s"), ("ss", "s"), ("h", "")):
        s = s.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", s)


def parecido(a, b) -> float:
    """Similaridade 0–1 entre duas grafias, pela chave fonética."""
    fa, fb = fonetica(a), fonetica(b)
    if not fa or not fb:
        return 0.0
    return difflib.SequenceMatcher(None, fa, fb).ratio()


def mmss(t, centesimos=False) -> str:
    t = max(0.0, float(t))
    h, resto = divmod(t, 3600)
    m, s = divmod(resto, 60)
    seg = f"{s:05.2f}".replace(".", ",") if centesimos else f"{int(s):02d}"
    return (f"{int(h)}:{int(m):02d}:" if h else f"{int(m):02d}:") + seg


def carregar(caminho):
    """Lê palavras.json (t0/t1, a/b ou ini/fim) e devolve [{"w","t0","t1","p"}] em ordem de tempo."""
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if isinstance(d, dict):
        d = d.get("palavras") or d.get("words") or []
    out = []
    for x in d:
        w = str(x.get("w", x.get("word", x.get("text", "")))).strip()
        t0 = next((x[k] for k in ("t0", "a", "ini", "start") if x.get(k) is not None), None)
        t1 = next((x[k] for k in ("t1", "b", "fim", "end") if x.get(k) is not None), t0)
        if not w or w.startswith("[") or t0 is None:
            continue
        out.append({"w": w, "t0": float(t0), "t1": float(t1), "p": x.get("p")})
    out.sort(key=lambda p: p["t0"])
    return out


def achar_palavras(caminho=None) -> Path:
    """palavras.json a partir de um arquivo, de uma pasta, ou subindo as pastas até achar transcricao/palavras.json."""
    if caminho:
        p = Path(caminho).expanduser()
        if p.is_dir():
            p = p / "palavras.json" if (p / "palavras.json").exists() else p / "transcricao" / "palavras.json"
        return p
    pasta = Path.cwd().resolve()
    for d in [pasta, *pasta.parents]:
        if (d / "transcricao" / "palavras.json").exists():
            return d / "transcricao" / "palavras.json"
    return Path("transcricao") / "palavras.json"


def frases(palavras, pausa=0.8, max_chars=160):
    """Agrupa palavras em frases: quebra em . ? ! …, em pausa maior que `pausa` e, se passar de max_chars, na vírgula."""
    out, cur = [], []

    def fecha():
        if cur:
            out.append({"t0": round(cur[0][1]["t0"], 3), "t1": round(cur[-1][1]["t1"], 3), "i0": cur[0][0],
                        "i1": cur[-1][0], "texto": " ".join(p["w"] for _, p in cur)})
            cur.clear()

    for i, p in enumerate(palavras):
        if cur and p["t0"] - cur[-1][1]["t1"] > pausa:
            fecha()
        cur.append((i, p))
        tam = sum(len(q["w"]) + 1 for _, q in cur)
        if re.search(r"[.?!…]$", p["w"]) or (tam > max_chars and re.search(r"[,;:]$", p["w"])) or tam > max_chars * 1.5:
            fecha()
    fecha()
    return out


def nomes_do_texto(texto, minimo=1):
    """Candidatos a nome próprio num texto (roteiro, documento): sequências de palavras com inicial maiúscula
    (com de/da/do no meio) e siglas. Palavra que abre frase só conta se não for comum nem aparecer em minúscula
    no texto. Devolve a lista em ordem de frequência."""
    texto = re.sub(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>|https?://\S+", " ", texto)
    minusculas = {normalizar(m) for m in re.findall(r"\b[a-zà-ÿ][\wà-ÿ'-]*", texto)}
    contagem, ordem, rotulo = {}, [], {}
    for linha in texto.splitlines():
        linha = re.sub(r"^[\s#>*\-–—\d.)]+", "", linha)
        toks = re.findall(r"[\wÀ-ÿ][\wÀ-ÿ'’.-]*|[.?!:;—–]", linha)
        inicio, seq, abriu = True, [], [True]

        def fecha():
            while seq and normalizar(seq[-1]) in CONECTORES:
                seq.pop()
            if seq:
                nome = " ".join(seq).strip(".")
                if nome not in contagem:
                    ordem.append(nome)
                contagem[nome] = contagem.get(nome, 0) + 1
                if abriu[0]:          # abriu a linha ou a frase: pode ser título ou rótulo, não nome próprio
                    rotulo[nome] = rotulo.get(nome, 0) + 1
            seq.clear()

        for t in toks:
            if t in ".?!:;—–":
                fecha()
                inicio = True
                continue
            if not seq:
                abriu[0] = inicio
            limpo = t.strip(".'’-")
            n = normalizar(limpo)
            sigla = bool(re.fullmatch(r"[A-ZÀ-Ý]{2,6}s?", limpo)) and n not in STOP
            maiuscula = limpo[:1].isupper() and not limpo.isdigit()
            if seq and n in CONECTORES and not limpo[:1].isupper():
                seq.append(limpo)
            elif sigla or (maiuscula and not (inicio and (n in STOP or n in minusculas))
                           and (n not in STOP or seq)):
                seq.append(limpo)
            else:
                fecha()
            if re.search(r"[.?!…]$", t):      # a frase acabou NESTA palavra: não emende com a seguinte
                fecha()
                inicio = True
                continue
            inicio = False
        fecha()
    nomes = [n for n in ordem if contagem[n] >= minimo and len(normalizar(n)) >= 2
             # palavra única que só aparece abrindo linha ou frase uma vez é título de seção, não nome
             and not (len(n.split()) == 1 and contagem[n] < 2 and rotulo.get(n, 0) >= contagem[n])]
    return sorted(nomes, key=lambda n: -contagem[n])


def ocorrencias_aproximadas(nome, palavras, limiar=0.8, tokens=None):
    """Onde um nome aparece escrito de outro jeito: janelas de 1–3 palavras com a mesma pronúncia aproximada.
    Devolve [(similaridade, i0, i1)] sem sobreposição, da maior para a menor."""
    alvo = fonetica(nome)
    if len(alvo) < 3:
        return []
    toks = tokens or [normalizar(p["w"]) for p in palavras]
    n_alvo = len(normalizar(nome).split())
    achados = []
    for i in range(len(toks)):
        for k in range(max(1, n_alvo - 1), n_alvo + 2):
            jan = toks[i:i + k]
            if len(jan) < k or not jan[0] or jan[0] in STOP or jan[-1] in STOP:
                continue
            f = fonetica(" ".join(jan))
            if abs(len(f) - len(alvo)) > max(2, 0.35 * len(alvo)):
                continue
            sm = difflib.SequenceMatcher(None, f, alvo)
            if sm.real_quick_ratio() < limiar or sm.quick_ratio() < limiar:
                continue
            r = sm.ratio()
            if r >= limiar:
                achados.append((round(r, 3), i, i + k - 1))
    achados.sort(key=lambda x: -x[0])
    usados, out = set(), []
    for r, a, b in achados:
        if not usados & set(range(a, b + 1)):
            out.append((r, a, b))
            usados |= set(range(a, b + 1))
    return out


def casa_dir() -> Path:
    return Path(os.environ.get("CRIABR_CASA", Path.home() / ".criabr"))


def ambiente() -> dict:
    f = casa_dir() / "ambiente.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gravar_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name("_" + caminho.name + ".tmp")
    texto = json.dumps(dados, ensure_ascii=False, indent=1)
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    os.replace(tmp, caminho)
