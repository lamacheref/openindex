# TODO OpenIndex — Suivi opérationnel

## Priorité haute (semaine en cours)

- [ ] Valider un jeu de tests reproductible API (`/health`, `/api/stats`, `/api/files`, `/api/db-explain`).
- [ ] Ajouter un scénario de test de non-régression frontend sur les vues principales.
- [ ] Documenter procédure de récupération sur DB SQLite absente/corrompue.

## Priorité moyenne

- [ ] Clarifier les workflows CI legacy vs J3 dans la gouvernance du dépôt.
- [ ] Définir les critères de bascule J3 -> J4 (PostgreSQL).
- [ ] Ajouter une section “limitations connues” dans le README.

## Backlog J4

- [ ] Implémenter adaptateur PostgreSQL API en parallèle du mode SQLite.
- [ ] Valider performances sur volumétrie représentative.
- [ ] Documenter migration des données J3 vers J4.

## Fait récemment

- [x] Harmonisation complète de la documentation (racine + `docs/`).
- [x] Clarification de la stack active et des composants legacy.
- [x] Mise à jour roadmap/projet/workflow sur état réel.
