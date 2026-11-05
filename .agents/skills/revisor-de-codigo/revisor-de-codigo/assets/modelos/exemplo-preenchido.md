<!-- EXEMPLO FICTÍCIO. A loja, os arquivos, as linhas e os números foram inventados para mostrar o
     formato. Não copie os achados: copie a forma. -->
# Exemplo preenchido · cupom de desconto no carrinho de uma loja de plantas

## Um achado, como o revisor escreveu

### S-01 · crítico · O percentual do desconto é lido do navegador

- **Onde:** `src/pagamento/aplicar-cupom.ts:18`
- **Descrição:** a ação confere que o código do cupom existe, mas usa o campo `percentual` que
  veio no corpo da requisição em vez do percentual gravado no cupom.
- **Cenário de falha:** cupom válido de 10%, enviado por chamada direta com `percentual=100` →
  o pedido fecha com total zero.
- **Correção sugerida:** ler o percentual do cupom no banco; tirar o campo da entrada; teste com
  o corpo adulterado.

**Veredito:** confirmado, crítico mantido. Caminho: `aplicar-cupom.ts:18` passa o campo do corpo
para `total.ts:33`, que multiplica sem consultar o cupom; nada entre os dois confere o valor.

## O relatório ao dono

**Posso subir?** Sim, nesta ordem: a migration, depois o código.

### O que foi revisado, e como

- Do ponto em que o ramo `cupom` se separou do principal até a árvore de trabalho: 14 arquivos,
  +420 -60 linhas.
- Lentes: banco e implantação, segurança e fronteiras, comportamento, testes. 13 leituras: 4
  revisores, 6 verificadores, 1 corretor, 1 reverificador e 1 validador.

### A contagem

6 achados: 5 confirmados (crítico 1, grave 0, médio 3, baixo 1), 1 refutado, 0 não verificados.
Rebaixados na verificação: 2 (um de grave para médio, um de médio para baixo).
Depois das correções: 5 resolvidos, o crítico só na rodada 2; 0 regressões.

### Confirmados e corrigidos

- **Dava para fechar um pedido de graça adulterando o desconto** (crítico;
  `src/pagamento/aplicar-cupom.ts:18`). Correção: o percentual sai do cupom gravado. Na
  reverificação a primeira correção não passou: com cupom de valor fixo, o campo do navegador
  ainda era somado. Rodada 2: o campo saiu da entrada. Entradas tentadas: 100, negativo, cupom de
  valor fixo, cupom inexistente. Resolvido.
- **Subir o código antes da migration derruba o carrinho** (de grave para médio: a esteira aplica
  migrations antes do código, `deploy.yml:22`; o risco é a subida manual;
  `src/carrinho/consulta.ts:41`). Correção: a ordem ficou escrita na lista de subida.
- **Cupom vencido some do carrinho sem aviso** (médio; `src/carrinho/Resumo.tsx:57`). Quem
  aplicou ontem reabre hoje e vê o total cheio. Correção: a linha "cupom vencido" com botão de
  remover. Resolvido.
- **O teste "aplica o desconto" passava com o desconto zerado** (médio;
  `src/carrinho/total.test.ts:30`). Ele comparava o total com o valor devolvido pela própria
  função. Correção: valor esperado escrito à mão. Com a conta invertida, agora falha.
- **Código colado com espaço no fim é recusado** (de médio para baixo: a tela já corta o espaço,
  `CampoCupom.tsx:24`; só a chamada direta envia; `src/pagamento/validar.ts:12`). Correção: a
  ação também corta. Resolvido.

### Confirmados e não corrigidos: para você decidir

Nenhum.

### Refutados

- "Remover cupom não tem guarda" (grave alegado): a guarda é a primeira linha de `comSessao`, que
  envolve a ação em `src/pagamento/remover-cupom.ts:7`, e o carrinho sai da sessão.

### Não verificados, e deixados de fora de propósito

- Não verificados: nenhum.
- De fora: o arredondamento do frete, defeito antigo que a mudança não toca; anotado para depois.

### Validação

- **Verifiquei rodando:** lint e tipos sem erro; testes de unidade, 184 de 184 em 37 arquivos;
  ponta a ponta do carrinho, 8 de 9: "aplica cupom" falhou por tempo esgotado e, isolado, passou
  em 4 s. As duas saídas estão abaixo. Não investiguei a causa: não conto como verde.
- **Só li:** a migration (coluna opcional, sem efeito nas linhas existentes) e a ordem de subida.
- **Não conferi:** as telas em 375 px de largura; não havia ferramenta de navegador.
- **Relatado por agente, não conferido por mim:** nada. Reli o caminho do crítico e a diferença
  das 5 correções.

### Para subir

1. Aplicar a migration `0031_cupom.sql`: o código antigo ignora a coluna nova.
2. Subir o código. Na ordem inversa, toda abertura do carrinho dá erro até a migration rodar.

Revisão por leitura não prova ausência de defeito: ela cobriu as lentes e os arquivos acima.
