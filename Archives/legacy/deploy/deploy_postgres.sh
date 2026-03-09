#!/bin/bash
# Script de déploiement PostgreSQL pour OpenIndex
# Utilise PostgreSQL 17 avec optimisations pour les grandes volumétries

set -e

echo "🚀 Déploiement PostgreSQL 17 pour OpenIndex..."

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Créer le fichier .env si inexistant
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env avec les valeurs par défaut..."
    cat > .env << EOF
# Configuration PostgreSQL
POSTGRES_PASSWORD=openindex_secure_password_$(date +%s)
POSTGRES_DB=openindex
POSTGRES_USER=openindex_user

# Configuration pgAdmin
PGADMIN_EMAIL=admin@openindex.local
PGADMIN_PASSWORD=admin123

# Configuration réseau
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
EOF
    echo "✅ Fichier .env créé. Modifiez-le si nécessaire."
fi

# Charger les variables d'environnement
source .env

echo "🔧 Démarrage des conteneurs PostgreSQL..."

# Démarrer les services
docker-compose up -d

echo "⏳ Attente du démarrage de PostgreSQL..."
sleep 10

# Vérifier que PostgreSQL est prêt
echo "🔍 Vérification de la connexion PostgreSQL..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker exec openindex-postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
        echo "✅ PostgreSQL est prêt!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL n'a pas pu démarrer après $max_attempts tentatives."
        echo "📋 Logs de PostgreSQL:"
        docker logs openindex-postgres
        exit 1
    fi
    
    echo "⏳ Tentative $attempt/$max_attempts..."
    sleep 2
    ((attempt++))
done

# Vérifier que les tables sont créées
echo "🔍 Vérification des tables..."
if docker exec openindex-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt" > /dev/null 2>&1; then
    echo "✅ Tables créées avec succès!"
else
    echo "❌ Erreur lors de la création des tables."
    docker logs openindex-postgres
    exit 1
fi

# Afficher les informations de connexion
echo ""
echo "🎉 Déploiement PostgreSQL 17 terminé avec succès!"
echo ""
echo "📋 Informations de connexion:"
echo "   Hôte: localhost"
echo "   Port: 5432"
echo "   Base de données: $POSTGRES_DB"
echo "   Utilisateur: $POSTGRES_USER"
echo "   Mot de passe: $POSTGRES_PASSWORD"
echo ""
echo "🌐 pgAdmin disponible sur: http://localhost:5050"
echo "   Email: $PGADMIN_EMAIL"
echo "   Mot de passe: $PGADMIN_PASSWORD"
echo ""
echo "🔧 Commandes utiles:"
echo "   Arrêter: docker-compose down"
echo "   Redémarrer: docker-compose restart"
echo "   Logs: docker-compose logs -f postgres"
echo "   Backup: docker exec openindex-postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql"
echo ""
echo "📝 Prochaine étape: Exécuter la migration des données SQLite"
echo "   python database/migrate_to_postgres.py"
echo ""

# Attendre que pgAdmin soit prêt
echo "⏳ Démarrage de pgAdmin..."
sleep 5

if curl -s http://localhost:5050 > /dev/null 2>&1; then
    echo "✅ pgAdmin est accessible!"
else
    echo "⚠️  pgAdmin est en cours de démarrage..."
fi

echo "🚀 PostgreSQL 17 est prêt pour OpenIndex!"
