# Rapport d'avancement — Restructuration de l'indexeur

**Date :** 18 mai 2026
**Version projet :** 0.6.23
**Branche :** V5_Projet / Devel

---

## 1. Contexte général

Le projet est en version **0.6.23** sur la branche `V5_Projet`/`Devel`. Le cap **J5** (Qualité et Observabilité) est en cours selon PROJET.md, mais la priorité immédiate a été recalée sur **T-INDEX-01** (Phase 1 — Indexeur efficace) avec les 9 derniers commits qui y sont dédiés.

Les phases PROJET.md se répartissent comme suit :
- **Phase 1** : Indexation intelligente — en cours (T-INDEX-01)
- **Phase 2** : Archivage — éléments livrés (T-ARCH-01/02/03/04)
- **Phase 3** : Sommaires IA — non commencé
- **Phase 4** : UI complète — authentification PocketBase livrée (T-AUTH-01), artefacts livrés (T-ART-01/02/03)
- **Phase 5** : Production/exploitation — socle J5 documenté

---

## 2. Ce qui est livré et fonctionnel

### 2.1 Infrastructure de l'indexeur

Fichier : `backend/src/workers/indexer_worker.py`

- Worker d'indexation complet avec queue de jobs et statuts (pending → running → completed/failed/cancelled)
- Mécanisme de polling toutes les 5 secondes sur la table `indexer_jobs`
- Crawl SMB récursif via `smbclient` (subprocess, plus robuste que smbprotocol)
- Insertion des fichiers dans PostgreSQL via `insert_file()`
- Mise à jour de la progression toutes les 100 fichiers
- Instance globale thread-safe avec historique (100 jobs max)

### 2.2 API REST dédiée

Fichier : `backend/src/api/indexer_router.py`

| Endpoint | Description |
|----------|-------------|
| `GET /api/indexer/stats` | Statistiques globales (pending/running/completed/failed + volumes) |
| `GET /api/indexer/current-job` | Job en cours d'exécution |
| `GET /api/indexer/jobs` | Liste paginée avec filtre par statut |
| `POST /api/indexer/jobs` | Création d'un job depuis une configuration SMB |
| `POST /api/indexer/start` | Déclenchement du worker (mode Docker) |
| `POST /api/indexer/stop` | Arrêt du worker (mode Docker) |
| `DELETE /api/indexer/jobs/{job_id}` | Annulation d'un job en attente |

### 2.3 Client SMB simplifié

Fichier : `backend/src/utils/crawl_utils.py`

- `SMBClient` via `smbclient` en subprocess (alternatif plus robuste que smbprotocol)
- Méthodes : connect, list_dir, get_file_info, disconnect, is_connected
- Gestion des credentials (host, share, username, password, domain)

### 2.4 Interface Sources SMB

- API CRUD complète pour les `crawl-configs` (création, modification, suppression)
- Modales de création/édition dans l'UI frontend
- Désactivation de l'authentification pour simplifier le développement
- Correction de l'ajout de source SMB (commit 4de59d0)

### 2.5 Interface de monitoring

- `frontend/indexer-monitoring.html` — Dashboard temps réel
- `frontend/archive-monitoring.html` — Monitoring archive
- `frontend/exploration.html` — Explorateur de fichiers

### 2.6 Structure backend réorganisée

```
backend/src/
├── api/
│   ├── artefact_filters_router.py
│   ├── artefacts_router.py
│   ├── duplicate_details_router.py
│   ├── indexer_router.py
│   └── main.py
├── core/
│   ├── config_manager.py
│   ├── logging_config.py
│   └── versioning.py
├── crawlers/
│   ├── smb_crawler.py
│   ├── smb_crawler_monitoring.py
│   ├── smb_crawler_postgresql.py
│   ├── smb_crawler_worker_monitoring.py
│   ├── smb_health_monitor.py
│   └── smb_mount_manager.py
├── database/
│   └── postgres_adapter.py
├── utils/
│   ├── crawl_utils.py
│   └── web_interface_v2.py
└── workers/
    ├── archive_scheduler.py
    ├── archive_transfer_worker.py
    └── indexer_worker.py
```

---

## 3. Problèmes identifiés

### 3.1 Couplage circulaire potentiel

`indexer_worker.py` importe `PostgreSQLAdapter` depuis `backend.src.api.main` au lieu de `backend.src.database.postgres_adapter`. Cela crée une dépendance anormale entre le worker et le module API.

### 3.2 Migration SQL manquante

La table `indexer_jobs` est utilisée par le worker et l'API, mais aucune migration SQL n'est présente dans `database/migrations/` pour la créer. Le commit 7723b9e (T-INDEX-01) n'a créé aucun fichier de migration.

### 3.3 Absence de tests

Aucun test unitaire ou d'intégration n'est visible pour :
- L'indexer worker (`indexer_worker.py`)
- L'API indexer (`indexer_router.py`)
- Le crawl utils (`crawl_utils.py`)

### 3.4 Mot de passe SMB non transmis

Dans `_get_smb_config()`, le mot de passe SMB est laissé vide (`''`) car l'API ne le retourne pas pour des raisons de sécurité. Cela bloque l'indexation réelle sur les partages SMB protégés.

---

## 4. Ce qui reste à faire

### 4.1 T-INDEX-01 — Indexeur efficace

| Tâche | Description | Statut |
|-------|-------------|--------|
| Scrutation périodique | Scheduler configurable (22h-6h) | ❌ Non commencé |
| Multi-espaces SMB | Gestion simultanée de plusieurs partages | ⚠️ Partiel (sources configurables, mais worker traite un job à la fois) |
| Files différenciées | Queue rapide (<200Mo) vs queue lente (≥200Mo) | ❌ Non commencé |
| Hashage xxHash | Remplacer SHA256 par xxHash pour performance | ❌ Non commencé |
| Détection changements | Mode incrémentiel avec hash + timestamps | ❌ Non commencé |
| Gestion des ordures | Patterns *.tmp, ~*, Thumbs.db | ❌ Non commencé |
| Base PostgreSQL | Schéma optimisé avec tables smb_spaces, directories, files | ❌ Non commencé |
| Tests de charge | Validation avec 166k+ fichiers | ❌ Non commencé |
| Documentation admin | Guide d'administration de l'indexation | ❌ Non commencé |

### 4.2 T-INDEX-02 — Optimisation et monitoring

| Tâche | Description | Statut |
|-------|-------------|--------|
| Métriques temps réel | Vitesse d'indexation, erreurs, files traitées | ❌ Non commencé |
| Health checks | Endpoints de santé pour le crawler | ❌ Non commencé |
| Gestion des erreurs | Queue retry pour fichiers verrouillés | ❌ Non commencé |
| Performance | Optimisation des requêtes PostgreSQL | ❌ Non commencé |
| Logs structurés | Format JSON pour tous les composants | ❌ Non commencé |

### 4.3 Correctifs bloquants

- Migration SQL pour la table `indexer_jobs`
- Découplage de l'import `PostgreSQLAdapter` (utiliser le module dédié)
- Transmission sécurisée du mot de passe SMB dans le worker
- Tests unitaires et d'intégration pour l'indexeur

---

## 5. Chronologie des commits récents

| Date | Commit | Description |
|------|--------|-------------|
| 18/05 | `4b5327e` | Refonte complète TODO.md selon PROJET.md v5 phases |
| - | `7d24e48` | Fix: crawl_utils avec smbclient pour indexer worker |
| - | `18a5b60` | Ajout module crawl_utils.py pour opérations SMB |
| - | `598b8b8` | Fix: interface indexer et création de jobs |
| - | `2e8e3b6` | Fix: création et édition de sources |
| - | `f657b8d` | Fix: API DELETE crawl-configs + modales |
| - | `4de59d0` | Fix: ajout de source SMB |
| - | `4fac6d3` | Fix: désactivation auth + UI Sources |
| 08/04 | `7723b9e` | T-INDEX-01: implémentation du service d'indexation dédié |

---

## 6. Recommandations pour la suite

1. **Priorité immédiate** : finaliser le socle T-INDEX-01 avant d'attaquer T-INDEX-02
2. **Corrections techniques** : migration SQL, découplage des imports, mots de passe SMB
3. **Tests** : écrire les tests pour l'indexeur avant d'ajouter des fonctionnalités
4. **Scrutation** : implémenter le scheduler cron pour l'indexation nocturne
5. **Performance** : intégrer xxHash pour le hachage et optimiser les requêtes PostgreSQL
6. **Documentation** : rédiger le guide d'administration

---

*Rapport généré le 18 mai 2026 — Projet OpenIndex v0.6.23*