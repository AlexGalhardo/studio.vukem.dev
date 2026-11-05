---
name: video-pintura-em-camadas
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "pintura em camadas" — uma pintura clássica pendurada no museu (parede escura, moldura dourada, foco de luz, placa) em que a câmera, num plano único sem cortes, atravessa a moldura e entra NA obra, separada em camadas de profundidade: dolly contínuo com parallax 2.5D real, profundidade de campo, luz quente de museu, e parada final na figura principal com um título elegante. A ferramenta recorta as figuras, refaz o fundo atrás delas por inpainting e estende a obra para o vertical; render com Playwright + ffmpeg e som sintetizado. Use quando pedirem "pintura que ganha vida", 2.5D parallax de quadro ou afresco, "entrar dentro do quadro", passeio por obra de arte, camera move em pintura clássica, vídeo de história da arte, reels de museu, Ken Burns 3D em quadro, ou mandarem referência nesse visual pedindo "nesse estilo". Difere da irmã video-colagem-parallax, que faz parallax com recortes de fotos diversas, não com uma obra única.
---

# Vídeo em pintura em camadas

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

As 3 marcas do estilo: **(1)** a obra aparece inteira, no lugar (museu: parede, moldura, luz, placa) e a câmera **atravessa a moldura** sem corte — a moldura voa para fora e a parede se dissolve; **(2)** a pintura está **separada em camadas de profundidade** e a câmera faz um **dolly contínuo** nelas: a frente cresce e escorrega para fora mais rápido que o fundo, e atrás de cada recorte existe pintura refeita, então nada abre buraco; **(3)** **profundidade de campo e luz de museu**: primeiro plano bem desfocado, a figura principal nítida no centro, cantos escuros, e o vídeo termina parado nela. Juntas, elas transformam um quadro conhecido em um lugar onde se entra: a moldura diz "isto é uma obra", o parallax diz "isto tem espaço", e o foco diz para onde olhar.

Veja `assets/exemplo.mp4` (7,5 s, *Independência ou Morte!*, Pedro Américo, 1888). O código está em `assets/projeto/videos/exemplo-independencia/` (`index.html` + `camadas.json`) e é o ponto de partida de todo vídeo novo.

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

1. **Escolher a obra.** Pintura em domínio público (Commons: `tools/commons.py buscar "<obra> <pintor>"`, prefira as versões "Google Art Project"). Baixe com `tools/commons.py baixar "File:…" videos/<nn>/img/pintura.jpg --largura 6000` (o Commons entrega até 3840 px, que basta). Escolha a **figura principal** (onde a câmera vai parar) e verifique se ela, enquadrada em 9:16, ocupa pelo menos ~1/3 da altura com a obra a ~0,9–1,0 px de tela por px da imagem.
2. **Planejar as camadas** (4–6): fundo (céu/arquitetura distante) → terreno/meio → grupo principal (plano de foco, K = 1) → grupos do meio → primeiro plano (K 1,4–1,6). Ver `references/estilo.md` e `references/receitas.md` ("Camadas").
3. **Recortar.** `tools/camadas.py vision … --caixa` para cada grupo (a caixa tem de CONTER as figuras inteiras), confira com `camadas.py prova`, complete à mão com polígonos na grade (`tools/grade.py`): espadas, braços erguidos, chapéus, o chão logo abaixo das figuras (`{pts, suave}`).
4. **Montar as camadas.** `cd videos/<nn> && ../../audio/.venv/bin/python ../../tools/camadas.py montar camadas.json` → `img/*.webp` + `img/camadas-out.json`. Abra as camadas sobre um fundo verde se algo parecer estranho.
5. **Página.** `cp -R videos/exemplo-independencia videos/<nn-nome>` e troque: placa, título, crédito, a câmera (`S` e `A` em chaves de tempo; ver `references/movimento.md`) e a cor da parede. A ordem da página (palco → sala → placa → poeira → acabamento → título → som) não muda.
6. **Preview.** `$N render.mjs <nn> --at=0,1.2,2.2,2.8,3.6,5,6.4,7.2` → `previews/<nn-nome>/` (use `tools/folha.py` para juntar). Olhe: a moldura some antes de aparecer área vazia? Alguma espada/braço solta da figura? O fundo atrás da frente parece poeira/terra e não mancha?
7. **Som e render.** `$N render.mjs <nn> --at=1` (grava `cues.json`) → `audio/.venv/bin/python audio/synth.py <nn>` → `$N render.mjs <nn>` → `out/<nn-nome>.mp4`. Ver `references/audio.md`.
8. **Conferir.** `ffprobe` (1080×1920, duração, faixa de áudio) e uma folha: `ffmpeg -i out/<v>.mp4 -vf "fps=4,scale=180:-1,tile=10x3" -frames:v 1 folha.jpg`. Para comparar com uma referência: `tools/analisar.py comparar <ref.mp4> out/<v>.mp4 previews/comparar.jpg`.

## Regras do motor

- **Tudo é função de `t`.** A câmera é `cam = PC.camera({...})` e cada quadro chama `palco.quadro(cam(t))` dentro de `onTick`. Nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` (use `K.rng`).
- **As camadas são desenhadas em UM canvas**, de trás para a frente, com `drawImage` e `filter: blur()` em px de tela. Não ponha as camadas como `<img>` com `transform`: o Chromium serrilha a redução de 4× do começo.
- **`SETUP` é assíncrono** (carrega e decodifica as imagens com `PC.carregar`). Registre o `onTick` dentro dele.
- **Elemento HTML escondido** entra com `TL.fromTo(..., {immediateRender: true})`.
- **Fontes:** só Playfair Display (títulos, placa) e Inter Tight (rótulos, crédito) vêm na skill. Outra: ponha o woff2 em `lib/fonts/` e o `@font-face` em `lib/fonts.css`.
- **Fatos:** placa e título só com o que é certo (autor, ano, técnica, acervo, o evento retratado). Não invente medidas nem histórias.
- **Crédito** da obra no rodapé do fim, mesmo em domínio público.

## Armadilhas conhecidas

- **Área vazia quando a parede some.** Uma obra larga em 9:16 nunca preenche a altura até ~0,93 px/px. Por isso a câmera aproxima rápido no museu (S × 2,4 em 2,6 s) e a obra é estendida (céu em cima, reflexo/mato embaixo). Se aparecer preto ou o pé da obra, aumente `extensao`, `estender_baixo`, ou adie `dissolve`.
- **Espada solta no céu.** Partes finas que o Vision perde ficam na camada de trás e se separam no parallax. Some-as com polígonos finos em `mais` da camada certa (veja os da `guarda` e da `frente` no exemplo).
- **Borda reta numa figura.** Era a borda da `--caixa` do Vision cortando a figura. Refaça com uma caixa maior.
- **Retângulo de céu andando junto com um grupo.** Um polígono grande demais em `mais` levou céu junto. Use as máscaras do Vision e polígonos só para as partes finas.
- **Faixa escura no alto do céu.** É verniz velho na borda da obra. Use `clarear_topo` (o `estender` já esfuma 180 px da borda e nivela a costura).
- **Fantasma no fundo** (mão, espada repetida): sobrou da figura no fundo. Aumente a máscara (polígono ou `dilatar`) da camada da frente; o inpainting apaga o que estiver dentro dela.

## Arquivos

- `assets/projeto/lib/pintura.js` — biblioteca do estilo (`window.PC`; API em `references/receitas.md`).
- `scripts/camadas.py` — máscaras (Vision), montagem das camadas, inpainting e extensão (formato do `camadas.json` no cabeçalho do arquivo).
- `scripts/grade.py` (grade de coordenadas) · `scripts/folha.py` (folha de quadros) · `scripts/commons.py` · `scripts/recortar.py` + `cutout.swift` · `scripts/analisar.py`.
- `assets/projeto/audio/synth.py` — trilha `museu` e os sons do estilo (`passo`, `sala`, `passagem`, `vento`, `galope`, `rufo`, `timpano`).
- `references/estilo.md` (marcas, paleta, camadas, composição) · `movimento.md` (câmera, tempos) · `receitas.md` (API e receitas) · `audio.md` (trilha e cues).
