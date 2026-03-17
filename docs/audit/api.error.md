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

Commande de vérification utilisée :

```bash
python -c "import src.api.main; print('ok')"
```

Résultat attendu : `ok`.

## Impact

- L'API peut démarrer correctement.
- Les workers Uvicorn n'échouent plus sur l'import initial.
- Le service redevient opérationnel.

## Date de mise à jour

2026-03-17
