# Comprovação: confirmar sem causar dano

**Leia quando:** passo 4 (comprovar) e passo 7 (reconferir depois da correção).
**Não é aqui:** o que cada ambiente permite (`references/escopo.md` §3), a redação do achado
(`references/achado.md`).

## O mínimo

Comprovar é mostrar, com usuário e dado de teste, que o sistema responde o que não deveria. Só em
ambiente local ou de homologação do dono. A prova para no primeiro sinal de que o problema existe:
ninguém extrai dado, altera registro de verdade nem repete a tentativa para "ver até onde vai".

## 1. Antes de qualquer prova

- O termo de escopo está confirmado e lista o ambiente onde a prova roda.
- Existem usuários de teste, um por tipo (visitante, logado, pagante, administrador), e dados de
  exemplo que são de cada um. Em homologação, quem cria é o dono.
- O ambiente não aponta para o banco de produção. Confira o endereço antes, não depois.

## 2. A forma de toda prova

Uma linha do roteiro (`assets/modelos/roteiro-de-comprovacao.md`) por prova:

1. **Quem pede:** qual usuário de teste.
2. **O que pede:** o recurso, e de quem ele é.
3. **O esperado:** recusa, zero linhas ou redirecionamento para o login.
4. **O obtido:** o que o sistema respondeu de fato.
5. **O controle:** o dono legítimo pedindo a mesma coisa, que tem de funcionar.

## 3. Controle positivo em toda prova

Uma recusa só vale se, na mesma rodada, o usuário certo conseguiu. Sem o controle, "não vazou"
pode ser sessão vencida, rota errada ou ambiente fora do ar, e a auditoria aprova o que não testou.

## 4. Leia o estado depois

Uma escrita barrada pode não devolver erro: ela simplesmente não altera nada. Depois de toda
tentativa de escrita com usuário de teste, leia o registro e compare com o que havia antes.

## 5. O que apaga se prova pela permissão

Para comando que apaga ou altera em massa, a evidência é a resposta do banco à pergunta "este
papel tem este privilégio?", e não a execução do comando. O privilégio já é o problema.

## 6. O que guardar como evidência

- Guarde: a data, o ambiente, o usuário de teste, o pedido em palavras, a resposta resumida
  (código de resposta, contagem de linhas, o nome do campo que apareceu) e o arquivo e a linha.
- Não guarde: conteúdo de registro real, valor de chave ou de sessão, senha, dado pessoal.
- A evidência vai para `<auditoria>`, fora do repositório.

## 7. Quando não comprovar

Marque "encontrado na leitura", com o motivo, quando: o ambiente de teste não existe; a prova
exigiria dado real, produção ou serviço de terceiro; ou a única forma de mostrar seria destrutiva.
Achado só lido entra no relatório com esse estado, e o dono decide se quer o ambiente para provar.

## 8. Pare na hora

Pare e avise o dono se: apareceu dado de pessoa de verdade; o ambiente era produção; a prova
alterou algo que não era de teste; ou surgiu sinal de que outra pessoa já explorou a falha (isso
é incidente, não auditoria: `references/escopo.md` §7).

## O que evitar

- **Provar em produção "só para confirmar".** A confirmação lê ou altera dado de gente de verdade.
- **Repetir a tentativa em volume.** Uma resposta basta; insistir vira carga sobre o sistema.
- **Guardar o que apareceu.** O relatório descreve o que vaza, e nunca reproduz o vazado.

Volte ao `SKILL.md`, passo 5.
