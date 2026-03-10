#!/usr/bin/env bash
# Script unique de déploiement Docker pour OpenIndex
# Stack canonique: postgres + api + crawler + ui

set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo "❌ Docker Compose n'est pas disponible (docker-compose ou docker compose)."
  exit 1
fi

ensure_env() {
  if [ ! -f .env ]; then
    echo "📝 Création de .env depuis .env.example..."
    if [ -f .env.example ]; then
      cp .env.example .env
    else
      cat > .env <<EOT
OPENINDEX_API_IMAGE=ghcr.io/OWNER/openindex-api:latest
OPENINDEX_CRAWLER_IMAGE=ghcr.io/OWNER/openindex-crawler:latest
OPENINDEX_UI_IMAGE=ghcr.io/OWNER/openindex-ui:latest
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user
POSTGRES_PASSWORD=openindex_secure_password
POSTGRES_PORT=5432
OPENINDEX_API_PORT=8000
OPENINDEX_UI_PORT=3000
DEBUG=false
EOT
    fi
    echo "✅ .env créé. Vérifiez les images GHCR et les identifiants DB avant déploiement."
  fi
}

pull_images() {
  ensure_env
  echo "📦 Pull des images GHCR (api + crawler + ui + postgres)..."
  $COMPOSE_CMD pull
}

up() {
  ensure_env
  echo "🚀 Déploiement complet de la stack (postgres + api + crawler + ui)..."
  $COMPOSE_CMD up -d
}

down() {
  echo "🛑 Arrêt des services..."
  $COMPOSE_CMD down
}

restart() {
  down
  pull_images
  up
}

status() {
  $COMPOSE_CMD ps
}

logs() {
  $COMPOSE_CMD logs -f "${1:-}"
}

case "${1:-help}" in
  pull) pull_images ;;
  up) up ;;
  down) down ;;
  restart) restart ;;
  status) status ;;
  logs) logs "${2:-}" ;;
  help|-h|--help)
    cat <<EOT
Usage: ./deploy.sh [pull|up|down|restart|status|logs [service]|help]
Services: postgres, api, crawler, ui
EOT
    ;;
  *)
    echo "❌ Commande inconnue: ${1}"
    exit 1
    ;;
esac
