# Archive Queue System (T-ARCH-01)

## Overview

L'Archive Queue System est une file d'attente asynchrone pour les opérations de transfert et d'archivage de fichiers SMB. Il permet de gérer les opérations de copy, move et delete avec retry automatique, suivi de progression et priorisation.

## Architecture

### Composants principaux

1. **Database Schema** (`database/migrations/`)
   - `001_add_archive_jobs.sql` : Table `archive_jobs` avec types ENUM
   - `archive_jobs_stats` : Vue pour les statistiques
   - Fonctions d'acquisition atomique des jobs

2. **Transfer Worker** (`src/archive_transfer_worker.py`)
   - Worker asynchrone avec retry backoff exponentiel
   - Gestion des erreurs SMB et reconnexion automatique
   - Suivi de progression en temps réel

3. **API REST** (`src/api/main.py`)
   - Endpoints CRUD pour les jobs d'archivage
   - Suivi de progression et statistiques
   - Gestion des priorités et annulations

## Database Schema

### Table archive_jobs

```sql
CREATE TYPE archive_job_type AS ENUM ('copy', 'move', 'delete');
CREATE TYPE archive_job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

CREATE TABLE archive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type archive_job_type NOT NULL DEFAULT 'copy',
    source_path TEXT NOT NULL,
    dest_path TEXT,
    status archive_job_status NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source_size BIGINT,
    bytes_transferred BIGINT DEFAULT 0
);
```

### Fonctions principales

- `get_next_archive_job()` : Acquérir le prochain job atomiquement
- `update_archive_job_status()` : Mettre à jour le statut d'un job
- `cancel_archive_job()` : Annuler un job en cours

## API Endpoints

### Gestion des jobs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/archive/queue` | Créer un nouveau job d'archivage |
| GET | `/api/archive/queue` | Lister les jobs avec pagination |
| GET | `/api/archive/queue/{job_id}` | Détails d'un job spécifique |
| DELETE | `/api/archive/queue/{job_id}` | Annuler un job |
| GET | `/api/archive/queue/stats` | Statistiques de la queue |

### Modèles Pydantic

```python
class ArchiveJobCreate(BaseModel):
    job_type: ArchiveJobType = ArchiveJobType.COPY
    source_path: str
    dest_path: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)

class ArchiveJobResponse(BaseModel):
    id: str
    job_type: str
    source_path: str
    dest_path: Optional[str]
    status: str
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    source_size: Optional[int]
    bytes_transferred: int
```

## Retry avec Backoff Exponentiel

### Configuration

```python
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # secondes
DEFAULT_MAX_DELAY = 60.0  # secondes
DEFAULT_EXPONENTIAL_BASE = 2.0
```

### Algorithme

1. **Calcul du délai** : `delay = base_delay * (exponential_base ^ retry_count)`
2. **Cap maximum** : `delay = min(delay, max_delay)`
3. **Jitter aléatoire** : ±25% pour éviter les thundering herds

### Décorateur

```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
def transfer_file(source, dest):
    # Code de transfert
    pass
```

## Worker Architecture

### Flux de traitement

1. **Acquisition atomique** : `get_next_archive_job()`
2. **Validation préliminaire** : Vérification des chemins et permissions
3. **Exécution avec retry** : Transfert SMB avec backoff
4. **Mise à jour statut** : `completed` ou `failed`
5. **Nettoyage** : Libération des ressources

### Types d'opérations

- **COPY** : Copie avec vérification SHA-256
- **MOVE** : Déplacement avec option lien .url
- **DELETE** : Suppression sécurisée

## Monitoring

### Métriques disponibles

- Jobs par statut (pending/running/completed/failed)
- Volume total en attente et transféré
- Taux de réussite/échec
- Temps moyen d'exécution

### Logs structurés

```python
logger.info(f"🚀 Job {job_id} started: {source_path} → {dest_path}")
logger.warning(f"⚠️  Job {job_id} retry {retry_count}/{max_retries}: {error}")
logger.error(f"❌ Job {job_id} failed: {error}")
logger.info(f"✅ Job {job_id} completed: {bytes_transferred} bytes")
```

## Utilisation

### Créer un job

```bash
curl -X POST http://localhost:8000/api/archive/queue \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "copy",
    "source_path": "\\\\server\\share\\file.txt",
    "dest_path": "\\\\archive\\storage\\file.txt",
    "priority": 8
  }'
```

### Suivre la progression

```bash
curl http://localhost:8000/api/archive/queue/stats
```

### Annuler un job

```bash
curl -X DELETE http://localhost:8000/api/archive/queue/{job_id}
```

## Configuration

### Variables d'environnement

- `OPENINDEX_ARCHIVE_WORKER_COUNT` : Nombre de workers (défaut: 2)
- `OPENINDEX_ARCHIVE_MAX_RETRIES` : Max retries (défaut: 3)
- `OPENINDEX_ARCHIVE_BASE_DELAY` : Délai base retry (défaut: 1.0s)
- `OPENINDEX_ARCHIVE_MAX_DELAY` : Délai max retry (défaut: 60s)

### Migration

```bash
# Appliquer les migrations
python scripts/migrate.py apply

# Vérifier le statut
python scripts/migrate.py status
```

## Performance

### Optimisations

- **Acquisition atomique** : Évite les doubles traitements
- **Batch updates** : Mise à jour par lots des progressions
- **Connection pooling** : Réutilisation des connexions SMB
- **Async I/O** : Parallélisation des transferts

### Limites

- Max 10 jobs concurrents par worker
- Taille max fichier : 10GB (configurable)
- Timeout connexion SMB : 30s

## Sécurité

### Permissions

- Validation des chemins SMB
- Isolation des jobs par configuration
- Audit trail complet des opérations

### Intégrité

- Vérification SHA-256 systématique
- Rollback automatique en cas d'échec
- Logs détaillés pour debugging

## Dépannage

### Erreurs communes

1. **SMBConnectionError** : Vérifier connectivité réseau
2. **Permission denied** : Valider credentials SMB
3. **Disk full** : Vérifier espace disponible cible
4. **Checksum mismatch** : Corruption lors transfert

### Logs utiles

```bash
# Logs du worker
tail -f logs/archive_transfer_worker.log

# Logs API
tail -f logs/api.log

# Logs système
journalctl -u openindex-archive
```

## Roadmap

### Prochaines versions

- [ ] Support des archives compressées
- [ ] Intégration S3/Glacier
- [ ] Interface web de monitoring
- [ ] Notifications webhook
- [ ] Support des gros fichiers (>10GB)

### Tests

```bash
# Tests unitaires
pytest tests/test_archive_worker.py

# Tests de charge
python scripts/load_test_archive.py --jobs 1000

# Tests end-to-end
python scripts/e2e_archive_test.py
```
