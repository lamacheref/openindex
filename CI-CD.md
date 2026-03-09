# CI/CD OpenIndex — état actuel

## Pipelines actifs

### 1) GitHub Actions (J3)
Fichier : `.github/workflows/docker-j3.yml`

- Déclencheurs : push/PR sur `main` et `develop`, tags `v*`, dispatch manuel.
- Build de l’image `Dockerfile.j3`.
- Push vers GHCR hors pull request.
- Tags gérés : branch, tag, sha, latest (branche par défaut).

### 2) Gitea workflow (legacy)
Fichier : `.gitea/workflows/ci.yml`

- Pipeline historique centré crawler + web legacy.
- Référence maintenue pour compatibilité, mais non alignée J3/J4.

## Recommandation opérationnelle

Pour l’état actuel du projet, la référence CI est le workflow GitHub J3.

## Variables clés

- `OPENINDEX_J3_IMAGE` : image à déployer via `docker-compose.j3.yml`.
- `OPENINDEX_DB_PATH` : chemin SQLite côté API.

## Commandes de validation locale

```bash
docker build -f Dockerfile.j3 -t openindex-j3:local .
docker compose -f docker-compose.j3.yml up -d
curl -f http://localhost:8000/health
```
