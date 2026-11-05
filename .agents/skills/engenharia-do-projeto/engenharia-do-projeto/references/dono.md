# Dono: como perguntar, decidir, avisar e validar com quem pede?

Leia quando: é preciso uma decisão, uma autorização ou uma validação; o dono pede algo contra a
recomendação; um termo novo vai aparecer para quem nunca programou.
Não é aqui: a primeira conversa de um projeto novo (`references/entrevista.md`).
**Base:** proposta. O glossário, os dois perfis e os textos de mensagem são desenho deste método,
sem uso anterior: troque as palavras pelas que o dono mostrar entender. As regras de colaboração
são prática vista; os exemplos de outros tipos de projeto (§1) são adaptação, a conferir.

## O mínimo

- Pergunte só com a decisão padrão ao lado: sem ela, o trabalho para até o dono responder.
- Valide por roteiro de três a sete passos, com um "não deve" e a lista do que vem depois.
- Combine uma palavra de liberação e não leia outra resposta como ela.
- O sim vale para a lista entregue. O que não está nela pede outro pedido.
- Pedido contra a recomendação: avise do risco uma vez, cumpra e registre quem decidiu.
- Resposta ambígua pede pergunta, não interpretação.

Conteúdo: 1. As três caixas 2. Pergunta com padrão 3. Validação e palavra de liberação 4. Avisar,
obedecer, registrar 5. Decisão registrada e regra 6. Cinco listas 7. A lista 8. Quem nunca programou

## 1. As três caixas na prática

A lista fechada está no `SKILL.md` §5. Em cada projeto ela ganha nomes, escritos no bloco "Como
trabalhamos" do arquivo de instruções. A quem nunca programou, diga a primeira caixa em quatro
verbos, logo no começo: gastar dinheiro, apagar dado, publicar, mudar o que o produto faz.

| Projeto | Entra em "Pergunte antes" | Entra em "Só o dono faz" |
| --- | --- | --- |
| Aplicação web com banco | mexer em tabela ou serviço que já atende gente; criar plano ou cobrança | variáveis na hospedagem, domínio, configuração do serviço de pagamento, envio de e-mail, texto legal, troca de chave exposta |
| Aplicativo móvel | tudo o que muda o que vai para a loja | a conta e a página do aplicativo na loja (a conferir) |
| Infraestrutura, dados e automações | o recurso que gera custo; o que é destrutivo ou não se reprocessa | contas e credenciais de cada serviço (a conferir) |

**Passo do dono** se escreve para ele seguir sem o agente: onde entrar, que valor colar, o que não
ligar e por quê. Leia antes a documentação atual do serviço, porque painel de terceiro muda sem
aviso. Diga até quando o passo é preciso e lembre na hora.

## 2. Pergunta com decisão padrão

| Tipo de pergunta | Quando | O padrão é | Enquanto a resposta não vem |
| --- | --- | --- | --- |
| A que espera | o ponto é da caixa "Pergunte antes" | a recomendação: o que o agente faria | para o que depende dela; o resto segue |
| A que não trava | toda outra escolha de produto | o que já está sendo seguido | segue; a resposta revê depois, com o custo dito |

```text
<n>. <O ponto, pelo que a pessoa vê ou paga, em uma frase>?
    Padrão: <o que será feito>, porque <motivo em meia linha>.
    Se preferir <a alternativa>: <o que muda, e quanto custa trocar depois>.
```

- **Até cinco por rodada**, as que mais pesam primeiro. O resto vira "Decidi sem perguntar": o
  dono corrige melhor o que lê pronto do que responde a vinte perguntas.
- **O ponto se escreve pelo efeito**, não pelo mecanismo: "o primeiro visitante depois de uma
  publicação ainda vê a versão anterior". Em jargão, a pergunta não é lida.
- **Padrão não afrouxa regra.** Opção que abre exceção a regra inegociável entra como alternativa
  e espera a resposta.
- **Resposta ambígua pede pergunta.** "Pode ser", ou um "ok" a uma mensagem com duas perguntas:
  refaça só o item sem resposta, com as duas leituras lado a lado. "Faça como achar melhor" não é
  ambíguo: adote o padrão e declare.

## 3. Roteiro de validação e palavra de liberação

O dono julga pelo que vê: o roteiro troca "dá uma olhada" por cinco minutos de conferência, e a
palavra separa "vi e gostei" de "pode seguir". Texto: `assets/modelos/mensagens-ao-dono.md` §2.

1. Deixe o produto no ar no ambiente local, sem enviar nada, e diga isso na primeira linha.
2. Escreva de três a sete passos: o que abrir ou fazer, e o que deve aparecer. Pelo menos um é
   "não deve aparecer", feito como quem não tem permissão. Havendo tela, um é no celular.
3. Diga o que não está na entrega, para a falta não parecer defeito, e peça o retorno pelo número
   do passo e pelo que apareceu.
4. Feche com o que acontece depois da palavra, na ordem. É essa lista que a palavra autoriza: sem
   lista, "validado" quer dizer só "vi e está certo".

- **A palavra:** "validado" por padrão; "aprovado" para a especificação. Combine na primeira
  entrega e anote em `docs/ESTADO.md`, em "Como trabalhamos aqui".
- **O que não é a palavra:** "ficou bom", "ok", "pode ser". Pergunte: "posso tratar como validado e
  seguir a lista?".

## 4. Avisar do risco, obedecer, registrar

1. **Avise uma vez**, antes de cumprir: o risco, para quem, e a alternativa
   (`assets/modelos/mensagens-ao-dono.md` §7).
2. **Se o dono mantiver, cumpra como pedido.** Versão diluída é decisão tomada no lugar dele.
3. **Registre quem decidiu** (`decisoes.py novo "<título>" --decidiu dono-contra`), com o aviso
   dado, o que não reintroduzir sem ele pedir e o primeiro ajuste se virar problema.

Pedido de ir mais rápido ou de gastar menos é outro caso: modo enxuto, e o piso fica
(`references/pesos.md` §6).

## 5. Não desfazer decisão registrada nem afrouxar regra

O que parece erro pode ser escolha. Quando a correção de um achado, de um teste ou de um plano
contraria um registro ou uma regra inegociável, não mexa em nenhum dos dois. Abra um item em "Para
decidir" com quatro partes: o problema (o comando e a saída, ou o arquivo e a linha); o que a
correção exige (que registro revê, que regra abre); o que ela não quebra; o que segue exposto.

Plano e revisão propõem; quem abre exceção é o dono. Quando ele disser sim, o registro novo cita a
autorização e diz qual registro revê (`references/decisoes.md` §5). Até lá, a regra vale.

## 6. As cinco listas abertas

Os itens moram só em `docs/ESTADO.md`: lista em dois lugares diverge na primeira atualização. O
roteiro guarda só corte de escopo com fase de destino. O registro de decisões guarda só o que é
permanente, e o item do estado cita o número do registro.

| Lista | De quem é | O que entra | Cada item traz |
| --- | --- | --- | --- |
| **Para decidir** | dono | decisão de produto; o que desfaz decisão registrada ou abre exceção a regra; inconsistência de produto | o problema, as opções e o risco de deixar como está |
| **Passos do dono** | dono | o que depende de painel, conta, credencial, dinheiro ou texto legal | o passo escrito para seguir sem o agente, e até quando é preciso |
| **Autorizações não dadas** | dono | ação que o agente sabe fazer e não faz sem o sim | a ação exata e o que fica parado sem ela |
| **Ficou para depois** | agente | o que foi adiado por prazo ou orçamento; degrau pendente; fluxo sem teste, pelo nome | a data de retomada |
| **Pendência aceita** | agente | risco conhecido, adiado de propósito | o que expõe, o cuidado até lá e o que fecha |

- Item sem dono, sem data ou sem o que dispara a retomada vira ruído: complete antes de gravar.
- Adiamento que voltar pela terceira vez deixa de ser do agente: vai para "Para decidir".

## 7. A autorização vale para a lista

- **A lista é o pedido:** o que será feito no ambiente remoto, na ordem, com o que não tem volta
  (`assets/modelos/mensagens-ao-dono.md` §8). Um sim autoriza a lista inteira; pedir um sim a cada
  passo devolve ao dono o trabalho que a lista poupa.
- **O sim não estica nem se guarda.** "Aplicar as migrações" não autoriza "inserir o
  administrador" nem "enviar um e-mail real", e não vale para a ida seguinte. O que aparecer no
  meio vira outro pedido, ou item de "Autorizações não dadas".
- **Depois de cada ação**, o estado diz o que foi feito "a pedido do dono", com a data.
- **Inconsistência de produto não se acerta em silêncio.** Um desconto que não fecha com o preço
  prometido na tela: registre a conta, com os números, e abra o item em "Para decidir".

## 8. Falar com quem nunca programou

| Perfil | Sinais | O que muda na fala |
| --- | --- | --- |
| Nunca programou (padrão) | descreve pelo que vê e pelo negócio; responde "não sei" a pergunta de ferramenta; pergunta o que é um arquivo | efeito antes do termo; um arquivo novo por vez, apresentado; roteiro com o endereço e o clique |
| Dev | usa o vocabulário técnico; cita arquivo, comando ou ferramenta; pede para ir direto | sem explicação de termo; relato com comando e saída; pergunta que pede o artefato |

O perfil muda a explicação, não o método: a lista, o roteiro de validação e os três blocos valem
nos dois. Anote o perfil em `docs/ESTADO.md`, em "Como trabalhamos aqui".

Arquivo novo se apresenta em uma frase, com o que o dono faz com ele. Termo do método se diz com a
frase abaixo, na primeira vez. O glossário traz só o que o método cria ou usa de modo próprio:

| Documento ou termo | Ao dono |
| --- | --- |
| `ESPECIFICACAO.md` | o combinado do que o produto faz e não faz; ele aprova uma vez |
| arquivo de instruções, `metodo.ini` | as regras e as verificações que o agente segue em toda conversa; ele não precisa abrir |
| `docs/ROTEIRO.md` | as fases, e o que prova que cada uma terminou |
| `docs/ESTADO.md` (estado) | a página que diz em que pé o projeto está hoje e o que depende dele |
| `docs/decisoes.md` (registro de decisão) | uma anotação numerada por escolha que pesa: a dúvida, o que foi escolhido e o que muda daí em diante |
| escada, degrau | as verificações automáticas, da mais rápida à mais demorada; cada uma é um degrau, e o relato diz até qual subiu |
| "Pronto quando" | a lista do que precisa ser verdade para uma fase valer como terminada |
| roteiro de validação | os passos do que abrir e do que deve aparecer, para conferir em cinco minutos |
| palavra de liberação | a resposta combinada que libera o passo seguinte: "validado" |
| migração | uma mudança na estrutura do banco, guardada em arquivo para ser repetida igual em produção |
| simulação | rodar o comando sem gravar nada, só para ler o que ele faria |
| dado restrito | o que nem toda pessoa pode ver: o pago, o pessoal, o de outro cliente |
| ambiente local, produção | a cópia que roda só na máquina dele, onde se testa; e o que as pessoas usam de verdade |

Qualquer outro termo: uma comparação com o negócio do dono, em uma oração ("teste é uma pergunta
que o computador faz ao produto toda vez, no lugar de quem confere"). Se pedir duas frases, troque
o termo pelo efeito.

Ensine na primeira entrega as três perguntas que o dono pode fazer no fim de toda mudança, e
responda-as no relato antes que ele faça: até que degrau da escada subiu? O que rodou e o que foi
só deduzido? Alguma coisa ficou vermelha, e por quê?

## O que evitar

- **O dono se surpreende, na validação, com algo que ninguém combinou.** Um padrão foi adotado e
  não foi dito. Cada padrão aparece em "Decidi sem perguntar", com como desfazer.
- **"Ficou ótimo" tratado como liberação.** O elogio não era a palavra combinada. Pergunte se pode
  seguir a lista. Não serve concluir que ele quis dizer "validado".
- **Valor inventado para não parar.** Contato de suporte, texto legal ou identificador que só o
  dono tem entrou como chute e ficou. Deixe a falta visível e pergunte na hora em que for preciso.

## Pronto quando

- [ ] Toda pergunta saiu com o padrão, e nenhuma rodada passou de cinco.
- [ ] O roteiro de validação tem de três a sete passos, um "não deve" e a lista do que vem depois.
- [ ] A palavra de liberação e o perfil do dono estão em `docs/ESTADO.md`.
- [ ] O que foi feito no ambiente remoto estava na lista autorizada, e o estado diz a data.
- [ ] Pedido contra a recomendação tem registro com quem decidiu.

Volte ao `SKILL.md`, §5.
