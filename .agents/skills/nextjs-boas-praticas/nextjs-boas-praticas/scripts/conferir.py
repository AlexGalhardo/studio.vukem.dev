#!/usr/bin/env python3
"""conferir.py: lê um projeto Next.js (App Router) e acusa cinco erros de arquitetura.

Só lê arquivos de código: não altera nada, não acessa a rede, não abre arquivos .env e nunca
imprime o valor de uma variável (só o nome).

uso:
  python3 conferir.py <projeto> [--guarda NOME]... [--sem-guarda ARQUIVO]...
                                [--segredos ARQUIVO]... [--alias PREFIXO]

confere:
  1. componente de cliente ("use client") que importa módulo só de servidor: next/headers,
     o pacote server-only ou um arquivo do projeto que tem `import "server-only"`;
  2. arquivo de ações ("use server" no topo) com função exportada que não começa pela guarda
     (padrão: requireUser e requireAdmin; troque com --guarda);
  3. função em cache ("use cache") que chama cookies() ou headers();
  4. página sem estado de carregamento (loading.* no segmento ou acima, ou <Suspense na própria
     página; se a página não tem async nem await, vira só aviso) ou sem estado de erro (error.*
     no segmento ou acima);
  5. variável de ambiente que não é NEXT_PUBLIC_ lida fora dos módulos indicados com --segredos,
     e nome de variável pública com cara de segredo.

saída: 0 nada acusado e tudo conferido; 1 há "acusa:"; 2 uso errado;
       3 nada acusado, mas alguma conferência não rodou ("não conferi:").

limites: lê texto. Olha só o import direto (não segue a cadeia), não entende a ordem de
execução, não vê <Suspense> dentro de um componente filho nem ação definida dentro de componente.
Não achar não prova que não há.
"""

import argparse
import os
import re
import sys

PASTAS_IGNORADAS = {
    ".git", "node_modules", ".next", "dist", "build", "out", "coverage", ".turbo", ".vercel",
    "tests", "test", "__tests__", "e2e", "scripts",
}
EXTENSOES = (".ts", ".tsx", ".js", ".jsx", ".mjs")
E_TESTE = re.compile(r"\.(test|spec)\.\w+$")
SUFIXOS = ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js")
ENV_LIVRES = {"NODE_ENV", "CI", "PORT", "NEXT_RUNTIME", "NEXT_PHASE", "TZ"}
CARA_DE_SEGREDO = re.compile(r"SECRET|PRIVATE|PASSWORD|SERVICE_ROLE|TOKEN")

IMPORT_DE = re.compile(r"^import\s+(?!type\b)[^;\"']*?\bfrom\s+[\"']([^\"']+)[\"']", re.M)
IMPORT_SOLTO = re.compile(r"^import\s+[\"']([^\"']+)[\"']", re.M)
IMPORT_DINAMICO = re.compile(r"\bimport\(\s*[\"']([^\"']+)[\"']\s*\)")
FUNCAO_EXPORTADA = re.compile(r"^export\s+(?:default\s+)?async\s+function\s+(\w+)\s*\(", re.M)
OUTRO_EXPORT = re.compile(r"^export\s+(?:const|let|var|function|default)\b(?!\s+async\s+function)", re.M)
LE_REQUISICAO = re.compile(r"\b(cookies|headers)\s*\(")
LE_ENV = re.compile(r"\bprocess\.env\.([A-Za-z0-9_]+)")


def diretiva(nome):
    return re.compile(r"^[ \t]*[\"']%s[\"'];?[ \t]*$" % re.escape(nome), re.M)


USE_CLIENT, USE_SERVER, USE_CACHE = diretiva("use client"), diretiva("use server"), diretiva("use cache")
SO_SERVIDOR = re.compile(r"^import\s+[\"']server-only[\"']", re.M)


class Relato:
    def __init__(self):
        self.contagem = {"acusa": 0, "aviso": 0, "ok": 0, "não conferi": 0}

    def linha(self, tipo, texto):
        self.contagem[tipo] += 1
        print("%s: %s" % (tipo, texto))

    def codigo(self):
        if self.contagem["acusa"]:
            return 1
        return 3 if self.contagem["não conferi"] else 0


def ler_fontes(raiz):
    """Caminho relativo (com /) -> texto, para todo arquivo de código fora de teste."""
    fontes = {}
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [s for s in subpastas if s not in PASTAS_IGNORADAS]
        for nome in arquivos:
            if not nome.endswith(EXTENSOES) or E_TESTE.search(nome) or nome.endswith(".d.ts"):
                continue
            caminho = os.path.join(pasta, nome)
            try:
                with open(caminho, encoding="utf-8") as arquivo:
                    fontes[os.path.relpath(caminho, raiz).replace(os.sep, "/")] = arquivo.read()
            except (OSError, UnicodeDecodeError):
                continue
    return fontes


def no_topo(texto, padrao):
    """A diretiva vale para o arquivo quando vem antes de qualquer import ou declaração."""
    achado = padrao.search(texto)
    if not achado:
        return False
    antes = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", texto[: achado.start()])
    return antes.strip() == ""


def imports_de_runtime(texto):
    return [m.group(1) for p in (IMPORT_DE, IMPORT_SOLTO, IMPORT_DINAMICO) for m in p.finditer(texto)]


def resolver(alvo, de, fontes, alias, base):
    """O arquivo do projeto que um import alcança, ou None (pacote externo, não achado)."""
    if alvo.startswith(alias):
        caminho = base + alvo[len(alias):]
    elif alvo.startswith("."):
        caminho = os.path.normpath(os.path.join(os.path.dirname(de), alvo)).replace(os.sep, "/")
    else:
        return None
    return next((caminho + s for s in SUFIXOS if caminho + s in fontes), None)


def corpo_apos(texto, inicio):
    """Do ponto dado até fechar a chave que estava aberta ali (contagem simples de chaves)."""
    nivel = 1
    for indice in range(inicio, len(texto)):
        if texto[indice] == "{":
            nivel += 1
        elif texto[indice] == "}":
            nivel -= 1
            if nivel == 0:
                return texto[inicio:indice]
    return texto[inicio:]


def primeira_instrucao(texto, abre_parentese):
    indice, nivel = abre_parentese, 0
    while indice < len(texto):
        nivel += texto[indice] == "("
        if texto[indice] == ")":
            nivel -= 1
            if nivel == 0:
                break
        indice += 1
    angulo = 0
    while indice < len(texto):
        angulo += (texto[indice] == "<") - (texto[indice] == ">")
        if texto[indice] == "{" and angulo == 0:
            break
        indice += 1
    corpo = re.sub(r"^(\s|//[^\n]*\n|/\*[\s\S]*?\*/)*", "", texto[indice + 1:])
    return re.split(r"[;\n]", corpo, maxsplit=1)[0]


def conferir_cliente(fontes, alias, base, relato):
    clientes = [f for f, t in fontes.items() if no_topo(t, USE_CLIENT)]
    achou = False
    for arquivo in sorted(clientes):
        for alvo in imports_de_runtime(fontes[arquivo]):
            destino = resolver(alvo, arquivo, fontes, alias, base)
            if alvo in ("server-only", "next/headers"):
                motivo = alvo
            elif destino and SO_SERVIDOR.search(fontes[destino]):
                motivo = "%s (só de servidor)" % destino
            else:
                continue
            achou = True
            relato.linha("acusa", "%s é de cliente e importa %s" % (arquivo, motivo))
    if not clientes:
        relato.linha("não conferi", 'cliente e servidor: nenhum arquivo com "use client"')
    elif not achou:
        relato.linha("ok", "%d arquivo(s) de cliente sem import só de servidor" % len(clientes))


def conferir_acoes(fontes, guardas, isentos, relato):
    comeca = re.compile(r"^(?:const\s+[\w{}\s,:]+=\s*)?await\s+(?:%s)\(" % "|".join(map(re.escape, guardas)))
    arquivos = [f for f, t in fontes.items() if no_topo(t, USE_SERVER)]
    total, achou = 0, False
    for arquivo in sorted(arquivos):
        texto = fontes[arquivo]
        if arquivo in isentos:
            relato.linha("aviso", "%s: isento da guarda por --sem-guarda" % arquivo)
            continue
        if OUTRO_EXPORT.search(texto):
            relato.linha("não conferi", "%s: há export que não é `export async function`" % arquivo)
        for funcao in FUNCAO_EXPORTADA.finditer(texto):
            total += 1
            if not comeca.match(primeira_instrucao(texto, funcao.end() - 1)):
                achou = True
                relato.linha("acusa", "%s: %s não começa pela guarda (%s)"
                             % (arquivo, funcao.group(1), ", ".join(guardas)))
    if not arquivos:
        relato.linha("não conferi", 'guarda: nenhum arquivo com "use server" no topo')
    elif not achou:
        relato.linha("ok", "%d ação(ões) começam pela guarda" % total)


def conferir_cache(fontes, relato):
    arquivos = [f for f, t in fontes.items() if USE_CACHE.search(t)]
    achou = False
    for arquivo in sorted(arquivos):
        texto = fontes[arquivo]
        if no_topo(texto, USE_CACHE):
            trechos = [texto]
        else:
            trechos = [corpo_apos(texto, m.end()) for m in USE_CACHE.finditer(texto)]
        if any(LE_REQUISICAO.search(trecho) for trecho in trechos):
            achou = True
            relato.linha("acusa", "%s: função em cache chama cookies() ou headers()" % arquivo)
        elif "next/headers" in imports_de_runtime(texto):
            relato.linha("aviso", "%s: tem função em cache e importa next/headers" % arquivo)
    if not arquivos:
        relato.linha("não conferi", 'cache: nenhum arquivo com "use cache"')
    elif not achou:
        relato.linha("ok", "%d arquivo(s) com cache sem cookies() nem headers()" % len(arquivos))


def conferir_estados(fontes, relato):
    raiz_app = next((p for p in ("app/", "src/app/") if any(f.startswith(p) for f in fontes)), None)
    if raiz_app is None:
        relato.linha("não conferi", "estados da rota: não achei a pasta app/")
        return
    paginas = [f for f in fontes if f.startswith(raiz_app) and re.search(r"/page\.(tsx|jsx|js|ts)$", "/" + f)]
    existe = lambda pasta, nome: any((pasta + nome + ext) in fontes for ext in (".tsx", ".jsx", ".js", ".ts"))
    limpas = 0
    for pagina in sorted(paginas):
        pasta = pagina.rsplit("/", 1)[0] + "/"
        acima = [pasta]
        while acima[-1] != raiz_app:
            acima.append(acima[-1].rstrip("/").rsplit("/", 1)[0] + "/")
        sem_carregamento = (not any(existe(p, "loading") for p in acima)
                            and "<Suspense" not in fontes[pagina])
        sem_erro = not any(existe(p, "error") for p in acima)
        if sem_carregamento:
            # Página sem async nem await não espera dado: vira aviso, não acusação
            espera = re.search(r"\b(async|await)\b", fontes[pagina]) is not None
            relato.linha("acusa" if espera else "aviso",
                         "%s: sem loading.* no segmento ou acima e sem <Suspense na página" % pagina)
        if sem_erro:
            relato.linha("acusa", "%s: sem error.* no segmento ou acima" % pagina)
        limpas += not (sem_carregamento or sem_erro)
    for nome in ("not-found", "global-error"):
        if not existe(raiz_app, nome):
            relato.linha("aviso", "%s%s.* não existe" % (raiz_app, nome))
    if not paginas:
        relato.linha("não conferi", "estados da rota: nenhuma página em %s" % raiz_app)
    elif limpas:
        relato.linha("ok", "%d de %d página(s) com carregamento e erro" % (limpas, len(paginas)))


def conferir_ambiente(fontes, modulos, relato):
    achou = False
    for arquivo in sorted(fontes):
        texto = fontes[arquivo]
        nomes = sorted(set(LE_ENV.findall(texto)) - ENV_LIVRES)
        for nome in nomes:
            if nome.startswith("NEXT_PUBLIC_") and CARA_DE_SEGREDO.search(nome):
                achou = True
                relato.linha("acusa", "%s: %s é pública (vai para o navegador) e tem nome de segredo"
                             % (arquivo, nome))
        privadas = [n for n in nomes if not n.startswith("NEXT_PUBLIC_")]
        if privadas and no_topo(texto, USE_CLIENT):
            achou = True
            relato.linha("acusa", "%s é de cliente e lê %s" % (arquivo, ", ".join(privadas)))
        elif privadas and modulos and arquivo not in modulos and "/" in arquivo:
            achou = True
            relato.linha("acusa", "%s lê %s fora do módulo de ambiente" % (arquivo, ", ".join(privadas)))
    if not modulos:
        relato.linha("não conferi", "segredo fora do módulo: passe --segredos <arquivo>")
    elif not achou:
        relato.linha("ok", "segredos lidos só em %s" % ", ".join(sorted(modulos)))


def main():
    parser = argparse.ArgumentParser(
        description="Lê um projeto Next.js (App Router) e acusa cinco erros de arquitetura. "
                    "Só lê: não altera nada, não acessa a rede e não abre arquivos .env.",
        epilog="saída: 0 limpo; 1 acusou; 2 uso errado; 3 alguma conferência não rodou. "
               "Lê texto: não achar não prova que não há.",
    )
    parser.add_argument("projeto", help="pasta raiz do projeto")
    parser.add_argument("--guarda", action="append", metavar="NOME",
                        help="função de guarda aceita no início da ação (repita; padrão: requireUser, requireAdmin)")
    parser.add_argument("--sem-guarda", action="append", default=[], metavar="ARQUIVO",
                        help="arquivo de ações isento da guarda, como o de login (repita)")
    parser.add_argument("--segredos", action="append", default=[], metavar="ARQUIVO",
                        help="módulo que pode ler variável de ambiente que não é NEXT_PUBLIC_ (repita)")
    parser.add_argument("--alias", default="@/", metavar="PREFIXO",
                        help="apelido de import que aponta para a raiz do código (padrão: @/)")
    args = parser.parse_args()

    if not os.path.isdir(args.projeto):
        print("uso errado: %s não é uma pasta" % args.projeto, file=sys.stderr)
        return 2
    fontes = ler_fontes(args.projeto)
    if not fontes:
        print("uso errado: nenhum arquivo de código em %s" % args.projeto, file=sys.stderr)
        return 2
    normal = lambda caminho: os.path.normpath(caminho).replace(os.sep, "/")
    for caminho in args.sem_guarda + args.segredos:
        if normal(caminho) not in fontes:
            print("uso errado: %s não existe no projeto (caminho relativo à raiz)" % caminho, file=sys.stderr)
            return 2
    base = "src/" if any(f.startswith("src/app/") for f in fontes) else ""

    relato = Relato()
    conferir_cliente(fontes, args.alias, base, relato)
    conferir_acoes(fontes, args.guarda or ["requireUser", "requireAdmin"],
                   {normal(c) for c in args.sem_guarda}, relato)
    conferir_cache(fontes, relato)
    conferir_estados(fontes, relato)
    conferir_ambiente(fontes, {normal(c) for c in args.segredos}, relato)
    print("resumo: %d acusa, %d aviso, %d ok, %d não conferi" % tuple(
        relato.contagem[t] for t in ("acusa", "aviso", "ok", "não conferi")))
    return relato.codigo()


if __name__ == "__main__":
    sys.exit(main())
