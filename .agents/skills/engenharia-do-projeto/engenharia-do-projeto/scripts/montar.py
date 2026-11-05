#!/usr/bin/env python3
"""Cria no projeto os documentos do método que faltam, a partir dos modelos. Não sobrescreve.

uso:
  python3 montar.py <pasta> --simular
      → uma linha por item ("simulação: criaria <arquivo>"); nada é gravado
  python3 montar.py <pasta> [--instrucoes <nome>] [--completo]
      → cria só o que falta: metodo.ini, especificação, arquivo de instruções, registro de
        decisões, roteiro e estado. Em projeto com código, especificação e roteiro só com
        --completo. Documento que já existe com outro nome é mapeado em metodo.ini
  python3 montar.py <pasta> --com-ferramentas
      → o mesmo, e copia os seis scripts para <pasta>/ferramentas/metodo/

à mão:
  Copie cada modelo de assets/modelos/ para o destino: metodo.ini, ESPECIFICACAO.md e o arquivo
  de instruções (CLAUDE.md, por padrão) na raiz do projeto; decisoes.md, ROTEIRO.md e ESTADO.md
  em docs/. Apague a primeira linha de cada cópia (o aviso de modelo) e escreva em [documentos],
  em metodo.ini, o caminho real de cada documento. Não copie por cima de arquivo que já existe.

recusa: sobrescrever ou alterar qualquer arquivo existente, com qualquer opção; gravar fora da
pasta; rodar na raiz do sistema, na pasta pessoal ou dentro da pasta da skill; criar arquivo de
ambiente; tocar no git ou no .gitignore; preencher comando de escada ou caminho de zona.
"""
import configparser, os, platform, re, shlex, subprocess, sys
from collections import deque

def _py():
    """Como se chama o Python na linha de comando deste sistema (no Windows, `python3` abre a loja)."""
    return "py -3" if platform.system() == "Windows" else "python3"

def _citar(texto):
    """Caminho pronto para a linha de comando do sistema; no Windows, aspas duplas."""
    if platform.system() == "Windows":
        return '"%s"' % texto if " " in texto else texto
    return shlex.quote(texto)

LIMITE = 5000
NAO_PERCORRER = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
                 "__pycache__"}
COPIA = "ferramentas/metodo"
# papel, modelo, destino padrão, nomes comuns, "em projeto com código, só com --completo"
PECAS = (
    ("especificacao", "especificacao.md", "ESPECIFICACAO.md",
     ["ESPECIFICACAO.md", "SPEC.md", "PRD.md", "docs/especificacao.md"], True),
    ("instrucoes", "instrucoes.md", "CLAUDE.md", ["CLAUDE.md", "AGENTS.md"], False),
    ("decisoes", "decisoes.md", "docs/decisoes.md",
     ["docs/decisoes.md", "DECISOES.md", "docs/decisions.md", "docs/adr.md", "docs/adr"], False),
    ("roteiro", "roteiro.md", "docs/ROTEIRO.md",
     ["docs/ROTEIRO.md", "ROTEIRO.md", "ROADMAP.md", "docs/roadmap.md"], True),
    ("estado", "estado.md", "docs/ESTADO.md", ["docs/ESTADO.md", "ESTADO.md"], False),
)
SCRIPTS = ("situacao.py", "montar.py", "escada.py", "decisoes.py", "envio.py", "fronteiras.py")
MANIFESTOS = {"package.json", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile",
              "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
              "composer.json", "mix.exs", "pubspec.yaml", "Package.swift", "deno.json",
              "CMakeLists.txt"}
CODIGO = set(".py .js .jsx .ts .tsx .mjs .cjs .go .rs .java .kt .swift .rb .php .cs .c .h .cc "
             ".cpp .m .scala .ex .exs .dart .lua .sql .sh .vue .svelte .html .css".split())
AMBIENTE = (".env", ".env.*", "!.env.example")


def parar(mensagem):
    """Uso errado ou pré-condição ausente: explica em stderr e devolve o código 2."""
    print(mensagem, file=sys.stderr)
    print("não conferi: nada; parei antes de começar")
    return 2

def achar(raiz, rel):
    """Caminho real de `rel` no projeto, sem distinguir maiúsculas; vazio se não há."""
    atual, partes = raiz, []
    for parte in rel.split("/"):
        try:
            nomes = sorted(os.listdir(atual))
        except OSError:
            return ""
        nome = parte if parte in nomes else next(
            (n for n in nomes if n.lower() == parte.lower()), None)
        if nome is None:
            return ""
        partes.append(nome)
        atual = os.path.join(atual, nome)
    return "/".join(partes)

def dentro(raiz, rel):
    """O caminho fica dentro da pasta, mesmo passando por atalho simbólico?"""
    base, alvo = os.path.realpath(raiz), os.path.realpath(os.path.join(raiz, rel))
    return not os.path.isabs(rel) and alvo.startswith(base + os.sep)

def varrer(raiz):
    """(manifestos achados, há código?). Mesmo critério do diagnóstico; para em LIMITE."""
    manifestos, codigo, fila, vistas = [], False, deque([""]), 0
    while fila:
        rel = fila.popleft()
        try:
            entradas = sorted(os.scandir(os.path.join(raiz, rel)), key=lambda e: e.name)
        except OSError:
            continue
        for e in entradas:
            vistas += 1
            if vistas > LIMITE:
                return manifestos, codigo or bool(manifestos)
            caminho = rel + "/" + e.name if rel else e.name
            if e.is_dir(follow_symlinks=False):
                if not (e.name in NAO_PERCORRER or e.name.startswith(".") or caminho == COPIA):
                    fila.append(caminho)
            elif e.is_file(follow_symlinks=False):
                if e.name in MANIFESTOS or e.name.endswith((".csproj", ".sln")):
                    manifestos.append(caminho)
                codigo = codigo or os.path.splitext(e.name)[1].lower() in CODIGO
    return manifestos, codigo or bool(manifestos)

def ler_modelo(caminho):
    """Texto do modelo sem a primeira linha, que é o aviso MODELO."""
    with open(caminho, encoding="utf-8") as f:
        linhas = f.read().split("\n")
    return "\n".join(linhas[1:] if linhas and "MODELO" in linhas[0] else linhas)

def texto_do_ini(modelo, valores, manifestos):
    """O modelo de metodo.ini com as linhas de [documentos] reescritas (`chave = valor`) e o
    comentário dos manifestos em [escada]. Nenhum comando nem caminho de zona é preenchido."""
    saida, secao = [], ""
    for linha in modelo.split("\n"):
        m = re.match(r"\[(.+)\]\s*$", linha)
        secao = m.group(1) if m else secao
        chave = re.match(r"(\w+) = ", linha + " ")
        if secao == "documentos" and chave and chave.group(1) in valores:
            valor = valores[chave.group(1)]
            if not valor:
                saida.append("; Sem valor: não foi criado, porque o projeto já tinha código. Com "
                             "o sim do dono: montar.py --completo.")
            linha = ("%s = %s" % (chave.group(1), valor)).rstrip()
        saida.append(linha)
        if m and secao == "escada":
            saida.append("; manifestos achados: " + (", ".join(manifestos[:8]) or "nenhum"))
    return "\n".join(saida)

def cobre_ambiente(raiz):
    """O .gitignore do projeto já ignora os arquivos de ambiente?"""
    try:
        _caminho = os.path.join(raiz, ".gitignore")
        with open(_caminho, encoding="utf-8", errors="replace") as f:
            linhas = [l.strip().lstrip("/") for l in f if l.strip() and not l.startswith(("#", "!"))]
    except OSError:
        return False
    def casa(nome):
        return any(re.match(re.escape(p).replace(r"\*", ".*") + "$", nome) for p in linhas)
    return casa(".env") and casa(".env.local")


def main(args):
    pasta, instrucoes, opcoes = None, None, set()
    args = list(args)
    while args:
        a = args.pop(0)
        if a in ("-h", "--help", "--ajuda"):
            print(__doc__.strip())
            return 0
        if a in ("--simular", "--completo", "--com-ferramentas"):
            opcoes.add(a)
        elif a == "--instrucoes" and args:
            instrucoes = args.pop(0)
        elif not a.startswith("-") and pasta is None:
            pasta = a
        else:
            return parar("erro de uso: não entendi %s (veja --ajuda)" % a)
    if pasta is None:
        return parar("erro de uso: falta a pasta do projeto; ela não tem padrão, porque este "
                     "script grava (veja --ajuda)")
    simular = "--simular" in opcoes

    raiz = os.path.abspath(pasta)
    skill = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    modelos = os.path.join(skill, "assets", "modelos")
    real = os.path.realpath(raiz)
    if not os.path.isdir(raiz):
        return parar("falta: a pasta %s (não existe; crie-a depois de combinar com o dono)" % raiz)
    for qual, ruim in (("a raiz do sistema", os.sep), ("a pasta pessoal", os.path.expanduser("~")),
                       ("a pasta da skill", skill)):
        ruim = os.path.realpath(ruim)
        if real == ruim or (qual == "a pasta da skill" and real.startswith(ruim + os.sep)):
            return parar("falta: uma pasta de projeto (esta é %s; combine a pasta com o dono)" % qual)
    if not all(os.path.isfile(os.path.join(modelos, m))
               for m in ["metodo.ini"] + [peca[1] for peca in PECAS]):
        return parar("falta: os modelos em %s (rode pelo caminho da skill, não pela cópia do "
                     "projeto)" % modelos)
    if instrucoes is not None and (not instrucoes or ".." in instrucoes.split("/")
                                   or not dentro(raiz, instrucoes)):
        return parar("falta: um nome de arquivo dentro da pasta em --instrucoes (não gravo fora dela)")
    faltam = [s for s in SCRIPTS if not os.path.isfile(os.path.join(skill, "scripts", s))]
    if "--com-ferramentas" in opcoes and faltam:
        return parar("falta: %s em %s (a skill está incompleta; nada foi copiado)"
                     % (", ".join(faltam), os.path.join(skill, "scripts")))
    if not simular and not os.access(raiz, os.W_OK):
        return parar("falta: permissão de escrita em %s (nada foi criado)" % raiz)

    declarados, ini_existe = {}, os.path.lexists(os.path.join(raiz, "metodo.ini"))
    if ini_existe:
        try:
            ini = configparser.ConfigParser(interpolation=None)
            _caminho = os.path.join(raiz, "metodo.ini")
            with open(_caminho, encoding="utf-8") as f:
                ini.read_file(f)
            declarados = dict(ini["documentos"]) if ini.has_section("documentos") else {}
        except (configparser.Error, UnicodeDecodeError, OSError) as erro:
            return parar("falta: metodo.ini válido (%s)" % str(erro).splitlines()[0])
    manifestos, ha_codigo = varrer(raiz)

    # decide o que acontece com cada documento, sem gravar nada ainda
    plano, valores, sugestoes, saida = [], {}, [], []
    for papel, modelo, padrao, comuns, so_completo in PECAS:
        declarado = (declarados.get(papel, padrao) or "").strip().strip("/")
        destino = (instrucoes if papel == "instrucoes" and instrucoes else declarado) or padrao
        if not dentro(raiz, destino):
            return parar("falta: %s dentro da pasta (o destino %s sai dela, pelo caminho ou por "
                         "um atalho)" % (papel, destino))
        candidatos = [destino] + [achar(raiz, n) for n in comuns]
        existente = next((c for c in candidatos if c and os.path.lexists(os.path.join(raiz, c))), "")
        valores[papel] = existente or destino
        if existente == destino:
            saida.append("já existe: " + destino)
        elif existente:
            saida.append("mapeado: %s = %s" % (papel, existente))
            if existente.lower() == "agents.md":
                sugestoes.append("aviso: confirme que AGENTS.md é carregado em toda sessão e não é "
                                 "gerado por outra ferramenta (references/instrucoes.md §8)")
        elif so_completo and ha_codigo and "--completo" not in opcoes:
            saida.append("não criado: %s (projeto com código; use --completo se o dono quiser)" % destino)
            valores[papel] = ""
        else:
            plano.append((destino, ler_modelo(os.path.join(modelos, modelo)).encode("utf-8")))
            saida.append(None)  # a linha sai depois de gravar
        if ini_existe and valores[papel] not in ("", declarado):
            sugestoes.append("sugestão: em metodo.ini, %s = %s" % (papel, valores[papel]))
        if papel == "instrucoes" and existente:  # compara cada título pelo começo da linha
            try:
                _caminho = os.path.join(raiz, existente)
                with open(_caminho, encoding="utf-8", errors="replace") as f:
                    linhas = f.read(1048576).split("\n")
            except OSError:
                linhas = None
            titulos = [l for l in ler_modelo(os.path.join(modelos, modelo)).split("\n")
                       if l.startswith("## ")]
            sem = [t[3:] for t in titulos if not any(l.startswith(t) for l in linhas or [])]
            if linhas is None:
                sugestoes.append("aviso: não consegui ler %s para conferir os blocos" % existente)
            elif sem:
                sugestoes.append("sugestão: faltam no seu %s os blocos: %s" % (existente, "; ".join(sem)))
    if ini_existe:
        saida.insert(0, "já existe: metodo.ini")
    else:
        texto = texto_do_ini(ler_modelo(os.path.join(modelos, "metodo.ini")), valores, manifestos)
        plano.insert(0, ("metodo.ini", texto.encode("utf-8")))
        saida.insert(0, None)
    if "--com-ferramentas" in opcoes:
        for nome in SCRIPTS:
            _caminho = os.path.join(skill, "scripts", nome)
            with open(_caminho, "rb") as f:
                dado = f.read()
            destino = COPIA + "/" + nome
            if not dentro(raiz, destino):
                return parar("falta: %s dentro da pasta (há um atalho para fora)" % COPIA)
            try:
                _caminho = os.path.join(raiz, destino)
                with open(_caminho, "rb") as f:
                    igual = f.read() == dado
                saida.append("já existe: " + destino if igual else "difere: %s (é de outra versão "
                             "da skill: mostre a diferença ao dono, apague a cópia num commit "
                             "próprio e rode de novo; não edite à mão)" % destino)
            except OSError:
                plano.append((destino, dado))
                saida.append(None)

    # grava, em criação exclusiva: nem uma corrida sobrescreve
    criados, falha = [], ""
    for destino, dado in plano:
        if simular:
            criados.append("simulação: criaria " + destino)
            continue
        try:
            os.makedirs(os.path.dirname(os.path.join(raiz, destino)), exist_ok=True)
            _caminho = os.path.join(raiz, destino)
            with open(_caminho, "xb") as f:
                f.write(dado)
            criados.append("criado: " + destino)
        except OSError as erro:
            falha = "FALHOU ao gravar %s: %s" % (destino, erro.strerror or erro)
            break
    feitos = iter(criados)
    for linha in saida:
        linha = next(feitos, None) if linha is None else linha
        if linha:
            print(linha)
    if falha:
        print(falha)
        print("ficou criado: " + (", ".join(c.split(": ", 1)[1] for c in criados) or "nada"))
        print("próximo: corrija a permissão ou o espaço e rode de novo; o que já existe não muda")
        print("não conferi: os arquivos que não cheguei a criar")
        return 1

    for linha in sugestoes:
        print(linha)
    if not cobre_ambiente(raiz):
        print("sugestão: ponha no .gitignore, uma por linha: " + "  ".join(AMBIENTE))
    try:
        repositorio = subprocess.run(["git", "-C", raiz, "rev-parse", "--is-inside-work-tree"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        repositorio = False
    if not repositorio:
        print("sugestão: git init antes do primeiro commit")
    def comando(nome):
        return "%s %s %s" % (_py(), _citar(os.path.join(skill, "scripts", nome)), _citar(raiz))
    if simular:
        print("próximo: diga ao dono o que será criado; depois, " + comando("montar.py"))
    else:
        print("próximo: " + comando("situacao.py"))
    print("não conferi: o formato dos documentos que já existiam; se o arquivo de instruções é "
          "carregado em toda sessão; comandos da escada e caminhos de zona, que ficam vazios")
    return 0


if __name__ == "__main__":
    for fluxo in (sys.stdout, sys.stderr):  # terminal sem UTF-8 não derruba a saída
        fluxo.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
