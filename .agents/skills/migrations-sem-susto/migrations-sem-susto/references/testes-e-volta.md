# Testes e volta: como ensaiar a migration, e o que dá para desfazer depois?

Leia quando: for verificar uma migration antes de subir (passo 3 do fluxo), montar o teste de
banco ou o passo do CI, ou quando algo quebrou depois de aplicar.
Não é aqui: a ordem da subida e a conferência em produção (`references/producao.md`).

## O mínimo

- Verificar uma migration é recriar o banco inteiro: todas em ordem, dados de exemplo, testes.
- O banco de teste tem nome próprio e é descartável. O de desenvolvimento tem dono.
- Cada teste de banco roda numa transação que termina desfeita.
- O que é gerado do banco (tipos, cliente) é gerado de novo e conferido no CI.
- Do zero não basta: ensaie também sobre um banco que já tem linhas.
- O conserto de uma migration aplicada é outra migration, para a frente.

Conteúdo: 1. Banco do zero 2. Testes em transação desfeita 3. Tipos gerados no CI 4. Datas
relativas 5. Sobre dados 6. Voltar atrás

## 1. Banco do zero a cada verificação (visto)

1. Derrube as conexões, apague e recrie um banco de teste. O script só aceita servidor local e
   nome com sufixo de teste: ele apaga o banco que recebe.
2. Aplique o mínimo que a plataforma traz pronto e as migrations supõem (papéis, esquemas).
3. Aplique as migrations em ordem fixa pelo nome, cada arquivo numa transação, parando no
   primeiro erro. Zero arquivos encontrados é falha, não verde.
4. Aplique os dados de exemplo e rode os testes.

- **Por quê do zero.** Aplicar por cima do banco de ontem esconde dependência de ordem e de
  estado: passa na máquina de quem escreveu e falha em todas as outras.
- **Em qualquer lugar.** No sistema de origem o comando oficial pedia contêiner, e um script de
  124 linhas fazia o mesmo num Postgres comum. O CI rodava os dois: é no ambiente real que
  aparecem as diferenças da imitação (uma proteção da plataforma barrou um comando que o banco
  comum aceitava).
- **A versão do banco no CI** é a instalada no executor, lida na hora. Fixada, quebra quando a
  imagem muda.

## 2. Testes de banco em transação desfeita (visto)

```sql
begin;
select plan(3);                                    -- quantas afirmações o arquivo tem
-- os dados do teste, criados aqui dentro
-- as afirmações: a função recusa, o papel não lê, a regra barra
select * from finish();
rollback;                                          -- nada sobra para o teste seguinte
```

- **Cada arquivo cria os dados de que precisa** e roda sozinho, em qualquer ordem.
- **Declare quantas afirmações há.** Afirmação que não rodou também é falha.
- **Teste com o papel do aplicativo,** não com o administrador do banco: ele passa por cima das
  permissões, e tudo dá verde.
- **O que testar de uma migration:** o privilégio de cada papel na tabela nova; a função
  redefinida recusando o que deve; a regra nova barrando a linha errada e aceitando a certa.
- O exemplo usa pgTAP. Em outra ferramenta, o que vale é a transação desfeita e a contagem.

## 3. Tipos gerados, conferidos no CI (visto)

1. Um comando do projeto gera os tipos ou o cliente a partir do banco com as migrations aplicadas.
2. O arquivo gerado é commitado na mesma mudança da migration.
3. O CI aplica as migrations num banco limpo, gera de novo, compara com o commitado e falha com
   a instrução do que rodar.

- **O CI e a pessoa geram pelo mesmo comando, com os mesmos argumentos.** Visto: dois caminhos de
  geração davam saídas diferentes, e a mensagem de erro do CI mandava rodar justamente o comando
  que causava a diferença.
- **Para que serve:** renomear ou remover no banco quebra a compilação nos pontos certos, e
  responde a pergunta "o código novo funciona com este banco?" sem subir nada.

## 4. A armadilha das datas relativas (visto)

Os dados de exemplo usavam datas relativas a hoje ("ontem", "daqui a 7 dias") numa coluna única, e
os testes criavam linhas com datas relativas na mesma coluna. Aplicados no mesmo dia, não
colidiam. Com os dados de exemplo aplicados num dia e o teste rodando em outro, os dois caíam na
mesma data, e o teste quebrava. Na virada do dia quebrava sozinho: um CI vermelho foi ignorado
por isso.

| Regra | Porque |
| --- | --- |
| O teste roda sempre sobre banco recriado na mesma execução | dados de exemplo de ontem já têm outras datas |
| Os dados de exemplo listam, no cabeçalho, os deslocamentos que os testes usam, e não os repetem | "hoje −3" dos dois lados colide em coluna única |
| Nenhuma afirmação depende de "hoje" | o teste que roda às 23h59 termina no dia seguinte |
| Fuso fixo na configuração do teste | "hoje" do banco e "hoje" do executor podem diferir |

Rodar de novo até passar esconde o defeito: o teste falha um dia sim, outro não.

## 5. Sobre dados (medido; o sistema de origem não tinha este passo)

O banco do zero recebe os dados de exemplo depois de todas as migrations. A migration nova nunca
encontra linha antiga, e produção só tem linha antiga.

1. Recrie o banco aplicando as migrations até a última que está em produção.
2. Carregue dados de exemplo, de preferência com os casos feios: nulo, texto vazio, valor repetido.
3. Aplique as migrations novas.

Medido: `set not null` passou na tabela vazia e falhou com 3 linhas, "contains null values".
Restrição nova, índice único e conversão de tipo falham do mesmo jeito. Cópia de produção para
ensaio é decisão do dono, por causa dos dados pessoais.

## 6. Voltar atrás

| Mudança aplicada | Dá para desfazer? | Como |
| --- | --- | --- |
| Tabela, coluna ou índice novos | sim, com perda do que foi gravado ali | migration nova, depois de o código parar de usar |
| Valor de enum | não (medido: "dropping an enum value is not implemented") | fica sem uso; recriar o tipo reescreve as colunas |
| Função, política ou visão redefinida | sim | migration nova com a definição anterior inteira |
| `not null`, `check`, chave estrangeira | sim | migration nova que remove a restrição |
| Dado preenchido ou convertido | só se o valor antigo foi guardado | sem ele, cópia de segurança |
| Coluna, tabela ou linha removida | a estrutura volta; o dado, não | cópia de segurança, com o dono |

- **Por quê para a frente.** Outros ambientes já aplicaram; o código implantado já depende; e o
  roteiro de desfazer roda sobre dados que mudaram desde a aplicação. Editar o arquivo aplicado
  não muda banco nenhum.
- **Se só acrescentou, voltar o código basta.** O código antigo funciona com o banco novo: foi a
  segunda pergunta de `references/producao.md` §1. É para isso que serve só acrescentar.
- **Quebrou depois de aplicar:** pare a lista; diga ao dono o que está no ar e o que foi
  aplicado; descubra qual das duas perguntas falhou; proponha o conserto mais curto, que quase
  sempre reabre o que fechou (tira a restrição, recria a coluna opcional). Reproduza no local
  antes de propor.
- **Migration de desfazer exigida pela ferramenta** (a conferir): escreva e ensaie no banco
  descartável, aplicando, desfazendo e aplicando de novo. Em produção, só com o dono.
- **Cópia de segurança e restauração** ficam fora desta skill. Antes de mudança sem volta,
  pergunte ao dono se há cópia recente e quem a restaura.

## O que evitar

- **Testar a migration só no banco de desenvolvimento.** Ele tem meses de estado que produção
  não tem.
- **Verde com zero arquivos.** Pasta errada, nenhuma migration aplicada, tudo "passa".
- **"Desfaço se der errado"** como plano de uma mudança que remove dado.
