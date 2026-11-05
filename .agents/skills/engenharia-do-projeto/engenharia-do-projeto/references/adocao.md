# Adoção: como entrar com o método num projeto que já tem código?

Leia quando: situação B.
Não é aqui: projeto que já tem os documentos e só mudou de sessão (`references/retomada.md`).
**Base:** adaptação. O método foi praticado numa aplicação web com banco relacional; o que está
aqui ainda não foi praticado. Confira antes de confiar.

## O mínimo

- Só leitura primeiro: nada é criado, alterado nem commitado antes do levantamento.
- Antes de rodar qualquer comando do projeto, olhe a linha `ambiente:` do diagnóstico. Se algum
  destino não é local, não rode nada que leia aquele arquivo.
- Atenda o pedido do dono: a adoção acompanha o pedido, não o substitui.
- Ofereça o mínimo do método como pergunta, com o padrão (até quatro arquivos novos; nada do que
  existe muda) e com a alternativa (seguir sem gravar nada: o piso se cumpre à mão, e o estado é
  dito na conversa).
- Não renomeie nada: mapeie em `metodo.ini`.
- Antes do primeiro commit de código, degraus 0 a 2 e `[zonas]` preenchidos.
- Nada de refatorar na primeira sessão: sem teste, não há como mostrar que nada quebrou.

Conteúdo: 1. O levantamento na adoção 2. Para onde o ambiente aponta 3. Mapear os documentos
4. Oferecer o mínimo 5. A primeira escada e as zonas 6. Contradições 7. O que muda para o dono

## 1. O levantamento na adoção

O procedimento é o de `references/fase-grande.md` §1, e o modelo é `assets/modelos/levantamento.md`.
Na adoção ele é curto, responde a "em que pé isso está?" e muda em três pontos: cada linha leva
"Rodei e vi" ou "Inferi"; "não há" também é resultado; o que existe e serve ganha "não refazer".

| O que levantar | Onde ler, sem rodar nada do projeto | O rótulo honesto |
| --- | --- | --- |
| Comandos de instalar, rodar, testar e gerar o build | Manifestos, leia-me, configuração do CI | "Inferi", até cada um rodar uma vez (§5) |
| O que há em produção | O ramo que implanta, a configuração da hospedagem, o histórico, a palavra do dono | "Inferi": do repositório não se vê o que está no ar |
| Testes e CI | Pastas de teste, configuração do CI | "Rodei e vi", pela leitura; "passam", só depois de rodar |
| O que a mudança pedida toca | Busca sem limite de profundidade: dados, acesso, segredos, dado restrito | "Rodei e vi", com os caminhos: é o que vai para `[zonas]` |

Até o levantamento fechar: não altere nem apague o que existe; em banco que já está em uso, o que é
novo leva prefixo próprio; se parecer preciso mexer no que está em produção, pare e pergunte.

## 2. Para onde o ambiente aponta

O erro mais barato num projeto herdado é rodar contra a produção sem perceber, porque o arquivo de
ambiente que veio na pasta aponta para ela. A linha `ambiente:` do diagnóstico responde sem mostrar
valor: `destinos não locais: sim (<CHAVE>, …)`, `não` ou `não sei`.

Sem Python, liste só os nomes das chaves e não abra o arquivo "para dar uma olhada": o valor
impresso fica no histórico da conversa. Só com os nomes, o destino é "não sei".

```bash
grep -oE '^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=' <arquivo>   # → só os nomes
```

- **Com "sim" ou "não sei":** não rode migração, servidor, teste que usa banco, carga de dados nem
  console do projeto, até o dono dizer para onde cada endereço aponta. Ler arquivos segue liberado.
- **Para rodar no ambiente local:** proponha um arquivo de ambiente só local, com valores de teste.
  O arquivo que existe não se edita nem se renomeia: é do dono.
- **Arquivo de ambiente rastreado pelo git:** o segredo já está no histórico. Diga isso sem repetir
  o valor; trocar a credencial é passo do dono.
- **Variável exportada no terminal** o diagnóstico não vê: ela pode apontar para fora mesmo assim.

## 3. Mapear os documentos

Para cada papel (especificação, arquivo de instruções, registro de decisões, roteiro, estado,
leia-me), aponte em `[documentos]` o documento que já o cumpre, sem renomear, mover nem reformatar.
`montar.py` faz isso para os nomes comuns (`mapeado:`); nome incomum vai à mão, `chave = valor`.

- **Documento em outro formato fica como está.** O diagnóstico só lê fases, registros e data nos
  formatos do método, e avisa quando não reconhece. Não converta o documento para calar o aviso.
- **Registro de decisões sem o título `## ADR-NNN · <título>`:** `decisoes.py` não o enxerga.
  Deixe-o onde está, aponte `decisoes` para um arquivo novo, criado do modelo, e diga no topo dele
  onde moram as decisões antigas.
- **`metodo.ini` que já veio com o repositório** se lê inteiro antes da primeira subida da escada:
  `escada.py` roda os comandos que estiverem ali. Comando que não se entende não roda.

## 4. Oferecer o mínimo

Depois do levantamento e da resposta ao pedido, faça a oferta. É pergunta, e espera o sim:

```text
Para as próximas conversas não dependerem da minha lembrança, proponho gravar até quatro arquivos
novos: metodo.ini (onde estão os documentos e os comandos de verificação), docs/decisoes.md (as
decisões, vazio por enquanto), docs/ESTADO.md (onde o projeto está) e, se faltar, o arquivo de
instruções. Nada do que existe muda de nome nem de conteúdo. A alternativa é não gravar nada: sigo
com o pedido, faço as verificações à mão e digo aqui na conversa onde o projeto está.
```

- **Com o sim:** `montar.py <projeto> --simular`, uma frase com o que será criado, e depois sem a
  opção (`SKILL.md` §2). Especificação e roteiro só nascem com `--completo`, se o dono quiser.
- **Com o não:** o piso vale, à mão. Os comandos que o projeto já tem fazem o papel dos degraus 0 a
  2, ligados ao commit por `&&`; o estado vai na mensagem de fecho; os scripts que pedem
  `metodo.ini` não rodam. Não há onde guardar a recusa: a oferta volta uma vez, na sessão seguinte.
- **O bloco "Como trabalhamos"** (texto em `assets/modelos/instrucoes.md`) é a única edição em
  arquivo que já existe, e `montar.py` só avisa que ele falta. Mostre o trecho e onde entra, e
  grave depois do sim: é ele que mantém o portão do commit quando a skill não é acionada.
- **Arquivo de instruções gerado por uma ferramenta, ou que não é carregado em toda sessão:** o
  que fazer está em `references/instrucoes.md` §8.

## 5. A primeira escada e as zonas

Antes do primeiro commit de código, os degraus 0 a 2 têm comando ou `n/a` com motivo estrutural;
sem isso o portão sai com código 3 (`SKILL.md` §4). O commit que só traz os documentos do método
sai antes, sem a escada. O que já roda vira degrau: ache o comando, rode uma vez sozinho, com a §2
resolvida, e só então grave (o passo a passo está em `references/testes.md` §8).

| Degrau | Recebe, na adoção | Se o projeto não tem |
| --- | --- | --- |
| 0 | A checagem de sintaxe, de compilação ou de estilo que já existe | A checagem de sintaxe ou de compilação da própria linguagem |
| 1 | A checagem de tipos que o projeto usa | `n/a`, se a stack não tem essa checagem, com o motivo |
| 2 | O comando de testes. O primeiro teste real é o da mudança pedida, ou o do que não pode vazar | Vazio até o teste nascer, junto com a mudança. Não é `n/a` |
| 3 a 5 | Só o que já roda | Vazio, que é pendente: vai a "Não rodei" e a "Ficou para depois", com data. `n/a` posto para o portão passar esconde a pendência de quem vem depois |

- **`[zonas]` com os caminhos reais**, inclusive os do código que a mudança vai criar: onde ficam
  as migrações, onde se decide quem pode, o módulo que lê os segredos, onde o dado restrito é lido.
  Zona que o projeto não tem se apaga, com um comentário; zona vazia desliga a rede sem avisar.
- **Registros reconstituídos:** só o que alguém desfaria por engano. O Contexto abre com
  "Reconstituído em <data>, a partir de <código, commit ou palavra do dono>" e diz o que não se
  sabe. Nenhum é obrigatório na primeira sessão; a decisão da mudança pedida é registro normal.

## 6. Contradições

Projeto herdado tem documento que diz uma coisa e código que faz outra. Não conserte nenhum dos
dois na primeira sessão: liste (o que o documento diz, o que o código faz, onde, a saída proposta)
e leve ao dono. Quem manda em cada caso, com a diferença entre documento que descreve e documento
que manda, está em `references/decisoes.md` §5.

- **Sem especificação retroativa por padrão.** Escrever agora o que o produto "deveria ser" ajusta
  a intenção ao que foi feito. O que o produto é hoje fica no parágrafo de abertura do arquivo de
  instruções. Se o dono quiser a especificação, ela é trabalho de uma fase (§7).

## 7. O que muda para o dono

Diga em até quatro linhas, pelo efeito: toda entrega fecha com o que foi decidido, o que depende
dele e como conferir; nada vai a produção sem uma lista que ele autorizou; todo commit de código
passa pelas verificações; e há alguns arquivos novos, cada um apresentado em uma frase.

A fase **"pôr a casa em ordem"** é oferecida, não imposta, e entra no roteiro com "Pronto quando"
como qualquer outra. Cabem nela, nesta ordem:

1. O que o projeto deve ao piso: teste de permissão por persona e de vazamento das áreas restritas
   que já existiam. Até esta fase, elas ficam em "Ficou para depois", com data e pelo nome.
2. Os degraus 3 a 5, o primeiro estágio do CI e um arquivo de ambiente por alvo.
3. As contradições da §6 resolvidas, os registros reconstituídos e, se o dono quiser,
   especificação e roteiro (`montar.py --completo`).

## Pare se

- O ambiente padrão aponta para fora do ambiente local e o pedido exige rodar com ele.
- Não há como rodar os testes sem tocar no ambiente remoto.

## O que evitar

- **Refazer o que já existe.** A busca rasa não achou a pasta, e o agente escreveu de novo. Busque
  sem limite de profundidade antes de propor, e marque "não refazer" no levantamento.
- **Rodar o comando do leia-me com o arquivo de ambiente que estava na pasta.** O padrão apontava
  para produção. Leia `ambiente:` antes do primeiro comando. Não serve: "é só para ver se abre".
- **Documento velho seguido como regra.** A especificação parou no tempo, e quem lê só ela desfaz
  o que foi decidido depois. Liste a contradição (§6) antes de agir sobre o documento.
- **Dizer o que está em produção olhando só o repositório.** Ele mostra o que foi commitado, não o
  que foi aplicado: o ambiente remoto pode divergir dos arquivos. Escreva "Inferi" e pergunte.

## Pronto quando

- [ ] `ambiente:` foi lido antes do primeiro comando do projeto, e nada rodou com destino não local.
- [ ] O levantamento separa "Rodei e vi" de "Inferi" e diz o que não foi lido.
- [ ] A oferta foi feita e respondida, e nenhum arquivo que existia mudou sem o dono ver.
- [ ] Degraus 0 a 2 com comando, ou `n/a` com motivo estrutural.
- [ ] Nenhuma zona com código e sem caminhos; a que o projeto não tem foi apagada.
- [ ] As contradições entre documento e código estão listadas para o dono.

Volte ao `SKILL.md`, §1.
