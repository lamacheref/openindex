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


## Scénario non-régression frontend (vues principales)

Objectif: garantir la présence des vues clés et de leurs bindings Alpine.

- Vues contrôlées: `dashboard`, `files`, `duplicates`, `monitoring`.
- Vérifications minimales:
  - présence du déclencheur `currentView = ...` dans la navigation,
  - présence du conteneur de vue `x-show="currentView === ..."`,
  - présence des libellés utilisateur associés (Tableau de bord, Fichiers, Doublons, Monitoring).

Commande recommandée:

```bash
pytest -q tests/test_frontend_structure.py
```
