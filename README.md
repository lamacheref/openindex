# OpenIndex

Solution d’indexation de partages SMB avec **crawler Python**, **API FastAPI**, **frontend statique** et **PostgreSQL**.

## État actuel (J4 en revalidation — mars 2026)

Le projet tourne sur une base **PostgreSQL** stabilisée, mais la preuve J4 doit encore être régénérée sur un recrawl complet de référence avant de rétablir une décision formelle exploitable.

La base active à date est :

- API FastAPI (`src/api/main.py`) avec base de données **PostgreSQL** via `OPENINDEX_DB_BACKEND=postgresql`.
- Frontend statique (`frontend/index.html`) servi par Nginx.
- Endpoint de diagnostic SQL `GET /api/db-explain` avec vue frontend associée.
- Orchestration recommandée : `docker-compose.yml` (stack complète PostgreSQL).
- Build/push d’images automatisé via GitHub Actions (`.github/workflows/docker-stack.yml`).

> La migration SQLite n'est plus nécessaire : la zone de test ayant été massivement modifiée, un recrawl complet est la stratégie de référence.
> La décision formelle J4 actuellement exploitable est `No-Go` tant que la nouvelle preuve de recrawl complet n'est pas publiée : voir `docs/2026-03-18_j4_go-no-go.md` et `docs/2026-03-18_j4_execution_report.md`.

## Fonctionnalités disponibles

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

## Installation

## Démarrage rapide (socle actuel avec PostgreSQL)

```bash
cp .env.example .env
# optionnel: renseigner OPENINDEX_API_IMAGE / OPENINDEX_CRAWLER_IMAGE / OPENINDEX_UI_IMAGE dans .env
# si packages GHCR privés: définir GHCR_USERNAME et GHCR_TOKEN dans .env

# Vérifier la disponibilité de PostgreSQL
./deploy.sh pull
./deploy.sh up
```

## Tests (commande unique)

Pour standardiser l'environnement de validation local (CMD-01), lancez:

```bash
./scripts/run_j3_test_suite.sh
```

Ce script crée un `.venv` local si nécessaire, installe `requirements/dev.txt`, puis exécute `pytest -q tests`.
Pour cibler les tests critiques anti-flakiness uniquement:

```bash
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
- Plan d'accélération 2 semaines : `docs/phases/J4_MIGRATION.md`

## Limitations connues

- Le backend SQLite est désormais legacy et non supporté sur le parcours opératoire principal.
- Le workflow `.gitea/workflows/ci.yml` est conservé en legacy et ne constitue pas la gate de merge de la stack active.
- La validation locale dépend de l'accès au registre pip pour installer `requirements/dev.txt`.
- Les tests structurels frontend vérifient le contrat HTML/Alpine, pas le rendu visuel pixel-perfect.
