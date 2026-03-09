# ROADMAP OpenIndex (mise à jour mars 2026)

## Vision

Industrialiser OpenIndex pour un usage régulier en environnement SMB volumineux, en sécurisant la chaîne : ingestion -> API -> visualisation -> exploitation.

## Phase J3 (actuelle) — Stabilisation SQLite

### Réalisé
- API FastAPI opérationnelle avec endpoints de consultation.
- Frontend statique connecté à l’API.
- Monitoring WebSocket basique.
- Endpoint d’analyse SQL (`/api/db-explain`).
- Déploiement image-first (`docker-compose.j3.yml`).

### À finaliser
- Renforcer les tests automatiques API/front.
- Durcir la fiabilité crawler en exécution longue.
- Standardiser les checklists d’exploitation.

## Phase J4 (prochaine) — Consolidation PostgreSQL

- Rebasculer le backend données principal vers PostgreSQL.
- Stabiliser le schéma et la stratégie d’indexation.
- Ajuster les jobs CI/CD autour de la cible J4.
- Préparer stratégie de migration depuis SQLite J3.

## Phase J5 — Qualité et observabilité

- Couverture de tests (unitaires/intégration) mesurée.
- Dashboards d’observabilité (santé API, crawl, volume, erreurs).
- Process de release plus strict (DoD + checklist publication).
