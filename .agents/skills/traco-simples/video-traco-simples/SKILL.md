---
name: video-traco-simples
description: Cria animações 2D curtas no estilo "traço simples" — formas chapadas de papel recortado (sem contorno, sombra ou gradiente), bordas que "fervem" a 12 qps e paleta curta e saturada. Cada objeto pula para dentro, faz um gesto em stop-motion e sai em chicote enquanto o fundo troca seco; tem estouro de estrelas, campo de ícones com zoom, mascote que pisca e wordmark digitado. Tudo desenhado em SVG por código com uma biblioteca de primitivas e ícones, renderizado em mp4 9:16 (ou 1:1 / 16:9) com trilha e efeitos sintetizados; também lê um vídeo de referência (folha de contato e paleta). Use sempre que o usuário pedir animação de traço simples, ilustração flat ou chapada, recorte de papel, cartoon simples, ícones animados, motion 2D colorido, explainer divertido, vinheta com mascote ou reels/shorts com bichos, objetos ou personagens desenhados, e quando mandar uma referência nesse visual pedindo algo "nesse estilo, traço e movimento", mesmo sem dizer "traço simples".
---

# Animação em traço simples

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


O estilo junta três coisas:

- **Formas:** grandes, chapadas e simples, recortadas à mão. A borda treme a 12 qps ("boil").
- **Movimento:** objetos que **pulam** para dentro (elástico), fazem **um gesto** característico em stop-motion e saem num **chicote**, com o fundo trocando seco.
- **Cor:** paleta curta e saturada, com um objeto por vez sobre fundo liso.

Veja `assets/exemplo.mp4` (15 s, "Raças de cachorro") para calibrar o olhar. O código dele está em `assets/projeto/videos/exemplo-cachorros/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar o projeto (uma vez por pasta)

```bash
bash <caminho-da-skill>/scripts/setup.sh <pasta-do-projeto>
```

O script copia o motor (`render.mjs`, `dbg.mjs`, `lib/` com `traco.js`, `audio/synth.py`), instala gsap e playwright, cria o venv Python com numpy, scipy e pillow, e copia `tools/referencia.py`.

- **Requisitos:** Node 18+, ffmpeg e python3. No macOS o encode usa VideoToolbox; nos outros sistemas, libx264.
- **Onde rodar:** todos os comandos abaixo rodam **da raiz do projeto**.

## Fluxo

### 1. Se houver referência, leia antes

```bash
audio/.venv/bin/python tools/referencia.py <video.mp4> previews/ref --em 0.7,3.2
```

Isso gera folhas de contato a 8 qps (4 s por folha) e quadros-chave, e lista a paleta dominante em hex. **Abra as folhas** e anote:

- a sequência de cenas e a duração de cada uma;
- como cada objeto entra, o que ele faz e como sai;
- quando o fundo troca;
- o que acontece no final.

Copie **estilo e movimento**, não o conteúdo. Ajuste a paleta com `TR.usarPaleta({...})` usando as cores listadas.

### 2. Roteiro

Escreva a tabela `T` de tempos antes de desenhar. O roteiro-tipo de 15 s e as versões de 5 e 8 s estão em `references/movimento.md`. Para cada objeto, decida três coisas:

- **o que é:** uma forma reconhecível em 2 a 6 peças;
- **o gesto:** o que ele faz de característico (rebolar, esticar, piscar, brotar pintas, pular);
- **o rótulo:** uma palavra.

Distribua as cores de fundo para nunca repetir em cenas seguidas e nunca coincidir com a cor do objeto.

### 3. Desenhar

```bash
cp -R videos/exemplo-cachorros videos/<nn-nome>
```

1. Desenhe cada objeto novo primeiro em `videos/folha-de-desenho/index.html` (o objeto `RECEITAS`).
2. Confira parado com `node render.mjs folha --at=0.5`.
3. Corrija a forma até ler bem a ~40% do tamanho. Só então leve o desenho para o vídeo.

Leia `references/desenho.md` para a API (`blob`, `poly`, `star`, `caixa`, `gota`, `line`, `olho`, `TR.IC`) e para as receitas de cabeça de frente, perfil, costas, corpo que estica, pernas, objetos e mascote. As regras de cor, forma e composição estão em `references/estilo.md`.

### 4. Animar

Leia `references/movimento.md` e use os valores de lá:

| movimento | valores |
|---|---|
| pop | `back.out(2.3)`, 0,3 s |
| chicote | 1400 px em 0,17 s, terminando no corte |
| gesto | `TR.q12` (12 qps) |
| sequências que brotam | a cada ~0,07 s |
| rótulo | 0,05 s por letra |

As peças de assinatura já estão prontas: `TR.estrelas`, `TR.campo`, `TR.confete`, `TR.tremer`, `TR.rotulo` e `TR.fundos`.

### 5. Preview e iteração

```bash
node render.mjs <nome> --preview=16                      # folha com 16 quadros → previews/<nome>.jpg
node render.mjs <nome> --at=0.7,2.4,5.5,7.6,12.6          # instantes específicos → previews/<nome>/NN.jpg
```

Para ver o **movimento**, renderize e monte uma folha a 8 qps de um trecho:

```bash
ffmpeg -ss 4.6 -t 5 -i out/<nome>.mp4 -vf "fps=8,scale=200:-1,tile=10x4" -frames:v 1 previews/mov.jpg
```

Confira:

- todo objeto lê como o que é;
- o objeto nunca tem a mesma cor do fundo;
- algo acontece a cada ≤ 0,3 s;
- o chicote é cortado no meio;
- o rótulo não colide com o objeto;
- o campo de ícones fica **lotado**;
- o último quadro parado está completo.

### 6. Som e render final

```bash
audio/.venv/bin/python audio/synth.py <nome>   # trilha + efeitos a partir de videos/<nome>/cues.json
node render.mjs <nome>                          # out/<nome>.mp4 (junta audio/<nome>.wav sozinho)
```

O `cues.json` é escrito a cada preview ou render, então rode um preview **antes** do synth. Os tipos de cue (pop, squeak, boing, bark, type, swoosh, boom, sparkle…), a trilha e como criar efeitos novos estão em `references/audio.md`.

Antes de entregar, extraia 2 ou 3 quadros do mp4 final e olhe.

## Regras do motor (o render pula para qualquer instante t)

- **Tudo é função do tempo.** Toda animação acontece em `onTick(t => ...)`, calculada a partir de `t` (ou na timeline `TL` do GSAP, pausada). Não use transição ou animação CSS, `setTimeout`, `requestAnimationFrame` nem `Math.random()`; use `K.rng(seed)`. Se não for assim, o quadro renderizado não bate com o instante.
- **Visibilidade:** ligue e desligue cada cena com `TR.show(grupo, TR.janela(t, a, b))` e só calcule o resto quando ela estiver visível.
- **Paleta:** `TR.usarPaleta()` só vale para o que for desenhado **depois** dela, então chame no topo do script.
- **Fontes locais** estão em `lib/fonts.css`: Anton, Bebas Neue, Rubik Mono One, Dela Gothic One, Permanent Marker, Unbounded e Inter Tight. Para outra fonte, baixe o woff2 em `lib/fonts/` e declare o `@font-face`. O render espera `document.fonts`.
- **Medidas de texto** (sublinhado, posição de confete) se fazem no `window.SETUP`, que roda depois das fontes carregarem. O exemplo mede o wordmark ali.
- **Para inspecionar um instante:** `node dbg.mjs <nome> 7.6 "document.getElementById('dhBody').getAttribute('d')"`.

## Formatos

O padrão é `VIDEO={w:1080,h:1920,fps:60,...}`. Para 1:1 ou 16:9, mude `w` e `h`, troque os centros fixos (540, 960) por `VIDEO.w/2` e `VIDEO.h/2` e recomponha o tamanho dos objetos (veja `references/estilo.md`). `TR.palco`, `TR.estrelas` e o rótulo já se adaptam ao tamanho.

## Arquivos

- `scripts/setup.sh`: cria ou completa um projeto.
- `scripts/referencia.py`: folhas de contato, quadros-chave e paleta de um vídeo de referência.
- `assets/projeto/lib/traco.js`: o kit do estilo (primitivas, movimento, palco, fervura, rótulos, estrelas, campo, confete, ícones).
- `assets/projeto/videos/exemplo-cachorros/`: o exemplo completo, comentado.
- `assets/projeto/videos/folha-de-desenho/`: receitas e ícones lado a lado, para testar desenhos parados.
- `assets/projeto/`: o motor (`render.mjs`, `dbg.mjs`, `lib/`, `audio/synth.py`, `audio/narrate.py`).
- `assets/exemplo.mp4`: o resultado de referência.
- `references/estilo.md`: paleta, forma, fervura, composição e tipografia.
- `references/movimento.md`: roteiro-tipo, vocabulário de movimento com valores e ritmo.
- `references/desenho.md`: API de desenho e receitas.
- `references/audio.md`: trilha, cues e efeitos novos.
