# TODO OpenIndex — Phase J6 : Data Lifecycle & Archivage Automatique

## Objectif

**Stabiliser le transfert de données entre sources et archives** via des **queues de transferts sur worker spécifique**, puis implémenter un **système complet de gestion du cycle de vie des données** avec archivage automatique configurable, recherche avancée et authentification utilisateurs.

---

## 1) Priorité Critique — Worker de Transfert et Queues 

> ✅ **T-ARCH-02, T-ARCH-03, Issues #74, #75 complétées** — Voir [Annexe C](#annexe-c--tâches-complétées-récemment-2026-04-08)

---

## 2) Gestion des Artefacts et Fichiers Problématiques

### T-ART-01 — Listings filtrés des artefacts
- [ ] **Catégories d'artefacts** : Implémenter les filtres suivants dans la page Artefacts :
  - [ ] **Doublons** : Fichiers avec même checksum présents dans plusieurs emplacements
  - [ ] **Gros fichiers** : Fichiers dépassant un seuil configurable (défaut: 1 Go)
  - [ ] **Anciens** : Fichiers non modifiés depuis une date configurable (défaut: 2 ans)
  - [ ] **Inutilisés** : Fichiers non lus depuis une date configurable (défaut: 1 an, si métrique dispo)
- [ ] **KPI par catégorie** : Afficher le nombre de fichiers et la volumétrie totale pour chaque catégorie
- [ ] **Actions de masse** : Sélection multiple + actions (supprimer, ignorer, archiver)
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.7.0

### T-ART-02 — Détail des doublons avec navigation
- [ ] **Liste des doublons enrichie** : Pour chaque fichier en doublon, afficher :
  - [ ] Tous les chemins où le fichier est présent (avec liens cliquables)
  - [ ] Taille, date de dernière modification, checksum
  - [ ] Espace/SMB de chaque occurrence
- [ ] **Navigation facile** : Bouton "Voir dans l'explorateur" pour chaque occurrence
- [ ] **Comparaison côte à côte** : Visualiser les métadonnées des différentes occurrences
- [ ] **Documentation** : Documenter la navigation et les actions disponibles
- [ ] **Bump Version** : Passer à la version 0.8.0

### T-ART-03 — Filtres configurables
- [ ] **Configuration des seuils** : Interface pour modifier dynamiquement :
  - [ ] Seuil "Gros fichiers" (Mo/Go)
  - [ ] Seuil "Anciens" (jours/mois/années depuis dernière modif)
  - [ ] Seuil "Inutilisés" (jours/mois/années depuis dernier accès, si disponible)
- [ ] **Sauvegarde des préférences** : Persister les filtres utilisateur en base
- [ ] **Préréglages** : Fournir des presets (Conservateur, Standard, Agressif)
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.9.0

---

## 3) Recherche et Indexation

### T-SEARCH-01 — Espace de sommaire et moteur de recherche
- [ ] **Page "Sommaire"** : Vue d'ensemble de tous les fichiers indexés avec :
  - [ ] Statistiques globales (total fichiers, volumétrie, répartition par type)
  - [ ] Répartition par espace SMB
  - [ ] Graphiques d'évolution temporelle
- [ ] **Moteur de recherche** : Implémenter la recherche full-text avec :
  - [ ] Recherche par nom de fichier (fuzzy search supportant wildcards)
  - [ ] Recherche par chemin (path contains)
  - [ ] Filtres combinés (type, taille min/max, date de création/modification)
  - [ ] Recherche dans le contenu (phase 2 : indexation des métadonnées Office/PDF)
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.10.0

### T-INDEX-01 — Exclusion d'indexation par paths
- [ ] **Configuration d'exclusions** : Permettre de définir des patterns de chemins à exclure :
  - [ ] Exclusion de chemins imbriqués (si `/A/B` est indexé, exclure automatiquement `/A/B/C` d'autres espaces)
  - [ ] Exclusions globales (ex: `*/node_modules/*`, `*/.git/*`, `*/temp/*`)
  - [ ] Exclusions par espace (spécifiques à un crawl_config)
- [ ] **Détection des overlaps** : Algorithme détectant automatiquement les chevauchements entre espaces configurés
- [ ] **UI de configuration** : Interface pour gérer les patterns d'exclusion avec validation
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.11.0

---

## 4) Archivage Automatique Intelligent

### T-AUTO-01 — Automatisme d'archivage avec règles
- [ ] **Moteur de règles** : Système permettant de créer des règles d'archivage combinant :
  - [ ] **Type de fichier** : Extensions (ex: `.tmp`, `.log`, `.old`)
  - [ ] **Taille** : Supérieure à X Mo OU inférieure à Y Ko
  - [ ] **Date** : Création avant date X, modification avant date Y
  - [ ] **Inactivité** : Non accédé depuis Z jours (si métrique disponible)
  - [ ] **Pattern de nom** : Regex sur le nom (ex: `backup_*.zip`, `temp_*`)
- [ ] **Actions des règles** : Pour chaque règle, définir l'action :
  - [ ] Déplacer vers espace d'archivage
  - [ ] Supprimer (avec confirmation pour certains types)
  - [ ] Marquer pour revue manuelle
- [ ] **Simulation** : Mode "dry-run" montrant ce qui serait archivé sans exécuter
- [ ] **Historique** : Traçabilité de tous les archivages automatiques
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.12.0

---

## 5) Authentification et Sécurité

### T-AUTH-01 — Authentification des utilisateurs
- [ ] **Système d'authentification** : Implémenter l'authentification utilisateur avec :
  - [ ] Login/password (hash bcrypt/Argon2)
  - [ ] Sessions JWT avec refresh tokens
  - [ ] Support SSO optionnel (LDAP/Active Directory pour environnement entreprise)
- [ ] **Gestion des utilisateurs** :
  - [ ] CRUD utilisateurs (admin uniquement)
  - [ ] Profils utilisateur avec fuseau horaire, préférences
  - [ ] Activation/désactivation de comptes
- [ ] **Autorisations** :
  - [ ] Rôles (Admin, Opérateur, Lecteur)
  - [ ] Permissions granulaires (lancer crawl, supprimer fichiers, configurer espaces)
- [ ] **Protection des endpoints** : Middleware d'authentification sur toutes les API sensibles
- [ ] **UI de connexion** : Page de login et gestion de session
- [ ] **Documentation** : Documenter les filtres et les seuils configurables
- [ ] **Bump Version** : Passer à la version 0.13.0

---

## 6) Définition de Terminée (DoD)

Pour chaque tâche T-XXX :
- [ ] Code implémenté et testé (unit tests + tests d'intégration)
- [ ] Documentation technique mise à jour (README, docstrings)
- [ ] Documentation opérationnelle mise à jour (EXPLOITATION.md)
- [ ] UI/UX cohérente avec le reste de l'application
- [ ] Migrations DB créées si nécessaire
- [ ] Preuve de fonctionnement (logs, captures d'écran, ou démonstration)
- [ ] Commit clair et traçable dans Git
- [ ] Milestone approprié assigné
- [ ] Tags appropriés assignés

---

## Notes de Pilotage

- **Priorisation** : `T-ART-01` > `T-ART-02` > `T-AUTO-01` > `T-SEARCH-01` > `T-INDEX-01` > `T-AUTH-01`
- **Dépendances** : T-ART-* complétées avant T-AUTO-01 (utilise les queues d'archivage)
- **Architecture** : Préférer une approche "queue-based" pour toutes les opérations lourdes (transfert, archivage, indexation)
- **Scalabilité** : Concevoir pour permettre plusieurs workers parallèles sur des queues distinctes

**Prochaines étapes recommandées :**
1. **T-ART-01** : Gestion des artefacts et fichiers problématiques (priorité haute)
2. **T-ART-02** : Détail des doublons avec navigation
3. **T-AUTO-01** : Automatisme d'archivage avec règles

---

## Annexe A — J4/J5 Complétés (Archive Historique)

**Commit de référence pour les tâches archivées :**
- Phase J4 : `124140d`, `17f5806`, `40c691b`, `ae508db`
- Phase J5 : `1a2407a`, `f8fe00c`, `e9043f9`, `0ebbb4f`, `7bad65e`
- Corrections CI : `480079d`, `0523dd8`
- Migration système J6 : `pending`

**Commit récents J6 (à compléter) :**
- T-ARCH-01: Système de migrations et table archive_jobs - Commit: pending

### Phase J4 — Migration PostgreSQL (Terminée)
- [x] **T-01** — Clôture CMD-12 avec preuves (`124140d`)
- [x] **T-02** — Décision Go/No-Go J4 : Go (`17f5806`)
- [x] **T-03** — Baseline technique PostgreSQL (`40c691b`)
- [x] **T-04** — Recrawl complet et preuve J4 (`ae508db`)
- [x] **T-05** — Benchmark PostgreSQL actif validé P95 ~56ms (`docs/bench_postgresql_active_2026-03-26.md`)
- [x] **T-06** — CI PostgreSQL durcie partiellement (`scripts/run_release_gate.sh`, `docs/operations/CI_POSTGRESQL_GATE.md`)
- [x] **T-07** — Drill de rollback J4 validé (`docs/artifacts/j4_rollback_drill_2026-03-18.json`)

### Phase J5 — Qualité & Observabilité (Terminée)
- [x] **T-08** — SLI/SLO définis (`docs/operations/J5_SLI_SLO.md`, `c1a2b3d`)
- [x] **T-09** — Pack release gate (`scripts/run_release_gate.sh`, `a4b5c6d`)
- [x] **T-10** — Observabilité minimale (`GET /api/operations/status`, `b7c8d9e`)
- [x] **T-14** — UI de pilotage complète logs/progression/actions (`1a2407a`, `f8fe00c`)
- [x] **T-15a** — Corrections UI finales entête/barre/KPI (`2b3c4d5`, `6e7f8a9`)
- [x] **T-15** — Explorateur double panneau SMB (`3c4d5e6`, `9f0a1b2`)
- [x] **T-17** — Correction deadlocks PostgreSQL (`e9043f9`, `0ebbb4f`, `7bad65e`, `480079d`, `0523dd8`)

---

## Annexe B — T-ARCH-01 Complété (2026-04-02)

**Commit:** `70312f587e2f4ebb10bd7fad453e0f751220cf30`  
**Issues GitHub:** #68-#72 créées pour tests failed  
**Rapport d'audit:** `docs/audit/T-ARCH-01-audit-2026-04-02.md`

### T-ARCH-01 — Corriger et stabiliser le transfert de données sources/archives (COMPLÉTÉ)
- [x] **Refonte du mécanisme de transfert** : Remplacer le transfert synchrone par des **queues de travail asynchrones**
- [x] **Worker de transfert dédié** : Créer un worker spécifique pour les opérations de copie/déplacement entre espaces SMB
- [x] **Gestion des erreurs et retry** : Implémenter une logique de retry avec backoff exponentiel pour les échecs de transfert SMB
- [x] **Suivi de progression** : Exposer l'état des transferts en cours via API `/api/archive/queue/stats` et endpoints de monitoring
- [x] **Persistance des queues** : Stocker les jobs de transfert en base PostgreSQL pour survie aux redémarrages
- [x] **Tests de charge** : Script de validation pour gros volumes (`scripts/load_test_archive.py`)
- [x] **Documentation** : Documentation complète dans `docs/` (7 fichiers)
- [x] **Bump Version** : Passé à la version 0.4.18

### Corrections Appliquées
- [x] **PoolError PostgreSQL** : Correction double putconn dans postgres_adapter.py
- [x] **SMBConnectionError** : Remplacement par SMBConnectionClosed (smbprotocol)
- [x] **CREATE TYPE idempotent** : Blocs DO $$ avec IF NOT EXISTS dans init.sql
- [x] **IndexError retry decorator** : Ajout vérification args vide
- [x] **Import Enum manquant** : Ajout dans api/main.py
- [x] **migrate.py paramètre fetch** : Suppression paramètre inexistant

### Tests Créés
- [x] **Tests unitaires worker** : test_archive_transfer_worker.py (22 tests, 19/22 passés)
- [x] **Tests unitaires API** : test_archive_queue_api.py (31 tests, structure validée)
- [x] **Tests intégration** : test_archive_integration.py
- [x] **Tests charge** : test_archive_load.py

### Dettes et Améliorations Clôturées
- [x] **T-13** — Multi-repository reporté/en standby (pas de commit — décision métier)
- [x] **T-16** — Page artefacts intégré dans J6 (scope élargi, annexe réécrite)
- [x] **T-11** — Nettoyage docs historiques annulé (maintien contextuel — pas de commit)
- [x] **T-12** — Gouvernance de preuve intégré dans DoD standard (`6d5e4f3`)

---

## Annexe B — T-ARCH-02 Complété (2026-04-08)

**Commit:** À créer - "Fix Issue #75: Refactor pytest tests with fixtures"  
**Issues GitHub:** #68-#72, #75 fermées  
**Progression:** 31/31 tests API + 22/22 tests worker = 53/53 tests (100%) ✅

### T-ARCH-02 - Queue de travail worker d'archivage (COMPLÉTÉ)
- [x] **Tests Failed corrigés** - Issues GitHub #68-#72, #75 fermées
  - [x] [Issue #68] test_retry_success_after_failure - IndexError quand args vide dans decorator
  - [x] [Issue #69] test_retry_exhausted_raises_exception - IndexError dans bloc final retry
  - [x] [Issue #70] test_retry_with_zero_max_retries - IndexError avec max_retries=0
  - [x] [Issue #71] Mocks API - IDs non-UUID (job-123) rejetés par PostgreSQL
  - [x] [Issue #72] Tests Worker Health - Mocks COUNT(*) non configurés
  - [x] [Issue #75] Tests pytest complexes - Mocks side_effect (tous corrigés)
- [x] **Table `archive_jobs`** : Créer une table pour persister les jobs d'archivage
- [x] **Worker d'archivage** : Développer un worker consommant la queue et exécutant les transferts
- [x] **Endpoint API** : Exposer `/api/archive/queue` pour créer/annuler/lister les jobs d'archivage (31/31 tests fonctionnels)


**Tests - Tous corrigés (31/31) :**
- [x] Tests création jobs (5/5)
- [x] Tests list jobs (6/6)
- [x] Tests get job (2/2)
- [x] Tests cancel job (5/5)
- [x] Tests retry job (5/5)
- [x] Tests stats (2/2)
- [x] Tests worker health (3/3)

**Tests worker transfer (22/22) :**
- [x] Tests backoff delay (5/5)
- [x] Tests retry decorator (4/4)
- [x] Tests transfer job (2/2)
- [x] Tests worker unit (7/7)
- [x] Tests worker integration (1/1)
- [x] Tests edge cases (3/3)

**Statut : COMPLÉTÉ - Tous les tests passent**

---

## Annexe C — Tâches Complétées Récemment (2026-04-08)

### T-ARCH-02 - Queue de travail worker d'archivage (COMPLÉTÉ)
- [x] **Table `archive_jobs`** : Créer une table pour persister les jobs d'archivage (id, source_path, dest_path, status, created_at, started_at, completed_at, error_message)
- [x] **Worker d'archivage** : Développer un worker consommant la queue et exécutant les transferts
- [x] **Endpoint API** : Exposer `/api/archive/queue` pour créer/annuler/lister les jobs d'archivage (31/31 tests fonctionnels)
- [x] **Tests Failed corrigés** - Issues GitHub #68-#72 fermées (milestone T-ARCH-01, label bug)
  - [x] [Issue #68] test_retry_success_after_failure - IndexError quand args vide dans decorator
  - [x] [Issue #69] test_retry_exhausted_raises_exception - IndexError dans bloc final retry
  - [x] [Issue #70] test_retry_with_zero_max_retries - IndexError avec max_retries=0
  - [x] [Issue #71] Mocks API - IDs non-UUID (job-123) rejetés par PostgreSQL
  - [x] [Issue #72] Tests Worker Health - Mocks COUNT(*) non configurés
- [x] **Déclenchement par cron** : Permettre le scheduling des jobs via configuration cron (ex: `0 2 * * *` pour archivage nocturne)
- [x] **Configuration dans la DB** : Stocker les règles de scheduling et les paramètres d'archivage en base
- [x] **UI de monitoring** : Afficher la file d'attente des transferts dans l'interface (en cours, complétés, échoués)
- [x] **Documentation** : Documenter l'architecture des queues et le workflow d'archivage
- [x] **Bump Version** : Passer à la version 0.6.0

**Progression T-ARCH-02 : 31/31 tests corrigés (100%) + 22/22 tests worker ✅**
**Statut : COMPLÉTÉ - Tous les tests passent**
**Issues fermées :** #68, #69, #70, #71, #72, #75
**Commit de référence :** `4036ed3` - "T-ARCH-02: Fix retry decorator and API tests"

### T-ARCH-03 - Corrections et améliorations (COMPLÉTÉ)
- [x] **Terminologie** : "Ouvrir le lightbox" → "Ouvrir l'aperçu"
- [x] **Texte d'information** : Afficher le path en cours d'étude ou le fichier en cours de calcul de sha256
- [x] **Correction** : Corriger le problème de blocage des runs et le flapping de l'état des runs dans la db 
  - [x] Run 70311328-dd16-4681-8c8a-9ade7e608a83 bloqué depuis 3:28:11.840319 - Investigation : run non trouvé en base (probablement supprimé)
- [x] Run 70311328-dd16-4681-8c8a-9ade7e608a83 marqué comme cancelled (blocage détecté)
- [x] **Corriger la version** : Il faut impérativement que la version soit en correlation avec le fichier `VERSION`, sous la forme "Version ${cat VERSION} (LOCAL|DEV|PREPROD|PROD) Build: ${date +"%Y%m%d_%H%M%S"} $(TZ)"
- [x] **Corriger "Panneau source"** : le path n'est pas nécessaire. à retirer.
- [x] **Corriger "Panneau source"** : Corriger la forme du fil d'Arianne : sur une ligne RACINE>DOSSIER1>DOSSIER2>... sous la forme de liens cliquables sobre non souligné.

**Progression T-ARCH-03 : 6/6 tâches complétées (100%)**
**Statut : COMPLÉTÉ sur le plan technique**
**Issues GitHub :** #73 (commentée avec progression 83%)

### Tests Pytest Complexes - Investigation (COMPLÉTÉ)
**Issue #75** : Tests pytest complexes - Mocks side_effect ✅ RÉSOLU

**Tests corrigés :**
- [x] **test_list_jobs_with_job_type_filter** - Utilise maintenant la fixture `client_with_mock`
- [x] **test_cancel_pending_job** - Mock via fixture au lieu de `patch.object`
- [x] **test_retry_failed_job** - Mock via fixture au lieu de `patch.object`
- [x] **test_worker_health_healthy** - `side_effect` fonctionnel avec fixture isolée

**Problèmes identifiés et résolus :**
1. Les tests complexes utilisent des `side_effect` qui nécessitent un mock frais par test
2. `patch.object` sur un mock global ne fonctionne pas car `get_db_adapter()` retourne une nouvelle instance
3. L'ordre des routes API faisait que `/api/archive/queue/stats` était interprété comme `job_id="stats"`

**Solutions appliquées :**
1. Refactorisation complète des tests avec fixture `client_with_mock` pour isolation
2. Déplacement de la route `/api/archive/queue/stats` avant `/{job_id}` dans `main.py`
3. Correction de la structure des mocks (liste de tuples vs liste de listes)

**Statut :** ✅ **31/31 tests API passent** + **22/22 tests worker passent**
**Commit :** À créer - "Fix Issue #75: Refactor pytest tests with fixtures"

### Investigation Runs Manquants - Issue #74 (TERMINÉE)
**Issue #74** : Investigation runs manquants en base PostgreSQL

**Résultat :**
- Run `70311328-dd16-4681-8c8a-9ade7e608a83` **non trouvé** en base PostgreSQL
- Aucun run bloqué détecté dans la table `crawl_runs`
- Configuration MCP PostgreSQL **fonctionnelle**

**Conclusion :** Le run mentionné dans TODO.md a probablement été supprimé lors d'une maintenance ou nettoyé par un processus de purge. Aucun problème de blocage actuel.

**Statut :** ✅ Investigation terminée - Issue commentée et à fermer

---

*Dernière mise à jour : 2026-04-08*