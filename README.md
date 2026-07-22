# OpenIndex

Solution d’indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## État actuel (J6 — juillet 2026)

Le projet est en phase **J6 — Déploiement LXC & Validation Indexeur**. L'infrastructure Docker est en cours de remplacement par des conteneurs LXC natifs, plus stables et mieux adaptés à l'infrastructure cible.

L'indexeur SMB est fonctionnellement complet (T-INDEX-01) mais nécessite une validation finale en conditions réelles avant le tag 0.7.0.

### Fonctionnalités disponibles

**Indexeur SMB (T-INDEX-01) :**
- Indexation complète SMB multi-espaces avec crawler récursif
- Scheduler cron pour scrutation périodique
- Files différenciées (fast <200Mo / slow >=200Mo)
- Hashage xxHash64 avec streaming et fallback SHA256
- Détection incrémentielle des changements (hash + timestamps)
- Détection automatique des fichiers ordures (*.tmp, Thumbs.db, etc.)
- Queue retry pour fichiers verrouillés
- Batch insert optimisé (100 fichiers/lot)
- Logs structurés JSON
- 12+ endpoints API REST (`/api/indexer/*`)
- Dashboard de monitoring temps réel

**Archivage (T-ARCH-01/02/03/04) :**
- Queue de jobs persistants en PostgreSQL
- Transfer Worker avec retry exponentiel + jitter
- Architecture hybride montage SMB + fallback programmatique
- API REST complète (7 endpoints)

**Authentification (T-AUTH-01) :**
- Intégration PocketBase, login JWT, routes protégées

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

### Installation LXC (recommandée — stable)

```bash
# Prérequis : Debian/Ubuntu avec LXC installé
sudo apt install lxc lxc-templates bridge-utils smbclient

# Déploiement complet (création des conteneurs, configuration, démarrage)
sudo ./scripts/install_lxc.sh

# Le script vous guidera à travers :
#   1. Configuration réseau (bridge LXC)
#   2. Paramètres SMB (partages, credentials)
#   3. Mots de passe PostgreSQL et PocketBase
```

**Services déployés :**
| Conteneur | Rôle | Accès |
|---|---|---|
| `lxc-openindex-pgsql` | PostgreSQL 16 | 10.0.3.10:5432 |
| `lxc-openindex-api` | FastAPI | 10.0.3.11:8000 |
| `lxc-openindex-frontend` | Nginx (frontend) | 10.0.3.12:80 |
| `lxc-openindex-worker` | Indexeur + workers SMB | — |
| `lxc-openindex-pb` | PocketBase (auth) | 10.0.3.14:8090 |

### Déploiement Docker (legacy — déprécié)

```bash
cp .env.example .env
./deploy.sh pull
./deploy.sh up
```

> Docker est maintenu pour compatibilité temporaire mais n'est plus le socle de production recommandé. La migration vers LXC est en cours (phase J6).

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
- Rapport d'avancement : `docs/rapports/20260722_rapport_avancement.md`
- Journal détaillé : `docs/`
- Guide d'installation LXC : `docs/operations/INSTALLATION_LXC.md` *(à construire)*
- Guide d'exploitation LXC : `docs/operations/EXPLOITATION_LXC.md` *(à construire)*
- Runbook hebdo d'exploitation PostgreSQL : `docs/operations/EXPLOITATION.md`
- Guide d'administration de l'indexation : `docs/operations/INDEXATION.md`

## Limitations connues

- **Docker déprécié** : l'infrastructure Docker est en cours de remplacement par LXC (phase J6). Utilisation possible mais non recommandée pour la production.
- **Erreur de syntaxe** dans `_handle_file_conflict()` (`backend/src/workers/indexer_worker.py:1078`) — corrigée dans la version 0.7.0.
- **Tests d'intégration manquants** : l'indexeur n'a que des tests unitaires mockés. Les tests d'intégration réels sont prévus en J6.
- Le backend SQLite est legacy et non supporté sur le parcours opératoire principal.
- Le workflow `.gitea/workflows/ci.yml` est conservé en legacy et ne constitue pas la gate de merge de la stack active.
- La validation locale dépend de l'accès au registre pip pour installer `requirements/dev.txt`.
