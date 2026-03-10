# Readiness J4 — CMD-07 à CMD-12

## CMD-07 — Critères go/no-go J3 -> J4

### Go (tous requis)
- **Performance**: P95 `/api/stats` et `/api/files` en PostgreSQL <= +10% de SQLite sur 3 runs.
- **Migration**: dry-run sans erreur bloquante avec journal généré.
- **Rollback**: procédure documentée testée une fois et validée par un pair.
- **CI**: pipeline vert sur matrice `sqlite` + `postgresql`.

### No-go (un seul suffit)
- Régression P95 > 10% sur endpoint critique.
- Échec de génération du journal dry-run.
- Rollback incomplet ou non reproductible.
- CI rouge sur un backend DB.

## CMD-09 — Dry-run de migration J3 -> J4

Commande:

```bash
python scripts/migration_dry_run_j3_j4.py --dry-run --journal docs/migration_dry_run_j3_j4.json
```

Sortie attendue:
- Un journal JSON contenant:
  - volumes SQLite,
  - état PostgreSQL avant migration,
  - delta estimé,
  - plan de rollback.

## CMD-10 — Bench comparatif SQLite vs PostgreSQL

Commande:

```bash
python scripts/benchmark_dual_db.py --samples 30 --output docs/bench_sqlite_vs_postgresql.json
```

Le rapport historisé est: `docs/bench_sqlite_vs_postgresql.json`.

## CMD-11 — CI dual DB

Le workflow CI exécute désormais une matrice `OPENINDEX_DB_BACKEND=sqlite|postgresql` pour les tests API critiques.

## CMD-12 — Checklist release commando

- [ ] Vérifier CI verte sur les 2 backends DB.
- [ ] Vérifier dry-run migration + journal versionné.
- [ ] Vérifier benchmark comparatif publié.
- [ ] Confirmer procédure rollback relue par un pair.
- [ ] Tagger release et mettre à jour `CHANGELOG.md`.
