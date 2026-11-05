# YouTube Data API v3 — o que `enviar_youtube.py` fala, com fonte

**Conferido em 2026-10-06** nas páginas oficiais listadas no fim. Leia este arquivo quando for preparar o primeiro envio pela API, quando a API devolver um erro que a mensagem do script não resolveu, ou antes de mexer no código.

> **Não testado contra a API real.** Não há credenciais do Google nesta máquina. O script foi testado contra um servidor local (`scripts/testes/servidor_falso.py`) que imita o subconjunto do protocolo descrito aqui. Isso prova que o cliente fala o protocolo documentado; não prova que o YouTube aceita o envio. **O primeiro envio real deve ser privado e conferido no Studio** — o script já força isso (§8).

## 1. O que o usuário cria uma vez (o Claude não cria nem digita credencial)

1. No Google Cloud Console: um projeto → ativar a **YouTube Data API v3**.
2. Configurar a tela de consentimento OAuth. Com público **externo** e estado de publicação **«Testing»**, o refresh token **expira em 7 dias** (a menos que os escopos sejam só nome, e-mail e perfil — não é o caso). Em «Testing», a conta do canal precisa estar na lista de usuários de teste.
3. Criar um **ID do cliente OAuth do tipo «App para computador» (Desktop app)**. Só esse tipo aceita o redirecionamento para `http://127.0.0.1:<porta>`; cliente «Aplicativo da Web» é recusado pelo script.
4. Baixar o JSON do cliente e salvar em `$VIDEO_OPS_HOME/youtube_client_secret.json` (padrão `~/.config/video-ops/`), com `chmod 600`. O script lê `installed.client_id` e `installed.client_secret`; os endereços `auth_uri`/`token_uri` do arquivo são **ignorados** (os oficiais estão fixos no código).

Os rótulos exatos do console mudam; os quatro passos acima não foram refeitos hoje numa conta real — siga o campo equivalente. Nunca peça ao usuário para colar o conteúdo desse arquivo na conversa.

Outras causas oficiais de um refresh token parar de funcionar: o usuário revogou o acesso; 6 meses sem uso; mais de 100 refresh tokens vivos para a mesma conta e o mesmo cliente (o mais antigo é invalidado sem aviso); acesso com prazo concedido pelo usuário. Em todos os casos o script responde `invalid_grant` → `autorizar --confirmar` de novo.

## 2. Autorização — OAuth 2.0 de aplicativo instalado, com PKCE

| passo | o que o script faz | fonte |
|---|---|---|
| verificador | `code_verifier` de 86 caracteres de `[A-Za-z0-9-_]` (o guia exige 43 a 128 de `[A-Z a-z 0-9 - . _ ~]`) | guia §"Create a code challenge" |
| desafio | `code_challenge` = Base64URL sem `=` do SHA-256 do verificador; `code_challenge_method=S256` | idem |
| retorno | servidor HTTP só em `127.0.0.1`, porta livre; `redirect_uri=http://127.0.0.1:<porta>` (o guia prefere o IP a `localhost`, por causa de firewall) | guia §"Loopback IP address" |
| pedido | `GET https://accounts.google.com/o/oauth2/v2/auth` com `client_id`, `redirect_uri`, `response_type=code`, `scope` (separados por espaço), `code_challenge`, `code_challenge_method`, `state` | guia §"Send a request to Google's OAuth 2.0 server" |
| consentimento | **o usuário** entra com a conta do canal e autoriza, no navegador dele; o script imprime o endereço de consentimento na hora (com `flush`: sai mesmo com a saída num pipe ou num arquivo) e só espera — 300 s por padrão (`--espera`). Quem chama precisa de um prazo maior que a espera: rode em segundo plano ou use `--espera 100` | — |
| volta | `?code=…&state=…` (ou `?error=access_denied`); pedido com `state` diferente recebe 400 e é ignorado | idem |
| troca | `POST https://oauth2.googleapis.com/token` (form): `client_id`, `client_secret` (se o arquivo trouxer), `code`, `code_verifier`, `grant_type=authorization_code`, `redirect_uri` | guia §"Exchange authorization code" |
| resposta | `access_token`, `expires_in`, `refresh_token`, `scope`, `token_type=Bearer` (e `refresh_token_expires_in` quando o acesso tem prazo) | idem |
| renovação | `POST …/token` com `client_id`, `client_secret`, `grant_type=refresh_token`, `refresh_token`; o refresh token antigo é conservado | guia §"Refreshing an access token" |

O token fica em `$VIDEO_OPS_HOME/youtube_token.json`, criado já com permissão **600** (se alguém afrouxar, o script corrige e avisa). Junto vão o nome e o id do canal (`channels.list?part=snippet&mine=true`, 1 unidade de cota), para que o plano de envio mostre **a conta** sem tocar a rede. Para desfazer: apagar o arquivo e revogar o acesso do aplicativo na página de permissões da Conta do Google (o guia também documenta `POST https://oauth2.googleapis.com/revoke?token=…`, que o script não implementa).

### Escopos (documento de descoberta da API)

| escopo | para quê | quando é pedido |
|---|---|---|
| `…/auth/youtube.upload` — "Manage your YouTube videos" | `videos.insert`, `thumbnails.set` | sempre |
| `…/auth/youtube.readonly` — "View your YouTube account" | `channels.list` (mostrar a conta) | sempre |
| `…/auth/youtube.force-ssl` — "See, edit, and permanently delete your YouTube videos, ratings, comments and captions" | `captions.insert` (não aceita `youtube.upload`) | só com `autorizar --legendas` |

O escopo de legendas é amplo (dá poder de apagar vídeos). Por isso é opcional: sem ele o script envia vídeo e thumbnail e manda subir o `.srt` pelo Studio.

## 3. Envio retomável do vídeo

1. **Abrir a sessão** — `POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` (mais `&notifySubscribers=false` se o pacote pedir). Cabeçalhos: `Authorization: Bearer …`, `Content-Type: application/json; charset=UTF-8`, `Content-Length`, `X-Upload-Content-Length` (tamanho do arquivo), `X-Upload-Content-Type` (`video/mp4`, `video/quicktime`…). Corpo: o recurso `video`. Resposta `200` com o endereço da sessão no cabeçalho `Location`.
2. **Enviar em pedaços** — `PUT <sessão>` com `Content-Length`, `Content-Type` e `Content-Range: bytes INÍCIO-FIM/TOTAL`. "The chunk size must be a multiple of 256 KB" (menos o último); o script usa 8 MB (`--pedaco-mb`, arredondado para múltiplo de 256 KB). Resposta `308 Resume Incomplete` com `Range: bytes=0-N` → o próximo pedaço começa em N+1 (o script segue o `Range` do servidor, não a própria conta). Resposta `201 Created` com o recurso `video` → terminou.
3. **Perguntar a situação** — `PUT <sessão>` com `Content-Length: 0` e `Content-Range: bytes */TOTAL`. `308` + `Range` diz quanto chegou (`308` sem `Range` = nada); `200/201` = já concluído.
4. **Falhas** — `500`, `502`, `503`, `504` e queda de conexão: esperar com recuo exponencial (1 s, 2 s, 4 s… até 64 s, mais até 1 s ao acaso), perguntar a situação e continuar. Depois de `--tentativas` falhas seguidas (padrão 6) o script para com código 1 e **deixa o envio retomável**: o endereço da sessão fica em `$VIDEO_OPS_HOME/youtube_envios/<chave>.json` (600; nunca impresso, porque quem tem o endereço consegue completar o envio). Rodar o mesmo comando com o mesmo código retoma. O script também para (retomável) se o servidor responder 5 vezes seguidas sem aceitar nenhum byte novo.
5. **Sessão expirada** — `404` na sessão: "you will need to start a new resumable upload". O script abre outra e recomeça do zero.
6. O endereço da sessão só é aceito se for HTTPS em `*.googleapis.com` — tanto o que a API devolve quanto o que é **lido de volta** do arquivo de estado numa retomada (endereço estranho é descartado e o envio recomeça em sessão nova); redirecionamentos nunca são seguidos (o `Authorization` não vai para outro endereço).

## 4. `videos.insert` — campos e regras

- Limites: arquivo de até **256 GB**; tipos aceitos `video/*` e `application/octet-stream`.
- Campos que o script envia: `snippet.title` ("Maximum length of 100 characters… except < and >"), `snippet.description` ("Maximum length of 5000 **bytes**… except < and >"), `snippet.tags[]` (500 caracteres na soma; vírgulas contam; tag com espaço conta como se tivesse aspas), `snippet.categoryId` (só se `categoria_id` estiver no meta.json; os ids variam por região — `videoCategories.list`), `snippet.defaultLanguage` (o `idioma` do pacote), `status.privacyStatus` (`private`, `public`, `unlisted`), `status.publishAt`, `status.selfDeclaredMadeForKids`, `status.containsSyntheticMedia`.
- **Agendamento**: `status.publishAt` "can be set only if the privacy status of the video is private"; data no passado publica **na hora**. O script converte `agendar_para` para UTC (`AAAA-MM-DDThh:mm:ssZ`) e a validação do pacote reprova data passada e privacidade diferente de `private`. Pela ajuda do Studio, vídeo agendado fica privado até a hora; canal com strike não publica agendado durante a penalidade.
- **Projeto de API não auditado**: "All videos uploaded via the videos.insert endpoint from unverified API projects created after 28 July 2020 will be restricted to private viewing mode." Para sair disso, o projeto passa por auditoria do Google. Na prática: **com cliente próprio não auditado, todo envio pela API fica privado**, e tornar público é feito no Studio. O script compara a privacidade pedida com a devolvida e avisa quando difere.
- `notifySubscribers` (padrão `true`) — parâmetro de consulta; o meta.json tem `notificar_inscritos`.
- Erros que o script traduz: `quotaExceeded`, `uploadLimitExceeded`, `forbidden`, `insufficientPermissions`, `invalidTitle`, `invalidDescription`, `invalidTags`, `invalidPublishAt`, `invalidCategoryId`, `defaultLanguageNotSet`, `youtubeSignupRequired`, `authError`.
- Um arquivo vertical ou quadrado de até 3 minutos enviado por este mesmo método **vira Short** sozinho (regra da plataforma, não da API).

## 5. Thumbnail e legenda

- **`thumbnails.set`** — `POST https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=<id>&uploadType=media`, corpo = a imagem, `Content-Type: image/png` ou `image/jpeg`. Limite **50 MB** (subiu de 2 MB em 2026-09-14, segundo o histórico de revisões). Cota ≈ 50 unidades. Erro `forbidden` costuma ser conta sem verificação (thumbnail personalizada exige conta verificada). Capa de **Short** não é enviada por aqui: a ajuda só garante o envio pelo Studio no computador.
- **`captions.insert`** — `POST https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet`, corpo `multipart/related` com duas partes: o JSON `{"snippet": {"videoId", "language" (BCP-47, o `idioma` do pacote), "name" (até 150 caracteres; o script manda vazio, ou `legenda_nome` do meta.json), "isDraft": false}}` e o arquivo `.srt` como `application/octet-stream`. Limite 100 MB. Cota 400 unidades. Erros: `captionExists`, `contentRequired`, `invalidMetadata`, `nameTooLong`, `videoNotFound`, `forbidden`.
- As formas `uploadType=media` e `uploadType=multipart` são o protocolo "simple" de upload das APIs do Google; o documento de descoberta confirma que os dois métodos o aceitam nesses caminhos (`protocols.simple`, `multipart: true`). O guia do YouTube só descreve em detalhe o protocolo retomável — **estes dois pedidos são o trecho com menos confirmação oficial do script**. Se o primeiro envio real falhar aqui, o vídeo já subiu: conclua thumbnail e legenda pelo Studio e relate o erro.

## 6. Cotas (desde 2026-06-01 há baldes separados)

| chamada | custo | balde |
|---|---|---|
| `videos.insert` | 1 por chamada | próprio: **100 chamadas por dia** |
| `thumbnails.set` | ≈ 50 unidades | geral: 10.000 unidades por dia |
| `captions.insert` | 400 unidades | geral |
| `channels.list` | 1 unidade | geral |

As cotas zeram à meia-noite do horário do Pacífico. Até 2025-12-04 um envio custava ≈ 1.600 unidades; muito material na internet ainda cita esse número. O limite diário de envios **do canal** (regra do YouTube, não da API) é outro e devolve `uploadLimitExceeded`.

## 7. O que o script recusa ou muda sozinho

- Sem `--confirmar CODIGO`, só simula. O código sai do plano inteiro (texto, arquivo, thumbnail, legenda, conta, privacidade, agendamento, **o envio anterior do pacote e a opção `--reenviar`**): mudou qualquer coisa, o código muda — **aprovação de um envio não vale para o seguinte**. Um código serve para um envio: depois de concluído, o plano de reenvio tem outro código, e o código antigo é recusado com mensagem própria. Durante uma retomada (envio interrompido, ou thumbnail/legenda que falhou) o código se mantém, porque o `envio.json` só é gravado quando tudo termina.
- Pacote não validado, reprovado ou alterado depois de `pacote.py validar` → recusado. **A validação gravada não basta**: a simulação e o envio refazem a conferência inteira na hora (um `ffprobe`); se ela reprovar — QA apagado ou reprovado, DA mudada ou sem aprovação, fato vencido, crédito novo, data agendada que passou — o pacote está "vencido" e o motivo aparece em "NÃO PODE SER ENVIADO AINDA". Exceções registradas (`--sem-qa`, crédito declarado fora de um corte) aparecem no plano e são copiadas para o `envio.json`, com motivo e data.
- Privacidade enviada = **`private`**, mesmo que o meta.json peça outra; `--usar-privacidade-do-pacote` muda isso.
- Pacote com `envio.json` não é enviado de novo sem `--reenviar` (que cria outro vídeo no canal; o plano diz isso e traz o endereço do envio anterior).
- Tirar a thumbnail ou a legenda de um envio já feito (`--sem-thumbnail`, `--sem-legenda`) pede novo código, mas **não** reenvia o vídeo.

## 8. Primeiro envio real

Enquanto `$VIDEO_OPS_HOME/youtube_envios/historico.json` estiver vazio, o envio vai **privado e sem `publishAt`**, digam o que disserem o pacote e as opções. Roteiro: enviar → abrir o link do Studio que o script imprime → conferir título inteiro, primeiras linhas da descrição, capítulos na barra, thumbnail, legenda, idioma → agendar ou publicar pelo Studio. Do segundo envio em diante o agendamento do pacote passa a valer.

## 9. O que NÃO foi verificado

- Nenhuma chamada foi feita à API real (nem `videos.insert`, nem `thumbnails.set`, nem `captions.insert`, nem o consentimento OAuth com uma conta Google).
- `name` vazio em `captions.insert`: a documentação exige o campo, não diz se aceita vazio.
- Tamanho de pedaço ideal e validade da sessão retomável: a documentação não dá número para a validade.
- Passos do Google Cloud Console (§1): descritos de memória do fluxo, não refeitos hoje.

## Fontes (todas abertas em 2026-10-06)

| assunto | endereço | atualizada em |
|---|---|---|
| Envio retomável | https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol | 2026-09-14 |
| `videos.insert` | https://developers.google.com/youtube/v3/docs/videos/insert | 2026-09-14 |
| Recurso `video` (título, descrição, tags, `publishAt`…) | https://developers.google.com/youtube/v3/docs/videos | 2026-09-16 |
| `thumbnails.set` | https://developers.google.com/youtube/v3/docs/thumbnails/set | 2026-09-14 |
| `captions.insert` e recurso `caption` | https://developers.google.com/youtube/v3/docs/captions/insert · https://developers.google.com/youtube/v3/docs/captions | 2026-09-14 / 09-16 |
| `channels.list` | https://developers.google.com/youtube/v3/docs/channels/list | 2026-09-14 |
| OAuth 2.0 para apps instalados (PKCE, loopback, token) | https://developers.google.com/youtube/v3/guides/auth/installed-apps | 2026-09-14 |
| Validade de refresh token («Testing» = 7 dias) | https://developers.google.com/identity/protocols/oauth2 | 2026-05-26 |
| Cotas | https://developers.google.com/youtube/v3/determine_quota_cost · https://developers.google.com/youtube/v3/getting-started | 2026-09-15 / 09-14 |
| Histórico de revisões (baldes de cota, thumbnail de 50 MB) | https://developers.google.com/youtube/v3/revision_history | 2026-09-30 |
| Documento de descoberta (caminhos de upload, escopos, esquemas) | https://youtube.googleapis.com/$discovery/rest?version=v3 | revisão 20261005 |
| Configuração OpenID do Google (endereços de autorização e token, S256) | https://accounts.google.com/.well-known/openid-configuration | — |
| Agendar publicação no Studio | https://support.google.com/youtube/answer/1270709 | — |

Os dois últimos documentos de máquina são conferidos pelo teste de rede: `cd ~/.claude/skills/video-publicacao/scripts && VIDEO_OPS_TESTE_REDE=1 python3 -m unittest testes.test_rede` (passou em 2026-10-06).
