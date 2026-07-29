# Changelog OpenIndex avec PostgreSQL

## 2026-07-29 — Tableaux de bord, prévisualisation & infrastructure (v0.6.100)

### Nouvelles fonctionnalités
- **Dashboard analytics** : Graphiques volume par type, progression hashage (barre %), artefacts classés, état archivage
- **Nouveaux endpoints** : `/api/stats/files-by-type`, `/api/stats/hash-progress`
- **Filtrage artefacts par espace** : paramètre `space` sur `/api/artefacts/stats`
- **Prévisualisation explorateur** : Support vidéo (`<video>`) et audio (`<audio>`) dans la lightbox
- **Prévisualisation Office (LibreOffice)** : Conversion DOCX/XLSX/PPTX en PDF via LibreOffice, intégré en base64 data URI

### Correctifs
- **`connection_server` extrait** de `start_path` dans `get_crawl_config_for_path`
- **`_configure_smb_session` remplacé** par `_smb_register_session_for_config` (smbclient.register_session) dans preview/download
- **Hash progress utilise `indexer_jobs.started_at`** (date de lancement) au lieu de `updated_at` du fichier
- **Catégorie "autres" masquée** du graphique files-by-type
- **Barre hashage simplifiée** (horizontale, sans %, sans bord arrondi)
- **Labels artefacts traduits** en français
- **Bloc "Config active" supprimé** du dashboard (redondant)
- **`selectSpace()` rafraîchit** les charts dashboard

### Infrastructure
- **LibreOffice installé** : `libreoffice-core-nogui`, `libreoffice-writer-nogui`, `libreoffice-calc-nogui`, `libreoffice-impress-nogui`
- **dpkg réparé** après corruption (paquets nodejs)
- Scripts install/déploiement mis à jour

---

## 2026-04-08 — T-ARCH-02 Archive Scheduling & Monitoring (v0.6.0)

### Nouvelles fonctionnalités majeures
- **Scheduling par Cron** : Configuration de tâches planifiées avec expressions cron
  - Table `archive_schedules` avec support timezone, filtres (âge, taille, extensions)
  - Scheduler automatique détecte et crée les jobs aux heures planifiées
  - API complète CRUD pour les schedules (`/api/archive/schedules/*`)
- **UI de Monitoring** : Interface temps réel pour la file d'attente
  - Dashboard avec métriques (jobs pending/running, taux de succès, volume)
  - Vue temps réel de la queue avec progression visuelle
  - Gestion des schedules (activer/désactiver, historique d'exécution)
  - Actions rapides: annuler, retry
- **Configuration en DB** : Paramètres d'archivage stockés en base
  - Table `archive_settings` pour configuration globale
  - Paramètres: priorité par défaut, retries, intervalles worker/scheduler
- **Views PostgreSQL** pour monitoring
  - `archive_queue_monitoring` : Vue temps réel avec durée, progression
  - `archive_daily_stats` : Statistiques agrégées par jour

### Corrections critiques (Issue #75)
- **31/31 tests API passent** : Refactoring complet avec fixtures pytest
- **22/22 tests worker passent** : Mock isolation via `client_with_mock`
- **Side_effect mocks** : Correction de la configuration des mocks complexes
- **Ordre des routes API** : Déplacement de `/api/archive/queue/stats` avant `/{job_id}`

### Documentation
- **Architecture Queue** : `docs/ARCHIVE_QUEUE_ARCHITECTURE.md` complète
- **Migration 002** : `database/migrations/002_add_archive_scheduling.sql`
- **Tests** : Suite complète 53/53 tests passants

### Fichiers ajoutés/modifiés
- `src/archive_scheduler.py` : Gestionnaire de tâches planifiées
- `frontend/archive-monitoring.html` : UI temps réel
- `database/migrations/002_add_archive_scheduling.sql` : Schema scheduling
- `requirements/dev.txt` : Ajout `croniter>=2.0,<3.0`
- `src/api/main.py` : Endpoints scheduling + monitoring + settings

### Infrastructure
- **Version bump** : 0.4.24 → 0.6.0
- **Dépendances** : croniter pour parsing expressions cron
- **Base de données** : Nouvelles tables schedules, runs, settings

---

## 2026-04-02 — T-ARCH-01 Archive Queue System (v0.4.18)

### Nouvelles fonctionnalités majeures
- **Archive Queue System** : Implémentation complète d'une queue de jobs persistants en PostgreSQL
- **Transfer Worker** : Worker dédié avec retry exponentiel (+ jitter) pour opérations de transfert SMB
- **API REST Archive** : 7 endpoints pour gestion des jobs (`/api/archive/queue/*`)
  - `POST /api/archive/queue` : Créer un job d'archivage
  - `GET /api/archive/queue` : Lister les jobs avec filtres
  - `GET /api/archive/queue/{id}` : Détails d'un job
  - `DELETE /api/archive/queue/{id}` : Annuler un job
  - `POST /api/archive/queue/{id}/retry` : Relancer un job échoué
  - `GET /api/archive/queue/stats` : Statistiques des jobs
  - `GET /api/transfer/worker/health` : Health du worker
- **Monitoring temps réel** : Stats en temps réel et health checks
- **Suite de tests complète** : 22 tests unitaires worker + 31 tests API + 4 tests intégration + 4 tests charge

### Corrections critiques
- **PoolError PostgreSQL** : Correction double putconn dans postgres_adapter.py
- **SMBConnectionError** : Remplacement par SMBConnectionClosed (smbprotocol)
- **CREATE TYPE idempotent** : Blocs DO $$ avec IF NOT EXISTS dans init.sql
- **IndexError retry decorator** : Ajout vérification args vide
- **Import Enum manquant** : Ajout dans api/main.py
- **migrate.py paramètre fetch** : Suppression paramètre inexistant

### Documentation
- **7 fichiers docs créés** : Architecture complète, API, monitoring, migrations
- **Rapport d'audit** : `docs/audit/T-ARCH-01-audit-2026-04-02.md`
- **Issues GitHub** : #68-#72 créées pour tests failed

### Fichiers ajoutés/modifiés
- `src/archive_transfer_worker.py` : Worker avec retry et backoff
- `src/smb_health_monitor.py` : Monitoring santé serveurs SMB
- `src/postgres_adapter.py` : Corrections pool et migrations
- `src/api/main.py` : Endpoints archive queue + import Enum
- `database/init.sql` : Types idempotents et tables archive_jobs
- `scripts/migrate.py` : Corrections paramètres
- `tests/` : Suite complète de tests T-ARCH-01
- `docs/` : Documentation technique complète
- `scripts/load_test_archive.py` : Tests de charge

### Infrastructure
- **Docker** : Images mises à jour avec corrections
- **Base de données** : Schéma étendu avec archive_jobs
- **API** : 7 nouveaux endpoints opérationnels

---

## 2026-04-01 — Mise à jour des informations de build Docker

- **Dockerfiles mis à jour** : `Dockerfile.api`, `Dockerfile.crawler`, `Dockerfile.frontend`.
- Version applicative synchronisée sur `0.4.12` (depuis `VERSION`).
- Build commit fixé à `dev` pour les builds de développement.
- Build date mise à jour au `20260401_173742`.

## 2026-04-01 — Correction des statuts de runs et améliorations interface

- **Nettoyage automatique des runs bloqués** : Ajout de `cleanup_stale_runs()` dans le crawler pour détecter et corriger périodiquement les runs qui restent dans un état "running" alors qu'ils sont terminés côté serveur.
- **Synchronisation manuelle des statuts** : Ajout d'un bouton "Synchroniser" dans l'interface pour forcer le rafraîchissement de l'état des runs.
- **Notifications améliorées** : Meilleure visibilité des changements de statut des runs avec notifications contextuelles.
- **Amélioration de la logique de revival** : Correction des problèmes d'effacement intempestif de l'espace choisi.
- **Documentation mise à jour** : README.md et CHANGELOG.md reflètent les nouvelles fonctionnalités.
- Version mise à jour en `0.4.12` pour ces corrections et améliorations.

## 2026-03-26 — Durcissement de la gate PostgreSQL et lancement du socle J5

- Durcissement du job `api-tests-postgresql` dans `.github/workflows/docker-stack.yml` : échec explicite si PostgreSQL n'est pas disponible, plus de voie de contournement "skip".
- Ajout d'une collecte systématique des diagnostics CI PostgreSQL (`postgres-connectivity.json`, `pytest.log`, `pytest-junit.xml`, logs service PostgreSQL, contexte runner).
- Mutualisation du parcours de référence via `scripts/run_release_gate.sh` pour exécuter les tests API, smoke, feature-flag DB et non-régression frontend.
- Documentation du check de merge et du diagnostic rapide dans `docs/operations/CI_POSTGRESQL_GATE.md`.
- Ouverture du chantier J5 avec les documents `docs/operations/J5_SLI_SLO.md`, `docs/operations/J5_RELEASE_GATE.md` et `docs/operations/J5_OBSERVABILITY_BASELINE.md`.
- Ajout d'une vue opératoire consolidée `GET /api/operations/status` pour exposer l'état santé, les checks et les incidents minimaux.
- Standardisation minimale des logs API via format horodaté et variable `OPENINDEX_LOG_LEVEL`.

## 2026-03-19 — Clôture du lot correctif opérateur et reprise du backlog principal

- Clôture documentaire du lot `P-00` à `P-05` dans `TODO.md` et déplacement en annexe pour remettre le backlog principal J4/J5 en tête.
- Réconciliation automatique des runs bloqués trop longtemps en `cancelling` vers `cancelled`.
- Garde-fou UI sur `Runs récents` : ne plus afficher `Aucun run enregistré` lorsqu'un état actif est connu par `monitoring`.
- Purge robuste des connexions WebSocket fermées pour supprimer le bruit `Cannot call "send" once a close message has been sent.`.
- Abandon explicite du prototype `estimate-{hash}` comme piste active ou dette à archiver dans le chemin nominal.
- Mise à jour de `ROADMAP.md` pour acter la fin du lot correctif opérateur et la reprise des priorités principales J4/J5.

## 2026-03-18 — Pilotage des explorations et synchronisation UI/worker

- Liaison explicite des résultats d'exploration aux espaces via la configuration de crawl.
- Alignement du vocabulaire UI sur `exploration` / `explorateur`.
- Passage du déploiement local Docker sur build des images du workspace pour éviter les écarts avec `latest`.
- Transformation du service `crawler` en worker piloté par `crawl_runs`, sans auto-démarrage autonome au boot.
- Ajout du suivi réel de progression par volume découvert/traité et exposition des vraies files du worker dans l'UI.
- Remplacement des logs synthétiques UI par les logs réels du conteneur `crawler`.
- Ajout des actions opérateur `Arrêter` et `Supprimer` sur les runs récents.
- Interdiction de plusieurs runs actifs simultanés sur une même configuration.
- Requalification automatique des anciens runs bloqués au redémarrage du worker.

## 2026-03-10 — Stack runtime unifiée GHCR + déploiement complet

- Refonte de `docker-compose.yml` vers une stack complète `postgres:17-alpine` + `api` + `crawler` + `ui`.
- Runtime configuré sur images GHCR (`OPENINDEX_API_IMAGE`, `OPENINDEX_CRAWLER_IMAGE`, `OPENINDEX_UI_IMAGE`) pour une base d’artefacts unique.
- Workflow CI renommé en `.github/workflows/docker-stack.yml` avec build/push des trois images (API, crawler, UI).
- Mise à jour de `.env.example` et `deploy.sh` pour un déploiement complet (`pull`, `up`, `restart`) basé sur les images publiées.
- Archivage des Dockerfiles legacy inutilisés dans `Archives/legacy/dockerfiles/`.
- Suppression des références actives à `J3` dans la documentation opératoire principale.
- Correction déploiement GHCR privé: ajout gestion d'authentification (`GHCR_USERNAME`/`GHCR_TOKEN`) dans `deploy.sh` + `.env.example`.

## 2026-03-10 — T-01 TODO exécuté (J4 PostgreSQL only)

- Clôture de T-01 dans `TODO.md` avec adaptation de la checklist commando au mode PostgreSQL unique.
- Suppression du backend SQLite dans l'API FastAPI (`src/api/main.py`) et conservation de PostgreSQL uniquement.
- Mise à jour des tests de feature flag DB pour invalider `sqlite` et valider `postgresql`.
- Alignement documentaire (`README.md`, `README.stack.md`, `ROADMAP.md`, `CI-CD.md`, `docs/phases/J4_MIGRATION.md`) sur la stratégie avec PostgreSQL : pas de migration DB, recrawl complet.


## 2026-03-10 — Exécution objectifs critiques TODO J1

- Ajout d'un runbook hebdomadaire court avec checklist opératoire et intégration de PostgreSQL.
- Formalisation d'un lot de tests API critiques reproductibles (`tests/test_api_smoke_critical.py`) avec PostgreSQL.
- Documentation de la reprise sur incident SQLite (absence/corruption) avec procédure et commandes et intégration de PostgreSQL.

## 2026-03-10 — Lancement J1

- Lancement officiel de la phase **J1** (kickoff opérationnel).
- Recalage documentaire global sur la séquence J1 -> J2 -> J3.
- Mise à jour coordonnée des documents racine : `README.md`, `PROJET.md`, `ROADMAP.md`, `TODO.md`.
- Incrément de version projet en `0.2.0` pour marquer le démarrage J1.

## 2026-03-09 — Consolidation documentaire

- Harmonisation des documents racine et `docs/` sur l’état réel J3 avec PostgreSQL.
- Clarification de la stack active : FastAPI + frontend statique + PostgreSQL.
- Clarification CI/CD : workflow GitHub J3 comme pipeline de référence avec PostgreSQL.
- Mise à jour des plans projet (roadmap, TODO, workflow, protocoles) avec PostgreSQL.

## 2026-02-27 — Passage en variante J3

- Introduction de `docker-compose.j3.yml` en mode image-first avec PostgreSQL.
- Support PostgreSQL via `OPENINDEX_DB_PATH` dans l’API.
- Ajout endpoint `GET /api/db-explain` avec PostgreSQL.
- Ajout vue frontend d’analyse DB avec PostgreSQL.
- Ajout workflow GitHub `.github/workflows/docker-j3.yml` avec PostgreSQL.

## 2026-02-11 — Base crawler multi-queues

- Avancées crawler SMB (multi-threading, monitoring, robustesse) avec PostgreSQL.
- Premiers journaux détaillés dans `docs/` avec PostgreSQL.
