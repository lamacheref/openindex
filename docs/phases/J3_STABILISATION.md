# Phase J3 — Stabilisation de la stack active

## Stack active (référence)

- API : FastAPI
- Frontend : statique (`frontend/index.html`) via Nginx
- Base : SQLite (backend par défaut J3)
- Référence CI : `.github/workflows/docker-j3.yml`

## Objectif de phase

Garantir une exécution reproductible sur la chaîne J3 avant toute bascule J4.

## Contrôles minimaux obligatoires

1. Santé API : `GET /health`
2. Endpoints critiques : `GET /api/stats`, `GET /api/files`, `GET /api/duplicates`
3. Diagnostic SQL : `GET /api/db-explain`
4. Frontend disponible sur le port 3000

## Non-régression frontend

Vues clés à préserver :
- `dashboard`
- `files`
- `duplicates`
- `monitoring`

Commande recommandée :

```bash
pytest -q tests/test_frontend_structure.py
```

## Conventions de merge (J3)

1. Une PR = un lot cohérent et ciblé.
2. Preuve de validation obligatoire (commandes + statuts).
3. Documentation synchronisée si comportement modifié (`README`, `ROADMAP`, `TODO`, `CI-CD`, `docs/`).
4. Squash merge recommandé.
5. Aucun P1 mergé si un P0 de stabilisation est bloqué.

## Workflow de travail recommandé

1. Développer sur branche dédiée.
2. Mettre à jour code + docs dans le même lot.
3. Valider localement (build + smoke tests).
4. Commit atomique explicite.
5. PR avec impact, risques, validation.

## Statut legacy

- `.gitea/workflows/ci.yml` est conservé pour compatibilité/historique.
- Ce workflow legacy n'est pas gate de merge sur la phase active.
