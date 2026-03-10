# OpenIndex

Solution d’indexation de partages SMB avec **crawler Python**, **API FastAPI** et **frontend statique**.

## État actuel (J4 lancé — mars 2026)

Le projet est en **phase J4 (test grandeur nature PostgreSQL)**.

La base active à date est :

- API FastAPI (`src/api/main.py`) sur base **PostgreSQL** via `OPENINDEX_DB_BACKEND=postgresql`.
- Frontend statique (`frontend/index.html`) servi par Nginx.
- Endpoint de diagnostic SQL `GET /api/db-explain` + vue frontend associée.
- Orchestration recommandée : `docker-compose.j3.yml` (stack active, backend PostgreSQL).
- Build/push d’image automatisé via GitHub Actions (`.github/workflows/docker-j3.yml`).

> La migration SQLite n'est plus une étape requise: la zone de test ayant été massivement modifiée, un recrawl complet est la stratégie de référence.

## Fonctionnalités disponibles

- Indexation et inventaire de fichiers SMB.
- Statistiques globales (`/api/stats`).
- Listing/recherche de fichiers (`/api/files`).
- Détection des doublons (`/api/duplicates`).
- Monitoring temps réel via WebSocket (`/ws`).
- Analyse de plan PostgreSQL (`/api/db-explain`).

## Démarrage rapide (socle actuel)

```bash
cp .env.example .env
# optionnel: définir OPENINDEX_J3_IMAGE et OPENINDEX_DB_BACKEND=postgresql

docker compose -f docker-compose.j3.yml pull
docker compose -f docker-compose.j3.yml up -d
```

## Tests (commande unique J3)

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
- Runbook hebdo J1 + reprise SQLite : `docs/operations/EXPLOITATION.md`
- Plan d'accélération 2 semaines : `docs/phases/J4_MIGRATION.md`

## Limitations connues

- Le backend SQLite est désormais legacy et non supporté sur le parcours opératoire principal.
- Le workflow `.gitea/workflows/ci.yml` est conservé en legacy et ne constitue pas la gate de merge J3.
- La validation locale dépend de l'accès au registre pip pour installer `requirements/dev.txt`.
- Les tests structurels frontend vérifient le contrat HTML/Alpine, pas le rendu visuel pixel-perfect.
