#!/bin/bash
set -e

ssh -i "$HOME/.ssh/flamachere_pro_20260511" root@192.168.110.6 "
cd /srv/OpenIndex
git pull

find . -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Copier les fichiers frontend vers le dossier servi par nginx
cp frontend/index.html /var/www/html/index.html
cp frontend/indexer-monitoring.html /var/www/html/indexer-monitoring.html
cp frontend/archive-monitoring.html /var/www/html/archive-monitoring.html
cp frontend/assets/* /var/www/html/assets/ 2>/dev/null || true

# Redémarrer les services
systemctl restart openindex-api openindex-indexer-worker
"
