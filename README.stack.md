# OpenIndex Stack — Référence actuelle

## Stack active (à utiliser)

| Domaine | Composant actuel |
|---|---|
| API | FastAPI (`src/api/main.py`) |
| Frontend | HTML/JS statique (`frontend/index.html`) via Nginx |
| Base active | PostgreSQL (`OPENINDEX_DB_BACKEND=postgresql`) |
| Orchestration J3 | `docker-compose.j3.yml` |
| Image J3 | `Dockerfile.j3` + `OPENINDEX_J3_IMAGE` |

## Stack legacy (historique)

Les éléments ci-dessous restent disponibles pour historique/migration mais ne sont plus la voie recommandée :

- `docker-compose.stack.yml`
- `deploy-stack.sh`
- `Dockerfile.web`
- ancienne UI Streamlit

## Architecture fonctionnelle active

```text
Frontend (3000) -> API FastAPI (8000) -> PostgreSQL (service dédié)
                                 \-> WebSocket /ws
```

## Endpoints clés

- `GET /health`
- `GET /api/files`
- `GET /api/stats`
- `GET /api/duplicates`
- `GET /api/db-explain`
- `GET /docs`

## Décision J4 (actée)

- PostgreSQL est le backend principal et unique du parcours cible.
- La migration SQLite est abandonnée sur zone de test: recrawl complet systématique.
- L’API FastAPI et le frontend actuel sont conservés.
