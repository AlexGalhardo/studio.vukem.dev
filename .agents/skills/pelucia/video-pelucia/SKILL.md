---
name: video-pelucia
description: Cria vídeos curtos 9:16 (reels, shorts, TikTok) no estilo pelúcia — bonecos, bichos e objetos de PELO CURTO de verdade (fios visíveis na silhueta, raiz escura e pontas claras, brilho de veludo na borda), olhos de botão, costurinhas e feltro, flutuando num estúdio creme com uma sombra enorme e muito desfocada no chão, com HUD editorial de "estudo de material" (amostras de pelo, sliders, dados em mono). Feito em three.js e renderizado quadro a quadro por Playwright + ffmpeg, com som sintetizado e loop perfeito. Use quando o usuário pedir pelúcia, plush, bicho de pelúcia, boneco fofinho de pano, feltro, mascote fofo em 3D, brinquedo macio animado, "material study", ou mandar uma referência nesse visual pedindo "nesse estilo". Difere das irmãs — video-jelly (gelatina translúcida que balança), video-blocos-de-montar (peças de plástico que se montam), video-maquete-3d (diorama semi-realista), video-pixel-art-hd2d (pixel art), video-lowpoly-explicativo (massinha fosca que EXPLICA um processo).
---

# Vídeo pelúcia

As 3 marcas do estilo: **(1)** o material — pelúcia de pelo curto (≈5 mm) feita por cascas: fios aparecem na silhueta contra o fundo, a raiz é escura e a ponta clara, a borda ganha brilho de veludo, o pelo clareia/escurece conforme a direção do penteado; olhos de botão plástico com reflexo, costurinhas de linha, feltro fosco com fibras; **(2)** o estúdio — fundo creme quase liso (#e1ddd8), luz alta e macia, lente longa (fov ~22, quase foto de produto) e uma sombra ENORME e muito desfocada no chão, bem abaixo do objeto, deslocada pela luz (ele flutua); **(3)** o HUD editorial de "estudo de material": rótulo miúdo espaçado, título gigante em serifa itálica com a 2ª linha recuada, texto itálico curto, painel do espécime (amostras de pelo, sliders, ações — a ativa fica preta), rodapé com dica itálica e dados em mono. Movimento sempre macio e contínuo: flutua, balança, enche/esvazia, nada em "S" lento.

Veja `assets/exemplo.mp4` (5 s, loop: a equipe de uma lanchonete fictícia — o chapeiro vira o hambúrguer na chapa, a atendente passa a bandeja e o entregador guarda o pedido na sacola). O código está em `assets/projeto/videos/01-lanchonete-pelucia/index.html` e é o ponto de partida de todo vídeo novo.

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
python3 "$S/scripts/novo_projeto.py" "$P"                 # copia o projeto e liga as bibliotecas Node
python3 "$S/scripts/renderizar.py"   "$P" 01 --at=0.3,1.6,3,4.2
```

`novo_projeto.py --node-modules <pasta>` aponta um `node_modules` que já exista na máquina (three 0.186 + gsap + playwright) em vez de baixar de novo — ele faz symlink e, se o sistema não deixar (Windows sem permissão de link), copia.

Requisitos: Node ≥ 20, ffmpeg, um Python com numpy e scipy, WebGL2 no Chromium do Playwright (no Mac usa Metal). Render: ~12 s para 5 s de vídeo 1080×1920.

## Fluxo

1. **Ideia em 1 frase + elenco.** Quem são as pelúcias, o que cada uma FAZ sem parar (todo mundo se mexe do 1º ao último quadro) e qual objeto passa entre elas. Vídeo curto = 1 ciclo de 5–8 s que fecha em loop.
2. **Modelar com a biblioteca.** `PL.boneco({...})` para gente (pele, cabelo, camisa, avental, boné/viseira, crachá, bigode, boca), `PL.pelucia(geo, {cor, comp, dens, ventre, pente…})` para qualquer bicho/objeto de pelo, `PL.feltro(cor)` para o resto. Comidas e objetos prontos: `hamburguer`, `carne`, `batata`, `refri`, `bandeja`, `sacola`, `chapa`, `espatula`. Ver `references/receitas.md`.
3. **Montar.** Copie `videos/01-lanchonete-pelucia` para `videos/<nn-nome>` e troque: elenco, `BASE` (posições), âncoras e viagem dos objetos, `S.update`, HUD (`cabecalhoEditorial`, `painel`, `rodape`) e as cues de som.
4. **Prévia.** `python3 "$S/scripts/renderizar.py" "$P" <nn> --at=0,1,2,3,4` → `previews/<nn-nome>.jpg` (cada quadro também em `previews/<nn-nome>/NN.jpg` em 1080×1920 — recorte com ffmpeg para olhar o pelo de perto). Confira a checklist.
5. **Som.** A prévia já gravou `videos/<nn-nome>/cues.json`; então `python3 "$S/scripts/som.py" "$P" <nn>` → `audio/<nn-nome>.wav` (caixinha de música em loop + efeitos de feltro).
6. **Render.** `python3 "$S/scripts/renderizar.py" "$P" <nn>` → `out/<nn-nome>.mp4` (1080×1920, 30 fps, H.264 yuv420p, faststart).
7. **Conferir.** `ffprobe` e folha: `ffmpeg -i out/<v>.mp4 -vf "fps=3,scale=270:-1,tile=5x3" -frames:v 1 folha.jpg` — e olhe cada quadro, não só a folha.

### Checklist de cada preview

- O elenco cabe entre y≈620 (fim do texto itálico) e y≈1380, e o canto de baixo à direita fica livre para o painel (top ~1300)?
- A sombra aparece no chão como formas reconhecíveis (não uma faixa)? Se virou faixa: menos `desfoque`, luz mais vertical, câmera mais alta (`elev` 22–28).
- A silhueta mostra fios (não um halo liso)? Recorte 1:1 e olhe a borda.
- Todo personagem faz algo o tempo todo e o último quadro emenda no primeiro?
- Nenhum objeto atravessa uma cabeça na viagem (use o desvio em Bézier `bez(A, B, k, off)`).

## Regras do motor

- **Tudo é função de `t`** em `S.update = t => {…}`; HUD se registra uma vez e se atualiza sozinho. Nada de `Math.random` (use `PL.rng`), `setTimeout`, rAF ou animação CSS.
- **Loop perfeito:** use `PL.onda(t, periodo, desloc)` com períodos que dividem a duração (5 → 5, 2,5, 1,25) e `PL.chaves(t, lista, {per: D})` para poses. Objeto que viaja de mão em mão: a viagem dura 2D e há DUAS cópias defasadas em D (ver `posBandeja` no exemplo).
- **Pelo:** geometria em unidades finais (escale a GEOMETRIA, não a malha — o ruído dos fios é em espaço do objeto). Comprimento 0,02–0,04 (corpo .036, cabeça ×.85, mãos ×.8, boné .012) e densidade 100–230 fios/unid.; `tufo` (.8) varia o comprimento por tufos para personagens de ~1,8 unid. vistos a ~20 unid.; pelo fino demais vira névoa na borda.
- **Fundo nunca desfoca** (o DOF ignora o fundo para não criar halo em volta do pelo). DOF só entre personagens, bem leve (`abertura` ~.02, `max` ~7).
- **Sombra:** `PL.sombraChao` renderiza as silhuetas vistas da luz e desfoca; toda malha entra, exceto as com `userData.semSombra = true` (as cascas do pelo já vêm marcadas).
- **Marcas sempre fictícias**, textos em pt-BR com acento. Nada de pessoa real, marca registrada ou cliente na tela.

## Armadilhas conhecidas

- **Halo claro em volta do pelo:** vinha do DOF misturando a borda com o fundo — já resolvido no `coc()`; se voltar, baixe `veludo` (.25–.35) e `pontas` (~1.05).
- **Sombra em faixa:** desfoque grande demais (`desfoque` > 1,5 com `res` 384) funde as sombras. Mantenha ~1,1 e `passes: 3`.
- **Pele escura + olho de botão preto some:** o boneco já põe um aro de feltro creme atrás do botão (`aroOlho`); não tire em pele escura.
- **Fumaça de feltro** (`PL.fumaca`) na frente do corpo vira mancha; use longe do personagem ou não use.
- **Material compartilhado:** `PL.feltro` faz cache por cor; para animar a opacidade de UMA peça use `{unico: true}`.
- **Só 9:16:** o HUD está posicionado em px para 1080×1920. Para 16:9, reposicione as classes `.pl-*` no CSS da biblioteca.
- **Trava de memória:** `renderizar.py` e `som.py` já passam pela trava do kit de direção de arte quando ela existe (máquina pequena, vários agentes). Não chame o `render.mjs` direto.

## Tipografia e direção de arte

- Fontes do estilo, todas em `assets/projeto/lib/fonts/` e declaradas em `lib/fonts.css`: a serifa editorial (título e itálicos), Geist (rótulos) e JetBrains Mono (dados). O render **não usa rede**; fonte que não estiver na pasta não carrega.
- A serifa que vem na caixa foi extraída de uma fonte de sistema do macOS. Para publicar fora do seu computador, troque por uma serifa itálica livre (OFL) com o mesmo nome de família em `lib/fonts.css` — o layout não muda.
- Este é um estilo fechado: ele **é** a direção de arte da peça. Quando o projeto já tiver `da/da.json`, use a cor de acento e as marcas fictícias dela no HUD em vez de inventar cor; o material do pelo e o estúdio creme não mudam.

## Arquivos

- `assets/projeto/lib/pelucia.js` — a biblioteca (API em `references/receitas.md`).
- `assets/projeto/videos/01-lanchonete-pelucia/` — o exemplo completo · `assets/projeto/audio/synth.py` — caixinha de música em loop + efeitos de feltro (vira, pof, fofo, sacola, sino, clique, pop, chiado).
- `references/estilo.md` (o que define o visual: material, luz, paleta, composição, HUD) · `references/receitas.md` (API + receitas).
- `scripts/novo_projeto.py` (cria o projeto) · `scripts/renderizar.py` (prévia e render) · `scripts/som.py` (trilha e efeitos) · `scripts/preparar.py` (instalação).
