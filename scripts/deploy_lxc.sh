#!/bin/bash
set -e

ssh -i "$HOME/.ssh/flamachere_pro_20260511" root@192.168.110.6 "
cd /srv/OpenIndex
git stash
git pull
git stash pop || true

find . -name __pycache__ -exec rm -rf {} + 2>/dev/null

ENV_FILE=/srv/openindex/.env

# Mettre à jour les dépendances Python
source .venv/bin/activate
pip install --upgrade -r requirements/dev.txt xxhash 2>&1 | tail -3

# Rebuilder le frontend (skip si npm absent)
if command -v npm &>/dev/null; then
  npm install --omit=dev 2>/dev/null || true
  npm run build:frontend
else
  echo \"⚠ npm not installed, skipping frontend build\"
fi

# Appliquer les migrations
for f in database/migrations/*.sql; do
  echo \"  Running \$f\"
  PGPASSWORD=\$(grep POSTGRES_PASSWORD \$ENV_FILE | cut -d= -f2) psql -h localhost -U \$(grep POSTGRES_USER \$ENV_FILE | cut -d= -f2) -d \$(grep POSTGRES_DB \$ENV_FILE | cut -d= -f2) -f \"\$f\" 2>/dev/null || true
done

# Redémarrer les services
systemctl daemon-reload
systemctl restart openindex-api openindex-indexer-worker openindex-indexer-scheduler
"
