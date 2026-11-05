# lib/jelly.js — API e receitas

```js
import * as JL from '../../lib/jelly.js';
const { THREE, V3, lerp, clamp, fase, suave, ciclo } = JL;
```

## Utilidades
- `JL.rng(seed)` · `clamp` · `lerp` · `suave(a,b,v)` · `fase(t, t0, t1, ease)` (ease do GSAP) · `ciclo(t, per, off)` (t dentro do período) · `JL.num(v, casas)` (vírgula decimal).

## Palco, luz, câmera
- `S = JL.palco({fov, luz:{dir:[x,y,z], forca}, ambiente, hemi, preenche, raioLuz, fundo:[3 cores], chao, neblina, vinheta, exposicao})` — renderer (antialias, Neutral), estúdio creme, RoomEnvironment, luz principal com sombra macia + preenchimento, chão infinito. Define `S.update = t => {}`.
- `S.luz(centro, raio)` — aponta a luz/caixa de sombra. `S.orbita(alvo, dist, azimuteGraus, elevacaoGraus, fov)` — câmera orbital (chame por quadro).
- `JL.prato({raio, fundo})` — prato de porcelana com sombra no chão; define o piso (`JL.piso()` = y onde as coisas apoiam).

## Material e balanço
- `JL.SABORES` / `JL.sabor(nome|cor)` — paleta (cor, fundo, miolo, borda).
- `J = JL.jiggle({altura, freq, amort, onda, decai, fOnda})` — um corpo que balança. `J.impacto(t, forca, [frente, lado])` registra um pulso (squash + cisalhamento + onda). `J.extra = {squash, frente, lado}` soma deformação contínua. `J.atualizar(t, obj)` (por quadro) usa a posição/frente do `obj`. `J.energia` (0–1) para números do HUD.
- `JL.mola({freq, amort, loop})` — mola avulsa: `.pulso(t, a)`, `.em(t)`.
- `JL.AJUSTE = {firmeza, amortecimento, balanco}` — multiplicadores globais (sliders).
- `JL.gelatina(sabor, J, {espessura, atenuacao, rug, brilho, borda, ior, env})` — MeshPhysicalMaterial de goma (transmissão + atenuação + verniz + miolo/borda) já com jiggle.
- `JL.plastico(cor, J, {rug, verniz, metal})` · `JL.fosco(cor, J, {rug, map})` · `JL.metal(cor, J, {rug})` · `JL.comJiggle(material, J, extra)` — prende qualquer material a um jiggle.
- `JL.bolhas(pontos, sabor, J, {claras, escala, seed})` — pontinhos escuros + bolhas claras instanciados.

## Formas por SDF
- `JL.sdf.{elip, bola, capsula, caixa, uniao(a,b,k), menos(a,b,k)}` sobre `p = [x,y,z]`.
- `JL.malhaSDF(f, min, max, res)` → BufferGeometry suave (marching cubes + normais). `JL.pontosDentro(f, min, max, n, seed, margem)`.

## Personagem
- `U = JL.ursinho({sabor, altura (.6), capacete: cor|false, colete: cor|false, listra, olhos, bolhas, seed, freq, amort, gel})`
  - `U.grupo` (posicione/gire: frente = +z local), `U.sombra` (adicione à cena), `U.jig`, `U.ossos` (raiz, tronco, cabeca, bracoE, bracoD, pernaE, pernaD), `U.mao.E / U.mao.D` (engates na ponta dos braços).
  - `U.pose({tronco, cabeca, bracoE, bracoD, pernaE, pernaD: [rx,ry,rz], sobe})` — braço: `rx` negativo levanta para a frente.
  - `U.atualizar(t)` — por quadro, DEPOIS de posar/posicionar.
- `JL.andar(t, passo, amp, off)` → pose parcial de caminhada · `JL.pisadas(t0, t1, passo, off)` → instantes de pé no chão · `JL.mistura(poseA, poseB, k)`.

## Peças de obra
- `JL.tijolo(J, {sabor, gel})` (tijolo baiano de goma, 8 furos; `JL.TIJOLO` = dimensões) · `JL.parede({cursos, porCurso, ultimo, alinhar:'esq'|'dir', J})` → `{grupo, topo, cursos, alt}` · `JL.argamassa(w,h,d,J,seed)`.
- `JL.martelo(J, {cabo})` (cabo em +y, cabeça em z) · `JL.enxada(J, {cabo})` (`.lamina`) · `JL.carrinho(J, {sabor})` (`.roda`, `.raioRoda`; cabos para −z) · `JL.masseira({w, d})` · `JL.placa(linhas, {largura, alturaPostes, prop})` · `JL.marmita()` · `JL.monte({n, raio, alt, cor})` (areia/açúcar granulado).
- `JL.sombraColorida({cor, miolo, raio, alonga, altura, forma:[sx,sz], caustica})` → `.posicionar(V3, escala)`.

## HUD
- `JL.titulo(S, {rotulo, titulo:[linhas], tam, x, y, sub:[linhas], tamSub, ponto: cor | t => cor})`
- `JL.pilula(S, {estado: t => 'TEXTO', x, y})`
- `JL.painel(S, {titulo, x, y, w, acoes:[{n, k, larga}], ativa: t => i, sabores:[nomes], sabor: t => i, rotSabor, sliders:[{n, v: t => 0..1, txt: t => str, ex:[...]}], botoes:[...]})`
- `JL.dados(S, {x, base, w, instrucao (html), campos:[{l, v: t => str, u}], nota})` · `JL.rodape(S, {txt, x, w, base})` · `JL.tela(S, alvo)` (3D → px).

## Receitas

**Ação periódica que fecha o loop (martelar 8× em 5 s):**
```js
const PER = D / 8, U_GOLPE = .62;
const golpes = Array.from({ length: 8 }, (_, k) => k * PER + U_GOLPE * PER);
for (const tk of golpes) { U.jig.impacto(tk, .9, [.45, 0]); jTopo.impacto(tk, 1.7); cue('martelo', tk); }
// por quadro: u = ciclo(t, PER)/PER → sobe (power2.out) até .5, desce (power3.in) até U_GOLPE, recua
```

**Acertar um alvo com a ferramenta (resolvedor):** gire o ursinho, varra o ângulo do braço, meça `ferramenta.cabeca.getWorldPosition()` e mova o grupo para a cabeça cair no alvo (ver bloco do mestre de obras no exemplo).

**Ir e voltar carregando algo:** caminho `P0 → P1` na diagonal para a câmera (o objeto carregado aparece contra o prato, não contra a parede); tempos `ida → larga → vira → volta → pega → vira`; o objeto na mão é um `Object3D` filho do grupo (`naMao`) e copia a posição por quadro; pisadas com `JL.pisadas` viram impactos e cues `passo`.

**Empurrar/arrastar com objeto preso:** prenda o objeto (carrinho) num grupo filho do ursinho, com jiggle próprio; impactos na partida e na parada; gire a roda por `distância / raio`.

**Outro bicho de goma:** escreva o SDF (uniões suaves de elipsoides/cápsulas), gere com `malhaSDF` (res 72–96), material `gelatina(sabor, J)`, bolhas com `pontosDentro` + `bolhas`, olhos opacos; sem esqueleto, anime pelo grupo e pelo jiggle (o balanço sozinho já dá vida). Com membros, copie o padrão do ursinho (pesos por distância às partes, `SkinnedMesh`).

**Som:** cues `martelo`, `passo`, `plop`, `massa`, `baque`, `boing`, `squish` (`{gain, pitch}`); música `VIDEO.music = {style:'jelly', key:'F', gain}` com `bpm` que feche o loop (96 bpm × 8 tempos = 5 s).
