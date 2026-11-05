#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pacote.py — pacote de publicação por plataforma (skill video-publicacao).

Transforma o vídeo pronto num pacote conferido: publicacao/<plataforma>/meta.json,
descricao.txt, checklist.md e o índice publicacao/pacote.json.

Subcomandos
    novo <plataforma> [--video ARQ] [--corte K01]   cria o meta.json com os campos técnicos
    capitulos [pacote]                               capítulos do YouTube (formata e valida)
    descricao <pacote>                               monta descricao.txt por blocos
    definir <pacote> [--agendar ISO] [--privacidade P] …   muda agenda, privacidade e declarações sem tocar no texto
    validar [pacote…]                                confere tudo contra plataformas.json + portão de QA
    checklist <pacote>                               passo a passo manual de envio, em Markdown
    registrar <pacote> --url URL                     anota um envio feito à mão, por conector ou pelo navegador
    resumo                                           publicacao/pacote.json + tabela no terminal

A validação gravada não é um salvo-conduto: `checklist`, `registrar`, `resumo` e o envio pela API refazem a
conferência inteira na hora (custa um ffprobe por pacote) e só aceitam o pacote se ela continuar passando.

Códigos de saída: 0 ok · 1 reprovado/erro · 2 projeto sem direção de arte · 64 uso incorreto.

Nenhum limite de plataforma está escrito neste arquivo: todos entram por `ler_plataformas()`,
que prefere os acessores do kit de direção de arte e cai para kit/plataformas.json.
Só stdlib + Pillow. Não toca a rede. Não escreve fora de publicacao/.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # a pasta da skill fica limpa (sem __pycache__)

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import shutil
import unicodedata
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
SKILL_FINAL = "~/.claude/skills/video-publicacao"           # caminho citado em textos para humanos
KIT_FINAL = "~/.claude/skills/video-direcao-de-arte/kit"

SAIDA_OK, SAIDA_ERRO, SAIDA_SEM_DA, SAIDA_USO = 0, 1, 2, 64

PLATAFORMAS = ("youtube", "shorts", "reels", "tiktok")
NOME_PLATAFORMA = {"youtube": "YouTube (vídeo longo)", "shorts": "YouTube Shorts",
                   "reels": "Instagram Reels", "tiktok": "TikTok"}
APELIDOS = {"yt": "youtube", "youtube_longo": "youtube", "youtube-longo": "youtube", "longo": "youtube",
            "short": "shorts", "youtube_shorts": "shorts", "youtube-shorts": "shorts",
            "instagram": "reels", "instagram_reels": "reels", "reel": "reels", "ig": "reels", "insta": "reels",
            "tt": "tiktok", "tik-tok": "tiktok"}
# Nome da seção de cada plataforma dentro de plataformas.json: o canônico primeiro, depois os
# nomes antigos (kit 1.1.0 usava youtube_longo e instagram_reels).
SECOES = {"youtube": ("youtube", "youtube_longo"), "shorts": ("shorts", "youtube_shorts"),
          "reels": ("reels", "instagram_reels", "instagram"), "tiktok": ("tiktok",)}
# O Short usa os mesmos campos e a mesma API do vídeo comum: o que a seção `shorts` não traz
# vem da seção `youtube` (é o que a nota do próprio plataformas.json diz).
HERDA_TEXTO = {"shorts": "youtube"}
VERTICAIS = ("shorts", "reels", "tiktok")
PRIVACIDADES = ("private", "unlisted", "public")
BLOCOS = ("abertura", "capitulos", "fontes", "creditos", "links", "hashtags")
BLOCOS_PADRAO = {"youtube": ("abertura", "capitulos", "fontes", "creditos", "links", "hashtags"),
                 "shorts": ("abertura", "creditos", "links", "hashtags"),
                 "reels": ("abertura", "creditos", "hashtags"),
                 "tiktok": ("abertura", "creditos", "hashtags")}
TITULO_BLOCO = {"capitulos": "Capítulos", "fontes": "Fontes", "creditos": "Créditos de imagem"}

VAR_PLATAFORMAS = "VIDEO_OPS_PLATAFORMAS_JSON"   # arquivo alternativo de limites — só para testes/revalidação
TOLERANCIA_RELOGIO_S = 300                       # folga ao comparar a data declarada pelo QA com o relógio e com o próprio arquivo

# Limites sem os quais a conferência não quer dizer nada: se plataformas.json não trouxer um deles (seção
# ausente ou renomeada, chave trocada), o pacote REPROVA em vez de passar "sem conferir".
ESSENCIAIS = {
    "youtube": (("limites_texto", "titulo_max_caracteres"), ("limites_texto", "descricao_max_caracteres"), ("limites_texto", "descricao_max_bytes_api"),
                ("limites_texto", "tags_max_caracteres_total"), ("limites_texto", "hashtags_max"), ("limites_texto", "capitulos"),
                ("specs", "duracao_max_s")),
    "shorts": (("limites_texto", "titulo_max_caracteres"), ("limites_texto", "descricao_max_caracteres"), ("limites_texto", "descricao_max_bytes_api"),
               ("limites_texto", "tags_max_caracteres_total"), ("limites_texto", "hashtags_max"), ("specs", "duracao_max_s")),
    "reels": (("limites_texto", "legenda_max_caracteres"), ("limites_texto", "hashtags_max"), ("specs", "duracao_min_s"), ("specs", "duracao_max_s")),
    "tiktok": (("limites_texto", "legenda_max_caracteres_api"), ("specs", "duracao_max_s")),
}
CHAVES_DE_CAPITULOS = ("primeiro_timestamp", "min_timestamps", "duracao_min_capitulo_s")


# ──────────────────────────────────────────────────────────────────── erros ──
class Erro(Exception):
    """Erro com mensagem acionável: o que houve + o que fazer."""
    codigo = SAIDA_ERRO

    def __init__(self, mensagem: str, dica: str | None = None, codigo: int | None = None):
        super().__init__(mensagem)
        self.mensagem, self.dica = mensagem, dica
        if codigo is not None:
            self.codigo = codigo

    def __str__(self) -> str:
        return self.mensagem if not self.dica else f"{self.mensagem}\n  → {self.dica}"


class ErroUso(Erro):
    codigo = SAIDA_USO


# ────────────────────────────────────────────────────────────── utilidades ──
def agora() -> datetime:
    """Relógio da skill. Não há variável de ambiente que o troque: uma validação feita com data falsa aprovaria
    fato vencido e agendamento passado sem deixar rastro (os testes trocam esta função dentro do processo)."""
    return datetime.now().astimezone()


def agora_iso() -> str:
    return agora().isoformat(timespec="seconds")


def nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def ler_json(caminho: Path):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise Erro(f"Arquivo não encontrado: {caminho}")
    except json.JSONDecodeError as e:
        raise Erro(f"JSON inválido em {caminho} (linha {e.lineno}, coluna {e.colno}): {e.msg}",
                   "Corrija o arquivo (vírgula sobrando e aspas simples são os erros mais comuns).")
    except UnicodeDecodeError:
        raise Erro(f"{caminho} não está em UTF-8.", "Regrave o arquivo em UTF-8.")


def ler_json_opcional(caminho: Path):
    return ler_json(caminho) if Path(caminho).is_file() else None


def gravar_texto(caminho: Path, texto: str) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    os.replace(tmp, caminho)
    return caminho


def gravar_json(caminho: Path, obj) -> Path:
    return gravar_texto(caminho, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


_SHA_VISTO: dict[tuple[str, int, int], str] = {}


def sha256_em_cache(caminho: Path) -> str:
    """sha256 do arquivo, calculado uma vez por (caminho, tamanho, mtime) em cada execução: o portão o compara com `alvos`."""
    st = caminho.stat()
    chave = (str(caminho), st.st_size, st.st_mtime_ns)
    if chave not in _SHA_VISTO:
        _SHA_VISTO[chave] = sha256_arquivo(caminho)
    return _SHA_VISTO[chave]


def fmt_tempo(seg: float, com_horas: bool = False) -> str:
    seg = int(seg)
    h, m, s = seg // 3600, (seg % 3600) // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if (com_horas or h) else f"{m:02d}:{s:02d}"


def fmt_dur(seg: float | None) -> str:
    if seg is None:
        return "—"
    if seg < 60:
        return f"{seg:.1f} s".replace(".", ",")
    return fmt_tempo(round(seg))


def fmt_bytes(n: int | float | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unidade == "TB":
            return (f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}").replace(".", ",")
        n /= 1024
    return "—"


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def conta_utf16(texto: str) -> int:
    """Contagem conservadora de 'caracteres': unidades UTF-16 (emoji fora do BMP conta 2).
    É como o TikTok documenta o limite da legenda; para texto comum é igual a len()."""
    return len(texto.encode("utf-16-le")) // 2


def conta_bytes(texto: str) -> int:
    return len(texto.encode("utf-8"))


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ─────────────────────────────────────────────────────────── kit e direção de arte ──
_KIT_MODULO = None


def achar_kit() -> Path:
    """O kit mora ao lado desta skill (<skills>/video-direcao-de-arte/kit); nunca por caminho embutido."""
    for cand in (SKILL.parent / "video-direcao-de-arte" / "kit", Path(KIT_FINAL).expanduser()):
        if (cand / "da.py").is_file():
            return cand
    raise Erro("Kit de direção de arte não encontrado (procurei ao lado desta skill e em "
               f"{KIT_FINAL}).", "Instale a skill video-direcao-de-arte: é dela que vêm a DA e os limites de plataforma.")


def kit():
    """Módulo `da` do kit, importado uma vez."""
    global _KIT_MODULO
    if _KIT_MODULO is None:
        pasta = achar_kit()
        if str(pasta) not in sys.path:
            sys.path.insert(0, str(pasta))
        import da as _da  # noqa: E402  (vizinho instalado ao lado)
        _KIT_MODULO = _da
    return _KIT_MODULO


def ler_plataformas() -> tuple[dict, str]:
    """ÚNICO ponto por onde os limites de plataforma entram nesta skill.

    Ordem: arquivo alternativo (variável VIDEO_OPS_PLATAFORMAS_JSON; testes e revalidação antecipada)
    > acessor do kit `da.plataformas()` (kit ≥ 1.2.0) > leitura direta de kit/plataformas.json.
    Devolve (dados, origem). Trocar a fonte dos limites = mexer só aqui."""
    alternativo = os.environ.get(VAR_PLATAFORMAS, "").strip()
    if alternativo:
        p = Path(alternativo).expanduser()
        if not p.is_file():
            raise Erro(f"{VAR_PLATAFORMAS} aponta para {p}, que não existe.",
                       f"Remova a variável para usar os limites do kit ({KIT_FINAL}/plataformas.json).")
        return _so_objeto(ler_json(p), p), f"arquivo alternativo: {p}"
    da = kit()
    acessor = getattr(da, "plataformas", None)
    if callable(acessor):
        try:
            dados = acessor()
            if isinstance(dados, dict) and dados.get("verificado_em"):
                # o acessor do próprio kit lê kit/plataformas.json: a origem é o arquivo realmente lido, não um rótulo
                do_kit = getattr(acessor, "__module__", None) == getattr(da, "__name__", "") and getattr(da, "PLATAFORMAS_ARQ", None)
                return dados, (f"kit: {achar_kit() / 'plataformas.json'}" if do_kit else "kit: da.plataformas()")
        except Exception:  # acessor em implantação: qualquer surpresa cai para o arquivo
            pass
    arquivo = achar_kit() / "plataformas.json"
    if not arquivo.is_file():
        raise Erro(f"{arquivo} não existe: sem limites de plataforma não dá para validar nada.",
                   "Reinstale a skill video-direcao-de-arte.")
    return _so_objeto(ler_json(arquivo), arquivo), f"kit: {arquivo}"      # o arquivo realmente lido, não um rótulo


def _so_objeto(dados, arquivo: Path) -> dict:
    if not isinstance(dados, dict):
        raise Erro(f"O arquivo de limites de plataformas ({arquivo}) não é um objeto JSON (veio {type(dados).__name__}).",
                   f"Sem limites não dá para validar nada: reinstale a skill video-direcao-de-arte ou corrija a variável {VAR_PLATAFORMAS}.")
    return dados


class Limites:
    """Leitura tolerante de plataformas.json (nomes canônicos ou antigos de seção; null = não encontrado)."""

    def __init__(self, dados: dict | None = None, origem: str | None = None):
        if dados is None:
            dados, origem = ler_plataformas()
        if not isinstance(dados, dict):
            raise Erro(f"Limites de plataforma em formato inesperado ({type(dados).__name__}, esperava um objeto JSON).",
                       "Reinstale a skill video-direcao-de-arte.")
        self.dados, self.origem = dados, origem or "injetado"
        self.do_kit = self.origem.startswith("kit")

    @property
    def verificado_em(self) -> date | None:
        try:
            return date.fromisoformat(str(self.dados.get("verificado_em"))[:10])
        except ValueError:
            return None

    @property
    def prazo_revalidacao_dias(self) -> int:
        meses = _num(self.dados.get("revalidar_a_cada_meses"))
        return int(meses * 30) if meses else 90

    def secao(self, grupo: str, plataforma: str) -> dict:
        bloco = self.dados.get(grupo)
        if not isinstance(bloco, dict):
            return {}
        for nome in SECOES.get(plataforma, (plataforma,)):
            if isinstance(bloco.get(nome), dict):
                return bloco[nome]
        return {}

    def obter(self, plataforma: str, chave: str, grupo: str = "limites_texto"):
        """Valor de um limite (None = não encontrado). Para os limites de texto, pergunta antes ao
        acessor do kit `da.limite(plataforma, chave)` quando ele existir."""
        if grupo == "limites_texto" and self.do_kit:
            acessor = getattr(kit(), "limite", None)
            if callable(acessor):
                try:
                    v = acessor(plataforma, chave)
                    if v is not None and isinstance(v, (int, float, str, list)) and not isinstance(v, bool):
                        return v
                except Exception:
                    pass
        v = self.secao(grupo, plataforma).get(chave)
        if v is None and grupo == "limites_texto" and plataforma in HERDA_TEXTO:
            v = self.secao(grupo, HERDA_TEXTO[plataforma]).get(chave)
        return v

    def oficial(self, plataforma: str, chave: str, grupo: str = "limites_texto") -> bool:
        """False quando o próprio plataformas.json marca a chave como estimativa (lista nao_oficial)."""
        for p in (plataforma, HERDA_TEXTO.get(plataforma)):
            if not p:
                continue
            s = self.secao(grupo, p)
            if chave in s:
                return chave not in (s.get("nao_oficial") or []) and s.get("oficial", True) is not False
        return True


def limites_que_faltam(lim: Limites, plataforma: str) -> list[str]:
    """Limites essenciais (tabela ESSENCIAIS) que plataformas.json não traz para a plataforma."""
    faltam = []
    for grupo, chave in ESSENCIAIS[plataforma]:
        v = lim.obter(plataforma, chave, grupo)
        if chave == "capitulos":
            if not isinstance(v, dict) or any(_num(v.get(k)) is None and not str(v.get(k) or "").strip() for k in CHAVES_DE_CAPITULOS):
                faltam.append(f"{grupo}.{chave}")
        elif _num(v) is None:
            faltam.append(f"{grupo}.{chave}")
    return faltam


def abrir_projeto(de: str | None):
    """Acha a DA (regra da casa: sem DA nada anda) e devolve (raiz, objeto DA)."""
    da = kit()
    da_json = da.achar(de=de or None)
    try:
        d = da.carregar(str(da_json), compilar=False)   # só leitura: não toca em da/build/
    except da.DAInvalida as e:
        raise Erro(f"A direção de arte do projeto está inválida: {e.mensagem}",
                   f"Corrija com a skill video-direcao-de-arte (python3 {KIT_FINAL}/da.py validar) antes de publicar.")
    return Path(da.raiz_do_projeto(da_json)).resolve(), d


# ─────────────────────────────────────────────────────────── caminhos do pacote ──
def canonica(nome: str) -> str:
    n = (nome or "").strip().lower()
    n = APELIDOS.get(n, n)
    if n not in PLATAFORMAS:
        raise ErroUso(f"Plataforma desconhecida: '{nome}'.",
                      "Use um dos nomes canônicos: " + ", ".join(PLATAFORMAS) + " (youtube = vídeo longo).")
    return n


def relativo(raiz: Path, caminho) -> str:
    """Caminho relativo à raiz do projeto, com barras normais (é o que vai para o meta.json)."""
    p = Path(str(caminho)).expanduser()
    if not p.is_absolute():
        # tenta relativo à pasta atual e, se não existir, relativo à raiz do projeto
        p = (Path.cwd() / p) if (Path.cwd() / p).exists() else (raiz / p)
    try:
        return p.resolve().relative_to(raiz).as_posix()
    except ValueError:
        raise ErroUso(f"{p} fica fora do projeto ({raiz}).",
                      "O pacote só aponta para arquivos dentro do projeto: copie ou exporte o arquivo para render/, cortes/ ou thumbs/.")


class Pacote:
    def __init__(self, raiz: Path, plataforma: str, sub: str | None = None):
        self.raiz, self.plataforma, self.sub = raiz, plataforma, sub
        self.pasta = raiz / "publicacao" / plataforma / sub if sub else raiz / "publicacao" / plataforma
        self.id = f"{plataforma}/{sub}" if sub else plataforma
        self.meta_path = self.pasta / "meta.json"
        self._meta = None

    @property
    def existe(self) -> bool:
        return self.meta_path.is_file()

    @property
    def meta(self) -> dict:
        if self._meta is None:
            m = ler_json(self.meta_path)
            if not isinstance(m, dict):
                raise Erro(f"{self.meta_path} não é um objeto JSON.", "Recrie com `pacote.py novo … --forcar`.")
            self._meta = m
        return self._meta

    def gravar(self) -> None:
        self.meta["atualizado_em"] = agora_iso()
        gravar_json(self.meta_path, self.meta)

    def rel(self, caminho: Path) -> str:
        return Path(caminho).resolve().relative_to(self.raiz).as_posix()

    def arquivo(self, chave: str) -> Path | None:
        v = self.meta.get(chave)
        return (self.raiz / v) if v else None


def listar_pacotes(raiz: Path) -> list[Pacote]:
    achados = []
    for plat in PLATAFORMAS:
        base = raiz / "publicacao" / plat
        if (base / "meta.json").is_file():
            achados.append(Pacote(raiz, plat))
        if base.is_dir():
            for sub in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
                if (sub / "meta.json").is_file():
                    achados.append(Pacote(raiz, plat, sub.name))
    return achados


def resolver_seletor(raiz: Path, seletor: str, deve_existir: bool = True) -> Pacote:
    """'shorts' = pacote padrão da plataforma; 'shorts/K02' = pacote do corte K02."""
    partes = [p for p in str(seletor).strip().strip("/").split("/") if p]
    if not partes or len(partes) > 2:
        raise ErroUso(f"Pacote inválido: '{seletor}'.", "Use <plataforma> ou <plataforma>/<corte>, por exemplo: youtube, shorts/K02.")
    plat = canonica(partes[0])
    padrao = Pacote(raiz, plat)
    if len(partes) == 1:
        pac = padrao
    else:
        sub = partes[1]
        pac = padrao if (padrao.existe and str(padrao.meta.get("corte") or "") == sub) else Pacote(raiz, plat, sub)
    if deve_existir and not pac.existe:
        existentes = ", ".join(p.id for p in listar_pacotes(raiz)) or "nenhum"
        raise Erro(f"Não existe pacote '{pac.id}' ({pac.meta_path}).",
                   f"Crie com: pacote.py novo {plat}" + (f" --corte {partes[1]}" if len(partes) == 2 else "")
                   + f"   (pacotes existentes: {existentes})")
    return pac


# ───────────────────────────────────────────────────────────────── insumos ──
RE_MARCADOR = re.compile(r"\[(F\d{2,}(?:\s*[,;]\s*F\d{2,})*)\]")


def marcadores(texto: str | None) -> list[str]:
    """Ids de fato citados como [F001] (ou [F001, F002])."""
    ids = []
    for grupo in RE_MARCADOR.findall(texto or ""):
        for i in re.split(r"\s*[,;]\s*", grupo):
            if i and i not in ids:
                ids.append(i)
    return ids


class Insumos:
    """O que as skills irmãs deixaram no projeto (tudo opcional; formatos em references/pacote.md)."""

    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.fatos_doc = ler_json_opcional(raiz / "pesquisa" / "fatos.json")
        self.licencas_doc = ler_json_opcional(raiz / "broll" / "licencas.json")
        self.storyboard = ler_json_opcional(raiz / "roteiro" / "storyboard.json")
        self.plano = ler_json_opcional(raiz / "cortes" / "plano.json")
        self.variacoes = ler_json_opcional(raiz / "thumbs" / "variacoes.json")
        roteiro = raiz / "roteiro" / "roteiro.md"
        self.roteiro = roteiro.read_text(encoding="utf-8", errors="replace") if roteiro.is_file() else None

    @property
    def fatos(self) -> dict[str, dict]:
        itens = (self.fatos_doc or {}).get("fatos") if isinstance(self.fatos_doc, dict) else None
        return {str(f.get("id")): f for f in (itens or []) if isinstance(f, dict) and f.get("id")}

    @property
    def itens_broll(self) -> list[dict]:
        itens = (self.licencas_doc or {}).get("itens") if isinstance(self.licencas_doc, dict) else None
        return [i for i in (itens or []) if isinstance(i, dict)]

    @property
    def cenas(self) -> list[dict]:
        cenas = (self.storyboard or {}).get("cenas") if isinstance(self.storyboard, dict) else None
        return [c for c in (cenas or []) if isinstance(c, dict)]

    @property
    def cortes(self) -> list[dict]:
        cortes = self.plano.get("cortes") if isinstance(self.plano, dict) else None
        return [c for c in cortes if isinstance(c, dict)] if isinstance(cortes, list) else []

    def corte(self, cid: str) -> dict | None:
        return next((c for c in self.cortes if str(c.get("id")) == str(cid)), None)

    def cortes_da_plataforma(self, plat: str) -> list[dict]:
        return [c for c in self.cortes if isinstance(c.get("plataformas"), list) and plat in c["plataformas"]]

    def cenas_do_recorte(self, meta: dict) -> set[str] | None:
        """Ids das cenas do storyboard cobertas por este pacote. None = não dá para saber
        (sem storyboard, ou corte cujas cenas não têm t0) → quem chama assume o projeto inteiro."""
        if not self.cenas:
            return None
        cid = meta.get("corte")
        if not cid:
            return {str(c.get("id")) for c in self.cenas}
        corte = self.corte(cid)
        if not corte or _num(corte.get("t0")) is None or _num(corte.get("t1")) is None:
            return None
        dentro = set()
        for c in self.cenas:
            t0, dur = _num(c.get("t0")), _num(c.get("dur"))
            if t0 is None or dur is None:
                return None
            if t0 < corte["t1"] and t0 + dur > corte["t0"]:
                dentro.add(str(c.get("id")))
        return dentro

    def fatos_citados(self, meta: dict) -> list[str]:
        ids = [str(i) for i in (meta.get("fato_ids") or [])]
        for campo in ("titulo", "abertura", "descricao"):
            ids += marcadores(meta.get(campo))
        cenas = self.cenas_do_recorte(meta)
        if not meta.get("corte"):
            ids += marcadores(self.roteiro)
        for c in self.cenas:
            if cenas is None and meta.get("corte"):
                break   # corte sem mapa de cenas: só valem os fatos declarados no pacote
            if cenas is None or str(c.get("id")) in cenas:
                ids += [str(i) for i in (c.get("fato_ids") or [])]
        vistos, saida = set(), []
        for i in ids:
            if i not in vistos:
                vistos.add(i)
                saida.append(i)
        return saida

    def cenas_por_broll(self) -> dict[str, list[str]]:
        """{id do b-roll: cenas} segundo o storyboard (campo `broll_id` de cada cena, que é do contrato)."""
        refs: dict[str, list[str]] = {}
        for c in self.cenas:
            if c.get("broll_id"):
                refs.setdefault(str(c["broll_id"]), []).append(str(c.get("id")))
        return refs

    @staticmethod
    def _usado_em(item: dict) -> list[str] | None:
        """`usado_em` como lista de ids de cena; None quando o campo não existe (não é o mesmo que lista vazia)."""
        v = item.get("usado_em")
        if v is None:
            return None
        if isinstance(v, (list, tuple)):
            return [str(c) for c in v if c is not None and str(c).strip()]
        return [str(v)] if str(v).strip() else []

    def uso_automatico(self, meta: dict) -> list[tuple[dict, str, list[str]]]:
        """Quais b-rolls aparecem na peça, SEM olhar a declaração manual (meta.broll_ids).

        Junta as duas fontes do contrato — `usado_em` de broll/licencas.json e `broll_id` das cenas do
        storyboard — porque uma pode estar desatualizada em relação à outra. Devolve [(item, evidência, cenas)]:
        'afirmado' = algum dos dois arquivos diz que aparece; 'presumido' = não dá para saber (campo `usado_em`
        ausente, corte sem mapa de cenas, cena fora do storyboard) e, na dúvida, o crédito entra."""
        e_corte = bool(meta.get("corte"))
        recorte = self.cenas_do_recorte(meta)                 # None = corte sem mapa de cenas (ou projeto sem storyboard)
        conhecidas = {str(c.get("id")) for c in self.cenas}
        refs = self.cenas_por_broll()
        saida = []
        for item in self.itens_broll:
            declaradas = self._usado_em(item)
            cenas = sorted(set(declaradas or []) | set(refs.get(str(item.get("id")), [])))
            if not cenas:
                if declaradas is None:                        # sem `usado_em` e sem cena apontando: não dá para afirmar que ficou de fora
                    saida.append((item, "presumido", []))
                continue
            if not e_corte:                                   # vídeo inteiro: usado em qualquer cena = aparece
                saida.append((item, "afirmado", cenas))
            elif recorte is None:
                saida.append((item, "presumido", cenas))
            else:
                dentro = [c for c in cenas if c in recorte]
                sem_tempo = [c for c in cenas if c not in conhecidas]     # cena que o storyboard não lista: não dá para excluir
                if dentro:
                    saida.append((item, "afirmado", dentro))
                elif sem_tempo:
                    saida.append((item, "presumido", sem_tempo))
        return saida

    def broll_em_uso(self, meta: dict) -> list[dict]:
        """Itens de b-roll que aparecem na peça deste pacote. Declaração explícita (meta.broll_ids)
        vence — e fica registrada quando tira um crédito obrigatório (ver creditos_excluidos)."""
        if isinstance(meta.get("broll_ids"), list):
            quer = {str(i) for i in meta["broll_ids"]}
            return [i for i in self.itens_broll if str(i.get("id")) in quer]
        return [item for item, _evidencia, _cenas in self.uso_automatico(meta)]

    def creditos_obrigatorios(self, meta: dict) -> list[dict]:
        return [i for i in self.broll_em_uso(meta) if i.get("exige_atribuicao")]

    def creditos_excluidos(self, meta: dict) -> list[tuple[dict, str, list[str]]]:
        """Itens com atribuição obrigatória que os insumos põem na peça e a declaração manual tirou."""
        if not isinstance(meta.get("broll_ids"), list):
            return []
        quer = {str(i) for i in meta["broll_ids"]}
        return [(item, ev, cenas) for item, ev, cenas in self.uso_automatico(meta)
                if item.get("exige_atribuicao") and str(item.get("id")) not in quer]

    def divergencias_de_broll(self, meta: dict) -> tuple[list[tuple[str, list[str]]], list[tuple[str, list[str]]]]:
        """(storyboard aponta para o item mas `usado_em` não lista a cena, storyboard aponta para id sem registro
        em broll/licencas.json) — só para as cenas desta peça."""
        recorte = self.cenas_do_recorte(meta) if meta.get("corte") else None
        por_id = {str(i.get("id")): i for i in self.itens_broll}
        fora_do_usado_em, sem_registro = [], []
        for bid, cenas in sorted(self.cenas_por_broll().items()):
            cenas = [c for c in cenas if recorte is None or c in recorte]
            if not cenas:
                continue
            if bid not in por_id:
                sem_registro.append((bid, cenas))
                continue
            declaradas = self._usado_em(por_id[bid])
            faltam = [c for c in cenas if declaradas is not None and c not in declaradas]
            if faltam:
                fora_do_usado_em.append((bid, faltam))
        return fora_do_usado_em, sem_registro


# ─────────────────────────────────────────────────────────── sondas de arquivo ──
def _bin(nome: str) -> str:
    """ffprobe/ffmpeg: a variável VIDEO_OPS_<NOME>, depois o PATH (shutil.which já acha o .exe no Windows)."""
    return os.environ.get(f"VIDEO_OPS_{nome.upper()}") or shutil.which(nome) or nome


def _fracao(v) -> float | None:
    try:
        if isinstance(v, str) and "/" in v:
            a, b = v.split("/", 1)
            return float(a) / float(b) if float(b) else None
        return float(v)
    except (TypeError, ValueError):
        return None


def moov_no_inicio(caminho: Path) -> bool | None:
    """True se o átomo moov vem antes do mdat (fast start); None se não for MP4/MOV legível."""
    try:
        tamanho_total = Path(caminho).stat().st_size
        with open(caminho, "rb") as f:
            pos = 0
            while pos + 8 <= tamanho_total:
                f.seek(pos)
                cab = f.read(8)
                if len(cab) < 8:
                    return None
                tam, tipo = struct.unpack(">I4s", cab)
                if tam == 1:
                    grande = f.read(8)
                    if len(grande) < 8:
                        return None
                    tam = struct.unpack(">Q", grande)[0]
                elif tam == 0:
                    tam = tamanho_total - pos
                if tipo == b"moov":
                    return True
                if tipo == b"mdat":
                    return False
                if tam < 8:
                    return None
                pos += tam
    except OSError:
        return None
    return None


def sondar_video(caminho: Path) -> dict:
    """ffprobe (leve; não entra na trava) → medidas usadas pela validação."""
    caminho = Path(caminho)
    cmd = [_bin("ffprobe"), "-v", "error", "-show_entries",
           "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,avg_frame_rate,sample_rate,"
           "channels,bit_rate,duration,field_order:stream_side_data=rotation:format=format_name,duration,size,bit_rate",
           "-of", "json", str(caminho)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except FileNotFoundError:
        raise Erro("ffprobe não encontrado.",
                   "Instale o ffmpeg pelo preparar.py desta skill (--instalar) ou aponte VIDEO_OPS_FFPROBE para ele.")
    except subprocess.TimeoutExpired:
        raise Erro(f"ffprobe demorou mais de 60 s para ler {caminho}.", "Confira se o arquivo não está corrompido ou num disco de rede.")
    if r.returncode != 0:
        raise Erro(f"ffprobe não conseguiu ler {caminho}: {r.stderr.strip()[-300:] or 'erro desconhecido'}",
                   "O arquivo está corrompido ou não é vídeo: exporte de novo.")
    dados = json.loads(r.stdout or "{}")
    fmt = dados.get("format") or {}
    video = next((s for s in dados.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in dados.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None:
        raise Erro(f"{caminho} não tem trilha de vídeo.", "Exporte de novo o arquivo final.")
    larg, alt = int(video.get("width") or 0), int(video.get("height") or 0)
    rot = 0
    for sd in video.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(_fracao(sd["rotation"]) or 0)
    if abs(rot) % 180 == 90:
        larg, alt = alt, larg
    dur = _fracao(fmt.get("duration")) or _fracao(video.get("duration")) or 0.0
    tamanho = int(_fracao(fmt.get("size")) or caminho.stat().st_size)
    taxa_video = _fracao(video.get("bit_rate"))
    return {
        "largura": larg, "altura": alt, "duracao": round(dur, 3),
        "fps": round(_fracao(video.get("avg_frame_rate")) or _fracao(video.get("r_frame_rate")) or 0.0, 3),
        "codec_video": video.get("codec_name"), "perfil": video.get("profile"), "pix_fmt": video.get("pix_fmt"),
        "varredura": video.get("field_order"), "bitrate_video_kbps": round(taxa_video / 1000) if taxa_video else None,
        "container": fmt.get("format_name"), "extensao": caminho.suffix.lower(), "tamanho_bytes": tamanho,
        "tem_audio": audio is not None,
        "codec_audio": audio.get("codec_name") if audio else None,
        "taxa_amostragem_hz": int(_fracao(audio.get("sample_rate")) or 0) if audio else None,
        "canais": audio.get("channels") if audio else None,
        "moov_no_inicio": moov_no_inicio(caminho),
    }


def sondar_imagem(caminho: Path) -> dict:
    try:
        from PIL import Image
    except ImportError:
        raise Erro("Este Python não tem o Pillow, necessário para conferir a thumbnail.",
                   "Rode com o Python da linha PYTHON= do preparar.py (gravado em ~/.criabr/ambiente.json): é ele que tem Pillow e numpy.")
    try:
        with Image.open(caminho) as im:
            return {"largura": im.width, "altura": im.height, "formato": (im.format or "").upper(),
                    "tamanho_bytes": Path(caminho).stat().st_size}
    except Exception as e:  # PIL levanta vários tipos
        raise Erro(f"Não consegui abrir a imagem {caminho}: {e}", "Gere a thumbnail de novo pelo kit da direção de arte (receita em kit-api.md §17.1).")


RE_TEMPO_SRT = re.compile(r"^\s*(\d{1,3}):(\d{2}):(\d{2})([,.])(\d{1,3})\s*-->\s*(\d{1,3}):(\d{2}):(\d{2})([,.])(\d{1,3})(?:\s+.*)?$")


def analisar_srt(caminho: Path) -> dict:
    """Lê um .srt e devolve {'cues': [(t0, t1, texto)], 'problemas': [(severidade, mensagem)]}."""
    problemas: list[tuple[str, str]] = []
    try:
        texto = Path(caminho).read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"cues": [], "problemas": [("erro", "o arquivo não está em UTF-8 (acentos vão sair trocados)")]}
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for n, bloco in enumerate([b for b in re.split(r"\n[ \t]*\n", texto) if b.strip()], 1):
        linhas = [ln.rstrip() for ln in bloco.split("\n")]
        while linhas and not linhas[0].strip():
            linhas.pop(0)
        i = 0
        if not RE_TEMPO_SRT.match(linhas[0]):
            if not linhas[0].strip().isdigit():
                problemas.append(("erro", f"bloco {n}: esperava o número da legenda ou a linha de tempo, veio «{linhas[0][:40]}»"))
                continue
            i = 1
        if i >= len(linhas) or not RE_TEMPO_SRT.match(linhas[i]):
            problemas.append(("erro", f"bloco {n}: linha de tempo ausente ou fora do formato HH:MM:SS,mmm --> HH:MM:SS,mmm"))
            continue
        if i == 0:
            problemas.append(("aviso", f"bloco {n}: falta o número da legenda antes da linha de tempo"))
        m = RE_TEMPO_SRT.match(linhas[i])
        if m.group(4) == "." or m.group(9) == ".":
            problemas.append(("erro", f"bloco {n}: milissegundos separados por ponto (isso é WebVTT); no .srt o separador é vírgula"))
        t0 = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(5).ljust(3, "0")) / 1000
        t1 = int(m.group(6)) * 3600 + int(m.group(7)) * 60 + int(m.group(8)) + int(m.group(10).ljust(3, "0")) / 1000
        corpo = "\n".join(linhas[i + 1:]).strip()
        if t1 <= t0:
            problemas.append(("erro", f"bloco {n}: o fim ({fmt_tempo(t1)}) não é depois do início ({fmt_tempo(t0)})"))
        if not corpo:
            problemas.append(("aviso", f"bloco {n}: legenda sem texto"))
        if cues and t0 < cues[-1][0]:
            problemas.append(("erro", f"bloco {n}: começa antes do bloco anterior (tempos fora de ordem)"))
        elif cues and t0 < cues[-1][1] - 0.001:
            problemas.append(("aviso", f"bloco {n}: sobrepõe o bloco anterior em {cues[-1][1] - t0:.2f} s".replace(".", ",")))
        cues.append((t0, t1, corpo))
    if not cues and not problemas:
        problemas.append(("erro", "nenhuma legenda no arquivo"))
    return {"cues": cues, "problemas": problemas}


# ──────────────────────────────────────────────────────────────── capítulos ──
RE_LINHA_CAP = re.compile(r"^\s*(?:[-*•]\s*)?\(?(\d{1,2}(?::\d{2}){1,2})\)?\s*(?:[-–—:|]\s*)?(.+?)\s*$")


def tempo_para_segundos(txt: str) -> int:
    """«mm:ss» ou «h:mm:ss» → segundos. Segundos (e minutos, quando há horas) acima de 59 são erro de digitação,
    não «00:75 = 01:15»."""
    partes = [int(p) for p in txt.split(":")]
    if partes[-1] > 59:
        raise ErroUso(f"Tempo impossível: «{txt}» tem {partes[-1]} segundos.", "Os segundos vão de 00 a 59 (75 s depois do início é 01:15).")
    if len(partes) == 2:
        return partes[0] * 60 + partes[1]
    if partes[1] > 59:
        raise ErroUso(f"Tempo impossível: «{txt}» tem {partes[1]} minutos depois das horas.", "No formato h:mm:ss os minutos vão de 00 a 59.")
    return partes[0] * 3600 + partes[1] * 60 + partes[2]


def ler_lista_de_capitulos(linhas: list[str]) -> list[dict]:
    caps = []
    for n, linha in enumerate(linhas, 1):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        m = RE_LINHA_CAP.match(linha)
        if not m:
            if re.match(r"^\s*(?:[-*•]\s*)?\(?\d{3,}:\d{2}\b", linha):
                raise ErroUso(f"Linha {n}: «{linha.strip()[:60]}» tem mais de 99 minutos no formato mm:ss.",
                              "Depois de 59:59 o YouTube usa h:mm:ss: 100 minutos se escreve 1:40:00.")
            raise ErroUso(f"Linha {n} não está no formato «mm:ss Título» (ou «h:mm:ss Título»): «{linha.strip()[:60]}»",
                          "Exemplo de lista válida: \"00:00 Abertura\" \"01:12 O que é um token\" \"03:40 Na prática\".")
        caps.append({"t": tempo_para_segundos(m.group(1)), "titulo": nfc(m.group(2).strip())})
    return caps


def normalizar_capitulos(bruto) -> list[dict]:
    """Aceita [{"t": s, "titulo": "…"}] (contrato de render/capitulos.json); t vira segundo inteiro."""
    if isinstance(bruto, dict) and isinstance(bruto.get("capitulos"), list):
        bruto = bruto["capitulos"]
    if not isinstance(bruto, list):
        raise Erro("Capítulos em formato inesperado (esperava uma lista de {\"t\": segundos, \"titulo\": \"…\"}).",
                   "Confira render/capitulos.json (dono: video-montagem) ou passe --lista.")
    caps = []
    for n, c in enumerate(bruto, 1):
        if not isinstance(c, dict) or _num(c.get("t")) is None or not str(c.get("titulo") or "").strip():
            raise Erro(f"Capítulo {n} inválido: {json.dumps(c, ensure_ascii=False)[:80]}",
                       "Cada capítulo precisa de \"t\" (segundos) e \"titulo\".")
        if c["t"] < 0:
            raise Erro(f"Capítulo {n} («{str(c['titulo']).strip()[:40]}») tem tempo negativo: t = {c['t']}.",
                       "O tempo é contado em segundos desde o início do vídeo; peça à skill video-montagem para remapear os capítulos.")
        caps.append({"t": int(c["t"]), "titulo": nfc(str(c["titulo"]).strip())})
    return caps


def conferir_capitulos(caps: list[dict], lim: Limites, duracao: float | None = None) -> list[tuple[str, str, str]]:
    """Regras oficiais do YouTube lidas de limites_texto.youtube.capitulos. Devolve [(id, severidade, mensagem)]."""
    regras = lim.obter("youtube", "capitulos") or {}
    if not isinstance(regras, dict):
        regras = lim.secao("limites_texto", "youtube").get("capitulos") or {}
    minimo = _num(regras.get("min_timestamps"))
    dur_min = _num(regras.get("duracao_min_capitulo_s"))
    primeiro = str(regras.get("primeiro_timestamp") or "")
    saida = []
    if not caps:
        return saida
    if primeiro:
        esperado = tempo_para_segundos(primeiro)
        if caps[0]["t"] != esperado:
            saida.append(("capitulos.primeiro", "erro",
                          f"o primeiro capítulo começa em {fmt_tempo(caps[0]['t'])}; o YouTube exige {primeiro}"))
    if minimo and len(caps) < minimo:
        saida.append(("capitulos.quantidade", "erro", f"há {len(caps)} capítulo(s); o YouTube exige ao menos {int(minimo)}"))
    for a, b in zip(caps, caps[1:]):
        if b["t"] <= a["t"]:
            saida.append(("capitulos.ordem", "erro",
                          f"«{b['titulo']}» ({fmt_tempo(b['t'])}) não vem depois de «{a['titulo']}» ({fmt_tempo(a['t'])}): a ordem tem de ser crescente"))
        elif dur_min and b["t"] - a["t"] < dur_min:
            saida.append(("capitulos.duracao", "erro",
                          f"«{a['titulo']}» dura {b['t'] - a['t']} s; o mínimo por capítulo é {int(dur_min)} s"))
    if duracao:
        ultimo = caps[-1]
        if ultimo["t"] >= duracao:
            saida.append(("capitulos.fora", "erro",
                          f"«{ultimo['titulo']}» começa em {fmt_tempo(ultimo['t'])}, depois do fim do vídeo ({fmt_dur(duracao)})"))
        elif dur_min and duracao - ultimo["t"] < dur_min:
            saida.append(("capitulos.duracao", "erro",
                          f"o último capítulo («{ultimo['titulo']}») dura {duracao - ultimo['t']:.0f} s; o mínimo é {int(dur_min)} s"))
    for c in caps:
        if "<" in c["titulo"] or ">" in c["titulo"]:
            saida.append(("capitulos.caracteres", "erro", f"«{c['titulo']}» tem < ou >, proibidos na descrição do YouTube"))
    return saida


def formatar_capitulos(caps: list[dict]) -> list[str]:
    com_horas = any(c["t"] >= 3600 for c in caps)
    return [f"{fmt_tempo(c['t'], com_horas)} {c['titulo']}" for c in caps]


# ──────────────────────────────────────────────────────────────── descrição ──
RE_HASHTAG = re.compile(r"(?<![\w&/])#(?=\w*[^\W\d_])(\w+)")
RE_MENCAO = re.compile(r"(?<![\w.])@([A-Za-z0-9_](?:[A-Za-z0-9_.]*[A-Za-z0-9_])?)")
RE_LINK_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def normalizar_hashtag(h: str) -> str:
    h = nfc(str(h).strip())
    if not h:
        raise ErroUso("Hashtag vazia.")
    if not h.startswith("#"):
        h = "#" + h
    if re.search(r"\s", h):
        raise ErroUso(f"Hashtag com espaço: «{h}».", "Hashtag não tem espaço: junte as palavras (#InteligenciaArtificial).")
    if not RE_HASHTAG.fullmatch(h):
        raise ErroUso(f"Hashtag inválida: «{h}».", "Use só letras, números e _ depois do #, com pelo menos uma letra.")
    return h


def separar_hashtags(valores: list[str] | None) -> list[str]:
    tags = []
    for v in valores or []:
        for pedaco in re.split(r"[\s,]+", v.strip()):
            if pedaco:
                h = normalizar_hashtag(pedaco)
                if h.lower() not in [t.lower() for t in tags]:
                    tags.append(h)
    return tags


def markdown_para_texto(md: str) -> str:
    """fontes.md → texto puro para descrição (sem #, sem [texto](url), sem <url>, sem ** e `)."""
    linhas = []
    for linha in md.replace("\r\n", "\n").split("\n"):
        linha = RE_LINK_MD.sub(lambda m: f"{m.group(1)}: {m.group(2)}" if m.group(1) != m.group(2) else m.group(2), linha)
        linha = re.sub(r"<(https?://[^>\s]+)>", r"\1", linha)
        linha = re.sub(r"(\*\*|__|`)", "", linha)
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", linha)
        if m:
            linha = m.group(1).rstrip("# ").strip()
        linha = re.sub(r"^(\s*)[*+]\s+", r"\1- ", linha)
        linhas.append(linha.rstrip())
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    return nfc(texto)


def bloco_fontes(ins: Insumos, meta: dict, modo: str) -> tuple[str, str]:
    """Devolve (texto, origem). modo: auto | fontes-md | fatos | nenhuma."""
    if modo == "nenhuma":
        return "", "nenhuma"
    fontes_md = ins.raiz / "pesquisa" / "fontes.md"
    if modo in ("auto", "fontes-md") and fontes_md.is_file():
        texto = markdown_para_texto(fontes_md.read_text(encoding="utf-8", errors="replace"))
        linhas = texto.split("\n")
        if linhas and re.fullmatch(r"(?i)fontes?(\s.*)?:?", linhas[0].strip()):   # o título do bloco já diz "Fontes"
            texto = "\n".join(linhas[1:]).strip()
        return texto, "pesquisa/fontes.md"
    if modo == "fontes-md":
        raise Erro("pesquisa/fontes.md não existe.", "Gere com a skill video-pesquisa-ia ou use --fontes fatos.")
    vistos, linhas = set(), []
    for fid in ins.fatos_citados(meta):
        fontes = (ins.fatos.get(fid) or {}).get("fontes")
        for fonte in fontes if isinstance(fontes, list) else []:
            if not isinstance(fonte, dict):
                continue
            url = str(fonte.get("url") or "").strip()
            if not url or url in vistos:
                continue
            vistos.add(url)
            rotulo = " — ".join(x for x in (str(fonte.get("titulo") or "").strip(), str(fonte.get("editor") or "").strip()) if x)
            linhas.append(f"- {rotulo}: {url}" if rotulo else f"- {url}")
    return nfc("\n".join(linhas)), "pesquisa/fatos.json (fatos citados)"


def bloco_creditos(ins: Insumos, meta: dict, modo: str = "obrigatorios") -> str:
    itens = ins.broll_em_uso(meta) if modo == "todos" else ins.creditos_obrigatorios(meta)
    linhas = []
    for item in itens:
        texto = " ".join(str(item.get("atribuicao") or "").split())
        if texto and texto not in linhas:
            linhas.append(texto)
    return nfc("\n".join(f"- {t}" for t in linhas))


def montar_descricao(pac: Pacote, ins: Insumos, lim: Limites) -> tuple[str, dict]:
    """Monta o texto final a partir dos campos do meta.json. Devolve (texto, relatório dos blocos)."""
    meta = pac.meta
    ordem = meta.get("blocos") or list(BLOCOS_PADRAO[pac.plataforma])
    partes, rel = [], {}
    for bloco in ordem:
        texto = ""
        if bloco == "abertura":
            texto = nfc(str(meta.get("abertura") or "").strip())
        elif bloco == "capitulos":
            if meta.get("capitulos"):
                texto = TITULO_BLOCO["capitulos"] + ":\n" + "\n".join(formatar_capitulos(normalizar_capitulos(meta["capitulos"])))
        elif bloco == "fontes":
            corpo, origem = bloco_fontes(ins, meta, meta.get("fontes_modo") or "auto")
            rel["fontes_origem"] = origem
            if corpo:
                texto = TITULO_BLOCO["fontes"] + ":\n" + corpo
        elif bloco == "creditos":
            corpo = bloco_creditos(ins, meta, meta.get("creditos_modo") or "obrigatorios")
            if corpo:
                texto = TITULO_BLOCO["creditos"] + ":\n" + corpo
        elif bloco == "links":
            linhas = [f"{l.get('rotulo')}: {l.get('url')}" if l.get("rotulo") else str(l.get("url"))
                      for l in (meta.get("links") or []) if isinstance(l, dict) and l.get("url")]
            if meta.get("assinatura"):
                linhas.append(str(meta["assinatura"]))
            texto = nfc("\n".join(linhas))
        elif bloco == "hashtags":
            texto = " ".join(str(h) for h in (meta.get("hashtags") or []) if str(h).strip())
        rel[bloco] = bool(texto)
        if texto:
            partes.append(texto)
    return "\n\n".join(partes).strip() + ("\n" if partes else ""), rel


# ──────────────────────────────────────────────────────────────── validação ──
class Achados:
    def __init__(self):
        self.itens: list[dict] = []

    def _por(self, sev, id_, cat, msg, como=""):
        self.itens.append({"id": id_, "categoria": cat, "severidade": sev, "mensagem": msg, "como_corrigir": como})

    def erro(self, id_, cat, msg, como=""):
        self._por("erro", id_, cat, msg, como)

    def aviso(self, id_, cat, msg, como=""):
        self._por("aviso", id_, cat, msg, como)

    def info(self, id_, cat, msg, como=""):
        self._por("info", id_, cat, msg, como)

    def conta(self, sev: str) -> int:
        return sum(1 for i in self.itens if i["severidade"] == sev)


def _proporcao_principal(txt) -> float | None:
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*:\s*(\d+(?:[.,]\d+)?)", str(txt or ""))
    if not m:
        return None
    a, b = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
    return a / b if b else None


_CODECS = (("h.264", "h264"), ("h264", "h264"), ("avc", "h264"), ("hevc", "hevc"), ("h.265", "hevc"), ("h265", "hevc"),
           ("vp8", "vp8"), ("vp9", "vp9"), ("av1", "av1"), ("prores", "prores"))
_AUDIOS = (("aac", "aac"), ("opus", "opus"), ("mp3", "mp3"), ("pcm", "pcm"))


def _codecs_citados(txt, tabela=_CODECS) -> set[str]:
    baixo = str(txt or "").lower()
    return {nome for chave, nome in tabela if chave in baixo}


def _containers_citados(txt) -> set[str]:
    baixo = str(txt or "").lower()
    return {c for c in ("mp4", "mov", "webm") if re.search(rf"\b{c}\b", baixo)}


def contar_tags(tags: list[str]) -> int:
    """Regra da API do YouTube: a lista inteira conta — vírgulas entre as tags e, em tag com espaço,
    as aspas que a API acrescenta."""
    if not tags:
        return 0
    return sum(conta_utf16(t) + (2 if " " in t else 0) for t in tags) + (len(tags) - 1)


def texto_publico(plataforma: str, meta: dict) -> str:
    """O texto que a plataforma vai ler: título + descrição no YouTube; só a legenda nas outras."""
    if plataforma in ("youtube", "shorts"):
        return f"{meta.get('titulo') or ''}\n{meta.get('descricao') or ''}"
    return str(meta.get("descricao") or "")


def impressao(pac: Pacote) -> dict:
    """Impressão digital do que foi validado: se algo mudar depois, a validação fica desatualizada."""
    meta = {k: v for k, v in pac.meta.items() if k not in ("atualizado_em",)}
    imp = {"meta_sha256": sha256_bytes(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8"))}
    for chave in ("arquivo_video", "thumbnail", "legenda_srt"):
        arq = pac.arquivo(chave)
        if arq and arq.is_file():
            st = arq.stat()
            imp[chave] = {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
            if chave != "arquivo_video":
                imp[chave]["sha256"] = sha256_arquivo(arq)
        else:
            imp[chave] = None
    txt = pac.pasta / "descricao.txt"
    imp["descricao_txt_sha256"] = sha256_arquivo(txt) if txt.is_file() else None
    return imp


def conferir_qa(raiz: Path, da_sha: str, video: Path | None, outros: list[Path]) -> tuple[list[str], list[tuple[str, str]], dict]:
    """Portão de QA: lê o qa/relatorio.json que `da conferencia` (kit da direção de arte) grava.
    Devolve (motivos de reprovação, avisos [(id, mensagem)], resumo do relatório)."""
    rel = raiz / "qa" / "relatorio.json"
    if not rel.is_file():
        return (["qa/relatorio.json não existe: o QA (`da conferencia`) ainda não rodou neste projeto"], [], {"relatorio": None})
    try:
        r = ler_json(rel)
    except Erro as e:
        return ([f"qa/relatorio.json ilegível ({e.mensagem})"], [], {"relatorio": "qa/relatorio.json"})
    if not isinstance(r, dict):
        return ([f"qa/relatorio.json não é um objeto JSON (veio {type(r).__name__}): não dá para ler o resultado do QA"], [],
                {"relatorio": "qa/relatorio.json"})
    motivos, avisos = [], []
    resumo = {"relatorio": "qa/relatorio.json", "ok": r.get("ok"), "verificado_em": r.get("verificado_em"),
              "da_sha256": r.get("da_sha256"), "resumo": r.get("resumo")}
    itens = r.get("itens") if isinstance(r.get("itens"), list) else []
    erros_qa = [i for i in itens if isinstance(i, dict) and i.get("severidade") == "erro"]
    if r.get("ok") is not True:
        n = r["resumo"].get("erros", len(erros_qa)) if isinstance(r.get("resumo"), dict) else len(erros_qa)
        motivos.append(f"o QA reprovou o projeto (ok = {json.dumps(r.get('ok'))}; {n} erro(s) em qa/relatorio.md)")
    elif erros_qa:
        motivos.append(f"qa/relatorio.json diz ok = true mas lista {len(erros_qa)} item(ns) com severidade erro")
    if not r.get("da_sha256"):
        motivos.append("qa/relatorio.json não traz da_sha256: não dá para saber contra qual direção de arte o QA rodou")
    elif r.get("da_sha256") != da_sha:
        motivos.append(f"o QA foi feito com outra direção de arte (relatório {str(r.get('da_sha256'))[:8]}…, DA atual {da_sha[:8]}…)")
    # O relatório só libera o arquivo que conferiu: `da conferencia --corte K01` sai ok sem dizer nada sobre
    # render/final.mp4, e um projeto sem entregável também sai ok (alvos: []).
    alvos = r.get("alvos")
    if not isinstance(alvos, list):
        motivos.append("qa/relatorio.json não traz a lista `alvos`: não dá para saber quais arquivos o QA conferiu "
                       "(o relatório de `da conferencia` sempre traz)")
    else:
        conferidos = {nfc(str(a.get("arquivo") or "")).replace("\\", "/"): a for a in alvos if isinstance(a, dict)}
        resumo["alvos"] = sorted(conferidos)
        if video is not None and video.is_file():
            try:
                rel_video = nfc(video.resolve().relative_to(raiz.resolve()).as_posix())
            except ValueError:
                rel_video = nfc(video.as_posix())
            alvo = conferidos.get(rel_video)
            if alvo is None:
                motivos.append(f"{rel_video} não está entre os arquivos que o QA conferiu (alvos do relatório: "
                               f"{', '.join(sorted(conferidos)) or 'nenhum'}): o relatório não diz nada sobre ele")
            elif (alvo.get("bytes") not in (None, video.stat().st_size)
                  or str(alvo.get("sha256") or "").lower() != sha256_em_cache(video)):
                motivos.append(f"{rel_video} não é mais o arquivo que o QA conferiu (sha256 diferente do registrado em `alvos`): "
                               "foi regravado depois da conferência")
    quando = None
    try:
        quando = datetime.fromisoformat(str(r.get("verificado_em")))
    except (TypeError, ValueError):
        motivos.append("qa/relatorio.json sem verificado_em válido (ISO 8601): não dá para saber se o QA é posterior ao vídeo")
    if quando is not None:
        sem_fuso = quando.tzinfo is None
        if sem_fuso:
            quando = quando.astimezone()
            avisos.append(("qa.fuso", f"verificado_em do QA ({r.get('verificado_em')}) não tem fuso horário; foi lido como hora local desta máquina"))
        dito = quando.isoformat(timespec="seconds")
        dica_fuso = " — hora gravada em UTC sem fuso é a causa mais comum" if sem_fuso else ""
        # O portão compara a data DECLARADA pelo QA com a data do vídeo; uma data adiantada (relógio errado, UTC lido
        # como hora local) faria todo reexport passar. Por isso ela não pode estar à frente nem do relógio nem do
        # próprio arquivo do relatório (que foi gravado, no máximo, naquele instante).
        gravado = rel.stat().st_mtime
        if quando.timestamp() > agora().timestamp() + TOLERANCIA_RELOGIO_S:
            motivos.append(f"a data do QA ({dito}) está no futuro: não serve para provar que o QA é posterior ao vídeo{dica_fuso}")
        elif quando.timestamp() > gravado + TOLERANCIA_RELOGIO_S:
            feito = datetime.fromtimestamp(gravado).astimezone().isoformat(timespec="seconds")
            motivos.append(f"a data do QA ({dito}) é posterior à gravação do próprio qa/relatorio.json ({feito}): data incoerente{dica_fuso}")
        if video is not None and video.is_file() and video.stat().st_mtime > quando.timestamp() + 1:
            feito = datetime.fromtimestamp(video.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            motivos.append(f"o arquivo de vídeo ({video.name}, gravado em {feito}) é mais novo que o QA ({dito})")
        for arq in outros:
            if arq and arq.is_file() and arq.stat().st_mtime > quando.timestamp() + 1:
                avisos.append(("qa.depois", f"{arq.name} foi alterado depois do QA"))
    return motivos, avisos, resumo


def estado_da_da(da_obj) -> tuple[bool, str]:
    """(aprovada?, situação em palavras). Único ponto que lê a aprovação da DA no objeto do kit."""
    meta = getattr(da_obj, "meta", None) or {}
    aprovada = getattr(da_obj, "aprovada", None)
    if aprovada is None:                                   # kit sem a propriedade: lê os mesmos campos
        aprovada = bool(meta.get("aprovada")) and not meta.get("alterada_apos_aprovacao")
    if aprovada:
        return True, "aprovada"
    if meta.get("aprovada") and meta.get("alterada_apos_aprovacao"):
        return False, "foi alterada depois de aprovada"
    return False, "ainda não foi aprovada"


def validar_pacote(pac: Pacote, lim: Limites, ins: Insumos, da_obj, sem_qa: bool = False, motivo_sem_qa: str | None = None) -> dict:
    """Confere um pacote inteiro. Não levanta exceção por conteúdo ruim: tudo vira item do relatório."""
    A = Achados()
    meta, plat, raiz = pac.meta, pac.plataforma, pac.raiz
    T = lambda chave: lim.obter(plat, chave, "limites_texto")      # noqa: E731
    S = lambda chave: lim.obter(plat, chave, "specs")              # noqa: E731
    refazer = f"pacote.py descricao {pac.id}"
    medidas: dict = {}
    excecoes: list[dict] = []
    ref_agora = agora()

    # ── a fundação: DA aprovada e limites que existem
    aprovada, situacao = estado_da_da(da_obj)
    if not aprovada:
        A.erro("da.aprovada", "da", f"a direção de arte (revisão {(getattr(da_obj, 'meta', None) or {}).get('revisao', '?')}) {situacao}: "
                                    "o QA de publicação exige DA aprovada, e abrir revisão não muda o da_sha256 que o portão compara",
               f"Mostre a DA ao usuário e, com o «sim» dele, rode `{KIT_FINAL}/bin/da aprovar` (se ela foi alterada: `revisar`, depois `aprovar`, "
               "e o QA de novo). Aprovar a DA é decisão do usuário, nunca sua.")
    faltam = limites_que_faltam(lim, plat)
    if faltam:
        A.erro("limites.ausentes", "limites",
               f"os limites essenciais de {NOME_PLATAFORMA[plat]} não foram encontrados em plataformas.json ({', '.join(faltam)}): "
               "sem eles o pacote passaria sem ser conferido",
               f"O arquivo de limites mudou de forma ou está incompleto ({lim.origem}). Atualize a skill video-direcao-de-arte; se as seções "
               "mudaram de nome, a tabela SECOES de pacote.py precisa acompanhar.")

    # ── o próprio pacote
    if meta.get("plataforma") != plat:
        A.erro("pacote.plataforma", "pacote", f"meta.json diz plataforma «{meta.get('plataforma')}» mas está na pasta de «{plat}»",
               f"Recrie com `pacote.py novo {plat} --forcar`.")
    faltando = [c for c in ("versao", "plataforma", "titulo", "descricao", "tags", "hashtags", "capitulos", "arquivo_video",
                            "thumbnail", "legenda_srt", "privacidade", "agendar_para", "idioma") if c not in meta]
    if faltando:
        A.erro("pacote.campos", "pacote", "meta.json sem os campos do contrato: " + ", ".join(faltando),
               f"Recrie com `pacote.py novo {plat} --forcar` (os campos não podem ser removidos nem renomeados).")
    for outro in listar_pacotes(raiz) if meta.get("arquivo_video") else []:
        try:
            mesmo = outro.id != pac.id and outro.plataforma == plat and outro.meta.get("arquivo_video") == meta["arquivo_video"]
        except Erro:
            mesmo = False
        if mesmo:
            A.aviso("pacote.duplicado", "pacote", f"o pacote «{outro.id}» aponta para o mesmo arquivo ({meta['arquivo_video']}) nesta plataforma",
                    f"Publicar os dois é postar o mesmo vídeo duas vezes: fique com um e apague a pasta do outro ({outro.rel(outro.pasta)}/).")
    for campo, tipo, nome_tipo in (("titulo", str, "texto"), ("descricao", str, "texto"), ("tags", list, "lista"), ("hashtags", list, "lista"),
                                   ("capitulos", list, "lista")):
        if campo in meta and meta[campo] is not None and not isinstance(meta[campo], tipo):
            A.erro("pacote.tipo", "pacote", f"meta.json: `{campo}` deveria ser {nome_tipo} e é {type(meta[campo]).__name__}",
                   "Corrija o tipo no meta.json (listas entre colchetes) ou use as opções de `pacote.py descricao`.")
            meta = dict(meta, **{campo: tipo()})          # segue a conferência com o campo vazio
    titulo, descricao = str(meta.get("titulo") or ""), str(meta.get("descricao") or "")
    tags = [str(t) for t in (meta.get("tags") or [])]
    hashtags = [str(h) for h in (meta.get("hashtags") or [])]
    publico = texto_publico(plat, meta)
    if nfc(publico) != publico:
        A.aviso("texto.nfd", "texto", "o texto tem acentos decompostos (NFD): ocupa mais caracteres e bytes do que parece",
                f"Rode `{refazer}` de novo: ele grava tudo em NFC.")

    # ── texto: título
    if plat in ("youtube", "shorts"):
        if not titulo.strip():
            A.erro("titulo.vazio", "texto", "título vazio (a API recusa com invalidTitle)",
                   f"Escreva o título (references/copy.md) e grave com `{refazer} --titulo \"…\"`.")
        maxt = _num(T("titulo_max_caracteres"))
        if maxt is None:
            A.info("titulo.limite", "limites", "limite de título não encontrado em plataformas.json; tamanho não conferido")
        elif conta_utf16(titulo) > maxt:
            A.erro("titulo.tamanho", "texto", f"título com {conta_utf16(titulo)} caracteres; o limite é {int(maxt)}",
                   f"Corte {conta_utf16(titulo) - int(maxt)} caractere(s): `{refazer} --titulo \"…\"`.")
        visivel = T("titulo_visivel_estimado_caracteres")
        if isinstance(visivel, list) and visivel and conta_utf16(titulo) > max(visivel):
            A.info("titulo.visivel", "texto", f"o título passa de {max(visivel)} caracteres; antes do corte aparece só «{titulo[:min(visivel)]}…» (estimativa)",
                   "Ponha a promessa e a palavra-chave nesses primeiros caracteres.")

    # ── texto: descrição / legenda
    proibidos = T("caracteres_proibidos") or []
    for campo, valor in (("título", titulo), ("descrição", descricao)):
        usados = [c for c in proibidos if c in valor]
        if usados and (plat in ("youtube", "shorts")):
            A.erro("texto.proibidos", "texto", f"{campo} com caractere proibido: {' '.join(usados)}",
                   "Troque < e > por palavras («menor que», «→») e remova os <> em volta de links.")
    regras_desc = {"youtube": (("descricao_max_caracteres", "caracteres"), ("descricao_max_bytes_api", "bytes")),
                   "shorts": (("descricao_max_caracteres", "caracteres"), ("descricao_max_bytes_api", "bytes")),
                   "reels": (("legenda_max_caracteres", "caracteres"),),
                   "tiktok": (("legenda_max_caracteres_api", "caracteres"), ("legenda_max_caracteres_app", "caracteres"))}[plat]
    nome_campo = "descrição" if plat in ("youtube", "shorts") else "legenda"
    achou_limite = False
    for chave, unidade in regras_desc:
        maximo = _num(T(chave))
        if maximo is None:
            continue
        achou_limite = True
        medido = conta_bytes(descricao) if unidade == "bytes" else conta_utf16(descricao)
        medidas[f"descricao_{unidade}"] = medido
        if medido > maximo:
            oficial = lim.oficial(plat, chave)
            detalhe = (f"{nome_campo} com {fmt_int(medido)} bytes em UTF-8 ({fmt_int(conta_utf16(descricao))} caracteres; acento pesa 2 bytes, emoji 4); o limite da API é {fmt_int(maximo)} bytes"
                       if unidade == "bytes" else f"{nome_campo} com {fmt_int(medido)} caracteres; o limite é {fmt_int(maximo)} ({chave})")
            como = f"Encurte {fmt_int(medido - maximo)} {unidade} (abertura e fontes costumam ser os blocos maiores) e rode `{refazer}`."
            (A.erro if oficial else A.aviso)(f"descricao.{unidade}" + ("" if oficial else ".estimativa"), "texto",
                                             detalhe + ("" if oficial else " — limite estimado, não oficial"), como)
    if not achou_limite:
        A.info("descricao.limite", "limites", f"limite de {nome_campo} não encontrado em plataformas.json; tamanho não conferido")
    if not descricao.strip():
        (A.aviso if plat in ("youtube", "shorts") else A.erro)(
            "descricao.vazia", "texto", f"{nome_campo} vazia", f"Escreva a abertura (references/copy.md) e rode `{refazer} --abertura \"…\"`.")
    elif not str(meta.get("abertura") or "").strip() and not meta.get("descricao_adotada"):
        A.aviso("descricao.abertura", "texto", f"{nome_campo} sem abertura: as primeiras linhas são o que aparece antes do «mais»",
                f"Escreva as duas primeiras linhas e rode `{refazer} --abertura \"…\"`.")
    vis = T("descricao_visivel_estimada_caracteres") or T("legenda_visivel_estimada_caracteres")
    corte_vis = (vis.get("reels") if isinstance(vis, dict) else (min(vis) if isinstance(vis, list) and vis else _num(vis)))
    if corte_vis and descricao.strip():
        primeira = descricao.strip().split("\n")[0]
        medidas["visivel_antes_do_mais"] = primeira[:int(corte_vis)]
        if conta_utf16(primeira) > corte_vis:
            A.info("descricao.visivel", "texto", f"antes do «mais» aparecem cerca de {int(corte_vis)} caracteres (estimativa): «{primeira[:int(corte_vis)]}»",
                   "Confira se o gancho cabe inteiro nesse trecho.")
    txt = pac.pasta / "descricao.txt"
    if not txt.is_file():
        A.erro("descricao.txt", "pacote", "descricao.txt não existe ao lado do meta.json", f"Rode `{refazer}`.")
    elif txt.read_text(encoding="utf-8", errors="replace").strip() != descricao.strip():
        A.erro("descricao.divergente", "pacote", "descricao.txt e o campo `descricao` do meta.json dizem coisas diferentes (um deles foi editado à mão)",
               f"Para remontar pelos blocos: `{refazer}`. Para adotar o descricao.txt editado: `{refazer} --adotar`.")
    for fid in marcadores(publico):
        A.erro("texto.marcador", "texto", f"marcador interno [{fid}] sobrou no texto público",
               "Apague o marcador do título/abertura (a fonte entra no bloco de fontes) e rode a descrição de novo.")

    # ── tags (só YouTube)
    max_tags = _num(T("tags_max_caracteres_total"))
    if tags and plat in ("youtube", "shorts"):
        soma = contar_tags(tags)
        medidas["tags_caracteres"] = soma
        if max_tags is not None and soma > max_tags:
            A.erro("tags.tamanho", "texto", f"as tags somam {soma} caracteres (vírgulas e aspas das tags com espaço contam); o limite é {int(max_tags)}",
                   "Remova tags: elas pesam pouco na descoberta; fique com grafias alternativas do tema.")
        for t in tags:
            if "," in t:
                A.erro("tags.virgula", "texto", f"tag com vírgula: «{t}» (a vírgula separa tags)", "Divida em duas tags ou tire a vírgula.")
            if any(c in t for c in proibidos):
                A.aviso("tags.proibidos", "texto", f"tag com < ou >: «{t}»", "Remova esses caracteres.")
    elif tags:
        A.info("tags.sem_uso", "texto", f"{NOME_PLATAFORMA[plat]} não tem campo de tags; as {len(tags)} tag(s) do meta.json não serão usadas")

    # ── hashtags e menções
    no_texto = RE_HASHTAG.findall(publico)
    medidas["hashtags_no_texto"] = len(no_texto)
    for h in hashtags:
        if re.search(r"\s", h) or not RE_HASHTAG.fullmatch(h if h.startswith("#") else "#" + h):
            A.erro("hashtags.formato", "texto", f"hashtag inválida no meta.json: «{h}»", "Hashtag é # + letras/números, sem espaço.")
    max_h = _num(T("hashtags_max"))
    if max_h is None:
        if no_texto:
            A.info("hashtags.limite", "limites", f"{NOME_PLATAFORMA[plat]}: nenhum limite oficial de quantidade de hashtags encontrado; elas contam dentro da legenda ({len(no_texto)} no texto)")
    elif len(no_texto) > max_h:
        consequencia = {"youtube": "o YouTube ignora TODAS as hashtags do vídeo", "shorts": "o YouTube ignora TODAS as hashtags do vídeo",
                        "reels": "o Instagram não publica o que passa do limite"}.get(plat, "a plataforma recusa")
        A.erro("hashtags.quantidade", "texto", f"{len(no_texto)} hashtags no texto público; o limite é {int(max_h)} ({consequencia})",
               f"Fique com as {int(max_h)} mais específicas: `{refazer} --hashtags \"#a #b …\"`.")
    exibidas = _num(T("hashtags_exibidas_junto_ao_titulo"))
    if exibidas and len(no_texto) > exibidas and plat in ("youtube", "shorts"):
        A.info("hashtags.exibidas", "texto", f"só {int(exibidas)} hashtags aparecem junto ao título; as outras {len(no_texto) - int(exibidas)} ficam apenas na descrição")
    baixas = [h.lower() for h in no_texto]
    repetidas = sorted({h for h in baixas if baixas.count(h) > 1})
    if repetidas:
        A.aviso("hashtags.repetidas", "texto", "hashtag repetida: " + ", ".join("#" + h for h in repetidas), "Deixe cada hashtag uma vez só.")
    max_m = _num(T("mencoes_max"))
    if max_m is not None and len(RE_MENCAO.findall(publico)) > max_m:
        A.erro("mencoes.quantidade", "texto", f"{len(RE_MENCAO.findall(publico))} menções com @; o limite é {int(max_m)}", "Remova menções.")

    # ── arquivo de vídeo
    video = pac.arquivo("arquivo_video")
    sonda = None
    if not meta.get("arquivo_video"):
        A.erro("video.ausente", "tecnico", "meta.json sem arquivo_video", f"Recrie com `pacote.py novo {plat} --video <arquivo> --forcar`.")
    elif not video.is_file():
        A.erro("video.ausente", "tecnico", f"o arquivo de vídeo não existe: {meta['arquivo_video']}",
               "Exporte o vídeo final (video-montagem / video-cortes-verticais) ou corrija o caminho no meta.json.")
    else:
        try:
            sonda = sondar_video(video)
        except Erro as e:
            A.erro("video.ilegivel", "tecnico", e.mensagem, e.dica or "")
    if sonda:
        medidas["video"] = sonda
        sonda.setdefault("extensao", Path(str(meta.get("arquivo_video") or "")).suffix.lower())
        _validar_video(A, plat, lim, sonda, S)

    # ── capítulos
    caps = meta.get("capitulos") or []
    if caps and plat != "youtube":
        A.aviso("capitulos.sem_uso", "texto", f"capítulos não se aplicam a {NOME_PLATAFORMA[plat]}; os {len(caps)} do meta.json serão ignorados",
                f"Limpe com `pacote.py capitulos {pac.id} --limpar`." if plat == "shorts" else "Remova o campo ou deixe a lista vazia.")
    if plat == "youtube":
        if caps:
            try:
                normalizados = normalizar_capitulos(caps)
            except Erro as e:
                normalizados = []
                A.erro("capitulos.formato", "texto", e.mensagem, e.dica or "")
            for id_, sev, msg in conferir_capitulos(normalizados, lim, sonda["duracao"] if sonda else None):
                A.erro(id_, "texto", msg, "Corrija os tempos (video-montagem remapeia quando sai export novo) e rode `pacote.py capitulos`.")
            linhas = formatar_capitulos(normalizados)
            if normalizados and not all(l in descricao for l in linhas):
                A.aviso("capitulos.fora_da_descricao", "texto", "há capítulos no meta.json que não estão na descrição: no YouTube eles só valem escritos lá",
                        f"Inclua o bloco: `{refazer}` (a ordem padrão já traz `capitulos`).")
            origem = raiz / str(meta.get("capitulos_origem") or "render/capitulos.json")
            if video and video.is_file() and origem.is_file() and origem.stat().st_mtime + 1 < video.stat().st_mtime:
                A.aviso("capitulos.antigos", "texto", f"{origem.relative_to(raiz).as_posix()} é mais antigo que o vídeo: os tempos podem ter mudado no último export",
                        "Peça à skill video-montagem para remapear os capítulos e rode `pacote.py capitulos` de novo.")
        elif sonda and sonda["duracao"] >= 600:
            A.info("capitulos.nenhum", "texto", "vídeo com mais de 10 min sem capítulos manuais (o YouTube pode gerar automáticos)",
                   "Se quiser controlar: `pacote.py capitulos` a partir de render/capitulos.json.")

    # ── thumbnail / capa
    _validar_thumbnail(A, pac, lim, medidas)

    # ── legenda .srt
    srt = pac.arquivo("legenda_srt")
    if meta.get("legenda_srt"):
        if not srt.is_file():
            A.erro("legenda.ausente", "legenda", f"o .srt não existe: {meta['legenda_srt']}",
                   "Gere com a skill video-legendas ou ponha `\"legenda_srt\": null` no meta.json.")
        else:
            an = analisar_srt(srt)
            medidas["legenda"] = {"cues": len(an["cues"]), "fim": an["cues"][-1][1] if an["cues"] else None}
            for sev, msg in an["problemas"][:12]:
                (A.erro if sev == "erro" else A.aviso)("legenda.formato", "legenda", f"{srt.name}: {msg}",
                                                       "Regere o .srt com a skill video-legendas (não edite os tempos à mão).")
            if len(an["problemas"]) > 12:
                A.aviso("legenda.formato", "legenda", f"{srt.name}: mais {len(an['problemas']) - 12} problema(s) omitido(s)")
            if sonda and an["cues"] and an["cues"][-1][1] > sonda["duracao"] + 0.5:
                A.erro("legenda.duracao", "legenda",
                       f"{srt.name} termina em {fmt_dur(an['cues'][-1][1])}, depois do fim do vídeo ({fmt_dur(sonda['duracao'])}): é legenda de outro corte ou de outro export",
                       "Regere a legenda para este arquivo.")
    elif plat == "youtube":
        A.info("legenda.nenhuma", "legenda", "sem .srt: o YouTube fica só com a legenda automática",
               "Se houver legendas/<nome>.srt, aponte com `pacote.py novo youtube --legenda <arquivo> --forcar`.")

    # ── privacidade e agendamento
    priv = meta.get("privacidade")
    if priv not in PRIVACIDADES:
        A.erro("privacidade.valor", "agenda", f"privacidade «{priv}» não existe", "Use private, unlisted ou public (padrão da casa: private).")
    ag = meta.get("agendar_para")
    data_ref = ref_agora
    if ag:
        try:
            quando = datetime.fromisoformat(str(ag))
        except ValueError:
            quando = None
            A.erro("agenda.formato", "agenda", f"agendar_para «{ag}» não é uma data ISO 8601", "Exemplo: 2026-10-20T18:00:00-03:00.")
        if quando is not None:
            if quando.tzinfo is None:
                A.erro("agenda.fuso", "agenda", f"agendar_para «{ag}» não tem fuso horário", "Inclua o fuso: 2026-10-20T18:00:00-03:00.")
            else:
                if quando <= ref_agora:
                    A.erro("agenda.passado", "agenda", f"agendar_para ({ag}) já passou: pela API o YouTube publicaria na hora",
                           "Escolha uma data futura ou ponha `\"agendar_para\": null`.")
                else:
                    data_ref = quando
                if plat in ("youtube", "shorts") and priv != "private":
                    A.erro("agenda.privacidade", "agenda", f"agendamento com privacidade «{priv}»: o YouTube só agenda vídeo privado (ele vira público na hora marcada)",
                           "Ponha `\"privacidade\": \"private\"` ou remova o agendamento.")
                if plat in ("reels", "tiktok"):
                    A.info("agenda.manual", "agenda", f"{NOME_PLATAFORMA[plat]}: o agendamento é feito à mão no aplicativo; a data do pacote ({ag}) é só lembrete")
    idioma = str(meta.get("idioma") or "")
    if not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", idioma):
        A.erro("idioma.formato", "pacote", f"idioma «{idioma}» não é um código BCP-47", "Use pt-BR.")
    if plat in ("youtube", "shorts") and meta.get("conteudo_sintetico") is None:
        A.aviso("ia.declaracao", "pacote", "`conteudo_sintetico` não respondido: o YouTube exige declarar conteúdo realista gerado ou alterado por IA",
                f"Responda com `pacote.py definir {pac.id} --sintetico sim` (há cena realista sintética) ou `--sintetico nao` "
                "(animação e gráfico não contam) — references/envio.md §5.")

    # ── fatos
    citados = ins.fatos_citados(meta)
    medidas["fatos_citados"] = citados
    if citados and not ins.fatos:
        A.erro("fatos.ficha", "fatos", f"há {len(citados)} fato(s) citado(s) ({', '.join(citados[:6])}…) mas pesquisa/fatos.json não existe ou está vazio",
               "Rode a skill video-pesquisa-ia para montar a ficha de fatos.")
    for fid in citados if ins.fatos else []:
        fato = ins.fatos.get(fid)
        if fato is None:
            A.erro("fatos.inexistente", "fatos", f"{fid} é citado mas não está em pesquisa/fatos.json", "Confira o id no roteiro/storyboard ou acrescente o fato à ficha.")
            continue
        resumo_f = str(fato.get("afirmacao") or "")[:70]
        if fato.get("status") != "confirmado":
            A.erro("fatos.status", "fatos", f"{fid} está «{fato.get('status')}» na ficha: «{resumo_f}»",
                   "Afirmação factual só com fato confirmado: reverifique (video-pesquisa-ia) ou tire a afirmação do vídeo/texto.")
        cad = fato.get("caduca_em")
        if cad:
            try:
                vence = date.fromisoformat(str(cad)[:10])
                if vence < data_ref.date():
                    quando_txt = "hoje" if data_ref is ref_agora else f"na data agendada ({data_ref.date().isoformat()})"
                    A.erro("fatos.vencido", "fatos", f"{fid} venceu em {vence.isoformat()} ({quando_txt} já não vale): «{resumo_f}»",
                           "Reverifique o fato com a skill video-pesquisa-ia e atualize caduca_em; se mudou, corrija o vídeo.")
                elif (vence - data_ref.date()).days <= 14:
                    A.aviso("fatos.vencendo", "fatos", f"{fid} vence em {vence.isoformat()}: «{resumo_f}»", "Publique antes disso ou reverifique.")
            except ValueError:
                A.aviso("fatos.data", "fatos", f"{fid} tem caduca_em ilegível: «{cad}»", "Use AAAA-MM-DD.")
        if fato.get("confianca") == "baixa":
            A.aviso("fatos.confianca", "fatos", f"{fid} tem confiança baixa: «{resumo_f}»", "Use a redação de `como_dizer` ou procure fonte primária.")

    # ── créditos de b-roll
    for item in ins.creditos_obrigatorios(meta):
        atrib = " ".join(str(item.get("atribuicao") or "").split())
        if not atrib:
            A.erro("licencas.sem_texto", "licencas", f"{item.get('id')} exige atribuição mas broll/licencas.json não traz o texto pronto",
                   "Complete `atribuicao` com a skill video-broll.")
        elif nfc(atrib) not in " ".join(nfc(descricao).split()):
            A.erro("licencas.credito", "licencas",
                   f"crédito obrigatório ausente da {nome_campo}: {item.get('id')} — «{atrib[:80]}» ({item.get('licenca')})",
                   f"Rode `{refazer}` com o bloco `creditos` (não o tire da ordem) ou cole o texto exato.")
    for item, evidencia, cenas in ins.creditos_excluidos(meta):
        onde = ("em " + ", ".join(cenas)) if cenas else "sem cena declarada (broll/licencas.json não traz `usado_em`)"
        quem = f"{item.get('id')} ({item.get('licenca')}, atribuição obrigatória)"
        if not meta.get("corte") and evidencia == "afirmado":
            A.erro("licencas.excluido", "licencas",
                   f"{quem} aparece no vídeo ({onde}) e foi tirado desta peça por `--broll`: o crédito obrigatório ficou de fora",
                   f"Rode `{refazer} --broll auto`. Se o b-roll saiu mesmo do vídeo, quem acerta `usado_em` em broll/licencas.json é a skill video-broll.")
        else:
            problema = f"{quem} foi declarado fora desta peça por `--broll`; pelos insumos ele " + \
                       (f"aparece {onde}" if evidencia == "afirmado" else f"pode aparecer ({onde})")
            excecoes.append({"tipo": "credito_excluido", "pacote": pac.id, "em": agora_iso(),
                             "motivo": "declaração manual de b-roll (pacote.py descricao --broll)", "problemas": [problema]})
            A.aviso("licencas.declarado", "licencas", problema + " — a exceção ficou registrada",
                    f"Confira no vídeo. Se o b-roll aparece, rode `{refazer} --broll auto`; se não aparece, siga: o registro fica no pacote e no envio.")
    fora_do_usado_em, sem_registro = ins.divergencias_de_broll(meta)
    for bid, cenas in fora_do_usado_em:
        A.aviso("licencas.divergente", "licencas",
                f"{bid} aparece em {', '.join(cenas)} no storyboard, mas `usado_em` de broll/licencas.json não lista essa(s) cena(s)",
                "O crédito foi decidido pelo storyboard. Peça à skill video-broll para acertar `usado_em` (os dois arquivos têm de contar a mesma história).")
    for bid, cenas in sem_registro:
        A.aviso("licencas.sem_registro", "licencas",
                f"o storyboard usa o b-roll {bid} em {', '.join(cenas)}, mas ele não está em broll/licencas.json: não dá para saber a licença nem o crédito",
                "Registre o item com a skill video-broll (ou tire o b-roll da cena) antes de publicar.")
    for item in ins.broll_em_uso(meta):
        if item.get("uso_comercial") is False:
            A.aviso("licencas.comercial", "licencas", f"{item.get('id')} tem licença sem uso comercial ({item.get('licenca')})",
                    "Em canal monetizado ou peça patrocinada, troque o b-roll (skill video-broll).")

    # ── corte × plataforma
    if meta.get("corte"):
        corte = ins.corte(meta["corte"])
        if corte is None:
            A.aviso("corte.plano", "pacote", f"o corte {meta['corte']} não está em cortes/plano.json", "Confira o id do corte.")
        elif corte.get("plataformas") and plat not in corte["plataformas"]:
            A.aviso("corte.plataforma", "pacote", f"o corte {meta['corte']} foi planejado para {', '.join(corte['plataformas'])}, não para {plat}",
                    "Confira a zona segura desta plataforma com a skill video-cortes-verticais.")

    # ── limites: idade e origem
    ver = lim.verificado_em
    if ver is None:
        A.aviso("limites.data", "limites", "plataformas.json sem data de verificação", "Revalide os limites (skill video-direcao-de-arte, references/plataformas.md §8).")
    else:
        idade = (ref_agora.date() - ver).days
        medidas["limites_idade_dias"] = idade
        if idade > lim.prazo_revalidacao_dias:
            A.aviso("limites.vencidos", "limites",
                    f"os limites de plataforma foram verificados em {ver.isoformat()} (há {idade} dias; o prazo é {lim.prazo_revalidacao_dias})",
                    "Revalide antes de confiar: skill video-direcao-de-arte, references/plataformas.md §8 (as plataformas mudam limite sem avisar).")
    if not lim.do_kit:
        A.aviso("limites.origem", "limites", f"limites lidos de {lim.origem}, não do kit", f"Remova a variável {VAR_PLATAFORMAS} para validar com os limites da casa.")

    # ── portão de QA
    outros = [a for a in (pac.arquivo("thumbnail"), pac.arquivo("legenda_srt")) if a]
    motivos, avisos_qa, resumo_qa = conferir_qa(raiz, da_obj.sha256, video, outros)
    excecao = None
    if motivos and sem_qa:
        excecao = {"tipo": "sem_qa", "pacote": pac.id, "em": agora_iso(), "motivo": motivo_sem_qa or "não informado", "problemas": motivos}
        excecoes.insert(0, excecao)
        for m in motivos:
            A.aviso("qa.dispensado", "qa", f"PORTÃO DE QA DISPENSADO (--sem-qa): {m}", "A exceção ficou registrada em publicacao/pacote.json.")
    else:
        for m in motivos:
            A.erro("qa.portao", "qa", m, f"Rode `{KIT_FINAL}/bin/da conferencia` (ou `… conferencia --corte NOME`) e publique só com qa/relatorio.json ok, "
                                         "da mesma DA, mais novo que o vídeo e com este arquivo em `alvos`. "
                                         "Exceção consciente: `pacote.py validar --sem-qa --motivo \"…\"` (fica registrada).")
    dicas_qa = {"qa.fuso": f"Rode `{KIT_FINAL}/bin/da conferencia` de novo: ele grava a data com fuso (2026-10-06T14:00:00-03:00).",
                "qa.depois": "Rode o QA de novo se a alteração foi de conteúdo."}
    for id_, m in avisos_qa:
        A.aviso(id_, "qa", m, dicas_qa.get(id_, ""))

    # `excecao` = a do portão de QA (ou None); `excecoes` = todas as registradas nesta validação.
    return {"ok": A.conta("erro") == 0, "validado_em": agora_iso(), "erros": A.conta("erro"), "avisos": A.conta("aviso"),
            "itens": A.itens, "medidas": medidas, "impressao": impressao(pac), "qa": resumo_qa, "excecao": excecao,
            "excecoes": excecoes, "da_sha256": da_obj.sha256}


def _validar_video(A: Achados, plat: str, lim: Limites, s: dict, S) -> None:
    nome = NOME_PLATAFORMA[plat]
    reexportar = ("Reexporte pela skill de origem (video-montagem / video-cortes-verticais): esta skill confere, não transcodifica.")
    L, Alt, dur = s["largura"], s["altura"], s["duracao"]
    menor, maior = min(L, Alt), max(L, Alt)
    vertical, quadrado = Alt > L, Alt == L

    # duração
    dmin, dmax = _num(S("duracao_min_s")), _num(S("duracao_max_s"))
    if dmin is not None and dur < dmin:
        A.erro("video.duracao_min", "tecnico", f"vídeo com {fmt_dur(dur)}; o mínimo em {nome} é {fmt_dur(dmin)}", reexportar)
    if dmax is not None and dur > dmax:
        extra = " (acima disso o YouTube trata como vídeo comum, não como Short)" if plat == "shorts" else ""
        A.erro("video.duracao_max", "tecnico", f"vídeo com {dur:.0f} s; o máximo em {nome} é {dmax:.0f} s{extra}",
               "Corte a peça (video-cortes-verticais) ou publique no formato longo.")
    elif dmax is None:
        A.info("video.duracao_limite", "limites", f"duração máxima de {nome} não encontrada em plataformas.json; não conferida")
    rec = _num(S("duracao_max_recomendada_s"))
    if rec is not None and dur > rec and (dmax is None or dur <= dmax):
        A.aviso("video.duracao_recomendada", "tecnico", f"vídeo com {dur:.0f} s: acima de {rec:.0f} s o {nome} não recomenda a novos públicos",
                "Para alcance, fique abaixo desse teto.")
    api = _num(S("duracao_max_api_s"))
    if api is not None and dur > api and (dmax is None or dur <= dmax):
        A.aviso("video.duracao_api", "tecnico", f"vídeo com {dur:.0f} s: por API/agendador o teto de {nome} é {api:.0f} s", "Só dá para postar pelo aplicativo.")
    garantida = _num(S("duracao_garantida_a_toda_conta_api_s"))
    if garantida is not None and dur > garantida and (api is None or dur <= api):
        A.aviso("video.duracao_conta", "tecnico", f"vídeo com {dur:.0f} s: só {garantida:.0f} s são garantidos a toda conta de {nome}", "Confira o limite da conta antes de postar.")
    nv = _num(S("duracao_max_conta_nao_verificada_s"))
    if nv is not None and dur > nv:
        A.aviso("video.conta_verificada", "tecnico", f"vídeo com {fmt_dur(dur)}: acima de {nv / 60:.0f} min o YouTube exige conta verificada", "Confira em youtube.com/verify antes do envio.")

    # tamanho
    tam = s["tamanho_bytes"]
    for chave, fator, sev, rotulo in (("tamanho_max_gb", 1 << 30, "erro", ""), ("tamanho_max_gb_api", 1 << 30, "aviso", " por API"),
                                      ("tamanho_max_mb_api", 1 << 20, "aviso", " por API")):
        maximo = _num(S(chave))
        if maximo is not None and tam > maximo * fator:
            (A.erro if sev == "erro" else A.aviso)("video.tamanho", "tecnico",
                                                   f"arquivo com {fmt_bytes(tam)}; o máximo{rotulo} em {nome} é {fmt_bytes(maximo * fator)}", reexportar)

    # proporção e orientação
    prop = _proporcao_principal(S("proporcao"))
    real = L / Alt if Alt else 0
    if plat == "shorts" and not (vertical or quadrado):
        A.erro("video.orientacao", "tecnico", f"vídeo horizontal ({L}×{Alt}) não vira Short: o YouTube só classifica como Short o que é vertical ou quadrado",
               "Gere o corte vertical com a skill video-cortes-verticais.")
    elif plat in ("reels", "tiktok") and not (vertical or quadrado):
        A.aviso("video.orientacao", "tecnico", f"vídeo horizontal ({L}×{Alt}) em {nome}: aceita, mas aparece pequeno com faixas", "Gere o corte vertical (video-cortes-verticais).")
    elif prop and abs(real - prop) / prop > 0.02:
        A.aviso("video.proporcao", "tecnico", f"proporção {L}×{Alt} ({real:.3f}) difere da esperada em {nome}: {S('proporcao')}", reexportar)
    if plat == "youtube" and (vertical or quadrado):
        teto = _num(lim.obter("shorts", "duracao_max_s", "specs"))
        if teto is not None and dur <= teto:
            A.aviso("video.vira_short", "tecnico", f"vídeo {'vertical' if vertical else 'quadrado'} de {dur:.0f} s enviado como «youtube»: o YouTube vai classificá-lo como Short",
                    "Se a intenção é Short, crie o pacote `shorts`; se é vídeo longo, o arquivo está errado.")

    # resolução
    recom = S("resolucao_recomendada_px")
    rmin = _num(S("resolucao_min_px")) or _num(S("resolucao_min_px_api"))
    if rmin is not None and menor < rmin:
        A.erro("video.resolucao_min", "tecnico", f"{L}×{Alt}: o lado menor tem {menor} px; o mínimo em {nome} é {rmin:.0f} px", reexportar)
    elif isinstance(recom, list) and len(recom) == 2 and (L, Alt) != tuple(recom) and L * Alt < recom[0] * recom[1]:
        A.aviso("video.resolucao", "tecnico", f"{L}×{Alt} está abaixo da resolução recomendada em {nome} ({recom[0]}×{recom[1]})",
                "Aceita, mas perde nitidez; exporte na resolução da DA se o material permitir.")
    rmax = _num(S("resolucao_max_px_api"))
    if rmax is not None and maior > rmax:
        A.aviso("video.resolucao_max", "tecnico", f"{L}×{Alt}: lado maior acima de {rmax:.0f} px (limite da API de {nome})", reexportar)
    lmax = _num(S("largura_max_px_api"))
    if lmax is not None and L > lmax:
        A.aviso("video.largura_max", "tecnico", f"largura de {L} px acima de {lmax:.0f} px (limite da API de {nome})", "Pelo aplicativo pode passar; por agendador, não.")
    m = re.search(r"(\d{3,4})\s*p", str(S("resolucao_max") or ""))
    if m and menor > int(m.group(1)):
        A.aviso("video.resolucao_max", "tecnico", f"{L}×{Alt} passa do máximo de {nome} ({m.group(1)}p): será reduzido", reexportar)

    # codec, croma, varredura, container, fast start
    aceitos = _codecs_citados(S("codec_video"))
    if aceitos and s["codec_video"] not in aceitos:
        sev = A.aviso if plat in ("youtube", "shorts") else A.erro
        sev("video.codec", "tecnico", f"codec de vídeo «{s['codec_video']}»; {nome} pede: {S('codec_video')}", reexportar + " Padrão da casa: H.264 (video.args_encode).")
    if "4:2:0" in str(S("codec_video") or "") and s["pix_fmt"] and "420" not in s["pix_fmt"]:
        A.aviso("video.croma", "tecnico", f"formato de pixel «{s['pix_fmt']}»; {nome} recomenda croma 4:2:0", reexportar + " (yuv420p).")
    if s["pix_fmt"] and "10" in s["pix_fmt"]:
        A.aviso("video.bits", "tecnico", f"vídeo em 10 bits ({s['pix_fmt']}): em SDR as plataformas esperam 8 bits", reexportar)
    if s.get("varredura") and s["varredura"] not in ("progressive", "unknown"):
        A.aviso("video.entrelacado", "tecnico", f"varredura «{s['varredura']}»: envie progressivo", "Desentrelace na exportação.")
    cont = _containers_citados(S("container"))
    familia = str(s["container"] or "")
    # O ffprobe chama MKV e WebM pelo mesmo nome («matroska,webm»). WebM de verdade = extensão .webm com VP8/VP9/AV1
    # e Vorbis/Opus; qualquer outra coisa nessa família é Matroska, que nenhuma das plataformas lista.
    webm = ("webm" in familia and str(s.get("extensao") or "").lower() == ".webm" and s["codec_video"] in ("vp8", "vp9", "av1")
            and s.get("codec_audio") in (None, "vorbis", "opus"))
    if cont:
        ok_cont = (("mp4" in cont or "mov" in cont) and "mp4" in familia) or ("webm" in cont and webm)
        if not ok_cont:
            visto = (f"Matroska/MKV («{familia}» com {s['codec_video']}/{s.get('codec_audio') or 'sem áudio'}; não é WebM)"
                     if "matroska" in familia and not webm else f"«{familia}»")
            sev = A.aviso if plat in ("youtube", "shorts") else A.erro
            sev("video.container", "tecnico", f"container {visto}; {nome} pede: {S('container')}", reexportar + " (.mp4).")
    if "moov" in str(S("container") or "").lower() and s["moov_no_inicio"] is False:
        A.aviso("video.faststart", "tecnico", "o MP4 não está em fast start (moov depois do mdat): o processamento começa mais tarde e algumas APIs recusam",
                "Regrave sem recodificar: ffmpeg -i entrada.mp4 -c copy -movflags +faststart saida.mp4 (sob a trava).")

    # fps
    fps = s["fps"]
    regra_fps = S("fps") if isinstance(S("fps"), dict) else {}
    faixa = regra_fps.get("faixa_api")
    if isinstance(faixa, list) and len(faixa) == 2 and fps and not (faixa[0] <= fps <= faixa[1] + 0.01):
        A.aviso("video.fps", "tecnico", f"{fps:g} fps fora da faixa da API de {nome} ({faixa[0]}–{faixa[1]})", reexportar)
    fmin = _num(regra_fps.get("min_central_de_ajuda"))
    if fmin is not None and fps and round(fps) < fmin:
        A.aviso("video.fps_min", "tecnico", f"{fps:g} fps; a Central de Ajuda de {nome} pede no mínimo {fmin:.0f}", reexportar)
    comuns = regra_fps.get("comuns")
    if isinstance(comuns, list) and fps and round(fps) not in comuns:
        A.aviso("video.fps_incomum", "tecnico", f"{fps:g} fps não é uma taxa comum ({', '.join(str(c) for c in comuns)})", "Confira a exportação: taxa estranha costuma ser erro de conformação.")

    # bitrate
    bmax = _num(S("bitrate_video_max_mbps"))
    if bmax is not None and s.get("bitrate_video_kbps") and s["bitrate_video_kbps"] > bmax * 1000:
        A.aviso("video.bitrate", "tecnico", f"bitrate de vídeo de {s['bitrate_video_kbps'] / 1000:.1f} Mbps acima do máximo da API de {nome} ({bmax:g} Mbps)", reexportar)

    # áudio
    regra_audio = S("audio") if isinstance(S("audio"), dict) else {}
    if not s["tem_audio"]:
        A.erro("video.sem_audio", "tecnico", "o arquivo não tem trilha de áudio",
               "É o defeito clássico de export mudo: confira o mix e o XML (video-montagem / video-mixagem) e exporte de novo.")
    else:
        aud_ok = _codecs_citados(regra_audio.get("codec"), _AUDIOS)
        if aud_ok and s["codec_audio"] not in aud_ok:
            A.aviso("video.codec_audio", "tecnico", f"áudio em «{s['codec_audio']}»; {nome} pede: {regra_audio.get('codec')}", reexportar + " (AAC).")
        taxa = _num(regra_audio.get("taxa_amostragem_hz"))
        if taxa and s["taxa_amostragem_hz"] and s["taxa_amostragem_hz"] != taxa:
            A.aviso("video.taxa_audio", "tecnico", f"áudio em {s['taxa_amostragem_hz']} Hz; {nome} recomenda {taxa:.0f} Hz", reexportar + " (-ar 48000).")
        if "estéreo" in str(regra_audio.get("canais") or "").lower() and s["canais"] == 1:
            A.info("video.mono", "tecnico", f"áudio mono; {nome} recomenda estéreo")


def _validar_thumbnail(A: Achados, pac: Pacote, lim: Limites, medidas: dict) -> None:
    plat, meta = pac.plataforma, pac.meta
    nome = NOME_PLATAFORMA[plat]
    regra = lim.secao("thumbnail", "youtube") if plat == "youtube" else lim.secao("capas", plat)
    thumb = pac.arquivo("thumbnail")
    if not meta.get("thumbnail"):
        if plat == "youtube":
            A.aviso("thumb.nenhuma", "thumbnail", "sem thumbnail: o YouTube escolhe um quadro qualquer",
                    "Faça a thumbnail pelo kit da direção de arte (kit-api.md §17.1) e indique o arquivo: `pacote.py definir youtube --thumbnail thumbs/ARQ.png`.")
        return
    if not thumb.is_file():
        A.erro("thumb.ausente", "thumbnail", f"a thumbnail não existe: {meta['thumbnail']}", "Gere de novo pelo kit da direção de arte (kit-api.md §17.1) ou corrija o caminho (`pacote.py definir … --thumbnail ARQ`).")
        return
    if plat == "tiktok":
        A.info("thumb.tiktok", "thumbnail", f"TikTok não recebe arquivo de capa: {regra.get('selecao') or 'a capa é um quadro do próprio vídeo'}",
               "Use a imagem só como referência para escolher o quadro no aplicativo.")
    try:
        im = sondar_imagem(thumb)
    except Erro as e:
        A.erro("thumb.ilegivel", "thumbnail", e.mensagem, e.dica or "")
        return
    medidas["thumbnail"] = im
    refazer = "Gere de novo pelo kit da direção de arte (receita em kit-api.md §17.1: é ele que desenha; aqui só se confere)."
    formatos = [str(f).upper().replace("JPG", "JPEG") for f in (regra.get("formatos") or [])]
    if formatos and im["formato"] not in formatos:
        A.erro("thumb.formato", "thumbnail", f"{thumb.name} está em {im['formato'] or 'formato desconhecido'}; {nome} aceita {', '.join(regra.get('formatos'))}", refazer)
    prop = _proporcao_principal(regra.get("proporcao"))
    real = im["largura"] / im["altura"] if im["altura"] else 0
    if prop and abs(real - prop) / prop > 0.01:
        A.erro("thumb.proporcao", "thumbnail", f"{thumb.name} tem {im['largura']}×{im['altura']} ({real:.3f}); {nome} pede {regra.get('proporcao')}", refazer)
    lmin = _num(regra.get("largura_min_px"))
    if lmin is not None and im["largura"] < lmin:
        A.erro("thumb.largura_min", "thumbnail", f"{thumb.name} tem {im['largura']} px de largura; o mínimo é {lmin:.0f}", refazer)
    amin = _num(regra.get("altura_min_px"))
    if amin is not None and im["altura"] < amin:
        A.erro("thumb.altura_min", "thumbnail", f"{thumb.name} tem {im['altura']} px de altura; o mínimo é {amin:.0f}", refazer)
    ab = regra.get("resolucao_minima_para_teste_ab_px")
    if isinstance(ab, list) and len(ab) == 2 and (im["largura"] < ab[0] or im["altura"] < ab[1]):
        A.aviso("thumb.teste_ab", "thumbnail", f"{thumb.name} ({im['largura']}×{im['altura']}) está abaixo de {ab[0]}×{ab[1]}: num teste A/B todas as variações seriam rebaixadas", refazer)
    pesos = regra.get("peso_max_mb")
    teto = max((_num(v) or 0) for v in pesos.values()) if isinstance(pesos, dict) and pesos else (_num(pesos) or _num(regra.get("peso_max_mb_api")))
    mb = im["tamanho_bytes"] / (1 << 20)
    if teto and mb > teto:
        A.erro("thumb.peso", "thumbnail", f"{thumb.name} pesa {fmt_bytes(im['tamanho_bytes'])}; o máximo em {nome} é {teto:g} MB", "Exporte em JPG de qualidade 90 ou reduza a resolução.")
    seguro = _num(regra.get("peso_max_seguro_mb")) or (_num(pesos.get("celular")) if isinstance(pesos, dict) else None)
    if seguro and mb > seguro and not (teto and mb > teto):
        A.aviso("thumb.peso_celular", "thumbnail", f"{thumb.name} pesa {fmt_bytes(im['tamanho_bytes'])}: acima de {seguro:g} MB só sobe pelo computador (ou pela API)",
                "Se for subir pelo celular, exporte abaixo desse peso.")
    if plat == "shorts" and regra.get("onde_enviar"):
        A.info("thumb.shorts", "thumbnail", f"capa de Short: {regra['onde_enviar']}")


# ────────────────────────────────────────────────────────────────── índice ──
def caminho_indice(raiz: Path) -> Path:
    return raiz / "publicacao" / "pacote.json"


def entrada_do_indice(pac: Pacote, validacao: dict | None) -> dict:
    meta = pac.meta
    ent = {"id": pac.id, "plataforma": pac.plataforma, "corte": meta.get("corte"),
           "meta": pac.rel(pac.meta_path), "descricao_txt": pac.rel(pac.pasta / "descricao.txt") if (pac.pasta / "descricao.txt").is_file() else None,
           "checklist": pac.rel(pac.pasta / "checklist.md") if (pac.pasta / "checklist.md").is_file() else None,
           "arquivo_video": meta.get("arquivo_video"), "thumbnail": meta.get("thumbnail"), "legenda_srt": meta.get("legenda_srt"),
           "titulo": meta.get("titulo"), "privacidade": meta.get("privacidade"), "agendar_para": meta.get("agendar_para"),
           "validacao": validacao}
    envio = pac.pasta / "envio.json"
    if envio.is_file():
        try:
            ent["envio"] = ler_json(envio)
        except Erro:
            ent["envio"] = None
    return ent


def _validacao_legivel(v) -> dict | None:
    """Uma validação gravada só vale se tiver a forma que este script grava; qualquer outra coisa = não validado."""
    if not isinstance(v, dict) or not isinstance(v.get("impressao"), dict) or not isinstance(v.get("itens"), list):
        return None
    if any(not isinstance(i, dict) or not {"id", "severidade", "mensagem"} <= set(i) for i in v["itens"]):
        return None
    if not isinstance(v.get("medidas") or {}, dict) or not isinstance(v.get("excecao") or {}, dict):
        return None
    exs = v.get("excecoes")
    if not isinstance(exs, list):                          # pacote.json gravado antes de existir a lista
        exs = [v["excecao"]] if v.get("excecao") else []
    v["excecoes"] = [e for e in exs if isinstance(e, dict) and isinstance(e.get("problemas"), list)]
    return v


def ler_indice(raiz: Path) -> dict:
    """publicacao/pacote.json saneado. Índice de tipo errado (editado à mão) vale como «nada validado»: nunca
    aprova ninguém, e o próximo `validar` regrava. Devolve sempre {'pacotes': [objetos], 'excecoes_historico': [objetos]}."""
    arq = caminho_indice(raiz)
    try:
        bruto = ler_json_opcional(arq)
    except Erro as e:
        raise Erro(f"{e.mensagem}", "publicacao/pacote.json é gerado por este script: apague o arquivo e rode `pacote.py validar` de novo.")
    if not isinstance(bruto, dict):
        return {"pacotes": [], "excecoes_historico": []}
    pacotes = [p for p in bruto["pacotes"] if isinstance(p, dict)] if isinstance(bruto.get("pacotes"), list) else []
    for ent in pacotes:
        ent["validacao"] = _validacao_legivel(ent.get("validacao"))
    hist = bruto.get("excecoes_historico")
    return {"pacotes": pacotes, "excecoes_historico": [e for e in hist if isinstance(e, dict)] if isinstance(hist, list) else []}


def validacao_gravada(raiz: Path, pacote_id: str) -> dict | None:
    return next((ent["validacao"] for ent in ler_indice(raiz)["pacotes"] if ent.get("id") == pacote_id), None)


ESTADOS_OK = ("ok", "ok_com_excecao")


def situacao_do_pacote(pac: Pacote, gravada: dict | None, lim: Limites, ins: Insumos, da_obj) -> tuple[str, dict | None]:
    """Estado do pacote AGORA. Devolve (estado, conferência refeita na hora — ou None quando nem chega a refazer).

    'nao_validado'   nunca passou por `validar` (ou o índice não é legível);
    'desatualizada'  o pacote mudou depois de validar (meta.json, vídeo, thumbnail, .srt ou descricao.txt);
    'reprovado'      a validação gravada reprovou;
    'vencida'        a validação gravada aprovou, mas a conferência de AGORA reprova: o QA sumiu, reprovou ou é de
                     outra DA, a DA perdeu a aprovação, um fato venceu ou foi rebaixado, entrou crédito obrigatório,
                     a data agendada passou… Uma aprovação antiga não é salvo-conduto;
    'ok' | 'ok_com_excecao'.

    Esta função nunca APROVA nada sozinha (quem aprova é `validar`); ela só pode tirar a aprovação."""
    if not gravada:
        return "nao_validado", None
    if gravada.get("impressao") != impressao(pac):
        return "desatualizada", None
    if not gravada.get("ok"):
        return "reprovado", None
    exc = gravada.get("excecao") or {}
    viva = validar_pacote(pac, lim, ins, da_obj, sem_qa=bool(exc), motivo_sem_qa=exc.get("motivo"))
    # Uma exceção cobre só os problemas que existiam quando o usuário a concedeu.
    cobertos = {(e.get("tipo"), prob) for e in gravada.get("excecoes") or [] for prob in e.get("problemas") or []}
    for e in viva["excecoes"]:
        for prob in e["problemas"]:
            if (e["tipo"], prob) not in cobertos:
                refazer = (f"pacote.py validar {pac.id} --sem-qa --motivo \"…\"" if e["tipo"] == "sem_qa" else f"pacote.py validar {pac.id}")
                viva["itens"].append({"id": "excecao.vencida", "categoria": "qa" if e["tipo"] == "sem_qa" else "licencas", "severidade": "erro",
                                      "mensagem": f"a exceção registrada na validação de {gravada.get('validado_em')} não cobre o problema de agora: {prob}",
                                      "como_corrigir": f"Resolva o problema ou, se o usuário decidir seguir mesmo assim, registre de novo: `{refazer}`."})
    viva["erros"] = sum(1 for i in viva["itens"] if i["severidade"] == "erro")
    viva["ok"] = viva["erros"] == 0
    if not viva["ok"]:
        return "vencida", viva
    return ("ok_com_excecao" if viva["excecoes"] else "ok"), viva


def erros_de(validacao: dict | None) -> list[str]:
    return [i["mensagem"] for i in (validacao or {}).get("itens", []) if i["severidade"] == "erro"]


def atualizar_indice(raiz: Path, da_obj, lim: Limites, novas: dict[str, dict] | None = None, ins: Insumos | None = None) -> dict:
    """Regrava publicacao/pacote.json: índice de TODOS os pacotes (é por aqui que as skills irmãs acham os pacotes
    de segundo corte em diante), a última validação de cada um e o estado de agora (situacao_do_pacote)."""
    anterior = ler_indice(raiz)
    antigas = {ent.get("id"): ent.get("validacao") for ent in anterior["pacotes"]}
    ins = ins or Insumos(raiz)
    historico = list(anterior["excecoes_historico"])       # só cresce: exceção concedida não some ao revalidar
    assinatura = lambda e: (e.get("tipo"), e.get("pacote"), e.get("motivo"), tuple(str(x) for x in e.get("problemas") or []))   # noqa: E731
    vistos = {assinatura(e) for e in historico}            # a mesma exceção revalidada não entra duas vezes (fica a primeira data)
    pacotes, excecoes = [], []
    for pac in listar_pacotes(raiz):
        if novas and pac.id in novas:
            val, viva = novas[pac.id], None
            estado = ("ok_com_excecao" if val.get("excecoes") else "ok") if val["ok"] else "reprovado"
            for e in val.get("excecoes") or []:
                if assinatura(e) not in vistos:
                    vistos.add(assinatura(e))
                    historico.append(e)
        else:
            val = antigas.get(pac.id)
            estado, viva = situacao_do_pacote(pac, val, lim, ins, da_obj)
        ent = entrada_do_indice(pac, val)
        ent["estado"] = estado
        if estado == "vencida":
            ent["conferencia"] = {"em": viva["validado_em"], "erros": erros_de(viva)}
        if estado == "ok_com_excecao":
            excecoes += val.get("excecoes") or []
        pacotes.append(ent)
    ver = lim.verificado_em
    indice = {
        "versao": 1, "gerado_em": agora_iso(), "projeto": (da_obj.meta or {}).get("nome"), "da_sha256": da_obj.sha256,
        "limites": {"origem": lim.origem, "verificado_em": ver.isoformat() if ver else None,
                    "idade_dias": (agora().date() - ver).days if ver else None},
        "ok": bool(pacotes) and all(ent["estado"] in ESTADOS_OK for ent in pacotes),
        "resumo": {"pacotes": len(pacotes), "erros": sum((ent["validacao"] or {}).get("erros", 0) for ent in pacotes),
                   "avisos": sum((ent["validacao"] or {}).get("avisos", 0) for ent in pacotes)},
        "excecoes": excecoes, "excecoes_historico": historico, "pacotes": pacotes,
    }
    gravar_json(caminho_indice(raiz), indice)
    return indice


ROTULO_ESTADO = {"ok": "ok", "ok_com_excecao": "ok (com exceção registrada)", "reprovado": "REPROVADO", "desatualizada": "mudou depois de validar",
                 "vencida": "VENCEU (a conferência de agora reprova)", "nao_validado": "não validado"}
ROTULO_EXCECAO = {"sem_qa": "portão de QA dispensado", "credito_excluido": "crédito de b-roll declarado fora da peça"}


def tabela_do_indice(indice: dict) -> str:
    linhas = [("pacote", "arquivo", "título", "privac.", "agendado", "validação", "erros", "avisos")]
    for p in indice["pacotes"]:
        v = p.get("validacao") or {}
        titulo = str(p.get("titulo") or "")
        erros, avisos = str(v.get("erros", "—")), str(v.get("avisos", "—"))
        if p.get("estado") == "vencida":                      # os números que valem são os da conferência de agora
            erros, avisos = str(len((p.get("conferencia") or {}).get("erros") or [])), "—"
        linhas.append((p["id"], str(p.get("arquivo_video") or "—"), (titulo[:34] + "…") if len(titulo) > 35 else (titulo or "—"),
                       str(p.get("privacidade") or "—"), str(p.get("agendar_para") or "—")[:16],
                       ROTULO_ESTADO.get(p.get("estado"), "?"), erros, avisos))
    larg = [max(len(l[i]) for l in linhas) for i in range(len(linhas[0]))]
    saida = []
    for n, l in enumerate(linhas):
        saida.append("  ".join(c.ljust(larg[i]) for i, c in enumerate(l)).rstrip())
        if n == 0:
            saida.append("  ".join("─" * w for w in larg))
    return "\n".join(saida)


# ──────────────────────────────────────────────────────────────── checklist ──
def _bloco_codigo(texto: str) -> str:
    cerca = "```"
    while cerca in texto:
        cerca += "`"
    return f"{cerca}text\n{texto.rstrip()}\n{cerca}"


def linhas_de_excecao(validacao: dict | None) -> list[str]:
    """Uma linha por exceção registrada na validação (para o checklist, o resumo e o plano de envio)."""
    linhas = []
    for e in (validacao or {}).get("excecoes") or []:
        rotulo = ROTULO_EXCECAO.get(e.get("tipo"), str(e.get("tipo")))
        if e.get("tipo") == "sem_qa":
            linhas.append(f"{rotulo} — motivo: {e.get('motivo')}")
        else:
            linhas.append(f"{rotulo} — {'; '.join(str(x) for x in e.get('problemas') or [])}")
    return linhas


def gerar_checklist(pac: Pacote, lim: Limites, validacao: dict | None, estado: str, viva: dict | None = None) -> str:
    """`validacao` = a gravada por `validar`; `viva` = a conferência refeita agora (situacao_do_pacote)."""
    meta, plat = pac.meta, pac.plataforma
    nome = NOME_PLATAFORMA[plat]
    abs_ = lambda rel: str((pac.raiz / rel).resolve()) if rel else "—"   # noqa: E731
    L = [f"# Checklist de envio — {nome}" + (f" · corte {meta['corte']}" if meta.get("corte") else ""), ""]
    L.append(f"Gerado em {agora_iso()} por `pacote.py checklist {pac.id}`. Limites de plataforma verificados em "
             f"{lim.verificado_em.isoformat() if lim.verificado_em else 'data desconhecida'}.")
    L.append("")
    conferido = f" (validado em {(validacao or {}).get('validado_em')}; conferido de novo agora)"
    if estado == "ok":
        L.append(f"**Validação: aprovado**{conferido} — pode publicar depois da confirmação do usuário.")
    elif estado == "ok_com_excecao":
        L.append(f"**Validação: aprovado COM EXCEÇÃO**{conferido}. Diga isto ao usuário antes de publicar:")
        L += [f"- {linha}" for linha in linhas_de_excecao(validacao)]
    elif estado == "vencida":
        L.append(f"> **NÃO PUBLIQUE AINDA — a validação de {(validacao or {}).get('validado_em')} venceu: a conferência de agora reprova.** "
                 f"Resolva o que está abaixo e rode `pacote.py validar {pac.id}`.")
    else:
        L.append(f"> **NÃO PUBLIQUE AINDA — validação: {ROTULO_ESTADO.get(estado, estado)}.** Rode `pacote.py validar {pac.id}` e resolva os erros.")
    fonte = viva if viva is not None else (validacao if estado != "nao_validado" else None)
    pend = [i for i in (fonte or {}).get("itens", []) if i["severidade"] in ("erro", "aviso")]
    if pend:
        L += ["", "Pendências da conferência de agora:" if viva is not None else "Pendências da última validação (o pacote mudou depois dela):"]
        L += [f"- **{i['severidade'].upper()}** — {i['mensagem']}" for i in pend]
    L += ["", "## Arquivos", "", f"- Vídeo: `{abs_(meta.get('arquivo_video'))}`"]
    v = ((viva or validacao or {}).get("medidas") or {}).get("video")
    if v:
        L.append(f"  - {v['largura']}×{v['altura']}, {str(round(v['fps'], 2)).replace('.', ',')} fps, {fmt_dur(v['duracao'])}, {fmt_bytes(v['tamanho_bytes'])}, "
                 f"{v['codec_video']}/{v['codec_audio'] or 'sem áudio'}")
    L.append(f"- {'Thumbnail' if plat == 'youtube' else 'Capa'}: `{abs_(meta.get('thumbnail'))}`")
    L.append(f"- Legenda (.srt): `{abs_(meta.get('legenda_srt'))}`")
    L += ["", "## Campos prontos para colar", ""]
    if plat in ("youtube", "shorts"):
        L += [f"**Título** ({conta_utf16(str(meta.get('titulo') or ''))} caracteres):", "", _bloco_codigo(str(meta.get("titulo") or "(vazio)")), ""]
        L += [f"**Descrição** ({fmt_int(conta_utf16(str(meta.get('descricao') or '')))} caracteres, {fmt_int(conta_bytes(str(meta.get('descricao') or '')))} bytes) — também em `{pac.rel(pac.pasta / 'descricao.txt')}`:",
              "", _bloco_codigo(str(meta.get("descricao") or "(vazia)")), ""]
        if meta.get("tags"):
            L += [f"**Tags** ({contar_tags([str(t) for t in meta['tags']])} caracteres na conta do YouTube):", "", _bloco_codigo(", ".join(str(t) for t in meta["tags"])), ""]
    else:
        L += [f"**Legenda do post** ({fmt_int(conta_utf16(str(meta.get('descricao') or '')))} caracteres; hashtags incluídas):", "",
              _bloco_codigo(str(meta.get("descricao") or "(vazia)")), ""]
    priv = {"private": "Privado", "unlisted": "Não listado", "public": "Público"}.get(meta.get("privacidade"), str(meta.get("privacidade")))
    if plat in ("youtube", "shorts"):
        L.append(f"**Privacidade:** {priv} (`{meta.get('privacidade')}`)")
    elif plat == "reels":
        L.append(f"**Visibilidade:** o pacote diz `{meta.get('privacidade')}`, mas o Instagram não tem envio privado: o Reel vai direto para o público da conta. "
                 "Só publique depois do «sim» do usuário.")
    else:
        quem = {"private": "só você", "public": "todos"}.get(meta.get("privacidade"), "escolha à mão (não há equivalente a «não listado»)")
        L.append(f"**Quem pode ver:** {quem} (`{meta.get('privacidade')}` no pacote).")
    if meta.get("agendar_para"):
        try:
            q = datetime.fromisoformat(str(meta["agendar_para"]))
            L.append(f"**Agendar para:** {q.strftime('%d/%m/%Y às %H:%M')} (fuso {q.strftime('%z')[:3]}:{q.strftime('%z')[3:]}) — `{meta['agendar_para']}`")
        except ValueError:
            L.append(f"**Agendar para:** `{meta['agendar_para']}`")
    else:
        L.append("**Agendamento:** nenhum.")
    L.append(f"**Idioma:** {meta.get('idioma')}")
    if plat in ("youtube", "shorts"):
        ia = meta.get("conteudo_sintetico")
        L.append("**Conteúdo alterado ou sintético (IA realista):** " + ("Sim" if ia is True else "Não" if ia is False else "NÃO RESPONDIDO — decida antes de publicar"))
        cr = meta.get("feito_para_criancas")
        L.append("**Feito para crianças:** " + ("Sim" if cr is True else "Não" if cr is False else "não respondido (o Studio vai perguntar)"))
    L += ["", "## Passo a passo", ""]
    junto = _num(lim.obter(plat, "hashtags_exibidas_junto_ao_titulo")) if plat in ("youtube", "shorts") else None
    nota_hashtags = f" (até {int(junto)} aparecem junto ao título)" if junto else ""
    passos = {
        "youtube": [
            "No computador, abra o YouTube Studio com a conta do canal e confira o nome do canal no canto superior direito.",
            "Criar → Enviar vídeos → selecione o arquivo de vídeo acima.",
            "Em Detalhes: cole o **Título** e a **Descrição** (os capítulos só valem se a lista estiver na descrição, começando em 00:00).",
            "Em Miniatura, envie a thumbnail acima (exige conta verificada).",
            "Em Público, marque a opção de «feito para crianças» conforme o campo acima.",
            "Abra «Mostrar mais»: responda «Conteúdo alterado», cole as **Tags**, escolha o idioma do vídeo e a categoria.",
            "Em Elementos do vídeo → legendas, envie o arquivo .srt «com marcação de tempo» (se houver).",
            "Em Verificações, espere a checagem de direitos autorais terminar e leia o resultado.",
            "Em Visibilidade: escolha a privacidade acima; para agendar, deixe Privado e use «Programar» com a data e o fuso acima.",
            "Depois de processar, abra o vídeo e confira: título inteiro, primeiras linhas da descrição, capítulos na barra, thumbnail, legenda.",
        ],
        "shorts": [
            "No computador, abra o YouTube Studio com a conta do canal e confira o nome do canal.",
            "Criar → Enviar vídeos → selecione o arquivo vertical acima (vertical ou quadrado de até o limite de Shorts vira Short sozinho).",
            f"Cole o **Título** e a **Descrição**; hashtags na descrição{nota_hashtags}.",
            "Capa: se a conta já tiver o recurso, envie a capa 9:16 pelo Studio no computador; senão, escolha o quadro no aplicativo.",
            "Responda «feito para crianças» e, em «Mostrar mais», «Conteúdo alterado».",
            "Espere as Verificações e leia o resultado: reivindicação de direitos sobre música de terceiros pode bloquear o Short no mundo todo.",
            "Em Visibilidade, escolha a privacidade acima; para agendar, Privado + «Programar».",
            "Abra no celular e confira que nada do texto do vídeo ficou sob os botões.",
        ],
        "reels": [
            "Passe o arquivo de vídeo para o celular (AirDrop/iCloud) sem recompactar por aplicativo de mensagem.",
            "No aplicativo do Instagram, confira a conta ativa e, nas configurações de mídia, ligue o envio na qualidade mais alta.",
            "Crie um novo Reel escolhendo o arquivo da galeria. Não aplique filtro nem corte: a peça já saiu pronta.",
            "Capa: escolha a imagem de capa acima (ou um quadro limpo); confira o recorte na grade do perfil antes de publicar.",
            "Cole a **Legenda do post** exatamente como está (as hashtags já estão dentro do limite).",
            "Se houver crédito de imagem obrigatório, confira que ele está na legenda.",
            "Declare conteúdo de IA ou parceria paga se for o caso, nas opções avançadas.",
            "Publique (ou agende pelo próprio aplicativo/Meta Business Suite) e confira no perfil: capa, legenda, áudio.",
        ],
        "tiktok": [
            "Passe o arquivo de vídeo para o celular sem recompactar, ou use o envio pelo site do TikTok no computador.",
            "Confira a conta ativa antes de qualquer coisa.",
            "Crie o post escolhendo o arquivo. Não aplique filtro, corte nem som do aplicativo por cima do áudio final.",
            "Cole a **Legenda do post**; as hashtags contam dentro do limite de caracteres.",
            "Capa: escolha um quadro limpo do próprio vídeo (o TikTok não recebe arquivo de capa; sem escolha, usa o primeiro quadro).",
            "Escolha quem pode ver e as permissões de comentário, dueto e costura.",
            "Ligue o rótulo de conteúdo gerado por IA se houver cena realista sintética; declare conteúdo promocional se for o caso.",
            "Publique (ou agende pelo site) e confira no perfil: capa, legenda, áudio.",
        ],
    }[plat]
    L += [f"{n}. [ ] {p}" for n, p in enumerate(passos, 1)]
    L += ["", "Os nomes dos menus mudam com frequência e variam por conta; se um passo não bater com a tela, siga o campo equivalente.",
          f"Envio automático e requisitos de cada API: `{SKILL_FINAL}/references/envio.md`.", ""]
    return "\n".join(L)


# ───────────────────────────────────────────────────────────────────── CLI ──
def diz(*partes, erro: bool = False) -> None:
    """Toda linha sai na hora (flush): com a saída num pipe ou num arquivo — é assim no Bash do Claude Code — o
    Python guardaria tudo até o processo acabar, e quem espera o endereço de consentimento do OAuth ficaria sem ele."""
    if erro:
        sys.stdout.flush()          # mantém a ordem das linhas entre stdout e stderr
    print(*partes, file=sys.stderr if erro else sys.stdout, flush=True)


def _escolher_thumbnail(ins: Insumos, plat: str) -> tuple[str | None, str]:
    """Thumbnail escolhida em thumbs/variacoes.json, se for do formato desta plataforma."""
    doc = ins.variacoes
    if not isinstance(doc, dict) or not isinstance(doc.get("variacoes"), list):
        return None, "nenhuma indicada: passe o arquivo em --thumbnail (thumbs/variacoes.json não existe)"
    quer = "thumbnail" if plat == "youtube" else "vertical"
    escolhida = doc.get("escolhida")
    if isinstance(escolhida, dict):            # tolera {"thumbnail": "A", "vertical": "V1"}
        escolhida = escolhida.get(quer)
    if not escolhida:
        return None, "nenhuma variação marcada como `escolhida` em thumbs/variacoes.json"
    var = next((v for v in doc["variacoes"] if isinstance(v, dict) and str(v.get("id")) == str(escolhida)), None)
    if var is None:
        return None, f"a variação escolhida «{escolhida}» não está na lista de thumbs/variacoes.json"
    if (var.get("formato") or "thumbnail") != quer:
        return None, f"a variação escolhida «{escolhida}» é do formato «{var.get('formato')}»; {NOME_PLATAFORMA[plat]} pede «{quer}»"
    return str(var.get("arquivo")), f"variação {escolhida} de thumbs/variacoes.json"


def _escolher_srt(raiz: Path, video_rel: str, corte: str | None) -> tuple[str | None, str]:
    if corte and (raiz / "cortes" / f"{corte}.srt").is_file():
        return f"cortes/{corte}.srt", "legenda do corte"
    tronco = Path(video_rel).stem
    for cand in (raiz / Path(video_rel).with_suffix(".srt"), raiz / "legendas" / f"{tronco}.srt"):
        if cand.is_file():
            return cand.relative_to(raiz).as_posix(), "mesmo nome do vídeo"
    for cues in sorted((raiz / "legendas").glob("*.cues.json")) if (raiz / "legendas").is_dir() else []:
        try:
            doc = json.loads(cues.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        srt = cues.with_name(cues.name[:-len(".cues.json")] + ".srt")
        if isinstance(doc, dict) and doc.get("origem") == video_rel and srt.is_file():
            return srt.relative_to(raiz).as_posix(), f"cues com origem = {video_rel}"
    return None, "nenhum .srt encontrado para este vídeo em legendas/ ou cortes/"


def cmd_novo(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    plat = canonica(args.plataforma)
    ins = Insumos(raiz)
    notas = []
    corte = None
    if args.corte:
        corte = ins.corte(args.corte)
        if corte is None:
            ids = ", ".join(str(c.get("id")) for c in ins.cortes) or "nenhum"
            raise ErroUso(f"O corte «{args.corte}» não está em cortes/plano.json.", f"Cortes disponíveis: {ids}. Gere com a skill video-cortes-verticais.")
        if plat == "youtube":
            raise ErroUso("`--corte` é para shorts, reels e tiktok; o pacote `youtube` é o vídeo longo.", "Para publicar o corte no YouTube use `novo shorts --corte …`.")
    elif plat in VERTICAIS and not args.video:
        candidatos = ins.cortes_da_plataforma(plat)
        if len(candidatos) == 1:
            corte = candidatos[0]
            notas.append(f"corte {corte.get('id')} escolhido por ser o único de cortes/plano.json para {plat}")
        elif candidatos:
            raise ErroUso(f"Há {len(candidatos)} cortes para {plat}: " + ", ".join(f"{c.get('id')} («{str(c.get('titulo') or '')[:30]}»)" for c in candidatos) + ".",
                          f"Diga qual: pacote.py novo {plat} --corte {candidatos[0].get('id')}")
        else:
            raise ErroUso(f"Não sei qual arquivo publicar em {plat}: cortes/plano.json não tem corte para esta plataforma.",
                          f"Passe --video <arquivo vertical> ou gere os cortes com a skill video-cortes-verticais.")
    if args.video:
        video_rel = relativo(raiz, args.video)
    elif corte:
        video_rel = str(corte.get("saida") or f"cortes/{corte.get('id')}.mp4")
    else:
        video_rel = "render/final.mp4"
    if not (raiz / video_rel).is_file():
        raise Erro(f"O arquivo de vídeo não existe: {raiz / video_rel}",
                   "Finalize o vídeo antes (video-montagem/video-mixagem para render/final.mp4; video-cortes-verticais para os cortes) ou passe --video.")
    cid = str(corte.get("id")) if corte else None

    padrao = Pacote(raiz, plat)
    pac = padrao
    mesma_peca = ""
    if cid and padrao.existe and str(padrao.meta.get("corte") or "") != cid:
        if not padrao.meta.get("corte") and padrao.meta.get("arquivo_video") == video_rel:
            # o pacote padrão foi criado com --video apontando para ESTE arquivo: é a mesma peça, não um segundo pacote ao lado
            mesma_peca = f" Ele foi criado com --video e aponta para o mesmo arquivo deste corte ({video_rel}): é a mesma peça."
            notas.append(f"o pacote padrão de {plat} já apontava para este arquivo (criado com --video); ele foi recriado ligado ao corte {cid}")
        else:
            pac = Pacote(raiz, plat, cid)   # o lugar padrão já é de outro corte: este vai para publicacao/<plataforma>/<corte>/
            notas.append(f"o pacote padrão de {plat} já é do corte {padrao.meta.get('corte') or '(vídeo sem corte)'}; este fica em {pac.rel(pac.pasta)}/ (seletor: {pac.id})")
    if pac.existe and not args.forcar:
        raise Erro(f"Já existe {pac.rel(pac.meta_path)} (título: «{str(pac.meta.get('titulo') or '')[:50]}»).{mesma_peca}",
                   "Para recomeçar do zero use --forcar (apaga título, abertura e hashtags); para mudar só o texto use `pacote.py descricao`; "
                   "para mudar agendamento, privacidade ou declarações use `pacote.py definir`.")
    substitui = pac.existe
    for outro in listar_pacotes(raiz):
        try:
            gemeo = outro.id != pac.id and outro.plataforma == plat and outro.meta.get("arquivo_video") == video_rel
        except Erro:
            gemeo = False
        if gemeo:
            notas.append(f"ATENÇÃO: o pacote «{outro.id}» já aponta para este mesmo arquivo em {plat}; publicar os dois é postar o vídeo duas vezes "
                         f"(apague a pasta {outro.rel(outro.pasta)}/ se ele sobrou)")

    if args.thumbnail and args.thumbnail.lower() in ("nenhuma", "none", "null"):
        thumb, nota_thumb = None, "sem thumbnail (pedido)"
    elif args.thumbnail:
        thumb, nota_thumb = relativo(raiz, args.thumbnail), "passada em --thumbnail"
    else:
        thumb, nota_thumb = _escolher_thumbnail(ins, plat)
    if args.legenda and args.legenda.lower() in ("nenhuma", "none", "null"):
        srt, nota_srt = None, "sem legenda (pedido)"
    elif args.legenda:
        srt, nota_srt = relativo(raiz, args.legenda), "passada em --legenda"
    else:
        srt, nota_srt = _escolher_srt(raiz, video_rel, cid)

    if args.privacidade not in PRIVACIDADES:
        raise ErroUso(f"Privacidade «{args.privacidade}» não existe.", "Use private (padrão), unlisted ou public.")
    if args.agendar:
        try:
            if datetime.fromisoformat(args.agendar).tzinfo is None:
                raise ValueError
        except ValueError:
            raise ErroUso(f"--agendar «{args.agendar}» não é uma data ISO 8601 com fuso.", "Exemplo: --agendar 2026-10-20T18:00:00-03:00")
    assinatura = (d.get("marca") or {}).get("assinatura")
    meta = {
        "versao": 1, "plataforma": plat,
        "titulo": nfc(args.titulo or (str(corte.get("titulo") or "") if corte else "")),
        "descricao": "", "tags": [], "hashtags": [], "capitulos": [],
        "arquivo_video": video_rel, "thumbnail": thumb, "legenda_srt": srt,
        "privacidade": args.privacidade, "agendar_para": args.agendar, "idioma": args.idioma,
        # ── campos acrescentados por esta skill (o contrato permite acrescentar)
        "corte": cid, "gancho": (str(corte.get("gancho") or "") if corte else ""),
        "abertura": "", "links": [], "assinatura": assinatura, "blocos": list(BLOCOS_PADRAO[plat]),
        "fontes_modo": "auto", "creditos_modo": "obrigatorios", "fato_ids": [],
        "conteudo_sintetico": None, "feito_para_criancas": False, "notificar_inscritos": True, "categoria_id": None,
        "da_sha256": d.sha256, "criado_em": agora_iso(), "atualizado_em": agora_iso(),
    }
    if substitui:                                    # --forcar: o pacote novo não nasce «enviado» nem com o checklist do anterior
        envio_antigo, checklist_antigo = pac.pasta / "envio.json", pac.pasta / "checklist.md"
        if envio_antigo.is_file():
            guardado = pac.pasta / f"envio_anterior_{agora().strftime('%Y%m%d-%H%M%S')}.json"
            os.replace(envio_antigo, guardado)
            notas.append(f"o pacote anterior já tinha sido enviado: o registro foi guardado em {pac.rel(guardado)} e este pacote começa sem envio")
        if checklist_antigo.is_file():
            checklist_antigo.unlink()
            notas.append("o checklist.md do pacote anterior foi apagado (gere outro depois de validar)")
    pac._meta = meta
    gravar_json(pac.meta_path, meta)
    lim = Limites()
    texto, _ = montar_descricao(pac, ins, lim)
    meta["descricao"] = texto.strip()
    gravar_json(pac.meta_path, meta)
    gravar_texto(pac.pasta / "descricao.txt", texto)
    atualizar_indice(raiz, d, lim, ins=ins)          # o índice lista o pacote desde que ele nasce

    diz(f"✓ pacote «{pac.id}» criado em {pac.rel(pac.meta_path)}")
    diz(f"  vídeo:      {video_rel}")
    diz(f"  thumbnail:  {thumb or '—'}   ({nota_thumb})")
    diz(f"  legenda:    {srt or '—'}   ({nota_srt})")
    diz(f"  assinatura: {assinatura or '— (marca.assinatura vazia na DA)'}")
    diz(f"  privacidade: {args.privacidade}" + (f" · agendado para {args.agendar}" if args.agendar else ""))
    for n in notas:
        diz(f"  nota: {n}")
    diz("Próximos passos: escrever título e abertura (references/copy.md) → "
        + ("`pacote.py capitulos` → " if plat == "youtube" else "") + f"`pacote.py descricao {pac.id} --titulo … --abertura …` → "
        + (f"`pacote.py definir {pac.id} --sintetico sim|nao` → " if plat in ("youtube", "shorts") else "") + f"`pacote.py validar {pac.id}`.")
    return SAIDA_OK


def cmd_capitulos(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    pac = resolver_seletor(raiz, args.pacote)
    if pac.plataforma != "youtube":
        raise ErroUso(f"Capítulos só existem no vídeo longo do YouTube, não em {NOME_PLATAFORMA[pac.plataforma]}.",
                      "Use `pacote.py capitulos youtube`.")
    lim = Limites()
    meta = pac.meta
    if "limites_texto.capitulos" in limites_que_faltam(lim, "youtube") and not args.limpar:
        raise Erro(f"As regras de capítulos do YouTube não foram encontradas em plataformas.json ({lim.origem}): sem elas nada seria conferido.",
                   "Atualize a skill video-direcao-de-arte (limites_texto.youtube.capitulos) e rode de novo.")
    if args.limpar:
        meta["capitulos"] = []
        meta.pop("capitulos_origem", None)
        pac.gravar()
        atualizar_indice(raiz, d, lim)
        diz(f"✓ capítulos removidos de {pac.rel(pac.meta_path)}. Rode `pacote.py descricao {pac.id}` para atualizar a descrição.")
        return SAIDA_OK
    if args.lista or args.arquivo:
        linhas = list(args.lista or [])
        origem = "lista passada em --lista"
        if args.arquivo:
            arq = Path(args.arquivo).expanduser()
            if not arq.is_file():
                raise ErroUso(f"O arquivo de capítulos não existe: {arq}")
            linhas += arq.read_text(encoding="utf-8-sig").splitlines()
            origem = str(arq)
        caps = ler_lista_de_capitulos(linhas)
        origem_rel = None
    elif args.mostrar:
        caps, origem, origem_rel = normalizar_capitulos(meta.get("capitulos") or []), "meta.json", meta.get("capitulos_origem")
    else:
        fonte = Path(args.de).expanduser() if args.de else raiz / "render" / "capitulos.json"
        if not fonte.is_absolute():
            fonte = (Path.cwd() / fonte) if (Path.cwd() / fonte).is_file() else raiz / fonte
        if not fonte.is_file():
            raise Erro(f"{fonte} não existe.",
                       "Peça os capítulos à skill video-montagem (render/capitulos.json) ou passe a lista: "
                       "pacote.py capitulos --lista \"00:00 Abertura\" \"01:12 …\" \"03:40 …\"")
        caps = normalizar_capitulos(ler_json(fonte))
        origem = str(fonte)
        try:
            origem_rel = fonte.resolve().relative_to(raiz).as_posix()
        except ValueError:
            origem_rel = None
    duracao = None
    video = pac.arquivo("arquivo_video")
    if video and video.is_file():
        try:
            duracao = sondar_video(video)["duracao"]
        except Erro:
            duracao = None
    problemas = conferir_capitulos(caps, lim, duracao)
    diz(f"Capítulos ({len(caps)}; origem: {origem}" + (f"; vídeo com {fmt_dur(duracao)}" if duracao else "") + "):")
    for linha in formatar_capitulos(caps):
        diz("  " + linha)
    if not caps:
        diz("  (nenhum)")
    if problemas:
        diz("")
        for _id, _sev, msg in problemas:
            diz(f"✗ {msg}", erro=True)
        regras = lim.obter("youtube", "capitulos")
        regras = regras if isinstance(regras, dict) else {}
        diz("Nada foi gravado. Regras do YouTube (plataformas.json → limites_texto.youtube.capitulos): "
            f"primeiro em {regras.get('primeiro_timestamp', '?')}, ao menos {regras.get('min_timestamps', '?')}, ordem crescente, "
            f"mínimo de {regras.get('duracao_min_capitulo_s', '?')} s cada.", erro=True)
        return SAIDA_ERRO
    if args.mostrar:
        return SAIDA_OK
    meta["capitulos"] = caps
    if origem_rel:
        meta["capitulos_origem"] = origem_rel
    else:
        meta.pop("capitulos_origem", None)
    pac.gravar()
    atualizar_indice(raiz, d, lim)
    diz(f"✓ {len(caps)} capítulos gravados em {pac.rel(pac.meta_path)}. Agora: `pacote.py descricao {pac.id}` (o bloco `capitulos` entra na descrição).")
    return SAIDA_OK


def _ler_links(valores: list[str] | None) -> list[dict]:
    links = []
    for v in valores or []:
        rotulo, sep, url = v.partition("=")
        if not sep or re.match(r"\s*https?://", rotulo):      # sem rótulo: o «=» é do próprio endereço (…/watch?v=abc)
            rotulo, url = "", v
        url = url.strip()
        if not re.match(r"https?://\S+$", url):
            raise ErroUso(f"Link inválido: «{v}».", "Formato: --link \"Rótulo=https://exemplo.com\" ou só --link \"https://exemplo.com\".")
        links.append({"rotulo": nfc(rotulo.strip()), "url": url})
    return links


def cmd_descricao(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    pac = resolver_seletor(raiz, args.pacote)
    ins, lim = Insumos(raiz), Limites()
    meta = pac.meta
    txt = pac.pasta / "descricao.txt"
    if args.adotar:
        if not txt.is_file():
            raise Erro(f"{pac.rel(txt)} não existe: não há o que adotar.", f"Rode `pacote.py descricao {pac.id}` para gerar.")
        meta["descricao"] = nfc(txt.read_text(encoding="utf-8-sig")).strip()
        meta["descricao_adotada"] = True
        pac.gravar()
        gravar_texto(txt, meta["descricao"] + "\n")
        atualizar_indice(raiz, d, lim, ins=ins)
        diz(f"✓ descricao.txt adotado como está ({fmt_int(conta_utf16(meta['descricao']))} caracteres). "
            f"Os blocos automáticos deixam de valer até o próximo `pacote.py descricao {pac.id}` sem --adotar.")
        return SAIDA_OK
    if args.abertura is not None and args.abertura_arquivo:
        raise ErroUso("Use --abertura ou --abertura-arquivo, não os dois.")
    if args.abertura_arquivo:
        arq = Path(args.abertura_arquivo).expanduser()
        if not arq.is_file():
            raise ErroUso(f"O arquivo de abertura não existe: {arq}")
        meta["abertura"] = nfc(arq.read_text(encoding="utf-8-sig").strip())
    elif args.abertura is not None:
        meta["abertura"] = nfc(args.abertura.replace("\\n", "\n").strip())
    if args.titulo is not None:
        meta["titulo"] = nfc(args.titulo.strip())
    if args.hashtags is not None:
        meta["hashtags"] = separar_hashtags(args.hashtags)
    if args.tags is not None:
        meta["tags"] = [nfc(t.strip()) for bloco in args.tags for t in bloco.split(",") if t.strip()]
    if args.link is not None:
        meta["links"] = _ler_links(args.link)
    if args.fatos is not None:
        meta["fato_ids"] = [f.strip() for bloco in args.fatos for f in re.split(r"[\s,]+", bloco) if f.strip()]
    if args.broll is not None:
        valores = [b.strip() for bloco in args.broll for b in re.split(r"[\s,]+", bloco) if b.strip()]
        if [v.lower() for v in valores] == ["auto"]:
            meta.pop("broll_ids", None)
        else:
            meta["broll_ids"] = [] if [v.lower() for v in valores] == ["nenhum"] else valores
    if args.blocos is not None:
        ordem = [b.strip().lower() for b in args.blocos.split(",") if b.strip()]
        ruins = [b for b in ordem if b not in BLOCOS]
        if ruins:
            raise ErroUso(f"Bloco desconhecido: {', '.join(ruins)}.", "Blocos válidos: " + ", ".join(BLOCOS) + ".")
        meta["blocos"] = ordem
    if args.fontes is not None:
        meta["fontes_modo"] = args.fontes
    if args.creditos is not None:
        meta["creditos_modo"] = args.creditos
    assinatura = (d.get("marca") or {}).get("assinatura")
    meta["assinatura"] = assinatura          # sempre a da DA atual: a marca não se decide na peça
    meta.pop("descricao_adotada", None)
    texto, rel = montar_descricao(pac, ins, lim)
    meta["descricao"] = texto.strip()
    pac.gravar()
    gravar_texto(txt, texto)
    atualizar_indice(raiz, d, lim, ins=ins)

    plat = pac.plataforma
    nome_campo = "descrição" if plat in ("youtube", "shorts") else "legenda"
    diz(f"✓ {nome_campo} de «{pac.id}» montada: {fmt_int(conta_utf16(meta['descricao']))} caracteres, {fmt_int(conta_bytes(meta['descricao']))} bytes → {pac.rel(txt)}")
    ordem = meta.get("blocos") or list(BLOCOS_PADRAO[plat])
    diz("  blocos: " + " → ".join(f"{b}{'' if rel.get(b) else ' (vazio)'}" for b in ordem)
        + (f"   [fontes: {rel['fontes_origem']}]" if rel.get("fontes") else ""))
    if not meta.get("abertura"):
        diz("  ! sem abertura: escreva as duas primeiras linhas (references/copy.md) e rode de novo com --abertura.")
    obrig = ins.creditos_obrigatorios(meta)
    if obrig and "creditos" not in ordem:
        diz(f"  ! há {len(obrig)} crédito(s) obrigatório(s) de b-roll e o bloco `creditos` está fora da ordem: a validação vai reprovar.", erro=True)
    excluidos = ins.creditos_excluidos(meta)
    if excluidos:
        ids = ", ".join(str(item.get("id")) for item, _ev, _cenas in excluidos)
        diz(f"  ! `--broll` tirou desta peça b-roll com atribuição obrigatória que os insumos dizem estar em uso ({ids}): "
            + ("a validação vai reprovar." if not meta.get("corte") else "a validação vai registrar a exceção — confira no vídeo."), erro=True)
    if args.mostrar:
        diz("─" * 60)
        diz(texto.rstrip())
        diz("─" * 60)
    return SAIDA_OK


_NENHUM = ("nenhum", "nenhuma", "none", "null", "")


def _sim_nao(valor: str, opcao: str) -> bool:
    v = valor.strip().lower()
    if v in ("sim", "s", "true", "1"):
        return True
    if v in ("nao", "não", "n", "false", "0"):
        return False
    raise ErroUso(f"{opcao} «{valor}» não é sim nem nao.", f"Use `{opcao} sim` ou `{opcao} nao`.")


def cmd_definir(args) -> int:
    """Muda os campos que não são texto — agenda, privacidade, declarações, thumbnail, legenda — sem recriar o pacote."""
    raiz, d = abrir_projeto(args.projeto)
    pac = resolver_seletor(raiz, args.pacote)
    meta, plat, mudou = pac.meta, pac.plataforma, []

    def por(campo: str, valor, rotulo: str) -> None:
        if campo not in meta or meta[campo] != valor or type(meta[campo]) is not type(valor):
            meta[campo] = valor
            if valor is None:
                mostra = "nenhum" if rotulo == "agendamento" else "nenhuma"
            else:
                mostra = ("sim" if valor else "não") if isinstance(valor, bool) else valor
            mudou.append(f"{rotulo}: {mostra}")

    if args.agendar is not None:
        if args.agendar.strip().lower() in _NENHUM:
            por("agendar_para", None, "agendamento")
        else:
            try:
                if datetime.fromisoformat(args.agendar.strip()).tzinfo is None:
                    raise ValueError
            except ValueError:
                raise ErroUso(f"--agendar «{args.agendar}» não é uma data ISO 8601 com fuso.",
                              "Exemplo: --agendar 2026-10-20T18:00:00-03:00 (ou --agendar nenhum para tirar o agendamento).")
            por("agendar_para", args.agendar.strip(), "agendamento")
    if args.privacidade is not None:
        if args.privacidade not in PRIVACIDADES:
            raise ErroUso(f"Privacidade «{args.privacidade}» não existe.", "Use private (padrão da casa), unlisted ou public.")
        por("privacidade", args.privacidade, "privacidade")
    for opcao, campo, rotulo in (("sintetico", "conteudo_sintetico", "conteúdo sintético (IA realista)"),
                                 ("para_criancas", "feito_para_criancas", "feito para crianças"), ("notificar", "notificar_inscritos", "notificar inscritos")):
        bruto = getattr(args, opcao)
        if bruto is not None:
            por(campo, _sim_nao(bruto, "--" + opcao.replace("_", "-")), rotulo)
    for opcao, campo, rotulo in (("thumbnail", "thumbnail", "thumbnail"), ("legenda", "legenda_srt", "legenda")):
        bruto = getattr(args, opcao)
        if bruto is None:
            continue
        if bruto.strip().lower() in _NENHUM:
            por(campo, None, rotulo)
            continue
        rel = relativo(raiz, bruto)
        if not (raiz / rel).is_file():
            raise Erro(f"O arquivo de {rotulo} não existe: {raiz / rel}", "Confira o caminho (relativo à raiz do projeto) ou gere o arquivo na skill dona.")
        por(campo, rel, rotulo)
    if args.idioma is not None:
        if not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", args.idioma.strip()):
            raise ErroUso(f"Idioma «{args.idioma}» não é um código BCP-47.", "Use pt-BR.")
        por("idioma", args.idioma.strip(), "idioma")
    if args.categoria is not None:
        if args.categoria.strip().lower() in _NENHUM:
            por("categoria_id", None, "categoria")
        elif not args.categoria.strip().isdigit():
            raise ErroUso(f"--categoria «{args.categoria}» não é um id de categoria do YouTube.", "É um número (os ids variam por região: consulte videoCategories.list da API) ou `nenhuma` para ficar com o padrão do YouTube.")
        else:
            por("categoria_id", args.categoria.strip(), "categoria")
    opcoes = ("agendar", "privacidade", "sintetico", "para_criancas", "notificar", "thumbnail", "legenda", "idioma", "categoria")
    if all(getattr(args, o) is None for o in opcoes):
        raise ErroUso("Nada a definir.", "Passe ao menos uma opção: --agendar, --privacidade, --sintetico, --para-criancas, --notificar, "
                                         "--thumbnail, --legenda, --idioma ou --categoria (pacote.py definir --help).")
    if not mudou:
        diz(f"· «{pac.id}» já estava assim; nada foi alterado.")
        return SAIDA_OK
    pac.gravar()
    atualizar_indice(raiz, d, Limites())
    diz(f"✓ «{pac.id}» atualizado — " + "; ".join(mudou))
    if meta.get("agendar_para") and plat in ("youtube", "shorts") and meta.get("privacidade") != "private":
        diz(f"  ! agendamento com privacidade «{meta.get('privacidade')}»: o YouTube só agenda vídeo privado; `validar` vai reprovar.", erro=True)
    if meta.get("agendar_para") and plat in ("reels", "tiktok"):
        diz(f"  · em {NOME_PLATAFORMA[plat]} o agendamento é feito à mão no aplicativo; a data do pacote é o lembrete.")
    diz(f"O pacote mudou: rode `pacote.py validar {pac.id}` de novo e mostre o plano atualizado ao usuário (a aprovação anterior não vale para ele).")
    return SAIDA_OK


def _imprimir_validacao(pac: Pacote, v: dict, detalhado: bool = True) -> None:
    marca = "✓" if v["ok"] else "✗"
    estado = "aprovado" if v["ok"] else "REPROVADO"
    if v.get("excecoes"):
        estado += " COM EXCEÇÃO (" + "; ".join(sorted({ROTULO_EXCECAO.get(e.get("tipo"), str(e.get("tipo"))) for e in v["excecoes"]})) + ")"
    diz(f"{marca} {pac.id} — {estado}: {v['erros']} erro(s), {v['avisos']} aviso(s)")
    simbolo = {"erro": "✗", "aviso": "!", "info": "·"}
    for sev in ("erro", "aviso", "info"):
        for i in v["itens"]:
            if i["severidade"] != sev or (sev == "info" and not detalhado):
                continue
            diz(f"  {simbolo[sev]} [{i['categoria']}] {i['mensagem']}")
            if i.get("como_corrigir") and sev != "info":
                diz(f"      → {i['como_corrigir']}")


def cmd_validar(args) -> int:
    if args.motivo and not args.sem_qa:
        raise ErroUso("--motivo só faz sentido junto com --sem-qa.")
    raiz, d = abrir_projeto(args.projeto)
    lim, ins = Limites(), Insumos(raiz)
    if args.pacotes:
        pacs = [resolver_seletor(raiz, s) for s in args.pacotes]
    else:
        pacs = listar_pacotes(raiz)
        if not pacs:
            raise Erro("Nenhum pacote em publicacao/.", "Crie o primeiro com: pacote.py novo youtube   (ou shorts/reels/tiktok --corte K01)")
    novas = {}
    for pac in pacs:
        novas[pac.id] = validar_pacote(pac, lim, ins, d, sem_qa=args.sem_qa, motivo_sem_qa=args.motivo)
    indice = atualizar_indice(raiz, d, lim, novas, ins=ins)
    reprovou = False
    if args.json:
        print(json.dumps({"ok": all(v["ok"] for v in novas.values()), "pacotes": novas, "indice": "publicacao/pacote.json"}, ensure_ascii=False, indent=2))
    else:
        ver = lim.verificado_em
        diz(f"Limites: {lim.origem} (verificado em {ver.isoformat() if ver else '?'}). DA {d.sha256[:8]}…")
        for pac in pacs:
            _imprimir_validacao(pac, novas[pac.id], detalhado=not args.resumido)
        diz(f"Índice atualizado: {caminho_indice(raiz).relative_to(raiz).as_posix()}")
        if all(v["ok"] for v in novas.values()):
            diz("Próximo passo: mostrar título, thumbnail e descrição ao usuário → `pacote.py checklist <pacote>` (manual) "
                "ou `enviar_youtube.py enviar <pacote>` (plano de envio; nada sobe sem o «sim» dele). "
                "Na hora de publicar, tudo isto é conferido de novo: esta aprovação não vale se o QA, a DA, um fato ou um crédito mudar.")
        if args.sem_qa and any(v.get("excecao") for v in novas.values()):
            diz("! EXCEÇÃO REGISTRADA: portão de QA dispensado" + (f" — motivo: {args.motivo}" if args.motivo else " — sem motivo informado (use --motivo)") + ".", erro=True)
        elif args.sem_qa:
            diz("· --sem-qa não foi necessário: o QA está em ordem para estes pacotes; nenhuma exceção foi registrada.")
    for v in novas.values():
        if not v["ok"] or (args.estrito and v["avisos"]):
            reprovou = True
    return SAIDA_ERRO if reprovou else SAIDA_OK


def cmd_checklist(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    pac = resolver_seletor(raiz, args.pacote)
    lim, ins = Limites(), Insumos(raiz)
    val = validacao_gravada(raiz, pac.id)
    estado, viva = situacao_do_pacote(pac, val, lim, ins, d)      # refaz a conferência: a validação gravada pode ter vencido
    texto = gerar_checklist(pac, lim, val, estado, viva)
    destino = pac.pasta / "checklist.md"
    gravar_texto(destino, texto)
    atualizar_indice(raiz, d, lim, ins=ins)
    if not args.silencioso:
        diz(texto)
    diz(f"✓ checklist gravado em {pac.rel(destino)} (validação: {ROTULO_ESTADO[estado]})")
    if estado == "vencida":
        for m in erros_de(viva):
            diz(f"  ✗ {m}", erro=True)
        diz(f"  → A validação gravada não vale mais. Resolva e rode `pacote.py validar {pac.id}`.", erro=True)
    return SAIDA_OK if estado in ESTADOS_OK else SAIDA_ERRO


def cmd_registrar(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    pac = resolver_seletor(raiz, args.pacote)
    if not re.match(r"https?://\S+$", args.url.strip()):
        raise ErroUso(f"URL inválida: «{args.url}».", "Passe o endereço público do post, começando por https://.")
    quando = args.quando or agora_iso()
    try:
        datetime.fromisoformat(quando)
    except ValueError:
        raise ErroUso(f"--quando «{quando}» não é uma data ISO 8601.", "Exemplo: 2026-10-20T18:00:00-03:00.")
    destino = pac.pasta / "envio.json"
    if destino.is_file() and not args.forcar:
        anterior = ler_json(destino)
        anterior = anterior if isinstance(anterior, dict) else {}
        raise Erro(f"Já há um envio registrado para «{pac.id}»: {anterior.get('url')} ({anterior.get('enviado_em')}).", "Para substituir o registro use --forcar.")
    lim, ins = Limites(), Insumos(raiz)
    val = validacao_gravada(raiz, pac.id)
    estado, viva = situacao_do_pacote(pac, val, lim, ins, d)
    registro = {"plataforma": pac.plataforma, "pacote": pac.id, "url": args.url.strip(), "enviado_em": quando, "por": args.por,
                "validacao_no_envio": estado, "validado_em": (val or {}).get("validado_em"),
                "excecoes": list((val or {}).get("excecoes") or []) if estado == "ok_com_excecao" else [],
                "titulo": pac.meta.get("titulo")}
    if estado == "vencida":
        registro["problemas_no_envio"] = erros_de(viva)
    gravar_json(destino, registro)
    atualizar_indice(raiz, d, lim, ins=ins)
    diz(f"✓ envio de «{pac.id}» registrado em {pac.rel(destino)} ({args.por}; validação no momento: {ROTULO_ESTADO[estado]})")
    for linha in linhas_de_excecao(val) if estado == "ok_com_excecao" else []:
        diz(f"  ! publicado com exceção registrada: {linha}")
    if estado not in ESTADOS_OK:
        diz("  ! o pacote não estava validado e aprovado quando foi publicado: confira o post no aplicativo.", erro=True)
        for m in erros_de(viva) if estado == "vencida" else []:
            diz(f"    ✗ {m}", erro=True)
    return SAIDA_OK


def cmd_resumo(args) -> int:
    raiz, d = abrir_projeto(args.projeto)
    lim = Limites()
    indice = atualizar_indice(raiz, d, lim)
    if args.json:
        print(json.dumps(indice, ensure_ascii=False, indent=2))
        return SAIDA_OK if indice["ok"] else SAIDA_ERRO
    diz(f"Projeto: {indice['projeto']} · DA {indice['da_sha256'][:8]}… · limites verificados em {indice['limites']['verificado_em']} "
        f"(há {indice['limites']['idade_dias']} dia(s))")
    if not indice["pacotes"]:
        diz("Nenhum pacote em publicacao/. Crie com: pacote.py novo youtube")
        return SAIDA_ERRO
    diz(tabela_do_indice(indice))
    for ent in indice["pacotes"]:
        if ent["estado"] == "vencida":
            diz(f"✗ {ent['id']}: a validação de {(ent.get('validacao') or {}).get('validado_em')} venceu — a conferência de agora reprova:")
            for m in ent["conferencia"]["erros"]:
                diz(f"    ✗ {m}")
    for ex in indice["excecoes"]:
        rotulo = ROTULO_EXCECAO.get(ex.get("tipo"), str(ex.get("tipo")))
        detalhe = f"motivo: {ex.get('motivo')}" if ex.get("tipo") == "sem_qa" else "; ".join(str(x) for x in ex.get("problemas") or [])
        diz(f"! exceção registrada em {ex.get('pacote')}: {rotulo} em {ex.get('em')} — {detalhe}")
    for ent in indice["pacotes"]:
        envio = ent.get("envio")
        if isinstance(envio, dict):
            diz(f"  enviado: {ent['id']} → {envio.get('url') or envio.get('video_id')} ({envio.get('enviado_em')})")
    diz(("✓ tudo validado e conferido agora" if indice["ok"] else "✗ há pacote não validado, reprovado, alterado depois da validação ou com a validação vencida")
        + f" — {caminho_indice(raiz).relative_to(raiz).as_posix()}")
    return SAIDA_OK if indice["ok"] else SAIDA_ERRO


# ─────────────────────────────────────────────────────────────── argparse ──
_TRADUCOES = (
    (r"the following arguments are required: (.*)", r"faltou informar: \1"),
    (r"unrecognized arguments: (.*)", r"opção ou argumento desconhecido: \1"),
    (r"argument (.*): expected one argument", r"a opção \1 precisa de um valor"),
    (r"argument (.*): expected at least one argument", r"a opção \1 precisa de pelo menos um valor"),
    (r"argument (.*): invalid choice: (.*) \(choose from (.*)\)", r"valor inválido para \1: \2 (opções: \3)"),
    (r"argument (.*): invalid int value: (.*)", r"valor inválido para \1: \2 (esperava um número inteiro)"),
    (r"argument (.*): invalid float value: (.*)", r"valor inválido para \1: \2 (esperava um número, com ponto decimal)"),
    (r"argument (.*): invalid \S+ value: (.*)", r"valor inválido para \1: \2"),
    (r"argument (.*): not allowed with argument (.*)", r"a opção \1 não pode ser usada junto com \2"),
    (r"invalid choice: (.*) \(choose from (.*)\)", r"subcomando desconhecido: \1 (opções: \2)"),
)


class Parser(argparse.ArgumentParser):
    """argparse em português: ajuda traduzida e erro de uso com código 64 (2 é 'projeto sem DA')."""

    def __init__(self, *a, **k):
        k.setdefault("add_help", False)
        k.setdefault("allow_abbrev", False)     # `--sem` não pode virar `--sem-qa`, nem `--conf` virar `--confirmar`
        k.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        super().__init__(*a, **k)
        self._positionals.title = "argumentos"
        self._optionals.title = "opções"
        self.add_argument("-h", "--help", action="help", help="mostra esta ajuda e sai")

    def format_usage(self):
        return super().format_usage().replace("usage:", "uso:", 1)

    def format_help(self):
        return super().format_help().replace("usage:", "uso:", 1)

    def error(self, message):
        for padrao, troca in _TRADUCOES:
            novo, n = re.subn(padrao, troca, message)
            if n:
                message = novo
                break
        self.print_usage(sys.stderr)
        self.exit(SAIDA_USO, f"erro de uso: {message}\nAjuda completa: {self.prog} --help\n")


def montar_parser() -> Parser:
    p = Parser(prog="pacote.py", description=(
        "Pacote de publicação por plataforma: meta.json, descricao.txt, checklist e validação contra os limites vigentes.\n"
        "Plataformas: youtube (vídeo longo), shorts, reels, tiktok. Um pacote é <plataforma> ou <plataforma>/<corte>."),
        epilog=("Exemplos:\n"
                "  pacote.py novo youtube\n"
                "  pacote.py capitulos\n"
                "  pacote.py descricao youtube --titulo \"…\" --abertura \"…\" --hashtags \"#IA #LLM\"\n"
                "  pacote.py novo reels --corte K01 && pacote.py descricao reels --abertura \"…\"\n"
                "  pacote.py definir youtube --agendar 2026-10-20T18:00:00-03:00 --sintetico nao\n"
                "  pacote.py validar && pacote.py checklist youtube && pacote.py resumo\n"
                "Códigos de saída: 0 ok · 1 reprovado/erro · 2 projeto sem direção de arte · 64 uso incorreto."))
    p.add_argument("--projeto", metavar="PASTA", help="pasta do projeto ou qualquer pasta dentro dele (padrão: pasta atual)")
    sub = p.add_subparsers(dest="comando", metavar="<subcomando>", parser_class=Parser)

    s = sub.add_parser("novo", help="cria publicacao/<plataforma>/meta.json com os campos técnicos",
                       description="Cria o pacote de uma plataforma preenchendo arquivo de vídeo, thumbnail escolhida, .srt e assinatura da DA. "
                                   "O texto (título, abertura, hashtags) quem escreve é o Claude, depois.")
    s.add_argument("plataforma", help="youtube | shorts | reels | tiktok")
    s.add_argument("--video", metavar="ARQ", help="arquivo de vídeo dentro do projeto (padrão: render/final.mp4, ou a saída do corte)")
    s.add_argument("--corte", metavar="K01", help="id do corte em cortes/plano.json (shorts, reels, tiktok)")
    s.add_argument("--thumbnail", metavar="ARQ", help="imagem dentro do projeto, ou 'nenhuma' (padrão: a escolhida em thumbs/variacoes.json)")
    s.add_argument("--legenda", metavar="ARQ", help="arquivo .srt dentro do projeto, ou 'nenhuma' (padrão: procura em cortes/ e legendas/)")
    s.add_argument("--titulo", metavar="TEXTO", help="título inicial (padrão: o título do corte, se houver)")
    s.add_argument("--privacidade", default="private", metavar="P", help="private (padrão) | unlisted | public")
    s.add_argument("--agendar", metavar="ISO", help="data e hora com fuso, ex.: 2026-10-20T18:00:00-03:00")
    s.add_argument("--idioma", default="pt-BR", metavar="COD", help="idioma do título, da descrição e da legenda (padrão: pt-BR)")
    s.add_argument("--forcar", action="store_true", help="recria o pacote do zero se ele já existir")
    s.set_defaults(func=cmd_novo)

    s = sub.add_parser("capitulos", help="lê, formata e valida os capítulos do YouTube",
                       description="Grava os capítulos no meta.json do pacote youtube a partir de render/capitulos.json ou de uma lista «mm:ss Título». "
                                   "Valida as regras oficiais lidas do kit (tempo do primeiro capítulo, quantidade mínima, ordem crescente, duração mínima de cada um); "
                                   "com erro, nada é gravado.")
    s.add_argument("pacote", nargs="?", default="youtube", help="pacote (padrão: youtube)")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--de", metavar="ARQ.json", help="arquivo de capítulos [{\"t\": s, \"titulo\": \"…\"}] (padrão: render/capitulos.json)")
    g.add_argument("--lista", nargs="+", metavar="\"mm:ss Título\"", help="capítulos na linha de comando")
    g.add_argument("--arquivo", metavar="ARQ.txt", help="arquivo de texto com uma linha «mm:ss Título» por capítulo")
    g.add_argument("--mostrar", action="store_true", help="só mostra e confere os capítulos já gravados")
    g.add_argument("--limpar", action="store_true", help="remove os capítulos do pacote")
    s.set_defaults(func=cmd_capitulos)

    s = sub.add_parser("descricao", help="monta descricao.txt por blocos e atualiza o meta.json",
                       description="Monta a descrição (YouTube/Shorts) ou a legenda do post (Reels/TikTok) nesta ordem configurável: "
                                   + ", ".join(BLOCOS) + ". Os valores passados ficam gravados no meta.json; rodar de novo sem opções só remonta.")
    s.add_argument("pacote", help="youtube | shorts | reels | tiktok | <plataforma>/<corte>")
    s.add_argument("--titulo", metavar="TEXTO", help="título do vídeo")
    s.add_argument("--abertura", metavar="TEXTO", help="abertura escrita pelo Claude (use \\n para quebrar linha)")
    s.add_argument("--abertura-arquivo", metavar="ARQ", help="lê a abertura de um arquivo de texto")
    s.add_argument("--hashtags", nargs="+", metavar="#TAG", help="hashtags (substitui as anteriores)")
    s.add_argument("--tags", nargs="+", metavar="TAG", help="tags do YouTube separadas por vírgula (substitui as anteriores)")
    s.add_argument("--link", action="append", metavar="\"Rótulo=URL\"", help="link do bloco de links (repita a opção; substitui os anteriores)")
    s.add_argument("--fatos", nargs="+", metavar="F001", help="ids de fatos citados nesta peça (além dos marcados no roteiro)")
    s.add_argument("--broll", nargs="+", metavar="B001", help="ids de b-roll que aparecem nesta peça; 'nenhum' ou 'auto' (padrão: auto, por usado_em)")
    s.add_argument("--blocos", metavar="a,b,c", help="ordem dos blocos, ex.: abertura,capitulos,fontes,creditos,links,hashtags")
    s.add_argument("--fontes", choices=("auto", "fontes-md", "fatos", "nenhuma"), help="de onde vem o bloco de fontes (padrão: auto = pesquisa/fontes.md, senão fatos citados)")
    s.add_argument("--creditos", choices=("obrigatorios", "todos"), help="quais créditos de b-roll entram (padrão: obrigatorios)")
    s.add_argument("--adotar", action="store_true", help="adota o descricao.txt editado à mão como descrição final")
    s.add_argument("--mostrar", action="store_true", help="imprime o texto final")
    s.set_defaults(func=cmd_descricao)

    s = sub.add_parser("definir", help="muda agendamento, privacidade, declarações, thumbnail ou legenda de um pacote existente",
                       description="Altera os campos que não são texto sem recriar o pacote (título, abertura e hashtags ficam como estão). "
                                   "Depois de definir, rode `validar` de novo: o pacote mudou.")
    s.add_argument("pacote", help="youtube | shorts | reels | tiktok | <plataforma>/<corte>")
    s.add_argument("--agendar", metavar="ISO|nenhum", help="data e hora com fuso, ex.: 2026-10-20T18:00:00-03:00; `nenhum` tira o agendamento")
    s.add_argument("--privacidade", metavar="P", help="private | unlisted | public")
    s.add_argument("--sintetico", metavar="sim|nao", help="há cena REALISTA gerada ou alterada por IA? (animação e gráfico não contam)")
    s.add_argument("--para-criancas", metavar="sim|nao", help="o vídeo é feito para crianças? (YouTube)")
    s.add_argument("--notificar", metavar="sim|nao", help="notificar os inscritos no envio pela API (YouTube)")
    s.add_argument("--thumbnail", metavar="ARQ|nenhuma", help="imagem dentro do projeto, ou `nenhuma`")
    s.add_argument("--legenda", metavar="ARQ|nenhuma", help="arquivo .srt dentro do projeto, ou `nenhuma`")
    s.add_argument("--idioma", metavar="COD", help="idioma do texto e da legenda (BCP-47, ex.: pt-BR)")
    s.add_argument("--categoria", metavar="ID|nenhuma", help="id numérico da categoria do YouTube, ou `nenhuma` (padrão do YouTube)")
    s.set_defaults(func=cmd_definir)

    s = sub.add_parser("validar", help="confere os pacotes contra plataformas.json e o portão de QA",
                       description="Confere texto (caracteres e bytes), tags, hashtags, vídeo (ffprobe), thumbnail, .srt, agendamento, fatos, "
                                   "créditos e o portão de QA. Grava o resultado em publicacao/pacote.json. Sai com 1 se houver erro.")
    s.add_argument("pacotes", nargs="*", metavar="pacote", help="pacotes a validar (padrão: todos)")
    s.add_argument("--sem-qa", action="store_true", help="não reprova pelo portão de QA; registra a exceção no pacote")
    s.add_argument("--motivo", metavar="TEXTO", help="motivo da exceção de QA (fica gravado)")
    s.add_argument("--estrito", action="store_true", help="avisos também reprovam")
    s.add_argument("--resumido", action="store_true", help="não lista os itens informativos")
    s.add_argument("--json", action="store_true", help="imprime o resultado em JSON")
    s.set_defaults(func=cmd_validar)

    s = sub.add_parser("checklist", help="passo a passo manual de envio, com os campos prontos para colar",
                       description="Gera publicacao/<pacote>/checklist.md e imprime. Refaz a conferência na hora: sai com 1 se o pacote "
                                   "não estiver validado, ou se a validação gravada não valer mais (QA, DA, fatos, créditos ou datas mudaram).")
    s.add_argument("pacote", help="youtube | shorts | reels | tiktok | <plataforma>/<corte>")
    s.add_argument("--silencioso", action="store_true", help="só grava o arquivo, sem imprimir o conteúdo")
    s.set_defaults(func=cmd_checklist)

    s = sub.add_parser("registrar", help="anota um envio feito à mão, por conector ou pelo navegador",
                       description="Grava publicacao/<pacote>/envio.json com o endereço do post (o enviar_youtube.py grava o dele sozinho). "
                                   "Serve para o resumo mostrar o que já foi ao ar em Reels e TikTok.")
    s.add_argument("pacote", help="youtube | shorts | reels | tiktok | <plataforma>/<corte>")
    s.add_argument("--url", required=True, metavar="URL", help="endereço público do post")
    s.add_argument("--por", choices=("manual", "conector", "navegador"), default="manual", help="como foi enviado (padrão: manual)")
    s.add_argument("--quando", metavar="ISO", help="data e hora do envio (padrão: agora)")
    s.add_argument("--forcar", action="store_true", help="substitui um registro existente")
    s.set_defaults(func=cmd_registrar)

    s = sub.add_parser("resumo", help="regrava publicacao/pacote.json e mostra a tabela de pacotes",
                       description="Índice de todos os pacotes com o estado de AGORA: refaz a conferência de cada pacote validado e marca o que "
                                   "mudou depois da validação ou cuja validação venceu.")
    s.add_argument("--json", action="store_true", help="imprime o índice em JSON")
    s.set_defaults(func=cmd_resumo)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = montar_parser()
    args = parser.parse_args(argv)
    _SHA_VISTO.clear()                      # o sha256 dos vídeos vale só para esta execução
    if not getattr(args, "func", None):
        parser.print_help()
        return SAIDA_USO
    try:
        return args.func(args)
    except Erro as e:
        prefixo = "erro de uso" if isinstance(e, ErroUso) else "erro"
        diz(f"{prefixo}: {e}", erro=True)
        return e.codigo
    except Exception as e:                      # erros do kit (DAErro, SemDA) têm mensagem e código próprios
        codigo = getattr(e, "codigo", None)
        if codigo is not None and hasattr(e, "mensagem"):
            diz(f"erro: {e}", erro=True)
            if codigo == SAIDA_SEM_DA:
                diz("Sem direção de arte não se publica: chame a skill video-direcao-de-arte e volte depois.", erro=True)
            return int(codigo)
        return erro_interno(e)


def erro_interno(e: Exception) -> int:
    """Defeito do script ou arquivo do projeto num formato que ninguém previu: uma linha, código 1 — a mesma
    convenção do kit (DA_DEBUG=1 mostra o traceback; a suíte roda assim, para que defeito nenhum se esconda)."""
    if os.environ.get("DA_DEBUG") == "1":
        raise e
    diz(f"erro interno: {type(e).__name__}: {e}", erro=True)
    diz("  → É defeito do script ou um arquivo do projeto em formato inesperado (JSON editado à mão?). "
        "Rode de novo com DA_DEBUG=1 na frente do comando para ver onde parou.", erro=True)
    return SAIDA_ERRO


if __name__ == "__main__":
    sys.exit(main())
