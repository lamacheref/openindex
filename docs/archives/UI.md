# UI OpenIndex — état actuel

## Technologie

- Frontend statique unique : `frontend/index.html`.
- Bibliothèques côté client : Alpine.js, HTMX, TailwindCSS, Chart.js.

## Vues principales

- Tableau de bord
- Fichiers
- Doublons
- Monitoring
- Analyse DB (plan SQL)

## Intégration API

L’interface interroge principalement :
- `/api/stats`
- `/api/files`
- `/api/duplicates`
- `/api/db-explain`
- WebSocket `/ws`

## Note

Le frontend Streamlit historique est considéré comme legacy.
