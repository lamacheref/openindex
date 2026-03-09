# OpenIndex

**Solution moderne d'archivage et de gestion des fichiers professionnels avec crawler SMB, API FastAPI et interface web VanillaJS.**

## 🎯 Objectif Principal

OpenIndex permet de crawler, indexer, et gérer efficacement des partages SMB de grande volumétrie (>2 To) avec déduplication automatique et interface de visualisation interactive basée sur une architecture microservices moderne.


## 🆕 Mise à jour J3 (variant en cours)

- **Base de données J3** : SQLite (variable `OPENINDEX_DB_PATH`) pour l'API `src/api/main.py`.
- **Analyse DB** : endpoint `GET /api/db-explain` + vue frontend **DB Explain** pour inspecter les plans (`EXPLAIN QUERY PLAN`).
- **Container J3** : `docker-compose.j3.yml` est en mode **image-first** via `OPENINDEX_J3_IMAGE`.
- **CI GitHub** : build/push automatique de l'image J3 vers GHCR via `.github/workflows/docker-j3.yml`.
- **Note planning** : la migration PostgreSQL est reportée à J4.

## ✅ Fonctionnalités Actuelles

### 🚀 **Crawler SMB Haute Performance**
- **Multi-threading avancé** : Workers dédiés pour répertoires, fichiers et gros fichiers
- **Robustesse exceptionnelle** : Gestion des erreurs, reprise après interruption, fallback smbclient
- **Performance optimisée** : Temporisation adaptative, queues séparées, traitement parallèle
- **Déduplication intelligente** : Détection automatique des doublons par checksum SHA-256
- **SQLite (J3)** : Base locale légère pour itération rapide
- **PostgreSQL (J4)** : migration prévue

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
- **SQLite (J3)** : base locale montée en volume Docker (`/data/openindex.db`)
- **Crawler Docker** : Service d'indexation isolé et scalable
- **Communication** : Proxy Nginx + WebSocket entre services

## 🏗️ Architecture Technique

### Backend (FastAPI)
- **Python 3.11+** avec async/await et Pydantic
- **SQLite (J3)** via `sqlite3`
- **WebSocket** pour monitoring temps réel
- **Uvicorn** comme serveur ASGI

### Frontend (VanillaJS)
- **HTML5 + CSS3** avec TailwindCSS
- **Alpine.js** pour la réactivité
- **HTMX** pour les interactions serveur
- **Chart.js** pour les visualisations

### Base de Données
- **SQLite (J3)** pour stockage local
- **Plans d'exécution** exposés via `/api/db-explain`
- **Préparation migration J4** vers PostgreSQL

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

### Prérequis
- Docker 20.10+ et Docker Compose 2.0+
- Git et accès aux dépôts OpenIndex
- 8GB+ RAM pour builds Docker
- 50GB+ espace disque disponible

### Installation
```bash
# Cloner le projet (depuis GitHub ou Gitea)
git clone https://github.com/lamacheref/openindex.git
# ou
git clone ssh://git@gitea.smiden.eu:2255/flamachere/openindex.git

cd OpenIndex

# Configuration environnement
cp .env.example .env
# Éditer .env avec vos credentials SMB et configuration

# Déploiement stack complète
./deploy-modern.sh modern

# Ou déploiement modulaire
./deploy-modern.sh api      # API uniquement
./deploy-modern.sh frontend   # Frontend uniquement  
./deploy-modern.sh crawler   # Crawler uniquement
```

### Option J3 (recommandée pour l’état actuel)
```bash
cp .env.example .env
# Adapter OPENINDEX_J3_IMAGE si nécessaire (GHCR)

docker compose -f docker-compose.j3.yml pull
docker compose -f docker-compose.j3.yml up -d
```

### Accès aux Services
- **Frontend** : http://localhost:3000
- **API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **WebSocket** : ws://localhost:8000/ws
- **DB SQLite (J3)** : fichier local monté dans le conteneur (`OPENINDEX_DB_PATH`)

### Configuration
```bash
# Variables d'environnement clés (J3)
OPENINDEX_J3_IMAGE=ghcr.io/<owner>/openindex-j3:latest
OPENINDEX_DB_PATH=/data/openindex.db
OPENINDEX_API_PORT=8000
```

### Tests
```bash
# Tests builds Docker
docker build -f Dockerfile.api -t openindex-api:test .
docker build -f Dockerfile.frontend -t openindex-frontend:test .
docker build -f Dockerfile.crawler -t openindex-crawler:test .

# Tests API
docker run --rm openindex-api:test python -c "from main import app; print('✅ API OK')"

# Tests Frontend  
docker run --rm -p 3001:3000 openindex-frontend:test curl -f http://localhost:3000/health
```

## 🔧 Développement

### Architecture
- **Backend** : FastAPI + SQLite (J3) + WebSocket
- **Frontend** : VanillaJS + Alpine.js + HTMX + TailwindCSS
- **Infrastructure** : Docker + CI/CD Gitea/GitHub Actions

### Dépôts Git
- **GitHub (principal)** : https://github.com/lamacheref/openindex.git
- **Gitea (backup)** : ssh://git@gitea.smiden.eu:2255/flamachere/openindex.git

### Reprise du Travail
Après la semaine de vacances, pour reprendre le développement :

1. **État actuel** : Architecture moderne terminée et testée
2. **Prochaines étapes** : Tests automatisés → Staging → Production
3. **Priorités** : Stabilisation (Phase 1) → Optimisations (Phase 2)
4. **Documentation** : TODO.md mis à jour avec progression (23% complété)

### Commandes Utiles
```bash
# Synchronisation dépôts
git push origin main    # Gitea
git push github main    # GitHub

# Vérifier état services
./deploy-modern.sh status

# Logs en temps réel
./deploy-modern.sh logs api
./deploy-modern.sh logs frontend
./deploy-modern.sh logs crawler

# Nettoyer containers
./deploy-modern.sh stop

# Tests builds
docker-compose -f docker-compose.modern.yml build
# Image J3 (image-first)
docker compose -f docker-compose.j3.yml pull
```

## 📊 Monitoring

### Métriques Clés
- **Performance API** : <100ms réponse (objectif)
- **Uptime** : 99.9% (objectif)
- **Coverage tests** : >90% (objectif)
- **Taille images** : <50MB total (actuel: 1GB)

### Health Checks
- **API** : http://localhost:8000/health
- **Frontend** : http://localhost:3000/health
- **Crawler** : Logs progression dans `/app/logs`

## 🚨 Dépannage

### Problèmes Connus
1. **Nginx proxy** : Corrigé dans nginx.conf (localhost:8000)
2. **Builds Docker** : PYTHONPATH corrigé dans Dockerfile.api
3. **Requirements** : hashlib supprimé de requirements.crawler.txt

### Solutions
```bash
# Problème API J3
docker compose -f docker-compose.j3.yml logs openindex-j3

# Redémarrage J3
docker compose -f docker-compose.j3.yml down
docker compose -f docker-compose.j3.yml up -d
```

### Clarification documentation
- La stack de référence est décrite dans `README.stack.md` (Modern + variante J3 SQLite).
- Les instructions Streamlit historiques sont considérées **legacy** et ne doivent plus être utilisées pour un nouveau déploiement.


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

Paragraphe de mise à jour J2 : cette révision documente une proposition J2 commune entre README, ROADMAP et TODO afin d'assurer un suivi synchronisé des priorités, des critères de validation et du reporting quotidien.
