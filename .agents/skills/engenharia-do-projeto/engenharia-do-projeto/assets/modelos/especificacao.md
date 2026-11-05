<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# {{Produto}}: especificação

## Como usar este documento

Fonte da verdade da intenção: o que o produto é, o que entra nesta versão e o que fica de fora.
Aprovada pelo dono em {{AAAA-MM-DD}}. Depois dessa data o texto abaixo não é editado: o que mudar
vira registro em `docs/decisoes.md` e ganha uma nota datada logo abaixo do título. As seções têm
número fixo, porque os outros documentos as citam. O "Pronto quando" de cada fase mora em
`docs/ROTEIRO.md`; o que vale hoje, no arquivo de instruções e em `docs/ESTADO.md`.

<!-- Apague cada comentário ao preencher a seção. As seções 1, 2, 6 e 9 saem das respostas do dono,
em linguagem comum. As seções 3, 5 e 7 são proposta do agente, que o dono aprova. Seção que não se
aplica fica com o título e uma frase dizendo por quê: apagar mudaria os números. -->

## 1. O que você vai construir

{{O produto em um parágrafo: quem usa, o que faz ali, o que leva embora.}}

Tipos de coisa que existem:
- {{Coisa}}: {{o que ela tem e quem cuida dela}}.

Quem usa:
- {{Persona}}: {{o que consegue ver e fazer}}.

O que é aberto e o que é restrito: {{o que todos veem; o que só alguns veem ou pagam; por quê}}.

Nesta versão: {{condição, como "vai ao ar sem nada cadastrado e precisa de um bom estado vazio"}}.

## 2. Referências

<!-- Fique com uma das duas versões e apague a outra. Sem material, diga isso em uma frase. -->
**Com telas.** Leia todas antes de escrever interface.

| Arquivo | O que mostra |
| --- | --- |
| `{{referencias/01-nome}}` | {{tela, largura, persona, estado}} |

- É para seguir: {{disposição, hierarquia, espaçamento, palavras, estados}}.
- É enfeite: {{o que na imagem é inventado, e como será no produto}}.
- Não copie: {{textos e nomes de exemplo não são conteúdo real e não vão ao banco de produção}}.
- Marca: {{o que pode usar; o que não pode}}.

**Sem telas.** Leia todos antes de escrever o contrato.

| Arquivo | O que mostra |
| --- | --- |
| `{{exemplos/01-nome}}` | {{entrada ou saída, de quem, em que caso}} |

- É para seguir: {{nomes de campo, formatos, códigos de erro}}.
- Não copie: {{os valores são fictícios e não vão a produção}}.

## 3. Stack e decisões

<!-- Uma linha por escolha. Versão, só como intenção: o número exato fica no registro de decisões e
no arquivo de instruções. Sem proposta firme, escreva o papel e deixe o nome para o registro. -->
- **{{Papel: linguagem, framework, banco, hospedagem}}:** {{escolha ou intenção}}; {{escopo}}.
  Cuidado: confira a documentação da versão instalada para {{o que mudou entre versões}}.

## 4. O que já existe

{{O que está em uso ou em produção e qual é a fonte da verdade de cada dado; ou "nada antes".}}

1. Não altere nem apague o que existe. O que é novo leva o prefixo `{{prefixo_}}`. Se precisar
   mexer, pare e pergunte.
2. {{O que pode ser reaproveitado, com "confira antes".}}

## 5. Modelo de dados e matriz de permissões

<!-- É a seção que mais custa mudar depois. Todo limite com número e unidade. -->
- Enumeração `{{nome}}`: `{{valor_a}}`, `{{valor_b}}` ({{quem usa cada valor}}).

**`{{conjunto de dados}}`:** {{para que serve; por que é separado, se for}}.

- `{{campo}}`: {{tipo}}; {{obrigatório ou não}}; {{padrão}}; {{limite}}; {{onde se valida}}.
- Único: {{campos}}. Ao apagar {{o pai}}: {{apaga junto ou fica}}.

| Recurso | {{Persona 1}} | {{Persona 2}} | {{Persona 3}} |
| --- | --- | --- | --- |
| {{recurso}} | {{lê? altera?}} | {{lê? altera?}} | {{lê? altera?}} |

| Dado restrito | Quem pode ver | Como o teste de vazamento procura |
| --- | --- | --- |
| {{dado}} | {{personas}} | {{marcador, valor sentinela ou ausência do nome do campo}} |

Arquivos: {{onde ficam; público ou privado; limite em MB; tipos; quem envia; quem baixa e como}}.

## 6. Fluxos

### 6.1 {{Área}} ({{quem acessa}})

1. {{Passo, na ordem em que a pessoa faz, com o limite e a mensagem de erro quando houver.}}

- **Não pode acontecer: {{a regra, com os lugares por onde o dado não pode sair}}.**
- {{Cuidado técnico conhecido}} ({{o porquê}}).
- {{O que se constrói agora e só se liga depois, e quando.}}

## 7. Organização do código

{{Pastas de primeiro nível, uma por linha, com o que mora em cada uma.}}

- {{Regra com endereço: toda, só ou nunca; o quê; onde.}}

## 8. Fases

Fundação antes de tela. O "Pronto quando" de cada fase e as paradas estão em `docs/ROTEIRO.md`.

- Fase 0 · Base: {{o que entrega}}.
- Fase 1 · Dados e permissões: {{o que entrega}}.
- Fase 2 · {{nome}}: {{o que entrega}}.

## 9. Fora do escopo

- {{O que não entra nesta versão.}} {{Se o modelo de dados já deixa a porta aberta, diga.}}

## 10. Variáveis de ambiente

| Nome, sem o valor | O que é | Só no lado do servidor? |
| --- | --- | --- |
| `{{NOME}}` | {{para que serve}} | {{sim ou não}} |

## 11. Quando tiver dúvida

Pergunte antes de: {{mexer no que já existe}}; {{criar o que custa dinheiro}};
{{acrescentar dependência grande}}; {{mudar o escopo}}. Fora isso, decida e registre em
`docs/decisoes.md`.
