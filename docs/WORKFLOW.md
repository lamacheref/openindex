# Workflow de travail — version actualisée

## Flux recommandé

1. Développer sur branche de travail.
2. Mettre à jour code + documentation dans le même lot.
3. Valider localement (build + smoke tests API).
4. Commit atomique et message explicite.
5. PR avec résumé impact + risques + étapes de test.

## Règle documentaire

Toute évolution de stack doit être répercutée au minimum dans :
- `README.md`
- `README.stack.md`
- `ROADMAP.md`
- `TODO.md`

## Référence CI

- Prioritaire : GitHub workflow `docker-j3.yml`.
- Legacy : `.gitea/workflows/ci.yml` (à maintenir séparément de la doc active).
