#!/usr/bin/env python3
"""conferir.py: lê os testes de ponta a ponta de um projeto e acusa descuidos conhecidos.

Só lê arquivos e pergunta ao git o que ele rastreia: não altera nada e não acessa a rede.

uso:
  python3 conferir.py <projeto> [--testes <pasta>] [--config <arquivo>]
                      [--prefixo <prefixo>] [--sessoes <pasta>]

confere:
  1. `.only` esquecido em teste;
  2. espera fixa por tempo (waitForTimeout, ou setTimeout dentro de uma Promise);
  3. endereço que não é local escrito em teste ou na configuração;
  4. arquivo de sessão (JSON com "cookies" e "origins") que o git rastreia, ou que ele não
     rastreia e também não ignora; com --sessoes, se a pasta de sessões está ignorada;
  5. com --prefixo: teste que grava por API sem citar o prefixo de limpeza, e prefixo sem
     nenhuma limpeza;
  6. na configuração, como "aviso:": repetição automática fora do CI, falta de forbidOnly,
     servidor de desenvolvimento como alvo e servidor reaproveitado.

saída: 0 nada acusado e tudo conferido; 1 há "acusa:"; 2 uso errado;
       3 nada acusado, mas alguma conferência não rodou ("não conferi:").

limites: lê texto, linha a linha. Não segue imports, não entende o que o código faz e não vê
gravação feita pela tela, por `update` ou por função de apoio que não cita o prefixo. Linha
que é só comentário é ignorada; linha com "conferir: ok" também. Nomes reservados que nunca
saem da máquina (.test, .example, .invalid, .localhost) contam como locais. Não achar não
prova que não há.
"""

import argparse
import json
import os
import re
import subprocess
import sys

PASTAS_IGNORADAS = {
    ".git", "node_modules", ".next", "dist", "build", "out", "coverage", ".turbo", ".vercel",
    "test-results", "playwright-report", "__pycache__", ".venv", "venv",
}
EXTENSOES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
PASTAS_DE_TESTE = ["tests/e2e", "test/e2e", "e2e", "tests-e2e", "playwright", "tests", "test"]
CONFIGS = ["playwright.config." + e for e in ("ts", "mts", "cts", "js", "mjs", "cjs")]
LIMITE_DE_BYTES = 1_000_000

SO_ESTE = re.compile(r"\b\w+(?:\.\w+)*\.only\s*\(")
ESPERA_FIXA = re.compile(r"\bwaitForTimeout\s*\(|new\s+Promise\b.*\bsetTimeout\b")
ENDERECO = re.compile(r"https?://([^\s/\"'`<>)\]},;\\]+)")
RESERVADOS = (".test", ".example", ".invalid", ".localhost")
GRAVA = re.compile(
    r"\.(insert|upsert|create|createMany|createUser|save)\s*\("
    r"|\brequest\.(post|put|patch)\s*\("
    r"|\bmethod\s*:\s*[\"'`](POST|PUT|PATCH)[\"'`]"
    r"|\binsert\s+into\b",
    re.I,
)
APAGA = re.compile(r"\.(delete|deleteMany|deleteUser|remove)\s*\(|\bdelete\s+from\b", re.I)
# (chave, padrão, o que acusar, o que dizer quando está limpo)
POR_LINHA = (
    ("só este", SO_ESTE, "`.only` esquecido; o resto da suíte não roda", "nenhum `.only` nos testes"),
    ("espera", ESPERA_FIXA, "espera fixa por tempo; espere o efeito", "nenhuma espera fixa por tempo"),
)
SEM_ENDERECO = "nenhum endereço fora da máquina em teste ou configuração"
NA_CONFIG = (
    (re.compile(r"\bretries\s*:\s*[1-9]"), "repetição automática também fora do CI"),
    (re.compile(r"\bcommand\s*:.*\bdev\b"), "o alvo é o servidor de desenvolvimento"),
    (re.compile(r"\breuseExistingServer\s*:\s*(?!false)\S"), "reaproveita um servidor que já está no ar"),
)
FUNCAO = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)")


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


def ler(caminho):
    try:
        if os.path.getsize(caminho) > LIMITE_DE_BYTES:
            return None
        with open(caminho, encoding="utf-8", errors="replace") as arquivo:
            return arquivo.read()
    except OSError:
        return None


def linhas_de_codigo(texto):
    # Devolve (número, linha) sem as linhas que são só comentário nem as marcadas como aceitas.
    em_bloco = False
    for numero, linha in enumerate(texto.splitlines(), 1):
        limpa = linha.strip()
        if em_bloco:
            em_bloco = "*/" not in limpa
            continue
        if limpa.startswith("/*"):
            em_bloco = "*/" not in limpa
            continue
        if not limpa or limpa.startswith("//") or limpa.startswith("*"):
            continue
        if "conferir: ok" in linha:
            continue
        yield numero, linha


def e_local(servidor):
    servidor = servidor.split("@")[-1].lower()
    if servidor.startswith("["):
        return servidor.startswith("[::1]")
    servidor = servidor.split(":")[0]
    if servidor in ("localhost", "0.0.0.0") or servidor.startswith("127."):
        return True
    return servidor.endswith(RESERVADOS)


def arquivos_de_teste(pasta):
    achados = []
    for atual, pastas, nomes in os.walk(pasta):
        pastas[:] = sorted(p for p in pastas if p not in PASTAS_IGNORADAS)
        for nome in sorted(nomes):
            if os.path.splitext(nome)[1] in EXTENSOES:
                achados.append(os.path.join(atual, nome))
    return achados


def git(raiz, *argumentos):
    try:
        saida = subprocess.run(
            ["git", "-C", raiz] + list(argumentos), capture_output=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None, b""
    return saida.returncode, saida.stdout


def conferir_linhas(relato, raiz, arquivos, config):
    achou = {}
    for caminho in arquivos + ([config] if config else []):
        nome = os.path.relpath(caminho, raiz)
        for numero, linha in linhas_de_codigo(ler(caminho) or ""):
            onde = "%s:%d" % (nome, numero)
            for chave, padrao, acusacao, _ in POR_LINHA:
                if caminho != config and padrao.search(linha):
                    achou[chave] = True
                    relato.linha("acusa", "%s: %s" % (onde, acusacao))
            for servidor in ENDERECO.findall(linha):
                if not servidor.startswith("$") and not e_local(servidor):
                    achou["endereço"] = True
                    relato.linha("acusa", "%s: endereço que não é local (%s)" % (onde, servidor))
    for chave, _, _, limpo in POR_LINHA + (("endereço", None, None, SEM_ENDERECO),):
        if chave not in achou:
            relato.linha("ok", limpo)


def e_sessao(caminho):
    texto = ler(caminho) or ""
    if '"cookies"' not in texto or '"origins"' not in texto:
        return False
    try:
        dado = json.loads(texto)
    except ValueError:
        return False
    return isinstance(dado, dict) and all(isinstance(dado.get(c), list) for c in ("cookies", "origins"))


def conferir_sessoes(relato, raiz, pasta_de_sessoes):
    codigo, _ = git(raiz, "rev-parse", "--is-inside-work-tree")
    if codigo != 0:
        relato.linha("não conferi", "arquivos de sessão: %s não é um repositório git" % raiz)
        return
    achou = 0
    for rotulo, argumentos in (
        ("rastreado pelo git", ["ls-files", "-z"]),
        ("fora do git e não ignorado", ["ls-files", "-z", "--others", "--exclude-standard"]),
    ):
        _, saida = git(raiz, *argumentos)
        for nome in saida.decode("utf-8", "replace").split("\0"):
            partes = nome.split("/")
            if not nome.endswith(".json") or PASTAS_IGNORADAS.intersection(partes):
                continue
            if e_sessao(os.path.join(raiz, nome)):
                achou += 1
                relato.linha("acusa", "arquivo de sessão %s: %s (é uma credencial)" % (rotulo, nome))
    if not achou:
        relato.linha("ok", "nenhum arquivo de sessão rastreado ou por rastrear")
    if not pasta_de_sessoes:
        relato.linha("não conferi", "se a pasta de sessões está ignorada (passe --sessoes)")
        return
    amostra = os.path.join(pasta_de_sessoes, "persona.json")
    codigo, _ = git(raiz, "check-ignore", "-q", amostra)
    if codigo == 0:
        relato.linha("ok", "a pasta de sessões %s está ignorada pelo git" % pasta_de_sessoes)
    elif codigo == 1:
        relato.linha("acusa", "a pasta de sessões %s não está no .gitignore" % pasta_de_sessoes)
    else:
        relato.linha("não conferi", "a pasta de sessões: o git não respondeu")


def nomes_do_prefixo(textos, prefixo):
    # O prefixo, as constantes que o guardam e, um nível acima, as funções que usam uma delas.
    constante = re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*[\"'`]" + re.escape(prefixo)
    )
    nomes = {prefixo}
    for texto in textos.values():
        nomes.update(constante.findall(texto))
    base = tuple(nomes)
    for texto in textos.values():
        atual = None
        for linha in texto.splitlines():
            declarada = FUNCAO.match(linha)
            if declarada:
                atual = declarada.group(1)
            elif linha.startswith("}"):
                atual = None
            if atual and not declarada and any(nome in linha for nome in base):
                nomes.add(atual)
    return nomes


def cita(texto, nomes):
    return any(re.search(r"(?<![\w$])" + re.escape(nome), texto) for nome in nomes)


def conferir_prefixo(relato, raiz, arquivos, prefixo):
    if not prefixo:
        relato.linha("não conferi", "gravação sem prefixo de limpeza (passe --prefixo)")
        return
    textos = {caminho: ler(caminho) or "" for caminho in arquivos}
    nomes = nomes_do_prefixo(textos, prefixo)
    gravam, citam, limpa = 0, 0, False
    for caminho, texto in textos.items():
        codigo = list(linhas_de_codigo(texto))
        corpo = "\n".join(linha for _, linha in codigo)
        usa = cita(corpo, nomes)
        citam += usa
        if usa and APAGA.search(corpo):
            limpa = True
        primeira = next(((n, GRAVA.search(l)) for n, l in codigo if GRAVA.search(l)), None)
        if primeira is None:
            continue
        gravam += 1
        if not usa:
            relato.linha(
                "acusa",
                '%s:%d: grava por API (%s) e o arquivo não cita o prefixo "%s"'
                % (os.path.relpath(caminho, raiz), primeira[0], primeira[1].group(0).strip(), prefixo),
            )
    if not gravam and not citam:
        relato.linha("ok", "nenhum teste grava por API (gravação pela tela este script não vê)")
        return
    if not limpa:
        relato.linha("acusa", 'nenhum arquivo de teste apaga pelo prefixo "%s"' % prefixo)
    else:
        relato.linha("ok", 'há limpeza pelo prefixo "%s"' % prefixo)


def conferir_config(relato, raiz, config):
    texto = ler(config) if config else None
    if texto is None:
        relato.linha("não conferi", "a configuração do Playwright (passe --config)")
        return
    nome = os.path.relpath(config, raiz)
    avisos = []
    if "forbidOnly" not in texto:
        avisos.append("%s: sem forbidOnly; um `.only` esquecido passa no CI" % nome)
    for numero, linha in linhas_de_codigo(texto):
        avisos += ["%s:%d: %s" % (nome, numero, a) for padrao, a in NA_CONFIG if padrao.search(linha)]
    for aviso in avisos:
        relato.linha("aviso", aviso)
    if not avisos:
        relato.linha("ok", "%s: sem repetição local, com forbidOnly e servidor próprio" % nome)


def achar(raiz, pedido, candidatos, e_pasta):
    existe = os.path.isdir if e_pasta else os.path.isfile
    if pedido:
        caminho = os.path.join(raiz, pedido)
        return caminho if existe(caminho) else False
    for candidato in candidatos:
        caminho = os.path.join(raiz, candidato)
        if existe(caminho) and (not e_pasta or arquivos_de_teste(caminho)):
            return caminho
    return None


def main():
    leitor = argparse.ArgumentParser(
        prog="conferir.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    leitor.add_argument("projeto", help="raiz do projeto")
    leitor.add_argument("--testes", help="pasta dos testes de ponta a ponta, relativa ao projeto")
    leitor.add_argument("--config", help="configuração do Playwright, relativa ao projeto")
    leitor.add_argument("--prefixo", help="prefixo dos dados que os testes criam")
    leitor.add_argument("--sessoes", help="pasta dos arquivos de sessão, relativa ao projeto")
    pedido = leitor.parse_args()

    raiz = os.path.abspath(pedido.projeto)
    if not os.path.isdir(raiz):
        print("uso: %s não é uma pasta" % pedido.projeto, file=sys.stderr)
        return 2
    testes = achar(raiz, pedido.testes, PASTAS_DE_TESTE, True)
    config = achar(raiz, pedido.config, CONFIGS, False)
    if testes is False or config is False:
        print("uso: --testes ou --config aponta para o que não existe", file=sys.stderr)
        return 2

    relato = Relato()
    arquivos = arquivos_de_teste(testes) if testes else []
    if arquivos:
        print("lendo %d arquivo(s) em %s" % (len(arquivos), os.path.relpath(testes, raiz)))
        conferir_linhas(relato, raiz, arquivos, config)
        conferir_prefixo(relato, raiz, arquivos, pedido.prefixo)
    else:
        relato.linha("não conferi", "os testes: não achei a pasta (passe --testes)")
    conferir_sessoes(relato, raiz, pedido.sessoes)
    conferir_config(relato, raiz, config or None)

    c = relato.contagem
    print("resumo: %d acusa, %d aviso, %d não conferi" % (c["acusa"], c["aviso"], c["não conferi"]))
    return relato.codigo()


if __name__ == "__main__":
    sys.exit(main())
