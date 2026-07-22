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
L'audit du code a révélé 5 écarts majeurs entre la spec PROJET.md Phase 1 et l'implémentation de l'indexeur. Cette phase priorise la **refonte protocolaire de l'indexeur** avant le déploiement LXC, pour garantir un socle métier fiable.

### Objectifs J6
1. **Refondre l'indexeur** pour implémenter le protocole 2 phases (BFS dossiers → bottom-up fichiers).
2. **Basculer les insertions** de la table legacy `files` vers `indexed_files_optimized`.
3. **Alimenter la table `directories`** avec la hiérarchie complète.
4. **Valider** avec des tests d'intégration réels et un benchmark 166k+ fichiers.
5. Abandonner Docker pour LXC une fois l'indexeur validé.
6. Atteindre la version 0.7.0.

### Lots J6

#### T-INDEX-R02 — Refonte du protocole d'indexation (priorité #1)
- [ ] **Phase A — BFS directories** : réécrire `_crawl_recursive()` en BFS, insérer chaque répertoire dans `directories` avec `space_id`, `parent_path`, `depth`
- [ ] **Phase B — Bottom-up files** : récupérer les répertoires classés par profondeur décroissante, indexer les fichiers feuilles → racine
- [ ] **Contrôle d'existence 4 métadonnées** : étendre `check_file_changed()` pour comparer nom + taille + created_at + modified_at
- [ ] **Basculer vers `indexed_files_optimized`** : remplacer les INSERT dans `files` par des INSERT dans `indexed_files_optimized`
- [ ] **Correction syntaxe `_handle_file_conflict()`** (L.1078)
- [ ] **Alignement `max_attempts`** (5 partout)
- [ ] **Nettoyage des `task_progress`** épars (L.1143-1155 et L.1223-1234)
- [ ] **Tests adaptés** : mise à jour des tests unitaires mockés pour couvrir les 2 phases
- [ ] **Tests d'intégration** : pipeline complet PostgreSQL + SMB simulé
- [ ] **Benchmark** 166k+ fichiers

#### T-LXC-01 — Installateur LXC automatisé
- [ ] Script `scripts/install_lxc.sh` : déploiement complet en une commande
- [ ] Création des conteneurs : pgsql, api, frontend, worker, pocketbase
- [ ] Réseau bridge LXC, montage SMB, persistance des données
- [ ] Wizard de configuration interactive
- [ ] Idempotence et mise à jour supportées

#### T-LXC-03 — Documentation opérationnelle
- [ ] Guide d'installation LXC pas-à-pas
- [ ] Guide d'exploitation (démarrage, arrêt, monitoring)
- [ ] Procédure de recovery et runbook
- [ ] Mise à jour README.md, PROJET.md, ROADMAP.md

### Livraisons déjà disponibles (phases antérieures)
- **T-INDEX-01** (⚠️ partiel 2026-05-18) : Indexeur SMB avec xxHash, files différenciées, scheduler cron, détection incrémentielle, garbage files — **refonte protocolaire en cours (T-INDEX-R02)**
- **T-ARCH-01** (✅ 2026-04-02) : Archive Queue System avec worker dédié, retry exponentiel
- **T-ARCH-02** (✅ 2026-04-08) : Scheduling d'archivage, configuration, monitoring
- **T-ARCH-03** (✅ 2026-04-08) : Corrections UI et stabilisation
- **T-ARCH-04** (✅ 2026-04-09) : Architecture hybride montage SMB + fallback
- **T-AUTH-01** (✅ 2026-04-14) : Intégration PocketBase, login JWT, routes protégées
