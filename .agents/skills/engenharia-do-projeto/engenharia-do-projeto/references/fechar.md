# Fechar: que documento muda junto, como commitar e o que dizer ao terminar?

Leia quando: toda vez que uma mudança termina (passo 6 do ciclo).
Não é aqui: enviar ao ramo que implanta (`references/producao.md`).

## O mínimo

- Documento que a mudança invalida muda na mesma mudança: depois, ele já contradiz o código.
- Commite pelo portão, numa linha só e sem variação. É o portão do `SKILL.md` §4:

```bash
python3 <skill>/scripts/escada.py --ate 2 && git commit -m "<o que muda no comportamento>"   # portão do commit
```

- Escreva a mensagem pelo comportamento, não pelo arquivo.
- Commit não é envio: enviar ao ramo (branch) que implanta é ir a produção.
- Feche com o relato e os três blocos.

Conteúdo: 1. Mudou X, atualize Y 2. Commits 3. O portão do commit e o envio que não implanta
4. Commit não é envio 5. O relato de fim de mudança

## 1. Mudou X, atualize Y

Na mesma mudança, antes do commit. Cada fato tem uma casa: atualize a casa, não uma cópia.

| Mudou | Atualize |
| --- | --- |
| Arquivo, pasta ou módulo criado, movido ou apagado | O mapa "Onde ficam as coisas", no arquivo de instruções |
| Comando do projeto | O bloco "Comandos" do arquivo de instruções e o leia-me; se é comando de degrau, `[escada]` |
| Regra, limite ou rotina de um assunto | O documento por assunto, com "(implementado)" no título |
| Esquema, permissão ou dados de exemplo (seed) | O documento por assunto dos dados, e o artefato gerado do banco |
| Decisão que alguém desfaria por engano | Um registro novo (`decisoes.py novo`) e, se nasce regra, o arquivo de instruções. O que merece registro: `references/decisoes.md` §1 |
| Item de "Pronto quando" que passou a ter prova | O roteiro: `- [x]` |
| O que está aplicado, a última rodada, uma das cinco listas | `docs/ESTADO.md`, com a data de hoje (como atualizar: `references/retomada.md` §3) |
| Arquivo novo de zona sensível | `[zonas]`, em `metodo.ini`: sem isso, a próxima mudança nele passa por leve |
| Degrau que passou a existir | O comando em `[escada]`; o item sai de "Ficou para depois" |
| Variável de ambiente nova | O arquivo de ambiente de exemplo, só com o nome |
| Passo que só o dono faz | "Passos do dono", no estado, e o passo a passo no leia-me |

Busque no repositório inteiro, sem limite de profundidade, o nome antigo e as expressões "ainda
não" e "planejado": documento que continua dizendo que algo não existe engana a sessão seguinte.

## 2. Commits

Forma: `tipo(escopo): frase`, no presente, sem ponto final. O histórico é a narrativa do projeto.

- **Tipos:** `feat`, `fix`, `docs`, `test`, `chore`, `ci`, `refactor`. **Escopo:** a pasta de
  domínio ou a camada. Linha de coautoria no fim, quando o ambiente pede.
- **Comportamento, não arquivo:** "gerente exporta os pedidos em arquivo". Não serve: "ajusta
  política", "corrige erro".
- **Assunto de até 72 caracteres,** e o resto no corpo. É recomendação deste método: na prática
  vista, os assuntos passavam disso.

Fatie por camada, na ordem das dependências, de modo que cada commit deixe a árvore coerente:

1. `feat(db)`: migração, testes de banco, dados de exemplo e artefato gerado.
2. `docs`: o registro da decisão, antes ou logo depois do código.
3. `feat(<domínio>)`: a funcionalidade, com os testes ao lado; `test`, para o que não coube ali.
4. `fix(<domínio>): achados da revisão de <mudança>`: as correções, listadas.
5. `docs`: mapa, documento por assunto e estado.

Corpo só quando há um porquê que o assunto não carrega. Três formas:

| Forma | O corpo diz |
| --- | --- |
| Causa do defeito | O que acontecia em produção, o que o código supunha, o que passa a aceitar ou a fazer |
| Restrição técnica | Por que a mudança tem este formato ("duas migrações, porque…") e o que vai junto |
| Achados da revisão | Um por linha, cada um como comportamento; se são muitos, agrupados por lente |

## 3. O portão do commit e o envio que não implanta

```bash
python3 <skill>/scripts/decisoes.py conferir     # antes, se a mudança criou ou citou registro
python3 <skill>/scripts/escada.py --ate 2 && git commit -m "<o que muda no comportamento>"   # portão do commit
git rev-parse --abbrev-ref HEAD                  # → o ramo atual: compare com ramo_que_implanta
git fetch && python3 <skill>/scripts/envio.py && git push     # só em ramo que não implanta
```

- **O portão é o segundo comando, sem variação.** A saída para o código 3 está no `SKILL.md` §4.
- **`decisoes.py conferir` acusou:** crie o registro que falta ou tire a citação antes de commitar.
- **`scripts/envio.py` só lê.** Acusa segredo nas linhas que sairiam, arquivo que casa com
  `nunca_enviar` e commit do outro lado que falta aqui. Com `ACHADO`, a cadeia para. Não achar
  segredo não prova que não há: ele conhece só os padrões comuns.
- **`git fetch` vem antes** porque nenhum script busca. Com outra sessão no mesmo ramo, busque
  também antes de numerar um registro. Havendo commits do outro lado, integre por merge e diga no
  corpo, arquivo a arquivo, que versão ficou e por quê. Forçar o envio apaga o trabalho alheio.
- **O ramo atual é o que implanta:** esta cadeia não serve. `envio.py` só avisa, e aviso não
  interrompe o `&&`. Valem os portões de `references/producao.md` §1.

## 4. Commit não é envio

O commit grava só na máquina do dono. Nada chega ao ambiente remoto antes de um envio, e enviar ao
ramo que implanta é ir a produção: são dois atos, com autorizações diferentes.

- **Depois do commit,** deixe o produto no ar no ambiente local, entregue o roteiro de validação e
  espere a palavra de liberação. Onde a implantação é manual, a espera é a mesma.
- **Ao dono, diga o efeito:** "está salvo na sua máquina; o que as pessoas usam não mudou". O que
  está commitado e não enviado aparece na linha `a enviar:` do diagnóstico.
- **Antes do primeiro envio,** pergunte ao dono se o código pode sair da máquina dele e se enviar
  implanta, e preencha `ramo_que_implanta`, em `[envio]`. Até saber, todo envio é ida a produção.

## 5. O relato de fim de mudança

1. Suba a escada do fim da mudança (`python3 <skill>/scripts/escada.py --exigido`) e copie inteira
   a linha `escada:` que ela imprime.
2. Cole a linha em `docs/ESTADO.md`, em "Verificações automáticas: última rodada", e troque a data
   do estado. Abaixo dela vai a contagem por degrau, copiada das linhas exibidas ou do registro
   `degrau-<n>.txt`: número que o comando não imprimiu não se escreve. Colar não vence a evidência.
3. Commite pelo portão (§3).
4. Entregue o relato e os três blocos, com o texto de `assets/modelos/mensagens-ao-dono.md` §1.

| Rótulo | Entra |
| --- | --- |
| **Rodei e vi** | O comando e o número copiado da saída; até que degrau a escada subiu |
| **Inferi** | O que parece certo e não foi rodado, com o motivo |
| **Não rodei** | Degrau pendente, verificação cortada, o que não dá para validar daqui e documento que ficou desatualizado; cada um com o lugar em que foi anotado |

## O que evitar

- **O registro ficou para o fim da fase, e a sessão caiu antes.** A decisão está no código, sem o
  porquê. Registre na mudança que decide. Não serve: juntar tudo num registro no fim.
- **O commit da funcionalidade saiu com dezenas de arquivos.** Banco, documentos e testes ficam
  pequenos; a funcionalidade, não. É o ponto fraco desta divisão: corte por tela ou por caso, até
  cada fatia poder ser lida de uma vez, e deixe as correções da revisão em commit próprio.
- **O merge trouxe um documento com um plano que o dono já trocou.** A outra sessão escreveu sobre
  o combinado antigo. Ponha no topo dele uma nota dizendo o que não vale mais, e não o apague.

## Pronto quando

- [ ] Cada documento que a mudança invalidou foi atualizado antes do commit.
- [ ] O commit saiu pelo portão, com mensagem que descreve comportamento.
- [ ] `decisoes.py conferir` saiu com código 0, se a mudança criou ou citou registro.
- [ ] O estado tem a data de hoje e a linha `escada:` desta árvore.
- [ ] O relato separa "Rodei e vi", "Inferi" e "Não rodei", e fecha com os três blocos.
- [ ] Nada foi enviado ao ramo que implanta.

Volte ao `SKILL.md`, §4.
