# CI/CD OpenIndex — état actuel

## Pipelines actifs

### 1) GitHub Actions (stack active)
Fichier : `.github/workflows/docker-stack.yml`

- Déclencheurs : push/PR sur `main` et `develop`, tags `v*`, dispatch manuel.
- Build/push des images `openindex-api`, `openindex-crawler`, `openindex-ui` vers GHCR.
- Push vers GHCR hors pull request.
- Tags gérés : branch, tag, sha, latest (branche par défaut).

### 2) Gitea workflow (legacy)
Fichier : `.gitea/workflows/ci.yml`

- Pipeline historique centré crawler + web legacy.
- Référence maintenue pour compatibilité, mais non alignée sur la stack active.

## Recommandation opérationnelle

Pour l’état actuel du projet, la référence CI est le workflow GitHub stack active.

## Variables clés

- `OPENINDEX_API_IMAGE`, `OPENINDEX_CRAWLER_IMAGE`, `OPENINDEX_UI_IMAGE` : images GHCR à déployer via `docker-compose.yml`.
- `OPENINDEX_DB_BACKEND` : backend DB attendu (`postgresql`).

## Commandes de validation locale

```bash
./deploy.sh pull
./deploy.sh up
curl -f http://localhost:8000/health
```


## Matrice de décision (actif vs legacy)

| Chaîne | Statut | Usage attendu | Action |
|---|---|---|---|
| `.github/workflows/docker-stack.yml` | **Active** | Build/publish images API+crawler+UI pour la stack courante | Référence unique pour validations CI |
| `.gitea/workflows/ci.yml` | **Legacy** | Historique, compatibilité infra Gitea non cible | Ne pas utiliser comme source de vérité; maintenance minimale |

## Critères de sortie J1 vers entrée J2

### Sortie J1 (DoD)

- Documentation de pilotage alignée (`README`, `ROADMAP`, `TODO`, `CI-CD`).
- Contrôles critiques automatisés disponibles (API smoke + non-régression frontend structurelle).
- Distinction explicite entre workflows CI actifs et legacy actée dans la documentation.

### Entrée J2 (gating)

- Exécution reproductible de la suite de smoke tests en local/CI.
- Règles de contribution orientées stack active (FastAPI + frontend + PostgreSQL) explicites.
- Backlog J2 priorisé sur fiabilisation (tests, incident, exploitation).

## Convention de merge

La convention opérationnelle de merge est d'imposer la CI `docker-stack.yml` sur toute PR touchant la stack.

## Gate PostgreSQL de référence

- Check nominal à imposer avant merge : `api-tests-postgresql`
- Workflow : `.github/workflows/docker-stack.yml`
- Commande mutualisée : `./scripts/run_release_gate.sh`
- Artefact de diagnostic : `api-tests-postgresql-diagnostics-<run_id>-<run_attempt>`

Le dépôt contient désormais le durcissement du job et la collecte systématique des diagnostics. Le blocage effectif avant merge dépend de la protection GitHub des branches `main` et `develop`, où `api-tests-postgresql` doit être déclaré en `required status check`.

Chemin de diagnostic rapide : `docs/operations/CI_POSTGRESQL_GATE.md`
