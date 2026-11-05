---
name: assinatura-com-stripe
description: Monta e revisa assinatura paga com Stripe em qualquer backend, do checkout à ida a produção. Entrega checkout com teste pago e período de avaliação, webhook como único escritor do estado da assinatura, uma função de acesso espelhada no banco e no aplicativo, portal do cliente, pausa e retomada, cancelamento com formulário e oferta de retenção, testes de fronteira e checklist de virada, com moldes em TypeScript e Postgres e um conferidor que só lê o projeto. Use sempre que o usuário quiser cobrar mensalidade, criar plano pago, paywall ou área de assinante, ou disser "integra o Stripe", "quero cobrar assinatura", "teste de 7 dias", "o webhook não funciona", "paguei e não liberou o acesso", "pausar a assinatura", "tela de cancelar", "cupom de retenção" ou "posso ligar o Stripe em produção", mesmo sem dizer assinatura. Não use para pagamento avulso sem recorrência, marketplace com repasse entre contas, nota fiscal ou imposto, nem para outro provedor de pagamento.
---

# Assinatura com Stripe

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Funciona no Windows, no macOS e no Linux. No Windows, onde estiver `python3` use `py -3`.

`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono.

- **Um escritor só.** Só o webhook grava o estado da assinatura. As ações da pessoa mudam o
  Stripe e esperam por ele.
- **O evento avisa, o Stripe responde.** O evento diz qual assinatura mudou. O que se grava é o
  estado atual, lido na API.
- **Uma função decide o acesso.** A mesma regra no banco e no aplicativo, com os mesmos casos de
  teste nas duas pontas.
- **Nenhum valor no código.** Preço, desconto e duração são lidos do Stripe.
- **O painel e a chave de produção são do dono.** O agente escreve o código e os testes.

Funciona porque quem confirma o pagamento é quem cobra: a tela de volta do checkout pode ser
aberta por quem não pagou, e o webhook assinado não. O teste antes de agir: sei quem escreve a
assinatura, de onde vem o estado e qual função libera o acesso?

Os moldes de `assets/moldes/` são TypeScript e Postgres, saídos de um sistema em produção, com os
nomes trocados. Passaram pelo verificador de tipos com a versão 23 do pacote `stripe`; o SQL rodou
em Postgres 18 e o teste de fronteira, em Vitest. Nenhum foi executado contra uma conta do Stripe:
adapte, rode os testes do projeto e confira no modo de teste. Em outra linguagem, banco ou versão
do pacote, copie a ordem das decisões e confira os nomes de parâmetro nos tipos instalados. O que
está marcado "a conferir na documentação do Stripe" não foi verificado. Cobre um plano por pessoa:
troca de plano, vários assentos e cobrança por uso ficam de fora.

## Preparar

1. Leia o que o projeto já tem: a guarda de usuário, o cliente do banco com a chave de serviço, o
   módulo que lê segredos e a versão instalada do pacote do Stripe.
2. Rode o conferidor, que só lê:

   ```bash
   python3 <skill>/scripts/conferir.py <projeto> --tabela <tabela> --modulo <arquivo do webhook>
   # → "acusa:", "aviso:", "ok:", "não conferi:". Saída 0 limpo, 1 acusou, 2 uso, 3 incompleto
   ```

3. Entregue ao dono a lista do que só ele faz (seção "Pare e pergunte ao dono").

- **Requisitos:** Python 3.8 ou mais novo, só para o conferidor. Ele rodou em macOS com Python
  3.14. Sem Python, faça à mão as três conferências do cabeçalho do script.
- **Projeto sem cobrança:** rode sem `--tabela` e `--modulo`; a saída 3 é esperada. **Projeto que
  já cobra:** nada é alterado; trate como revisão e comece pela tabela abaixo.

## Onde o projeto está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Sem cobrança | não há tabela de assinatura nem rota de webhook | passo 1 | `references/checkout.md` §1 |
| Acesso liberado sem webhook | a tela de volta ou uma ação grava "ativo" | passo 3 | `references/webhook.md` |
| Cobra, falta a conta | não há portal, pausa nem caminho para cancelar | passo 5 | `references/portal.md` |
| O dono quer reter quem sai | pedido de formulário, desconto ou pausa | passo 6 | `references/cancelamento.md` |
| Vai ligar de verdade | "posso ligar em produção?" | passo 7 | `references/producao.md` §5 |
| Algo quebrou | "paguei e não liberou", evento com erro | "Armadilhas já vistas" | a ficha citada no sintoma |

## Fluxo

### 1. Combine com o dono o que será vendido

Pergunte, já com o padrão: o plano e o intervalo; se há teste pago, o valor de entrada e os dias
(padrão: 7); quem recebe o teste (padrão: só quem nunca assinou); o que a pausa faz com o acesso
(padrão: sem cobrança e sem acesso); se cancelar terá formulário (padrão: não). Entregue a lista do
que ele cria no painel: `references/checkout.md` §1.
**Confira:** cada variável de `references/producao.md` §2 tem dono e lugar.
**Pronto quando:** o arquivo de exemplo de ambiente lista os nomes, sem nenhum valor.

### 2. Crie as tabelas e a função de acesso

Copie `assets/moldes/tabelas.sql` para uma migração nova e `assets/moldes/acesso.ts` para o módulo
de cobrança. Uma linha por pessoa; cliente e assinatura do Stripe únicos; a pessoa lê só a própria
linha; usuário logado não tem permissão de escrita.
**Confira:** no banco local, logado como usuário comum, um `update` na tabela é recusado.
**Pronto quando:** o teste do banco e o do aplicativo passam com a mesma lista de casos de acesso.

### 3. Escreva o webhook

Parta de `assets/moldes/webhook.ts`. A rota só lê o corpo cru e repassa. A ordem dentro do
manipulador: conferir a assinatura, filtrar o tipo, consultar o evento já visto, buscar o estado
atual, gravar, marcar o evento. Detalhes e respostas por caso: `references/webhook.md`.
**Confira:** os casos da §7 dessa ficha, com assinatura de teste gerada pelo próprio pacote.
**Pronto quando:** assinatura errada dá 400 sem tocar o banco, evento repetido dá 200 sem
regravar, e falha de gravação dá 500 sem marcar o evento.

### 4. Abra o checkout

Parta de `assets/moldes/checkout.ts`. A ação começa pela guarda de usuário, manda para a conta
quem já tem assinatura viva e identifica a pessoa em dois lugares da sessão. A tela de volta
espera o webhook: `references/checkout.md` §3 e §4.
**Confira:** o teste da ação cobre nunca assinou, já assinou e bloqueado.
**Pronto quando:** no modo de teste, com o dono, a compra termina em `trialing` gravado pelo
webhook e a tela libera sozinha.

### 5. Monte a conta: portal, pausa e retomada

Parta de `assets/moldes/portal.ts`: `references/portal.md`. Pergunte ao dono antes de decidir o
que a pausa faz com o acesso.
**Confira:** pausar e retomar não escrevem na tabela; a página espera o webhook.
**Pronto quando:** `paused` tira o acesso e retomar devolve, os dois gravados pelo webhook.

### 6. Cancelamento com formulário e retenção (só se o dono pediu)

Avise o risco uma vez e registre a decisão: `references/cancelamento.md` §1. A obrigatoriedade
mora no servidor, em um portão que as três ações seguintes atravessam.
**Confira:** chamar aceitar desconto, pausar e seguir para cancelar sem resposta gravada devolve
erro, e nenhuma chamada ao Stripe acontece.
**Pronto quando:** o texto da oferta muda sozinho ao trocar o cupom no modo de teste.

### 7. Prenda as regras e vá a produção

Copie `assets/moldes/fronteira.test.ts`, ajuste as constantes e ligue aos testes do projeto. Siga
a virada de `references/producao.md` §5: os passos do dono, depois os seus.
**Confira:** `conferir.py` sai com 0 e o teste de fronteira falha quando você escreve na tabela
fora do webhook de propósito.
**Pronto quando:** uma compra de verdade, feita pelo dono, chega pelo webhook com resposta 200.

## Regras inegociáveis

1. **Só o webhook escreve na tabela de assinatura.** Tire a permissão de escrita do usuário logado
   e prenda com o teste de fronteira. Se não, uma ação apressada dá o plano a quem não pagou.
2. **A assinatura do webhook é conferida sobre o corpo cru, antes de qualquer leitura.** Se não,
   quem descobrir o endereço da rota dá o plano a si mesmo.
3. **Grave o estado atual do Stripe, nunca o retrato do evento.** Se não, um reenvio antigo
   desfaz um estado mais novo.
4. **O id do evento é marcado depois de gravar, e falha responde 500.** Se marcar antes, um erro
   no meio perde o evento para sempre.
5. **Toda ação de cobrança começa pela guarda de usuário e usa os ids da linha da própria
   pessoa.** Se o id vier do navegador, uma pessoa pausa ou cancela a assinatura de outra.
6. **O acesso sai de uma função só.** Tela, ação e webhook perguntam a ela. Se não, a tela libera
   o que o banco nega.
7. **Chave, preço e cupom vêm de variável de ambiente, lidas em um módulo só.** Chave de produção
   mora no painel da hospedagem. Se não, vaza pelo histórico do git, que não se apaga.
8. **Regra de fluxo vale no servidor.** O formulário obrigatório é um portão dentro das ações. Se
   valer só na tela, uma chamada direta passa por fora.

## Pare e pergunte ao dono

- **Só o dono faz**, com o passo escrito para ele: criar produto, preço, cupom e código
  promocional; criar o endpoint de webhook; colar chave e segredo no painel da hospedagem; trocar
  chave exposta; comprar, estornar e cancelar de verdade. Não peça o valor de chave na conversa.
- **Pergunte antes:** valor e dias do teste; quem tem direito a ele; o que a pausa faz com o
  acesso; formulário obrigatório; o texto de qualquer oferta; aplicar migração no banco remoto;
  qualquer chamada à API do Stripe fora do modo de teste.

## Armadilhas já vistas

- **"Paguei e continuo sem acesso", logo depois do checkout.** A pessoa voltou antes do webhook.
  Marca no endereço de volta e espera de 2 em 2 segundos, até 30: `references/checkout.md` §4.
- **Toda entrega do webhook dá 400.** O corpo passou por um parser de JSON antes da conferência,
  ou o segredo é de outro endpoint ou de outro modo: `references/webhook.md` §1 e §2.
- **O acesso some e volta, ou o status regride.** Foi gravado o retrato do evento, e os eventos
  chegaram fora de ordem: `references/webhook.md` §4.
- **A pessoa pausou e continua com acesso.** No Stripe a pausa da cobrança não muda o status. A
  tradução é do webhook: `references/portal.md` §3.
- **"Fim do período" vem vazio.** Nas versões novas da API o campo fica no item da assinatura:
  `references/webhook.md` §5.
- **A mesma pessoa tem duas assinaturas.** Um checkout novo foi aberto para quem tinha cobrança
  pendente. Bloqueie pelo status: `references/checkout.md` §3.
- **O mesmo evento falha para sempre.** Usuário que não existe, vindo de outro ambiente. Responda
  200 e registre: `references/webhook.md` §6.
- **A oferta promete "para sempre" e desconta uma vez.** Texto fixo. Leia a duração do cupom:
  `references/cancelamento.md` §4.
- **Cancelaram pelo portal, sem responder nada.** O botão de gerenciar abriu a configuração padrão
  do painel: `references/portal.md` §1.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/checkout.md` | o que o dono cria, teste pago, a ação, a volta, preço na tela | passos 1 e 4 |
| `references/webhook.md` | rota, assinatura, idempotência, fora de ordem, mapa de evento e status, casos de teste | passo 3; qualquer sintoma de acesso |
| `references/portal.md` | duas configurações, qual abrir, pausa e retomada, textos da conta | passo 5 |
| `references/cancelamento.md` | aviso ao dono, portão, formulário, cupom e código promocional, painel de motivos | passo 6 |
| `references/producao.md` | modos, variáveis, camadas de teste, eventos do endpoint, virada, conferidor | passos 1 e 7 |
| `assets/moldes/tabelas.sql` | tabelas de assinatura, de eventos e de respostas; função de acesso; permissões | passo 2 |
| `assets/moldes/acesso.ts` | quem tem o plano, quem bloqueia checkout, quem pode cancelar, status na pausa | passo 2 |
| `assets/moldes/webhook.ts` | o manipulador, com a camada de banco em uma interface | passo 3 |
| `assets/moldes/checkout.ts` | criação da sessão com teste pago e avaliação | passo 4 |
| `assets/moldes/portal.ts` | configurações do portal, tela de cancelar, pausa, retomada, desconto | passos 5 e 6 |
| `assets/moldes/fronteira.test.ts` | três regras de arquitetura lidas do código-fonte | passo 7 |
| `scripts/conferir.py` | chave em arquivo, escrita fora do webhook, webhook sem conferência; `--help` | antes de começar e antes de enviar |
