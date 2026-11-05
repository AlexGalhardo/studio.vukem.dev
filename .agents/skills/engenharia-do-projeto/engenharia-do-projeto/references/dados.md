# Dados e permissões: o que se guarda, quem pode ver e como o banco muda sem quebrar?

Leia quando: fase de dados; passo 3 do ciclo, se a mudança mexe em esquema, migração, permissão ou
dado de exemplo; antes de mexer em quem pode ver o quê.
Não é aqui: SQL, políticas e privilégios de PostgreSQL (`references/variante-web.md`).

## O mínimo

- Escreva a matriz de permissões antes do código: persona por recurso, quem lê e quem altera.
- Imponha a regra onde todos os caminhos passam (banco ou camada única de acesso), não na tela.
- Guarde o dado restrito separado do resto, com uma porta de leitura só.
- Escreva migração que só acrescenta. Corrigir uma migração já aplicada é escrever outra.
- Verifique num banco de teste recriado do zero, não no banco em que o dono cadastrou coisas.
- Mantenha os dados de exemplo (seed) só no ambiente local, com um marcador em cada dado restrito.

Conteúdo: 1. Modelo 2. Convenções 3. Matriz 4. Barreiras 5. Dado restrito à parte 6. Invariante
7. Espelho 8. Migrações 9. Dados de exemplo e marcador 10. Leituras 11. Falha 12. Outras stacks

## 1. O modelo na especificação e o documento vivo

Escreva o modelo de dados na seção 5 da especificação antes de existir tela: tela muda barato,
tabela com dado dentro muda caro, e regra de acesso que entra depois entra como remendo.

1. Liste os substantivos do produto: o que se cadastra, o que se cobra, quem usa, o que se mede.
2. De cada um: campo, tipo, obrigatório, limite, para onde aponta cada chave e as enumerações.
3. Escreva a matriz (§3) na mesma seção e confira que todo dado citado num fluxo existe no modelo.

Com um banco já em uso: não altere nem apague nada, dê prefixo ao que é novo e pare antes de mexer
no que existe. Ao fechar a fase, copie `assets/modelos/documento-por-assunto.md` para
`docs/dados.md`: o que está no banco, as convenções, uma seção por tabela e o que só o aplicativo
impõe. Sem isso alguém lê o banco, conclui que pode e abre um caminho por fora.

## 2. Convenções que se decidem uma vez

Decida uma vez, escreva no topo do documento de dados e aplique em toda tabela.

| Convenção | Regra e motivo |
| --- | --- |
| Prefixo | Em tudo o que é do produto: é ele que permite um teste genérico de privilégios |
| Identificador e datas | Identificador gerado pelo banco; data de criação obrigatória; data de alteração só onde a linha muda, mantida pelo banco. "Hoje" no banco pode não ser o dia de quem usa, por causa do fuso: escreva junto da tabela |
| Quem usa o produto | Aponte para a tabela de contas do serviço de login; o perfil vai em tabela à parte, com a mesma chave |
| Apagar o pai | Decida o destino de cada filho e escreva o motivo quando não é o óbvio |
| Teto no banco, regra fina no aplicativo | Tamanho de texto, de lista e de campo estruturado ficam no banco: sem teto, qualquer logado grava um registro enorme. Lista de opções que muda fica no aplicativo, porque trocar uma opção não deve pedir migração |
| Comentário e nome | Comentário em todo objeto; nome de restrição previsível, para o aplicativo reconhecer o erro pelo nome. Em unicidade com campo que aceita nulo, decida se dois nulos contam como iguais |
| Registro de uso | Guarda o que aconteceu e com qual item, não o texto que a pessoa digitou |
| Coluna sem uso | Fica, listada no documento de dados: tirar pede migração |

## 3. Matriz de permissões por persona

A matriz é o contrato que os testes conferem. Nas colunas vão as personas, com as de borda (em
período de teste, cancelado) e o serviço, que é a credencial do servidor e ignora as regras. Nas
linhas, os recursos, agrupados pelas cinco famílias de regra.

| Família | Visitante | Logado | Pagante | Administrador | Serviço |
| --- | --- | --- | --- | --- | --- |
| Conteúdo publicado | lê | lê | lê | lê e altera | tudo |
| Dado restrito | não lê | não lê | lê | lê e altera | tudo |
| Da própria pessoa | nada | lê e altera o seu | lê e altera o seu | nada dos outros | tudo |
| Só inserção (registro de uso) | nada | insere o seu | insere o seu | lê | tudo |
| Só serviço (estado de terceiro, lista de administradores) | nada | lê o seu | lê o seu | não escreve | escreve |

Escreva o motivo de toda célula que não é óbvia. Implementada, a matriz vira duas tabelas no
documento de dados: o que cada papel pode em cada objeto e as regras por tabela.

**Valide com o dono** em frases, não com a tabela: uma por linha que importa, com o que a persona
consegue, o que não consegue (a parte que ninguém pede) e a decisão padrão. Exemplo: "Quem ainda
não pagou vê o título e o resumo, mas não o texto. Sigo assim, salvo aviso em contrário."

## 4. Três barreiras

Barre o acesso em três lugares independentes, porque cada um falha de um jeito.

| Barreira | O que decide | O que não segura |
| --- | --- | --- |
| Privilégio de objeto | se o papel pode executar aquele comando naquela tabela | não distingue linhas |
| Regra de linha | quais linhas o papel alcança | não filtra o comando que esvazia a tabela |
| Guarda no aplicativo | quem é a pessoa, antes de validar ou ler qualquer coisa: é a primeira instrução de toda ação e de toda leitura protegida | não existe para quem chama o banco por fora do aplicativo |

- Em área restrita, a guarda vai na casca, em cada página e em cada função de leitura: a casca
  sozinha não protege página nem ação chamada direto.
- Logado que não pode recebe "não encontrado", não "proibido": a área fica invisível.
- A credencial de serviço mora em um módulo só, usado em poucos pontos, listados no documento.
- Teste e anote com o que um objeto novo nasce neste ambiente: em alguns, nasce aberto a todos.

## 5. O que é restrito mora em lugar próprio, com uma porta de leitura

| Faça | Porque |
| --- | --- |
| Separe a vitrine, pública quando publicada, do dado restrito, que vai em tabela, coleção ou depósito à parte. O nível de acesso é atributo do item, não da pessoa | Como campo de um registro público, toda consulta teria de lembrar de não pedi-lo, e uma consulta que pede tudo vaza |
| Escreva a decisão ("esta pessoa pode ler isto?") onde a regra é imposta, e a mesma decisão em função pura no aplicativo, com teste | A tela decide o que desenhar antes de ler. Mudou uma, muda a outra |
| Leia o dado restrito em uma função só, chamada depois da decisão. Para quem não pode, ela devolve nulo | O dado não vai escondido na página, em propriedade de componente nem no payload |
| Guarde arquivo restrito em depósito privado e entregue por endereço assinado de vida curta | Endereço público serve o arquivo sem passar por regra nenhuma |

Passo obrigatório de experiência (formulário depois do login) não protege nada: fica fora da matriz.

## 6. Invariante no banco, mensagem no aplicativo

Regra que não pode quebrar (o publicado não muda; no máximo um rascunho por item; publicar é tudo
ou nada) é garantida pelo banco: há mais de um caminho de escrita (tela, script, console do
provedor, credencial de serviço) e só o banco está em todos. O aplicativo confere a mesma regra
antes, numa função pura com teste, para responder com uma frase boa. As duas listas mudam juntas.

| A regra | No banco |
| --- | --- |
| Imutável | Trava que vale para todo papel, inclusive o de serviço. Documente o que ela bloqueia e o que deixa passar de propósito |
| No máximo um | Unicidade condicional |
| Operação composta | Uma transação que trava as linhas, monta a lista do que falta, recusa com a lista e só então grava tudo |
| Três erros combinados | Não autorizado, não encontrado, falta isto. Só a mensagem do terceiro chega à pessoa: erro cru do banco não vai à tela |

## 7. Estado que vem de terceiro: espelho com um escritor

Quando um serviço externo decide um estado (quem pagou, quem foi aprovado), guarde um espelho com
um único escritor: se a tela pudesse gravá-lo, um erro de regra daria acesso a quem não tem. Aqui
está só o modelo de dados (a rota de ligar o serviço é `references/stack.md` §5).

- **Tabela-espelho:** uma linha por pessoa, com a situação copiada. Sem linha é "nunca teve".
- **Um escritor:** o receptor de notificação. As ações do aplicativo agem no serviço, e quem
  grava a situação nova é a notificação que volta. Quem tem sessão recebe só leitura.
- **Uma vez só:** outra tabela guarda o identificador de cada notificação já recebida.
- **Quem tem acesso** sai de uma função, espelhada no aplicativo; caso de borda tem persona própria.

## 8. Migrações

Toda mudança de banco é um arquivo versionado, com carimbo de tempo e assunto no nome, que abre
dizendo o que faz, por quê e o que deixa de fora de propósito.

| Regra | Como | Porque |
| --- | --- | --- |
| Só acrescentar | Não apague nem altere estrutura que guarda dado; coluna nova aceita nulo ou tem padrão. Regra (de acesso, de função) pode ser trocada, numa migração nova que diz o que havia e o que passa a valer. Editar no lugar, só enquanto o arquivo não saiu do ambiente local | Editar depois cria dois bancos diferentes com o mesmo histórico |
| Expandir primeiro, usar depois | A estrutura que o código novo exige vai ao banco num passo anterior, compatível com o código antigo | O código antigo ignora o que não conhece; o novo falha sem a estrutura |
| Dado de produção em migração própria | Vocabulário fixo e o que o produto precisa para funcionar; idempotente; avisa na saída quando não pôde fazer o que devia | Os dados de exemplo não vão ao ambiente remoto, e migração que falha em silêncio deixa produção sem o dado |
| Fora da migração o que depende de quem ainda não existe | O primeiro administrador só existe depois do primeiro login: a linha dele é um passo à parte, anotado em `docs/ESTADO.md` | A migração roda antes de a conta existir |
| Banco do zero a cada verificação | Todas as migrações em ordem, os dados de exemplo, os testes, num banco de teste com nome próprio: o de desenvolvimento tem dono (`references/ambientes.md` §4) | Aplicar por cima esconde dependência de ordem |
| Artefato gerado do banco | Tipos, cliente ou esquema gerados de novo e commitados na mesma mudança (a conferência está em `references/ci.md` §4) | Escrito à mão ou esquecido, o código compila contra um banco que não existe mais |

## 9. Dados de exemplo desenhados para os testes

O arquivo só roda no ambiente local e no banco de teste, abre com esse aviso e só insere linhas. O
script que o aplica recusa endereço que não seja local: a trava vale mais que a regra escrita.

| O arquivo tem | Porque |
| --- | --- |
| Cabeçalho-índice com personas, itens, faixas de identificador e marcadores; identificadores fixos, em faixa diferente da dos testes | Quem escreve um teste lê o cabeçalho, não o arquivo |
| Uma persona por papel, no estado que o produto gravaria e com os passos obrigatórios do aplicativo cumpridos | Se não, todo teste com sessão é desviado para o formulário |
| Um exemplo de cada estado que as regras distinguem: publicado restrito, publicado livre, rascunho, publicado com versão nova em rascunho | Estado sem exemplo é regra que nenhum teste alcança |
| Datas relativas que não repetem os deslocamentos usados nos testes | Em coluna única, colidem |

**O marcador** tem forma única: `<SIGLA>-SEED-<ÁREA>-<6 caracteres aleatórios>`, com a sigla do
projeto, o dado restrito em uma palavra e seis letras maiúsculas ou dígitos. É uma linha dentro do
texto restrito e não aparece em nenhum outro campo. Texto longo leva dois, na primeira linha e na
última, porque vazamento só do começo também tem de ser pego. Mais um vai num dado livre, que o
visitante deve ver (prova que o teste enxerga), e um em cada rascunho, que ninguém vê em público.

**Base:** adaptação. O método foi praticado numa aplicação web com banco relacional; o que está
aqui (as duas últimas linhas da tabela) ainda não foi praticado. Confira antes de confiar.

| O dado restrito é | Plante nos dados de exemplo | O teste de vazamento afirma |
| --- | --- | --- |
| Texto livre | o marcador | não chega a quem não pode, e chega a quem pode |
| Campo com formato (telefone, documento) | valor sentinela único, no formato do campo e impossível de existir: um telefone com código de área que não existe | o valor sentinela não aparece |
| Enumeração, ou sim e não | nada: não há valor único | o nome do campo não aparece na resposta crua |

## 10. Leitura compartilhada e leitura por pessoa

Decida a família ao escrever a leitura: em cache compartilhado, o que depende de quem pede vaza.

| | Leitura compartilhada | Leitura por pessoa |
| --- | --- | --- |
| Exemplo | vitrine, listagem, página pública | o que é da pessoa, sessão, dado restrito, a área restrita inteira |
| Cache | compartilhado, com prazo | nenhum |
| Lê com que identidade | nenhuma: o papel de visitante | a sessão da pessoa |

É a permissão do visitante no banco que torna o cache seguro: ele só recebe o que é público.
Escrita por fora do aplicativo não expira o cache: preveja isso antes de carregar dados em
produção. **Arquivos**, só o princípio: vitrine em depósito público; restrito em depósito privado,
sem leitura para a pessoa comum; tipo e tamanho valem os que o depósito informa, não o navegador.

## 11. Para que lado falha

Decida, caso a caso, o que acontece quando a consulta falha, e escreva. Toda leitura distingue
três resultados: erro (lança), não existe (devolve nulo, e a página responde "não encontrado") e
vazio de verdade (lista vazia, e a tela mostra o estado vazio).

| O que falhou | Faça | Por quê |
| --- | --- | --- |
| Leitura compartilhada | lance erro; não devolva lista vazia | vazio guardado em cache esconde tudo até o prazo |
| "É administrador?" | negue | erro não pode abrir área restrita |
| Passo obrigatório de experiência | libere | banco fora do ar não pode prender ninguém |
| Apagar arquivo do depósito | registre e siga | falha na limpeza não derruba a ação |

## 12. Em outras stacks

| Nesta ficha | Onde não existe |
| --- | --- |
| Regra de linha no banco | camada única de acesso a dados que sempre recebe "quem pede" e filtra; o teste por persona roda contra ela |
| Papéis do banco por persona | contas de conexão com privilégios distintos: público só leitura, aplicativo, migrações |
| Função no banco com direitos elevados | função de servidor com a credencial elevada, num módulo único, com a guarda na primeira linha |
| Unicidade condicional | coluna derivada com índice único, ou trava na aplicação dentro de transação |
| Enumeração do banco | texto com restrição de valores: primeiro a restrição aceita o valor, depois alguém grava |
| Tabela e coluna | coleção e campos, em banco de documentos: escreva também os índices que as consultas pedem |
| Migração escrita à mão | migração gerada de um arquivo de esquema: revise o que foi gerado antes de commitar e não gere de novo uma já aplicada |
| Banco de teste recriado por script | banco efêmero por execução, em contêiner ou em serviço do CI |

## Pare se

- A mudança pede editar ou apagar uma migração já aplicada fora do ambiente local.

## O que evitar

- **O visitante esvazia ou apaga o que não devia.** O objeto nasceu com privilégios que ninguém
  concedeu. Revogue antes de conceder e teste os privilégios à parte: regra de linha não segura.
- **O erro ou o sucesso de uma gravação revela se um identificador existe.** A chave para outro
  registro funciona como oráculo. Exija que o item referido seja visível para quem grava.
- **"A linha existe, logo o passo foi cumprido."** Quem grava a própria linha pode gravar direto,
  sem o formulário. Valide de novo o conteúdo da linha antes de liberar o passo seguinte.
- **O teste de banco passa hoje e falha amanhã.** Datas relativas colidem com as dos dados de
  exemplo ou viram com o dia. Recrie o banco a cada verificação; rodar de novo até passar não serve.

## Pronto quando

- [ ] A matriz de permissões está na especificação e o dono confirmou as frases de cada persona.
- [ ] O banco de teste sobe do zero, com todas as migrações em ordem, sem erro.
- [ ] Cada persona da matriz tem teste do que lê, do que altera e do que não consegue.
- [ ] Cada dado restrito está no cabeçalho dos dados de exemplo; há um marcador que o visitante vê.
- [ ] Os dados de exemplo só rodam no ambiente local, e o script recusa outro endereço.
- [ ] O documento de dados mudou junto; `docs/ESTADO.md` diz que migração falta no ambiente remoto.

Volte ao `SKILL.md`, §4.
