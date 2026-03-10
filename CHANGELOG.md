# Changelog OpenIndex

## 2026-03-10 — Stack runtime unifiée GHCR + déploiement complet

- Refonte de `docker-compose.yml` vers une stack complète `postgres:17-alpine` + `api` + `crawler` + `ui`.
- Runtime configuré sur images GHCR (`OPENINDEX_API_IMAGE`, `OPENINDEX_CRAWLER_IMAGE`, `OPENINDEX_UI_IMAGE`) pour une base d’artefacts unique.
- Workflow CI renommé en `.github/workflows/docker-stack.yml` avec build/push des trois images (API, crawler, UI).
- Mise à jour de `.env.example` et `deploy.sh` pour un déploiement complet (`pull`, `up`, `restart`) basé sur les images publiées.
- Archivage des Dockerfiles legacy inutilisés dans `Archives/legacy/dockerfiles/`.
- Suppression des références actives à `J3` dans la documentation opératoire principale.

## 2026-03-10 — T-01 TODO exécuté (J4 PostgreSQL only)

- Clôture de T-01 dans `TODO.md` avec adaptation de la checklist commando au mode PostgreSQL unique.
- Suppression du backend SQLite dans l'API FastAPI (`src/api/main.py`) et conservation de PostgreSQL uniquement.
- Mise à jour des tests de feature flag DB pour invalider `sqlite` et valider `postgresql`.
- Alignement documentaire (`README.md`, `README.stack.md`, `ROADMAP.md`, `CI-CD.md`, `docs/phases/J4_MIGRATION.md`) sur la stratégie: pas de migration DB, recrawl complet.


## 2026-03-10 — Exécution objectifs critiques TODO J1

- Ajout d'un runbook hebdomadaire court avec checklist opératoire.
- Formalisation d'un lot de tests API critiques reproductibles (`tests/test_api_smoke_critical.py`).
- Documentation de la reprise sur incident SQLite (absence/corruption) avec procédure et commandes.

## 2026-03-10 — Lancement J1

- Lancement officiel de la phase **J1** (kickoff opérationnel).
- Recalage documentaire global sur la séquence J1 -> J2 -> J3.
- Mise à jour coordonnée des documents racine : `README.md`, `PROJET.md`, `ROADMAP.md`, `TODO.md`.
- Incrément de version projet en `0.2.0` pour marquer le démarrage J1.

## 2026-03-09 — Consolidation documentaire

- Harmonisation des documents racine et `docs/` sur l’état réel J3.
- Clarification de la stack active : FastAPI + frontend statique + SQLite.
- Clarification CI/CD : workflow GitHub J3 comme pipeline de référence.
- Mise à jour des plans projet (roadmap, TODO, workflow, protocoles).

## 2026-02-27 — Passage en variante J3

- Introduction de `docker-compose.j3.yml` en mode image-first.
- Support SQLite via `OPENINDEX_DB_PATH` dans l’API.
- Ajout endpoint `GET /api/db-explain`.
- Ajout vue frontend d’analyse DB.
- Ajout workflow GitHub `.github/workflows/docker-j3.yml`.

## 2026-02-11 — Base crawler multi-queues

- Avancées crawler SMB (multi-threading, monitoring, robustesse).
- Premiers journaux détaillés dans `docs/`.
