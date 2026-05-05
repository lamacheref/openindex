#!/bin/bash
set -e

# Attendre que PocketBase soit prêt
sleep 10

# Créer un utilisateur admin via l'API interne
# Comme PocketBase force HTTPS, nous allons utiliser la commande interne
/opt/pocketbase/pocketbase superuser upsert admin@example.com admin123

# Garder le container en vie
tail -f /dev/null