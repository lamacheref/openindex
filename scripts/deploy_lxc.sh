#!/bin/bash
set -e

ssh -i "$HOME/.ssh/flamachere_pro_20260511" root@192.168.110.6 "
cd /srv/OpenIndex
git stash
git pull
git stash pop || true

find . -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Mettre à jour les dépendances Python
source .venv/bin/activate
pip install --upgrade -r requirements/dev.txt xxhash

# Rebuilder le frontend
npm install --omit=dev 2>/dev/null || true
npm run build:frontend

# Appliquer les migrations
for f in database/migrations/*.sql; do
  echo \"Running \$f\"
  PGPASSWORD=\$(grep POSTGRES_PASSWORD .env | cut -d= -f2) psql -h localhost -U \$(grep POSTGRES_USER .env | cut -d= -f2) -d \$(grep POSTGRES_DB .env | cut -d= -f2) -f \"\$f\" 2>/dev/null || true
done

# Redémarrer les services
systemctl daemon-reload
systemctl restart openindex-api openindex-indexer-worker openindex-indexer-scheduler
"
