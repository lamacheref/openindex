# OpenIndex

Solution d'indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## Installation (LXC Ubuntu 24.04)

Documentation complète de déploiement → [`docs/operations/DEPLOY_LXC.md`](docs/operations/DEPLOY_LXC.md)

Crée un conteneur LXC Ubuntu 24.04 (2 CPU, 2 Go RAM, 16 Go disque) avec PostgreSQL 17, PocketBase, FastAPI, indexeur SMB et frontend Nginx.

## État actuel

**Phase J6 — Refonte protocolaire de l'indexeur terminée (T-INDEX-R02 ✅).**

L'indexeur implémente désormais le protocole 2 phases : BFS des répertoires → bottom-up des fichiers, avec contrôle d'existence sur 4 métadonnées (nom + taille + date création + date modification) et écriture dans la table `indexed_files_optimized`.

Ce qui reste :
- ✅ **Tests unitaires** — 90 tests (Phase A/B, Priority 4, indexer worker) passés
- ⏳ **Déploiement LXC** — validation en cours sur Proxmox
- ❌ Gestion des raccourcis/symlinks — hors périmètre Phase 1

## Fonctionnalités

- **Indexation SMB incrémentielle** : détection des fichiers nouveaux/changés par comparaison sur 4 métadonnées
- **Files différenciées** : fast (<200Mo, xxHash immédiat), slow (≥200Mo, job dédié), retry (verrouillés)
- **Hashage xxHash64** avec streaming pour les gros fichiers et fallback SHA256
- **Queue retry** : réessai automatique, backoff exponentiel, max 5 tentatives
- **Détection des ordures** : *.tmp, Thumbs.db, *.bak, etc.
- **Scheduler cron** : scrutation périodique configurable
- **Base PostgreSQL optimisée** : 10 tables, index, vues, fonctions PL/pgSQL
- **Archivage SMB** : queue de jobs persistants, transfer worker avec retry
- **Authentification** : PocketBase, JWT, routes protégées
- **Monitoring temps réel** : métriques, health checks, WebSocket
- **API REST** : 20+ endpoints

## Accès

| Interface | URL |
|---|---|
| Frontend | `http://<LXC_IP>` |
| API (Swagger) | `http://<LXC_IP>/api/docs` |
| PocketBase admin | `http://<LXC_IP>/_/` |

Par défaut : admin `admin@openindex.local` / `admin123`.

## Développement local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt xxhash
npm install && npm run build:frontend

# API
uvicorn backend.src.api.main:app --reload

# Tests
pytest -q tests/
```

## Documents de référence

| Document | Contenu |
|---|---|
| `PROJET.md` | Vision, périmètre, spécifications |
| `ROADMAP.md` | Planification et jalons |
| `TODO.md` | Suivi d'exécution courant |
| `README.stack.md` | Architecture technique |
| `CHANGELOG.md` | Historique des versions |
| `docs/operations/INDEXATION.md` | Administration de l'indexation |
| `docs/operations/EXPLOITATION.md` | Runbook PostgreSQL |
| `docs/operations/DEPLOY_LXC.md` | Déploiement LXC pas-à-pas |

## Historique des commits

| Hash | Date | Gitea | GitHub | Description |
|------|------|-------|--------|-------------|
| `6db7a356` | 2026-07-23 | non | non | perf: avoid duplicate list_dir in get_file_info by passing entries_list |
| `ba62f8c3` | 2026-07-23 | oui | oui | fix: update progress every 10 items in Phase B too |
| `58c0b0a5` | 2026-07-23 | oui | oui | feat: real-time dir count in progression column (every 10 dirs) |
| `f5d552ad` | 2026-07-23 | oui | oui | fix: add cancelJob function |
| `253640ca` | 2026-07-23 | oui | oui | fix: add commit=True to purge/resume/cancel endpoints |
| `aac68b17` | 2026-07-23 | oui | oui | feat: fault-tolerant worker (resume after crash), purge + resume buttons |
| `33383a9c` | 2026-07-22 | oui | oui | fix: add index col + smart auto-scroll (only if near bottom) |
| `acdc1e54` | 2026-07-22 | oui | oui | fix: increase scroll timeout to 200ms |
| `0ec256fe` | 2026-07-22 | oui | oui | fix: standard log order (newest at bottom, auto-scroll to bottom) |
| `f37fce82` | 2026-07-22 | oui | oui | fix: reverse log order (newest first), auto-scroll to top |
| `a02a6714` | 2026-07-22 | oui | oui | fix: default logService value |
| `96b86be6` | 2026-07-22 | oui | oui | feat: dedicated log file /var/log/openindex/indexer-worker.log, logs tab reads from file |
| `4768de08` | 2026-07-22 | oui | oui | feat: add logs tab with real-time journalctl view + deploy script |
| `f95821b4` | 2026-07-22 | oui | oui | fix: escape apostrophe in SQL |
| `703e4d83` | 2026-07-22 | oui | oui | fix: stop job endpoint + frontend stopJob + Phase A table display |
| `8ff7e798` | 2026-07-22 | oui | oui | fix: keep files_found=0 during Phase A, show discovery text in UI |
| `79f8e12d` | 2026-07-22 | oui | oui | fix: show live progress during Phase A dir discovery, reset at Phase B start |
| `afad2e87` | 2026-07-22 | oui | oui | fix: pass domain to SMBClient in worker |
| `33de4985` | 2026-07-22 | oui | oui | chore: debug connect method |
| `708d04d3` | 2026-07-22 | oui | oui | fix: smbclient connect pass password via stdin, connect to share not -L |
| `c2b4af4a` | 2026-07-22 | oui | oui | fix: smbclient cannot connect to subdirectory, use cd before ls |
| `cf310d30` | 2026-07-22 | oui | oui | fix: correct import path crawl_utils (utils.crawl_utils) |
| `03df7049` | 2026-07-22 | oui | oui | fix: normalize UNC start_path in backend (strip duplicate slashes) |
| `e9b8161f` | 2026-07-22 | oui | oui | fix: start_path triple slash, use local tailwind.css |
| `d8fd155e` | 2026-07-22 | oui | oui | fix: add GET /api/indexer/jobs/{job_id}, update benchmark script for Phase A/B |
| `4f85ecac` | 2026-07-22 | oui | oui | fix frontend: copy alpine.min.js + fontawesome assets, add node_modules to gitignore |
| `5e0301d1` | 2026-07-22 | oui | oui | fix integration tests: use UUID for space_id |
| `c87adf6f` | 2026-07-22 | oui | oui | add integration DB tests (real PG) |
| `8f1300fc` | 2026-07-22 | oui | oui | fix tests Priority 4 + docs T-LXC-03 + update TODO |
| `fe209a30` | 2026-07-22 | oui | oui | fix install: embed inner script, pass env vars, idempotent PG |
| `59986ec0` | 2026-07-22 | oui | oui | fix install 404: inner script + tests Phase A/B |
| `c49e443d` | 2026-07-22 | oui | oui | feat: ajout historique des commits dans README + post-commit hook |
| `663366ff` | 2026-07-22 | oui | oui | Restore scripts/versioning.py + fix pre-commit exécutable |
| `510f627c` | 2026-07-22 | oui | oui | README: URL installation GitHub (main) |
| `8331c600` | 2026-07-22 | oui | oui | README: URL installation pointe vers main (Devel supprimée) |
| `a2db82a6` | 2026-07-22 | oui | oui | README: URL installation Gitea (vs GitHub), suppression ref CI-CD.md |
| `3deee6b3` | 2026-07-22 | oui | oui | Merge pull request 'T-INDEX-R02 : Refonte protocolaire de l'indexation (BFS, bottom-up, écritures optimisées)' (#2) from Devel into main |
| `be81fda0` | 2026-07-22 | oui | oui | Merge gitea/main into Devel, résolution conflit OpenIndex.code-workspace |
| `f2e6064b` | 2026-07-22 | oui | oui | Suppression des pipelines CI/CD (GitHub Actions, Gitea CI, CI-CD.md) — déploiement LXC |
| `5a5e746d` | 2026-07-22 | oui | oui | README: déploiement ProxmoxVE (curl bash), état T-INDEX-R02 terminé |
| `169dea87` | 2026-07-22 | oui | oui | T-LXC-01 installeur ProxmoxVE LXC complet |
| `773fa3b2` | 2026-07-22 | oui | oui | T-INDEX-R02 finalisation 1d : logs, filtres space_id, PROJET.md à jour |
| `a7aadd06` | 2026-07-22 | oui | oui | T-INDEX-R02 refonte protocole indexeur (P0 + P1a/b/c) |
| `941c4f0e` | 2026-07-22 | oui | oui | Phase J6: réorientation LXC + validation indexeur |
| `11948c34` | 2026-05-18 | oui | oui | Add indexer retries table and priority 4 features |
| `caeffa13` | 2026-05-18 | oui | oui | Merge pull request 'V5_Projet' (#1) from V5_Projet into main |
| `b82e2d5c` | 2026-05-18 | oui | oui | Ajout du fichier OpenIndex.code-workspace pour l'environnement de développement |
| `1b978783` | 2026-05-18 | oui | oui | Mise à jour quotidienne : modifications de l'environnement virtuel et du TODO |
| `5245847b` | 2026-05-18 | oui | oui | T-INDEX-01: Gestion des ordures - Détection et marquage des fichiers indésirables |
| `aeb37d90` | 2026-05-18 | oui | oui | T-INDEX-01: Base PostgreSQL optimisée - Schéma complet |
