# Phase J4 — Migration et consolidation PostgreSQL

## Objectif de phase

Passer de la readiness documentée à une migration contrôlée, avec critères go/no-go vérifiables.

## Critères go/no-go J3 -> J4

### Go (tous requis)
- P95 `/api/stats` et `/api/files` en PostgreSQL <= +10% vs SQLite (3 runs).
- Dry-run migration sans erreur bloquante avec journal.
- Procédure rollback testée et validée par un pair.
- CI verte en matrice `sqlite` + `postgresql`.

### No-go (un seul suffit)
- Régression P95 > 10% sur endpoint critique.
- Échec du journal dry-run.
- Rollback incomplet/non reproductible.
- CI rouge sur un backend DB.

## Commandes de référence

```bash
python scripts/migration_dry_run_j3_j4.py --dry-run --journal docs/artifacts/migration_dry_run_j3_j4.json
python scripts/benchmark_dual_db.py --samples 30 --output docs/artifacts/bench_sqlite_vs_postgresql.json
```

## Checklist release J4

- [ ] CI verte sur `sqlite` et `postgresql`
- [ ] Dry-run migration versionné
- [ ] Benchmark comparatif publié
- [ ] Rollback relu/testé
- [ ] `CHANGELOG.md` à jour

## Backlog commando résiduel (ordre recommandé)

1. Finaliser décision formelle go/no-go.
2. Exécuter migration contrôlée en environnement de référence.
3. Valider performances post-bascule.
4. Durcir la CI dual DB (artefacts + diagnostic).
5. Rejouer un drill de rollback chronométré.
