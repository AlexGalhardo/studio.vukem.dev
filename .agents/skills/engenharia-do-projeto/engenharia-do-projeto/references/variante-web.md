# Variante web: como ficam dados, permissões, cache e testes em PostgreSQL com segurança por linha?

Variante. Só vale para aplicação web com PostgreSQL e segurança por linha, login, arquivos e
pagamento por assinatura. O equivalente geral está em `references/dados.md`.

Leia quando: a stack é desse tipo, junto de `references/dados.md`, `references/testes.md` ou
`references/fronteiras.md`. Sempre por seção: use o índice.
Não é aqui: os princípios (`references/dados.md`); os princípios de cobrança
(`references/stack.md` §5).

## O mínimo

- Confira a §1 antes de copiar qualquer molde: se o banco não tem os papéis e a função que ela
  lista, o molde não roda sem o calço.
- Crie objeto novo com tudo revogado e só depois conceda: há plataforma em que ele nasce aberto.
- Ponha a guarda na primeira linha de toda função com privilégio e revogue a execução.
- Acrescente valor de enumeração numa migração e use-o em outra.
- Não deixe leitura compartilhada tocar sessão nem dado restrito.
- Rode cada molde antes de confiar: todos foram generalizados e não foram executados nesta forma.

Conteúdo: 1. O que a variante supõe 2. Privilégios 3. Funções 4. Políticas por linha
5. Enumeração 6. Testes no banco e banco de teste 7. Arquivos 8. Cache 9. Pagamento por assinatura
10. Ponta a ponta 11. Armadilhas 12. Onde estão os moldes

## 1. O que a variante supõe

Os moldes usam os nomes das plataformas de banco com API automática sobre PostgreSQL. Confira os
seis no banco do projeto antes de copiar um molde.

| Papel no desenho | Nome nos moldes | Como conferir |
| --- | --- | --- |
| Papel de visitante, sem sessão | `anon` | `select 1 from pg_roles where rolname = 'anon'` devolve uma linha |
| Papel de quem tem sessão | `authenticated` | o mesmo, com `authenticated` |
| Papel de serviço, que ignora as políticas | `service_role` | `select rolbypassrls from pg_roles where rolname = 'service_role'` devolve verdadeiro |
| Função "quem sou eu" | `auth.uid()` | `select auth.uid()` devolve nulo fora de uma sessão |
| Configuração de sessão com as declarações do token | `request.jwt.claims` | `select current_setting('request.jwt.claims', true)` não dá erro |
| Tabela de usuários do provedor | `auth.users` | `select count(*) from auth.users` não dá erro |

Confira também com o que um objeto novo nasce: crie uma tabela de teste e rode
`select has_table_privilege('anon', 'public.<tabela>', 'TRUNCATE')`. Verdadeiro quer dizer que a
plataforma concede tudo de fábrica, e a §2 é obrigatória.

Com backend próprio sobre PostgreSQL, há dois caminhos, nenhum praticado neste método (confira):
criar o calço (o SQL está em `assets/variante-web/banco-de-teste.sh`) e fazer o servidor abrir cada
transação com `set local role` e `set_config('request.jwt.claims', <declarações>, true)`; ou
trocar, nos moldes, os seis nomes pelos papéis e pela função de identidade que o projeto já tem.

## 2. Privilégios: revogar antes de conceder

Nessas plataformas os privilégios de fábrica dão tudo, a todos os papéis, em todo objeto novo do
esquema público. Quem só soma concessões não tira o que veio de fábrica.
Molde: `assets/variante-web/migracao-tabela-nova.sql`.

| Faça | Detalhe |
| --- | --- |
| Revogue primeiro | `revoke all privileges on <objetos novos> from anon, authenticated;` em toda migração que cria tabela, visão ou sequência |
| Conceda o mínimo | `anon`: só `select` no que é público. `authenticated`: os comandos que as políticas decidem; só leitura nas tabelas de serviço; sem `delete` onde a linha só sai junto com a conta. `service_role`: tudo. Visão: só leitura |
| Revogue objeto a objeto | Não mexa nos privilégios padrão do banco inteiro: muda o comportamento de tudo |
| Fixe num teste só de privilégios | `table_privs_are` por tabela e por papel, com a lista exata, e as provas por efeito: `truncate` falha para visitante, logado e administrador; escrita pela visão falha. Objeto novo entra no arquivo na mesma mudança |
| Anote o efeito no documento de dados | Sem privilégio, o visitante recebe o erro `42501`, e não zero linhas |

## 3. Funções de autorização e função com privilégio

Molde das duas: `assets/variante-web/funcao-com-guarda.sql`.

| | Função de autorização | Função com privilégio |
| --- | --- | --- |
| Para quê | responder sim ou não: "é administrador?", "tem acesso pago?", "pode ler isto?" | operação que atravessa as políticas: publicar em vários passos, cruzar tabelas que ninguém lê inteiras |
| Atributos | `language sql stable security definer set search_path = ''`; todo objeto com o esquema | `security definer`, `set search_path = ''`; a guarda é a primeira instrução |
| Identidade | não recebe por argumento: usa `auth.uid()`. Só lê | a mesma regra: quem decide é a sessão de quem chama |
| Execução | todos os papéis; para `anon`, responde falso | `revoke execute ... from public, anon`; `grant` a `authenticated` e `service_role` |
| Teste | atributos e resultado por persona | visitante falha por privilégio; logado falha pela guarda, e o dado fica como estava; administrador passa |
| Quantas | duas ou três; toda política e toda função com privilégio usa só elas, e a definição de "administrador" fica num lugar | uma por operação que precisa atravessar |

- O caminho de busca vazio impede que um objeto de mesmo nome, em outro esquema, seja chamado
  dentro de função que roda com direitos elevados.
- `service_role` tem execução e não tem identidade: `auth.uid()` é nulo e a guarda recusa. É de
  propósito, para a credencial de serviço não virar atalho por cima da guarda.
- `create or replace` numa migração posterior mantém proprietário, caminho de busca e privilégios:
  diga isso no cabeçalho da migração e deixe o teste confirmar.

## 4. Padrões de política por linha

Nome: `<tabela>_<quem>_<comando>`. Um teste confere o conjunto exato de políticas de cada tabela
(`policies_are`): nada a mais, nada a menos.

| Caso | Política |
| --- | --- |
| Leitura pública do que está publicado | `for select to anon, authenticated using (status = 'publicado')` |
| Tabela filha segue o pai | `using (exists (select 1 from public.app_itens i where i.id = item_id and i.status = 'publicado'))` |
| Administrador faz tudo no conteúdo | `for all to authenticated using ((select public.app_is_admin())) with check ((select public.app_is_admin()))` |
| Da própria pessoa | `using (user_id = (select auth.uid()))`, e a mesma condição em `with check` |
| Onde não deve haver acesso | nenhuma política: o administrador não tem política nas tabelas da própria pessoa dos outros, nem de escrita nas tabelas de serviço |
| Escrita que cita outro registro | acrescente `exists (select 1 from public.app_itens i where i.id = item_id)`: o item citado tem de ser visível para quem grava |
| Função dentro de política | embrulhe em subconsulta, `(select public.app_is_admin())`: é avaliada uma vez por comando, e não uma vez por linha |

## 5. Enumeração: valor novo e uso em migrações separadas

Um valor de enumeração recém-criado não pode ser usado na transação que o cria, e cada arquivo de
migração roda numa transação. Tudo num arquivo só falha.

1. Migração A: só `alter type public.app_<tipo> add value if not exists '<valor>';` e o
   comentário do tipo. O cabeçalho diz por que é só isso e qual é a migração seguinte.
2. Migração B, com o carimbo seguinte: o que usa o valor. O cabeçalho cita a A.
3. No registro de decisões: valor de enumeração não sai depois; voltar atrás pede recriar o tipo.

A mesma restrição dá a ordem de ida a produção: o build novo valida entradas contra os valores
gerados do banco e falha num banco sem o valor; o código antigo ignora o que não conhece.

## 6. Testes de permissão dentro do banco e o banco de teste

Os testes são arquivos SQL com pgTAP, um por persona. Molde:
`assets/variante-web/teste-por-persona.sql` (o que cobrir está em `references/testes.md` §6).

| Peça | Como |
| --- | --- |
| Ordem dos arquivos | Numerados: estrutura; funções; políticas como visitante, como logado, como pagante, como administrador; arquivos; privilégios; funções de administração; depois, um arquivo por tabela nova, com tudo dela |
| Cada arquivo | `begin`; `select plan(N)`; os próprios dados, numa faixa de identificadores que não colide com a dos dados de exemplo; as afirmações; `select * from finish()`; `rollback`. Plano desatualizado faz o arquivo falhar, de propósito: afirmação que não rodou também é falha |
| Virar persona | `set local role anon` ou `authenticated`, e `select set_config('request.jwt.claims', '<declarações>', true)`. Vazias para o visitante. `reset role` volta a quem abriu a transação, que equivale ao serviço |

| O bloqueio vem de | O que acontece | Como afirmar |
| --- | --- | --- |
| Política, em `update` e `delete` | nenhum erro: zero linhas afetadas | `is_empty` sobre o comando com `returning`, ou contagem antes e depois |
| Política, em `insert` | erro `42501` | `throws_ok` com o código |
| Falta de privilégio; guarda de função | erro `42501` | `throws_ok` com o código |
| Restrição, unicidade, trava | erro com o código de cada uma (`23514`, `23505`, o que a trava lança) | `throws_ok` com o código |

**Banco de teste sem contêiner.** Molde: `assets/variante-web/banco-de-teste.sh`. Recria um banco
com nome terminado em `_teste`, aplica o calço, as migrações em ordem (cada arquivo numa
transação), os dados de exemplo e os testes, e recusa servidor que não seja local. O calço cria os
três papéis, `auth.users`, `auth.uid()`, os privilégios de fábrica e o pgTAP; nada do produto.

- O calço imita, não é. Rode os mesmos testes também no ambiente real da plataforma: é lá que
  aparece a proteção que ela tem e o calço não tem.
- Aponte para o servidor, e não para um intermediário de conexões: ele não aceita criar nem
  apagar banco. No CI, leia a versão do PostgreSQL instalada em vez de fixá-la.
- Função que grava e é consultada no mesmo comando não enxerga a linha nova: chame, depois consulte.

## 7. Arquivos: depósito público, depósito privado e envio direto

Depósitos criados por migração, com limite de tamanho e lista de tipos no próprio depósito.
**Público** para a vitrine, com escrita só de administrador. **Privado** para o que é restrito: a
pessoa comum não tem nem leitura, e o arquivo sai por endereço assinado de vida curta, gerado no
servidor depois de conferir sessão e direito. O envio vai direto ao depósito, porque função de
servidor tem limite de corpo:

| Passo | Quem | O que faz |
| --- | --- | --- |
| 1 | navegador | valida tipo, tamanho, duração e proporção, e mostra erro claro |
| 2 | ação de servidor | exige administrador, valida de novo, confere que o item existe, monta o caminho com um identificador aleatório novo e devolve um endereço assinado de envio |
| 3 | navegador | envia direto ao depósito |
| 4 | ação de registro | exige administrador, confere que o caminho é do próprio item, usa o tamanho e o tipo que o depósito informa, grava a linha, apaga o arquivo antigo e, com o item publicado, expira o cache |

- Limites e mensagens moram num módulo puro, usado no navegador, no servidor e nos testes; os
  caminhos, num módulo só: uma ação não registra caminho que ela mesma não poderia ter montado.
- Em depósito público a política só governa a listagem: quem sabe o endereço abre o arquivo.
- O arquivo nasce no depósito antes da linha no banco: o administrador precisa enxergar tudo, ou
  o registro falha. Arquivo compartilhado entre versões só se apaga quando nenhuma outra o usa.

## 8. Cache: leitura compartilhada e leitura por pessoa

| Regra | Como |
| --- | --- |
| Leitura compartilhada em arquivo próprio | Cada função declara o cache, as etiquetas e o prazo nas primeiras linhas e usa um cliente de banco sem sessão, com a chave pública e o papel `anon`. As políticas de `anon` já entregam só o publicado; a consulta filtra "publicado" mesmo assim |
| Etiquetas num módulo só | Molde: `assets/variante-web/etiquetas-de-cache.ts`, com as tabelas "quem lê" e "quem expira". Um segundo módulo, só de servidor, expira nas ações de escrita, e só quando a mudança afeta o que é público |
| Erro lança | Lista vazia devolvida num erro ficaria em cache e esconderia tudo até o prazo |
| O build consulta o banco | As leituras compartilhadas rodam ao pré-montar as páginas: o estágio de CI sem banco não faz build; o que sobe o banco migra antes do build; na hospedagem, banco migrado e variáveis presentes antes do primeiro build |
| A primeira visita depois da mudança pode vir antiga | A página pré-montada é entregue e refeita em segundo plano. O teste de ponta a ponta recarrega até o item aparecer, com prazo, e o dono fica sabendo |
| A separação tem teste | Um teste de fronteiras confere que arquivo com cache não importa leitura por pessoa, sessão nem a credencial de serviço |

## 9. Pagamento por assinatura: o SQL e o código

```sql
create table public.app_assinaturas (            -- espelho: uma linha por pessoa
  user_id uuid primary key references auth.users (id) on delete cascade,
  status public.app_status_assinatura not null   -- os valores do provedor de pagamento
);
create table public.app_eventos_de_pagamento (id text primary key);   -- cada notificação, uma vez
alter table public.app_assinaturas enable row level security;
alter table public.app_eventos_de_pagamento enable row level security;
create policy app_assinaturas_owner_select on public.app_assinaturas
  for select to authenticated using (user_id = (select auth.uid()));
revoke all privileges on public.app_assinaturas, public.app_eventos_de_pagamento
  from anon, authenticated;
grant select on public.app_assinaturas to authenticated;   -- só leitura: quem grava é o receptor
grant all on public.app_assinaturas, public.app_eventos_de_pagamento to service_role;
```

O receptor de notificação é o único ponto que escreve no espelho, com a credencial de serviço:

1. Confere a assinatura da mensagem com o segredo do provedor, antes de usar o conteúdo.
2. Procura o identificador do evento em `app_eventos_de_pagamento`. Se já está lá, responde
   sucesso e para.
3. Grava a situação nova no espelho, em inserção que atualiza em caso de conflito. Estado que o
   provedor não tem e o produto precisa (cobrança pausada) vira um valor próprio, que não dá acesso.
4. Grava o identificador do evento junto com o espelho, na mesma transação, ou por último. Esta
   ordem é adaptação, a conferir: gravado antes, uma falha no meio descarta a nova tentativa.

"Tem acesso pago?" é uma função de autorização (§3) sobre o espelho, com a mesma decisão em
função pura no aplicativo: em período de teste conta como acesso; cancelada e em atraso, não. No
teste do receptor, simule só o cliente do provedor: a conferência da assinatura é a de verdade,
com segredo de teste, e as escritas são afirmadas na ordem.

## 10. Ponta a ponta nesta stack

| Peça | Como |
| --- | --- |
| Sessões por persona, sem tela | Molde: `assets/variante-web/sessoes-de-teste.ts`. Um passo de preparo gera, para cada conta dos dados de exemplo, a credencial de uso único pela API de administração do login e a troca por sessão com a biblioteca de sessão do aplicativo. Sessão gravada vence e não sobrevive a recriar o banco: rode o preparo de novo |
| Teste de vazamento | Molde: `assets/variante-web/vazamento.spec.ts`. Peça o HTML e também o payload de dados que o framework envia junto, com o cabeçalho que ele usa para isso: o dado restrito pode estar no payload sem aparecer na tela |
| Guarda em três pontos | Na casca da área restrita, em cada página e em cada função de leitura: o framework não impede a página de renderizar por causa da casca. Logado sem papel recebe "não encontrado". O teste pede cada rota sem seguir redirecionamento (`references/fronteiras.md` §7) |
| Ambiente do executor | O executor de ponta a ponta não lê o arquivo de ambiente do framework: a configuração o carrega. Rode contra o build de produção, em outra porta |

## 11. As armadilhas, como lista de revisão

Passe a lista na revisão de toda mudança de banco, cache ou arquivos.

| Grupo | Confira |
| --- | --- |
| Privilégios e políticas | Objeto novo revogado antes de conceder e incluído no teste de privilégios; função nova com a execução revogada de `public` e de `anon` |
| | Nenhuma visão atualizável rodando com os direitos de quem a criou: é porta de escrita por baixo das políticas |
| | `update` e `delete` barrados por política provados pelo efeito; `insert` com retorno só onde há leitura |
| | Escrita que cita outro registro exige que ele seja visível; "todos leem tudo" revisto quando o conteúdo da tabela muda de natureza |
| | Guarda em cada página e em cada ação, não só na casca; `service_role` não usado como atalho |
| Migrações e ambiente | Valor de enumeração e uso em arquivos separados; migração de dado avisa quando não faz nada |
| | Nenhuma migração já aplicada no ambiente remoto foi editada. Depois de aplicar, o histórico remoto foi listado e comparado com os nomes dos arquivos: ferramenta que registra outra versão desalinha o histórico |
| | Artefato do banco gerado pelo mesmo comando, com os mesmos argumentos, na máquina e no CI |
| Cache | Erro não vira lista vazia em cache; nada restrito nem por pessoa em leitura compartilhada |
| | Banco migrado e variáveis presentes antes do build; escrita por fora do aplicativo prevista, porque não expira o cache |
| Dados de exemplo e testes | Datas relativas não colidem entre os dados de exemplo e os dos testes; métrica global isolada dentro da transação do teste |
| | As personas dos dados de exemplo cumprem os passos obrigatórios do aplicativo; marcador na primeira e na última linha |
| Arquivos | Nada em depósito público que não possa ser aberto por quem souber o endereço; tamanho e tipo vêm do depósito; referências contadas antes de apagar arquivo compartilhado |

## 12. Onde estão os moldes

Copie para o projeto, troque os nomes e rode antes de confiar.

| Molde | Para quê | Quando copiar |
| --- | --- | --- |
| `assets/variante-web/migracao-tabela-nova.sql` | tabela com restrições e comentários, políticas e o bloco de revogar antes de conceder | ao criar tabela |
| `assets/variante-web/funcao-com-guarda.sql` | função de autorização e função com privilégio | na primeira regra "só administrador"; em operação que atravessa as políticas |
| `assets/variante-web/teste-por-persona.sql` | teste dentro do banco: dados próprios, virar persona, efeito, prova final | junto da primeira política |
| `assets/variante-web/dados-de-exemplo-cabecalho.sql` | cabeçalho-índice com personas, faixas, estados e marcadores | ao criar os dados de exemplo |
| `assets/variante-web/banco-de-teste.sh` | banco de teste do zero, com o calço | quando o banco nasce; no projeto, vira o comando do degrau 3 em `[escada]` |
| `assets/variante-web/etiquetas-de-cache.ts` | módulo de etiquetas e as tabelas "quem lê" e "quem expira" | na primeira leitura compartilhada |
| `assets/variante-web/fronteiras.test.ts` | teste que lê o código-fonte com o analisador sintático | na primeira regra de imports, de primeira instrução ou de ordem |
| `assets/variante-web/vazamento.spec.ts` | marcadores na resposta crua, por persona | no primeiro dado restrito com página |
| `assets/variante-web/sessoes-de-teste.ts` | sessões por persona geradas sem tela, com trava de ambiente local | na primeira tela protegida |
| `assets/variante-web/cliente-falso.test.ts` | cliente encadeável que registra chamadas; guarda antes de tudo | na primeira ação de servidor |
| `assets/variante-web/trava-de-alvo.ts` | alvo em três degraus e escrita com simulação pelo mesmo caminho | na primeira ferramenta que escreve por fora do aplicativo |

## O que evitar

- **O visitante apaga linhas por uma visão.** A visão roda com os direitos de quem a criou e é
  atualizável: escreve por baixo das políticas. Revogue tudo dela, conceda só leitura e prove no
  teste que escrever por ela falha. Não serve conferir só as tabelas.
- **O teste passa no banco de teste e falha na plataforma.** Ela tem proteção que o calço não
  tem: uma trava dela pode barrar o comando antes da política. Rode nos dois e, no teste, siga o
  caminho oficial da plataforma. Não serve afrouxar o teste até os dois passarem.
- **Alguém "conserta" a função que recusa o papel de serviço.** A recusa é o desenho: sem
  identidade, a guarda nega. Use a sessão de um administrador. Não passe a identidade por
  argumento: quem chama escolheria quem é.

## Pronto quando

- [ ] Os seis nomes da §1 existem no banco do projeto, ou o calço foi criado e isso está escrito.
- [ ] Toda tabela, visão e função nova está no teste de privilégios.
- [ ] O banco de teste sobe do zero pelo script; os testes por persona passam nele e na plataforma.
- [ ] Cada molde copiado foi rodado no projeto antes de alguém confiar nele.

Volte ao `SKILL.md`, §4.
