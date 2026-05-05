#!/bin/bash
set -e

# Démarrer PocketBase en arrière-plan
exec /opt/pocketbase/pocketbase serve &

# Attendre que PocketBase soit prêt
sleep 15

# Créer un superutilisateur
/opt/pocketbase/pocketbase superuser upsert admin@example.com admin123

# Garder le container en vie
wait $!