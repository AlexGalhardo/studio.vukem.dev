#!/usr/bin/env python3
"""voz_ia.py: gera o trecho novo com a voz do apresentador pela API do ElevenLabs. **API PAGA.**

Cada chamada daqui gasta créditos da SUA conta. O script nunca roda sozinho: ele exige o consentimento
registrado (código 2 sem ele), mostra o que vai fazer e só segue com `--confirmar`.

Três caminhos:
  --clonar amostra.wav --nome "Voz do apresentador"   clone instantâneo a partir de 1 a 3 minutos de fala
                                                      limpa da própria pessoa (devolve o id da voz)
  --texto "a frase certa" --voz <id>                  texto → fala
  --fala trecho_regravado.wav --voz <id>              fala → fala (mantém a sua interpretação e o ritmo;
                                                      é o caminho que dá mais chance de a boca bater)
  --vozes                                             lista as vozes da conta

A chave vem de ELEVENLABS_API_KEY no ambiente ou de uma linha `ELEVENLABS_API_KEY=...` em
`<casa da crIAbr>/chaves.env` (~/.criabr/chaves.env). Sem chave, o script explica e sai com código 2 —
nada é cobrado. A saída é convertida para WAV 48 kHz, pronta para o dublar.py.

Se você não tem (ou não quer) a API, pule este script: grave você mesmo o trecho, ou gere o WAV em outra
ferramenta, e passe o arquivo direto para o dublar.py. A skill inteira funciona sem o ElevenLabs.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consentimento as consent  # noqa: E402
from audio import SR, casa, para_wav  # noqa: E402

BASE = "https://api.elevenlabs.io/v1"
MODELO_TTS = "eleven_multilingual_v2"
MODELO_STS = "eleven_multilingual_sts_v2"


def chave():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k.strip()
    f = casa() / "chaves.env"
    if f.is_file():
        for linha in f.read_text(encoding="utf-8").splitlines():
            if linha.strip().startswith("ELEVENLABS_API_KEY"):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    print("Não achei a chave do ElevenLabs.\n"
          f"Ponha ELEVENLABS_API_KEY=... em {f} ou no ambiente — a chave é sua e nunca sai daqui.\n"
          "Sem ela, grave o trecho você mesmo (ou gere o WAV em outra ferramenta) e passe direto ao dublar.py.",
          file=sys.stderr)
    sys.exit(2)


def _pedir(url, dados=None, cabecalhos=None, metodo=None):
    req = urllib.request.Request(url, data=dados, method=metodo or ("POST" if dados else "GET"))
    for k, v in {"xi-api-key": chave(), **(cabecalhos or {})}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read(), r.headers.get_content_type()
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "replace")[:600]
        raise SystemExit(f"ElevenLabs recusou ({e.code}): {corpo}")
    except urllib.error.URLError as e:
        raise SystemExit(f"não consegui falar com a API: {e.reason}")


def _multipart(campos, arquivos):
    """Monta um corpo multipart/form-data sem dependência externa."""
    limite = f"----criabr{uuid.uuid4().hex}"
    partes = []
    for k, v in campos:
        partes.append(f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, caminho in arquivos:
        p = Path(caminho)
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        partes.append(f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"; "
                      f"filename=\"{p.name}\"\r\nContent-Type: {tipo}\r\n\r\n".encode())
        partes.append(p.read_bytes())
        partes.append(b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def gravar_saida(bruto, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cru = destino.with_name(f"_{destino.stem}_api.mp3")
    cru.write_bytes(bruto)
    para_wav(cru, destino)
    cru.unlink(missing_ok=True)
    print(f"{destino}: WAV {SR} Hz pronto para o dublar.py")
    return destino


def main():
    ap = argparse.ArgumentParser(description="Voz do apresentador pelo ElevenLabs (API PAGA).")
    ap.add_argument("--projeto", default=".")
    ap.add_argument("--texto", help="texto → fala")
    ap.add_argument("--fala", help="WAV de referência para fala → fala")
    ap.add_argument("--clonar", help="WAV de 1 a 3 min para o clone instantâneo")
    ap.add_argument("--nome", help="nome da voz, com --clonar")
    ap.add_argument("--voz", help="id da voz (--vozes lista)")
    ap.add_argument("--vozes", action="store_true", help="lista as vozes da conta e sai")
    ap.add_argument("--saida", default="som/dublagem/trecho.wav")
    ap.add_argument("--estabilidade", type=float, default=0.45)
    ap.add_argument("--semelhanca", type=float, default=0.85)
    ap.add_argument("--confirmar", action="store_true", help="obrigatório: confirma o gasto de créditos")
    a = ap.parse_args()

    if a.vozes:
        corpo, _ = _pedir(f"{BASE}/voices")
        for v in json.loads(corpo).get("voices", []):
            print(f"{v.get('voice_id')}  {v.get('name')}  ({v.get('category')})")
        return

    c = consent.exigir(a.projeto)
    acao = ("clonar a voz" if a.clonar else "gerar fala a partir de texto" if a.texto else
            "converter a sua gravação na voz clonada" if a.fala else None)
    if not acao:
        raise SystemExit("escolha --clonar, --texto ou --fala (ou --vozes).")
    print(f"Vai {acao} de {c['voz_de']}, autorizada por {c['quem_autorizou']} em {c['data']} ({c['escopo']}).")
    print("Isto é uma API PAGA e consome créditos da sua conta.")
    if not a.confirmar:
        print("Nada foi chamado. Repita o comando com --confirmar.", file=sys.stderr)
        sys.exit(2)

    if a.clonar:
        if not a.nome:
            raise SystemExit("--clonar precisa de --nome.")
        corpo, tipo = _multipart([("name", a.nome),
                                  ("description", f"Consentimento de {c['quem_autorizou']} em {c['data']}")],
                                 [("files", a.clonar)])
        resp, _ = _pedir(f"{BASE}/voices/add", corpo, {"Content-Type": tipo})
        vid = json.loads(resp).get("voice_id")
        print(f"voz criada: {vid}\nUse --voz {vid} nas próximas chamadas.")
        return

    if not a.voz:
        raise SystemExit("--texto e --fala precisam de --voz <id> (veja --vozes).")
    ajustes = {"stability": a.estabilidade, "similarity_boost": a.semelhanca}
    if a.texto:
        dados = json.dumps({"text": a.texto, "model_id": MODELO_TTS,
                            "voice_settings": ajustes}).encode("utf-8")
        bruto, _ = _pedir(f"{BASE}/text-to-speech/{a.voz}", dados, {"Content-Type": "application/json"})
    else:
        corpo, tipo = _multipart([("model_id", MODELO_STS), ("voice_settings", json.dumps(ajustes))],
                                 [("audio", a.fala)])
        bruto, _ = _pedir(f"{BASE}/speech-to-speech/{a.voz}", corpo, {"Content-Type": tipo})
    gravar_saida(bruto, a.saida)
    print("Agora emende com dublar.py --tipo " + ("texto" if a.texto else "fala"))


if __name__ == "__main__":
    main()
