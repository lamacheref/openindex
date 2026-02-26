#!/bin/bash
# Scripts de déploiement pour la stack OpenIndex

set -e

echo "🐳 OpenIndex Stack Deployment"
echo "================================"

# Vérifier si Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

# Créer les répertoires nécessaires
mkdir -p logs monitoring/grafana/{dashboards,datasources}

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

# Configuration Crawler
CRAWLER_WORKERS=4
CRAWLER_DELAY=0.1
CRAWLER_MAX_DEPTH=
LARGE_FILE_THRESHOLD=104857600
DEBUG_MODE=false

# Configuration Web
STREAMLIT_SERVER_PORT=8502
STREAMLIT_SERVER_ADDRESS=0.0.0.0
LOG_LEVEL=info

# Configuration Admin (optionnel)
PGADMIN_EMAIL=admin@openindex.local
PGADMIN_PASSWORD=admin123

# Configuration Monitoring (optionnel)
GRAFANA_PASSWORD=admin123
EOF
    echo "✅ Fichier .env créé. Adaptez-le selon votre environnement."
fi

# Fonctions de déploiement
deploy_full() {
    echo "🚀 Déploiement de la stack complète..."
    docker-compose -f docker-compose.stack.yml --profile monitoring up -d
    echo ""
    echo "🌐 Services déployés:"
    echo "   📊 Web UI: http://localhost:8502"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Admin pgAdmin: http://localhost:5050"
    echo "   📈 Monitoring Grafana: http://localhost:3000"
}

deploy_web_only() {
    echo "🌐 Déploiement de l'interface web uniquement..."
    docker-compose -f docker-compose.stack.yml up -d web postgres pgadmin
    echo ""
    echo "🌐 Services déployés:"
    echo "   📊 Web UI: http://localhost:8502"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Admin pgAdmin: http://localhost:5050"
}

deploy_crawler_only() {
    echo "🔍 Déploiement du crawler uniquement..."
    docker-compose -f docker-compose.stack.yml --profile crawler up -d crawler postgres
    echo ""
    echo "🔍 Services déployés:"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Crawler en cours d'exécution..."
}

deploy_admin_tools() {
    echo "🔧 Déploiement des outils d'administration..."
    docker-compose -f docker-compose.stack.yml --profile admin --profile monitoring up -d postgres pgadmin grafana
    echo ""
    echo "🔧 Outils déployés:"
    echo "   🐘 Base de données: localhost:5432"
    echo "   🔧 Admin pgAdmin: http://localhost:5050"
    echo "   📈 Monitoring Grafana: http://localhost:3000"
}

stop_services() {
    echo "🛑 Arrêt des services..."
    docker-compose -f docker-compose.stack.yml down
}

show_status() {
    echo "📊 État des services:"
    docker-compose -f docker-compose.stack.yml ps
}

logs_service() {
    local service=$1
    echo "📝 Logs du service $service:"
    docker-compose -f docker-compose.stack.yml logs -f $service
}

# Menu d'aide
show_help() {
    echo "OpenIndex Stack Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  full         Déploie toute la stack (web + crawler + monitoring)"
    echo "  web          Déploie uniquement l'interface web"
    echo "  crawler      Déploie uniquement le crawler"
    echo "  admin        Déploie les outils d'administration"
    echo "  stop         Arrête tous les services"
    echo "  status       Affiche l'état des services"
    echo "  logs [service]  Affiche les logs d'un service"
    echo "  help         Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 full              # Déploie tout"
    echo "  $0 web               # Interface web uniquement"
    echo "  $0 crawler           # Crawler uniquement"
    echo "  $0 logs web          # Logs de l'interface web"
    echo "  $0 stop              # Arrêter tout"
}

# Analyse des arguments
COMMAND=${1:-help}

case $COMMAND in
    full)
        deploy_full
        ;;
    web)
        deploy_web_only
        ;;
    crawler)
        deploy_crawler_only
        ;;
    admin)
        deploy_admin_tools
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
