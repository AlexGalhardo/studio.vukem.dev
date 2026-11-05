> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Leia primeiro: o que é esta pasta

Serve a quem testa os scripts, não a quem conduz um projeto. É o projeto Quadra Livre (reserva das
duas quadras de um clube de bairro) visto só pelos documentos do método, no meio da Fase 2. Não há
código: os comandos de `metodo.ini` não rodam aqui. A stack foi escolhida para este produto
fictício; não é recomendação.

| Arquivo | O que olhar |
| --- | --- |
| `metodo.ini` | a escada com um degrau `n/a` e um pendente, quatro zonas com caminhos, uma regra de fronteira |
| `ESPECIFICACAO.md` | as onze seções, apertadas em dados e permissões |
| `INSTRUCOES.md` | o arquivo de instruções, com outro nome para a ferramenta não o carregar; cinco regras com `Verifica:` |
| `docs/decisoes.md` | cinco registros: um revisto por outro, um decidido pelo dono contra a recomendação |
| `docs/ROTEIRO.md` | cinco fases; a Fase 2 em andamento, com 3 de 7 itens marcados |
| `docs/ESTADO.md` | o estado com data, as cinco listas e a última rodada das verificações |
| `conversa.md` | a régua de tom. Foi construída para este exemplo: não é transcrição de conversa real |

## A saída esperada

Rode sobre uma cópia, fora de qualquer repositório: dentro de um, o git entra no diagnóstico.

```bash
E="$(mktemp -d)" && cp -R <skill>/assets/exemplo/. "$E"
python3 <skill>/scripts/situacao.py "$E" --estrito             # → código 0; as linhas abaixo
python3 <skill>/scripts/decisoes.py --projeto "$E" conferir    # → 5 registros, 0 achados; código 0
python3 <skill>/scripts/escada.py --projeto "$E" --listar      # → seis degraus; não roda nada
python3 <skill>/scripts/fronteiras.py --projeto "$E"           # → código 3
```

De `situacao.py`, fora a linha `git:`. Os três pontos estão no lugar de um número que muda quando o
arquivo de instruções do exemplo é editado:

```text
documentos:
  especificacao  ESPECIFICACAO.md  declarado
  instrucoes     INSTRUCOES.md  declarado; … caracteres (orçamento 6000)
  decisoes       docs/decisoes.md  declarado; 5 registros; último ADR-005
  roteiro        docs/ROTEIRO.md  declarado; fase atual: 2 · Reservas (3 de 7 itens)
  estado         docs/ESTADO.md  declarado; Estado em 2026-03-10
lacunas: 0
escada: 0 formato e lint (com comando); 1 tipos (com comando); 2 unidade e fronteiras (com comando); 3 banco (com comando); 4 build (n/a: sem etapa de build); 5 ponta a ponta (pendente)
atenção: nenhum item
situação provável: C (documentos presentes)
leia: SKILL.md §4
```

- `escada.py --listar`: degraus 0 a 3 com comando, o 4 `n/a` e o 5 pendente.
- `fronteiras.py` sai com 3 porque não há código na pasta: a sanidade reprova e nenhuma regra
  roda. É a defesa contra passar por vacuidade: zero arquivo lido não dá verde.
