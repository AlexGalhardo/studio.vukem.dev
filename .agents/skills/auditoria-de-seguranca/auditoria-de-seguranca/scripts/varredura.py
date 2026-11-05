#!/usr/bin/env python3
"""varredura.py: lê um projeto e lista, por área, os pontos que uma pessoa precisa olhar.

Só lê arquivos: não altera nada, não acessa a rede, não executa o projeto e nunca imprime o
valor de uma chave nem a linha do código.

uso:
  python3 varredura.py <projeto> [--guarda <regex>] [--so <área>] [--limite <n>] [--com-testes]

áreas: segredos, rotas, entrada, banco, webhooks, sessao, arquivos, cache, bordas, erros,
       tentativas, dependencias

saída: 0 nenhum ponto listado; 1 há pontos para olhar; 2 uso errado ou pasta ausente;
       3 nenhum arquivo foi lido (pasta vazia, ou só com arquivo ignorado).

limites: é leitura por texto. Aponta onde olhar, não prova vulnerabilidade, e não achar não
prova que não há. Não segue imports, não entende de onde um valor vem, não olha o histórico do
git e não abre arquivo .env (só acusa o que o git rastreia). Os padrões são de JavaScript,
TypeScript e SQL, com um pouco de Python: em outra stack o padrão muda. "guarda aparente" quer
dizer que um nome com cara de guarda aparece perto, não que a guarda esteja certa.
"""

import argparse
import os
import re
import subprocess
import sys

AREAS = [("segredos", "Segredos"), ("rotas", "Rotas e ações de servidor (inventário)"),
         ("entrada", "Entrada e injeção"), ("banco", "Permissões no banco (SQL)"),
         ("webhooks", "Webhooks"), ("sessao", "Sessão, cookies e criptografia"),
         ("arquivos", "Upload, arquivos e pagamento"), ("cache", "Cache compartilhado"),
         ("bordas", "Cabeçalhos e CORS"), ("erros", "Erros, log e mapas de código-fonte"),
         ("tentativas", "Limite de tentativas"), ("dependencias", "Dependências")]
PASTAS_IGNORADAS = {".git", "node_modules", ".next", "dist", "build", "out", "vendor", ".venv",
                    "venv", "__pycache__", "coverage", ".turbo", ".vercel", "target", ".nuxt",
                    ".svelte-kit", ".output", ".cache"}
JS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}
MODELOS = {".html", ".ejs", ".erb", ".hbs", ".njk", ".jinja", ".j2", ".php"}
PY, SQL = {".py"}, {".sql"}
CODIGO = JS | MODELOS | PY | SQL | {".rb", ".go", ".java", ".kt", ".cs", ".ex", ".exs", ".rs"}
MANIFESTOS = {"package.json", "requirements.txt", "pyproject.toml", "Gemfile", "go.mod",
              "composer.json", "Cargo.toml"}
TRAVAS = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb",
          "npm-shrinkwrap.json", "poetry.lock", "uv.lock", "Pipfile.lock", "Gemfile.lock",
          "go.sum", "composer.lock", "Cargo.lock"}
E_TESTE = re.compile(r"(^|/)(tests?|__tests__|specs?|e2e|fixtures?)/|\.(test|spec)\.\w+$"
                     r"|_test\.\w+$|(^|/)test_[^/]*$")
EXEMPLO_DE_ENV = re.compile(r"\.(example|sample|template|dist|defaults?)$", re.I)
LIMITE_DE_BYTES = 1_000_000
I = re.I

# Os prefixos são montados em partes para este arquivo não acusar a si mesmo.
CHAVES = [(rotulo, re.compile(padrao)) for rotulo, padrao in [
    ("bloco de chave privada", "-----BEGIN [A-Z ]*PRIV" + "ATE KEY-----"),
    ("chave secreta de pagamento, de produção", r"\b[sr]k_" + "live" + r"_[0-9A-Za-z]{16,}"),
    ("chave secreta de pagamento, de teste", r"\b[sr]k_" + "test" + r"_[0-9A-Za-z]{16,}"),
    ("segredo de webhook", r"\bwh" + "sec" + r"_[0-9A-Za-z]{16,}"),
    ("chave de acesso de nuvem", r"\bAK" + "IA" + r"[0-9A-Z]{16}\b"),
    ("token de hospedagem de código", r"\b(gh[pousr]_|github_" + r"pat_|gl" + r"pat-)[\w-]{20,}"),
    ("token de mensageria", r"\bxox" + r"[abprs]-[0-9A-Za-z-]{10,}"),
    ("chave de API de nuvem", r"\bAI" + r"za[0-9A-Za-z_-]{35}\b"),
    ("token JWT", r"\beyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,}"),
    ("endereço de banco com senha",
     r"\b(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp)://[^\s:/@]+:[^\s@/$<{]{3,}@"),
]]
ATRIBUICAO = re.compile(
    r"\b(\w*(?:SECRET|TOKEN|PASSWORD|PASSWD|SENHA|API_?KEY|PRIVATE_?KEY|ACCESS_?KEY)\w*)"
    r"""\s*[:=]\s*["']([^"'\s]{16,})["']""", I)
MARCADOR = re.compile(r"^(<.*>|x{4,}|\*{4,})|exampl|exemplo|changeme|your[_-]|seu[_-]|sua[_-]"
                      r"|placeholder|dummy|fake|process\.env|\$\{|^\w+\.\w+\.\w+$", I)
PUBLICA = re.compile(r"\b((?:NEXT_PUBLIC|VITE|REACT_APP|EXPO_PUBLIC|NUXT_PUBLIC|GATSBY|PUBLIC)"
                     r"_[A-Z0-9_]+)\b")
SUSPEITA = re.compile(r"SECRET|PRIVATE|SERVICE_ROLE|SERVICE_KEY|PASSWORD|PASSWD|SENHA|WEBHOOK"
                      r"|ADMIN|TOKEN")
INOFENSIVA = re.compile(r"PUBLISHABLE|ANON|PUBLIC_KEY|SITE_KEY|CLIENT_KEY|MAPS|ANALYTICS")

SQL_EM_ASPAS = (r"%(a)s[^%(a)s\n]*\b(select\b[^%(a)s\n]*\bfrom|insert\s+into|update\b[^%(a)s\n]*"
                r"\bset|delete\s+from)\b[^%(a)s\n]*%(a)s\s*(\+|%%\s*[\w(]|\.format\s*\()")
REQ = r"(req|request|ctx|context|event)\.(query|body|params)|searchParams|formData\.get|\.nextUrl"
REGRAS = [(area, exts, re.compile(padrao, flags), texto) for area, exts, padrao, flags, texto in [
    ("entrada", JS | MODELOS,
     r"dangerouslySetInnerHTML|\.(inner|outer)HTML\s*=|insertAdjacentHTML\s*\(|document\.write\s*\("
     r"|\bv-html\s*=|\{@html\b|\|\s*safe\b|\.html_safe\b", 0,
     "HTML sem escape: de onde vem o texto?"),
    ("entrada", JS, r"(?<![.\w])eval\s*\(|\bnew\s+Function\s*\(|\bvm\.runIn\w+\s*\("
                    r"|\bset(Timeout|Interval)\s*\(\s*[\"'`]", 0,
     "texto executado como código"),
    ("entrada", PY, r"(?<![.\w])(eval|exec)\s*\(|\bos\.(system|popen)\s*\(|shell\s*=\s*True"
                    r"|\bpickle\.loads?\s*\(|yaml\.load\s*\((?![^)\n]*Loader)", 0,
     "texto executado como código ou comando"),
    ("entrada", JS, r"\b(exec|execSync|spawn|spawnSync)\s*\(\s*(`[^`\n]*\$\{|[\"'][^\"'\n]*[\"']"
                    r"\s*\+)|\bshell\s*:\s*true", 0, "comando do sistema montado com texto"),
    ("entrada", JS | PY, SQL_EM_ASPAS % {"a": '"'} + "|" + SQL_EM_ASPAS % {"a": "'"}
     + r"|\.execute\s*\(\s*f[\"']", I, "SQL montado por concatenação: use parâmetro"),
    ("entrada", JS, r"\$(query|execute)RawUnsafe|\bsql\.raw\s*\(|\.unsafe\s*\(|\bknex\.raw\s*\(", 0,
     "SQL cru: confira se algum valor da requisição entra no texto"),
    ("entrada", JS | PY,
     r"\b(redirect|permanentRedirect|router\.(push|replace)|location\.(href|assign|replace))\b"
     r"[^\n]*(" + REQ + r"|\b(next|returnTo|return_to|callbackUrl|redirect_?[tT]o|redirectUrl)\b)",
     0, "redirecionamento com valor da requisição: confira a lista de destinos aceitos"),
    ("entrada", JS, r"\b(readFile|readFileSync|createReadStream|writeFile|writeFileSync|unlink"
                    r"|sendFile|path\.(join|resolve))\s*\([^)\n]*(" + REQ + r")", 0,
     "caminho de arquivo com valor da requisição"),
    ("entrada", JS | PY, r"\b(fetch|axios(\.\w+)?|got(\.\w+)?|https?\.get|requests\.(get|post))"
                         r"\s*\(\s*(" + REQ + r"|\b(url|uri|href|link|target|endpoint)\b\s*[,)])", 0,
     "requisição do servidor a endereço que pode vir do usuário"),
    ("entrada", JS, r"(\.\.\.|data\s*:\s*|\(\s*)(req|request)\.body\b(?!\.)", 0,
     "corpo inteiro da requisição gravado: valide e escolha os campos"),
    ("banco", SQL, r"\b(using|with\s+check)\s*\(\s*true\s*\)", I,
     "regra por linha que libera tudo: o conteúdo da tabela ainda é todo público?"),
    ("banco", SQL, r"\bgrant\s+all\b[^;\n]*\bto\b[^;\n]*\b(anon|public|authenticated)\b", I,
     "concede tudo a um papel público"),
    ("banco", SQL, r"\bdisable\s+row\s+level\s+security\b", I, "regra por linha desligada"),
    ("sessao", JS, r"\bhttpOnly\s*:\s*false|\bsecure\s*:\s*false|\bsameSite\s*:\s*[\"']none[\"']", I,
     "cookie com proteção desligada"),
    ("sessao", JS, r"(local|session)Storage\.setItem\s*\([^)\n]*(token|jwt|session|secret)", I,
     "token guardado onde qualquer script da página lê"),
    ("sessao", JS | PY, r"\bjwt\.decode\s*\(|algorithms?\s*[:=]\s*\[?\s*[\"']none[\"']"
                        r"|ignoreExpiration\s*:\s*true|verify_signature[\"']?\s*:\s*False", I,
     "token aceito sem conferir a assinatura ou o prazo"),
    ("sessao", JS | PY, r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED"
                        r"|verify\s*=\s*False", 0, "conferência de certificado desligada"),
    ("sessao", JS, r"(token|secret|password|senha|otp|codigo|code|nonce)\w*\s*[:=][^\n]*"
                   r"Math\.random\s*\(", I, "código ou token gerado com aleatório previsível"),
    ("sessao", JS | PY, r"createHash\s*\(\s*[\"'](md5|sha1)[\"']|hashlib\.(md5|sha1)\s*\(", I,
     "resumo fraco: confira se guarda senha ou assina algo"),
    ("arquivos", JS, r"\bexpiresIn\s*:\s*(\d[\d_]{4,})|createSignedUrl\s*\([^,\n]+,\s*(\d[\d_]{4,})",
     0, "link assinado com prazo de 10.000 segundos ou mais"),
    ("arquivos", JS, r"\bgetPublicUrl\s*\(|\bpublic\s*:\s*true\b|ACL\s*:\s*[\"']public-read", 0,
     "arquivo com endereço público: nada pago ou privado pode estar aí"),
    ("arquivos", JS, r"\bfile\.(type|size)\b|\.mimetype\b", 0,
     "tipo ou tamanho informado pelo navegador: o servidor confere de novo?"),
    ("arquivos", JS, r"\b(price|priceId|amount|unit_amount|preco|valor|plan|plano)\w*\s*:\s*[^,\n]*"
                     r"(" + REQ + r"|\b(body|input|payload)\.)", I,
     "preço ou plano lido da requisição: quem decide o valor é o servidor"),
    ("cache", JS | PY, r"Cache-Control[^\n]*\b(public|s-maxage)\b", I,
     "resposta liberada para cache compartilhado: ela depende de quem pede?"),
    ("bordas", JS | PY, r"Access-Control-Allow-Origin[\"']?\s*[,:)]\s*[\"']\*[\"']|\bcors\s*\(\s*\)"
                        r"|\borigin\s*:\s*(true|[\"']\*[\"'])|allow_origins\s*=\s*\[\s*[\"']\*", I,
     "CORS aberto a qualquer origem"),
    ("erros", JS, r"productionBrowserSourceMaps\s*:\s*true|\bsourcemap\s*:\s*(true|[\"']inline)"
                  r"|\bdevtool\s*:\s*[\"'][^\"']*source-map", 0,
     "mapa de código-fonte ligado: vai para produção?"),
    ("erros", JS | PY, r"\b(json|send|end|write)\s*\([^)\n]*\b(err|error|e|exc)\.(stack|message)\b"
                       r"|\bDEBUG\s*=\s*True\b|\bdebug\s*=\s*True\b", 0,
     "erro interno ou modo de depuração pode chegar à resposta"),
    ("erros", JS | PY, r"\b(console\.(log|info|debug)|print|logger\.\w+)\s*\([^)\n]*"
                       r"(password|senha|token|secret|authorization|cookie)", I,
     "credencial pode ir para o log"),
]]

GUARDA_PADRAO = (r"\b(require|ensure|assert|check|verify|protect|authorize|authenticate)[A-Z_]\w*"
                 r"\s*\(|\b(auth|getUser|getSession|getServerSession|currentUser|getCurrentUser"
                 r"|getToken|validateRequest|isAuthenticated|isAdmin|withAuth)\s*\("
                 r"|\.auth\.(getUser|getSession|getClaims)\s*\(|passport\.authenticate"
                 r"|@login_required|\bDepends\s*\(|\bpermission_classes\b")
ROTAS_POR_ARQUIVO = [(tipo, re.compile(padrao)) for tipo, padrao in [
    ("rota", r"(^|/)app/(.*/)?route\.(ts|tsx|js|jsx|mjs)$"),
    ("rota", r"(^|/)pages/api/.+\.(ts|tsx|js|jsx|mjs)$"),
    ("rota", r"(^|/)server/(api|routes)/.+\.(ts|js|mjs)$"),
    ("rota", r"(^|/)\+(server|page\.server|layout\.server)\.(ts|js)$"),
    ("função de borda", r"(^|/)(supabase|netlify)/functions/.+\.(ts|js|mjs)$"),
    ("página", r"(^|/)app/(.*/)?page\.(tsx|jsx|ts|js)$"),
    ("página", r"(^|/)app/routes/.+\.(tsx|ts|jsx|js)$"),
]]
METODOS = re.compile(r"export\s+(?:async\s+)?(?:function|const)\s+"
                     r"(GET|POST|PUT|PATCH|DELETE|action|loader|load|actions)\b")
ROTA_NO_CODIGO = re.compile(r"\b(?:app|router|server|fastify|hono|routes?)\.(get|post|put|patch"
                            r"|delete|all)\s*\(\s*[\"'`]([/*][^\"'`\n]*)[\"'`]")
ROTA_EM_PYTHON = re.compile(r"^\s*@\w+(?:\.\w+)*\.(route|get|post|put|patch|delete)\s*\(\s*"
                            r"[\"'](/[^\"']*)[\"']")
USE_SERVER = re.compile(r"""^\s*["']use server["']""", re.M)
EXPORTADA = re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)"
                       r"|^export\s+const\s+(\w+)\s*=\s*(?:async\b|\w+\()")
AREA_PRIVADA = re.compile(r"admin|conta|account|dashboard|painel|settings|perfil|profile|billing"
                          r"|assinatura|pedido|order|checkout", I)
SENSIVEL = re.compile(r"login|log-in|signin|sign-in|signup|sign-up|entrar|cadastr|register|otp"
                      r"|codigo|verif|reset|recuper|senha|password|magic|convite|invite|contato"
                      r"|contact", I)
VERIFICA_ASSINATURA = re.compile(r"constructEvent|verifyHeader|verify_header|construct_event"
                                 r"|createHmac|timingSafeEqual|compare_digest|\bhmac\b|svix"
                                 r"|verif\w*Signature|verify_signature|validateSignature", I)
CORPO_COMO_JSON = re.compile(r"\b(request|req)\.json\(\s*\)|\b(express|bodyParser)\.json\(")
SQL_NO_MODELO = re.compile(r"\b(select\b.{0,400}?\bfrom|insert\s+into|update\b.{0,200}?\bset"
                           r"|delete\s+from)\b", I | re.S)
CACHE = re.compile(r"""["']use cache["']|\bunstable_cache\s*\(""")
LE_SESSAO = re.compile(r"\bcookies\s*\(|\bheaders\s*\(|getSession|getUser|\bauth\s*\(")
LIMITADOR = re.compile(r"rate.?limit|throttl|slowDown|too many requests|\b429\b", I)
CABECALHOS = re.compile(r"Content-Security-Policy|Strict-Transport-Security|X-Frame-Options"
                        r"|frame-ancestors|X-Content-Type-Options|\bhelmet\s*\(", I)


class Relato:
    def __init__(self):
        self.pontos = {area: [] for area, _ in AREAS}
        self.notas = {area: [] for area, _ in AREAS}

    def ponto(self, area, rel, linha, texto):
        self.pontos[area].append("%s  %s" % ("%s:%d" % (rel, linha) if linha else rel, texto))

    def nota(self, area, texto):
        self.notas[area].append(texto)


def pelo_git(raiz):
    # Rastreados (True) e os ainda não rastreados que o git não ignora (False). None sem git.
    achados = []
    for rastreado, opcoes in ((True, []), (False, ["--others", "--exclude-standard"])):
        try:
            saida = subprocess.run(["git", "-C", raiz, "ls-files", "-z"] + opcoes,
                                   capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        if saida.returncode != 0:
            return None
        achados += [(p, rastreado) for p in saida.stdout.decode("utf-8", "replace").split("\0") if p]
    return achados or None


def pela_pasta(raiz):
    achados = []
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = sorted(s for s in subpastas if s not in PASTAS_IGNORADAS)
        for nome in sorted(arquivos):
            achados.append((os.path.relpath(os.path.join(pasta, nome), raiz), None))
    return achados


def ler(caminho):
    try:
        if os.path.getsize(caminho) > LIMITE_DE_BYTES:
            return None
        with open(caminho, "rb") as arquivo:
            dados = arquivo.read()
    except OSError:
        return None
    return None if b"\0" in dados[:4096] else dados.decode("utf-8", "replace")


def linha_de(texto, posicao):
    return texto.count("\n", 0, posicao) + 1


def conferir_segredos(relato, rel, linhas, rastreado, publicas):
    extra = " (arquivo ainda não rastreado, e não ignorado)" if rastreado is False else ""
    for numero, linha in enumerate(linhas, 1):
        if len(linha) > 4000:
            continue
        achou = False
        for rotulo, padrao in CHAVES:
            if padrao.search(linha):
                achou = True
                relato.ponto("segredos", rel, numero, "%s escrito no arquivo (valor oculto)%s"
                             % (rotulo, extra))
        m = ATRIBUICAO.search(linha)
        if m and not achou and not MARCADOR.search(m.group(2)) and len(set(m.group(2))) > 5:
            relato.ponto("segredos", rel, numero, "atribuição com cara de segredo: %s (valor "
                         "oculto, %d caracteres)%s" % (m.group(1), len(m.group(2)), extra))
        for m in PUBLICA.finditer(linha):
            resto = m.group(1).split("PUBLIC_", 1)[-1] if "PUBLIC_" in m.group(1) else m.group(1)
            if SUSPEITA.search(resto) or ("KEY" in resto and not INOFENSIVA.search(resto)):
                publicas.setdefault(m.group(1), (rel, numero))


def conferir_sql(relato, rel, texto, tabelas, com_regra):
    limpo = re.sub(r"--[^\n]*", lambda m: " " * len(m.group()), texto)
    for m in re.finditer(r"\bcreate\s+(?:or\s+replace\s+)?function\s+([\w.\"]+)", limpo, I):
        fim = re.search(r"\bcreate\s+(?:or\s+replace\s+)?(function|table|view|policy|trigger)\b",
                        limpo[m.end():], I)
        bloco = limpo[m.start():m.end() + (fim.start() if fim else len(limpo))]
        if re.search(r"security\s+definer", bloco, I):
            if "search_path" not in bloco.lower():
                relato.ponto("banco", rel, linha_de(limpo, m.start()), "função com privilégio do "
                             "dono sem caminho de busca fixo: %s" % m.group(1))
            relato.nota("banco", "função com privilégio do dono: %s:%d  %s (confira a guarda na "
                        "primeira linha e quem pode executar)" % (rel, linha_de(limpo, m.start()),
                                                                   m.group(1)))
    for m in re.finditer(r"\bcreate\s+(?:or\s+replace\s+)?view\s+([\w.\"]+)[^;]*;", limpo, I):
        if "security_invoker" not in m.group(0).lower():
            relato.ponto("banco", rel, linha_de(limpo, m.start()), "visão que roda com os direitos "
                         "do dono: %s (é atualizável? quem tem privilégio nela?)" % m.group(1))
    for m in re.finditer(r"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)", limpo, I):
        tabelas.setdefault(m.group(1).replace('"', "").split(".")[-1].lower(),
                           (rel, linha_de(limpo, m.start())))
    for m in re.finditer(r"\balter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?([\w.\"]+)\s+enable"
                         r"\s+row\s+level\s+security", limpo, I):
        com_regra.add(m.group(1).replace('"', "").split(".")[-1].lower())


def conferir_modelos_de_sql(relato, rel, texto):
    # Texto entre crases com SQL e ${}: pareamento simples das crases, sem entender aninhamento.
    partes = texto.split("`")
    posicao = 0
    for indice, parte in enumerate(partes):
        if indice % 2 == 1 and "${" in parte and SQL_NO_MODELO.search(parte):
            anterior = partes[indice - 1][-1:]
            aviso = ("SQL em texto com ${}: com etiqueta, confira se a biblioteca vira parâmetro"
                     if anterior.isalnum() or anterior in ")>" else
                     "SQL montado com ${} dentro do texto: use parâmetro")
            relato.ponto("entrada", rel, linha_de(texto, posicao), aviso)
        posicao += len(parte) + 1


def inventariar(relato, rel, ext, texto, linhas, guarda, sensiveis):
    def registrar(linha, descricao, tem_guarda, mostrar=True, sem="sem guarda aparente"):
        local = "%s:%d" % (rel, linha) if linha else rel
        relato.total_de_rotas += 1
        if SENSIVEL.search(rel + " " + descricao):
            sensiveis.append("%s  %s" % (local, descricao))
        if tem_guarda:
            relato.nota("rotas", "guarda aparente: %s  %s" % (local, descricao))
        elif mostrar:
            relato.pontos["rotas"].append("%s  %s: %s" % (local, sem, descricao))

    # Na linha de uma rota, a guarda costuma vir como middleware, sem parênteses.
    solta = re.compile(guarda.pattern.replace(r"\s*\(", r"\b"))
    for tipo, padrao in ROTAS_POR_ARQUIVO:
        if padrao.search(rel):
            metodos = sorted(set(METODOS.findall(texto)))
            if tipo == "página" and metodos:
                tipo = "rota"
            mostrar = tipo != "página" or bool(AREA_PRIVADA.search(rel))
            descricao = "%s%s" % (tipo, " (%s)" % ", ".join(metodos) if metodos else "")
            registrar(0, descricao, bool(guarda.search(texto)), mostrar)
            break
    if ext in JS and USE_SERVER.search(texto):
        no_topo = bool(re.match(r"""\s*(?:(?://[^\n]*|/\*.*?\*/)\s*)*["']use server["']""", texto,
                                re.S))
        for numero, linha in enumerate(linhas, 1):
            m = EXPORTADA.match(linha) if no_topo else None
            dentro = not no_topo and USE_SERVER.match(linha) and linha[:1] in " \t"
            if not m and not dentro:
                continue
            janela = []
            for seguinte in linhas[numero:numero + 15]:
                if seguinte.startswith("export "):
                    break
                janela.append(seguinte)
            nome = (m.group(1) or m.group(2)) if m else "declarada dentro de função"
            registrar(numero, "ação de servidor %s" % nome, bool(guarda.search("\n".join(janela))),
                      sem="sem guarda aparente nas 15 linhas seguintes")
    for numero, linha in enumerate(linhas, 1):
        m = ROTA_NO_CODIGO.search(linha) if ext in JS else None
        if m:
            registrar(numero, "rota %s %s" % (m.group(1).upper(), m.group(2)),
                      bool(guarda.search(linha) or solta.search(linha)),
                      sem="sem guarda aparente na linha (pode estar em middleware do roteador)")
        m = ROTA_EM_PYTHON.match(linha) if ext in PY else None
        if m:
            vizinhas = "\n".join(linhas[max(0, numero - 4):numero + 4])
            registrar(numero, "rota %s %s" % (m.group(1).upper(), m.group(2)),
                      bool(guarda.search(vizinhas)))


def varrer(raiz, guarda, com_testes):
    relato = Relato()
    relato.total_de_rotas = 0
    arquivos = pelo_git(raiz)
    relato.com_git = arquivos is not None
    arquivos = arquivos if arquivos is not None else pela_pasta(raiz)
    este = os.path.realpath(__file__)
    publicas, tabelas, com_regra, sensiveis, pastas = {}, {}, set(), [], {}
    usa_regra = tem_limitador = tem_cabecalho = False
    lidos = 0
    for rel, rastreado in sorted(arquivos):
        rel = rel.replace(os.sep, "/")
        nome = os.path.basename(rel)
        ext = os.path.splitext(nome)[1].lower()
        caminho = os.path.join(raiz, rel)
        if set(rel.split("/")[:-1]) & PASTAS_IGNORADAS or os.path.realpath(caminho) == este:
            continue
        if nome in MANIFESTOS or nome in TRAVAS:
            pastas.setdefault(os.path.dirname(rel), set()).add(nome)
        if nome in TRAVAS or nome.endswith((".min.js", ".map")):
            continue
        if nome.startswith(".env") and not EXEMPLO_DE_ENV.search(nome):
            if rastreado:
                relato.ponto("segredos", rel, 0, "arquivo de ambiente rastreado pelo git: tire do "
                             "repositório e troque o que houver nele (não foi aberto)")
            continue
        texto = ler(caminho)
        if texto is None:
            continue
        lidos += 1
        linhas = texto.split("\n")
        conferir_segredos(relato, rel, linhas, rastreado, publicas)
        if ext not in CODIGO or (E_TESTE.search(rel) and not com_testes):
            continue
        tem_limitador = tem_limitador or bool(LIMITADOR.search(texto))
        tem_cabecalho = tem_cabecalho or bool(CABECALHOS.search(texto))
        for numero, linha in enumerate(linhas, 1):
            if len(linha) > 1000:
                continue
            for area, exts, padrao, aviso in REGRAS:
                if ext in exts and padrao.search(linha):
                    relato.ponto(area, rel, numero, aviso)
        if ext in SQL:
            usa_regra = usa_regra or bool(re.search(r"row\s+level\s+security|create\s+policy",
                                                    texto, I))
            conferir_sql(relato, rel, texto, tabelas, com_regra)
        if ext in JS:
            conferir_modelos_de_sql(relato, rel, texto)
            m = CACHE.search(texto)
            if m and LE_SESSAO.search(texto):
                relato.ponto("cache", rel, linha_de(texto, m.start()), "cache e leitura de sessão "
                             "no mesmo arquivo: a resposta de uma pessoa pode servir a outra")
        if "webhook" in rel.lower() and ext in (JS | PY):
            if not VERIFICA_ASSINATURA.search(texto):
                relato.ponto("webhooks", rel, 0, "webhook sem verificação aparente de assinatura")
            elif CORPO_COMO_JSON.search(texto):
                relato.ponto("webhooks", rel, 0, "corpo lido como JSON: a assinatura vale sobre o "
                             "corpo cru, lido antes")
            else:
                relato.nota("webhooks", "verificação aparente: %s (confira se roda antes de "
                            "qualquer leitura ou gravação)" % rel)
        inventariar(relato, rel, ext, texto, linhas, guarda, sensiveis)
    for nome, (rel, numero) in sorted(publicas.items()):
        relato.ponto("segredos", rel, numero, "variável pública com cara de segredo: %s (variável "
                     "pública vai dentro do JavaScript de todo visitante)" % nome)
    if tabelas and usa_regra:
        for tabela, (rel, numero) in sorted(tabelas.items()):
            if tabela not in com_regra:
                relato.ponto("banco", rel, numero, "tabela sem regra por linha ligada em nenhum "
                             ".sql lido: %s" % tabela)
    elif tabelas:
        relato.nota("banco", "nenhuma regra por linha no SQL lido: o filtro por dono precisa "
                    "estar em toda consulta do aplicativo")
    for item in sensiveis:
        relato.ponto("tentativas", item, 0, "entrada sensível: há limite de tentativas?")
    if lidos and not tem_limitador:
        relato.nota("tentativas", "nenhuma menção a limite de tentativas no código lido: confira "
                    "se a hospedagem ou o provedor de login limita")
    if lidos and not tem_cabecalho:
        relato.nota("bordas", "nenhum cabeçalho de segurança definido no código lido: confira se "
                    "a hospedagem ou o proxy os envia")
    for pasta, nomes in sorted(pastas.items()):
        if nomes & MANIFESTOS and not nomes & TRAVAS and nomes != {"go.mod"}:
            relato.ponto("dependencias", "%s/" % (pasta or "."), 0, "manifesto sem arquivo de "
                         "trava: as versões mudam entre instalações")
    if pastas:
        relato.nota("dependencias", "o comando de auditoria do gerenciador de pacotes acessa a "
                    "rede. Este script não o roda: só com o aval do dono")
    relato.nota("rotas", "%d no inventário. Confira a guarda de cada uma, inclusive as de "
                "\"guarda aparente\"" % relato.total_de_rotas)
    return relato, lidos


def main():
    partes = __doc__.split("\n\n")
    analisador = argparse.ArgumentParser(
        description=partes[0] + "\n\n" + partes[1], epilog="\n\n".join(partes[3:]),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("projeto", help="a pasta do projeto")
    analisador.add_argument("--guarda", help="regex com o nome da guarda do projeto, somada às "
                            "conhecidas (ex.: 'exigeUsuario|exigeAdmin')")
    analisador.add_argument("--so", action="append", choices=[a for a, _ in AREAS],
                            help="mostra só esta área (pode repetir)")
    analisador.add_argument("--limite", type=int, default=40,
                            help="linhas por área (padrão: 40; 0 mostra tudo)")
    analisador.add_argument("--com-testes", action="store_true",
                            help="inclui arquivos de teste nos usos perigosos e no inventário")
    args = analisador.parse_args()
    raiz = os.path.abspath(args.projeto)
    if not os.path.isdir(raiz):
        print("erro: pasta não encontrada: %s" % args.projeto, file=sys.stderr)
        return 2
    try:
        guarda = re.compile(GUARDA_PADRAO + ("|" + args.guarda if args.guarda else ""))
    except re.error as erro:
        print("erro: --guarda não é uma regex válida (%s)" % erro, file=sys.stderr)
        return 2
    relato, lidos = varrer(raiz, guarda, args.com_testes)
    print("varredura de %s: %d arquivos lidos (%s)" % (
        raiz, lidos, "lista do git" if relato.com_git else "sem git: pasta inteira"))
    print("Leitura por texto: aponta onde olhar, não prova vulnerabilidade, e não achar não prova "
          "que não há.")
    if not lidos:
        print("não conferi: nenhum arquivo lido")
        return 3
    total = areas_com_ponto = 0
    for area, titulo in AREAS:
        if args.so and area not in args.so:
            continue
        pontos, notas = relato.pontos[area], relato.notas[area]
        total += len(pontos)
        areas_com_ponto += 1 if pontos else 0
        print("\n== %s [%s]: %d ponto(s)" % (titulo, area, len(pontos)))
        for prefixo, itens in (("olhe: ", pontos), ("nota: ", notas)):
            corte = args.limite if args.limite > 0 else len(itens)
            for item in itens[:corte]:
                print(prefixo + item)
            if len(itens) > corte:
                print("... e mais %d (rode com --so %s --limite 0)" % (len(itens) - corte, area))
    print("\nresumo: %d ponto(s) em %d área(s). Cada ponto é uma pergunta para a leitura, não um "
          "achado." % (total, areas_com_ponto))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
