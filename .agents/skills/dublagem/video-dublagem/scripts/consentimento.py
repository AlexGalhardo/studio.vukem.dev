#!/usr/bin/env python3
"""consentimento.py: o portão desta skill. Sem consentimento registrado, nada roda.

Gerar a voz de uma pessoa com IA só é aceitável com a autorização dela, registrada por escrito. Esta skill
não trabalha sem `som/dublagem/consentimento.json`. Se o arquivo não existir, este script grava um modelo
e sai com **código 2**; se existir incompleto, aponta o que falta e sai com código 2.

O arquivo guarda:
  voz_de               de quem é a voz que será gerada
  quem_autorizou       quem assinou a autorização (normalmente a mesma pessoa)
  data                 data da autorização, AAAA-MM-DD
  texto                o texto da autorização, com as palavras de quem autorizou
  escopo               para que vale (este vídeo, este canal, este prazo)
  como_foi_registrado  e-mail, contrato assinado, vídeo gravado, mensagem — e onde está guardado
  registrado_por       quem anotou aqui
  validade             opcional, AAAA-MM-DD: depois disso o portão fecha de novo

Uso:
  python3 consentimento.py --projeto .                  confere (0 = pode rodar, 2 = falta)
  python3 consentimento.py --projeto . --modelo         grava o modelo para preencher
  python3 consentimento.py --projeto . --voz-de "Nome" --quem "Nome" --data 2026-10-22 \\
      --texto "Autorizo o uso da minha voz gerada por IA para corrigir trechos deste vídeo." \\
      --escopo "vídeo X do canal Y" --como "e-mail de 22/10/2026 guardado em juridico/" --por "Editor"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

CAMPOS = ["voz_de", "quem_autorizou", "data", "texto", "escopo", "como_foi_registrado", "registrado_por"]
MODELO = {
    "voz_de": "PREENCHA: de quem é a voz",
    "quem_autorizou": "PREENCHA: quem assinou a autorização",
    "data": "PREENCHA: AAAA-MM-DD",
    "texto": "PREENCHA: o texto da autorização, nas palavras de quem autorizou",
    "escopo": "PREENCHA: para que vale (este vídeo, este canal, este prazo)",
    "como_foi_registrado": "PREENCHA: e-mail, contrato, vídeo gravado — e onde está guardado",
    "registrado_por": "PREENCHA: quem anotou isto",
    "validade": None,
}


def caminho(projeto):
    return Path(projeto) / "som" / "dublagem" / "consentimento.json"


def gravar_modelo(projeto):
    f = caminho(projeto)
    f.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(MODELO, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texto, encoding="utf-8", newline="\n")
    return f


def conferir(projeto, silencioso=False):
    """Devolve (ok, consentimento, problemas). Grava o modelo quando o arquivo não existe."""
    f = caminho(projeto)
    if not f.is_file():
        gravar_modelo(projeto)
        return False, None, [f"não existe {f}. Gravei o modelo: preencha e rode de novo."]
    try:
        c = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, None, [f"{f} não é um JSON válido: {e}"]
    problemas = []
    for campo in CAMPOS:
        v = str(c.get(campo) or "").strip()
        if not v:
            problemas.append(f"falta o campo {campo!r}")
        elif v.upper().startswith("PREENCHA"):
            problemas.append(f"o campo {campo!r} ainda está com o texto do modelo")
    for campo in ("data", "validade"):
        v = c.get(campo)
        if v and not str(v).upper().startswith("PREENCHA"):
            try:
                d = dt.date.fromisoformat(str(v))
            except ValueError:
                problemas.append(f"{campo} não está em AAAA-MM-DD: {v!r}")
                continue
            if campo == "data" and d > dt.date.today():
                problemas.append(f"a data da autorização está no futuro: {v}")
            if campo == "validade" and d < dt.date.today():
                problemas.append(f"a autorização venceu em {v}. Peça uma nova.")
    if len(str(c.get("texto") or "")) < 25:
        problemas.append("o texto da autorização está curto demais para valer como registro")
    if not silencioso and not problemas:
        print(f"consentimento ok: voz de {c['voz_de']}, autorizada por {c['quem_autorizou']} em {c['data']} "
              f"({c['escopo']}; registro: {c['como_foi_registrado']})")
    return not problemas, c, problemas


def exigir(projeto):
    """Usado pelos outros scripts: encerra com código 2 se não houver consentimento válido."""
    ok, c, problemas = conferir(projeto, silencioso=True)
    if not ok:
        print("ESTA SKILL NÃO RODA SEM CONSENTIMENTO REGISTRADO.", file=sys.stderr)
        for p in problemas:
            print(f"   ✗ {p}", file=sys.stderr)
        print(f"\nArquivo: {caminho(projeto)}\nPeça a autorização à pessoa, registre aqui e rode de novo.",
              file=sys.stderr)
        sys.exit(2)
    return c


def main():
    ap = argparse.ArgumentParser(description="Registro de consentimento para dublagem com voz de IA.")
    ap.add_argument("--projeto", default=".", help="pasta do projeto (onde fica som/)")
    ap.add_argument("--modelo", action="store_true", help="grava o modelo e sai")
    ap.add_argument("--voz-de")
    ap.add_argument("--quem", help="quem autorizou")
    ap.add_argument("--data", help="AAAA-MM-DD")
    ap.add_argument("--texto", help="o texto da autorização")
    ap.add_argument("--escopo")
    ap.add_argument("--como", help="como foi registrado e onde está guardado")
    ap.add_argument("--por", help="quem anotou")
    ap.add_argument("--validade", help="AAAA-MM-DD (opcional)")
    a = ap.parse_args()
    if a.modelo:
        print(f"modelo gravado em {gravar_modelo(a.projeto)} — preencha todos os campos.")
        sys.exit(2)
    novos = {"voz_de": a.voz_de, "quem_autorizou": a.quem, "data": a.data, "texto": a.texto,
             "escopo": a.escopo, "como_foi_registrado": a.como, "registrado_por": a.por,
             "validade": a.validade}
    if any(v for v in novos.values()):
        f = caminho(a.projeto)
        atual = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else dict(MODELO)
        atual.update({k: v for k, v in novos.items() if v})
        atual["anotado_em"] = dt.date.today().isoformat()
        f.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(atual, ensure_ascii=False, indent=1) + "\n"
        f.write_text(texto, encoding="utf-8", newline="\n")
        print(f"gravado em {f}")
    ok, _c, problemas = conferir(a.projeto)
    for p in problemas:
        print(f"   ✗ {p}", file=sys.stderr)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
