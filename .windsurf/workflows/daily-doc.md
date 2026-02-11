---
description: Générer automatiquement la documentation quotidienne du développement
---

# Workflow : Documentation Quotidienne Automatique

## Description
Ce workflow génère automatiquement un fichier de documentation quotidienne dans le dossier `docs/` avec la date du jour, en se basant sur les commits Git et les fichiers modifiés.

## Quand l'utiliser
- À la fin de chaque journée de développement
- Avant de faire un commit majeur
- Pour documenter une session de travail intense

## Étapes d'exécution

### 1. Créer le fichier de documentation du jour
// turbo
```bash
# Créer le dossier docs s'il n'existe pas
mkdir -p docs

# Générer le nom de fichier avec la date du jour
DOC_FILE="docs/$(date +%Y-%m-%d).md"
```

### 2. Extraire les informations Git
```bash
# Récupérer les commits du jour
COMMITS_TODAY=$(git log --since="midnight" --pretty=format:"- %h %s" --author="$(git config user.name)")

# Récupérer les fichiers modifiés aujourd'hui
FILES_MODIFIED=$(git diff --name-only HEAD~1 2>/dev/null || echo "Aucun fichier modifié")

# Compter les lignes de code ajoutées/supprimées
LINES_STATS=$(git diff --stat HEAD~1 2>/dev/null | tail -1 || echo "0 fichiers modifiés")
```

### 3. Analyser l'état du projet
```bash
# Compter les fichiers Python dans src/
PYTHON_FILES=$(find src/ -name "*.py" | wc -l)

# Compter les lignes de code totales
TOTAL_LINES=$(find src/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')

# Vérifier l'état des TODO
TODO_COUNT=$(grep -c "\[ \]" TODO.md 2>/dev/null || echo "0")
DONE_COUNT=$(grep -c "\[x\]" TODO.md 2>/dev/null || echo "0")
```

### 4. Générer le fichier de documentation
// turbo
```bash
cat > "$DOC_FILE" << 'EOF'
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
```python
[Ajouter la configuration technique testée]
```

### Commandes Utilisées
```bash
[Ajouter les commandes importantes]
```

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

echo "📝 Documentation générée : $DOC_FILE"
```

### 5. Mettre à jour le TODO.md
```bash
# Ajouter une entrée dans les tâches terminées si nécessaire
TODAY_DATE=$(date +%Y-%m-%d)
if ! grep -q "$TODAY_DATE" TODO.md; then
    echo "| $TODAY_DATE | \`XXXXXXX\` | Génération documentation quotidienne automatique. | ✅     |" >> TODO.md
fi
```

### 6. Ouvrir le fichier pour édition manuelle
```bash
# Ouvrir le fichier dans l'éditeur par défaut pour compléter les sections manuelles
${EDITOR:-nano} "$DOC_FILE"
```

## Raccourci
Pour exécuter rapidement tout le workflow :
```bash
# Créer un script exécutable
cat > generate_daily_doc.sh << 'EOF'
#!/bin/bash
echo "🚀 Génération de la documentation quotidienne..."
mkdir -p docs
DOC_FILE="docs/$(date +%Y-%m-%d).md"

# [Le reste du script ci-dessus]
EOF

chmod +x generate_daily_doc.sh
./generate_daily_doc.sh
```

## Notes
- Les sections entre crochets `[]` doivent être complétées manuellement
- Le workflow peut être personnalisé selon les besoins spécifiques du projet
- Les variables Git ne fonctionnent que s'il y a des commits dans la journée
