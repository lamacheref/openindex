# Archives consolidées

Ce dossier `Archives/` est désormais l'unique emplacement des archives projet.

## Nettoyage effectué

- Suppression de l'ancien dossier `archives/` (minuscule).
- Suppression des scripts et artefacts historiques qui ne servent plus au développement courant (debug, tests manuels anciens, interface Streamlit obsolète, rapport HTML daté).
- Conservation dans `Archives/` des documents de cadrage utiles :
  - `PROJET.MD`
  - `PROPOSITION.md`
  - `PROPOSITION_WS.md`

## Consolidation technique (root allégé)

Les variantes techniques redondantes ont été archivées dans `Archives/legacy/` :

- `Archives/legacy/docker/` : anciens fichiers `docker-compose.*.yml`
- `Archives/legacy/requirements/` : anciens `requirements.*.txt`
- `Archives/legacy/deploy/` : anciens scripts de déploiement Docker

Le dépôt racine expose désormais uniquement :

- `docker-compose.yml` (compose canonique)
- `requirements.txt` (dépendances unifiées)
- `deploy.sh` (script unique de déploiement Docker)
