# ROADMAP OpenIndex (J6 — juillet 2026)

## Vision

Industrialiser OpenIndex pour un usage régulier en environnement SMB volumineux, en substituant Docker par une infrastructure LXC plus stable et en validant le bon bout-en-bout de l'indexeur.

## Phases

## Phases J1-J5 (historique)
- **J1** : Kickoff opérationnel, baseline documentaire, TODO priorisé.
- **J2** : Fiabilisation des tests API/front, procédures d'incident, CI.
- **J3** : Stabilisation applicative, exploitation robuste stack API + frontend PostgreSQL.
- **J4** : Consolidation PostgreSQL, recrawls complets, schéma stabilisé (validé 2026-03-18).
- **J5** : Qualité et observabilité, dashboards, DoD, release process.

## Phase J6 — Déploiement LXC & Validation Indexeur (en cours)

### Contexte
Docker Compose s'est révélé instable en préproduction. Cette phase remplace l'orchestration Docker par des conteneurs LXC natifs, plus légers et mieux adaptés à l'infrastructure cible. Elle valide également le fonctionnement de l'indexeur, qui est le cœur métier du projet.

### Objectifs J6
- Abandonner Docker comme socle de déploiement au profit de LXC.
- Fournir un installateur automatisé LXC complet et documenté.
- Valider l'indexeur SMB en conditions réelles (tests d'intégration, charge, correction des anomalies).
- Atteindre la version 0.7.0 avec DoD complétée.

### Lots J6

#### T-LXC-01 — Installateur LXC automatisé
- [ ] Script `scripts/install_lxc.sh` : déploiement complet en une commande
- [ ] Création des conteneurs : pgsql, api, frontend, worker, pocketbase
- [ ] Réseau bridge LXC, montage SMB, persistance des données
- [ ] Wizard de configuration interactive
- [ ] Idempotence et mise à jour supportées

#### T-LXC-02 — Validation de l'indexeur
- [ ] Correction de l'erreur de syntaxe dans `_handle_file_conflict()` (`backend/src/workers/indexer_worker.py:1078`)
- [ ] Alignement des `max_attempts` (5 tentatives partout)
- [ ] Finalisation des tests Priority 4 (mock DB)
- [ ] Tests d'intégration réels : pipeline complet PostgreSQL + SMB simulé
- [ ] Benchmark capacitaire avec 166k+ fichiers
- [ ] DoD : PR + version bump 0.7.0 + tag

#### T-LXC-03 — Documentation opérationnelle
- [ ] Guide d'installation LXC pas-à-pas
- [ ] Guide d'exploitation (démarrage, arrêt, monitoring)
- [ ] Procédure de recovery et runbook
- [ ] Mise à jour README.md, PROJET.md, ROADMAP.md

### Livraisons déjà disponibles (phases antérieures)
- **T-INDEX-01** (✅ 2026-05-18) : Indexeur SMB complet avec xxHash, files différenciées, scheduler cron, détection incrémentielle, garbage files, schéma PostgreSQL optimisé — 70+ tests unitaires
- **T-ARCH-01** (✅ 2026-04-02) : Archive Queue System avec worker dédié, retry exponentiel
- **T-ARCH-02** (✅ 2026-04-08) : Scheduling d'archivage, configuration, monitoring
- **T-ARCH-03** (✅ 2026-04-08) : Corrections UI et stabilisation
- **T-ARCH-04** (✅ 2026-04-09) : Architecture hybride montage SMB + fallback
- **T-AUTH-01** (✅ 2026-04-14) : Intégration PocketBase, login JWT, routes protégées
