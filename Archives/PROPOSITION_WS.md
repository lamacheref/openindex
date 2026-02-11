# Plan OpenIndex - Phase 1

Ce plan détaille l'implémentation des fonctionnalités à court terme d'OpenIndex pour le 3 mars, avec l'infrastructure technique, les solutions proposées et les spécifications finalisées.

## Objectif à court terme (3 mars)

### 1. Crawler SMB et base de données
- **Solution** : Utiliser Python avec `smbprotocol` pour accéder aux partages SMB
- **Base de données** : SQLite pour la simplicité, avec tables pour fichiers, dossiers et checksums
- **Checksum** : Implémentation avec hashlib (SHA-256) pour identifier les doublons
- **Métadonnées** : Récupération dates création/modification, taille, propriétaire

### 2. Interface web de visualisation
- **Framework** : Streamlit (simple, rapide à déployer)
- **Fonctionnalités** : 
  - Arborescence interactive des fichiers
  - Affichage des métadonnées
  - Détection visuelle des doublons
  - Filtres par date/taille/type

## Infrastructure technique proposée

### Architecture
- **Conteneur Docker** pour la portabilité sur Proxmox
- **Backend** : Python FastAPI + SQLAlchemy
- **Frontend** : Streamlit
- **Base de données** : SQLite (évolutive vers PostgreSQL)
- **Stockage** : Volumes Docker pour la persistance

### Structure du projet
```
openindex/
├── backend/
│   ├── crawler.py          # Crawler SMB
│   ├── database.py         # Modèles DB
│   ├── api.py             # API FastAPI
│   └── utils.py           # Utilitaires checksum
├── frontend/
│   └── app.py             # Interface Streamlit
├── docker-compose.yml     # Déploiement
└── requirements.txt       # Dépendances
```

## Fonctionnalités complémentaires suggérées

### Court terme (en plus des exigences)
- **Recherche plein texte** : Indexation des noms de fichiers pour recherche rapide
- **Export CSV/Excel** : Extraction des inventaires pour rapports
- **Tableau de bord statistique** : Espace utilisé, nombre de fichiers, doublons détectés
- **Tags personnalisés** : Étiquetage des dossiers/fichiers pour organisation

### Moyen terme
- **Notifications email** : Alertes automatiques d'archivage
- **API REST complète** : Intégration avec des outils tiers
- **Gestion multi-utilisateurs** : Droits et permissions différenciés
- **Planning d'archivage** : Automatisation des tâches programmées

## Spécifications techniques finalisées

### Contexte
- **Volume SMB** : > 2 To (très grande volumétrie)
- **Permissions** : Accès complet pour le crawler
- **Fréquence** : Hebdomadaire ou à la demande
- **Doublons** : Affichage uniquement (phase 1), RAG et consolidation (phase 2)
- **NAS** : QNAP 23 To sur fibre
- **Utilisateurs** : 15 maximum

### Adaptations techniques nécessaires

#### 1. Gestion de la grande volumétrie (>2 To)
- **Pagination** : Traitement par lots de 1000 fichiers pour éviter la surcharge mémoire
- **Indexation progressive** : Sauvegarde intermédiaire toutes les 10 000 entrées
- **Optimisation SQLite** : WAL mode et transactions par lots
- **Cache intelligent** : Mémorisation de l'arborescence pour accélérer les crawls suivants

#### 2. Performance pour crawl hebdomadaire
- **Comparaison incrémentale** : Basée sur les dates de modification et checksums
- **Parallélisation** : Multi-threading pour l'analyse des fichiers
- **Monitoring** : Barre de progression et temps estimé restant

#### 3. Gestion multi-utilisateurs (15 personnes)
- **Authentification simple** : Base utilisateurs locale avec rôles admin/utilisateur
- **Sessions simultanées** : Gestion des accès concurrents à la base de données
- **Interface adaptée** : Vues différenciées admin vs utilisateur

## Contraintes respectées
- ✅ Intégrable Proxmox (Docker/LXC)
- ✅ Interface graphique simple (Streamlit)
- ✅ Utilisation admin et utilisateur facilitée

## Étapes de réalisation adaptées

1. **Structure projet et dépendances** : Docker + FastAPI + Streamlit
2. **Crawler SMB optimisé** : Pagination + multi-threading pour >2 To
3. **Base de données performante** : SQLite WAL mode + indexation progressive
4. **API backend avec authentification** : Gestion 15 utilisateurs + rôles
5. **Interface Streamlit responsive** : Arborescence + filtres + doublons
6. **Monitoring crawl** : Progression + temps estimé + logs
7. **Tests volumétrie** : Validation sur grands volumes de données
8. **Déploiement Docker** : Configuration Proxmox optimisée

## Livrables pour le 3 mars

### Fonctionnel
- ✅ Crawl complet SMB >2 To avec checksum SHA-256
- ✅ Interface web visualisation arborescence
- ✅ Détection et affichage des doublons
- ✅ Filtres par date/taille/type
- ✅ Export CSV des inventaires
- ✅ Tableau de bord statistique

### Technique
- ✅ Conteneur Docker déployable sur Proxmox
- ✅ Base de données SQLite optimisée
- ✅ Authentification pour 15 utilisateurs
- ✅ Crawl hebdomadaire automatique ET à la demande
- ✅ Monitoring progression et performance

### Documentation
- ✅ README technique et utilisateur
- ✅ Configuration déploiement
- ✅ Guide d'administration
