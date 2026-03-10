# TODO OpenIndex — suite post-commando (J4 -> J5)

## Objectif

Passer d'une **readiness J4 documentée** à une **exécution J4 pilotée par preuves**, puis enclencher J5 (qualité & observabilité) avec critères de sortie mesurables.

---

## 1) Priorités immédiates (Semaine en cours)

- [ ] **T-01 — Clôturer CMD-12 (checklist release commando) avec preuves**
  - Vérifier CI verte sur `sqlite` + `postgresql`.
  - Vérifier dry-run migration et journal versionné.
  - Vérifier bench comparatif publié.
  - Vérifier rollback relu par un pair.
  - Mettre à jour `CHANGELOG.md` pour le lot de clôture.

- [ ] **T-02 — Décision formelle Go/No-Go J4**
  - Appliquer les critères de `docs/phases/J4_MIGRATION.md`.
  - Rédiger la décision dans un compte-rendu daté dans `docs/`.
  - Si No-Go: lister précisément les écarts bloquants et le plan de correction.

- [ ] **T-03 — Figer la baseline technique J4**
  - Confirmer le backend DB par défaut (`sqlite` ou `postgresql`) dans la doc principale.
  - Aligner `README.md`, `README.stack.md`, `ROADMAP.md` et ce `TODO.md`.
  - Supprimer les ambiguïtés "actif vs legacy" dans les parcours opératoires.

---

## 2) Exécution J4 (prochaines 2 semaines)

- [ ] **T-04 — Migration contrôlée J3 -> J4 en environnement de référence**
  - Exécuter le dry-run sur un dataset représentatif.
  - Exécuter la migration réelle sur environnement cible.
  - Produire un rapport de migration (durée, volume, incidents, rollback readiness).

- [ ] **T-05 — Validation de performance post-bascule**
  - Rejouer le benchmark SQLite vs PostgreSQL sur endpoints critiques.
  - Vérifier le respect des seuils P95 annoncés.
  - Publier les résultats dans `docs/` avec conclusion explicite (OK / NOK).

- [ ] **T-06 — Renforcement CI dual DB**
  - Rendre obligatoire le passage du job dual DB avant merge.
  - Ajouter collecte d'artefacts minimaux en échec (logs API/tests).
  - Documenter le chemin de diagnostic rapide en cas de pipeline rouge.

- [ ] **T-07 — Drill de rollback J4**
  - Simuler un incident post-migration.
  - Exécuter le rollback complet avec chronométrage.
  - Capitaliser la procédure réelle dans `docs/operations/EXPLOITATION.md`.

---

## 3) Préparation J5 (qualité & observabilité)

- [ ] **T-08 — Définir les SLI/SLO opérationnels minimum**
  - Disponibilité API, latence P95, taux d'erreurs, temps de recovery.
  - Seuils d'alerte + responsables + fréquence de revue.

- [ ] **T-09 — Pack de tests critiques "release gate"**
  - API smoke critique.
  - Non-régression frontend structurelle.
  - Vérification DB explain / requêtes clés.
  - Exécution via une commande unique documentée.

- [ ] **T-10 — Observabilité minimale exploitable**
  - Standardiser logs applicatifs (format, niveau, corrélation).
  - Définir 1 dashboard santé + 1 vue incidents.
  - Définir la procédure d'escalade en cas de dérive.

---

## 4) Dette documentaire à résorber

- [ ] **T-11 — Nettoyage docs historiques vs référence active**
  - Marquer explicitement les documents legacy.
  - Ajouter un index "où trouver la vérité" dans `docs/`.
  - Réduire les doublons roadmap/projet/todo.

- [ ] **T-12 — Gouvernance de preuve**
  - Chaque item clos doit pointer vers: commande exécutée, artefact, commit.
  - Remplacer tout marqueur implicite par une preuve vérifiable.

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
