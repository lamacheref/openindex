#!/bin/bash

# Script pour rebuild les images Docker nécessaires pour tester les nouvelles fonctionnalités
# Ce script rebuild uniquement les images nécessaires pour le développement et les tests

echo "🚀 Rebuild des images Docker pour OpenIndex"
echo "=========================================="

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erreur: docker-compose.yml non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

# Rebuild uniquement les images nécessaires pour le développement
echo "🔧 Reconstruction de l'image backend..."
docker compose build backend

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la construction de l'image backend"
    exit 1
fi

echo "✅ Image backend reconstruite avec succès"

echo ""
echo "📋 Images disponibles pour les tests:"
docker images | grep openindex

echo ""
echo "💡 Pour démarrer l'environnement de test, exécutez:"
echo "   docker compose up -d"

echo ""
echo "🧪 Pour exécuter les tests:"
echo "   docker compose exec backend pytest tests/test_search_api.py tests/test_artefacts_api.py -v"

echo ""
echo "✅ Script terminé avec succès !"