# Gate CI PostgreSQL de référence

## Objectif

Bloquer tout merge tant que le parcours de référence PostgreSQL n'est pas vert et rendre chaque échec diagnostiquable sans relancer la pipeline à l'aveugle.

## Check requis

- Workflow actif : `.github/workflows/docker-stack.yml`
- Job de référence : `api-tests-postgresql`
- Commande exécutée : `./scripts/run_release_gate.sh`

## Règle de merge

- Le job `api-tests-postgresql` doit être déclaré comme **required status check** sur les branches protégées `main` et `develop`.
- Le workflow ne tolère plus l'absence de PostgreSQL : une indisponibilité réseau ou SQL fait désormais échouer le job.
- Les diagnostics sont publiés à chaque exécution via l'artefact GitHub Actions `api-tests-postgresql-diagnostics-<run_id>-<run_attempt>`.

## Contenu minimal de l'artefact

- `postgres-connectivity.json` : test socket + connexion SQL réelle.
- `pytest.log` : sortie complète de la gate.
- `pytest-junit.xml` : rapport structuré pytest.
- `pytest.exitcode` : code de sortie du pack.
- `postgres-service.log` : logs du service PostgreSQL CI.
- `runner-summary.json` et `pip-freeze.txt` : contexte d'exécution.

## Diagnostic rapide si la pipeline est rouge

1. Ouvrir le run GitHub Actions en échec et télécharger l'artefact `api-tests-postgresql-diagnostics-*`.
2. Lire `postgres-connectivity.json`.
3. Si `socket_available=false`, traiter l'incident comme un problème de boot/service GitHub Actions.
4. Si `socket_available=true` mais `sql_available=false`, traiter l'incident comme un problème de connexion PostgreSQL ou de dépendance Python.
5. Si la connexion SQL est verte, lire `pytest.log` puis `pytest-junit.xml` pour identifier le test cassé.
6. En cas de doute sur l'état du service, corréler avec `postgres-service.log`.

## Portée

- Cette gate couvre le backend PostgreSQL, le smoke critique API, la non-régression structurelle frontend et le feature flag DB.
- Les jobs de build/publish restent utiles mais ne remplacent pas le check de référence pour autoriser un merge.
