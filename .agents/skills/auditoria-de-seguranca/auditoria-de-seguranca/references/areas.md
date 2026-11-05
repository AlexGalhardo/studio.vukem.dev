# Áreas: a pergunta que cada uma responde

**Leia quando:** passos 2 e 3 do fluxo, ou quando o dono pedir uma área só.
**Não é aqui:** como comprovar (`references/comprovacao.md`), como escrever o achado
(`references/achado.md`).

## O mínimo

Esta ficha é um índice: diz o que perguntar e onde ler, não como explorar. O detalhe de cada área
está em padrão público (seção 3) e nas skills irmãs. Toda área termina com uma de duas anotações:
"olhei: o quê" ou "não se aplica: por quê". Área em branco não existe.

## 1. As 14 áreas

| # | Área | A pergunta | Onde ler |
| --- | --- | --- | --- |
| 1 | Acesso a dado de outro usuário | Toda rota, ação e consulta confere quem pede e de quem é o dado? | o que recebe um identificador vindo de fora |
| 2 | Permissões no banco | O que cada papel pode fazer em cada tabela, além de ler? | migrações, regras por linha, funções com privilégio |
| 3 | Rotas e ações sem guarda | A checagem está em cada rota e ação, ou só na casca da página? | o inventário do passo 2 |
| 4 | Segredos | Há chave em arquivo rastreado, no histórico, em variável pública ou em log? | a saída da varredura e a configuração de ambiente |
| 5 | Webhooks | Quem chama prova quem é antes de qualquer efeito? | as rotas que recebem chamada de outro serviço |
| 6 | Entrada | O que vem de fora é validado antes de chegar a banco, arquivo, comando, endereço ou página? | os pontos "entrada" da varredura |
| 7 | Upload e arquivos | Quem envia, o quê, de que tamanho, e quem lista ou baixa depois? | regras do depósito e a geração de link |
| 8 | Pagamento | Preço, plano e estado da assinatura vêm do servidor e do provedor, e não do cliente? | início da cobrança e quem grava o estado |
| 9 | Sessão e cookies | A sessão expira, é renovada no servidor e o cookie leva as proteções? | a criação e a renovação da sessão |
| 10 | Cache | Algo que depende de quem pede foi para cache compartilhado? | leituras em cache e o que elas leem |
| 11 | Cabeçalhos e origens | Que origens podem chamar a API e que cabeçalhos de proteção a resposta leva? | configuração do servidor e das rotas |
| 12 | Limite de tentativas | Login, envio de código e formulário público têm limite por pessoa e por origem? | as rotas públicas que disparam e-mail ou conferem código |
| 13 | Erros e arquivos publicados | A mensagem de erro e o que é publicado revelam mais do que o usuário precisa? | tratamento de erro e a configuração do build |
| 14 | Dependências | Há pacote com falha conhecida? | o comando de auditoria do gerenciador, só com o aval do dono |

Percorra na ordem. As áreas 1 a 3 concentram a maior parte dos problemas de um aplicativo web,
porque são de autorização: gaste nelas a maior parte do tempo.

## 2. Como registrar o que foi olhado

Uma linha por área em `<auditoria>/areas.md`, no formato:

```
3 · Rotas e ações sem guarda · olhei: as 22 ações de servidor do inventário · candidatos: 2
9 · Sessão e cookies · não se aplica: o sistema não tem login
```

Candidato a achado leva arquivo e linha, ou a rota. Sem endereço, não é candidato: é impressão.

## 3. Onde buscar o detalhe

- **Padrão público.** O OWASP ASVS traz, por capítulo, os requisitos verificáveis de cada área, e
  o OWASP Top 10 dá o nome corrente de cada categoria. Cite a categoria no achado quando ajudar o
  dono a pesquisar. Confira a versão vigente dos dois: os capítulos mudam de número.
- **Skills irmãs.** `app-com-supabase` para as áreas 2, 7 e 9 nesse provedor;
  `assinatura-com-stripe` para 5 e 8; `nextjs-boas-praticas` para 3, 4 e 10 nesse framework;
  `vazamento-de-paywall` para conteúdo pago nas áreas 1 e 10. Elas trazem o molde da correção.
- **O que a varredura cobre.** `scripts/varredura.py` aponta lugares nas áreas 3, 4, 5, 6, 7, 9,
  10, 11, 12, 13 e 14. Nas áreas 1, 2 e 8 ela ajuda pouco: a resposta depende de ler a regra do
  negócio.

## O que evitar

- **Parar na varredura.** Ela lê texto e conhece poucos padrões; não achar não prova que não há.
- **Marcar "não se aplica" sem motivo.** O motivo é o que o dono confere.
- **Tratar a lista como completa.** São as áreas vistas em aplicativo web com login, banco e
  pagamento. Sistema com outra forma (aplicativo móvel, integração entre empresas) tem áreas que
  não estão aqui: diga isso no relatório.

Volte ao `SKILL.md`, passo 4.
