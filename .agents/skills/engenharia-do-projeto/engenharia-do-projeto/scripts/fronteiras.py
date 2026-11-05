#!/usr/bin/env python3
"""Confere regras de fronteira lendo o código-fonte como texto: nome restrito e texto proibido.

uso:
  fronteiras.py [--projeto <pasta>] [--regra <nome>]
      lê [fronteiras] e as seções [fronteira.<nome>] de metodo.ini; imprime "sanidade:" e uma
      linha por regra: ok, VIOLOU com caminho:linha e o motivo, ou VAZIA. --regra confere uma só.
  fronteiras.py [--projeto <pasta>] --listar
      não lê código: mostra a configuração da varredura e as regras declaradas.
  Num degrau da escada ou no CI, chame a cópia do projeto: python3 ferramentas/metodo/fronteiras.py
  saída 0: sanidade e regras ok. 1: alguma VIOLOU. 2: configuração inválida ou nenhuma regra.
      3: alguma VAZIA e nenhuma violação (a regra não está protegendo nada).

à mão:
  Para cada regra, busque o padrão nas pastas de código, sem limite de profundidade.
  Antes de confiar no "nada encontrado", confira que a mesma busca acha o arquivo permitido:
  busca que não acha nem o que deve achar está olhando para o lugar errado.
  Nome restrito: toda ocorrência fora dos arquivos permitidos é violação.
  Texto proibido: toda ocorrência fora dos arquivos de "exceto" é violação.

recusa: dar verde com zero arquivo lido; aceitar regra sem motivo; ler fora do projeto; alterar
  arquivo; fingir que entende a sintaxe da linguagem.
"""
import configparser, os, posixpath, re, shutil, subprocess, sys

NAO_CONFERI = ("não conferi: imports resolvidos, import só de tipo, primeira instrução de função, "
               "ordem de chamadas; comentário e texto contam como ocorrência. Para isso, teste na "
               "linguagem do projeto (references/fronteiras.md §3)")
NAO_PERCORRE = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
                "__pycache__"}  # mais ferramentas/metodo e toda pasta iniciada por ponto
LIMITE = 5000  # entradas de pasta lidas numa varredura
CHAVES = {"tipo", "padrao", "regex", "exemplo", "permitidos", "exceto", "motivo"}

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

# --- Fim do código de referência. ---

def ler_opcoes(argv):
    o, i = {"projeto": None, "regra": None, "listar": False}, 0
    while i < len(argv):
        nome, igual, valor = argv[i].partition("=")
        if nome in ("--projeto", "--regra"):
            if not igual:
                i, valor = i + 1, (argv[i + 1] if i + 1 < len(argv) else "")
            if not valor:
                raise Sair(2, "o valor de %s (veja --ajuda)" % nome)
            o[nome[2:]] = valor
        elif argv[i] == "--listar":
            o["listar"] = True
        else:
            raise Sair(2, 'uma opção conhecida no lugar de "%s" (veja --ajuda)' % argv[i])
        i += 1
    return o

def achar_projeto(pasta):
    """Devolve (raiz, configuração). Sem --projeto e sem metodo.ini aqui, tenta a raiz do git."""
    raiz = os.path.realpath(pasta or os.getcwd())
    if pasta and not os.path.isdir(raiz):
        raise Sair(2, "a pasta %s (não existe: confira o caminho de --projeto)" % pasta)
    if not pasta and not os.path.isfile(os.path.join(raiz, "metodo.ini")) and shutil.which("git"):
        cod, saida = _git(raiz, "rev-parse", "--show-toplevel")
        topo = saida.decode("utf-8", "surrogateescape").strip()
        if cod == 0 and os.path.isfile(os.path.join(topo, "metodo.ini")):
            raiz = os.path.realpath(topo)
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

def ler_configuracao(cfg):
    """Devolve (varredura, regras). Qualquer erro aqui é configuração inválida: código 2."""
    lista = lambda texto: [p.strip() for p in (texto or "").split(",") if p.strip()]
    if not cfg.has_section("fronteiras"):
        raise Sair(2, "a seção [fronteiras] em metodo.ini (copie de assets/modelos/metodo.ini)")
    sec = cfg["fronteiras"]
    v = {"pastas": [p.replace("\\", "/") for p in lista(sec.get("pastas"))],
         "extensoes": ["." + e.lstrip("*.") for e in lista(sec.get("extensoes"))],
         "ignorar": lista(sec.get("ignorar")), "minimo": (sec.get("minimo_de_arquivos") or "1"),
         "conhecido": (sec.get("arquivo_conhecido") or "").strip().replace("\\", "/")}
    v["conhecido"] = posixpath.normpath(v["conhecido"]) if v["conhecido"] else ""
    if not v["pastas"] or not v["extensoes"]:
        raise Sair(2, "pastas e extensoes preenchidas em [fronteiras] (as pastas de código do "
                      "projeto e as extensões que contam, separadas por vírgula)")
    for p in v["pastas"]:
        if re.match(r"^(/|~|[A-Za-z]:)", p) or ".." in p.split("/"):
            raise Sair(2, 'pastas relativas ao projeto em [fronteiras] ("%s" é absoluta ou tem '
                          '"..": este script não lê fora do projeto)' % p)
    v["pastas"] = [posixpath.normpath(p) for p in v["pastas"]]
    if not v["minimo"].strip().isdigit() or int(v["minimo"]) < 1:
        raise Sair(2, "minimo_de_arquivos inteiro, de 1 para cima, em [fronteiras] (verde com "
                      "zero arquivo lido não vale)")
    v["minimo"], regras = int(v["minimo"]), {}
    for secao in cfg.sections():
        if not secao.startswith("fronteira."):
            continue
        nome, s = secao[len("fronteira."):], cfg[secao]
        erro, r = None, {"tipo": (s.get("tipo") or "").strip(), "padrao": s.get("padrao") or "",
                         "motivo": (s.get("motivo") or "").strip(), "exemplo": s.get("exemplo"),
                         "permitidos": lista(s.get("permitidos")), "exceto": lista(s.get("exceto")),
                         "regex": (s.get("regex") or "").strip()}
        if set(s) - CHAVES:
            erro = "só as chaves %s (achei %s)" % (
                ", ".join(sorted(CHAVES)), ", ".join(sorted(set(s) - CHAVES)))
        elif r["tipo"] not in ("nome-restrito", "texto-proibido"):
            erro = "tipo = nome-restrito ou tipo = texto-proibido"
        elif not r["padrao"].strip() or not r["motivo"]:
            erro = "padrao e motivo (regra sem motivo não é aceita)"
        elif r["regex"] not in ("", "sim"):
            erro = "regex = sim, ou a linha apagada"
        elif r["regex"] and not (r["exemplo"] or "").strip():
            erro = "exemplo, obrigatório com regex = sim: um texto que o padrão tem de achar"
        elif r["tipo"] == "nome-restrito" and (not r["permitidos"] or s.get("exceto") is not None):
            erro = "permitidos preenchido e nenhum exceto (exceto é só de texto-proibido)"
        elif r["tipo"] == "texto-proibido" and s.get("permitidos") is not None:
            erro = "nenhum permitidos (em texto-proibido, a exceção se chama exceto)"
        if not erro:
            try:
                r["rx"] = re.compile(r["padrao"] if r["regex"] else re.escape(r["padrao"]), re.M)
                erro = "um padrão que não case com o texto vazio" if r["rx"].search("") else None
            except re.error as falha:
                erro = "uma expressão regular válida em padrao (%s)" % falha
        if erro:
            raise Sair(2, "[%s] com %s" % (secao, erro))
        regras[nome] = r
    if not regras:
        raise Sair(2, "pelo menos uma regra [fronteira.<nome>] em metodo.ini (sem regra não há o "
                      "que conferir; veja references/fronteiras.md §3)")
    return v, regras

def varrer(raiz, v):
    """Lê os arquivos das pastas. Devolve ({caminho: texto}, {pasta: quantos}, ignorados,
    não lidos, interrompida, pastas que não abriram)."""
    arquivos, ignorados, nao_lidos, entradas, fechadas = {}, 0, [], 0, []
    por_pasta = {pasta: 0 for pasta in v["pastas"]}
    for pasta in v["pastas"]:
        partes = [] if pasta == "." else pasta.split("/")
        if any(p in NAO_PERCORRE or p.startswith(".") for p in partes) or \
                (pasta + "/").startswith("ferramentas/metodo/"):
            continue  # pasta que não se percorre: não contribui, e a sanidade acusa
        def anotar(erro):  # pasta que existe e não abre: a varredura não é inteira
            fechadas.extend([] if isinstance(erro, FileNotFoundError) else [erro.filename])
        for atual, subpastas, nomes in os.walk(os.path.join(raiz, pasta), onerror=anotar):
            rel = os.path.relpath(atual, raiz).replace(os.sep, "/")
            rel = "" if rel == "." else rel + "/"
            entradas += len(subpastas) + len(nomes)
            if entradas > LIMITE:
                return arquivos, por_pasta, ignorados, nao_lidos, True, fechadas
            subpastas[:] = sorted(s for s in subpastas if s not in NAO_PERCORRE
                                  and not s.startswith(".") and rel + s != "ferramentas/metodo")
            for nome in sorted(nomes):
                caminho, inteiro = rel + nome, os.path.join(atual, nome)
                if not any(nome.endswith(e) for e in v["extensoes"]):
                    continue
                if any(casa(caminho, p) for p in v["ignorar"]):
                    ignorados += 1
                    continue
                dado = b"\0"  # atalho para fora do projeto e arquivo ilegível ficam assim
                if os.path.isfile(inteiro) and os.path.realpath(inteiro).startswith(raiz + os.sep):
                    try:
                        with open(inteiro, "rb") as f:
                            dado = f.read(1048577)
                    except OSError:
                        pass
                if len(dado) > 1048576 or b"\0" in dado[:8192]:  # mais de 1 MB, ou binário
                    nao_lidos.append(caminho)
                    continue
                por_pasta[pasta] += 1
                arquivos[caminho] = dado.decode("utf-8", "replace")
    return arquivos, por_pasta, ignorados, nao_lidos, False, fechadas

def conferir(nome, r, arquivos):
    """Devolve (situação, linhas a imprimir) de uma regra: 'ok', 'VIOLOU' ou 'VAZIA'."""
    if r["regex"] and not r["rx"].search(r["exemplo"]):
        return "VAZIA", ["VAZIA regra %s: o padrão não casa com o exemplo declarado" % nome]
    onde = {}
    for caminho, texto in arquivos.items():
        linhas = [texto.count("\n", 0, m.start()) + 1 for m in r["rx"].finditer(texto)]
        if linhas:
            onde[caminho] = linhas
    livres = r["permitidos"] if r["tipo"] == "nome-restrito" else r["exceto"]
    livre = lambda caminho: any(casa(caminho, p) for p in livres)
    if r["tipo"] == "nome-restrito":
        sumidos = [p for p in r["permitidos"] if not any(casa(a, p) for a in arquivos)]
        if sumidos:  # sem o arquivo permitido, a lista de violações não quer dizer nada
            return "VAZIA", ["VAZIA regra %s: permitidos sem arquivo na varredura: %s (o arquivo "
                             "mudou de nome ou está fora das pastas)" % (nome, ", ".join(sumidos))]
    fora = sorted(a for a in onde if not livre(a))
    saida = ["VIOLOU regra %s: %s:%d%s" % (nome, a, onde[a][0], "" if len(onde[a]) == 1 else
             " (e mais %d no mesmo arquivo)" % (len(onde[a]) - 1)) for a in fora[:20]]
    if len(fora) > 20:
        saida.append("VIOLOU regra %s: e mais %d arquivos" % (nome, len(fora) - 20))
    if fora:
        saida.append("    motivo: " + r["motivo"])
    com = [a for a in onde if livre(a)]
    if r["tipo"] == "nome-restrito" and not com:
        saida.append("VAZIA regra %s: nenhum arquivo permitido contém o padrão (a regra não "
                     "protege nada ou o nome mudou)" % nome)
    if not saida:
        quais = "permitidos" if r["tipo"] == "nome-restrito" else "de exceto"
        saida.append("ok regra %s (%d arquivos conferidos; %d %s contêm o padrão)"
                     % (nome, len(arquivos), len(com), quais))
    return ("VIOLOU" if fora else "VAZIA" if saida[0].startswith("VAZIA") else "ok"), saida

def executar(argv, notas):
    o = ler_opcoes(argv)
    raiz, cfg = achar_projeto(o["projeto"])
    v, regras = ler_configuracao(cfg)
    if o["regra"] and o["regra"] not in regras:
        raise Sair(2, 'a regra "%s" em metodo.ini (declaradas: %s)'
                      % (o["regra"], ", ".join(regras)))
    if o["listar"]:
        print("projeto: " + raiz)
        print("varredura: pastas %s; extensões %s; ignorar %s; mínimo de %d arquivos%s" % (
            ", ".join(v["pastas"]), ", ".join(v["extensoes"]), ", ".join(v["ignorar"]) or "nada",
            v["minimo"], "; arquivo conhecido " + v["conhecido"] if v["conhecido"] else ""))
        for nome, r in regras.items():
            print("regra %s (%s%s): %s\n    motivo: %s" % (
                nome, r["tipo"], ", regex" if r["regex"] else "", r["padrao"], r["motivo"]))
        return
    arquivos, por_pasta, ignorados, nao_lidos, interrompida, fechadas = varrer(raiz, v)
    if nao_lidos:
        notas.append("%d arquivos que não li (mais de 1 MB, binários ou fora do projeto): %s"
                     % (len(nao_lidos), ", ".join(nao_lidos[:3])))
    vazia = ["a pasta %s não contribuiu com nenhum arquivo" % p
             for p in v["pastas"] if not por_pasta[p]]
    vazia += ["não consegui abrir a pasta %s" % pasta for pasta in fechadas[:3]]
    if interrompida:
        print("aviso: varredura interrompida em %d entradas" % LIMITE)
        notas.append("o que ficou depois das %d primeiras entradas" % LIMITE)
        vazia.append("a varredura parou em %d entradas e não leu tudo: restrinja pastas" % LIMITE)
    if len(arquivos) < v["minimo"]:
        vazia.append("li %d arquivos; o mínimo declarado é %d" % (len(arquivos), v["minimo"]))
    if v["conhecido"] and v["conhecido"] not in arquivos:
        vazia.append("arquivo_conhecido %s não está na varredura" % v["conhecido"])
    entrou = [a for a in arquivos if any(casa(a, p) for p in v["ignorar"])]
    if entrou:
        vazia.append("arquivo de ignorar entrou na varredura: %s" % entrou[0])
    print("sanidade: %d arquivos em %d pastas%s" % (
        len(arquivos), sum(1 for p in v["pastas"] if por_pasta[p]),
        "; %d de ignorar ficaram de fora" % ignorados if v["ignorar"] else ""))
    corrigir = ("corrigir a configuração em metodo.ini (pasta, arquivo permitido, exemplo): a "
                "regra não está protegendo nada. Baixar minimo_de_arquivos não serve")
    if vazia:  # as regras não rodam: sem varredura conferida, todo "ok" seria vazio
        for motivo in vazia:
            print("VAZIA sanidade: " + motivo)
        raise Sair(3, proximo=corrigir)
    situacoes = set()
    for nome, r in regras.items():
        if o["regra"] in (None, nome):
            situacao, linhas = conferir(nome, r, arquivos)
            situacoes.add(situacao)
            print("\n".join(linhas))
    if "VIOLOU" in situacoes:
        raise Sair(1, proximo='corrigir o código. Acrescentar o arquivo a "permitidos" ou a '
                              '"exceto" abre a fronteira: é decisão, e passa pelo dono')
    if "VAZIA" in situacoes:
        raise Sair(3, proximo=corrigir)

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
    print(NAO_CONFERI + "".join(". Também: " + n for n in notas))
    return codigo

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
