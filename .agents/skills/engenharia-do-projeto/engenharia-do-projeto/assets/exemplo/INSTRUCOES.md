> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Quadra Livre

Reserva das duas quadras de um clube de bairro, em blocos de 30 minutos. Está na Fase 2, e os
sócios ainda não usam. A especificação está em `ESPECIFICACAO.md`.

## Stack

Python, com um framework web completo na versão de suporte longo (ADR-001), e PostgreSQL; permissão
na camada de aplicação. Stack escolhida para este produto fictício; não é recomendação.

## Comandos

- `python manage.py runserver`: abre em `localhost:8000` (precisa do PostgreSQL local no ar).
- `python3 ferramentas/metodo/escada.py --exigido`: sobe a escada (comandos em `metodo.ini`).

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
4. Ambiente remoto só com a lista que o dono autorizou; enviar ao ramo `main` é ir a produção.
5. Segredo não se repete: nem na conversa, nem no git, nem em documento.
6. Toda entrega fecha com os três blocos (Decidi sem perguntar, Preciso de você, Como conferir);
   todo relato separa "Rodei e vi", "Inferi" e "Não rodei".
7. Pergunte antes de: mudar quem vê dado restrito; e-mail real a sócio; gasto; mudança de escopo.
   Só o dono faz: contas, domínio e chaves. No resto, decida e registre em `docs/decisoes.md`.
8. O perfil do dono e a palavra de liberação estão em `docs/ESTADO.md`, em "Como trabalhamos aqui".

## Regras inegociáveis (especificação §7; nos dados restritos vale o ADR-002)

- Só `socios/contato.py` e `socios/tesouraria.py` leem telefone, situação de pagamento e observação
  (sem exceção, ADR-002). Verifica: regra de fronteira `contato-so-pela-porta` e teste de vazamento.
- Toda ação de `reservas/` e de `socios/` começa pela guarda de `reservas/permissoes.py`, mesmo que
  a tela esconda o botão (exceção: a grade de horários livres). Verifica: teste por persona.
- Toda conta de horário é em blocos de 30 minutos e mora em `reservas/regras.py`: nada compara
  intervalos (ADR-005, que revê o ADR-003). Verifica: `test_dois_socios_mesmo_bloco`.
- Nunca crie prazo, multa nem limite para cancelar (`reservas/regras.py`, `pode_cancelar()`; decisão
  do dono, ADR-004). Verifica: revisão manual, até existir o teste do item 4 da Fase 2.
- Só `quadra/segredos.py` lê segredo do ambiente (sem exceção). Verifica: revisão manual (hoje:
  nenhuma leitura de variável de ambiente fora dele).

## Onde ficam as coisas

- `quadra/`: configuração do projeto. `segredos.py` = o único que lê segredo.
- `contas/`: entrar e sair.
- `socios/`: cadastro. `contato.py` e `tesouraria.py` = as portas de leitura do dado restrito.
- `reservas/`: grade e reservas. `regras.py` = puro, com teste ao lado; `permissoes.py` = a guarda;
  `migrations/` = todas as migrações, só de acréscimo; `tests/` = por persona e de vazamento.
- `ferramentas/metodo/`: cópia dos scripts do método; não se edita à mão.

## Antes de mexer, leia

- Leia os títulos de `docs/decisoes.md` antes de mudar stack, configuração, reserva ou cancelamento.
- Leia `docs/ESTADO.md` do disco antes de qualquer ação no ambiente remoto.
- Leia a documentação da versão instalada antes de usar um recurso do framework (ADR-001).
