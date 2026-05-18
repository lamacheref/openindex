#!/bin/bash
# Script d'entrée pour Docker OpenIndex
# Permet de lancer différents modes : crawler, ui, ou production

set -e

# Fonction d'affichage d'aide
show_help() {
    echo "OpenIndex Docker Entry Point"
    echo ""
    echo "Usage: docker run [OPTIONS] openindex [MODE]"
    echo ""
    echo "Modes:"
    echo "  crawler       Lance le crawler SMB avec PostgreSQL"
    echo "  ui            Lance l'interface web Streamlit"
    echo "  production    Lance crawler en arrière-plan + interface web"
    echo ""
    echo "Options:"
    echo "  --debug       Active le mode debug"
    echo "  --workers N   Nombre de workers (défaut: 4)"
    echo "  --share NAME   Nom du partage SMB (défaut: Public\\SEPM)"
    echo ""
    echo "Variables d'environnement:"
    echo "  POSTGRES_HOST     Hôte PostgreSQL (défaut: localhost)"
    echo "  POSTGRES_PORT     Port PostgreSQL (défaut: 5432)"
    echo "  POSTGRES_DB       Base de données (défaut: openindex)"
    echo "  POSTGRES_USER     Utilisateur PostgreSQL (défaut: openindex_user)"
    echo "  POSTGRES_PASSWORD Mot de passe PostgreSQL"
    echo ""
}

# Fonction pour attendre PostgreSQL
wait_for_postgres() {
    echo "⏳ Attente de PostgreSQL..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host='${POSTGRES_HOST:-localhost}',
        port=${POSTGRES_PORT:-5432},
        database='${POSTGRES_DB:-openindex}',
        user='${POSTGRES_USER:-openindex_user}',
        password='${POSTGRES_PASSWORD}'
    )
    conn.close()
    print('✅ PostgreSQL prêt')
except Exception as e:
    print(f'❌ PostgreSQL pas prêt: {e}')
    exit(1)
"; then
            return 0
        fi
        
        echo "⏳ Tentative $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ Timeout d'attente de PostgreSQL"
    return 1
}

# Mode crawler
run_crawler() {
    echo "🚀 Démarrage du mode Crawler"
    
    # Attendre PostgreSQL si nécessaire
    if [ "${POSTGRES_HOST}" != "localhost" ]; then
        wait_for_postgres || exit 1
    fi
    
    # Lancer le crawler
    cd /app
    python src/smb_crawler_postgresql.py \
        --debug ${DEBUG:-false} \
        --workers ${WORKERS:-4} \
        --share "${SHARE:-Public\\SEPM}"
}

# Mode UI
run_ui() {
    echo "🌐 Démarrage de l'interface web"
    
    # Attendre PostgreSQL si nécessaire
    if [ "${POSTGRES_HOST}" != "localhost" ]; then
        wait_for_postgres || exit 1
    fi
    
    # Lancer Streamlit
    cd /app
    streamlit run src/web_interface_v2.py \
        --server.port ${STREAMLIT_PORT:-8502} \
        --server.address ${STREAMLIT_ADDRESS:-0.0.0.0} \
        --logger.level ${LOG_LEVEL:-info}
}

# Mode production (crawler + UI)
run_production() {
    echo "🏭 Démarrage du mode Production"
    
    # Attendre PostgreSQL
    if [ "${POSTGRES_HOST}" != "localhost" ]; then
        wait_for_postgres || exit 1
    fi
    
    # Lancer le crawler en arrière-plan
    cd /app
    python src/smb_crawler_postgresql.py \
        --debug ${DEBUG:-false} \
        --workers ${WORKERS:-4} \
        --share "${SHARE:-Public\\SEPM}" &
    CRAWLER_PID=$!
    
    # Lancer l'interface web au premier plan
    trap "kill $CRAWLER_PID 2>/dev/null" EXIT
    
    echo "📊 Crawler démarré (PID: $CRAWLER_PID)"
    echo "🌐 Interface web en démarrage..."
    
    streamlit run src/web_interface_v2.py \
        --server.port ${STREAMLIT_PORT:-8502} \
        --server.address ${STREAMLIT_ADDRESS:-0.0.0.0} \
        --logger.level ${LOG_LEVEL:-info}
}

# Analyse des arguments
MODE=${1:-production}
DEBUG=false
WORKERS=4
SHARE="Public\\SEPM"

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            DEBUG=true
            shift
            ;;
        --workers)
            WORKERS=$2
            shift 2
            ;;
        --share)
            SHARE=$2
            shift 2
            ;;
        crawler|ui|production)
            MODE=$1
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Configuration des variables d'environnement
export DEBUG=${DEBUG}
export WORKERS=${WORKERS}
export SHARE=${SHARE}

echo "🎯 OpenIndex - Mode: ${MODE}"
echo "🔧 Configuration: Workers=${WORKERS}, Share=${SHARE}, Debug=${DEBUG}"

# Exécuter le mode demandé
case $MODE in
    crawler)
        run_crawler
        ;;
    ui)
        run_ui
        ;;
    production)
        run_production
        ;;
    *)
        echo "Mode inconnu: $MODE"
        show_help
        exit 1
        ;;
esac
