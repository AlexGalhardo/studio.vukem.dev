#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enviar_youtube.py — envia um pacote validado pela YouTube Data API v3 (só stdlib).

    enviar_youtube.py autorizar [--legendas] [--confirmar]     login OAuth feito PELO USUÁRIO no navegador dele
    enviar_youtube.py enviar <pacote> [--simular]              (padrão) imprime o plano completo; não toca a rede
    enviar_youtube.py enviar <pacote> --confirmar CODIGO       envia; CODIGO é o que a simulação imprimiu
    enviar_youtube.py enviar <pacote> --reenviar               plano (e código próprio) para enviar DE NOVO um pacote já enviado
    enviar_youtube.py estado                                   conta autorizada e envios pendentes (sem segredos)

Regras da casa embutidas no código:
  · simular é o padrão; enviar exige --confirmar com o código do plano que o usuário aprovou;
  · privacidade padrão SEMPRE private; o primeiro envio real por esta máquina é privado e sem agendamento;
  · só envia pacote validado (publicacao/pacote.json), que não mudou depois da validação E que continua passando
    na conferência refeita na hora (QA, DA, fatos, créditos e datas são conferidos de novo na simulação e no envio);
  · o código de confirmação vale para UM envio: reenviar o mesmo pacote gera outro código;
  · nunca imprime token, segredo do cliente nem o endereço da sessão de envio;
  · envio retomável: interrompido, o mesmo comando continua de onde parou.

NÃO TESTADO CONTRA A API REAL (não há credenciais nesta máquina): testado contra um servidor local que
imita o subconjunto usado do protocolo. Protocolo, escopos e cotas conferidos na documentação oficial em
2026-10-06 — links em references/youtube-api.md.

Credenciais: $VIDEO_OPS_HOME/youtube_client_secret.json (cliente OAuth do tipo «App para computador»,
fornecido pelo usuário) e $VIDEO_OPS_HOME/youtube_token.json (criado aqui, permissão 600).
Códigos de saída: 0 ok · 1 erro/recusado · 2 projeto sem direção de arte · 64 uso incorreto.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import base64
import hashlib
import http.server
import json
import os
import random
import secrets
import socket
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import pacote as P  # noqa: E402

Erro, ErroUso = P.Erro, P.ErroUso

# ── endereços oficiais (conferidos em 2026-10-06; ver references/youtube-api.md)
URL_AUTORIZACAO = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
URL_API = "https://www.googleapis.com/youtube/v3"
ESCOPO_ENVIO = "https://www.googleapis.com/auth/youtube.upload"        # videos.insert, thumbnails.set
ESCOPO_LEITURA = "https://www.googleapis.com/auth/youtube.readonly"    # channels.list (mostrar a conta)
ESCOPO_LEGENDAS = "https://www.googleapis.com/auth/youtube.force-ssl"  # captions.insert (escopo amplo: só com --legendas)
MULTIPLO_PEDACO = 256 * 1024          # "The chunk size must be a multiple of 256 KB"
# Cotas: só informam o plano impresso (nada é decidido com elas). Fonte e data em references/youtube-api.md §6.
COTAS = {"verificado_em": "2026-10-06", "videos_insert": "1 das 100 chamadas diárias de videos.insert",
         "thumbnails_set": "~50 unidades das 10.000 diárias", "captions_insert": "400 unidades das 10.000 diárias"}
PEDACO_PADRAO_MB = 8
CODIGOS_REPETIVEIS = (500, 502, 503, 504)
VAR_TESTE = "VIDEO_OPS_YT_TESTE_BASE"  # http://127.0.0.1:PORTA — SOMENTE para testes; só aceita endereço de loopback
LOOPBACK = ("127.0.0.1", "localhost", "::1")
TIPOS_VIDEO = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".mkv": "video/x-matroska"}
TIPOS_IMAGEM = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class ErroRede(Erro):
    """Falha de transporte (queda, tempo esgotado, 5xx): vale tentar de novo."""


class ErroAPI(Erro):
    def __init__(self, status: int, motivo: str, mensagem: str, dica: str | None = None):
        super().__init__(f"a API respondeu {status} ({motivo}): {mensagem}", dica)
        self.status, self.motivo = status, motivo


class SessaoExpirada(Erro):
    pass


# ───────────────────────────────────────────────────────────── endereços ──
class Enderecos:
    def __init__(self):
        base = os.environ.get(VAR_TESTE, "").strip().rstrip("/")
        self.teste = bool(base)
        if base:
            u = urllib.parse.urlsplit(base)
            if u.scheme != "http" or (u.hostname or "") not in LOOPBACK:
                raise Erro(f"{VAR_TESTE} só aceita endereço de loopback (http://127.0.0.1:PORTA); veio «{base}».",
                           "Essa variável existe só para a suíte de testes. Remova-a para falar com o Google.")
            self.autorizacao, self.token = base + "/o/oauth2/v2/auth", base + "/token"
            self.upload, self.api = base + "/upload/youtube/v3", base + "/youtube/v3"
        else:
            self.autorizacao, self.token, self.upload, self.api = URL_AUTORIZACAO, URL_TOKEN, URL_UPLOAD, URL_API

    def sessao_confiavel(self, url: str) -> bool:
        """O endereço de sessão recebe o token e o arquivo: só serve HTTPS em *.googleapis.com
        (nos testes, a mesma origem de loopback)."""
        a = urllib.parse.urlsplit(url)
        if self.teste:
            b = urllib.parse.urlsplit(self.upload)
            return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port)
        host = (a.hostname or "").lower()
        return a.scheme == "https" and (host == "googleapis.com" or host.endswith(".googleapis.com"))


# ─────────────────────────────────────────────────────────────────── HTTP ──
class _SemRedirecionar(urllib.request.HTTPRedirectHandler):
    """Nunca segue redirecionamento: 308 é resposta do protocolo retomável, e um Authorization
    não pode ser reenviado para outro endereço."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _abridor(teste: bool):
    manip = [_SemRedirecionar()]
    if teste:
        manip.append(urllib.request.ProxyHandler({}))   # loopback nunca passa por proxy
    return urllib.request.build_opener(*manip)


def requisitar(metodo: str, url: str, cabecalhos: dict | None = None, corpo: bytes | None = None, espera: float = 120.0,
               teste: bool = False) -> tuple[int, dict, bytes]:
    """Uma requisição. Devolve (status, cabeçalhos em minúsculas, corpo). Levanta ErroRede em falha de transporte."""
    req = urllib.request.Request(url, data=corpo, method=metodo)
    for k, v in (cabecalhos or {}).items():
        req.add_header(k, v)
    if corpo is None and metodo in ("PUT", "POST"):
        req.add_header("Content-Length", "0")
    try:
        with _abridor(teste).open(req, timeout=espera) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        try:
            dados = e.read()
        except Exception:
            dados = b""
        return e.code, {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}, dados
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
        motivo = getattr(e, "reason", e)
        raise ErroRede(f"falha de rede em {metodo} {_sem_segredo(url)}: {motivo}",
                       "Confira a conexão e rode o mesmo comando de novo: o envio continua de onde parou.")
    except Exception as e:   # http.client.RemoteDisconnected, IncompleteRead…
        if e.__class__.__module__.startswith("http."):
            raise ErroRede(f"a conexão caiu em {metodo} {_sem_segredo(url)}: {e.__class__.__name__}",
                           "Rode o mesmo comando de novo: o envio continua de onde parou.")
        raise


def _sem_segredo(url: str) -> str:
    """URL sem a query (o upload_id da sessão dá acesso ao envio: nunca vai para a tela)."""
    u = urllib.parse.urlsplit(url)
    return f"{u.scheme}://{u.netloc}{u.path}" + ("?…" if u.query else "")


_DICAS_API = {
    "quotaExceeded": "A cota diária do projeto no Google Cloud acabou; ela zera à meia-noite do horário do Pacífico. Rode de novo amanhã (o envio é retomado).",
    "uploadLimitExceeded": "O canal atingiu o limite de envios do YouTube (ele é diário). Tente de novo mais tarde.",
    "forbidden": "A conta autorizada não pode fazer isso neste canal (thumbnail personalizada exige conta verificada; legenda exige o escopo de legendas).",
    "insufficientPermissions": "O token não tem o escopo necessário: rode `enviar_youtube.py autorizar --legendas --confirmar`.",
    "invalidTitle": "Título vazio ou inválido: rode `pacote.py validar`.",
    "invalidDescription": "Descrição inválida (acima do limite em bytes ou com < >): rode `pacote.py validar`.",
    "invalidTags": "Tags inválidas: rode `pacote.py validar`.",
    "invalidPublishAt": "Data de agendamento inválida: precisa ser futura e o vídeo precisa estar privado.",
    "invalidCategoryId": "categoria_id inexistente para a região do canal: remova o campo do meta.json ou consulte videoCategories.list.",
    "defaultLanguageNotSet": "A API pediu o idioma padrão: confira o campo `idioma` do meta.json.",
    "youtubeSignupRequired": "A conta Google autorizada não tem canal no YouTube: crie o canal ou autorize a conta certa.",
    "authError": "Token recusado: rode `enviar_youtube.py autorizar --confirmar` de novo.",
    "captionExists": "Já existe legenda com esse idioma e nome no vídeo: apague no Studio ou mude `legenda_nome` no meta.json.",
    "invalidImage": "O YouTube recusou a imagem: gere a thumbnail de novo em JPG ou PNG 16:9.",
    "videoNotFound": "O vídeo ainda não está disponível para receber thumbnail/legenda: espere um minuto e rode de novo.",
}


def erro_da_api(status: int, corpo: bytes) -> ErroAPI:
    motivo, mensagem = "erro", ""
    try:
        doc = json.loads(corpo.decode("utf-8", "replace") or "{}")
        err = doc.get("error")
        if isinstance(err, dict):
            mensagem = str(err.get("message") or "")
            itens = err.get("errors") or []
            if itens and isinstance(itens[0], dict):
                motivo = str(itens[0].get("reason") or motivo)
        elif isinstance(err, str):                      # formato do endpoint de token
            motivo, mensagem = err, str(doc.get("error_description") or "")
    except ValueError:
        mensagem = corpo[:200].decode("utf-8", "replace")
    if status == 401 and motivo == "erro":
        motivo = "authError"
    return ErroAPI(status, motivo, mensagem[:300] or "sem detalhe", _DICAS_API.get(motivo))


# ───────────────────────────────────────────────────── credenciais e token ──
def pasta_ops() -> Path:
    v = os.environ.get("VIDEO_OPS_HOME")
    return Path(v).expanduser() if v else Path.home() / ".config" / "video-ops"


def caminho_cliente() -> Path:
    return pasta_ops() / "youtube_client_secret.json"


def caminho_token() -> Path:
    return pasta_ops() / "youtube_token.json"


def pasta_envios() -> Path:
    return pasta_ops() / "youtube_envios"


def gravar_privado(caminho: Path, obj) -> None:
    """Grava JSON com permissão 600 desde a criação (o arquivo nunca existe legível por outros)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(caminho.parent, 0o700)
    except OSError:
        pass
    tmp = caminho.with_name(caminho.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, caminho)


def permissao_frouxa(caminho: Path) -> bool:
    try:
        return bool(stat.S_IMODE(caminho.stat().st_mode) & 0o077)
    except OSError:
        return False


def ler_cliente() -> dict:
    arq = caminho_cliente()
    if not arq.is_file():
        raise Erro(f"Credenciais do cliente OAuth não encontradas em {arq}.",
                   "Quem cria é o usuário, no Google Cloud Console: projeto → ativar «YouTube Data API v3» → Credenciais → "
                   "ID do cliente OAuth do tipo «App para computador» → baixar o JSON e salvar nesse caminho (chmod 600). "
                   "Passo a passo em references/youtube-api.md §1. Nunca cole o conteúdo do arquivo na conversa.")
    doc = P.ler_json(arq)
    if isinstance(doc, dict) and "web" in doc and "installed" not in doc:
        raise Erro("O arquivo de credenciais é de um cliente do tipo «Aplicativo da Web».",
                   "Crie um ID do cliente OAuth do tipo «App para computador» (Desktop app): só ele aceita o redirecionamento para 127.0.0.1.")
    cli = doc.get("installed") if isinstance(doc, dict) else None
    if not isinstance(cli, dict) or not cli.get("client_id"):
        raise Erro(f"{arq} não tem o formato esperado ({{\"installed\": {{\"client_id\": …}}}}).",
                   "Baixe de novo o JSON do cliente OAuth «App para computador» no Google Cloud Console.")
    return {"client_id": str(cli["client_id"]), "client_secret": str(cli.get("client_secret") or "")}


def ler_token() -> dict | None:
    arq = caminho_token()
    if not arq.is_file():
        return None
    if permissao_frouxa(arq):
        os.chmod(arq, 0o600)
        P.diz(f"! {arq} estava legível por outros usuários; a permissão foi corrigida para 600.", erro=True)
    tok = P.ler_json(arq)
    return tok if isinstance(tok, dict) and (tok.get("refresh_token") or tok.get("access_token")) else None


def _pkce() -> tuple[str, str]:
    verificador = secrets.token_urlsafe(64)          # 86 caracteres de [A-Za-z0-9-_]: dentro de 43–128
    desafio = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verificador, desafio


_PAGINA = ("<!doctype html><html lang=\"pt-BR\"><meta charset=\"utf-8\"><title>video-publicacao</title>"
           "<body><h1>{titulo}</h1><p>{texto}</p></body></html>")


class _Retorno(http.server.BaseHTTPRequestHandler):
    """Recebe o redirecionamento do Google em http://127.0.0.1:<porta>/?code=…&state=…"""

    def do_GET(self):  # noqa: N802
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        srv = self.server
        if q.get("state", [""])[0] != srv.estado_esperado:
            self._pagina(400, "Pedido recusado", "Este endereço só atende ao retorno da autorização em andamento.")
            return
        if "error" in q:
            srv.resultado = {"erro": q["error"][0]}
            self._pagina(200, "Autorização negada", "Nada foi autorizado. Pode fechar esta aba e voltar ao terminal.")
        elif "code" in q:
            srv.resultado = {"codigo": q["code"][0]}
            self._pagina(200, "Autorização recebida", "Pode fechar esta aba e voltar ao terminal.")
        else:
            self._pagina(400, "Pedido incompleto", "Faltou o código de autorização.")

    def _pagina(self, status, titulo, texto):
        corpo = _PAGINA.format(titulo=titulo, texto=texto).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *a):   # nada de código de autorização no terminal
        pass


def _trocar_no_token(end: Enderecos, campos: dict) -> dict:
    corpo = urllib.parse.urlencode(campos).encode("ascii")
    status, _cab, dados = requisitar("POST", end.token, {"Content-Type": "application/x-www-form-urlencoded"}, corpo, espera=60, teste=end.teste)
    if status != 200:
        err = erro_da_api(status, dados)
        if err.motivo == "invalid_grant":
            raise Erro("O Google recusou a credencial (invalid_grant): o acesso foi revogado ou expirou.",
                       "Rode `enviar_youtube.py autorizar --confirmar` de novo. Em app com tela de consentimento em modo «Testing», "
                       "o acesso expira em 7 dias (references/youtube-api.md §1).")
        raise err
    try:
        return json.loads(dados.decode("utf-8"))
    except ValueError:
        raise Erro("O endpoint de token respondeu algo que não é JSON.", "Tente de novo; se persistir, confira proxy/antivírus interceptando HTTPS.")


def _guardar_token(resposta: dict, anterior: dict | None = None, canal: dict | None = None) -> dict:
    agora = int(time.time())
    tok = dict(anterior or {})
    tok.update({"access_token": resposta["access_token"], "token_type": resposta.get("token_type", "Bearer"),
                "expira_em": agora + int(resposta.get("expires_in", 3600)), "renovado_em": P.agora_iso()})
    if resposta.get("refresh_token"):
        tok["refresh_token"] = resposta["refresh_token"]
        tok["obtido_em"] = P.agora_iso()
    if resposta.get("scope"):
        tok["escopos"] = sorted(str(resposta["scope"]).split())
    if resposta.get("refresh_token_expires_in"):
        tok["refresh_expira_em"] = agora + int(resposta["refresh_token_expires_in"])
    if canal is not None:
        tok["canal"] = canal
    gravar_privado(caminho_token(), tok)
    return tok


def autorizar(end: Enderecos, escopos: list[str], abrir=None, porta: int = 0, espera: float = 300.0) -> dict:
    """Fluxo OAuth 2.0 de aplicativo instalado: redirecionamento para 127.0.0.1 + PKCE (S256).
    Quem faz login e consente é o usuário, no navegador dele; este processo só recebe o código."""
    cliente = ler_cliente()
    verificador, desafio = _pkce()
    estado = secrets.token_urlsafe(24)
    try:
        servidor = http.server.HTTPServer(("127.0.0.1", porta), _Retorno)
    except OSError as e:
        raise Erro(f"Não consegui abrir a porta local {porta} para receber a autorização: {e}", "Use outra porta com --porta ou deixe 0 (automática).")
    servidor.estado_esperado, servidor.resultado = estado, None
    servidor.timeout = 1.0
    redirecionar = f"http://127.0.0.1:{servidor.server_address[1]}"
    url = end.autorizacao + "?" + urllib.parse.urlencode({
        "client_id": cliente["client_id"], "redirect_uri": redirecionar, "response_type": "code", "scope": " ".join(escopos),
        "code_challenge": desafio, "code_challenge_method": "S256", "state": estado})
    try:
        P.diz("Abra este endereço no SEU navegador, entre com a conta do canal e autorize (o endereço não contém segredo):")
        P.diz("  " + url)
        if abrir is not None:
            try:
                abrir(url)
            except Exception:
                pass
        P.diz(f"Aguardando a autorização em {redirecionar} (até {int(espera)} s)…")
        limite = time.monotonic() + espera
        while servidor.resultado is None and time.monotonic() < limite:
            servidor.handle_request()
    finally:
        servidor.server_close()
    res = servidor.resultado
    if res is None:
        raise Erro(f"Ninguém concluiu a autorização em {int(espera)} s.", "Rode de novo e conclua o login no navegador; nada foi gravado.")
    if "erro" in res:
        raise Erro(f"A autorização foi negada no navegador ({res['erro']}).", "Sem consentimento do usuário não há envio. Nada foi gravado.")
    campos = {"client_id": cliente["client_id"], "code": res["codigo"], "code_verifier": verificador,
              "grant_type": "authorization_code", "redirect_uri": redirecionar}
    if cliente["client_secret"]:
        campos["client_secret"] = cliente["client_secret"]
    resposta = _trocar_no_token(end, campos)
    if not resposta.get("access_token"):
        raise Erro("O Google não devolveu access_token.", "Tente autorizar de novo.")
    tok = _guardar_token(resposta, anterior=None)
    if not resposta.get("scope"):
        tok["escopos"] = sorted(escopos)
    if not resposta.get("refresh_token"):
        P.diz("! o Google não devolveu refresh token: este acesso vale cerca de 1 hora e depois será preciso autorizar de novo.", erro=True)
    canal = None
    try:
        canal = consultar_canal(end, tok["access_token"])
    except Erro as e:
        P.diz(f"! não consegui ler o nome do canal ({e.mensagem}); o token foi gravado mesmo assim.", erro=True)
    tok["canal"] = canal
    gravar_privado(caminho_token(), tok)
    return tok


def consultar_canal(end: Enderecos, access_token: str) -> dict | None:
    status, _cab, dados = requisitar("GET", end.api + "/channels?part=snippet&mine=true", {"Authorization": f"Bearer {access_token}"}, espera=60, teste=end.teste)
    if status != 200:
        raise erro_da_api(status, dados)
    itens = json.loads(dados.decode("utf-8")).get("items") or []
    if not itens:
        return None
    return {"id": itens[0].get("id"), "titulo": (itens[0].get("snippet") or {}).get("title")}


def token_de_acesso(end: Enderecos, forcar: bool = False) -> str:
    """Access token válido; renova com o refresh token quando faltar menos de 60 s (ou quando `forcar`)."""
    tok = ler_token()
    if tok is None:
        raise Erro("Nenhuma conta do YouTube autorizada nesta máquina.", "Rode `enviar_youtube.py autorizar --confirmar` (o usuário faz o login no navegador dele).")
    if not forcar and tok.get("access_token") and int(tok.get("expira_em", 0)) - 60 > time.time():
        return tok["access_token"]
    if not tok.get("refresh_token"):
        raise Erro("O acesso expirou e não há refresh token guardado.", "Rode `enviar_youtube.py autorizar --confirmar` de novo.")
    cliente = ler_cliente()
    campos = {"client_id": cliente["client_id"], "grant_type": "refresh_token", "refresh_token": tok["refresh_token"]}
    if cliente["client_secret"]:
        campos["client_secret"] = cliente["client_secret"]
    resposta = _trocar_no_token(end, campos)
    return _guardar_token(resposta, anterior=tok)["access_token"]


# ───────────────────────────────────────────────────────── envio retomável ──
_dormir = time.sleep      # ponto único de espera (a suíte troca por uma função que não espera)


class Envio:
    """Protocolo retomável da API (guia oficial «Resumable Uploads»): sessão → pedaços → 308/201."""

    def __init__(self, end: Enderecos, tentativas: int = 6, espera: float = 120.0, progresso=None):
        self.end, self.tentativas, self.espera = end, tentativas, espera
        self.dormir = lambda seg: _dormir(seg)
        self.progresso = progresso or (lambda enviados, total: None)

    def _auth(self, forcar: bool = False) -> dict:
        return {"Authorization": f"Bearer {token_de_acesso(self.end, forcar)}"}

    def _pedir(self, metodo, url, cabecalhos, corpo=None):
        """Uma requisição autenticada; em 401 renova o token uma vez e repete."""
        status, cab, dados = requisitar(metodo, url, {**cabecalhos, **self._auth()}, corpo, self.espera, self.end.teste)
        if status == 401:
            status, cab, dados = requisitar(metodo, url, {**cabecalhos, **self._auth(forcar=True)}, corpo, self.espera, self.end.teste)
        return status, cab, dados

    def iniciar(self, recurso: dict, tamanho: int, tipo: str, notificar: bool = True) -> str:
        consulta = {"uploadType": "resumable", "part": ",".join(sorted(recurso))}
        if not notificar:
            consulta["notifySubscribers"] = "false"
        corpo = json.dumps(recurso, ensure_ascii=False).encode("utf-8")
        status, cab, dados = self._pedir("POST", self.end.upload + "/videos?" + urllib.parse.urlencode(consulta), {
            "Content-Type": "application/json; charset=UTF-8", "Content-Length": str(len(corpo)),
            "X-Upload-Content-Length": str(tamanho), "X-Upload-Content-Type": tipo}, corpo)
        if status != 200:
            raise erro_da_api(status, dados)
        uri = cab.get("location")
        if not uri:
            raise Erro("A API aceitou o início do envio mas não devolveu o endereço da sessão (cabeçalho Location).", "Tente de novo.")
        if not self.end.sessao_confiavel(uri):
            raise Erro("A API devolveu um endereço de sessão fora de googleapis.com; o envio foi abortado por segurança.",
                       "Não reenvie. Confira se há proxy interceptando o tráfego.")
        return uri

    def consultar(self, uri: str, total: int):
        """→ ('incompleto', próximo_byte) | ('completo', recurso) ; levanta SessaoExpirada em 404."""
        status, cab, dados = self._pedir("PUT", uri, {"Content-Length": "0", "Content-Range": f"bytes */{total}"})
        return self._interpretar(status, cab, dados, total)

    def _interpretar(self, status, cab, dados, total):
        if status == 308:
            faixa = cab.get("range")
            if not faixa:
                return "incompleto", 0
            try:
                return "incompleto", int(faixa.split("-")[-1]) + 1
            except ValueError:
                raise Erro(f"Cabeçalho Range inesperado na resposta 308: «{faixa}».", "Rode de novo; se repetir, comece um envio novo com --reenviar.")
        if status in (200, 201):
            try:
                return "completo", json.loads(dados.decode("utf-8") or "{}")
            except ValueError:
                return "completo", {}
        if status in (404, 410):
            raise SessaoExpirada("A sessão de envio expirou no servidor.")
        if status in CODIGOS_REPETIVEIS:
            raise ErroRede(f"o servidor respondeu {status} (indisponível)", "Rode o mesmo comando de novo: o envio continua de onde parou.")
        raise erro_da_api(status, dados)

    def enviar(self, uri: str, arquivo: Path, total: int, tipo: str, inicio: int, pedaco: int) -> dict:
        """Envia do byte `inicio` até o fim. Queda ou 5xx: espera (recuo exponencial), pergunta ao servidor
        quanto chegou e continua dali. Devolve o recurso `video` criado."""
        pos, falhas, parados = inicio, 0, 0
        self.progresso(pos, total)
        with open(arquivo, "rb") as f:
            while True:
                f.seek(pos)
                bloco = f.read(pedaco)
                fim = pos + len(bloco) - 1
                try:
                    status, cab, dados = self._pedir("PUT", uri, {
                        "Content-Length": str(len(bloco)), "Content-Type": tipo, "Content-Range": f"bytes {pos}-{fim}/{total}"}, bloco)
                    estado, valor = self._interpretar(status, cab, dados, total)
                except ErroRede as e:
                    falhas += 1
                    if falhas > self.tentativas:
                        raise ErroRede(f"envio interrompido depois de {falhas} falha(s) seguidas: {e.mensagem}",
                                       "Rode o mesmo comando de novo (com o mesmo código de confirmação): ele retoma de onde parou.")
                    self.dormir(min(64.0, 2.0 ** (falhas - 1)) + random.random())
                    while True:                                  # pergunta ao servidor até onde chegou
                        try:
                            estado, valor = self.consultar(uri, total)
                            break
                        except ErroRede as e2:
                            falhas += 1
                            if falhas > self.tentativas:
                                raise ErroRede(f"envio interrompido depois de {falhas} falha(s) seguidas: {e2.mensagem}",
                                               "Rode o mesmo comando de novo: ele retoma de onde parou.")
                            self.dormir(min(64.0, 2.0 ** (falhas - 1)) + random.random())
                else:
                    falhas = 0
                if estado == "completo":
                    self.progresso(total, total)
                    return valor
                if valor < pos:
                    raise Erro(f"O servidor disse ter {valor} bytes, menos do que já havia confirmado ({pos}).", "Comece um envio novo com --reenviar.")
                parados = parados + 1 if valor == pos else 0
                if parados >= 5:                                 # 308 atrás de 308 sem aceitar um byte: não insistir para sempre
                    raise ErroRede(f"o servidor respondeu 5 vezes sem aceitar nenhum byte novo (parado em {P.fmt_bytes(pos)})",
                                   "Espere alguns minutos e rode o mesmo comando de novo: o envio continua de onde parou.")
                pos = valor
                self.progresso(pos, total)
                if pos >= total:                                 # tudo chegou, falta só a resposta final
                    estado, valor = self.consultar(uri, total)
                    if estado == "completo":
                        self.progresso(total, total)
                        return valor
                    raise Erro("O servidor recebeu todos os bytes mas não concluiu o envio.", "Rode de novo; se repetir, use --reenviar.")

    def thumbnail(self, video_id: str, arquivo: Path) -> dict:
        tipo = TIPOS_IMAGEM.get(arquivo.suffix.lower(), "application/octet-stream")
        dados_img = arquivo.read_bytes()
        url = self.end.upload + "/thumbnails/set?" + urllib.parse.urlencode({"videoId": video_id, "uploadType": "media"})
        status, _cab, dados = self._pedir("POST", url, {"Content-Type": tipo, "Content-Length": str(len(dados_img))}, dados_img)
        if status != 200:
            raise erro_da_api(status, dados)
        return json.loads(dados.decode("utf-8") or "{}")

    def legenda(self, video_id: str, arquivo: Path, idioma: str, nome: str = "", rascunho: bool = False) -> dict:
        meta = json.dumps({"snippet": {"videoId": video_id, "language": idioma, "name": nome, "isDraft": bool(rascunho)}}, ensure_ascii=False).encode("utf-8")
        limite = "vp_" + secrets.token_hex(12)
        corpo = (f"--{limite}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("ascii") + meta
                 + f"\r\n--{limite}\r\nContent-Type: application/octet-stream\r\n\r\n".encode("ascii") + arquivo.read_bytes()
                 + f"\r\n--{limite}--\r\n".encode("ascii"))
        url = self.end.upload + "/captions?" + urllib.parse.urlencode({"uploadType": "multipart", "part": "snippet"})
        status, _cab, dados = self._pedir("POST", url, {"Content-Type": f"multipart/related; boundary={limite}", "Content-Length": str(len(corpo))}, corpo)
        if status != 200:
            raise erro_da_api(status, dados)
        return json.loads(dados.decode("utf-8") or "{}")


# ─────────────────────────────────────────────────────────────────── plano ──
def historico() -> list[dict]:
    arq = pasta_envios() / "historico.json"
    if not arq.is_file():
        return []
    try:
        h = P.ler_json(arq)
        return h if isinstance(h, list) else []
    except Erro:
        return []


def envio_anterior(pac: P.Pacote) -> dict | None:
    """Registro do envio já feito deste pacote (publicacao/…/envio.json), se houver."""
    arq = pac.pasta / "envio.json"
    if not arq.is_file():
        return None
    try:
        doc = P.ler_json(arq)
    except Erro:
        doc = None
    return doc if isinstance(doc, dict) else {}


def montar_plano(pac: P.Pacote, validacao: dict | None, estado_val: str, usar_privacidade: bool = False, sem_thumbnail: bool = False,
                 sem_legenda: bool = False, viva: dict | None = None, reenviar: bool = False) -> dict:
    """Tudo o que seria enviado — sem tocar a rede. É o que o usuário aprova; o código de confirmação sai daqui.
    `validacao` = a gravada por `pacote.py validar`; `viva` = a conferência refeita agora (P.situacao_do_pacote)."""
    meta = pac.meta
    if pac.plataforma not in ("youtube", "shorts"):
        raise ErroUso(f"O pacote «{pac.id}» é de {P.NOME_PLATAFORMA[pac.plataforma]}; este script só envia para o YouTube (youtube e shorts).",
                      "Para Reels e TikTok: `pacote.py checklist` + references/envio.md.")
    video = pac.arquivo("arquivo_video")
    tok = ler_token()
    canal = (tok or {}).get("canal")
    escopos = (tok or {}).get("escopos") or []
    avisos, recusas = [], []

    primeiro_envio = not historico()
    privacidade = meta.get("privacidade") if usar_privacidade else "private"
    agendar = meta.get("agendar_para")
    if meta.get("privacidade") != "private" and not usar_privacidade:
        avisos.append(f"o pacote pede «{meta.get('privacidade')}», mas o envio vai como private (padrão da casa). Depois de conferir no Studio, "
                      "publique por lá — ou repita com --usar-privacidade-do-pacote.")
    if primeiro_envio and (privacidade != "private" or agendar):
        avisos.append("PRIMEIRO ENVIO REAL por esta máquina: vai privado e SEM agendamento, para ser conferido no Studio"
                      + (f" (o agendamento de {agendar} fica para ser feito no Studio)" if agendar else "") + ".")
        privacidade, agendar = "private", None
    publicar_em = None
    if agendar:
        try:
            quando = datetime.fromisoformat(str(agendar))
            if quando.tzinfo is None:
                raise ValueError
            publicar_em = quando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if privacidade != "private":
                recusas.append("agendamento só vale com privacidade private")
        except ValueError:
            recusas.append(f"agendar_para inválido: {agendar}")

    snippet = {"title": str(meta.get("titulo") or ""), "description": str(meta.get("descricao") or ""), "defaultLanguage": str(meta.get("idioma") or "pt-BR")}
    if meta.get("tags"):
        snippet["tags"] = [str(t) for t in meta["tags"]]
    if meta.get("categoria_id"):
        snippet["categoryId"] = str(meta["categoria_id"])
    status = {"privacyStatus": privacidade}
    if publicar_em:
        status["publishAt"] = publicar_em
    if isinstance(meta.get("feito_para_criancas"), bool):
        status["selfDeclaredMadeForKids"] = meta["feito_para_criancas"]
    if isinstance(meta.get("conteudo_sintetico"), bool):
        status["containsSyntheticMedia"] = meta["conteudo_sintetico"]
    recurso = {"snippet": snippet, "status": status}

    thumb = None if sem_thumbnail else pac.arquivo("thumbnail")
    srt = None if sem_legenda else pac.arquivo("legenda_srt")
    if thumb and pac.plataforma == "shorts":
        avisos.append("capa de Short não é enviada pela API neste script (a ajuda do YouTube só garante o envio pelo Studio no computador): suba à mão.")
        thumb = None
    if srt and tok and ESCOPO_LEGENDAS not in escopos:
        avisos.append("a legenda NÃO será enviada: o token não tem o escopo de legendas. Rode `enviar_youtube.py autorizar --legendas --confirmar` ou suba o .srt no Studio.")
        srt = None

    if estado_val == "vencida":
        recusas.append(f"a validação de {(validacao or {}).get('validado_em')} venceu — a conferência de agora reprova: "
                       + "; ".join(P.erros_de(viva)) + f". Resolva e rode `pacote.py validar {pac.id}`")
    elif estado_val not in P.ESTADOS_OK:
        recusas.append(f"pacote {P.ROTULO_ESTADO.get(estado_val, estado_val)}: rode `pacote.py validar {pac.id}` e resolva os erros")
    if not video or not video.is_file():
        recusas.append("arquivo de vídeo ausente")
    if tok is None:
        recusas.append("nenhuma conta autorizada: rode `enviar_youtube.py autorizar --confirmar`")
    elif not any(e in escopos for e in (ESCOPO_ENVIO, ESCOPO_LEGENDAS, "https://www.googleapis.com/auth/youtube")):
        recusas.append("o token não tem escopo de envio: rode `enviar_youtube.py autorizar --confirmar`")
    anterior = envio_anterior(pac)
    n_anterior = 0 if anterior is None else (anterior.get("numero_do_envio") if isinstance(anterior.get("numero_do_envio"), int) else 1)
    marca_anterior = None if anterior is None else f"{n_anterior}:{anterior.get('video_id') or anterior.get('url') or anterior.get('enviado_em') or 'registrado'}"
    if anterior is not None and not reenviar:
        recusas.append("este pacote já foi enviado (publicacao/…/envio.json existe); para enviar outra vez use --reenviar")
    elif anterior is not None:
        avisos.append(f"REENVIO: este pacote já foi enviado {n_anterior} vez(es) (a última: {anterior.get('url') or anterior.get('video_id')}, em {anterior.get('enviado_em')}). "
                      "Confirmar este plano cria OUTRO vídeo no canal; o anterior continua lá.")

    tamanho = video.stat().st_size if video and video.is_file() else 0
    base = {"pacote": pac.id, "projeto": str(pac.raiz), "recurso": recurso, "notificar": bool(meta.get("notificar_inscritos", True)),
            "video": {"arquivo": meta.get("arquivo_video"), "bytes": tamanho, "mtime_ns": video.stat().st_mtime_ns if tamanho else None},
            "thumbnail": {"arquivo": pac.rel(thumb), "sha256": P.sha256_arquivo(thumb)} if thumb and thumb.is_file() else None,
            "legenda": {"arquivo": pac.rel(srt), "sha256": P.sha256_arquivo(srt), "idioma": meta.get("idioma"), "nome": str(meta.get("legenda_nome") or "")}
            if srt and srt.is_file() else None,
            "canal": canal,
            # Um código vale para UM envio: o envio anterior do pacote e a opção --reenviar fazem parte do plano. Depois de
            # um envio concluído o código muda sozinho; durante uma retomada (envio.json ainda não mudou) ele se mantém.
            "envio_anterior": marca_anterior, "reenviar": bool(reenviar)}
    def _sha(obj) -> str:
        return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    # código = o plano inteiro (é o que o usuário aprova); chave = só o que define o VÍDEO, para que tirar a
    # thumbnail ou a legenda de um envio já feito não crie um segundo vídeo no canal.
    digest = _sha(base)
    chave = _sha({k: base[k] for k in ("pacote", "projeto", "recurso", "notificar", "video", "canal", "envio_anterior")})
    return {**base, "codigo": digest[:8], "chave": chave[:24], "avisos": avisos, "recusas": recusas, "primeiro_envio": primeiro_envio,
            "codigo_ja_usado": (anterior or {}).get("codigo_confirmado"), "numero_do_envio": n_anterior + 1,
            "validacao": validacao, "conferencia": viva, "estado_validacao": estado_val, "tipo_video": TIPOS_VIDEO.get(Path(str(meta.get("arquivo_video") or "")).suffix.lower(), "application/octet-stream"),
            "agendar_original": meta.get("agendar_para"), "privacidade_do_pacote": meta.get("privacidade")}


def imprimir_plano(plano: dict, pac: P.Pacote, pedaco: int) -> None:
    r, d = plano["recurso"], P.diz
    medidas = ((plano.get("conferencia") or plano.get("validacao") or {}).get("medidas") or {}).get("video") or {}
    d("═" * 72)
    d(f"PLANO DE ENVIO — YouTube · pacote «{pac.id}»  (SIMULAÇÃO: nada foi enviado, a rede não foi tocada)")
    d("═" * 72)
    canal = plano.get("canal")
    d("Conta:        " + (f"{canal.get('titulo')} (canal {canal.get('id')})" if canal else "NENHUMA CONTA AUTORIZADA ou canal não identificado"))
    d(f"Arquivo:      {plano['video']['arquivo']}  ({P.fmt_bytes(plano['video']['bytes'])}"
      + (f", {medidas.get('largura')}×{medidas.get('altura')}, {P.fmt_dur(medidas.get('duracao'))}" if medidas else "") + ")")
    d(f"Título:       {r['snippet']['title']}")
    d(f"Privacidade:  {r['status']['privacyStatus']}" + (f"   (o pacote pede {plano['privacidade_do_pacote']})" if plano["privacidade_do_pacote"] != r["status"]["privacyStatus"] else ""))
    if r["status"].get("publishAt"):
        d(f"Agendamento:  {plano['agendar_original']}  → publishAt {r['status']['publishAt']} (UTC)")
    else:
        d("Agendamento:  nenhum" + (f"   (o pacote pede {plano['agendar_original']}; não será aplicado neste envio)" if plano["agendar_original"] else ""))
    d(f"Idioma:       {r['snippet']['defaultLanguage']}   Tags: {', '.join(r['snippet'].get('tags', [])) or '—'}   Categoria: {r['snippet'].get('categoryId', 'padrão do YouTube')}")
    simnao = lambda v: {True: "sim", False: "não"}.get(v, "não declarado")   # noqa: E731
    d(f"Feito para crianças: {simnao(r['status'].get('selfDeclaredMadeForKids'))}   Conteúdo sintético (IA realista): "
      f"{simnao(r['status'].get('containsSyntheticMedia'))}   Notificar inscritos: {'sim' if plano['notificar'] else 'não'}")
    d(f"Thumbnail:    {plano['thumbnail']['arquivo'] if plano['thumbnail'] else '— (não será enviada)'}")
    d(f"Legenda:      {plano['legenda']['arquivo'] + ' (' + str(plano['legenda']['idioma']) + ')' if plano['legenda'] else '— (não será enviada)'}")
    d("Descrição:")
    for linha in (r["snippet"]["description"] or "(vazia)").split("\n"):
        d("  │ " + linha)
    estado = plano["estado_validacao"]
    d("Validação:    " + P.ROTULO_ESTADO.get(estado, estado)
      + (f"   (validado em {(plano.get('validacao') or {}).get('validado_em')}; conferido de novo agora)" if estado in P.ESTADOS_OK else ""))
    if estado == "ok_com_excecao":
        for linha in P.linhas_de_excecao(plano.get("validacao")):
            d(f"  ! EXCEÇÃO: {linha}")
    for item in (plano.get("conferencia") or {}).get("itens", []) if estado in P.ESTADOS_OK else []:
        if item["severidade"] == "aviso" and item["id"] != "qa.dispensado":
            d(f"  ! aviso da conferência: {item['mensagem']}")
    n_ped = -(-plano["video"]["bytes"] // pedaco) if plano["video"]["bytes"] else 0
    d("Requisições que seriam feitas:")
    d(f"  1. POST {URL_UPLOAD}/videos?uploadType=resumable&part=snippet,status   (cota: {COTAS['videos_insert']})")
    d(f"  2. PUT  <sessão>  × {n_ped} pedaço(s) de até {P.fmt_bytes(pedaco)}")
    n = 3
    if plano["thumbnail"]:
        d(f"  {n}. POST {URL_UPLOAD}/thumbnails/set?videoId=…&uploadType=media   (cota: {COTAS['thumbnails_set']})")
        n += 1
    if plano["legenda"]:
        d(f"  {n}. POST {URL_UPLOAD}/captions?uploadType=multipart&part=snippet   (cota: {COTAS['captions_insert']})")
    d(f"  (cotas conferidas na documentação em {COTAS['verificado_em']}; elas mudam — references/youtube-api.md §6)")
    for a in plano["avisos"]:
        d(f"! {a}")
    d("! Se o projeto de API do usuário não foi auditado pelo Google, o vídeo fica travado em privado até a auditoria (regra de videos.insert).")
    d("! Este script não foi testado contra a API real: o primeiro envio real deve ser privado e conferido no Studio.")
    if plano["recusas"]:
        d("─" * 72)
        d("NÃO PODE SER ENVIADO AINDA:")
        for x in plano["recusas"]:
            d(f"  ✗ {x}")
    else:
        d("─" * 72)
        d("Mostre este plano ao usuário (título, descrição, privacidade, agendamento, arquivo e conta) e espere um «sim» explícito.")
        d(f"Só então: enviar_youtube.py enviar {pac.id}" + (" --reenviar" if plano["reenviar"] else "") + f" --confirmar {plano['codigo']}")
        d("O código vale só para este plano e para UM envio: qualquer mudança de texto, arquivo, conta ou privacidade — ou o próprio envio "
          "concluído — gera outro código.")


# ───────────────────────────────────────────────────────────────── comandos ──
def _estado_do_envio(chave: str) -> Path:
    return pasta_envios() / f"{chave}.json"


def _progresso(enviados: int, total: int) -> None:
    pct = 100 * enviados / total if total else 100
    print(f"  enviado {P.fmt_bytes(enviados)} de {P.fmt_bytes(total)} ({pct:.0f} %)", file=sys.stderr)


def cmd_enviar(args) -> int:
    raiz, d = P.abrir_projeto(args.projeto)
    pac = P.resolver_seletor(raiz, args.pacote)
    if args.simular and args.confirmar is not None:
        raise ErroUso("--simular e --confirmar não andam juntos.")
    if args.pedaco_mb <= 0:
        raise ErroUso("--pedaco-mb precisa ser positivo.")
    pedaco = max(MULTIPLO_PEDACO, int(args.pedaco_mb * (1 << 20)) // MULTIPLO_PEDACO * MULTIPLO_PEDACO)
    # A validação gravada não basta: a conferência inteira é refeita agora, na simulação E no envio (um ffprobe).
    val = P.validacao_gravada(raiz, pac.id)
    estado_val, viva = P.situacao_do_pacote(pac, val, P.Limites(), P.Insumos(raiz), d)
    plano = montar_plano(pac, val, estado_val, args.usar_privacidade_do_pacote, args.sem_thumbnail, args.sem_legenda, viva=viva, reenviar=args.reenviar)

    if args.confirmar is None:
        if args.json:
            print(json.dumps({k: v for k, v in plano.items() if k not in ("validacao", "conferencia", "codigo_ja_usado")}, ensure_ascii=False, indent=2))
        else:
            imprimir_plano(plano, pac, pedaco)
        return P.SAIDA_OK if not plano["recusas"] else P.SAIDA_ERRO

    # ── envio de verdade
    if not args.confirmar:
        raise ErroUso("--confirmar precisa do código do plano.",
                      f"Rode `enviar_youtube.py enviar {pac.id}` (simulação), mostre o plano ao usuário, espere o «sim» e use o código impresso.")
    if plano["recusas"]:
        raise Erro("Envio recusado: " + "; ".join(plano["recusas"]) + ".", "Resolva e simule de novo.")
    dado = args.confirmar.strip().lower()
    if plano["codigo_ja_usado"] and dado == str(plano["codigo_ja_usado"]).lower() and dado != plano["codigo"]:
        raise Erro(f"O código «{args.confirmar}» já foi usado no envio anterior deste pacote: a aprovação de um envio não vale para o seguinte.",
                   f"Rode `enviar_youtube.py enviar {pac.id} --reenviar` (simulação), mostre o plano ao usuário — ele cria OUTRO vídeo no canal — "
                   "e use o código novo só depois do «sim» dele.")
    if dado != plano["codigo"]:
        raise Erro(f"O código «{args.confirmar}» não corresponde ao plano atual: algo mudou desde a simulação (texto, arquivo, conta, privacidade "
                   "ou as opções do comando), ou o código é de outro envio.",
                   f"Rode `enviar_youtube.py enviar {pac.id}` de novo, mostre o plano atualizado ao usuário e peça nova confirmação. Aprovação de um envio não vale para outro.")
    end = Enderecos()
    envio = Envio(end, tentativas=args.tentativas, progresso=_progresso)
    video = pac.arquivo("arquivo_video")
    total = plano["video"]["bytes"]
    arq_estado = _estado_do_envio(plano["chave"])
    est = P.ler_json_opcional(arq_estado) or {}
    if args.reenviar and est.get("video_id"):
        est = {}
    est.setdefault("pacote", pac.id)
    est.setdefault("projeto", str(raiz))
    est.setdefault("etapas", {})

    P.diz(f"Enviando «{plano['recurso']['snippet']['title']}» ({P.fmt_bytes(total)}) para o canal "
          f"{(plano['canal'] or {}).get('titulo') or '(não identificado)'} como {plano['recurso']['status']['privacyStatus']}…")
    recurso_video = None
    if not est.get("video_id"):
        inicio, uri = 0, est.get("sessao_uri")
        if uri and not end.sessao_confiavel(str(uri)):      # o arquivo de estado é só um arquivo: o token não vai para qualquer endereço
            P.diz("! o endereço de sessão guardado não é da API de envio do YouTube e foi descartado; começando um envio novo.", erro=True)
            uri = None
            est.pop("sessao_uri", None)
            gravar_privado(arq_estado, est)
        if uri:
            try:
                situacao, valor = envio.consultar(uri, total)
                if situacao == "completo":
                    recurso_video = valor
                else:
                    inicio = valor
                    P.diz(f"Retomando o envio interrompido a partir de {P.fmt_bytes(inicio)}.")
            except SessaoExpirada:
                P.diz("! a sessão anterior expirou no servidor; começando um envio novo.", erro=True)
                uri = None
        if recurso_video is None:
            if not uri:
                uri = envio.iniciar(plano["recurso"], total, plano["tipo_video"], plano["notificar"])
                est.update({"sessao_uri": uri, "criada_em": P.agora_iso(), "total": total})
                gravar_privado(arq_estado, est)
                inicio = 0
            try:
                recurso_video = envio.enviar(uri, video, total, plano["tipo_video"], inicio, pedaco)
            except SessaoExpirada:
                est.pop("sessao_uri", None)
                gravar_privado(arq_estado, est)
                raise Erro("A sessão de envio expirou no meio do caminho.", "Rode o mesmo comando de novo: ele abre uma sessão nova.")
        vid = (recurso_video or {}).get("id")
        if not vid:
            raise Erro("O envio terminou mas a API não devolveu o id do vídeo.", "Confira no YouTube Studio se o vídeo chegou antes de tentar de novo.")
        est.update({"video_id": vid, "privacidade_devolvida": ((recurso_video.get("status") or {}).get("privacyStatus")),
                    "agendado_para": (recurso_video.get("status") or {}).get("publishAt")})
        est["etapas"]["video"] = "ok"
        est.pop("sessao_uri", None)
        gravar_privado(arq_estado, est)
    vid = est["video_id"]
    P.diz(f"✓ vídeo enviado: id {vid}")

    falhas = []
    for etapa, dados_etapa, acao in (
            ("thumbnail", plano["thumbnail"], lambda: envio.thumbnail(vid, raiz / plano["thumbnail"]["arquivo"])),
            ("legenda", plano["legenda"], lambda: envio.legenda(vid, raiz / plano["legenda"]["arquivo"], str(plano["legenda"]["idioma"]), plano["legenda"]["nome"]))):
        if est["etapas"].get(etapa) == "ok":
            continue
        if not dados_etapa:
            est["etapas"][etapa] = "não enviada"
            continue
        try:
            acao()
            est["etapas"][etapa] = "ok"
            P.diz(f"✓ {etapa} enviada")
        except Erro as e:
            est["etapas"][etapa] = "falhou"
            falhas.append(f"{etapa}: {e}")
            P.diz(f"✗ {etapa} não foi enviada — {e}", erro=True)
        gravar_privado(arq_estado, est)

    pedida = plano["recurso"]["status"]["privacyStatus"]
    registro = {"plataforma": pac.plataforma, "pacote": pac.id, "video_id": vid, "url": f"https://youtu.be/{vid}",
                "studio": f"https://studio.youtube.com/video/{vid}/edit", "enviado_em": P.agora_iso(),
                "privacidade_pedida": pedida, "privacidade_devolvida": est.get("privacidade_devolvida"),
                "agendado_para": plano["recurso"]["status"].get("publishAt"), "canal": plano.get("canal"), "etapas": est["etapas"],
                "codigo_confirmado": plano["codigo"], "por": "api", "numero_do_envio": plano["numero_do_envio"],
                # o que valia quando o vídeo subiu: o estado da validação e, se houve, a exceção inteira (motivo, problemas, data)
                "validacao_no_envio": estado_val, "validado_em": (val or {}).get("validado_em"),
                "excecoes": list((val or {}).get("excecoes") or []) if estado_val == "ok_com_excecao" else []}
    if not falhas:
        P.gravar_json(pac.pasta / "envio.json", registro)
        h = historico()
        h.append({k: registro[k] for k in ("pacote", "video_id", "enviado_em", "privacidade_pedida")})
        gravar_privado(pasta_envios() / "historico.json", h)
        try:
            arq_estado.unlink()
        except OSError:
            pass
        P.atualizar_indice(raiz, d, P.Limites())
    if est.get("privacidade_devolvida") and est["privacidade_devolvida"] != pedida:
        P.diz(f"! pedimos «{pedida}» e o YouTube devolveu «{est['privacidade_devolvida']}» (projeto de API não auditado trava em privado).", erro=True)
    P.diz(f"Confira no Studio antes de qualquer outra coisa: {registro['studio']}")
    P.diz("  título inteiro · primeiras linhas da descrição · capítulos · thumbnail · legenda · privacidade/agendamento")
    if falhas:
        P.diz("O vídeo subiu, mas houve falha em etapa complementar. Rode o mesmo comando de novo para repetir só o que faltou; "
              "para concluir sem ela, simule com --sem-thumbnail/--sem-legenda e confirme o novo código (o vídeo NÃO é reenviado); ou conclua pelo Studio.", erro=True)
        return P.SAIDA_ERRO
    return P.SAIDA_OK


def cmd_autorizar(args) -> int:
    escopos = [ESCOPO_ENVIO, ESCOPO_LEITURA] + ([ESCOPO_LEGENDAS] if args.legendas else [])
    if not args.confirmar:
        P.diz("SIMULAÇÃO de autorização (nada foi aberto, a rede não foi tocada). Com --confirmar este comando:")
        P.diz(f"  1. lê o cliente OAuth em {caminho_cliente()}" + ("" if caminho_cliente().is_file() else "   ← AINDA NÃO EXISTE (o usuário cria no Google Cloud Console)"))
        P.diz("  2. abre um servidor só nesta máquina (127.0.0.1, porta livre) para receber o retorno;")
        P.diz(f"  3. mostra o endereço de consentimento do Google ({URL_AUTORIZACAO}) — o USUÁRIO faz login e autoriza no navegador dele;")
        P.diz("  4. troca o código pelo token (PKCE S256) e grava " + str(caminho_token()) + " com permissão 600.")
        P.diz("Escopos pedidos:")
        for e in escopos:
            P.diz(f"  · {e}")
        if not args.legendas:
            P.diz("  (sem --legendas o script não envia .srt: o escopo de legendas dá poder de editar e apagar vídeos, só peça se for usar)")
        P.diz("Peça ao usuário um «sim» explícito antes de rodar com --confirmar.")
        return P.SAIDA_OK
    end = Enderecos()
    abrir = None
    if not args.sem_navegador:
        import webbrowser
        abrir = webbrowser.open
    tok = autorizar(end, escopos, abrir=abrir, porta=args.porta, espera=args.espera)
    canal = tok.get("canal")
    P.diz("✓ autorização concluída. Token gravado em " + str(caminho_token()) + " (permissão 600).")
    P.diz("  Conta: " + (f"{canal.get('titulo')} (canal {canal.get('id')})" if canal else "canal não identificado — confira no primeiro plano de envio"))
    P.diz("  Escopos concedidos: " + ", ".join(e.rsplit("/", 1)[-1] for e in tok.get("escopos", [])))
    return P.SAIDA_OK


def cmd_estado(args) -> int:
    P.diz(f"Pasta de configuração: {pasta_ops()}")
    cli = caminho_cliente()
    P.diz(f"Cliente OAuth: {'presente' if cli.is_file() else 'AUSENTE'} ({cli})" + (" — PERMISSÃO FROUXA: rode chmod 600" if permissao_frouxa(cli) else ""))
    tok = ler_token()
    if tok is None:
        P.diz("Token: nenhuma conta autorizada.")
    else:
        canal = tok.get("canal") or {}
        P.diz(f"Token: conta {canal.get('titulo') or '(canal não identificado)'} · obtido em {tok.get('obtido_em', '?')} · "
              f"escopos: {', '.join(e.rsplit('/', 1)[-1] for e in tok.get('escopos', [])) or '?'}")
        if tok.get("refresh_expira_em"):
            P.diz("  o refresh token expira em " + datetime.fromtimestamp(int(tok["refresh_expira_em"])).astimezone().isoformat(timespec="minutes"))
    pend = sorted(pasta_envios().glob("*.json")) if pasta_envios().is_dir() else []
    pend = [p for p in pend if p.name != "historico.json"]
    P.diz(f"Envios feitos por esta máquina: {len(historico())}. Envios interrompidos aguardando retomada: {len(pend)}.")
    for p in pend:
        try:
            e = P.ler_json(p)
            P.diz(f"  · pacote {e.get('pacote')} em {e.get('projeto')} — " + (f"vídeo {e.get('video_id')} enviado; etapas: {e.get('etapas')}" if e.get("video_id") else f"sessão aberta em {e.get('criada_em')}"))
        except Erro:
            pass
    return P.SAIDA_OK


def montar_parser() -> P.Parser:
    p = P.Parser(prog="enviar_youtube.py", description=(
        "Envia um pacote validado (youtube ou shorts) pela YouTube Data API v3. Simular é o padrão; enviar exige --confirmar CODIGO.\n"
        "NÃO TESTADO CONTRA A API REAL: o primeiro envio real deve ser privado e conferido no Studio."),
        epilog=("Exemplos:\n"
                "  enviar_youtube.py autorizar                 (mostra o que a autorização faz)\n"
                "  enviar_youtube.py autorizar --confirmar     (o usuário faz o login no navegador dele)\n"
                "  enviar_youtube.py enviar youtube            (plano completo, sem rede)\n"
                "  enviar_youtube.py enviar youtube --confirmar 1a2b3c4d\n"
                "Códigos de saída: 0 ok · 1 erro/recusado · 2 projeto sem direção de arte · 64 uso incorreto."))
    p.add_argument("--projeto", metavar="PASTA", help="pasta do projeto ou qualquer pasta dentro dele (padrão: pasta atual)")
    sub = p.add_subparsers(dest="comando", metavar="<subcomando>", parser_class=P.Parser)

    s = sub.add_parser("enviar", help="simula (padrão) ou envia um pacote", description=(
        "Sem --confirmar: imprime o plano completo e o código de confirmação, sem tocar a rede (refaz a conferência do pacote: um ffprobe).\n"
        "Com --confirmar CODIGO: envia vídeo (retomável), thumbnail e legenda. Interrompido, o mesmo comando retoma."))
    s.add_argument("pacote", nargs="?", default="youtube", help="youtube (padrão) | shorts | shorts/<corte>")
    s.add_argument("--simular", action="store_true", help="imprime o plano e sai (é o padrão)")
    s.add_argument("--confirmar", nargs="?", const="", metavar="CODIGO", help="envia de verdade; CODIGO é o impresso pela simulação que o usuário aprovou")
    s.add_argument("--usar-privacidade-do-pacote", action="store_true", help="envia com a privacidade do meta.json em vez de private")
    s.add_argument("--sem-thumbnail", action="store_true", help="não envia a thumbnail")
    s.add_argument("--sem-legenda", action="store_true", help="não envia o .srt")
    s.add_argument("--reenviar", action="store_true", help="envia de novo um pacote que já tem envio.json (cria OUTRO vídeo no canal); "
                                                           "o plano de reenvio tem código próprio: simule com --reenviar e confirme com --reenviar")
    s.add_argument("--pedaco-mb", type=float, default=PEDACO_PADRAO_MB, metavar="MB", help=f"tamanho do pedaço (múltiplo de 256 KB; padrão {PEDACO_PADRAO_MB})")
    s.add_argument("--tentativas", type=int, default=6, metavar="N", help="falhas seguidas toleradas antes de parar (padrão 6; o envio fica retomável)")
    s.add_argument("--json", action="store_true", help="imprime o plano em JSON")
    s.set_defaults(func=cmd_enviar)

    s = sub.add_parser("autorizar", help="login OAuth feito pelo usuário no navegador dele", description=(
        "Fluxo OAuth 2.0 de aplicativo instalado com redirecionamento para 127.0.0.1 e PKCE. Sem --confirmar só explica o que faria."))
    s.add_argument("--confirmar", action="store_true", help="inicia o fluxo de verdade (depois do «sim» do usuário)")
    s.add_argument("--legendas", action="store_true", help="pede também o escopo youtube.force-ssl, necessário para enviar .srt")
    s.add_argument("--sem-navegador", action="store_true", help="não tenta abrir o navegador; só imprime o endereço")
    s.add_argument("--porta", type=int, default=0, metavar="N", help="porta local do retorno (padrão: 0 = automática)")
    s.add_argument("--espera", type=float, default=300.0, metavar="SEG", help="tempo máximo esperando o usuário (padrão 300)")
    s.set_defaults(func=cmd_autorizar)

    s = sub.add_parser("estado", help="conta autorizada e envios pendentes (sem segredos)")
    s.set_defaults(func=cmd_estado)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = montar_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return P.SAIDA_USO
    try:
        return args.func(args)
    except Erro as e:
        P.diz(("erro de uso: " if isinstance(e, ErroUso) else "erro: ") + str(e), erro=True)
        return e.codigo
    except KeyboardInterrupt:
        P.diz("\ninterrompido. Se um envio estava em curso, rode o mesmo comando de novo para retomar.", erro=True)
        return P.SAIDA_ERRO
    except Exception as e:
        codigo = getattr(e, "codigo", None)
        if codigo is not None and hasattr(e, "mensagem"):
            P.diz(f"erro: {e}", erro=True)
            return int(codigo)
        return P.erro_interno(e)


if __name__ == "__main__":
    sys.exit(main())
