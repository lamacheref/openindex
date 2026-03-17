# API - Incident `ModuleNotFoundError: No module named 'src.api'`

## Résumé

L'API ne démarrait pas car Uvicorn tentait de charger `src.api.main:app`, mais le package `src.api` n'était pas résolu dans certains contextes d'exécution (notamment en workers multiprocess).

## Symptômes observés

- Crash immédiat des workers Uvicorn au démarrage.
- Erreur répétée sur chaque process spawn.
- API indisponible (`healthcheck` en échec).

```text
ModuleNotFoundError: No module named 'src.api'
```

## Cause racine

Le code était lancé via un chemin de module valide (`src.api.main:app`), mais l'arborescence Python ne garantissait pas explicitement `src`/`src.api` comme packages importables dans tous les environnements.

## Correctif appliqué

1. Ajout de `src/__init__.py` pour déclarer explicitement le package `src`.
2. Ajout de `src/api/__init__.py` pour déclarer explicitement le package `src.api`.

Ce correctif rend l'import `src.api.main` robuste et compatible avec l'exécution multiprocess Uvicorn.

## Validation

Commande de vérification utilisée :

```bash
python -c "import src.api.main; print('ok')"
```

Résultat attendu : `ok`.

## Impact

- L'API peut démarrer correctement.
- Les workers Uvicorn n'échouent plus sur l'import initial.
- Le service redevient opérationnel.

## Date de mise à jour

2026-03-17

---

# API - Incident `TypeError: Client.__init__() got an unexpected keyword argument 'app'`

## Résumé

Les tests d'API échouaient en raison d'une incompatibilité de versions entre Starlette et httpx.

## Symptômes observés

- 25 erreurs lors de l'exécution des tests d'API.
- Erreur répétée : `TypeError: Client.__init__() got an unexpected keyword argument 'app'`.
- Tous les tests FastAPI échouaient lors de l'initialisation du client de test.
- Les tests smoke test étaient également impactés.

## Cause racine

Incompatibilité entre les versions des dépendances installées dans l'environnement de test :
- Starlette 0.27.0 (TestClient basé sur un appel `app=` côté client HTTP)
- httpx 0.28.1 (suppression de l'argument `app` dans le constructeur `Client`)

Conséquence : `fastapi.testclient.TestClient` échoue à l'initialisation.

## Correctif appliqué

1. Ajout d'une contrainte explicite sur Starlette dans `requirements/dev.txt` :
   ```text
   starlette>=0.37,<1.0
   ```
2. Conservation des contraintes existantes FastAPI/httpx compatibles avec cette plage.

Cette correction aligne les dépendances de test et supprime l'erreur d'initialisation du client.

## Validation

Commandes de vérification utilisées :

```bash
python -c "import fastapi, starlette, httpx; print(f'FastAPI: {fastapi.__version__}, Starlette: {starlette.__version__}, httpx: {httpx.__version__}')"
pytest tests/test_api_fastapi.py tests/test_api_smoke_critical.py -q
```

> Note : dans cet environnement, l'installation des dépendances depuis PyPI est bloquée par proxy (`403 Forbidden`), donc la validation de bout en bout nécessite un environnement CI/dev avec accès au registre Python.

## Impact

- Les versions de dépendances sont désormais explicites et cohérentes pour les tests FastAPI.
- Le risque de réapparition de cette erreur lors d'une nouvelle installation est fortement réduit.

## Date de mise à jour

2026-03-17
