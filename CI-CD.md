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
- `OPENINDEX_DB_BACKEND` : backend DB attendu (`postgresql`).

## Commandes de validation locale

```bash
docker build -f Dockerfile.j3 -t openindex-j3:local .
docker compose -f docker-compose.j3.yml up -d
curl -f http://localhost:8000/health
```


## Matrice de décision (actif vs legacy)

| Chaîne | Statut | Usage attendu | Action |
|---|---|---|---|
| `.github/workflows/docker-j3.yml` | **Active** | Build/publish images crawler+UI pour la stack courante | Référence unique pour validations CI J1/J2 |
| `.gitea/workflows/ci.yml` | **Legacy** | Historique, compatibilité infra Gitea non cible | Ne pas utiliser comme source de vérité; maintenance minimale |

## Critères de sortie J1 vers entrée J2

### Sortie J1 (DoD)

- Documentation de pilotage alignée (`README`, `ROADMAP`, `TODO`, `CI-CD`, `docs/phases/J3_STABILISATION`).
- Contrôles critiques automatisés disponibles (API smoke + non-régression frontend structurelle).
- Distinction explicite entre workflows CI actifs et legacy actée dans la documentation.

### Entrée J2 (gating)

- Exécution reproductible de la suite de smoke tests en local/CI.
- Règles de contribution orientées stack active (FastAPI + frontend + PostgreSQL) explicites.
- Backlog J2 priorisé sur fiabilisation (tests, incident, exploitation).

## Convention de merge J3

La convention opérationnelle de merge et la référence CI unique sont détaillées dans `docs/phases/J3_STABILISATION.md`.
