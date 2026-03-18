# ROADMAP OpenIndex (J4 validé — mars 2026)

## Vision

Industrialiser OpenIndex pour un usage régulier en environnement SMB volumineux, en sécurisant la chaîne : ingestion -> API -> visualisation -> exploitation.

## Phases

## Phase J1 (historique) — Kickoff opérationnel

### Objectifs J1
- Cadrer les priorités de sprint et les responsabilités.
- Rendre la documentation de pilotage totalement alignée.
- Mettre sous contrôle les points critiques de fiabilité (tests/sauvegarde).

### Sorties attendues J1
- Baseline documentaire stable et versionnée.
- TODO priorisé avec critères de done explicites.
- Plan de passage J1 -> J2 validé.

## Phase J2 (historique) — Fiabilisation

- Renforcer les tests API/front essentiels.
- Formaliser procédures d’incident sur la base active.
- Clarifier les workflows CI utiles et déprécier les parcours legacy.

## Phase de stabilisation initiale (historique)

- Exploitation robuste initiale de la stack API + frontend avant bascule PostgreSQL.
- Optimisation des performances de consultation.
- Durcissement des exécutions longues côté crawler.

## Phase J4 — Consolidation PostgreSQL (validée)

- Opérer le backend de données principal en PostgreSQL avec vérification de la disponibilité et stabilité.
- Stabiliser le schéma et la stratégie d’indexation dans PostgreSQL.
- Exécuter des recrawls complets sur zones de test avec PostgreSQL.
- Décision `Go` documentée le `2026-03-18`.

## Phase J5 (prochaine) — Qualité et observabilité

- Couverture de tests mesurée et suivie.
- Dashboards de santé et alerting.
- Processus de release strict (DoD + checklist publication).
- Préparer la configuration multi-repository et la segmentation des sources de crawl.
- Faire converger l'UI finale vers une console opératoire active, centrée sur le crawl réel et l'exploitation.
- Concevoir un explorateur de fichiers double panneau et une page dédiée aux traitements des artefacts.
