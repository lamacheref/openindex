# CI de référence J3 + conventions de merge

## Référence unique à utiliser

La chaîne de référence pour l'état actuel OpenIndex (J3, SQLite) est:

- `.github/workflows/docker-j3.yml`

Cette chaîne est la seule source de vérité pour les validations d'intégration continue.

## Statut des workflows legacy

- `.gitea/workflows/ci.yml` reste conservé pour compatibilité historique.
- Ce workflow legacy ne doit pas être utilisé comme gate de merge J3.
- Toute divergence entre workflows doit être résolue en faveur de la chaîne GitHub J3.

## Conventions de merge (J3)

1. **Branche courte et ciblée**: une PR = un lot cohérent.
2. **Preuve de validation obligatoire**: commandes lancées + statut (pass/warn/fail).
3. **Documentation synchronisée**: si comportement/opération change, mettre à jour `README.md`, `TODO.md`, `CI-CD.md` ou `docs/`.
4. **Merge policy**: squash merge recommandé pour conserver un historique lisible des lots commando.
5. **Blocage P0**: aucun merge d'un ticket P1 si un ticket P0 de stabilisation est en défaut.

## Check de merge minimal

- Build images concernées sans erreur (`Dockerfile.crawler` / `Dockerfile.frontend`).
- Tests de non-régression ciblés (API critique + frontend structure) exécutés.
- Référence CI J3 citée dans la PR en cas de question de gouvernance.
