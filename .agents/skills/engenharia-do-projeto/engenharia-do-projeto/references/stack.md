# Stack e arquitetura: como escolher e ligar ferramentas sem chutar?

Leia quando: situação A, passo 3; troca de ferramenta, de versão ou de serviço; passo 3 do ciclo,
quando a mudança liga um serviço externo (banco, login, pagamento, hospedagem, e-mail): só a §5.
Não é aqui: como registrar a decisão (`references/decisoes.md`).
**Base:** proposta. A §1 (critérios de escolha por padrão) é desenho deste método, sem uso
anterior: confira com o dono o que pesa mais para ele.

## O mínimo

- Proponha uma stack, não um cardápio, com o motivo, o custo e como trocar depois.
- Leia a documentação da versão instalada antes de escrever para ela: a memória conhece melhor a
  versão anterior e escreve com convicção o que deixou de existir.
- Meça o que der em vez de supor, e diga de onde veio cada afirmação técnica (§2).
- Um registro por escolha, com a alternativa descartada.
- Todo serviço externo ganha a ficha do serviço (§5) antes da primeira linha de código que o chama.
- Ao dono que nunca programou, não pergunte ferramenta: diga o que escolheu e o que isso custa a
  ele em contas, em dinheiro e no que fica preso.

Conteúdo: 1. Quem escolhe e os critérios 2. Medir em vez de supor 3. As vinte perguntas
4. Fronteiras que a arquitetura nomeia 5. Ligar um serviço externo 6. O que vira registro

## 1. Quem escolhe e os critérios

O agente propõe e o dono aprova. Vão a ele, como pergunta com padrão, só as partes que são dele:
conta a criar, o que custa dinheiro e dependência grande (`SKILL.md` §5). Dono dev que já traz a
stack: use os critérios como conferência, diga uma vez onde há risco e siga a escolha dele. Projeto
que já existe: a stack é a que está lá, e trocar uma peça é mexer no que está em produção.

Entre duas opções, vale esta ordem. Cada critério tem uma conferência que se observa: escreva na
proposta o resultado dela, não um adjetivo.

| Critério | Conferência |
| --- | --- |
| 1. O mais simples que atende | Quantas peças novas entram (linguagem, banco, serviço, processo no ar). Sai a que nenhum fluxo da especificação usa |
| 2. Documentação da versão instalada à mão | Onde ela está no projeto: o caminho, ou a página da versão exata |
| 3. Menos contas e painéis para o dono | Quantas contas ele cria e quantos painéis passa a abrir |
| 4. Custo zero para começar e preço conhecido depois | A página de preço lida, com a data, e o que dispara a primeira cobrança |
| 5. Igual no ambiente local, no CI e em produção | O que difere, por escrito, e o que garante que a diferença não importa |
| 6. Dá para sair | O que se perde ao trocar: o que não se exporta e o que fica preso ao serviço |

A proposta diz, em linguagem comum: o que entra; o critério que decidiu, com o resultado da
conferência; o que custa ao dono (contas a criar, quanto e a partir de quando); o que se perde ao
trocar; e a alternativa descartada. Na especificação fica só a intenção ("a versão estável, com
suporte"), que não envelhece; a versão exata mora no registro e no arquivo de instruções.

## 2. Medir em vez de supor

Documentação e memória divergem do comportamento real: um exemplo da própria documentação pode não
valer com uma opção do projeto ligada, e só a medição mostra. Toda afirmação técnica que sustenta
uma decisão leva a etiqueta de onde veio:

| Etiqueta de origem | Quer dizer | Sustenta decisão? |
| --- | --- | --- |
| `[medido]` | Rodou e viu, com o número. Diga onde: no projeto, no build de produção ou na sonda | Sim |
| `[documentação da versão instalada]` | Está escrito, com o caminho e o trecho | Sim, até a medição dizer outra coisa |
| `[memória]` | Lembrança ou conclusão própria, sem fonte aberta agora | Não: ache o trecho ou meça antes |

Meça o que é caro de desfazer e depende de comportamento: o que entra em cache, o que acontece no
erro, o limite de um serviço, o que a versão nova mudou. Quando não dá para medir no projeto sem
alterá-lo, use uma **sonda**:

1. Crie um projeto mínimo fora do repositório, com a mesma versão e as mesmas opções, que imita só
   a estrutura em questão.
2. Rode, anote o número e guarde o script. A sonda fica fora do repositório; o resultado e, quando
   é curto, o script vão para o plano da fase ou para o Contexto do registro.
3. Declare a validade: "medido na sonda; repetir no projeto antes de fechar". Onde os dois
   divergirem, vale o número do projeto.

## 3. As vinte perguntas

São para o agente responder antes de escrever o registro; com dono dev, servem de lista de
conferência. Ao dono que nunca programou vai só o efeito: o que custa, o que ele precisa criar e o
que não tem volta. "Não se aplica" é resposta, desde que dita.

| Bloco | Perguntas |
| --- | --- |
| Escolha e versão | **1.** Qual versão exata entra, e por que não a mais nova (ou a anterior)? **2.** A documentação consultada é a da versão instalada, e onde ela está no projeto? **3.** O resto da cadeia acompanha essa versão: lint, editor, gerador de código, CI, hospedagem? **4.** O que entra junto sem ser pedido: dependência indireta, arquivo de configuração novo? **5.** O instalador ou gerador da ferramenta sobrescreve algo que já existe, e dá para adotar sem ele? |
| O que passa a ser obrigatório | **6.** Que regra a escolha impõe a todo arquivo novo? É a linha que vai para o arquivo de instruções. **7.** O que deixou de existir, mudou de nome ou de assinatura em relação ao que a memória lembra? **8.** Onde fica a fronteira entre o que roda no servidor e o que vai ao cliente, e onde moram os segredos? |
| Como falha | **9.** Quando alguém erra, o erro aparece onde: no editor, no lint, no build, em execução, só na tela ou em lugar nenhum? **10.** Quando a dependência cai ou responde errado, o sistema falha fechando ou abrindo? **11.** O que foi medido rodando e o que é só leitura da documentação? |
| Ambientes | **12.** Roda igual no ambiente local, no CI e em produção, e onde difere, o que garante que não importa? **13.** A verificação roda no CI sem segredo e sem serviço externo? **14.** O build passa a precisar de algo no ar (banco, variável, serviço), e isso muda a ordem de ida a produção? |
| Saída | **15.** Que condição observável dispara a revisão da escolha, e o que não fazer até lá? **16.** Dá para voltar atrás, e o que não tem volta? **17.** Qual alternativa foi descartada, e o que ela custaria? |
| Amarração | **18.** Quem decidiu, o agente dentro de "decida e registre" ou o dono, e falta algo dele (conta, chave, pagamento)? **19.** Que teste, regra de lint ou verificação do CI impede a regressão? **20.** Que linhas do arquivo de instruções e que documentos por assunto mudam, e alguma seção da especificação ficou velha? |

## 4. Fronteiras que a arquitetura nomeia

Cinco respostas que se dão antes do primeiro arquivo do tipo, porque depois cada arquivo novo
responde de um jeito. Cada uma vira regra no arquivo de instruções, com quem a verifica (como se
impõem as duas últimas está em `references/dados.md` §10 e §11).

| Fronteira | O que a arquitetura diz | Se ficar sem nome |
| --- | --- | --- |
| Onde mora o segredo | Um módulo lê os segredos, do lado do servidor; o resto recebe dele. É o caminho de `segredos.caminhos`, em `[zonas]` | O segredo é lido em dois lugares, e um deles vai ao cliente |
| Servidor e cliente | O que roda só no servidor, o que é entregue a quem usa o produto e a marca que separa os dois | Dado ou segredo acaba no código entregue ao cliente, que é público mesmo que a tela não mostre |
| Quem escreve cada dado | O único ponto que grava cada tabela ou coleção. Estado que vem de serviço externo tem um escritor: quem recebe a notificação | "Por que este registro está assim?" passa a ter duas respostas |
| Leitura compartilhada e leitura por pessoa | Toda leitura é de uma das duas famílias, decidida ao escrevê-la. A compartilhada não conhece quem pede | O que depende de quem pede entra na cópia de todos e vaza para o próximo |
| Para que lado falha | Em cada ponto de decisão, o que acontece no erro: nega, libera ou mostra erro. Decide-se caso a caso e escreve-se | A falha escolhe sozinha: a checagem de acesso que quebra libera, e a lista vazia vai ao cache como se fosse dado |

## 5. Ligar um serviço externo

É a rota única para banco hospedado, login, pagamento, hospedagem, e-mail e qualquer outro serviço
de terceiros. Antes da primeira linha de código que o chama, leia a documentação atual do serviço e
preencha a ficha dele. O que não der para responder é o que falta ler. A ficha do serviço é a
tabela de consulta do documento por assunto (`assets/modelos/documento-por-assunto.md`):

```markdown
| <Serviço> | Resposta |
| --- | --- |
| Fonte da verdade | <o serviço ou o banco do projeto>; o outro lado é cópia |
| Escritor único | <o único módulo que grava a cópia> |
| Variáveis | `<NOME>`: <o que é>; <só servidor ou pública>; sem ela, <o que o produto faz> |
| Mora no painel | <configuração>: esperado <valor>; o código aceita <a faixa que o serviço permite> |
| Só o dono faz | <criar a conta, colar a chave na hospedagem, ligar a notificação> |
| Testar sem as chaves | <o que o cliente falso cobre; o que fica sem cobertura> |
```

- **Variáveis:** só os nomes. O valor de teste mora no arquivo de ambiente local; o de produção,
  só no painel da hospedagem, posto pelo dono. Sem as chaves o produto abre, com um aviso no lugar
  da função, e as verificações rodam no CI sem segredo e sem o serviço.
- **Mora no painel:** o que se configura fora do repositório diverge do ambiente local sem ninguém
  ver. O leia-me diz o valor esperado, o código aceita a faixa inteira que o serviço permite, e o
  primeiro uso em produção é testado de verdade pelo dono.
- **Só o dono faz:** escreva cada passo para ele seguir sem o agente (onde clicar, que valor colar,
  o que não ligar e por quê), depois de ler a documentação atual, porque painel muda sem aviso. O
  item entra em "Passos do dono", no estado.

**Cobrança.** Sete princípios que valem para qualquer serviço de pagamento:

1. **Quem escreve o estado de pagamento é o receptor de notificação**, e só ele. As ações do
   produto (cancelar, pausar, dar desconto) agem no serviço, e quem grava o estado novo é a
   notificação que volta. Se uma tela pudesse gravar, um erro de regra daria acesso pago a quem não
   pagou (o espelho, como modelo de dados, está em `references/dados.md` §7).
2. **Idempotência por evento.** Guarde o identificador de cada notificação e processe cada uma só
   uma vez, porque o serviço reenvia.
3. **Assinatura conferida no corpo cru**, sobre os bytes recebidos e antes de interpretar.
   Notificação sem assinatura válida não grava nada.
4. **Chave de teste e chave de produção em ambientes separados:** a de teste, no ambiente local; a
   de produção, só na hospedagem.
5. **O que se testa sem chave:** o receptor, com cliente falso e a conferência de assinatura de
   verdade, com segredo de mentira (`references/testes.md` §4); e a regra "que estados dão acesso",
   como função pura, com um caso por estado que o serviço tem.
6. **O que só o dono faz no painel:** a conta, os produtos e os preços, a notificação com a lista
   exata de eventos e a chave de produção na hospedagem. Preço é decisão dele.
7. **Configuração do painel:** aceita na faixa que o serviço permite ("Mora no painel", acima).

O SQL e o código de cobrança da variante web estão em `references/variante-web.md` §9.

## 6. O que vira registro

Um registro por escolha, e não um para a stack inteira: assim cada uma se cita e se revê sozinha.

- **Vira registro:** a versão escolhida contra a mais nova; cada serviço externo, com o que se
  perde ao sair; a fronteira da §4 que contraria o costume da stack; a diferença aceita entre
  ambientes; a escolha que o dono fez contra a recomendação.
- **Do que ele é feito:** as respostas 1 e 17 dão o Contexto; a 6, a 10, a 15 e a 16, as
  Consequências; a medição da §2 entra como evidência, com o número e a data.
- **Não vira registro:** o que a especificação já dizia, sem alternativa descartada.

## O que evitar

- **Código escrito para a versão que a memória lembra.** A memória conhece melhor a versão
  anterior: função que mudou de nome, arquivo que mudou de lugar. Leia a documentação da versão
  instalada e ponha no arquivo de instruções as diferenças que já causaram erro.
- **Inferência escrita como fato.** O plano afirmava um comportamento que a medição desmentiu. Sem
  etiqueta, só aparece quando alguém mede. Etiquete e meça antes de apoiar a decisão.
- **"A ferramenta impede isso", e não impede.** A proteção foi escrita de memória. Confira rodando:
  cometa a violação de propósito e veja o erro aparecer.
- **O instalador sobrescreveu o que já existia.** Gerador de ferramenta regrava estilo e
  configuração sem perguntar. Leia o que ele altera e, quando der, adote sem rodá-lo.
- **O valor do ambiente local tomado como o de produção.** O código de confirmação tinha um tamanho
  no ambiente local e outro no painel de produção: a tela cortava e ninguém entrava. Aceite a
  faixa que o serviço permite. Não serve: ajustar o código ao valor novo e esperar a próxima troca.

## Pronto quando

- [ ] A proposta diz o motivo, o custo para o dono e o que se perde ao trocar.
- [ ] As vinte perguntas têm resposta ou "não se aplica"; nada se apoia só em `[memória]`.
- [ ] As cinco fronteiras da §4 estão nomeadas, cada uma com o arquivo ou a pasta.
- [ ] Cada serviço externo tem a ficha preenchida, só com nomes de variável, e os passos do dono
      estão no estado.
- [ ] Há um registro por escolha, com a alternativa descartada.

Volte ao `SKILL.md`, §3.
