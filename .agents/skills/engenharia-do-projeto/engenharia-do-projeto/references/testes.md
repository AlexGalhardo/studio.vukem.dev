# Testes: em que camada prender cada regra e até que degrau subir?

Leia quando: passo 3 do ciclo (a seção da camada) e passo 4 (§1); ao montar a escada num projeto
novo (§8); um degrau falhou ou um teste é instável (§9).
Não é aqui: os testes que seguram o que não pode acontecer (`references/fronteiras.md`).
**Base:** proposta. Três partes são desenho montado a partir da prática, sem uso anterior nesta
forma: a escada em degraus numerados (§1), a ordem para montá-la (§8) e o procedimento de teste
instável (§9, depois da tabela). As camadas e a tabela de causas são prática vista.

## O mínimo

- Escreva o teste na mesma mudança, na camada mais barata que enxerga a regra: as camadas caras só
  testam o que as baratas não veem.
- Suba a escada com `escada.py` e diga até que degrau subiu, com os números copiados da saída.
- Degrau que não existe é pendência dita em "Não rodei". Omitido, ele é lido como "passou".
- Falhou: relate com a saída e diagnostique antes de rodar de novo, porque repetir esconde a causa.
- Em teste de permissão, confira o efeito e não só a exceção: bloqueio pode ser "zero linhas".

```bash
python3 <skill>/scripts/escada.py --exigido   # → uma linha por degrau e a linha `escada:` do relato
```

Conteúdo: 1. A escada de verificação 2. As camadas 3. Lógica pura 4. Cliente falso 5. Interface
6. Permissão por persona 7. Ponta a ponta 8. Montar a escada 9. Falhou ou é instável 10. Em outras
stacks

## 1. A escada de verificação

Um degrau só é subido se o de baixo passou, e o custo cresce para cima. Os degraus 0 a 5 são
comandos em `[escada]` de `metodo.ini`; o 6 e o 7 não têm comando. O custo é ordem de grandeza.

| Degrau | O que prova | Custo | Quando roda |
| --- | --- | --- | --- |
| 0. formato e lint | As regras de estilo que são inegociáveis | segundos | toda mudança |
| 1. tipos | Os contratos entre módulos e com o banco, pelo artefato gerado | segundos | toda mudança |
| 2. unidade e fronteiras | Regras de negócio; quem importa o quê; a guarda primeiro | segundos | toda mudança |
| 3. banco | Migrações aplicadas do zero; permissão por persona; privilégios; artefato gerado em dia | poucos minutos | mudança de esquema, permissão ou dados de exemplo (seed) |
| 4. build | O produto compila e monta as páginas contra um banco migrado | minutos | mudança de rota, leitura compartilhada, cache ou configuração |
| 5. ponta a ponta | Fluxos por persona em dois tamanhos de tela; vazamento; guarda de área restrita | minutos | mudança em acesso, sessão, dado restrito ou cobrança; fim de fase |
| 6. revisão | O que nenhum teste pergunta | caro | fim de fase; mudança de risco |
| 7. conferência em produção | Que o visitante anônimo recebe o que deveria, no endereço real | minutos | depois de cada ida a produção |

- **Até onde subir.** Vale o número que `escada.py --exigido` calcula das zonas que a mudança em
  curso toca; antes de enviar, `--a-enviar` faz a mesma conta sobre o que está a enviar. A coluna
  "Quando roda" é essa conta à mão, para a mudança que toca uma zona por um arquivo que `[zonas]`
  ainda não lista. No fim de fase, todos os degraus com comando (`escada.py` sem opção).
- **Estados de um degrau.** `ok`; `FALHOU`; `pendente` (sem comando: não conta como subido); `n/a`
  (não existe na stack: conta como subido); `não rodado` (um degrau de baixo falhou).
- **Nenhum pulo.** `escada.py` para na primeira falha, porque degrau de cima sobre degrau de baixo
  quebrado mede outra coisa. `--so <n>` roda um degrau só, para iterar num teste: a evidência
  continua valendo só até onde os degraus de baixo passaram sobre a mesma árvore.
- **A evidência é por degrau e presa à árvore.** Editar código ou `metodo.ini` a vence; editar os
  documentos do método, não. O portão do commit e a saída para o código 3 estão no `SKILL.md` §4.

## 2. As camadas

| Camada | O que protege | Precisa no ar | Degrau | Quando falha, quer dizer |
| --- | --- | --- | --- | --- |
| Formato, lint, tipos | Regras de estilo inegociáveis e contratos de tipo | nada | 0 e 1 | Regra do projeto quebrada antes de rodar qualquer coisa |
| Lógica pura (§3) | Filtro, permissão calculada, formatação, validação, mensagens | nada | 2 | A regra mudou ou regrediu |
| Ação de servidor com cliente falso (§4) | A ordem: guarda, depois validação, nenhuma escrita sem sessão | nada | 2 | Uma ação toca o banco sem checar quem é |
| Interface (§5) | Semântica e acessibilidade das peças básicas; estado de erro | nada (tela montada em memória) | 2 | Botão que não é botão; erro cru na tela |
| Fronteiras | Quem importa o quê; onde um nome restrito aparece; a primeira instrução de cada ação | nada | 2 | Alguém abriu um caminho novo para o dado restrito |
| Banco (§6) | Esquema, funções, permissão por persona, privilégios | um banco de teste | 3 | A permissão no banco não é a que o documento diz |
| Build | O produto compila e monta as páginas | banco migrado, se o build consulta | 4 | Código e banco não combinam |
| Ponta a ponta (§7) | Fluxos reais por persona; vazamento; guarda de área restrita | o produto inteiro no ambiente local, com dados de exemplo | 5 | Quem usa o produto veria o defeito |

## 3. Lógica pura com teste ao lado

Tire da tela o que é cálculo (filtro, decisão de quem lê, formatação, validação) para um módulo
sem import de framework, com o teste no arquivo vizinho: a regra sem teste fica à vista.

| Técnica | Como | O que pega |
| --- | --- | --- |
| Frase como nome | O nome do teste afirma a regra na língua do produto: "visitante não lê item restrito" | Quem lê a falha sabe que regra quebrou |
| Tabela de casos | Persona, alvo e resultado esperado, uma linha por combinação, com as entradas inválidas | A regressão de borda que o exemplo feliz não vê |
| Propriedades | Ida e volta; entrada que não é alterada; ordem estável das chaves; valor padrão omitido; texto de borda | O defeito que nenhum exemplo escolhido mostra |
| Paridade | A mesma regra em dois lugares (servidor e navegador; banco e código) usa a mesma tabela, num arquivo de apoio que não entra no produto | Duas implementações que derivam em silêncio |
| Alarme de enumeração | Um teste lê os valores no artefato gerado e afirma quantos caem de cada lado de uma decisão; o comentário diz o que fazer quando quebrar | Valor novo que passaria em branco em toda condição |

## 4. Ação de servidor e receptor de notificação com cliente falso

As funções que mudam dado no servidor se testam sem banco: as bordas (guarda de sessão, cliente do
banco, cache, navegação) viram peças falsas, e o teste afirma **ordem e ausência**. Teste pela
tela não distingue "checou e negou" de "nem chegou lá".

1. Troque só as bordas: peça falsa que cobre a própria regra faz o teste afirmar a peça. O cliente
   do banco vira um cliente falso encadeável, que registra cada chamada (tabela, operação,
   argumentos) e responde com o resultado combinado.
2. Uma lista com **todas** as ações do arquivo alimenta os casos comuns: sem sessão, o erro da
   guarda sobe e nada é chamado; a guarda vem antes da validação (entrada inválida sem sessão é
   barrada pela guarda); o caminho de volta só aceita rota interna conhecida.
3. Faça o cliente falso lançar quando o código faz o que a regra proíbe, como pedir de volta a
   linha inserida onde a persona não tem leitura.
4. No receptor de notificação, troque só o cliente do serviço externo. A conferência de assinatura
   é a de verdade, com segredo de mentira; afirme as escritas na ordem em que aconteceram.

## 5. Interface: pouco, e só o que as outras camadas não veem

- **Peças básicas** (botão, campo, estado vazio): consulte por papel acessível e nome, e afirme o
  elemento real e o estado desabilitado. Peça errada se multiplica por toda tela.
- **Estado que a ponta a ponta não provoca**, como a tela de erro de uma rota pública: monte-a com
  um erro de mensagem técnica e afirme que a mensagem crua não aparece e que há como tentar de novo.
- Afirme classe de estilo só onde a classe é o contrato (altura mínima do alvo de toque). No resto,
  todo ajuste visual vira teste quebrado.

## 6. Permissão por persona

É o teste que exercita a regra como ela é imposta, sem o aplicativo no meio. Sai da matriz de
permissões (`references/dados.md` §3): um arquivo por persona, mais um só com os privilégios.

| Faça | Porque |
| --- | --- |
| Cada arquivo cria os próprios dados, numa faixa de identificadores que não colide com os dados de exemplo, e desfaz tudo no fim | Roda sozinho, até sem dados de exemplo, e nada fica no banco |
| Vire a persona pelo caminho que o produto usa (papel, sessão ou credencial) e zere a identidade ao trocar | Como dono do banco, a regra de linha é ignorada e tudo passa |
| Por persona: o que lê (contagem exata), o que não vê (conjunto vazio), o que escreve e o que não escreve (inserir, alterar, apagar) | A mesma lista para todas mostra a persona que ficou de fora |
| **Tentativa de autopromoção:** "logado não se dá acesso pago", "logado não se torna administrador" | É a escrita que mais rende a quem ataca |
| **Efeito, e não só exceção:** afirme "a consulta com retorno veio vazia" ou a contagem antes e depois; onde o bloqueio é erro, confira o código exato | Alterar ou apagar barrado por regra de linha não dá erro: afeta zero linhas em silêncio |
| Insira sem pedir retorno e, à parte, prove que com retorno falha | O erro de um inserir com retorno pode vir da falta de leitura, não da regra de inserção |
| **Prova final:** depois das tentativas, como dono dos dados, confira que nada do que foi tentado ficou gravado | Uma tentativa pode ter passado sem erro |
| Declare quantas afirmações o arquivo tem, se a ferramenta permitir; nenhuma depende de "hoje" | Afirmação que não rodou também é falha; data relativa envelhece |

## 7. Ponta a ponta

| Assunto | Regra | Porque |
| --- | --- | --- |
| Personas | Uma conta de identificador fixo por persona nos dados de exemplo; um passo de preparo gera a sessão de cada uma sem tela, com a biblioteca de sessão do produto; visitante é a sessão vazia; o login de verdade tem um teste próprio; sessão gravada vence e não sobrevive a recriar o banco: rode o preparo de novo | Login pela tela em todo teste é lento e frágil; rota de teste no produto é porta dos fundos em produção; sessão montada à mão quebra quando o formato muda |
| Trava de ambiente | A função que lê as variáveis recusa endereço de banco que não seja local | Estes testes criam sessões e dados |
| Dados que o teste cria | Prefixo de teste em tudo; o teste deixa o banco como achou; quem grava usa conta própria; limpeza antes, depois e das sobras antigas; arquivo de teste pequeno, nomeado pelo defeito | Os dois tamanhos de tela rodam ao mesmo tempo, e execução interrompida deixa sobra |
| Estado que vem de fora | O teste grava fazendo o papel do receptor; os testes passam com e sem as chaves do serviço externo | O CI roda sem essas chaves |
| Dois tamanhos de tela | Largo e celular rodam os mesmos testes; o que é de um só pula com o motivo escrito; resposta crua roda num só; localidade e fuso fixos | Defeito de tela pequena não aparece na larga, e o resultado não pode mudar com a máquina |
| Onde roda | Contra o build de produção, em outra porta de rede, sem reaproveitar nem derrubar o servidor que o dono deixou aberto | Servidor de desenvolvimento com horas de uso falha por conta própria |

## 8. Montar a escada num projeto novo

A escada não nasce inteira. São cinco momentos, cada um na mudança que cria o que ele verifica:

| Momento | Entra |
| --- | --- |
| Fase de base | Formato, lint, tipos e o executor de unidade com o preparo de ambiente: degraus 0 a 2 |
| Nasce o banco | Testes por persona e de privilégios; o comando que recria um banco de teste com nome próprio, e não o banco em que o dono cadastrou coisas (`references/ambientes.md` §4): degrau 3 |
| Nasce a primeira tela protegida | Contas por persona, preparo de sessão, guarda pela resposta crua: degrau 5 |
| Nasce o primeiro dado restrito | Marcadores nos dados de exemplo, teste de vazamento, teste de fronteiras |
| Cada funcionalidade com regra "só X pode Y" | A regra nova no teste de fronteiras, na mesma mudança |

Preencha `[escada]` um degrau por vez:

1. Descubra o comando no manifesto do projeto e na documentação da versão instalada.
2. Rode uma vez, sozinho, e leia a saída. Comando inferido e não rodado é promessa.
3. Só então grave em `N.comando`. O que o degrau precisa no ar vai em `N.precisa`.
4. `n/a: <motivo>` é honesto quando o degrau não existe na stack por estrutura: sem banco, sem
   build, sem interface. Degrau que existe e ainda não foi escrito fica vazio, que é pendente.
5. Preencha `[zonas]` no mesmo passo, com os caminhos reais (`references/pesos.md` §2).

```ini
[escada]
3.comando = <o comando que recria o banco de teste e roda os testes de banco>
3.precisa = o banco local no ar
4.comando = n/a: sem build
5.comando =
```

- **Ambiente de teste que roda sem arquivo de ambiente.** O preparo do executor de unidade define
  valores de mentira para as variáveis obrigatórias, só quando elas não existem: o CI não tem
  arquivo de ambiente, e o módulo que valida as variáveis lança ao ser importado. Use valores
  obviamente falsos e endereços locais. Atribuição direta sobrescreveria o valor real da máquina.

## 9. Falhou ou é instável

| Causa | Sintoma | Conserto |
| --- | --- | --- |
| Clique antes de a página ficar interativa | O botão existe e o clique não faz nada | Repita a ação e a conferência juntas até passar: o critério é o efeito observável, não o tempo |
| Cache que serve a versão anterior na primeira visita | O item publicado não aparece na primeira carga | Recarregue até aparecer, com limite; o comportamento fica num registro (ADR), e o teste o cita |
| Dado que depende da data | Selo "novo", ordem por uso, "vigente desde ontem" | Não afirme o que depende do dia; banco recriado; localidade e fuso fixos |
| Serviço com limite de pedidos | Vários testes pedem código de login ao mesmo tempo | Os testes daquele arquivo rodam em fila |
| Um teste depende do estado do anterior | O segundo passo falha isolado | Grupo declarado em série, com o porquê no comentário, e conta própria do grupo |
| Os dois tamanhos de tela gravam na mesma linha | Falha só quando roda tudo junto | Uma conta por tamanho de tela, criada e apagada no grupo |
| Sobra de execução anterior | "Já existe" na criação | Prefixo de teste; limpeza antes, depois e das sobras antigas |
| Servidor de desenvolvimento compilando a rota | Estoura a espera na primeira vez | Constante nomeada com a espera maior e o motivo, só nos passos que dependem dela; o limite global não sobe |
| Servidor de desenvolvimento degradado | Falhas ao acaso depois de horas | Reinicie; o resultado que vale é contra o build de produção |
| Mensagem assíncrona | O e-mail ainda não chegou | Espera ativa com limite e mensagem própria |
| Elemento duplicado no documento | "Achou 2 elementos" | Localize por papel acessível ou só os visíveis, não por texto solto |
| Passo naturalmente longo | O envio de um arquivo estoura o limite | Limite maior só naquele teste, com o motivo no comentário |

A rede: nenhuma nova tentativa no ambiente local, para a instabilidade aparecer a quem escreve; no
CI, até duas, com rastro gravado na primeira e relatório guardado só quando falha.

1. Leia a saída e o rastro. Relate a falha com a saída, não com "falhou um teste".
2. Reproduza sozinho e depois junto dos outros. Só junto: estado compartilhado. Só no servidor de
   desenvolvimento: ambiente. Só em certo dia ou hora: data.
3. Classifique numa linha da tabela e aplique o conserto. Se a causa é defeito do produto (o
   clique perdido afeta quem usa o produto?), é correção, não ajuste de teste.
4. Não servem: espera fixa, limite global maior sem comentário, teste pulado ou apagado em
   silêncio, CI vermelho "conhecido".

## 10. Em outras stacks

| Peça | Equivalente |
| --- | --- |
| Lógica pura | Qualquer executor de unidade: valem o arquivo vizinho e a frase como nome |
| Cliente falso | Repositório em memória que registra chamadas, injetado no lugar do real; afirme "não chamou" |
| Permissão por persona | Sem regra por linha no banco: teste de integração da camada de autorização contra um banco real recriado, com uma sessão ou credencial por persona |
| Sessões na ponta a ponta | Autenticação própria: o preparo insere a sessão no armazenamento de sessões. Token em cabeçalho: o preparo emite com a chave de teste |
| Sem banco relacional | O degrau 3 vira a integração da camada de dados e a conferência do artefato gerado |

## O que evitar

- **Tudo passa no teste de permissão.** Ele roda como dono do banco, que ignora a regra de linha.
  Vire a persona pelo caminho do produto e inclua um caso que tem de ser barrado.
- **"Não chamou" passa ou falha sem motivo.** Sobrou estado da peça falsa do teste anterior, ou a
  peça falsa cobre a própria regra e o teste afirma a peça. Zere as peças antes de cada teste e
  troque só as bordas.
- **A ponta a ponta falha ao acaso depois de horas de trabalho.** O servidor de desenvolvimento
  degradou ou a máquina está sem memória. Rode contra o build de produção, um processo pesado por
  vez. Aumentar o limite global não serve.

## Pronto quando

- [ ] Cada regra nova tem teste na mesma mudança, na camada mais barata que a enxerga.
- [ ] Os degraus 0 a 2 têm comando rodado uma vez antes de gravado, ou `n/a` com motivo estrutural.
- [ ] Havendo permissão: um arquivo por persona, com efeito conferido, autopromoção e prova final.
- [ ] A linha `escada:` está no relato; degrau pendente está em "Não rodei" e em "Ficou para
      depois", com data.
- [ ] Nenhuma falha foi resolvida rodando de novo: cada uma tem a causa classificada (§9).

Volte ao `SKILL.md`, §4.
