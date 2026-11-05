# Especificação: como escrever a fonte da verdade da intenção, e o que fazer com ela depois?

Leia quando: situação A, depois da entrevista. A dúvida é "o que era para ser". O dono muda o que
o produto faz.
Não é aqui: as perguntas ao dono (`references/entrevista.md`).
**Base:** proposta. A divisão de quem preenche cada seção (§1) e a aprovação por resumo de uma tela
(§6) são desenho deste método, sem uso anterior: confira se o resumo coube em uma tela e se o dono
respondeu a ele.

## O mínimo

- Preencha o arquivo que a preparação criou a partir de `assets/modelos/especificacao.md`, sem
  mudar o número das seções: os outros documentos citam "seção 5 da especificação".
- Aperte em dados, permissões, números e segurança, que é onde o erro sai caro ou não aparece.
  Solte no que dá para decidir depois.
- Não peça ao dono que leia o arquivo: mostre na conversa o resumo de uma tela, que é também a
  devolução do que foi entendido, com as três decisões que mais pesam e "Decidi sem perguntar".
- Pare até o dono responder "aprovado". Sem isso não há stack, fase nem código.
- Depois da aprovação o texto não se edita: a mudança vira registro, com uma nota datada no topo.

Conteúdo: 1. Quem preenche o quê 2. As onze seções 3. Apertar e soltar 4. Referências com regras
de uso 5. Fases, paradas e dúvida 6. Aprovação 7. Depois de aprovada 8. Projeto que já existe

## 1. O que é e quem preenche o quê

Um arquivo só, na raiz do projeto, com a intenção: sem ele, cada sessão reinterpreta o pedido.
Redija para uma sessão que não viu a conversa, porque é ela que vai implementar.

| Seções | De onde vem o texto | O que o dono confere |
| --- | --- | --- |
| 1, 2, 6 e 9 | Das respostas dele na entrevista, com as palavras dele | O próprio texto, que ele reconhece |
| 4 | Do que ele disse que existe, conferido pela leitura do que há | O inventário |
| 3, 5 e 7 | Proposta do agente: stack, dados, organização do código | O efeito, no resumo: quem vê o quê, o que custa, o que fica caro de trocar |
| 8, 10 e 11 | Do agente, a partir das outras | As fases, uma linha cada, e o que pede pergunta |

Na seção 3 escreva a intenção ("a versão estável mais recente") ou só o papel ("banco relacional"):
o nome e o número exato nascem no registro de cada escolha. Na seção 7 a árvore é plano: o mapa
do que existe mora no arquivo de instruções.

## 2. As onze seções e o que cada uma resolve

A ordem segue a dependência: o que é, com o quê, os dados, o comportamento, a forma do código, o
plano. Seção que não se aplica fica com o título e uma frase, porque apagar mudaria os números.

| Nº | Seção | O que contém | O que resolve |
| --- | --- | --- | --- |
| 1 | O que você vai construir | O produto em um parágrafo; os tipos de coisa; quem usa; o que é aberto e o que é restrito, e por quê; as condições desta versão | Dá o vocabulário comum e a regra de negócio que vira regra de segurança |
| 2 | Referências | A tabela "arquivo, o que mostra" e as regras de uso (§4) | Diz o que na referência é lei e o que é enfeite |
| 3 | Stack e decisões | Uma linha por escolha, com escopo e cuidado | Impede troca de ferramenta no meio e uso fora do escopo |
| 4 | O que já existe | O que está em uso, a fonte da verdade de cada dado, as regras de convivência | Protege o que está no ar |
| 5 | Modelo de dados e matriz de permissões | Enumerações; cada conjunto de dados, campo a campo; a matriz, se há mais de uma persona (`references/dados.md` §3); o dado restrito; os arquivos | Fixa o que mais custa mudar depois |
| 6 | Fluxos | Um bloco por área, com passos, limites e textos | Descreve o comportamento que se observa |
| 7 | Organização do código | Pastas comentadas e regras com endereço | Dá lugar certo a todo arquivo novo |
| 8 | Fases | Uma linha por fase (§5) | Dá a ordem das entregas |
| 9 | Fora do escopo | O que não entra nesta versão | Corta a expansão do escopo |
| 10 | Variáveis de ambiente | Os nomes, sem valores, e quais são só do lado do servidor | Impede variável inventada e segredo dentro do arquivo |
| 11 | Quando tiver dúvida | O que pede pergunta neste projeto (§5) | Dá autonomia com limite |

## 3. Onde apertar e onde soltar

Aperte no que é persistente, no que cruza fronteira de confiança e no que tem número. Detalhe em
tudo deixa o documento ilegível; de menos em dados e permissões, vira retrabalho e vazamento.

| Aperte em | O que escrever |
| --- | --- |
| Dados | Uma linha de propósito por conjunto, com o porquê de ser separado. De cada campo: tipo, obrigatório ou não, padrão, limite, unicidade, o que acontece ao apagar o pai. Onde a regra é validada, quando não é no banco |
| Permissões | A matriz persona por recurso: quem lê, quem altera |
| Números | Todo limite com unidade: tamanho de arquivo, duração, validade de um link, quantos dias um aviso dura |
| Segurança | A regra central em negrito, no ponto do fluxo em que ela morde, com os lugares por onde o dado costuma sair ditos pelo nome ("nem escondido na página, nem na resposta de dados") |
| Cuidado técnico conhecido | A instrução com o porquê entre parênteses, para ninguém "consertar" depois |
| Regra que vale em dois lugares | O arquivo em que ela é decidida, e que o outro lugar o espelha |
| Texto dos momentos que importam | A frase exata do botão e do aviso |
| Construir sem ligar | O que se implementa agora e só se ativa depois, e quando |
| Privacidade | A proibição no ponto em que o dado nasce ("não grave o texto que a pessoa digitou") |

Solte em: nomes de componentes (a árvore sugere, não obriga), desenho interno das funções e ordem
do trabalho dentro de uma fase.

## 4. Referências com regras de uso

Referência mistura decisão com enfeite: nome inventado, texto de exemplo, ilustração que no produto
será outra coisa. Sem regra escrita, o enfeite vai parar no banco.

1. Na tabela, uma linha por arquivo, com tela, largura, persona e estado ("a mesma página para
   visitante", "o cartão normal e com foco"). O "Pronto quando" de uma fase de telas cita a
   referência por largura e estado: sem os dois, o critério não tem como ser conferido.
2. Abaixo da tabela, mande ler todas antes de escrever interface e escreva as regras de uso:

| Na referência | É | O que escrever |
| --- | --- | --- |
| Disposição, hierarquia, espaçamento, tipografia, cores, estados | Lei | "Siga", e onde estão as variáveis de estilo |
| Nome inventado, número, ilustração provisória | Enfeite | O que é de mentira e como será no produto |
| Texto e mídia de exemplo | Não copiar | Não são conteúdo real: valem em dados de exemplo e em testes, não no banco de produção |
| Depoimento, contagem, oferta ou marca que o produto não tem | Não copiar | Fica de fora, dito pelo nome |
| Marca | Restrição | O que pode usar e o que não pode |

Produto sem interface: a referência são exemplos de entrada e saída, com a mesma tabela e a regra
"os valores são fictícios". Sem referência nenhuma, a seção diz isso em uma frase.

## 5. Fases, paradas e política de dúvida dentro da especificação

- **Seção 8, uma linha por fase:** o nome e o que entrega, com a fundação (base, dados e
  permissões) antes das telas. O "Pronto quando" mora no roteiro: critério em dois lugares diverge
  na primeira mudança (as qualidades de um bom critério estão em `references/fases.md` §2).
- **Paradas:** a especificação não as repete. Moram no `SKILL.md` §5 e no roteiro.
- **Seção 11, o que pede pergunta neste projeto:** parta da caixa "Pergunte antes" do `SKILL.md` §5
  e escreva o caso concreto do produto ("mexer na planilha de clientes que já existe"). Feche com
  "fora isso, decida e registre": é dessa frase que nasce o registro de decisões. Esta é a lista
  do dia da aprovação; a que vale hoje é a do bloco "Como trabalhamos" do arquivo de instruções.
- **A parada no ponto exato:** além da lista, escreva a instrução onde ela morde, na seção 4 ou no
  fluxo ("se precisar mexer no que existe, pare e pergunte"; "peça os identificadores; não crie").

## 6. Aprovação, uma parada só

Grave a especificação e mostre, na mesma mensagem, o resumo abaixo. Ele faz o papel de "confirmar o
que entendi": não há parada anterior para isso. Cabe em uma tela, em linguagem comum, sem nome de
ferramenta que o dono não citou (a régua de tom é o trecho 2 de `assets/exemplo/conversa.md`).

```text
O que entendi: <o produto em até quatro linhas, com as palavras do dono: quem usa, o que faz e o
que fica de fora>
As três decisões que mais pesam:
1. <a decisão, dita pelo efeito para quem usa>
Decidi sem perguntar: <cada padrão adotado e cada detalhe que o dono não citou, com como desfazer>
Preciso de você: <conta, custo ou material que só o dono resolve; ou "nada agora">
Como conferir: leia as três decisões; se alguma estiver errada, diga o número.
Se está certo, responda "aprovado". Daí em diante, o que mudar vira decisão anotada, com data.
```

- As três decisões são as mais caras de desfazer, não as mais interessantes: quase sempre quem pode
  ver o quê, o que não pode acontecer e o que o produto não faz ou não cobra.
- Resposta que não é a palavra de liberação ("legal", "pode ser", outra pergunta) não libera:
  responda e peça a palavra de novo. Correção pedida: edite, mostre só o que mudou e peça de novo.
- Com o "aprovado", preencha a data no topo do arquivo e siga a ordem do `SKILL.md` §3. No perfil
  dev o resumo encurta: as três decisões, "Decidi sem perguntar" e o pedido.

## 7. Depois de aprovada, congelada

Reescrever a especificação a cada mudança apaga o porquê de cada desvio e convida a ajustá-la ao
que foi feito. Quando o dono muda o que o produto faz, ou a implementação precisa se afastar dela:

1. Escreva o registro, citando a seção atingida e quem decidiu.
2. Acrescente uma nota datada logo abaixo do título da especificação, na forma `> Nota de
   AAAA-MM-DD, posterior à aprovação: a seção <n> dizia <o quê>; vale o ADR-NNN. Continua valendo:
   <o resto>.` É o único acréscimo permitido; o corpo fica como foi aprovado.
3. Na mesma mudança, atualize o que descreve o produto de hoje: o parágrafo de abertura do arquivo
   de instruções e, se a mudança mexe em fase, o roteiro.

Com o tempo a especificação deixa de descrever o produto, e quem a lê sozinha erra: ela guarda a
intenção de partida (qual documento vale quando dois divergem está em `references/decisoes.md`
§5). Seção desatualizada fica assim até o dono pedir a revisão, que passa pela parada da §6.

## 8. Projeto que já existe

Não escreva especificação retroativa por padrão: ela descreveria o que o código já faz, e aí o
código é a fonte. A preparação só cria o arquivo em projeto com código quando o dono pede (o que
se oferece na adoção está em `references/adocao.md`). A intenção dali em diante entra por registro
e pelo "Pronto quando" da próxima fase. Especificação pedida para uma versão nova cobre o que será
construído, e o que está no ar entra como inventário na seção 4.

## O que evitar

- **A especificação é editada para bater com o que foi feito.** O texto velho incomoda. Escreva o
  registro e a nota datada: corrigir "só o parágrafo" apaga a alternativa descartada e o motivo.
- **Uma sessão lê só a especificação e implementa o que já mudou.** O texto congelado não descreve
  o produto de hoje. Mantenha a nota do topo e o parágrafo de abertura do arquivo de instruções.
- **O texto de exemplo da referência aparece em produção, ou o critério de tela diz só "igual à
  referência".** Faltaram as regras de uso e a largura e o estado de cada arquivo. Escreva a §4
  antes da primeira tela.
- **Número de versão escrito na seção 3.** Envelhece na primeira atualização e passa a contradizer
  o registro. Escreva a intenção; o número mora no registro e no arquivo de instruções.

## Pronto quando

- [ ] As onze seções estão no arquivo, com os números do modelo; a que não se aplica diz por quê.
- [ ] A seção 5 traz a matriz de permissões e a tabela do dado restrito; todo limite tem unidade.
- [ ] A seção 2 diz o que seguir e o que não copiar, ou diz que não há referência.
- [ ] O resumo de uma tela foi mostrado, e o dono respondeu "aprovado".
- [ ] A data da aprovação está no topo, e não sobra lacuna no arquivo.

Volte ao `SKILL.md`, §3.
