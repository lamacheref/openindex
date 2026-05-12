#!/bin/bash

# Script de génération automatique de la documentation quotidienne
# Usage: ./generate_daily_doc.sh

echo "🚀 Génération de la documentation quotidienne..."

# Créer le dossier docs s'il n'existe pas
mkdir -p docs

# Générer le nom de fichier avec la date du jour
DOC_FILE="docs/$(date +%Y-%m-%d).md"

# Vérifier si le fichier existe déjà
if [ -f "$DOC_FILE" ]; then
    echo "⚠️  Le fichier $DOC_FILE existe déjà. Ouverture pour modification..."
    ${EDITOR:-nano} "$DOC_FILE"
    exit 0
fi

echo "📝 Création du fichier : $DOC_FILE"

# Extraire les informations Git
COMMITS_TODAY=$(git log --since="midnight" --pretty=format:"- %h %s" --author="$(git config user.name)" 2>/dev/null || echo "- Aucun commit aujourd'hui")
FILES_MODIFIED=$(git diff --name-only HEAD~1 2>/dev/null 2>/dev/null || echo "Premier commit ou pas de modifications")
LINES_STATS=$(git diff --stat HEAD~1 2>/dev/null 2>/dev/null | tail -1 || echo "0 fichiers modifiés")

# Analyser l'état du projet
PYTHON_FILES=$(find src/ -name "*.py" 2>/dev/null | wc -l)
TOTAL_LINES=$(find src/ -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
TODO_COUNT=$(grep -c "\[ \]" TODO.md 2>/dev/null || echo "0")
DONE_COUNT=$(grep -c "\[x\]" TODO.md 2>/dev/null || echo "0")

# Générer le fichier de documentation
cat > "$DOC_FILE" << EOF
# Journal de Développement - $(date +%Y-%m-%d)

## 🎯 Objectif du Jour
[À compléter manuellement avec l'objectif principal de la journée]

---

## 📋 État Initial

### Projet OpenIndex
- **Objectif** : Indexation >2 To de données SMB avec échéance 3 mars 2026
- **État actuel** : [Décrire brièvement l'état du projet au début de la journée]
- **Priorités** : [Lister les priorités identifiées]

---

## 🔧 Développement du Jour

### Commits d'aujourd'hui
$COMMITS_TODAY

### Fichiers modifiés
$FILES_MODIFIED

---

## 📊 Résultats Obtenus

### ✅ Fonctionnalités Implémentées
[À compléter avec les fonctionnalités terminées]

### 📁 Fichiers Modifiés/Créés
[À compléter avec la liste des fichiers modifiés]

### 🐛 Problèmes Résolus
[À compléter avec les problèmes corrigés]

---

## 🎯 Prochaines Étapes

### Priorité 1
- [ ] [Prochaine tâche prioritaire]

### Priorité 2  
- [ ] [Autre tâche importante]

---

## 📝 Notes Techniques

### Configuration Testée
\`\`\`python
[Ajouter la configuration technique testée]
\`\`\`

### Commandes Utilisées
\`\`\`bash
[Ajouter les commandes importantes]
\`\`\`

---

## 🔍 Leçons Apprises
[À compléter avec les leçons apprises]

---

## 📈 Métriques du Jour

- **Fichiers Python** : $PYTHON_FILES
- **Lignes de code totales** : $TOTAL_LINES  
- **Tâches en attente** : $TODO_COUNT
- **Tâches terminées** : $DONE_COUNT
- **Statistiques Git** : $LINES_STATS

---

*Fin du journal de développement - $(date +%Y-%m-%d)*
EOF

echo "✅ Fichier généré avec succès !"
echo "📝 Le fichier contient des sections à compléter manuellement."
echo "🔧 Ouverture du fichier pour édition..."

# Mettre à jour le TODO.md si nécessaire
TODAY_DATE=$(date +%Y-%m-%d)
if ! grep -q "$TODAY_DATE" TODO.md 2>/dev/null; then
    echo "| $TODAY_DATE | \`XXXXXXX\` | Génération documentation quotidienne automatique. | ✅     |" >> TODO.md
    echo "📋 TODO.md mis à jour"
fi

# Ouvrir le fichier dans l'éditeur par défaut pour compléter les sections manuelles
${EDITOR:-nano} "$DOC_FILE"

echo "🎉 Documentation quotidienne terminée !"
