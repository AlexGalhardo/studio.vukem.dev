#!/usr/bin/env bash
# Molde da variante web. Generalizado de uso real, com nomes genéricos.
# Não foi executado nesta forma: rode antes de confiar.
# Recria um banco de teste num PostgreSQL comum, sem contêiner: calço, migrações em ordem, dados
# de exemplo e testes pgTAP. Uma linha por passo; para no primeiro que falhar. Roda no bash 3.2.
# uso: bash banco-de-teste.sh      (a partir da raiz do projeto)
#   URL_DO_SERVIDOR   conexão de administração ao servidor local, direto: um intermediário de
#                     conexões não aceita criar nem apagar banco
#   BANCO_DE_TESTE    apagado e recriado a cada execução; o nome tem de terminar em _teste
#   PASTA_MIGRACOES, ARQUIVO_EXEMPLO, PASTA_TESTES   onde estão os .sql (padrões logo abaixo)
#   PULAR_EXEMPLO=1, PULAR_TESTES=1   pulam o passo    APAGAR_NO_FIM=1   apaga o banco ao terminar
set -euo pipefail

URL_DO_SERVIDOR="${URL_DO_SERVIDOR:-postgresql://postgres@127.0.0.1:5432/postgres}"
BANCO_DE_TESTE="${BANCO_DE_TESTE:-app_teste}"
PASTA_MIGRACOES="${PASTA_MIGRACOES:-banco/migracoes}"
ARQUIVO_EXEMPLO="${ARQUIVO_EXEMPLO:-banco/dados-de-exemplo.sql}"
PASTA_TESTES="${PASTA_TESTES:-banco/testes}"
passo() { printf '%-7s %s\n' "$1" "$2"; }
falha() { passo FALHOU "$1" >&2; exit 1; }

# Trava de alvo. Este script apaga o banco que recebe: só servidor local e só nome de teste.
# O banco de desenvolvimento tem dono e não passa por aqui.
forma_da_url='^([a-z]+://[^/?]*)(/[^?]*)?(\?.*)?$'
forma_do_nome='^[a-z0-9_]+_teste$'
[[ "$URL_DO_SERVIDOR" =~ $forma_da_url ]] || falha "URL_DO_SERVIDOR não tem a forma de um endereço"
BASE="${BASH_REMATCH[1]}"; CONSULTA="${BASH_REMATCH[3]}"
SERVIDOR="${BASE##*@}"; SERVIDOR="${SERVIDOR#*://}"; SERVIDOR="${SERVIDOR%%:*}"
[[ "$SERVIDOR" == "127.0.0.1" || "$SERVIDOR" == "localhost" ]] \
  || falha "o servidor é \"$SERVIDOR\": este script apaga e recria banco, e só roda no local"
[[ "$BANCO_DE_TESTE" =~ $forma_do_nome ]] || falha "BANCO_DE_TESTE precisa terminar em _teste"
URL_DE_TESTE="$BASE/$BANCO_DE_TESTE$CONSULTA"
PSQL=(psql -X -q -v ON_ERROR_STOP=1)
aplicar() {   # $1 = rótulo; $2 = arquivo, aplicado numa transação só
  "${PSQL[@]}" --single-transaction -d "$URL_DE_TESTE" -f "$2" >/dev/null || falha "$1 ($2)"
  passo ok "$1"
}

# 1. Banco do zero.
PGOPTIONS="--client-min-messages=warning" "${PSQL[@]}" -d "$URL_DO_SERVIDOR" \
  -c "select pg_terminate_backend(pid) from pg_stat_activity
      where datname = '$BANCO_DE_TESTE' and pid <> pg_backend_pid()" \
  -c "drop database if exists \"$BANCO_DE_TESTE\"" \
  -c "create database \"$BANCO_DE_TESTE\"" >/dev/null || falha "não recriei $BANCO_DE_TESTE"
passo ok "banco $BANCO_DE_TESTE recriado em $SERVIDOR"

# 2. Calço: o mínimo para um PostgreSQL comum ter o que a variante supõe. Não cria nada do produto.
"${PSQL[@]}" --single-transaction -d "$URL_DE_TESTE" >/dev/null <<'SQL' || falha "calço"
do $$ declare papel text; begin
  foreach papel in array array['anon', 'authenticated', 'service_role'] loop
    if not exists (select 1 from pg_roles where rolname = papel) then
      execute format('create role %I nologin', papel); end if;
  end loop;
end $$;
alter role service_role bypassrls;
create schema auth;
create table auth.users (id uuid primary key, email text unique);
create function auth.uid() returns uuid language sql stable as $$
  select nullif(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub', '')::uuid
$$;
grant usage on schema auth, public to anon, authenticated, service_role;
-- Privilégios de fábrica como os da plataforma: objeto novo nasce aberto aos três papéis.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public
  grant all on sequences to anon, authenticated, service_role;
create extension if not exists pgtap;
SQL
passo ok "calço (três papéis, esquema auth, função de identidade, privilégios de fábrica, pgTAP)"

# 3. Migrações, em ordem lexicográfica fixa. Sem mapfile: o bash 3.2 não tem.
total=0
while IFS= read -r arquivo; do
  aplicar "migração $(basename "$arquivo")" "$arquivo"; total=$((total + 1))
done < <(find "$PASTA_MIGRACOES" -maxdepth 1 -name '*.sql' 2>/dev/null | LC_ALL=C sort)
[[ "$total" -gt 0 ]] || falha "nenhuma migração em $PASTA_MIGRACOES: zero arquivos não é verde"

# 4. Dados de exemplo.
if [[ "${PULAR_EXEMPLO:-0}" == "1" ]]; then passo pulou "dados de exemplo (PULAR_EXEMPLO=1)"
elif [[ -f "$ARQUIVO_EXEMPLO" ]]; then aplicar "dados de exemplo" "$ARQUIVO_EXEMPLO"
else passo pulou "dados de exemplo: não achei $ARQUIVO_EXEMPLO"; fi

# 5. Testes. Falha é erro do psql, "not ok" ou o aviso do pgTAP de que o plano não bateu.
if [[ "${PULAR_TESTES:-0}" == "1" ]]; then passo pulou "testes (PULAR_TESTES=1)"; else
  total=0
  while IFS= read -r arquivo; do
    nome="$(basename "$arquivo")"; total=$((total + 1))
    saida="$("${PSQL[@]}" -A -t -d "$URL_DE_TESTE" -f "$arquivo" 2>&1)" \
      || { printf '%s\n' "$saida" >&2; falha "teste $nome"; }
    if printf '%s\n' "$saida" | grep -E '^(not ok|# )' >&2; then falha "teste $nome"; fi
    passo ok "teste $nome: $(printf '%s\n' "$saida" | grep -c '^ok ') afirmações"
  done < <(find "$PASTA_TESTES" -maxdepth 1 -name '*.sql' 2>/dev/null | LC_ALL=C sort)
  [[ "$total" -gt 0 ]] || falha "nenhum teste em $PASTA_TESTES"
fi
if [[ "${APAGAR_NO_FIM:-0}" == "1" ]]; then
  "${PSQL[@]}" -d "$URL_DO_SERVIDOR" -c "drop database if exists \"$BANCO_DE_TESTE\"" >/dev/null
  passo ok "banco $BANCO_DE_TESTE apagado"
else passo ok "banco $BANCO_DE_TESTE mantido para inspeção"; fi

# O que adaptar:
# - Os caminhos e o nome do banco de teste; este script é o comando do degrau do banco.
# - O calço: acrescente só o que a plataforma do projeto traz pronto e as migrações usam. Ele
#   imita, não é: rode os mesmos testes também no ambiente real da plataforma.
# - Sem pgTAP instalado no servidor o passo do calço falha: instale a extensão antes.
