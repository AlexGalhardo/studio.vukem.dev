<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
## Ida a produção: {{mudança}} ({{AAAA-MM-DD}})

<!-- Só quando a ida a produção leva banco ou dados; ida só de código leva a lista na conversa.
     Grave em docs/planos/, com a data no nome. Marque cada caixa depois de ver a saída, não antes.
     Pare no primeiro resultado fora do previsto e anote em "Não feito ou com o dono". O porquê de
     cada passo está em references/producao.md. Apague este comentário, o que não se aplica e, a
     partir da segunda ida a produção, o bloco "Se é a primeira vez". -->

### A lista autorizada

O dono autorizou em {{AAAA-MM-DD}}, com "{{a palavra dele}}", esta lista e só ela:

1. Banco: aplicar as migrações {{nomes}}, nesta ordem.
2. Dados: {{a carga}}, depois da simulação.
3. Código: enviar ao ramo {{o ramo que implanta}}.
4. Conferir como visitante. O commit do estado: {{enviado no fim, ou fica no ambiente local}}.

Dito a ele na lista: sem volta, {{o quê, ou "nada"}}; degrau pendente, {{qual, ou "nenhum"}};
revisão, {{feita, ou cortada em modo enxuto}}; passos dele que vêm antes, {{quais, ou "nenhum"}}.

### Portões (todos antes de tocar o ambiente remoto)

- [ ] Validado no ambiente local pelo dono em {{AAAA-MM-DD}}.
- [ ] `escada.py --evidencia`: {{a linha "vale até o degrau …; exigido …", colada}}.
- [ ] Mudança em zona sensível: a revisão está no relato, ou o corte foi dito na lista.
- [ ] Depois de `git fetch`, `envio.py` sem `ACHADO`: nada indevido sai, nada novo do outro lado.
- [ ] `docs/ESTADO.md` relido do disco, e "Ainda não aplicado" conferido no ambiente remoto.

### 1. Banco

- [ ] Conferência prévia: migrações aplicadas do zero no ambiente local (degrau 3); histórico do
      ambiente remoto igual aos arquivos até {{a última aplicada}}. {{Simulação, se houver.}}
- [ ] Aplicadas uma por arquivo, na ordem, pelo canal de migrações: {{lista}}.
- [ ] Histórico conferido depois: {{igual aos arquivos, ou a divergência, anotada no estado}}.
- [ ] Conferido por consulta o que um aviso da migração diria: {{o quê}}.

### 2. Dados

- Só pode sobrar na simulação: {{as linhas esperadas}}.
- Pare se aparecer: {{a linha que indica escrita não prevista}}.
- [ ] Simulação pelo mesmo caminho da escrita, lida linha a linha: {{o que sobrou}}.
- [ ] Escrita de verdade, com o resumo conferido: {{alvo e contagem}}.

### 3. Código

- [ ] `escada.py --evidencia && envio.py && git push`, no ramo {{o ramo que implanta}}.
- [ ] CI verde e implantação concluída: {{como foi visto}}.

### Depois

- [ ] Conferido sem sessão, em {{o endereço que o dono usa}}: {{o que contar; o que não aparece}}.
- [ ] Cache: {{expira sozinho em tal prazo, pede nova implantação ou foi pedido ao dono}}.
- [ ] `docs/ESTADO.md` atualizado: aplicado até, a pedido de quem, o que conferir antes da próxima.
- [ ] Commit do estado: {{enviado, como último item da lista, ou ficou no ambiente local}}.

### Não feito ou com o dono

- {{Ação barrada, fora da lista ou não autorizada, e o que conferir antes da próxima.}}

### Se é a primeira vez

- [ ] Banco migrado antes do primeiro build.
- [ ] Variáveis na hospedagem, em todo ambiente em que o build roda (passo do dono).
- [ ] O dado de que produção precisa foi por migração própria; dados de exemplo não foram.
- [ ] Primeiro administrador: só depois do primeiro login, com autorização própria.
- [ ] Configuração de painel testada pelo dono no primeiro uso real: {{qual}}.
- [ ] Cada comando contra o ambiente remoto confirmado com o dono ao lado.
