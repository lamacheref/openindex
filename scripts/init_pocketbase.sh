#!/bin/bash
set -e

# Créer le répertoire de données avec les bonnes permissions
mkdir -p /pb/pb_data
chown -R 5678:5678 /pb/pb_data
chmod -R 755 /pb/pb_data

# Démarrer PocketBase
exec /opt/pocketbase/pocketbase serve --dir /pb/pb_data