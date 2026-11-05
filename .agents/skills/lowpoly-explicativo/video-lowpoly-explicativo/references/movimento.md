# Movimento — capítulos, tempos, câmera

## Sumário
1. Estrutura das referências
2. Roteiro-tipo de 8–12 s (o exemplo)
3. Câmera por capítulos
4. Tempos e eases medidos
5. Transições
6. O que se mexe dentro de cada capítulo

## 1. Estrutura das referências

As referências têm 60–93 s com narração. O padrão: abre com o objeto em close + pergunta ("O Waze não tem nenhuma câmera…") → plano geral da maquete → capítulos (o chip troca a cada 6–12 s) com corte, explosão, rótulos e painel → um caso curioso → volta ao começo com a conclusão. Cortes secos são raros (2–11 por minuto); quase tudo é câmera contínua com rack focus na entrada de cada plano. A legenda troca a cada ~1,8–2,6 s, a ~3 palavras/s.

Num vídeo curto (8–12 s), **comprima os capítulos, não o ritmo da legenda**: 3–5 capítulos de 2,3–3 s, uma frase de 5–9 palavras por capítulo.

## 2. Roteiro-tipo de 8–12 s (o exemplo, 11 s)

| t (s) | capítulo (chip) | plano | prova visual | legenda |
|---|---|---|---|---|
| 0–2,7 | A REPRESA | geral alto, rio na vertical da tela, dolly lento para frente | lago com setas indo para a barragem; rótulos "Reservatório", "Barragem" | "A represa segura a água do rio." |
| 2,7–5,3 | A QUEDA | lateral, perpendicular ao corte | maquete fatiada (seção hachurada, terra em faixas, água azul); fluxo de setas no conduto; cota "queda" | "Ela desce com força pelo conduto" |
| 5,3–8,0 | A TURBINA → O GERADOR | close na turbina, sobe e afasta | turbina acelera; painel 1-2-3; gerador explode na vertical; bobinas acendem; pulsos saem pelo cabo | "e empurra a turbina, que gira o gerador." |
| 8,0–11 | A CIDADE | geral alto em órbita, subindo | pulsos nos cabos; luz do estúdio baixa; janelas acendem da entrada da linha para longe; carimbo | "A energia viaja pelos fios e a cidade acende." |

Regras: o chip troca **no corte**; a legenda começa ~.15 s depois do corte e some ~.05 s antes do próximo; rótulos entram depois que a câmera assentou (≥ .4 s após o corte) e saem junto com o capítulo.

## 3. Câmera por capítulos (`LP.roteiroCamera`)

Cada plano: `{t0, t1, de:{pos, alvo}, ate:{pos, alvo}, ease, arco, fov, foco, abertura, rack, sombra}`.

- **Dolly** (padrão): posição e alvo interpolados; aproxime 15–25% da distância no capítulo. `ease: 'sine.inOut'` (ou `'sine.out'` no primeiro plano, que já começa andando).
- **Órbita** (`arco: true`): interpola raio, azimute e elevação em volta do alvo; bom para planos gerais e para a conclusão (gira 10–20° e sobe).
- **Grua** (subir e afastar): close na peça → vista do conjunto explodido; `power2.inOut`.
- **Rack focus** automático na entrada: foco começa a 3,2× a distância e a abertura em 1,6×, e assentam em `rack` = .45 s com `power2.out`.
- **`fov`:** 38–44 em planos gerais (9:16 é estreito), 30–34 em closes.
- **`sombra: [x,y,z,raio]`:** a caixa de sombra do sol acompanha o plano. Raio ≈ metade do que aparece na tela.
- A câmera nunca para: mesmo o último plano termina andando (o fim do vídeo é corte seco).

## 4. Tempos e eases medidos

| evento | duração | ease |
|---|---|---|
| rack focus na entrada do plano | .45 s | power2.out |
| chip: some o texto velho / pílula muda de largura / digita | .1 s / .25 s / ~45 letras/s | — / power3.out / linear |
| legenda: caixa entra / palavras | .14 s (escala .94 → 1) / proporcional ao tamanho | power2.out |
| rótulo: cartão / fio / anel | .25 s / .22 s / .7 s | back.out(1.7) / power2.out / power2.out |
| painel: entra / cada linha acende | .3 s / .25 s, com ~.5 s entre linhas | power3.out / power2.out |
| corte varrendo a maquete | .7 s (de 6,5 a 0 unidades) | power2.out |
| explosão | .7 s | back.inOut(1.4) |
| turbina acelerando | ~1,3 s até a velocidade de cruzeiro | quadrático |
| fluxo "ligando" (`qt` 0 → 1) | .5–.6 s | linear |
| luzes da cidade | ~1,4 s do primeiro ao último prédio, cada janela em ~.1 s | por distância da entrada |
| carimbo | 4 degraus em .12 s (escala 1,6 → 1) | steps |
| pino / peça brotando | .3 s | back.out(2.5) |

## 5. Transições

1. **Corte seco + rack focus** (a das referências): troca o plano da câmera no quadro; o novo plano nasce desfocado.
2. **Corte que abre**: no começo do capítulo, o plano de corte varre a maquete (a seção hachurada "passa" pelo objeto como uma lâmina).
3. **Grua para dentro/fora**: do conjunto para a peça (ou ao contrário) sem corte.
4. **Mudança de cena distante**: modelos isolados ficam longe na mesma cena (ex.: `(60,0,60)`) e o corte seco leva até eles.

## 6. O que se mexe dentro de cada capítulo (sempre 2+ camadas)

- câmera (dolly/órbita) + poeira subindo devagar (sempre);
- o mecanismo: fluxo de partículas, peça girando, explosão, corte, luz acendendo;
- a superfície: água ondulando (`agua`, `rio`), rodas, braços do boneco;
- o HUD: rótulo estalando, chip trocando, palavras acendendo.

Nada fica parado mais de ~.6 s.
