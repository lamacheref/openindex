# TODO OpenIndex — suite post-commando (J4 -> J5)

## Objectif

Passer d'une **readiness J4 documentée** à une **exécution J4 pilotée par preuves**, puis enclencher J5 (qualité & observabilité) avec critères de sortie mesurables.

---

## 1) Priorités immédiates (Semaine en cours)

- [x] **T-01 — Clôturer CMD-12 (checklist release commando) avec preuves**
  - Vérifier CI verte sur PostgreSQL (backend unique).
  - Migration de DB non requise : re-crawl complet prévu sur zone de test massivement modifiée avec PostgreSQL.
  - Vérifier bench comparatif publié avec PostgreSQL.
  - Vérifier rollback relu par un pair.
  - Mettre à jour `CHANGELOG.md` pour le lot de clôture.
  - Numéro de commit : [commit_hash]

- [ ] **T-02 — Décision formelle Go/No-Go J4**
  - Appliquer les critères de `docs/phases/J4_MIGRATION.md`.
  - Rédiger la décision dans un compte-rendu daté dans `docs/`.
  - Si No-Go: lister précisément les écarts bloquants et le plan de correction.

- [ ] **T-03 — Figer la baseline technique J4**
  - Confirmer PostgreSQL comme backend de données unique dans la doc principale.
  - Aligner `README.md`, `README.stack.md`, `ROADMAP.md` et ce `TODO.md`.
  - Supprimer les ambiguïtés "actif vs legacy" dans les parcours opératoires.

---

## 2) Exécution J4 (prochaines 2 semaines)

- [ ] **T-04 — Initialisation contrôlée J4 sur PostgreSQL en environnement de référence**
  - Initialiser PostgreSQL sur un dataset représentatif recrawlé.
  - Exécuter un recrawl complet sur environnement cible avec PostgreSQL (pas de migration SQLite).
  - Produire un rapport d'initialisation avec PostgreSQL (durée, volume, incidents, rollback readiness).

- [ ] **T-05 — Validation de performance post-bascule**
  - Rejouer le benchmark PostgreSQL sur endpoints critiques et comparer à la baseline historique SQLite.
  - Vérifier le respect des seuils P95 annoncés avec PostgreSQL.
  - Publier les résultats dans `docs/` avec conclusion explicite (OK / NOK) et intégration de PostgreSQL.

- [ ] **T-06 — Renforcement CI dual DB**
  - Rendre obligatoire le passage du job dual DB avant merge.
  - Ajouter collecte d'artefacts minimaux en échec (logs API/tests) avec PostgreSQL.
  - Documenter le chemin de diagnostic rapide en cas de pipeline rouge avec PostgreSQL.

- [ ] **T-07 — Drill de rollback J4**
  - Simuler un incident post-migration avec PostgreSQL.
  - Exécuter le rollback complet avec chronométrage et intégration de PostgreSQL.
  - Capitaliser la procédure réelle dans `docs/operations/EXPLOITATION.md` avec PostgreSQL.

---

## 3) Préparation J5 (qualité & observabilité)

- [ ] **T-08 — Définir les SLI/SLO opérationnels minimum**
  - Disponibilité API, latence P95, taux d'erreurs, temps de recovery.
  - Seuils d'alerte + responsables + fréquence de revue.

- [ ] **T-09 — Pack de tests critiques "release gate"**
  - API smoke critique avec PostgreSQL.
  - Non-régression frontend structurelle avec PostgreSQL.
  - Vérification DB explain / requêtes clés avec PostgreSQL.
  - Exécution via une commande unique documentée avec PostgreSQL.

- [ ] **T-10 — Observabilité minimale exploitable**
  - Standardiser logs applicatifs (format, niveau, corrélation) avec PostgreSQL.
  - Définir 1 dashboard santé + 1 vue incidents avec PostgreSQL.
  - Définir la procédure d'escalade en cas de dérive avec PostgreSQL.

---

## 4) Dette documentaire à résorber

- [ ] **T-11 — Nettoyage docs historiques vs référence active**
  - Marquer explicitement les documents legacy avec PostgreSQL.
  - Ajouter un index "où trouver la vérité" dans `docs/` avec PostgreSQL.
  - Réduire les doublons roadmap/projet/todo avec PostgreSQL.

- [ ] **T-12 — Gouvernance de preuve**
  - Chaque item clos doit pointer vers: commande exécutée, artefact, commit.
  - Remplacer tout marqueur implicite par une preuve vérifiable avec PostgreSQL.

---

## Définition de terminé (DoD) pour chaque tâche

- [ ] Une preuve d'exécution est versionnée (log, JSON, capture, rapport).
- [ ] Les impacts doc sont propagés aux fichiers de référence.
- [ ] Un risque principal et son plan de mitigation sont notés.
- [ ] La tâche est traçable dans l'historique Git (commit clair).

---

## Notes de pilotage

- Priorisation: **fiabilité > migration > confort**.
- Pas de nouvelle feature produit tant que T-01 à T-07 ne sont pas clôturées.
- Revue hebdo obligatoire des KPI (pipeline, flakiness, perf, recovery).
