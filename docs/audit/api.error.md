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

---

# API - Incident `TypeError: Client.__init__() got an unexpected keyword argument 'app'`

## Résumé

Les tests d'API échouent en raison d'une incompatibilité de versions entre FastAPI (0.103.1) et Starlette (0.27.0) utilisées dans l'environnement de test.

## Symptômes observés

- 25 erreurs lors de l'exécution des tests d'API
- Erreur répétée : `TypeError: Client.__init__() got an unexpected keyword argument 'app'`
- Tous les tests FastAPI échouent lors de l'initialisation du client de test
- Tests de smoke test également impactés

## Cause racine

Incompatibilité entre les versions des dépendances :
- FastAPI version 0.103.1
- Starlette version 0.27.0
- httpx version 0.28.1

La version de Starlette ne reconnaît pas le paramètre `app` dans le constructeur de TestClient, ce qui cause l'échec de l'initialisation des clients de test.

## Tests impactés

### Erreurs (25) :
- Tous les tests de `test_api_fastapi.py`
- Tous les tests de `test_api_smoke_critical.py`

### Échecs (3) :
- `test_api_concurrent_health_requests`
- `test_frontend_has_expected_views_and_bindings`
- `test_queue_initialization`

### Succès (19) :
- Tests de base de données
- Tests de configuration
- Tests de frontend structure

## Correctifs recommandés

1. **Mettre à jour les dépendances** :
   ```bash
   pip install fastapi>=0.110.0 starlette>=0.28.0
   ```

2. **Adapter les tests** pour utiliser la nouvelle API de TestClient si nécessaire

3. **Vérifier la compatibilité** des versions dans requirements.txt

## Validation

Commande de vérification des versions :
```bash
python -c "import fastapi, starlette, httpx; print(f'FastAPI: {fastapi.__version__}, Starlette: {starlette.__version__}, httpx: {httpx.__version__}')"
```

## Impact

- Les tests d'intégration ne peuvent pas être exécutés
- Impossible de valider le bon fonctionnement de l'API via les tests automatisés
- Le code de l'API fonctionne correctement, mais les tests d'intégration échouent

## Date de mise à jour

2026-03-17
