# Produção: como testar a cobrança e ligar o modo de verdade sem surpresa?

Leia quando: for montar os testes da cobrança, preparar os arquivos de ambiente ou responder
"posso ligar o Stripe em produção?" (passo 7 do fluxo).
Não é aqui: os casos de teste do manipulador (`references/webhook.md` §7).

## O mínimo

- O modo de teste e o de produção são duas contas lado a lado: chave, preço, cupom, endpoint de
  webhook e configuração do portal existem separados em cada um.
- Chave de produção mora só no painel da hospedagem. Não passa pela conversa, por arquivo nem
  pelo git.
- O aplicativo sobe e os testes automáticos passam sem nenhuma variável do Stripe.
- Quem cria objeto no painel e cola chave é o dono. O agente entrega a lista e confere depois.

Conteúdo: 1. Teste contra produção 2. Variáveis por ambiente 3. As camadas de teste 4. O endpoint
de webhook 5. A virada 6. O conferidor

## 1. Teste contra produção

| Existe separado em cada modo | Consequência |
| --- | --- |
| Chave secreta | o modo de uma chamada é o da chave usada |
| Produtos, preços, cupons e códigos promocionais | o id de um modo não existe no outro: cada ambiente tem os seus |
| Endpoint de webhook e o segredo dele | cada endpoint tem um segredo próprio |
| Configurações do portal | o código de achar ou criar roda uma vez em cada modo |
| Clientes e assinaturas | compra de teste nunca aparece em produção |

O erro típico de mistura é "esse objeto não existe": chave de um modo com id do outro.

## 2. Variáveis por ambiente

| Variável | O que é | Obrigatória |
| --- | --- | --- |
| `STRIPE_SECRET_KEY` | chave secreta | para vender |
| `STRIPE_WEBHOOK_SECRET` | segredo do endpoint de webhook | para gravar assinatura |
| `STRIPE_PRICE_PLAN` | id do preço recorrente | para vender |
| `STRIPE_PRICE_TRIAL` | id do preço avulso de entrada | não: em branco, checkout sem avaliação |
| `STRIPE_RETENTION_REF` | id do cupom ou do código promocional | não: em branco, sem oferta de desconto |

| Ambiente | Onde os valores moram | Quem preenche |
| --- | --- | --- |
| Local | arquivo de ambiente ignorado pelo git, com valores do modo de teste | o dono |
| Exemplo | arquivo rastreado, só com os nomes; valor de exemplo é `<SUA_CHAVE>` | o agente |
| Produção | painel da hospedagem | o dono |

- Leia as cinco em um módulo só de servidor. Variável em branco conta como ausente.
- Todas são opcionais para o aplicativo subir. Sem elas: a página de venda diz que a assinatura
  ainda não está disponível, e o webhook responde 500.
- Não abra o arquivo de ambiente para "conferir": o valor entra na conversa. Confira pelos nomes.
- Se o dono colar uma chave na conversa: não repita, peça a troca no painel do Stripe e siga com
  valor de teste. Trocar é passo dele.

## 3. As camadas de teste

| Camada | O que prova | Precisa de |
| --- | --- | --- |
| Funções puras | quem tem o plano, status gravado na pausa, valor com desconto, texto por duração | nada |
| Manipulador do webhook | os casos de `references/webhook.md` §7 | assinatura gerada pelo pacote; banco e API simulados |
| Ações | parâmetros da sessão, portão do formulário, guarda | API simulada |
| Banco | função de acesso com a mesma tabela de casos; usuário logado não escreve a assinatura | banco local |
| Fronteiras | só o webhook escreve; toda ação começa pela guarda; um módulo cria o cliente | só o código-fonte |
| Ponta a ponta | páginas de conta, venda e cancelamento, sem as chaves | aplicativo e banco locais |
| Manual, no modo de teste | o caminho inteiro com o Stripe de verdade | chaves de teste e o dono |

- **As duas pontas da função de acesso usam a mesma lista de casos.** Mudou a regra de um lado,
  o teste do outro quebra.
- **O ponta a ponta automático roda sem o Stripe.** Ele não prova o checkout hospedado. Diga isso
  no relato, em "não rodei".
- **O teste manual é um roteiro**, feito com o dono: comprar com um cartão de teste, ver
  `trialing` chegar, abrir o portal, pausar, retomar, responder o formulário, aceitar o desconto,
  cancelar, ver "acesso até a data". Números de cartão de teste, como avançar o tempo para ver o
  fim da avaliação e como receber webhook na máquina local: a conferir na documentação do Stripe.
  A ferramenta de linha de comando do Stripe usa um segredo de webhook próprio, diferente do
  segredo do endpoint do painel: também a conferir.

## 4. O endpoint de webhook

O dono cria um endpoint por ambiente, apontando para a rota do aplicativo, com estes eventos:

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
```

São os quatro que o manipulador trata. Eventos a mais custam chamadas e respondem 200 sem efeito.
Se o dono quiser avisar a pessoa de cobrança recusada ou do fim da avaliação, isso pede outros
eventos e outro manipulador: não misture com o que grava a assinatura.

## 5. A virada

Passos do dono, na ordem, cada um com o que conferir:

- [ ] Conta do Stripe ativada para receber em produção.
- [ ] Produto, preço recorrente e preço de entrada criados no modo de produção.
- [ ] Cupom ou código promocional de retenção criado no modo de produção, se houver oferta.
- [ ] Endpoint de webhook de produção criado, com os quatro eventos.
- [ ] As cinco variáveis coladas no painel da hospedagem, no ambiente de produção.
- [ ] Nova implantação feita depois de colar as variáveis.

Passos do agente:

- [ ] Migração das tabelas aplicada no banco de produção, com a autorização do dono para essa
      lista.
- [ ] Conferidor com saída 0 (§6) e teste de fronteira verde.
- [ ] Arquivo de exemplo de ambiente com os cinco nomes e nenhum valor.

Depois da virada, com o dono:

- [ ] Uma compra de verdade, com o cartão dele. No painel do Stripe, o endpoint mostra as
      entregas com resposta 200.
- [ ] A linha dele na tabela de assinatura tem o status certo, e o acesso abriu sem recarregar.
- [ ] O portal abre, e a configuração de gerenciar não oferece cancelamento, se há formulário.
- [ ] Ele cancela ou estorna a compra de verificação, e o estado novo chega pelo webhook.

Compra, estorno e cancelamento de verdade são atos do dono. O agente não paga, não estorna e não
chama a API do Stripe com chave de produção.

## 6. O conferidor

```bash
python3 <skill>/scripts/conferir.py <projeto> --tabela subscriptions --modulo features/billing/webhook.ts
# → linhas "acusa:", "aviso:", "ok:" e "não conferi:", um resumo e os limites
```

| Saída | Significa | O que fazer |
| --- | --- | --- |
| 0 | nada acusado, tudo conferido | seguir |
| 1 | há "acusa:" | corrigir antes de enviar; chave acusada se troca no painel, além de sair do arquivo |
| 2 | uso errado | corrigir o comando |
| 3 | nada acusado, mas algo não foi conferido | passar a opção que faltou, ou conferir à mão e dizer isso no relato |

Ele lê o texto dos arquivos. Não segue imports, não olha o histórico do git, não entende a escrita
feita por ORM e não substitui o teste de fronteira, que roda junto dos testes do projeto. Valor de
mentira com formato de chave, em arquivo de teste, é acusado: troque por um valor curto.

## O que evitar

- **Testar em produção "só uma vez" com chave de produção no arquivo local.** O arquivo local é o
  que as ferramentas carregam sozinhas.
- **Usar o mesmo endpoint para os dois modos.** Evento de teste chega com usuário que não existe
  em produção.
- **Copiar id de preço de um modo para o outro.** Cada ambiente tem os seus.
- **Dizer "testado" sem dizer em que camada.** O relato separa o que rodou do que foi lido.
