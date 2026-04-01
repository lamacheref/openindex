# Changelog OpenIndex avec PostgreSQL

## 2026-03-31 — Navigation SMB live pour l'explorateur de fichiers

- Ajout de l'endpoint `GET /api/explorer/live-items` pour la navigation SMB en temps réel sans passer par la base de données.
- Cette fonctionnalité permet de voir les fichiers non indexés et les ajouts récents sur les partages SMB.
- PR #62 sur `fix/explorer-live-navigation`.
- Dette T-15 (navigation SMB live hors index) résolue.
- Version mise à jour en `0.4.2` pour cette nouvelle fonctionnalité.

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
