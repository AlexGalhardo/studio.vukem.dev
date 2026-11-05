# Escopo: o que entra na revisão, e que lentes a mudança pede?

Leia quando: for começar uma revisão (passo 1 do fluxo) ou o script imprimir um aviso.
Não é aqui: as perguntas de cada lente (`references/lentes.md`).

## O mínimo

- Parta da diferença do git. A descrição de quem escreveu diz o que ele quis fazer; a revisão
  procura o que ele fez sem querer.
- A base é o ponto em que a mudança se separou do que está em produção. Base errada põe na
  revisão código que já está no ar, ou deixa metade da mudança de fora.
- Arquivo novo ainda fora do git não aparece em `git diff`. O script lista; à mão, use
  `git status --short`.
- A zona decide a lente. O script vê o caminho, não o conteúdo: acrescente lente, nunca tire.
- Uma revisão cobre até 800 linhas mudadas ou 40 arquivos. Acima disso, divida.

Conteúdo: 1. A base 2. Ler a saída do script 3. Zonas 4. Das zonas às lentes 5. Mudança grande
6. O contexto que todo papel recebe 7. Os avisos

## 1. A base

| Situação | Base certa | Como pedir |
| --- | --- | --- |
| A mudança está num ramo; o principal é o que está no ar | o ponto de separação do ramo principal | sem `--base`: o script acha sozinho |
| Commits no ramo principal local, ainda não enviados | o ramo principal do remoto | sem `--base`, se o remoto existe |
| Nada foi commitado ainda | `HEAD` | `--base HEAD` |
| Commits no ramo principal local, sem remoto | o commit anterior à mudança | `--base <commit>` |
| Produção roda uma tag ou outro ramo | a tag ou o ramo | `--base <tag>` |

A primeira linha da saída diz a base e como foi escolhida. Se disser "o próprio HEAD", só entrou
o que não foi commitado: confira com `git log --oneline -5` se a mudança já tem commits.

## 2. Ler a saída do script

Saída abreviada, de uma mudança fictícia:

```text
base: 4f2a91c03b7e (ponto em que HEAD se separou de origin/main, escolhida sozinha)
zonas: padrões embutidos
mudança: 14 arquivo(s), +420 -60 linhas, 2 ainda fora do git

zona banco: 1 arquivo(s), +18 -0; lentes: banco-e-implantacao
  A    +18     -0  db/migrations/0031_cupom.sql
lentes pedidas:
  banco-e-implantacao: zona banco (1)
aviso: migration junto de código: confira a ordem de subida nos dois sentidos (...)
```

`A` novo, `M` alterado, `D` removido, `R` renomeado, `?` fora do git. Um `?` no lugar do número
quer dizer linhas não contadas: arquivo de ambiente (nunca aberto), binário ou maior que 1 MB.

## 3. Zonas

Cada arquivo cai na primeira zona cujo padrão casa, nesta ordem:

| Zona | O que cai nela (padrões embutidos, resumidos) | Por que é zona |
| --- | --- | --- |
| `segredo` | arquivo de ambiente, chave, certificado, nome com `secret` ou `credential` | o que vaza não se desfaz |
| `documentacao` | `.md`, `.mdx`, `.rst`, `.adoc` | não pede lente |
| `banco` | pastas de migration e do ORM, `.sql`, dados de exemplo | mexe em dado que já existe |
| `pagamento` | cobrança, checkout, assinatura, webhook, fatura | erro custa dinheiro de alguém |
| `acesso` | login, sessão, permissão, política, guarda, área de admin | erro abre a porta |
| `testes` | pastas e sufixos de teste que não caíram numa zona acima | prova, ou finge provar |
| `implantacao` | esteira de CI, contêiner, dependências, configuração de build | muda o que sobe e como |
| `interface` | rotas, páginas, componentes, modelos de tela, estilos | é o que o visitante vê |
| `outros` | o resto | sem padrão conhecido |

- **O padrão erra para o lado de pedir lente a mais.** `*auth*` pega `authors.ts`. Uma lente a
  mais custa uma leitura; uma a menos custa o defeito que ela acharia.
- **Declare as zonas do projeto** quando as pastas dele têm outros nomes: `--zona
  pagamento='**/cobranca/**,*fatura*'`, ou um `.revisor.ini` na raiz, a partir de
  `assets/modelos/zonas.ini`. Zona declarada vem antes das embutidas; mesmo nome substitui.
- **Teste em zona sensível fica nela**, marcado `[teste]`, e conta para a lente de testes.

## 4. Das zonas às lentes

| Zona tocada | Lentes |
| --- | --- |
| `banco`, `implantacao` | banco e implantação |
| `segredo` | segurança e fronteiras |
| `pagamento`, `acesso` | segurança e fronteiras; comportamento |
| `interface`, `outros` | comportamento |
| qualquer arquivo de teste novo ou alterado | testes |
| só `documentacao` | nenhuma: leia a diferença uma vez |

Acrescente à mão o que o caminho do arquivo não mostra:

- **Segurança e fronteiras**, se um arquivo de `interface` ou `outros` lê dado restrito, monta
  resposta para o navegador, usa cache compartilhado ou recebe parâmetro do visitante.
- **Banco e implantação**, se a mudança altera o formato de um dado gravado sem migration (JSON
  numa coluna, arquivo, fila), cria variável de ambiente, tarefa agendada ou ferramenta de carga.
- **Comportamento**, sempre que houver código de aplicação: toda mudança pode regredir.

Nunca rode menos lentes que as pedidas. Na revisão de origem rodaram três, e a qualidade dos
testes era uma pergunta da de comportamento: a lente de testes separada é desenho deste método.

## 5. Mudança grande

Acima de 800 linhas ou 40 arquivos, a leitura por lente vira amostragem sem que ninguém diga.
Os dois números são ponto de partida, não medida: ajuste com `--max-linhas` e `--max-arquivos`.

1. Divida por zona, da mais sensível para a menos: `segredo`, `banco`, `pagamento`, `acesso`,
   depois o resto. Cada parte é uma revisão, com as suas lentes e os seus achados.
2. A pergunta que atravessa as partes (a ordem de subida) fica com a parte do banco, que recebe
   a lista de arquivos das outras.
3. Se não dá para dividir (uma renomeação em 60 arquivos), revise por amostra e escreva no
   relato quantos arquivos foram lidos de quantos.

## 6. O contexto que todo papel recebe

Cada agente começa sem o histórico; com um agente só, escrever o contexto obriga a dizer o que a
mudança faz. Cinco partes, no modelo de `assets/modelos/papeis.md`:

1. **O projeto**, em uma linha, e onde está o arquivo de instruções dele.
2. **Como ver a mudança:** a base, e os comandos (`git status --short`, `git diff <base>`).
3. **O que a mudança faz**, em até 5 itens numerados, cada um com os arquivos principais.
4. **O que o autor relatou como frágil**, em itens com letra. É o mapa mais barato de onde olhar
   primeiro, e não o limite da revisão: o que o autor não desconfiou também entra.
5. **As regras do papel:** só leitura, o que pode rodar, o que é proibido (ambiente remoto,
   arquivo de ambiente, imprimir segredo) e a língua da resposta.

## 7. Os avisos

| O script disse | O que fazer |
| --- | --- |
| `aviso: mudança grande demais` | divida (§5) ou diga no relato que foi por amostra |
| `aviso: migration junto de código` | a lente de banco responde a ordem de subida nos dois sentidos (`references/lentes.md` §2) |
| `aviso: arquivo de teste removido` | é achado até alguém mostrar onde a regra continua provada |
| `aviso: arquivo de ambiente no diff` | pare e avise o dono; não abra o arquivo. Se havia segredo, a chave é trocada: o histórico do git guarda o valor |
| `aviso: arquivo de ambiente fora do git e fora do .gitignore` | proponha a linha no `.gitignore` antes de qualquer commit |
| `nota: exemplo de ambiente mudou` | pergunte se a variável nova já existe em cada ambiente |
| `nota: código mudou e nenhum arquivo de teste mudou` | a lente de comportamento pergunta o que prova a mudança |
| `nota: a base é o próprio HEAD` | confira se a mudança já tem commits (§1) |

## O que evitar

- **Revisar pela descrição do autor.** O arquivo que ele esqueceu de citar fica sem leitura.
- **Tirar uma lente porque "essa parte é simples".** Na revisão de origem, o plano de subida
  estava na ordem errada e só a lente de banco viu.
- **Ler o arquivo de ambiente para "só conferir".** O valor entra na conversa e no relato.

## Pronto quando

- [ ] A base foi lida na primeira linha da saída e é o que está em produção.
- [ ] Todo arquivo mudado está numa zona, e os de `outros` foram olhados um a um.
- [ ] A lista de lentes está escrita, com o motivo de cada uma, e nenhuma pedida foi tirada.
- [ ] Cada aviso tem resposta, e o contexto comum tem as cinco partes.

Volte ao `SKILL.md`, passo 2.
