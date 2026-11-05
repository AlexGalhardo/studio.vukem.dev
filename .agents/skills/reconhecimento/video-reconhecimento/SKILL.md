---
name: video-reconhecimento
description: Diz, trecho por trecho de um vídeo, se a pessoa está OLHANDO PARA A CÂMERA, LENDO (roteiro, teleprompter, papel na mesa) ou SEM ROSTO no quadro, e grava transcricao/olhar.json e olhar.md com os tempos. Mede rosto, giro da cabeça e direção dos olhos com o que já roda na máquina - o Vision da Apple no Mac (Swift compilado na hora, sem baixar nada) e o OpenCV no Linux e no Windows -, amostrando pouco quadro por segundo e tratando a trava do detector. Separa o material em dois grupos sozinho e pergunta qual é o da câmera, ou calibra por um XML do Premiere com os clipes marcados de verde. Use quando o usuário disser "onde ele olha para a câmera", "onde ele está lendo", "marca os trechos em que o apresentador aparece", "o trecho lido tem de ser coberto por animação", "acha onde não tem rosto". Difere das irmãs - video-cortes-verticais usa o rosto para enquadrar vertical, video-decupagem corta pela fala, não pelo olhar.
---

# video-reconhecimento

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

Há uma regra de edição que vale ouro em vídeo longo: **apresentador lendo nunca aparece na tela.** Ele só
aparece quando olha para a câmera; onde está lendo, entra animação, b-roll ou cartela. Para cumprir isso
alguém precisa dizer, minuto a minuto, onde ele olhou para a câmera — é o que esta skill faz. O
`transcricao/olhar.json` que ela grava é lido depois pela montagem, pela cobertura de animação e pelo QA.

## Fluxo

1. **Meça**: `python3 scripts/reconhecer.py bruto/x.mp4 --saida transcricao/ --fps 1 --folha`
   O `--folha` grava `transcricao/olhar_grupos.jpg` com quadros dos dois grupos.
2. **Diga qual grupo é a câmera.** Sem calibração o rótulo é PALPITE e a skill avisa. Abra a folha, mostre ao
   usuário e rode de novo com `--grupo-camera A` (ou `B`).
3. **Ou calibre de verdade**: se o usuário tiver uma sequência do Premiere com os clipes de "olhando para a
   câmera" marcados de **verde**, exporte-a em Final Cut Pro XML e rode
   `--calibrar decupagem_rotulada.xml`. A skill mede o acerto contra o rótulo do editor e grava o número no
   `olhar.json` — é a única forma de saber se acertou.
4. **Use o resultado**: cada trecho tem `t0`, `t1`, `estado` (`camera` / `lendo` / `sem_rosto`) e `confianca`
   (quanto das amostras cruas já concordava antes do alisamento).

Opções úteis: `--trecho-min 1.5` (trecho menor que isso é absorvido pelo vizinho — evita piscar),
`--inicio`/`--fim` para medir só um pedaço, `--conf-min` para exigir rosto mais firme, `--grupo-min` (veja
"um jeito de olhar só", abaixo).

## Como ele decide (e por que não há limiar fixo)

Não existe número universal de "olhando para a câmera": depende da altura da câmera, da lente, da distância e
de onde está o teleprompter. Por isso a skill **não** usa limiar fixo:

1. mede por amostra: caixa do rosto, `roll`/`yaw`/`pitch` da cabeça, para onde a pupila aponta dentro do olho
   (`olho_x`, `olho_y`) e quanto o olho está aberto (`abertura`);
2. normaliza tudo pela mediana e pela dispersão **do próprio vídeo**;
3. separa em **dois grupos** com k-médias de semente determinística (mesmo vídeo, mesmo resultado) e publica a
   silhueta: perto de 1 os dois grupos estão bem separados, perto de 0 o vídeo só tem um jeito de olhar e a
   divisão é artificial — nesse caso não confie no rótulo "lendo";
4. decide qual grupo é "câmera" pelo XML rotulado, pelo `--grupo-camera` do usuário, ou chuta no grupo com
   `yaw`, `pitch` e `olho_y` mais perto do ZERO ABSOLUTO (olhar de frente é 0) — avisando, em letras
   grandes, que chutou. O palpite usa o valor cru, não o normalizado: a mediana de um vídeo em que a pessoa
   lê o tempo todo É o jeito de ler, e medir a partir dela inverte a resposta (aconteceu, e foi medido).

Com mais de uma pessoa no quadro, a skill segue **uma**: a que mais aparece na mesma posição ao longo do
vídeo (os rostos são agrupados por posição; vence o aglomerado maior). Quem passa ao fundo não vira "a
pessoa". Se precisar da outra, corte o trecho dela e rode nele.

## O detector, por sistema

| sistema | detector | observação |
|---|---|---|
| macOS | **Vision da Apple** (`olhar.swift`, compilado por `swiftc` na primeira vez em `~/.criabr/bin/olhar`) | não baixa nada, não usa rede; duas passadas: caixas na revisão 3 (é ela que devolve o `pitch`) e pontos de referência em cima delas |
| Linux / Windows | **OpenCV** (`olhar_cv.py`) | o `preparar.py` instala o `opencv-python`; o giro da cabeça é *deduzido* da posição dos olhos na caixa do rosto, então é mais grosseiro — calibre com XML ou confirme o grupo na folha |

No Mac, o OpenCV também é instalado como reserva (para o caso de a máquina não ter as ferramentas de linha de
comando do Xcode, sem as quais não há `swiftc`). Se o `swiftc` existir, é o Vision que roda.

## Um jeito de olhar só

O k-médias é **obrigado** a devolver dois grupos. Num vídeo em que a pessoa nunca desvia o olhar ele separa
dois ou três quadros atípicos (uma piscada, a cabeça virando) e chama aquilo de "lendo" — e a silhueta ainda
sai alta, porque um ponto distante longe de todos *parece* um grupo bem separado. Medido nas amostras: 1
amostra de 40 e 3 de 76, todas falsas.

Por isso, quando ninguém disse qual é o grupo da câmera (sem `--calibrar` e sem `--grupo-camera`) e o grupo
menor é pequeno nas DUAS contas — menos de `--grupo-min` amostras (padrão 10) **e** menos de 8% do total —,
a skill declara **um jeito de olhar só**: tudo que tem rosto vira `camera`, não existe `lendo`, e o
`olhar.md` diz isso em letras grandes. `"um_jeito_de_olhar": true` no JSON. Se você SABE que há trecho lido,
aumente o `--fps` (mais amostras), baixe o `--grupo-min` ou calibre com XML.

## Armadilhas que custaram caro

- **O Vision trava se for aquecido demais.** Nunca amostre quadro a quadro. O padrão é **1 amostra por
  segundo** e o vídeo é varrido em blocos de 120 s, com 1 s de respiro entre eles; cada bloco tem prazo e, se
  estourar, é encerrado, esperado 3 s e tentado uma vez com metade da taxa. Bloco que não vai de jeito nenhum
  entra em `nao_medido` no `olhar.json` em vez de derrubar a varredura inteira.
- **Amostrar custa tempo de leitura, não de análise.** Medido aqui: 1080p60, ~0,3 s por amostra. Um vídeo de
  1 h a 1 amostra por segundo leva perto de 20 min. Para uma primeira passada use `--fps 0.5`.
- **Um quadro perdido não é "sem rosto".** Uma piscada, um movimento rápido ou um quadro escuro fazem o
  detector falhar por um instante. Por isso existe o `--trecho-min` (padrão 1,5 s): ilha curta demais é
  absorvida pelo vizinho. Se você precisa do quadro exato em que o rosto some, baixe para `--trecho-min 0`.
- **Confira sempre com os olhos.** Tire quadros dos trechos antes de confiar:
  `ffmpeg -ss <t> -i bruto/x.mp4 -frames:v 1 q.jpg`. O `olhar.md` existe para essa conferência.

## O que sai

```json
{"fonte": "bruto/x.mp4", "detector": "...", "fps_amostra": 1.0, "grupo_camera": "A",
 "origem_do_rotulo": "xml|usuario|palpite|grupo único", "um_jeito_de_olhar": false, "grupos": {"silhueta": 0.92, "A": 300, "B": 41},
 "calibracao": {"amostras_comparadas": 280, "acerto": 0.93}, "nao_medido": [],
 "segundos_por_estado": {"camera": 820.0, "lendo": 140.0, "sem_rosto": 40.0},
 "trechos": [{"t0": 0.0, "t1": 12.5, "estado": "camera", "confianca": 0.95, "amostras": 13}],
 "amostras": [{"t": 0.0, "estado": "camera", "estado_cru": "camera", "grupo": "A", "yaw": -0.05,
               "pitch": 0.18, "olho_y": 0.21}]}
```

`estado` é o final (o mesmo do trecho); `estado_cru` é o que o detector disse antes do alisamento —
é por ele que se vê quanto o `--trecho-min` corrigiu. `transcricao/olhar.md` traz a mesma coisa em
mm:ss, para ler com o usuário.

## Limites

- A skill diz **para onde a cabeça e os olhos apontam**, não o que a pessoa está fazendo. "Lendo" é o grupo
  que não é o da câmera: pode ser lendo, pode ser olhando para o convidado do lado.
- Silhueta alta NÃO garante que existam dois jeitos de olhar: um punhado de quadros atípicos também dá
  silhueta alta. Quem decide isso é o tamanho do grupo menor (veja "um jeito de olhar só"). Com silhueta
  baixa (abaixo de ~0,3) e dois grupos grandes, os dois jeitos existem mas se parecem: calibre.
- Óculos com reflexo, contraluz forte e rosto muito pequeno no quadro derrubam a pupila; o rosto continua
  sendo achado, mas o `olho_x`/`olho_y` fica ruim.
- Não identifica QUEM é a pessoa e não guarda nenhum dado biométrico: só posição, ângulo e tempo.
