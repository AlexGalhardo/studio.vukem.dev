---
name: video-garimpo-de-midia
description: Garimpa mídia POR NECESSIDADE em bancos livres, numa ordem de preferência configurável (acervos públicos, Wikimedia/Agência Brasil, NASA, Internet Archive, Openverse e, no fim, Pexels/Pixabay), com pausa entre os pedidos para não levar bloqueio, conferência da identidade da pessoa na foto pela legenda da fonte, e a regra de que NADA é baixado sem o "sim" do usuário — ela propõe, grava licença e crédito de tudo e imprime o comando de download. Vídeo de terceiro (YouTube) entra só como citação curta, sem som e com crédito na tela. Use quando o usuário disser "procura imagem/vídeo pra isso", "o que existe de graça sobre X", "acha uma foto dele", "de onde tiramos essa imagem", "pode usar?", "monta a lista do que falta de mídia" ou "garimpa". Difere das irmãs - video-broll é quem fala com os provedores e baixa, video-pauta-midia lê o roteiro e baixa YouTube e Google Imagens, video-prancha-de-referencia monta as folhas de contato numeradas.
---

# video-garimpo-de-midia

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

Quando falta mídia e ninguém sabe de onde ela vem. Esta skill é **fina de propósito**: quem conversa com os
provedores é a `video-broll` (`scripts/buscar.py` e `scripts/baixar.py`) e quem guarda licença é
`broll/licencas.json`. Aqui mora o que falta entre uma coisa e outra:

- a **necessidade** (o que o vídeo precisa mostrar), vinda de `roteiro/pauta.json` ou escrita à mão;
- a **ordem de preferência** das fontes, configurável e diferente por gênero de necessidade;
- a **pausa** entre pedidos, que é o que evita bloqueio;
- a **conferência de identidade** de pessoa na foto, pela legenda da fonte;
- a regra de ouro: **nada é baixado sem o «sim» do usuário**.

Se o pedido já é "baixa este vídeo do YouTube de 1:10 a 1:25", vá direto para a `video-pauta-midia`. Se já há
candidatos escolhidos, o download é da `video-broll`. Se o que falta é montar a folha de contato numerada por
unidade do roteiro, é a `video-prancha-de-referencia`.

## Fluxo

Todos os comandos rodam na raiz do projeto (ou com `--projeto <pasta>`). `<skills>` = `~/.claude/skills`.

1. **Levantar as necessidades**

   ```bash
   python3 <skills>/video-garimpo-de-midia/scripts/garimpar.py necessidades
   python3 <skills>/video-garimpo-de-midia/scripts/garimpar.py necessidades \
       --nova "retrato de <nome>" --en "<name> portrait" --pessoa "<Nome Sobrenome>" --tipo imagem
   ```
   Sem `--nova`, lê `roteiro/pauta.json` (pedidos de tipo `banco`, `imagem_web` e `video_youtube` ainda em
   aberto). Grava `broll/garimpo/necessidades.json`. Gêneros: `pessoa`, `lugar`, `documento`, `evento`,
   `objeto`, `ambiente` (padrão) — o gênero é o que escolhe a ordem das fontes.

2. **Ajustar a ordem de preferência e a pausa** (opcional; o padrão já serve)

   ```bash
   python3 .../garimpar.py fontes --ordem wikimedia,nasa,archive,openverse,pexels,pixabay --pausa 2 --bastam 4
   ```
   Grava `broll/garimpo/fontes.json`. `bastam` = quantos candidatos bons encerram a fila de fontes: com 4 bons
   na primeira fonte, as outras nem são consultadas (menos pedido, menos risco de bloqueio).

3. **Buscar** (não baixa mídia)

   ```bash
   python3 .../garimpar.py buscar            # todas as pendentes
   python3 .../garimpar.py buscar N003 --folha
   ```
   Percorre as fontes na ordem, uma de cada vez, com a pausa entre pedidos. `--folha` gera a folha de contato
   da `video-broll` (baixa **só as miniaturas**). Para necessidade com `--pessoa`, cada candidato passa pela
   conferência de identidade e só entra na proposta quem **confere**; o resto fica em `a_conferir`.

4. **Mostrar ao usuário e esperar o «sim»** — os candidatos (ou a folha) vão para a conversa. Só então:

   ```bash
   python3 .../garimpar.py escolher N001 --numeros 2,5
   ```
   Isso **não baixa**: registra a escolha e imprime o comando de download da `video-broll`, que por sua vez só
   baixa com `--confirmar`.

5. **Vídeo de terceiro: citação, nunca acervo**

   ```bash
   python3 .../garimpar.py citar N004 --url <url> --t0 1:10 --t1 1:18 \
       --credito "Reprodução · <canal>" --porque "comentar a frase dita no trecho"
   ```
   Teto de 10 s, **sem som** na montagem, crédito na tela durante todo o trecho. O download, depois do «sim», é
   da `video-pauta-midia` (`youtube.py baixar … --base-legal citacao --nota "…" --confirmar`).

6. **Créditos** — `garimpar.py creditos` grava `broll/garimpo/creditos.md` (licença e crédito de **tudo** que
   foi proposto, antes mesmo de baixar). Depois do download, o registro oficial continua sendo
   `broll/licencas.json` e o texto público, `broll/creditos.md`, ambos da `video-broll`.

## O que sai

| arquivo | o que é |
|---|---|
| `broll/garimpo/necessidades.json` | cada necessidade com gênero, ordem de fontes, fontes tentadas, candidatos (com licença e veredito de identidade), escolhidos e citação |
| `broll/garimpo/fontes.json` | ordem de preferência, ordem por gênero, pausa, `por_fonte`, `bastam`, política do YouTube |
| `broll/garimpo/creditos.md` | licença e crédito de tudo, legível, antes do download |
| `broll/_busca/*.json` e `*.png` | as buscas e folhas de contato, gravadas pela `video-broll` |

## Regras que custaram caro

- **Nada é baixado sem o «sim».** `buscar` e `escolher` só propõem; o download é um comando separado da
  `video-broll`/`video-pauta-midia`, que ainda exige `--confirmar`. `--folha` baixa miniatura — avise.
- **Pausa é obrigação, não educação.** Consultar seis fontes sem respirar é como se leva bloqueio de IP num
  acervo público. A pausa padrão é 2 s e a busca para assim que já tem candidatos bons.
- **Legenda da fonte é a única prova de quem está na foto.** O autor é quem fotografou, não quem aparece:
  nunca use o campo `autor` para identificar a pessoa. Sem legenda, a identidade não confere.
- **Mesmo sobrenome com outro primeiro nome = xará ou parente**, não a pessoa: vai para `a_conferir` e precisa
  de olho humano. Estátua, ator, ilustração e caricatura também: a legenda traz o nome, mas a foto não é ela.
- **YouTube não é banco de imagens.** Entra como citação curta e muda, com crédito na tela; nunca como b-roll.
- **Sem DA o garimpo não busca** (`código 2`): o tratamento da mídia é da direção de arte, e é ela que diz
  orientação e lado mínimo. Crie a DA antes (`video-direcao-de-arte`).

## Códigos de saída

`0` ok · `1` nada encontrado ou falhou · `2` projeto sem direção de arte · `64` erro de uso · `75` sem rede.
