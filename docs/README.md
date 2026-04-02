# Documentation OpenIndex — indexation et archivage SMB intelligent

## 📚 Index de la Documentation

### 🏗️ Architecture et Composants (T-ARCH-01)

- **[Archive Queue System](archive-queue-system.md)** - Système de file d'attente pour les opérations d'archivage
- **[Transfer Worker Architecture](transfer-worker-architecture.md)** - Architecture du worker de transfert avec retry et monitoring
- **[SMB Health Monitoring](smb-health-monitoring.md)** - Surveillance des serveurs SMB et gestion des pannes
- **[Database Migrations](database-migrations.md)** - Système de gestion des migrations PostgreSQL

### 🔌 API Reference

- **[API Archive Queue](api-archive-queue.md)** - Documentation complète de l'API REST pour la gestion des jobs

### 📖 Parcours Historique

#### Par phase

1. **Stabilisation initiale (historique)** : `docs/phases/J3_STABILISATION.md`
2. **J4 — Migration PostgreSQL** : `docs/phases/J4_MIGRATION.md`
3. **J5 — Qualité & observabilité** : `docs/phases/J5_QUALITE_OBSERVABILITE.md`
4. **J6 — T-ARCH-01 Archive Queue** : *(phase actuelle)*

#### Exploitation

- Runbook et protocoles : `docs/operations/EXPLOITATION.md`
- Gate CI PostgreSQL : `docs/operations/CI_POSTGRESQL_GATE.md`
- SLI/SLO J5 : `docs/operations/J5_SLI_SLO.md`
- Release gate J5 : `docs/operations/J5_RELEASE_GATE.md`
- Baseline observabilité J5 : `docs/operations/J5_OBSERVABILITY_BASELINE.md`
- Runbook exploitation : `docs/operations/EXPLOITATION.md`
- Contrat UI opérateur : `docs/definition_ui.md`

### 📊 Artefacts et Benchmarks

- Dry-run migration : `docs/artifacts/migration_dry_run_j3_j4.json`
- Benchmark DB : `docs/artifacts/bench_sqlite_vs_postgresql.json` avec PostgreSQL
- Benchmark PostgreSQL actif : `docs/artifacts/bench_postgresql_active_2026-03-26.json`

## 🚀 Démarrage Rapide (T-ARCH-01)

### 1. Installation

```bash
# Cloner le projet
git clone https://github.com/lamacheref/openindex.git
cd openindex

# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données
cp .env.example .env
# Éditer .env avec vos paramètres
```

### 2. Initialisation

```bash
# Appliquer les migrations T-ARCH-01
python scripts/migrate.py apply

# Démarrer les services
python src/api/main.py &
python src/transfer_worker.py &
```

### 3. Vérification

```bash
# Vérifier l'API
curl http://localhost:8000/health

# Vérifier le worker
curl http://localhost:8000/api/transfer/worker/health

# Vérifier les jobs d'archivage
curl http://localhost:8000/api/archive/queue/stats
```

## 🏗️ Architecture T-ARCH-01

### Composants Principaux

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway    │───▶│   Job Queue      │───▶│  Transfer Worker │
│   (FastAPI)      │    │ (PostgreSQL)    │    │   (AsyncIO)      │
│                 │    │                 │    │                 │
│   Archive Models │    │  Retry Engine    │    │ SMB Monitoring  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ PostgreSQL DB    │    │   SMB Storage  │
                       │ (schema + data)  │    │  (partages)     │
                       └──────────────────┘    └─────────────────┘
```

### Flux de Données T-ARCH-01

1. **Indexation** : Crawler SMB → PostgreSQL (J3-J5)
2. **Archivage** : API Queue → Worker → SMB (T-ARCH-01)
3. **Monitoring** : Health Monitor → Crawler (Issue #65)
4. **Transfert** : Worker → SMB avec retry backoff (T-ARCH-01)

## 🔧 Configuration

### Variables d'Environnement

```bash
# Base de données
DATABASE_URL=postgresql://user:pass@localhost/openindex

# SMB Configuration
OPENINDEX_SMB_SERVER=server.local
OPENINDEX_SMB_SHARE=share
OPENINDEX_SMB_USERNAME=user
OPENINDEX_SMB_PASSWORD=pass

# Archive Queue (T-ARCH-01)
OPENINDEX_ARCHIVE_WORKER_COUNT=4
OPENINDEX_TRANSFER_MAX_CONCURRENT=10
OPENINDEX_TRANSFER_MAX_RETRIES=3
OPENINDEX_TRANSFER_BASE_DELAY=1.0
OPENINDEX_TRANSFER_MAX_DELAY=60.0

# Monitoring SMB (Issue #65)
OPENINDEX_SMB_CHECK_INTERVAL=30
OPENINDEX_SMB_TIMEOUT=5
OPENINDEX_SMB_MAX_FAILURES=3
OPENINDEX_CRAWL_PAUSE_ON_SMB_DOWN=true
```

## 📊 Monitoring et Observabilité

### Métriques T-ARCH-01

- **Jobs Archive** : Statut, volume, performance, retry
- **SMB Health** : Connectivité, latence, pannes, reprises
- **Workers** : Actifs, charge, throughput, erreurs
- **Database** : Migrations, connexions, performance

### Endpoints de Monitoring

```bash
# Santé globale
curl http://localhost:8000/health

# Statistiques archive (T-ARCH-01)
curl http://localhost:8000/api/archive/queue/stats

# État du worker
curl http://localhost:8000/api/transfer/worker/health

# Monitoring SMB (Issue #65)
curl http://localhost:8000/api/smb/health
```

## 🔍 Dépannage T-ARCH-01

### Problèmes Communs

1. **Jobs bloqués en pending**
   ```bash
   # Vérifier le statut des workers
   curl http://localhost:8000/api/transfer/worker/health
   
   # Vérifier la queue
   curl "http://localhost:localhost:8000/api/archive/queue?status=pending"
   ```

2. **SMB server down**
   ```bash
   # Vérifier le monitoring SMB
   curl http://localhost:8000/api/smb/health
   
   # Logs du health monitor
   tail -f logs/smb_health_monitor.log
   ```

3. **Retry loops excessifs**
   ```bash
   # Vérifier configuration retry
   grep -i "retry" logs/transfer_worker.log
   
   # Ajuster les paramètres si nécessaire
   export OPENINDEX_TRANSFER_MAX_RETRIES=3
   ```

### Logs Utiles

```bash
# Logs API (incl. T-ARCH-01)
tail -f logs/api.log

# Logs worker (T-ARCH-01)
tail -f logs/transfer_worker.log

# Logs SMB monitoring (Issue #65)
tail -f logs/smb_health_monitor.log

# Logs crawler
tail -f logs/smb_crawler.log
```

## 📈 Performance T-ARCH-01

### Benchmarks

| Opération | Configuration | Résultat |
|-----------|----------------|---------|
| Transfert Archive | 4 workers | ~80MB/s |
| Retry avec Backoff | 3 retries | <5s overhead |
| Monitoring SMB | 30s interval | <1% CPU |
| API Queue | 50 concurrent | ~200 req/s |

### Optimisations T-ARCH-01

- **Atomic Job Acquisition** : Éviter les doubles traitements
- **Exponential Backoff** : Retry intelligent avec jitter
- **Progress Tracking** : Suivi temps réel non bloquant
- **Connection Pooling** : Réutilisation des connexions SMB

## 🔐 Sécurité

### Permissions T-ARCH-01

- **SMB** : Accès en lecture/écriture aux partages
- **Database** : Accès aux tables `archive_jobs` et `schema_migrations`
- **API** : Authentification par tokens JWT

### Isolation

- **Jobs isolés** : Chaque job s'exécute dans son contexte
- **Sandboxing** : Pas d'accès direct au système de fichiers
- **Audit Trail** : Logs complets de toutes les opérations d'archivage

## 📝 Historique des Versions

### Version 0.5.0 (T-ARCH-01) - *Actuelle*

- ✅ Système de queue d'archivage asynchrone
- ✅ Worker de transfert avec retry backoff exponentiel
- ✅ Monitoring SMB intelligent (Issue #65)
- ✅ Migrations PostgreSQL versionnées
- ✅ API REST complète pour les jobs
- ✅ Interface WebSocket pour monitoring temps réel

### Version 0.4.18 (J5)

- ✅ Crawler SMB avec PostgreSQL
- ✅ Interface web d'exploration
- ✅ Détection des doublons
- ✅ Statistiques et monitoring
- ✅ SLI/SLO et observabilité

### Version 0.4.17 (J4)

- ✅ Migration complète vers PostgreSQL
- ✅ Performance et stabilité améliorées
- ✅ Baseline monitoring

## 🚀 Déploiement

### Docker (T-ARCH-01)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

# Démarrer tous les services
CMD ["python", "scripts/start_all.sh"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:5432/openindex
    depends_on:
      - postgres
      - redis
  
  worker:
    build: .
    command: python src/transfer_worker.py
    environment:
      - DATABASE_URL=postgresql://postgres:5432/openindex
    depends_on:
      - postgres
  
  monitoring:
    build: .
    command: python src/smb_crawler_worker_monitoring.py
    environment:
      - DATABASE_URL=postgresql://postgres:5432/openindex
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=openindex
      - POSTGRES_USER=openindex
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

## 📞 Support et Communauté

### Documentation technique

- **GitHub Issues** : https://github.com/lamacheref/openindex/issues
- **Wiki** : https://github.com/lamacheref/openindex/wiki
- **Discord** : Serveur de support technique

### Canaux de communication

- **Issues GitHub** : Rapports de bugs et demandes de fonctionnalités
- **Discussions GitHub** : Propositions techniques et architecture
- **Stack Overflow** : Support technique (tags `openindex`)

---

*Pour la documentation détaillée des composants T-ARCH-01, consultez les fichiers individuels listés ci-dessus.*
