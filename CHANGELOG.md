# Changelog OpenIndex

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
