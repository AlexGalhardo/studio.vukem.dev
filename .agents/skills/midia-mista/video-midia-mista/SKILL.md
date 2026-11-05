---
name: video-midia-mista
description: Cria vídeos curtos explicativos no estilo "mídia mista" (mixed media) — colagem com FOTOS REAIS recortadas sobre texturas reais (papel cinza, tecido escuro, mesa de madeira, mesa de desenho), fita amarela rasgada com letra à mão, marcador (laços, setas, X de marca-texto), título datilografado, mãos desfocadas de passagem, chuva de adesivos, objeto explodido em 3D, caleidoscópio, foto em cartão com legenda e lousa final. Busca fotos livres no Commons com crédito, recorta com o Vision, gera texturas, sintetiza trilha e efeitos e renderiza mp4 9:16 quadro a quadro (GSAP + Playwright + ffmpeg). Use sempre que pedirem vídeo de mídia mista, mixed media, colagem explicativa com fotos reais, explainer estilo documentário/Vox, reels educativos sobre um tema ("sobre os microchips", "sobre as locadoras"), motion "com fotos reais, texturas e flechas", ou mandarem uma referência nesse visual pedindo "faça igual" — mesmo sem dizer "mídia mista".
---

# Vídeo de mídia mista

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


Um explicativo de 7–8 s em que **objetos reais** chegam numa mesa em stop-motion, são **anotados à mão** e a câmera corre de cena em cena com transições sempre diferentes. Veja `assets/exemplo.mp4` antes de começar: é o padrão de qualidade. O código dele, `assets/projeto/videos/exemplo-microchips/index.html`, é o ponto de partida de todo vídeo novo.

O exemplo (microchips, 7,9 s) tem 7 cenas:
1. título datilografado;
2. padrão de válvulas com foto do ENIAC riscada com X;
3. chip caindo na palma da mão sobre madeira;
4. chuva de adesivos;
5. CPU explodida em 3D;
6. caleidoscópio para a foto da sala limpa em cartão;
7. lousa com "MICROCHIPS".

## Preparar o projeto (uma vez por pasta)

```bash
bash <caminho-da-skill>/scripts/setup.sh <pasta-do-projeto>
```

O script copia o motor (`render.mjs`, `dbg.mjs`, `lib/` com `midia.js`, `audio/synth.py`), instala gsap e playwright, cria o venv com numpy, scipy e pillow, compila o recorte do Vision (`tools/cutout`) e copia `tools/commons.py`, `tools/recortar.py` e `tools/texturas.py`.

- **Requisitos:** macOS 14+ (Vision e VideoToolbox), Node 18+, ffmpeg, python3, swiftc (`xcode-select --install`). Fora do Mac o render usa libx264, mas o recorte tem que ser feito à mão ou com rembg.
- **Onde rodar:** todos os comandos abaixo rodam da **raiz do projeto**.

## Fluxo

### 1. Roteiro em 7 cenas

Escreva uma linha por cena antes de qualquer imagem. O arco que funciona:

| Cena | Pergunta | Exemplo (microchips) | Exemplo (locadoras) |
|---|---|---|---|
| 1 título | a meia frase que prende | "Do tamanho de uma sala…" | "Sexta à noite, 1998…" |
| 2 padrão + X | o que era antes / o problema | válvulas, ENIAC 1946, riscado | fitas VHS, "rebobine antes de devolver" |
| 3 mesa | o objeto na mão, de perto | chip na palma | carteirinha da locadora, fita na mão |
| 4 adesivos | a quantidade, a explosão | chips, CPUs, wafers | capas de filme, fitas |
| 5 explodido | o que tem dentro | dissipador, die, substrato | a fita VHS aberta: carcaça, rolos, fita |
| 6 foto em cartão | onde acontece, gente real | sala limpa, "wafer de silício" | fachada/prateleiras de locadora |
| 7 lousa | a frase final | "MICROCHIPS" · "do ENIAC ao seu bolso" | "LOCADORAS" · "o streaming de antes" |

Textos curtos: fita até ~22 caracteres, título até ~26. Os fatos têm que ser verdadeiros. Na dúvida, prefira uma frase sem número a um número inventado.

### 2. Fotos, recortes e texturas

Siga `references/fotos.md`:
- busque no Commons e baixe com crédito;
- recorte com o Vision e **abra a prova**;
- gere versões leves para o padrão e os adesivos, e a mão desfocada;
- gere as texturas de papel, tecido, mesa e madeira.

Crie a pasta do vídeo copiando o exemplo:

```bash
cp -R videos/exemplo-microchips videos/<nn-nome>
```

Troque imagens, textos, posições e tempos. Leia `references/estilo.md` (materiais, cores, tipografia, composição) e `references/cenas.md` (a receita de cada cena com os tempos exatos) **antes** de mexer.

### 3. Preview e iteração

```bash
node render.mjs <nome> --preview=12                      # folha de 12 quadros → previews/<nome>.jpg
node render.mjs <nome> --at=0.5,1.7,2.8,3.9,4.9,6.3,7.8  # instantes escolhidos → previews/<nome>/NN.jpg
```

Olhe **cada quadro** e corrija:
- texto cortado na borda (fita, lousa, rótulo);
- tela preta entre adesivos (a cena de baixo precisa continuar visível);
- peça importante pequena demais;
- um detalhe circulado na foto que não está onde o laço está;
- quadro final incompleto.

Para inspecionar um instante: `node dbg.mjs <nome> 4.9 "K.$('#tg5').getBoundingClientRect().width"`.

### 4. Som e render final

```bash
audio/.venv/bin/python audio/synth.py <nome>
node render.mjs <nome>                      # out/<nome>.mp4, com o áudio junto
```

O `cues.json` é escrito a cada preview ou render: rode um preview antes do synth. Os cues de cada gesto estão em `references/audio.md`. Antes de entregar, extraia uma folha de contato do mp4 pronto (`ffmpeg -i out/<nome>.mp4 -vf "fps=6,scale=180:-1,tile=12x4" -frames:v 1 previews/final.jpg`) e confira a sequência inteira.

## Biblioteca `lib/midia.js` (objeto `M`)

| Função | Para quê |
|---|---|
| `M.vis(id, a, b, t)` | mostra a cena só na janela `[a, b)` |
| `M.slap(t, t0, k)` · `M.steps` · `M.pop` | chegada em stop-motion (4 quadros) · degraus · pop elástico |
| `M.marcador()` · `M.ink(path, u)` · `M.reink` | filtro de traço tremido · revelar um traço de 0 a 1 |
| `M.laco(cx, cy, rx, ry, giro, seed)` · `M.seta(pontos)` | laço feito à mão · seta com ponta (`{haste, ponta}`) |
| `M.rasgarTudo()` · `M.letras` · `M.digitar` | bordas rasgadas em `.tape`/`.tag` · letra a letra torta · texto digitado |
| `M.datilografia(el, texto, o)` | título com cursor e câmera seguindo (`medir`, `tick`, `cursorX`, `sons`) |
| `M.padrao(el, o)` | grade diagonal de recortes que brotam do centro |
| `M.adesivos(el, o)` · `M.somAdesivos` | chuva de adesivos que cobre e voa para fora |
| `M.explodido(el, camadas, o)` | objeto em camadas 3D que se separam |
| `M.caleidoscopio(el, url, pos)` · `M.mapaCapa` | transição espelhada · posição de um ponto da foto num cartão "cover" |
| `M.chicote(t, t0, t1)` · `M.filtroBlur` | chicote entre duas cenas (`u` e desfoque) |
| `M.acabamento({grao})` | vinheta, grão e tremor de projetor |

As transições estão detalhadas em `references/transicoes.md`.

## Regras do motor (o render pula para qualquer instante t)

- **Tudo é função do tempo.** Animação vai no `onTick(t => ...)` (ou na timeline `TL` do GSAP, pausada). Não use transição ou animação CSS, `setTimeout`, `requestAnimationFrame` nem `Math.random()`. Use `K.rng(seed)`. Se não for assim, o quadro renderizado não bate com o instante.
- **Medidas de texto** (`titulo.medir()`) vão no `window.SETUP`, que roda depois de as fontes carregarem.
- **Filtro SVG em traço reto** (linha horizontal) precisa de região em `userSpaceOnUse`. O `#mk` do `M.marcador()` já vem assim. Uma região relativa à caixa de um traço reto tem altura zero e some.
- **Ordem no HTML é a ordem na mesa:** textura → objetos → X de marca-texto → fitas → laços e setas → mãos desfocadas.
- **Fontes locais** em `lib/fonts.css`: Playfair Display, DM Serif Display, Kalam, Permanent Marker, Dela Gothic One, Inter Tight e Caveat.
- **30 fps** é o padrão do estilo, com cara de filme e render rápido. Todos os vídeos são **9:16 (1080×1920)**.

## Arquivos

- `scripts/setup.sh`: cria ou completa um projeto.
- `scripts/commons.py`: busca e baixa fotos do Commons, com créditos.
- `scripts/recortar.py` + `scripts/cutout.swift`: recorte com o Vision.
- `scripts/texturas.py`: papel, tecido, mesa e madeira; versões reduzidas e desfocadas.
- `assets/projeto/`: o motor, `lib/midia.js` e o exemplo `videos/exemplo-microchips/` (com `img/creditos.json`).
- `assets/exemplo.mp4`: o resultado de referência.
- `references/estilo.md`, `cenas.md`, `transicoes.md`, `fotos.md`, `audio.md`.
