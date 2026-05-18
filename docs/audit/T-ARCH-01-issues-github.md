# Issues GitHub à créer — T-ARCH-01 Tests Failed

**Milestone:** T-ARCH-01  
**Label:** bug  
**Date:** 2026-04-02  
**Source:** `tests/test_archive_transfer_worker.py`, `tests/test_archive_queue_api.py`

---

## Issue #1 — IndexError dans retry decorator (args vide)

**Title:** `test_retry_success_after_failure` — IndexError quand args vide dans retry decorator

**Labels:** `bug`, `T-ARCH-01`, `tests`, `high-priority`

**Milestone:** T-ARCH-01

**Description:**
```
Le test `test_retry_success_after_failure` échoue avec une IndexError dans le décorateur `retry_with_backoff`.

Erreur:
```
File "src/archive_transfer_worker.py", line 101, in wrapper
    if hasattr(args[0], 'logger'):
       ^^^^^^
IndexError: tuple index out of range
```

Cause: Le décorateur suppose que `args[0]` existe toujours (self pour méthodes de classe), mais quand une fonction simple (sans self) est décorée, args peut être vide.

Correction appliquée partiellement: Vérification `if args and hasattr(args[0], 'logger')` ajoutée aux lignes 101 et 113.

À vérifier: S'assurer que tous les chemins de code testés passent correctement.
```

**Fichier:** `src/archive_transfer_worker.py:101`

---

## Issue #2 — IndexError dans bloc final retry

**Title:** `test_retry_exhausted_raises_exception` — IndexError dans bloc final du retry decorator

**Labels:** `bug`, `T-ARCH-01`, `tests`, `high-priority`

**Milestone:** T-ARCH-01

**Description:**
```
Le test `test_retry_exhausted_raises_exception` échoue avec une IndexError dans le bloc final du décorateur retry.

Erreur:
```
File "src/archive_transfer_worker.py", line 113, in wrapper
    if hasattr(args[0], 'logger'):
       ^^^^^^
IndexError: tuple index out of range
```

Cause: Même problème que #1 — accès à args[0] sans vérifier si args est non-vide.

Correction: Même fix que #1 — utiliser `if args and hasattr(args[0], 'logger')`.
```

**Fichier:** `src/archive_transfer_worker.py:113`

---

## Issue #3 — IndexError avec max_retries=0

**Title:** `test_retry_with_zero_max_retries` — IndexError quand max_retries=0

**Labels:** `bug`, `T-ARCH-01`, `tests`, `edge-case`

**Milestone:** T-ARCH-01

**Description:**
```
Le test `test_retry_with_zero_max_retries` échoue avec une IndexError.

Scénario: Lorsque max_retries=0, le décorateur doit exécuter la fonction une seule fois sans retry. L'erreur d'IndexError se produit dans le logging du retry.

Erreur:
```
IndexError: tuple index out of range
```

Cause: Accès à args[0] sans vérification dans le bloc de logging.

Note: Ce cas de bord (max_retries=0) est rare en production mais doit être géré correctement.
```

**Fichier:** `src/archive_transfer_worker.py`

---

## Issue #4 — Tests API utilisent IDs non-UUID

**Title:** Mocks API — IDs non-UUID (job-123) rejetés par PostgreSQL

**Labels:** `bug`, `T-ARCH-01`, `tests`, `api`, `mock`

**Milestone:** T-ARCH-01

**Description:**
```
Les tests API utilisent des IDs string comme "job-123" qui sont rejetés par PostgreSQL car la colonne id est de type UUID.

Erreur:
```
ERROR: invalid input syntax for type uuid: "job-123"
LINE 1: SELECT status::text FROM archive_jobs WHERE id = 'job-123'
                                                         ^
```

Tests affectés:
- test_get_job_success
- test_get_job_not_found
- test_cancel_pending_job
- test_cancel_running_job
- test_cancel_already_completed_job
- test_cancel_already_failed_job
- test_cancel_nonexistent_job
- test_retry_failed_job
- test_retry_cancelled_job
- test_retry_pending_job
- test_retry_running_job
- test_retry_nonexistent_job
- test_list_jobs_with_data
- test_list_jobs_with_status_filter
- test_list_jobs_with_job_type_filter
- test_list_jobs_pagination
- test_get_stats_empty
- test_get_stats_with_data

Solution: Utiliser des UUID valides dans les mocks (ex: "550e8400-e29b-41d4-a716-446655440000") ou configurer le mock adapter pour accepter n'importe quel ID.
```

**Fichier:** `tests/test_archive_queue_api.py`

---

## Issue #5 — Tests Worker Health mocks incomplets

**Title:** Tests Worker Health — Mocks COUNT(*) non configurés

**Labels:** `bug`, `T-ARCH-01`, `tests`, `api`, `mock`

**Milestone:** T-ARCH-01

**Description:**
```
Les tests de Worker Health échouent car les mocks retournent 0 pour tous les COUNT(*), ce qui fait que le status est toujours "healthy".

Tests affectés:
- test_worker_health_healthy
- test_worker_health_degraded
- test_worker_health_unhealthy

Erreurs:
```
assert data["running_jobs"] == 2  # Actual: 0
assert data["status"] == "degraded"  # Actual: "healthy"
assert data["status"] == "unhealthy"  # Actual: "healthy"
```

Cause: Le mock `mock_adapter.execute_query` retourne des valeurs par défaut (0, None, []) qui ne permettent pas de tester les différents états de santé.

Solution: Configurer les side_effect des mocks pour retourner les valeurs appropriées selon la requête SQL.
```

**Fichier:** `tests/test_archive_queue_api.py:463`

---

## Issue #6 — CREATE TYPE idempotent dans init.sql

**Title:** CREATE TYPE archive_job_type échoue si type existe déjà

**Labels:** `bug`, `T-ARCH-01`, `database`, `fixed`

**Milestone:** T-ARCH-01

**Description:**
```
L'initialisation de la base échoue avec:
```
psycopg2.errors.DuplicateObject: type "archive_job_type" already exists
```

Quand la base est réinitialisée ou quand plusieurs services essaient de créer les types simultanément.

**Statut:** ✅ CORRIGÉ
**Solution:** Utilisation de blocs DO $$ avec IF NOT EXISTS:
```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'archive_job_type') THEN
        CREATE TYPE archive_job_type AS ENUM ('copy', 'move', 'delete');
    END IF;
END $$;
```
```

**Fichier:** `database/init.sql:240`

---

## Issue #7 — PoolError double putconn

**Title:** psycopg2.pool.PoolError: trying to put unkeyed connection

**Labels:** `bug`, `T-ARCH-01`, `database`, `critical`, `fixed`

**Milestone:** T-ARCH-01

**Description:**
```
Erreur critique lors des opérations DB:
```
psycopg2.pool.PoolError: trying to put unkeyed connection
```

Cause: Double appel à `self.connection_pool.putconn(conn)` — une fois dans le bloc `except`, une fois dans le bloc `finally`.

**Statut:** ✅ CORRIGÉ
**Solution:** Supprimer le `putconn()` du bloc `except`, ne le garder que dans `finally`:
```python
except Exception as e:
    if conn:
        conn.rollback()
        # REMOVED: self.connection_pool.putconn(conn)
    raise
finally:
    if conn:
        self.connection_pool.putconn(conn)
```
```

**Fichier:** `src/postgres_adapter.py:83`

---

## Issue #8 — SMBConnectionError n'existe pas

**Title:** ImportError: cannot import name 'SMBConnectionError' from 'smbprotocol.exceptions'

**Labels:** `bug`, `T-ARCH-01`, `smb`, `fixed`

**Milestone:** T-ARCH-01

**Description:**
```
Erreur d'import:
```
ImportError: cannot import name 'SMBConnectionError' from 'smbprotocol.exceptions'
```

La classe correcte dans smbprotocol est `SMBConnectionClosed`, pas `SMBConnectionError`.

**Statut:** ✅ CORRIGÉ
**Solution:** Remplacer `SMBConnectionError` par `SMBConnectionClosed` dans:
- `src/archive_transfer_worker.py:21`
- `src/smb_health_monitor.py:14`
```

**Fichier:** `src/archive_transfer_worker.py`, `src/smb_health_monitor.py`

---

## Issue #9 — Import Enum manquant dans api/main.py

**Title:** NameError: name 'Enum' is not defined dans api/main.py

**Labels:** `bug`, `T-ARCH-01`, `api`, `fixed`

**Milestone:** T-ARCH-01

**Description:**
```
Erreur au démarrage de l'API:
```
NameError: name 'Enum' is not defined
```

Classe `ArchiveJobType` hérite de `Enum` mais l'import est manquant.

**Statut:** ✅ CORRIGÉ
**Solution:** Ajouter `from enum import Enum` en haut du fichier.
```

**Fichier:** `src/api/main.py:27`

---

## Issue #10 — scripts/migrate.py paramètre fetch inexistant

**Title:** PostgreSQLAdapter.execute_query() got an unexpected keyword argument 'fetch'

**Labels:** `bug`, `T-ARCH-01`, `migration`, `fixed`

**Milestone:** T-ARCH-01

**Description:**
```
Le script de migration échoue avec:
```
TypeError: PostgreSQLAdapter.execute_query() got an unexpected keyword argument 'fetch'
```

Cause: La méthode `execute_query` ne prend pas de paramètre `fetch`, mais le script migrate.py l'utilise.

**Statut:** ✅ CORRIGÉ
**Solution:** Supprimer le paramètre `fetch=True`/`fetch=False` des appels `execute_query()` dans `scripts/migrate.py`.
```

**Fichier:** `scripts/migrate.py`

---

## Récapitulatif

| Issue | Titre | Status | Priorité |
|-------|-------|--------|----------|
| #1 | IndexError retry decorator (args vide) | 🔴 À corriger | High |
| #2 | IndexError bloc final retry | 🔴 À corriger | High |
| #3 | IndexError max_retries=0 | 🔴 À corriger | Medium |
| #4 | Mocks API IDs non-UUID | 🔴 À corriger | High |
| #5 | Tests Worker Health mocks incomplets | 🔴 À corriger | Medium |
| #6 | CREATE TYPE idempotent | ✅ Corrigé | - |
| #7 | PoolError double putconn | ✅ Corrigé | - |
| #8 | SMBConnectionError import | ✅ Corrigé | - |
| #9 | Import Enum manquant | ✅ Corrigé | - |
| #10 | migrate.py paramètre fetch | ✅ Corrigé | - |

---

**Commande pour créer les issues:**
```bash
# Issues à créer (statut 🔴)
gh issue create --title "test_retry_success_after_failure — IndexError quand args vide dans retry decorator" --label "bug,T-ARCH-01" --milestone "T-ARCH-01"
gh issue create --title "test_retry_exhausted_raises_exception — IndexError dans bloc final retry" --label "bug,T-ARCH-01" --milestone "T-ARCH-01"
gh issue create --title "test_retry_with_zero_max_retries — IndexError avec max_retries=0" --label "bug,T-ARCH-01" --milestone "T-ARCH-01"
gh issue create --title "Mocks API — IDs non-UUID (job-123) rejetés par PostgreSQL" --label "bug,T-ARCH-01" --milestone "T-ARCH-01"
gh issue create --title "Tests Worker Health — Mocks COUNT(*) non configurés" --label "bug,T-ARCH-01" --milestone "T-ARCH-01"
```
