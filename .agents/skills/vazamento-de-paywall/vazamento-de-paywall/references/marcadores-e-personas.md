# Marcadores e personas: o que plantar nos dados de exemplo e quem vai pedir?

Leia quando: for preparar os dados de exemplo e as sessões de teste (passos 2 e 4 do fluxo), ou
quando o teste passar com todo mundo virando visitante.
Não é aqui: escrever o teste (`references/resposta-crua.md`).

## O mínimo

- Cada corpo pago dos dados de exemplo leva um marcador na primeira linha e outro na última.
- O marcador não aparece em nenhum outro campo: nem título, nem resumo, nem endereço.
- Há pelo menos 2 itens pagos, 1 livre e 1 rascunho, todos com marcador.
- Cada persona é uma conta de identificador fixo; o visitante é a sessão vazia.
- A sessão de cada persona é gerada sem tela, com a biblioteca de sessão do próprio produto.

Conteúdo: 1. O formato 2. Onde plantar 3. Conteúdo que não aceita texto 4. As personas
5. Sessão sem tela 6. Os dados de exemplo ficam no local

## 1. O formato

`<CLASSE>-<PONTA>-<6 caracteres>`, por exemplo `PAGO-INICIO-R3NM3R` e `PAGO-FIM-DTVAV3`.

| Parte | Regra | Por quê |
| --- | --- | --- |
| Classe | `PAGO`, `LIVRE` ou `RASCUNHO` | o teste proíbe a classe inteira, e pega o marcador que a lista dele ainda não conhece |
| Ponta | `INICIO` na primeira linha, `FIM` na última | vazamento parcial traz uma ponta só: a prévia de 200 caracteres, o começo; o trecho citado, o fim |
| Final | 6 caracteres sorteados, um par por item | a falha diz qual item vazou, e o texto não casa com nada escrito por gente |
| Alfabeto | só maiúsculas, dígitos e hífen | passa igual por HTML, JSON e endereço, sem escape |

Sorteie; marcador inventado à mão se repete:

```bash
python3 -c "import secrets; print(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)))"
```

## 2. Onde plantar

O molde é `assets/moldes/dados-de-exemplo.sql`. O que ele precisa ter:

| O quê | Quantos | Para quê |
| --- | --- | --- |
| Item pago publicado | 2 ou mais | um é "a página de outro item" para o outro: relacionados e listagens vazam assim |
| Item livre publicado | 1 | controle positivo: o visitante tem de receber as duas pontas |
| Item em rascunho | 1 | ninguém recebe em rota pública, nem quem paga |
| Versão nova em rascunho de item publicado | 1, se o produto tem versões | a versão antiga aparece, a nova não |
| Um pago de cada tipo vendido | 1 por tipo | texto, arquivo e vídeo saem por caminhos diferentes |

- Escreva a tabela de marcadores no cabeçalho do arquivo: item, classe e as duas pontas. É a
  lista que o teste confere contra a dele.
- Dê ao corpo de exemplo o tamanho e o formato do conteúdo de verdade. Corpo de uma linha não
  passa pelo corte de prévia nem pela conversão de formato que o conteúdo real atravessa.
- Marcador repetido no título ou no resumo aparece para todo mundo e o teste acusa vazamento que
  não existe. Confira com uma busca: cada marcador ocorre 1 vez no corpo e 1 vez no cabeçalho.

## 3. Conteúdo que não aceita texto

**Base:** adaptação. O método foi praticado com texto; o que está nesta seção não foi.

| Conteúdo pago | O que procurar |
| --- | --- |
| Arquivo (PDF, zip, vídeo) | o nome do repositório privado e o nome da coluna do caminho não aparecem em resposta nenhuma; o endereço público do arquivo responde 4xx (`references/camadas.md` §4) |
| Campo com formato (telefone, documento) | um valor sentinela por registro, e também a forma sem pontuação |
| Número ou sim e não | o nome do campo ausente na resposta de quem não pode e presente na de quem pode. Isso não prova que o valor não foi derivado para outro campo, como um selo |

## 4. As personas

| Persona | Como existe nos dados de exemplo | Recebe | Prova de que é ela |
| --- | --- | --- | --- |
| Visitante | não existe: sessão vazia | só `LIVRE` | o botão de entrar, e não o de sair |
| Logado sem plano | conta fixa, sem linha de assinatura | só `LIVRE` | o botão de sair |
| Assinante | conta fixa e uma linha de assinatura ativa | `PAGO` e `LIVRE` | o conteúdo pago chega |
| Admin | conta fixa com o papel de admin | `PAGO` e `LIVRE` | o conteúdo pago chega |

- A assinante é assinante porque os dados de exemplo gravam a linha de assinatura. Em produção
  quem grava é o aviso do provedor de pagamento; no teste, os dados de exemplo fazem esse papel.
- **Ex-assinante** (assinatura cancelada, vencida ou pausada) é a quinta persona de todo produto
  que cobra por mês. Entra no bloco "sem acesso". O molde de banco já a traz; no teste de ponta a
  ponta ela é uma linha a mais em `CONTAS` e em `SEM_ACESSO` (adaptação: não foi praticada lá).
- A prova da persona existe porque sessão gravada vence. Sem ela, todo mundo vira visitante, o
  bloco "logado sem plano" passa pelo motivo errado e o controle positivo é o único que reclama.

## 5. Sessão sem tela

O molde é `assets/moldes/personas.ts`.

1. Um passo de preparo roda antes de todos os testes e grava um arquivo de sessão por persona.
2. Para cada conta, ele gera uma credencial de uso único pela interface de administração do
   login e a troca por sessão com a mesma biblioteca que o produto usa. Cookie montado à mão
   quebra no dia em que a biblioteca muda o formato.
3. A função que lê as variáveis recusa banco que não seja local. O preparo cria sessões: apontado
   para produção, cria sessão de verdade.
4. Os arquivos de sessão ficam numa pasta que o git ignora. São credenciais.
5. O login pela tela tem um teste próprio, uma vez. Passar por ele em todo teste é lento, e criar
   uma rota de login de teste no produto abre uma porta em produção.

Token no cabeçalho em vez de cookie: o preparo emite o token com a chave de teste e o teste o
envia. O resto não muda. Para montar personas em detalhe (dados que o teste cria, dois tamanhos
de tela, limpeza de sobras), a skill irmã é `ponta-a-ponta-com-personas`, ainda por sair.

## 6. Os dados de exemplo ficam no local

- O arquivo de dados de exemplo nunca roda em produção. Lá não há marcador: a conferência por
  fora usa outro meio (`references/onde-vaza.md` §3).
- Conteúdo de exemplo é inventado. Texto pago de verdade nos dados de exemplo vai para o
  repositório, e o repositório tem mais leitores que a área paga.

## O que evitar

- **Marcador igual em dois itens.** A falha não diz qual vazou.
- **Um item pago só.** Não existe "página de outro item", e o vazamento por relacionados passa.
- **Persona sem conta fixa, criada pelo teste.** Dois testes ao mesmo tempo brigam pela conta.
- **Sessão gravada no repositório.** É credencial, e vence: o próximo a rodar testa como visitante.
- **Pular o item livre.** Sem o controle positivo, teste cego e teste limpo ficam iguais.
