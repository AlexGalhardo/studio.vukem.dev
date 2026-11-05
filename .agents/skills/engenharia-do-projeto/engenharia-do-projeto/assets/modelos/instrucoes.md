<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# {{nome do produto}}

{{O que é, em um parágrafo: produto, para quem, em que versão está.}} A especificação está em
`ESPECIFICACAO.md`.

## Stack

{{a preencher}}

## Comandos

{{a preencher}}

## Como trabalhamos

1. No começo de toda sessão: este projeto usa a skill `engenharia-do-projeto`; acione-a, e ela roda o
   diagnóstico. Sem ela: `python3 ferramentas/metodo/situacao.py`, se a pasta existir; senão,
   responda a cinco perguntas (há código? quais documentos existem? que fase está em andamento? o
   estado é mais velho que o último commit? o que `git status` mostra?) e leia `docs/ESTADO.md` do
   disco.
2. O ciclo: mapear, combinar, implementar com os testes junto, subir a escada, revisar, fechar.
3. O portão do commit: os degraus 0 a 2 ligados ao commit por `&&`
   (`python3 ferramentas/metodo/escada.py --ate 2 && git commit`, ou os comandos de `[escada]` em
   `metodo.ini`, na ordem, ligados por `&&`).
4. Ambiente remoto só com a lista que o dono autorizou; enviar ao ramo `{{ramo que implanta}}` é ir
   a produção.
5. Segredo não se repete: nem na conversa, nem no git, nem em documento.
6. Toda entrega fecha com os três blocos (Decidi sem perguntar, Preciso de você, Como conferir);
   todo relato separa "Rodei e vi", "Inferi" e "Não rodei".
7. Pergunte antes de: {{lista do projeto}}. Só o dono faz: {{lista do projeto}}. No resto, decida e
   registre em `docs/decisoes.md`.
8. O perfil do dono e a palavra de liberação estão em `docs/ESTADO.md`, em "Como trabalhamos aqui".

## Regras inegociáveis

{{a preencher}}

## Onde ficam as coisas

{{a preencher}}

## Antes de mexer, leia

{{a preencher}}
