#!/bin/bash
##
# scripts/psql_lxc.sh — Wrapper psql SSH -> base OpenIndex sur le LXC
# ---------------------------------------------------------------------------
# Le client `psql` n’étant pas installé sur les machines de dev, ce wrapper
# exécute la requête SQL **directement sur le serveur LXC** (`192.168.110.6`)
# via SSH, en utilisant le **jeu de clés SSH** commun à `deploy_lxc.sh`
# (`~/.ssh/flamachere_pro_20260511`).
#
# Principe :
#   1. un ssh préalable lit `POSTGRES_USER/DB/PASSWORD/HOST/PORT` depuis
#      `/srv/openindex/.env` sur le LXC  (stdin récupéré via `< /dev/null`
#      pour ne pas consommer un futur pipe stdin destine a psql) ;
#   2. les vars d’environnement PG sont exportées localement ;
#   3. la commande psql proprement dite est lancée sur le LXC en transmettant
#      les args (`-c`/`-f`/etc.) echappes via `printf '%q'`, ou en laissant
#      psql lire la requete depuis stdin (pipe/heredoc).
#
# ⚠️ Usage en **lecture seule** recommandé. Ce wrapper ne modifie aucune donnée
#    tant que la requete transmise ne soit pas un `UPDATE/DELETE/DROP`. Le
#    `ON_ERROR_STOP=1` arretera en cas d’erreur de syntaxe.
#
# Usage identique a psql (la requete est executee sur la base du LXC) :
#
#   ./scripts/psql_lxc.sh -c "SELECT count(*) FROM indexed_files_optimized;"
#   ./scripts/psql_lxc.sh -c "SELECT count(*) FROM files WHERE is_duplicate;"
#   ./scripts/psql_lxc.sh -f database/migrations/009_optimize_indexer_schema.sql
#   echo "SELECT 1" | ./scripts/psql_lxc.sh
#   ./scripts/psql_lxc.sh <<'SQL'
#     SELECT count(*) FROM indexed_files_optimized WHERE is_garbage;
#   SQL
#
# Variables d'environnement (facultatives, surcharge du defaut) :
#   PSQL_LXC_KEY     ssh key       (defaut ~/.ssh/flamachere_pro_20260511)
#   PSQL_LXC_HOST    host          (defaut 192.168.110.6)
#   PSQL_LXC_USER    ssh user      (defaut root)
#
# Retour : exit code identique a psql (0 = ok, !=0 = erreur SQL). La sortie
# texte brut de psql est renvoyee telle quelle sur stdout/stderr.
set -euo pipefail

SSH_KEY="${PSQL_LXC_KEY:-$HOME/.ssh/flamachere_pro_20260511}"
LXC_HOST="${PSQL_LXC_HOST:-192.168.110.6}"
LXC_USER="${PSQL_LXC_USER:-root}"
ENV_FILE="/srv/openindex/.env"

# Recupere les vars d'environnement de la base depuis le .env du LXC.
# Note: < /dev/null pour ne pas consommer un eventuel stdin pipe destine a psql.
creds="$(ssh -i "$SSH_KEY" "$LXC_USER@$LXC_HOST" < /dev/null \
  "set -e; U=\$(grep '^POSTGRES_USER' $ENV_FILE | cut -d= -f2-); D=\$(grep '^POSTGRES_DB' $ENV_FILE | cut -d= -f2-); P=\$(grep '^POSTGRES_PASSWORD' $ENV_FILE | cut -d= -f2-); H=\$(grep '^POSTGRES_HOST' $ENV_FILE | cut -d= -f2-); Port=\$(grep '^POSTGRES_PORT' $ENV_FILE | cut -d= -f2-); printf '%s|%s|%s|%s|%s' \"\$U\" \"\$D\" \"\$P\" \"\${H:-localhost}\" \"\${Port:-5432}\"")"

PGUSER_LOCAL="$(printf '%s' "$creds" | cut -d'|' -f1)"
PGDATABASE_LOCAL="$(printf '%s' "$creds" | cut -d'|' -f2)"
PGPASSWORD_LOCAL="$(printf '%s' "$creds" | cut -d'|' -f3)"
PGHOST_LOCAL="$(printf '%s' "$creds" | cut -d'|' -f4)"
PGPORT_LOCAL="$(printf '%s' "$creds" | cut -d'|' -f5)"

# Escape chaque argument pour le remote shell (on le transmet tel quel a psql).
args_remote=""
for a in "$@"; do
  esc=$(printf '%q' "$a")
  args_remote="$args_remote $esc"
done

# La requete: si des args sont fournis (-c / -f / etc), on les transmet a psql.
# Sinon, on laisse psql lire la requete depuis stdin (ex: echo "SELECT 1" | script).
base="PGPORT='$PGPORT_LOCAL' PGHOST='$PGHOST_LOCAL' PGDATABASE='$PGDATABASE_LOCAL' PGUSER='$PGUSER_LOCAL' PGPASSWORD='$PGPASSWORD_LOCAL' psql -X -q -v ON_ERROR_STOP=1 -h '$PGHOST_LOCAL' -p '$PGPORT_LOCAL' -U '$PGUSER_LOCAL' -d '$PGDATABASE_LOCAL'"
if [ "$#" -gt 0 ]; then
  ssh -i "$SSH_KEY" "$LXC_USER@$LXC_HOST" "$base $args_remote"
else
  # stdin piped: on le transmet au psql distant.
  ssh -i "$SSH_KEY" "$LXC_USER@$LXC_HOST" "$base"
fi
