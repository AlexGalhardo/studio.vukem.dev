#!/usr/bin/env python3
"""relatorio.py: lê achados.json e gera o relatório de auditoria em PDF e em Markdown.

Só biblioteca padrão: o PDF é escrito por este arquivo (A4, Helvetica, codificação WinAnsi).
Não acessa a rede e não lê nada além do arquivo de achados.

uso:
  python3 relatorio.py <achados.json> [--saida <pasta>] [--nome <base>] [--so-validar]

saída: 0 gerado (ou válido, com --so-validar);
       1 achados.json inválido: lista cada campo que falta e não gera nada;
       2 uso errado, arquivo ausente ou JSON malformado;
       3 gerado com aviso (campo desconhecido, ou caractere fora do WinAnsi trocado por "?").

limites: texto corrido, sem imagem e sem tabela; emoji e alfabeto não latino viram "?" no PDF (o
Markdown guarda o texto original); o resumo executivo cabe em uma página porque os textos dele
têm teto de caracteres. O mesmo arquivo de achados gera sempre o mesmo PDF, byte a byte.
"""

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata
import zlib

GRAVIDADES = ["critico", "alto", "medio", "baixo", "informativo"]
ROTULO = {"critico": "Crítico", "alto": "Alto", "medio": "Médio", "baixo": "Baixo",
          "informativo": "Informativo"}
COR = {"critico": (0.69, 0.11, 0.13), "alto": (0.82, 0.36, 0.05), "medio": (0.67, 0.49, 0.02),
       "baixo": (0.16, 0.40, 0.66), "informativo": (0.40, 0.43, 0.47)}
CRITERIO = {
    "critico": "sem conta, ou com uma conta comum, lê ou altera dado de todas as pessoas, assume "
               "a conta de outra, executa código no servidor ou obtém um segredo que dá isso.",
    "alto": "com uma conta comum, alcança dado de outra pessoa, conteúdo pago ou ação de "
            "administrador; ou, sem conta, alcança dado de parte das pessoas.",
    "medio": "precisa de uma condição a mais (a vítima clicar, um identificador difícil de "
             "adivinhar, uma janela de tempo) ou o estrago é limitado a pouco dado.",
    "baixo": "sozinho não dá acesso: revela informação interna ou facilita outro ataque.",
    "informativo": "boa prática ausente, sem cenário de exploração escrito.",
}
ESTADOS = ["comprovado com teste", "encontrado na leitura"]
ESFORCOS = {"pequeno": "pequeno (até 2 horas)", "medio": "médio (até 1 dia)",
            "grande": "grande (mais de 1 dia)"}
SITUACOES = {"aberto": "aberto", "corrigido": "corrigido e reconferido",
             "aceito": "risco aceito pelo dono"}
NAO_COBRE = [
    "Não é um teste de invasão profissional e não garante ausência de falha: lista o que foi "
    "encontrado no escopo, na data e com o método descritos.",
    "Achado \"encontrado na leitura\" não foi reproduzido: pode existir uma barreira que a "
    "leitura não viu, e o impacto pode ser maior ou menor que o descrito.",
    "Ficam de fora engenharia social, segurança física, as contas pessoais da equipe e a "
    "infraestrutura dos fornecedores (hospedagem, banco, provedor de pagamento e de login).",
    "Não houve teste de carga, negação de serviço, força bruta nem varredura agressiva.",
    "O que mudar no sistema depois da data deste relatório não está coberto. Refaça a auditoria "
    "a cada mudança grande em acesso, pagamento ou upload.",
]
CAMPOS_RELATORIO = {"sistema", "exemplo_ficticio", "data", "versao", "pedido_por", "auditado_por",
                    "confirmacao_de_escopo", "escopo", "metodo", "resumo", "nao_cobre"}
CAMPOS_ACHADO = {"id", "titulo", "gravidade", "area", "onde", "consegue", "precisa", "cenario",
                 "evidencia", "estado", "correcao", "esforco", "situacao", "reconferencia",
                 "aceite", "ordem"}

PRETO, CINZA, CLARO, BRANCO = (0.10, 0.11, 0.13), (0.38, 0.41, 0.45), (0.80, 0.83, 0.87), (1, 1, 1)
ESCURO, AMBAR, FIO = (0.11, 0.15, 0.22), (0.67, 0.49, 0.02), (0.82, 0.84, 0.87)

# Larguras da Helvetica e da Helvetica-Bold (AFM, por mil), do código 32 ao 126. Letra acentuada
# tem a largura da letra sem acento.
_REGULAR = (
    "278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556 556 556 556 556 556 556 "
    "556 556 556 278 278 584 584 584 556 1015 667 667 722 722 667 611 778 722 278 500 667 556 833 "
    "722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 556 556 500 556 "
    "556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 "
    "260 334 584")
_NEGRITO = (
    "278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556 556 556 556 556 556 556 "
    "556 556 556 333 333 584 584 584 611 975 722 722 722 722 667 611 778 722 278 556 722 611 833 "
    "722 778 667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 333 556 611 556 611 "
    "556 333 611 611 278 278 556 278 889 611 611 611 611 389 556 333 611 556 778 556 556 500 389 "
    "280 389 584")
LARGURAS = {"F1": [int(n) for n in _REGULAR.split()], "F2": [int(n) for n in _NEGRITO.split()]}
LARGURAS["F3"] = LARGURAS["F1"]
OUTRAS = {"–": 556, "—": 1000, "…": 1000, "•": 350, "“": 333,
          "”": 333, "‘": 222, "’": 222, "º": 365, "ª": 370, "°": 400,
          "·": 278, "§": 556, "«": 556, "»": 556, "€": 556}
TROCAS = {" ": " ", "\t": " ", "\r": "", "→": "->", "←": "<-", "≥": ">=",
          "≤": "<=", "≠": "!=", "✓": "ok", "−": "-"}
_trocados = [0]


def limpar(texto):
    # Deixa só o que a codificação WinAnsi (cp1252) representa; conta o que virou "?".
    saida = []
    for ch in unicodedata.normalize("NFC", str(texto)):
        ch = TROCAS.get(ch, ch)
        if ch == "\n" or ch == "":
            saida.append(ch)
        elif ord(ch[0]) < 32:
            saida.append(" ")
        else:
            try:
                ch.encode("cp1252")
                saida.append(ch)
            except UnicodeEncodeError:
                saida.append("?")
                _trocados[0] += 1
    return "".join(saida)


def largura(texto, fonte, tam):
    tabela, total = LARGURAS[fonte], 0
    for ch in texto:
        codigo = ord(ch)
        if 32 <= codigo <= 126:
            total += tabela[codigo - 32]
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        total += tabela[ord(base) - 32] if 32 <= ord(base) <= 126 else OUTRAS.get(ch, 556)
    return total * tam / 1000.0


def quebrar(texto, fonte, tam, maximo):
    maximo *= 0.985  # folga para a diferença entre a tabela e a fonte do leitor
    linhas = []
    for paragrafo in texto.split("\n"):
        atual = ""
        for palavra in paragrafo.split(" "):
            if not palavra:
                continue
            while largura(palavra, fonte, tam) > maximo:  # palavra maior que a linha: corta
                if atual:
                    linhas.append(atual)
                    atual = ""
                corte = len(palavra)
                while corte > 1 and largura(palavra[:corte], fonte, tam) > maximo:
                    corte -= 1
                linhas.append(palavra[:corte])
                palavra = palavra[corte:]
            tentativa = palavra if not atual else atual + " " + palavra
            if largura(tentativa, fonte, tam) <= maximo:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


class Pdf:
    """Escritor mínimo de PDF 1.4: páginas A4, três fontes padrão, texto e retângulo."""

    L, A = 595.28, 841.89
    FONTES = (("F1", "Helvetica"), ("F2", "Helvetica-Bold"), ("F3", "Helvetica-Oblique"))

    def __init__(self):
        self.paginas = []

    def pagina(self):
        self.paginas.append([])

    def ret(self, x, y, larg, alt, cor, indice=-1):
        self.paginas[indice].append(
            b"%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (tuple(cor) + (x, y, larg, alt)))

    def texto(self, x, y, texto, fonte="F1", tam=10, cor=PRETO, indice=-1):
        cru = texto.encode("cp1252", "replace")
        cru = cru.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        self.paginas[indice].append(
            b"BT /%s %.1f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET"
            % ((fonte.encode(), tam) + tuple(cor) + (x, y, cru)))

    @staticmethod
    def _cadeia(texto):
        # Texto de metadado em UTF-16 com marca de ordem, escrito em hexadecimal.
        return b"<" + ("﻿" + texto).encode("utf-16-be").hex().upper().encode() + b">"

    def salvar(self, caminho, titulo, autor, data_iso):
        objetos = [b"", b""]  # 1 é o catálogo e 2 é a árvore de páginas, preenchidos no fim
        nomes = []
        for nome, base in self.FONTES:
            objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding "
                           b"/WinAnsiEncoding >>" % base.encode())
            nomes.append(b"/%s %d 0 R" % (nome.encode(), len(objetos)))
        recursos = b"<< /Font << " + b" ".join(nomes) + b" >> >>"
        filhos = []
        for operacoes in self.paginas:
            dados = zlib.compress(b"\n".join(operacoes), 9)
            objetos.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(dados)
                           + dados + b"\nendstream")
            objetos.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources %s "
                           b"/Contents %d 0 R >>" % (self.L, self.A, recursos, len(objetos)))
            filhos.append(b"%d 0 R" % len(objetos))
        objetos[0] = b"<< /Type /Catalog /Pages 2 0 R /Lang (pt-BR) >>"
        objetos[1] = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(filhos), b" ".join(filhos))
        objetos.append(b"<< /Title %s /Author %s /Producer %s /CreationDate (D:%s120000Z) >>" % (
            self._cadeia(titulo), self._cadeia(autor), self._cadeia("relatorio.py"),
            data_iso.replace("-", "").encode()))
        saida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        posicoes = []
        for numero, corpo in enumerate(objetos, 1):
            posicoes.append(len(saida))
            saida += b"%d 0 obj\n" % numero + corpo + b"\nendobj\n"
        inicio = len(saida)
        saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
        for posicao in posicoes:
            saida += b"%010d 00000 n \n" % posicao
        saida += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objetos) + 1, len(objetos), inicio)
        with open(caminho, "wb") as arquivo:
            arquivo.write(bytes(saida))


class Folha:
    """Cursor de escrita: margens, quebra de linha e de página."""

    ME, MD, MS, MI = 56, 56, 66, 62

    def __init__(self, pdf):
        self.pdf = pdf
        self.y = 0
        self.util = Pdf.L - self.ME - self.MD

    def nova(self):
        self.pdf.pagina()
        self.y = Pdf.A - self.MS

    def garantir(self, altura):
        if self.y - altura < self.MI:
            self.nova()

    def escrever(self, texto, fonte="F1", tam=10, cor=PRETO, recuo=0, depois=6):
        passo = tam * 1.38
        for linha in quebrar(limpar(texto), fonte, tam, self.util - recuo):
            self.garantir(passo)
            self.y -= passo
            self.pdf.texto(self.ME + recuo, self.y, linha, fonte, tam, cor)
        self.y -= depois

    def marcado(self, marca, texto, recuo=14):
        self.garantir(14)
        self.pdf.texto(self.ME, self.y - 13.8, limpar(marca), "F1", 10, CINZA)
        self.escrever(texto, recuo=recuo, depois=3)

    def faixa(self, texto, cor, altura=22):
        self.pdf.ret(self.ME, self.y - altura, self.util, altura, cor)
        self.pdf.texto(self.ME + 9, self.y - altura + 7, limpar(texto), "F2", 10.5, BRANCO)
        self.y -= altura + 4


def situacao(achado):
    return achado.get("situacao", "aberto")


def em_lista(valor):
    return [valor] if isinstance(valor, str) else list(valor or [])


def data_br(iso):
    dia = datetime.date.fromisoformat(iso)
    return "%02d/%02d/%04d" % (dia.day, dia.month, dia.year)


def _texto(obj, chave, onde, erros, teto=None):
    valor = obj.get(chave) if isinstance(obj, dict) else None
    if not isinstance(valor, str) or not valor.strip():
        erros.append('%s: falta "%s" (texto)' % (onde, chave))
        return ""
    if teto and len(valor) > teto:
        erros.append('%s: "%s" tem %d caracteres; o teto é %d' % (onde, chave, len(valor), teto))
    return valor.strip()


def _lista(obj, chave, onde, erros, minimo=1, maximo=None, teto=None):
    valor = obj.get(chave) if isinstance(obj, dict) else None
    valor = [valor] if isinstance(valor, str) else valor
    if not isinstance(valor, list) or any(not isinstance(v, str) or not v.strip() for v in valor):
        erros.append('%s: falta "%s" (lista de textos, sem item vazio)' % (onde, chave))
        return []
    if len(valor) < minimo:
        erros.append('%s: "%s" precisa de ao menos %d item' % (onde, chave, minimo))
    if maximo is not None and len(valor) > maximo:
        erros.append('%s: "%s" aceita até %d itens (tem %d)' % (onde, chave, maximo, len(valor)))
    if teto and any(len(v) > teto for v in valor):
        erros.append('%s: item de "%s" passa de %d caracteres' % (onde, chave, teto))
    return valor


def _opcao(obj, chave, opcoes, onde, erros):
    if obj.get(chave) not in opcoes:
        erros.append('%s: "%s" precisa ser um de: %s' % (onde, chave, ", ".join(opcoes)))


def validar(dados):
    erros, avisos = [], []
    if not isinstance(dados, dict):
        return ["a raiz do arquivo precisa ser um objeto com \"relatorio\" e \"achados\""], avisos
    rel = dados.get("relatorio")
    if not isinstance(rel, dict):
        erros.append('falta "relatorio" (objeto)')
        rel = {}
    for chave in ("sistema", "pedido_por", "auditado_por", "confirmacao_de_escopo"):
        _texto(rel, chave, "relatorio", erros, 200)
    try:
        datetime.date.fromisoformat(rel.get("data"))
    except (TypeError, ValueError):
        erros.append('relatorio: "data" precisa ser uma data no formato AAAA-MM-DD')
    versao = rel.get("versao")
    if not isinstance(versao, int) or isinstance(versao, bool) or versao < 1:
        erros.append('relatorio: "versao" precisa ser um número inteiro, a partir de 1')
    partes = {}
    for nome in ("escopo", "metodo", "resumo"):
        partes[nome] = rel.get(nome) if isinstance(rel.get(nome), dict) else {}
    for chave in ("dentro", "fora", "ambientes"):
        _lista(partes["escopo"], chave, "relatorio.escopo", erros, teto=300)
    for chave in ("testado", "nao_testado"):
        _lista(partes["metodo"], chave, "relatorio.metodo", erros, teto=300)
    _texto(partes["resumo"], "parecer", "relatorio.resumo", erros, 700)
    riscos = _lista(partes["resumo"], "riscos_principais", "relatorio.resumo", erros, 0, 3, 320)
    if "nao_cobre" in rel:
        _lista(rel, "nao_cobre", "relatorio", erros, 0, teto=300)
    for chave in sorted(set(rel) - CAMPOS_RELATORIO):
        avisos.append('relatorio: campo desconhecido "%s" foi ignorado' % chave)
    achados = dados.get("achados")
    if not isinstance(achados, list):
        erros.append('falta "achados" (lista; pode ser vazia)')
        achados = []
    vistos = set()
    for numero, achado in enumerate(achados, 1):
        onde = "achados[%d]" % numero
        if not isinstance(achado, dict):
            erros.append("%s: precisa ser um objeto" % onde)
            continue
        ident = _texto(achado, "id", onde, erros)
        if ident:
            onde = ident
            if not re.match(r"^[A-Z]{2,5}-\d{3}$", ident):
                erros.append('%s: "id" precisa ter o formato SEG-001' % onde)
            if ident in vistos:
                erros.append("%s: id repetido" % onde)
            vistos.add(ident)
        for chave, teto in (("titulo", 160), ("area", 80), ("consegue", 600), ("precisa", 600),
                            ("cenario", 1500), ("evidencia", 1500), ("correcao", 1500)):
            _texto(achado, chave, onde, erros, teto)
        _lista(achado, "onde", onde, erros, teto=200)
        _opcao(achado, "gravidade", GRAVIDADES, onde, erros)
        _opcao(achado, "estado", ESTADOS, onde, erros)
        _opcao(achado, "esforco", list(ESFORCOS), onde, erros)
        if situacao(achado) not in SITUACOES:
            erros.append('%s: "situacao" precisa ser um de: %s' % (onde, ", ".join(SITUACOES)))
        if situacao(achado) == "corrigido":
            _texto(achado, "reconferencia", onde + " (corrigido)", erros, 600)
        if situacao(achado) == "aceito":
            _texto(achado, "aceite", onde + " (aceito)", erros, 300)
        ordem = achado.get("ordem", 1)
        if not isinstance(ordem, int) or isinstance(ordem, bool):
            erros.append('%s: "ordem" precisa ser um número inteiro' % onde)
        for chave in sorted(set(achado) - CAMPOS_ACHADO):
            avisos.append('%s: campo desconhecido "%s" foi ignorado' % (onde, chave))
    abertos = [a for a in achados if isinstance(a, dict) and situacao(a) == "aberto"]
    if abertos and not riscos:
        erros.append('relatorio.resumo: há achado aberto e "riscos_principais" está vazio')
    return erros, avisos


def plano(achados):
    abertos = [a for a in achados if situacao(a) == "aberto"]
    return sorted(abertos, key=lambda a: (a.get("ordem", 10 ** 6), GRAVIDADES.index(a["gravidade"]),
                                          list(ESFORCOS).index(a["esforco"]), a["id"]))


def montar_blocos(dados):
    # A mesma lista de blocos vira o PDF e o Markdown: os dois saem com o mesmo conteúdo.
    rel = dados["relatorio"]
    achados = sorted(dados["achados"], key=lambda a: (GRAVIDADES.index(a["gravidade"]), a["id"]))
    abertos = [a for a in achados if situacao(a) == "aberto"]
    contagem = {g: sum(1 for a in abertos if a["gravidade"] == g) for g in GRAVIDADES}
    quantos = {s: sum(1 for a in achados if situacao(a) == s) for s in SITUACOES}
    blocos = [("capa", rel), ("pagina",), ("h1", "1. Resumo executivo"),
              ("p", "Achados abertos, por gravidade:"), ("caixas", contagem),
              ("p", "Achados: %d · abertos: %d · corrigidos e reconferidos: %d · risco aceito "
                    "pelo dono: %d\nComprovados com teste: %d · encontrados na leitura: %d" % (
                        len(achados), quantos["aberto"], quantos["corrigido"], quantos["aceito"],
                        sum(1 for a in achados if a["estado"] == ESTADOS[0]),
                        sum(1 for a in achados if a["estado"] == ESTADOS[1]))),
              ("h2", "Parecer"), ("p", rel["resumo"]["parecer"])]
    riscos = em_lista(rel["resumo"]["riscos_principais"])
    if riscos:
        blocos.append(("h2", "Os riscos principais"))
        blocos += [("num", n, texto) for n, texto in enumerate(riscos, 1)]
    if not achados:
        blocos.append(("p", "Nenhum achado no escopo auditado. Isso não prova que não há falha: "
                            "veja a seção 5."))
    blocos.append(("nota", "Este relatório lista o que foi encontrado no escopo e na data da capa. "
                           "Não substitui um teste de invasão profissional e não garante "
                           "ausência de falha."))
    blocos += [("pagina",), ("h1", "2. Escopo e método")]
    for titulo, itens in (("Dentro do escopo", rel["escopo"]["dentro"]),
                          ("Fora do escopo", rel["escopo"]["fora"]),
                          ("Ambientes", rel["escopo"]["ambientes"]),
                          ("O que foi testado", rel["metodo"]["testado"]),
                          ("O que não foi testado", rel["metodo"]["nao_testado"])):
        blocos.append(("h2", titulo))
        blocos += [("li", item) for item in em_lista(itens)]
    blocos += [("h2", "Como ler a gravidade"),
               ("p", "A gravidade responde a duas perguntas: o que um atacante consegue e o que "
                     "ele precisa ter para conseguir.")]
    blocos += [("criterio", g, CRITERIO[g]) for g in GRAVIDADES]
    blocos += [("h2", "Como ler o estado"),
               ("li", "Comprovado com teste: o problema foi reproduzido em ambiente local ou de "
                      "homologação, com usuários e dados de teste."),
               ("li", "Encontrado na leitura: o código ou a configuração mostra o problema, e ele "
                      "não foi reproduzido."),
               ("pagina",), ("h1", "3. Achados, por gravidade")]
    if not achados:
        blocos.append(("p", "Nenhum achado."))
    for a in achados:
        blocos.append(("faixa", a["gravidade"], "%s · %s · %s" % (
            a["id"], ROTULO[a["gravidade"]], SITUACOES[situacao(a)])))
        blocos.append(("h3", a["titulo"]))
        campos = [("Área", a["area"]), ("Onde", "\n".join(em_lista(a["onde"]))),
                  ("Estado", a["estado"]), ("O que o atacante consegue", a["consegue"]),
                  ("O que ele precisa ter", a["precisa"]), ("Cenário de exploração", a["cenario"]),
                  ("Evidência", a["evidencia"]), ("Correção", a["correcao"]),
                  ("Esforço da correção", ESFORCOS[a["esforco"]])]
        if situacao(a) == "corrigido":
            campos.append(("Reconferência", a["reconferencia"]))
        if situacao(a) == "aceito":
            campos.append(("Aceite do risco", a["aceite"]))
        blocos += [("campo", rotulo, valor) for rotulo, valor in campos]
        blocos.append(("espaco",))
    blocos += [("pagina",), ("h1", "4. Plano de correção, em ordem")]
    fila = plano(achados)
    if fila:
        blocos.append(("p", "Ordem: primeiro a gravidade, depois o menor esforço. A correção de "
                            "cada item está descrita no achado, na seção 3."))
        blocos += [("num", n, "%s (%s, esforço %s): %s" % (
            a["id"], ROTULO[a["gravidade"]].lower(), ESFORCOS[a["esforco"]], a["titulo"]))
                   for n, a in enumerate(fila, 1)]
    else:
        blocos.append(("p", "Nenhum achado aberto."))
    for chave, titulo, campo in (("corrigido", "Corrigidos e reconferidos", "reconferencia"),
                                 ("aceito", "Riscos aceitos pelo dono", "aceite")):
        grupo = [a for a in achados if situacao(a) == chave]
        if grupo:
            blocos.append(("h2", titulo))
            blocos += [("li", "%s: %s. %s" % (a["id"], a["titulo"], a[campo])) for a in grupo]
    blocos.append(("h1", "5. O que esta auditoria não cobre"))
    blocos += [("li", item) for item in NAO_COBRE + em_lista(rel.get("nao_cobre"))]
    return blocos


def linhas_da_capa(rel):
    return [("Sistema", rel["sistema"]), ("Data", data_br(rel["data"])),
            ("Versão do relatório", str(rel["versao"])), ("Pedido por", rel["pedido_por"]),
            ("Auditado por", rel["auditado_por"]),
            ("Escopo", "; ".join(em_lista(rel["escopo"]["dentro"]))),
            ("Confirmação do escopo", rel["confirmacao_de_escopo"])]


TITULO = "Relatório de auditoria de segurança"
FICTICIO = "Exemplo fictício: nenhum sistema real foi auditado"
SIGILO = ("Confidencial. Este documento descreve falhas que podem estar abertas: não publique e "
          "não guarde no repositório do código.")


def escrever_pdf(blocos, caminho):
    pdf = Pdf()
    f = Folha(pdf)
    rel = blocos[0][1]
    for bloco in blocos:
        tipo = bloco[0]
        if tipo == "capa":
            pdf.pagina()
            pdf.ret(0, Pdf.A - 290, Pdf.L, 290, ESCURO)
            y = Pdf.A - 128
            for linha in quebrar(TITULO, "F2", 28, f.util):
                pdf.texto(f.ME, y, linha, "F2", 28, BRANCO)
                y -= 35
            for linha in quebrar(limpar(rel["sistema"]), "F1", 16, f.util)[:3]:
                pdf.texto(f.ME, y - 6, linha, "F1", 16, CLARO)
                y -= 22
            f.y = Pdf.A - 290 - 26
            if rel.get("exemplo_ficticio"):
                f.faixa(FICTICIO, AMBAR)
                f.y -= 10
            for rotulo, valor in linhas_da_capa(rel)[1:]:
                f.escrever(rotulo, "F2", 8.5, CINZA, depois=0)
                f.escrever(valor, tam=11, depois=9)
            y = 84
            for linha in quebrar(SIGILO, "F3", 9, f.util):
                pdf.texto(f.ME, y, linha, "F3", 9, CINZA)
                y -= 12.5
        elif tipo == "pagina":
            f.nova()
        elif tipo == "h1":
            f.garantir(130)
            f.y -= 8
            f.escrever(bloco[1], "F2", 17, ESCURO, depois=5)
            pdf.ret(f.ME, f.y, f.util, 0.8, FIO)
            f.y -= 8
        elif tipo == "h2":
            f.garantir(60)
            f.y -= 6
            f.escrever(bloco[1], "F2", 11.5, ESCURO, depois=3)
        elif tipo == "h3":
            f.escrever(bloco[1], "F2", 12, PRETO, depois=5)
        elif tipo == "p":
            f.escrever(bloco[1])
        elif tipo == "nota":
            f.y -= 6
            f.escrever(bloco[1], "F3", 9.5, CINZA)
        elif tipo == "li":
            f.marcado("•", bloco[1])
        elif tipo == "num":
            f.marcado("%d." % bloco[1], bloco[2], recuo=18)
        elif tipo == "campo":
            f.garantir(40)
            f.escrever(bloco[1], "F2", 8.5, CINZA, depois=0)
            f.escrever(bloco[2], depois=5)
        elif tipo == "faixa":
            f.garantir(170)
            f.faixa(bloco[2], COR[bloco[1]])
        elif tipo == "espaco":
            f.y -= 14
        elif tipo == "criterio":
            f.garantir(42)
            pdf.ret(f.ME, f.y - 12, 8, 8, COR[bloco[1]])
            f.escrever(ROTULO[bloco[1]], "F2", 10, recuo=14, depois=0)
            f.escrever(bloco[2], recuo=14, depois=4)
        elif tipo == "caixas":
            vao, alt = 8, 58
            larg = (f.util - vao * 4) / 5
            for n, g in enumerate(GRAVIDADES):
                x = f.ME + n * (larg + vao)
                pdf.ret(x, f.y - alt, larg, alt, COR[g])
                pdf.texto(x + 10, f.y - 32, str(bloco[1][g]), "F2", 24, BRANCO)
                pdf.texto(x + 10, f.y - 48, limpar(ROTULO[g]), "F1", 9, BRANCO)
            f.y -= alt + 12
    total = len(pdf.paginas)
    cabecalho = quebrar(limpar("%s · %s" % (TITULO, rel["sistema"])), "F1", 8, f.util)[0]
    for indice in range(1, total):
        pdf.texto(f.ME, Pdf.A - 40, cabecalho, "F1", 8, CINZA, indice)
        pdf.ret(f.ME, Pdf.A - 47, f.util, 0.6, FIO, indice)
        pdf.texto(f.ME, 34, "Confidencial", "F1", 8, CINZA, indice)
        numero = limpar("Página %d de %d" % (indice + 1, total))
        pdf.texto(Pdf.L - f.MD - largura(numero, "F1", 8), 34, numero, "F1", 8, CINZA, indice)
    pdf.salvar(caminho, "%s: %s" % (TITULO, rel["sistema"]), rel["auditado_por"], rel["data"])
    return total


def escrever_markdown(blocos, caminho):
    rel = blocos[0][1]
    saida = []
    for bloco in blocos:
        tipo = bloco[0]
        if tipo == "capa":
            saida.append("# %s\n" % TITULO)
            if rel.get("exemplo_ficticio"):
                saida.append("> %s\n" % FICTICIO)
            saida += ["- **%s:** %s" % par for par in linhas_da_capa(rel)]
            saida.append("\n> %s" % SIGILO)
        elif tipo in ("h1", "h2", "h3"):
            saida.append("\n%s %s\n" % ({"h1": "##", "h2": "###", "h3": "####"}[tipo], bloco[1]))
        elif tipo == "p":
            saida.append(bloco[1].replace("\n", "  \n") + "\n")
        elif tipo == "nota":
            saida.append("\n> %s" % bloco[1])
        elif tipo == "li":
            saida.append("- %s" % bloco[1])
        elif tipo == "num":
            saida.append("%d. %s" % (bloco[1], bloco[2]))
        elif tipo == "campo":
            saida.append("- **%s:** %s" % (bloco[1], bloco[2].replace("\n", "; ")))
        elif tipo == "faixa":
            saida.append("\n### %s" % bloco[2])
        elif tipo == "criterio":
            saida.append("- **%s:** %s" % (ROTULO[bloco[1]], bloco[2]))
        elif tipo == "caixas":
            saida.append("| " + " | ".join(ROTULO[g] for g in GRAVIDADES) + " |")
            saida.append("|" + " --- |" * len(GRAVIDADES))
            saida.append("| " + " | ".join(str(bloco[1][g]) for g in GRAVIDADES) + " |\n")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(saida).rstrip() + "\n")


def main():
    partes = __doc__.split("\n\n")
    analisador = argparse.ArgumentParser(
        description=partes[0] + "\n\n" + partes[1], epilog="\n\n".join(partes[3:]),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("achados", help="o arquivo de achados (modelo: assets/modelos/)")
    analisador.add_argument("--saida", help="pasta de saída (padrão: a pasta do arquivo de achados)")
    analisador.add_argument("--nome", help="nome base (padrão: relatorio-de-seguranca-v<versão>)")
    analisador.add_argument("--so-validar", action="store_true",
                            help="confere o arquivo e não gera nada")
    args = analisador.parse_args()
    try:
        with open(args.achados, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except OSError as erro:
        print("erro: não consegui ler %s (%s)" % (args.achados, erro.strerror), file=sys.stderr)
        return 2
    except ValueError as erro:
        print("erro: JSON malformado em %s: %s" % (args.achados, erro), file=sys.stderr)
        return 2
    erros, avisos = validar(dados)
    for aviso in avisos:
        print("aviso: %s" % aviso)
    if erros:
        for erro in erros:
            print("falta: %s" % erro)
        print("recusado: %d problema(s) no arquivo de achados. Nada foi gerado." % len(erros))
        return 1
    if args.so_validar:
        print("ok: %d achado(s), arquivo válido" % len(dados["achados"]))
        return 3 if avisos else 0
    pasta = args.saida or os.path.dirname(os.path.abspath(args.achados))
    base = args.nome or "relatorio-de-seguranca-v%d" % dados["relatorio"]["versao"]
    try:
        os.makedirs(pasta, exist_ok=True)
        blocos = montar_blocos(dados)
        paginas = escrever_pdf(blocos, os.path.join(pasta, base + ".pdf"))
        escrever_markdown(blocos, os.path.join(pasta, base + ".md"))
    except OSError as erro:
        print("erro: não consegui escrever em %s (%s)" % (pasta, erro.strerror), file=sys.stderr)
        return 2
    if _trocados[0]:
        print("aviso: %d caractere(s) fora do WinAnsi viraram \"?\" no PDF; o Markdown guarda o "
              "texto original" % _trocados[0])
    if dados["relatorio"].get("exemplo_ficticio"):
        print("nota: o arquivo está marcado como exemplo fictício, e a capa diz isso")
    print("pronto: %s (%d páginas) e %s" % (os.path.join(pasta, base + ".pdf"), paginas,
                                            os.path.join(pasta, base + ".md")))
    return 3 if (avisos or _trocados[0]) else 0


if __name__ == "__main__":
    sys.exit(main())
