# OpenIndex

**Solution moderne d'archivage et de gestion des fichiers professionnels avec crawler SMB, API FastAPI et interface web VanillaJS.**

## 🎯 Objectif Principal

OpenIndex permet de crawler, indexer, et gérer efficacement des partages SMB de grande volumétrie (>2 To) avec déduplication automatique et interface de visualisation interactive basée sur une architecture microservices moderne.

## ✅ Fonctionnalités Actuelles

### 🚀 **Crawler SMB Haute Performance**
- **Multi-threading avancé** : Workers dédiés pour répertoires, fichiers et gros fichiers
- **Robustesse exceptionnelle** : Gestion des erreurs, reprise après interruption, fallback smbclient
- **Performance optimisée** : Temporisation adaptative, queues séparées, traitement parallèle
- **Déduplication intelligente** : Détection automatique des doublons par checksum SHA-256
- **PostgreSQL 17** : Base de données robuste avec UUID, index et triggers

### 🌐 **API FastAPI Moderne**
- **Performance extrême** : 10x plus rapide que Streamlit avec async/await
- **WebSocket natif** : Monitoring temps réel des crawls et statistiques
- **Documentation auto-générée** : Swagger UI et ReDoc intégrés
- **Validation Pydantic** : Types forts et sérialisation automatique
- **CORS configuré** : Support frontend découplé

### 🎨 **Frontend VanillaJS Ultra-Léger**
- **VanillaJS + Alpine.js** : Réactivité sans framework lourd
- **HTMX** : Interactions AJAX fluides sans JavaScript complexe
- **TailwindCSS** : Design utilitaire moderne et responsive
- **Chart.js** : Graphiques performants et animés
- **Monitoring temps réel** : WebSocket pour mises à jour instantanées

### 📊 **Architecture Microservices**
- **API FastAPI** : Service backend indépendant (port 8000)
- **Frontend Nginx** : Service web statique optimisé (port 3000)
- **PostgreSQL 17** : Base de données partagée (port 5432)
- **Crawler Docker** : Service d'indexation isolé et scalable
- **Communication** : Proxy Nginx + WebSocket entre services

## 🏗️ Architecture Technique

### Backend (FastAPI)
- **Python 3.11+** avec async/await et Pydantic
- **PostgreSQL 17** avec psycopg2-binary et SQLAlchemy
- **WebSocket** pour monitoring temps réel
- **Uvicorn** comme serveur ASGI

### Frontend (VanillaJS)
- **HTML5 + CSS3** avec TailwindCSS
- **Alpine.js** pour la réactivité
- **HTMX** pour les interactions serveur
- **Chart.js** pour les visualisations

### Base de Données
- **PostgreSQL 17** avec UUID primary keys
- **Index optimisés** sur checksum, paths et dates
- **Triggers** pour updated_at automatique
- **Vues matérialisées** pour les doublons et statistiques

### Infrastructure
- **Docker multi-stage** pour builds optimisés
- **Nginx reverse proxy** avec compression et cache
- **Healthchecks** pour tous les services
- **CI/CD Gitea** pour déploiements automatisés

## 📁 Structure du Projet

```
OpenIndex/
├── 📦 Docker & CI/CD
│   ├── Dockerfile.api              # Service FastAPI
│   ├── Dockerfile.frontend         # Frontend Nginx
│   ├── Dockerfile.crawler           # Service Crawler
│   ├── docker-compose.modern.yml  # Stack complète
│   ├── .gitea-ci.yml            # Configuration CI/CD
│   └── deploy-modern.sh          # Script déploiement
├── 🚀 Services
│   ├── src/
│   │   ├── api/
│   │   │   └── main.py          # API FastAPI principale
│   │   ├── smb_crawler_postgresql.py  # Crawler PostgreSQL
│   │   └── postgres_adapter.py  # Adaptateur BDD
│   ├── frontend/
│   │   └── index.html         # Interface VanillaJS
│   └── nginx/
│       └── nginx.conf          # Configuration reverse proxy
├── 📊 Base de données
│   └── database/
│       └── init.sql            # Schema PostgreSQL 17
├── 🔧 Configuration
│   ├── config/
│   │   └── admin_credentials.ini
│   └── .env                    # Variables d'environnement
├── 📝 Documentation
│   ├── README.md               # Documentation principale
│   ├── README.stack.md         # Architecture microservices
│   ├── CI-CD.md               # Documentation CI/CD
│   ├── CHANGELOG.md            # Historique des changements
│   ├── ROADMAP.md              # Feuille de route technique
│   └── TODO.md                 # Tâches en cours
└── 📦 Dépendances
    ├── requirements.api.txt       # FastAPI et WebSocket
    ├── requirements.web.txt       # Frontend minimal
    ├── requirements.crawler.txt  # Crawler optimisé
    └── requirements.txt         # Complet (legacy)
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

### Configuration du Logging
Le système utilise une rotation automatique des logs avec compression :
- **Rotation** : Fichiers tournés à 5MB (10MB par défaut)
- **Compression** : Fichiers de rotation compressés en GZIP
- **Rétention** : 10 rotations conservées (configurable)
- **Emplacement** : Tous les logs sont stockés dans le répertoire `/logs/`

Les logs sont automatiquement gérés sans intervention manuelle.

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
- Système de logging avec rotation et compression automatique

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

- **Fichiers indexés** : 77+
- **Dossiers** : 151+
- **Doublons détectés** : 0+
- **Taille totale** : Variable selon crawl
- **Système de logging** : Rotation automatique avec compression GZIP

## 🤝 Contribution

Les contributions sont bienvenues ! Consultez [TODO.md](TODO.md) pour les tâches disponibles et suivez les règles dans [`.clinerules`](.clinerules).

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).

---

**Développé avec ❤️ pour l'archivage professionnel efficace**