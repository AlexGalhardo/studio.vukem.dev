# CI: o que roda a cada envio, e em que ordem?

Leia quando: fase de base (§1 e §2); nasce o banco; nasce a primeira tela protegida; o CI ficou
vermelho.
Não é aqui: o que cada degrau prova (`references/testes.md` §1).

## O mínimo

- O primeiro estágio são os degraus 0 a 2. Os outros dois nascem com o banco e com a primeira tela
  protegida: CI escrito inteiro no primeiro dia não tem o que verificar.
- O CI chama os mesmos comandos de `[escada]`, ou a cópia em `ferramentas/metodo/`. O caminho da
  skill não existe na máquina do CI.
- Nenhum segredo do repositório entra no CI.
- Artefato gerado e commitado é gerado de novo e comparado: diferença é falha.
- Vermelho se diagnostica, não se convive: vermelho "conhecido" ensina a ignorar o sinal.
- Enquanto o dono não criou a conta e o repositório remoto, vale o portão do commit no ambiente
  local, e o relato diz isso.

Conteúdo: 1. Três estágios 2. O CI cresce com as fases 3. Nenhum segredo do repositório
4. Artefato gerado conferido 5. Vermelho 6. Em outros serviços de CI

## 1. Três estágios e por que dividir

São três estágios independentes, em paralelo, a cada envio em qualquer ramo (branch) e a cada
pedido de merge. A skill não traz arquivo de CI, porque a sintaxe é de cada serviço: escreva o
arquivo com a documentação atual do serviço do projeto, a partir da tabela e dos passos abaixo.

| Estágio | Degraus | Precisa no ar | O que faz falhar | Nasce |
| --- | --- | --- | --- | --- |
| `rapido` | 0, 1 e 2 | nada | regra de estilo, tipo, teste de unidade ou de fronteiras | na fase de base |
| `dados` | 3, e a conferência do artefato gerado (§4) | um banco de teste na máquina do CI | migração que não aplica do zero, permissão diferente da matriz, artefato desatualizado | com o banco |
| `completo` | 3 de novo, 4 e 5 | o produto inteiro no ambiente do CI, com dados de exemplo | comportamento: fluxo por persona, vazamento, guarda, build | com a primeira tela protegida |

- **Retorno rápido.** `rapido` não espera banco nem navegador: erro de tipo aparece em minutos.
- **O vermelho diz onde olhar**, antes de alguém ler a saída: a coluna "O que faz falhar".
- **O build mora onde há banco.** Se ele consulta o banco para montar páginas, roda em `completo`;
  se não consulta, em `rapido`. O motivo fica num comentário no topo do estágio.
- **Os testes de banco rodam duas vezes de propósito**, se `dados` usa um banco comum no lugar do
  da plataforma: em `completo` eles rodam no ambiente real, e é ali que a diferença aparece.
- **Ponta a ponta contra o build de produção**, sem reaproveitar servidor que já esteja no ar.

Passos, na ordem, para escrever na sintaxe do serviço:

- **Em todo estágio:** baixar o código; linguagem na versão lida do arquivo de versão; dependências
  com o arquivo de trava congelado; limite de tempo (de partida, 15, 15 e 30 minutos).
- **`rapido`:** formato, só conferindo; lint; tipos; testes de unidade, com os de fronteiras.
- **`dados`:** pôr no ar o banco que a máquina do CI já traz, lendo a versão instalada; recriar o
  banco de teste com as migrações do zero, os dados de exemplo e os testes; conferir o artefato.
- **`completo`:** pôr no ar o produto inteiro, sem os serviços que ele não usa; ler endereço e
  chaves desse ambiente (§3); testes de banco; build de produção; ponta a ponta contra esse build;
  guardar o relatório só quando falha.

**De onde o CI chama.** Dos mesmos comandos de `[escada]`, copiados para o arquivo de CI: mudou um
comando em `metodo.ini`, mude o arquivo de CI na mesma mudança. Com a cópia dos scripts no
projeto, `rapido` chama a escada, e o comando mora num lugar só:

```bash
python3 ferramentas/metodo/escada.py --ate 2   # → uma linha por degrau; código de saída 0 se passou
```

O caminho da skill instalada não entra em arquivo de CI. Passo que chama script da skill pede antes
`montar.py --com-ferramentas` (a regra inteira está em `references/fronteiras.md` §3).

## 2. O CI cresce com as fases

| Momento | Entra no CI |
| --- | --- |
| Fase de base | `rapido`, com o build se ele não consulta o banco |
| Nasce o banco | `dados`, com a conferência do artefato gerado |
| Nasce a primeira tela protegida | `completo`; o build muda para cá se passou a consultar o banco |

Criar a conta no serviço e o repositório remoto são passos do dono: escreva-os em "Passos do
dono", em `docs/ESTADO.md`. Até lá o primeiro estágio é o portão do commit no ambiente local
(`SKILL.md` §4), e o relato diz "sem CI: os degraus 0 a 2 rodam só nesta máquina". Com a conta
criada, leia a primeira execução inteira: o primeiro vermelho costuma ser de configuração.

## 3. Nenhum segredo do repositório

- **`rapido`** roda com valores de mentira, definidos no preparo do executor de unidade
  (`references/testes.md` §8).
- **`completo`** usa as chaves do ambiente que o próprio CI põe no ar: leia-as do comando de
  estado desse ambiente, grave-as nas variáveis do estágio e falhe o passo se alguma vier vazia.
- **Serviço externo** (pagamento, envio de mensagem): os testes passam com e sem as chaves, e o CI
  roda sem elas. O teste afirma o aviso tratado em que o caminho termina.
- **Não coberto:** implantar pelo CI e testar contra o ambiente remoto. Se o projeto precisar, a
  credencial é cadastrada pelo dono no painel do serviço e não passa pela conversa.

## 4. Artefato gerado conferido

Vale para todo arquivo gerado por ferramenta e commitado: tipos do banco, cliente de API, esquema
da camada de dados, documentação de rotas. Escrito à mão, ou esquecido depois de uma migração, ele
faz o código compilar contra um banco que não existe mais.

1. No estágio `dados`, depois de recriar o banco de teste, gere o artefato para um arquivo
   temporário, pelo mesmo comando do projeto e com os mesmos argumentos.
2. Passe o resultado pelo mesmo formatador do arquivo commitado.
3. Compare com o arquivo commitado. Havendo diferença, falhe com a mensagem que diz o conserto:
   "<arquivo> desatualizado: rode <o comando que gera> e commite".

O arquivo gerado fica fora do lint e não se edita à mão. No ambiente local, ele é gerado de novo
na mesma mudança da migração, e o degrau 3 confere.

## 5. Vermelho

1. Leia a saída do estágio antes de rodar de novo: repetir esconde a causa.
2. Reproduza no ambiente local com o comando do mesmo degrau. Causa e conserto de teste instável
   estão em `references/testes.md` §9.
3. Não existe vermelho "conhecido": ou a causa é corrigida, ou vai ao dono em "Para decidir", com
   a saída.
4. Vermelho depois de um envio que implanta se diz ao dono na hora (`references/producao.md` §5).

## 6. Em outros serviços de CI

Os três estágios são os mesmos em qualquer serviço. Procure na documentação atual dele como dizer:

| Peça | O que o arquivo precisa dizer |
| --- | --- |
| Gatilho | todo envio, em qualquer ramo, e todo pedido de merge |
| Paralelismo | três estágios independentes: um vermelho não cancela os outros |
| Concorrência | execução nova do mesmo ramo cancela a anterior |
| Banco | o que a máquina do CI já traz, ou um banco efêmero por execução |
| Testes | proibido teste marcado como "só este"; novas tentativas como em `references/testes.md` §9 |

Sem banco relacional, `dados` vira a integração da camada de dados e a conferência do artefato.

## O que evitar

- **O build quebra no CI no dia em que a primeira página lê o banco.** Ele ficou no estágio sem
  banco. Mude o build para `completo` e escreva o motivo no topo do estágio.
- **O CI manda rodar um comando, e rodar o comando não acaba com a diferença.** O CI e a máquina
  geram o artefato por caminhos diferentes. Um comando só, com os mesmos argumentos, nos dois.
- **O estágio `dados` quebra quando o serviço troca a máquina do CI.** A versão do banco estava
  fixada, e a instalação puxou um segundo servidor. Leia a versão instalada e falhe com mensagem
  clara se não houver banco.
- **O vermelho "sempre foi assim".** Ninguém leu a saída, e a causa era um teste que dependia do
  dia. Diagnostique na hora: vermelho ignorado esconde o próximo.
- **Passa na máquina e quebra no CI.** A máquina tem o que o CI não tem: falta o preparo com
  valores de mentira, ou o executor de ponta a ponta não lê o arquivo de ambiente sozinho. Dê os
  valores no preparo e carregue o arquivo na configuração do executor.

## Pronto quando

- [ ] O arquivo de CI está na sintaxe do serviço do projeto, e a primeira execução foi lida.
- [ ] `rapido` roda os comandos dos degraus 0 a 2, ou a escada pela cópia em `ferramentas/metodo/`.
- [ ] Nenhum segredo do repositório é usado, e o passo que lê as chaves falha se vierem vazias.
- [ ] Havendo artefato gerado, o CI gera de novo pelo mesmo comando e compara.
- [ ] Sem conta ou repositório remoto: o passo está em "Passos do dono", e o relato diz isso.

Volte ao `SKILL.md`, §4.
