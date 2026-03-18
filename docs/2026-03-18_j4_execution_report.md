# Rapport d'exécution J4 PostgreSQL

Date: 2026-03-18
Périmètre: exécution contrôlée J4 sur cible SMB `\\172.16.252.34\Public\SMIDEN`

## Résumé

L'exécution contrôlée J4 a été rejouée sur une base PostgreSQL dédiée de validation `openindex_j4_validation`.

Résultat synthétique:
- Initialisation + recrawl: OK
- Benchmark performance 3 runs: OK après correction API
- Drill de rollback: OK techniquement
- Validation du rollback: validée par le responsable opérationnel

## 1. Initialisation PostgreSQL + recrawl

Artefact:
- `docs/artifacts/j4_init_recrawl_2026-03-18.json`

Résultat:
- Statut: `completed`
- Répertoire de départ: `\\172.16.252.34\Public\SMIDEN`
- Répertoires explorés: `8`
- Fichiers trouvés: `5`
- Taille totale: `251755` octets
- Doublons: `0`
- Erreurs: `0`
- Durée: environ `3.0` secondes

Conclusion:
- Le critère "Initialisation PostgreSQL + recrawl complet sans erreur bloquante avec journal" est satisfait sur l'environnement de validation exécuté le 2026-03-18.

## 2. Benchmark PostgreSQL

Artefact:
- `docs/artifacts/bench_sqlite_vs_postgresql.json`

Méthode:
- `3` runs successifs
- `30` échantillons par run et par endpoint
- Endpoints: `/api/stats`, `/api/files?limit=5&offset=0`
- Warm-up non mesuré: `5` requêtes avant chaque série
- Exécution contre l'application FastAPI réelle via ASGI sur la base `openindex_j4_validation`

Résultats PostgreSQL finaux:
- `/api/stats` P95 par run: `0.55`, `0.49`, `0.42`
- `/api/files` P95 par run: `0.71`, `0.51`, `0.52`

Conclusion:
- Le critère J4 de stabilité sur 3 runs successifs est satisfait sur l'environnement de validation.
- Cause principale identifiée et corrigée pendant l'exécution:
  - l'API ouvrait une nouvelle connexion PostgreSQL à chaque requête et revalidait la connexion sur chaque appel
  - correction appliquée: cache de l'adapter + pool de connexions côté API

## 3. Drill de rollback

Artefact:
- `docs/artifacts/j4_rollback_drill_2026-03-18.json`

Méthode:
- Dump de `openindex_j4_validation`
- Suppression et recréation de la base
- Restauration complète
- Vérification des volumes avant/après

Résultat:
- Comptes avant: `12,7,5,0`
- Comptes après: `12,7,5,0`
- Restauration identique: `true`
- Durée du drill: `0.41` seconde

Conclusion:
- La procédure de rollback est reproductible techniquement sur la base de validation.
- La validation explicite a été assumée par le responsable opérationnel, faute de pair distinct disponible dans la collectivité.

## 4. État J4 au 2026-03-18

Critères:
- Performance stable sur 3 runs: `OK`
- Initialisation + recrawl journalisés: `OK`
- Rollback testé: `OK`
- Rollback validé par le responsable opérationnel: `OK`
- CI PostgreSQL de référence: tests locaux `OK`, statut CI hébergé non prouvé dans le dépôt

Décision opérationnelle:
- Le statut global reste `No-Go` tant que la validation pair du rollback et la preuve CI PostgreSQL hébergée ne sont pas closes.
