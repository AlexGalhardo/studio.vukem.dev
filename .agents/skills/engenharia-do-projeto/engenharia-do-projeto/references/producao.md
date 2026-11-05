# Produção: como levar a mudança ao que as pessoas usam, na ordem certa e com conferência?

Leia quando: situação D, antes de qualquer comando que toque o ambiente remoto, inclusive leitura;
vai ser escrita uma ferramenta que grava por fora do aplicativo (só a §8).
Não é aqui: arquivos de ambiente e segredos (`references/ambientes.md`).

## O mínimo

Dois caminhos, pelo que a ida a produção leva:

- **Só código:** os portões da §1, `envio.py`, a lista ao dono, o envio, a conferência como
  visitante. A lista vai na conversa, e nenhum arquivo é criado.
- **Com banco ou dados:** copie `assets/modelos/ida-a-producao.md`, que é a casa da lista de
  passos, e siga a ordem banco, dados, código.

Nos dois: ambiente local primeiro, validado pelo dono. Um sim para a lista inteira; pare no
primeiro resultado fora do previsto. Depois, confira como visitante anônimo, no endereço que o dono
usa, e atualize o estado.

Conteúdo: 1. Portões 2. A ordem e a conferência prévia 3. Migração no ambiente remoto 4. Dados
5. Código 6. Depois 7. Passos do dono e a primeira vez 8. Ferramenta que escreve por fora 9. Quando
a permissão barra 10. O que o método não cobre. A §8 e a §10 ficam fora da leitura de rotina.

## 1. Portões antes de tocar em produção

É a casa deste fato. Os cinco passam antes de qualquer escrita no ambiente remoto:

| Portão | Passa quando | Se não passa |
| --- | --- | --- |
| a. A palavra de liberação responde a uma lista | O roteiro de validação foi entregue com a lista do que acontece depois, e o dono disse a palavra: ela autoriza essa lista | "Pode subir" sem lista anterior, ou pedido do que não estava nela: entregue a lista exata uma vez (`assets/modelos/mensagens-ao-dono.md` §8) e espere um único sim. Se o dono ainda não viu a mudança, o roteiro de validação vai junto |
| b. A evidência vale até o degrau exigido | `escada.py --evidencia` sai com código 0 | Código 3: suba de novo com `escada.py --a-enviar`. Se o que falta é degrau pendente, ele consta de "Ficou para depois", é dito ao dono na lista, e a cadeia usa `--evidencia --ate <maior degrau com comando>` |
| c. Em zona sensível, houve revisão | O relato da mudança traz a revisão do passo 5 | O corte dela, em modo enxuto, está escrito no estado e é dito na lista |
| d. Nada indevido sai no envio | Depois de `git fetch`, `envio.py` sai com código 0 | Com `ACHADO` (segredo, arquivo de `nunca_enviar`, commit do outro lado que falta aqui), resolva antes |
| e. O estado é o do disco | `docs/ESTADO.md` foi relido agora, e "Ainda não aplicado" foi conferido na fonte | Corrija o estado antes de agir, e não aplique nada |

A cadeia do envio, sempre com `&&`:

```bash
python3 <skill>/scripts/escada.py --evidencia && python3 <skill>/scripts/envio.py && git push
```

- **Ler o ambiente remoto também tem regra:** só quando a próxima ação depende da resposta, com o
  alvo dito pelo nome no comando, e por comando que não tem como escrever (listar o histórico, e
  não "aplicar o que falta").
- **Correção urgente. Leitura do método, não regra vista do dono.** Quando o próprio dono pede
  para enviar já a correção de um defeito de produção, cai a espera pelo roteiro de validação.
  Ficam de pé o piso inteiro, o pedido dele para aquela ação, reproduzir no ambiente local, enviar
  só a correção, conferir como visitante e registrar depois.

## 2. A ordem e a conferência prévia

Banco, depois dados, depois código, porque:

- Migração que só acrescenta é invisível para o código que está no ar, e dado novo também: o
  produto antigo ignora o que não conhece.
- O build novo pode consultar o banco para montar as páginas. Sem a estrutura nova, ele falha; com
  a estrutura e sem os dados, monta páginas incompletas, que ficam assim até o cache expirar.

**Quando inverte:** remover coluna, tabela ou valor pede o código primeiro e o banco depois, e
apagar dado pede pergunta ao dono. Adaptação, a conferir: a prática vista só acrescentou.

A conferência prévia é o que se lê antes de cada escrita sem volta:

| Passo | Conferência prévia | Onde não há simulação, o relato diz |
| --- | --- | --- |
| Banco | A migração aplicada do zero no ambiente local (degrau 3); o histórico do ambiente remoto comparado com os arquivos; a simulação (dry-run) da ferramenta de migração, se houver | "sem simulação; conferi: aplicada do zero no ambiente local; histórico remoto igual aos arquivos até <a última>" |
| Dados | A simulação pelo mesmo caminho da escrita, lida linha a linha (§4) | "sem simulação; conferi <o quê>", e a lista já avisou o dono disso |
| Código | `envio.py` e os commits que ele lista como saindo | não se aplica: `envio.py` só lê |

## 3. Aplicar migração no ambiente remoto

1. Liste o histórico de migrações do ambiente remoto e compare com os nomes dos arquivos.
2. Aplique uma por arquivo, na ordem, pelo canal de migrações da stack. Ele deixa nome e
   histórico; SQL solto numa ferramenta genérica, não.
3. Liste o histórico de novo e compare. Ferramenta que não é a de migrações pode gravar a hora da
   aplicação no lugar da versão do arquivo, e um envio futuro tentaria reaplicar tudo. Divergiu:
   não acerte por conta própria; anote no estado, com a conferência a fazer antes do próximo envio,
   e leve ao dono.
4. Confira com uma consulta o que um aviso da migração diria: pelo canal usado, ele pode não
   aparecer.

Diga na lista o que não tem volta: valor acrescentado a uma enumeração, por exemplo, não sai.
Migração já aplicada fora do ambiente local não se edita (`references/dados.md` §8).

## 4. Dados

1. Escreva antes de rodar: "só pode sobrar: <as linhas esperadas>" e "pare se aparecer: <linha>".
   Numa carga feita só para etiquetar itens, só podem sobrar "criar a etiqueta" e "pôr N etiquetas
   no item".
2. Rode a simulação contra o próprio ambiente remoto, pelo mesmo caminho da escrita. Simulação que
   percorre outro caminho não diz o que a escrita fará.
3. Leia a saída linha a linha. Sobrou só o previsto: rode a escrita e confira o resumo, com o alvo
   e a contagem. Sobrou outra coisa: pare, não escreva e mostre a linha ao dono.

Sem ferramenta com simulação, um script de banco pode rodar numa transação que termina desfazendo,
para mostrar o que mudaria (adaptação, a conferir).

## 5. Código

- **Enviar é implantar?** Se o ramo (branch) atual é o `ramo_que_implanta` de `[envio]`, é, e
  `envio.py` avisa. Onde a implantação é manual, ela entra na lista como passo próprio.
- **Espere o CI e a implantação terminarem antes de conferir.** Antes disso, a página mostra a
  versão anterior e parece falha.
- **O envio saiu, e a página não mudou:** veja, nesta ordem, se a implantação terminou, se ela
  falhou (build contra banco sem a estrutura, §2), se o ramo enviado é o que implanta, e o cache.
- **CI vermelho depois do envio:** diga ao dono na hora, com a saída do estágio e com o que está
  no ar, separando "Rodei e vi" de "Inferi". Não envie outro commit para ver se passa: reproduza
  no ambiente local, no mesmo degrau. A correção é mudança nova, pelo portão do commit.

## 6. Depois

1. **Confira como visitante anônimo,** sem sessão, no endereço que o dono usa: conte o que deveria
   estar lá e confira o que não deve aparecer. É o degrau 7 da escada.
2. **Cada endereço guarda a sua cópia em cache.** O endereço padrão da hospedagem pode mostrar o
   novo enquanto o do dono mostra o antigo. A primeira visita depois da mudança também pode vir
   antiga: recarregue antes de concluir.
3. **Escrita por fora do aplicativo não expira o cache.** A carga termina sem erro, e o site
   continua igual até o prazo do cache ou até uma nova implantação. Em carga sem código, diga ao
   dono em quanto tempo o dado aparece ou o que precisa ser feito para aparecer.
4. **Atualize o estado** (`references/retomada.md` §3): o que foi feito, a pedido de quem e
   quando; o que não saiu como previsto; o que conferir antes da próxima ação.
5. **O commit do estado** entra como último item da lista autorizada ("e envio o registro do que
   foi feito") ou fica no ambiente local, e isso é dito: no ramo que implanta, até um commit só de
   documentos é um envio. Feche com o relato e os três blocos.

## 7. Passos que só o dono faz, e a primeira vez

O que depende de painel, de conta ou de dinheiro fica em "Passos do dono", no estado, antes de a
lista ser entregue: variáveis na hospedagem, domínio, a notificação do serviço de pagamento, envio
de e-mail, texto legal. A lista diz qual passo dele vem antes de qual passo do agente.

**Configuração que mora num painel diverge do ambiente local.** O mesmo código funciona aqui e
falha lá porque um valor (o tamanho de um código de acesso, um limite) é outro em produção. Para
cada uma: o leia-me diz o valor esperado, e o código aceita a faixa que o provedor permite.

**Se é a primeira vez:**

1. O banco é migrado antes do primeiro build, se o build consulta o banco.
2. As variáveis existem na hospedagem, em todo ambiente em que o build roda (passo do dono).
3. O dado que produção precisa para funcionar vai em migração própria. Dados de exemplo não vão.
4. O primeiro administrador só existe depois do primeiro login: a linha dele é passo à parte, com
   autorização própria. Sem ela, ninguém entra como administrador.
5. Configuração de painel é testada pelo dono no primeiro uso real.
6. Cada comando contra o ambiente remoto é confirmado com o dono ao lado. A lista continua uma só;
   nesta vez, ele vê cada comando antes de rodar.

## 8. Ferramenta que escreve por fora do aplicativo

Com credencial que ignora as permissões do banco, todo o cuidado tem de estar na ferramenta.

| Propriedade | Como |
| --- | --- |
| Alvo em três degraus | Endereço local passa. Qualquer outro exige opção explícita. Com a opção, só o endereço exato de produção, em https, escrito como constante no código: padrão largo deixa passar o projeto errado. Antes de agir, a ferramenta imprime o alvo e o rótulo, local ou produção; a chave não é impressa |
| Simulação pelo mesmo caminho | Toda escrita passa por uma função só, que em simulação anuncia e não executa. Três começos de linha: `=` (já está igual), `faria` e `ok` |
| Conferência antes da primeira escrita | Uma passada só de leitura: entrada válida, arquivos dentro dos limites, nenhuma colisão de chave. Nenhuma transação cobre banco e arquivos juntos: erro no meio deixa pela metade |
| Idempotência | Rodar de novo com a mesma entrada não muda nada: chave natural do item; caminho de arquivo derivado do conteúdo; campo ausente não mexe, e lista vazia tira tudo |
| Destrutivo é outro modo | Opção própria, que não combina com publicar, aceita simulação e tem alcance fechado |
| Uma cópia de cada regra | A ferramenta importa limites e validações do aplicativo, e a parte pura tem teste. O leia-me dela diz o que ela não faz, como expirar o cache |

Na variante web há um molde das duas funções centrais (`references/variante-web.md` §12).

## 9. Quando a permissão barra

Vale para toda barreira: permissão da sessão, proteção de ramo, aprovação obrigatória.

1. Pare na hora. Não repita a ação por outro caminho que dê no mesmo efeito. Escolher desde o
   começo o canal feito para a ação é o certo; procurar outra rota depois de um não é contornar.
2. Diga ao dono o que ia fazer, para quê, o que a recusa disse e como fica sem a ação. O texto é o
   de `assets/modelos/mensagens-ao-dono.md` §5.
3. Entregue o comando ou o clique, para ele fazer com as próprias mãos. A decisão é dele.
4. Anote no estado, com a conferência a fazer antes da próxima ação relacionada.
5. Siga só com o que não depende daquilo e já estava na lista. Banco ou dados barrados: a lista
   para ali. Passo do fim barrado, como invalidar o cache: siga para a conferência e diga o efeito.

## 10. O que este método não cobre

Não há prática vista de volta atrás de implantação, cópia de segurança e restauração,
monitoramento, rotina de incidente nem homologação. Antes da primeira ida a produção, diga isso ao
dono na lista e pergunte o que a hospedagem e o banco dele já oferecem para voltar atrás e para
copiar os dados. O que faltar vira item de "Para decidir" ou de "Pendência aceita", com data.

Onde há homologação, ela faz o papel do ambiente local nesta ficha, e o estado ganha uma linha por
ambiente (adaptação, a conferir).

## Pare se

Em qualquer dos quatro, não escreva mais nada, diga ao dono o que já foi feito e o que apareceu, e
anote no estado:

- Sobrou na simulação algo fora do "só pode sobrar".
- O histórico de migrações do ambiente remoto não bate com os arquivos.
- A conferência como visitante falhou.
- Apareceu um passo que não está na lista.

## O que evitar

- **A carga feita só para acrescentar uma coisa ia trocar o que já estava no ar.** A ferramenta
  gerava de novo arquivos que não saem idênticos de uma execução para outra. O "só pode sobrar",
  escrito antes, acusa. Não serve: rodar direto porque "é só uma etiqueta".
- **A ida a produção parou no meio, e o estado ficou como se tivesse terminado.** O banco entrou,
  e um passo seguinte foi barrado ou saiu do previsto. Escreva o que entrou, o que não entrou e a
  conferência a fazer antes do próximo envio.
- **"Para testar", um e-mail ou uma cobrança de verdade.** Tem efeito em gente real e não estava
  na lista. O primeiro uso real é do dono; o pedido vai para "Autorizações não dadas".

## Pronto quando

- [ ] O dono validou no ambiente local e disse sim à lista entregue.
- [ ] O envio saiu pela cadeia, com a evidência no degrau exigido ou o degrau pendente na lista.
- [ ] Cada escrita teve a conferência prévia lida, e o relato diz qual foi.
- [ ] O histórico de migrações do ambiente remoto bate com os arquivos, ou a diferença foi anotada.
- [ ] A conferência como visitante anônimo foi feita no endereço que o dono usa.
- [ ] O estado diz o que foi feito, a pedido de quem e quando, e se o commit dele foi enviado.
- [ ] O que foi barrado ou ficou fora da lista está no estado, na lista que lhe cabe.

Volte ao `SKILL.md`, §4.
