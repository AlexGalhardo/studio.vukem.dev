---
name: video-dublagem
description: >
  Troca só o trecho errado da fala por outra gravação, com a emenda casada: nível, timbre (EQ de 1/3 de
  oitava limitado a ±6 dB), ruído de sala e duração do novo trecho são puxados para os do entorno, e a
  junção é feita em cruzamento por zero com 25 ms de cruzamento. O relatório mede o salto na emenda para
  provar que não ficou clique, mede o LUFS do trecho contra o de antes e depois, e avisa quando a boca
  não vai bater e o trecho precisa ser coberto. O áudio novo pode ser gravado por você, feito em
  qualquer ferramenta, ou gerado com a voz do apresentador pelo ElevenLabs (API paga, opcional). SÓ RODA
  COM CONSENTIMENTO REGISTRADO em som/dublagem/consentimento.json; sem ele, código 2. Use quando o
  usuário disser "ele falou o número errado", "troca só essa frase", "conserta essa palavra sem regravar
  tudo", "dubla esse trecho", "clona a voz dele". Loudness do vídeo inteiro é video-compositor.
---

# video-dublagem

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

Quando uma frase saiu errada e regravar o vídeo inteiro não é opção: um número trocado, um nome errado,
uma palavra engolida. A promessa é pequena de propósito — **o resto do áudio não é tocado**.

## O portão: consentimento

Gerar ou emendar a voz de uma pessoa só é aceitável com a autorização dela, registrada por escrito. Sem
`som/dublagem/consentimento.json` preenchido, **nada roda**: todos os scripts saem com **código 2**.

```bash
python3 scripts/consentimento.py --projeto . --modelo     # grava o modelo para preencher
python3 scripts/consentimento.py --projeto .              # confere (0 = pode rodar, 2 = falta)
```

Campos obrigatórios: `voz_de`, `quem_autorizou`, `data`, `texto` (as palavras de quem autorizou, com no
mínimo 25 caracteres), `escopo`, `como_foi_registrado` (e-mail, contrato, vídeo gravado — e onde está
guardado) e `registrado_por`. `validade` é opcional e, quando vence, o portão fecha de novo. **Não
preencha isso "para testar": pergunte ao usuário e escreva o que ele responder.**

## 1. De onde vem o trecho novo

Três caminhos, nesta ordem de preferência:

1. **O apresentador regrava a frase** no mesmo microfone e na mesma sala. É o melhor resultado e não
   custa nada.
2. **Um WAV feito em qualquer outra ferramenta** — passe o arquivo direto ao `dublar.py`.
3. **ElevenLabs** (`scripts/voz_ia.py`), **API paga e opcional**: clone instantâneo, texto→fala ou
   fala→fala. A chave é sua (`ELEVENLABS_API_KEY` no ambiente ou em `~/.criabr/chaves.env`), nunca sai
   da máquina, e nada é chamado sem `--confirmar`. Sem chave, o script explica e sai com código 2 — nada
   é cobrado.

```bash
python3 scripts/voz_ia.py --vozes
python3 scripts/voz_ia.py --clonar som/dublagem/amostra.wav --nome "Voz do apresentador" --confirmar
python3 scripts/voz_ia.py --fala som/dublagem/regravado.wav --voz <id> --confirmar
```

**Fala→fala dá muito mais chance de a boca bater** do que texto→fala: a sua interpretação e o seu ritmo
são preservados.

## 2. A emenda

```bash
python3 scripts/dublar.py som/voz.wav --t0 12.30 --t1 15.80 \
    --novo som/dublagem/trecho.wav --saida som/dublagem/voz_dublada.wav --tipo fala
```

O trecho novo é ajustado ao que está em volta (±4 s) em quatro frentes, nesta ordem:

| frente | o que faz |
|---|---|
| timbre | EQ de 1/3 de oitava: tira o nível global, suaviza em 3 bandas e só então limita a ±6 dB |
| nível | o RMS de fala do novo vai para o RMS de fala da vizinhança |
| sala | o chão de ruído do original entra por baixo, para o silêncio entre as palavras não ficar surdo |
| duração | `atempo` de no máximo ±8%; além disso a voz fica artificial |

A junção é feita no **cruzamento por zero** mais próximo dos dois lados, com 25 ms de cruzamento em
seno² e 3 ms de fade nas pontas do novo.

`--tipo texto` (padrão) é texto→fala; `--tipo fala` é fala→fala. `--duracao-natural` desliga o atempo e
empurra o resto da linha do tempo.

## 3. Leia o relatório antes de aprovar

`som/dublagem/voz_dublada.json` responde quatro perguntas:

- **Ficou clique?** `emendas[].sem_clique`: o maior salto entre amostras vizinhas nos ±10 ms da junção,
  contra o p99,9 dos saltos normais em volta. Se vier `false`, o script sai com **código 1**.
- **O nível casou?** `loudness.diferenca_para_o_entorno_lufs`. Acima de ±1 LUFS, dá para ouvir.
- **Andou a linha do tempo?** `deslocamento_depois_do_trecho_s`. Com `--manter-duracao` (padrão) tem de
  ser **0,000 s** — se não for, tudo depois do trecho sai do lugar no vídeo.
- **A boca vai bater?** `boca.bate` e `boca.motivos`. Texto→fala **nunca** bate: as palavras mudaram.

## Regras e armadilhas

- **Boca que não bate é problema de imagem, não de som.** Quando o relatório disser que não bate, cubra
  o trecho inteiro — do primeiro ao último quadro — com b-roll, animação, cartela ou corte de retomada.
- **O corte não é no segundo que você pediu**, é no cruzamento por zero mais próximo (até ±12 ms). O
  relatório mostra onde caiu em `trecho.corte_em_zero_s`.
- **Pegue t0 e t1 no `transcricao/palavras.json`**, não no olhômetro: comece no silêncio antes da
  primeira palavra errada e termine no silêncio depois da última.
- **O EQ de timbre não troca de voz.** ±6 dB por banda corrige o mesmo microfone na mesma sala; se o
  trecho novo veio de outro ambiente, a emenda vai aparecer — regrave.
- **Esticar passa de ±8% e a voz fica artificial.** Além disso a skill mantém a duração natural, empurra
  a linha do tempo e **avisa** no relatório.
- **A API do ElevenLabs é paga.** Nenhum script a chama sem `--confirmar`, e a skill inteira funciona
  sem ela.
- O ffmpeg passa pela trava do kit de direção de arte quando ela existe (uma tarefa pesada por vez).

## Saídas

| arquivo | o que é |
|---|---|
| `som/dublagem/consentimento.json` | o registro da autorização — o portão da skill |
| `som/dublagem/trecho.wav` | o áudio novo (seu, de outra ferramenta ou do `voz_ia.py`) |
| `som/dublagem/voz_dublada.wav` | a fala inteira com o trecho trocado, 48 kHz estéreo 16-bit |
| `som/dublagem/voz_dublada.json` | emendas, nível, LUFS, atempo, deslocamento e o veredicto da boca |
