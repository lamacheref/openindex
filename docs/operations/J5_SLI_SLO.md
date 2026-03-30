# J5 — SLI/SLO opérationnels minimum

## Objectif

Fixer un socle mesurable pour la disponibilité, la performance et la récupération avant d'étendre l'observabilité.

## SLI / SLO retenus

| Domaine | SLI | Source de mesure | SLO cible | Seuil d'alerte | Responsable | Revue |
|---|---|---|---|---|---|---|
| Disponibilité API | Taux de succès `200` sur `/health` | Probe locale/exploitation + gate CI | `>= 99,5 %` par semaine | `< 99,8 %` sur 24 h | Exploitation OpenIndex | Hebdo |
| Latence endpoints critiques | P95 de `/api/stats` et `/api/files?limit=5&offset=0` | Benchmark versionné `docs/artifacts/bench_postgresql_active_2026-03-26.json` puis runs suivants | `<= 100 ms` sur le parcours de référence | `> 120 ms` sur 2 runs successifs | Référent backend | Hebdo |
| Taux d'erreurs critique | Ratio de succès du pack `run_release_gate.sh` | CI GitHub + exécution locale de release gate | `100 %` sur chaque release candidate | `1` test rouge suffit | Référent release | À chaque PR/release |
| Recovery incident DB/API | Temps entre détection et retour `health` + gate verte | Runbook + drill de rollback + incident réel | `<= 30 min` | `> 20 min` sans service rétabli | Astreinte / opérateur | Après incident |

## Décisions de seuil

- Le SLO de latence reprend la preuve de référence du `2026-03-26`, où le P95 observé reste autour de `56 ms` sur `/api/stats` et `66 ms` sur `/api/files`.
- Le seuil d'alerte est volontairement au-dessus de la baseline mais en dessous d'une dérive qui banaliserait une régression.
- Le taux d'erreurs critique est binaire à ce stade : un seul échec sur le release gate bloque la publication.

## Actions attendues en cas d'écart

- Disponibilité : vérifier `/health`, la connectivité PostgreSQL, puis les logs API/crawler.
- Latence : rejouer le benchmark de référence, comparer au dernier artefact validé et ouvrir un incident si la dérive se confirme.
- Taux d'erreurs : bloquer le merge, télécharger l'artefact CI, corriger avant tout nouveau merge.
- Recovery : appliquer `docs/operations/EXPLOITATION.md`, puis consigner le temps réel de rétablissement.

## Preuves de référence

- Benchmark actif : `docs/bench_postgresql_active_2026-03-26.md`
- Artefact benchmark : `docs/artifacts/bench_postgresql_active_2026-03-26.json`
- Gate CI PostgreSQL : `docs/operations/CI_POSTGRESQL_GATE.md`
