# O pacote por dentro — arquivos, campos e tudo o que `validar` confere

Leia quando precisar editar um `meta.json` à mão, entender um item da validação ou um estado do índice, ou escrever outra skill que leia `publicacao/`. Tudo aqui foi executado em 2026-10-06 com o kit de direção de arte 1.3.0 (`plataformas.json` verificado em 2026-10-05, seções `specs.youtube_longo` e `limites_texto.instagram_reels`, ainda sem os acessores `da.plataformas()` / `da.limite()` — o script usa os acessores quando existirem e, sem eles, lê o arquivo).

## 1. Arquivos

```
publicacao/
  pacote.json                    índice de TODOS os pacotes + última validação e estado de agora (regravado por todo subcomando que muda algo)
  youtube/meta.json              pacote padrão da plataforma (contrato entre as skills)
  youtube/descricao.txt          o mesmo texto de meta.descricao, para colar
  youtube/checklist.md           passo a passo manual (pacote.py checklist)
  youtube/envio.json             só depois de enviado (enviar_youtube.py ou pacote.py registrar)
  youtube/envio_anterior_<data>.json   registro de envio de um pacote que foi recriado com `novo --forcar`
  shorts/meta.json               primeiro corte publicado em Shorts
  shorts/K02/meta.json           demais cortes da mesma plataforma → seletor «shorts/K02»
  reels/…  tiktok/…
```

**Para skills irmãs**: o contrato só fixa `publicacao/<plataforma>/meta.json`, que é onde mora o primeiro pacote de cada plataforma. O segundo corte em diante vai para `publicacao/<plataforma>/<corte>/meta.json` — extensão desta skill, ainda não registrada no contrato. Quem precisa de todos os pacotes lê `publicacao/pacote.json` → `pacotes[].meta` (caminho de cada `meta.json`) e `pacotes[].estado`; o índice é regravado por `novo`, `capitulos`, `descricao`, `definir`, `validar`, `checklist`, `registrar`, `resumo` e pelo envio, então lista o pacote desde que ele nasce.

**Seletor de pacote**: `<plataforma>` ou `<plataforma>/<corte>`. `shorts/K01` também acha o pacote padrão quando ele é do corte K01. Um pacote padrão criado com `--video` apontando para o arquivo de um corte **é** a peça desse corte: `novo <plataforma> --corte K01` não cria um segundo pacote ao lado — pede `--forcar` e substitui o padrão. Se ainda assim dois pacotes da mesma plataforma apontarem para o mesmo arquivo (plano de cortes com duas saídas iguais, `meta.json` editado), `novo` avisa e `validar` dá `pacote.duplicado`. Apelidos aceitos na linha de comando (`instagram`, `yt`, `short`…) viram o nome canônico; as pastas são sempre `youtube`, `shorts`, `reels`, `tiktok`.

## 2. `meta.json`

Campos do contrato (nunca renomeie nem remova):

| campo | conteúdo |
|---|---|
| `versao` | `1` |
| `plataforma` | `youtube` \| `shorts` \| `reels` \| `tiktok` |
| `titulo` | título (YouTube, Shorts). Em Reels e TikTok é rótulo interno: o que se publica é `descricao` |
| `descricao` | descrição (YouTube, Shorts) ou legenda do post (Reels, TikTok), já montada |
| `tags` | lista (só YouTube e Shorts) |
| `hashtags` | lista com `#`; entram no bloco `hashtags` da descrição |
| `capitulos` | `[{"t": segundos inteiros, "titulo": "…"}]` (só `youtube`) |
| `arquivo_video`, `thumbnail`, `legenda_srt` | caminhos relativos à raiz do projeto (`thumbnail` e `legenda_srt` podem ser `null`) |
| `privacidade` | `private` (padrão) \| `unlisted` \| `public` |
| `agendar_para` | `null` ou ISO 8601 **com fuso** (`2026-10-20T18:00:00-03:00`) |
| `idioma` | BCP-47 (`pt-BR`): idioma do texto e da legenda |

Campos acrescentados por esta skill:

| campo | conteúdo |
|---|---|
| `corte`, `gancho` | id e gancho do corte em `cortes/plano.json` (`null`/vazio no vídeo longo) |
| `abertura` | as primeiras linhas, escritas pelo Claude (`descricao --abertura`) |
| `links` | `[{"rotulo", "url"}]` do bloco de links |
| `assinatura` | cópia de `marca.assinatura` da DA, atualizada a cada `descricao` (a marca não se decide na peça) |
| `blocos` | ordem dos blocos da descrição |
| `fontes_modo` | `auto` (usa `pesquisa/fontes.md`; sem ele, os fatos citados) \| `fontes-md` \| `fatos` \| `nenhuma` |
| `creditos_modo` | `obrigatorios` \| `todos` |
| `fato_ids` | fatos citados nesta peça além dos marcados no roteiro |
| `broll_ids` | (opcional) b-roll que aparece nesta peça, quando a dedução automática não serve |
| `conteudo_sintetico` | `null` (não respondido → aviso), `true`, `false` → `status.containsSyntheticMedia` |
| `feito_para_criancas`, `notificar_inscritos`, `categoria_id`, `legenda_nome` | opções do envio pela API do YouTube |
| `capitulos_origem`, `descricao_adotada`, `da_sha256`, `criado_em`, `atualizado_em` | controle |

Quem muda cada campo: texto (`titulo`, `abertura`, `hashtags`, `tags`, `links`, `blocos`, `fato_ids`, `broll_ids`…) → `pacote.py descricao`; `capitulos` → `pacote.py capitulos`; `agendar_para`, `privacidade`, `conteudo_sintetico`, `feito_para_criancas`, `notificar_inscritos`, `thumbnail`, `legenda_srt`, `idioma`, `categoria_id` → `pacote.py definir` (não toca no texto). Editar o `meta.json` à mão continua permitido; depois de mexer em campo de texto, rode `pacote.py descricao <pacote>` para remontar `descricao` e `descricao.txt`. Qualquer mudança pede `validar` de novo.

## 3. Blocos da descrição

Ordem padrão — `youtube`: abertura, capitulos, fontes, creditos, links, hashtags · `shorts`: abertura, creditos, links, hashtags · `reels` e `tiktok`: abertura, creditos, hashtags. Muda com `--blocos a,b,c` (fica gravado).

| bloco | de onde vem |
|---|---|
| `abertura` | `meta.abertura` |
| `capitulos` | `meta.capitulos` formatados (`00:00 Título`; `0:00:00` se o vídeo passa de 1 h), sob "Capítulos:" |
| `fontes` | `pesquisa/fontes.md` convertido para texto puro (sem `#`, `[texto](url)` → `texto: url`, sem `<url>` — `<` e `>` são proibidos no YouTube), ou as fontes dos fatos citados; sob "Fontes:" |
| `creditos` | `atribuicao` dos itens de `broll/licencas.json` com `exige_atribuicao` que aparecem na peça; sob "Créditos de imagem:" |
| `links` | `meta.links` + a assinatura da DA |
| `hashtags` | `meta.hashtags` numa linha |

**Quais b-rolls "aparecem na peça"**: as duas fontes do contrato são unidas — `usado_em` de `broll/licencas.json` e `broll_id` das cenas de `roteiro/storyboard.json` (um arquivo pode estar atrasado em relação ao outro; a divergência vira aviso `licencas.divergente`). No vídeo sem corte, aparece todo item citado em alguma cena, por qualquer das duas fontes — inclusive cena que o storyboard não lista (b-roll montado direto na timeline). Num corte, só os das cenas que cruzam o intervalo `t0–t1` do corte; se o storyboard não tem `t0`/`dur` em todas as cenas, ou a cena citada não está no storyboard, não dá para saber e o crédito entra (pecar por excesso). Item sem o campo `usado_em` e sem cena apontando para ele também entra (não dá para afirmar que ficou de fora); `usado_em: []` sem cena apontando fica de fora.

`--broll B001 B003` (ou `nenhum`, ou `auto`) declara à mão e vence a dedução — com rastro: se a declaração tira um item de atribuição obrigatória que os insumos põem na peça, o vídeo longo reprova (`licencas.excluido`: ali a dedução não tem dúvida) e o corte passa com aviso `licencas.declarado` e **exceção registrada** (`tipo: credito_excluido`), visível no checklist, no resumo, no plano de envio e no `envio.json`.

**Quais fatos**: os `[F001]` do roteiro (só no vídeo sem corte), os `fato_ids` das cenas do recorte e os declarados com `--fatos`. Corte sem mapa de cenas: só valem os declarados.

O texto é gravado em NFC. `--adotar` troca tudo pelo `descricao.txt` editado à mão; os blocos voltam a valer no próximo `descricao` sem `--adotar`.

## 4. O que `validar` confere

Severidades: **erro** reprova (código de saída 1); **aviso** não reprova (com `--estrito`, reprova); **info** só informa. Limite **essencial** que `plataformas.json` não traz — seção ausente ou renomeada, chave trocada — é erro `limites.ausentes` (o pacote não pode passar "sem conferir"): título, descrição em caracteres e em bytes, tags, hashtags, regras de capítulos e duração máxima no YouTube; os mesmos menos capítulos em Shorts; legenda, hashtags e duração mínima e máxima em Reels; legenda (API) e duração máxima no TikTok (tabela `ESSENCIAIS` de `pacote.py`; um teste da suíte falha se o kit real deixar de trazê-los). Os demais limites, quando ausentes ou `null`, viram info "não conferido", nunca erro inventado. Chave marcada como estimativa em `nao_oficial` rebaixa o erro a aviso.

| o quê | de onde vem o limite (`plataformas.json`) | resultado |
|---|---|---|
| Direção de arte aprovada | `da/da.json` (`projeto.aprovada`, sem alteração depois da aprovação) | erro `da.aprovada` |
| Limites essenciais presentes | tabela `ESSENCIAIS` × `plataformas.json` | erro `limites.ausentes` |
| Dois pacotes da mesma plataforma para o mesmo arquivo | — | aviso `pacote.duplicado` |
| Título vazio / tamanho / caracteres proibidos | `limites_texto.<plat>.titulo_max_caracteres`, `caracteres_proibidos` | erro `titulo.vazio`, `titulo.tamanho`, `texto.proibidos` |
| Trecho visível do título e da primeira linha | `titulo_visivel_estimado_caracteres`, `descricao_visivel_estimada_caracteres`, `legenda_visivel_estimada_caracteres` | info com o trecho |
| Descrição/legenda em caracteres | `descricao_max_caracteres` · `legenda_max_caracteres` (Reels) · `legenda_max_caracteres_api` e `…_app` (TikTok) | erro `descricao.caracteres` (aviso se a chave é estimativa) |
| Descrição em **bytes** UTF-8 | `descricao_max_bytes_api` (YouTube; Shorts herda) | erro `descricao.bytes` |
| Tags | `tags_max_caracteres_total`, contando vírgulas e as aspas das tags com espaço | erro `tags.tamanho`, `tags.virgula` |
| Hashtags no texto público inteiro | `hashtags_max` (`null` no TikTok → info), `hashtags_exibidas_junto_ao_titulo` | erro `hashtags.quantidade`, `hashtags.formato`; aviso `hashtags.repetidas` |
| Menções com @ | `mencoes_max` (Reels) | erro `mencoes.quantidade` |
| Marcador `[F001]` no texto público; texto em NFD; `descricao.txt` ≠ `meta.descricao` | — | erro `texto.marcador`, `descricao.divergente`; aviso `texto.nfd` |
| Duração | `specs.<plat>.duracao_min_s`, `duracao_max_s`; `duracao_max_recomendada_s`, `duracao_max_api_s`, `duracao_garantida_a_toda_conta_api_s`, `duracao_max_conta_nao_verificada_s` | erro `video.duracao_min/_max`; avisos |
| Orientação e proporção | `proporcao`; Short precisa ser vertical ou quadrado; vertical curto em `youtube` vira Short | erro `video.orientacao` (Shorts); avisos `video.proporcao`, `video.vira_short` |
| Resolução | `resolucao_min_px` / `…_api`, `resolucao_recomendada_px`, `resolucao_max`, `resolucao_max_px_api`, `largura_max_px_api` | erro `video.resolucao_min`; avisos |
| Codec, croma, bits, varredura | `codec_video` | erro `video.codec` em Reels/TikTok, aviso em YouTube/Shorts; avisos `video.croma`, `video.bits`, `video.entrelacado` |
| Container e fast start | `container` | idem `video.container`; aviso `video.faststart` (moov depois do mdat). O `ffprobe` chama MKV e WebM de `matroska,webm`: só vale como WebM o arquivo `.webm` com VP8/VP9/AV1 e Vorbis/Opus; o resto é Matroska e reprova onde só se aceita MP4/MOV/WebM |
| fps | `fps.faixa_api`, `fps.min_central_de_ajuda`, `fps.comuns` | avisos |
| Áudio | `audio.codec`, `audio.taxa_amostragem_hz`, `audio.canais` | **erro `video.sem_audio`** (arquivo sem trilha); avisos |
| Tamanho do arquivo, bitrate | `tamanho_max_gb`, `tamanho_max_gb_api`, `tamanho_max_mb_api`, `bitrate_video_max_mbps` | erro `video.tamanho` (limite geral); avisos (limites de API) |
| Capítulos | `limites_texto.youtube.capitulos` (`primeiro_timestamp`, `min_timestamps`, `duracao_min_capitulo_s`) + duração do vídeo | erros `capitulos.*`; avisos `capitulos.fora_da_descricao`, `capitulos.antigos` (o JSON é mais velho que o vídeo). Na entrada, `00:75` e `1:75:00` são erro de uso (segundos e minutos vão até 59), `100:00` pede `1:40:00`, e `t` negativo no JSON é recusado |
| Thumbnail / capa | `thumbnail.youtube` ou `capas.<plat>`: `formatos`, `proporcao`, `largura_min_px`, `altura_min_px`, `resolucao_minima_para_teste_ab_px`, `peso_max_mb`, `peso_max_seguro_mb` | erros `thumb.formato`, `thumb.proporcao`, `thumb.largura_min`, `thumb.peso`…; avisos `thumb.teste_ab`, `thumb.peso_celular`, `thumb.nenhuma` |
| Legenda `.srt` | — (formato SubRip; fim ≤ duração do vídeo + 0,5 s; UTF-8) | erros `legenda.ausente`, `legenda.formato`, `legenda.duracao` |
| Privacidade e agendamento | regra da API: `publishAt` só com `private`; data futura; fuso obrigatório | erros `privacidade.valor`, `agenda.formato`, `agenda.fuso`, `agenda.passado`, `agenda.privacidade` |
| Declaração de IA | — | aviso `ia.declaracao` enquanto `conteudo_sintetico` for `null` |
| Fatos citados | `pesquisa/fatos.json`: `status`, `caduca_em` (comparado com hoje ou com a data agendada), `confianca` | erros `fatos.ficha`, `fatos.inexistente`, `fatos.status`, `fatos.vencido`; avisos `fatos.vencendo` (≤ 14 dias), `fatos.confianca` |
| Créditos obrigatórios | `broll/licencas.json` (`exige_atribuicao`, `atribuicao`, `uso_comercial`, `usado_em`) + `broll_id` do storyboard | erros `licencas.credito`, `licencas.sem_texto`, `licencas.excluido` (crédito em uso tirado por `--broll` no vídeo longo); avisos `licencas.declarado` (o mesmo num corte, com exceção registrada), `licencas.divergente` (storyboard aponta, `usado_em` não lista), `licencas.sem_registro` (storyboard usa id que não está em `licencas.json`), `licencas.comercial` |
| Idade e origem dos limites | `verificado_em` + `revalidar_a_cada_meses` × 30 dias (hoje 90) | avisos `limites.vencidos`, `limites.data`, `limites.origem` |
| **Portão de QA** | `qa/relatorio.json` (gravado por `da conferencia`, o comando do kit de direção de arte; contrato em `kit-api.md` §18): existe, é um objeto, `ok` = true sem item de erro, `da_sha256` = DA atual, **o arquivo de vídeo do pacote está em `alvos` com o mesmo `bytes` e `sha256`** (sem a lista `alvos` reprova), `verificado_em` mais novo que o arquivo de vídeo **e** não adiantado — nem em relação ao relógio, nem em relação à data de gravação do próprio relatório (folga de 5 min) | erro `qa.portao`; com `--sem-qa`, aviso `qa.dispensado` + exceção gravada; aviso `qa.fuso` se `verificado_em` vem sem fuso (lido como hora local); aviso `qa.depois` se thumbnail ou `.srt` mudaram depois do QA |

"Caracteres" são contados em unidades UTF-16 (emoji fora do plano básico conta 2): é como o TikTok documenta a legenda e nunca subestima as outras plataformas. Acento em NFC conta 1 caractere e 2 bytes.

**O que `validar` não faz**: não mede loudness, não confere zona segura nem carimbos (é o QA: `da conferencia`), não decodifica o vídeo (só `ffprobe`), não abre a rede, não confere se o título é bom.

## 5. `publicacao/pacote.json` e o estado de cada pacote

```json
{"versao": 1, "gerado_em": "ISO", "projeto": "nome na DA", "da_sha256": "…",
 "limites": {"origem": "kit: /caminho/real/plataformas.json", "verificado_em": "2026-10-05", "idade_dias": 1},
 "ok": true, "resumo": {"pacotes": 4, "erros": 0, "avisos": 1},
 "excecoes": [{"tipo": "sem_qa | credito_excluido", "pacote": "youtube", "em": "ISO", "motivo": "…", "problemas": ["…"]}],
 "excecoes_historico": [{"…": "toda exceção já concedida; só cresce"}],
 "pacotes": [{"id": "youtube", "plataforma": "youtube", "corte": null, "meta": "publicacao/youtube/meta.json",
              "descricao_txt": "…", "checklist": "…", "arquivo_video": "render/final.mp4", "thumbnail": "…", "legenda_srt": "…",
              "titulo": "…", "privacidade": "private", "agendar_para": null,
              "estado": "ok | ok_com_excecao | vencida | reprovado | desatualizada | nao_validado",
              "conferencia": {"em": "ISO", "erros": ["só quando estado = vencida: o que a conferência de agora reprovou"]},
              "validacao": {"ok": true, "validado_em": "ISO", "erros": 0, "avisos": 1,
                            "itens": [{"id", "categoria", "severidade", "mensagem", "como_corrigir"}],
                            "medidas": {"video": {"largura", "altura", "duracao", "fps", "codec_video", "extensao", "…"}, "thumbnail": {…}, "…": "…"},
                            "impressao": {"meta_sha256", "arquivo_video": {"bytes", "mtime_ns"}, "thumbnail": {…}, "legenda_srt": {…}, "descricao_txt_sha256"},
                            "qa": {…}, "excecao": null, "excecoes": [], "da_sha256": "…"},
              "envio": {"video_id", "url", "enviado_em", "por", "validacao_no_envio", "excecoes", "…": "só depois de enviado"}}]}
```

`validacao` é o que o último `validar` gravou. `estado` é calculado **na hora** por todo comando que regrava o índice (e por `enviar_youtube.py`), nesta ordem:

| estado | quando | como sair |
|---|---|---|
| `nao_validado` | nunca passou por `validar` (ou o índice foi editado e ficou ilegível) | `validar` |
| `desatualizada` | o pacote mudou depois de validar: `meta.json`, vídeo, thumbnail, `.srt` ou `descricao.txt` (`impressao` diferente) | `validar` |
| `reprovado` | a validação gravada tem erro | corrigir + `validar` |
| `vencida` | a validação gravada aprovou e o pacote não mudou, **mas a conferência refeita agora reprova**: QA apagado, reprovado ou de outra DA; DA com revisão aberta; fato rebaixado ou vencido; crédito obrigatório novo; data agendada que passou; limite essencial que sumiu; exceção que não cobre o problema de agora | resolver o que `conferencia.erros` lista + `validar` |
| `ok` / `ok_com_excecao` | aprovado e confirmado agora (o segundo com `--sem-qa` ou com crédito declarado fora de um corte) | — |

A conferência refeita custa um `ffprobe` por pacote e **nunca aprova** nada sozinha: só `validar` aprova; ela só tira a aprovação. `ok` global = todos os pacotes em `ok`/`ok_com_excecao`. `checklist`, `registrar` e `enviar_youtube.py enviar` (simulação e envio) usam o mesmo cálculo; o envio só acontece nesses dois estados.

Uma **exceção** cobre só os problemas listados em `problemas` na hora em que foi concedida: se o QA mudar depois (ex.: dispensado quando não existia, e agora existe e reprova), o pacote fica `vencida` até o usuário decidir de novo. `excecoes` traz as exceções dos pacotes hoje em `ok_com_excecao`; `excecoes_historico` guarda todas as já concedidas e não encolhe ao revalidar (a mesma exceção — mesmo pacote, motivo e problemas — entra uma vez só, com a primeira data).

`envio.json` — gravado pelo envio pela API (`por: "api"`, com `video_id`, `url`, `studio`, `etapas`, `privacidade_pedida`/`devolvida`, `agendado_para`, `canal`, `codigo_confirmado`, `numero_do_envio`) ou por `pacote.py registrar` (`por: manual|conector|navegador`, com `url`). Nos dois casos leva `validacao_no_envio` (o estado na hora), `validado_em` e `excecoes` (a exceção inteira: motivo, problemas e data); o registro manual de um pacote `vencida` leva também `problemas_no_envio`.

## 6. Variáveis de ambiente e códigos de saída

| variável | uso |
|---|---|
| `VIDEO_OPS_HOME` | pasta de configuração do usuário (padrão `~/.config/video-ops`): credenciais e token do YouTube. Em testes, aponte para a área de teste |
| `VIDEO_OPS_PLATAFORMAS_JSON` | arquivo alternativo de limites, para testes e para revalidar antes de o kit ser atualizado; `validar` avisa (`limites.origem`) |
| `DA_DEBUG` | `1` = defeito interno aparece com traceback (convenção do kit; a suíte roda assim). Sem ela sai uma linha `erro interno: …` e código 1 |
| `VIDEO_OPS_YT_TESTE_BASE` | endereço do servidor falso — somente testes; só aceita `http://127.0.0.1:…` |
| `VIDEO_OPS_FFPROBE` | caminho do ffprobe, se ele não estiver no `PATH` |

Não existe variável para trocar o relógio: uma validação com data falsa aprovaria fato vencido e agendamento passado sem rastro (os testes trocam `pacote.agora` dentro do processo).

Códigos de saída dos dois scripts: **0** ok · **1** reprovado, recusado ou erro · **2** projeto sem direção de arte · **64** uso incorreto.

## 7. Testes

```bash
cd ~/.claude/skills/video-publicacao/scripts
python3 -m unittest                                   # 167 testes (165 rodam, 2 de rede ficam pulados), ~20 s com a trava livre, sem rede
VIDEO_OPS_TESTE_REDE=1 python3 -m unittest testes.test_rede   # confere endereços e escopos nos documentos públicos do Google
python3 testes/ponta_a_ponta.py --destino "/tmp/teste de publicação"   # 56 passos pela linha de comando, com ffmpeg sob a trava (~30 s)
```

A suíte cria os projetos em pastas temporárias com espaço e acento no nome (com a DA aprovada pela função do kit), usa uma `VIDEO_OPS_HOME` própria, roda com `DA_DEBUG=1` (defeito interno vira exceção, não uma linha de "erro interno") e apaga os `__pycache__` ao sair. Arquivos:

- `test_pacote.py` — criação, capítulos, descrição, cada item de `validar`, índice e checklist; `SondaReal` gera dois vídeos de 1 s (320×180) por `video.executar` (trava global) e se pula se a fila passar de 240 s.
- `test_enviar_youtube.py` — OAuth com PKCE, envio retomável, quedas, renovação de token, thumbnail e legenda contra `servidor_falso.py`.
- `test_regressoes.py` — um bloco por achado da revisão independente de 2026-10-06: validação que vence (QA apagado, DA mudada, fato vencido, agenda passada) em `resumo`, `checklist`, `registrar` e no envio; QA com data adiantada; créditos por `usado_em` × `broll_id` e `--broll`; limites essenciais ausentes; saída sem terminal (`autorizar` num pipe); código de confirmação de uso único; exceção durável; MKV × WebM (com `ffprobe` de verdade); `definir`; entradas de tipo errado.
- `ponta_a_ponta.py` — não é coletado pelo unittest: projeto real com `da init`, vídeos minúsculos, os casos bons e ruins pela linha de comando e a simulação de envio.
