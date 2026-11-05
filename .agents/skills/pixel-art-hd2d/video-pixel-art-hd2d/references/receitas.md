# Receitas — biblioteca `lib/hd2d.js`

```js
import * as HD from '../../lib/hd2d.js';
const { THREE, lerp, clamp, fase, suave } = HD;
const S = HD.palco({ fov: 28, tilt: { faixa: 3.2, abertura: .036, max: 26 } });
S.update = t => { /* tudo por quadro */ };
```

## 1. Palco, câmera, utilidades

- `HD.palco(o)` → `S` (`scene`, `camera`, `renderer`, `sol`, `hemi`, `tilt`, `nevoa`, `sprites`, `particulas`, `hud`).
  Opções: `fov`, `exposicao`, `ceu:[cores]`, `hemi:{ceu,chao,forca}`, `sol:{cor,forca,dir,suave}`, `sombraCaixa:[cx,cz,raio]`,
  `tilt:{faixa,abertura,max, tela:{centro,faixa,suave,max}}`, `nevoa:{cima,baixo,ini,fim,max}`, `bloom:{forca,raio,limiar}`,
  `grade:{sombra,luz,sat,contraste,vinheta,grao, sol:{uv,cor,forca}}`, `tintaSprite`. Pode mexer em `S.tilt`/`S.nevoa` por quadro.
- `HD.travelling(S, {de, ate, dist, pitch, yaw, fov, t0, t1, ease, focoExtra})` → `cam(t)` (chame no `S.update`; ajusta o foco).
- `HD.CFG = {ppu: 24, ppuSprite: 20}` — densidade de pixels (mude antes de criar peças).
- `HD.rng`, `HD.hash(x,y,s)`, `HD.ruido`, `HD.fbm`, `HD.dither(x,y)`, `HD.fase`, `HD.lerp`, `HD.clamp`, `HD.suave`, `HD.v3`.

## 2. Pixel art: pincel, cor, fonte

- `HD.rampa(cor, n, {contraste, matiz})` → n tons com matiz deslocado. `HD.misturar(a, b, k)`, `HD.cor('#hex')`, `HD.linear('#hex')`.
- `new HD.Pixels(w, h)`: `px(x,y,cor,alfa)`, `rect`, `disc`, `elipse`, `linha`, `poli([[x,y]...])`, `mapa(x,y,['..ab'],{a:'#..'})`,
  `a(x,y,altura)` (mapa de altura → normal), `contorno(cor)`, `rep = true` (tileável), `textura()`, `normais(forca)`, `canvas()`.
- Fonte bitmap 5×7 com acentos: `HD.textoPx(P, 'PÃO QUENTE', x, y, cor, {escala})`, `HD.medirPx(texto)`.

## 3. Texturas (`HD.tex.*`, todas em cache, UV em texels)

`paralelepipedo({cor})`, `pedraPortuguesa({claro, escuro, lambda, amp, banda})`, `rebocoTile(cor)`, `liso(cor)`, `concreto(cor)`,
`tijolo({cor, junta})`, `telha({cor})`, `madeira(cor)`, `folhagem(cor, {flores, corFlor, n})`, `grama(cor)`, `terra(cor)`, `casca(cor)`,
`azulejo({cor, fundo})`, `toldo(cores)`, `toldoSaia(cores)`, `chapa(cor, {vertical})`, `grade(cor, {meio})`, `veneziana(cor)`,
`janela({w,h,acesa,cortina,moldura,tipo,planta})`, `porta({w,h,cor,tipo:'madeira'|'ferro',acesa})`, `revistas()`, `fronde(cor)`.
Fachada inteira pintada: `HD.fachada(W, H, cor, {aberturas, barra, descascado, rachaduras})` + `HD.pintarLoja(F, {...})`,
`HD.pintarPortao(F, {...})` → `F.pronto()`.

Materiais: `HD.matTex(pacote, {cor, relevo, rug, metal, emissivo, brilho, alpha, lados})`, `HD.matCor(cor)`, `HD.brilho(cor, forca)`.
Geometria com UV em texels: `HD.caixa(w,h,d, mat|[6 mats], {pos})`, `HD.plano(w,h,mat,{pos})`, `HD.chao(x0,x1,z0,z1,y,mat,{variacao})`,
`HD.cilindro(rt,rb,h,mat,{seg,base,pos})`, `HD.bolha(r, mat, seed, {irregular, achata})`.

## 4. Cenário

- `HD.rua({x0,x1,larg,calcLonge,calcPerto, paralelepipedo, pedra})` — pista, meio-fio, sarjeta e calçadas (y = 0,16).
- `HD.casa({x, z, larg, prof, andares, pe, cor, corLado, telhado:'colonial'|'platibanda'|'laje', plat, corTelha, seed,
  janelas:[{x,y,w,h,acesa,veneziana,grade,floreira,cortina}], portas:[{x,y,w,h,cor,tipo,acesa}], loja:{x,w,h}, portao:{x,w,h},
  barra:{cor|azulejo,h}, toldo:{x,y,w,prof,cores}, letreiro:{linhas,fundo,borda,brilho,x,y}, sacada:{x,w,y},
  muro:{recuo,altura,cor,portao:{x,w}}, caixaDagua:{x}, ferragens, numero, tijoloAndar})` — origem no canto esquerdo
  da fachada; `x` das aberturas é o centro, a partir da esquerda; `g.userData.portao` é o portão (anime `position.x` p/ correr).
- `HD.letreiro({linhas:[{texto, escala, cor}], fundo, borda, brilho})`, `HD.toldo(g, {...})`, `HD.janela3D`, `HD.porta3D`,
  `HD.telhadoColonial(larg, prof, alt, {cor, beiral})`, `HD.caixaDagua()`.
- `HD.poste({x,z,trafo,luz,forcaLuz,alcance,lado})` + `HD.emaranhado(postes, {ramais:[[a,b]...]})`, `HD.fio(a, b, {queda,raio})`.
- `HD.banca({x,z,texto,cor})`, `HD.orelhao({x,z,cor})`, `HD.mesaBoteco({x,z,cor})`, `HD.vaso({x,y,z,flor,alto})`,
  `HD.engradado({x,y,z,pilha,cor})`, `HD.canteiro({x,y,z,larg})`, `HD.carro({tipo:'seda'|'kombi',x,z,cor,cor2,giro})`.
- `HD.arvore({tipo:'ipe'|'mangueira', cor, x,y,z, altura, raio, bolhas})`, `HD.palmeira({x,z,altura})`,
  `HD.bairroFundo({x0,x1,z0,fileiras,passo,subida,acesas})` — morro de casinhas para o topo do quadro.

## 5. Sprites

- `HD.folhaSprite(w, h, n, (P, i) => {...}, {contorno})` → folha; `HD.sprite(S, folha, {pos, ppu, ancora, inclina, blob, sombraReal, tinta})`
  → `{g, plano, quadro(i), visivel(v), flip}`.
- Prontos: `HD.folhaPessoa({pele: HD.PELE.parda, cabelo:{cor, estilo:'curto'|'crespo'|'longo'|'coque'|'careca'}, camisa, calca, sapato,
  extra:['touca','bandeja'] | 'bone' | 'colete' | 'avental' | 'sacola', corBone})` — quadros 0-1 parado, 2-5 andar, 6-7 acenar,
  8-11 varrer, 12-13 arrumar. `HD.folhaMotoboy({moto, bau, raio, jaqueta, calca, capacete})` — 0-3 andando, 4-5 parado.
  `HD.folhaCachorro({cor})` — 0-1 rabo, 2-3 latindo. `HD.folhaBalao('BI-BI!', {cor})`.
- Roda que gira com a distância: `moto.quadro(Math.floor((x - x0) / .183) % 4)`. Balão que "pula" em degraus:
  escala 0 → .55 → 1.18 → 1 em 0,1 s.

## 6. Partículas, luz, água, HUD

- `HD.particulas(S, n, (t, P) => P.set(i, x,y,z, tam, [r,g,b] linear, alfa), {aditivo, forma:'disco'})`.
- `HD.poeira(S, {caixa, n, cor, forca})`, `HD.petalas(S, {centro, raio, n, cores, vento})`, `HD.vagalumes(S, {caixa, n})`,
  `HD.fumaca(S, fonte(t)→[x,y,z], {intervalo, vida, deriva, tam, alfa, forca(nasc)})`, `HD.respingos(S, [{t0,x,z,n,vx}])`.
- `HD.raios(S, {pontos, dir, comp, larg, cor, forca})` — cortinas de luz aditivas sempre de frente para a câmera.
- `HD.poca(S, {x,z,rx,rz,corA,corB,luz, ondas:[{x,z,t0,forca}]})` — água pixelada que reflete o céu e faz anéis.
- `HD.placaLocal(S, 'RUA DAS PALMEIRAS', {sub:'18h40', t0, t1, y, escala})` — placa com moldura dourada e ramos que crescem.

## 7. Receitas de cena

- **Herói atravessando:** `x(t) = lerp(x0, x1, fase(t, 0, tPara, 'power2.out'))`; câmera `travelling` linear um pouco mais lenta;
  no fim, troca de quadros para "parado" + balão + reação de figurantes (cachorro late, cliente acena).
- **Trabalhadores em loop:** cada figurante com uma ação e uma frequência diferente (`Math.floor(t * 3..7) % n`) — nunca em sincronia.
- **Outros lugares:** feira (toldos de várias cores + `mesaBoteco` como bancas + `engradado`), praça (canteiros, `arvore`, bancos,
  `vagalumes` à noite), praia (troque `pedraPortuguesa` por areia com `tex.terra('#e8c98a')`, `palmeira`, `poca` como mar raso),
  noite (sol fraco azulado, `hemi` escuro, janelas e postes acesos, bloom 0,8).
- **Loop curto:** comece com o herói já no quadro e algo se movendo; termine com ele parado mas animado (motor, rabo, aceno).

## 8. Esqueleto de página

```html
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="formats" content="9x16,16x9">
<script>VIDEO={w:1080,h:1920,fps:30,dur:5,bpm:96}; if (/fmt=16x9/.test(location.search)) { VIDEO.w = 1920; VIDEO.h = 1080; }</script>
<script src="../../lib/boot.js"></script>
<style>#stage{background:#1a1420;overflow:hidden} .layer{position:absolute;inset:0;width:100%;height:100%}</style></head><body>
<div id="stage"></div>
<script type="module">
import * as HD from '../../lib/hd2d.js';
const S = HD.palco({ fov: 28 });
S.scene.add(HD.rua());
const heroi = HD.sprite(S, HD.folhaMotoboy(), { pos: [-6, 0, .8] });
const cam = HD.travelling(S, { de: [-3, 2.3, -4], ate: [3, 2.3, -4], dist: 41, pitch: 31, yaw: 8, fov: 28 });
S.update = t => { cam(t); heroi.g.position.x = -6 + t * 2; heroi.quadro(Math.floor(t * 12) % 4); };
cue('amb:rua', 0, { d: VIDEO.dur }); cue('motor', 0, { d: VIDEO.dur, para: VIDEO.dur });
window.SETUP = () => {};
</script></body></html>
```

Som (`audio/synth.py`): cues `amb:rua {d}`, `motor {d, para}`, `buzina`, `latido`, `respingo`, `placa`, `chime {m}`, `blip`
(todas com `gain` e `pan`); a música é um loop curto de violão dedilhado em bossa no `bpm` do vídeo, mixada a ~−14 LUFS.
