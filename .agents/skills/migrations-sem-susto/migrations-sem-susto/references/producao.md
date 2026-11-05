# Produção: em que ordem subir, o que simular antes e o que conferir depois?

Leia quando: a mudança está pronta e testada no ambiente local e vai a produção (passos 4 a 7 do
fluxo), ou antes de qualquer comando que toque o ambiente remoto, inclusive leitura.
Não é aqui: ensaiar a migration (`references/testes-e-volta.md`); o que fazer quando quebrou
(`references/testes-e-volta.md` §6).

## O mínimo

- Duas perguntas antes de montar a ordem (§1). A resposta de cada uma vem com a evidência.
- Banco, depois dados, depois código. Em remoção, código primeiro.
- O dono autoriza uma lista escrita. O agente não aplica nada por conta própria.
- Dados: simulação contra o destino, lida linha a linha, com o que pode sobrar escrito antes.
- Depois: consultar o banco, comparar o histórico com os arquivos e registrar o estado.

Conteúdo: 1. As duas perguntas 2. A ordem 3. Aplicar a migration 4. Antes de tocar em produção
5. Simular os dados 6. Conferir, alinhar e registrar

## 1. As duas perguntas

| Pergunta | Por que importa | Como responder |
| --- | --- | --- |
| O código NOVO funciona com o banco ANTIGO? | se não, o código não pode subir antes do banco | rode a montagem e os testes do código novo contra um banco sem a migration |
| O código ANTIGO funciona com o banco NOVO? | ele fica no ar entre o passo do banco e o do código, por minutos ou por dias | aplique a migration no ambiente local e use a versão que está em produção |

- **No sistema de origem a primeira resposta foi não.** A montagem das páginas consultava o
  banco e validava entradas contra os valores do enum: sem o valor novo, a implantação falhava.
  Por isso o banco foi primeiro.
- **A segunda tem de ser sim.** Lá era: migration que só acrescenta não aparece para o código
  antigo, que ignora o que não conhece. Se a resposta for não, a mudança não está pronta: divida
  em mais uma etapa (`references/expandir-e-usar.md`).
- **Escreva as duas respostas no roteiro** (`assets/moldes/roteiro-de-subida.md`), cada uma com o
  que foi rodado. "Deve funcionar" não é resposta.

## 2. A ordem

| Passo | O que sobe | Por que nesta posição |
| --- | --- | --- |
| 1. Banco | as migrations, uma por arquivo, na ordem | o código antigo não vê o que só foi acrescentado |
| 2. Dados | o que o código novo espera achar: vocabulário, vínculos, preenchimento | dado novo também não muda o sistema antigo |
| 3. Código | o envio que implanta | a montagem já acha a estrutura e os dados |

- **Código antes dos dados** (visto): as páginas foram montadas sem os dados e ficaram
  incompletas até a cópia em cache expirar, cerca de 1 hora. Carga feita por fora do aplicativo
  não avisa o cache.
- **Quando inverte:** remover pede código primeiro e banco depois (`references/expandir-e-usar.md`
  §5). A conferir: o sistema de origem só acrescentou.
- **Entre um passo e outro o sistema fica no ar.** Se a subida parar depois do passo 1 ou do 2,
  nada quebra: é esse o teste da lista.

## 3. Aplicar a migration no ambiente remoto

1. Liste o histórico de migrations do ambiente e compare com os nomes dos arquivos. Use um
   comando que não tem como escrever: listar, e não "aplicar o que falta".
2. Aplique uma por arquivo, na ordem, pelo canal de migrations da ferramenta. Ele grava versão e
   nome no histórico; SQL colado num console, não.
3. Depois de cada uma, confira (§6) antes de seguir para a próxima.
4. Falhou no meio: pare. Não aplique a seguinte, não edite o arquivo. Leia o erro e o estado do
   banco, e leve ao dono (`references/testes-e-volta.md` §6).

- **O aviso da migration pode não chegar** (visto): aplicada por uma ferramenta que não era a de
  linha de comando, `raise warning` não apareceu. Rode a consulta que responde o que o aviso diria.
- **Diga antes o que não tem volta.** Valor de enum não sai; dado preenchido não se distingue
  depois. Isso vai na lista que o dono lê.

## 4. Antes de tocar em produção

| Portão | Passa quando |
| --- | --- |
| Ambiente local primeiro | a mudança roda e foi validada pelo dono fora de produção |
| Do zero e sobre dados | as migrations aplicam num banco recriado e num banco com linhas |
| Conferidor | `conferir.py <migrations> --base <ref de produção>` sai com 0 |
| Estado relido | o que está aplicado em produção foi lido do arquivo no disco, agora |
| Envio seguro | no ramo que implanta sozinho, enviar é implantar: o código só é enviado no passo 3 |
| Pedido do dono | ele leu a lista inteira e pediu. O sim vale para aquela lista |

## 5. Simular os dados antes de escrever

1. Escreva antes de rodar: "só pode sobrar: `<as linhas esperadas>`" e "pare se aparecer:
   `<linha>`". No caso visto, uma carga feita só para etiquetar itens publicados: só podiam
   sobrar "criar a etiqueta" e "pôr N etiquetas no item"; "subir arquivo" ou "atualizar a mídia"
   era a linha de parar, porque trocaria arquivos que já estavam no ar.
2. Rode a simulação contra o próprio ambiente de destino, pelo mesmo caminho de código da
   escrita. Simulação que percorre outro caminho não diz o que a escrita fará.
3. Leia a saída linha a linha. Uma forma que se lê bem: `=` já está igual, `dry` escreveria,
   `ok` escreveu.
4. Sobrou só o previsto: rode a escrita e confira o resumo, com o alvo e a contagem. Sobrou
   outra coisa: pare, não escreva e mostre a linha ao dono.

- **Sem ferramenta com simulação** (a conferir): rode o script de dados numa transação que
  termina em `rollback`, com as contagens antes e depois impressas.
- **Migration de estrutura** raramente tem simulação que valha. O relato diz então o que foi
  conferido no lugar: "aplicada do zero e sobre dados no local; histórico remoto igual aos
  arquivos até `<a última>`".

## 6. Conferir, alinhar e registrar

Consultas de conferência, em Postgres, para rodar depois de cada migration:

```sql
select to_regclass('public.items');                                -- o objeto existe (não nulo)
select enum_range(null::public.item_kind);                         -- o valor novo está na lista
select prosecdef, proconfig, proacl from pg_proc                   -- t | {search_path=""} | quem executa
  where oid = 'public.publish_item(uuid)'::regprocedure;
select grantee, privilege_type from information_schema.role_table_grants
  where table_schema = 'public' and table_name = 'items';          -- só os papéis previstos
select policyname, cmd, roles, qual from pg_policies where tablename = 'items';
```

- **Histórico:** liste de novo e compare versão por versão com os nomes dos arquivos. Visto: duas
  migrations aplicadas por outro canal ficaram com a hora da aplicação no lugar da versão do
  arquivo, e um "aplique o que falta" futuro tentaria reaplicar as duas.
- **Divergiu: não acerte por conta própria.** É uma escrita em produção, na tabela de controle
  da ferramenta. Anote a divergência no estado, com "antes do próximo envio em lote: alinhar", e
  leve ao dono o comando exato de reparo da ferramenta (o nome varia: a conferir na sua).
- **Como visitante,** sem sessão, no endereço que o dono usa, conte o que deveria estar lá. Cada
  endereço guarda a própria cópia em cache: um pode mostrar o novo enquanto o outro mostra o antigo.
- **Registre o estado** no arquivo que toda sessão lê, uma linha por ambiente:

  ```text
  Produção: migrations aplicadas até <versão>, em <AAAA-MM-DD>, a pedido de <quem>.
  Ainda não aplicadas: <versões>. O código que depende delas só sobe depois, na ordem.
  Divergência conhecida: <qual>, a alinhar antes de <quê>.
  Aplicar migration em produção: só quando o dono pedir.
  ```

- **Um lugar só.** O mesmo estado copiado em quatro documentos envelheceu em ritmos diferentes
  (visto). Escolha um e faça os outros apontarem para ele.

## O que evitar

- **"Aplicar o que falta" sem listar antes.** Com o histórico divergente, reaplica o que já está.
- **Enviar o código "para adiantar".** No ramo que implanta, o envio é a subida.
- **Ler a simulação pelo resumo.** A linha que troca o que está no ar está no meio.
- **Dizer "aplicado" sem ter consultado.** O relato separa o que rodou do que foi inferido.
