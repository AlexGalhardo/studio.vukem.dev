# API de `lib/maquete.js` + receitas

```js
import * as M from '../../lib/maquete.js';
const { THREE, PAL, PELE, CABELO, tex, MAT, ACAO, OBJ, ciclo, lerp } = M;
window.SETUP = async () => { const S = M.palco({...}); /* cena */ S.update = t => {...}; /* HUD */ };
```
Convenções: 1 unid. = 1 m · topo do bloco em y = 0 · `pos` das caixas/cilindros = centro da BASE · frente dos objetos em +z (gire com `rotation.y`) · "D" = direita do boneco (−x), "E" = esquerda (+x).

## Palco, câmera, animação

| função | o que faz |
|---|---|
| `M.palco({fov, exposicao, ambiente, sol:{dir,forca,cor,raio}, chao, sombraChao, ao:{raio,forca}, grao, vinheta, raioSombra, fundo:[topo,base]})` | renderer + estúdio creme + IBL + sol VSM + chão de sombra + GTAO + acabamento. Devolve `S` |
| `S.cada(fn)` | registra `fn(t)` por quadro (peças animadas usam isto) |
| `S.update = t => {}` | sua lógica por quadro (câmera, ações) |
| `S.sombra(centro, raio)` | move a caixa de sombra do sol |
| `M.orbita(S, {alvo, raio:[r0,r1], azim:[a0,a1], elev:[e0,e1], fov, t0, t1, ease})` | devolve `fn(t)`; azimute 0 = +z, 90 = +x |
| `M.fase(t,t0,t1,ease)`, `M.ciclo(t,T,f)`, `M.rng(s)`, `M.fbm`, `M.suave`, `M.lerp`, `M.clamp` | tempo e ruído determinísticos |

## Bloco, pisos, paredes

- `M.bloco({x:[x0,x1], z:[z0,z1], seed, estratos:[{h, tipo, cor?, raizes?, canos:{frente:[...], lado:[...]}}]})` — tipos: `concreto`, `contrapiso`, `terra`, `argila`, `areia`, `brita`, `rocha`, `asfalto`. Cano: `{u (0–1 na face), v (m abaixo do topo do estrato), r, cor, agua:true}`.
- `M.piso([x0,z0,x1,z1], textura, {tam (m por repetição), h, y, rug})` — placa fina com UV em metros.
- `M.parede([xa,za], [xb,zb], {h, y, esp, dentro, fora, tam, corte})` — `dentro` = face à DIREITA de quem anda de a→b (textura ou material). Porta = segmento com `h: .5, y: 2.3` (só a verga).
- `M.caixa(w,h,d,cor|mat,{pos, chanfro, sombra})`, `M.caixaTex(w,h,d,tex,tam,{pos})`, `M.cilindro(r,h,cor,{r2, pos, seg, aberto})`, `M.bola(r,cor,{pos, esc})`, `M.plano(w,h,tex|mat,{pos, rotY})`, `M.grupo(pai,x,y,z)`, `M.malha(geo, mat)`.

## Texturas (`tex.*`, canvas procedural, com cache)

`ladrilho({fundo,cor1,cor2})` · `azulejo({cor, rejunte, n, linhas, faixa:{linhas:[i], cor}})` · `pedraPortuguesa({faixa, pedra, claro, escuro})` · `asfalto()` · `madeira({cor})` · `xadrez({cor})` · `pintura({cor, alt, barra:{alt,cor}, rodape})` · `listras([cores])` · `macia()` · `estrato(tipo, larg, alt, {...})` · `giz([{txt, tam, cor, peso, esp}], {w,h,topo})` · `placa([{txt, tam, y, cor, peso}], {fundo, borda, w, h})`. `M.repetir(tex, rx, ry)` clona com outra repetição; `M.manchar(g,w,h,amp,esc,seed)` suja um canvas seu.

## Materiais

`M.mat(cor, {rug, metal, mapa, env, opac, lados, emis})` (cache) e prontos em `MAT`: `pele`, `tecido`, `cabelo`, `plastico`, `ceramica`, `inox`, `aluminio`, `ferro`, `madeira`, `vidro`, `luz`, `corte`. Água animada: `M.agua(S, {cor, opac, rep, vel})`.

## Peças prontas

Restaurante/comércio: `mesa({toalha, lado, alt})`, `cadeira({plastico, cor})`, `pf({r})` (prato feito), `copo(cor)` (americano), `garrafa(cor,{h})`, `salgado('coxinha'|'pastel'|'paoDeQueijo'|'esfiha')`, `balcaoVidro({comp, salgados})`, `geladeira({texto, faixa, cores})`, `fogao(S,{bocas, comp})` (chamas animadas), `panela({conteudo:'feijao'|'arroz'|'molho'|'agua'|cor, r, alt})`, `chapa({bifes, ovos})` (`userData.bifes`), `pia(S,{comp, pratos})` (água correndo), `caixaRegistradora()`, `quadro(w,h,tex)`, `cavalete(tex)`, `toldo({comp, proj, cair, cores})`, `ventilador(S)` (gira e oscila), `tv(S,{placar})` (futebol animado), `planta()` (espada-de-são-jorge).
Rua: `orelhao()`, `arvore({alt})`, `cachorro(S)` (vira-lata caramelo abanando o rabo).
Efeitos: `vapor(S, {pos, n, T, alt, larg, cor, opac, tam})` — vapor/fumaça em ciclo (cor `#aab6bf` para vapor, `#8f8d89` para fumaça).

## Pessoas

```js
const p = M.pessoa({ corpo:'m', pele: PELE[3], touca:'#fff', camisa:'#fff', avental: PAL.azulBR, calca:'#fff' });
p.root.position.set(x, 0, z); p.root.rotation.y = ang; cena.add(p.root);
M.segurar(p, 'D', OBJ.colher(), [0,-.05,.02], [-.6,0,0]);       // objeto na mão
S.update = t => ACAO.mexer(p, t, { T: 1.25 });
```
Opções: `altura, corpo ('h'|'m'), pele, cabelo, penteado ('curto'|'coque'|'rabo'|'black'|'longo'|'careca'), camisa, manga ('curta'|'longa'|'regata'), calca, bermuda, sapato, chinelo, avental, touca, bone, colete, gravata, cracha, luvas`.
Juntas: `p.tronco`, `p.cabeca`, `p.ombro.D/E`, `p.cotovelo.D/E`, `p.mao.D/E`, `p.coxa.D/E`, `p.joelho.D/E`, `p.quadril`.
`M.pose(p, {tronco:[x,y,z], cabeca, ombroD:[x,y,z], cotoveloD, maoD, coxaD, joelhoD, …, altura})` — sinais: ombro/coxa x < 0 = para a frente; cotovelo x < 0 = dobra; joelho x > 0 = dobra; tronco x > 0 = inclina para a frente; `M.SENTADO` = pernas de quem está sentado (cadeira de assento .46).
Ações (`ACAO.nome(p, t, {T, f, extra})`): `parado`, `mexer`, `chapear`, `lavar`, `varrer`, `digitar` (+`Tolhar`), `comer` (sentado), `conversar` (`sentado`), `pagar`, `andar` (`bandeja`). Andar por um laço: `M.caminho(p, curvaFechada, t, dur)` + `ACAO.andar(p, t, {T: dur / nPassos})` com `nPassos = round(comprimento / 1,3)`.
Objetos de mão (`OBJ.*`): `colher`, `espatula`, `prato`, `bandeja(n)`, `vassoura`, `cartao`, `garfo`. Bandeja e vassoura: prenda em `p.tronco` (`bandeja.position.set(.33,.31,.3)`; vassoura `(-.04,.12,.33)` com `rotation (-.3,0,-.12)`).
Ação nova = função que chama `M.pose` com ângulos em seno/cosseno de `ciclo(t, T)`; teste com a câmera colada (raio 16).

## HUD

- `M.cabecalho(S, {x, y, rotulo, titulo:['Linha 1', 'Linha 2.'], tam, sub:['…','…'], entrada})`
- `M.selo(S, {txt, relogio:[h,m,s], direita, y})`
- `M.painel(S, {x:'auto', direita, y, w, titulo, fig, blocos:[{tipo:'botoes', itens:[{txt, on, cor}], pulso}, {tipo:'stats', itens:[[rot, valor|fn]]}, {tipo:'chips', rot, itens:[{txt, cor}], ativo}, {tipo:'slider', titulo, val:fn|0–1, txt, de, ate}, {tipo:'linha'}]})`
- `M.rodape(S, {x, y, cab, frase, dados:[{rot, val|fn, uni}], nota})`
- `M.tela(S, ponto3D)` → px na tela (para pôr algo HTML sobre um objeto).

## Receitas de outros lugares (mesma planta: bloco 10 × 9, calçada em L, fachada à direita)

- **Padaria:** balcão de vidro com `salgado('paoDeQueijo')` + pães (`bola` alongada `#d79a52`), forno de lastro (caixa inox + porta de vidro com `MAT.luz('#ff9a3c')`), padeiro tirando assadeira (`ACAO.pagar` adaptado), cliente com sacola, letreiro "PADARIA PÃO DOURADO", piso `azulejo` bege.
- **Oficina mecânica:** piso de concreto (`tex.estrato('concreto',…)` como mapa) com mancha de óleo, carro sobre elevador (caixas), mecânico deitado (pose com `altura` −.8 e tronco x −1.5), compressor, pneus empilhados (`TorusGeometry`), estrato de cima `asfalto`.
- **Obra:** sem paredes de perto; laje, pilares, betoneira girando (`S.cada`), pedreiro assentando tijolo (`ACAO.lavar` com colher de pedreiro), servente com carrinho de mão (andar em laço), capacete = `bone` amarelo; estratos com fundação aparente (estaca de concreto cortada).
- **Feira:** sem paredes; barracas com `toldo` listrado (cores trocadas), caixotes de madeira com frutas (`bola`), feirante gritando (`conversar`), pastel e caldo de cana (cilindro + `vapor`).
- **Escritório/coworking:** mesas `mesa()` sem toalha, monitores com `MAT.luz`, pessoas `digitar`, uma andando com café (`andar` + copo), planta, persiana (listras), piso de madeira (`caixaTex` com `tex.madeira`).

## Ajuste fino

- Bloco maior ou menor no quadro: `raio` (9:16 ~55 para 10 m; proporcional ao tamanho do bloco). Mudou o tamanho do bloco → mude `raioSombra` (~= metade da diagonal + 2).
- Sombra mais dura: `sol.raio` 4–6; mais macia: 10–14 (VSM).
- AO mais forte nos cantos: `ao:{raio:.5, forca:1}`.
- Render: 5 s × 30 fps ≈ 30 s por formato num Mac M (`--conc=2` faz 9:16 e 16:9 juntos).
