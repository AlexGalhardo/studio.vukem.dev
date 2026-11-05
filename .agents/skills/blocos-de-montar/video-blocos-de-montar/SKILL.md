---
name: video-blocos-de-montar
description: Cria vídeos curtos 9:16 (e 16:9) no estilo peças de montar — um objeto inteiro (carro, casa, máquina, monumento) feito de MILHARES de bloquinhos de plástico com pinos que se MONTA em enxame (as peças saem de montes coloridos sobre uma placa-base verde, voam em arco e assentam com quique) e depois se DESMONTA de cima para baixo, em loop perfeito, num cenário de cidade de brinquedo, com contador de peças e cliques de plástico sintetizados. Feito em three.js, renderizado por Playwright + ffmpeg. Use quando o usuário pedir algo "de LEGO", de bloquinhos, de tijolinhos, de blocos ou peças de montar, "se montando sozinho", "peça por peça", montagem ou desmontagem animada, build animation, voxel que se monta, "explodir em peças e voltar", ou mandar uma referência disso pedindo "nesse estilo". Difere das irmãs — video-jelly (gelatina translúcida), video-pelucia (pelo e feltro), video-maquete-3d (diorama semi-realista), video-pixel-art-hd2d (pixel art), video-lowpoly-explicativo (massinha que explica processos).
---

# Vídeo de peças de montar (montando e desmontando)

As 4 marcas do estilo: **(1)** um objeto inteiro feito de **milhares de peças pequenas** com pinos cilíndricos, bordas chanfradas e plástico ABS brilhante, em **voxels de tijolo** (contorno em degraus, juntas desencontradas); **(2)** a **montagem em enxame**: cada peça sai de um **monte da sua cor** sobre uma **placa-base verde cheia de pinos**, voa em **arco com giro** e **assenta com quique**, por subconjuntos na ordem real de montagem (chassi → rodas → mecânica → carroceria → detalhes → vidros → acessórios), e os montes **encolhem** enquanto o objeto cresce; **(3)** a **desmontagem** de cima para baixo (estouro para fora e para cima, cai de volta no monte) que termina idêntica ao quadro 0 → **loop perfeito**; **(4)** o **cenário de brinquedo**: rua de asfalto com faixas brancas, chão cinza-claro, prédios pastel low-poly com janelinhas, névoa clara, luz de dia suave com AO, câmera 3/4 alta que orbita e aproxima. Nada de marca registrada: diga "peças/blocos de montar", sem logotipo nos pinos e sem minifigura oficial (o bonequinho daqui é feito de tijolos).

Veja `assets/exemplo.mp4` (5 s, 9:16, ~3.000 peças numa grade 1,4× mais fina que a placa + extras): um ônibus rodoviário clássico fictício (amarelo inteiro, inclusive o teto, faixa escura de janelas correndo o lado todo com montantes, frente chata e para-brisa inteiriço, escotilhas e antena no teto) monta em 2,45 s; o letreiro do lado **cola** com um flash; ele fica pronto por 1,25 s (suspensão balança, faróis piscam e acendem, motor e buzina, a câmera chega à frente em 3/4) enquanto o bonequinho de capacete comemora, e se desmonta até 4,8 s. Código: `assets/projeto/videos/01-onibus/index.html` — ponto de partida de todo vídeo novo.

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
python3 "$S/scripts/renderizar.py"   "$P" 01 --at=0.6,1.8,3.1,4.0
```

`novo_projeto.py --node-modules <pasta>` aponta um `node_modules` que já exista na máquina (three 0.186 + gsap + playwright) em vez de baixar de novo — ele faz symlink e, se o sistema não deixar (Windows sem permissão de link), copia.

Requisitos: Node ≥ 20, ffmpeg, um Python com numpy e scipy, WebGL2 no Chromium do Playwright (no Mac usa Metal). Render: ~14 s para 150 quadros 1080×1920 com ~2.700 objetos.

## Fluxo

1. **Desenhe o objeto em voxels finos.** Peças MENORES que o passo da placa: `escala: 1/1.4` em `modelo()` (e em `placaBase`, peças avulsas `esc`) — o ônibus tem 88 × 21 × 22 voxels para ~61 de comprimento no mundo (≈3.000 peças, contorno de mosaico). Descreva a forma em **unidades do mundo** amostradas no centro de cada voxel (`W(x,y,z)` na demo): o sólido é a interseção de 3 retângulos arredondados — planta, perfil (frente chata e alta, canto do teto arredondado) e vista de frente (teto abaulado) — menos as caixas de roda; tire a casca (`casca()`), e classifique cada voxel pela face exposta (frente/trás/lado) para janelas, frisos, lanternas. Interior (bancos, painel, motor) só onde é sólido e não é casca. Modelos pequenos: `camadas([...texto], legenda)`.
2. **Subconjuntos e ordem.** `grupo(x,y,z,k)` dá o nome do subconjunto; em `programar()` cada um ganha uma janela de partida na ordem de quem monta. Peças especiais (rodas, faróis em `botao`, rack, carga) entram com `peca()`/`roda()` e o mesmo `grupo`. **Adesivo/letreiro na face externa NÃO voa** (atravessaria a carroceria): `B.colar()` depois de `instanciar()`.
3. **Montes a ~30 do centro, sempre no quadro.** No 9:16 com câmera perto, a faixa visível NA FRENTE (perto da câmera) é estreita, diante do nariz; ATRÁS cabe um arco largo (os montes de trás somem atrás do objeto quando ele cresce — ótimo para os grupos que saem cedo). Cores grandes em 2 montes (frente e trás): cada peça sai do monte do SEU lado. `montes(..., {voo, vooVolta})` deixa o voo proporcional à distância e `instanciar({arco: .7})` sobe o arco → fitas que passam por cima do objeto. Pilha de pneus, monte `resto`, bonequinho na faixa da frente. Confira as posições projetando os pontos com a mesma conta de `orbita()` antes de gastar preview.
4. **Câmera e rótulo.** `orbita()` periódica (o balanço fecha o loop) que chega à frente em 3/4 (~60°) no instante "pronto", mais perto (o objeto ~80–85% da largura) e mais baixa; `alvo` um pouco para a frente e acima do centro. `rotulo()` em y ≥ 260 px no 9:16 (fora da interface do Reels/TikTok) com contador (`contar()`, que desconta no POUSO no monte) e estado.
5. **Prévia** (≈1 s): `python3 "$S/scripts/renderizar.py" "$P" <nn> --at=0.6,1.8,3.1,4.0`; para conferir detalhe, recorte o quadro cheio em `previews/<v>-9x16/NN.jpg`.
6. **Som.** A prévia já gravou `videos/<v>/cues.json` (decolagem, encaixe, soltura e pouso de cada peça); então `python3 "$S/scripts/som.py" "$P" <nn>` → `audio/<v>.wav` (−14 LUFS, pico ≤ −2 dBTP).
7. **Render.** `python3 "$S/scripts/renderizar.py" "$P" <nn> --fmt=9x16` → `out/<v>-9x16.mp4`.
8. **Conferir.** `ffprobe` (1080×1920, yuv420p, 5 s, áudio ≈ −14 LUFS, true peak ≤ −1,5 dBTP) e folha: `ffmpeg -i out/X.mp4 -vf "fps=3,scale=270:-1,tile=5x3" -frames:v 1 folha.jpg`. Compare o primeiro e o último quadro (devem ser quase iguais) e olhe cada quadro, não só a folha.

### Checklist de cada preview

- O objeto ocupa ~80–85% da largura no instante mais próximo (9:16: `fov` 44, `raio` [121, 82] para 40 de comprimento) e a frente ~45% dele? Prédios enevoados no topo, rua embaixo?
- Os montes estão inteiros no quadro durante a montagem e encolhem sem virar anel (o algoritmo de cone já cuida disso)?
- O enxame lê como FITAS em arco saindo dos montes (não nuvem fervendo em volta do chassi)? Janelas de partida sobrepostas ~0,1 s.
- Nenhuma peça cruza o objeto já fechado (recorte 900×700 nos quadros finais da montagem; decalques com `colar()`)?
- O "pronto" dura ≥ 1,2 s e mostra a FRENTE (faróis acesos) e o adesivo legível?
- O bonequinho está dentro do quadro em todos os instantes (a órbita muda o enquadramento)?
- No último quadro todas as peças estão de volta (`fimDesmontagem` < dur − 0,2 s) e o rótulo volta a "montando"?

## Regras do motor

- **Tudo é função de `t`.** As peças são animadas por `instanciar()` (registrado em `S.cada`); o resto vai em `S.update`. Nada de `Math.random` sem semente, `setTimeout`, rAF ou animação CSS — use `B.rng(semente)`.
- **Loop:** a desmontagem é a ordem inversa EXATA da montagem e cada peça volta para a SUA posição no monte → o quadro final é o inicial. Câmera, bonequinho e suspensão usam funções periódicas em `dur`.
- **Desempenho:** uma `InstancedMesh` por tipo × família, cor por instância, matrizes atualizadas a cada quadro. 2–5 mil peças renderizam a ~0,09 s/quadro (a demo: 2.430 + extras + 15 mil pinos da placa). Não crie `Mesh` por peça.
- **Construa dentro de `window.SETUP`** (o adesivo usa a fonte Geist, que só está carregada ali).
- **Marcas sempre fictícias**; o contador e textos são decorativos. Nunca escreva na tela a marca registrada das peças, nem nome de pessoa real ou de cliente.

## Armadilhas conhecidas

- A casca só é calculada certo se o sólido for contínuo: defina `solido()` e tire a casca você mesmo quando houver interior (bancos), senão o interior some ou a carroceria fica maciça.
- Camadas com arredondamento diferente (teto recuado) deixam buracos nos cantos se forem paredes independentes — faça tudo como um sólido e deixe a casca resolver.
- Monte grande demais esconde o objeto: divida cores com muitas peças em 2 montes e ponha atrás os que forem maiores.
- O adesivo de canvas tem verso de papel (não aparece espelhado ao girar no voo). Texto pequeno (< 40 px no canvas de 1024) some no 9:16.
- Peça voando para a face externa de um objeto já fechado atravessa a carroceria: use `colar()` ou um monte do mesmo lado.
- A face de trás de uma caixa de roda também é "traseira": limite lanternas/vigia por posição (`xw < -17`), não só pela face exposta.
- As cores do cenário em `CENA` são cores-BASE calibradas: a luz do palco clareia ~1,4× (linear) — meça o render, não a cor-base.
- O GTAO ignora objetos transparentes (vidro, sprites); para pôr um no AO: `obj.userData.ao = true`.
- **Trava de memória:** `renderizar.py` e `som.py` já passam pela trava do kit de direção de arte quando ela existe (máquina pequena, vários agentes). Não chame o `render.mjs` direto.

## Tipografia e direção de arte

- Fontes do estilo, em `assets/projeto/lib/fonts/` e declaradas em `lib/fonts.css`: Geist (rótulo, contador e o adesivo desenhado em canvas) e JetBrains Mono (dados). Ambas são livres (OFL) e já vêm na caixa. O render **não usa rede**; fonte que não estiver na pasta não carrega.
- Este é um estilo fechado: ele **é** a direção de arte da peça. Quando o projeto já tiver `da/da.json`, use a cor de acento e os nomes fictícios dela no rótulo e no adesivo em vez de inventar cor; a paleta das peças e o cenário de brinquedo não mudam.

## Arquivos

- `assets/projeto/lib/blocos.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/videos/01-onibus/` — a demo (9:16 e 16:9 via `<meta name="formats">`).
- `assets/projeto/audio/synth.py` — sons por peça (chacoalhar na decolagem, encaixe, soltar, cair no monte), motor, buzina, faróis, whoosh por lote, marimba leve e ambiente de rua, em loop; loudness BS.1770 −14 LUFS e limitador de pico verdadeiro.
- `references/estilo.md` (marcas, paleta, materiais, luz, câmera, composição, tempo) · `references/receitas.md` (API + receitas de outros objetos).
- `scripts/novo_projeto.py` (cria o projeto) · `scripts/renderizar.py` (prévia e render) · `scripts/som.py` (trilha e efeitos) · `scripts/preparar.py` (instalação).
