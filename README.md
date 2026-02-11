# OpenIndex

**Solution complète d'archivage et de gestion des fichiers professionnels avec crawler SMB et interface web moderne.**

## 🎯 Objectif Principal

OpenIndex permet de crawler, indexer, et gérer efficacement des partages SMB de grande volumétrie (>2 To) avec déduplication automatique et interface de visualisation interactive.

## ✅ Fonctionnalités Actuelles

### 🚀 **Crawler SMB Avancé**
- **Multi-threading** : Workers dédiés pour répertoires et fichiers
- **Robustesse** : Gestion des erreurs, reprise après interruption
- **Performance** : Temporisation adaptative, queues optimisées
- **Déduplication** : Détection automatique des doublons par checksum SHA-256

### 🌐 **Interface Web Moderne**
- **Arborescence Interactive** : streamlit-tree-select pour navigation fluide
- **Visualisation de Fichiers** : streamlit-elements pour documents, images, Excel
- **Tableau de Bord** : Métriques temps réel et graphiques interactifs
- **Analyse des Doublons** : Groupes détaillés avec comparaison
- **Panneau Latéral** : Actions contextuelles (⚠️ en cours de correction)

### 📊 **Gestion des Données**
- **Base SQLite** : Optimisée pour grande volumétrie
- **Export CSV** : Données filtrées et statistiques
- **Configuration** : Paramètres dynamiques du crawler
- **Filtres Avancés** : Recherche, type, doublons

## 🏗️ Architecture Technique

- **Backend** : Python 3.11+ avec smbprotocol
- **Frontend** : Streamlit v2 avec composants modernes
- **Base** : SQLite avec schéma optimisé
- **Librairies** : streamlit-tree-select, streamlit-elements, plotly

## 📁 Structure du Projet

```
OpenIndex/
├── src/
│   ├── smb_crawler.py          # Crawler SMB principal
│   └── web_interface_v2.py     # Interface web moderne
├── docs/                      # Documentation quotidienne
├── archives/                  # Fichiers archivés
├── PROJET.md                  # Spécifications complètes
├── TODO.md                    # Tâches en cours
└── requirements.txt           # Dépendances Python
```

## 🚀 Démarrage Rapide

### Installation
```bash
# Cloner le projet
git clone <repository-url>
cd OpenIndex

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'interface web
streamlit run src/web_interface_v2.py
```

### Accès
- **Interface Web** : http://localhost:8502
- **Documentation** : [PROJET.md](PROJET.md)
- **Tâches en cours** : [TODO.md](TODO.md)

## 📋 État du Projet

### ✅ **Accompli (Phase 1-2)**
- Crawler SMB récursif complet
- Interface web avec onglets multiples
- Détection et gestion des doublons
- Visualisation de fichiers intégrée
- Arborescence interactive

### 🔄 **En Cours (Phase 3)**
- ⚠️ Correction du panneau latéral (s'affiche en bas)
- Responsive design pour mobiles
- Actions en temps réel

### 📋 **Planifié (Phase 4-5)**
- Module d'archivage NAS
- Gestion des favoris et tags
- Notifications système
- Déploiement Docker

## 📊 Métriques Actuelles

- **Fichiers indexés** : 77
- **Dossiers** : 151
- **Doublons détectés** : 0
- **Taille totale** : Variable selon crawl

## 🤝 Contribution

Les contributions sont bienvenues ! Consultez [TODO.md](TODO.md) pour les tâches disponibles et suivez les règles dans [`.clinerules`](.clinerules).

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).

---

**Développé avec ❤️ pour l'archivage professionnel efficace**