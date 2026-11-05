---
name: video-jelly
description: Cria vídeos curtos 9:16 (reels, shorts, TikTok) no estilo gelatina — criaturas e objetos de BALA DE GOMA translúcida que BALANÇAM (squash & stretch, ondas que sobem pelo corpo a cada passo e impacto), com miolo luminoso, bolhas suspensas, olhinhos brilhantes e sombra colorida, sobre um prato de porcelana num estúdio creme, com HUD editorial de "estudo de material". Feito em three.js e renderizado quadro a quadro por Playwright + ffmpeg, com som sintetizado e loop perfeito. Use quando o usuário pedir gelatina, jelly, bala de goma, jujuba, ursinho de goma, gummy bear, personagem translúcido/gelatinoso que chacoalha, "material study" de doce, animação fofa que balança, ou mandar uma referência nesse visual pedindo "nesse estilo". Difere das irmãs — video-pelucia (pelo e feltro opacos), video-blocos-de-montar (peças de plástico que se montam), video-maquete-3d (diorama semi-realista), video-pixel-art-hd2d (pixel art), video-lowpoly-explicativo (massinha fosca que EXPLICA um processo).
---

# Vídeo Jelly Bear (gelatina)

As 3 marcas do estilo: **(1)** o MATERIAL — gelatina translúcida e saturada que deixa a luz passar e tinge o que está atrás, borda densa, miolo que brilha, verniz com reflexo branco nítido, pontinhos escuros e bolhas claras suspensos; **(2)** o BALANÇO — tudo que é de goma reage a passos e impactos com squash & stretch, cisalhamento e ondas que sobem e morrem (molas amortecidas), e a sombra colorida respira junto; **(3)** a VITRINE editorial — prato branco de porcelana num estúdio creme, câmera quase parada com leve deriva, HUD de estudo de material (serifa itálica enorme com ponto da cor do sabor, painel do espécime, dados embaixo). O espectador lê como um experimento de laboratório de doce: "olha como esse material se comporta".

Paleta de sabores: morango (vermelho), limão (verde), laranja, uva (roxo), abacaxi (amarelo), framboesa azul. Fundo creme, prato branco, sombras coloridas translúcidas.

Veja `assets/exemplo.mp4` (5 s, loop: mini obra de ursinhos de goma — mestre de obras martela o tijolo do topo, servente carrega tijolo, ajudante mexe a massa, operário manobra o carrinho de mão). Código em `assets/projeto/videos/01-obra-jelly/index.html` — ponto de partida de todo vídeo novo.

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Começar um projeto (uma vez por pasta)

```bash
S="<pasta desta skill>"; P="<pasta do projeto>"
python3 "$S/scripts/novo_projeto.py" "$P"                       # copia o projeto e liga as bibliotecas Node
python3 "$S/scripts/renderizar.py"   "$P" 01 --at=0.3,1.2,2.3,3.4,4.6
```

`novo_projeto.py --node-modules <pasta>` aponta um `node_modules` que já exista na máquina (three 0.186 + gsap + playwright) em vez de baixar de novo — ele faz symlink e, se o sistema não deixar (Windows sem permissão de link), copia.

Requisitos: Node ≥ 20, ffmpeg, um Python com numpy e scipy, WebGL2 no Chromium do Playwright (no Mac usa Metal). Render: ~15–40 s para 150 quadros 1080×1920.

## Fluxo

1. **Elenco e ações em loop.** Liste os personagens (1 sabor cada, contrastando com o que fica atrás deles) e o que cada um faz. Para o loop fechar, toda ação é periódica no `VIDEO.dur` (martelar 8×, mexer 4×, ir-e-voltar) e a câmera deriva com `sin(2πt/dur)`. Escreva a tabela de tempos `T` antes de modelar.
2. **Montar a cena.** `JL.palco()` → `JL.prato()` → peças (`JL.parede`, `JL.tijolo`, `JL.carrinho`, `JL.masseira`, `JL.placa`, `JL.marmita`, `JL.monte`) → personagens (`JL.ursinho({sabor, capacete, colete})`) com ferramentas presas nas mãos (`U.mao.E/D`). Ver `references/receitas.md`.
3. **Balanço.** Cada corpo que balança junto tem um `JL.jiggle()`; registre os impactos uma vez no setup (`J.impacto(t, força, [frente, lado])` para pisadas, paradas, marteladas, quedas) e chame `J.atualizar(t, objeto)` / `U.atualizar(t)` no `S.update`. Os mesmos instantes viram `cue(...)` de som.
4. **Composição 9:16.** Título em cima à esquerda, painel em cima à direita, prato no meio-baixo, dados embaixo. Objetos altos (placa, quem fica atrás da parede) do lado ESQUERDO: o painel cobre o fundo à direita. Câmera: `fov 30`, elevação ~28°, distância ~6,6 para um prato de raio 1,18.
5. **Prévia e conferência.** `python3 "$S/scripts/renderizar.py" "$P" 01 --at=0.3,1.2,2.3` → `previews/01-obra-jelly.jpg` e os quadros cheios em `previews/01-obra-jelly/`. Rode a checklist abaixo. Use `dbg.mjs` para medir posições (`window.DBG`).
6. **Som.** A prévia já gravou `videos/01-obra-jelly/cues.json`; então `python3 "$S/scripts/som.py" "$P" 01` → `audio/01-obra-jelly.wav` (trilha 'jelly' + efeitos de goma, −14 LUFS, loop perfeito).
7. **Render.** `python3 "$S/scripts/renderizar.py" "$P" 01` → `out/01-obra-jelly.mp4` (1080×1920, 30 fps, H.264 yuv420p, faststart, AAC).
8. **Folha de quadros:** `ffmpeg -i out/X.mp4 -vf "fps=3,scale=270:-1,tile=5x3" -frames:v 1 folha.jpg` — e olhe cada quadro, não só a folha.

### Checklist de cada preview

- Cada personagem tem silhueta livre? Ninguém passa na frente da ação principal; o objeto que ele carrega não se perde contra algo da mesma cor (tijolo laranja contra parede laranja não lê — mude o caminho).
- A goma está translúcida (dá para ver o prato/colete através, pontinhos visíveis) e não parece plástico? Se ficou "chapada": aumente `atenuacao`, clareie `cor`, reduza `borda`.
- O balanço aparece em sequência de quadros (extraia 6 quadros seguidos em volta de um impacto)?
- Sombras coloridas presentes sob as peças de goma; a placa e o painel não se sobrepõem.
- Primeiro e último quadro combinam (câmera e ações periódicas)?

## Regras do motor

- **Tudo é função de `t`.** Molas são analíticas (soma de respostas a pulsos), então dá para pular para qualquer quadro. Com `loop = dur` (padrão) os pulsos do fim reverberam no começo. Nada de `Math.random` (use `JL.rng`), `setTimeout`, rAF ou animação CSS.
- **Jiggle no shader:** `JL.comJiggle(material, J)` injeta a deformação em qualquer material (inclusive InstancedMesh e SkinnedMesh). Tudo que é preso a um corpo usa o MESMO `J` (olhos, bolhas, capacete, colete, ferramenta, tijolo na mão), senão descola.
- **Transmissão:** a goma só "enxerga" objetos opacos atrás dela (prato, colete, massa). Goma atrás de goma não aparece através. Sombras coloridas são decalques (multiply + aditivo), não shadow map; peças de goma têm `castShadow = false`.
- **Malhas suaves por SDF:** `JL.malhaSDF(f, min, max, res)` (marching cubes) faz formas orgânicas sem emenda (ursinho, tijolo com furos, caçamba). Gere uma vez e compartilhe a geometria.
- **Página = módulo** com `window.SETUP` síncrono; HUD registrado uma vez (`JL.titulo`, `JL.pilula`, `JL.painel`, `JL.dados`, `JL.rodape`) e atualizado por quadro.
- **Marcas sempre fictícias** (ex.: "CONSTRUTORA JUJUBA"); textos em pt-BR com acentos. Nada de pessoa real, marca registrada ou cliente na tela.

## Armadilhas conhecidas

- **Painel em cima à direita cobre o fundo do prato:** coloque placa, parede alta e quem martela à esquerda/centro.
- **Ferramenta na mão errada:** com o ursinho virado para a câmera, a mão E (+x local) fica à DIREITA da tela. Para acertar o alvo use o resolvedor do exemplo (varre o ângulo do braço e posiciona o corpo para a cabeça do martelo cair no tijolo).
- **`yuvj420p`:** o render.mjs já converte para `yuv420p` faixa TV; não tire o `-vf scale=...`.
- **Material cacheado:** `JL.gelatina(sabor, J, o)` faz cache por (cor, jiggle, opções). Para outra intensidade numa peça, passe opções diferentes ou outro `J`.
- **Loop com objetos que mudam de lugar** (tijolo largado no monte) dá um "pulo" de 1 quadro no fecho; esconda atrás de alguém ou prefira ações que voltam ao estado inicial.
- **Trava de memória:** `renderizar.py` e `som.py` já passam pela trava do kit de direção de arte quando ela existe (máquina pequena, vários agentes). Não chame o `render.mjs` direto.

## Tipografia e direção de arte

- Fontes do estilo, todas em `assets/projeto/lib/fonts/` e declaradas em `lib/fonts.css`: a serifa editorial do título, Geist nos rótulos e JetBrains Mono nos dados. O render **não usa rede**; fonte que não estiver na pasta não carrega.
- A serifa que vem na caixa é a fonte de sistema do macOS (NewYork*.ttf). Para publicar fora do seu computador, troque por uma serifa itálica livre (OFL) com o mesmo nome de família em `lib/fonts.css` — o layout não muda.
- Este é um estilo fechado: ele **é** a direção de arte da peça. Quando o projeto já tiver `da/da.json`, use a cor de acento e as marcas fictícias dela no HUD (ponto do título, pílula "AO VIVO") em vez de inventar cor; o material da goma e o estúdio creme não mudam.

## Arquivos

- `assets/projeto/lib/jelly.js` — a biblioteca (API em `references/receitas.md`) · `assets/projeto/audio/synth.py` — trilha 'jelly' + efeitos de goma (martelo, passo, plop, massa, baque, boing, squish), loop perfeito.
- `references/estilo.md` — o que define o visual (material, luz, paleta, câmera, composição, HUD) · `references/receitas.md` — API + receitas.
- `scripts/novo_projeto.py` (cria o projeto) · `scripts/renderizar.py` (prévia e render) · `scripts/som.py` (trilha e efeitos) · `scripts/preparar.py` (instalação).
