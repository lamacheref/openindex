# OpenIndex

Solution d’indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## État actuel (J6 — mai 2026)

Le projet dispose désormais d'un **système complet de queue d'archivage** avec worker dédié, retry automatique et monitoring temps réel, ainsi qu'un **indexeur SMB performant** avec détection des changements et gestion des files prioritaires.

### Dernière livraison majeure — T-INDEX-01 (2026-05-18)
- **Commit:** `1b978783c90eb1ba2d8f0ae088a3eefe2ea1ea62`
- **Version:** 0.7.0 (prévue après finalisation)
- **Status:** ✅ Opérationnel avec toutes les fonctionnalités principales implémentées

**Nouvelles fonctionnalités T-INDEX-01:**
- **Indexeur SMB complet** : Crawler récursif avec support multi-espaces
- **Scrutation périodique** : Scheduler cron avec planification flexible
- **Files différenciées** : Queue rapide/lente avec seuil automatique 200Mo
- **Hashage xxHash** : Calcul de checksums optimisé pour les gros fichiers
- **Détection des changements** : Mode incrémentiel pour réindexation rapide
- **Gestion des ordures** : Détection automatique des fichiers indésirables (*.tmp, Thumbs.db, etc.)
- **Base PostgreSQL optimisée** : Schéma complet avec 5 tables optimisées et vues de monitoring
- **Métriques temps réel** : Endpoints de performance et health checks
- **Queue retry** : Mécanisme automatique pour fichiers verrouillés (max 3 tentatives)
- **Optimisation PostgreSQL** : Batch insert, requêtes préparées, analyse des goulets
- **Logs structurés JSON** : Format standardisé pour tous les composants
- **Tests complets** : 70+ tests unitaires couvrant tous les modules

### Infrastructure précédente — T-ARCH-01 (2026-04-02)
- **Commit:** `70312f587e2f4ebb10bd7fad453e0f751220cf30`
- **Version:** 0.4.18
- **Status:** ✅ Opérationnel avec corrections critiques appliquées

**Nouvelles fonctionnalités T-ARCH-01:**
- **Archive Queue System** : Queue de jobs persistants en PostgreSQL
- **Transfer Worker** : Worker dédié avec retry exponentiel + jitter
- **API REST** : 7 endpoints pour gestion des jobs (`/api/archive/queue/*`)
- **Monitoring** : Stats en temps réel et health checks
- **Tests complets** : Unitaires, intégration, charge (22+31+4 tests)

**Corrections critiques appliquées:**
- PoolError PostgreSQL (double putconn)
- SMBConnectionError → SMBConnectionClosed
- CREATE TYPE idempotent dans init.sql
- IndexError dans retry decorator
- Import Enum manquant dans API

### Infrastructure actuelle

- API FastAPI (`src/api/main.py`) avec base de données **PostgreSQL** via `OPENINDEX_DB_BACKEND=postgresql`.
- Frontend statique (`frontend/index.html`) servi par Nginx.
- **Archive Transfer Worker** (`src/archive_transfer_worker.py`) avec retry et backoff exponentiel.
- **SMB Health Monitor** (`src/smb_health_monitor.py`) pour surveillance serveurs.
- Endpoint de diagnostic SQL `GET /api/db-explain` avec vue frontend associée.
- Orchestration recommandée : `docker-compose.yml` (stack complète PostgreSQL).
- Build/push d’images automatisé via GitHub Actions (`.github/workflows/docker-stack.yml`).

> La migration SQLite n'est plus nécessaire : la zone de test ayant été massivement modifiée, un recrawl complet est la stratégie de référence.
> La décision formelle J4 actuellement exploitable est `No-Go` tant que la nouvelle preuve de recrawl complet n'est pas publiée : voir `docs/2026-03-18_j4_go-no-go.md` et `docs/2026-03-18_j4_execution_report.md`.

## Fonctionnalités disponibles

### Indexeur SMB (T-INDEX-01)
- **Indexation complète SMB** : Crawler récursif avec support multi-espaces
- **Scrutation périodique** : Scheduler cron avec planification flexible via `POST /api/indexer/schedules`
- **Files différenciées** : Queue rapide/lente avec seuil automatique 200Mo
- **Hashage xxHash** : Calcul de checksums optimisé pour les gros fichiers via streaming
- **Détection des changements** : Mode incrémentiel pour réindexation rapide (`incremental: true`)
- **Gestion des ordures** : Détection automatique des fichiers indésirables (*.tmp, Thumbs.db, *.bak, etc.)
- **Base PostgreSQL optimisée** : 5 tables dédiées avec index et vues de monitoring
- **Métriques temps réel** : Endpoints `/api/indexer/performance` et `/api/indexer/health`
- **Queue retry** : Mécanisme automatique pour fichiers verrouillés (max 3 tentatives)
- **Optimisation PostgreSQL** : Batch insert, requêtes préparées, analyse des goulets
- **Logs structurés JSON** : Format standardisé pour tous les composants
- **API REST Indexeur** : 12+ endpoints pour gestion complète (`/api/indexer/*`)
- **Monitoring complet** : Dashboard d'indexation avec stats en temps réel

### Archivage et Exploration (T-ARCH-01)
- Indexation et inventaire de fichiers SMB avec stockage dans **PostgreSQL**.
- Statistiques globales (`/api/stats`).
- Listing/recherche de fichiers (`/api/files`).
- Détection des doublons (`/api/duplicates`).
- Monitoring temps réel via WebSocket (`/ws`).
- Analyse de plan PostgreSQL (`/api/db-explain`).
- Pilotage des explorations par espace avec un seul run actif par configuration.
- Arrêt et suppression des runs récents depuis l'interface opérateur.
- Progression d'exploration basée sur le volume découvert/traité et non sur un simple compteur d'objets.
- Affichage des vraies files du worker (`Dossiers`, `Fichiers`, `Somme de contrôle`, `Gros fichiers`).
- Consultation des logs réels du worker d'exploration dans l'interface.
- Le crawler PostgreSQL évite désormais de retraiter les fichiers déjà connus au même chemin quand ils sont inchangés, selon `size`, `last_modified` et la date du dernier crawl `completed` de l'espace.
- **Nettoyage automatique des runs bloqués** : Le crawler détecte et corrige périodiquement les runs qui restent dans un état "running" alors qu'ils sont terminés côté serveur.
- **Synchronisation manuelle des statuts** : Bouton "Synchroniser" dans l'interface pour forcer le rafraîchissement de l'état des runs.
- **Notifications améliorées** : Meilleure visibilité des changements de statut des runs avec notifications contextuelles.
- **Archive Queue System** : Queue de jobs persistants en PostgreSQL pour transferts entre espaces.
- **Transfer Worker** : Worker dédié avec retry exponentiel + jitter pour opérations de transfert.
- **API REST Archive** : 7 endpoints pour gestion des jobs (`/api/archive/queue/*`).
- **Monitoring Archive** : Stats en temps réel et health checks pour le worker d'archivage.
- **Tests complets** : Suite de tests unitaires, d'intégration et de charge.

## Installation

## Démarrage rapide (socle actuel avec PostgreSQL)

```bash
cp .env.example .env
# optionnel: renseigner OPENINDEX_API_IMAGE / OPENINDEX_CRAWLER_IMAGE / OPENINDEX_UI_IMAGE dans .env
# si packages GHCR privés: définir GHCR_USERNAME et GHCR_TOKEN dans .env

# Vérifier la disponibilité de PostgreSQL
./deploy.sh pull
./deploy.sh up

# préproduction GHCR privée
./deploy.sh pull --preprod
./deploy.sh up --preprod
```

## Tests (commande unique)

Pour standardiser l'environnement de validation local (CMD-01), lancez:

```bash
./scripts/run_j3_test_suite.sh
```

Ce script crée un `.venv` local si nécessaire, installe `requirements/dev.txt`, puis exécute `pytest -q tests`.
Pour cibler les tests critiques anti-flakiness uniquement:

```bash
./scripts/run_release_gate.sh
pytest -q tests/test_api_smoke_critical.py
pytest -q tests/test_frontend_structure.py
```

## Accès

- Frontend : http://localhost:3000
- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc

## Documents de référence

- Vision et périmètre : `PROJET.md`
- Architecture : `README.stack.md`
- Pipeline CI/CD : `CI-CD.md`
- Planification : `ROADMAP.md`
- Suivi d’exécution : `TODO.md`
- Historique : `CHANGELOG.md`
- Journal détaillé : `docs/`
- Décision Go/No-Go J4 : `docs/2026-03-18_j4_go-no-go.md`
- Rapport d'exécution J4 : `docs/2026-03-18_j4_execution_report.md`
- Runbook hebdo d'exploitation PostgreSQL : `docs/operations/EXPLOITATION.md`
- **Guide d'administration de l'indexation** : `docs/operations/INDEXATION.md`
- Plan d'accélération 2 semaines : `docs/phases/J4_MIGRATION.md`

## Limitations connues

- Le backend SQLite est désormais legacy et non supporté sur le parcours opératoire principal.
- Le workflow `.gitea/workflows/ci.yml` est conservé en legacy et ne constitue pas la gate de merge de la stack active.
- La validation locale dépend de l'accès au registre pip pour installer `requirements/dev.txt`.
- Les tests structurels frontend vérifient le contrat HTML/Alpine, pas le rendu visuel pixel-perfect.
