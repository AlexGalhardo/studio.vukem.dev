#!/usr/bin/env python3
"""Conferidor da skill app-com-supabase. Só lê as migrations e o código; não altera nada.

Acusa:
  1. tabela criada sem "enable row level security";
  2. tabela sem "revoke all" de anon e de authenticated antes de conceder;
  3. função "security definer" sem "set search_path";
  4. a chave secreta lida do ambiente fora do módulo de --modulo, e variável com prefixo
     público e nome de segredo.

Sem rede. Não abre arquivos .env e não imprime o conteúdo de nenhuma linha: só arquivo, número
da linha e nome de tabela, função ou variável.

Saída: 0 limpo; 1 acusou; 2 uso errado; 3 nada acusado, mas algo não foi conferido.
"""
import argparse
import os
import re
import sys

PAPEIS = ("anon", "authenticated")
VARIAVEIS_PADRAO = ["SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
EXTENSOES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}
PASTAS_FORA = {"node_modules", "dist", "build", "out", "coverage", "vendor", "playwright-report",
               "test-results"}
PREFIXO_PUBLICO = re.compile(
    r"\b(?:NEXT_PUBLIC|NUXT_PUBLIC|EXPO_PUBLIC|VITE|PUBLIC|REACT_APP|GATSBY)_[A-Z0-9_]*"
    r"(?:SECRET|SERVICE_ROLE)[A-Z0-9_]*\b")
EH_TESTE = re.compile(r"(\.(test|spec)\.[a-z]+$)|((^|/)(tests?|__tests__|e2e)/)")
CIFRAO = re.compile(r"\$[A-Za-z_]*\$")
NAO_E_TABELA = re.compile(
    r"^(function|procedure|routine|sequence|schema|database|type|domain|language|foreign|large|"
    r"tablespace|parameter|all\s+(functions|sequences|routines|procedures))\b")


def limpar_sql(texto):
    """Troca por espaços os comentários e o miolo de textos e de corpos entre cifrões."""
    saida = list(texto)
    fim = len(texto)

    def apagar(de, ate):
        for k in range(de, min(ate, fim)):
            if saida[k] != "\n":
                saida[k] = " "

    i = 0
    while i < fim:
        if texto.startswith("--", i):
            j = texto.find("\n", i)
            j = fim if j < 0 else j
            apagar(i, j)
            i = j
        elif texto.startswith("/*", i):
            nivel, j = 1, i + 2
            while j < fim and nivel:
                if texto.startswith("/*", j):
                    nivel, j = nivel + 1, j + 2
                elif texto.startswith("*/", j):
                    nivel, j = nivel - 1, j + 2
                else:
                    j += 1
            apagar(i, j)
            i = j
        elif texto[i] == "'":
            j = i + 1
            while j < fim:
                if texto[j] == "'":
                    if texto.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            apagar(i + 1, j)
            i = j + 1
        elif texto[i] == "$":
            marca = CIFRAO.match(texto, i)
            if not marca:
                i += 1
                continue
            j = texto.find(marca.group(0), marca.end())
            j = fim if j < 0 else j
            apagar(marca.end(), j)
            i = j + len(marca.group(0))
        elif texto[i] == '"':
            j = texto.find('"', i + 1)
            i = fim if j < 0 else j + 1
        else:
            i += 1
    return "".join(saida)


def nome_de(ident, esquema):
    partes = [p.strip().strip('"').lower() for p in ident.strip().split(".")]
    return (esquema, partes[0]) if len(partes) == 1 else (partes[-2], partes[-1])


def lista(texto, corte):
    texto = re.split(corte, texto, maxsplit=1, flags=re.I)[0]
    return [p.strip().strip('"').lower() for p in texto.split(",") if p.strip()]


class Banco:
    """Estado das tabelas e das funções, comando a comando, na ordem dos arquivos."""

    def __init__(self, esquema):
        self.esquema = esquema
        self.tabelas = {}
        self.funcoes = {}
        self.padrao_alterado = False

    def alvos(self, objeto):
        objeto = re.sub(r"^table\s+", "", objeto.strip(), flags=re.I)
        geral = re.match(r"all\s+tables\s+in\s+schema\s+([\w\"]+)", objeto, re.I)
        if geral:
            esquema = geral.group(1).strip('"').lower()
            return [chave for chave in self.tabelas if chave[0] == esquema]
        if NAO_E_TABELA.match(objeto.lower()):
            return []
        return [nome_de(p, self.esquema) for p in objeto.split(",") if p.strip()]

    def comando(self, sql, onde):
        s = " ".join(sql.split())
        baixo = s.lower()
        m = re.match(r"create (?:(?:global |local )?(temp|temporary) |unlogged )?table "
                     r"(?:if not exists )?([\w.\"]+)", baixo)
        if m:
            if not m.group(1):
                self.tabelas.setdefault(nome_de(m.group(2), self.esquema), {
                    "onde": onde, "rls": False, "revogou": set(), "cedo": set()})
            return
        m = re.match(r"alter table (?:if exists )?(?:only )?([\w.\"]+) (.*)$", baixo)
        if m:
            chave = nome_de(m.group(1), self.esquema)
            tabela = self.tabelas.get(chave)
            if tabela is None:
                return
            if re.search(r"\benable row level security\b", m.group(2)):
                tabela["rls"] = True
            if re.search(r"\bdisable row level security\b", m.group(2)):
                tabela["rls"] = False
            novo = re.search(r"\brename to ([\w\"]+)", m.group(2))
            if novo:
                self.tabelas[(chave[0], novo.group(1).strip('"'))] = self.tabelas.pop(chave)
            return
        m = re.match(r"drop table (?:if exists )?(.+)$", baixo)
        if m:
            for parte in lista(m.group(1), r"\s+(cascade|restrict)\b"):
                self.tabelas.pop(nome_de(parte, self.esquema), None)
            return
        if baixo.startswith("alter default privileges"):
            self.padrao_alterado = True
            return
        m = re.match(r"revoke (.+?) on (.+?) from (.+)$", baixo)
        if m and m.group(1) in ("all", "all privileges"):
            papeis = lista(m.group(3), r"\s+(cascade|restrict|granted by)\b")
            for chave in self.alvos(m.group(2)):
                if chave in self.tabelas:
                    self.tabelas[chave]["revogou"].update(p for p in papeis if p in PAPEIS)
            return
        m = re.match(r"grant (.+?) on (.+?) to (.+)$", baixo)
        if m:
            papeis = lista(m.group(3), r"\s+(with grant option|granted by)\b")
            for chave in self.alvos(m.group(2)):
                tabela = self.tabelas.get(chave)
                if tabela is not None:
                    tabela["cedo"].update(
                        p for p in papeis if p in PAPEIS and p not in tabela["revogou"])
            return
        m = re.match(r"create (?:or replace )?(?:function|procedure) ([\w.\"]+)", baixo)
        if m:
            caminho = re.search(r"\bset search_path\s*(?:=|to)\s*(''|\S+)", baixo)
            self.funcoes[nome_de(m.group(1), self.esquema)] = {
                "onde": onde, "definer": bool(re.search(r"\bsecurity definer\b", baixo)),
                "caminho": caminho.group(1) if caminho else None}
            return
        m = re.match(r"alter (?:function|procedure|routine) ([\w.\"]+).*?\bset search_path\s*"
                     r"(?:=|to)\s*(''|\S+)", baixo)
        if m and nome_de(m.group(1), self.esquema) in self.funcoes:
            self.funcoes[nome_de(m.group(1), self.esquema)]["caminho"] = m.group(2)
            return
        m = re.match(r"drop (?:function|procedure|routine) (?:if exists )?([\w.\"]+)", baixo)
        if m:
            self.funcoes.pop(nome_de(m.group(1), self.esquema), None)


def ler_migrations(pasta, raiz, esquema):
    banco = Banco(esquema)
    arquivos = sorted(n for n in os.listdir(pasta) if n.endswith(".sql"))
    for nome in arquivos:
        caminho = os.path.join(pasta, nome)
        with open(caminho, encoding="utf-8", errors="replace") as arquivo:
            limpo = limpar_sql(arquivo.read())
        relativo = os.path.relpath(caminho, raiz)
        inicio = 0
        for trecho in limpo.split(";"):
            corpo = trecho.lstrip()
            if corpo:
                posicao = inicio + len(trecho) - len(corpo)
                linha = limpo.count("\n", 0, posicao) + 1
                banco.comando(corpo, "%s:%d" % (relativo, linha))
            inicio += len(trecho) + 1
    return banco, len(arquivos)


def ler_codigo(raiz, variaveis):
    """Devolve (leituras do ambiente, citações, prefixos públicos), cada item com arquivo e linha."""
    nomes = "|".join(re.escape(v) for v in variaveis)
    leitura = re.compile(
        r"(?:process\.env|import\.meta\.env|Bun\.env)\s*(?:\.\s*|\[\s*[\"'])(%s)\b"
        r"|env\.get\(\s*[\"'](%s)[\"']"
        r"|\{[^{}]*\b(%s)\b[^{}]*\}\s*=\s*(?:process\.env|import\.meta\.env)" % (nomes, nomes, nomes))
    citacao = re.compile(r"(?<![A-Za-z0-9_])(%s)(?![A-Za-z0-9_])" % nomes)
    leituras, citacoes, publicos = [], set(), []
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = sorted(d for d in subpastas if d not in PASTAS_FORA and not d.startswith("."))
        for nome in sorted(arquivos):
            if nome.startswith(".env") or os.path.splitext(nome)[1] not in EXTENSOES:
                continue
            caminho = os.path.join(pasta, nome)
            try:
                if os.path.getsize(caminho) > 2000000:
                    continue
                with open(caminho, encoding="utf-8", errors="replace") as arquivo:
                    texto = arquivo.read()
            except OSError:
                continue
            relativo = os.path.relpath(caminho, raiz).replace(os.sep, "/")
            for m in leitura.finditer(texto):
                variavel = m.group(1) or m.group(2) or m.group(3)
                leituras.append((relativo, texto.count("\n", 0, m.start()) + 1, variavel))
            if citacao.search(texto):
                citacoes.add(relativo)
            for m in PREFIXO_PUBLICO.finditer(texto):
                publicos.append((relativo, texto.count("\n", 0, m.start()) + 1, m.group(0)))
    return leituras, citacoes, publicos


def main():
    analisador = argparse.ArgumentParser(
        prog="conferir.py",
        description="Lê as migrations e o código de um projeto com Supabase e acusa tabela sem "
                    "RLS, tabela sem revoke antes de conceder, função security definer sem "
                    "search_path e a chave secreta lida fora do módulo indicado. Só lê.",
        epilog="Saída: 0 limpo; 1 acusou; 2 uso errado; 3 nada acusado, mas algo não foi "
               "conferido. Lê texto: não segue imports, não consulta o banco, não abre .env.")
    analisador.add_argument("projeto", help="raiz do projeto")
    analisador.add_argument("--migrations", default="supabase/migrations", metavar="PASTA",
                            help="pasta das migrations, relativa ao projeto (padrão: %(default)s)")
    analisador.add_argument("--esquema", default="public",
                            help="esquema das tabelas sem prefixo (padrão: %(default)s)")
    analisador.add_argument("--modulo", action="append", default=[], metavar="ARQUIVO",
                            help="arquivo que pode ler a chave secreta do ambiente; repita para "
                                 "cada leitor legítimo (ferramenta de carga, por exemplo)")
    analisador.add_argument("--variavel", action="append", default=[], metavar="NOME",
                            help="nome da variável da chave secreta; repita se houver mais de um "
                                 "(padrão: %s)" % ", ".join(VARIAVEIS_PADRAO))
    args = analisador.parse_args()

    raiz = os.path.abspath(args.projeto)
    if not os.path.isdir(raiz):
        analisador.error("projeto não encontrado: %s" % args.projeto)
    modulos = set()
    for modulo in args.modulo:
        caminho = modulo if os.path.isabs(modulo) else os.path.join(raiz, modulo)
        if not os.path.isfile(caminho):
            analisador.error("--modulo não é um arquivo do projeto: %s" % modulo)
        modulos.add(os.path.relpath(caminho, raiz).replace(os.sep, "/"))
    variaveis = args.variavel or VARIAVEIS_PADRAO
    for variavel in variaveis:
        if not re.match(r"^[A-Z][A-Z0-9_]{1,63}$", variavel):
            analisador.error("--variavel é um nome de variável em maiúsculas, nunca o valor")

    acusa, aviso, ok, falta = [], [], [], []

    pasta = os.path.join(raiz, args.migrations)
    if not os.path.isdir(pasta):
        falta.append("migrations: a pasta %s não existe (passe --migrations)" % args.migrations)
    else:
        banco, quantos = ler_migrations(pasta, raiz, args.esquema)
        print("migrations: %d arquivos em %s" % (quantos, args.migrations))
        if banco.padrao_alterado:
            falta.append("privilégios: há \"alter default privileges\" nas migrations; confira "
                         "no banco com o que uma tabela nova nasce")
        limpas = 0
        for (esquema, tabela), dados in sorted(banco.tabelas.items()):
            if esquema != args.esquema:
                continue
            rotulo = "%s tabela %s.%s" % (dados["onde"], esquema, tabela)
            problemas = len(acusa)
            if not dados["rls"]:
                acusa.append("%s sem \"enable row level security\"" % rotulo)
            sem = [p for p in PAPEIS if p not in dados["revogou"]]
            if sem:
                frase = "%s sem \"revoke all\" de %s: nasce com todos os privilégios" % (
                    rotulo, " e ".join(sem))
                (aviso if banco.padrao_alterado else acusa).append(frase)
            desfeito = sorted(dados["cedo"] & dados["revogou"])
            if desfeito:
                aviso.append("%s concede a %s antes do \"revoke all\": a concessão foi desfeita" % (
                    rotulo, " e ".join(desfeito)))
            limpas += len(acusa) == problemas
        ok.append("%d de %d tabelas de %s com RLS ligada e revoke antes de conceder" % (
            limpas, sum(1 for chave in banco.tabelas if chave[0] == args.esquema), args.esquema))
        com_guarda = 0
        for (esquema, funcao), dados in sorted(banco.funcoes.items()):
            if not dados["definer"]:
                continue
            rotulo = "%s função %s.%s" % (dados["onde"], esquema, funcao)
            if dados["caminho"] is None:
                acusa.append("%s é security definer e não define search_path" % rotulo)
                continue
            com_guarda += 1
            if dados["caminho"] not in ("''", '""'):
                aviso.append("%s define search_path com esquema: prefira vazio (set search_path "
                             "= '') e escreva todo objeto com o esquema" % rotulo)
        ok.append("%d funções security definer com search_path definido" % com_guarda)

    leituras, citacoes, publicos = ler_codigo(raiz, variaveis)
    for arquivo, linha, variavel in publicos:
        acusa.append("%s:%d variável %s tem prefixo público e nome de segredo: vai para o "
                     "navegador" % (arquivo, linha, variavel))
    fora = [item for item in leituras if item[0] not in modulos]
    if not modulos:
        falta.append("chave secreta: passe --modulo com o arquivo que pode lê-la")
        for arquivo, linha, variavel in fora:
            aviso.append("%s:%d lê %s do ambiente" % (arquivo, linha, variavel))
    else:
        for arquivo, linha, variavel in fora:
            frase = "%s:%d lê %s do ambiente fora de %s" % (
                arquivo, linha, variavel, ", ".join(sorted(modulos)))
            (aviso if EH_TESTE.search(arquivo) else acusa).append(frase)
        if not any(item[0] in modulos for item in leituras):
            aviso.append("nenhum --modulo lê %s do ambiente: confira o caminho e o nome da "
                         "variável (--variavel)" % " nem ".join(variaveis))
        elif not any(not EH_TESTE.search(item[0]) for item in fora):
            ok.append("chave secreta lida do ambiente só em %s" % ", ".join(sorted(modulos)))
    outros = sorted(citacoes - modulos - {item[0] for item in leituras})
    if outros:
        aviso.append("o nome da chave secreta aparece, sem leitura do ambiente, em %d arquivos "
                     "(%s%s): confira para onde o valor é repassado" % (
                         len(outros), ", ".join(outros[:5]), ", ..." if len(outros) > 5 else ""))

    for rotulo, linhas in (("acusa", acusa), ("aviso", aviso), ("ok", ok), ("não conferi", falta)):
        for linha in linhas:
            print("%s: %s" % (rotulo, linha))
    print("resumo: %d acusações, %d avisos, %d não conferidos" % (len(acusa), len(aviso), len(falta)))
    print("limites: lê texto; não segue imports, não consulta o banco nem o projeto remoto, não "
          "entende SQL gerado por ORM. Não achar não prova que não há.")
    return 1 if acusa else 3 if falta else 0


if __name__ == "__main__":
    sys.exit(main())
