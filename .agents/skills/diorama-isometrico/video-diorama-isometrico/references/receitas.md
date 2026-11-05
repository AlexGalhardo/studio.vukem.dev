# Receitas: a API de `lib/diorama.js`

## Sumário
1. Esqueleto de página
2. Palco
3. Bloco de terreno, água, base, chão
4. Relevos (funções de altura)
5. Metamorfose
6. Mata, adereços, cabos
7. Material próprio
8. HUD
9. Receitas prontas (outros temas)

## 1. Esqueleto de página

```html
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<script>VIDEO={w:1080,h:1920,fps:30,dur:8,bpm:84,music:{style:'ambient',key:'D',gain:-4}}</script>
<script>LIBS=[]</script>
<script src="../../lib/boot.js"></script>
<style>#stage{background:#0a9d92;overflow:hidden}</style></head><body>
<div id="stage"><div class="di-hud"> <svg class="di-fios" id="fios" width="1080" height="1920"></svg> …título, etiquetas… </div></div>
<script type="module">
import * as DI from '../../lib/diorama.js';
const { THREE, clamp, lerp, suave, domo, smax, fbm, cristas, ruido, io, saida, backOut, prog } = DI;
DI.estiloHUD();
const S = DI.palco({ meia: 6.6, alvo: [0, 1.2, 0], elevacao: 35 });
// … terreno, base, chão, água, metamorfose …
S.update = t => { /* tudo que muda no 3D */ };
window.SETUP = async () => { /* TL do HUD + cue(...) */ };
</script></body></html>
```

## 2. Palco — `DI.palco(o)`

| opção | padrão | o que faz |
|---|---|---|
| `meia` | 6.85 | meia-largura visível em unidades (zoom) |
| `alvo` | [0,0,0] | ponto que a câmera olha; subir `y` desce o bloco na tela |
| `azimute`, `elevacao` | 45, 33 | ângulo da câmera (graus) |
| `sol` | [-.55,.68,1] | direção PARA a luz (sombra cai à direita) |
| `ss` | 2 | superamostragem (qualidade do nanquim) |
| `traco` | 1.3 | espessura do nanquim em px finais |
| `kDepth`, `kNormal` | .05, .32 | limiares do contorno (suba se riscar demais) |
| `grao` | .022 | grão do pós |

Devolve `S` com `scene`, `camera`, `S.add(...objs)` (liga sombra), `S.tela(x,y,z) → [px, py]` e `S.update = t => …`.

## 3. Bloco de terreno, água, base, chão

```js
const ter = DI.terreno(S, { lx: 10, lz: 8, nx: 200, nz: 160, fundo: 2.3 });   // ter.X, ter.Z, ter.H, ter.altura(x,z), ter.alturas(fn)
const B = DI.base(S, { lx: 10, lz: 8, fundo: 2.3, alt: 1.5 });                    // plinto + deck + trilho + postes; B.piso = y do chão
DI.chao(S, { y: B.piso, grelhas: [[x, z, larg, prof, rotY], …], cabos: [[[x,z], [x,z], …], …] });
const A = DI.agua(S, ter);  A.set(nivel);   // nível < -fundo esconde; espuma automática na margem
```

- Malha 200×160 é o equilíbrio (≈3,5 px por célula). Menos que 120 fica facetado.
- `terreno({mat, matFace})` aceita materiais próprios (topo e faces).

## 4. Relevos (funções de altura)

- `DI.domo(x, z, {x, z, rx, rz, rx2, h, ang, pot, ombro, sulcos, sulcosF, semente, pe, peLarg})`
  - `pot` alto + `ombro` baixo → paredes verticais (pão de açúcar, mesa); `pot` 1,7 + `ombro` .7 → morro redondo.
  - `rx2`: raio do lado −x local (encosta assimétrica). `sulcos` .05–.1: caneluras verticais. `pe`: talude no pé.
  - Fora do raio é negativo: combine com `DI.smax(chao, domo, k)`.
- `DI.cristas(x, z, oct)` (0..1, arestas) para serras e textura de rocha; `DI.fbm` (−1..1) para ondulação; `DI.ruido` simples.
- Rocha "crocante": `+ rocha·(.34·cristas(x·1.7) − .12) + rocha·.17·cristas(x·4.8)` onde `rocha = suave(.4, 2, altura do domo)`.
- Mar: `lerp(fundoMar≈-1, terra≈.15, suave(-.05, .3, máscara))` com uma linha de costa `costa(z) − x`.
- Serra (estilo da referência): `h = .3 + sino(x,z)·(2.4 + 1.7·cristas(x·.35, z·.35))`.
- Rio/cânion: `h = base − 1.2·exp(−(dist até a curva do rio / .5)²)` e água em `A.set(-.3)`.

## 5. Metamorfose

```js
const M = DI.metamorfose(ter, {
  estados: [planicie, macico, final],
  passos: [
    { t: [-.35, 1.75], modo: 'inchar', larg: .45, crista: .22, u: (x, z) => Math.hypot(x + 1.6, z + .7) / 7 },
    { t: [1.65, 3.6],  modo: 'onda',   larg: .4,  crista: -.15, u: (x, z) => (1 - (x / 5 + z / 4) / 2) / 2 },
  ],
});
S.update = t => { M.update(t); /* … */ };   // M.E[k] = alturas do estado k (para posicionar coisas no relevo final)
```

## 6. Mata, adereços, cabos

```js
const veg = DI.tufos(S, ter, [{ x, z, s: .15, t0: 4.0 }, …]);  veg.update(t);     // tufos pousados no relevo atual
const casa = DI.casinha(S, { x, y, z, rot: .6, larg: .5, alt: .32, prof: .42 });   // creme + telhado vermelho + mastro
const c = DI.cabo(S, [x0, y0, z0], [x1, y1, z1], { flecha: .3 });  c.mostrar(k); c.P(u) → Vector3
const b = DI.cabine(S, { escala: 1.25 });  b.position.copy(c.P(u)).y -= b.userData.alturaHaste;
const barco = DI.barco(S, { escala: 1.7 });
```

Ponto mais alto de um morro (para estação/farol): varra `M.E[últ]` num raio. Mata: sorteie vértices com `DI.rng`, recuse altura < .1 e declive alto.

## 7. Material próprio

```js
DI.material({ rampa: 'areia' | {c: ['#…'×5], cs: '#sombra', hc: '#hachura'}, rocha: 'rocha' | null,
  faixas: [.1, .25, .42, .86], faixasRocha: [.14, .34, .6, .9], hachura: [.85, 22, .38, .6], estrias: [0, 30, .5],
  salpico: [.05, .015, 13], aspereza: [.12, 3], grad: { dir: [x,y,z], de, ate, cor, forca }, mapa: DI.textura(…), rep: [u, v], agua: false })
```

Textura pintada: `DI.textura(512, 512, (ctx, w, h) => { ctx.strokeStyle = DI.CV.TINTA; … })` — `CV.BASE` (não muda), `CV.TINTA` (nanquim), `CV.FUNDO`/`FUNDO2` (rebaixo), `CV.LUZ` (brilho). Prontas: `texPainel`, `texChao`, `texGrelha`.

## 8. HUD

```js
DI.estiloHUD();                                  // CSS das classes .di-fig .di-tit .di-sub .di-tag .di-fios .di-escala
DI.titulo('#tit', 980);                          // no SETUP: quebra em letras (.ch) e cabe na largura
const TAGS = DI.etiquetas(S, [{ el: '#tg1', t: [.35, 1.62], alvo: () => [x, ter.altura(x, z), z] }, …], '#fios');
onTick(t => DI.carimbar('#selo', t, 6.35));      // carimbo em 4 degraus
```

`alvo` é uma função: o anel acompanha o relevo subindo ou um objeto andando (`() => [b.position.x, b.position.y, b.position.z]`).

## 9. Receitas prontas (outros temas)

- **Vulcão que nasce** (`inchar` de um cone com cratera: `domo − .6·domo(raio menor)`) + lava: água com rampa laranja (`rampa: {c:['#5a0f1a','#a3201c','#e2531d','#f59a3a','#ffd36b']}`).
- **Rio que cava um cânion**: estado 2 com o leito rebaixado ao longo de uma curva; passo `onda` com `u` = posição ao longo do rio; água sobe junto.
- **Cidade que cresce**: relevo quase fixo + `casinha` instanciadas brotando por distância ao centro.
- **Geleira que recua**: rampa clara (`c: ['#5d6f9a','#8fa6c8','#c3d3e6','#e7eef6','#ffffff']`) num domo que encolhe com `onda`.
