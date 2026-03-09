# Dossier projet (docs) — État courant

Ce dossier complète `../PROJET.md` avec une vue opérationnelle.

## Stack retenue aujourd’hui

- API : FastAPI
- UI : frontend statique HTML/JS
- Base : SQLite (J3)
- Déploiement recommandé : `docker-compose.j3.yml`

## Avancées marquantes

- API de consultation + stats + doublons.
- WebSocket de monitoring.
- Endpoint d’explication de plan SQL.
- Pipeline image J3 sur GitHub Actions.

## Points d’attention

- Coexistence d’artefacts legacy (Streamlit, anciens compose).
- Besoin de tests automatisés plus systématiques.
- Préparation migration J4 PostgreSQL.
