# Receitas — API e passo a passo

## Sumário
1. Página mínima
2. API de `lib/laminas.js` (global `LA`)
3. Fotos: achar, recortar, normalizar
4. `especimes.json` (lista de exemplares)
5. Outros acervos (conchas, minerais, folhas…)
6. Problemas comuns

## 1. Página mínima

```html
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<script>VIDEO={w:1080,h:1920,fps:60,dur:64/9,bpm:135,music:{style:'gabinete',key:'F',gain:-1,laco:true}}</script>
<script>LIBS=['laminas.js']</script>
<script src="../../lib/boot.js"></script>
<script src="especimes.js"></script>                       <!-- gerado por tools/especime.py -->
<style>#stage{background:#e9ecd9}</style></head><body>
<div id="stage"></div>
<script>
const ORDEM = ['b01','b19','b08', /* … 64 ids … */];
LA.palco();
const col = LA.colecao(LA.ordenar(ESPECIMES, ORDEM), { x: 540, y: 860, faixa: [235, 1475] });
LA.cabecalho('Coleção entomológica', { y: 168 });
LA.etiqueta(col, { y: 1530 });
LA.creditos('Fotos de exemplares de museu via Wikimedia Commons: Fulano (CC BY-SA 4.0) · …', { y: 1818 });
window.SETUP = async () => { await col.pronto(); LA.sons(col); };
</script></body></html>
```

## 2. API de `lib/laminas.js`

| chamada | o que faz |
|---|---|
| `LA.palco({fundo, tinta, apagado})` | pinta o `#stage` (padrão `#e9ecd9`, `#2a2c22`, `#7c7f6d`) e injeta o CSS do estilo. Chame antes do resto. |
| `LA.ordenar(lista, ids)` | devolve os exemplares de `ESPECIMES` na ordem dos ids (erro se faltar algum). |
| `LA.colecao(itens, o)` | cria um `<img>` por exemplar com o **centro do corpo** (`cx,cy`) em `(o.x, o.y)`; mostra um por vez: `idx(t) = floor((t − t0)·ritmo)`. Opções: `x`, `y`, `t0` (0), `ritmo` (9), `escala` (1), `faixa:[topo,base]` (antena não passa), `laco` (true: depois do último volta ao 1º; false: fica no último), `realce` ({sat:1.12, con:1.04, luz:1} ou `false`). Devolve `{n, itens, imgs, idx(t), tempo(k), dur, pronto()}`. |
| `col.pronto()` | `await` no SETUP: decodifica todas as imagens antes do 1º quadro. |
| `LA.cabecalho(txt, {y})` | versal espaçada com fios dos dois lados. |
| `LA.etiqueta(col, {y, grupos, prefixo, largura})` | etiqueta que troca junto com o exemplar: `GRUPO · Ordem` / *nome* / `nº 001 / 064`. `grupos` acrescenta/reescreve `LA.GRUPOS` (`{chave: {nome, ordem}}`); a chave é o campo `g` de cada exemplar. Nome comprido encolhe para caber em `largura` (960). |
| `LA.creditos(txt, {y})` | rodapé de 15 px; cada "Autor (licença)" separado por ` · ` não quebra no meio. |
| `LA.sons(col, {acento, ganhoFlip, ganhoGaveta, ganhoMadeira})` | cues: `madeira` no 1º exemplar, `gaveta` 0,3 s antes de cada troca de grupo, `flip` em toda troca (0 dB nos tempos, −4 dB no resto, pan leve). |
| `LA.alternar(ids, cores, primeiro)` | ordem gulosa de contraste máximo entre vizinhos (`cores = {id: [L,a,b]}`). |
| `LA.GRUPOS` | besouros, lepidopteros, borboletas, mariposas, cigarras, percevejos, abelhas, libelulas, gafanhotos (nome pt-BR + ordem). |
| `LA.RITMO`, `LA.FUNDO`, `LA.TINTA`, `LA.APAGADO` | constantes do estilo. |

`ESPECIMES` (de `especimes.js`): `[{id, src, w, h, cx, cy, g, nome}]` — `src` relativo à pasta do vídeo, `w,h` já em px de tela, `cx,cy` = centro do corpo dentro da imagem.

## 3. Fotos: achar, recortar, normalizar

**Achar** (só CC0, domínio público, CC BY, CC BY-SA; `--claro` descarta fotos sem fundo liso claro):

```
$P -I tools/colecao.py buscar \
  'deepcategory:"Coleoptera of Brazil" Schmidt' 'deepcategory:"Coleoptera of Brazil" filetype:png' \
  --n 80 --claro --json previews/busca/a.json --folha previews/busca/a.jpg
# fundo preto (mariposas do MHNT): --claro --min-brilho -1  (aceita qualquer fundo uniforme)
```

Consultas que renderam bem:

| busca | o que vem |
|---|---|
| `deepcategory:"Coleoptera of Brazil" Schmidt` / `filetype:png` | Udo Schmidt: crisomelídeos, escaravelhos, buprestídeos em fundo branco (cabeça à esquerda → `rot: 90`) |
| `deepcategory:"Coleoptera of Brazil" Bennyboymothman` | Ben Sale: serra-paus e buprestídeos em pares (dorsal à esquerda), cabeça para cima |
| `deepcategory:"Lepidoptera of Brazil" Descouens` | borboletas do MHNT; prefira os arquivos "… MHNT dos.jpg" (só a face dorsal) |
| `deepcategory:"Lepidoptera of Brazil" MHNT dorsal` | mariposas esfingídeas do MHNT em fundo preto, com localidade no Brasil |
| `deepcategory:"Insects of Brazil" …` | troque a ordem/família/fotógrafo |

`deepcategory:` garante que a espécie está numa categoria "… of Brazil" (útil quando o tema é "do Brasil"; mesmo assim, não escreva "do Brasil" no vídeo sem conferir).

**Recortar e normalizar** (lê `especimes.json`, grava tudo na pasta do vídeo):

```
$P -I tools/especime.py preparar videos/01-x/especimes.json      # todos
$P -I tools/especime.py preparar videos/01-x/especimes.json --so b07,b12   # refaz só esses
$P -I tools/especime.py creditos videos/01-x/creditos.json       # linha de autores
```

Saídas: `img/esp/<id>.webp` (alfa, tamanho de tela), `especimes.js`, `creditos.json`, `fontes/` (originais baixados — não vão para a skill nem para o vídeo) e `previews/especimes.jpg` (todos no creme, com id, nome e tamanho). **Abra a folha sempre.**

## 4. `especimes.json`

```json
{"saida": "img/esp", "alvo": 560, "caixa": [900, 1150],
 "itens": [
  {"id": "b01", "t": "File:Eumolpus ignitus Fabricius, 1787 (11206106423).png", "g": "besouros", "rot": 90},
  {"id": "b32", "t": "File:Psiloptera attenuata (Fabricius, 1793) - Espirito Santo, Brazil - Flickr.jpg", "g": "besouros", "rot": 0},
  {"id": "b39", "t": "File:Buprestidae - Euchroma gigantea.jpg", "g": "besouros", "vision": true},
  {"id": "l08", "t": "File:Caligo martia.jpg", "g": "lepidopteros", "caixa": [0, 0, 0.5, 1]}
 ]}
```

| campo | efeito |
|---|---|
| `rot` | giro horário em graus antes de normalizar (90: cabeça da esquerda vai para cima; −90: da direita; 180: de baixo) |
| `lado` | `"esq"` (padrão) / `"dir"`: com dois exemplares grandes na foto, fica com esse |
| `caixa` | recorte em frações antes de tudo (ex.: metade esquerda de uma prancha dorsal+ventral) |
| `t0`, `t1` | limiares de distância ao fundo (14, 46). Suba (24–32 / 56–64) se sobrar sombra. |
| `vision` | `true`: intersecta com a máscara do Vision (macOS) — resolve sombra forte em fundo não branco |
| `alvo`, `caixa_tela` | tamanho por exemplar (raiz da área em px; caixa máxima [w, h]) |
| `nome` | sobrescreve o nome tirado do título (o padrão pega "Gênero espécie", tira subgênero, família e autor) |
| `largura` | largura pedida ao Commons (2600) |

## 5. Outros acervos

O estilo funciona com qualquer coisa que tenha "exemplar de coleção fotografado de cima em fundo liso":

| acervo | busca no Commons | grupos (`grupos:` em `LA.etiqueta`) |
|---|---|---|
| conchas | `shell specimen white background`, `"Conus" shell MHNT` | `{conchas:{nome:'Conchas', ordem:'Mollusca'}}` |
| minerais | `mineral specimen Rob Lavinsky` (CC BY-SA, fundo preto) | `{minerais:{nome:'Minerais', ordem:''}}` |
| sementes, folhas, penas | `seed specimen white background`, `herbarium` (cuidado: exsicata tem papel e etiqueta) | |
| moedas, botões, selos | objetos de museu em domínio público (Smithsonian, Met Open Access) | |

Para fotos de objeto redondo/sem "cabeça", `rot: 0` e o centro do corpo é o centro do objeto.

## 6. Problemas comuns

| sintoma | causa | conserto |
|---|---|---|
| imagem não aparece no render | `.webp` sem MIME no servidor ou `col.pronto()` fora do SETUP | o `render.mjs` daqui já serve `image/webp`; mantenha `await col.pronto()` |
| exemplar "pula" de lado entre trocas | centro pela caixa, não pelo corpo | use `cx,cy` do `especime.py` (já é o padrão de `LA.colecao`) |
| antena passa por cima do cabeçalho | exemplar comprido centrado pelo corpo | `faixa: [235, 1475]` |
| mancha clara do corpo virou buraco | buraco grande e claro (élitros creme sobre fundo branco) | baixe `t0`/`t1` (10/36) para esse item |
| halo cinza em volta | foto JPEG com fundo sujo | suba `t0`; o halo do fundo branco já é removido |
| créditos quebrando "CC BY-/SA" | — | `LA.creditos` já agrupa por " · "; não escreva licenças sem espaço normal |
