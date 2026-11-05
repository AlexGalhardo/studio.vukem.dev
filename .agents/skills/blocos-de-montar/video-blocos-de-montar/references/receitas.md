# lib/blocos.js — API e receitas

`import * as B from '../../lib/blocos.js'` dentro de `<script type="module">`; monte tudo em `window.SETUP = async () => {…}`. Unidade: 1 = passo de pino; tijolo = 1,2 de altura (`B.H_TIJOLO`), placa = 0,4 (`B.H_PLACA`). Topo da placa-base em y = 0.

## Palco e cenário

| função | o que faz |
|---|---|
| `B.palco({fov, sol:{dir, forca}, hemi, ambiente, ao:{raio, forca}, raioSombra, centroSombra})` | renderer + IBL + sol com sombra + GTAO + acabamento. Devolve `S` (`scene`, `camera`, `mats{abs,vidro,luz,borracha,metal}`, `rig{}`, `cada(fn)`, `update(t)`, `hud[]`, `sombra(c, r)`). |
| `B.cidade(S, {rua:{z, largura}, ruas:[{z, largura}], seed, nevoa:[perto, longe] (padrão 140–600), predios:{z0, n}, cores:{chao, asfalto, predios:[…]}, transversal, transversalX, semPostes, livre})` | chão, ruas com faixas e calçadas, rua transversal, postes, prédios pastel dessaturados com janelinhas e caixas-d'água, céu em gradiente, nuvens em blocos, névoa. `cores` sobrepõe `CENA`. |
| `B.placaBase(S, {w, d, x, z, cor, escala})` | placa verde w×d pinos com todos os pinos (instanciados); `escala` = passo do pino (use a mesma das peças: w·escala é o tamanho no mundo). |

## Peças e modelos

| função | o que faz |
|---|---|
| `B.geoPeca(tipo)` | geometria (com cache): `tijolo-MxN`, `placa-MxN`, `liso-MxN` (sem pino), `redondo-NxN`, `botao-NxN` (placa redonda), `telha-1xN` (rampa que desce para +x), `pneu-1xR`, `aro-1xR`. M = largura (z), N = comprimento (x). Origem no centro da base. |
| `B.peca({tipo, cor, fam, pos, rot:[x,y,z] \| rotY, grupo, rig, chave, obj, tam, esc})` | uma peça avulsa (`obj` = qualquer Object3D voando como peça). `esc` = escala da peça (número ou `[sx,sy,sz]`, ex. pupila achatada). |
| `B.modelo({dim:[X,Y,Z], forma, cores, alturas, origem, oco, grupo, rig, max, escala})` | grade de voxels → lista de peças 1x1…1x`max` (padrão 4; a demo usa 2). `escala: 1/1.4` = grade e peças 1,4× menores (posições em `origem + índice·escala`). `cores[chave]` = `'#hex'` ou `{cor, fam, tipo}`. `oco:true` só gera a casca visível (vidro conta como vazio). |
| `B.camadas([texto por camada], legenda)` | `{dim, forma}` a partir de camadas desenhadas em texto (linha = z, caractere = x, `.` = vazio). |
| `B.roda(pos, lado, {raio, aro, cor, rig, grupo, esc})` | pneu + aro (2 peças); `lado` +1 calota para +z, −1 para −z. A demo usa `raio` 3,1 e `aro` 1,85 (pneu aparecendo sob a saia). |
| `B.boneco(S, {nome, pos, rotY, pele, camisa, colete, calca, botina, capacete, bigode, fn})` | bonequinho de tijolos (não é a minifigura oficial) com rigs `nome`, `nome.cabeca`, `nome.bracoE`, `nome.bracoD`. |
| `B.adesivo(w, h, draw(ctx, W, H), {res, verso})` | decalque impresso em canvas (face +z, verso de papel). Canvas com altura `res·h/w`: desenhe a última linha em `H − 22`. |
| `B.colar(S, obj, {rig, pos, rot, entra, dur, sai, flash})` | cola o objeto NO LUGAR (escala 0→1 com sobra + flash emissivo em `entra`, descola em `sai`). Para decalques/letreiros na face externa; chame depois de `instanciar()`. |
| `B.brilho(cor, tam)` | sprite aditivo para faróis/lâmpadas (`.material.opacity` por quadro). |

## Rigs (articulações)

`B.rig(S, nome, {pai, pos, rot, pivo, fn: t => ({pos:[…], rot:[…]})})` — peças com `rig: nome` seguem a matriz `pai · T(pos) · T(pivo) · R(rot) · T(−pivo)`. Defina os pais antes dos filhos. A demo usa `onibus` (rodas) → `carroceria` (suspensão, tremor); o bonequinho anima `S.rig['ze.bracoD'].fn`.

## Linha do tempo

| função | o que faz |
|---|---|
| `B.programar(pecas, {grupos:{nome:[t0,t1]}, voo:[min,max], desmonta:[t0,t1], vooVolta:[min,max], seed, mistura})` | janelas de partida por subconjunto (dentro de cada uma, de baixo para cima com camadas misturadas) e desmontagem na ordem inversa exata. Devolve `{total, fimMontagem, fimDesmontagem}` (os fins são calculados na hora). |
| `B.montes(pecas, [{x, z, chaves, resto, pilha, passo, rot, y0, raio, altura, sobra}], {seed, sobra, voo, vooVolta})` | casa de cada peça no monte mais próximo que aceita a chave (raio do monte pela escala das peças); ordem de saída do topo; com `voo`/`vooVolta` a duração passa a ser proporcional à distância (fita contínua). Devolve as peças extras (que nunca saem). |
| `B.instanciar(S, todas, {centro, seed, quique, variacao, arco})` | cria as InstancedMesh e registra a animação de todas as peças (montes, voo, encaixe, estouro, volta). `arco` (padrão .7) × distância horizontal = altura do arco de ida. |
| `B.contar(pecas)` | `t => n`: sobe no encaixe e desce no POUSO no monte (chega a 0 com a nuvem já no chão). |
| `B.sons(S, pecas, B.projetor(S, cam))` | cues `sai`/`clique`/`solta`/`cai` por peça, com pan de tela. Outros: `cue('motor', t, {dur})`, `cue('buzina', t)`, `cue('farol', t)`, `cue('whoosh', t, {dur, g})`. |
| `B.orbita(S, {alvo, raio:[longe, perto], azim:[centro, amp, fase], elev:[centro, amp], fov, perto, T})` | câmera em balanço periódico (loop); `perto` = instante mais próximo. |
| `B.rotulo(S, {x, y, linha, total, contador, estado: t => [texto, cor], cor})` | HUD discreto com contador. |
| utilidades | `B.rng(seed)`, `clamp`, `lerp`, `suave`, `fase(t,a,b)`, `janela(t,a,b,c,d)`, `COR`, `CENA`. |

## Esqueleto mínimo

```js
const S = B.palco({ fov: 46 }), s = 1 / 1.4;                         // peças 1,4× menores que o pino da placa
B.cidade(S, { rua: { z: 56, largura: 24 }, ruas: [{ z: -62, largura: 22 }], nevoa: [140, 600], predios: { z0: 90, n: 90 } });
B.placaBase(S, { w: 124, d: 124, z: -6, escala: s });
B.rig(S, 'obj', {});
const pecas = B.modelo({ dim: [X, Y, Z], forma, cores, origem: [-(X - 1) / 2 * s, 0, -(Z - 1) / 2 * s], grupo, rig: 'obj', max: 2, escala: s });
const prog = B.programar(pecas, { grupos: { base: [0, .4], corpo: [.35, 1.5], topo: [1.4, 1.76] }, voo: [.55, .72], desmonta: [3.7, 4.3], vooVolta: [.38, .5] });
const extras = B.montes(pecas, [{ x: 23, z: 22, chaves: ['vermelho'] }, { x: -11, z: -32, chaves: ['vermelho'] }, { x: -26, z: -23, chaves: ['branco'] }, { x: -37, z: -11, resto: true }],
  { sobra: .08, voo: [.55, .72], vooVolta: [.38, .5] });
B.instanciar(S, [...pecas, ...extras], { arco: .7 });
const cam = B.orbita(S, { alvo: [5, 7.5, 1], raio: [121, 82], azim: [48, 12, -2.33], elev: [26, -4], fov: 44, perto: 3.1 });
B.sons(S, pecas, B.projetor(S, cam));
S.update = t => cam(t);
B.rotulo(S, { x: 48, y: 260, linha: 'Nº 02 · Nome', total: prog.total, contador: B.contar(pecas), estado: t => ['montando', '#2f7fd0'] });
```

## Receitas

- **Carro de corrida (como a referência).** Carroceria vermelha baixa: `pegada` de cunha (largura cresce de trás para a frente), listras brancas por `z` no centro (`Math.abs(z - Z/2 + .5) < 2 → 'branco'`), número em `adesivo()` redondo nas portas e no capô, aerofólio = 2 colunas `redondo-1x1` pretas + `placa-1xN` vermelha/branca. Subconjuntos: chassi grafite/preto → rodas → bancos bege → carroceria → listras → vidros → aerofólio.
- **Caminhão, van, trator.** Igual ao ônibus: sólido com planta arredondada + casca, para-lamas com `arco()`, rodas maiores (`roda(pos, lado, {raio: 3.4, aro: 2})`); carga como peças avulsas num rig próprio.
- **Casa / prédio.** `alturas` de tijolo nas paredes e uma camada de `placa` no topo; janelas `'vidro'`; telhado em `telha-1x2` com `rotY` (a rampa desce para +x; gire 90°/180° para as outras águas).
- **Modelo pequeno desenhado à mão** (troféu, logotipo fictício, mascote): `B.modelo({ ...B.camadas([camada0, camada1, …], { R: 'vermelho', W: 'branco' }), origem, oco: false })`.
- **Só montar (sem desmontar).** `desmonta: [dur + 1, dur + 2]` e termine com o objeto pronto; o loop deixa de ser perfeito — use um corte.
- **Sair andando no fim (como a referência).** Rig raiz com `fn: t => ({ pos: [andou(t), 0, 0] })` e um rig por roda com `pivo` no centro dela e `rot: [0, 0, -andou(t) / 2.6]`; deixe a desmontagem de fora ou faça-a depois que voltar.
- **Mais peças / mais fino.** Diminua `escala` (peças e placa) e aumente a grade na mesma proporção; descreva a forma em unidades do mundo para o desenho acompanhar. Medido: 2.430 peças + ~190 extras nos montes + 15 mil pinos da placa → ~0,09 s/quadro (14 s para 150 quadros 1080×1920).
- **Física de desmoronar** não está na biblioteca: a desmontagem é um estouro em curva de Bézier determinístico. Para "desabar", troque o ramo de volta em `instanciar()` por queda balística com quique no chão (sempre função de `t`).
