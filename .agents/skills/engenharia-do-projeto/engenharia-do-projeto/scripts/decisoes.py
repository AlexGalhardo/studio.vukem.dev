#!/usr/bin/env python3
"""Registro de decisões: índice dos títulos, próximo número, registro novo e conferência.

uso:
  python3 decisoes.py titulos
      → uma linha por registro: número, título e a marca de substituído ou de revisto
  python3 decisoes.py proximo
      → o próximo número livre, contando os ramos remotos já buscados
  python3 decisoes.py novo "<título>" [--decidiu agente|dono|dono-contra] [--simular]
      → insere o registro acima do molde do fim do arquivo (em pasta, cria <NNN>-<título>.md),
        com a data de hoje e três campos por preencher; com --simular, só mostra
  python3 decisoes.py conferir [--estrito]
      → uma linha por ACHADO e por aviso, com arquivo:linha; código 1 se houver achado
        (com --estrito, também se houver aviso)
  Em todas: [--projeto <pasta>]. Sem ela, vale a pasta atual.

à mão:
  Ache o maior número com uma busca por "## " mais o prefixo no registro de decisões. Copie o
  molde do fim do arquivo para logo acima dele, com o número seguinte. Procure cada número
  citado no código e nos documentos e confira se o registro existe.

recusa: editar, renumerar ou apagar registro existente; reaproveitar número; buscar no remoto.
"""
import configparser, datetime, os, re, subprocess, sys, tempfile, unicodedata

LIMITE = 5000
NAO_PERCORRER = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
                 "__pycache__"}
COPIA = "ferramentas/metodo"
OBRIGATORIOS = ("Contexto", "Decisão", "Consequências")
DESEJAVEIS = ("Data", "Decidiu")
QUEM = {"agente": "agente", "dono": "dono", "dono-contra": "dono, contra a recomendação"}
NAO_CONFERI = "não conferi: ramos não buscados; rode `git fetch` antes se há outra sessão"


def parar(mensagem):
    """Uso errado ou pré-condição ausente: explica em stderr e devolve o código 2."""
    print(mensagem, file=sys.stderr)
    print("não conferi: nada; parei antes de começar")
    return 2

def _git(raiz, *args):
    amb = dict(os.environ, LC_ALL="C", GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", raiz] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=amb)
    except OSError:  # git não instalado: vale como "não é repositório"
        return 127, b""
    return r.returncode, r.stdout

def percorrivel(caminho):
    """O caminho (relativo, com /) fica fora das pastas que não se percorrem?"""
    pastas = caminho.split("/")[:-1]
    return not (any(p in NAO_PERCORRER or p.startswith(".") for p in pastas)
                or (caminho + "/").startswith(COPIA + "/"))

def ler(caminho):
    """Texto do arquivo, ou None se passa de 1 MB, é binário ou não abre."""
    try:
        if os.path.getsize(caminho) > 1048576:
            return None
        with open(caminho, "rb") as f:
            dado = f.read()
    except OSError:
        return None
    return None if b"\0" in dado[:8192] else dado.decode("utf-8", "replace")

def arquivos_de_texto(raiz):
    """(caminhos relativos a conferir, a varredura parou no limite?). Com git, os rastreados e
    os novos que ele não ignora; sem git, a pasta inteira."""
    cod, saida = _git(raiz, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".")
    if cod == 0:
        nomes = sorted(n.decode("utf-8", "surrogateescape") for n in saida.split(b"\0") if n)
    else:
        nomes = []
        for pasta, subpastas, arquivos in os.walk(raiz):
            rel = os.path.relpath(pasta, raiz).replace(os.sep, "/")
            subpastas[:] = sorted(s for s in subpastas if percorrivel(
                (s if rel == "." else rel + "/" + s) + "/x"))
            nomes += [a if rel == "." else rel + "/" + a for a in sorted(arquivos)]
            if len(nomes) > LIMITE:
                break
    nomes = [n for n in nomes if percorrivel(n)]
    return nomes[:LIMITE], len(nomes) > LIMITE

class Registro(object):
    def __init__(self, numero, titulo, arquivo, linha):
        self.numero, self.titulo, self.arquivo, self.linha = numero, titulo, arquivo, linha
        self.campos, self.revisto, self.lacuna = set(), [], 0

def ler_registros(raiz, arquivos, prefixo):
    """(registros, [(arquivo, linha)] de títulos fora do formato). O molde (XXX) é ignorado."""
    titulo = re.compile(r"## %s(\d{3,}) · (.*\S)\s*$" % re.escape(prefixo))
    numero = re.compile(re.escape(prefixo) + r"(\d{3,})")
    registros, tortos = [], []
    for arquivo in arquivos:
        atual = None
        for n, linha in enumerate((ler(os.path.join(raiz, arquivo)) or "").split("\n"), 1):
            if linha.startswith("## "):
                m, atual = titulo.match(linha), None
                if m:
                    atual = Registro(int(m.group(1)), m.group(2), arquivo, n)
                    registros.append(atual)
                elif linha.startswith("## " + prefixo) and not linha.startswith("## %sXXX" % prefixo):
                    tortos.append((arquivo, n))
            elif atual is not None:
                m = re.match(r"\*\*([^*:]+):\*\*", linha)
                if m:
                    atual.campos.add(m.group(1))
                if linha.startswith("**Revisto por:**"):
                    atual.revisto += [(int(x), n) for x in numero.findall(linha)]
                if "{{" in linha and not atual.lacuna:
                    atual.lacuna = n
    return registros, tortos

def maior_nos_ramos(raiz, rel, em_pasta, prefixo):
    """(maior número, ramo) entre os ramos remotos já buscados, lendo só os objetos locais."""
    cod, saida = _git(raiz, "for-each-ref", "--format=%(refname:short)", "refs/remotes")
    maior, onde = 0, ""
    for ramo in (saida.decode("utf-8", "replace").split() if cod == 0 else []):
        if ramo.endswith("/HEAD"):
            continue
        if em_pasta:  # só os nomes de arquivo, sem abrir
            cod, lista = _git(raiz, "ls-tree", "--name-only", ramo, "--", rel + "/")
            nomes = [os.path.basename(x) for x in lista.decode("utf-8", "replace").split("\n")]
            numeros = [int(m.group(1)) for m in (re.match(r"(\d{3,})-", x) for x in nomes) if m]
        else:
            cod, texto = _git(raiz, "show", "%s:./%s" % (ramo, rel))
            numeros = [int(x) for x in re.findall(
                r"^## %s(\d{3,}) · " % re.escape(prefixo), texto.decode("utf-8", "replace"), re.M)]
        if cod == 0 and numeros and max(numeros) > maior:
            maior, onde = max(numeros), ramo
    return maior, onde

def proximo_numero(raiz, rel, em_pasta, registros, prefixo):
    """(próximo número, linha de aviso ou vazio). Nunca reaproveita número."""
    aqui = max([r.numero for r in registros] or [0])
    if em_pasta:
        for nome in os.listdir(os.path.join(raiz, rel)):
            m = re.match(r"(\d{3,})-", nome)
            aqui = max(aqui, int(m.group(1)) if m else 0)
    la, ramo = maior_nos_ramos(raiz, rel, em_pasta, prefixo)
    aviso = ""
    if la > aqui:
        aviso = "aviso: o ramo %s já tem %s%03d, que não está aqui; pulei para o número seguinte" % (
            ramo, prefixo, la)
    return max(aqui, la) + 1, aviso

def bloco_novo(rotulo, titulo, quem):
    return ["## %s · %s" % (rotulo, titulo), "",
            "**Data:** " + datetime.date.today().isoformat(),
            "**Decidiu:** " + quem,
            "**Contexto:** {{a tensão: o que puxava para cada lado}}",
            "**Decisão:** {{o que se faz, dito de modo que se ache no código}}",
            "**Consequências:** {{o que fica mais caro; o que quebra se alguém desfizer; para que "
            "lado falha}}"]

def inserir(caminho, bloco, prefixo):
    """Insere o bloco acima do molde (ou no fim) e troca o arquivo de uma vez. Devolve a linha
    do título novo. Antes de gravar, confere que as linhas antigas continuam lá, em ordem."""
    with open(caminho, encoding="utf-8", newline="") as f:
        texto = f.read()
    fim = "\r\n" if "\r\n" in texto else "\n"
    antigas = texto.split(fim)
    molde = next((i for i, l in enumerate(antigas) if l.startswith("## %sXXX" % prefixo)), None)
    if molde is None:
        while antigas and antigas[-1] == "":
            antigas.pop()
        novas, onde = antigas + [""] + bloco + [""], len(antigas) + 2
        antigas = antigas + [""]
    else:
        antes = [] if molde == 0 or antigas[molde - 1] == "" else [""]
        novas = antigas[:molde] + antes + bloco + [""] + antigas[molde:]
        onde = molde + len(antes) + 1
    resto = iter(novas)
    if not all(linha in resto for linha in antigas):
        raise RuntimeError("as linhas antigas não ficaram intactas; nada foi gravado")
    fd, provisorio = tempfile.mkstemp(dir=os.path.dirname(caminho), prefix=".decisoes-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(fim.join(novas))
        try:  # permissão de arquivo é coisa de Unix: no Windows não existe e não faz falta
            os.chmod(provisorio, os.stat(caminho).st_mode & 0o777)
        except (OSError, NotImplementedError):
            pass
        os.replace(provisorio, caminho)
    except BaseException:
        os.unlink(provisorio)
        raise
    return onde

def conferir(raiz, registros, tortos, prefixo, estrito):
    achados, avisos, ditos = [], [], set()
    numeros, rotulo = {}, lambda n: "%s%03d" % (prefixo, n)
    def achado(arquivo, linha, texto):
        if (arquivo, linha, texto) not in ditos:
            ditos.add((arquivo, linha, texto))
            achados.append("ACHADO %s:%d  %s" % (arquivo, linha, texto))
    anterior = 0
    for r in registros:
        onde = (r.arquivo, r.linha)
        if r.numero in numeros:
            achado(onde[0], onde[1], "%s repetido (o primeiro está em %s:%d)"
                   % ((rotulo(r.numero),) + numeros[r.numero]))
        numeros.setdefault(r.numero, onde)
        for campo in OBRIGATORIOS:
            if campo not in r.campos:
                achado(onde[0], onde[1], "%s sem **%s:**" % (rotulo(r.numero), campo))
        for campo in DESEJAVEIS:
            if campo not in r.campos:
                avisos.append("aviso: %s:%d  %s sem **%s:**" % (onde + (rotulo(r.numero), campo)))
        limpo = re.sub(r"\s*\(substituída pelo .*\)$", "", r.titulo)
        if limpo.endswith("?") or len(limpo.split()) < 3:
            avisos.append("aviso: %s:%d  %s: o título é pergunta ou tem menos de três palavras; "
                          "escreva a decisão como afirmação" % (onde + (rotulo(r.numero),)))
        if r.lacuna:
            avisos.append("aviso: %s:%d  %s com lacuna por preencher" % (r.arquivo, r.lacuna, rotulo(r.numero)))
        if r.numero < anterior:
            avisos.append("aviso: %s:%d  %s vem depois de %s: números fora de ordem"
                          % (onde + (rotulo(r.numero), rotulo(anterior))))
        anterior = max(anterior, r.numero)
    for arquivo, linha in tortos:
        avisos.append("aviso: %s:%d  título fora do formato '## %sNNN · <título>': este registro "
                      "não é lido" % (arquivo, linha, prefixo))
    # ligações entre registros e citações no resto do repositório
    for r in registros:
        m = re.search(r"\(substituída pelo %s(\d{3,})\)\s*$" % re.escape(prefixo), r.titulo)
        for n, linha in ([(int(m.group(1)), r.linha)] if m else []) + r.revisto:
            if n not in numeros:
                achado(r.arquivo, linha, "%s aponta para %s, que não existe" % (rotulo(r.numero), rotulo(n)))
                ditos.add((r.arquivo, linha, n))
    citacao = re.compile(r"(?<![A-Za-z0-9])%s(\d{3,})(?!\d)" % re.escape(prefixo))
    nomes, parou = arquivos_de_texto(raiz)
    lidos = 0
    for nome in nomes:
        texto = None if os.path.islink(os.path.join(raiz, nome)) else ler(os.path.join(raiz, nome))
        if texto is None or prefixo not in texto:
            lidos += texto is not None
            continue
        lidos += 1
        for n, linha in enumerate(texto.split("\n"), 1):
            for numero in set(int(x) for x in citacao.findall(linha)):
                if numero not in numeros and (nome, n, numero) not in ditos:
                    achado(nome, n, "%s citado sem registro" % rotulo(numero))
    for linha in achados[:60] + avisos[:60]:
        print(linha)
    if len(achados) > 60 or len(avisos) > 60:
        print("aviso: saída cortada em 60 linhas de cada tipo")
    if parou:
        print("aviso: varredura interrompida em %d arquivos" % LIMITE)
    print("conferidos: %d registros; %d arquivos lidos; %d achados; %d avisos"
          % (len(registros), lidos, len(achados), len(avisos)))
    if achados:
        print("próximo: corrija cada ACHADO à mão, numa edição que o dono vê; este script não "
              "edita registro existente (references/decisoes.md §7)")
    elif avisos:
        print("próximo: preencha as lacunas e os campos que faltam (references/decisoes.md §2)")
    print(NAO_CONFERI + "; o sentido do texto de cada campo; arquivo binário ou acima de 1 MB"
          + ("; o que passou do limite de %d arquivos" % LIMITE if parou else ""))
    return 1 if achados or (estrito and avisos) else 0


def main(args):
    args, projeto, opcoes, quem, soltos = list(args), None, set(), "agente", []
    while args:
        a = args.pop(0)
        if a in ("-h", "--help", "--ajuda"):
            print(__doc__.strip())
            return 0
        if a in ("--simular", "--estrito"):
            opcoes.add(a)
        elif a in ("--projeto", "--decidiu") and args:
            valor = args.pop(0)
            projeto, quem = (valor, quem) if a == "--projeto" else (projeto, valor)
        elif a.startswith("--"):
            return parar("erro de uso: não entendi %s (veja --ajuda)" % a)
        else:
            soltos.append(a)
    comando = soltos[0] if soltos else ""
    if comando not in ("titulos", "proximo", "novo", "conferir") or quem not in QUEM \
            or len(soltos) != (2 if comando == "novo" else 1):
        return parar("erro de uso: decisoes.py titulos | proximo | novo \"<título>\" [--decidiu "
                     "agente|dono|dono-contra] [--simular] | conferir [--estrito] (veja --ajuda)")

    raiz = os.path.abspath(projeto) if projeto else os.getcwd()
    if not projeto and not os.path.isfile(os.path.join(raiz, "metodo.ini")):
        cod, saida = _git(raiz, "rev-parse", "--show-toplevel")
        topo = saida.decode("utf-8", "surrogateescape").strip()
        if cod == 0 and topo and os.path.isfile(os.path.join(topo, "metodo.ini")):
            raiz = topo
    if not os.path.isfile(os.path.join(raiz, "metodo.ini")):
        return parar("falta: metodo.ini (rode montar.py)")
    try:
        ini = configparser.ConfigParser(interpolation=None)
        _caminho = os.path.join(raiz, "metodo.ini")
        with open(_caminho, encoding="utf-8") as f:
            ini.read_file(f)
    except (configparser.Error, UnicodeDecodeError) as erro:
        return parar("falta: metodo.ini válido (%s)" % str(erro).splitlines()[0])
    rel = ini.get("documentos", "decisoes", fallback="docs/decisoes.md").strip().strip("/")
    prefixo = ini.get("decisoes", "prefixo", fallback="ADR-").strip() or "ADR-"
    caminho = os.path.join(raiz, rel)
    dentro = os.path.realpath(caminho).startswith(os.path.realpath(raiz) + os.sep)
    if not rel or not dentro or not os.path.exists(caminho):
        return parar("falta: o registro de decisões em %s (crie com montar.py ou aponte "
                     "decisoes em metodo.ini)" % (rel or "[documentos] decisoes"))
    em_pasta = os.path.isdir(caminho)
    arquivos = (sorted(rel + "/" + n for n in os.listdir(caminho) if n.endswith(".md"))
                if em_pasta else [rel])
    registros, tortos = ler_registros(raiz, arquivos, prefixo)

    if comando == "titulos":
        for r in registros:
            revisto = ", ".join("%s%03d" % (prefixo, n) for n, _ in r.revisto)
            marca = " (revisto por %s)" % revisto if revisto and "(substituída pelo" not in r.titulo else ""
            print("%s%03d · %s%s" % (prefixo, r.numero, r.titulo, marca))
        if not registros:
            print("nenhum registro em %s" % rel)
        if tortos:
            print("aviso: %d títulos fora do formato não aparecem aqui (rode conferir)" % len(tortos))
        print(NAO_CONFERI)
        return 0
    if comando == "conferir":
        return conferir(raiz, registros, tortos, prefixo, "--estrito" in opcoes)

    numero, aviso = proximo_numero(raiz, rel, em_pasta, registros, prefixo)
    rotulo = "%s%03d" % (prefixo, numero)
    if comando == "proximo":
        print(rotulo)
        if aviso:
            print(aviso)
        print(NAO_CONFERI)
        return 0

    titulo = " ".join(soltos[1].split())
    if not titulo or len(titulo) > 120:
        return parar("falta: um título de 1 a 120 caracteres (ele é a própria decisão, em forma "
                     "de afirmação)")
    bloco = bloco_novo(rotulo, titulo, QUEM[quem])
    if em_pasta:
        sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
        nome = "%03d-%s.md" % (numero, re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
                               or "registro")
        destino = rel + "/" + nome
    else:
        destino = rel
    if "--simular" in opcoes:
        print("simulação: %s:" % ("criaria " + destino if em_pasta else
                                  "inseriria em %s, acima do molde (sem molde, no fim)" % destino))
        print("\n".join("  " + linha for linha in bloco))
    else:
        try:
            if em_pasta:
                _caminho = os.path.join(raiz, destino)
                with open(_caminho, "x", encoding="utf-8") as f:
                    f.write("\n".join(bloco) + "\n")
                linha = 1
            else:
                linha = inserir(caminho, bloco, prefixo)
        except (OSError, RuntimeError) as erro:
            print("FALHOU ao gravar %s: %s" % (destino, erro))
            print("não conferi: nada mudou no registro de decisões")
            return 1
        print("criado: %s · %s (%s:%d)" % (rotulo, titulo, destino, linha))
    if aviso:
        print(aviso)
    print("próximo: rode de novo sem --simular para gravar" if "--simular" in opcoes else
          "próximo: preencha Contexto, Decisão e Consequências em %s; depois, decisoes.py conferir"
          % destino)
    print(NAO_CONFERI + "; se a decisão já estava registrada com outro título")
    return 0


if __name__ == "__main__":
    for fluxo in (sys.stdout, sys.stderr):  # terminal sem UTF-8 não derruba a saída
        fluxo.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
