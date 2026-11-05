# Receitas — API de `lib/ilustra.js` (global `IL`)

Na página: `<script>LIBS=['terra.js','ilustra.js']</script>` antes do `boot.js` (`terra.js` só se usar o globo).
Tudo devolve string SVG (para `IL.add`) ou elemento; quem anima é você, no `onTick`.

## Sumário
1. Esqueleto de página e cenas
2. Primitivas
3. Fundo e grão
4. Fotos em cantoneiras (cena 1)
5. Rachaduras e coroas
6. Personagens
7. Objetos e efeitos
8. Globo e fluxo
9. Câmera do plano contínuo
10. Nuvens, varrida e título (cena 3)
11. Fotos e créditos
12. Receita de um vídeo novo

## 1. Esqueleto de página e cenas

```html
<div id="stage"><div id="c1" class="cena"></div><div id="c2" class="cena"><div id="mundo"></div></div><div id="c3" class="cena"></div></div>
```
```js
const T = { c2: 2.05, c3: 6.40, fim: 8.0, … };
const cenaEm = t => t < T.c2 ? 1 : t < T.c3 ? 2 : 3;
onTick(t => { const c = cenaEm(t); ['#c1', '#c2', '#c3'].forEach((s, i) => IL.show(K.$(s), c === i + 1)); });
// em cada onTick de cena: if (cenaEm(t) !== 2) return;
IL.grao(K.$('#stage'), { op: .2, amp: 70, qps: 12 });     // por último: grão por cima de tudo
```

## 2. Primitivas

| função | o que faz |
|---|---|
| `IL.add(parent, str)` | insere HTML/SVG (em `<svg>`/`<g>` os nós nascem SVG) e devolve o nó novo |
| `IL.svg(parent, w, h)` | `<svg>` absoluto no canto |
| `IL.forma(d, fill, {lw, cor})` | caminho preenchido com contorno preto |
| `IL.linha(d, cor, w)` · `IL.tubo(d, w, fill)` · `IL.setTubo(g, d)` | traço; tubo com contorno (braço, cano); atualizar tubo |
| `IL.circ`, `IL.elipse`, `IL.pilula(x, y, w, h, fill)` | formas com contorno (`{sem:true}` tira o contorno) |
| `IL.poli(pts, fechado)` · `IL.cm(pts, fechado)` | polilinha; curva Catmull-Rom macia |
| `IL.tf(el, x, y, s, giro)` · `IL.show(el, on)` | transform SVG; mostrar/esconder |
| `IL.E(ease, t, a, b)` · `IL.q(t, 12)` · `IL.quadro(t, 8)` · `IL.pop(t, t0)` · `IL.passo(t, [[t, v]…])` | tempo: ease num trecho; tempo "em dois"; índice de fervura; pop elástico; degraus |
| `IL.P` · `IL.LW` | paleta e contorno padrão |

## 3. Fundo e grão

```js
IL.fundo(c1, IL.P.rosa);                 // div chapada
IL.grao(stage, { op: .2, amp: 70 });     // ruído de 1 px em overlay, deslocado a 12 qps (o da referência é fino e quase parado)
```

## 4. Fotos em cantoneiras (cena 1)

```js
const fotos = ['a', 'b', 'c', 'd'].map(n => IL.foto(c1, `img/${n}_pb.jpg`, 480, 320, { canto: 34 }));
// poses [t, x, y, escala, giro, duração, ease] — a 1ª pose (fora da tela) é a entrada; cada pose interpola a partir da anterior
IL.coreografia(fotos[0], [[-1, 540, 830, 1.18, -9], [-.14, 540, 900, 1.34, -3, .42, 'expo.out'], [T.f2, 285, 770, 1, -3, .38]]);
IL.coreografia(fotos[1], [[T.f2, 1560, 700, 1, 14], [T.f2, 795, 770, 1, 3, .24, 'expo.out']], { fase: 1.3 });
IL.coreografia(fotos[2], [[T.f3, 470, 2240, 1, -12], [T.f3, 540, 1130, 1, 2.5, .24, 'expo.out'], [T.f4, 285, 1130, 1, 2, .38]], { fase: 2.1 });
IL.coreografia(fotos[3], [[T.f4, 1580, 1300, 1, 13], [T.f4, 795, 1130, 1, -2.5, .24, 'expo.out']], { fase: 3.7 });
```
O balanço lento (±3 px, ±.6°) "em dois" já vem na coreografia (`fase` desencontra as fotos).

## 5. Rachaduras e coroas

```js
const s1 = IL.svg(c1, 1080, 1920);                       // ANTES das fotos (fica atrás)
const rios = IL.rachaduras(s1, { seed: 21, n: 10, lw: 3.6, seg: [60, 135], passos: [6, 11], ramo: .45 });
onTick(t => IL.crescer(rios, t, { t0: -.5, dur: 1.6, atraso: .1 }));   // começa já crescendo no quadro 0
const s1b = IL.svg(c1, 1080, 1920);                      // DEPOIS das fotos
IL.coroa(s1b, 30, 1690, 210, 270, { seed: 3 });          // canto de baixo, base fora do quadro
IL.coroa(s1b, 840, 1690, 210, 270, { seed: 8, espelho: true });
```
`IL.coroaD(w, h, seed, quadro, {picos, esp, j})` dá só o caminho; `IL.coroa` já ferve a 8 qps e solta faíscas.

## 6. Personagens

```js
const C = IL.boneco(svg, { x: 225, y: 1831, s: 1.55, dir: 1, jaleco: true, blusa: P.rosa, estampa: 'rabisco', corEstampa: P.azulm,
  cabelo: 'curto', pele: P.azulm, bico: P.rosa, maos: P.azulm });
// no onTick (coordenadas locais: (0,0) = topo do tronco; cabeça em y −78; ombros ≈ (±80, 30))
C.pos(225, 1831 + sai, 1.55, Math.sin(IL.q(t, 12) * 3) * .8);
C.braco('tras', [[80, 30], [150, 6], [168, -98]], { tipo: 'aponta', ang: -72 });   // ombro, cotovelo, pulso
C.braco('frente', [[-76, 30], [-78, 128], [8, 136]], { ang: -25 });
```
- `tipo`: `luva` (mitene), `punho` (segurando), `aponta`. `ang` gira a mão; `cor` troca a luva; `s` escala a mão.
- Objeto na mão: `IL.add(C.bracos.frente.g, …)` e mova-o para o 1º filho para ficar atrás da luva.
- Sem jaleco: tronco-pílula largo (pessoa comum). `hx` desloca a cabeça.
- Mãos soltas (braços que entram pela borda): `IL.mao(x, y, giro, cor, {tipo:'punho', s:1.95})` + `IL.tubo` grosso (96–108).

## 7. Objetos e efeitos

| função | uso |
|---|---|
| `IL.regador({icone:'arvore'})` | regador cinza com selo rosa (ícones: `arvore`, `vento`, `gota`, `sol`); bico local em (228,−44); alça no topo |
| `IL.lupa()` (tem `.palpebra` para piscar) · `IL.prancheta()` · `IL.exclamaD(quadro)` | acessórios do cientista |
| `IL.fogoD(cx, cy, r, seed, quadro, {picos:6, dir:-62, abertura:170, alto:.95})` | bola de fogo: abraça o círculo por baixo, picos para cima |
| `IL.labaredaD(cx, cy, r, n, seed, quadro, {vale, var, dir, puxa})` | estouro radial (sol, explosão) |
| `IL.bolhas(svg, {x, y, larg, n, t0, dur, sobe, r, vida})` | bolhas de contorno que sobem (vapor, água) |
| `IL.icone(nome, x, y, s)` | ícones de traço para selos |

## 8. Globo e fluxo

```js
const G = IL.globo(w2, { cx: 540, cy: 1250, r: 290, lon0: -58, lat0: -14, cor: P.rosa, lw: 2.8, pais: P.rosa, paisLw: 4 });
const d = G.caminho([[-31, -1], [-50, -3.5], [-72, -10.5], [-65.5, -19.5], [-50.5, -23]]);   // [lon, lat] → caminho SVG
const RV = IL.fluxo(w2, d, { w: 22, cor: P.azulc, ponta: true });   // tubo com contorno + traços brancos que correm + seta
onTick(t => RV.set(IL.E('power2.inOut', IL.q(t, 15), T.rio, T.rio + .75), (t - T.rio) * 160));   // (progresso, fase em px)
G.proj(lon, lat) → [x, y, visível]; G.terra.setAttribute('stroke', P.creme)   // continentes "esfriam"
```
`IL.fluxo` também serve para cano com água (`borda: P.azulc, lw: 0` dentro de um `IL.tubo` creme).

## 9. Câmera do plano contínuo

```js
const camY = IL.chaves([[T.c2, 640], [T.sobe, 610, 'none'], [T.sobe + .58, -50, 'power2.inOut'], [T.desce, -110, 'none'], [T.desce + .62, 1150, 'power2.inOut'], [T.c3, 1190, 'none']]);
onTick(t => K.$('#mundo').style.transform = `translateY(${-camY(t).toFixed(1)}px)`);
```

## 10. Nuvens, varrida e título (cena 3)

```js
const chuvaG = IL.add(IL.svg(c3, 1080, 1920), `<g></g>`);          // chuva ATRÁS do título
const tit = IL.add(c3, `<div><div class="titulo" id="t1" style="color:${P.k}"><span>RIOS</span></div><div class="titulo" id="t2" style="color:${P.creme}"><span>VOADORES</span></div></div>`);
const s3 = IL.svg(c3, 1080, 1920);
const NV = IL.nuvens(s3, { seed: 42, rotulo: IL.H2O });            // IL.CO2 para carbono; miolo/rotMold/topo/lado configuráveis
const arco = IL.bezier3([-260, 2150], [430, 1150], [760, 520], [1500, 200]);
NV.varrer(arco, T.varre, .62, -260);                               // alcance: + = pega pela ferramenta à frente da mão
const ferr = IL.add(s3, IL.guardaChuva());                         // ou IL.rede() — a da referência
IL.varredor(ferr, arco, T.varre, .62, { cena: t => cenaEm(t) === 3 });
const chover = IL.chuva(chuvaG, { t0: T.chuva });
onTick(t => { if (cenaEm(t) !== 3) return; NV.update(t); chover(t); /* título, subtítulo, crédito */ });
window.SETUP = () => { const fs = IL.cabe(K.$('#t2'), 790); /* aplique fs às 2 linhas, posicione em y ≈ 585 */ };
```
CSS do título: `.titulo{position:absolute;left:0;right:0;text-align:center;font-family:'Archivo';font-stretch:125%;font-weight:900;line-height:.92;white-space:nowrap}`.

## 11. Fotos e créditos

```bash
<PYTHON> -I tools/commons.py buscar "Amazon rainforest aerial view" --n 16 --folha previews/c.jpg
<PYTHON> -I tools/commons.py baixar 1 videos/<nn>/img/floresta.jpg --largura 1400
<PYTHON> -I tools/ilustra.py foto videos/<nn>/img/floresta.jpg videos/<nn>/img/floresta_pb.jpg --foco .5,.55
<PYTHON> -I tools/commons.py creditos videos/<nn>/img        # linha pronta para o rodapé
```
Apague os originais depois de gerar os `_pb.jpg`. Crédito no rodapé da cena 3 (17 px, preto 72%); com globo, acrescente "Mapa: Natural Earth".

## 12. Receita de um vídeo novo (ex.: "Por que o mar é salgado")

1. Cena 1: 4 fotos (mar, rio, rocha, salina) entrando; rachaduras viram "rios" pretos.
2. Cena 2: cientistas olham o globo com um fluxo do continente para o oceano; câmera sobe → braços derramam saleiros cinza (selo com ícone `gota`) no mar; câmera desce → pessoa prova a água num copo.
3. Cena 3: nuvens com `NaCl` (`'NaCl'` como rótulo), varrida com a rede, título "MAR / SALGADO" e subtítulo de 2 linhas.
4. Mesma `T`, mesmos eases; troque só desenho e texto.
