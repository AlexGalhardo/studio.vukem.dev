---
name: video-decupagem
description: Decupa o bruto de uma gravação. Junta a energia do áudio às palavras cronometradas para achar retomadas, repetições, gaguejos, muletas, pausas mortas e sobras de bastidor, e DEIXA A ÚLTIMA TENTATIVA CERTA; grava a EDL no padrão da casa ({"fonte", "cortes":[{"src0","src1","motivo"}]}), renderiza na especificação do original com corte em quadro exato e microfade de 24 ms nas emendas, e confere o resultado contra o bruto (PSNR/SSIM quadro a quadro, atraso do áudio, imagem de cada junção). Calibra pelo XML de uma decupagem feita à mão e tem modo rígido. Use quando o usuário disser "decupa esse vídeo", "tira as pausas", "limpa a gravação", "corta os erros e as repetições", "deixa só a última tentativa", "esse take tem muita enrolação", ou pedir a EDL/corte seco do bruto. Difere das irmãs: video-transcricao entrega as palavras que esta consome; video-montagem leva a EDL para a timeline/XML do Premiere; video-mixagem cuida de loudness, não de corte.
---

# video-decupagem

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

O usuário gravou e quer o bruto limpo: sem bastidor, sem as tentativas abandonadas, sem pausa morta, sem
gaguejo — mas sem perder nenhuma frase boa. Esta skill mede, propõe e renderiza; **quem decide é o usuário**,
e o relatório existe para ele conferir.

## Fluxo

1. **Transcreva primeiro** (a skill `video-transcricao`), palavra a palavra:
   `python3 ~/.claude/skills/video-transcricao/scripts/transcrever.py bruto/x.mp4 --saida transcricao/`
2. **Decupe**: `python3 scripts/decupar.py bruto/x.mp4 --palavras transcricao/palavras.json --saida cortes/`
   · `--rigido` corta pausa curta e muleta solta também · `--calibrar <xml>` aprende os números de uma
   decupagem manual · `--manter 12.0-19.5` protege um trecho · `--sem-repeticao` / `--sem-pausa` desligam
   um analista.
3. **Leia `cortes/relatorio.md` com o usuário** e ajuste (o `--manter` e o `--pausa-max` existem para isso).
   Dá para editar o `cortes/edl.json` na mão: é só a lista dos trechos que ficam.
4. **Renderize**: `python3 scripts/render.py cortes/edl.json --saida render/ --fonte bruto/x.mp4`
5. **Confira**: `python3 scripts/qa.py render/x_decupado.mp4 --edl cortes/edl.json --saida qa/ --palavras transcricao/palavras.json`
   (com `--palavras` a conferência das junções usa a borda da palavra; sem ele usa só a energia, que acusa
   qualquer corte em fala contínua — e corte de retomada é sempre em fala contínua.)
   Ele sai com código 1 se reprovar. Abra as imagens de `qa/juncoes/` antes de entregar.

## A linha de agentes (é assim que a decupagem fica boa)

Os scripts dão a medida; a cabeça é sua. Use este time, nesta ordem — foi ele que produziu a decupagem que
deu origem a esta skill:

1. **Três analistas em paralelo**, cada um lendo `cortes/analise.json` + `cortes/relatorio.md` com um olho só:
   - *retomadas e repetições*: o que foi recomeçado? a última tentativa está inteira e correta?
   - *gaguejos e erros de fala*: concordância errada, palavra trocada, autocorreção. Há outro take?
   - *ritmo e imagem*: pausa longa demais, pausa curta demais, trecho que arrasta.
2. **Montador**: junta as três listas numa EDL só, resolve conflito e grava `cortes/edl.json`.
3. **Três verificadores adversariais**, que tentam DERRUBAR a EDL:
   - *sentido*: lendo só o texto que sobrou, a fala continua coerente? sumiu alguma informação?
   - *áudio*: alguma junção corta no meio de palavra? (coluna dB do relatório e do `qa.py`)
   - *imagem*: alguma junção dá pulo? (as imagens de `qa/juncoes/`)
4. **Corretor**: arbitra cada apontamento, ajusta a EDL e manda renderizar de novo.

Regra que custou caro: **o whisper funde retomadas e apaga gaguejos.** Toda checagem de repetição tem de ser
feita sobre as palavras do BRUTO (`transcricao/palavras.json`, passada palavra a palavra) e sobre a energia,
nunca sobre a retranscrição do resultado — ela "conserta" sozinha o que você queria ver.

## O que sai

- `cortes/edl.json` — `{"fonte", "fps", "modo", "parametros", "cortes":[{"src0","src1","motivo"}]}`, os
  trechos que **ficam**, em ordem, em segundos do bruto e já na fronteira de quadro.
- `cortes/removidos.json` — cada trecho que saiu, com motivo, texto e a energia das duas pontas.
- `cortes/analise.json` — o material dos analistas: retomadas candidatas, gaguejos, muletas, pausas mantidas,
  palavras de confiança baixa (as que o whisper ouviu mal: **confira antes de cortar em cima delas**).
- `cortes/relatorio.md` · `render/render.json` · `qa/relatorio.md` + `qa/juncoes/*.jpg`.

## Qualidade do original — o que foi medido

O render tem dois caminhos e escolhe sozinho (`--modo auto`):

| caminho | quando | o que acontece |
|---|---|---|
| `copia` | **todas** as entradas caem em quadro-chave | vídeo sai bit a bit igual (`-c:v copy`); só o áudio é refeito |
| `preciso` | o caso normal | decodifica tudo, escolhe os quadros por ÍNDICE e recodifica com qualidade alta de propósito |

Medido na amostra de teste (H.264 1080p60, cortes em 2,88 / 8,33 / 12,48 / 19,67 / 21,93 s, GOP de 2 s):
**nenhum** ponto de corte caiu em quadro-chave — a fala não espera o GOP. Por isso o caminho normal é o
`preciso`, e ele recodifica com CRF 12 (H.264), mantendo tamanho, fps, `pix_fmt`, perfil e marcação de cor do
bruto. O `qa.py` mediu PSNR e SSIM contra os mesmos quadros do bruto (os números da sua rodada ficam em
`qa/relatorio.md`); abaixo de 45 dB de PSNR ou 0,985 de SSIM ele reprova.

Armadilhas que custaram caro, nesta ordem de importância:

- **O corte só pode cair no VÃO ENTRE PALAVRAS.** O encaixe procura o ponto de menor energia perto do corte;
  solto, ele escorrega para dentro da palavra vizinha atrás de um silêncio — numa rodada caiu 27 ms dentro de
  «que», no fecho da consoante, e a emenda deixou meio fonema no ar. O `decupar.py` fecha a busca no vão entre
  a palavra que FICA e a que SAI; quando o whisper encosta uma palavra na outra (vão de 0 s), cai na fronteira
  de quadro mais perto da borda, que é o melhor que a grade permite. O número medido de cada rodada sai no
  `relatorio.md` e em `analise.json` → `folga_ate_borda_de_palavra` (negativo = corte dentro de palavra: isso
  é defeito, volte e conserte).
- **Nunca use `-ss` para posicionar o corte.** Em MP4 vindo de HLS o `-ss` erra o quadro e o corte anda. O
  `render.py` decodifica do começo e seleciona por `select=between(n,a,b-1)`, que é índice de quadro.
- **VP9**: o recorte exato também é por índice de quadro (num contêiner IVF o índice é o próprio número do
  pacote). O `render.py` já seleciona por índice; se precisar cortar VP9 sem recodificar, demuxe para `.ivf`,
  corte por número de pacote e remuxe — não corte por tempo.
- **HEVC para edição**: o `render.py` usa `hevc_videotoolbox -q:v 88` quando existe (é a qualidade que o
  usuário aprovou para material de edição) e cai para `libx265 -crf 16` quando não.
- **O áudio é sempre remontado** amostra a amostra do bruto, com crossfade de potência constante de 24 ms
  centrado em cada junção. Ele usa as *alças* do bruto (o som continua 12 ms depois da saída e começa 12 ms
  antes da entrada), então a emenda não estala **e a duração não muda**. Sem isso, cada corte vira um clique.
- **Timestamps**: depois do `select`, `settb` + `setpts=N*den` refazem a base de tempo. Sem isso a saída fica
  com fps variável e o Premiere relinka errado.

## Modo rígido e calibração

- `--rigido`: pausa máxima 0,30 s (em vez de 0,60), respiro 0,07 s (em vez de 0,12) e tira muleta solta
  ("é…", "ãh", "hum" entre duas pausas). É o corte seco de aula/curso.
- `--calibrar decupagem_manual.xml`: lê o XML (Final Cut Pro XML do Premiere) de uma decupagem que o editor
  fez à mão sobre o MESMO bruto, mede o respiro que ele deixa nas pontas (mediana) e o tamanho de pausa que
  ele aceita (percentil 90) e usa esses números. Grava `cortes/calibracao.json` com tudo que mediu.

## Limites

- O limiar fala × silêncio é medido no próprio material (34 dB abaixo do pico). Em gravação muito comprimida
  quase tudo é "fala" — e está certo: não há pausa para cortar.
- Retomada só é retomada se o apresentador **parou** antes de recomeçar (0,12 s; 0,06 s no rígido) e se a
  tentativa abandonada for curta em relação ao que ele repetiu. Sem essas duas peneiras a skill apaga ênfase
  ("confere, cara, confere") e conteúdo.
- Erro de conteúdo (número errado, nome trocado) não é detectável aqui: é trabalho dos analistas e da
  `video-checagem`.
- Cortar com `-c copy` só é possível quando a edição cai em quadro-chave; isso é raro em decupagem.
