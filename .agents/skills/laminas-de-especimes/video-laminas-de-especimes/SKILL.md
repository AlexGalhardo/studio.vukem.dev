---
name: video-laminas-de-especimes
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "lâminas de espécimes" — uma coleção de museu folheada em ritmo de semicolcheia: UM exemplar por vez (inseto, concha, mineral, folha, semente, pena), fotografado de cima, recortado sem sombra e centrado pelo corpo sobre creme-sálvia liso, trocando por corte seco a cada 1/9 s, com cores vivas alternadas e laço perfeito; por baixo, etiqueta de coleção discreta (grupo em versal, nome científico em itálico, número datilografado). Páginas HTML quadro a quadro (GSAP + Playwright + ffmpeg), fotos do Wikimedia Commons recortadas e trilha a 135 bpm. Use quando pedirem "coleção", "espécimes", "pranchas de museu", "catálogo de insetos/besouros/borboletas/conchas/minerais", "gabinete de curiosidades", "flipbook de fotos", "desfile de objetos um por um", "muitos bichos passando rápido", ou mandarem referência nesse visual pedindo "nesse estilo". Difere da irmã video-mosaico-de-fotos, que troca versões da MESMA foto em blocos de uma grade.
---

# Vídeo em lâminas de espécimes

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Três marcas, juntas, fazem o estilo:

1. **Espécime de museu sozinho no creme liso.** Foto macro real (foco empilhado), vista de cima, recortada **sem sombra**, centrada pelo **corpo** (não pela caixa: antena comprida não desloca o bicho) sobre creme-sálvia `#e9ecd9` sem textura nem vinheta. O eixo do corpo segue o lado maior do quadro: no 9:16, **cabeça para cima**.
2. **Folhear a 9 por segundo.** Corte seco a cada 1/9 s (6–7 quadros a 60 qps), imagem **parada** entre os cortes, ritmo constante do primeiro ao último quadro e **laço perfeito** (o último exemplar emenda no primeiro). 9/s = semicolcheia a 135 bpm: a música e a imagem fecham juntas.
3. **Desfile de cor.** Cada vizinho contrasta com o anterior (metálico → aposemático → iridescente → escuro), em blocos por forma (redondos, escaravelhos, alongados, asas abertas). Os tamanhos são parecidos (normalizados pela área do corpo).

O texto é mínimo e fica fora do bicho: um cabeçalho em versal espaçada e uma etiqueta de coleção embaixo (grupo · ordem / nome científico / nº 001–064). A referência original não tinha texto: se o usuário não pedir rótulos, `LA.etiqueta` e `LA.cabecalho` podem sair.

Veja `assets/exemplo.mp4` (7,1 s, "Coleção entomológica": 48 besouros + 16 borboletas e mariposas de espécies registradas no Brasil). O código está em `assets/projeto/videos/exemplo-insetos/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar o projeto (uma vez por pasta)

```
python3 <caminho-da-skill>/scripts/setup.py <pasta-do-projeto>
```

Roda igual no Mac, no Linux e no Windows (não precisa de bash). Ele confere `ffmpeg`/`ffprobe` e um
Node ≥ 20, copia o projeto para a pasta, roda `npm install`, baixa o Chromium do Playwright, cria o
venv em `audio/.venv` com numpy/scipy/pillow, copia as ferramentas para `tools/` e grava
`tools/ambiente.json`. No fim imprime:

```
PYTHON=<python do venv do projeto>     ← chamado de $P daqui para a frente
NODE=<o Node >= 20 que ele achou>
```

Daí em diante **todo comando roda da raiz do projeto** com esse `$P`
(`audio/.venv/bin/python` no Mac e no Linux, `audio\.venv\Scripts\python.exe` no Windows).
O motor é chamado por `$P tools/render.py <nn> [...]`, que acha o Node sozinho, passa pela trava de
máquina e repassa o resto dos argumentos ao `render.mjs`.

## Fluxo

1. **Coleção e conta.** Decida o grupo (insetos, conchas, minerais…) e o número de exemplares: **16 por compasso** a 135 bpm (48 = 5,3 s · 64 = 7,1 s). Divida em 1–3 "gavetas" (grupos com etiqueta própria), cada uma com um número inteiro de compassos se der. Não invente fatos: a etiqueta só leva grupo, ordem/família e o nome do arquivo.
2. **Achar fotos** (ver `references/receitas.md`, "Fotos"): `tools/colecao.py buscar 'deepcategory:"Coleoptera of Brazil" Schmidt' … --claro --folha previews/busca/a.jpg` e escolha olhando a folha. Exemplares de museu em fundo liso (claro ou preto), vista dorsal, um ou dois por foto.
3. **Recortar e normalizar:** `mkdir -p videos/<nn-nome> && cp videos/exemplo-insetos/index.html videos/<nn-nome>/`; escreva `videos/<nn-nome>/especimes.json` (id, título "File:…", grupo, giro) e rode `tools/especime.py preparar videos/<nn-nome>/especimes.json` → WebP com alfa no tamanho de tela + `especimes.js` + `creditos.json` + `previews/especimes.jpg` (folha de conferência no creme). Confira a folha: cabeça para cima? sombra? fundo preso entre antenas? Corrija o item (`rot`, `lado`, `t0/t1`, `vision`) e rode com `--so b07,b12`.
4. **Montar:** no `index.html`, escreva a `ORDEM` (ids) alternando cores; troque cabeçalho, grupos e créditos (`tools/especime.py creditos videos/<nn-nome>/creditos.json` dá a lista de autores).
5. **Preview:** `$P tools/render.py <nn> --at=0,1,2,3,4,5,6,7` → `previews/<nn-nome>.jpg`.
6. **Som e render:** `$P tools/render.py <nn> --at=0` (grava `cues.json`), `$P audio/synth.py <nn>`, `$P tools/render.py <nn>` → `out/<nn-nome>.mp4` (ver `references/audio.md`).
7. **Conferir:** `ffprobe` (1080×1920, duração = n/9, uma faixa de áudio), folha a 8 qps (`ffmpeg -i out/x.mp4 -vf "fps=8,scale=216:384,tile=8x8" -frames:v 1 folha.jpg`): vizinhos contrastam? nenhum bicho escuro em fila? antenas dentro da faixa? crédito no rodapé?

## Regras do motor

- Tudo é função do tempo: `LA.colecao` troca o `<img>` visível no `onTick`; nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` (use `K.rng`).
- Imagens: `await col.pronto()` dentro do `window.SETUP` (decodifica tudo antes do 1º quadro). `LA.sons(col)` também vai no SETUP.
- `fps: 60` (a referência é 60 e a cadência 7-7-6 fica mais regular); `dur: n / 9`.
- Fontes só de `lib/fonts.css` (Inter Tight, Libre Caslon Text, Courier Prime, todas OFL).

## Armadilhas do estilo

- **Bicho escuro em fila** (rola-bostas pretos, mariposas pardas): o desfile apaga. Intercale com um vivo a cada 2–3 ou troque o exemplar.
- **Sombra no recorte** (foto com luz lateral sobre fundo cinza): suba `t0/t1` ou use `"vision": true`.
- **Fundo branco preso dentro de antena em laço:** o `especime.py` já deixa transparente buraco grande com cor de fundo; se sobrar, baixe o limiar com `t0/t1`.
- **Antena tocando o cabeçalho:** use `faixa: [topo, base]` em `LA.colecao` (o exemplar desliza só o necessário).
- **Cabeça para baixo ou de lado:** `rot` é giro horário em graus (90 = cabeça que estava à esquerda vai para cima). Fotos de Udo Schmidt costumam vir de cabeça à esquerda (`rot: 90`); Ben Sale e Didier Descouens já vêm de cabeça para cima.
- **Movimento dentro do hold:** não ponha. Zoom, flutuação ou fade entre exemplares desmancham a marca 2.
- **Rótulo legível?** A 9/s o nome científico não é para ser lido, é textura de catálogo; o que se lê é o grupo (fica ~2–5 s).

## Arquivos

- `assets/projeto/lib/laminas.js` — biblioteca do estilo, global `LA` (API em `references/receitas.md`).
- `scripts/especime.py` — baixa do Commons, recorta por cor (mantém antenas), separa pares, gira, tira halo, normaliza tamanho, grava WebP + `especimes.js` + créditos + folha de conferência.
- `scripts/colecao.py` — busca no Commons com filtro de licença e de fundo liso, folha de contato numerada.
- `references/estilo.md` (marcas, paleta, tipografia, composição 9:16) · `movimento.md` (ritmo e tempos medidos) · `receitas.md` (API e passo a passo) · `audio.md` (trilha `gabinete` e efeitos).
- `scripts/setup.py` · `node.py` · `commons.py` · `recortar.py` + `cutout.swift` · `analisar.py` (ler uma referência nova e comparar lado a lado).
