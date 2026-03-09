# Protocoles automatisés — état cible minimal

## Contrôles à systématiser

1. Santé API : `GET /health`.
2. Endpoints métiers : `GET /api/stats`, `GET /api/files`, `GET /api/duplicates`.
3. Endpoint diagnostic : `GET /api/db-explain`.
4. Frontend disponible via Nginx (port 3000).

## Pipeline recommandé

- Build image J3 (`Dockerfile.j3`).
- Lancement compose J3.
- Tests HTTP de fumée.
- Collecte artefacts logs en cas d’échec.

## Écart actuel

Les workflows legacy existent encore; la référence opérationnelle doit rester la chaîne J3.
