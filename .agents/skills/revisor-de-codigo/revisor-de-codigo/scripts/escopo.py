#!/usr/bin/env python3
"""escopo.py: lê o git e imprime o que uma revisão de código precisa cobrir.

Só lê: não altera nada, não acessa a rede e não abre arquivo de ambiente (.env e parecidos).
Deles sai só o nome: nem conteúdo, nem contagem de linhas.

uso:
  python3 escopo.py [projeto] [--base REF] [--zona NOME=PADRÕES] [--lente NOME=LENTES]
                    [--config ARQUIVO] [--max-linhas N] [--max-arquivos N]

imprime:
  1. a base usada e como foi escolhida;
  2. os arquivos mudados desde a base (commits, área de preparo, árvore de trabalho e arquivos
     não rastreados), com linhas acrescentadas e removidas, agrupados por zona;
  3. as lentes que a mudança pede, com o motivo de cada uma;
  4. avisos: mudança grande demais para uma revisão só, migration junto de código, arquivo de
     teste removido, arquivo de ambiente no diff.

base: sem --base, é o ponto em que HEAD se separou do ramo principal (origin/HEAD, origin/main,
  origin/master, main ou master, o primeiro que existir). Sem ramo principal, é o próprio HEAD,
  e só entra o que ainda não foi commitado.

zonas: cada arquivo cai na primeira zona cujo padrão casa. Padrão sem barra casa com o nome do
  arquivo em qualquer pasta; com barra, casa com o caminho desde a raiz, e ** atravessa pastas.
  Maiúsculas e minúsculas não fazem diferença. --zona pagamento='**/cobranca/**,*fatura*'
  declara ou substitui uma zona; --lente pagamento=seguranca-e-fronteiras,comportamento diz as
  lentes dela. --config lê o mesmo de um arquivo com as seções [zonas] e [lentes]; sem --config,
  vale o .revisor.ini da raiz do repositório, se existir. Zona declarada vem antes das embutidas.

saída: 0 escopo impresso, sem aviso; 1 escopo impresso, com aviso; 2 uso errado ou git falhou;
       3 nada mudou em relação à base.

limites: a zona sai do caminho do arquivo, não do conteúdo. Um arquivo fora dos padrões pode
  tocar pagamento ou permissão sem cair na zona: na dúvida, acrescente a lente. Este script
  delimita a revisão; não revisa nada.
"""

import argparse
import configparser
import os
import re
import subprocess
import sys

ORDEM_DAS_LENTES = ["banco-e-implantacao", "seguranca-e-fronteiras", "comportamento", "testes"]
E_TESTE = re.compile(
    r"(^|/)(tests?|__tests__|specs?|e2e|cypress)/|\.(test|spec)\.\w+$|_test\.\w+$|(^|/)test_[^/]*$",
    re.I,
)
E_AMBIENTE = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.env)$", re.I)
E_EXEMPLO = re.compile(r"\.(example|sample|template|dist|defaults?)$", re.I)
# O git não calcula a diferença destes caminhos: deles só o nome é pedido.
FORA_DA_CONTAGEM = [":(exclude,glob)**/.env*", ":(exclude,glob)**/*.env"]
LIMITE_DE_BYTES = 1_000_000

# (zona, padrões, lentes). A ordem é a da sensibilidade: o primeiro padrão que casa decide.
ZONAS_EMBUTIDAS = [
    ("segredo", "*.pem, *.key, *.p12, *.pfx, *secret*, *credential*, **/secrets/**",
     ["seguranca-e-fronteiras"]),
    ("documentacao", "*.md, *.mdx, *.rst, *.adoc, LICENSE*", []),
    ("banco", "**/migrations/**, **/migrate/**, *.sql, **/prisma/**, **/drizzle/**, "
     "**/alembic/**, **/db/**, **/database/**, **/seeds/**, seed.*, schema.rb",
     ["banco-e-implantacao"]),
    ("pagamento", "**/billing/**, **/payment*/**, **/checkout/**, **/subscription*/**, "
     "**/webhook*/**, *billing*, *payment*, *checkout*, *subscription*, *webhook*, *invoice*, "
     "*paywall*, *stripe*, *pagamento*, *assinatura*, *cobranca*",
     ["seguranca-e-fronteiras", "comportamento"]),
    ("acesso", "**/auth/**, **/authz/**, **/login/**, **/session*/**, **/permission*/**, "
     "**/polic*/**, **/guards/**, **/roles/**, **/admin/**, *auth*, *session*, *login*, "
     "*permission*, *policy*, *policies*, *guard*, *rls*, middleware.*, proxy.*",
     ["seguranca-e-fronteiras", "comportamento"]),
    ("testes", None, ["testes"]),
    ("implantacao", ".github/**, .gitlab-ci.yml, .circleci/**, Dockerfile*, docker-compose*, "
     "compose.y*ml, *.tf, Procfile, Makefile, vercel.json, netlify.toml, fly.toml, render.yaml, "
     "package.json, package-lock.json, pnpm-lock.yaml, yarn.lock, *.lock, go.mod, go.sum, "
     "requirements*.txt, pyproject.toml, Gemfile, composer.json, Cargo.toml, pom.xml, "
     "build.gradle*, next.config.*, vite.config.*, nginx*.conf, **/deploy/**, **/infra/**, "
     "**/k8s/**, **/helm/**", ["banco-e-implantacao"]),
    ("interface", "**/app/**, **/pages/**, **/components/**, **/views/**, **/templates/**, "
     "**/layouts/**, **/routes/**, **/controllers/**, **/handlers/**, **/api/**, **/public/**, "
     "**/static/**, *.tsx, *.jsx, *.vue, *.svelte, *.astro, *.html, *.css, *.scss, *.erb, "
     "*.blade.php", ["comportamento"]),
]
SEM_CODIGO = {"documentacao", "segredo"}


class Falha(Exception):
    pass


def git(raiz, *args):
    ambiente = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", raiz, "-c", "core.quotepath=off"] + list(args),
                           capture_output=True, env=ambiente)
    except FileNotFoundError:
        raise Falha("git não encontrado no PATH")
    if r.returncode != 0:
        erro = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise Falha("git %s falhou: %s" % (args[0], erro[-1] if erro else "sem mensagem"))
    return r.stdout.decode("utf-8", "surrogateescape")


def commit_de(raiz, ref):
    try:
        return git(raiz, "rev-parse", "--verify", "--quiet", ref + "^{commit}").strip()
    except Falha:
        return ""


def ponto_comum(raiz, ref):
    try:
        return git(raiz, "merge-base", ref, "HEAD").strip()
    except Falha:
        return ""


def escolher_base(raiz, pedida):
    if pedida:
        if not commit_de(raiz, pedida):
            raise Falha("a base '%s' não existe neste repositório" % pedida)
        comum = ponto_comum(raiz, pedida)
        if not comum:
            raise Falha("HEAD e '%s' não têm commit em comum" % pedida)
        return comum, "ponto em que HEAD se separou de %s, pedida em --base" % pedida
    try:
        padrao = git(raiz, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD").strip()
    except Falha:
        padrao = ""
    for ref in [padrao, "origin/main", "origin/master", "main", "master"]:
        if ref and commit_de(raiz, ref):
            comum = ponto_comum(raiz, ref)
            if comum:
                return comum, "ponto em que HEAD se separou de %s, escolhida sozinha" % ref
    return commit_de(raiz, "HEAD"), "o próprio HEAD: nenhum ramo principal foi achado"


def compilar(padrao):
    p = padrao.strip()
    if "/" not in p:
        p = "**/" + p
    partes, i = [], 0
    while i < len(p):
        if p.startswith("**/", i):
            partes.append("(?:.*/)?")
            i += 3
        elif p.startswith("**", i):
            partes.append(".*")
            i += 2
        elif p[i] == "*":
            partes.append("[^/]*")
            i += 1
        elif p[i] == "?":
            partes.append("[^/]")
            i += 1
        else:
            partes.append(re.escape(p[i]))
            i += 1
    return re.compile("^" + "".join(partes) + "$", re.I)


def par(texto, opcao):
    nome, sep, valor = texto.partition("=")
    itens = [v.strip() for v in valor.split(",") if v.strip()]
    if not sep or not nome.strip() or not itens:
        raise Falha("%s espera NOME=VALOR,VALOR; recebi '%s'" % (opcao, texto))
    return nome.strip().lower(), itens


def montar_zonas(args, raiz):
    """Devolve ([(zona, [regex])], {zona: [lentes]}, origem da configuração)."""
    declaradas, lentes, origem = [], {}, "padrões embutidos"
    caminho = args.config or os.path.join(raiz, ".revisor.ini")
    if args.config or os.path.isfile(caminho):
        leitor = configparser.ConfigParser(interpolation=None, delimiters=("=",))
        try:
            with open(caminho, encoding="utf-8") as arquivo:
                leitor.read_file(arquivo)
        except (OSError, configparser.Error) as erro:
            raise Falha("não li a configuração %s: %s" % (caminho, erro))
        for secao, opcao, destino in (("zonas", "[zonas]", declaradas), ("lentes", "[lentes]", None)):
            if not leitor.has_section(secao):
                continue
            for nome, valor in leitor.items(secao):
                chave, itens = par("%s=%s" % (nome, valor.replace("\n", ",")), opcao)
                if destino is None:
                    lentes[chave] = itens
                else:
                    destino.append((chave, itens))
        origem = caminho
    declaradas += [par(z, "--zona") for z in args.zona]
    lentes.update(dict(par(l, "--lente") for l in args.lente))

    zonas, mapa = [], {}
    for nome, padroes in declaradas:
        zonas = [z for z in zonas if z[0] != nome] + [(nome, [compilar(p) for p in padroes])]
        mapa[nome] = ["comportamento"]
    for nome, padroes, lentes_da_zona in ZONAS_EMBUTIDAS:
        if nome not in mapa:
            regexes = [E_TESTE] if padroes is None else [compilar(p) for p in padroes.split(",")]
            zonas.append((nome, regexes))
        mapa[nome] = lentes_da_zona
    mapa["outros"] = ["comportamento"]
    mapa.update(lentes)
    return zonas, mapa, origem


def zona_de(caminho, zonas):
    if E_AMBIENTE.search(caminho):
        return "segredo"
    for nome, regexes in zonas:
        if any(r.search(caminho) for r in regexes):
            return nome
    return "outros"


def contar_linhas(raiz, caminho):
    inteiro = os.path.join(raiz, caminho)
    try:
        if os.path.islink(inteiro) or os.path.getsize(inteiro) > LIMITE_DE_BYTES:
            return None
        with open(inteiro, "rb") as arquivo:
            dados = arquivo.read()
    except OSError:
        return None
    if b"\0" in dados[:8000]:
        return None
    return dados.count(b"\n") + (1 if dados and not dados.endswith(b"\n") else 0)


def mudancas(raiz, base, zonas):
    arquivos = {}

    def novo(caminho, status, antigo=None):
        arquivos[caminho] = {
            "caminho": caminho, "status": status, "antigo": antigo, "mais": None, "menos": None,
            "ambiente": bool(E_AMBIENTE.search(caminho)), "teste": bool(E_TESTE.search(caminho)),
            "zona": zona_de(caminho, zonas),
        }

    campos = git(raiz, "diff", "--name-status", "-M", "-z", base).split("\0")
    i = 0
    while i + 1 < len(campos) and campos[i]:
        if campos[i][0] in "RC":
            novo(campos[i + 2], campos[i][0], campos[i + 1])
            i += 3
        else:
            novo(campos[i + 1], campos[i][0])
            i += 2

    campos = git(raiz, "diff", "--numstat", "-M", "-z", base, "--", ".", *FORA_DA_CONTAGEM).split("\0")
    i = 0
    while i < len(campos) and campos[i]:
        mais, menos, caminho = campos[i].split("\t", 2)
        if caminho == "":
            caminho = campos[i + 2]
            i += 3
        else:
            i += 1
        item = arquivos.get(caminho)
        if item and not item["ambiente"] and mais != "-":
            item["mais"], item["menos"] = int(mais), int(menos)

    for caminho in git(raiz, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
        if caminho:
            novo(caminho, "?")
            if not arquivos[caminho]["ambiente"]:
                linhas = contar_linhas(raiz, caminho)
                if linhas is not None:
                    arquivos[caminho]["mais"], arquivos[caminho]["menos"] = linhas, 0
    return list(arquivos.values())


def avisar(arquivos, base_e_head, args):
    avisos, notas = [], []
    linhas = sum((a["mais"] or 0) + (a["menos"] or 0) for a in arquivos)
    if linhas > args.max_linhas or len(arquivos) > args.max_arquivos:
        avisos.append(
            "mudança grande demais para uma revisão só (%d arquivos, %d linhas; o limite é %d "
            "arquivos ou %d linhas): divida por zona, da mais sensível para a menos"
            % (len(arquivos), linhas, args.max_arquivos, args.max_linhas))
    codigo = [a for a in arquivos if a["zona"] not in SEM_CODIGO and not a["teste"]]
    if any(a["zona"] == "banco" for a in arquivos) and any(a["zona"] != "banco" for a in codigo):
        avisos.append(
            "migration junto de código: confira a ordem de subida nos dois sentidos (o código "
            "novo sem a migration; a migration com o código antigo ainda no ar)")
    for a in arquivos:
        if a["teste"] and a["status"] == "D":
            avisos.append("arquivo de teste removido: %s: diga onde a regra que ele provava "
                          "continua provada" % a["caminho"])
        if not a["ambiente"]:
            continue
        if E_EXEMPLO.search(a["caminho"]):
            notas.append("exemplo de ambiente mudou: %s (conteúdo não lido): confira que só há "
                         "nomes, sem valor, e que cada variável nova existe em todo ambiente "
                         "antes da subida" % a["caminho"])
        elif a["status"] == "?":
            avisos.append("arquivo de ambiente fora do git e fora do .gitignore: %s (conteúdo "
                          "não lido): ignore-o antes de qualquer commit" % a["caminho"])
        else:
            avisos.append("arquivo de ambiente no diff: %s (conteúdo não lido): confira à mão "
                          "que não há segredo e se ele devia estar no git" % a["caminho"])
    em_teste = [a for a in arquivos if a["teste"] and a["status"] != "D"]
    if [a for a in codigo if a["zona"] != "implantacao"] and not em_teste:
        notas.append("código mudou e nenhum arquivo de teste mudou: pergunte o que prova a mudança")
    sem_contagem = [a for a in arquivos if a["mais"] is None and not a["ambiente"]]
    if sem_contagem:
        notas.append("%d arquivo(s) sem contagem de linhas (binário, grande ou link): abra à mão "
                     "o que importar" % len(sem_contagem))
    if base_e_head:
        notas.append("a base é o próprio HEAD: só entra o que não foi commitado; para rever "
                     "commits já feitos, passe --base <commit anterior à mudança>")
    return avisos, notas


def imprimir(base, como, origem, arquivos, zonas, mapa, avisos, notas):
    def numero(valor, sinal):
        return "%6s" % ("?" if valor is None else "%s%d" % (sinal, valor))

    mais = sum(a["mais"] or 0 for a in arquivos)
    menos = sum(a["menos"] or 0 for a in arquivos)
    fora = sum(1 for a in arquivos if a["status"] == "?")
    print("base: %s (%s)" % (base[:12], como))
    print("zonas: %s" % origem)
    print("mudança: %d arquivo(s), +%d -%d linhas, %d ainda fora do git" % (len(arquivos), mais, menos, fora))
    print("legenda: A novo, M alterado, D removido, R renomeado, ? fora do git; '?' no lugar "
          "do número = linhas não contadas")
    motivos = {}
    for nome in [z[0] for z in zonas] + ["outros"]:
        grupo = sorted((a for a in arquivos if a["zona"] == nome),
                       key=lambda a: (-((a["mais"] or 0) + (a["menos"] or 0)), a["caminho"]))
        if not grupo:
            continue
        lentes = mapa.get(nome, [])
        print("\nzona %s: %d arquivo(s), +%d -%d; lentes: %s" % (
            nome, len(grupo), sum(a["mais"] or 0 for a in grupo),
            sum(a["menos"] or 0 for a in grupo), ", ".join(lentes) or "nenhuma"))
        for a in grupo:
            marcas = []
            if a["antigo"]:
                marcas.append("era %s" % a["antigo"])
            if a["ambiente"]:
                marcas.append("ambiente: conteúdo não lido")
            if a["teste"] and nome != "testes":
                marcas.append("teste")
            print("  %s %s %s  %s%s" % (a["status"], numero(a["mais"], "+"), numero(a["menos"], "-"),
                                        a["caminho"], "  [%s]" % "; ".join(marcas) if marcas else ""))
        for lente in lentes:
            if lente != "testes":
                motivos.setdefault(lente, []).append("zona %s (%d)" % (nome, len(grupo)))
    em_teste = sum(1 for a in arquivos if a["teste"] and a["status"] != "D")
    if em_teste:
        motivos.setdefault("testes", []).append("%d arquivo(s) de teste novo(s) ou alterado(s)" % em_teste)
    print("\nlentes pedidas:")
    ordem = ORDEM_DAS_LENTES + sorted(l for l in motivos if l not in ORDEM_DAS_LENTES)
    for lente in [l for l in ordem if l in motivos]:
        print("  %s: %s" % (lente, ", ".join(motivos[lente])))
    if not motivos:
        print("  nenhuma: só documentação mudou; leia a diferença uma vez")
    for texto in avisos:
        print("aviso: %s" % texto)
    for texto in notas:
        print("nota: %s" % texto)


def main(argv=None):
    leitor = argparse.ArgumentParser(
        prog="escopo.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    leitor.add_argument("projeto", nargs="?", default=".", help="pasta do repositório (padrão: .)")
    leitor.add_argument("--base", help="ramo, tag ou commit de comparação (padrão: ver acima)")
    leitor.add_argument("--zona", action="append", default=[], metavar="NOME=PADRÕES",
                        help="declara ou substitui uma zona; pode repetir")
    leitor.add_argument("--lente", action="append", default=[], metavar="NOME=LENTES",
                        help="lentes de uma zona; pode repetir")
    leitor.add_argument("--config", metavar="ARQUIVO", help="arquivo com [zonas] e [lentes]")
    leitor.add_argument("--max-linhas", type=int, default=800,
                        help="linhas mudadas que cabem em uma revisão (padrão: 800)")
    leitor.add_argument("--max-arquivos", type=int, default=40,
                        help="arquivos que cabem em uma revisão (padrão: 40)")
    args = leitor.parse_args(argv)
    try:
        raiz = git(args.projeto, "rev-parse", "--show-toplevel").strip()
        if not commit_de(raiz, "HEAD"):
            raise Falha("o repositório ainda não tem commit")
        zonas, mapa, origem = montar_zonas(args, raiz)
        base, como = escolher_base(raiz, args.base)
        arquivos = mudancas(raiz, base, zonas)
    except Falha as erro:
        print("erro: %s" % erro, file=sys.stderr)
        return 2
    if not arquivos:
        print("base: %s (%s)" % (base[:12], como))
        print("nada mudou em relação à base: nada a revisar")
        return 3
    avisos, notas = avisar(arquivos, base == commit_de(raiz, "HEAD"), args)
    imprimir(base, como, origem, arquivos, zonas, mapa, avisos, notas)
    return 1 if avisos else 0


if __name__ == "__main__":
    sys.exit(main())
