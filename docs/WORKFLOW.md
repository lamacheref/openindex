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


## Workflows CI actifs vs legacy

- **Actif (référence)** : `.github/workflows/docker-j3.yml` pour build et publication des images de la stack courante.
- **Legacy (compatibilité)** : `.gitea/workflows/ci.yml` conservé pour historique/infrastructures non cibles J1-J2.
- En cas de divergence, la décision opérationnelle est prise sur le workflow GitHub J3.

## Critères de passage J1 -> J2

### J1 validé si
- Les priorités critiques et hautes du `TODO.md` sont clôturées.
- Les checks API critiques et le scénario de non-régression frontend passent localement.
- Les workflows actifs vs legacy sont clairement documentés.

### J2 démarre avec
- Un backlog fiabilisation testable (tests API/front, protocole incident, exploitation).
- Une cadence de validation standard (tests + revue + PR) appliquée à chaque lot.
