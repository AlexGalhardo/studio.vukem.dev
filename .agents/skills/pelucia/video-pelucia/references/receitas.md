# Receitas — API de `lib/pelucia.js`

```js
import * as PL from '../../lib/pelucia.js';
const { THREE, PAL, lerp, clamp, onda, chaves, fase } = PL;
```

## Palco, câmera, sombra

| função | o que faz |
|---|---|
| `PL.palco({fov, dof:{abertura,max}, grao, vinheta, fundo:[cores], luzFundo, luz:{key,rim,keyForca,rimForca,ceu,chao,amb}, ambiente})` | renderer + estúdio creme + luzes (compartilhadas com o pelo) + DOF suave (fundo não desfoca) + acabamento. Devolve `S` (`S.update`, `S.antes`, `S.hud`, `S.scene`, `S.camera`). |
| `PL.derivaCamera(S, {alvo, dist, elev, az, giro, alt, periodo, fov, foco})` | devolve `fn(t)`: órbita leve e periódica + foco no alvo. Chame no `S.update`. |
| `PL.sombraChao(S, {y, dir, centro:[x,z], tam, res, desfoque, passes, cor, opac})` | sombra enorme e desfocada no chão (silhuetas vistas da luz). `dir` = de onde vem a luz. |
| `PL.fundoEstudio(cores, luz)` | textura de fundo (já usada pelo palco). |

## Materiais e peças

| função | o que faz |
|---|---|
| `PL.materialPelo({cor, ventre:{cor,eixo,lim,suave}, pontas, comp, dens, fio, pente, dobra, grav, redemoinho, veludo, brilho, ao, var, manchas, nap, tufo, tufoFreq, semente, camadas})` | ShaderMaterial do pelo por cascas. |
| `PL.pelucia(geo, opçõesDoPelo)` | Group = base + cascas instanciadas. **Geometria em unidades finais.** |
| `PL.torno(perfil[[r,y]...], {seg, fi0, fi})` | sólido de revolução suavizado (corpo, pão, carne, copo, avental). |
| `PL.esfera(r, [sx,sy,sz], {te, fi...})`, `PL.capsula(r, comp)`, `PL.caixaMacia(w,h,d,raio)` | geometrias macias. |
| `PL.amassar(geo, amp, semente)` | amassado suave pela normal (copa de boné, tecido enchido). |
| `PL.feltro(cor, {map, bump, sheen, opac, lados, unico})` | feltro fosco com fibras (cache por cor). |
| `PL.plastico(cor, {rug, verniz, reflexo})` | plástico brilhante. |
| `PL.botao(r)` | olho de botão (aponta para +z). |
| `PL.costura(curvaOuPontos, {passo, raio, cor, cheio})` | pontinhos de linha. |
| `PL.naSuperficie(c, r, esc, lat, lon)` / `PL.colar(obj, c, r, esc, lat, lon, saliencia)` | posiciona detalhes na superfície de um elipsoide olhando para fora. |
| `PL.etiqueta(desenhar(g,w,h), w, h, fundo)` | CanvasTexture para letras e estampas. |
| `PL.logoMarca({nome, sub, acento})` / `PL.remendo(r, {...})` | marca fictícia em remendo redondo de feltro costurado. |

## Boneco de pelúcia

```js
const ze = PL.boneco({ pele: PAL.pele[0], cabelo: PAL.cabelo[0], cabeloTipo: 'curto'|'coque'|'black'|'nenhum',
  camisa: PAL.porDoSol, calca: PAL.carvao, sapato, avental: PAL.bronze, chapeu: 'bone'|'viseira'|null, corChapeu: PAL.laguna,
  corMarca, cracha: 'ZÉ', crachaLado: 1|-1, bigode: '#1a1310', boca: 'costura'|'aberta', bochechas: true, aroOlho, pelo: {comp, dens}, semente: 11 });
cena.add(ze.raiz);                         // posicione/gire a raiz
ze.balancar(t, { periodo: 2.5, desloc: 0, amp: 1 });   // flutua, balança, enche/esvazia, cabeça e pernas
ze.bracos({ e: [x, y, z], d: [x, y, z] });  // x<0 levanta p/ frente; z>0 abre o esquerdo (+x local), z<0 abre o direito
ze.maoE / ze.maoD                            // grupos das mãos: pendure objetos (espátula etc.)
```
O boneco olha para +z; ~1,8 unid. de altura (sapato −0,58 → topo do boné ~1,25). E = esquerda DO boneco (+x local).

## Comidas e objetos

`PL.hamburguer({raio, pao, semente})` · `PL.carne({raio})` · `PL.batata({cor})` · `PL.refri({cor, faixa, texto:'GUARANÁ', canudo})` · `PL.bandeja({cor, semente})` (pedido completo; `userData.itens`) · `PL.sacola({cor, larg, alt, prof})` (aberta; `userData.boca` = centro da abertura) · `PL.chapa({larg, prof, cor})` · `PL.espatula()` (cresce para +z) · `PL.fumaca({n, periodo, alt})` → `{grupo, update(t)}`.

## HUD editorial

```js
PL.cabecalhoEditorial(S, { rotulo: 'Estudos de material &nbsp;|&nbsp; Nº 028', titulo: ['Equipe', 'Pelúcia.'], texto: ['linha 1', 'linha 2', 'linha 3'], selo: 'WebGL · ao vivo' });
PL.painel(S, { titulo: 'O turno', fig: 'fig. 28', top: 1300, pelos: [{ nome: 'Bronze', cor: PAL.bronze }, ...], pelo: 2,
  sliders: [{ nome: 'Enchimento', valor: t => '0,55', k: t => .55, min: 'frouxo', max: 'firme' }, ...],
  acoes: ['Chapa', 'Caixa', 'Entrega', 'Montar', 'Pentear pelo', 'Pausa'], ativa: t => índice, checks: [['Ciclo', true], ['¼ veloc.', false]] });
PL.rodape(S, { dica: t => ['CHAPA', 'texto itálico'], dados: [{ r: 'Pedidos', v: t => '214' }, { r: 'Tempo', v: '3', u: 'min' }], nota: 'Escala ilustrativa: ...' });
```
`valor`, `k`, `v`, `dica` e `ativa` aceitam função de `t` (o HUD vive junto com a cena).

## Receitas

**Passar um objeto de mão em mão em loop.** Âncoras (`Object3D`) presas ao `corpo` de cada personagem; a viagem completa dura 2D e duas cópias andam defasadas em D: `pos(b0, (t + D) % (2*D)); pos(b1, t % (2*D))`. Em cada trecho: segurando (= posição da âncora) → indo (Bézier `bez(A, B, k, off)` com `off` que desvia das cabeças) → guardando (afunda na sacola, cujas paredes escondem). Braços seguem com `chaves(t, [[t0, pose], ...], {per: D})`. Ver `posBandeja` no exemplo.

**Bicho de pelúcia (ex.: o tubarão-martelo da referência).** Corpo = `PL.torno` com perfil fusiforme deitado (`geo.rotateZ(Math.PI/2)`), martelo = `PL.esfera(.12, [3.2, .45, .9])`, nadadeiras = `PL.caixaMacia` afinadas (escale vértices); cada peça com `PL.pelucia(geo, { cor: PAL.bronze, ventre: { cor: PAL.bronzeVentre, eixo: [0,-1,0] }, pente: [-1, 0, 0] })` (pelo deitado para a cauda). Olhos `PL.botao` nas pontas do martelo, boca de feltro vermelho com dentinhos de feltro creme. Nado em S: divida o corpo em 3–4 segmentos encadeados e gire cada um com `onda(t, P, -i*.12)` em y, com amplitude crescendo para a cauda; a raiz percorre um 8/círculo lento.

**Trocar a pelagem (amostras Bronze/Laguna/Pôr do sol).** `m.uniforms.uCor.value.set(cor)` no material do pelo (cada `pelucia` tem o seu em `grupo.userData.pelo`); sincronize com `pelo`/`ativa` do painel.

**Pentear o pelo** (como a ferramenta "Comb" da referência): anime `uPente` e `uDobra` (pelo deita e muda de brilho) e `uNap` (claro/escuro conforme a direção).

**Mais lento/rápido:** `balancar({periodo})` — use 2,5 s para 5 s de vídeo (ou D/3, D/4) para manter o loop.

## Som (`audio/synth.py`)

Circular (caudas voltam ao começo), ~−16 LUFS. Cues: `m:loop` (caixinha de música F maj7 → B♭maj7, 96 bpm, bumbo de feltro, escovinha), `vira`, `pof`, `fofo` (passagem), `sacola`, `sino` (campainha de balcão), `clique` (botão do painel), `pop`, `chiado` (chapa, `d`). Opções `gain` (dB) e `pan`.
