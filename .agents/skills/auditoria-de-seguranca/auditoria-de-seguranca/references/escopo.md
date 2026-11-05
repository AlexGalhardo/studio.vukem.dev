# Escopo: o que pode ser auditado, por quem e até onde?

Leia quando: antes de abrir qualquer arquivo do projeto (passo 1 do fluxo) e sempre que o pedido
mudar de alvo no meio da conversa.
Não é aqui: como fazer cada prova sem causar dano (`references/comprovacao.md`).

## O mínimo

- Sem termo de escopo confirmado pelo dono, não há leitura nem teste.
- O alvo é o sistema de quem pede. Site, API ou conta de terceiros: recuse.
- Comprovação em local ou homologação, com usuários de teste. Produção só entra com pedido
  explícito do dono, escrito no termo, e só para leitura não destrutiva.
- Nunca: força bruta, negação de serviço, teste de carga, varredura agressiva, comando destrutivo.
- O que ficou de fora vai escrito no relatório, em "o que não foi testado".

Conteúdo: 1. As perguntas do termo 2. O sistema é de quem pede? 3. O que cada ambiente permite
4. O que recusar, e o que oferecer 5. Serviços de terceiros dentro do sistema 6. Segredo e dado
real no caminho 7. Quando parar 8. O que evitar 9. Checklist

## 1. As perguntas do termo

Pergunte tudo de uma vez, cada pergunta já com o padrão. O dono confirma ou corrige.

| Pergunta | Padrão |
| --- | --- |
| Qual sistema, e em qual pasta ou repositório? | o projeto aberto nesta sessão |
| Quem é o dono, e quem está pedindo? | quem está na conversa; se pede por outra pessoa, ela confirma |
| O que entra? | código, configuração, migrações do banco e o ambiente local |
| Há homologação? Qual endereço, e quais usuários de teste? | não há: comprovação só no local |
| Produção entra? | não |
| O que fica de fora? | fornecedores, contas pessoais, rede e máquinas da equipe |
| Posso rodar a auditoria de dependências? Ela acessa a rede. | não rodar |
| Há dado com regra própria (saúde, pagamento, menor de idade)? | sem padrão: pergunte sempre |
| Onde fica o relatório? | pasta fora do repositório |

O modelo é `assets/modelos/termo-de-escopo.md`. Registre a resposta do dono com a data: ela vai
para o campo `confirmacao_de_escopo` do arquivo de achados e aparece na capa do relatório.

## 2. O sistema é de quem pede?

Uma conversa não dá prova absoluta. Dá sinais, e há o que não serve de sinal.

| Serve de sinal | Por quê |
| --- | --- |
| o código-fonte completo está na máquina, com histórico de commits | quem só quer atacar um site não tem o repositório dele |
| o ambiente local sobe com o banco e os dados de exemplo do projeto | exige as credenciais de desenvolvimento |
| a pessoa cria usuários de teste e muda configuração | é acesso de quem mantém o sistema |

| Não serve | Por quê |
| --- | --- |
| "tenho autorização", sem código nem ambiente | não dá para conferir |
| só um endereço público | qualquer pessoa tem o endereço |
| pressa ("preciso para hoje") | pressa não muda de quem é o sistema |

Trabalho feito para um cliente: o dono é o cliente. Peça a frase dele no termo ("autorizo a
auditoria do sistema X no ambiente Y") e audite só o ambiente citado. Na dúvida, fique na leitura
do código que está na máquina e não faça requisição a endereço nenhum.

## 3. O que cada ambiente permite

| Ambiente | Leitura | Requisição de prova | Escrita |
| --- | --- | --- | --- |
| Local | tudo | sim, com usuários de teste | só dado de teste; recrie o banco ao terminar |
| Homologação do dono | tudo | sim, com usuários criados para a auditoria | só dado de teste, e apague ao terminar |
| Produção | o que está no repositório | só com pedido explícito, e só leitura não destrutiva | nunca |

Leitura não destrutiva em produção, quando o dono pede: os cabeçalhos de resposta de uma página
pública; se o mapa de código-fonte de um arquivo público existe; os atributos do cookie de uma
sessão que o próprio dono abriu. Uma requisição por conferência, no ritmo de uma pessoa. O que
prova acesso a dado de outro usuário se prova no local, nunca com conta de gente de verdade.

## 4. O que recusar, e o que oferecer

| Pedido | Por que não | O que cabe |
| --- | --- | --- |
| auditar o site de um concorrente, cliente ou fornecedor | sem autorização do dono é sondagem | auditar o sistema próprio; ou pedir a autorização por escrito ao dono de lá |
| descobrir uma senha, testar lista de senhas | força bruta afeta contas reais | ler se há limite de tentativas e provar no local, com 1 usuário de teste |
| derrubar o site para ver se aguenta | negação de serviço atinge todos os usuários | ler limites e tempo máximo de resposta; teste de carga é outro serviço |
| varrer portas, pastas e subdomínios em massa | é varredura agressiva, e atinge terceiros na mesma rede | inventário de rotas pelo código |
| um programa que explore a falha | código de ataque serve de novo, contra outros | a prova mínima, descrita em palavras no relatório |
| esconder o teste dos registros do servidor | auditoria autorizada não se esconde | avisar o dono do horário e do endereço de origem |
| baixar a base "para provar" | prova não precisa de dado real | a mesma prova com 2 usuários de teste |

Recuse em uma frase, diga o motivo e ofereça o que cabe. Não negocie o limite.

## 5. Serviços de terceiros dentro do sistema

Hospedagem, banco gerenciado, provedor de pagamento, de login e de e-mail entram pelo que o
sistema configura neles: chaves, regras de acesso, visibilidade dos depósitos, verificação de
webhook, endereços de retorno. A infraestrutura deles fica de fora. Se a falha parecer do
fornecedor, relate ao dono, que fala com o fornecedor. Teste contra a API de um fornecedor segue
os termos dele: a conferir na documentação de cada um.

## 6. Segredo e dado real no caminho

- **Chave ou senha num arquivo, no histórico ou na conversa:** não repita o valor. Registre o
  tipo, o arquivo e a linha. Diga ao dono que a chave precisa ser trocada, porque apagar o
  arquivo não a tira do histórico. Siga com valores de teste.
- **Dado pessoal de verdade** (homologação com cópia de produção é comum): pare aquela prova,
  não copie o conteúdo para a conversa nem para o relatório, e registre só o tipo de dado e onde
  apareceu. Homologação com dado real é, por si, um achado.
- **Arquivo de ambiente (`.env`):** leia os nomes das variáveis só no arquivo de exemplo. O valor
  de produção não é necessário para nenhuma conferência desta skill.

## 7. Quando parar

Pare, diga o que viu e espere o dono:

- o endereço chamado de homologação serve o site de produção;
- aparece dado pessoal de verdade numa resposta;
- o pedido passa a mirar sistema que não é do dono;
- uma prova alterou algo que não era dado de teste;
- o dono não confirma o termo, ou outra pessoa passa a dar as ordens;
- há sinal de invasão em andamento (acessos estranhos, dado alterado, cobrança de resgate).

Invasão em andamento não é auditoria. Diga ao dono para trocar as chaves, guardar os registros de
acesso sem apagar nada e procurar resposta a incidente profissional. A auditoria vem depois.

## 8. O que evitar

- Começar pela varredura "para adiantar", antes do termo.
- Tratar o endereço de produção como homologação porque "é só um GET".
- Aceitar "o sistema é meu" e auditar o que a pessoa só usa como cliente.
- Deixar o escopo crescer no meio do trabalho sem voltar ao termo.
- Omitir do relatório o que ficou de fora: o dono lê silêncio como "está tudo certo".

## 9. Checklist antes de começar

- [ ] Sistema, pasta e dono escritos no termo.
- [ ] Ambientes listados, com os usuários de teste de cada um.
- [ ] Produção: "fora", ou o pedido explícito do dono com o que pode ser lido.
- [ ] O que fica de fora, em lista.
- [ ] Decisão sobre a auditoria de dependências.
- [ ] Confirmação do dono, com data.
- [ ] Pasta `<auditoria>` criada fora do repositório.
