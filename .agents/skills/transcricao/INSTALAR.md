# Como instalar (instruções para o Claude) — Mac, Linux e Windows

Este zip traz uma skill da crIAbr e, quando ela precisa, as skills de que depende. O mesmo zip serve para os três
sistemas; só muda o comando do Python.

## Windows

**Não existe `python3` no Windows** — digitar isso abre a Microsoft Store e não roda nada. Use **`py -3`**.

1. Descompacte o zip numa pasta (botão direito → Extrair tudo). Não rode de dentro do zip.
2. Dois cliques em **`instalar.bat`**, na raiz da pasta — ele acha o Python sozinho e faz a conferência.
   Pelo terminal: `py -3 <pasta>\<skill principal>\scripts\preparar.py`.
3. Com o ok do usuário, rode de novo com `--instalar` (ou `instalar.bat --instalar`). Ele copia as skills para
   `%USERPROFILE%\.claude\skills\`, instala os programas que faltam pelo **winget** e as bibliotecas Python num
   ambiente próprio (`%USERPROFILE%\.criabr\venv`).
4. Sem Python: https://www.python.org/downloads/, marcando *"Add python.exe to PATH"*. Sem winget: vem no
   "Instalador de Aplicativo" da Microsoft Store.
5. A transcrição no Windows usa **faster-whisper** (o `whisper-cli` só tem pacote pronto no Mac); o modelo é
   baixado sozinho no primeiro uso.

## Mac e Linux

1. Descompacte o zip numa pasta temporária.
2. Rode `python3 <pasta>/<skill principal>/scripts/preparar.py` e mostre ao usuário o que faltar.
3. Com o ok dele, rode o mesmo comando com `--instalar`. Ele copia as skills para `~/.claude/skills/`, instala os
   programas que faltam (ffmpeg, Node, Whisper) pelo Homebrew ou pelo apt e as bibliotecas Python em
   `~/.criabr/venv`.
4. Se faltar o Homebrew no Mac: https://brew.sh. Depois, rode de novo.

## Nos três

- Skill que já existe na máquina é mantida; `--atualizar` substitui e guarda a antiga em `~/.criabr/antigas/`.
- Código de saída 0 = pronto · 3 = falta algo (a lista final diz o quê) · 1 = erro.
- Use os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).
