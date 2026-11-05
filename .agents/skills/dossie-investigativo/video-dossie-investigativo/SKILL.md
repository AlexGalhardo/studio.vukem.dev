---
name: video-dossie-investigativo
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "dossiê investigativo": arquivo de investigação em preto e branco, papel de xerox sujo (grão, bandas de scanner, vinco), tarjas de censura sobre o texto e sobre os olhos das fotos, ficha 3x4 desbotada, impressões digitais, texto datilografado letra a letra, anotações à mão, carimbo de tinta falhada e painel de fotos presas por alfinetes e ligadas por fios, percorrido por uma câmera de mesa. Tudo desenhado por código, em páginas HTML animadas quadro a quadro (GSAP + Playwright + ffmpeg), com retratos gerados por código ou a foto do usuário tratada em xerox, e som sintetizado. Use quando o usuário pedir vídeo "estilo dossiê", "arquivo secreto", "ficha de investigação", "documento confidencial", "painel investigativo", "mural de detetive com fios", "tarja preta", "censurado", "true crime", "caso arquivado", linha do tempo de um caso, reels de jornalismo investigativo, motion "de xerox" em P&B, ou mandar uma referência nesse visual pedindo algo "nessa pegada".

---

# Vídeo em dossiê investigativo

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## As 3 marcas do estilo

1. **Papel de xerox em preto e branco, sujo.** Folha cinza-clara com grão, bandas horizontais de scanner, riscos de toner, vinco e a sombra irregular da borda da fotocópia. Nada é liso nem limpo, e tudo treme um pouco, em degraus de 12 quadros por segundo, como registro de stop-motion. Cor: preto, branco e cinzas; no máximo **um** acento pequeno (o exemplo usa laranja só em três fios).
2. **O que está escondido.** Tarjas pretas de borda irregular riscam o texto da esquerda para a direita (marcador) e batem de uma vez sobre os olhos da foto (fita). A foto é uma 3x4 em xerox de alto contraste, com cópias desbotadas ao lado; a impressão digital entra como carimbo. A tensão do vídeo vem do que não se pode ler.
3. **O painel de fios.** Fotos, cartões e etiquetas de nome presos por alfinetes e ligados por fios finos que se desenham no tempo, com a câmera de mesa seguindo o fio e abrindo no fim para mostrar o mural inteiro sobre um título em grotesca pesada. A tipografia é de arquivo: grotesca pesada nos títulos, mono de máquina de escrever na ficha, serifada nas citações.

Veja `assets/exemplo.mp4` (11 s, caso fictício "Arquivo RL-0417 — Quem apagou Vila Aurora?"): página 1 é a ficha do sujeito; corte seco; página 2 é o painel. O código está em `assets/projeto/videos/exemplo-arquivo-0417/index.html` e é o ponto de partida de todo vídeo novo.

## Regras de conteúdo (valem sempre)

O visual de dossiê dá **peso de prova** ao que mostra. Por isso:

- **Fato, data, nome, número e acusação vêm do roteiro do usuário**, de preferência com a fonte. O Claude não inventa dado, depoimento nem documento que pareça oficial. Faltou informação: pergunte, ou deixe o campo tarjado ou vazio (tarja não é fato).
- **Caso real leva a fonte no rodapé** (`DS.rodape(stage, 'Fonte: …')`) e separa o comprovado da suspeita com as palavras do roteiro ("investigado", "segundo a denúncia"). **Ficção leva o aviso** ("CASO FICTÍCIO · NOMES E FATOS INVENTADOS").
- **Pessoa real só com foto fornecida pelo usuário, ou de domínio público/licença livre** (crédito no rodapé). Sem foto, use o retrato gerado por código (`DS.retrato`). Nunca use as fotos de uma referência.
- **Nenhum selo, brasão, logotipo ou nome de órgão real** (polícia, ministério público, agência, governo). Carimbos e cabeçalhos são genéricos e fictícios ("ARQUIVO INTERNO", "SETOR 9", "CONFIDENCIAL").
- O garrancho e a assinatura são textura: não dizem nada e não imitam a letra de ninguém.

## Preparar o projeto (uma vez por pasta)

```bash
python3 <pasta desta skill>/scripts/projeto.py "<pasta-do-projeto>"
```

Ele copia o projeto-modelo, cria as pastas e imprime duas linhas: `NODE=` (o Node ≥ 20 do render) e `PYTHON=`
(o Python com numpy, scipy e Pillow). Guarde as duas — abaixo, `$N` é o NODE e `$P` é o PYTHON:

```bash
cd "<pasta-do-projeto>"
N=<o que saiu em NODE=>   # no Windows: $N = "<o que saiu em NODE=>"
P=<o que saiu em PYTHON=>
```

Funciona igual em macOS, Linux e Windows (o `projeto.py` só usa a biblioteca padrão; não há mais `setup.sh`
nem `node.sh`). Requisitos: Node ≥ 20 (o PATH pode ter um velho — por isso a linha `NODE=`), ffmpeg e o Python
do `preparar.py`. Código 3 do `projeto.py` = falta alguma coisa, e ele lista o quê.

## Fluxo

1. **Roteiro e peças.** Do roteiro do usuário, tire: o código do arquivo, 4 a 6 campos de ficha (quais nascem tarjados), 2 a 4 pessoas ou lugares do painel, os fios (quem se liga a quem), 1 ou 2 carimbos e o título final (≤ 2 linhas de ~12 caracteres). Leia antes as regras de conteúdo acima.
2. **Fotos.** Com foto do usuário: `$P tools/dossie.py xerox foto.jpg videos/<nn>/img/x.png --largura 500` e `DS.foto(pai, {src: 'img/x.png', …})`. Sem foto: `DS.foto(pai, {seed, retrato: {cabelo, roupa}})` desenha uma silhueta em xerox.
3. **Composição** (ver `references/estilo.md`): página 1 é uma folha 1080×1920 (cabeçalho e código no alto, foto com cópias no meio, ficha, digitais e carimbo embaixo); página 2 é um mural 2000×3556 que a câmera percorre.
4. **Montar:** `cp -R videos/exemplo-arquivo-0417 videos/<nn-nome>` e troque textos, posições e tempos mantendo a tabela `T` e as chaves da câmera (`references/movimento.md`; API em `references/receitas.md`).
5. **Prévia:** `$N render.mjs <nn> --at=0.3,2.6,4.7,5.8,8.1,10.5` (ou `--preview=12`) → `previews/<nn-nome>.jpg`. Olhe e corrija antes de renderizar o vídeo.
6. **Som e render:** `$N render.mjs <nn> --at=1` (grava `cues.json`), `$P audio/synth.py <nn>`, `$N render.mjs <nn>` → `out/<nn-nome>.mp4` (ver `references/audio.md`). Um render por vez.
7. **Conferir:** `ffprobe` (1080×1920, duração, uma faixa de áudio), `$P tools/dossie.py folha out/<nn-nome>.mp4 previews/folha.jpg --n 9 [--refs …]`, texto legível no celular, quadro quase todo preto e branco, aviso ou fonte no rodapé.

## Regras do motor

- Tudo é função do tempo (`onTick(t => …)`); nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` (use `K.rng`).
- **Monte todas as peças dentro de `window.SETUP`**: várias medem texto ou desenham letras em canvas e precisam das fontes carregadas. Fora dele, tarjas e carimbos saem com a largura errada.
- Fontes: só as de `lib/fonts.css` (Inter Tight nos títulos, Courier Prime na ficha, Lora nas citações). Outra fonte: baixe o woff2 OFL para `lib/fonts/` e declare o `@font-face`.
- O texto entre `[[ ]]` em `DS.texto` e `DS.cartao`, e o valor de um campo com `tarja: true`, **nunca são desenhados**: ficam transparentes sob a tarja. Mesmo assim, não escreva ali um dado sensível de verdade.
- Coordenadas são do **mundo** (a folha ou o mural), não da tela; quem decide o que aparece é `DS.camera`.
- 16:9: troque `VIDEO={w:1920,h:1080,…}` e recomponha (mural deitado, por exemplo 3200×1800); a biblioteca lê `VIDEO.w/h` e nada mais muda (`references/estilo.md`, "16:9").

## Armadilhas do estilo

- **Quadro vazio depois do corte.** A página nova tem de nascer com pelo menos três coisas na tela (foto, etiqueta, cartão) no primeiro meio segundo; comece a câmera mais fechada e abra depois.
- **Texto cortado pela câmera.** Com zoom, a tela mostra `1080/z` px do mundo: deixe 40 px de margem entre o texto e a borda do que a câmera vê.
- **Limpo demais.** Se parecer infográfico, falta sujeira: `verso: true` e `furos: true` no papel, `DS.grao`, mais `manchas`, rotação de 1 a 2 graus nos cartões e fotos.
- **Cor demais.** Um acento só, em pouca área (fios, uma etiqueta). Se dois elementos coloridos aparecem juntos, tire um.
- **Retrato procedural sem tarja.** O rosto gerado por código é uma mancha de xerox; cubra os olhos (`F.olhos`) em até 0,6 s ou ele parece boneco.
- **Tudo ao mesmo tempo.** Carimbo, digital e fita sacodem a câmera; deixe pelo menos 0,2 s entre duas batidas.

## Arquivos

- `references/variantes.md` — variantes salvas do estilo (hoje: **iceberg-pt**, preto, branco e vermelho para vídeo longo 16:9). Se o pedido citar uma variante pelo nome, leia a seção dela antes de montar.
- `assets/projeto/lib/dossie.js` — biblioteca do estilo, global `DS` (API em `references/receitas.md`).
- `scripts/dossie.py` — `xerox` (foto do usuário → fotocópia P&B) e `folha` (folha de contato, com as referências ao lado).
- `references/estilo.md` (paleta, tipografia, materiais, composição) · `movimento.md` (tempos, entradas e câmera) · `receitas.md` (API e passo a passo) · `audio.md` (trilha e efeitos).
- `scripts/projeto.py` (cria/completa a pasta do projeto e diz qual Node e qual Python usar) · `analisar.py` (para ler um vídeo de referência novo e comparar lado a lado).
