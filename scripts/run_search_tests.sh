#!/bin/bash

# Script pour exécuter les tests de recherche dans l'environnement Docker

echo "🧪 Exécution des tests de recherche"
echo "=================================="

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erreur: docker-compose.yml non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

# Exécuter les tests de recherche
echo "🔍 Exécution des tests de recherche..."
docker compose exec backend pytest tests/test_search_api.py -v

if [ $? -ne 0 ]; then
    echo "❌ Certains tests de recherche ont échoué"
    exit 1
fi

echo "✅ Tous les tests de recherche ont passé"

# Exécuter également les tests des artefacts pour s'assurer que rien n'est cassé
echo ""
echo "🔍 Exécution des tests des artefacts..."
docker compose exec backend pytest tests/test_artefacts_api.py -v

if [ $? -ne 0 ]; then
    echo "❌ Certains tests des artefacts ont échoué"
    exit 1
fi

echo "✅ Tous les tests des artefacts ont passé"

echo ""
echo "🎉 Tous les tests ont passé avec succès !"
echo "   - Tests de recherche: ✅"
echo "   - Tests des artefacts: ✅"

echo ""
echo "📊 Statistiques des tests:"
docker compose exec backend pytest tests/test_search_api.py tests/test_artefacts_api.py --tb=no -q