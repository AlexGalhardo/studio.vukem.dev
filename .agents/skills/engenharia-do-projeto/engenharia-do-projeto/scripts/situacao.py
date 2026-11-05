#!/usr/bin/env python3
"""Diagnóstico do projeto: o que existe, o que está em curso e a situação provável. Só lê.

uso:
  python3 situacao.py [<pasta>] [--projeto <pasta>]
      → até 34 linhas: git, documentos, lacunas, ambiente, escada, evidência, mudança em curso,
        a enviar, sinais, atenção, "situação provável" e "leia"
  python3 situacao.py [<pasta>] --completo
      → o mesmo, com uma linha por fase do roteiro e a contagem de itens de cada lista do estado
  python3 situacao.py [<pasta>] --estrito
      → o mesmo, com código de saída 1 se houver item de atenção

à mão:
  Há código? Quais dos cinco documentos existem (especificação, instruções, decisões, roteiro,
  estado)? Qual fase está em andamento no roteiro? Qual a data do estado e houve commit depois?
  O que `git status` mostra? Para o ambiente: liste só os nomes das chaves do arquivo, sem os
  valores.

recusa: escrever qualquer coisa; imprimir valor ou endereço de arquivo de ambiente; buscar no
remoto; afirmar a situação (diz "provável" e o sinal); calcular porcentagem ou prazo; rodar na
raiz do sistema ou na pasta pessoal.
"""
import configparser, datetime, hashlib, json, os, re, subprocess, sys, tempfile
from collections import deque

LIMITE = 5000
NAO_PERCORRER = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
                 "__pycache__"}
COPIA = "ferramentas/metodo"
PAPEIS = ("especificacao", "instrucoes", "decisoes", "roteiro", "estado")
COMUNS = {
    "especificacao": ["ESPECIFICACAO.md", "SPEC.md", "PRD.md", "docs/especificacao.md"],
    "instrucoes": ["CLAUDE.md", "AGENTS.md"],
    "decisoes": ["docs/decisoes.md", "DECISOES.md", "docs/decisions.md", "docs/adr.md", "docs/adr"],
    "roteiro": ["docs/ROTEIRO.md", "ROTEIRO.md", "ROADMAP.md", "docs/roadmap.md"],
    "estado": ["docs/ESTADO.md", "ESTADO.md"],
}
PADRAO = {"especificacao": "ESPECIFICACAO.md", "instrucoes": "CLAUDE.md",
          "decisoes": "docs/decisoes.md", "roteiro": "docs/ROTEIRO.md", "estado": "docs/ESTADO.md",
          "leiame": "README.md", "planos": "docs/planos", "notas": "docs/notas",
          "orcamento_instrucoes": "8000"}
NUNCA_ENVIAR = ".env, .env.*, !.env.example, *.pem, *.key"
MANIFESTOS = {"package.json", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile",
              "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile",
              "composer.json", "mix.exs", "pubspec.yaml", "Package.swift", "deno.json",
              "CMakeLists.txt"}
CODIGO = set(".py .js .jsx .ts .tsx .mjs .cjs .go .rs .java .kt .swift .rb .php .cs .c .h .cc "
             ".cpp .m .scala .ex .exs .dart .lua .sql .sh .vue .svelte .html .css".split())
TESTE = re.compile(r"(^|/)(tests?|__tests__|specs?|e2e)/|(^|/)test_[^/]*$|[._-](test|spec)\.[^/]*$")
CI = (".github/workflows", ".gitlab-ci.yml", ".circleci", "bitbucket-pipelines.yml",
      "azure-pipelines.yml", "Jenkinsfile", ".travis.yml", ".woodpecker.yml", ".buildkite")
FASE = re.compile(r"## Fase (\d+) · (.+) \((a fazer|em andamento|pronta)\)\s*$")
LISTAS = ("Para decidir", "Passos do dono", "Autorizações não dadas", "Ficou para depois",
          "Pendência aceita")
DESTINO = re.compile(r"(?:://(?:[^/\s@]*@)?|@)(\[[^\]]*\]|[^\s/?#\"',;:]*)")


# --- funções comuns do método: iguais em todo script que as usa; não altere a lógica ---

def _regex_do_padrao(padrao):
    p = padrao.strip().replace("\\", "/")
    if p.endswith("/"):
        p += "**"
    ancorado = "/" in p
    i, out = 0, []
    while i < len(p):
        c = p[i]
        if p.startswith("**/", i):
            out.append("(?:.*/)?"); i += 3
        elif p.startswith("**", i):
            out.append(".*"); i += 2
        elif c == "*":
            out.append("[^/]*"); i += 1
        elif c == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(c)); i += 1
    return re.compile(("^" if ancorado else "^(?:.*/)?") + "".join(out) + "$")

def casa(caminho, padrao):
    """Diz se o caminho (relativo à raiz, com /) casa com o padrão."""
    caminho = caminho.replace("\\", "/")
    if caminho.startswith("./"):
        caminho = caminho[2:]
    return bool(_regex_do_padrao(padrao).match(caminho))

def casa_lista(caminho, padroes):
    """Lista com reinclusão por '!': vale o último padrão que casar."""
    resultado = False
    for p in padroes:
        p = p.strip()
        if not p:
            continue
        if p.startswith("!"):
            if casa(caminho, p[1:]):
                resultado = False
        elif casa(caminho, p):
            resultado = True
    return resultado

def _git(raiz, *args):
    amb = dict(os.environ, LC_ALL="C", GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", raiz] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=amb)
    except OSError:  # git não instalado: vale como "não é repositório"
        return 127, b""
    return r.returncode, r.stdout

def _nomes(saida):
    return [n.decode("utf-8", "surrogateescape") for n in saida.split(b"\0") if n]

def fora_da_impressao(documentos):
    """Padrões dos documentos do método, que não entram na impressão digital."""
    fora = []
    for chave in ("especificacao", "instrucoes", "decisoes", "roteiro", "estado", "leiame"):
        v = (documentos.get(chave) or "").strip().strip("/")
        if v:
            fora += [v, v + "/**"]
    for chave in ("planos", "notas"):
        v = (documentos.get(chave) or "").strip().strip("/")
        if v:
            fora.append(v + "/**")
    return fora

def impressao(raiz, fora=()):
    """Impressão digital do conteúdo da árvore de trabalho, sem os documentos do método."""
    cod, saida = _git(raiz, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if cod != 0:
        return "sem-git"
    h = hashlib.sha256()
    for nome in sorted(set(n for n in saida.split(b"\0") if n)):
        texto = nome.decode("utf-8", "surrogateescape")
        if any(casa(texto, p) for p in fora):
            continue
        caminho = os.path.join(os.fsencode(raiz), nome)
        if os.path.islink(caminho):
            dado = b"link:" + os.fsencode(os.readlink(caminho))
        elif os.path.isfile(caminho):
            with open(caminho, "rb") as f:
                dado = f.read()
        else:
            continue  # apagado na árvore, ou submódulo
        h.update(nome + b"\0" + hashlib.sha256(dado).digest())
    return h.hexdigest()

def mudanca_em_curso(raiz):
    """Arquivos alterados, preparados e não rastreados da árvore de trabalho. None sem git."""
    cod, _ = _git(raiz, "rev-parse", "--is-inside-work-tree")
    if cod != 0:
        return None
    nomes = set()
    cod, saida = _git(raiz, "diff", "--name-only", "-z", "--relative", "--no-renames",
                      "HEAD", "--", ".")
    if cod != 0:  # repositório ainda sem commit: o que está preparado é novo
        cod, saida = _git(raiz, "ls-files", "-z", "--cached", "--", ".")
    nomes.update(_nomes(saida))
    cod, saida = _git(raiz, "ls-files", "-z", "--others", "--exclude-standard", "--", ".")
    nomes.update(_nomes(saida))
    return sorted(nomes)

def a_enviar(raiz, base):
    """Arquivos dos commits à frente da base, mais a mudança em curso. None sem git ou base."""
    curso = mudanca_em_curso(raiz)
    if curso is None or not base:
        return None
    cod, saida = _git(raiz, "diff", "--name-only", "-z", "--relative", "--no-renames",
                      base + "...HEAD", "--", ".")
    if cod != 0:
        return None
    return sorted(set(_nomes(saida)) | set(curso))

def ler_zonas(secao):
    """secao: o dicionário da seção [zonas]. Devolve {nome: (degrau, [padrões])}."""
    zonas = {}
    for chave, valor in secao.items():
        if not chave.endswith(".degrau"):
            continue
        nome = chave[:-len(".degrau")]
        padroes = [p.strip() for p in (secao.get(nome + ".caminhos") or "").split(",")]
        zonas[nome] = (int(valor), [p for p in padroes if p])
    return zonas

def zonas_tocadas(arquivos, zonas):
    """Devolve {nome da zona: quantos arquivos casam}, só das zonas tocadas."""
    tocadas = {}
    for nome, (_degrau, padroes) in zonas.items():
        n = sum(1 for a in arquivos if any(casa(a, p) for p in padroes))
        if n:
            tocadas[nome] = n
    return tocadas

def degrau_minimo(arquivos, zonas):
    """Maior degrau entre as zonas tocadas; sem zona tocada, 2 (o piso)."""
    return max([zonas[z][0] for z in zonas_tocadas(arquivos, zonas)] + [2])

def subiu_ate(resultados):
    """Maior n tal que 0..n são todos 'ok' ou 'n/a'. None se o degrau 0 não é um dos dois."""
    n, ate = 0, None
    while resultados.get(n) in ("ok", "n/a"):
        ate, n = n, n + 1
    return ate

# --- fim das funções comuns ---


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

def ler(raiz, rel):
    """Texto de um arquivo do projeto. None se não existe, passa de 1 MB, é binário ou aponta
    para fora do projeto. Pasta (um arquivo por registro): os .md dela, juntos."""
    caminho, base = os.path.realpath(os.path.join(raiz, rel)), os.path.realpath(raiz)
    if caminho != base and not caminho.startswith(base + os.sep):
        return None
    if os.path.isdir(caminho):
        nomes = sorted(n for n in os.listdir(caminho) if n.endswith(".md"))[:500]
        return "\n".join(ler(raiz, rel + "/" + n) or "" for n in nomes)
    try:
        if os.path.getsize(caminho) > 1048576:
            return None
        with open(caminho, "rb") as f:
            dado = f.read()
    except OSError:
        return None
    return None if b"\0" in dado[:8192] else dado.decode("utf-8", "replace")

def varrer(raiz):
    """Percorre o projeto em largura, fora das pastas que não se percorrem; para no limite."""
    v = {"manifestos": [], "codigo": 0, "testes": 0, "parou": False}
    fila, vistas = deque([""]), 0
    while fila:
        rel = fila.popleft()
        try:
            entradas = sorted(os.scandir(os.path.join(raiz, rel)), key=lambda e: e.name)
        except OSError:
            continue
        for e in entradas:
            vistas += 1
            if vistas > LIMITE:
                v["parou"] = True
                return v
            caminho = rel + "/" + e.name if rel else e.name
            if e.is_dir(follow_symlinks=False):
                if not (e.name in NAO_PERCORRER or e.name.startswith(".") or caminho == COPIA):
                    fila.append(caminho)
            elif e.is_file(follow_symlinks=False):
                if e.name in MANIFESTOS or e.name.endswith((".csproj", ".sln")):
                    v["manifestos"].append(caminho)
                if os.path.splitext(e.name)[1].lower() in CODIGO:
                    v["codigo"] += 1
                    v["testes"] += bool(TESTE.search(caminho))
    return v

def commits(raiz, fora, *intervalo):
    """[(data local, toca código?)] dos commits do intervalo que tocam a pasta do projeto.
    Código é tudo o que fica fora dos caminhos de [documentos]. Lê no máximo 1.000 commits."""
    cod, saida = _git(raiz, "-c", "core.quotePath=false", "log", "--no-renames", "--name-only",
                      "--relative", "--max-count=1000", "--format=%x01%ct", *intervalo, "--", ".")
    lista = []
    for bloco in (saida.decode("utf-8", "surrogateescape").split("\x01")[1:] if cod == 0 else []):
        linhas = [l for l in bloco.split("\n") if l]
        if not linhas or not linhas[0].isdigit():
            continue
        dia = datetime.date.fromtimestamp(int(linhas[0])).isoformat()
        lista.append((dia, any(not any(casa(a, p) for p in fora) for a in linhas[1:])))
    return lista

def ler_fases(texto):
    """([[n, nome, situação, marcados, total]], quantos títulos de fase fora do formato)."""
    fases, fora, atual = [], 0, None
    for linha in texto.splitlines():
        if linha.startswith("## "):
            m = FASE.match(linha)
            atual = [m.group(1), m.group(2), m.group(3), 0, 0] if m else None
            if m:
                fases.append(atual)
            elif re.match(r"## Fase\b", linha, re.I):
                fora += 1
        elif atual is not None and re.match(r"- \[[ xX]\]", linha):
            atual[4] += 1
            atual[3] += linha[3] != " "
    return fases, fora

def contar_listas(texto):
    """{lista do estado: quantos itens}, pelas cinco listas abertas."""
    cont, atual = {}, None
    for linha in texto.splitlines():
        if linha.startswith("#"):
            titulo = linha.lstrip("#").strip()
            atual = titulo if linha.startswith("### ") and titulo in LISTAS else None
            if atual:
                cont[atual] = 0
        elif atual and re.match(r"(- |\d+\. )", linha):
            cont[atual] += 1
    return cont

def ambiente(raiz, nome):
    """(linha do arquivo de ambiente, há destino não local?). Nunca devolve valor nem endereço."""
    exemplo = nome.endswith((".example", ".sample", ".template"))
    rotulo = "ambiente: %s%s: " % (nome, " (exemplo)" if exemplo else "")
    texto = ler(raiz, nome)
    if texto is None:
        return rotulo + "não li (grande, binário ou atalho para fora do projeto)", False
    chaves, com_destino, fora = 0, 0, []
    for linha in texto.splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*=(.*)$", linha)
        if not m:
            continue
        chaves += 1
        destinos = [d.strip("[]").lower().rstrip(".") for d in DESTINO.findall(m.group(2))]
        destinos = [d for d in destinos if d and "$" not in d]
        com_destino += bool(destinos)
        if any(not _local(d) for d in destinos):
            fora.append(m.group(1))
    if fora:
        resposta = "sim (%s%s)" % (", ".join(fora[:5]), ", …" if len(fora) > 5 else "")
    else:
        resposta = "não" if com_destino else "não sei"
    return rotulo + "%d chaves; destinos não locais: %s" % (chaves, resposta), bool(fora) and not exemplo

def _local(destino):
    if destino in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if ":" in destino:
        return False
    return destino.endswith((".localhost", ".local", ".test")) or "." not in destino

def evidencia(raiz, gitdir, fora):
    """(estado, até que degrau, data): estado é 'vale', 'vencida', 'sem git' ou 'nenhuma'.
    Lê o que escada.py gravou na pasta de evidência; a pasta e o formato são os dele."""
    ident = hashlib.sha256(os.path.realpath(raiz).encode("utf-8", "surrogateescape")).hexdigest()[:12]
    pasta = (os.path.join(gitdir, "metodo", ident) if gitdir
             else os.path.join(tempfile.gettempdir(), "metodo-" + ident))
    try:
        _caminho = os.path.join(pasta, "escada.json")
        with open(_caminho, encoding="utf-8") as f:
            ev = json.load(f)
        degraus = {int(d["n"]): d for d in ev["degraus"]} if ev["versao"] == 2 else {}
    except (OSError, ValueError, KeyError, TypeError):
        return "nenhuma", None, ""
    if not degraus:
        return "nenhuma", None, ""
    ate = subiu_ate({n: d.get("resultado") for n, d in degraus.items()})
    data = max(str(d.get("data") or "") for d in degraus.values())
    if not gitdir:
        return "sem git", ate, data
    return ("vale" if ev.get("impressao") == impressao(raiz, fora) else "vencida"), ate, data

def texto_zonas(arquivos, zonas, com_peso):
    tocadas = zonas_tocadas(arquivos, zonas)
    if not tocadas:
        return "nenhuma zona tocada; degrau mínimo: 2"
    nomes = ", ".join("%s (%d)" % par for par in tocadas.items())
    return "zonas: %s; %sdegrau mínimo: %d" % (nomes, "peso mínimo: médio; " if com_peso else "",
                                               degrau_minimo(arquivos, zonas))


def main(args):
    pasta, completo, estrito = None, False, False
    args = list(args)
    while args:
        a = args.pop(0)
        if a in ("-h", "--help", "--ajuda"):
            print(__doc__.strip())
            return 0
        if a == "--completo":
            completo = True
        elif a == "--estrito":
            estrito = True
        elif a == "--projeto" or not a.startswith("-"):
            valor = (args.pop(0) if args else None) if a == "--projeto" else a
            if not valor or (pasta and pasta != valor):
                return parar("erro de uso: uma pasta só, depois de --projeto ou sozinha (veja --ajuda)")
            pasta = valor
        else:
            return parar("erro de uso: opção desconhecida %s (veja --ajuda)" % a)

    raiz = os.path.abspath(pasta) if pasta else os.getcwd()
    if not pasta and not os.path.isfile(os.path.join(raiz, "metodo.ini")):
        cod, saida = _git(raiz, "rev-parse", "--show-toplevel")
        topo = saida.decode("utf-8", "surrogateescape").strip()
        if cod == 0 and topo and os.path.isfile(os.path.join(topo, "metodo.ini")):
            raiz = topo
    if not os.path.isdir(raiz):
        return parar("falta: a pasta %s (não existe; confira o caminho)" % raiz)
    for qual, ruim in (("a raiz do sistema", os.sep), ("a pasta pessoal", os.path.expanduser("~"))):
        if os.path.realpath(raiz) == os.path.realpath(ruim):
            return parar("falta: uma pasta de projeto (esta é %s; combine a pasta com o dono)" % qual)

    ini = None
    try:
        if os.path.isfile(os.path.join(raiz, "metodo.ini")):
            ini = configparser.ConfigParser(interpolation=None)
            _caminho = os.path.join(raiz, "metodo.ini")
            with open(_caminho, encoding="utf-8") as f:
                ini.read_file(f)
        secao = lambda nome: dict(ini[nome]) if ini is not None and ini.has_section(nome) else {}
        documentos = dict(PADRAO, **secao("documentos"))
        zonas, escada, envio = ler_zonas(secao("zonas")), secao("escada"), secao("envio")
        orcamento = int(documentos["orcamento_instrucoes"])
    except (configparser.Error, ValueError, UnicodeDecodeError) as erro:
        return parar("falta: metodo.ini válido (não consegui ler; degrau de zona e orçamento são "
                     "números: %s)" % str(erro).splitlines()[0])
    fora = fora_da_impressao(documentos)
    S, atencao = ["projeto: " + raiz], []
    v = varrer(raiz)
    ha_codigo = bool(v["manifestos"] or v["codigo"])

    # git
    cod, saida = _git(raiz, "rev-parse", "--show-toplevel", "--git-dir")
    ha_git = cod == 0 and saida.count(b"\n") >= 2
    curso, ramo, base, gitdir, frente = None, "", "", "", []
    sem_base = "sem ramo remoto de acompanhamento"
    if not ha_git:
        S.append("git: não é repositório")
    else:
        topo, gitdir = saida.decode("utf-8", "surrogateescape").split("\n")[:2]
        gitdir = os.path.join(raiz, gitdir)
        ramo = _git(raiz, "symbolic-ref", "--short", "-q", "HEAD")[1].decode("utf-8", "replace").strip()
        curso = mudanca_em_curso(raiz) or []
        base = (envio.get("base") or "").strip()
        if not base:
            cod, saida = _git(raiz, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            base = saida.decode("utf-8", "replace").strip() if cod == 0 else ""
        if base and _git(raiz, "rev-parse", "-q", "--verify", base + "^{commit}")[0] != 0:
            base, sem_base = "", "a base %s não existe neste repositório" % base
        linha = "git: ramo %s; " % (ramo or "nenhum (HEAD solto)")
        if os.path.realpath(topo) != os.path.realpath(raiz):
            linha += "subpasta de %s; " % topo
        linha += "%d arquivos alterados; " % len(curso)
        if base:
            frente = commits(raiz, fora, base + "..HEAD")
            atras = _git(raiz, "rev-list", "--count", "HEAD.." + base, "--", ".")[1].decode().strip()
            try:
                busca = "pela última busca, em " + datetime.date.fromtimestamp(
                    os.path.getmtime(os.path.join(gitdir, "FETCH_HEAD"))).isoformat()
            except OSError:
                busca = "sem busca registrada neste repositório"
            linha += "%d commits à frente e %s atrás de %s (%s)" % (len(frente), atras or "?", base, busca)
        else:
            linha += sem_base
        S.append(linha)

    # documentos
    S.append("documentos:")
    achados, lacunas, fases, fora_do_formato, data_estado, depois = {}, [], [], 0, "", 0
    for papel in PAPEIS:
        rel, origem = (documentos.get(papel) or "").strip().strip("/") if ini is not None else "", "declarado"
        if not rel:
            rel, origem = next((r for r in (achar(raiz, n) for n in COMUNS[papel]) if r), ""), "nome comum"
        if not rel:
            S.append("  %-13s  não achei" % papel)
            continue
        texto = ler(raiz, rel)
        if texto is None:
            if os.path.exists(os.path.join(raiz, rel)):
                S.append("  %-13s  %s  %s; não li (grande, binário ou fora do projeto)" % (papel, rel, origem))
            else:
                S.append("  %-13s  %s  declarado, não existe" % (papel, rel))
                atencao.append("%s declarado em metodo.ini e inexistente: %s" % (papel, rel))
            continue
        achados[papel] = rel
        n = len(re.findall(r"\{\{.+?\}\}", texto, re.S))
        lacunas += ["%s %d" % (rel, n)] if n else []
        extra = ""
        if papel == "instrucoes":
            extra = "; %d caracteres (orçamento %d)" % (len(texto), orcamento)
            if len(texto) > orcamento:
                atencao.append("arquivo de instruções acima do orçamento: %d de %d caracteres"
                               % (len(texto), orcamento))
        elif papel == "decisoes":
            prefixo = secao("decisoes").get("prefixo", "").strip() or "ADR-"
            numeros = [int(x) for x in re.findall(
                r"^## %s(\d{3,}) · \S" % re.escape(prefixo), texto, re.M)]
            extra = "; %d registros" % len(numeros)
            if numeros:
                extra += "; último %s%03d" % (prefixo, max(numeros))
        elif papel == "roteiro":
            fases, fora_do_formato = ler_fases(texto)
            atual = next((f for f in fases if f[2] == "em andamento"), None) or next(
                (f for f in fases if f[2] == "a fazer"), None)
            if not fases:
                extra = "; não reconheci o formato das fases"
            elif completo:
                extra = "; %d fases" % len(fases)
            elif atual:
                extra = "; fase atual: %s · %s (%d de %d itens)" % (atual[0], atual[1], atual[3], atual[4])
            else:
                extra = "; todas as %d fases estão prontas" % len(fases)
            if fora_do_formato and fases:
                extra += "; %d títulos de fase fora do formato" % fora_do_formato
        elif papel == "estado":
            m = re.search(r"^## Estado em (\d{4}-\d{2}-\d{2})\s*$", texto, re.M)
            if not m:
                extra = '; sem a linha "## Estado em AAAA-MM-DD"'
            else:
                data_estado = m.group(1)
                extra = "; Estado em " + data_estado
                if ha_git:
                    depois = sum(1 for dia, codigo in commits(
                        raiz, fora, "--since=%s 00:00:00" % data_estado, "HEAD")
                        if codigo and dia > data_estado)
                    extra += "; %s commits de código depois dessa data" % (
                        depois if depois < 1000 else "1000 ou mais")
        S.append("  %-13s  %s  %s%s" % (papel, rel, origem, extra))
        if completo and papel == "roteiro":
            S += ["    fase %s · %s (%s): %d de %d itens" % tuple(f) for f in fases]
        if completo and papel == "estado":
            S.append("    listas: " + ("; ".join("%s %d" % par for par in contar_listas(texto).items())
                                       or "não reconheci os títulos das listas"))
    if ini is not None:
        n = len(re.findall(r"\{\{.+?\}\}", ler(raiz, "metodo.ini") or "", re.S))
        lacunas += ["metodo.ini %d" % n] if n else []
    total = sum(int(l.rsplit(" ", 1)[1]) for l in lacunas)
    S.append("lacunas: %d%s" % (total, " (%s)" % ", ".join(lacunas) if lacunas else ""))

    # ambiente, escada, evidência
    try:
        nomes_env = sorted(n for n in os.listdir(raiz) if n == ".env" or n.startswith(".env."))
    except OSError:
        nomes_env = []
    remotos = []
    for nome in nomes_env:
        if os.path.isfile(os.path.join(raiz, nome)):
            linha, fora_daqui = ambiente(raiz, nome)
            S.append(linha)
            remotos += [nome] if fora_daqui else []
    degraus = sorted({int(k.split(".")[0]) for k in escada if re.match(r"\d+\.(nome|comando)$", k)})
    partes = []
    for n in degraus:
        comando = (escada.get("%d.comando" % n) or "").strip()
        como = ("pendente" if not comando else "n/a: " + comando.partition(":")[2].strip()
                if re.match(r"(?i)n/a(\s*:|\s*$)", comando) else "com comando")
        partes.append("%d %s (%s)" % (n, (escada.get("%d.nome" % n) or "sem nome").strip(), como))
    S.append("escada: " + ("; ".join(partes) or ("nenhum degrau em metodo.ini" if ini is not None
                                                 else "sem metodo.ini")))
    ev, ate, data_ev = evidencia(raiz, gitdir if ha_git else "", fora)
    subiu = "nenhum degrau subido desde o 0" if ate is None else "subiu até o degrau %d" % ate
    S.append("evidência: " + {
        "nenhuma": "nenhuma",
        "vale": ("vale até o degrau %s para a árvore atual (%s)" % (ate, data_ev) if ate is not None
                 else "vale para a árvore atual, mas %s (%s)" % (subiu, data_ev)),
        "vencida": "vencida (%s em %s)" % (subiu, data_ev),
        "sem git": "sem git: não sei se a árvore mudou (%s em %s)" % (subiu, data_ev)}[ev])

    # mudança em curso e a enviar
    de_codigo, envio_arquivos = sum(1 for _, codigo in frente if codigo), None
    if not ha_git:
        S.append("mudança em curso: sem git, não há como saber")
    else:
        if curso:
            S.append("mudança em curso: %d arquivos; %s" % (len(curso), texto_zonas(curso, zonas, True)))
        envio_arquivos = a_enviar(raiz, base)
        if envio_arquivos is None:
            S.append("a enviar: sem base (%s)" % sem_base)
        elif envio_arquivos:
            quantos = "%d commits" % len(frente)
            quantos += (", só documentos à frente" if frente and not de_codigo
                        else " (%d só de documentos)" % (len(frente) - de_codigo))
            S.append("a enviar: %s%s; %s" % (quantos, " e a mudança em curso" if curso else "",
                                             texto_zonas(envio_arquivos, zonas, False)))

    # sinais
    ci = [c for c in CI if os.path.exists(os.path.join(raiz, c))]
    S.append("sinais: manifestos: %s; testes: %s; CI: %s" % (
        ", ".join(v["manifestos"][:5]) or "nenhum",
        "%d arquivos" % v["testes"] if v["testes"] else "nenhum arquivo com nome de teste",
        ", ".join(ci) or "nenhum arquivo de configuração"))
    if v["parou"]:
        S.append("aviso: varredura interrompida em %d entradas; os sinais são parciais" % LIMITE)

    # itens de atenção (lista fechada)
    no_ramo = bool(ramo) and ramo == (envio.get("ramo_que_implanta") or "").strip()
    if depois:
        atencao.append("estado mais velho que o código: %s commits de código depois de %s"
                       % (depois, data_estado))
    if total:
        atencao.append("lacunas por preencher: %d" % total)
    if ha_git:
        nunca = (envio.get("nunca_enviar") or NUNCA_ENVIAR).split(",")
        rastreados = [n for n in _nomes(_git(raiz, "ls-files", "-z", "--", ".")[1]) if casa_lista(n, nunca)]
        if rastreados:
            atencao.append("arquivo que casa com nunca_enviar está rastreado pelo git: "
                           + ", ".join(rastreados[:5]))
    if remotos:
        atencao.append("arquivo de ambiente com destino não local (%s): não rode comando do projeto "
                       "antes de references/adocao.md §2" % ", ".join(remotos))
    if ha_codigo and ini is not None:
        vazias = [nome for nome, (_d, padroes) in zonas.items() if not padroes]
        if vazias:
            atencao.append("a classificação por caminho está desligada para: " + ", ".join(vazias))
        sem = [str(n) for n in (0, 1, 2) if not (escada.get("%d.comando" % n) or "").strip()]
        if sem:
            atencao.append("degrau %s sem comando: o portão do commit vai sair com 3" % ", ".join(sem))
    if ha_git and not curso and de_codigo and envio_arquivos:
        exigido = degrau_minimo(envio_arquivos, zonas)
        if ev != "vale" or ate is None or ate < exigido:
            atencao.append("evidência abaixo do exigido para o que está a enviar: %s; exigido %d" % (
                "vale até o degrau %d" % ate if ev == "vale" and ate is not None else
                "nenhum degrau subido desde o 0" if ev == "vale" else ev, exigido))
    if no_ramo and frente and curso:
        atencao.append("no ramo que implanta, com commits a enviar e %d arquivos alterados: "
                       "o que não foi commitado não vai no envio" % len(curso))
    em_andamento = [f[0] for f in fases if f[2] == "em andamento"]
    if len(em_andamento) > 1:
        atencao.append("mais de uma fase em andamento: " + ", ".join(em_andamento))
    if "roteiro" in achados and (not fases or fora_do_formato):
        atencao.append("roteiro não reconhecido: títulos de fase fora do formato "
                       "'## Fase <n> · <nome> (<situação>)'")
    if achados and ini is None:
        atencao.append("documentos presentes sem metodo.ini")
    if v["parou"]:
        atencao.append("varredura interrompida no limite de %d entradas" % LIMITE)
    S += ["atenção:"] + ["  - " + item for item in atencao] if atencao else ["atenção: nenhum item"]

    # situação provável, pela primeira regra que servir
    iniciada = any(f[2] in ("em andamento", "pronta") for f in fases)
    falta = [nome for nome, tem in (("metodo.ini", ini is not None),
                                    ("arquivo de instruções", "instrucoes" in achados),
                                    ("estado", "estado" in achados)) if not tem]
    tocou = bool(curso) and bool(zonas_tocadas(curso, zonas))
    if not ha_codigo and not iniciada:
        letra, sinal = "A", "sem código e sem fase em andamento ou pronta"
        leia = "SKILL.md §3" if achados or ini is not None else "references/entrevista.md"
    elif ha_codigo and falta:
        letra, sinal, leia = "B", "há código e falta: " + ", ".join(falta), "references/adocao.md"
    elif no_ramo and not curso and de_codigo:
        letra, leia = "D", "references/producao.md"
        sinal = "no ramo que implanta, árvore limpa, %d commits de código à frente de %s" % (de_codigo, base)
    elif depois:
        letra, leia = "E", "references/retomada.md"
        sinal = "estado de %s; %s commits de código depois" % (data_estado, depois)
    else:
        letra, sinal = "C", "documentos presentes" + ("; mudança em zona sensível" if tocou else "")
        leia = "SKILL.md §4" + ("; references/pesos.md §2" if tocou else "")
        leia += "; para enviar: references/producao.md" if no_ramo and de_codigo else ""
    S.append("situação provável: %s (%s)" % (letra, sinal))
    S.append("leia: " + leia)
    S.append("não conferi: ambiente remoto, CI, se os comandos da escada funcionam, variáveis "
             "exportadas no shell; classifico zona só por caminho"
             + ("; a varredura parou em %d entradas" % LIMITE if v["parou"] else ""))
    print("\n".join(S))
    return 1 if estrito and atencao else 0


if __name__ == "__main__":
    for fluxo in (sys.stdout, sys.stderr):  # terminal sem UTF-8 não derruba a saída
        fluxo.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
