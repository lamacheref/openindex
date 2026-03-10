# PROJET — OpenIndex

## Objectif

OpenIndex fournit un socle d’indexation de fichiers SMB avec restitution via API et interface web légère.

## Cap J1 (en cours)

Le **jour J1** marque le lancement du pilotage projet avec 4 priorités :

- Stabiliser le cadre documentaire (vision, roadmap, suivi, changelog).
- Poser un cadre d’exécution hebdomadaire clair (priorités + done).
- Conserver la stack technique actuelle comme base d’itération rapide.
- Préparer les conditions de passage en J2/J3 sans dette d’organisation.

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

## Trajectoire

- **J1** : cadrage et discipline d’exécution.
- **J2** : fiabilisation tests + exploitation.
- **J3** : stabilisation applicative renforcée.
- **J4** : consolidation PostgreSQL.
- **J5** : observabilité et qualité industrielle.
