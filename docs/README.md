# Documentation OpenIndex — index rationalisé avec PostgreSQL

## Parcours actuel (à suivre)

### Par phase

1. **Stabilisation initiale (historique)** : `docs/phases/J3_STABILISATION.md`
2. **J4 — Migration PostgreSQL** : `docs/phases/J4_MIGRATION.md`
3. **J5 — Qualité & observabilité** : `docs/phases/J5_QUALITE_OBSERVABILITE.md`

### Exploitation

- Runbook et protocoles : `docs/operations/EXPLOITATION.md`
- Gate CI PostgreSQL : `docs/operations/CI_POSTGRESQL_GATE.md`
- SLI/SLO J5 : `docs/operations/J5_SLI_SLO.md`
- Release gate J5 : `docs/operations/J5_RELEASE_GATE.md`
- Baseline observabilité J5 : `docs/operations/J5_OBSERVABILITY_BASELINE.md`
- Runbook exploitation : `docs/operations/EXPLOITATION.md`
- Contrat UI opérateur : `docs/definition_ui.md`

### Artefacts de preuve

- Dry-run migration : `docs/artifacts/migration_dry_run_j3_j4.json`
- Benchmark DB : `docs/artifacts/bench_sqlite_vs_postgresql.json` avec PostgreSQL
- Benchmark PostgreSQL actif : `docs/artifacts/bench_postgresql_active_2026-03-26.json`

## Référence active au 2026-03-18

- Le frontend expose le pilotage des explorations, l'arrêt d'un run actif et la suppression des runs terminés.
- L'API interdit désormais plusieurs runs actifs simultanés sur une même configuration.
- Le worker `crawler` consomme les `crawl_runs` en base, journalise sa progression réelle et reprend proprement après redémarrage.

## Archives / legacy

Les documents historiques, d'analyse ponctuelle et de propositions anciennes sont rangés dans `docs/archives/`.
Ils ne servent pas de source opérationnelle de vérité.
