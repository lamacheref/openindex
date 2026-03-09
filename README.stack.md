# OpenIndex Stack — Référence actuelle

## Stack active (à utiliser)

| Domaine | Composant actuel |
|---|---|
| API | FastAPI (`src/api/main.py`) |
| Frontend | HTML/JS statique (`frontend/index.html`) via Nginx |
| Base J3 | SQLite (`OPENINDEX_DB_PATH`) |
| Orchestration J3 | `docker-compose.j3.yml` |
| Image J3 | `Dockerfile.j3` + `OPENINDEX_J3_IMAGE` |

## Stack legacy (historique)

Les éléments ci-dessous restent disponibles pour historique/migration mais ne sont plus la voie recommandée :

- `docker-compose.stack.yml`
- `deploy-stack.sh`
- `Dockerfile.web`
- ancienne UI Streamlit

## Architecture fonctionnelle J3

```text
Frontend (3000) -> API FastAPI (8000) -> SQLite (fichier local monté)
                                 \-> WebSocket /ws
```

## Endpoints clés

- `GET /health`
- `GET /api/files`
- `GET /api/stats`
- `GET /api/duplicates`
- `GET /api/db-explain`
- `GET /docs`

## Transition J4 (prévue)

- Basculer vers PostgreSQL comme backend principal.
- Conserver l’API FastAPI et le frontend actuel.
- Adapter la CI pour image applicative cible J4.
