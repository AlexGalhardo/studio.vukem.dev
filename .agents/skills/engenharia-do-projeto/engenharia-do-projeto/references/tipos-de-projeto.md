# Tipos de projeto: o que muda quando o projeto não é aplicação web com banco?

Leia quando: passo 3 da ordem do zero, se o projeto é biblioteca, CLI, API sem interface,
aplicativo móvel, dados e automações ou site estático.
Não é aqui: aplicação web com PostgreSQL (`references/variante-web.md`).
**Base:** adaptação. O método foi praticado numa aplicação web com banco relacional; o que está
aqui ainda não foi praticado. Confira antes de confiar.

## O mínimo

- Mantenha o que não muda: uma casa por fato, "Pronto quando", a escada, o relato, as três caixas.
- Decida o que muda: o que é "produção", o que é dado restrito e por onde ele vaza, quais degraus
  existem. Escreva as três respostas na especificação antes de escolher a stack.
- Não copie comando desta ficha: ela não traz nenhum. Descubra os comandos pelos manifestos e pela
  documentação da versão instalada, rode cada um uma vez e só então grave em `metodo.ini`.
- Degrau que o tipo não tem leva `n/a: <motivo>`; o que só ainda não existe fica vazio e é dito.

Conteúdo: 1. O que não muda 2. O que muda, por tipo 3. Comandos da escada 4. Zonas 5. Decisões

## 1. O que não muda em tipo nenhum

| No método | Sem interface ou sem banco, fica assim |
| --- | --- |
| Referências da especificação | Exemplos de entrada e saída: requisição e resposta, arquivo de exemplo, saída esperada do comando |
| Matriz de permissões | Vale onde há mais de um papel: em API, "quem pode chamar o quê". Em produto de uma pessoa só, some |
| Fases | A mesma lógica, em outra ordem. Biblioteca e CLI: base, núcleo puro, interface, empacotamento, publicação. Aplicativo móvel: base, dados e sincronização, telas, conta e compras, lojas |
| "Pronto quando" | O mesmo critério observável, pelo que a stack tem: saída do comando, consulta ao banco, captura de tela, teste de contrato |
| Onde detalhar | No que é persistente, no que cruza fronteira de confiança e no que tem número |
| "Pergunte antes" | A lista ganha o que é sem volta no tipo: publicar pacote, mudar o que vai para a loja, criar recurso que gera custo, mexer em fila ou depósito de produção |
| Ambientes | O padrão aponta para o lugar seguro, e o perigoso tem de ser chamado pelo nome |
| Ferramenta que escreve em produção | Lê o alvo, compara com uma lista de um e exige opção explícita para sair do ambiente local; a simulação percorre o mesmo caminho |

## 2. O que muda, por tipo

| Tipo | O que é "produção" | Dado restrito e por onde vaza | Degraus que existem | Só o dono faz |
| --- | --- | --- | --- | --- |
| Biblioteca e CLI | A versão publicada, que outras pessoas instalam. Publicar o pacote é ir a produção | Credencial e arquivo de quem usa a ferramenta; vaza por mensagem de erro, saída gravada e arquivo que entra no pacote sem querer | 0 a 2; 3 só se há banco; 4 é empacotar; 5 é instalar o pacote construído e rodar o comando de fora | Conta no repositório de pacotes e credencial de publicação |
| API sem interface | O serviço no ar e o contrato que outros sistemas já usam | Dado de outra pessoa ou de outro cliente; vaza no corpo da resposta de cada rota, também nas de erro e de listagem | 0 a 5; o 5 chama a API de fora, por persona | Contas de hospedagem e credenciais entregues a quem consome |
| Aplicativo móvel | A versão na loja e o servidor que ela chama | O mesmo da API que o aplicativo consome, mais o que fica guardado no aparelho, como a sessão | 0 a 2; 3 no servidor; 4 é o pacote do aplicativo; 5 em emulador ou aparelho | Conta da loja, credenciais de assinatura do pacote, envio para a revisão da loja |
| Dados e automações | A execução agendada sobre os dados de verdade e os destinos onde ela grava | Dado pessoal das fontes; vaza por arquivo de saída, saída gravada e destino mais aberto que a fonte | 0 a 2; 3 se há base própria; 4 costuma ser `n/a`; 5 é a execução inteira sobre uma amostra, com simulação | Credenciais das fontes e dos destinos; a agenda, quando mora num painel |
| Site estático | O site publicado no endereço do dono | Rascunho e página ainda não publicada; segredo embutido no que é gerado | 0; 1 a 3 costumam ser `n/a`; 4 gera o site; 5 abre as páginas geradas e confere os endereços | Domínio, conta do provedor e o que depende de plano pago |

Infraestrutura como código, **sem prática** neste método, em três linhas:
- "Produção" é a conta onde os recursos existem; a conta e a cobrança dela são do dono.
- "Pergunte antes" inclui todo recurso que gera custo.
- A conferência prévia é o plano que a ferramenta imprime, lido linha a linha antes de aplicar.

## 3. Descobrir os comandos da escada

Cada degrau é ocupado por um tipo de ferramenta. Ache o comando no manifesto do projeto, confirme
na documentação da versão instalada, rode uma vez e leia a saída; só então grave em `[escada]` (o
passo a passo está em `references/testes.md` §8). Os nomes da tabela são exemplos, **a conferir**.

| Degrau | Tipo de ferramenta que o ocupa | Exemplo, a conferir |
| --- | --- | --- |
| 0 · formato e lint | formatador e analisador de estilo da linguagem | |
| 1 · tipos | compilador, ou anotações de tipo com analisador estático | |
| 2 · unidade e fronteiras | executor de testes de unidade; teste que varre os imports | pytest, `go test`, JUnit, RSpec; módulo `ast` do Python |
| 3 · banco | ferramenta de migração e teste de integração da camada de autorização, contra um banco de verdade recriado | Alembic; as migrações do Django e do Rails |
| 4 · build | o que monta o artefato que vai a produção; gerador de artefato a partir do banco ou do contrato | sqlc |
| 5 · ponta a ponta | o produto montado, exercitado de fora, por persona | |

## 4. Zonas

Um exemplo de padrão de caminho por zona: troque pelos caminhos reais (como preencher `[zonas]`
está em `references/pesos.md` §2). Zona que o tipo não tem se apaga, com o motivo em comentário:
biblioteca sem cobrança, site estático sem acesso.

| Zona | Exemplo de padrão | O que costuma morar ali |
| --- | --- | --- |
| `dados` | `migracoes/**`, `esquema.*` | esquema, migrações, dados de exemplo |
| `acesso` | `**/permissoes.*`, `autenticacao/**` | login, sessão, guarda, regra de quem pode |
| `segredos` | `config/segredos.*` | o módulo que lê os segredos, não o arquivo de ambiente |
| `restrito` | `**/exportar.*`, `relatorios/**` | o que lê, mostra ou exporta dado restrito |
| `cache` | `**/cache/**` | leitura guardada para mais de uma pessoa |
| `cobranca` | `pagamentos/**` | preço, plano, estado de pagamento |

## 5. Decisões que costumam pedir registro

| Tipo | Decisões |
| --- | --- |
| Biblioteca e CLI | O que é interface pública e o que pode mudar sem aviso; versões da linguagem atendidas; formato da saída que outros programas leem. Sem fonte na prática: a conferir |
| API sem interface | Versionamento da API, formato de erro, autenticação entre serviços, idempotência, limites |
| Aplicativo móvel | Versão mínima do sistema, biblioteca de navegação, onde guardar a sessão, o que roda sem conexão, permissões pedidas e quando |
| Dados e automações | Fonte de verdade de cada dado, o que é reprocessável, o que é destrutivo, agenda e o que acontece na falha |
| Site estático | Onde mora o conteúdo, quem publica, o que depende de plano pago do provedor, o que não dá para exportar |

## O que evitar

- **Comando da escada lembrado de cabeça ou copiado de outro projeto.** Sintaxe de uma ferramenta
  usada em outra falha, ou passa sem testar nada. Rode uma vez e leia a saída antes de gravar.
- **O teste de vazamento olha a tela.** Em API e em aplicativo móvel o dado vaza na resposta que o
  cliente recebe: procure o marcador no corpo de cada resposta (`references/fronteiras.md` §8).
- **A ferramenta que escreve em produção aceita qualquer alvo parecido.** Lista de permitidos por
  padrão largo deixa passar o projeto errado. Compare com o endereço inteiro.

## Pronto quando

- [ ] A especificação diz o que é "produção", o dado restrito, por onde vaza e o que só o dono faz.
- [ ] Cada degrau de `[escada]` tem comando rodado uma vez ou `n/a: <motivo>`, ou está vazio e dito.
- [ ] `[zonas]` tem os caminhos reais, e a zona que o projeto não tem foi apagada com o motivo.

Volte ao `SKILL.md`, §3.
