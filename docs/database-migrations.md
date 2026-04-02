# Database Migration System

## Overview

Le système de migrations gère les évolutions du schéma PostgreSQL de manière versionnée, atomique et réversible. Il permet de suivre les migrations appliquées, de créer de nouvelles migrations et de gérer les rollbacks en production.

## Architecture

### Composants principaux

1. **Migration Scripts** (`database/migrations/`)
   - Fichiers SQL versionnés (001, 002, ...)
   - Tracking avec checksums SHA-256
   - Structure standardisée pour compatibilité

2. **Migration Manager** (`scripts/migrate.py`)
   - CLI complet pour gérer les migrations
   - Support status, apply, create, rollback
   - Validation d'intégrité des migrations

3. **Schema Tracking** (`schema_migrations` table)
   - Historique des migrations appliquées
   - Checksums pour détection de modifications
   - Temps d'exécution pour monitoring

## Migration Scripts

### Structure de nommage

```
database/migrations/
├── 000_init_migrations.sql          # Table de tracking
├── 001_add_archive_jobs.sql        # Table archive_jobs
├── 002_add_user_authentication.sql  # Authentification
└── 003_add_file_metadata.sql       # Métadonnées fichiers
```

### Format des fichiers

```sql
-- ============================================================
-- Migration: 001_add_archive_jobs
-- Description: Add archive_jobs table and related types
-- Created: 2026-04-02
-- Dependencies: 000_init_migrations
-- ============================================================

-- Types ENUM
CREATE TYPE archive_job_type AS ENUM ('copy', 'move', 'delete');
CREATE TYPE archive_job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

-- Table principale
CREATE TABLE archive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type archive_job_type NOT NULL DEFAULT 'copy',
    source_path TEXT NOT NULL,
    dest_path TEXT,
    status archive_job_status NOT NULL DEFAULT 'pending',
    -- ... autres colonnes
);

-- Indexes
CREATE INDEX idx_archive_jobs_status ON archive_jobs(status);
CREATE INDEX idx_archive_jobs_priority ON archive_jobs(priority DESC);

-- Vues et fonctions
CREATE VIEW archive_jobs_stats AS
    SELECT 
        status,
        COUNT(*) as count,
        SUM(bytes_transferred) as total_bytes
    FROM archive_jobs
    GROUP BY status;

-- Fonctions d'acquisition atomique
CREATE OR REPLACE FUNCTION get_next_archive_job()
RETURNS UUID AS $$
    -- Implémentation atomique
$$ LANGUAGE plpgsql;
```

### Table de tracking

```sql
-- 000_init_migrations.sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64),
    execution_time_ms INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version);
CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at ON schema_migrations(applied_at);

COMMENT ON TABLE schema_migrations IS 'Tracks all applied database schema migrations';
```

## Migration Manager

### Commandes disponibles

```bash
# Vérifier le statut des migrations
python scripts/migrate.py status

# Appliquer toutes les migrations en attente
python scripts/migrate.py apply

# Appliquer une migration spécifique
python scripts/migrate.py apply --version 001

# Créer une nouvelle migration
python scripts/migrate.py create --name "add_user_authentication"

# Rollback (préparé)
python scripts/migrate.py rollback --version 001
```

### Options CLI

```bash
# Mode verbose
python scripts/migrate.py status --verbose

# Mode dry-run (simulation)
python scripts/migrate.py apply --dry-run

# Force application (dangereux)
python scripts/migrate.py apply --force

# Base de données spécifique
python scripts/migrate.py status --database postgresql://user:pass@host/db
```

### Configuration

```python
# scripts/migrate.py
import os
import argparse
import hashlib
import psycopg2
from pathlib import Path

# Configuration par défaut
DEFAULT_MIGRATIONS_DIR = "database/migrations"
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://openindex:password@localhost/openindex")
DEFAULT_LOCK_TIMEOUT = 30  # secondes
```

## Workflow de Migration

### 1. Créer une migration

```bash
# Créer le fichier template
python scripts/migrate.py create --name "add_file_metadata"

# Éditer le fichier généré
vim database/migrations/002_add_file_metadata.sql
```

### 2. Développer la migration

```sql
-- 002_add_file_metadata.sql
-- Types et tables
CREATE TYPE file_metadata_type AS ENUM ('exif', 'document', 'video');

CREATE TABLE file_metadata (
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    metadata_type file_metadata_type NOT NULL,
    metadata_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, metadata_type)
);

-- Indexes
CREATE INDEX idx_file_metadata_type ON file_metadata(metadata_type);
CREATE INDEX idx_file_metadata_data ON file_metadata USING gin(metadata_data);
```

### 3. Tester la migration

```bash
# Mode dry-run pour vérifier la syntaxe
python scripts/migrate.py apply --dry-run --version 002

# Appliquer sur base de test
DATABASE_URL="postgresql://test:test@localhost/test" python scripts/migrate.py apply --version 002
```

### 4. Déployer en production

```bash
# Vérifier statut actuel
python scripts/migrate.py status

# Appliquer la migration
python scripts/migrate.py apply --version 002

# Vérifier post-déploiement
python scripts/migrate.py status
```

## Sécurité et Intégrité

### Checksums SHA-256

Chaque migration est protégée par un checksum pour détecter les modifications post-apply :

```python
def calculate_migration_checksum(file_path: Path) -> str:
    """Calcule le SHA-256 du fichier de migration"""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_migration_integrity(version: str) -> bool:
    """Vérifie que la migration n'a pas été modifiée"""
    stored_checksum = get_stored_checksum(version)
    current_checksum = calculate_migration_checksum(get_migration_file(version))
    return stored_checksum == current_checksum
```

### Locking atomique

```sql
-- Verrouillage pour éviter les migrations concurrentes
BEGIN;
LOCK TABLE schema_migrations IN SHARE MODE;

-- Vérifier si migration déjà appliquée
SELECT 1 FROM schema_migrations WHERE version = '001';

-- Appliquer migration si nécessaire
INSERT INTO schema_migrations (version, description, checksum, execution_time_ms)
VALUES ('001', 'Add archive_jobs table', 'abc123...', 1500);

COMMIT;
```

## Rollback Strategy

### Rollback manuel

```sql
-- Rollback de la migration 001
BEGIN;
DROP TABLE IF EXISTS archive_jobs;
DROP TYPE IF EXISTS archive_job_type;
DROP TYPE IF EXISTS archive_job_status;
DELETE FROM schema_migrations WHERE version = '001';
COMMIT;
```

### Rollback automatisé (préparé)

```bash
# Créer le fichier de rollback
python scripts/migrate.py rollback --version 001 --create-rollback

# Éditer 001_rollback.sql
vim database/migrations/001_rollback.sql

# Appliquer le rollback
python scripts/migrate.py rollback --version 001
```

## Monitoring

### Métriques de migration

```sql
-- Vue des statistiques de migration
CREATE VIEW migration_stats AS
SELECT 
    COUNT(*) as total_migrations,
    SUM(execution_time_ms) as total_execution_time_ms,
    AVG(execution_time_ms) as avg_execution_time_ms,
    MAX(applied_at) as last_migration_at
FROM schema_migrations;

-- Historique des migrations
SELECT 
    version,
    description,
    applied_at,
    execution_time_ms,
    checksum
FROM schema_migrations 
ORDER BY applied_at DESC;
```

### Alertes

```python
# Monitoring des migrations lentes
def check_migration_performance():
    """Alerte si une migration prend trop de temps"""
    slow_migrations = get_slow_migrations(threshold_ms=5000)
    if slow_migrations:
        alert_team(f"Migrations lentes détectées: {slow_migrations}")

# Monitoring des checksums invalides
def check_migration_integrity():
    """Alerte si des checksums ne correspondent plus"""
    invalid_migrations = get_invalid_checksum_migrations()
    if invalid_migrations:
        alert_team(f"Checksums invalides: {invalid_migrations}")
```

## Bonnes Pratiques

### Développement de migrations

1. **Immutabilité** : Ne jamais modifier une migration déjà appliquée
2. **Test** : Toujours tester sur base de développement
3. **Rollback** : Préparer le rollback avant déploiement
4. **Documentation** : Commenter les changements complexes
5. **Performance** : Ajouter des indexes après chargement des données

### Déploiement

1. **Backup** : Sauvegarder la base avant migration
2. **Staging** : Tester sur environnement de staging
3. **Maintenance Window** : Planifier pendant périodes creuses
4. **Monitoring** : Surveiller les performances post-migration
5. **Rollback Plan** : Avoir un plan de retour immédiat

### Nommage

- **Préfixe numérique** : `001`, `002`, `003` (ordre chronologique)
- **Description claire** : `add_archive_jobs`, `create_user_table`
- **Snake case** : Utiliser underscores, pas de camelCase
- **Pas d'espaces** : Éviter les caractères spéciaux

## Dépannage

### Erreurs communes

1. **Migration déjà appliquée**
   ```
   ERROR: Migration 001 already applied
   ```
   Solution : `--force` ou vérifier version

2. **Checksum invalide**
   ```
   ERROR: Migration 001 checksum mismatch
   ```
   Solution : Restaurer depuis backup ou créer nouvelle migration

3. **Timeout de lock**
   ```
   ERROR: Lock timeout on schema_migrations
   ```
   Solution : Attendre libération ou augmenter timeout

4. **Syntax error SQL**
   ```
   ERROR: syntax error at or near "CREATE"
   ```
   Solution : Corriger syntaxe et recréer migration

### Logs utiles

```bash
# Logs du migration manager
tail -f logs/migrations.log

# Logs PostgreSQL
tail -f /var/log/postgresql/postgresql-*.log

# Logs d'erreur détaillés
python scripts/migrate.py status --verbose
```

### Commandes de debug

```python
# Vérifier checksums
python -c "
from scripts.migrate import verify_all_migrations
verify_all_migrations()
"

# Forcer réinitialisation
python -c "
from scripts.migrate import reset_migrations
reset_migrations(confirm=True)
"
```

## Roadmap

### Fonctionnalités futures

- [ ] Support des migrations multi-bases
- [ ] Interface web de gestion
- [ ] Validation automatique des migrations
- [ ] Support des migrations Go/Java
- [ ] Integration avec CI/CD

### Améliorations

- [ ] Mode transactionnel complet
- [ ] Support des données volumineuses
- [ ] Migration zero-downtime
- [ ] Rollback automatique sur erreur
