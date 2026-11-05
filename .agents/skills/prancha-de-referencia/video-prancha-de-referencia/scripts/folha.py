#!/usr/bin/env python3
"""folha.py — folha de contato NUMERADA de uma unidade: miniaturas com o código ligado à unidade (U045-3) e a
licença embaixo de cada uma. O usuário escolhe os números; só depois é que se baixa.

    folha.py montar U045 [--colunas 4] [--por-fonte 4] [--pausa 2]
    folha.py montar U045 --sem-busca            # redesenha a folha com os candidatos já guardados
    folha.py escolher U045-3 U045-7             # registra a escolha e IMPRIME o comando de download
    folha.py listar

Quem busca é a video-broll (scripts/buscar.py); aqui ficam a numeração por unidade, o desenho da folha e a
escolha. `montar` baixa só as miniaturas; `escolher` não baixa nada — imprime o comando que baixa, e esse ainda
exige --confirmar. A folha é ferramenta de trabalho: usa os tokens da DA quando há DA e um visual neutro quando
não há."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import base  # noqa: E402

ESCOLHAS = base.PASTA / "escolhas.json"
UNIDADES = Path("roteiro") / "unidades.json"
NEUTRO = {"fundo": (246, 245, 243, 255), "superficie": (228, 226, 222, 255), "texto": (26, 26, 28, 255),
          "texto_suave": (104, 104, 110, 255), "primaria": (32, 70, 140, 255),
          "positivo": (28, 122, 72, 255), "alerta": (176, 118, 16, 255), "negativo": (168, 38, 38, 255)}
FONTES_NEUTRAS = ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc", "segoeui.ttf", "LiberationSans-Regular.ttf")


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ────────────────────────────────────────────────────────────────── o pincel ──
class Pincel:
    """Texto e cor da folha: pelos tokens da DA quando há DA, neutro quando não há."""

    def __init__(self, d=None, texto_mod=None):
        self.d, self.texto = d, texto_mod
        self._cache: dict = {}

    def cor(self, token: str, alfa: float = 1.0):
        if self.d is not None:
            try:
                return self.d.rgba(token, alfa) if alfa != 1.0 else self.d.rgba(token)
            except Exception:
                pass
        r, g, b, a = NEUTRO.get(token, NEUTRO["texto"])
        return (r, g, b, int(round(a * alfa)))

    def _fonte(self, tamanho: int):
        if tamanho in self._cache:
            return self._cache[tamanho]
        from PIL import ImageFont
        f = None
        for nome in FONTES_NEUTRAS:
            try:
                f = ImageFont.truetype(nome, tamanho)
                break
            except (OSError, ValueError):
                continue
        if f is None:
            try:
                f = ImageFont.load_default(size=tamanho)
            except TypeError:                        # Pillow antigo: só o bitmap de tamanho fixo
                f = ImageFont.load_default()
        self._cache[tamanho] = f
        return f

    def largura(self, s: str, tamanho: int, papel: str = "dados") -> int:
        if self.d is not None:
            return int(self.texto.largura_texto(s, self.texto.Estilo.do_papel(self.d, papel, tamanho, cor="texto")))
        from PIL import ImageDraw, Image
        return int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(s, font=self._fonte(tamanho)))

    def linha(self, s: str, tamanho: int, token: str = "texto", papel: str = "dados", max_larg: int | None = None):
        """Uma linha de texto como imagem RGBA, cortada com reticências se não couber."""
        s = "".join(ch for ch in " ".join(str(s).split()) if ord(ch) < 0x250 or ch in "–—‘’“”…·×•⚠")
        if max_larg and self.largura(s, tamanho, papel) > max_larg:
            while len(s) > 1 and self.largura(s.rstrip() + "…", tamanho, papel) > max_larg:
                s = s[:-1]
            s = s.rstrip(" ,.;:-–") + "…"
        s = s or "—"
        if self.d is not None:
            est = self.texto.Estilo.do_papel(self.d, papel, tamanho, cor=token)
            return self.texto.desenhar(s, est)[0]
        from PIL import Image, ImageDraw
        f = self._fonte(tamanho)
        larg = max(1, self.largura(s, tamanho, papel))
        img = Image.new("RGBA", (larg + 2, int(tamanho * 1.45)), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((0, 0), s, font=f, fill=self.cor(token))
        return img


# ───────────────────────────────────────────────────────── candidatos da unidade ──
def _unidade(raiz: Path, id_: str) -> dict:
    doc = base.ler_json(raiz / UNIDADES)
    if not doc:
        raise base.Erro(f"não achei {UNIDADES.as_posix()}.", "Rode decupar.py <roteiro de edição> primeiro.", base.USO)
    for u in doc["unidades"]:
        if u["id"].lower() == str(id_).lower():
            return u
    raise base.Erro(f"não achei a unidade {id_!r}.",
                    f"Unidades: {', '.join(u['id'] for u in doc['unidades'][:20])}…", base.USO)


def _sinal_da_licenca(rotulo: str, exige_atribuicao) -> str:
    r = (rotulo or "").lower()
    if "recusada" in r:
        return "negativo"
    if "confira" in r or "relevância baixa" in r or exige_atribuicao:
        return "alerta"
    return "positivo"


def buscar_candidatos(raiz: Path, d, u: dict, por_fonte: int, pausa: float, fontes=None) -> dict:
    """Roda a busca da video-broll para CADA mídia pedida pela unidade e numera tudo na folha da unidade."""
    _comum, _prov, buscar_mod, _baixar = base.broll()
    http = _comum.Http()
    celulas = []
    if not u["midias"]:
        raise base.Erro(f"{u['id']} não pede mídia nenhuma.",
                        "Acrescente linhas «- Mídia: …» a essa unidade no roteiro de edição e rode decupar.py de novo.", base.USO)
    for m in u["midias"]:
        base.respirar(pausa, f"{u['id']} → {m['codigo']}", base.diz)
        base.diz(f"  {m['codigo']}  «{m['o_que']}»" + (f" / «{m['en']}»" if m.get("en") else ""))
        try:
            r = buscar_mod.buscar(d, m["o_que"], m.get("en"), m.get("tipo") or "imagem", m.get("orientacao") or "qualquer",
                                  fontes, por_fonte, None, 600.0, None, None, "permitidas", False, True, None, http,
                                  lambda x: base.diz(f"    {x}"))
        except _comum.Erro as e:
            base.diz(f"    ! {e.mensagem}", erro=True)
            continue
        for c in r.get("candidatos") or []:
            rotulo = buscar_mod.rotulo_licenca(c, curto=True)[0]
            celulas.append({"busca": r["slug"], "n_na_busca": c.get("n"), "midia_codigo": m["codigo"],
                            "fonte": c.get("fonte"), "tipo": c.get("tipo"), "titulo": c.get("titulo"),
                            "autor": c.get("autor"), "pagina_url": c.get("pagina_url"),
                            "miniatura_url": c.get("miniatura_url"), "largura": c.get("largura"),
                            "altura": c.get("altura"), "duracao": c.get("duracao"), "licenca": c.get("licenca"),
                            "licenca_url": c.get("licenca_url"), "exige_atribuicao": c.get("exige_atribuicao"),
                            "rotulo_licenca": rotulo, "sinal": buscar_mod.rotulo_licenca(c)[1]})
    for i, c in enumerate(celulas, 1):
        c["codigo"] = f"{u['id']}-{i}"
        c["n"] = i
    return {"versao": 1, "unidade": u["id"], "tipo_tela": u.get("tipo_tela"), "fala": u.get("texto_falado") or u.get("texto_roteiro"),
            "feito_em": agora(), "celulas": celulas}


# ───────────────────────────────────────────────────────────── desenho da folha ──
def _miniatura(raiz: Path, http, c: dict, lado: int):
    """PIL.Image da miniatura: arquivo local quando há, senão a miniatura do provedor (cache da video-broll)."""
    from PIL import Image, ImageOps
    arq = c.get("miniatura_arquivo")
    if arq:
        p = Path(arq)
        p = p if p.is_absolute() else raiz / p
        try:
            with Image.open(p) as im:
                return ImageOps.exif_transpose(im).convert("RGB")
        except (OSError, ValueError):
            return None
    if not c.get("miniatura_url") or http is None:
        return None
    try:
        _comum, _prov, buscar_mod, _baixar = base.broll()
        return buscar_mod._miniatura(raiz, http, c)
    except Exception:
        return None


def desenhar(raiz: Path, dados: dict, pincel: Pincel, saida: Path, colunas: int = 4, largura_celula: int = 420,
             http=None) -> Path:
    """A folha de contato da unidade. Cada célula leva o CÓDIGO (U045-3) em cima e a LICENÇA embaixo."""
    from PIL import Image, ImageDraw, ImageOps
    celulas = dados["celulas"]
    if not celulas:
        raise base.Erro(f"{dados['unidade']}: nenhum candidato para desenhar.", "Rode folha.py montar sem --sem-busca.", base.USO)
    colunas = max(1, min(colunas, len(celulas)))
    u = largura_celula
    margem, vao = int(u * 0.11), int(u * 0.05)
    alt_mini = int(u * 9 / 16)
    t_nota, t_corpo, t_titulo = max(13, int(u * 0.036)), max(15, int(u * 0.043)), int(u * 0.082)
    t_codigo = int(t_corpo * 1.5)
    alt_leg = int(t_corpo * 1.9 + t_nota * 3.6)
    linhas_n = max(1, -(-len(celulas) // colunas))
    cab = int(t_titulo * 4.1)
    rodape = int(t_nota * 4.2)
    W = max(margem * 2 + colunas * u + (colunas - 1) * vao, margem * 2 + int(u * 2.4))
    H = margem + cab + linhas_n * (alt_mini + alt_leg) + (linhas_n - 1) * vao + rodape + margem // 2
    img = Image.new("RGBA", (W, H), pincel.cor("fundo"))
    des = ImageDraw.Draw(img)

    def por(bloco, x, y):
        img.alpha_composite(bloco, (int(max(0, x)), int(max(0, y))))
        return bloco.width

    # cabeçalho: unidade, tipo de tela, fala
    por(pincel.linha(f"{dados['unidade']} · folha de contato", t_titulo, "texto", "titulo", W - 2 * margem), margem, margem)
    por(pincel.linha(dados.get("tipo_tela") or "", t_corpo, "texto_suave", "corpo", W - 2 * margem), margem, margem + int(t_titulo * 1.45))
    fala = (dados.get("fala") or "").strip()
    if fala:
        por(pincel.linha(f"«{fala}»", t_nota, "texto_suave", "dados", W - 2 * margem), margem, margem + int(t_titulo * 2.35))
    y_fio = margem + cab - int(t_titulo * 0.75)
    des.rectangle([margem, y_fio, W - margem, y_fio + max(2, int(u * 0.005))], fill=pincel.cor("primaria"))

    def sinal(x, y, token):
        r = max(4, int(t_nota * 0.36))
        des.ellipse([x, y + int(t_nota * 0.18), x + 2 * r, y + int(t_nota * 0.18) + 2 * r], fill=pincel.cor(token))
        return 2 * r + int(t_nota * 0.55)

    for i, c in enumerate(celulas):
        col, lin = i % colunas, i // colunas
        x = margem + col * (u + vao)
        y = margem + cab + lin * (alt_mini + alt_leg + vao)
        quadro = Image.new("RGBA", (u, alt_mini), pincel.cor("superficie"))
        mini = _miniatura(raiz, http, c, u)
        if mini is not None:
            mini = ImageOps.contain(mini, (u, alt_mini), Image.LANCZOS)   # miniatura de terceiro entra inteira, sem recorte
            quadro.paste(mini, ((u - mini.width) // 2, (alt_mini - mini.height) // 2))
        else:
            vazio = pincel.linha("sem miniatura", t_nota, "texto_suave")
            quadro.alpha_composite(vazio, ((u - vazio.width) // 2, (alt_mini - vazio.height) // 2))
        img.paste(quadro, (x, y))
        # CÓDIGO da célula: é o que o usuário diz em voz alta («quero o U045-3»)
        cod = pincel.linha(c["codigo"], t_codigo, "fundo", "dados")
        alt_selo, pad = int(t_codigo * 1.75), int(t_codigo * 0.45)
        larg_selo = cod.width + 2 * pad
        des.rectangle([x, y, x + larg_selo, y + alt_selo], fill=pincel.cor("primaria"))
        por(cod, x + pad, y + (alt_selo - cod.height) // 2)
        etq = ("VÍDEO " + (f"{c['duracao']:.0f} s" if c.get("duracao") else "")) if c.get("tipo") == "video" else "IMAGEM"
        bloco = pincel.linha(etq.strip(), t_nota, "texto", "dados")
        des.rectangle([x + u - bloco.width - 2 * pad, y + alt_mini - int(t_nota * 2.0), x + u, y + alt_mini], fill=pincel.cor("fundo", 0.85))
        por(bloco, x + u - bloco.width - pad, y + alt_mini - int(t_nota * 1.75))
        # legenda: título · fonte e resolução · LICENÇA com sinal
        yl = y + alt_mini + int(t_corpo * 0.45)
        por(pincel.linha(c.get("titulo") or "(sem título)", t_corpo, "texto", "corpo", u), x, yl)
        yl += int(t_corpo * 1.5)
        dims = f"{c['largura']}×{c['altura']}" if c.get("largura") and c.get("altura") else "resolução ?"
        por(pincel.linha(f"{c.get('fonte') or '?'} · {dims} · {c.get('midia_codigo') or ''}", t_nota, "texto_suave", "dados", u), x, yl)
        yl += int(t_nota * 1.75)
        token = c.get("sinal") or _sinal_da_licenca(c.get("rotulo_licenca"), c.get("exige_atribuicao"))
        dx = sinal(x, yl, token)
        por(pincel.linha(c.get("rotulo_licenca") or c.get("licenca") or "licença não informada", t_nota, "texto", "dados", u - dx), x + dx, yl)

    # rodapé: como escolher + legenda dos sinais
    yb = H - margem // 2 - int(t_nota * 3.0)
    por(pincel.linha("Escolha pelos códigos (ex.: «quero o " + celulas[0]["codigo"] + "»). Nada é baixado antes disso.",
                     t_corpo, "texto", "corpo", W - 2 * margem), margem, yb)
    yb += int(t_corpo * 1.7)
    xr = margem
    for token, rot in (("positivo", "crédito opcional"), ("alerta", "crédito obrigatório ou origem a conferir"),
                       ("negativo", "licença recusada pela política")):
        xr += sinal(xr, yb, token)
        xr += por(pincel.linha(rot, t_nota, "texto_suave", "dados"), xr, yb) + int(t_nota * 2.0)
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_name(saida.stem + ".parcial.png")
    img.convert("RGB").save(tmp, "PNG", optimize=True)
    tmp.replace(saida)
    return saida


# ──────────────────────────────────────────────────────────────────────── CLI ──
def main(argv=None) -> int:
    ap = base.Parser(prog="folha.py", description="Folha de contato numerada de uma unidade: código ligado à unidade (U045-3) "
                     "e licença embaixo de cada miniatura. O usuário escolhe os números; só então se baixa.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("montar", help="busca os candidatos da unidade e desenha a folha (baixa só as miniaturas)")
    p.add_argument("unidade", metavar="U045")
    p.add_argument("--colunas", type=int, default=4)
    p.add_argument("--por-fonte", type=int, default=4, metavar="N", help="resultados por provedor (padrão 4)")
    p.add_argument("--pausa", type=float, default=2.0, metavar="S", help="segundos entre pedidos (padrão 2)")
    p.add_argument("--fontes", metavar="A,B", help="limita os provedores (padrão: todos os da video-broll)")
    p.add_argument("--sem-busca", action="store_true", help="só redesenha a folha com os candidatos já guardados")
    p.add_argument("--sem-da", action="store_true", help="desenha com o visual neutro, sem direção de arte")

    p = sub.add_parser("escolher", help="registra a escolha do usuário e imprime o comando de download")
    p.add_argument("codigos", nargs="+", metavar="U045-3")

    sub.add_parser("listar", help="as folhas já montadas e o que foi escolhido")

    for s in sub.choices.values():
        s.add_argument("--projeto", metavar="PASTA")
        s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    raiz = base.achar_projeto(a.projeto)

    if a.cmd == "listar":
        escolhas = base.ler_json(raiz / ESCOLHAS, {}) or {}
        folhas = sorted((raiz / base.PASTA).glob("*.candidatos.json")) if (raiz / base.PASTA).is_dir() else []
        if a.json:
            print(json.dumps({"folhas": [f.name for f in folhas], "escolhas": escolhas}, ensure_ascii=False, indent=1))
            return 0
        if not folhas:
            base.diz("Nenhuma folha montada ainda. Rode folha.py montar U001.")
            return 1
        for f in folhas:
            dados = base.ler_json(f, {})
            uid = dados.get("unidade")
            base.diz(f"{uid}  {len(dados.get('celulas') or [])} candidato(s)  escolhidos: {', '.join(escolhas.get(uid, [])) or '—'}"
                     f"   {f.with_suffix('').with_suffix('.png').name}")
        return 0

    if a.cmd == "montar":
        u = _unidade(raiz, a.unidade)
        arq_cand = raiz / base.PASTA / f"{u['id']}.candidatos.json"
        d, texto_mod = None, None
        if not a.sem_da:
            da_mod, texto_mod = base.kit()
            try:
                d = da_mod.carregar(str(raiz))
            except Exception as e:
                base.diz(f"! sem direção de arte ({getattr(e, 'mensagem', e)}): a folha sai com o visual neutro.", erro=True)
                texto_mod = None
        if a.sem_busca:
            dados = base.ler_json(arq_cand)
            if not dados:
                raise base.Erro(f"não achei {arq_cand}.", "Monte a folha sem --sem-busca (aí ele busca).", base.USO)
        else:
            if d is None:
                raise base.Erro("buscar mídia exige direção de arte neste projeto.",
                                "Crie a DA com a skill video-direcao-de-arte, ou redesenhe uma folha já montada com --sem-busca.",
                                base.SEM_DA)
            fontes = [f.strip() for f in a.fontes.split(",")] if a.fontes else None
            base.diz(f"{u['id']} · {u.get('tipo_tela')} · {len(u['midias'])} mídia(s) pedida(s)")
            dados = buscar_candidatos(raiz, d, u, a.por_fonte, a.pausa, fontes)
            base.gravar_json(arq_cand, dados)
        http = None
        if not a.sem_busca:
            _comum, _prov, _buscar, _baixar = base.broll()
            http = _comum.Http()
        png = desenhar(raiz, dados, Pincel(d, texto_mod), raiz / base.PASTA / f"{u['id']}.png", a.colunas, http=http)
        if a.json:
            print(json.dumps({"folha": str(png), "candidatos": str(arq_cand), "celulas": dados["celulas"]}, ensure_ascii=False, indent=1))
            return 0
        base.diz(f"\n{len(dados['celulas'])} candidato(s) na folha:")
        for c in dados["celulas"]:
            base.diz(f"  {c['codigo']:10} {c['fonte'] or '?':10} {(c.get('titulo') or '')[:52]:52} {c.get('rotulo_licenca') or ''}")
        base.diz(f"\nFolha: {png}")
        base.diz("MOSTRE a folha ao usuário e espere a escolha. Depois: folha.py escolher "
                 f"{dados['celulas'][0]['codigo']}")
        return 0

    if a.cmd == "escolher":
        escolhas = base.ler_json(raiz / ESCOLHAS, {}) or {}
        por_busca: dict[str, list[int]] = {}
        achados = []
        for codigo in a.codigos:
            m = re.fullmatch(r"(?i)(U\d+)-(\d+)", codigo.strip())
            if not m:
                raise base.Erro(f"código inválido: {codigo!r}", "Use o código que está na folha, como U045-3.", base.USO)
            uid, n = m.group(1).upper(), int(m.group(2))
            dados = base.ler_json(raiz / base.PASTA / f"{uid}.candidatos.json")
            if not dados:
                raise base.Erro(f"não achei a folha de {uid}.", f"Monte-a antes: folha.py montar {uid}", base.USO)
            c = next((x for x in dados["celulas"] if x["n"] == n), None)
            if c is None:
                raise base.Erro(f"{uid} não tem o candidato {n}.",
                                f"A folha vai de 1 a {len(dados['celulas'])}.", base.USO)
            achados.append(c)
            escolhas.setdefault(uid, [])
            if c["codigo"] not in escolhas[uid]:
                escolhas[uid].append(c["codigo"])
            por_busca.setdefault(c["busca"], []).append(c["n_na_busca"])
        base.gravar_json(raiz / ESCOLHAS, escolhas)
        comandos = [f'python3 <skills>/video-broll/scripts/baixar.py --busca "{slug}" --escolher {",".join(str(x) for x in sorted(set(ns)))}'
                    for slug, ns in por_busca.items()]
        if a.json:
            print(json.dumps({"escolhidos": achados, "comandos": comandos}, ensure_ascii=False, indent=1))
            return 0
        for c in achados:
            base.diz(f"{c['codigo']}  {c.get('titulo') or ''}  [{c.get('rotulo_licenca') or ''}]  {c.get('pagina_url') or ''}")
        base.diz("\nCom o «sim» do usuário, o download é da video-broll (ela monta o plano e só baixa com --confirmar):")
        for cmd in comandos:
            base.diz(f"  {cmd}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(base.rodar(main))
