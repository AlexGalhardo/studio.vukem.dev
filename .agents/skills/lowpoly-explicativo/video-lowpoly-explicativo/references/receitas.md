# Receitas — biblioteca `lib/lowpoly.js`

```js
import * as LP from '../../lib/lowpoly.js';
const { THREE, PAL, lerp, clamp, suave, fase } = LP;
const S = LP.palco({ dof: { abertura: .018, max: 34 } });
S.update = t => { /* 3D por quadro */ };
```

## Sumário
1. Palco, câmera e utilidades
2. Primitivas e materiais
3. Paisagem: terreno, água, rio, árvores
4. Cidade, casas, carros, gente
5. Máquinas e energia
6. Fluxos, setas, trilhas, partículas
7. Corte e explosão
8. HUD
9. Receitas para explicar QUALQUER processo
10. Esqueleto de página

## 1. Palco, câmera e utilidades

- `LP.palco(o)` → `S` com `scene`, `camera`, `renderer`, `sol`, `hemi`, `borda`, `dof` ({foco, abertura, max}), `hud` (lista de funções por quadro) e `S.sombra(centro, raio)`. Opções: `fundo:[cores]`, `fov`, `exposicao`, `dof`, `bloom:{forca,raio,limiar}`, `grao`, `vinheta`, `sol:{cor,forca,dir}`, `ceu`, `chao`, `hemi`, `borda`.
- `LP.roteiroCamera(S, planos)` → `cam(t)`; chame no `S.update`. Ver `movimento.md` §3.
- `LP.fase(t, t0, t1, ease)` → 0..1 com ease do GSAP. É o "relógio" de tudo.
- `LP.rng(seed)`, `LP.ruido(x,y)`, `LP.fbm(x,y,oct)`, `LP.suave(a,b,v)`, `LP.lerp`, `LP.clamp`, `LP.v3([x,y,z])`.
- `LP.tela(S, alvo)` → `{x, y, atras}` em px (para posicionar HTML sobre o 3D).

## 2. Primitivas e materiais

```js
LP.caixa(w, h, d, cor, { pos:[x,y,z] /* centro da BASE */, chanfro, plano, mat:{...} })
LP.cilindro(r, h, cor, { rTopo, lados: 10, aberto, pos })
LP.bola(r, cor, { det: 1, sacode: .05, seed })     // icosaedro facetado
LP.mat(cor, { plano, rug, metal, emis, emisForca, opac, lados })   // com cache por cor+opções
LP.brilho(cor, forca)                               // material que passa no bloom
LP.malha(geo, material, { sombra, recebe })
LP.facetar(geo, amp, seed)                          // tira índices e sacode vértices: vira low-poly
```

Objeto novo = grupo de 2–6 primitivas. Ex.: semáforo = `cilindro` (poste) + `caixa` grafite + 3 `bola` com `brilho`.

## 3. Paisagem

```js
const H = (x, z) => /* altura */;
const ilha = LP.terreno({ x:[-10,10], z:[-12,22], seg:[44,76], altura: H, cor: (x,y,z,inclinacao) => hex, base: -1.6, corSaia: '#8a6649' });
const lago = LP.agua({ x:[-9.3,9.3], z:[-12,0], nivel: 3.7, fundo: .5, onda: .05 });   // lago.userData.update(t); .lamina; .volume
const rio  = LP.rio(curva, { largura: 1.3, onda: .03 });                                // rio.userData.update(t)
const mata = LP.floresta({ n: 120, h: .85, pinheiros: .3, chao: H, area: r => [x, z], filtro: (x, z) => bool });
const arv  = LP.arvore({ h: 1, tipo: 'pinheiro' | 'redonda', seed });
const nuv  = LP.nuvem({ tam: 1, seed });
```

- Vale entre morros: `A * suave(L, L + W, |x|)` com ruído; garganta estreita = `W` pequeno.
- Cor por face: inclinação > .55 vira rocha; perto da água vira areia; 3 tons de grama por ruído.
- O terreno é um sólido fechado (topo + saia + fundo): o corte mostra a terra em faixas.

## 4. Cidade, casas, carros, gente

```js
const cid = LP.cidade({ lotes: [{ x, z, y, w, d, andares, cor, ry }], acesa: '#ffcf73', forca: 1.9 });
cid.userData.acender(j => clamp((k - ordem(j)) * 9));   // j: {mundo (Vector3), k (aleatório 0..1), predio}
LP.predio({ w, d, andares, altAndar, cor })              // um prédio solto (janelas em userData.janelas)
LP.casa({ w, d, h, cor, telhado })
LP.carro({ cor, comp })                                  // frente em +z; userData.rodas para girar
LP.boneco({ cor, h })                                    // userData.bracos / pernas: pivôs nos ombros/quadris
LP.pino(cor, { h, r, forca })                            // "este aqui": haste + bolinha que brilha
```

Andar do boneco: `k = sin(t*6)`; braços `±k*.5`, pernas `∓k*.4` em `rotation.x`.

## 5. Máquinas e energia

```js
LP.turbina({ r, pas: 13, cor, corPa })                 // gire rotation.y
LP.gerador({ r, bobinas: 12, polos: 8 })               // userData.partes = { estator, rotor, tampa }; estator.userData.bobinas[] (emissive próprio)
LP.engrenagem({ r, dentes, esp, furo, cor })           // duas iguais engrenam a 2r+~.1 com defasagem de π/dentes e giros opostos
LP.torre({ h, cor })                                   // userData.pontas (isoladores, coords locais)
LP.catenaria(a, b, caida) → curva;  LP.cabo(curva, { raio, cor })
LP.cano(curva, { raio, cor, interior, lados })         // tubo com interior escuro (corte mostra o "por dentro")
```

- Linha de transmissão: para cada fio, um `THREE.CurvePath` de catenárias entre pontas de torres (`ponta.clone().applyMatrix4(torre.matrixWorld)`), depois `LP.cabo(path)` + `LP.fluxo(path, {forca})` para os pulsos.
- Bobinas acendem quando o polo passa: `emissiveIntensity = k * (.35 + 2.4 * max(0, cos(np/2 * (a - ang)))**6)`.

## 6. Fluxos, setas, trilhas, partículas

```js
const f = LP.fluxo(curva, { n: 30, forma: 'seta' | 'bola' | 'capsula', tam: .17, cor, forca /* brilho */, vel: .5, espalha: .1 });
f.userData.update(t, quantidade /* 0..1 liga aos poucos */, vel?);
const s = LP.seta(curva, { largura: .3, cor, normal });  s.userData.progresso(k);   // seta chata que se desenha
const tr = LP.trilha(curva, { raio: .05, cor, forca });  tr.userData.progresso(k);  // tubo luminoso que se desenha (ref. luz verde)
const po = LP.poeira({ n: 200, centro, raio: [rx, ry, rz], tam: .045, cores });  po.userData.update(t);
```

Curvas: `new THREE.CatmullRomCurve3(pontos)` (passe `true` como 2º argumento para laço fechado: ciclos).

## 7. Corte e explosão

```js
const c = LP.corte([-1, 0, 0], 100);                 // normal (-1,0,0): mantém x ≤ pos
c.aplicar(ilha, { secao: '#c48a5c', faixas: [[-.6, '#7d5a43'], [.4, '#a8744f']] });   // terra em camadas
c.aplicar(barragem, { secao: '#c3cad4', hachura: ['#a7b0bc', .32] });                  // concreto hachurado
c.aplicar(arvores);                                   // só corta (sem tampa)
c.pos(lerp(6.5, 0, fase(t, t0, t0 + .7, 'power2.out')));   // varre
const sec = LP.secaoAgua({ z: [z0, z1], nivel, fundo, chao: H });  sec.userData.pos(c);   // água com terreno dentro
LP.prepararExplosao(parte, [0, 1.4, 0], [giroX, giroY, giroZ]);
LP.explodir([partes], fase(t, t0, t0 + .7, 'back.inOut(1.4)'));
LP.brotar(obj, fase(t, t0, t0 + .3, 'back.out(2.5)'));   // escala 0 → 1
```

Use **normais diferentes para cortes diferentes**: `[0,-1,0]` tira a metade de cima (vê dentro de um cano deitado), `[0,0,-1]` tira a frente (vê dentro de um anel com a câmera em +z).

## 8. HUD

```js
LP.cabecalho(S, 'COMO FUNCIONA · TEMA', [{ t: .12, txt: 'CAPÍTULO 1' }, { t: 2.7, txt: 'CAPÍTULO 2' }]);
LP.legenda(S, [{ t0: .25, t1: 2.64, txt: 'Frase curta do capítulo.', fala /* s, opcional */ }]);
LP.rotulo(S, { alvo: obj | [x,y,z], titulo, sub, t0, t1, lado: 'dir' | 'esq', dx, dy, margem });
LP.painel(S, [{ t, txt, val }], { titulo, t0, t1, top });                     // lista que acende (1-2-3)
LP.placar(S, { esq: { rot, val }, dir: { rot, de, para, cor }, conta: [t0, t1], t0, t1, top });   // 2 números, o da direita conta
LP.cota(S, a, b, { t0, t1, texto, lado });                                    // linha de medida entre 2 pontos 3D
LP.carimbo(S, 'TEXTO', { t0, t1, y, giro });
LP.tituloCapitulo(S, { n: '1', txt: 'cabos', cor, t0, t1, y });               // numeral gigante (variante clara)
```

## 9. Receitas para explicar QUALQUER processo

Comece respondendo, para cada etapa: **onde acontece** (o lugar/peça), **o que muda** (verbo) e **como provar com movimento**. Escolha a prova pelo verbo:

| verbo do processo | prova visual | peças |
|---|---|---|
| entra, sai, corre, desce, circula | partículas andando numa curva | `fluxo` em `cano`, `rio`, `cabo` |
| gira, move, empurra | peça girando que move a seguinte | `turbina`, `engrenagem`, eixo `cilindro` |
| é feito de, tem dentro | corte varrendo + rótulos nas camadas | `corte` + `faixas`/`hachura`, `rotulo` |
| tem partes, se monta | explosão vertical + rótulos | `prepararExplosao` / `explodir` |
| acende, esquenta, liga | material que brilha em sequência | `brilho`, `emissiveIntensity`, `cidade.acender` |
| aumenta, conta, compara | placar contando, barras crescendo | `placar`, `caixa` com `scale.y = fase(...)` |
| mede, fica mais alto/baixo | linha de medida | `cota` |
| chega em muitos lugares | pinos brotando + pulsos | `pino` + `brotar`, `fluxo` |
| alguém usa / faz | boneco + objeto | `boneco`, `carro`, `casa` |
| repete em ciclo | fluxo em curva fechada | `CatmullRomCurve3(pts, true)` + `fluxo` |

Formatos prontos:

- **Cadeia (A → B → C → D)**, como a hidrelétrica: um capítulo por elo; o fluxo do fim de um capítulo vira o começo do próximo (pulso que sai do gerador → pulsos nos cabos). Termine com o resultado visível (cidade acendendo) + carimbo.
- **Máquina por dentro** (motor, fechadura, relógio, impressora): plano geral → corte → close na peça-chave → explosão → volta ao conjunto funcionando.
- **Sistema/rede** (internet, trânsito, correio, esgoto): vista alta da maquete, pinos nos nós, pulsos entre eles; um capítulo em close num nó.
- **Ciclo** (água, carbono, reciclagem): maquete com 3–4 estações em volta de um laço; a câmera orbita 90° por capítulo; o fluxo nunca para.
- **Antes/depois ou mito/verdade**: placar com o número "esperado" × o real, carimbo com a palavra-chave ("DE PROPÓSITO", "SOBRAM 10").
- **Corpo/natureza em camadas** (pele, solo, oceano): bloco em corte com faixas coloridas, trilha luminosa atravessando as camadas.

## 10. Esqueleto de página

```html
<script>VIDEO={w:1080,h:1920,fps:60,dur:10,bpm:100,music:{style:'ambient_major',key:'D',gain:-4}}</script>
<script src="../../lib/boot.js"></script>
<style>#stage{background:#0c0f15;overflow:hidden} .layer{position:absolute;inset:0;width:100%;height:100%}</style>
<div id="stage"></div>
<script type="module">
import * as LP from '../../lib/lowpoly.js';
const { THREE, PAL, fase } = LP;
const T = { c1: 0, c2: 2.5, c3: 5, c4: 7.5, fim: 10 };
const S = LP.palco({});
// … maquete …
const cam = LP.roteiroCamera(S, [ /* 1 plano por capítulo */ ]);
S.update = t => { cam(t); /* mecanismo */ };
LP.cabecalho(S, 'COMO FUNCIONA · TEMA', [/* chips */]);
LP.legenda(S, [/* frases */]);
// rótulos, painel, carimbo…
cue('m:intro', 0); cue('m:drop', T.c3); cue('m:stop', T.fim - .25);   // + efeitos (audio.md)
window.SETUP = () => {};
</script>
```
