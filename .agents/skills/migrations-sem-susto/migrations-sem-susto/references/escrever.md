# Escrever a migration: o que vai no arquivo e o que nunca se edita?

Leia quando: for criar ou revisar um arquivo de migration, redefinir função, política ou visão, ou
pôr dado dentro de migration (passo 2 do fluxo).
Não é aqui: em quantas etapas a mudança se divide (`references/expandir-e-usar.md`); aplicar no
ambiente remoto (`references/producao.md`).

## O mínimo

- Um arquivo por mudança, criado pela ferramenta do projeto, que põe a versão no nome.
- O arquivo abre com um cabeçalho de seis respostas (§2). Quem vai ler é uma sessão sem memória.
- Só acrescenta. Estrutura que guarda dado não é alterada nem apagada sem o dono.
- Saiu da máquina, não se edita: a correção é outro arquivo.
- Função redefinida leva a definição inteira, com as proteções repetidas.

Conteúdo: 1. Um arquivo por mudança 2. O cabeçalho 3. Editar ou escrever outra 4. Redefinir função,
política e visão 5. Dado dentro de migration 6. SQL gerado por ferramenta

## 1. Um arquivo por mudança

| Cabe numa migration comum | Pede etapas, ou o dono |
| --- | --- |
| Tabela, índice, tipo e função novos | Coluna obrigatória em tabela com linhas |
| Coluna nova opcional, ou com valor padrão | Renomear, trocar tipo, remover |
| Valor novo de enum, sozinho no arquivo | Qualquer `drop`, `truncate` ou `delete` sem `where` |
| Trocar uma regra: função, política, restrição que afrouxa | Restrição nova que linha antiga pode não cumprir |

- **Como dividir.** Uma funcionalidade, um arquivo: a tabela nova com os índices, os privilégios
  e as políticas dela. Troca de regra vai sozinha: um arquivo só para a função, outro só para a
  política. No sistema de origem foram 11 arquivos: 4 na primeira leva, por assunto, e depois um
  por funcionalidade, o menor com 11 linhas.
- **O nome** é `<versão>_<assunto>.sql`, e a versão vem da ferramenta. Versão escrita à mão repete
  ou sai de ordem quando duas pessoas trabalham ao mesmo tempo.
- **Privilégios na mesma migration que cria.** O objeto nasce com os privilégios de fábrica da
  plataforma. Em Postgres, função nasce com `execute` para todos: revogue e conceda o mínimo ali.
- **Comentário no objeto** (`comment on`), com o propósito em uma frase: fica no banco, para
  quem só tem o banco para ler.
- **Nada preso a uma versão do banco** quando teste e produção rodam versões diferentes. No
  sistema de origem rodavam, de propósito.

## 2. O cabeçalho

Seis respostas, em comentário, no topo do arquivo. O molde é
`assets/moldes/01-migration-com-cabecalho.sql`.

| Resposta | Exemplo |
| --- | --- |
| O que faz, em uma frase | "Cria items.source, opcional." |
| Por quê | a funcionalidade ou a decisão, com o número do registro de decisão |
| O que fica de fora, de propósito | "A obrigatoriedade vem depois do preenchimento, em outra migration." |
| O que substitui | "Igual à função da 20250301120000, mudando só a linha do formato." Ou "nada" |
| Roda de novo sem erro? | "Sim: if not exists." Ou "Não: é aplicada uma vez" |
| O que não tem volta | "Valor de enum não sai." Ou "Remover pede migration nova" |

Migration não precisa rodar duas vezes. As que rodam (dado de produção, valor de enum com `if not
exists`) dizem isso no cabeçalho, porque é isso que permite reaplicar depois de uma falha.

## 3. Editar ou escrever outra

| Onde o arquivo já foi aplicado | O que fazer |
| --- | --- |
| Só nesta máquina | Pode editar. Recrie o banco do zero e diga no relato que foi esse o caso |
| No ramo compartilhado ou no banco de outra pessoa | Migration nova |
| Em qualquer ambiente remoto | Migration nova, sempre |

- **Por quê.** A ferramenta guarda no banco a versão de cada arquivo aplicado e não aplica de
  novo. Editado depois, o arquivo diz uma coisa e o banco tem outra, com o mesmo histórico.
  Ferramenta que guarda a soma do conteúdo recusa a próxima execução (a conferir na sua).
- **A regra leva a condição escrita.** No sistema de origem, dois arquivos foram editados no
  lugar, antes de irem ao remoto, e o registro de decisão diz isso com essas palavras. Sem a
  condição, a exceção vira hábito.
- **O conferidor acusa** arquivo que mudou depois do commit em que entrou. Com `--base <ref>`,
  só o que existe em `<ref>` conta como aplicado.

## 4. Redefinir função, política e visão

Medido em Postgres 17.11, numa transação desfeita:

| Depois de `create or replace function` | O que acontece |
| --- | --- |
| Dono | fica |
| Privilégios (quem tem `execute`) | ficam |
| `security definer` | some se não for repetido: a função passa a rodar com o privilégio de quem chama |
| `set search_path` | some se não for repetido: vale o caminho de busca da sessão |
| Volatilidade (`stable`, `immutable`) | volta para `volatile` se não for repetida |
| Tipo de argumento diferente | nasce uma segunda função, sem proteção e com `execute` para todos; a antiga fica |
| Tipo de retorno diferente | erro: "cannot change return type of existing function" |
| `drop function` e `create function` | função nova, com os privilégios de fábrica: os `grant` e `revoke` antigos se perdem |

1. Copie a definição em vigor inteira: da última migration que a define, ou do banco
   (`select pg_get_functiondef('public.publish_item(uuid)'::regprocedure)`).
2. Mude só o que precisa mudar, e marque o trecho.
3. Repita tudo o que vem antes e depois do corpo: linguagem, `security definer`, `set search_path`,
   volatilidade. O molde é `assets/moldes/05-redefinir-funcao.sql`.
4. Diga no cabeçalho de qual versão ela é cópia e o que mudou.
5. Depois de aplicar, consulte as proteções em cada ambiente (`references/producao.md` §6).

- **Política:** `drop policy` e `create policy` na mesma migration, com a regra inteira. Na mesma
  transação, as outras sessões veem a regra antiga ou a nova, nunca a tabela sem regra (a troca
  foi medida; a concorrência, não). O cabeçalho diz o que havia, o que passa a valer e o que não
  muda.
- **Visão:** `create or replace view` também perde as opções se não repetir (medido com
  `security_invoker`) e, pela documentação, só aceita coluna nova no fim.
- **O conferidor acusa** função redefinida sem `security definer` ou sem `set search_path` quando
  a definição anterior tinha. Ele não vê volatilidade nem visão.

## 5. Dado dentro de migration

| Dado | Onde vai |
| --- | --- |
| O que o produto precisa para funcionar: vocabulário fixo, configuração inicial | migration própria |
| Exemplo para desenvolver e testar | arquivo de dados de exemplo, que nunca vai ao remoto |
| O que depende de quem ainda não existe, como o primeiro administrador | passo à parte, anotado no estado |
| Vocabulário que as pessoas criam pelo sistema | nasce pelo sistema, não por migration |

- **Roda de novo sem duplicar:** "se já existe, atualiza" (`on conflict ... do update`).
- **Avisa quando não pôde fazer o que devia.** A primeira versão vista inseria o administrador
  pelo e-mail e, quando a conta não existia, não fazia nada e não dizia nada: o produto iria ao
  ar sem administrador. Virou um aviso (`raise warning`) com o que fazer em cada ambiente.
- **O aviso pode não aparecer** no canal usado para aplicar. Tenha a consulta que responde o
  mesmo.

## 6. SQL gerado por ferramenta

Quando a ferramenta gera a migration a partir de um modelo no código, a regra vira: leia o SQL
gerado antes de commitar, e nunca gere de novo uma migration já aplicada. Confira três coisas no
que saiu: renomear não virou `drop` e `add` (a conferir na sua ferramenta), coluna obrigatória tem
o caminho de três passos, e nada destrutivo entrou sem pedido.

## O que evitar

- **"É só um ajuste", direto no arquivo já aplicado.** O banco de produção não recebe o ajuste, e
  o banco recriado do zero passa a ser outro.
- **Um arquivo com três assuntos.** Um erro no terceiro desfaz os dois primeiros, ou deixa pela
  metade onde o banco não desfaz estrutura.
- **Redefinir a função colando só o corpo novo.** As proteções moram fora do corpo.
- **Mudar pelo painel do banco e escrever a migration depois.** O arquivo vira uma descrição de
  memória, e produção fica diferente de todo banco recriado.
