# OpenIndex

Solution d’indexation de partages SMB avec **crawler Python**, **API FastAPI** et **frontend statique**.

## État actuel (mars 2026)

OpenIndex est actuellement exploité dans une variante **J3 orientée stabilisation** :

- API FastAPI (`src/api/main.py`) sur base **SQLite** via `OPENINDEX_DB_PATH`.
- Frontend statique (`frontend/index.html`) servi par Nginx.
- Endpoint de diagnostic SQL `GET /api/db-explain` + vue frontend associée.
- Orchestration recommandée : `docker-compose.j3.yml` (mode image-first, variable `OPENINDEX_J3_IMAGE`).
- Build/push d’image J3 automatisé via GitHub Actions (`.github/workflows/docker-j3.yml`).

> La cible J4 reste la consolidation PostgreSQL pour la suite.

## Fonctionnalités disponibles

- Indexation et inventaire de fichiers SMB.
- Statistiques globales (`/api/stats`).
- Listing/recherche de fichiers (`/api/files`).
- Détection des doublons (`/api/duplicates`).
- Monitoring temps réel via WebSocket (`/ws`).
- Analyse de plan SQLite (`/api/db-explain`).

## Démarrage rapide (J3)

```bash
cp .env.example .env
# optionnel: définir OPENINDEX_J3_IMAGE et OPENINDEX_DB_PATH

docker compose -f docker-compose.j3.yml pull
docker compose -f docker-compose.j3.yml up -d
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
