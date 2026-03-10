# TODO OpenIndex — J1 à J3

## Priorité critique (J1)

- [x] Établir une checklist de démarrage hebdo (runbook court).
- [x] Valider un jeu de tests reproductible API (`/health`, `/api/stats`, `/api/files`, `/api/db-explain`).
- [x] Décrire la procédure de reprise sur incident SQLite (absence/corruption).

## Priorité haute (J1)

- [x] Ajouter un scénario de non-régression frontend sur les vues principales.
- [x] Clarifier les workflows CI actifs vs legacy dans le dépôt.
- [x] Définir les critères de sortie J1 et entrée J2.

## Préparation J2/J3 (finalisée)

- [x] Formaliser les SLO minimaux API (latence, erreurs, disponibilité) via KPI commando et critères go/no-go.
- [x] Préparer un plan de test de charge et benchmark comparatif SQLite vs PostgreSQL.
- [x] Lister les prérequis techniques pour la consolidation PostgreSQL (adaptateur parallèle, dry-run, rollback, CI dual DB).

## Suite (issue des docs / option commando)

### Semaine 1 — Stabilisation exécutable J3

- [ ] CMD-01 — Standardiser l'environnement de test (requirements/dev + script unique).
- [ ] CMD-02 — Fiabiliser les tests API critiques et éliminer la flakiness.
- [ ] CMD-03 — Renforcer la non-régression frontend sur les vues clés.
- [ ] CMD-04 — Tester le runbook incident SQLite et mesurer le temps de recovery.
- [ ] CMD-05 — Documenter une CI de référence unique (J3) + conventions de merge.
- [ ] CMD-06 — Ajouter la section "limitations connues" dans la documentation principale.

### Semaine 2 — Readiness J4 sans big bang

- [ ] CMD-07 — Définir les critères go/no-go J3 -> J4 (perf, rollback, migration).
- [ ] CMD-08 — Introduire l'adaptateur PostgreSQL en mode parallèle (feature flag).
- [ ] CMD-09 — Écrire et valider le dry-run de migration J3 -> J4.
- [ ] CMD-10 — Publier un bench comparatif SQLite vs PostgreSQL (P95 endpoints critiques).
- [ ] CMD-11 — Étendre la CI pour couvrir SQLite + PostgreSQL (matrice dual DB).
- [ ] CMD-12 — Préparer la checklist de release commando.

## Fait (lancement J1)

- [x] Mise à jour synchronisée `CHANGELOG`, `PROJET`, `README`, `ROADMAP`, `TODO`.
- [x] Version projet incrémentée pour marquer le kickoff J1.
