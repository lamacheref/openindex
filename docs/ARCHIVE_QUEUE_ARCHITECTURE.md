# Architecture des Queues d'Archivage (T-ARCH-02)

## Vue d'ensemble

Le système d'archivage d'OpenIndex permet d'automatiser le transfert de fichiers entre espaces SMB via une **queue de jobs** et un **worker dédié**.

## Composants Principaux

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARCHIVE QUEUE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐   │
│  │   API        │    │   PostgreSQL     │    │   Archive Transfer       │   │
│  │   FastAPI    │───▶│   archive_jobs   │───▶│   Worker                 │   │
│  │              │    │   archive_schedules│   │   (Threaded)           │   │
│  └──────────────┘    └──────────────────┘    └──────────────────────────┘   │
│         │                      │                        │                    │
│         │                      │                        │                    │
│         ▼                      ▼                        ▼                    │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐   │
│  │   UI Web     │    │   Views/Funcs    │    │   SMB Operations         │   │
│  │   AlpineJS   │    │   get_next_...   │    │   copy/move/delete       │   │
│  └──────────────┘    └──────────────────┘    └──────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Archive Scheduler (Cron)                          │   │
│  │         Détecte et crée automatiquement les jobs planifiés          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1. Base de Données

### Tables

#### `archive_jobs`
Queue principale des jobs de transfert.

```sql
- id UUID PRIMARY KEY
- job_type: 'copy' | 'move' | 'delete'
- source_path: TEXT NOT NULL
- dest_path: TEXT (optionnel pour delete)
- status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
- priority: INTEGER (1-10, 1=haute)
- retry_count: INTEGER
- max_retries: INTEGER DEFAULT 3
- error_message: TEXT
- started_at, completed_at, created_at: TIMESTAMPTZ
- source_size, bytes_transferred: BIGINT
```

#### `archive_schedules` (Nouveau - T-ARCH-02)
Configuration des tâches planifiées.

```sql
- id UUID PRIMARY KEY
- name, description: VARCHAR/TEXT
- cron_expression: VARCHAR (ex: "0 2 * * *")
- timezone: VARCHAR DEFAULT 'Europe/Paris'
- is_active: BOOLEAN
- job_type: 'copy' | 'move' | 'delete'
- source_pattern: TEXT (pattern de fichiers)
- dest_path: TEXT
- priority: INTEGER
- max_age_days, min_size_bytes, max_size_bytes: INTEGER/BIGINT
- file_extensions: TEXT[]
- last_run_at, next_run_at: TIMESTAMPTZ
- run_count: INTEGER
```

### Fonctions PostgreSQL

#### `get_next_archive_job()`
Fonction atomique pour récupérer et verrouiller le prochain job :

```sql
UPDATE archive_jobs 
SET status = 'running', started_at = CURRENT_TIMESTAMP
WHERE id = (
    SELECT id FROM archive_jobs 
    WHERE status = 'pending' 
       OR (status = 'failed' AND retry_count < max_retries)
    ORDER BY priority ASC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING ...;
```

## 2. API Endpoints

### Jobs
- `POST /api/archive/queue` - Créer un job
- `GET /api/archive/queue` - Lister les jobs (filtres: status, job_type, priority)
- `GET /api/archive/queue/{id}` - Détails d'un job
- `DELETE /api/archive/queue/{id}` - Annuler un job (si pending/running)
- `POST /api/archive/queue/{id}/retry` - Réessayer un job failed

### Scheduling (Nouveau - T-ARCH-02)
- `POST /api/archive/schedules` - Créer un schedule
- `GET /api/archive/schedules` - Lister les schedules
- `PUT /api/archive/schedules/{id}` - Modifier un schedule
- `DELETE /api/archive/schedules/{id}` - Supprimer
- `POST /api/archive/schedules/{id}/toggle` - Activer/désactiver
- `GET /api/archive/schedules/{id}/runs` - Historique d'exécution

### Monitoring (Nouveau - T-ARCH-02)
- `GET /api/archive/monitoring/queue` - Vue temps réel de la queue
- `GET /api/archive/monitoring/dashboard` - Métriques agrégées
- `GET /api/archive/settings` - Paramètres globaux
- `PUT /api/archive/settings` - Modifier les paramètres

### Worker Health
- `GET /api/transfer/worker/health` - État du worker (running/pending jobs, taux de réussite)

## 3. Workers

### ArchiveTransferWorker
```python
class ArchiveTransferWorker:
    - poll_interval: int = 5  # secondes
    - max_concurrent: int = 3  # transferts parallèles
    - chunk_size: int = 8192  # 8KB
    
    def _worker_loop():
        while running:
            if active_transfers < max_concurrent:
                job = _get_next_job()
                if job:
                    _start_transfer(job)
            sleep(poll_interval)
    
    def _execute_transfer(job):
        try:
            if job.type == 'copy': _copy_file(job)
            elif job.type == 'move': _move_file(job)
            elif job.type == 'delete': _delete_file(job)
            _update_job_status(job.id, success=True)
        except Exception as e:
            _update_job_status(job.id, success=False, error=e)
```

**Features:**
- Retry automatique avec backoff exponentiel
- Vérification checksum après copie
- Transfert par chunks pour les gros fichiers
- Gestion des erreurs SMB

### ArchiveScheduler (Nouveau - T-ARCH-02)
```python
class ArchiveScheduler:
    - poll_interval: int = 60  # secondes
    
    def _scheduler_loop():
        while running:
            schedules = get_due_schedules()
            for schedule in schedules:
                files = find_matching_files(schedule.pattern)
                for file in files:
                    create_archive_job(file, schedule.config)
                update_schedule_next_run(schedule)
            sleep(poll_interval)
```

**Features:**
- Expressions cron supportées (via `croniter`)
- Filtres: âge, taille, extensions
- Timezone support
- Historique des exécutions

## 4. Interface Utilisateur

### Page de Monitoring: `/archive-monitoring.html`

**Dashboard:**
- Métriques temps réel (jobs pending/running, taux de succès, volume transféré)
- Graphiques d'activité

**File d'Attente:**
- Liste des jobs avec progression visuelle
- Actions: Annuler (pending), Retry (failed)
- Filtres par statut

**Schedules:**
- Liste des tâches planifiées avec statut actif/inactif
- Prochaine exécution
- Historique des runs
- Création/édition de schedules

## 5. Workflows

### Création d'un Job
```
Utilisateur/API → POST /api/archive/queue
                    ↓
            Validation (dest_path requis pour copy/move)
                    ↓
            INSERT INTO archive_jobs (status='pending')
                    ↓
            Retourne ArchiveJobResponse
```

### Exécution par le Worker
```
Worker Loop → get_next_archive_job() 
                ↓ (atomic lock)
            UPDATE status='running'
                ↓
            Thread de transfert
                ↓
            copy/move/delete avec retry
                ↓
            UPDATE status='completed'/'failed'
```

### Schedule Automatique
```
Scheduler Loop → SELECT schedules WHERE next_run_at <= NOW()
                    ↓
            SELECT files FROM files WHERE path LIKE pattern
                AND age > max_age_days
                AND size BETWEEN min AND max
                    ↓
            INSERT archive_jobs pour chaque fichier
                    ↓
            UPDATE schedule.next_run_at
```

## 6. Sécurité & Fiabilité

### Atomicité
- `FOR UPDATE SKIP LOCKED` pour l'acquisition de jobs
- Empêche les race conditions entre workers

### Retry & Backoff
```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
def _copy_file(job):
    ...
```

### Isolation
- Chaque transfert dans un thread séparé
- Max concurrent configurable

### Persistance
- Tous les états en PostgreSQL
- Possibilité de redémarrer sans perte de jobs

## 7. Configuration

### Variables d'Environnement
```bash
# Worker
ARCHIVE_WORKER_POLL_INTERVAL=5
ARCHIVE_WORKER_MAX_CONCURRENT=3
ARCHIVE_WORKER_CHUNK_SIZE=8192

# Scheduler
ARCHIVE_SCHEDULER_ENABLED=true
ARCHIVE_SCHEDULER_POLL_INTERVAL=60

# Database (utilise les mêmes variables que le reste de l'app)
POSTGRES_HOST=localhost
POSTGRES_DB=openindex
...
```

### Settings DB (T-ARCH-02)
```sql
archive.default_priority = 5
archive.max_retries = 3
archive.worker.poll_interval = 5
archive.worker.max_concurrent = 3
archive.retention_days = 30
archive.cleanup_interval_hours = 24
```

## 8. Tests

### Suite de Tests
- `tests/test_archive_queue_api.py` - 31 tests API
- `tests/test_archive_transfer_worker.py` - 22 tests worker
- `tests/test_archive_scheduler.py` - (à créer)

### Test Critiques
- Atomicité de l'acquisition de jobs
- Transitions de statut
- Retry avec backoff
- Vérification checksum
- Schedule cron parsing

## 9. Déploiement

### Démarrer le Worker
```bash
python -m src.archive_transfer_worker \
    --poll-interval 5 \
    --max-concurrent 3
```

### Démarrer le Scheduler
```bash
python -m src.archive_scheduler \
    --poll-interval 60
```

### Docker Compose
```yaml
services:
  archive-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - POSTGRES_HOST=db
      - ARCHIVE_WORKER_MAX_CONCURRENT=3
    depends_on:
      - db
  
  archive-scheduler:
    build:
      context: .
      dockerfile: Dockerfile.scheduler
    environment:
      - POSTGRES_HOST=db
      - ARCHIVE_SCHEDULER_ENABLED=true
    depends_on:
      - db
```

---

## Références

- **Issue #75**: Tests pytest complexes corrigés avec fixtures
- **Migration 001**: `database/migrations/001_add_archive_jobs.sql`
- **Migration 002**: `database/migrations/002_add_archive_scheduling.sql`
- **Module Worker**: `src/archive_transfer_worker.py`
- **Module Scheduler**: `src/archive_scheduler.py`
- **UI Monitoring**: `frontend/archive-monitoring.html`
