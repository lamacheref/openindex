# Protocole de pré-estimation volumétrique du crawl

## Objectif

Obtenir, avant le démarrage de l'exploration principale, une estimation la plus fidèle possible de la masse totale de données à traiter afin de rendre la progression opérateur réellement significative.

## Décision cible

Le moteur de crawl doit fonctionner en deux phases successives :

1. `Pré-estimation`
2. `Exploration et vérification d'intégrité`

La barre principale ne doit afficher un pourcentage de traitement fiable qu'après la fin de la phase `Pré-estimation`.

## Stratégie prioritaire

La stratégie prioritaire retenue est :

1. monter temporairement le partage SMB via CIFS sur l'hôte d'exécution ;
2. exécuter `du -sb` sur la racine cible ;
3. récupérer :
   - le volume total en octets ;
   - idéalement le nombre d'entrées par un parcours complémentaire si nécessaire ;
4. démonter le partage ;
5. démarrer l'exploration applicative avec cette baseline figée.

Cette approche donne une volumétrie en octets plus fidèle qu'une estimation opportuniste dérivée du crawl lui-même.

## Pré-requis techniques

- `cifs-utils` disponible sur l'hôte ou dans un worker dédié ;
- droits de montage CIFS ;
- gestion sécurisée des credentials via fichier temporaire ou secret ;
- répertoire de montage éphémère par run ;
- nettoyage garanti en cas d'erreur ou d'arrêt.

## Fallbacks acceptables

Si le montage CIFS n'est pas possible :

1. `smbclient-ng sizeof` sur la racine ciblée ;
2. parcours récursif SMB dédié ne faisant qu'inventorier tailles et compteurs, sans checksum ni écriture lourde ;
3. en dernier recours seulement, mode actuel avec indication explicite `volume en cours d'estimation`.

## Exigences d'interface

- afficher la phase courante : `Pré-estimation`, `Exploration`, `Vérification d'intégrité`, `Terminé`, `Arrêté`, `Erreur` ;
- afficher la baseline estimée seulement quand elle est stabilisée ;
- garder les files de traitement en diagnostic secondaire ;
- privilégier les indicateurs de progression cumulés :
  - dossiers découverts ;
  - fichiers découverts ;
  - volume inventorié ;
  - volume traité ;
  - gros fichiers détectés ;
  - backlog de vérification d'intégrité.

## Risques

- coût temporel initial supplémentaire avant le crawl ;
- dépendance système au montage CIFS ;
- divergence possible entre estimation et traitement réel si le partage change pendant l'exploration.

## Mitigations

- limiter la pré-estimation au périmètre exact du run ;
- tracer la date de baseline ;
- afficher qu'une exploration a démarré sur une volumétrie figée à `T0` ;
- conserver le fallback actuel si la pré-estimation échoue.
