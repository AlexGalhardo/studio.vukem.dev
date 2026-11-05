# Estilo — low-poly explicativo

Lido de 5 referências do mesmo formato (Reels 720×1280, 30 qps, 60–93 s, narração + legenda): freios de elevador (variante clara), como funciona o Waze, overbooking, batimento no relógio, divisão de fazenda. O demo recompõe tudo em 1080×1920 e 60 qps.

## Sumário
1. As 3 marcas
2. Paleta
3. Tipografia
4. Materiais e modelagem
5. Luz, desfoque e acabamento
6. Composição 9:16 (zonas da tela)
7. HUD peça por peça
8. Variantes

## 1. As 3 marcas

1. **Maquete de massinha low-poly sobre azul-noite.** Peças geométricas simples (caixas chanfradas, cilindros de poucas faces, icosaedros), foscas, sem textura; quase tudo branco/cinza-claro com **um** acento laranja; o fundo é um gradiente azul-noite com poeira branca (e algumas laranja/azuis) em bokeh. O desfoque de profundidade forte faz tudo parecer miniatura.
2. **HUD "COMO FUNCIONA · TEMA".** Cabeçalho mono espaçado em cinza, chip-pílula escura (bolinha branca + ponto laranja + capítulo em mono negrito maiúsculo), rótulos com fio fino até um ponto no objeto, painéis e placares escuros, carimbo laranja inclinado.
3. **Legenda karaokê + câmera que conduz.** Caixa escura arredondada embaixo, palavras acendendo de cinza para branco no ritmo da fala; cada capítulo é um plano que entra desfocado e ganha foco enquanto a câmera desliza ou orbita, e a maquete se abre (corte) ou se separa (explosão) para mostrar o mecanismo.

Tudo o que você fizer deve servir a essas 3 coisas. Se um quadro não tem maquete + HUD + legenda, ele não é do estilo.

## 2. Paleta (`LP.PAL`)

| papel | hex |
|---|---|
| fundo (gradiente, de cima para baixo) | `#151a24` → `#1c212b` → `#0b0d12` |
| massinha clara / gelo / cinza | `#e8ebf0` / `#c9cfd8` / `#9aa1ab` |
| grafite / carvão (máquinas, rodas, cabos) | `#424852` / `#272b33` |
| **acento** (1 objeto por capítulo, chips, carimbo, números) | `#ff6a2a` |
| verde / azul / vermelho de sinal (pinos, ímãs, estados) | `#3ccf8e` / `#4f8cff` / `#ff4d4d` |
| energia (pulsos, janelas acesas) | `#ffc94a` / `#ffcf73` (com brilho) |
| água (lâmina / seção / fluxo) | `#3f8fdc` / `#4b90d8` / `#8fd0ff` |
| natureza (grama 3 tons, folhas 3 tons, tronco) | `#86b26a` `#6f9e58` `#9cc27a` · `#5f9c56` `#7fb35f` `#4c8a4f` · `#80614a` |
| seção de corte: concreto (hachura) / terra (faixas) | `#c3cad4` + `#a7b0bc` / `#7d5a43` `#a8744f` `#c48a5c` |
| texto: branco / apagado / mono | `#ffffff` / `#7b818b` / `#8b9099` |

Regra: no máximo **uma** cor saturada por capítulo, além do laranja do HUD. A natureza pode ter verde e azul, mas com saturação de massinha (nada neon).

## 3. Tipografia

- **Legenda:** Geist 700, 49 px, entrelinha 1,18, tracking −.012 em; ditas `#fff`, próximas `#7b818b`; caixa `rgba(20,23,29,.9)`, raio 20, padding 22/34, centro em y = 1480 (77%), largura máx. 860.
- **Cabeçalho:** JetBrains Mono 500, 23 px, tracking .26 em, `#8b9099`, maiúsculas, em (69, 285).
- **Chip:** JetBrains Mono 700, 31 px, tracking .17 em, branco, altura 70, em (62, 330).
- **Rótulo:** título Geist 700 33 px com bolinha vazada; subtítulo JetBrains Mono 500 20 px, tracking .14 em, cinza, maiúsculas.
- **Painel/placar:** cabeçalho mono 20 px; linhas Geist 700 36 px; números Geist 800 84 px (o da direita em laranja).
- **Carimbo:** JetBrains Mono 800 46 px, texto quase preto `#1a1410` sobre laranja, giro −5° a −6°.

## 4. Materiais e modelagem

- `MeshStandardMaterial` fosco (`roughness` .82, `metalness` 0), `flatShading` nas peças "low-poly" (terreno, árvores, rochas, máquinas) e sombreamento liso nas peças "massinha" (carro, boneco, caixas chanfradas).
- Cada objeto: 2–6 primitivas. Chanfro em toda caixa (`LP.caixa`, ~12% do menor lado). Cilindros com 8–16 faces, esferas como icosaedro de detalhe 0–1, sacudido de leve (`LP.facetar`).
- Natureza low-poly: terreno por função de altura com cor por face (grama em 3 tons por ruído, rocha nas encostas íngremes); árvore = tronco de 5 faces + copa de icosaedro sacudido ou 3 cones de 6 faces.
- **A maquete é um bloco**: terreno com saia de terra e fundo (fica "flutuando" no escuro, como peça de museu), água com volume translúcido.
- Brilho só no que é energia/sinal: `LP.brilho(cor, forca)` (MeshBasic sem tone mapping, passa no bloom).

## 5. Luz, desfoque e acabamento (`LP.palco`)

- Céu suave (hemisférica `#e4ebff` / `#2b3039`, 1,5) + sol morno com sombra macia (`#fff2e0`, 2,4, vindo de cima-esquerda-frente) + borda azulada por trás (`#9fb8ff`, 1,0). Tone mapping Neutral (cores fiéis).
- **Desfoque de profundidade** (passe próprio, coletando 260 amostras em espiral): `abertura` .014–.02, `max` 34 px. Foco = distância ao alvo do plano (+ `foco` para ajustar). O fundo sempre derrete; partículas viram bolinhas de bokeh.
- Bloom suave (`forca` .42, `raio` .5, `limiar` .92) — só janelas, pulsos, LEDs e bobinas passam.
- Acabamento: vinheta .38 e grão .03.
- Capítulo final pode "anoitecer": baixe sol e céu (2,4 → 1,55 e 1,5 → .95) para as luzes acenderem com força.

## 6. Composição 9:16 (zonas da tela, 1080×1920)

| zona | y (px) | o que vai |
|---|---|---|
| margem de cima | 0–270 | céu escuro, poeira; topo da maquete pode passar por aqui desfocado |
| cabeçalho + chip | 285–400 | fixo, sempre visível |
| painel / placar / numeral de capítulo | 430–720 | só quando o capítulo pede |
| **objeto do capítulo** | ~480–1380 (25%–72%) | a prova visual; rótulos em volta |
| legenda | ~1420–1540 | caixa centrada |
| carimbo | ~1250–1300 | sobre a maquete, acima da legenda |
| margem de baixo | 1560–1920 | maquete desfocada (chão, base), poeira |

- Em 9:16 o campo horizontal é estreito: com `fov` 40 vertical o horizontal é ~23°. Para mostrar algo de 11 unidades de largura, afaste a ~25. Coloque o eixo do processo (rio, cabo, cano) **na vertical da tela** sempre que puder: a altura sobra, a largura não.
- Rótulos: cartão a 40–90 px do ponto, para o lado com mais espaço; nunca sobre a legenda.

## 7. HUD peça por peça

- `LP.cabecalho(S, 'COMO FUNCIONA · TEMA', [{t, txt}…])` — o chip troca: some em .1 s, a pílula muda de largura (.25 s, `power3.out`) e o novo nome é digitado a ~45 letras/s; o ponto laranja pulsa.
- `LP.legenda(S, [{t0,t1,txt,fala?}…])` — uma frase por capítulo; as palavras dividem `fala` (padrão 78% da janela) em proporção ao tamanho.
- `LP.rotulo(S, {alvo, titulo, sub, t0, t1, lado, dx, dy})` — cartão estala com `back.out(1.7)` em .25 s, fio se estica em .22 s, ponto estala e um anel se expande e some (.7 s).
- `LP.painel`, `LP.placar`, `LP.cota`, `LP.carimbo`, `LP.tituloCapitulo` — ver `receitas.md`.

## 8. Variantes

- **Escura (padrão, refs Waze/overbooking/batimento):** o que está acima.
- **Clara (ref. elevador):** `LP.palco({fundo:['#efe6d6','#e6dccb','#d9cdb8'], ceu:'#ffffff', chao:'#b9ad98'})`, poeira com `cores:['#ffffff','#c9bfae']`, `tituloCapitulo` para abrir cada capítulo com numeral colorido (laranja, vermelho, roxo, azul, verde em sequência). Mantenha o HUD escuro: ele contrasta com o bege.
- **Mapa/terreno visto de cima (ref. fazenda):** câmera alta (`fov` 30, de cima a ~60°), terreno em retalhos de verde e amarelo, rótulos e documentos em cartões; legenda pode virar faixa amarela (`.lp-leg{background:#ffd400;color:#111}`).
