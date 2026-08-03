#!/bin/bash
set -e

ssh -i "$HOME/.ssh/flamachere_pro_20260511" root@192.168.110.6 "
cd /srv/OpenIndex

# Fetch sans écrire le working tree, puis reset hard pour éviter les conflits
# de stash pop (le repo peut avoir des mods locaux non trackées).
git fetch origin main

# Si des changements locaux non commités bloquent le reset, stash + pop safe.
git stash push -u -m \"deploy-precheck\" 2>/dev/null || true
git reset --hard origin/main
git stash pop 2>/dev/null || git reset --hard origin/main

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

# Synchroniser le frontend vers la racine servie par nginx (/var/www/html).
# sans cela, le build tailwind (et les HTML) sont dans frontend/ mais nginx
# sert /var/www/html -> les changements frontend seraient ignorés.
echo \"-> rsync frontend/ -> /var/www/html\"
rsync -a --delete --exclude 'src' frontend/ /var/www/html/ 2>/dev/null || true

# Appliquer les migrations
for f in database/migrations/*.sql; do
  echo \"  Running \$f\"
  PGPASSWORD=\$(grep POSTGRES_PASSWORD \$ENV_FILE | cut -d= -f2) psql -h localhost -U \$(grep POSTGRES_USER \$ENV_FILE | cut -d= -f2) -d \$(grep POSTGRES_DB \$ENV_FILE | cut -d= -f2) -f \"\$f\" 2>/dev/null || true
done

# Recharger la config systemd et redémarrer les services
systemctl daemon-reload
systemctl restart openindex-api openindex-indexer-worker openindex-indexer-scheduler
"
