# Receitas: API de `lib/floresta.js`

```html
<script>VIDEO={w:1080,h:1920,fps:30,dur:8,bpm:72,music:{style:'noturno',key:'D',gain:-3}}</script>
<script>LIBS=[]</script>
<script src="../../lib/boot.js"></script>
<div id="stage"></div>
<script type="module">
import * as FL from '../../lib/floresta.js';
const { THREE, PAL, lerp, suave, prog, io } = FL;
const S = FL.palco({ fov: 32, cam: [0, 3.7, 11], alvo: [0, .5, -1.2] });
// … cenário …
FL.calibrar(S);
S.update = (t) => { /* t já vem em degraus de 0,1 s */ };
window.SETUP = () => { /* texto, cues */ };
</script>
```

## Palco e utilidades

| função | o que faz |
|---|---|
| `palco({fov, cam, alvo, fundo, bloom:{forca,raio,limiar}, vinheta, fps})` | renderer sem tone mapping, MSAA, bloom e acabamento; chama `S.update(tq, t)` com `tq = degrau(t, fps=10)` |
| `calibrar(S)` | fixa a profundidade de referência do traço de cada malha (chame depois de montar a cena) |
| `degrau(t, fps)` · `prog(t,a,b)` · `suave(a,b,v)` · `io(k)` · `lerp` · `clamp` | tempo e easing |
| `rng(semente)` · `ruido(x,y)` | aleatório determinístico e ruído suave [-1,1] |
| `PAL` | paleta do estilo (ver `estilo.md`) |
| `U` | uniforms globais: `tempo`, `sol` (direção da lua), `aneis` |

## Material de lápis

```js
const mat = FL.lapis({ cor: '#8a5432', cor2: '#a86a42', px: 4.4, comp: 16, amb: .42, dif: .75 });
```

| opção | padrão | efeito |
|---|---|---|
| `cor` / `cor2` | madeira | traço principal / realce (2ª camada girada) |
| `papel` | `#0e0a06` | cor entre os traços |
| `px` | 4,4 | espaço entre fileiras, em pixels na profundidade `prof` |
| `prof` | 0 (auto) | profundidade de referência; dê um valor fixo para objetos que andam |
| `comp`, `larg`, `dens` | 14, 1, 1 | comprimento (em fileiras), largura e densidade do traço |
| `amb`, `dif`, `brilho` | .42, .75, 1 | luz ambiente, luz da lua, multiplicador (use `brilho` para tirar da sombra) |
| `var` | .45 | quanto o tom varia de face para face |
| `vel` | 0 | riscos deslizando (água) em u/s |
| `alfa` | 1 | <1 = vãos translúcidos (vidro d'água) |
| `manchas:[tipo, célula, raio, barriga]` | — | 1 = rosetas quebradas, 2 = pintas cheias; barriga 1 clareia faces para baixo com `ventre` |
| `fundo:{y, cor}` | — | abaixo de `y` (mundo) troca para `cor` (leito sob a água) |
| `grad:[y0,y1,k0,k1]` | — | gradiente vertical de luz (céu) |
| `lustro` | 0 | brilho ondulado dentro das facetas (água) |
| `aneis` | false | desenha as ondas quadradas de `FL.anel` |

`FL.aguaMat(o)` = `lapis` emissivo com as cores da água, `vel` .35, lustro e anéis ligados.

## Geometria facetada

```js
const g = FL.facetar(FL.loft(secoes, { forma: FL.FORMA.caixa, dir: [1, 0, 0] }), { eixo: [1, 0, 0], jit: .5, semente: 3 });
FL.malha(g, FL.lapis({...}), grupo);
```

- `loft(secoes, {forma, cima, dir, tampas})`: une seções `{p:[x,y,z], w, h}` ao longo de um caminho. `FORMA.caixa` (chanfrada, corpo), `hex`, `pent`, `losango`.
- `tris([[a,b,c], …])`: geometria de triângulos soltos (orelhas, folhas).
- `facetar(geo, {eixo, jit, semente, porTriangulo, eixoFn})`: obrigatório antes do material — dá a cada face plana a direção do traço (eixo projetado + giro aleatório ±jit/2) e um tom.
- `transformar(geo, M4(pos, rot, esc))`: aplica matriz a geometria já facetada (gira também a direção do traço). `unir([...])` junta várias.
- `pedraGeo({r, achatar, semente})`.

## Cenário

```js
FL.ceu(S); FL.estrelas(S, { n: 150, x: [-9, 9], y: [-3, 9], tam: [4, 8] });
FL.paredao(S, { x: [-14, 14], z: -15, base: -.5, topo: x => .55 + .45 * FL.ruido(x * .35, 4), n: 16, linhas: 2, mat: { cor: '#2c3a3c' } });  // serra
FL.paredao(S, { x: [-9, 9], z: -7.6, base: -.6, topo: x => (Math.abs(x - CX) < .7 ? .85 : 1.1) });                                          // paredão com entalhe
FL.cachoeira(S, { x: CX, z: -7.45, y0: -.05, y1: .9, larg: 1.15 });
const { altura, margem } = FL.relevoRio({ centro: z => …, largura: z => …, poco: x => 1.3, fundo: -1.8 });
const TER = FL.terreno(S, { x: [-7, 7], z: [-7.6, 2.6], nx: 22, nz: 14, altura, fundo: { y: -.08, cor: '#323c38' }, base: -4.5 });
FL.rio(S, { x: [-4, 4], z: [-7.5, 2.6], nx: 6, nz: 10 });
FL.vidroAgua(S, TER.perfil);
FL.arvore(S, { x: -1.85, z: -1.9, alt: 3.2, raio: 1.5, inclina: .2, galhos: [[-1, .6], [1, .74]] });
FL.roseta(S, { x: 1.55, y: .14, z: -1.2, n: 9, aneis: 3, comp: .8 });
FL.capim(S, { x: 1.75, y: -2.55, z: 3.4, n: 8, alt: 1.5 });
FL.pedra(S, { x: -1.55, y: .02, z: .55, r: .34, achatar: .35 });
const p = FL.peixe(S, { x: -.7, y: -.55, z: 1.9, rot: .2, tam: 1.25, semente: 1 });   // no update: FL.nadar(p, t)
```

- **Rio = terreno que afunda.** A água (`rio`) é um plano em y=0 do tamanho da cena; só aparece onde o terreno está abaixo de 0. Desenhe o curso pelo `relevoRio`.
- **Corte de aquário.** O terreno termina em `z1` com uma parede (`base`); `vidroAgua(S, TER.perfil)` fecha a frente da água com um vidro quase invisível. Ponha peixes e seixos entre o poço e o corte.
- **Paredão com entalhe:** baixe `topo` onde passa a cachoeira, e ponha a cachoeira 0,15 à frente da parede.

## O bicho (`FL.onca`)

```js
const O = FL.onca(S, { prof: 10, escala: 1.25 });
O.g.position.set(x, margem(x, z) + .02, z); O.g.rotation.y = rumo;      // rumo = atan2(-dz, dx)
O.pose({ t, passo, andar, agachar, pescoco, cabecaX, cabecaY, piscar, luz, brilhoOlho });
O.P.cabeca.localToWorld(boca.set(.44, -.11, 0));  // ponto do focinho (para os anéis)
```

| chave | faixa | efeito |
|---|---|---|
| `passo` | ciclos | fase da caminhada |
| `andar` | 0–1 | amplitude da caminhada |
| `agachar` | 0–1 | inclina para a frente e abre as patas dianteiras (beber) |
| `pescoco`, `cabecaX` | rad | abaixa/ergue (negativo = abaixa) |
| `cabecaY` | rad | gira a cabeça (positivo = para o lado −z local; confira no preview) |
| `piscar` | 0–1 | fecha os olhos |
| `luz` | .1–1 | sai da sombra |
| `brilhoOlho` | 0–1 | olhos refletindo no escuro (bloom) |

**Outro bicho:** copie `onca()` e troque as seções do corpo/cabeça (anta: focinho longo e corpo mais alto; capivara: corpo-barril, patas curtas, sem cauda; lobo-guará: patas longas e finas), cores e `manchas` (0 = sem pintas). Mantenha `dir: [1,0,0]` nos lofts de cabeça e corpo.

## Água e anéis

```js
FL.anel(k, x, z, t0, força);   // k = 0..3; dispare no instante em que o focinho toca a água
```

## Texto a lápis

```js
window.SETUP = () => {
  TIT = FL.textoLapis({ texto: 'onça-pintada', fonte: '600 138px Fraunces', x: 540, y: 300, w: 1040, h: 230, cor: PAL.creme, esp: 3.4 });
  SUB = FL.textoLapis({ texto: 'o maior felino das Américas', fonte: '500 60px Fraunces', x: 540, y: 428, w: 1000, h: 120, cor: PAL.azulTexto, esp: 2.6, larg: 1.6, comp: [8, 20], base: .75 });
};
// no update: TIT.desenhar(Math.floor(prog(t, 1.75, 2.75) * 10) / 10)
```

Opções: `esp` (espaço entre riscos), `larg`, `comp:[min,max]`, `ang` (−.42 rad), `base` (opacidade da base escura que dá corpo à letra), `sombra` (cor ou `false`). Títulos longos: diminua a fonte até caber em ~960 px.
