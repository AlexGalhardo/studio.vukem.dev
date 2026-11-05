---
name: auditoria-de-seguranca
description: Audita a segurança do aplicativo web do próprio dono e entrega um relatório em PDF com cada vulnerabilidade, onde está, o que alguém consegue fazer com ela, a gravidade e a correção. Começa pelo termo de escopo, percorre 14 áreas (dado de outro usuário, permissões no banco, rotas sem guarda, segredos, webhooks, entrada, upload, pagamento, sessão, cache, cabeçalhos, limite de tentativas, erros e dependências), comprova só em ambiente local ou de homologação com usuários de teste e gera o PDF por script sem dependência externa. Use sempre que o usuário disser "meu app pode ser hackeado?", "faz uma auditoria de segurança", "procura vulnerabilidades no meu site", "quero um relatório de segurança em PDF", "revisa a segurança antes de lançar" ou "tem chave vazando no código?", mesmo sem dizer auditoria. Não use para site ou sistema de terceiros, teste em produção, força bruta, negação de serviço nem código de ataque, e não a trate como teste de invasão profissional.
---

# Auditoria de segurança

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Funciona no Windows, no macOS e no Linux. No Windows, onde estiver `python3` use `py -3`.

`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono; `<auditoria>`, uma pasta
fora do repositório, onde ficam o termo, os achados e o relatório.

## Escopo e limites

Valem antes de abrir qualquer arquivo do projeto, e não mudam no meio da conversa.

- **Só o sistema de quem pede.** Código, configuração e ambiente local ou de homologação do
  próprio dono, com o termo de escopo confirmado por ele. Site ou sistema de terceiros: recuse.
- **Nada destrutivo.** Sem força bruta, negação de serviço, teste de carga nem varredura
  agressiva. Nenhum comando que apague ou altere dado que não seja de teste.
- **Produção fica fora.** Só entra com pedido explícito do dono, e só para leitura não
  destrutiva. A comprovação é local ou em homologação, com usuários de teste.
- **Prova mínima.** O bastante para mostrar que o problema existe. Sem extrair dado real, sem
  código de ataque que sirva de novo, sem técnica para escapar de detecção.
- **O relatório diz o que não cobre.** Esta skill não substitui um teste de invasão profissional
  e não garante ausência de falha.

O que perguntar, os sinais de que o sistema é de quem pede e quando parar: `references/escopo.md`.

## O método

- **Escopo antes de leitura.** O termo confirmado define o que se lê e o que se testa.
- **Três barreiras por recurso.** Privilégio no banco, regra por linha e guarda no aplicativo.
  Cada uma falha de um jeito, então confira as três.
- **Persona contra persona.** Toda prova é um usuário de teste pedindo o que é de outro, com um
  controle positivo ao lado.
- **Lido não é comprovado.** Cada achado diz "comprovado com teste" ou "encontrado na leitura".
- **Gravidade com critério.** O que o atacante consegue e o que ele precisa ter, escritos.

Funciona porque a maior parte das falhas de um aplicativo web é de autorização, e autorização só
se confere perguntando, recurso por recurso, quem pede e de quem é o dado. O teste antes de
escrever um achado: sei quem consegue o quê, a partir de onde, e como o dono confere a correção?

A ficha de áreas traz a pergunta de cada área e onde ler. Como cada falha aparece no código não
está nesta skill: está no OWASP ASVS, que é público, e nas skills irmãs.

## Preparar

```bash
python3 <skill>/scripts/varredura.py <projeto>
# → pontos "olhe:" e "nota:" por área. Saída 0 sem ponto, 1 com pontos, 2 uso, 3 nada lido
python3 <skill>/scripts/relatorio.py <skill>/assets/modelos/achados.json --saida <auditoria>
# → o relatório do exemplo fictício, em PDF e Markdown, para o dono ver o formato
```

- **Requisitos:** Python 3.8 ou mais novo, só biblioteca padrão; os scripts rodaram em macOS com
  Python 3.14 e não acessam a rede. Sem Python, o relatório sai em Markdown, escrito à mão na
  ordem de `references/relatorio.md` §1.
- **A varredura é leitura por texto.** Aponta onde olhar, não prova vulnerabilidade, e não achar
  não prova que não há. Não abre arquivo `.env` e nunca imprime o valor de uma chave.

## Onde o pedido está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Primeira auditoria | "meu app pode ser hackeado?" | passo 1 | `references/escopo.md` §1 |
| Antes de lançar | "posso lançar?" | passo 1, com as 14 áreas | `references/areas.md` |
| Já corrigiu | "corrigi, confere de novo" | passo 7 | `references/relatorio.md` §6 |
| Pedido fora do limite | site de outro, "derruba", "descobre a senha" | recuse e ofereça o que cabe | `references/escopo.md` §4 |
| Invasão em andamento | "acho que fui invadido" | pare: é resposta a incidente | `references/escopo.md` §7 |

## Fluxo

### 1. Feche o escopo e a autorização

Copie `assets/modelos/termo-de-escopo.md` para `<auditoria>`, preencha com os padrões e mostre ao
dono. Ele confirma ou corrige.
**Confira:** o termo diz o que entra, o que fica de fora, os ambientes e quem confirmou, com data.
**Pronto quando:** a confirmação do dono está escrita no termo. Sem ela, pare aqui.

### 2. Rode a varredura e monte o inventário

Rode `varredura.py` e guarde a saída em `<auditoria>`. Liste as personas do sistema (visitante,
logado, pagante, administrador) e complete o inventário de rotas e ações de servidor lendo as
pastas de rotas: o script perde o que não conhece.
**Confira:** a contagem do inventário bate com a das pastas de rotas do framework.
**Pronto quando:** cada rota e cada ação tem escrito quem pode chamar.

### 3. Leia por área

Percorra as 14 áreas de `references/areas.md`, na ordem. Em cada uma, leia o código que os pontos
da varredura indicam, responda à pergunta da ficha e anote os candidatos a achado.
**Confira:** toda área tem "olhei: o quê" ou "não se aplica: por quê".
**Pronto quando:** nenhuma área está em branco, e cada candidato tem arquivo e linha.

### 4. Comprove com segurança

Só em local ou homologação, com usuários de teste. Copie `assets/modelos/roteiro-de-comprovacao.md`
e preencha uma linha por prova: `references/comprovacao.md`.
**Confira:** toda prova negativa tem controle positivo, e nenhum dado real foi lido nem copiado.
**Pronto quando:** cada candidato virou "comprovado com teste", "encontrado na leitura" (com o
motivo de não ter sido reproduzido) ou "descartado" (com o trecho que impede a falha).

### 5. Escreva e classifique os achados

Copie `assets/modelos/achados-em-branco.json` para `<auditoria>/achados.json` e preencha um
achado por problema, com a gravidade tirada da tabela de `references/achado.md` §2.
**Confira:** `python3 <skill>/scripts/relatorio.py <auditoria>/achados.json --so-validar` sai 0.
**Pronto quando:** todo achado tem "consegue", "precisa", evidência, correção e esforço.

### 6. Gere o relatório e entregue

```bash
python3 <skill>/scripts/relatorio.py <auditoria>/achados.json
# → pronto: relatorio-de-seguranca-v1.pdf (N páginas) e .md. Saída 0 gerado, 1 recusado, 3 aviso
```

Abra o PDF e confira a capa, o resumo e a contagem: `references/relatorio.md` §5.
**Confira:** o resumo executivo cabe em uma página e os três riscos estão em linguagem de dono.
**Pronto quando:** o dono recebeu o caminho do PDF e, na conversa, a contagem por gravidade e os
três riscos principais. O relatório não entra no repositório.

### 7. Reconfira depois da correção

Para cada achado que o dono disser que corrigiu, repita a mesma prova do passo 4. Atualize
`situacao` e `reconferencia`, some 1 em `versao`, troque a data e gere de novo.
**Confira:** a prova que antes mostrava o problema agora mostra a recusa, e o controle positivo
continua passando.
**Pronto quando:** o relatório novo lista os corrigidos e reconferidos e os que seguem abertos.

## Regras inegociáveis

1. **Sem termo confirmado, não há leitura nem teste.** Se não, você audita o que não é de quem
   pede.
2. **Alvo de terceiros se recusa, mesmo "só para olhar".** Sondar sistema alheio sem autorização
   não é auditoria.
3. **Comprovação só em local ou homologação, com usuário e dado de teste.** Se não, a prova lê
   ou altera dado de gente de verdade.
4. **O que apaga ou altera se prova pelo privilégio, não pela execução.** Consulte a permissão
   em vez de rodar o comando: o privilégio já é a evidência.
5. **Valor de segredo nunca se repete.** Nem na conversa, nem no arquivo de achados, nem no
   relatório: escreva o tipo, o arquivo e a linha. Chave exposta, quem troca é o dono.
6. **Achado sem "consegue" e "precisa" não entra.** Sem os dois, a gravidade é palpite.
7. **Lido e comprovado não se misturam.** Se não, o dono corrige primeiro o que talvez nem
   exista.
8. **Comando que acessa a rede, só com o aval do dono.** A auditoria de dependências envia a
   lista de pacotes a um serviço externo.
9. **O relatório fica fora do repositório.** Ele é o mapa das falhas ainda abertas.

## Pare e pergunte ao dono

- **Só o dono faz:** confirmar o termo; trocar chave exposta; criar usuários de teste em
  homologação; qualquer ação em produção; aceitar um risco, com data; aplicar correção em banco
  remoto. Não peça valor de chave nem senha na conversa.
- **Pergunte antes:** rodar o comando de auditoria de dependências; fazer requisição a endereço
  que não seja local; o que conta como dado sensível no sistema; quais são as personas; para
  onde vai o relatório.

## Armadilhas já vistas

- **A regra por linha está certa, e o visitante esvazia a tabela.** O privilégio com que a tabela
  nasceu nunca foi retirado, e a regra por linha não filtra esse comando: área 2.
- **A página de administração está protegida, e a ação dela não.** A guarda ficou só na casca
  da área: área 3.
- **O depósito é público "só para a vitrine", e lista arquivo de item não publicado.** A regra
  do depósito governa a listagem, não o endereço: área 7.
- **A prova diz "não vazou", e a sessão de teste tinha vencido.** Todo mundo virou visitante.
  Controle positivo em toda prova: `references/comprovacao.md` §3.
- **Tudo virou crítico.** A gravidade foi dada pelo susto. Volte às duas perguntas:
  `references/achado.md` §2.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/escopo.md` | perguntas do termo, sinais de dono, o que cada ambiente permite, recusas, quando parar | passo 1; pedido que muda de alvo |
| `references/areas.md` | as 14 áreas, com a pergunta de cada uma, onde ler e onde buscar o detalhe | passos 2 e 3 |
| `references/comprovacao.md` | a forma da prova, controle positivo, evidência, quando não comprovar e quando parar | passos 4 e 7 |
| `references/achado.md` | os campos, a tabela de gravidade, esforço, redação, descartados | passo 5 |
| `references/relatorio.md` | as seções, o resumo de uma página, como gerar, conferir, entregar e reemitir | passos 6 e 7 |
| `assets/modelos/termo-de-escopo.md` | o texto que o dono confirma | passo 1 |
| `assets/modelos/roteiro-de-comprovacao.md` | a tabela das provas, com esperado, obtido e controle | passo 4 |
| `assets/modelos/achados-em-branco.json` | o arquivo de achados vazio, para preencher | passo 5 |
| `assets/modelos/achados.json` | exemplo fictício com 4 achados, de crítico a baixo | antes de escrever o primeiro achado |
| `scripts/varredura.py` | pontos para a leitura, por área, e inventário de rotas e ações; `--help` | passo 2 |
| `scripts/relatorio.py` | valida o arquivo de achados e gera o PDF e o Markdown; `--help` | passos 5, 6 e 7 |
