---
name: video-lowpoly-explicativo
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "low-poly explicativo" — o formato "COMO FUNCIONA · X": uma maquete 3D de massinha low-poly (peças simples, quase tudo branco/cinza com um acento laranja) flutuando num fundo azul-noite com poeira em bokeh e desfoque forte; cabeçalho mono, chip de capítulo, rótulos presos aos objetos, painéis de dados, legenda karaokê palavra a palavra; câmera que conduz por capítulos, vista em corte hachurada, peças que explodem e fluxos (água, energia, ar, dados) correndo por canos e cabos. Feito em three.js, renderizado quadro a quadro com Playwright + ffmpeg. Use quando o usuário pedir explainer 3D, "como funciona" animado, animação que ilustra um processo/máquina/sistema, infográfico 3D, vista explodida ou em corte, maquete 3D explicativa, reels educativo de ciência ou tecnologia, ou mandar referência nesse visual pedindo "nesse estilo". Difere das irmãs: video-maquete-3d é um lugar semi-realista contemplativo, video-pixel-art-hd2d é pixel art.
---

# Vídeo low-poly explicativo

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## As 3 marcas do estilo

1. Uma **maquete 3D de massinha low-poly** — peças simples e foscas, quase tudo branco/cinza com **um** acento laranja — flutuando num fundo azul-noite com poeira em bokeh e desfoque de profundidade forte (cara de miniatura).
2. O **HUD "COMO FUNCIONA · TEMA"**: cabeçalho mono espaçado, chip-pílula com o nome do capítulo, rótulos que acompanham os objetos com um fio fino, painéis escuros e carimbo laranja.
3. A **legenda karaokê** embaixo (palavras acendendo de cinza para branco) e uma **câmera que conduz a explicação por capítulos**, abrindo a maquete em corte e separando peças para mostrar o "por dentro".

O espectador lê o vídeo como uma aula: cada capítulo responde "o que acontece aqui?", e a maquete prova com movimento. Detalhe em `references/estilo.md` e `references/movimento.md`.

Veja `assets/exemplo.mp4` (11 s, "como funciona uma hidrelétrica": represa → queda no conduto → turbina gira o gerador → linhas → cidade acende). O código está em `assets/projeto/videos/exemplo-hidreletrica/index.html` e é o ponto de partida de todo vídeo novo. `videos/catalogo/` mostra todas as peças da biblioteca num quadro só.

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py exemplo --preview=6     # confere -> previews/exemplo-hidreletrica.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy e WebGL2 no Chromium do
Playwright (no Mac usa Metal). O `renderizar.py` passa o render pela trava de memória quando ela existe.

## Fluxo

1. **Roteiro em capítulos.** Quebre o processo em 3–5 etapas, cada uma vira um capítulo de 2–3 s (num vídeo de 8–12 s) com: nome curto no chip (`A REPRESA`, `A QUEDA`…), uma frase de legenda, um plano de câmera e uma "prova visual" (corte, explosão, fluxo, luz acendendo). Escreva a tabela `T` antes de modelar. Ver `references/movimento.md` e as receitas de processo em `references/receitas.md`.
2. **Modelar com a biblioteca.** Monte a maquete com `LP.terreno`, `LP.agua`, `LP.floresta`, `LP.cidade`, `LP.torre`, `LP.cano`, `LP.turbina`, `LP.gerador`, `LP.engrenagem`, `LP.carro`, `LP.boneco`… Para algo que não existe, componha `LP.caixa` / `LP.cilindro` / `LP.bola` (chanfradas, foscas, facetadas). Cada objeto: 2–6 primitivas, uma cor só, sem textura.
3. **Montar.** `cp -R videos/exemplo-hidreletrica videos/<nn-nome>` e troque: maquete, `LP.roteiroCamera` (um plano por capítulo), `S.update` (o que se mexe), HUD (`cabecalho`, `legenda`, `rotulo`, `painel`, `placar`, `cota`, `carimbo`, `tituloCapitulo`) e as cues de som.
4. **Preview.** `python3 tools/renderizar.py <nn> --at=0.6,2,3.4,5,6.6,8,9.6` → `previews/<nn-nome>.jpg`. Confira a checklist abaixo.
5. **Som e render.** `python3 tools/renderizar.py <nn> --at=1` (grava `cues.json`) → `<PYTHON> audio/synth.py <nn>` → `python3 tools/renderizar.py <nn>` → `out/<nn-nome>.mp4`. Ver `references/audio.md`.
6. **Conferir.** `ffprobe` (1080×1920, duração, faixa de áudio) e uma folha de quadros: `ffmpeg -i out/<v>.mp4 -vf "fps=3,scale=216:-1,tile=8x4" -frames:v 1 folha.jpg`. Para comparar com uma referência: `<PYTHON> tools/analisar.py comparar <ref.mp4> out/<v>.mp4 previews/comparar.jpg`.

### Checklist de cada preview

- O objeto do capítulo está entre ~25% e ~72% da altura (acima fica o HUD, abaixo a legenda) e inteiro na largura? Em 9:16 o campo horizontal é estreito: use `fov` 38–44 em planos gerais e afaste a câmera.
- Cada rótulo aponta para a peça certa e o cartão não cobre o objeto do capítulo nem a legenda?
- Há sempre 2 camadas de movimento (câmera + objeto/fluxo, poeira ao fundo)?
- O primeiro quadro de cada capítulo entra desfocado e ganha foco (rack focus)?
- A legenda acende inteira antes do corte (`t1` ≥ fim da fala + ~.5 s)?

## Regras do motor

- **Tudo é função de `t`.** O 3D muda em `S.update = t => {…}`; o HUD é registrado uma vez (`LP.rotulo(S, {...})` etc.) e se atualiza sozinho por quadro. Nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` — use `LP.rng(semente)` e `LP.fase(t, t0, t1, ease)`.
- **Página = módulo.** `boot.js` (GSAP + núcleo + importmap do three) e depois `<script type="module">import * as LP from '../../lib/lowpoly.js'</script>`. Defina `window.SETUP` de forma síncrona no módulo (sem `await` no topo).
- **Corte:** `LP.corte(normal, pos)` + `.aplicar(obj, {secao, faixas, hachura})` funciona com malhas FECHADAS (a seção é desenhada pelas faces de trás). Se houver outra malha DENTRO do volume (terreno dentro do lago), a seção falha: use `LP.secaoAgua` (perfil próprio). Tubos (`LP.cano`) não precisam de tampa: o interior escuro já aparece.
- **Explosão:** `LP.prepararExplosao(parte, [dx,dy,dz])` uma vez e `LP.explodir([partes], k)` por quadro. Explosão vertical cabe melhor em 9:16.
- **Fluxos** (`LP.fluxo`) usam InstancedMesh: centenas de partículas custam pouco. O 2º argumento de `update(t, qt)` "liga" o fluxo aos poucos.
- **Peças longe umas das outras = cenas diferentes.** Um close de máquina pode ficar em `(60, 0, 60)` na mesma cena: mude a sombra com `sombra: [x,y,z,raio]` no plano da câmera.
- **Fontes:** só Geist (legenda, rótulos, placar) e JetBrains Mono (HUD) vêm na skill. Outra fonte: ponha o woff2 em `lib/fonts/` e o `@font-face` em `lib/fonts.css`.
- **Fatos:** não invente números no texto. Prefira verbos de processo ("desce", "gira", "acende") a dados; use `placar` só com números que você conhece com certeza.
- **Estilo fechado.** O azul-noite, o branco/laranja e o HUD "COMO FUNCIONA" são a identidade do formato: não troque por tokens de `da/da.json`. A direção de arte do projeto entra no uso do clipe (moldura, carimbo, conferência final).

## Armadilhas conhecidas

- **Cena enorme e câmera colada:** em 9:16 com `fov` 30 o campo horizontal é ~17°. Uma barragem de 11 unidades a 16 de distância não cabe. Afaste ou suba o `fov`.
- **Legenda quebrando cedo:** a caixa usa `width:max-content` — não troque por `left:50%` sem largura, que encolhe a caixa à metade da tela.
- **Brilho estourado:** janelas e pulsos passam do limiar do bloom quando `forca` > ~2. Use 1,6–2,2 e `bloom.forca` ~.4.
- **Primeiros quadros do corte:** se o plano de corte começa longe, os primeiros quadros mostram uma parede marrom de seção. Comece perto (ex.: 6,5 → 0 em .7 s, `power2.out`).
- **Rótulo atrás da câmera** some sozinho; rótulo perto da borda é empurrado para dentro (margem 36 px).
- **Material compartilhado:** `LP.mat` faz cache por cor. Para mudar a cor ou o brilho de UMA peça por quadro, use `.material = LP.mat(...).clone()`.

## Arquivos

- `assets/projeto/lib/lowpoly.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/audio/synth.py` — trilha e efeitos sintetizados, com os sons do estilo (`agua`, `turbina`, `rede`).
- `assets/projeto/videos/exemplo-hidreletrica/` — o exemplo completo · `videos/catalogo/` — todas as peças.
- `references/estilo.md` (as 3 marcas, paleta, materiais, luz, composição 9:16) · `movimento.md` (capítulos, tempos, eases, câmera) · `receitas.md` (API + receitas para explicar qualquer processo) · `audio.md` (trilha e cues).
- `scripts/projeto.py` · `scripts/renderizar.py` · `scripts/comum.py` · `scripts/analisar.py` (ler e comparar referências).
