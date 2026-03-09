#!/bin/bash
# Script de déploiement pour la stack moderne FastAPI + VanillaJS

set -e

echo "🚀 OpenIndex Modern Stack Deployment"
echo "=================================="

# Vérifier si Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

# Créer les répertoires nécessaires
mkdir -p logs frontend nginx

# Créer le fichier .env si inexistant
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env..."
    cat > .env << EOF
# Configuration PostgreSQL
POSTGRES_PASSWORD=openindex_secure_password_$(date +%s)
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user

# Configuration SMB (à adapter)
SMB_SERVER=172.16.252.34
SMB_SHARE=Public\\SEPM
SMB_DOMAIN=SMIDEN
SMB_USERNAME=adminsmiden
SMB_PASSWORD=

# Configuration API
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
LOG_LEVEL=info

# Configuration Frontend
FRONTEND_PORT=3000

# Configuration Crawler (optionnel)
CRAWLER_WORKERS=4
CRAWLER_DELAY=0.1
CRAWLER_MAX_DEPTH=
LARGE_FILE_THRESHOLD=104857600
DEBUG_MODE=false

# Configuration Admin (optionnel)
PGADMIN_EMAIL=admin@openindex.local
PGADMIN_PASSWORD=admin123
EOF
    echo "✅ Fichier .env créé. Adaptez-le selon votre environnement."
fi

# Fonctions de déploiement
deploy_modern() {
    echo "🚀 Déploiement de la stack moderne..."
    docker-compose -f docker-compose.modern.yml up -d --build
    echo ""
    echo "🌐 Services déployés:"
    echo "   🎨 Frontend: http://localhost:3000"
    echo "   🔌 API: http://localhost:8000"
    echo "   📚 Documentation API: http://localhost:8000/docs"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Admin pgAdmin: http://localhost:5050"
}

deploy_api_only() {
    echo "🔌 Déploiement de l'API uniquement..."
    docker-compose -f docker-compose.modern.yml up -d --build api postgres
    echo ""
    echo "🔌 Services déployés:"
    echo "   🔌 API: http://localhost:8000"
    echo "   📚 Documentation API: http://localhost:8000/docs"
    echo "   🐘 Base de données: localhost:5432"
}

deploy_frontend_only() {
    echo "🎨 Déploiement du frontend uniquement..."
    docker-compose -f docker-compose.modern.yml up -d --build frontend
    echo ""
    echo "🎨 Services déployés:"
    echo "   🎨 Frontend: http://localhost:3000"
}

deploy_with_crawler() {
    echo "🔍 Déploiement complet avec crawler..."
    docker-compose -f docker-compose.modern.yml --profile crawler up -d --build
    echo ""
    echo "🌐 Services déployés:"
    echo "   🎨 Frontend: http://localhost:3000"
    echo "   🔌 API: http://localhost:8000"
    echo "   📚 Documentation API: http://localhost:8000/docs"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Admin pgAdmin: http://localhost:5050"
    echo "   🔍 Crawler: en cours d'exécution..."
}

stop_services() {
    echo "🛑 Arrêt des services..."
    docker-compose -f docker-compose.modern.yml down
}

show_status() {
    echo "📊 État des services:"
    docker-compose -f docker-compose.modern.yml ps
}

logs_service() {
    local service=$1
    echo "📝 Logs du service $service:"
    docker-compose -f docker-compose.modern.yml logs -f $service
}

# Menu d'aide
show_help() {
    echo "OpenIndex Modern Stack Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  modern       Déploie toute la stack moderne (API + Frontend)"
    echo "  api          Déploie uniquement l'API FastAPI"
    echo "  frontend     Déploie uniquement le frontend VanillaJS"
    echo "  crawler      Déploie la stack complète avec le crawler"
    echo "  stop         Arrête tous les services"
    echo "  status       Affiche l'état des services"
    echo "  logs [service]  Affiche les logs d'un service"
    echo "  help         Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 modern              # Stack complète"
    echo "  $0 api                 # API uniquement"
    echo "  $0 frontend            # Frontend uniquement"
    echo "  $0 crawler             # Stack avec crawler"
    echo "  $0 logs api            # Logs de l'API"
    echo "  $0 stop                # Arrêter tout"
}

# Analyse des arguments
COMMAND=${1:-help}

case $COMMAND in
    modern)
        deploy_modern
        ;;
    api)
        deploy_api_only
        ;;
    frontend)
        deploy_frontend_only
        ;;
    crawler)
        deploy_with_crawler
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        logs_service $2
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Commande inconnue: $COMMAND"
        show_help
        exit 1
        ;;
esac
