# Como escrever título, descrição, tags, hashtags e legendas

Leia antes de escrever qualquer texto do pacote. As citações em inglês vêm das páginas de ajuda das plataformas, abertas em **2026-10-06** (lista no fim). Os números de limite **não** estão aqui de propósito: quem diz o limite vigente é `pacote.py validar` (lê `plataformas.json` do kit). O que está aqui é critério.

## 0. Antes de escrever

1. Leia `roteiro/roteiro.md` e `pesquisa/fatos.json` (campo `como_dizer` de cada fato): o texto público só afirma o que a ficha confirma.
2. Veja a thumbnail do pacote (`meta.json` → `thumbnail`; se o projeto tem `thumbs/variacoes.json`, a variação em `escolhida` → campo `texto`). Título e thumbnail são lidos juntos.
3. Para corte vertical: `cortes/plano.json` → `titulo` e `gancho` do corte (o `pacote.py novo --corte` já copia os dois para o meta.json).
4. Se não há gancho escolhido, peça à skill `gerar-ganchos` (§7). Não invente gancho aqui.

## 1. Título do YouTube

O que o YouTube diz ("Thumbnail & title tips"):
- "Make sure your title accurately represents the video. If not, viewers may stop watching."
- "Viewers may only see part of your title. So aim to keep it short and put the most important words near the beginning." — e: "Save episode numbers and branding for the end."
- "Limit ALL CAPS and emoji. Use them carefully, to emphasize emotion or special elements."
- Dois tipos de título: o **pesquisável** (diz o assunto com as palavras que a pessoa digita) e o **intrigante** (abre uma curiosidade para quem não estava procurando).

Como aplicar:
- **Uma promessa específica, que o vídeo cumpre.** "Como um modelo de linguagem escolhe a próxima palavra" promete uma explicação; "A verdade sobre o ChatGPT" não promete nada.
- **O que importa cabe antes do corte.** O título inteiro pode ir até o limite, mas a parte visível em celular e na lateral é bem menor (estimativa em `plataformas.json`: `titulo_visivel_estimado_caracteres`; `validar` mostra o trecho que sobra). Palavra-chave e promessa primeiro; nome da série e número do episódio por último.
- **Coerência com a thumbnail, sem repetição.** A thumbnail mostra a tensão ("8 PÁGINAS"); o título diz do que se trata ("O artigo de 2017 que criou a IA de hoje"). Thumbnail e título dizendo a mesma frase desperdiçam um dos dois; dizendo coisas sem relação, quebram a promessa.
- **Número só com fato.** "7 vezes mais rápido" precisa de um F### confirmado e não vencido; sem isso, descreva sem número.
- **Português direto**, sem caixa alta inteira, sem "CHOCANTE", sem "isso muda tudo". Emoji conta dobrado no limite e raramente ajuda num canal de explicação.
- **Teste A/B** (só vídeo longo, só pelo Studio no computador): até 3 variações de título e/ou thumbnail; vence a de maior participação no tempo de exibição, não a de mais cliques. Se o usuário quiser testar, entregue 3 títulos com promessas diferentes — não 3 grafias da mesma.

| fraco | por quê | melhor |
|---|---|---|
| Tudo sobre Transformers!! | não promete nada; pontuação de anúncio | Como a atenção faz um modelo entender contexto |
| IA EXPLICADA EM 10 MINUTOS | caixa alta; o vídeo tem 12 | O que acontece dentro de um modelo de linguagem |
| Lab de IA #14 – Tokens | série na frente, assunto no fim | O que é um token (e por que a IA cobra por ele) · Lab de IA 14 |

## 2. As duas primeiras linhas da descrição

O que o YouTube diz ("Tips for video descriptions"):
- "Consider using the first few lines of your description to describe your video because it's what viewers will see first."
- "Identify 1-2 main words that describe your video and feature them prominently in both your description and title."
- "Be sure that each video has a unique description; this makes it easier to find through search."
- "Search terms are matched with the video and the text in the description."

Como aplicar:
- **Linha 1**: a promessa do título dita de outro jeito, com a palavra-chave principal. **Linha 2**: o que a pessoa leva (o que vai entender, para quem é). É isso que aparece antes do «mais» — link, pedido de inscrição e crédito ficam para depois.
- Não comece por "Neste vídeo eu vou…" nem por "Fala, pessoal". Comece pelo assunto.
- É a `--abertura` do `pacote.py descricao`. O resto (capítulos, fontes, créditos, links, hashtags) o script monta; não reescreva esses blocos à mão.
- Cada vídeo com a sua abertura: descrição copiada do vídeo anterior atrapalha a busca (é a regra da "unique description").

## 3. Capítulos que ajudam a navegar

Regras oficiais (o `pacote.py capitulos` confere): lista na descrição, primeiro em 00:00, ao menos três, ordem crescente, mínimo de 10 s cada. Capítulos manuais substituem os automáticos.

- Os **tempos** vêm de `render/capitulos.json` (dono: video-montagem). Aqui só se revisam os **títulos**.
- Título de capítulo é o **assunto**, não a função: "O que é atenção", não "Parte 2" nem "Desenvolvimento". Quem cai no meio do vídeo pela busca precisa saber onde está.
- O primeiro capítulo não se chama "Introdução": chama-se o gancho ("Oito páginas").
- Curtos (até umas 5 palavras): a barra do player corta.
- Não abra capítulo para a vinheta nem para o pedido de inscrição.

## 4. Tags

O que o YouTube diz ("Add tags to your YouTube videos"): "Tags play a minimal role in your video's discovery." · "Tags can be useful if the content of your video is commonly misspelled." · "Your video's title, thumbnail, and description are more important pieces of metadata for your video's discovery." · "Adding excessive tags to your video description is against our policies on spam, deceptive practices, and scams."

Então: **5 a 8 tags**, e só as que cumprem a função que a ajuda descreve —
- grafias que as pessoas erram ou variam: `chatgpt`, `chat gpt`, `gpt`;
- o termo em inglês e em português: `modelo de linguagem`, `llm`, `large language model`;
- o nome próprio central do vídeo.

Nada de lista de palavras na descrição. Tags não existem em Reels e TikTok.

## 5. Hashtags

- **YouTube e Shorts** ("Find playlists & videos using hashtags"): "up to three hashtags that are considered most engaging will appear by your video title"; "If a video or playlist has more than 60 hashtags, we'll ignore each hashtag on that content"; "Don't add hashtags that are not directly related to the video or playlist"; "Hashtags don't contain any spaces." Na prática: **2 ou 3**, do assunto exato do vídeo, no fim da descrição (é o bloco `hashtags`).
- **Instagram**: limite baixo por publicação, somando legenda e comentários (o número vigente está em `plataformas.json` → `hashtags_max`; o kit o conferiu na Central de Ajuda em 2026-10-05 — hoje a página não abriu sem sessão). Use todas as vagas só se todas forem específicas.
- **TikTok**: nenhum limite oficial de quantidade foi encontrado (o suporte não publica; a API só diz que hashtags contam dentro do limite da legenda). Recomendação da casa, não regra da plataforma: 3 a 5.
- Em qualquer uma: hashtag é **assunto**, não desejo (`#Transformer`, não `#viral` nem `#fyp`). Hashtag sem relação direta com o vídeo o YouTube classifica como enganosa.
- Acento em hashtag: `#InteligenciaArtificial` e `#InteligênciaArtificial` podem cair em páginas diferentes; veja no aplicativo qual das duas a comunidade usa antes de escolher.

## 6. Legenda de Reels, TikTok e Shorts

- **Abra com o gancho** — a primeira linha é quase tudo o que aparece antes do «mais» (estimativa em `plataformas.json`: `legenda_visivel_estimada_caracteres`; `validar` mostra o trecho). Se o gancho não cabe nesse trecho, encurte o gancho, não conte com o clique.
- **Não repita o que já está queimado na tela.** Se o vídeo abre com "Oito páginas mudaram a IA" em legenda grande, a legenda do post pode dar o passo seguinte: "O artigo de 2017 que quase ninguém leu — e que está por trás de todo chatbot."
- **Segunda linha**: contexto ou chamada (de onde é o corte, onde está o vídeo completo). Na legenda do Instagram o link não vira clicável (comportamento conhecido do aplicativo, não conferido hoje em fonte oficial): escreva "vídeo completo no canal", não a URL.
- **Crédito obrigatório de imagem** entra mesmo em legenda curta (o bloco `creditos` cuida; `validar` reprova se faltar).
- **Hashtags no fim**, dentro do limite.
- **Shorts**: o que aparece é o **título** (mesmo limite do vídeo longo; curto funciona melhor); a descrição quase ninguém abre — abertura de uma linha, crédito se houver, 2 ou 3 hashtags.
- A mesma peça em três plataformas pede três legendas com o mesmo gancho e acabamento diferente (hashtags, chamada). O `pacote.py novo` cria um pacote por plataforma justamente para isso.

## 7. Ganchos: use a skill `gerar-ganchos`

Título intrigante e primeira linha de legenda são ganchos. Quem gera é a skill irmã:

1. Chame `gerar-ganchos` com **tema** = a tese do vídeo ou do corte (uma frase), **público**, **quantidade** (10) e **objetivo** (alcance para corte curto; autoridade para o vídeo longo).
2. Ela devolve ganchos numerados, rotulados com gatilho e motor. Mostre ao usuário e deixe-o escolher — o gancho é decisão dele.
3. Adapte o escolhido ao campo: no **título**, cabe no trecho visível e mantém a palavra-chave; na **legenda**, vai inteiro na primeira linha.
4. As regras de escrita dela valem aqui (numeral concreto vence termo vago; texto que soa como fala; sem a fórmula seca "Não é X, é Y"). Uma regra extra desta skill: **número em gancho é afirmação factual** — precisa de fato confirmado na ficha.
5. Se o gancho escolhido não é cumprido pelo vídeo, o problema é do roteiro (`melhorar-roteiro`), não do título: não "ajuste" a promessa para vender melhor.

## 8. Honestidade (isto reprova na validação ou na plataforma)

- **Nada de promessa que o vídeo não cumpre.** É política do YouTube, não só gosto: é proibido usar "maliciously misleading titles, thumbnails, descriptions… to trick users into clicking on a video that does not deliver what was promised."
- **Afirmação factual só com fato confirmado.** Todo número, data, preço, nome de modelo e superlativo ("o maior", "o primeiro", "o mais usado") no título, na abertura ou na legenda corresponde a um fato de `pesquisa/fatos.json` com `status: confirmado` e `caduca_em` no futuro. Declare-os com `pacote.py descricao <pacote> --fatos F001 F004`; `validar` reprova fato vencido, não confirmado ou inexistente — e reprova marcador `[F001]` esquecido no texto público.
- **Use a redação de `como_dizer`.** Ela existe porque a afirmação crua costuma dizer mais do que a fonte sustenta.
- **Preço, benchmark e "modelo mais novo" envelhecem.** Ponha a data na frase ("em outubro de 2026") e confira `caduca_em` contra a data de publicação — com agendamento, `validar` compara com a data agendada, não com hoje.
- **Fontes na descrição** do vídeo longo: o bloco `fontes` vem de `pesquisa/fontes.md` ou dos fatos citados. Não o remova para "limpar" a descrição.
- **IA realista se declara** (`conteudo_sintetico`; `envio.md` §5).
- Sem fato confirmado para uma frase boa? A frase sai, ou vira pergunta honesta. Peça a verificação à skill video-pesquisa-ia; não publique "para corrigir depois".

## 9. Revisão em 30 segundos

1. O título, sozinho, diz o que o vídeo entrega? A parte visível tem a palavra-chave?
2. Título e thumbnail se completam?
3. As duas primeiras linhas da descrição funcionam sem o resto?
4. Algum número ou superlativo sem fato confirmado?
5. Hashtags: poucas, do assunto, dentro do limite da plataforma?
6. `pacote.py validar` sem erro — e os avisos lidos, não ignorados?

## Fontes (abertas em 2026-10-06)

- YouTube — Thumbnail & title tips: https://support.google.com/youtube/answer/12340300
- YouTube — Tips for video descriptions: https://support.google.com/youtube/answer/12948449
- YouTube — Add tags to your YouTube videos: https://support.google.com/youtube/answer/146402
- YouTube — Find playlists & videos using hashtags: https://support.google.com/youtube/answer/6390658
- YouTube — Video Chapters: https://support.google.com/youtube/answer/9884579
- YouTube — Spam, deceptive practices & scams policies: https://support.google.com/youtube/answer/2801973
- TikTok — Content Posting API, Direct Post (limite e contagem da legenda): https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- Instagram — Use hashtags (não abriu hoje; valor do kit, conferido em 2026-10-05): https://help.instagram.com/351460621611097
- Teste A/B, trechos visíveis e demais números: `~/.claude/skills/video-direcao-de-arte/references/plataformas.md` (§4 e §5)
