## Type de version

- [ ] `fix` : correction incrémentant `PATCH` (`x.y.z` -> `x.y.z+1`)
- [ ] `minor` : évolution incrémentant `MINOR` (`x.y.z` -> `x.y+1.0`)

Règles :
- le titre de PR doit commencer par `fix:` ou `minor:`, ou la PR doit porter le label GitHub correspondant
- le fichier `VERSION` doit être mis à jour dans la PR
- la CI refusera une PR dont le bump de version ne correspond pas au type annoncé

## Résumé

-

## Vérifications

- [ ] Tests locaux exécutés
- [ ] `VERSION` mis à jour
