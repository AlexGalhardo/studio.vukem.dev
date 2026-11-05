# Termo de escopo da auditoria de segurança

> Preencha com o dono e peça a confirmação por escrito. Sem ela, a auditoria não começa.

**Sistema:** {{nome do sistema}}
**Quem pede e responde pelo sistema:** {{nome}}
**Data:** {{dd/mm/aaaa}}

## O que entra

- Código e configuração do repositório: {{caminho ou endereço do repositório}}
- Ambientes onde se pode testar: {{local | homologação em <endereço>}}
- Áreas: {{as 14 | só estas: …}}

## O que fica de fora

- Produção: {{fora | só leitura não destrutiva, pedida aqui pelo dono}}
- Serviços de terceiros usados pelo sistema (pagamento, e-mail, hospedagem): só a configuração do
  lado do sistema; o serviço em si não é testado.
- {{outros itens que o dono quiser excluir}}

## O que não se faz em nenhum caso

Força bruta, negação de serviço, teste de carga, varredura agressiva, leitura ou cópia de dado de
pessoa de verdade, código de ataque reutilizável, e qualquer teste em sistema que não seja o
descrito acima.

## Usuários e dados de teste

| Tipo | Identificação do usuário de teste | Quem criou |
| --- | --- | --- |
| visitante | sem conta | não se aplica |
| logado | {{…}} | {{…}} |
| pagante | {{…}} | {{…}} |
| administrador | {{…}} | {{…}} |

## Para onde vai o relatório

{{pasta fora do repositório}} · {{quem pode ver}}

## Confirmação

"Confirmo que o sistema acima é meu ou está sob minha responsabilidade, e autorizo a auditoria
dentro deste escopo." {{nome}}, {{data}}
