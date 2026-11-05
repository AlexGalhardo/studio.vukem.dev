#!/usr/bin/env python3
"""Confere uma pasta de migrations SQL. Só lê os arquivos e o histórico do git.

Acusa:
  1. migration alterada, apagada ou renomeada depois do commit em que entrou. Com
     --base <ref>, a conta muda: só o que existe em <ref> conta como já aplicado, e
     o que entrou depois dele ainda pode ser editado;
  2. comando destrutivo: drop table, drop column, truncate, delete sem where;
  3. valor de enum criado (alter type ... add value) e citado no mesmo arquivo;
  4. função redefinida sem "security definer" ou sem "set search_path" quando a
     definição anterior, em migration mais antiga, tinha;
  5. versão repetida, ou versão nova menor que uma que entrou antes.

É leitura por texto: não interpreta SQL, não conecta em banco, não usa rede e não
sabe o que está aplicado em ambiente nenhum. Não achar não prova que não há.
"""
import argparse
import os
import re
import subprocess
import sys

LIMITES = """saída:
  0  nada acusado e tudo conferido
  1  há linha "acusa:"
  2  uso errado (pasta que não existe, ref que o git não conhece)
  3  nada acusado, mas algo não foi conferido (linha "não conferi:")

limites, para ler antes de confiar:
  - Lê arquivos .sql da pasta e das subpastas; "down.sql" e "*.down.sql" ficam de
    fora. Migration escrita em outra linguagem não é lida.
  - A versão é o número no começo do nome do arquivo ou da subpasta (ou V1.2__ no
    formato do Flyway).
  - Função com o mesmo nome e argumentos diferentes é tratada como uma só.
  - SQL montado em texto (execute '...') e apóstrofo solto dentro de $$...$$ escapam.
  - Destrutivo de propósito: escreva no cabeçalho do arquivo um comentário com
    "destrutivo-de-proposito: <quem autorizou e por quê>" e a linha vira aviso.
  - Sem --base, não sabe o que já foi aplicado: acusa toda alteração posterior ao
    commit de entrada, e não vê renomeação antiga feita com o conteúdo igual.
"""

MARCA = "destrutivo-de-proposito:"
TETO_DE_BYTES = 2_000_000
FORMA_FLYWAY = re.compile(r"^[vV](\d+(?:[._]\d+)*)__")
FORMA_COMUM = re.compile(r"^(\d+)")
DESTRUTIVOS = (
    ("drop table", re.compile(r"\bdrop\s+table\b")),
    ("drop column", re.compile(r"\bdrop\s+column\b")),
    ("truncate", re.compile(r"(?:\A|;|\bbegin|\bthen|\belse|\bloop)\s*truncate\b")),
)
ALTER_TABLE = re.compile(r"\balter\s+table\b[^;]*")
DROP_SEM_COLUMN = re.compile(
    r"\bdrop\s+(?!column\b|constraint\b|default\b|not\s+null\b|identity\b|expression\b"
    r"|index\b|primary\b|foreign\b|key\b|check\b)\w"
)
DELETE = re.compile(r"\bdelete\s+from\b[^;]*")
NOVO_VALOR = re.compile(
    r"\balter\s+type\s+[\w.\"]+\s+add\s+value\s+(?:if\s+not\s+exists\s+)?'((?:[^']|'')*)'[^;]*",
    re.I,
)
FUNCAO = re.compile(
    r"\b(?:create\s+(or\s+replace\s+)?|(alter)\s+|(drop)\s+)function\s+(?:if\s+exists\s+)?([\w.\"]+)",
    re.I,
)
DOLAR = re.compile(r"\$(?:[A-Za-z_]\w*)?\$")
DEFINER = re.compile(r"\bsecurity\s+definer\b", re.I)
INVOKER = re.compile(r"\bsecurity\s+invoker\b", re.I)
CAMINHO = re.compile(r"\bset\s+search_path\b", re.I)
SEM_CAMINHO = re.compile(r"\breset\s+(?:search_path|all)\b", re.I)


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


def git(pasta, *argumentos, entrada=None):
    # A saída do git como texto; None se não há git, se a pasta não é repositório ou se falhou.
    comando = ["git", "-C", pasta, "-c", "core.quotepath=off"] + list(argumentos)
    try:
        feito = subprocess.run(comando, input=entrada, capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return feito.stdout.decode("utf-8", "replace") if feito.returncode == 0 else None


def e_migration(caminho):
    nome = caminho.lower().rsplit("/", 1)[-1]
    return nome.endswith(".sql") and nome != "down.sql" and not nome.endswith(".down.sql")


def listar(pasta):
    achados = []
    for raiz, subpastas, arquivos in os.walk(pasta):
        subpastas[:] = sorted(s for s in subpastas if not s.startswith("."))
        for nome in arquivos:
            caminho = os.path.relpath(os.path.join(raiz, nome), pasta).replace(os.sep, "/")
            if e_migration(caminho):
                achados.append(caminho)
    return sorted(achados)


def versao(caminho):
    primeiro = caminho.split("/")[0]
    achado = FORMA_FLYWAY.match(primeiro)
    if achado:
        return tuple(int(parte) for parte in re.split(r"[._]", achado.group(1)))
    achado = FORMA_COMUM.match(primeiro)
    return (int(achado.group(1)),) if achado else None


def escrita(numeros):
    return ".".join(str(n) for n in numeros)


def ler(pasta, caminho):
    completo = os.path.join(pasta, caminho)
    try:
        if os.path.getsize(completo) > TETO_DE_BYTES:
            return None
        with open(completo, "rb") as arquivo:
            return arquivo.read().decode("utf-8", "replace")
    except OSError:
        return None


def limpar(texto, apagar_textos):
    # Troca comentário (e, se pedido, o miolo de '...') por espaços. As quebras de linha ficam.
    saida, i, fim = [], 0, len(texto)
    while i < fim:
        if texto.startswith("--", i):
            j = texto.find("\n", i)
            j = fim if j < 0 else j
            saida.append(" " * (j - i))
        elif texto.startswith("/*", i):
            j = texto.find("*/", i + 2)
            j = fim if j < 0 else j + 2
            saida.append(re.sub(r"[^\n]", " ", texto[i:j]))
        elif texto[i] == "'":
            j = i + 1
            while j < fim and (texto[j] != "'" or texto.startswith("''", j)):
                j += 2 if texto[j] == "'" else 1
            j = min(j + 1, fim)
            miolo = texto[i + 1:j - 1]
            saida.append("'" + (re.sub(r"[^\n]", " ", miolo) if apagar_textos else miolo) + "'")
        else:
            j = i + 1
            saida.append(texto[i])
        i = j
    return "".join(saida)


def linha_de(texto, posicao):
    return texto.count("\n", 0, posicao) + 1


def conferir_historico(relato, pasta, arquivos, base):
    # Devolve (aplicados, ordem de entrada) para as conferências seguintes; None sem git.
    if git(pasta, "rev-parse", "--is-inside-work-tree") is None:
        relato.linha("não conferi", "a pasta não está num repositório git (ou não há git): "
                     "não sei que migration mudou depois de entrar")
        return set(), None
    antes = relato.contagem["acusa"]
    if base:
        arvore = git(pasta, "ls-tree", "-r", base, "--", ".") or ""
        na_base = {}
        for registro in arvore.splitlines():
            dados, _, caminho = registro.partition("\t")
            if e_migration(caminho):
                na_base[caminho] = dados.split()[2]
        vivos = [c for c in sorted(na_base) if os.path.isfile(os.path.join(pasta, c))]
        # Caminho absoluto: o hash-object lê os da entrada a partir da raiz do repositório.
        inteiros = "\n".join(os.path.abspath(os.path.join(pasta, c)) for c in vivos)
        somas = (git(pasta, "hash-object", "--stdin-paths", entrada=inteiros.encode("utf-8"))
                 or "").split()
        if not na_base or len(somas) != len(vivos):
            relato.linha("não conferi", "%s não tem migration nesta pasta, ou o git não deu a soma "
                         "dos arquivos: não comparei com ele" % base)
            return set(), None
        agora = dict(zip(vivos, somas))
        for caminho in sorted(na_base):
            if caminho not in agora:
                relato.linha("acusa", "%s: existe em %s e foi apagada ou renomeada" % (caminho, base))
            elif agora[caminho] != na_base[caminho]:
                relato.linha("acusa", "%s: difere de %s; já aplicada não se edita: "
                             "escreva uma migration nova" % (caminho, base))
        if relato.contagem["acusa"] == antes:
            relato.linha("ok", "%d migrations de %s estão iguais; %d entraram depois dele"
                         % (len(na_base), base, len([c for c in arquivos if c not in na_base])))
        return set(na_base), [sorted(na_base), sorted(c for c in arquivos if c not in na_base)]
    registro = git(pasta, "log", "--reverse", "--no-renames", "--format=%x01%h",
                   "--name-status", "--relative", "--", ".")
    if not registro:
        relato.linha("não conferi", "nenhuma migration desta pasta está em commit: "
                     "não há histórico para comparar")
        return set(), None
    entrada, ordem, commit = {}, [], ""
    for linha in registro.splitlines():
        if linha.startswith("\x01"):
            commit = linha[1:]
            ordem.append([])
            continue
        letra, _, caminho = linha.partition("\t")
        if not caminho or not e_migration(caminho):
            continue
        if caminho not in entrada:
            entrada[caminho] = commit
            ordem[-1].append(caminho)
        elif letra == "M":
            relato.linha("acusa", "%s: alterada no commit %s, depois do commit %s em que entrou"
                         % (caminho, commit, entrada[caminho]))
        elif letra == "D":
            relato.linha("acusa", "%s: apagada ou renomeada no commit %s" % (caminho, commit))
    pendente = git(pasta, "diff", "--no-renames", "--name-status", "--relative", "HEAD", "--", ".")
    for linha in (pendente or "").splitlines():
        letra, _, caminho = linha.partition("\t")
        if caminho in entrada and letra in ("M", "D"):
            relato.linha("acusa", "%s: %s sem commit, depois do commit %s em que entrou"
                         % (caminho, "alterada" if letra == "M" else "apagada", entrada[caminho]))
    novas = sorted(c for c in arquivos if c not in entrada)
    if relato.contagem["acusa"] == antes:
        relato.linha("ok", "nenhuma das %d migrations em commit mudou depois de entrar; "
                     "%d ainda sem commit" % (len(entrada), len(novas)))
    else:
        relato.linha("aviso", "se a migration alterada ainda não foi aplicada fora desta máquina, "
                     "diga o que já foi com --base <ref>")
    return set(), [grupo for grupo in ordem if grupo] + [novas]


def conferir_versoes(relato, arquivos, ordem):
    antes = relato.contagem["acusa"] + relato.contagem["aviso"]
    grupos = {}
    for caminho in arquivos:
        if versao(caminho) is None:
            relato.linha("aviso", "%s: nome sem versão no começo; não dá para ler a ordem" % caminho)
        else:
            grupos.setdefault(versao(caminho), []).append(caminho)
    for numeros, lista in sorted(grupos.items()):
        if len({caminho.split("/")[0] for caminho in lista}) > 1:
            relato.linha("acusa", "versão %s repetida: %s" % (escrita(numeros), ", ".join(lista)))
    maior, dona = None, ""
    for grupo in ordem or []:
        com_versao = [c for c in grupo if c in arquivos and versao(c) is not None]
        for caminho in com_versao:
            if maior is not None and versao(caminho) < maior:
                relato.linha("acusa", "%s: versão menor que a de %s, que entrou antes; a ferramenta "
                             "pode pular este arquivo ou aplicar fora de ordem" % (caminho, dona))
        for caminho in com_versao:
            if maior is None or versao(caminho) > maior:
                maior, dona = versao(caminho), caminho
    numeradas = [c for c in arquivos if versao(c) is not None]
    por_numero = sorted(numeradas, key=lambda c: (versao(c), c))
    for por_nome, certo in zip(sorted(numeradas), por_numero):
        if por_nome != certo:
            relato.linha("aviso", "a ordem por nome difere da ordem numérica a partir de %s; "
                         "ferramenta que ordena por texto aplica fora de ordem" % certo)
            break
    if relato.contagem["acusa"] + relato.contagem["aviso"] == antes:
        relato.linha("ok", "%d versões sem repetição e em ordem" % len(grupos))
    return por_numero + sorted(c for c in arquivos if versao(c) is None)


def conferir_destrutivos(relato, caminho, bruto, aplicada):
    codigo = limpar(bruto, True).lower()
    achados = [(m.end() - 1, nome) for nome, forma in DESTRUTIVOS for m in forma.finditer(codigo)]
    for comando in ALTER_TABLE.finditer(codigo):
        achados += [(comando.start() + m.start(), "drop de coluna sem a palavra column")
                    for m in DROP_SEM_COLUMN.finditer(comando.group(0))]
    achados += [(m.start(), "delete sem where") for m in DELETE.finditer(codigo)
                if not re.search(r"\bwhere\b", m.group(0))]
    tipo, sufixo = "acusa", ""
    if MARCA in bruto.lower():
        tipo, sufixo = "aviso", " (marcado como de propósito)"
    elif aplicada:
        tipo, sufixo = "aviso", " (já aplicada: não há o que editar)"
    for posicao, nome in sorted(achados):
        relato.linha(tipo, "%s:%d: %s%s" % (caminho, linha_de(codigo, posicao), nome, sufixo))
    return len(achados)


def conferir_enum(relato, caminho, bruto):
    codigo = limpar(bruto, False)
    criados = list(NOVO_VALOR.finditer(codigo))
    resto = codigo
    for achado in criados:   # o próprio comando que cria não conta como uso
        resto = resto[:achado.start()] + " " * len(achado.group(0)) + resto[achado.end():]
    total = 0
    for achado in criados:
        uso = resto.find("'%s'" % achado.group(1))
        if uso >= 0:
            total += 1
            relato.linha("acusa", "%s:%d: valor de enum '%s' criado na linha %d e citado no mesmo "
                         "arquivo; o uso vai na migration seguinte" % (
                             caminho, linha_de(resto, uso), achado.group(1),
                             linha_de(codigo, achado.start())))
    return total


def cabecalho(codigo, inicio):
    # O comando de `inicio` até o ';' que o fecha, sem o corpo entre $marca$. Devolve (texto, fim).
    partes, i = [], inicio
    while i < len(codigo) and codigo[i] != ";":
        marca = DOLAR.match(codigo, i) if codigo[i] == "$" else None
        if marca:
            fecho = codigo.find(marca.group(0), marca.end())
            i = len(codigo) if fecho < 0 else fecho + len(marca.group(0))
            partes.append(" ")
        else:
            partes.append(codigo[i])
            i += 1
    return "".join(partes), i


def conferir_funcoes(relato, caminho, bruto, estado, apagadas):
    # estado: nome -> [tem security definer, tem search_path, arquivo da definição]
    codigo = limpar(bruto, True)
    anterior = {nome: list(valor) for nome, valor in estado.items()}
    redefinidas, livre = [], 0
    for achado in FUNCAO.finditer(codigo):
        if achado.start() < livre:   # está dentro do corpo de outra função
            continue
        nome = achado.group(4).replace('"', "").lower()
        nome = nome[7:] if nome.startswith("public.") else nome
        texto, livre = cabecalho(codigo, achado.end())
        if achado.group(3):
            apagadas.add(nome)
        elif achado.group(2):
            if nome in estado:
                atual = estado[nome]
                atual[0] = (atual[0] or bool(DEFINER.search(texto))) and not INVOKER.search(texto)
                atual[1] = (atual[1] or bool(CAMINHO.search(texto))) and not SEM_CAMINHO.search(texto)
        else:
            if nome in anterior and (achado.group(1) or nome in apagadas):
                redefinidas.append((nome, linha_de(codigo, achado.start())))
            apagadas.discard(nome)
            estado[nome] = [bool(DEFINER.search(texto)), bool(CAMINHO.search(texto)), caminho]
    total = 0
    for nome, linha in redefinidas:
        faltou = [rotulo for indice, rotulo in ((0, "security definer"), (1, "set search_path"))
                  if anterior[nome][indice] and not estado[nome][indice]]
        if faltou:
            total += 1
            relato.linha("acusa", "%s:%d: função %s redefinida sem %s, que a definição de %s tinha"
                         % (caminho, linha, nome, " nem ".join(faltou), anterior[nome][2]))
    return total


def main():
    leitor = argparse.ArgumentParser(
        description=__doc__, epilog=LIMITES, formatter_class=argparse.RawDescriptionHelpFormatter)
    leitor.add_argument("pasta", help="a pasta de migrations do projeto")
    leitor.add_argument("--base", metavar="REF", help="ref do git que corresponde ao que já foi "
                        "aplicado fora desta máquina: o ramo que implanta, uma tag, um commit")
    opcoes = leitor.parse_args()
    pasta = opcoes.pasta
    if not os.path.isdir(pasta):
        print("erro: %s não é uma pasta" % pasta, file=sys.stderr)
        return 2
    if opcoes.base and git(pasta, "rev-parse", "--is-inside-work-tree") is not None \
            and git(pasta, "rev-parse", "--verify", "--quiet", opcoes.base + "^{commit}") is None:
        print("erro: o git não conhece o ref %s" % opcoes.base, file=sys.stderr)
        return 2
    relato = Relato()
    arquivos = listar(pasta)
    if not arquivos:
        relato.linha("não conferi", "nenhum arquivo .sql em %s" % pasta)
        return relato.codigo()
    aplicadas, ordem = conferir_historico(relato, pasta, arquivos, opcoes.base)
    em_ordem = conferir_versoes(relato, arquivos, ordem)
    estado, apagadas, achados = {}, set(), [0, 0, 0]
    for caminho in em_ordem:
        bruto = ler(pasta, caminho)
        if bruto is None:
            relato.linha("não conferi", "%s: não consegui ler, ou passa de 2 MB" % caminho)
            continue
        achados[0] += conferir_destrutivos(relato, caminho, bruto, caminho in aplicadas)
        achados[1] += conferir_enum(relato, caminho, bruto)
        achados[2] += conferir_funcoes(relato, caminho, bruto, estado, apagadas)
    for total, texto in zip(achados, (
            "nenhum comando destrutivo", "nenhum valor de enum criado e citado no mesmo arquivo",
            "nenhuma função redefinida perdeu security definer ou search_path")):
        if not total:
            relato.linha("ok", "%s em %d arquivos" % (texto, len(em_ordem)))
    print("resumo: %d acusa, %d aviso, %d não conferi. Leitura por texto: não interpreta SQL "
          "nem toca em banco." % (relato.contagem["acusa"], relato.contagem["aviso"],
                                  relato.contagem["não conferi"]))
    return relato.codigo()


if __name__ == "__main__":
    sys.exit(main())
