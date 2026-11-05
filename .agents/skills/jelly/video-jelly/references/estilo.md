# Estilo Jelly Bear — o que define o visual

Referência: "Crab Jelly" (caranguejo de gelatina num prato, HUD "MATERIAL STUDIES / DECAPODA"). Observado em quadros cheios:

## 1. Material: gelatina / bala de goma

- **Translúcida e saturada.** A luz atravessa e tinge o que está atrás: sobre o prato branco a goma fica clara e viva; onde é grossa (miolo do corpo) fica mais profunda. Não é vidro (não é límpida) nem plástico (não é opaca): é "leitosa" de leve.
- **Borda mais densa, miolo luminoso.** Na silhueta a cor escurece/satura; no centro, virado para a câmera, há um brilho interno quente. Na lib: termo `jMiolo·pow(n·v, 1.6)` somado e `mix(…, jBorda, (1−n·v)^2.2)`.
- **Verniz molhado.** Reflexo especular branco nítido (clearcoat 1, rugosidade 0,03) e transmissão um pouco borrada (roughness 0,2) — a combinação "por fora liso, por dentro turvo" é o que vende gelatina.
- **Inclusões.** Pontinhos escuros (sementes/açúcar queimado) e bolhas claras suspensos dentro, visíveis por refração. Densidade: ~340 por ursinho, 30% claras.
- **Olhos** pequenos, pretos, muito brilhantes (opacos, clearcoat), meio enterrados na goma.
- **Sombra colorida.** A sombra no prato é tingida da cor do sabor, mais escura perto do objeto, com um ponto mais claro (cáustica) do lado da luz. Nunca sombra cinza dura.

### Paleta de sabores (lib `SABORES`)

| sabor | cor (transmissão) | fundo (atenuação) | uso |
|---|---|---|---|
| morango | `#ff5c68` | `#ff1835` | vermelho morango |
| limão | `#b4f55a` | `#62c800` | verde |
| laranja | `#ffad4a` | `#ff7a00` | manga/laranja |
| uva | `#b882ff` | `#7a2cff` | roxo |
| abacaxi | `#ffe45a` | `#ffb800` | amarelo |
| framboesa | `#5aa0ff` | `#1a62ff` | azul framboesa |
| tijolo | `#ffb070` | `#ff7420` | goma de tijolo (terracota clara) |

Regra de elenco: cada personagem um sabor, e nunca o mesmo tom do que fica atrás dele ou do que ele carrega (tijolo laranja ≠ ursinho laranja/vermelho).

## 2. Movimento: tudo balança

- **Squash & stretch** a cada pisada/impacto (y encolhe, xz incha, pés plantados).
- **Cisalhamento ∝ altura²**: ao parar, o topo continua indo pra frente e volta (overshoot); ao arrancar, fica pra trás.
- **Onda que sobe** pelo corpo depois do impacto e some (amortecimento ~0,15–0,2; frequência 3–5 Hz; peças pequenas mais rápidas).
- Personagens de goma andam com passos curtos (0,3 s), quicando um pouco (`sobe`), e os braços são tocos que balançam.
- Câmera: quase parada, deriva periódica pequena (±4° de azimute, ±0,8° de elevação) — o loop fecha.

## 3. Vitrine e luz

- **Estúdio creme claro** (`#e6e4e0` → `#dedbd6`), chão infinito sem horizonte (neblina da cor do fundo), vinheta muito leve.
- **Prato branco de porcelana** (torno, aba levantada, verniz), com sombra macia embaixo — é o "pedestal" do espécime.
- **Luz suave lateral**: principal vindo de trás-direita (deixa a goma contraluz e acende o miolo), preenchimento frio da frente-esquerda (pinta o reflexo branco), ambiente de estúdio (RoomEnvironment) para reflexos retangulares. Tone mapping Neutral (brancos limpos, cores saturadas).
- Sem profundidade de campo forte, sem bloom: a referência é nítida, de produto.

## 4. HUD editorial (estudo de material)

- **Rótulo** versalete pequeno espaçado com fio embaixo: `ESTUDOS DE MATERIAL / TEMA`.
- **Título** enorme em serifa itálica (Nova York), 2 linhas, entrelinha 0,84, terminado por um **ponto colorido** da cor do sabor em destaque (troca junto com o painel).
- **Subtítulo** itálico de 2 linhas, tom poético curto.
- **Pílula** "● AO VIVO · ESTADO" no canto.
- **Painel do espécime** (claro, borda fina): título versalete + sabor atual em itálico; botões de ação em serifa itálica com "TECLA n"; linha de sabores (bolinhas com brilho); sliders Firmeza / Amortecimento / Luz com extremos; botões Reiniciar / Pausar / ¼ velocidade.
- **Dados** embaixo à esquerda: instrução com verbos em negrito, campos com rótulo mono e valor em serifa itálica grande + unidade mono, nota técnica mono clarinha. Rodapé "DENTRO DO … +".
- Cores do HUD: tinta `#26221e`, cinzas quentes `#5c554d` / `#8d857b` / `#d6cfc4`; painel `rgba(251,249,246,.86)`.

## 5. Composição 9:16

- Título ocupa ~0–620 px à esquerda; painel ~170–760 px à direita; prato do meio para baixo (~700–1600 px); dados de 1650 px para baixo.
- O prato pode vazar pelas laterais (fica mais "close"); personagens com ~280 px de altura.
- Coisas altas à esquerda/centro; à direita do fundo só peças baixas (o painel cobre).
