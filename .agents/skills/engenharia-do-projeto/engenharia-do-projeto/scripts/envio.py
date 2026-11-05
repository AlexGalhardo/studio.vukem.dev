#!/usr/bin/env python3
"""Confere o que sairia no próximo envio: posição, arquivo proibido, segredo e evidência. Só lê.

uso:
  envio.py [--projeto <pasta>] [--base <ref>] [--tudo]
      uma linha por conferência (ok, ACHADO ou aviso:) e a lista dos commits que sairiam.
      A base é --base; sem ela, [envio] base de metodo.ini; sem ela, o ramo remoto de
      acompanhamento. --tudo procura segredo em todos os arquivos rastreados, e não só nas
      linhas que saem. Na cadeia do envio: escada.py --evidencia && envio.py && git push
  saída 0: nenhum ACHADO. 1: algum ACHADO. 2: não é repositório, sem base ou uso errado.

à mão:
  git status                (o que não foi commitado não vai no envio)
  git log <base>..HEAD      (os commits que sairiam; se a base andou, integre antes)
  git diff <base>...HEAD    (leia linha a linha, procurando chave, senha e arquivo de ambiente)
  git ls-files              (há arquivo de ambiente, .pem ou .key rastreado?)

recusa: enviar, buscar ou commitar; imprimir mais que os quatro primeiros caracteres de um valor;
  corrigir o que achou; "limpar" o histórico.
"""
import configparser, hashlib, json, os, platform, re, shlex, shutil, subprocess, sys, time

def _py():
    """Como se chama o Python na linha de comando deste sistema (no Windows, `python3` abre a loja)."""
    return "py -3" if platform.system() == "Windows" else "python3"

def _citar(texto):
    """Caminho pronto para a linha de comando do sistema; no Windows, aspas duplas."""
    if platform.system() == "Windows":
        return '"%s"' % texto if " " in texto else texto
    return shlex.quote(texto)

NAO_CONFERI = ("não conferi: segredo fora dos padrões conhecidos (não achar não prova que não "
               "há); o remoto depois da última busca")
DOCUMENTOS = {"especificacao": "ESPECIFICACAO.md", "instrucoes": "CLAUDE.md",
              "decisoes": "docs/decisoes.md", "roteiro": "docs/ROTEIRO.md",
              "estado": "docs/ESTADO.md", "leiame": "README.md", "planos": "docs/planos",
              "notas": "docs/notas"}  # o padrão de [documentos] para chave ausente
NUNCA_ENVIAR = ".env, .env.*, !.env.example, *.pem, *.key"  # o padrão de [envio] nunca_enviar
# Os prefixos são montados por concatenação: este arquivo, copiado para o projeto e commitado,
# não pode ser acusado por si mesmo.
_B = "[A-Za-z0-9_-]"
PADROES = [
    ("bloco de chave privada", re.compile("-----BEGIN [A-Z ]*PRIV" + "ATE KEY-----")),
    ("chave de API com prefixo conhecido", re.compile(
        r"\b(?:[spr]" + r"k_(?:live|test)_[A-Za-z0-9]{16,}|s" + r"k-(?=" + _B + r"*\d)" + _B
        + r"{20,}|whs" + r"ec_" + _B + r"{16,}|AI" + r"za" + _B + r"{30,}|xox[abprs]-" + _B
        + r"{10,})")),
    ("token em três partes de base64", re.compile(
        r"\bey" + r"J" + _B + r"{8,}\." + _B + r"{8,}\." + _B + r"{8,}")),
    ("chave de acesso de nuvem", re.compile(r"\bA[KS]" + r"IA[0-9A-Z]{16}\b")),
    ("token de serviço de repositório", re.compile(
        r"\b(?:gh[pousr]" + r"_[A-Za-z0-9]{30,}|git" + r"hub_pat_" + _B + r"{30,}|glp" + r"at-"
        + _B + r"{20,})")),
    ("endereço com usuário e senha embutidos", re.compile(
        r"\b[a-z][a-z0-9+.-]*://[^\s/:@\"'<>]*:([^\s/@\"']+)@[^\s/\"'<>]+")),
]
_PALAVRAS = "secret|token|key|password|senha|chave"
ATRIBUICOES = [  # valor literal: entre aspas, ou sem aspas numa linha NOME=valor de ambiente
    re.compile(r"(?i)(?<![\w.-])[\w.-]*(?:" + _PALAVRAS + r")[\w.-]*[\"']?\s*[:=]\s*"
               r"[\"']([^\"'\s]{20,})[\"']"),
    re.compile(r"^\s*(?:export\s+)?[A-Z0-9_]*(?:" + _PALAVRAS.upper() + r")[A-Z0-9_]*="
               r"([^\s\"'#]{20,})\s*$"),
]

class Sair(Exception):
    """Termina com o código dado; `falta` vai para stderr; `proximo` vira a linha `próximo:`."""
    def __init__(self, codigo, falta=None, proximo=None):
        Exception.__init__(self)
        self.codigo, self.falta, self.proximo = codigo, falta, proximo

# --- Código de referência do método, igual em todo script que o usa: não altere a lógica. ---

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
    r = subprocess.run(["git", "-C", raiz] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=amb)
    return r.returncode, r.stdout

def _nomes(saida):
    return [n.decode("utf-8", "surrogateescape") for n in saida.split(b"\0") if n]

def fora_da_impressao(documentos):
    """Padrões dos documentos do método, que não entram na impressão digital.
    documentos: o dicionário da seção [documentos] de metodo.ini."""
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
    """Impressão digital do conteúdo da árvore de trabalho, sem os documentos do método.
    Não muda com o commit nem com edição de documento listado em `fora`."""
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
    """Arquivos alterados, preparados e não rastreados da árvore de trabalho (relativos à
    raiz do projeto). Não inclui commits. Devolve None se não há git."""
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
    """Arquivos dos commits à frente da base, mais a mudança em curso. Devolve None se não
    há git, se não há base ou se a base não existe."""
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
    """resultados: {n: 'ok' | 'n/a' | 'falhou' | 'pendente'}. Maior n tal que 0..n são todos
    'ok' ou 'n/a'. None se o degrau 0 não é um dos dois."""
    n, ate = 0, None
    while resultados.get(n) in ("ok", "n/a"):
        ate, n = n, n + 1
    return ate

# --- Fim do código de referência. ---

def _texto(saida):
    return saida.decode("utf-8", "surrogateescape").strip()

def _limpo(texto):
    return re.sub(r"[\x00-\x1f\x7f]", " ", texto)

def ler_opcoes(argv):
    o, i = {"projeto": None, "base": None, "tudo": False}, 0
    while i < len(argv):
        nome, igual, valor = argv[i].partition("=")
        if nome in ("--projeto", "--base"):
            if not igual:
                i, valor = i + 1, (argv[i + 1] if i + 1 < len(argv) else "")
            if not valor:
                raise Sair(2, "o valor de %s (veja --ajuda)" % nome)
            o[nome[2:]] = valor
        elif argv[i] == "--tudo":
            o["tudo"] = True
        else:
            raise Sair(2, 'uma opção conhecida no lugar de "%s" (veja --ajuda)' % argv[i])
        i += 1
    return o

def achar_projeto(pasta):
    """Devolve (raiz, configuração). Sem --projeto e sem metodo.ini aqui, tenta a raiz do git."""
    raiz = os.path.realpath(pasta or os.getcwd())
    if pasta and not os.path.isdir(raiz):
        raise Sair(2, "a pasta %s (não existe: confira o caminho de --projeto)" % pasta)
    if not pasta and not os.path.isfile(os.path.join(raiz, "metodo.ini")):
        cod, saida = _git(raiz, "rev-parse", "--show-toplevel")
        if cod == 0 and os.path.isfile(os.path.join(_texto(saida), "metodo.ini")):
            raiz = os.path.realpath(_texto(saida))
    cfg = configparser.ConfigParser(interpolation=None)
    try:
        _caminho = os.path.join(raiz, "metodo.ini")
        with open(_caminho, encoding="utf-8") as f:
            cfg.read_file(f)
    except FileNotFoundError:
        raise Sair(2, "metodo.ini (rode montar.py)")
    except (configparser.Error, UnicodeDecodeError, OSError) as erro:
        raise Sair(2, "metodo.ini que se leia (%s)" % " ".join(str(erro).split()))
    return raiz, cfg

def ler_evidencia(raiz):
    """Devolve (impressão, {n: resultado}) da evidência que escada.py gravou, ou None."""
    ident = hashlib.sha256(raiz.encode("utf-8", "surrogateescape")).hexdigest()[:12]
    cod, saida = _git(raiz, "rev-parse", "--git-dir")
    pasta = os.path.join(os.path.normpath(os.path.join(raiz, _texto(saida))), "metodo", ident)
    try:
        _caminho = os.path.join(pasta, "escada.json")
        with open(_caminho, encoding="utf-8") as f:
            dados = json.load(f)
        itens = {int(d["n"]): d["resultado"] for d in dados["degraus"]}
        return (dados["impressao"], itens) if dados["versao"] == 2 and itens else None
    except (OSError, ValueError, KeyError, TypeError):
        return None

def segredos(linha):
    """Devolve [(tipo, valor)] dos padrões de segredo que aparecem na linha."""
    linha, achados = linha[:4000], []
    for tipo, padrao in PADROES:
        for m in padrao.finditer(linha):
            if not (m.groups() and re.search(r"[<>{}$*]", m.group(1))):  # senha que é lacuna
                achados.append((tipo, m.group(0)))
    for padrao in ATRIBUICOES if not achados else ():
        for m in padrao.finditer(linha):
            v = m.group(1)
            classes = sum(1 for c in ("[a-z]", "[A-Z]", "[0-9]") if re.search(c, v))
            if classes >= 2 and not re.search(r"[<>{}$*]|://", v):  # literal, e não lacuna
                achados.append(("atribuição de valor a nome de segredo", v))
    return achados

def linhas_que_saem(raiz, base):
    """Gera (arquivo, linha, texto, commit) de cada linha acrescentada nos commits a enviar.
    Lê commit por commit: linha acrescentada e depois apagada continua no histórico que sai."""
    cod, saida = _git(raiz, "-c", "core.quotepath=off", "log", "-p", "-U0", "--no-color",
                      "--no-renames", "--no-ext-diff", "--no-textconv", "--relative",
                      "--format=%x01%h", base + "..HEAD", "--", ".")
    commit, arquivo, n, cabecalho = "", None, 0, True
    for bruta in saida.split(b"\n"):
        l = bruta.decode("utf-8", "replace")
        if l.startswith("\x01"):
            commit, arquivo = l[1:], None
        elif l.startswith("diff --git "):
            arquivo, cabecalho = None, True
        elif cabecalho and l.startswith("+++ "):
            arquivo = None if l[4:] == "/dev/null" else l[4:].rstrip("\t").strip('"')[2:]
        elif l.startswith("@@ ") and re.match(r"@@ -\S+ \+(\d+)", l):
            cabecalho, n = False, int(re.match(r"@@ -\S+ \+(\d+)", l).group(1))
        elif not cabecalho and arquivo and l.startswith("+"):
            yield arquivo, n, l[1:], commit
            n += 1

def linhas_rastreadas(raiz, arquivos, nao_lidos):
    """Gera (arquivo, linha, texto, "") de cada arquivo rastreado, como está na árvore."""
    for arquivo in arquivos:
        caminho = os.path.join(raiz, arquivo)
        try:
            if os.path.islink(caminho) or not os.path.isfile(caminho):
                continue
            with open(caminho, "rb") as f:
                dado = f.read(1048577)
        except OSError:
            dado = b"\0"
        if len(dado) > 1048576 or b"\0" in dado[:8192]:
            nao_lidos.append(arquivo)
            continue
        for n, texto in enumerate(dado.decode("utf-8", "replace").split("\n"), 1):
            yield arquivo, n, texto, ""

def executar(argv, notas):
    o = ler_opcoes(argv)
    if not shutil.which("git"):
        raise Sair(2, "git (instale: sem ele não há envio a conferir)")
    raiz, cfg = achar_projeto(o["projeto"])
    if _git(raiz, "rev-parse", "--is-inside-work-tree")[0] != 0:
        raise Sair(2, "repositório git (esta pasta não é um: não há envio a conferir)")
    if _git(raiz, "rev-parse", "--verify", "--quiet", "HEAD")[0] != 0:
        raise Sair(2, "um commit (o repositório ainda não tem nenhum: não há o que enviar)")
    envio = dict(cfg["envio"]) if cfg.has_section("envio") else {}
    lista = lambda texto: [p.strip() for p in texto.split(",") if p.strip()]
    nunca, excecoes = lista(envio.get("nunca_enviar", NUNCA_ENVIAR)), \
        lista(envio.get("excecoes_de_segredo", ""))
    base = o["base"] or (envio.get("base") or "").strip()
    if not base:
        cod, saida = _git(raiz, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        base = _texto(saida) if cod == 0 else ""
    if not base:
        raise Sair(2, "base (este ramo não tem ramo remoto de acompanhamento: passe --base <ref> "
                      "ou preencha [envio] base em metodo.ini)")
    if base.startswith("-") or \
            _git(raiz, "rev-parse", "--verify", "--quiet", base + "^{commit}")[0] != 0:
        raise Sair(2, 'a base "%s" (não existe neste repositório: confira o nome; se nunca foi '
                      'buscada, rode git fetch)' % base)
    try:
        zonas = ler_zonas(dict(cfg["zonas"]) if cfg.has_section("zonas") else {})
    except ValueError:
        raise Sair(2, "[zonas] com <nome>.degrau inteiro em metodo.ini")
    documentos = dict(cfg["documentos"]) if cfg.has_section("documentos") else {}
    fora, achados = fora_da_impressao(dict(DOCUMENTOS, **documentos)), 0
    if _texto(_git(raiz, "rev-parse", "--show-prefix")[1]):
        notas.append("arquivos fora da pasta do projeto, que é subpasta do repositório")

    # 1. Árvore de trabalho.
    curso = mudanca_em_curso(raiz)
    print("aviso: %d arquivos alterados na árvore de trabalho: o que não foi commitado não vai "
          "no envio" % len(curso) if curso else "ok árvore de trabalho limpa")

    # 2. Posição. A contagem é do ramo inteiro: o envio leva o ramo, e não só a pasta.
    contagem = _git(raiz, "rev-list", "--left-right", "--count", base + "...HEAD")[1].split()
    if len(contagem) != 2:
        raise Sair(2, "a comparação de HEAD com %s (o git não respondeu: confira a base)" % base)
    atras, frente = int(contagem[0]), int(contagem[1])
    marca = os.path.join(raiz, _texto(_git(raiz, "rev-parse", "--git-path", "FETCH_HEAD")[1]))
    busca = "sem registro de busca neste clone"
    if os.path.isfile(marca):
        busca = "pela última busca, em " + time.strftime(
            "%Y-%m-%d", time.localtime(os.path.getmtime(marca)))
    campos = _nomes(_git(raiz, "log", "--format=", "--name-status", "-z", "--no-renames",
                         "--relative", base + "..HEAD", "--", ".")[1])
    campos = [c.strip("\n") for c in campos if c.strip("\n")]
    tocados, i = [], 0
    while i + 1 < len(campos):  # pares: situação (A, M, D...), caminho
        if re.match(r"^[A-Z]\d*$", campos[i]):
            tocados.append((campos[i][0], campos[i + 1]))
            i += 1
        i += 1
    so_documentos = bool(tocados) and all(any(casa(c, p) for p in fora) for _, c in tocados)
    achados += 1 if atras else 0
    print("%s posição: à frente: %d; atrás: %d de %s (%s)%s" % (
        "ACHADO" if atras else "ok", frente, atras, base, busca,
        "; só documentos à frente" if so_documentos else ""))

    # 3 e 4. Arquivo que nunca se envia: nos commits a enviar, e já rastreado.
    saem = sorted(set(c for s, c in tocados if s != "D" and casa_lista(c, nunca)))
    rastreados = _nomes(_git(raiz, "ls-files", "-z", "--cached", "--", ".")[1])
    ja = [c for c in rastreados if casa_lista(c, nunca) and c not in saem]
    for c in saem:
        print("ACHADO sairia no envio e casa com nunca_enviar: " + _limpo(c))
    for c in ja:
        print("ACHADO já rastreado pelo git e casa com nunca_enviar: " + _limpo(c))
    if not saem:
        print("ok nenhum arquivo dos commits a enviar casa com nunca_enviar")
    if not ja:
        print("ok nenhum outro arquivo rastreado casa com nunca_enviar")

    # 5. Padrão de segredo nas linhas acrescentadas (com --tudo, também nos rastreados).
    nao_lidos, vistos, excetuados, livres, lidas, segredo = [], set(), [], {}, 0, 0
    fontes = [linhas_que_saem(raiz, base)]
    if o["tudo"]:
        fontes.append(linhas_rastreadas(raiz, rastreados, nao_lidos))
    for fonte in fontes:
        for arquivo, n, texto, commit in fonte:
            if arquivo not in livres:
                livres[arquivo] = not any(casa(arquivo, p) for p in excecoes)
                excetuados += [] if livres[arquivo] else [arquivo]
            if not livres[arquivo]:
                continue
            lidas += 1
            for tipo, valor in segredos(texto):
                if (arquivo, tipo, valor) in vistos:
                    continue
                vistos.add((arquivo, tipo, valor))
                segredo += 1
                if segredo <= 30:
                    print("ACHADO segredo: %s:%d  %s  %s… (%d caracteres)%s" % (
                        _limpo(arquivo), n, tipo, _limpo(valor[:4]), len(valor),
                        "  commit " + commit if commit else ""))
    if segredo > 30:
        print("ACHADO segredo: e mais %d, não mostrados" % (segredo - 30))
    if not segredo:
        print("ok nenhum padrão de segredo em %d linhas (%s)" % (lidas, "as que saem e os "
              "arquivos rastreados" if o["tudo"] else "só as acrescentadas nos commits a enviar"))
    for arquivo in excetuados[:5]:
        print("aviso: exceção declarada: " + _limpo(arquivo))
    if len(excetuados) > 5:
        print("aviso: exceção declarada: e mais %d arquivos" % (len(excetuados) - 5))
    if nao_lidos:
        notas.append("%d arquivos rastreados com mais de 1 MB ou binários" % len(nao_lidos))
    achados += len(saem) + len(ja) + segredo

    # 6. O ramo que implanta.
    ramo, implanta = _texto(_git(raiz, "rev-parse", "--abbrev-ref", "HEAD")[1]), \
        (envio.get("ramo_que_implanta") or "").strip()
    if not implanta:
        print("aviso: [envio] ramo_que_implanta está vazio: não sei se enviar este ramo implanta")
    elif ramo == implanta:
        print("aviso: enviar para %s implanta: só com a lista que o dono autorizou" % ramo)
    else:
        print("ok o ramo %s não é o que implanta (%s)" % (ramo, implanta))

    # 7. Evidência da escada. Aqui é aviso: o portão é escada.py --evidencia, antes na cadeia.
    exigido, n = degrau_minimo(a_enviar(raiz, base) or [], zonas), None
    guardada = ler_evidencia(raiz)
    if not guardada:
        vale = "nenhuma"
    elif guardada[0] != impressao(raiz, fora):
        vale = "vencida (a árvore mudou desde a subida)"
    else:
        n = subiu_ate(guardada[1])
        vale = "sem nenhum degrau subido desde o 0" if n is None else "vale até o degrau %d" % n
    coberta = n is not None and n >= exigido
    print(("ok evidência: %s; exigido %d" if coberta else "aviso: evidência %s; exigido %d")
          % (vale, exigido))

    print("commits que sairiam: %d" % frente)
    saida = _git(raiz, "log", "--format=%h %s", "-n", "10", base + "..HEAD")[1]
    for l in _texto(saida).split("\n") if frente else ():
        print("  " + _limpo(l)[:110])
    if frente > 10:
        print("  e mais %d" % (frente - 10))
    if achados:
        motivos = ["integre os commits de %s antes, sem forçar o envio" % base] if atras else []
        if saem or ja or segredo:
            motivos.append("leve o que foi achado ao dono antes de corrigir: o que entrou num "
                           "commit segue no histórico mesmo depois de apagado, e chave que "
                           "apareceu se troca (references/ambientes.md §2 e §3)")
        raise Sair(1, proximo="não envie. " + "; ".join(motivos))
    if not coberta:
        escada = os.path.join(os.path.dirname(sys.argv[0]), "escada.py")
        raise Sair(0, proximo="%s %s --a-enviar" % (_py(), _citar(escada)))

def main(argv):
    for canal in (sys.stdout, sys.stderr):
        if hasattr(canal, "reconfigure"):
            canal.reconfigure(errors="replace")
    if any(a in ("-h", "--help", "--ajuda") for a in argv):
        print(__doc__.strip())
        return 0
    codigo, proximo, falta, notas = 0, None, None, []
    try:
        executar(argv, notas)
    except Sair as fim:
        codigo, proximo, falta = fim.codigo, fim.proximo, fim.falta
    except OSError as erro:  # pasta sem permissão, arquivo que sumiu no meio
        codigo, falta = 2, "ler sem erro (%s)" % erro
    if falta:
        sys.stdout.flush()
        print("falta: " + falta, file=sys.stderr, flush=True)
    if proximo:
        print("próximo: " + proximo)
    print("; ".join([NAO_CONFERI] + notas))
    return codigo

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
