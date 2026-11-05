---
name: video-floresta-luminosa
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "floresta luminosa" — diorama noturno low-poly em 3D "desenhado a lápis de cor sobre papel preto" (cada face facetada é hachurada numa direção própria), madeira e terra em marrons e ocre, céu marinho com estrelas e a ÁGUA como única luz fria: cachoeira, rio facetado e um corte de aquário com peixes. Câmera travada, micro-movimentos em laço a 10 qps e texto curto a lápis. Feito em three.js (lib/floresta.js) com Playwright + ffmpeg e som sintetizado. Use quando pedirem floresta luminosa, cena noturna mágica ou onírica, 3D com textura de lápis de cor, hachura, scratchboard, bicho na mata à noite, animal bebendo água, rio que brilha, vídeo de fauna brasileira (onça, anta, capivara, lobo-guará) com clima de livro ilustrado, reels de natureza contemplativo, ou mandarem referência nesse visual pedindo "nesse estilo". Difere da irmã video-diorama-isometrico, que é bloco de terreno diurno com traço de HQ e relevo que se transforma.
---

# Vídeo em floresta luminosa

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

As 3 marcas do estilo: **(1)** formas 3D low-poly facetadas em que cada face é hachurada à mão, numa direção própria, com lápis de cor sobre papel preto; **(2)** noite quente (madeira, terra e bicho em marrons e ocre, céu marinho com estrelas) cortada por água fria que brilha — cachoeira, rio facetado e o corte de aquário com peixes; **(3)** diorama parado em laço lento a 10 qps: a câmera nunca mexe, só micro-movimentos cíclicos. Juntas, elas dão a sensação de um livro ilustrado que respira: o traço manual tira o "cara de 3D", a água azul guia o olho no escuro e o laço a 10 qps parece stop-motion.

Veja `assets/exemplo.mp4` (8 s, "onça-pintada — o maior felino das Américas"): olhos acendem na moita, a onça sai da sombra, caminha até a beira, bebe (anéis quadrados na água) e encara a câmera. O código está em `assets/projeto/videos/exemplo-onca/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py exemplo --preview=6     # confere → previews/exemplo-onca.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy e WebGL2 no Chromium do
Playwright (no Mac usa Metal). Render de 8 s leva ~40 s. O `renderizar.py` passa o render pela trava de memória
quando ela existe. Funciona igual em Mac, Linux e Windows — não há script `.sh` no caminho obrigatório.

## Fluxo

1. **Roteiro em tempos.** Escreva a tabela `T` (ver `references/movimento.md`): 1 plano só, câmera parada, um "evento" a cada ~1,5–2 s (olhos acendem → bicho entra → age → reação), com o laço ambiente rodando por baixo o tempo todo. 6–8 s.
2. **Cenário.** Monte o diorama com a lib (`references/receitas.md`): `ceu` + `estrelas`, `paredao` com entalhe e `cachoeira`, `terreno` com `relevoRio` (vala + poço da frente), `rio`, `vidroAgua`, `arvore` emoldurando as laterais, `roseta`/`capim`/`pedra` nas margens, `peixe` no corte de aquário.
3. **Bicho.** `FL.onca` é o modelo de rig (grupos com corpo, pescoço, cabeça, 4 patas de 2 segmentos, cauda em corrente). Para outro animal, copie a função e troque seções do `loft`, cor e `manchas`.
4. **Montar.** `cp -R videos/exemplo-onca videos/<nn-nome>` e troque `T`, cenário, caminho do bicho (`P0 → P1`), texto e cues.
5. **Preview.** `python3 tools/renderizar.py <nn> --at=0.6,2.5,4,5.5,7.7` → `previews/<nn-nome>.jpg`. Confira: o bicho ocupa ~35–45 % da largura? a água é a coisa mais clara da tela? o céu com estrelas aparece no topo, atrás do título? nada de "tijolinho" no traço?
6. **Som e render.** `python3 tools/renderizar.py <nn> --at=1` (grava `cues.json`) → `<PYTHON> audio/synth.py <nn>` → `python3 tools/renderizar.py <nn>` → `out/<nn-nome>.mp4`. Ver `references/audio.md`.
7. **Conferir.** `ffprobe` (1080×1920, duração, faixa de áudio) e uma folha: `ffmpeg -i out/<v>.mp4 -vf "fps=8,scale=135:-1,tile=8x8" -frames:v 1 folha.jpg`.

Para recriar o estilo a partir de outra referência, compare lado a lado: `<PYTHON> tools/analisar.py comparar <ref.mp4> out/<v>.mp4 previews/comparar.jpg`.

## Regras do motor

- **Tudo é função de `t`, quantizado a 10 qps.** O palco passa ao `S.update(tq, t)` o tempo já em degraus de 0,1 s (`FL.degrau`). Use `tq` para tudo (bicho, peixes, texto) — é isso que dá o ar de stop-motion da referência. Nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()`; use `FL.rng(semente)`.
- **Página = módulo.** Carregue `boot.js` e depois `<script type="module">import * as FL from '../../lib/floresta.js'</script>`. Defina `window.SETUP` de forma síncrona no módulo; crie o texto (`FL.textoLapis`) e os cues dentro dele (as fontes já carregaram).
- **Câmera travada.** Não anime a câmera. Enquadre com `cam`/`alvo` no `FL.palco` e mexa o cenário.
- **Não escale malhas; escale a geometria.** O traço é calculado nas coordenadas do objeto (por isso não "nada" quando o bicho anda). Uma malha com `scale` ≠ 1 teria traço esticado. Os construtores já recebem tamanhos (`escala`, `r`, `comp`…).
- **Chame `FL.calibrar(S)` depois de montar a cena.** Ele fixa, para cada malha, a profundidade usada para o traço ter ~`px` pixels de espaçamento. Objetos que se movem em profundidade (o bicho) recebem `prof` fixa no construtor.
- **Cores em hex sRGB direto.** A lib desliga gestão de cor e tone mapping. Só a água e os olhos passam do limiar do bloom (~0,58): se algo mais "brilhar", escureça a cor dele.
- **Fonte:** só Fraunces (OFL) vem na skill. Outra fonte: ponha o woff2 em `lib/fonts/` e o `@font-face` em `lib/fonts.css`.

## Armadilhas conhecidas

- **Testa cobrindo os olhos:** o `loft` inclina cada anel conforme o caminho sobe/desce. Em cabeças e corpos use `dir: [1, 0, 0]` (anéis retos); senão o rosto "debruça" e esconde os olhos.
- **Traço de "tijolinho":** fileiras cheias demais e traços largos parecem lascas de madeira. Mantenha `dens` ≤ 1, `larg` ≤ 1 e `px` 4–5,5; o material já intercala duas fileiras defasadas.
- **Bicho pequeno e na borda:** em 9:16 a tela é estreita. Aproxime a câmera (z ~11) e traga o bicho para o terço central; ele deve ocupar ~40 % da largura.
- **Céu sumindo:** câmera alta olhando para baixo esconde o céu atrás do paredão. Baixe `topo` do paredão e da serra antes de baixar a câmera.
- **Fundo d'água claro demais:** o corte de aquário é ESCURO na referência; quem brilha são os olhos dos peixes. Use `fundo.cor` escuro no terreno e `vidroAgua` com `alfa` ~0,1.
- **Giro de cabeça com sinal trocado:** `cabecaY` positivo vira o focinho para o lado −z local. Confira num preview que o bicho olha para a câmera.

## Arquivos

- `assets/projeto/lib/floresta.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/audio/synth.py` — trilha `noturno` e os efeitos `passo`, `folhas`, `lapis`, `lambida`, `brilho`.
- `references/estilo.md` (marcas, paleta, traço, composição) · `movimento.md` (tempos, laços, coreografia) · `receitas.md` (API e receitas) · `audio.md` (trilha e cues).
- `scripts/projeto.py` (monta a pasta de trabalho) · `scripts/renderizar.py` (chama o motor com o Node certo e pela trava) · `scripts/analisar.py` (ler/comparar referências) · `scripts/comum.py` · `scripts/preparar.py`.
