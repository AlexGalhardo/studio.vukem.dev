---
name: video-mapa-documental
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "mapa documental" de canal de história — mapa de satélite escuro sobre papel quadriculado, país que acende em verde-esmeralda piscando, com bordas brancas e rios acesos, região vermelha translúcida que se espalha e se fecha numa área marcada por um triângulo vermelho, e anotações de documentário (chamada com cotovelo cujo rótulo se decodifica, retrato P&B em círculo, círculo tracejado), num mergulho de câmera sem cortes. Páginas HTML quadro a quadro (canvas + GSAP + Playwright + ffmpeg), com relevo e vetores de domínio público. Use quando o usuário pedir mapa animado, "mapa estilo documentário", mapa histórico ou de guerra, "como X se espalhou pelo mapa", expansão/rota/território/migração no mapa, explainer de história ou geografia, reels educativo com mapa, "igual aos mapas de canal de história", ou mandar referência nesse visual pedindo "nesse estilo". Difere das irmãs 3D (video-maquete-3d, video-lowpoly-explicativo): aqui o palco é o mapa.
---

# Vídeo em mapa documental

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## As 3 marcas do estilo

1. **Mapa escuro de satélite sobre papel cinza quadriculado com vinheta** — o país em foco acende verde-esmeralda com bordas brancas brilhantes e rios/lagos verde-água acesos; o resto da terra fica cinza-escuro.
2. **Região vermelha translúcida de borda macia** que acende piscando, se espalha em manchas e se fecha numa área só, marcada por um **triângulo vermelho com texto branco black**.
3. **Anotações de documentário** sobre um **mergulho contínuo de câmera sem cortes**: chamadas com cotovelo cujo rótulo se decodifica (barras borradas → letras), retrato P&B em círculo que voa para dentro do triângulo, círculo tracejado que encolhe girando.

Funciona porque o espectador lê o mapa como "documento": a textura de satélite dá verdade, o piscar elétrico dá a sensação de sistema/arquivo, e o vermelho sobre verde dirige o olho para um só lugar enquanto a câmera mergulha. Detalhe em `references/estilo.md` e `references/movimento.md`.

Veja `assets/exemplo.mp4` (8 s, "o café no Brasil — como ele se espalhou pelo mapa"). O código está em `assets/projeto/videos/exemplo-cafe/index.html` e é o ponto de partida de todo vídeo novo.

O demo foi escolhido de propósito: um caso econômico documentado, com as fontes no rodapé. **Guerra, conflito, fronteira em disputa e perseguição são o terreno onde este estilo mente melhor** — o mapa parece documento e qualquer mancha vermelha vira afirmação. Nesses temas, ou você tem fonte para cada mancha, cada data e cada rótulo, ou escolhe outro recorte. Para treinar o formato sem risco, use um caso fictício (uma ilha inventada, uma rota de comércio imaginária).

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py exemplo --preview=12    # confere -> previews/exemplo-cafe.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy, scipy e Pillow, e internet na
primeira vez em que for baixar os dados de um mapa novo (o exemplo já vem com as texturas prontas).
O `renderizar.py` passa o render pela trava de memória quando ela existe.

## Fluxo

1. **Roteiro** — escolha o país e a região-alvo, e escreva a tabela `T` com o roteiro-tipo de `references/movimento.md` (mundo → país acende → mergulho com bordas → etiquetas → manchas se espalham → núcleo + mergulho → triângulo → chamada 1 → retrato → círculo → chamada 2 → respiro). Em 5–8 s mantenha essa ordem e proporção.
   **Fatos:** não invente números nem datas; use só o que você sabe com certeza (ano marcante, século, "maior produtor hoje"…). Assunto sensível (guerra, conflito, perseguição) exige fonte: sem fonte, escolha outro recorte.
2. **Dados do mapa** (`tools/mapa.py`, domínio público — ver `references/receitas.md` §1). Baixa na hora do uso; nada vem pronto além do exemplo:
   ```
   <PYTHON> -I tools/mapa.py baixar fontes --bbox=<l0,b0,l1,b1 do continente> --ppd 16 --nome base
   <PYTHON> -I tools/mapa.py baixar fontes --bbox=<caixa do país>  --ppd 64  --nome pais
   <PYTHON> -I tools/mapa.py baixar fontes --bbox=<caixa da região final> --ppd 160 --nome reg
   <PYTHON> -I tools/mapa.py texturas fontes base videos/<nn-nome>/img --borda 0
   <PYTHON> -I tools/mapa.py texturas fontes pais videos/<nn-nome>/img --relevo
   <PYTHON> -I tools/mapa.py texturas fontes reg  videos/<nn-nome>/img --relevo
   <PYTHON> -I tools/mapa.py vetores  fontes <País em inglês> videos/<nn-nome>/geo.json --bbox=<caixa do país>
   ```
3. **Retrato** — foto livre (CC0/PD/CC BY/BY-SA) do Commons: `<PYTHON> tools/commons.py buscar <termo>` → `baixar <n> <destino>` → `pb <entrada> <saida>` (P&B quadrada, ~560 px) → `creditos videos/<nn>/img` para a linha do rodapé. Só figura histórica com foto em domínio público; nunca pessoa viva da referência.
4. **Montar** — `cp -R videos/exemplo-cafe videos/<nn-nome>`; troque câmera, manchas, etiquetas e anotações mantendo a gramática (`references/estilo.md`, API em `references/receitas.md`).
5. **Preview** — `python3 tools/renderizar.py <nn> --at=0.4,1.3,2.2,2.9,3.4,4.3,5.2,7.8` → `previews/<nn-nome>.jpg`. Confira: nada cortado na borda, rótulo fora do círculo tracejado, triângulo sem cobrir o alvo da chamada.
6. **Som e render** — `python3 tools/renderizar.py <nn> --at=1` (grava cues) → `<PYTHON> audio/synth.py <nn>` → `python3 tools/renderizar.py <nn>` → `out/<nn-nome>.mp4` (ver `references/audio.md`).
7. **Conferir** — `ffprobe` (1080×1920, duração, áudio) e uma folha de 8 qps; créditos no rodapé (`.md-cred`).

## Regras do motor

- Tudo é função do tempo: estado do mapa e peças são calculados no `onTick` (o render pula para qualquer `t`). Nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` — use `K.rng` / `MD.pisca`.
- O mapa é **um canvas redesenhado a cada quadro** (`M.desenhar(t)`); as anotações são DOM presas a lon/lat (`MD.tick(t)`). Chame os dois no mesmo `onTick`, nessa ordem.
- `MD.mapa` é assíncrono (carrega `geo.json` e texturas): crie tudo dentro de `window.SETUP = async () => {…}`.
- Projeção equirretangular com `lat0` no meio do país (`x = lon·cos(lat0)`). Para países longe do equador (> 45°) a deformação aparece; aceite ou escolha `lat0` no centro da região final.
- Texturas: a fina (`--ppd 160`) só na região do mergulho final; a grossa embaixo cobre o resto. A ordem em `tex:[…]` é de baixo para cima.
- Camada vermelha: as texturas são desenhadas primeiro e recortadas pela máscara desfocada (`destination-in`). Nunca troque por `source-in` — ele apaga tudo fora de cada textura.
- Chamadas e rótulos: largura máxima ≈ 440 px; deixe ≥ 40 px de margem lateral. Não ponha `escala` nas chamadas (o empurrão as joga para fora da tela); triângulo, retrato e círculo podem crescer com `escala: () => M.cam.z / zFinal`.
- O 9:16 é recomposição, não corte: a coluna vertical acompanha o "caminho" (norte → sul, origem → destino), os rótulos usam a altura extra acima e abaixo da região.
- **Estilo fechado.** O verde-esmeralda, o vermelho e o papel quadriculado são a identidade do formato: não troque por tokens de `da/da.json`. A direção de arte do projeto entra no uso do clipe (moldura, carimbo, conferência final).

## Armadilhas conhecidas

- **Mapa cinza e sem brilho:** a textura `_verde` só acende se o `geo.json` do país vier junto; sem ele o país não é recortado.
- **Rótulo em cima do triângulo:** o triângulo cresce com a câmera e cobre o alvo da chamada — ancore a chamada do lado oposto ao mergulho.
- **Textura fina pesada:** `--ppd 160` numa caixa grande gera um arquivo de centenas de MB; use a caixa da região final, não a do país.
- **Nomes e datas:** o rótulo que "decodifica" chama atenção; qualquer afirmação histórica ali precisa de fonte.

## Arquivos

- `assets/projeto/lib/mapadoc.js` — a biblioteca do estilo (global `MD`; API em `references/receitas.md`).
- `assets/projeto/videos/exemplo-cafe/` — o demo completo (página, `geo.json`, texturas, créditos).
- `assets/projeto/audio/synth.py` — trilha `documental` + efeitos `flicker` e `decode`.
- `scripts/mapa.py` — baixa relevo (NASA GIBS) e vetores (Natural Earth), tinge as texturas e extrai estados/rios.
- `scripts/commons.py` — busca, baixa e credita foto livre do Wikimedia Commons, e converte em retrato P&B.
- `references/estilo.md` · `movimento.md` · `receitas.md` · `audio.md`.
- `scripts/projeto.py` · `scripts/renderizar.py` · `scripts/comum.py` · `scripts/analisar.py` (ler referências).
