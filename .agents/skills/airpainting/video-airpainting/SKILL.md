---
name: video-airpainting
description: Cria motions curtos (5–8 s, 9:16) no estilo "airpainting", com papel claro, objetos grandes chapados com gradiente pontilhado de risografia (grain gradient), cópias desfocadas ao fundo e uma mão de cartoon com contorno de giz que toca o objeto e "pinta no ar" uma cor nova a partir da ponta do dedo. Um selo violeta com letra laranja troca de texto a cada passo, e o vídeo fecha num infográfico de objetos empilhados por cor, com números contando e a marca. Desenha tudo em SVG com peças prontas (pasta, cartão, celular, caixa, pizza, mão, selo, fundo, pilhas) e renderiza mp4 com trilha e efeitos sintetizados. Use sempre que o usuário pedir airpainting, gradiente granulado ou pontilhado, risografia, grain gradient, mão apontando ou tocando, selo ou sticker que troca de texto, infográfico de pastas ou objetos, motion de produto ou app "organize / pinte / escolha" ou explicação em passos com objetos, e quando mandar uma referência nesse visual pedindo algo parecido, mesmo sem dizer "airpainting".
---

# Motion no estilo airpainting

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


O estilo junta cinco ingredientes:

- **papel claro e quente** quase vazio;
- **objetos chapados com gradiente pontilhado** de risografia (a assinatura);
- **profundidade de campo**, com cópias pequenas e desfocadas ao fundo;
- **mão de cartoon** com contorno de giz que toca e "pinta" o objeto;
- **selo** violeta com letra laranja que conta os passos.

Faltando um, vira flat design genérico.

Veja `assets/exemplo.mp4` (5 s) para calibrar o olhar. O código dele está em `assets/projeto/videos/exemplo-airpainting/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar o projeto (uma vez por pasta)

```bash
bash <caminho-da-skill>/scripts/setup.sh <pasta-do-projeto>
```

O script copia o motor (`render.mjs`, `dbg.mjs`, `lib/` com `riso.js`, `audio/synth.py`), instala gsap e playwright, cria o venv Python com numpy, scipy e pillow, e copia `tools/referencia.py`.

- **Requisitos:** Node 18+, ffmpeg e python3. No macOS o encode usa VideoToolbox; nos outros sistemas, libx264.
- **Onde rodar:** todos os comandos abaixo rodam **da raiz do projeto**.
- **Projeto existente:** se a pasta já tem o motor (de uma skill irmã), o script só acrescenta `lib/riso.js` e o exemplo.

## Fluxo

### 1. Se houver referência, leia antes

```bash
audio/.venv/bin/python tools/referencia.py <video.mp4> previews/ref --em 0.6,1.4,2.2
```

Isso gera folhas de contato a 8 qps e quadros-chave, e lista as cores dominantes. **Abra as folhas** e anote:

- o objeto principal e como ele entra;
- quantos toques há, e o que muda em cada um;
- os textos do selo;
- como termina.

Copie **estilo e movimento**, não o conteúdo.

### 2. Roteiro em passos

O estilo **explica em passos**. Escreva primeiro a lista do selo (1 a 3 palavras cada):

1. **o que é** ("organize suas pastas");
2. **o que você faz** ("pinte no ar"), que vem com o 1º toque;
3. **uma regra ou detalhe** ("uma cor por tema"), que vem com o 2º toque;
4. **o resultado** ("tudo no lugar");
5. **a marca**, quando o selo alarga.

Depois escolha:

- **o objeto principal:** pasta, cartão, celular, caixa…;
- **as cores:** até 3, começando pelo azul;
- **o infográfico final:** 3 colunas com nome e número, de altura proporcional.

O roteiro-tipo com todos os tempos está em `references/movimento.md`. Para 7–8 s, acrescente um toque, um segundo objeto ou uma coluna; não estique os tempos.

### 3. Montar

```bash
cp -R videos/exemplo-airpainting videos/<nn-nome>
```

1. Troque os textos (`STK`), as cores (`ORD`), as colunas (`COLS`) e a frase final.
2. Para trocar a **pasta por outro objeto**, use `RI.pintavel` e as receitas de `references/objetos.md` (celular, caixa, pizza, cartão).
3. Teste o objeto novo parado na folha (`videos/folha-de-objetos`, `node render.mjs folha --at=0.5`) antes de animar.

A técnica do pontilhado, as cores, a composição 9:16, a mão e o selo estão em `references/estilo.md`. Leia antes de desenhar algo novo.

### 4. Preview e iteração

```bash
node render.mjs <nome> --at=0.1,0.6,1.3,1.6,2.05,2.6,3.3,3.7,4.9   # instantes → previews/<nome>/NN.jpg e folha previews/<nome>.jpg
node render.mjs <nome> --preview=12
```

Para ver o **movimento**, renderize e monte uma folha a 8 qps:

```bash
ffmpeg -i out/<nome>.mp4 -vf "fps=8,scale=216:-1,tile=10x4" -frames:v 1 previews/mov.jpg
```

Para conferir o **grão**, recorte um pedaço em tamanho real:

```bash
ffmpeg -i previews/<nome>/02.jpg -vf "crop=500:400:200:850" previews/grao.jpg
```

Confira:

- o pontilhado aparece (pontos sólidos, sem linha reta onde começa);
- só o objeto principal está nítido;
- a tinta nasce **da ponta do dedo**;
- o selo troca **no** toque;
- o texto do selo cabe;
- as pilhas são proporcionais aos números;
- o último 0,5 s fica parado e completo.

### 5. Som e render final

```bash
audio/.venv/bin/python audio/synth.py <nome>   # trilha + efeitos a partir de videos/<nome>/cues.json
node render.mjs <nome>                          # out/<nome>.mp4 (junta audio/<nome>.wav sozinho)
```

O `cues.json` é escrito a cada preview ou render, então rode um preview **antes** do synth. O mapa de efeitos do estilo (clique, bolha e brilho no toque; papel; pops nas pilhas; chime na marca) está em `references/audio.md`. `RI.somToque` e `pilhas.sons()` já marcam a maior parte.

Antes de entregar, extraia 2 ou 3 quadros do mp4 final e olhe.

## Regras do motor (o render pula para qualquer instante t)

- **Tudo é função do tempo.** Toda animação acontece em `onTick(t => ...)`, calculada a partir de `t`. Não use transição ou animação CSS, `setTimeout`, `requestAnimationFrame` nem `Math.random()`; use `K.rng(seed)`. Se não for assim, o quadro renderizado não bate com o instante.
- **`RI.instalar()` primeiro**, no topo do script. Os gradientes e filtros que ele cria são usados por todas as peças.
- **Filtro em traço fino:** o `filter` com região em `objectBoundingBox` corta traços sem área (uma linha horizontal some). Use `filterUnits="userSpaceOnUse"` com região fixa.
- **Desfoque em SVG:** CSS `filter: blur()` funciona em elementos HTML (`<svg>` inteiro, como no fundo), mas não é confiável dentro do SVG. Para desfocar um `<g>`, use `RI.blur()`. O `pasta.foco()` já faz isso.
- **Fontes locais** estão em `lib/fonts.css`: Unbounded, Inter Tight, Dela Gothic One, Rubik Mono One, Bricolage Grotesque e Caveat. O render espera `document.fonts`. O selo mede o texto **depois** das fontes carregarem, ao trocar.
- **Para inspecionar um instante:** `node dbg.mjs <nome> 1.3 "document.querySelector('.ri-selo .tx').textContent"`.

## Arquivos

- `scripts/setup.sh`: cria ou completa um projeto.
- `scripts/referencia.py`: folhas de contato, quadros-chave e cores de um vídeo de referência.
- `assets/projeto/lib/riso.js`: o kit do estilo (cores, pontilhado, giz, pasta, `pintavel`, mão, toque, anéis, selo, fundo desfocado, pilhas, sons).
- `assets/projeto/videos/exemplo-airpainting/`: o exemplo completo, comentado.
- `assets/projeto/videos/folha-de-objetos/`: todas as peças paradas, em todas as cores e peles, para testar desenhos.
- `assets/projeto/`: o motor (`render.mjs`, `dbg.mjs`, `lib/`, `audio/synth.py`, `audio/narrate.py`).
- `assets/exemplo.mp4`: o resultado de referência.
- `references/estilo.md`: papel, técnica do pontilhado, cores, profundidade de campo, mão, selo, composição e o que evitar.
- `references/movimento.md`: roteiro-tipo de 5 s com tempos e eases, o toque passo a passo, selo, pilhas e microdetalhes.
- `references/objetos.md`: API completa do `RI`, receitas de objetos, como trocar a pasta e outras poses de mão.
- `references/audio.md`: trilha, mapa de efeitos e como criar efeitos novos.
