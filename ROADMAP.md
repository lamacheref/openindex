# ROADMAP OpenIndex (J6 — avril 2026)

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
- Formaliser procédures d'incident sur la base active.
- Clarifier les workflows CI utiles et déprécier les parcours legacy.

## Phase de stabilisation initiale (historique)
- Exploitation robuste initiale de la stack API + frontend avant bascule PostgreSQL.
- Optimisation des performances de consultation.
- Durcissement des exécutions longues côté crawler.

## Phase J4 — Consolidation PostgreSQL (validée)
- Opérer le backend de données principal en PostgreSQL avec vérification de la disponibilité et stabilité.
- Stabiliser le schéma et la stratégie d'indexation dans PostgreSQL.
- Exécuter des recrawls complets sur zones de test avec PostgreSQL.
- Décision `Go` documentée le `2026-03-18`.
- Lot correctif opérateur clôturé le `2026-03-19` : progression runtime fiable, cohérence UI renforcée, réconciliation des runs `cancelling`, purge WebSocket des clients fermés, abandon explicite du prototype `estimate-{hash}`.

## Phase J5 (prochaine) — Qualité et observabilité
- Couverture de tests mesurée et suivie.
- Dashboards de santé et alerting.
- Processus de release strict (DoD + checklist publication).
- Reprendre le backlog principal sur recrawl réel, performance PostgreSQL et observabilité, sans rouvrir le lot correctif opérateur clôturé.
- Préparer la configuration multi-repository et la segmentation des sources de crawl.
- Faire converger l'UI finale vers une console opératoire active, centrée sur le crawl réel et l'exploitation.
- Concevoir un explorateur de fichiers double panneau et une page dédiée aux traitements des artefacts.

## Phase J6 — Data Lifecycle & Archivage Automatique (en cours)
### Objectifs J6
- Stabiliser le transfert de données entre sources et archives via queues de travail.
- Implémenter un système complet de gestion du cycle de vie des données.
- Mettre en place l'archivage automatique configurable.
- Sécuriser l'application avec un système d'authentification robuste.

### Livraisons J6
- **T-ARCH-01** (✅ complété 2026-04-02) : Archive Queue System
  - Queue de jobs persistants en PostgreSQL
  - Transfer Worker avec retry exponentiel + jitter
  - API REST complète (7 endpoints)
  - Monitoring temps réel et health checks
  - Suite de tests complète (22+31+4 tests)
  - Documentation technique complète

- **T-ARCH-02** (✅ complété 2026-04-08) : Scheduling et configuration
  - ✅ Déclenchement par cron des jobs d'archivage
  - ✅ Configuration des règles en base de données
  - ✅ UI de monitoring des files d'attente
  - ✅ 53/53 tests passés (31 API + 22 worker)
  - ✅ Issues #68-#72, #75 fermées

- **T-ARCH-03** (✅ complété 2026-04-08) : Corrections UI et stabilisation
  - ✅ Terminologie et textes d'information corrigés
  - ✅ Correction blocage runs et flapping état
  - ✅ Version alignée avec fichier VERSION
  - ✅ Corrections panneau source (breadcrumb cliquable)

- **T-ARCH-04** (✅ complété 2026-04-09) : Correction SMB SMIDEN (Issue #85)
  - ✅ Architecture hybride : montage SMB + fallback programmatique
  - ✅ Module `smb_mount_manager.py` avec gestion dynamique des montages
  - ✅ Auto-remontage après timeout 30min d'inactivité
  - ✅ API endpoints `/api/smb-mounts` pour monitoring et contrôle
  - ✅ Résout Issues #80 et #85 (credentials SMB incorrects)

- **T-AUTH-01** (✅ complété 2026-04-14) : Authentification des utilisateurs
  - ✅ Intégration PocketBase pour l'authentification
  - ✅ Pages de login et accès refusé fonctionnelles
  - ✅ Protection des routes avec règles granulaires
  - ✅ Gestion des sessions JWT
  - ✅ Interface d'administration PocketBase configurée

### Prochaines livraisons prévues
- **T-ART-01/02/03** : Gestion des artefacts et doublons
- **T-SEARCH-01** : Moteur de recherche et sommaire
- **T-AUTO-01** : Archivage automatique intelligent
- **T-AUTH-02** : Améliorations de sécurité (2FA, logs, rate limiting)
