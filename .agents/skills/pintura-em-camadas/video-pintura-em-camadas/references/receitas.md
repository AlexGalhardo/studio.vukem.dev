# Receitas — pintura em camadas

## Sumário
1. Camadas (camadas.py)
2. Página: esqueleto
3. API de `lib/pintura.js` (`window.PC`)
4. Variações

## 1. Camadas (camadas.py)

O formato completo do `camadas.json` está no cabeçalho de `tools/camadas.py`. Passo a passo para uma obra nova:

```bash
P=audio/.venv/bin/python; V=videos/02-nova
mkdir -p $V/img $V/masc
$P tools/commons.py buscar "The Third of May 1808 Goya" --n 12 --folha previews/c_obra.jpg
$P tools/commons.py baixar "File:….jpg" $V/img/pintura.jpg --largura 6000
$P tools/grade.py $V/img/pintura.jpg previews/grade.jpg --passo 50            # mapa geral (escala 1600 px)
$P tools/camadas.py vision $V/img/pintura.jpg $V/masc/v_frente.png --caixa .39,.48,.96,1
$P tools/camadas.py vision $V/img/pintura.jpg $V/masc/v_foco.png   --caixa .15,.14,.48,.57
$P tools/camadas.py prova  $V/img/pintura.jpg $V/masc/*.png --saida previews/mascaras.jpg
$P tools/grade.py $V/img/pintura.jpg previews/g_espada.jpg --caixa 560,120,800,320 --passo 10   # zoom para polígonos finos
cd $V && ../../$P ../../tools/camadas.py montar camadas.json
```

Esqueleto de `camadas.json` (pontos desenhados na grade de 1600 px, `escala_pts` = largura da obra / 1600):

```json
{
 "pintura": "img/pintura.jpg", "saida": "img", "limpar_borda": 8, "clarear_topo": [600, 1.17],
 "extensao": {"cima": 1400, "baixo": 600, "lados": 160},
 "camadas": [
  {"nome": "ceu", "K": 0.8},
  {"nome": "terra", "K": 0.93, "escala_pts": 2.4, "suave": 3, "mais": [[[0,318],[600,335],[1600,288],[1600,856],[0,856]]]},
  {"nome": "foco", "K": 1.0, "escala_pts": 2.4, "mascara": "masc/v_foco.png", "suave": 1.2,
   "mais": [[[626,166],[629.5,166],[640,236],[636,239]],
            {"pts": [[255,415],[760,440],[750,400],[255,390]], "suave": 9}]},
  {"nome": "frente", "K": 1.45, "escala_pts": 2.4, "mascara": ["masc/v_frente.png"], "suave": 1.5,
   "estender_baixo": 650, "modo_baixo": "reflexo"}
 ]
}
```

- **A 1ª camada é o fundo**: a obra inteira, sem máscara, com tudo o que está na frente apagado (inpainting) e estendida (`extensao`). Ela fica atrás de tudo, então pode ter K baixo (céu).
- **"terra"** é um polígono abaixo da linha do horizonte: separa o chão do céu, para o céu andar menos.
- **O chão sob a figura principal** vai junto com ela (polígono com `suave` 8–12): sem isso, os cascos/pés "patinam" sobre o chão.
- **Partes finas** (espadas, lanças, bengalas, braços erguidos, chapéus no ar): polígonos de 3–5 px na camada da figura. Desenhe olhando a grade com `--passo 10`.
- **Ordem** do fundo para a frente: a placa de cada camada apaga as da frente dela. Uma figura que aparece em duas máscaras fica na da frente; para tirar de uma, use `menos`.
- **Conferir**: depois do `montar`, renderize `--at` no fim do dolly (onde o parallax é máximo) e procure fantasmas, bordas retas e retângulos de céu (ver "Armadilhas" no SKILL.md).

## 2. Página: esqueleto

```html
<script>VIDEO={w:1080,h:1920,fps:30,dur:7.5,bpm:70,music:{style:'museu',key:'D',gain:-3}}</script>
<script>LIBS=['pintura.js']</script>
<script src="../../lib/boot.js"></script>
…  <div id="stage"> <div id="placa">…</div> <div id="titulo">…</div> <div id="credito">…</div> </div>
<script>
const stage = K.$('#stage');
window.SETUP = async () => {
  const P = await PC.carregar();                     // img/camadas-out.json + imagens decodificadas
  const [pw, ph] = P.pintura;
  const palco = PC.palco(stage, P, { dof: 30 });     // canvas das camadas
  const sala = PC.sala(palco, P, { borda: 170, brilho: [0, 2.6] });
  const facho = PC.facho(stage);
  const S0 = 940 / pw, poeira = PC.poeira(stage, { n: 60, S0, a: .2, r: 3.2 });
  PC.acabamento(stage, { vinheta: .42, luz: .3, grao: .06 });
  stage.append(K.$('#placa'), K.$('#titulo'), K.$('#credito'));   // HTML por cima do canvas
  const T = { para: 6.4, titulo: 6.55 };
  const cam = PC.camera({ S: […], A: […], sep: [1.9, T.para], atravessa: [1.9, 3.0], voo: 1.6, dissolve: [2.0, 2.9] });
  const placa = PC.placa(K.$('#placa'), { x: pw / 2 - 860, y: ph + 170 + 150 });
  onTick(t => { const c = cam(t); palco.quadro(c); sala(c, t); placa(c); facho.style.opacity = c.sala; poeira(t, c, 1); });
  PC.titulo(K.$('#titulo'), T.titulo);
  PC.som({ entra: 1.9, para: T.para, fim: VIDEO.dur });
  TL.set({}, {}, VIDEO.dur);
};
</script>
```

## 3. API de `lib/pintura.js` (`window.PC`)

| função | o que faz |
|---|---|
| `PC.carregar(url?, pasta?)` | lê `img/camadas-out.json`, carrega e decodifica cada imagem (`c.img`). Assíncrona: `await` no `SETUP`. |
| `PC.chaves([[t, v], …])` | interpolação cúbica monotônica (não passa do ponto, para com derivada zero). |
| `PC.camera({S, A, sep, sepEase, atravessa, voo, dissolve})` | devolve `t → {S, ax, ay, p, kw, sala}`. |
| `PC.palco(stage, P, {dof, foco, grade})` | cria o canvas; `.quadro(cam)` desenha as camadas (escala `S·K^p`, desfoque `dof·|1−foco/K|·p` ou `c.blur`); `.tela(x, y, cam, K)` converte um ponto da obra para a tela (para pôr rótulos presos a uma figura). |
| `PC.moldura(w, h, b, {res, seed, perfil})` | canvas da moldura dourada (vão transparente). `perfil`: `[[de, até, '#hex'], …]` do lado de fora para dentro. |
| `PC.sala(palco, P, {borda, parede, moldura, brilho, brilhoA})` | devolve `(cam, t) → desenha` parede com vão + sombra + moldura + brilho + sombra interna + luz sobre a tela, na escala `S·kw` e opacidade `cam.sala`. `parede`: 3 cores (centro → canto). |
| `PC.placa(el, {x, y})` | prende um `<div>` na parede (px da obra): `(cam) → posiciona/esmaece`. |
| `PC.titulo(root, t0, {de, ate, fio})` | entrada do título (`.sobre`, `.nome`, `.fio`, `.sob`). |
| `PC.som({entra, para, fim}, {cena})` | cues do estilo (ver `audio.md`). `cena: null` tira o galope. |
| `PC.poeira(stage, {n, S0, a, r, seed})` | `(t, cam, z0) → desenha` partículas de poeira com profundidade. |
| `PC.facho(stage)` | cone de luz do spot (controle a opacidade com `cam.sala`). |
| `PC.acabamento(stage, {vinheta, luz, grao})` | vinheta quente, véu de luz `soft-light`, grão. |

Campos extras por camada (no `camadas-out.json` ou mexendo em `P.camadas[i]` no `SETUP`): `blur` (px fixo), `blurExtra`, `alpha`, `dx`/`dy` (deslocamento em px de tela). Com `palco.quadro(cam, (c, cam) => { … })` dá para animar uma camada sozinha (ex.: bandeira que balança: `c.dx = Math.sin(t*3)*2`).

## 4. Variações

- **Afresco/arquitetura (como a Escola de Atenas):** em vez de moldura dourada, `PC.sala` com `moldura: {perfil: […]}` em tons de pedra e uma parede clara; a extensão em cima continua a abóbada pintada.
- **Obra vertical (retrato, retábulo):** quase não precisa de extensão; o museu pode durar mais (a obra já enche a altura com S ≈ 0,5).
- **Dois focos:** pare em um, faça um pan curto (chave em `A`) para o segundo e pare de novo. Mantenha S quase constante no pan para não parecer zoom de reportagem.
- **Sem texto:** apague `#placa`, `#titulo` e as chamadas; deixe só o crédito no fim.
- **Ritmo mais lento (10–12 s, como a referência):** estique as chaves de `S` proporcionalmente e mantenha 2 s parado no fim.
