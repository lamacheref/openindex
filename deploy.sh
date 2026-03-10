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

load_env() {
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
}

ensure_env() {
  if [ ! -f .env ]; then
    echo "📝 Création de .env depuis .env.example..."
    if [ -f .env.example ]; then
      cp .env.example .env
    else
      cat > .env <<EOT
OPENINDEX_API_IMAGE=ghcr.io/lamacheref/openindex-api:latest
OPENINDEX_CRAWLER_IMAGE=ghcr.io/lamacheref/openindex-crawler:latest
OPENINDEX_UI_IMAGE=ghcr.io/lamacheref/openindex-ui:latest
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user
POSTGRES_PASSWORD=openindex_secure_password
POSTGRES_PORT=5432
OPENINDEX_API_PORT=8000
OPENINDEX_UI_PORT=3000
DEBUG=false
GHCR_USERNAME=
GHCR_TOKEN=
EOT
    fi
    echo "✅ .env créé. Vérifiez les images GHCR et les identifiants DB avant déploiement."
  fi
  load_env
}

ensure_ghcr_auth() {
  if [[ "${OPENINDEX_API_IMAGE:-}" != ghcr.io/* ]] && [[ "${OPENINDEX_CRAWLER_IMAGE:-}" != ghcr.io/* ]] && [[ "${OPENINDEX_UI_IMAGE:-}" != ghcr.io/* ]]; then
    return 0
  fi

  if [ -n "${GHCR_USERNAME:-}" ] && [ -n "${GHCR_TOKEN:-}" ]; then
    echo "🔐 Forçage re-login GHCR avec GHCR_USERNAME/GHCR_TOKEN..."
    docker logout ghcr.io >/dev/null 2>&1 || true
    if ! printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin >/dev/null 2>&1; then
      echo "❌ Échec docker login ghcr.io. Vérifiez GHCR_USERNAME/GHCR_TOKEN (scope package read)."
      exit 1
    fi
    return 0
  fi

  if [ -f "$HOME/.docker/config.json" ] && rg -q '"ghcr\.io"' "$HOME/.docker/config.json"; then
    return 0
  fi

  cat <<'EOT'
❌ Authentification GHCR requise.
Images privées détectées sur ghcr.io mais aucun accès n'est configuré.
Ajoutez GHCR_USERNAME et GHCR_TOKEN dans .env (token avec scope read:packages),
ou exécutez manuellement: docker login ghcr.io
EOT
  exit 1
}

pull_images() {
  ensure_env
  ensure_ghcr_auth
  echo "📦 Pull des images GHCR (api + crawler + ui + postgres)..."
  $COMPOSE_CMD pull
}

up() {
  ensure_env
  ensure_ghcr_auth
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
Note GHCR: re-login forcé si GHCR_USERNAME/GHCR_TOKEN sont définis dans .env.
EOT
    ;;
  *)
    echo "❌ Commande inconnue: ${1}"
    exit 1
    ;;
esac
