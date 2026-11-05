#!/usr/bin/env python3
"""Sobe a escada de verificação do projeto, para no primeiro degrau que falhar e grava a evidência.

uso:
  escada.py [--projeto <pasta>] [--ate <n> | --so <n> | --exigido | --a-enviar]
      roda os comandos de [escada] de metodo.ini em ordem (sem opção, os degraus 0 a 5); sai uma
      linha por degrau e a linha "escada:", para o relato e para o estado. --exigido vai até o
      degrau das zonas tocadas pela mudança em curso; --a-enviar, das tocadas pelo que está a
      enviar; nos dois, sem zona tocada, até o 2. --so <n> roda só aquele degrau.
  escada.py [--projeto <pasta>] --evidencia [--ate <n>]
      não roda nada: até que degrau a evidência vale para a árvore atual, e o degrau exigido.
  escada.py [--projeto <pasta>] --listar
      não roda nada: os degraus, os comandos e a pasta de evidência.
  saída 0: passou. 1: um degrau falhou. 2: uso errado ou falta algo. 3: passou, mas não prova
      (degrau pedido sem comando; evidência vencida, ausente ou abaixo do exigido).

à mão:
  Rode os comandos de [escada] de metodo.ini em ordem, ligados por &&, e não por ponto e vírgula.
  Pare no primeiro que falhar: degrau de cima não prova nada sobre degrau de baixo quebrado.
  Anote a data, o commit, até que degrau subiu, quais ainda não existem e quais não rodou.
  Editou código ou metodo.ini depois? A anotação venceu: suba de novo antes de citar.

recusa: seguir depois de uma falha; contar degrau pendente como aprovado; rodar comando com git
  push ou git commit; duas subidas ao mesmo tempo; rodar o que não está em metodo.ini; contar
  testes por conta própria (quem cita número cita o que está nas linhas mostradas).
"""
import configparser, hashlib, json, os, platform, re, shlex, shutil
import signal, subprocess, sys, tempfile, time

def _py():
    """Como se chama o Python na linha de comando deste sistema (no Windows, `python3` abre a loja)."""
    return "py -3" if platform.system() == "Windows" else "python3"

def _citar(texto):
    """Caminho pronto para a linha de comando do sistema; no Windows, aspas duplas."""
    if platform.system() == "Windows":
        return '"%s"' % texto if " " in texto else texto
    return shlex.quote(texto)

JANELA = platform.system() == "Windows"


def shell_do_sistema(comando):
    """O comando do degrau pela linha de comando do sistema, sempre como lista de argumentos.
    No Windows é o interpretador do COMSPEC; nos outros, o sh. Nunca pelo atalho do shell."""
    if JANELA:
        return [os.environ.get("COMSPEC") or "cmd.exe", "/d", "/c", comando]
    return [shutil.which("sh") or "sh", "-c", comando]


def processo_vivo(pid):
    """Diz se o processo existe. No Windows os.kill MATA o processo mesmo com sinal 0, então lá
    a pergunta vai ao sistema por ctypes."""
    if JANELA:
        import ctypes
        kernel = ctypes.windll.kernel32
        alca = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not alca:
            return False
        codigo = ctypes.c_ulong()
        vivo = bool(kernel.GetExitCodeProcess(alca, ctypes.byref(codigo))) and codigo.value == 259
        kernel.CloseHandle(alca)
        return vivo
    try:
        os.kill(pid, 0)  # sinal 0: só pergunta se o processo existe
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def matar_arvore(p):
    """Derruba o processo do degrau e o que ele abriu, no Windows e fora dele."""
    if JANELA:
        matar = shutil.which("taskkill")
        if matar:
            subprocess.run([matar, "/F", "/T", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    else:
        try:
            os.killpg(os.getpgid(p.pid), getattr(signal, "SIGKILL", signal.SIGTERM))
            return
        except OSError:
            pass
    p.kill()

NAO_CONFERI = ("não conferi: se cada comando prova o que o degrau promete; o que os comandos "
               "fazem por dentro; os degraus 6 (revisão) e 7 (conferência em produção); o CI; "
               "classifico zona só por caminho")
DOCUMENTOS = {"especificacao": "ESPECIFICACAO.md", "instrucoes": "CLAUDE.md",
              "decisoes": "docs/decisoes.md", "roteiro": "docs/ROTEIRO.md",
              "estado": "docs/ESTADO.md", "leiame": "README.md", "planos": "docs/planos",
              "notas": "docs/notas"}  # o padrão de [documentos] para chave ausente
# "git" como palavra e, no mesmo comando simples, "push" ou "commit" como palavra.
RECUSADO = re.compile(r"(?:^|[\s;&|(`/])git(?:\s+[^\s;&|]+)*?\s+(?:push|commit)(?=$|[\s;&|)`])")

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

def ler_opcoes(argv):
    o, i = {"projeto": None, "ate": None, "so": None, "modo": []}, 0
    while i < len(argv):
        nome, igual, valor = argv[i].partition("=")
        if nome in ("--projeto", "--ate", "--so"):
            if not igual:
                i, valor = i + 1, (argv[i + 1] if i + 1 < len(argv) else "")
            if nome != "--projeto" and valor in tuple("012345"):
                o[nome[2:]] = int(valor)
                o["modo"].append(nome[2:])
            elif nome == "--projeto" and valor:
                o["projeto"] = valor
            else:
                raise Sair(2, "o valor de %s (uma pasta em --projeto; um degrau de 0 a 5 em --ate "
                              "e --so: 6 é a revisão e 7, a conferência em produção)" % nome)
        elif argv[i] in ("--exigido", "--a-enviar", "--evidencia", "--listar"):
            o["modo"].append(argv[i][2:])
        else:
            raise Sair(2, 'uma opção conhecida no lugar de "%s" (veja --ajuda)' % argv[i])
        i += 1
    modo = set(o["modo"])
    if len(modo) != len(o["modo"]) or not (modo <= {"evidencia", "ate"} or len(modo) <= 1):
        raise Sair(2, "uma forma de uso só (--ate, --so, --exigido e --a-enviar não se combinam; "
                      "--evidencia aceita só --ate; --listar vai sozinha)")
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

def ler_escada(cfg):
    """Os degraus 0 a 5, em ordem. Degrau sem a chave N.comando é pendente."""
    if not cfg.has_section("escada"):
        raise Sair(2, "a seção [escada] em metodo.ini (copie de assets/modelos/metodo.ini)")
    sec, degraus = dict(cfg["escada"]), []
    for chave in sec:
        if not re.match(r"^[0-5]\.(nome|comando|precisa|limite)$", chave):
            raise Sair(2, '[escada] só com N.nome, N.comando, N.precisa e N.limite, N de 0 a 5 '
                          '(achei "%s"; 6 é a revisão e 7, a conferência em produção)' % chave)
    for n in range(6):
        ler = lambda chave: (sec.get("%d.%s" % (n, chave)) or "").strip()
        d = {"n": n, "nome": ler("nome") or "sem nome", "comando": ler("comando"),
             "precisa": ler("precisa"), "limite": ler("limite") or "1800", "tipo": "comando"}
        if not d["limite"].isdigit() or int(d["limite"]) < 1:
            raise Sair(2, "[escada] %d.limite em segundos inteiros, maior que zero" % n)
        d["limite"] = int(d["limite"])
        if not d["comando"]:
            d["tipo"] = "pendente"
        elif re.match(r"(?i)^n/a\s*(:|$)", d["comando"]):
            d["tipo"], d["motivo"] = "n/a", d["comando"].partition(":")[2].strip()
            if not d["motivo"]:
                raise Sair(2, 'o motivo em [escada] %d.comando (escreva "n/a: <motivo>")' % n)
        elif RECUSADO.search(d["comando"]):
            raise Sair(2, "[escada] %d.comando sem git push e sem git commit (a escada só "
                          "verifica: commit e envio se ligam a ela por &&, fora dela)" % n)
        degraus.append(d)
    return degraus

def pasta_de_evidencia(raiz):
    ident = hashlib.sha256(raiz.encode("utf-8", "surrogateescape")).hexdigest()[:12]
    cod, saida = _git(raiz, "rev-parse", "--git-dir")
    if cod != 0:
        return os.path.join(tempfile.gettempdir(), "metodo-" + ident)
    return os.path.join(os.path.normpath(os.path.join(raiz, _texto(saida))), "metodo", ident)

def ler_evidencia(pasta):
    """Devolve (impressão, {n: item}) ou None. Só entende a versão 2."""
    try:
        _caminho = os.path.join(pasta, "escada.json")
        with open(_caminho, encoding="utf-8") as f:
            dados = json.load(f)
        itens = {int(d["n"]): d for d in dados["degraus"]
                 if d["resultado"] and d["data"] and d["hora"] and d["commit"]}
        return (dados["impressao"], itens) if dados["versao"] == 2 and itens else None
    except (OSError, ValueError, KeyError, TypeError):
        return None

def travar(pasta):
    """Cria a trava com o número deste processo. Trava de processo vivo: código 2."""
    caminho = os.path.join(pasta, "trava")
    for _ in range(2):
        try:
            fd = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            pid = "?"
            try:
                with open(caminho, encoding="utf-8") as f:
                    pid = int(f.read().strip())
                if pid > 0 and not processo_vivo(pid):
                    print("aviso: removi a trava de um processo que não existe mais (%d)" % pid)
                    os.remove(caminho)
                    continue
            except (OSError, ValueError):
                pass
            break
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(str(os.getpid()))
        return caminho
    raise Sair(2, "a trava livre (outra subida em curso, processo %s: espere terminar. Sem "
                  "subida nenhuma em curso, apague %s)" % (pid, caminho))

def rodar(raiz, d, registro):
    """Roda o comando do degrau pela linha de comando do sistema, na raiz (no Windows, o
    interpretador do COMSPEC; fora dele, o sh). Devolve (código, segundos, o que houve)."""
    inicio, houve = time.time(), ""
    extras = {} if JANELA else {"start_new_session": True}  # só existe fora do Windows
    with open(registro, "wb") as saida:
        p = subprocess.Popen(shell_do_sistema(d["comando"]), cwd=raiz, stdin=subprocess.DEVNULL,
                             stdout=saida, stderr=subprocess.STDOUT, **extras)
        try:
            codigo = p.wait(timeout=d["limite"])
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as erro:
            houve = "tempo esgotado: limite de %d s" % d["limite"]
            if isinstance(erro, KeyboardInterrupt):
                houve = "interrompido"
            matar_arvore(p)  # o interpretador e o que ele abriu
            p.wait()
            codigo = None
    return codigo, int(round(time.time() - inicio)), houve

def ultimas(registro, quantas):
    """As últimas linhas não vazias do registro, sem cor nem caractere de controle, e se há
    mais para ler no arquivo do que foi mostrado."""
    try:
        with open(registro, "rb") as f:
            tamanho = f.seek(0, os.SEEK_END)
            f.seek(max(0, tamanho - 65536))
            texto = f.read().decode("utf-8", "replace")
    except OSError:
        return [], False
    texto = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", texto)  # sequências de cor
    texto = texto.replace("\r", "\n").replace("\t", "    ")
    linhas = [re.sub(r"[\x00-\x1f\x7f]", "", l).rstrip() for l in texto.split("\n")]
    linhas = [l[:200] for l in linhas if l.strip()]
    return linhas[-quantas:], len(linhas) > quantas or tamanho > 65536

def linha_do_relato(degraus, itens):
    """A linha `escada:`, calculada sobre a evidência somada da árvore atual."""
    res = {n: i["resultado"] for n, i in itens.items()}

    def lista(qual):  # degrau sem resultado guardado: o que metodo.ini diz dele
        achados = [str(d["n"]) for d in degraus if qual == (res.get(d["n"]) or (
            d["tipo"] if d["tipo"] != "comando" else "não rodado"))]
        return ", ".join(achados) or "nenhum"

    ultimo, n = max(itens.values(), key=lambda i: (i["data"], i["hora"])), subiu_ate(res)
    ate = "nenhum degrau subido desde o 0" if n is None else \
        "subiu até o degrau %d (%s)" % (n, degraus[n]["nome"])
    linha = "escada: %s, commit %s, %s; n/a: %s; pendentes: %s; não rodados: %s" % (
        ultimo["data"], ultimo["commit"], ate, lista("n/a"), lista("pendente"), lista("não rodado"))
    return linha + ("" if lista("falhou") == "nenhum" else "; falhou: " + lista("falhou"))

def exigido(raiz, cfg, do_envio):
    """Degrau mínimo da mudança em curso, ou do que está a enviar, e a linha que o explica."""
    try:
        zonas = ler_zonas(dict(cfg["zonas"]) if cfg.has_section("zonas") else {})
        valida = all(0 <= z[0] <= 5 for z in zonas.values())
    except ValueError:
        valida = False
    if not valida:
        raise Sair(2, "[zonas] com <nome>.degrau inteiro, de 0 a 5, em metodo.ini")
    rotulo, arquivos = "mudança em curso", mudanca_em_curso(raiz)
    if arquivos is None:
        raise Sair(2, "repositório git (sem ele não sei o que mudou: rode git init, ou diga o "
                      "degrau com --ate <n>)")
    if do_envio:
        base = cfg.get("envio", "base", fallback="").strip()
        if not base:  # sem [envio] base, o ramo remoto de acompanhamento
            cod, saida = _git(raiz, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            base = _texto(saida) if cod == 0 else ""
        rotulo = "a enviar, sem base (só a mudança em curso)"
        if base:
            rotulo = "a enviar (base %s)" % base
            arquivos = None if base.startswith("-") else a_enviar(raiz, base)
        if arquivos is None:
            raise Sair(2, 'a base "%s" (não existe neste repositório: confira [envio] base em '
                          'metodo.ini; se nunca foi buscada, rode git fetch)' % base)
    tocadas, n = zonas_tocadas(arquivos, zonas), degrau_minimo(arquivos, zonas)
    quais = ", ".join("%s (%d)" % par for par in sorted(tocadas.items()))
    return n, "%s: %d arquivos; %s; degrau mínimo: %d" % (
        rotulo, len(arquivos), "zonas: " + quais if quais else "nenhuma zona tocada", n)

def saida_do_3(pendentes, antes_de_enviar, cobre, eu):
    """O que fazer quando passou, mas há degrau pendente: o 3 não trava nem passa em silêncio."""
    quais = ", ".join(str(n) for n in pendentes)
    if min(pendentes) <= 2:
        return ('preencher [escada] N.comando do degrau %s em metodo.ini (o comando que o projeto '
                'já tem, ou "n/a: <motivo>") e rodar de novo: código não é commitado com o degrau '
                '0, 1 ou 2 pendente' % quais)
    if antes_de_enviar:
        return ('degrau %s pendente: confira que ele está em "Ficou para depois", no estado, diga '
                'ao dono na lista e use na cadeia do envio: %s --evidencia --ate %d'
                % (quais, eu, cobre))
    return ('degrau %s pendente: diga isso em "Não rodei" e abra item datado em "Ficou para '
            'depois", no estado. Esta chamada não trava o commit' % quais)

def evidencia(raiz, cfg, degraus, pasta, fora, ate, eu):
    """Não roda nada: compara a evidência guardada com a árvore atual e com o degrau exigido."""
    de_novo = eu + (" --a-enviar" if ate is None else " --ate %d" % ate)
    atual, guardada = impressao(raiz, fora), ler_evidencia(pasta)
    if atual == "sem-git":
        print("sem git: não sei se a árvore mudou")
        raise Sair(3, proximo="git init; depois, " + eu + " --ate <n>")
    m, nota = ate, ""
    if ate is None:
        m, explica = exigido(raiz, cfg, True)
        nota = " (sem base: só a mudança em curso)" if "sem base" in explica else ""
        print(explica)
    if not guardada:
        print("nenhuma evidência; exigido %d%s" % (m, nota))
        raise Sair(3, proximo=de_novo)
    res = {n: i["resultado"] for n, i in guardada[1].items()}
    n = subiu_ate(res)
    if guardada[0] != atual:
        print("vencida: a árvore mudou desde a subida (%s em %s)" % (
            "nenhum degrau subido desde o 0" if n is None else "subiu até o degrau %d" % n,
            max(i["data"] for i in guardada[1].values())))
        raise Sair(3, proximo=de_novo)
    print(linha_do_relato(degraus, guardada[1]))
    vale = ("nenhum degrau subido desde o 0" if n is None else "vale até o degrau %d" % n) \
        + " para a árvore atual; exigido %d%s" % (m, nota)
    if n is not None and n >= m:
        return print(vale)
    faltam = [(k, res.get(k) or ("pendente" if degraus[k]["tipo"] == "pendente" else "não rodado"))
              for k in range(0 if n is None else n + 1, m + 1)]
    faltam = [f for f in faltam if f[1] not in ("ok", "n/a")]
    print(vale + "; faltam: " + ", ".join("%d (%s)" % f for f in faltam))
    if all(f[1] == "pendente" for f in faltam):
        raise Sair(3, proximo=saida_do_3([f[0] for f in faltam], True, n, eu))
    raise Sair(3, proximo=de_novo)

def subir(raiz, degraus, pedidos, pasta, fora, antes_de_enviar, eu):
    """Sobe os degraus pedidos, em ordem, e grava a evidência por degrau."""
    os.makedirs(pasta, exist_ok=True)
    trava = travar(pasta)
    try:
        antes, guardada = impressao(raiz, fora), ler_evidencia(pasta)
        # Mesma árvore: as subidas se somam. Árvore diferente, ou sem git: parte do zero.
        itens = dict(guardada[1]) if guardada and guardada[0] == antes != "sem-git" else {}
        cod, saida = _git(raiz, "rev-parse", "--short", "HEAD")
        commit, novos, falha = _texto(saida) if cod == 0 else "sem-commit", {}, None
        for d in pedidos:
            rotulo, codigo, segundos = "degrau %d · %s" % (d["n"], d["nome"]), None, 0
            if falha is not None:
                print("não rodado %s (a subida parou no degrau %d)" % (rotulo, falha))
                continue
            if d["tipo"] == "pendente":
                res = "pendente"
                print("pendente %s (sem comando em metodo.ini)" % rotulo)
            elif d["tipo"] == "n/a":
                res = "n/a"
                print("n/a %s (%s)" % (rotulo, d["motivo"]))
            else:
                if d["precisa"]:
                    print("precisa: %s: %s" % (rotulo, d["precisa"]))
                if ";" in d["comando"] or "\n" in d["comando"]:
                    print('aviso: o comando do degrau %d tem ";" ou mais de uma linha: uma falha '
                          'no meio pode não interromper. Ligue com &&' % d["n"])
                sys.stdout.flush()
                registro = os.path.join(pasta, "degrau-%d.txt" % d["n"])
                codigo, segundos, houve = rodar(raiz, d, registro)
                res = "ok" if codigo == 0 else "falhou"
                if res == "ok":
                    print("ok %s (%d s)" % (rotulo, segundos))
                else:
                    falha = d["n"]
                    houve = houve or "código %d, %d s" % (codigo, segundos)
                    print("FALHOU %s (%s)" % (rotulo, houve))
                mostra, ha_mais = ultimas(registro, 3 if res == "ok" else 20)
                for linha in mostra:
                    print("    " + linha)
                if res != "ok" or ha_mais:
                    print("    registro: " + registro)
            agora = time.localtime()
            novos[d["n"]] = {"n": d["n"], "nome": d["nome"], "resultado": res, "codigo": codigo,
                             "segundos": segundos, "data": time.strftime("%Y-%m-%d", agora),
                             "hora": time.strftime("%H:%M:%S", agora), "commit": commit}
            sys.stdout.flush()
        depois = impressao(raiz, fora)
        if depois != antes:
            print("aviso: a árvore mudou durante a subida: a evidência guarda só os degraus desta")
            itens = {}
        itens.update(novos)
        dados = {"versao": 2, "impressao": depois, "degraus": [itens[n] for n in sorted(itens)]}
        _caminho = os.path.join(pasta, "escada.json.tmp")
        with open(_caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        os.replace(os.path.join(pasta, "escada.json.tmp"), os.path.join(pasta, "escada.json"))
    finally:
        os.remove(trava)
    print(linha_do_relato(degraus, itens))
    if depois == "sem-git":
        print("aviso: sem git: não sei se a árvore muda depois desta subida; a evidência não vale")
    if falha is not None:
        raise Sair(1, proximo="ler o registro, corrigir a causa e subir de novo; falha que vai e "
                              "volta: references/testes.md §9")
    pendentes = [n for n in sorted(novos) if novos[n]["resultado"] == "pendente"]
    if pendentes:
        cobre = subiu_ate({n: i["resultado"] for n, i in itens.items()})
        antes_de_enviar = antes_de_enviar and cobre is not None
        raise Sair(3, proximo=saida_do_3(pendentes, antes_de_enviar, cobre, eu))

def executar(argv):
    o = ler_opcoes(argv)
    if not shutil.which("git"):
        raise Sair(2, "git (instale: sem ele não sei o que mudou nem onde guardar a evidência)")
    raiz, cfg = achar_projeto(o["projeto"])
    degraus, modo, pasta = ler_escada(cfg), o["modo"], pasta_de_evidencia(raiz)
    documentos = dict(cfg["documentos"]) if cfg.has_section("documentos") else {}
    fora = fora_da_impressao(dict(DOCUMENTOS, **documentos))
    eu = _py() + " " + _citar(sys.argv[0])
    if o["projeto"]:
        eu += " --projeto " + _citar(o["projeto"])
    if "listar" in modo:
        print("projeto: " + raiz)
        for d in degraus:
            como = {"pendente": "pendente", "n/a": "n/a: " + d.get("motivo", "")}.get(d["tipo"])
            precisa = "; precisa: " + d["precisa"] if d["precisa"] and not como else ""
            print("degrau %d · %s (%s%s)%s" % (d["n"], d["nome"], como or "com comando", precisa,
                                              "" if como else ": " + d["comando"]))
        return print("pasta de evidência: " + pasta)
    if "evidencia" in modo:
        return evidencia(raiz, cfg, degraus, pasta, fora, o["ate"], eu)
    ate = 5 if o["ate"] is None else o["ate"]
    if "exigido" in modo or "a-enviar" in modo:
        ate, explica = exigido(raiz, cfg, "a-enviar" in modo)
        print(explica)
    pedidos = [degraus[o["so"]]] if "so" in modo else degraus[:ate + 1]
    subir(raiz, degraus, pedidos, pasta, fora, "a-enviar" in modo, eu)

def main(argv):
    for canal in (sys.stdout, sys.stderr):
        if hasattr(canal, "reconfigure"):  # saída de teste traz de tudo: não quebre por isso
            canal.reconfigure(errors="replace")
    if any(a in ("-h", "--help", "--ajuda") for a in argv):
        print(__doc__.strip())
        return 0
    codigo, proximo, falta = 0, None, None
    try:
        executar(argv)
    except Sair as fim:
        codigo, proximo, falta = fim.codigo, fim.proximo, fim.falta
    except OSError as erro:  # disco cheio, pasta sem permissão, arquivo que sumiu no meio
        codigo, falta = 2, "ler e gravar sem erro (%s)" % erro
    if falta:
        sys.stdout.flush()
        print("falta: " + falta, file=sys.stderr, flush=True)
    if proximo:
        print("próximo: " + proximo)
    print(NAO_CONFERI)
    return codigo

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
