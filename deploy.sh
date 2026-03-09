#!/usr/bin/env bash
# Script unique de déploiement Docker pour OpenIndex
# Stack canonique: postgres + crawler + ui (nginx)

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
POSTGRES_PASSWORD=openindex_secure_password
DEBUG=false
EOT
    fi
    echo "✅ .env créé. Complétez vos identifiants SMB dans config/admin_credentials.ini."
  fi
}

up() {
  ensure_env
  echo "🚀 Démarrage des services (postgres + crawler + ui)..."
  $COMPOSE_CMD up -d --build
}

down() {
  echo "🛑 Arrêt des services..."
  $COMPOSE_CMD down
}

restart() {
  down
  up
}

status() {
  $COMPOSE_CMD ps
}

logs() {
  $COMPOSE_CMD logs -f "${1:-}"
}

case "${1:-help}" in
  up) up ;;
  down) down ;;
  restart) restart ;;
  status) status ;;
  logs) logs "${2:-}" ;;
  help|-h|--help)
    cat <<EOT
Usage: ./deploy.sh [up|down|restart|status|logs [service]|help]
Services démarrés: postgres, crawler, ui
EOT
    ;;
  *)
    echo "❌ Commande inconnue: ${1}"
    exit 1
    ;;
esac
