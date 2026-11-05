#!/usr/bin/env python3
"""sonda.py: pede cada rota e diz em qual delas cada marcador apareceu na resposta crua.

Só faz GET: uma requisição por rota, com pausa entre elas. Não executa JavaScript, não envia
formulário, não usa proxy do ambiente e nunca imprime o valor do cookie.

uso:
  python3 sonda.py --base http://localhost:3000 --rota / --rota /itens/item-pago \\
      --marcador PAGO-INICIO-R3NM3R --marcador PAGO-FIM-DTVAV3 --controle LIVRE-INICIO-AXWPYX

persona:
  sem nada, a sonda é o visitante anônimo. Para pedir como outra persona, ponha o valor do
  cabeçalho Cookie na variável de ambiente SONDA_COOKIE (no seu terminal, nunca na conversa).

alvo:
  por padrão só localhost, 127.0.0.1 e nomes terminados em .localhost ou .test. Qualquer outro
  endereço exige --site-proprio <host exato>, e só vale para o site de quem está rodando.

saída: 0 nada vazou e tudo foi conferido; 1 há "vazou:"; 2 uso errado;
       3 nada vazou, mas alguma rota ou o controle não foi conferido ("não conferi:").

limites: a busca é por texto exato. Marcador que não foi plantado nos dados, que chega
codificado (base64, compactação que a sonda não abre) ou partido entre dois blocos não é
achado. "limpo" quer dizer "não achei o que procurei", e só para a persona que pediu.
"""

import argparse
import gzip
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

HOSTS_LOCAIS = {"localhost", "127.0.0.1"}
SUFIXOS_LOCAIS = (".localhost", ".test")
LIMITE_DE_ROTAS = 200
LIMITE_DE_BYTES = 5_000_000
TAMANHO_MINIMO_DO_MARCADOR = 8
PAUSA_MINIMA_FORA_DO_LOCAL = 1.0
CABECALHOS_RECUSADOS = {"cookie", "authorization", "host"}
AGENTE = "sonda-de-vazamento/1 (conferencia do proprio site)"


class ErroDeUso(Exception):
    pass


class SemRedirecionar(urllib.request.HTTPRedirectHandler):
    """Redirecionamento não é seguido às cegas: a tela de login também 'não contém' o marcador."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def e_local(host):
    return host in HOSTS_LOCAIS or host.endswith(SUFIXOS_LOCAIS)


def conferir_alvo(base, site_proprio, tem_cookie):
    """Devolve (base sem barra final, host, local?). Lança ErroDeUso antes de qualquer requisição."""
    partes = urllib.parse.urlsplit(base)
    host = (partes.hostname or "").lower()
    if partes.scheme not in ("http", "https") or not host:
        raise ErroDeUso("--base precisa ser http://host[:porta] ou https://host[:porta]")
    if partes.username or partes.password or partes.query or partes.fragment:
        raise ErroDeUso("--base não leva usuário, senha, parâmetros nem âncora")
    if partes.path not in ("", "/"):
        raise ErroDeUso("--base é só o endereço; o caminho vai em --rota")
    local = e_local(host)
    if not local:
        if not site_proprio:
            raise ErroDeUso(
                f'"{host}" não é local. Se o site é seu, repita com --site-proprio {host}'
            )
        if site_proprio.lower() != host:
            raise ErroDeUso(f'--site-proprio "{site_proprio}" não é o host de --base ("{host}")')
        if tem_cookie and partes.scheme != "https":
            raise ErroDeUso("cookie fora do local só por https")
    return f"{partes.scheme}://{partes.netloc}", host, local


def ler_linhas(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        linhas = [linha.strip() for linha in arquivo]
    return [linha for linha in linhas if linha and not linha.startswith("#")]


def sem_repetidos(itens):
    return list(dict.fromkeys(itens))


def conferir_entradas(args):
    rotas = sem_repetidos(args.rota + (ler_linhas(args.rotas_de) if args.rotas_de else []))
    marcadores = sem_repetidos(
        args.marcador + (ler_linhas(args.marcadores_de) if args.marcadores_de else [])
    )
    if not rotas:
        raise ErroDeUso("nenhuma rota: use --rota ou --rotas-de")
    if not marcadores and not args.controle:
        raise ErroDeUso("nada a procurar: use --marcador, --marcadores-de ou --controle")
    if len(rotas) > LIMITE_DE_ROTAS:
        raise ErroDeUso(f"{len(rotas)} rotas: o limite é {LIMITE_DE_ROTAS} por execução")
    for rota in rotas:
        if not rota.startswith("/") or rota.startswith("//") or "#" in rota or " " in rota:
            raise ErroDeUso(f'rota "{rota}": comece por uma barra só, sem host, espaço nem âncora')
    for texto in marcadores + args.controle:
        if len(texto) < TAMANHO_MINIMO_DO_MARCADOR:
            raise ErroDeUso(
                f'"{texto}" tem menos de {TAMANHO_MINIMO_DO_MARCADOR} caracteres: casaria por acaso'
            )
    cabecalhos = {}
    for bruto in args.cabecalho:
        nome, separador, valor = bruto.partition(":")
        if not separador or not nome.strip() or any(c in bruto for c in "\r\n"):
            raise ErroDeUso(f'--cabecalho "{bruto}": use o formato "Nome: valor"')
        if nome.strip().lower() in CABECALHOS_RECUSADOS:
            raise ErroDeUso(f"--cabecalho não aceita {nome.strip()}: o cookie vai em SONDA_COOKIE")
        cabecalhos[nome.strip()] = valor.strip()
    return rotas, marcadores, cabecalhos


def abrir_corpo(bruto, codificacao):
    """Devolve o texto da resposta, ou None se a compactação não é das que a sonda abre."""
    codificacao = (codificacao or "identity").strip().lower()
    try:
        if codificacao == "gzip":
            bruto = gzip.decompress(bruto)
        elif codificacao == "deflate":
            bruto = zlib.decompress(bruto)
        elif codificacao != "identity":
            return None
    except (OSError, EOFError, zlib.error):
        return None
    return bruto.decode("utf-8", errors="replace")


def pedir(abridor, url, cabecalhos, tempo):
    """Um GET. Devolve (status, tipo, texto ou None, destino do redirecionamento, cortado?)."""
    pedido = urllib.request.Request(url, headers=cabecalhos, method="GET")
    try:
        resposta = abridor.open(pedido, timeout=tempo)
    except urllib.error.HTTPError as erro:  # 3xx sem seguir, 4xx e 5xx: o corpo também é varrido
        resposta = erro
    with resposta:
        bruto = resposta.read(LIMITE_DE_BYTES + 1)
        tipo = (resposta.headers.get("Content-Type") or "sem tipo").split(";")[0].strip()
        texto = abrir_corpo(bruto[:LIMITE_DE_BYTES], resposta.headers.get("Content-Encoding"))
        codigo = resposta.code
        destino = resposta.headers.get("Location") if 300 <= codigo < 400 else None
        return codigo, tipo, texto, destino, len(bruto) > LIMITE_DE_BYTES


def mesmo_caminho(url, destino):
    """O destino é a mesma página no mesmo host, só com parâmetros a mais? Devolve a URL ou None."""
    absoluto = urllib.parse.urljoin(url, destino)
    a, b = urllib.parse.urlsplit(url), urllib.parse.urlsplit(absoluto)
    return absoluto if (a.scheme, a.netloc, a.path) == (b.scheme, b.netloc, b.path) else None


def onde_fica(texto, posicao):
    """Pista de onde o marcador está. É pista, não prova: leia a resposta para confirmar."""
    if texto.rfind("<script", 0, posicao) > texto.rfind("</script", 0, posicao):
        return "dentro de <script>: dado embutido para o navegador"
    abre = texto.rfind("<", 0, posicao)
    if abre != -1 and texto.find(">", abre, posicao) == -1:
        pedacos = texto[abre + 1 : abre + 30].split(None, 1)
        nome = pedacos[0] if pedacos else ""
        return f"em atributo de <{nome}>" if nome.isalnum() else "dentro de uma marcação"
    return "no texto da resposta"


def montar_argumentos():
    analisador = argparse.ArgumentParser(
        prog="sonda.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analisador.add_argument("--base", required=True, help="endereço do site, sem caminho")
    analisador.add_argument("--rota", action="append", default=[], help="caminho; repita a opção")
    analisador.add_argument("--rotas-de", metavar="ARQUIVO", help="uma rota por linha; # comenta")
    analisador.add_argument("--marcador", action="append", default=[],
                            help="texto que NÃO pode aparecer; repita a opção")
    analisador.add_argument("--marcadores-de", metavar="ARQUIVO", help="um marcador por linha")
    analisador.add_argument("--controle", action="append", default=[],
                            help="texto que TEM de aparecer em alguma rota: prova que a busca enxerga")
    analisador.add_argument("--cabecalho", action="append", default=[], metavar='"Nome: valor"',
                            help="cabeçalho extra, como o que pede o payload do framework")
    analisador.add_argument("--site-proprio", metavar="HOST",
                            help="libera um host que não é local; tem de ser igual ao de --base")
    analisador.add_argument("--pausa", type=float, default=1.0,
                            help="segundos entre requisições (padrão 1; fora do local, mínimo 1)")
    analisador.add_argument("--minimo", type=int, default=200,
                            help="bytes mínimos para a resposta contar como conferida (200)")
    analisador.add_argument("--tempo", type=float, default=15.0, help="limite por requisição, em s")
    return analisador


def main(argv=None):
    args = montar_argumentos().parse_args(argv)
    cookie = os.environ.get("SONDA_COOKIE", "").strip()
    try:
        base, host, local = conferir_alvo(args.base, args.site_proprio, bool(cookie))
        rotas, marcadores, cabecalhos = conferir_entradas(args)
        if args.pausa < 0 or args.minimo < 0 or args.tempo <= 0:
            raise ErroDeUso("--pausa e --minimo não podem ser negativos; --tempo é maior que zero")
    except (ErroDeUso, OSError) as erro:
        print(f"uso: {erro}", file=sys.stderr)
        return 2
    pausa = args.pausa if local else max(args.pausa, PAUSA_MINIMA_FORA_DO_LOCAL)
    cabecalhos = {"User-Agent": AGENTE, "Accept-Encoding": "identity", **cabecalhos}
    if cookie:
        cabecalhos["Cookie"] = cookie
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}), SemRedirecionar())
    persona = "com cookie (valor não exibido)" if cookie else "visitante anônimo"
    print(f"alvo: {base} ({'local' if local else 'site próprio: ' + host}) · persona: {persona}"
          f" · {len(rotas)} rota(s) · {len(marcadores)} marcador(es)")

    vazamentos, nao_conferidas, vistos = 0, 0, set()
    for indice, rota in enumerate(rotas):
        if indice:
            time.sleep(pausa)
        url = base + rota
        try:
            status, tipo, texto, destino, cortado = pedir(abridor, url, cabecalhos, args.tempo)
            seguinte = mesmo_caminho(url, destino) if destino else None
            if seguinte:  # o framework acrescentou um parâmetro: um salto só, para a mesma página
                status, tipo, texto, destino, cortado = pedir(
                    abridor, seguinte, cabecalhos, args.tempo
                )
        except (urllib.error.URLError, OSError, ValueError) as erro:
            motivo = getattr(erro, "reason", erro)
            print(f"não conferi: {rota} não respondeu ({motivo})")
            nao_conferidas += 1
            continue
        if texto is None:
            print(f"não conferi: {rota} veio compactada de um jeito que a sonda não abre ({status})")
            nao_conferidas += 1
            continue
        achados = [(m, texto.find(m)) for m in marcadores if m in texto]
        vistos.update(c for c in args.controle if c in texto)
        for marcador, posicao in achados:
            pista = onde_fica(texto, posicao)
            print(f"vazou: {rota} contém {marcador} ({status}, {tipo}, {pista})")
        vazamentos += len(achados)
        if achados:
            continue
        resumo = f"{status}, {tipo}, {len(texto.encode('utf-8'))} bytes"
        if status != 200:
            para = f", vai para {destino}" if destino else ""
            print(f"não conferi: {rota} respondeu {status}{para}: não é a página pedida")
        elif len(texto.encode("utf-8")) < args.minimo:
            print(f"não conferi: {rota} veio com menos de {args.minimo} bytes ({resumo})")
        elif cortado:
            print(f"não conferi: {rota} passa de {LIMITE_DE_BYTES} bytes; só o começo foi varrido")
        else:
            print(f"limpo: {rota} ({resumo})")
            continue
        nao_conferidas += 1

    faltam = [c for c in args.controle if c not in vistos]
    for controle in faltam:
        print(f"não conferi: o controle {controle} não apareceu em rota nenhuma; a sonda pode"
              " estar cega (rota errada, persona errada ou marcador que não está nos dados)")
    for controle in sorted(vistos):
        print(f"controle: {controle} apareceu, como esperado")
    print(f"resumo: {vazamentos} vazamento(s); {nao_conferidas} rota(s) não conferida(s);"
          f" {len(faltam)} controle(s) sem aparecer")
    if vazamentos:
        return 1
    return 3 if nao_conferidas or faltam else 0


if __name__ == "__main__":
    sys.exit(main())
