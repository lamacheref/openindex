# TODO OpenIndex — Plan d'action : Refonte protocole indexeur (T-INDEX-R02)

**Objectif :** Mettre l'indexeur en conformité avec le protocole spec Phase 1 PROJET.md (BFS dossiers → bottom-up fichiers, table `indexed_files_optimized`, contrôle 4 métadonnées).

---

## Priorité 0 — Correctifs immédiats (avant toute refonte)

- [x] **Corriger la syntaxe** `_handle_file_conflict()` L.1078
  - `backend/src/workers/indexer_worker.py`
  - `'port': int(os.getenv('POSTGRES_PORT', 5432),` → `'port': int(os.getenv('POSTGRES_PORT', '5432')),`
- [x] **Aligner `max_attempts`** à 5 partout :
  - `backend/src/workers/indexer_worker.py` L.90
  - `backend/src/workers/archive_transfer_worker.py` L.25
  - `database/migrations/010_add_indexer_retries_table.sql` L.13
  - `backend/src/api/indexer_router.py` L.90
- [x] **Nettoyer les blocs `task_progress`** épars dans le code :
  - L.1143-1155 et L.1223-1234 dans `indexer_worker.py`
  - Ces blocs sont des notes de dev, pas du code exécutable

---

## Priorité 1 — Refonte du protocole d'indexation (T-INDEX-R02)

### 1a — Phase A : BFS des répertoires

- [x] **Réécrire `_crawl_recursive()`** en `_phase_a_bfs_directories()` (BFS)
  - Utilise `collections.deque` pour le parcours en largeur
  - Parcourir niveau par niveau (root → depth=1 → depth=2 → ...)
- [x] **Insérer chaque répertoire** dans la table `directories` :
  - `space_id`, `name`, `path`, `parent_path`, `depth`
  - UPSERT sur `UNIQUE(space_id, path)`
- [x] **Ne pas toucher aux fichiers** pendant cette phase
- [x] **Métriques** : nombre de répertoires découverts retourné et loggé

### 1b — Phase B : Bottom-up fichiers

- [x] **Récupérer les répertoires** classés par `depth DESC` :
  ```sql
  SELECT id, path, name FROM directories
  WHERE space_id = %s
  ORDER BY depth DESC
  ```
- [x] **Pour chaque répertoire** (du plus profond au moins profond) :
  - Lister les fichiers via `SMBClient.list_dir(repertoire_path)`
  - Ignorer les sous-répertoires (déjà traités en Phase A)
- [x] **Contrôle d'existence 4 métadonnées** :
  ```sql
  SELECT id FROM indexed_files_optimized
  WHERE path = %s AND name = %s AND size = %s
    AND created_at = %s AND last_modified = %s
  ```
  - Si trouvé → fichier inchangé, passer au suivant (pas de re-hashage)
  - Si non trouvé → fichier nouveau ou modifié → indexer
- [x] **Appliquer les files différenciées** :
  - Si size < 200Mo → hashage xxHash immédiat, insertion
  - Si size >= 200Mo → créer un job `slow` dédié
  - Si fichier verrouillé → queue retry (via `_add_file_to_retry`)

### 1c — Basculer vers `indexed_files_optimized`

- [x] **Ajouter `insert_file_optimized()`** dans `postgres_adapter.py` :
  - Cible : `indexed_files_optimized`
  - Colonnes : `space_id`, `directory_id`, `path`, `name`, `extension`, `size`,
    `hash_xxh64`, `hash_sha256`, `last_modified`, `is_garbage`, `is_deleted`
  - UPSERT sur `(space_id, path)`
- [x] **Ajouter `insert_files_batch_optimized()`** dans `postgres_adapter.py` :
  - Même cible, batch via `execute_values`
- [x] **Supprimer l'écriture legacy** dans la worker :
  - `_insert_file()` cible `indexed_files_optimized` (via `insert_file_optimized`)
  - `_flush_batch()` cible `indexed_files_optimized` (via `insert_files_batch_optimized`)
  - Plus d'écriture dans les tables `files` et `indexed_files`
- [x] **Contrôle 4 métadonnées inline** dans `_phase_b_bottom_up_files()`

### 1d — Finalisation

- [x] **Mettre à jour les statuts** : `space_id` utilisé dans les requêtes principales (`directories`, `indexed_files_optimized`), `config_id` conservé pour la compatibilité job
- [x] **Logs de progression** : Phase A log toutes les 500 entrées, Phase B log final avec nb ignorés/indexés
- [ ] **Tester le cycle complet** : nécessite PostgreSQL + SMB en runtime (hors session)

---

## Priorité 2 — Tests & Validation

- [ ] **Tests unitaires Phase A** : BFS directories, UPSERT, profondeur, déduction parent_id
- [ ] **Tests unitaires Phase B** : bottom-up, contrôle 4 métadonnées, fast/slow/retry queues
- [ ] **Tests unitaires `check_file_changed()`** : match 4 champs, mismatch partiel
- [ ] **Tests unitaires `insert_file()`** vers `indexed_files_optimized`
- [ ] **Tests d'intégration** : pipeline complet PostgreSQL + SMB simulé (mock SMB mais vraie DB)
- [ ] **Benchmark capacitaire** : `scripts/load_test_indexer.py` — 166k+ fichiers
- [ ] **Finaliser les tests Priority 4** avec vrai mock DB

---

## Priorité 3 — Déploiement LXC & Documentation

- [x] **T-LXC-01** : `scripts/install_lxc.sh` (installeur ProxmoxVE LXC complet)
- [ ] **T-LXC-03** : documentation opérationnelle
- [ ] **Version bump** : 0.6.23 → 0.7.0
- [ ] **Tag** : `v0.7.0`
- [ ] **PR** revue et mergée

---

## Définition de Terminé (DoD) T-INDEX-R02

- [x] Phase A BFS alimente `directories` avec hiérarchie complète
- [x] Phase B bottom-up indexe les fichiers feuilles → racine
- [x] Contrôle d'existence sur 4 métadonnées (name+size+created+modified)
- [x] Insertions dans `indexed_files_optimized` (plus `files` legacy)
- [x] Files différenciées fast/slow/retry fonctionnelles
- [x] Erreur syntaxe L.1078 corrigée
- [x] `max_attempts` aligné à 5
- [x] Blocs `task_progress` supprimés du code
- [ ] Tests unitaires passant (70+) — **Priorité 2**
- [ ] Tests d'intégration passant (pipeline complet) — **Priorité 2**
- [ ] Benchmark 166k+ fichiers validé — **Priorité 2**
- [x] `scripts/install_lxc.sh` créé
- [ ] Version 0.7.0 taguée — **Priorité 3**
