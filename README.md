# OpenIndex

Solution d'indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## Installation (ProxmoxVE — test)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/lamacheref/OpenIndex/main/scripts/install_lxc.sh)"
```

Crée un conteneur LXC Ubuntu 24.04 (2 CPU, 2 Go RAM, 16 Go disque) avec :

- PostgreSQL 17
- PocketBase (auth)
- FastAPI backend
- Indexeur SMB (worker + scheduler)
- Frontend statique servi par Nginx (port 80)

Les credentials sont générés aléatoirement et sauvegardés dans `/srv/openindex/.env`.

## État actuel

**Phase J6 — Refonte protocolaire de l'indexeur terminée (T-INDEX-R02 ✅).**

L'indexeur implémente désormais le protocole 2 phases : BFS des répertoires → bottom-up des fichiers, avec contrôle d'existence sur 4 métadonnées (nom + taille + date création + date modification) et écriture dans la table `indexed_files_optimized`.

Ce qui reste :
- ⏳ **Tests unitaires Phase A/B** — Priorité 2
- ⏳ **Déploiement LXC stabilisé** — script créé, validation en cours
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
