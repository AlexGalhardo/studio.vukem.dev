# Desenhar no traço simples

Tudo é SVG gerado por funções de `lib/traco.js` (objeto global `TR`). Cada desenho é uma **string** com alguns `<path>` empilhados: o primeiro fica atrás e o último na frente.

As receitas abaixo estão desenhadas em `videos/folha-de-desenho/index.html`. Para ver todas lado a lado:

```bash
node render.mjs folha --at=0.5
```

Ponha cada desenho novo nessa folha **antes** de animar. É muito mais rápido acertar a forma num quadro parado.

## API

```js
const P = TR.P, { blob, poly, star, line, G, caixa, gota, olho, tf, show, E, pop, q12, whip, janela, f1 } = TR;

blob(cx, cy, rx, ry, cor, { n: 11, j: .05, rot: 0 })  // redondo cortado à mão (cabeça, corpo, pata, nuvem, mancha)
poly([[x, y], ...], cor, { j: 3 })                     // arestas retas, vértices tortos j px (casa, perna, telhado, faceta)
star(cx, cy, pontas, rFora, rDentro, cor, { j: .12 })  // estrela irregular (estouro, selo, brilho)
caixa(x, y, w, h, raio, cor, { j: 3 })                 // retângulo de canto redondo torto (tela, pasta, cartão, relógio)
gota(cx, cy, r, cor)                                   // pino de mapa / gota (ponta para baixo)
line('M.. Q..', cor, largura)                          // traço grosso de ponta redonda (boca, ruga, costura, alça)
olho(x, y, r)                                          // bola preta + brilho branco (o olho padrão)
G('id', inner)                                         // <g id> para animar uma parte
TR.IC.nome(cores)                                      // ícones prontos (~±70 px): heart star8 aster tri dots rosette house sock ball disc bone paw bowl hydrant collar mutt sausage leash
```

- **Sementes:** cada chamada usa uma semente nova (contador global), então duas bolhas iguais saem levemente diferentes, como recortes de verdade. Para fixar um formato, passe `{ seed: 123 }`.
- **Animação:** no tick, use `tf(el, x, y, escala, rotação, escalaY)` para posicionar um grupo e `show(el, bool)` para ligar e desligar.

## Como montar um objeto

1. **Desenhe em coordenadas locais**, com o centro do objeto em (0,0) e cabendo em ~±250 px. O grupo é posicionado no tick (`tf(EL.obj, 540, 900, s, r)`), então o pop e a rotação acontecem em volta do centro.
2. **Empilhe de trás para frente:**
   - partes de trás: orelha de trás, rabo, pernas de trás, língua que sai por baixo;
   - corpo e cabeça;
   - manchas e facetas;
   - rosto: olhos, nariz, boca;
   - acessórios: coleira, pino, brilho.
3. **Use de 2 a 6 formas grandes.** Se precisar de mais de ~10, você está desenhando detalhe demais.
4. **Dê volume sem sombra:** um brilho branco pequeno (blob achatado e girado) no alto da forma principal, ou uma segunda forma de outra cor (facetas, miolo da orelha, barriga).
5. **Isole o que mexe:** cada parte animada vai num `G('id', ...)`.
   - **Para girar em volta de uma junta**, use o pivô no atributo: `el.setAttribute('transform', \`rotate(${a} pivôX pivôY)\`)`. Orelha gira pelo alto, rabo pela base, perna pelo quadril, língua pela raiz.
   - **Para peças que brotam uma a uma** (pintas, pompons, pinos), desenhe cada uma em (0,0) dentro de um `<g class>` e posicione no tick com `tf(g, x, y, pop(...))`. Assim cada peça cresce do próprio centro.

## Receitas

### Cabeça de frente (cachorro, gato, urso, pug)

```js
poly([[-150, -40], [-120, -190], [-40, -120]], P.R) + poly([[-130, -70], [-115, -160], [-70, -115]], P.M)   // orelha + miolo (gato)
// cachorro: orelhas caídas = blob(±185, 10, 70, 135, P.k, { rot: ±18 }) ANTES da cabeça, pivô em (±170, -110)
+ blob(0, 10, 175, 150, P.R, { j: .03 })                    // cabeça (j baixo = forma calma)
+ blob(0, 105, 135, 95, P.W)                                // focinho mais largo embaixo (opcional)
+ olho(-62, -5, 24) + olho(62, -5, 24)                      // olhos afastados = fofo
+ blob(0, 62, 42, 30, P.k)                                  // nariz (gato: poly triangular rosa)
+ line('M-46 118Q-20 140 0 116Q20 140 46 118', P.k, 9)      // boca em "w"
```

**Olhos grandes e expressivos** (pug, mascote): esclera `blob(..., P.W)`, depois a pupila preta deslocada para onde olha, depois um brilho branco pequeno. Para piscar, mude a escalaY do grupo do olho ou desça uma "pálpebra" (um `<rect>` da cor da pele ou preto).

### De perfil (corpo comprido)

- **Corpo:** cápsula, que pode ser um `blob` largo ou um path com as pontas redondas.
- **Cabeça:** `blob` na frente, mais o focinho (outro `blob` alongado, `rot` de 4°), nariz preto na ponta e **um** olho só.
- **Orelha:** caída **por cima** da cabeça (desenhada depois).
- **Pernas:** `poly` de 4 pontos desenhada com a origem no quadril (`[[-21, -10], [21, -10], [18, 84], [-18, 84]]`) mais a pata (`blob`) no pé. Para andar, gire a perna em volta de (0,0) com `Math.sin(q12(t) * 26 + fase) * 30`, alternando a fase entre as pernas.

### Corpo que estica (dachshund, cobra, trem, minhoca)

O corpo é um `<path id="corpo">` **sem `d`**, e o `d` é refeito a cada quadro a partir das duas pontas:

```js
const xf = -260 + 1050 * E('power3.out', t, t0, t0 + .4);       // frente chega rápido
const xb = -1350 + 1600 * E('back.out(1.25)', t, t0, t0 + .78);  // traseira chega depois, com mola
EL.corpo.setAttribute('d', `M${xb + 75} 905H${xf - 60}C${xf + 20} 905 ${xf + 20} 1055 ${xf - 60} 1055H${xb + 75}C${xb - 25} 1055 ${xb - 25} 905 ${xb + 75} 905Z`);
tf(EL.cabeca, xf, 0);                        // cabeça acompanha a frente
EL.rabo.setAttribute('transform', `translate(${xb} 0) rotate(${ang} 0 920)`);
```

### De costas (corgi, gato sentado)

Desenhe a cabeça e as orelhas **atrás**, as pernas, depois o "bumbum": o corpo grande e, por cima, a forma clara (no corgi, um coração de cabeça para baixo: dois `blob` mais um triângulo com a ponta para cima). Para rebolar, gire o grupo do bumbum em volta de um ponto **acima** dele (`rotate(a 0 -110)`) e levante a perna do lado contrário.

### Pernas andando (pessoa, sem tronco)

São duas pernas de calça, cada uma com coxa e canela (`poly` de 4 pontos) mais uma bolha no joelho para arredondar, um sapato `blob` girado e o cós com `caixa`. Para animar, alterne quadros-chave de pose a 12 qps em vez de girar suave.

### Objetos

| objeto | formas |
|---|---|
| notebook | tela preta (`poly` em paralelogramo) + ícone `caixa` + base violeta (`poly`) + trackpad lima |
| pasta | fundo com aba (`poly`) + papel branco saindo + frente `caixa` **um pouco mais larga que o fundo** (cobre as bordas) + etiqueta `blob` |
| relógio | `caixa` com raio grande + centro preto + 2 ponteiros `caixa` em `<g transform="rotate()">`. Para animar, gire os ponteiros em degraus. |
| globo | `blob` violeta + 2 ou 3 continentes `blob` verdes por dentro + pinos `gota` vermelhos com furo preto |
| gema / objeto precioso | contorno `poly` + 3 facetas `poly` de outra cor + brilho branco |
| casa | corpo `poly` + telhado triângulo + porta (retângulo preto + `blob` preto em cima) |
| flor | caule `line` grosso + folha `blob` girado + 6 pétalas `blob` em círculo + miolo |

### Mascote (encerramento)

Uma silhueta preta (cabeça `blob`, orelhas e focinho) com olhos brancos grandes, pupila que se move e pálpebra preta (`<rect>`) cobrindo o topo do olho. Isso dá o olhar "de lado", meio sonolento. Para animar, troque o olhar em degraus (`TR.passo`), pisque com a altura da pálpebra (20 → 74 → 20 em ~0,14 s) e ponha a língua magenta saindo por baixo com `back.out`.

## Ícones novos (para o campo)

Um ícone é uma função `cores => string`, centrada em (0,0), com ~±70 px, usando 1 a 3 cores do array:

```js
const lata = c => caixa(-34, -50, 68, 100, 12, c[0]) + poly([[-34, -20], [34, -20], [34, 10], [-34, 10]], c[1], { j: 1.5 }) + blob(-14, -36, 8, 5, P.W, { n: 6 });
TR.campo(gCampo, { icones: [[lata, [P.R, P.W]], ['heart', [P.M]], ...], t0, tSaida });
```

Para o campo ficar rico, faça de 12 a 20 tipos, cada um com 2 ou 3 combinações de cor, e misture ícones "temáticos" com formas genéricas (`tri`, `aster`, `dots`, `star8`).
