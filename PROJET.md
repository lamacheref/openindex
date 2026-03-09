# PROJET — OpenIndex

## Objectif

OpenIndex fournit un socle d’indexation de fichiers SMB avec restitution via API et interface web légère.

## Périmètre actuel

- Collecte et inventaire des fichiers/répertoires.
- Exposition des données via API FastAPI.
- Consultation, recherche et visualisation depuis frontend statique.
- Détection de doublons et indicateurs globaux.

## Livrables disponibles

- Crawler Python SMB (base existante + historique d’optimisations).
- API FastAPI (`src/api/main.py`).
- Frontend (`frontend/index.html`).
- Déploiement J3 via Docker Compose (`docker-compose.j3.yml`).

## Contraintes traitées

- Déploiement simplifié en environnement Docker.
- Base SQLite en J3 pour itérations rapides.
- Exposition d’un endpoint de diagnostic SQL pour analyse.

## Suite prévue

- J4 : consolidation PostgreSQL.
- J5 : observabilité et renforcement qualité.
