<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Plano-contrato · Fase {{número}} · {{nome}}

<!-- Só para o peso pesado. Grave em docs/planos/. Apague os comentários ao preencher. -->

Escrito em {{AAAA-MM-DD}}, sobre o commit {{abreviado}}, com a árvore limpa. É o contrato entre
quem planeja e os {{quantos}} pacotes, que rodam em sequência na mesma árvore. **Os nomes de
arquivos, tipos, funções, propriedades, parâmetros e marcações de teste daqui são definitivos:**
quem precisar mudar um deles muda aqui primeiro.

- **Fontes:** {{o levantamento, com as seções; os documentos lidos}}.
- **Revisão do plano:** {{onde está a decisão de cada achado, ou "ainda não revisto"}}.
- **Regras de trabalho, que valem para todo pacote:** {{lista, cada uma com a consequência}}.

## Errata (prevalece sobre qualquer trecho abaixo)

<!-- Fica vazia até a primeira correção. Cada item: E-1, a regra nova em uma frase, por quê e de
     quem é a decisão, cada lugar que muda e a consequência aceita. -->

Nenhuma até {{AAAA-MM-DD}}.

## 0. O que foi medido

| # | Medição | Onde está o script | Resultado | Vale para |
| --- | --- | --- | --- | --- |
| M1 | {{o que foi medido}} | {{caminho, ou o bloco abaixo}} | {{número}} | {{a sonda: repetir no build real}} |

## 1. Decisões de arquitetura

### A-01 · {{a decisão, em uma frase}}

{{Um parágrafo concreto: o que se faz, dito de modo que se ache no código.}}

- **Motivo:** {{por quê}}. **Fonte:** {{seção do levantamento, medição, registro}}.
- **O que isto não resolve:** {{limite}}. **Custos aceitos:** {{quais}}.
- **Como validar:** {{comando}}, que deve dar {{saída esperada}}.
- **Plano B:** se {{gatilho}}, {{o que fazer}}, e registrar.

## 2. Mapa de arquivos

<!-- Marca: N novo, A alterado, X apagado. Cada arquivo tem um dono só; quando outro pacote
     precisa encostar, diga na linha o mínimo autorizado e quem reescreve depois. -->

| Pacote | Arquivo | Marca | Papel |
| --- | --- | --- | --- |
| P1 | {{caminho}} | N | {{papel}} |

## 3. Contratos

{{Tipos, assinaturas e propriedades, com os nomes definitivos.}} {{As marcações que os testes usam
para achar cada elemento: papel e nome acessível primeiro; identificador de teste onde não bastar.}}

## 4. Dados

{{O que cada leitura seleciona.}} {{As chaves de cache e quem usa cada uma.}} {{O que muda nos
dados de exemplo.}}

## 5. Segurança

### 5.1 O caminho do dado restrito

{{Do banco até a resposta: por onde passa, quem lê, onde é barrado.}}

### 5.2 O que não pode acontecer, e o teste que prova

| # | Não pode acontecer | Teste que prova | O que este teste não prova |
| --- | --- | --- | --- |
| 1 | {{a proibição}} | {{arquivo e nome do teste}} | {{o limite, dito com franqueza}} |

### 5.3 Regras do teste de fronteiras

<!-- Cada regra entra no pacote que cria o arquivo que ela protege, nunca antes: regra sem arquivo
     não protege nada e derruba o degrau. -->

| Regra | Arquivo que ela protege | Pacote em que entra |
| --- | --- | --- |
| {{nome da regra}} | {{caminho}} | {{pacote}} |

## 6. Pacotes

Ordem fixa, um por vez, na mesma árvore. Todo pacote termina com os degraus 0 a 2 passando.
Vale para todos: {{como obter a sessão de cada persona; o que não é divergência das referências}}.

### P1 · {{nome}}

- **Objetivo:** {{o que fica pronto, e o estado ao fim}}.
- **Arquivos:** os do P1 na parte 2.
- **Passos, em ordem:** {{lista numerada}}.
- **Aceite:** o bloco abaixo, rodado como escrito.
- **Entrega ao P2:** {{o que fica pronto e o que o relatório precisa dizer}}.

```bash
{{comando}}     # → {{saída esperada}}
```

## 7. Plano de testes

{{As camadas e o pacote dono de cada uma.}} {{A rodada final, em passos ordenados: cada passo
depende do anterior.}}

## 8. Registros novos

<!-- Sem número de registro: o número nasce com decisoes.py novo, e um número escrito antes faz
     decisoes.py conferir acusar este plano. Até lá, o código cita a decisão por A-01. -->

| Vem de | Título, que é a própria decisão | A decisão, em uma frase | Registro que atualiza ou cita |
| --- | --- | --- | --- |
| A-01 | {{título}} | {{decisão}} | {{registro existente, ou "nenhum"}} |

## 9. Rastreabilidade

| Requisito | O que pede | Pacote e arquivos | Prova |
| --- | --- | --- | --- |
| R-01 | {{requisito}} | {{pacote e caminho}} | {{teste ou comando de aceite}} |

- **Sem arquivo dono, de propósito:** {{requisitos cuja regra é não fazer}}.
- **Pendências com fase-alvo:** {{o destino de cada uma: pacote, fora da fase ou já resolvida}}.

## 10. Perguntas em aberto

Nada aqui bloqueia a implementação: cada ponto já tem a decisão padrão que os pacotes seguem.

| # | Ponto, como o dono vê | Decisão padrão adotada | Se o dono quiser diferente |
| --- | --- | --- | --- |
| 1 | {{o que a pessoa vê}} | {{padrão}} | {{o que muda, onde, e se pede migração ou revê registro}} |
