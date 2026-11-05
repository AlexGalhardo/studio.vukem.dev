#!/usr/bin/env python3
"""conferir.py: lê um projeto e acusa três erros de cobrança com Stripe.

Só lê arquivos: não altera nada, não acessa a rede e nunca imprime o valor de uma chave.

uso:
  python3 conferir.py <projeto> --tabela <tabela> --modulo <arquivo do webhook> [--rota <arquivo>]

confere:
  1. chave de produção do Stripe ou segredo de webhook em arquivo que o git rastreia
     (ou que ainda não rastreia e também não ignora);
  2. escrita na tabela de assinatura fora do módulo do webhook (pede --tabela e --modulo);
  3. rota de webhook sem conferência da assinatura do Stripe.

saída: 0 nada acusado e tudo conferido; 1 há "acusa:"; 2 uso errado;
       3 nada acusado, mas alguma conferência não rodou ("não conferi:").

limites: lê texto. Não segue imports, não entende ordem de execução, não olha o histórico do
git e não conhece a escrita de todo ORM. Não achar não prova que não há.
"""

import argparse
import os
import re
import subprocess
import sys

PASTAS_IGNORADAS = {
    ".git", "node_modules", ".next", "dist", "build", "out", "vendor", ".venv", "venv",
    "__pycache__", "coverage", ".turbo", ".vercel", "target",
}
EXTENSOES_DE_CODIGO = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".php", ".java", ".kt",
    ".cs", ".ex", ".exs", ".rs",
}
E_TESTE = re.compile(r"(^|/)(tests?|__tests__|specs?|e2e)/|\.(test|spec)\.\w+$|_test\.\w+$|(^|/)test_[^/]*$")
LIMITE_DE_BYTES = 1_000_000

# Os prefixos são montados em partes para este arquivo não acusar a si mesmo.
_S, _R, _W = "sk", "rk", "wh" + "sec"
CHAVES = [
    ("chave secreta de produção", re.compile(r"\b%s_live_[0-9A-Za-z]{16,}" % _S), "acusa"),
    ("chave restrita de produção", re.compile(r"\b%s_live_[0-9A-Za-z]{16,}" % _R), "acusa"),
    ("segredo de webhook", re.compile(r"\b%s_[0-9A-Za-z]{16,}" % _W), "acusa"),
    ("chave secreta de teste", re.compile(r"\b%s_test_[0-9A-Za-z]{16,}" % _S), "aviso"),
]

LE_CABECALHO = re.compile(r"stripe[-_]signature", re.I)
VERIFICA = re.compile(
    r"\b(constructEvent(Async)?|construct_event|ConstructEvent(WithOptions)?"
    r"|verifyHeader(Async)?|verify_header)\s*\("
)
SEM_VERIFICAR = re.compile(r"\bconstructEventWithoutVerification\s*\(")
CORPO_COMO_JSON = re.compile(r"\b(request|req)\.json\(\s*\)|\b(express|bodyParser)\.json\(")


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


def listar_pelo_git(raiz):
    # Arquivos rastreados e os ainda não rastreados que o git não ignora. None sem git.
    grupos = []
    for opcoes in (["ls-files", "-z"], ["ls-files", "-z", "--others", "--exclude-standard"]):
        try:
            saida = subprocess.run(
                ["git", "-C", raiz] + opcoes, capture_output=True, timeout=60, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if saida.returncode != 0:
            return None
        grupos.append([p for p in saida.stdout.decode("utf-8", "replace").split("\0") if p])
    return grupos[0], grupos[1]


def listar_pela_pasta(raiz):
    achados = []
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [s for s in subpastas if s not in PASTAS_IGNORADAS]
        for nome in arquivos:
            achados.append(os.path.relpath(os.path.join(pasta, nome), raiz).replace(os.sep, "/"))
    return achados


def ler(raiz, caminho):
    # O texto do arquivo, ou None se é grande demais, binário ou ilegível.
    completo = os.path.join(raiz, caminho)
    try:
        if not os.path.isfile(completo) or os.path.getsize(completo) > LIMITE_DE_BYTES:
            return None
        with open(completo, "rb") as arquivo:
            dados = arquivo.read()
    except OSError:
        return None
    if b"\0" in dados:
        return None
    return dados.decode("utf-8", "replace")


def numero_da_linha(texto, posicao):
    return texto.count("\n", 0, posicao) + 1


def conferir_chaves(relato, raiz, rastreados, nao_rastreados):
    antes = relato.contagem["acusa"] + relato.contagem["aviso"]
    for caminhos, situacao in ((rastreados, "rastreado"), (nao_rastreados, "não ignorado pelo git")):
        for caminho in caminhos:
            texto = ler(raiz, caminho)
            if texto is None:
                continue
            for nome, padrao, tipo in CHAVES:
                for achado in padrao.finditer(texto):
                    # O valor fica fora da saída de propósito
                    relato.linha(tipo, "%s:%d: %s em arquivo %s" % (
                        caminho, numero_da_linha(texto, achado.start()), nome, situacao))
    if relato.contagem["acusa"] + relato.contagem["aviso"] == antes:
        relato.linha("ok", "nenhuma chave do Stripe em %d arquivos lidos" % (
            len(rastreados) + len(nao_rastreados)))


def padroes_de_escrita(tabela):
    nome = re.escape(tabela)
    alvo = r"""(?:["`]?\w+["`]?\.)?["`]?%s["`]?(?![\w.])""" % nome
    return [
        re.compile(r"""from\(\s*["'`]%s["'`]\s*\)[\s\S]{0,200}?\.(insert|update|upsert|delete)\(""" % nome),
        re.compile(r"\binsert\s+into\s+" + alvo, re.I),
        re.compile(r"\bupdate\s+" + alvo + r"\s+set\b", re.I),
        re.compile(r"\bdelete\s+from\s+" + alvo, re.I),
    ]


def conferir_escrita(relato, fontes, tabela, modulo):
    if not tabela or not modulo:
        relato.linha("não conferi", "escrita fora do webhook: passe --tabela e --modulo")
        return
    padroes = padroes_de_escrita(tabela)
    fora, no_modulo = [], False
    for caminho, texto in fontes.items():
        for padrao in padroes:
            achado = padrao.search(texto)
            if not achado:
                continue
            if caminho == modulo:
                no_modulo = True
            else:
                fora.append((caminho, numero_da_linha(texto, achado.start())))
            break
    for caminho, linha in sorted(fora):
        relato.linha("acusa", "%s:%d: escreve em %s fora de %s" % (caminho, linha, tabela, modulo))
    if not no_modulo:
        # Sem este controle, um nome errado faria a regra passar sem olhar nada
        relato.linha("não conferi", "%s não escreve em %s por nenhuma forma que eu conheça: "
                     "confira os nomes, ou a escrita do projeto passa por um ORM" % (modulo, tabela))
    elif not fora:
        relato.linha("ok", "só %s escreve em %s" % (modulo, tabela))


def conferir_webhook(relato, fontes, rotas):
    candidatas = rotas or sorted(c for c, texto in fontes.items() if LE_CABECALHO.search(texto))
    if not candidatas:
        relato.linha("não conferi", "assinatura do webhook: não achei arquivo que leia o "
                     "cabeçalho stripe-signature; passe --rota")
        return
    for caminho, texto in sorted(fontes.items()):
        achado = SEM_VERIFICAR.search(texto)
        if achado:
            relato.linha("acusa", "%s:%d: monta o evento sem conferir a assinatura" % (
                caminho, numero_da_linha(texto, achado.start())))
    for caminho in candidatas:
        achado = CORPO_COMO_JSON.search(fontes.get(caminho, ""))
        if achado:
            relato.linha("aviso", "%s:%d: lê o corpo como JSON; a assinatura vale sobre o texto cru" % (
                caminho, numero_da_linha(fontes[caminho], achado.start())))
    onde = sorted(c for c, texto in fontes.items() if VERIFICA.search(texto))
    if onde:
        relato.linha("ok", "conferência de assinatura em %s (não sigo imports: confirme que %s "
                     "passa por ela antes de ler o evento)" % (", ".join(onde), ", ".join(candidatas)))
    else:
        relato.linha("acusa", "%s recebe o webhook e nenhum arquivo de código confere a assinatura "
                     "(constructEvent ou equivalente)" % ", ".join(candidatas))


def normalizar(raiz, caminho):
    # Caminho relativo ao projeto, com barras; None se o arquivo não existe dentro dele.
    completo = caminho if os.path.isabs(caminho) else os.path.join(raiz, caminho)
    completo = os.path.realpath(completo)
    if not os.path.isfile(completo) or not completo.startswith(raiz + os.sep):
        return None
    return os.path.relpath(completo, raiz).replace(os.sep, "/")


def main(argumentos=None):
    leitor = argparse.ArgumentParser(
        prog="conferir.py", add_help=False, formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)
    leitor.add_argument("projeto", help="raiz do projeto a ler")
    leitor.add_argument("--tabela", help="nome da tabela de assinatura")
    leitor.add_argument("--modulo", help="arquivo do webhook, o único que pode escrever nela")
    leitor.add_argument("--rota", action="append", default=[],
                        help="arquivo que recebe o webhook (repita a opção para mais de um)")
    leitor.add_argument("-h", "--help", "--ajuda", action="help", help="mostra esta ajuda e sai")
    opcoes = leitor.parse_args(argumentos)

    raiz = os.path.realpath(opcoes.projeto)
    if not os.path.isdir(raiz):
        print("uso: %s não é uma pasta" % opcoes.projeto, file=sys.stderr)
        return 2
    if bool(opcoes.tabela) != bool(opcoes.modulo):
        print("uso: --tabela e --modulo andam juntas", file=sys.stderr)
        return 2
    modulo, rotas = None, []
    for opcao, valor in [("--modulo", opcoes.modulo)] + [("--rota", r) for r in opcoes.rota]:
        if not valor:
            continue
        normal = normalizar(raiz, valor)
        if normal is None:
            print("uso: %s %s não é um arquivo do projeto" % (opcao, valor), file=sys.stderr)
            return 2
        if opcao == "--modulo":
            modulo = normal
        else:
            rotas.append(normal)

    relato = Relato()
    pelo_git = listar_pelo_git(raiz)
    if pelo_git is not None and not (pelo_git[0] or pelo_git[1]):
        pelo_git = None  # pasta inteira ignorada pelo git de fora: vale a leitura da pasta
    if pelo_git is None:
        relato.linha("aviso", "sem git nesta pasta: li todos os arquivos, menos as pastas de dependência")
        rastreados, nao_rastreados = listar_pela_pasta(raiz), []
    else:
        rastreados, nao_rastreados = pelo_git

    fontes = {}
    for caminho in rastreados + nao_rastreados:
        fixo = caminho in rotas or caminho == modulo
        if os.path.splitext(caminho)[1] not in EXTENSOES_DE_CODIGO and not fixo:
            continue
        if E_TESTE.search(caminho) and not fixo:
            continue
        texto = ler(raiz, caminho)
        if texto is not None:
            fontes[caminho] = texto

    conferir_chaves(relato, raiz, rastreados, nao_rastreados)
    conferir_escrita(relato, fontes, opcoes.tabela, modulo)
    conferir_webhook(relato, fontes, rotas)

    print("resumo: %d acusa, %d aviso, %d não conferi; %d arquivos de código lidos, sem os de teste" % (
        relato.contagem["acusa"], relato.contagem["aviso"], relato.contagem["não conferi"], len(fontes)))
    print("limites: não segui imports, não olhei o histórico do git nem a ordem das chamadas")
    return relato.codigo()


if __name__ == "__main__":
    sys.exit(main())
