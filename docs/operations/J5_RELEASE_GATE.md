# J5 — Release gate minimal

## Commande unique

```bash
./scripts/run_release_gate.sh
```

## Contenu du pack

- `tests/test_api_fastapi.py`
- `tests/test_api_smoke_critical.py`
- `tests/test_db_backend_feature_flag.py`
- `tests/test_frontend_structure.py`

## Couverture par exigence

- Smoke API critique PostgreSQL : `tests/test_api_smoke_critical.py`
- Non-régression frontend structurelle : `tests/test_frontend_structure.py`
- Vérification DB explain / requêtes clés : `tests/test_api_smoke_critical.py` et `tests/test_api_fastapi.py`
- Sélection explicite du backend PostgreSQL : `tests/test_db_backend_feature_flag.py`

## Attendu

- `100 %` vert avant merge sur le parcours de référence PostgreSQL.
- Même commande utilisable en local et dans GitHub Actions pour éviter deux définitions différentes du gate.

## Sorties de preuve

- En CI : artefact `api-tests-postgresql-diagnostics-*`
- En local : sortie pytest standard, à joindre à toute preuve J5 si exécution de validation manuelle

## Quand l'utiliser

- Avant merge de toute PR touchant la stack active.
- Avant publication d'une image ou d'un tag opératoire.
- Après incident PostgreSQL ou changement de requêtes critiques.
