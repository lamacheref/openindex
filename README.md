# OpenIndex

Solution d'indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## Installation (LXC Ubuntu 24.04)

Documentation complète de déploiement → [`docs/operations/DEPLOY_LXC.md`](docs/operations/DEPLOY_LXC.md)

Crée un conteneur LXC Ubuntu 24.04 (2 CPU, 2 Go RAM, 16 Go disque) avec PostgreSQL 17, PocketBase, FastAPI, indexeur SMB et frontend Nginx.

## État actuel

**Phase J6 — Déploiement LXC & Dashboard opérationnel (v0.6.100).**

L'indexeur 2 phases (BFS → bottom-up) est validé et déployé sur le LXC Proxmox (`nyx`). La console opératoire est enrichie de tableaux de bord (volume par type, progression hashage, artefacts, archivage) et la prévisualisation supporte désormais vidéo, audio et documents Office (LibreOffice).

Ce qui reste :
- ✅ **Tests unitaires** — 90 tests passés
- ✅ **Déploiement LXC** — validation sur nyx, 3 espaces SMB (SEPM, SMIDEN, Archives_SEM)
- ⏳ **Hashage des fichiers** — crawl en cours (large volume SEPM)
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
- **API REST** : 25+ endpoints
- **Dashboard** : Volume par type, progression hashage, artefacts, archivage
- **Prévisualisation fichiers** : Image, vidéo, audio, documents Office (LibreOffice)

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
| `89a64195` | 2026-08-04 | non | non | fix(api): /api/duplicates detect duplicates by hash+size group (issue #3); fix versioning path + system status version env |
| `a65c4c69` | 2026-08-03 | oui | oui | docs(ops): split psql_lxc.sh usage into its own doc file; clean up DEPLOY_LXC numbering |
| `bd689a75` | 2026-08-03 | oui | oui | docs(ops): document scripts/psql_lxc.sh in DEPLOY_LXC (read-only DB access dev->LXC) |
| `e4322503` | 2026-08-03 | oui | oui | docs(psql_lxc): document wrapper, env vars, examples and read-only usage note |
| `376646d8` | 2026-08-03 | oui | oui | feat(dev): add scripts/psql_lxc.sh SSH wrapper to query the LXC database directly (read-only) |
| `2130204b` | 2026-08-03 | oui | oui | fix(api): /api/duplicates uses indexed_files_optimized + hash_xxh64 (was: dead 'files' table) |
| `40174039` | 2026-08-03 | oui | oui | fix(deploy): make deploy_lxc.sh robust (clean reset, rsync frontend to /var/www/html) |
| `c7cc1386` | 2026-08-03 | oui | oui | fix(backend): add missing versioning.get_current_version shim (tracked) |
| `2b3ea4c6` | 2026-08-03 | oui | oui | feat(live-explorer): surligner les pourriels/gros/anciens dans le panneau Archive SMB live |
| `71ecfeec` | 2026-08-03 | oui | oui | feat(ui): gris clair sur les dossiers contenant des fichiers signalés (doublons/gros/anciens/indesirables) |
| `6736eff6` | 2026-08-03 | oui | oui | feat(ui): surligner les lignes de l'explorateur (doublons/gros/anciens/pourriels) + icone archive locale |
| `2dedbad0` | 2026-08-03 | oui | oui | fix(ui): use fa-box-archive (FA6) instead of deprecated fa-archive for archive zones icons |
| `f540bcbd` | 2026-08-03 | oui | oui | feat(ui): distinct color and badge for archive zones vs sources in configured sources view |
| `0bee0901` | 2026-08-03 | oui | oui | fix(smb): fall back to domain_zone when connection_domain is empty (archive server auth) |
| `9cbbd6c9` | 2026-08-03 | oui | oui | fix(smb): use 'or WORKGROUP' fallback for domain_zone when connection_domain is NULL (resolves smb_spaces NOT NULL violation) |
| `638cc394` | 2026-08-03 | oui | oui | feat(archive): link an archive space to a source config; auto-select archive when source space is active |
| `b5d9ea5e` | 2026-07-29 | oui | oui | fix(ui): remove duplicate hash percentage from current job phase C to avoid confusion with global hash card |
| `695e115a` | 2026-07-29 | oui | oui | fix(hash): use global DB hash progress in indexer-monitoring dashboard; fix Phase C files_found to match actual hash target |
| `89de0f4c` | 2026-07-29 | oui | oui | fix(artefacts): drop unused_files (no last_accessed in indexed_files), migrate large/old to space_id |
| `198f502a` | 2026-07-29 | oui | oui | fix(artefacts): recreate large_files/old_files/unused_files on indexed_files_optimized |
| `0e1fc2aa` | 2026-07-29 | oui | oui | fix(ui): prevent empty-path 404 from hidden preview elements by checking previewModal.open |
| `d6f3157d` | 2026-07-29 | oui | oui | fix(artefacts): resolve space_id and crawl_config_id separately per view |
| `724f45b7` | 2026-07-29 | oui | oui | fix(ui): remove 'Version' prefix and 'v' duplication, display build timestamp on second line |
| `5dd5d1ec` | 2026-07-29 | oui | oui | fix(versioning): resolve PROJECT_ROOT correctly from backend/src/core/versioning.py |
| `60d88178` | 2026-07-29 | oui | oui | fix(deploy): use absolute path for .env file and skip npm if missing |
| `d9f70e52` | 2026-07-29 | oui | oui | fix(deploy): use correct path /srv/OpenIndex and handle local stash before pull |
| `777b4c47` | 2026-07-29 | oui | oui | fix: replace LibreOffice PDF conversion with HTML embedding for native read-only preview |
| `15d331b5` | 2026-07-29 | oui | oui | feat: dashboard charts, preview Office/video/audio, artefacts filter, LibreOffice |
| `6c610980` | 2026-07-28 | oui | oui | refonte complète interface + fix espaces SMB multi-sources |
| `70dcf8a3` | 2026-07-24 | oui | oui | affiche dossiers traités pendant Phase B sur 3e ligne |
| `a208d822` | 2026-07-24 | oui | oui | progression temps réel Phase B via compteur dossiers traités |
| `166e994f` | 2026-07-24 | oui | oui | ajout version commit dans le footer sidebar |
| `9cebdec6` | 2026-07-24 | oui | oui | fix: parsing SMB (espaces/accents), frontend 3 lignes progression, dirs_found |
| `7d4758fb` | 2026-07-23 | oui | oui | perf: avoid duplicate list_dir in get_file_info by passing entries_list |
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
