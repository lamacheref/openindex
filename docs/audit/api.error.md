# Logs API - Erreurs de démarrage

## Erreurs observées

### ModuleNotFoundError: No module named 'src.api'

L'API ne parvient pas à démarrer en raison d'une erreur d'import du module `src.api`.

**Erreur complète :**
```
ModuleNotFoundError: No module named 'src.api'
```

**Contexte :**
- L'application tente de charger le module via `uvicorn src.api.main:app`
- Le module `src.api` n'est pas trouvé dans le PYTHONPATH
- Cela se produit lors de l'initialisation de chaque worker process

**Processus concernés :**
- Process SpawnProcess-1
- Process SpawnProcess-2  
- Process SpawnProcess-3
- Process SpawnProcess-4
- Process SpawnProcess-135

**Stack trace type :**
```
File "/usr/local/lib/python3.11/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
File "/usr/local/lib/python3.11/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
ModuleNotFoundError: No module named 'src.api'
```

**Impact :**
- L'API ne démarre pas
- Tous les workers échouent lors de l'import du module
- Le service est inopérant

**Durée d'observation :** 5 secondes
**Date :** 2026-03-17