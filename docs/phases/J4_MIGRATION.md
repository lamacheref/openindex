# Phase J4 — Migration et consolidation PostgreSQL

## Objectif de phase

Passer de la readiness documentée à une exécution PostgreSQL contrôlée, avec critères go/no-go vérifiables.

## Critères go/no-go pour exécution J4 PostgreSQL

### Go (tous requis)
- P95 `/api/stats` et `/api/files` en PostgreSQL stables sur 3 runs successifs.
- Initialisation PostgreSQL + recrawl complet sans erreur bloquante avec journal.
- Procédure rollback testée et validée par un pair.
- CI verte sur le backend `postgresql` (parcours de référence).

### No-go (un seul suffit)
- Régression P95 significative et répétable sur endpoint critique.
- Échec du journal d'initialisation/recrawl.
- Rollback incomplet/non reproductible.
- CI rouge sur le backend PostgreSQL de référence.

## Commandes de référence

```bash
python scripts/benchmark_dual_db.py --samples 30 --output docs/artifacts/bench_sqlite_vs_postgresql.json  # comparaison vs baseline historique SQLite
```

## Checklist release J4

- [ ] CI verte sur `postgresql`
- [ ] Rapport d'initialisation + recrawl versionné
- [ ] Benchmark comparatif publié
- [ ] Rollback relu/testé
- [ ] `CHANGELOG.md` à jour

## Backlog commando résiduel (ordre recommandé)

1. Finaliser décision formelle go/no-go.
2. Exécuter migration contrôlée en environnement de référence.
3. Valider performances post-bascule.
4. Durcir la CI dual DB (artefacts + diagnostic).
5. Rejouer un drill de rollback chronométré.
