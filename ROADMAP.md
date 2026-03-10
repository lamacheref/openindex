# ROADMAP OpenIndex (J1 relancé — mars 2026)

## Vision

Industrialiser OpenIndex pour un usage régulier en environnement SMB volumineux, en sécurisant la chaîne : ingestion -> API -> visualisation -> exploitation.

## Phase J1 (active) — Kickoff opérationnel

### Objectifs J1
- Cadrer les priorités de sprint et les responsabilités.
- Rendre la documentation de pilotage totalement alignée.
- Mettre sous contrôle les points critiques de fiabilité (tests/sauvegarde).

### Sorties attendues J1
- Baseline documentaire stable et versionnée.
- TODO priorisé avec critères de done explicites.
- Plan de passage J1 -> J2 validé.

## Phase J2 (prochaine) — Fiabilisation

- Renforcer les tests API/front essentiels.
- Formaliser procédures d’incident sur la base active.
- Clarifier les workflows CI utiles et déprécier les parcours legacy.

## Phase de stabilisation initiale (historique)

- Exploitation robuste initiale de la stack API + frontend avant bascule PostgreSQL.
- Optimisation des performances de consultation.
- Durcissement des exécutions longues côté crawler.

## Phase J4 — Consolidation PostgreSQL (active)

- Opérer le backend données principal en PostgreSQL.
- Stabiliser le schéma et la stratégie d’indexation.
- Exécuter des recrawls complets (sans migration SQLite) sur zones de test.

## Phase J5 — Qualité et observabilité

- Couverture de tests mesurée et suivie.
- Dashboards de santé et alerting.
- Processus de release strict (DoD + checklist publication).
