# 🔍 Moteur de Recherche & Sommaire - Documentation

## 📋 Vue d'ensemble

Cette documentation décrit les nouvelles fonctionnalités de recherche et de sommaire ajoutées à OpenIndex (T-SEARCH-01).

## 🎯 Fonctionnalités Implémentées

### 1. Interface Utilisateur

#### Onglet "Recherche & Sommaire"
- **Emplacement** : Ajouté à la navigation principale
- **Icône** : 🔍 (Font Awesome fa-search)
- **Fonction** : Accès centralisé à la recherche et au sommaire

#### Système d'Onglets
Deux sous-onglets disponibles :
- **Moteur de recherche** : Pour effectuer des recherches
- **Sommaire global** : Pour voir les statistiques globales

### 2. Moteur de Recherche

#### Interface de Recherche
- **Champ de recherche** : Avec icône et placeholder
- **Bouton de recherche** : Bouton dédié avec icône
- **Support clavier** : Recherche avec la touche Entrée
- **Indicateurs** : Nombre de résultats et temps de recherche

#### Affichage des Résultats
- **Tableau** : Nom, Chemin, Type, Taille, Date de modification
- **Pagination** : Défilement dans les résultats (hauteur fixe)
- **État de chargement** : Animation pendant la recherche
- **Messages** : "Aucun résultat trouvé" lorsque applicable

### 3. Sommaire Global

#### Statistiques Principales
Quatre cartes avec les métriques clés :
- **Fichiers totaux** : Nombre total de fichiers indexés
- **Volumétrie totale** : Taille totale des fichiers
- **Types de fichiers** : Nombre de types différents
- **Espaces SMB** : Nombre d'espaces configurés

#### Répartition par Type
- **Grille responsive** : 2-7 colonnes selon la taille d'écran
- **Pour chaque type** : Nom, Count, Pourcentage
- **Tri** : Par ordre alphabétique

#### Répartition par Espace SMB
- **Liste avec barres de progression**
- **Pour chaque espace** : Nom, Nombre de fichiers, Pourcentage
- **Visualisation** : Barres de progression colorées

#### Fichiers Récents
- **Tableau** : Nom, Chemin, Type, Taille, Date
- **Limite** : Affiche les fichiers récemment modifiés
- **Tri** : Par date de modification (décroissant)

## 📊 Structure des Données

### Recherche

```javascript
{
  searchQuery: string,          // Requête de recherche
  searchResults: Array<{
    id: string,
    name: string,
    path: string,
    type: string,
    size: number,
    last_modified: string
  }>,
  loadingSearch: boolean,       // État de chargement
  searchPerformed: boolean,     // Indique si une recherche a été effectuée
  searchTime: number             // Temps de recherche en ms
}
```

### Sommaire

```javascript
{
  summaryStats: {
    total_files: number,          // Nombre total de fichiers
    total_size: number,           // Taille totale en octets
    files_by_type: {              // Répartition par type
      [type: string]: number
    },
    files_by_space: {            // Répartition par espace
      [space: string]: number
    },
    recent_files: Array<{        // Fichiers récents
      id: string,
      name: string,
      path: string,
      type: string,
      size: number,
      last_modified: string
    }>
  },
  loadingSummary: boolean       // État de chargement
}
```

## 🔧 Fonctions JavaScript

### `performSearch()`
**Description** : Effectue une recherche dans les fichiers indexés

**Paramètres** : Aucun (utilise `this.searchQuery`)

**Comportement** :
- Vérifie que la requête n'est pas vide
- Affiche l'état de chargement
- Simule une recherche (à remplacer par un appel API)
- Filtre les résultats simulés
- Met à jour les résultats et le temps de recherche
- Gère les erreurs

### `loadSummary()`
**Description** : Charge les statistiques du sommaire

**Paramètres** : Aucun

**Comportement** :
- Affiche l'état de chargement
- Simule le chargement des données (à remplacer par un appel API)
- Met à jour les statistiques du sommaire
- Gère les erreurs

### `updateSearchTab()`
**Description** : Met à jour l'onglet actif et charge les données si nécessaire

**Paramètres** : Aucun

**Comportement** :
- Appelé lors du changement d'onglet
- Charge automatiquement le sommaire si l'onglet est sélectionné et que les données ne sont pas encore chargées

## 🎨 Composants UI

### Barre de Recherche
```html
<div class="flex flex-wrap items-center gap-4">
  <div class="flex-1 min-w-[20rem]">
    <input type="text" x-model="searchQuery"
           @keyup.enter="performSearch()"
           placeholder="Rechercher des fichiers, dossiers, ou contenu..."
           class="block w-full rounded-2xl border-0 bg-slate-100 py-3 pl-12 pr-4">
  </div>
  <button @click="performSearch()" class="rounded-2xl bg-teal-700 px-6 py-3 text-sm font-semibold text-white hover:bg-teal-800">
    <i class="fas fa-search mr-2"></i>Rechercher
  </button>
</div>
```

### Carte de Statistiques
```html
<div class="rounded-2xl border border-slate-200 bg-white p-6 text-center">
  <p class="text-xs uppercase tracking-[0.22em] text-slate-400">Fichiers totaux</p>
  <p class="mt-3 text-3xl font-semibold text-slate-800" x-text="summaryStats.total_files.toLocaleString()"></p>
</div>
```

### Barre de Progression
```html
<div class="h-2 rounded-full bg-slate-200">
  <div class="h-2 rounded-full bg-teal-600" 
       :style="`width: ${Math.round(count / summaryStats.total_files * 100)}%`"></div>
</div>
```

## 🚀 Utilisation

### Effectuer une Recherche
1. Cliquez sur l'onglet "Recherche & Sommaire"
2. Assurez-vous que l'onglet "Moteur de recherche" est sélectionné
3. Entrez votre requête dans le champ de recherche
4. Appuyez sur Entrée ou cliquez sur le bouton "Rechercher"
5. Les résultats s'affichent dans le tableau

### Consulter le Sommaire
1. Cliquez sur l'onglet "Recherche & Sommaire"
2. Sélectionnez l'onglet "Sommaire global"
3. Les statistiques se chargent automatiquement
4. Parcourez les différentes sections (statistiques, types, espaces, fichiers récents)

## 🔮 Évolution Future

### Backend à Implémenter
- **Endpoint `/api/search`** : Recherche full-text
- **Endpoint `/api/summary`** : Statistiques globales
- **Indexation** : Indexation full-text des fichiers
- **Optimisation** : Optimisation des requêtes de recherche

### Améliorations UI
- **Filtres avancés** : Par type, date, taille
- **Graphiques** : Graphiques d'évolution temporelle
- **Intégration** : Navigation vers les résultats dans l'explorateur
- **Export** : Export des résultats de recherche

### Fonctionnalités Avancées
- **Recherche dans le contenu** : Indexation des métadonnées Office/PDF
- **Suggestions** : Suggestions de recherche
- **Historique** : Historique des recherches
- **Favoris** : Fichiers favoris

## 🧪 Tests

### Exécution des Tests
```bash
# Tests de recherche
pytest tests/test_search_api.py -v

# Tests des artefacts (pour s'assurer que rien n'est cassé)
pytest tests/test_artefacts_api.py -v

# Tous les tests liés
pytest tests/test_search_api.py tests/test_artefacts_api.py -v
```

### Couverture des Tests
- ✅ Interface utilisateur (présence des éléments)
- ✅ Structure des données
- ✅ Fonctions JavaScript (présence et signature)
- ✅ Intégration avec les composants existants
- ❌ Appels API (non encore implémentés)
- ❌ Performances (non encore testées)

## 📝 Notes de Développement

### Données Simulées
Actuellement, les fonctions utilisent des données simulées :
- `performSearch()` : Résultats simulés avec filtrage local
- `loadSummary()` : Statistiques simulées avec délai artificiel

### À Remplacer
Les parties suivantes doivent être remplacées par des appels API réels :
```javascript
// Dans performSearch()
// await new Promise(resolve => setTimeout(resolve, 500));
// const response = await fetch('/api/search?q=' + encodeURIComponent(this.searchQuery));

// Dans loadSummary()
// await new Promise(resolve => setTimeout(resolve, 800));
// const response = await fetch('/api/summary');
```

### Conventions
- **Nommage** : Variables en camelCase, fonctions en camelCase
- **Style** : Suivre le style existant du projet
- **Responsive** : Utilisation de Tailwind CSS pour le responsive design
- **Accessibilité** : Utilisation d'ARIA et de bonnes pratiques

## 🎓 Exemples

### Recherche Simple
```javascript
// Rechercher "rapport"
this.searchQuery = "rapport";
await this.performSearch();
```

### Chargement du Sommaire
```javascript
// Charger le sommaire
await this.loadSummary();
// Accéder aux statistiques
console.log(this.summaryStats.total_files);
```

### Navigation entre Onglets
```javascript
// Basculer vers le sommaire
this.searchTab = 'summary';
this.updateSearchTab();
```

## 📚 Ressources

- **Documentation Tailwind CSS** : https://tailwindcss.com/docs
- **Documentation Alpine.js** : https://alpinejs.dev/
- **Documentation Font Awesome** : https://fontawesome.com/

---

*Documentation générée pour T-SEARCH-01 - Moteur de recherche & Sommaire* 🚀