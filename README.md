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

### Accès aux Services
- **Frontend** : http://localhost:3000
- **API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **WebSocket** : ws://localhost:8000/ws
- **PostgreSQL** : localhost:5432
- **pgAdmin** : http://localhost:5050

### Configuration
```bash
# Variables d'environnement clés
POSTGRES_PASSWORD=votre_mot_de_passe
SMB_SERVER=votre_serveur_smb
SMB_USERNAME=votre_utilisateur
SMB_PASSWORD=votre_mot_de_passe
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
- **Backend** : FastAPI + PostgreSQL + WebSocket
- **Frontend** : VanillaJS + Alpine.js + HTMX + TailwindCSS
- **Infrastructure** : Docker + Nginx + CI/CD Gitea

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
- **PostgreSQL** : `pg_isready` automatique
- **Crawler** : Logs progression dans `/app/logs`

## 🚨 Dépannage

### Problèmes Connus
1. **Nginx proxy** : Corrigé dans nginx.conf (localhost:8000)
2. **Builds Docker** : PYTHONPATH corrigé dans Dockerfile.api
3. **Requirements** : hashlib supprimé de requirements.crawler.txt

### Solutions
```bash
# Problème de connexion PostgreSQL
docker-compose -f docker-compose.modern.yml logs postgres

# Problème API
docker-compose -f docker-compose.modern.yml logs api

# Rebuild forcé
docker-compose -f docker-compose.modern.yml build --no-cache
```

### Clarification documentation
- La stack de référence est décrite dans `README.stack.md` (FastAPI + frontend statique + PostgreSQL).
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
