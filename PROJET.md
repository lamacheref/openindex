# PROJET — OpenIndex

## Objectifs du projet

OpenIndex fournit un socle d'indexation de fichiers SMB avec restitution via API et interface web légère.

## Phase 1 - Indexation intelligente des espaces SMB

### 1.1 Protocole d'indexation en 2 phases

L'indexation suit un protocole strict en deux passages pour garantir l'intégrité de la base et minimiser la charge sur le serveur SMB :

**Phase A — Enregistrement des répertoires (BFS depuis la racine)**
- Parcours l'arborescence en **largeur (BFS)** depuis le répertoire racine
- Pour chaque répertoire rencontré, inscription immédiate dans la table `directories` avec :
  - `space_id`, `parent_path`, `name`, `full_path`, `depth`
  - Relation hiérarchique (`parent_id`) pour reconstruction de l'arbre
- Descente couche par couche jusqu'à épuisement de la profondeur maximale
- Aucun fichier n'est indexé pendant cette phase

**Phase B — Indexation des fichiers (bottom-up, des feuilles vers la racine)**
- Récupération de tous les répertoires connus triés par **profondeur décroissante** (des plus profonds à la racine)
- Pour chaque répertoire (du plus profond au moins profond) :
  1. Lister les fichiers présents
  2. Pour chaque fichier, vérifier s'il existe déjà en base sur les 4 métadonnées : **nom + taille + date_création + date_modification**
  3. Si les 4 métadonnées correspondent → fichier considéré inchangé, ignoré (pas de réindexation, pas de re-hashage)
  4. Si une métadonnée diffère → fichier considéré changé ou nouveau → indexation complète avec xxHash

### 1.2 Files de traitement différenciées
- **Queue rapide** (fast) : fichiers <200Mo, hashage xxHash immédiat pendant la Phase B
- **Queue lente** (slow) : fichiers ≥200Mo, hashage xxHash différé (job séparé, traitement nocturne)
- **Queue retry** : fichiers verrouillés/en utilisation, réessai automatique (max 5 tentatives, backoff exponentiel)

### 1.3 Collecte des métadonnées
**Fichiers :**
- Nom, type (extension), taille, dates création/modification
- Hash **xxHash** (64-bit) pour unicité et détection des changements
- Chemin complet, relation avec le dossier parent (`directory_id`) et l'espace SMB (`space_id`)
- Statuts : doublon, corbeille (garbage), supprimé

**Dossiers :**
- Métadonnées complètes : nom, chemin, profondeur, dates, taille cumulée
- Structure hiérarchique via `parent_id` et `depth`
- Calcul de taille récursive (somme des fichiers enfants)

### 1.4 Gestion intelligente des contenus
- **Raccourcis/liens symboliques** : détection et traitement spécifique (à implémenter)
- **Déchets** : marquage automatique des patterns suspects (*.tmp, ~*, Thumbs.db, .DS_Store, *.bak, *.swp)
- **Fichiers déplacés/renommés** : détectés comme nouveaux via hash + chemin (si hash identique mais chemin différent → potentiel déplacement)

### 1.5 Base de données PostgreSQL
```sql
smb_spaces (id, name, host, share, domain_zone, connection_username, connection_password, is_active, created_at, updated_at, last_crawled_at, total_files_indexed, total_bytes_indexed)

directories (id, space_id, parent_id, name, path, parent_path, depth, file_count, directory_count, total_size, created_at, updated_at)
-- UNIQUE(space_id, path)

indexed_files_optimized (id, space_id, directory_id, path, name, extension, size, hash_xxh64, hash_sha256, last_modified, created_at, updated_at, is_duplicate, duplicate_of, is_garbage, is_deleted, deleted_at)
-- UNIQUE(space_id, path)
```

### 1.6 Stratégie de mise à jour
- **Mode incrémentiel (Phase B)** : comparaison sur (nom + taille + created_at + modified_at) → si identique, fichier ignoré
- **Mode complet** : réindexation intégrale avec re-hashage xxHash
- **Réindexation manuelle** : disponible pour l'administrateur via `POST /api/indexer/jobs`
- **Volume cible** : 166k+ fichiers, évolutivité verticale/horizontale

### 1.7 Scheduler
- **Scrutation périodique** : exécution configurable (cron), par défaut hors heures de travail (22h-6h)
- **Gestion multi-espaces** : un job par espace SMB avec sa propre configuration et son propre historique
- **Surveillance incrémentielle** : détection des changements entre deux scrutations consécutives

## Phase 2 - Archivage intelligent des fichiers

### 2.1 Configuration multi-zones d'archivage
- **Zones miroir** : une zone d'archivage par espace source
- **Structure préservée** : hiérarchie identique à la source
- **Permissions** : mêmes droits que les espaces de départ

### 2.2 Workflow de copie sécurisée
```python
1. Vérifier hash source vs base de données
2. Si incohérent : stop et informer utilisateur
3. Si cohérent : copier vers archive
4. Vérifier hash destination
5. Si échec : retry (max 5 fois) avec logging détaillé
6. Si succès : créer raccourci optionnel (symlinks recommandés)
7. Supprimer fichier source
```

### 2.3 Gestion des erreurs et conflits
- **Fichier disparu** : erreur loguée + notification utilisateur
- **Fichiers verrouillés** : queue retry après redémarrage serveur
- **Conflits de noms** : choix utilisateur (renommer/écraser)
- **Logging complet** : fichier de logs + notifications UI

### 2.4 Modes d'archivage
**Archivage manuel (prioritaire) :**
- Sélection multi-fichiers avec prévisualisation
- Option raccourci configurable par utilisateur
- Annulation possible par initiateur ou admin

**Archivage automatique (post-v1.0.0) :**
- Critères : type "archive" ET taille >500Mo
- Exécution avant indexation nocturne
- Raccourcis obligatoires

### 2.5 Base de données étendue
```sql
archive_operations (id, user_id, space_id, file_id, operation_type, status, created_at)
archive_zones (id, space_id, archive_path, active)
archive_logs (id, operation_id, step, status, message, timestamp)
```

### 2.6 Raccourcis et traçabilité
- **Format recommandé** : liens symboliques (symlinks)
- **Métadonnées préservées** : compatibles avec indexation existante
- **Traçabilité complète** : qui, quand, pourquoi en base

## Phase 3 - Sommaires IA intelligents

### 3.1 Infrastructure IA locale
- **Modèle recommandé** : Mistral-Nemo via Ollama Docker (excellent français)
- **Configuration** : 32GB RAM, 8 threads CPU sur serveur Dual Xeon 32 coeurs
- **Optimisation CPU** : modèles quantifiés pour performance maximale sans GPU

### 3.2 Génération asynchrone des sommaires
- **Site dynamique** : basé sur base de données mise à jour lors de l'indexation
- **Traitement IA** : asynchrone, en arrière-plan
- **Statut "en cours"** : affichage "en cours de traitement IA" si résumé non généré
- **Déclenchement** : automatique sur détection de changements
- **Profondeur** : analyse séquentielle de l'arborescence complète
- **Extraction texte** : pour résumés intelligents des fichiers ≤100Mo

### 3.3 Format HTML Material Design
```html
<div class="summary-card">
  <div class="file-preview">
    <!-- Thumbnails, aperçus intégrés -->
  </div>
  <div class="file-metadata">
    <h3>filename.ext</h3>
    <p class="ai-summary">Résumé généré par IA...</p>
    <span class="details">taille | date | type</span>
  </div>
</div>
```

### 3.4 Visualisation multi-formats
- **Bureautique** : OnlyOffice intégré (Word, Excel, PowerPoint)
- **PDF** : PDF.js natif web
- **Images** : galerie avec thumbnails automatiques
- **Vidéos** : player HTML5 avec formats supportés
- **Audio** : player web avec waveforms

### 3.5 Base de données dédiée
```sql
ai_summaries (id, directory_id, content, status, generated_at, model_version)
-- status: 'completed', 'processing', 'pending'
file_previews (id, file_id, thumbnail_path, preview_type, generated_at)
summary_cache (id, file_hash, content, last_updated)
```

### 3.6 Gestion des erreurs et sécurité
- **Fichiers protégés** : warning admin + métadonnées minimales
- **Retry automatique** : max 3 tentatives avec logging détaillé
- **Timeout** : passage au fichier suivant sans blocage
- **Notifications** : alertes admin pour fichiers confidentiels

### 3.7 Interface utilisateur repensée
- **Design Material** : cards visuelles avec aperçus immédiats
- **Recherche plein texte** : dans sommaires IA et métadonnées
- **Navigation fluide** : entre dossiers et sommaires
- **Export avancé** : PDF/Word des sommaires générés

## Phase 4 - Interface utilisateur complète

### 4.1 Backoffice administrateur
- **Tableau de bord complet** : métriques fichiers indexés, espace utilisé, erreurs/warnings
- **Contrôles manuels** : lancement/arrêt/pause/resume des indexations
- **Notifications temps réel** : WebSocket pour erreurs et warnings en direct
- **Gestion des ordures** : suppression auto (Thumbs.db, .DS_Store) + validation admin autres

### 4.2 Authentification Active Directory
- **Protocole LDAP** : integration simplifiée Windows Server 2019
- **Mapping permissions** : basé sur groupes AD et permissions SMB
- **Fallback local** : accès admin DB si AD indisponible
- **Sessions sécurisées** : tokens avec expiration

### 4.3 Espace utilisateur personnel
- **Filtrage automatique** : fichiers accessibles selon permissions AD/SMB
- **Accès restreint** : uniquement fichiers de l'utilisateur connecté
- **Pas de délégation** : accès personnel uniquement
- **Interface adaptée** : vue simplifiée pour utilisateurs finaux

### 4.4 Gestion avancée des doublons
- **Détection** : hash + nom (hash inclus dans calcul)
- **Affichage groupé** : liste avec chemins complets et métadonnées
- **Actions multiples** : suppression individuelle/multiple + déplacement archive
- **Corbeille 30 jours** : traçabilité complète avec restauration possible
- **Confirmation requise** : validation avant toute suppression

### 4.5 Architecture technique
```javascript
Frontend: React + Material-UI + WebSocket
Backend: FastAPI + WebSocket support
Auth: LDAP + fallback DB
Real-time: WebSocket pour notifications temps réel
```

### 4.6 Sécurité et audit
- **Réseau MPLS** : HTTP suffisant (HTTPS post-production v1.5.0)
- **Audit complet** : logs détaillés des actions utilisateurs/admin
- **Sessions** : gestion tokens avec expiration automatique
- **Séparation** : accès distinct admin/utilisateurs

## Phase 5 - Production et exploitation

### 5.1 Monitoring et observabilité
- **Métriques système** : CPU, RAM, disque utilisés par les processus
- **Alerting** : seuils d'alerte (espace disque, performances IA, erreurs)
- **Health checks** : endpoints de santé pour chaque composant
- **Dashboard Grafana** : visualisation temps réel des métriques

### 5.2 Gestion des logs centralisée
- **Logs structurés** : format JSON pour tous les composants
- **Agrégation ELK** : Elasticsearch + Logstash + Kibana
- **Rétention** : politique de conservation des logs (30 jours)
- **Recherche avancée** : filtrage et analyse des logs

### 5.3 Sauvegarde et recovery
- **Backup PostgreSQL** : pg_dump quotidien + WAL archiving
- **Backup configurations** : paramètres SMB, modèles IA, certificats
- **Plan de recovery** : procédures de restauration testées
- **RTO/RTO** : objectifs de recovery time/point

### 5.4 Scalabilité et performance
- **Load testing** : tests de charge avec 166k+ fichiers
- **Cache Redis** : optimisation des requêtes fréquentes
- **Indexation optimisée** : PostgreSQL tuning et partitions
- **Horizontal scaling** : possibilité de multi-instances

### 5.5 Documentation utilisateur
- **Guide admin** : procédures backoffice, dépannage, monitoring
- **Guide utilisateur** : navigation, recherche, gestion doublons
- **API docs** : Swagger/OpenAPI pour développeurs
- **Playbooks** : procédures incident response

### 5.6 CI/CD et déploiement
- **Pipeline GitLab** : build/test/déploiement automatisé
- **Blue-green deployment** : déploiement sans coupure
- **Rollback automatique** : retour arrière sur échec
- **Environment staging** : pré-production identique

### 5.7 Sécurité avancée
- **Audit trails** : logs détaillés des accès et modifications
- **Rate limiting** : protection contre abus API
- **Input validation** : validation stricte des entrées utilisateur
- **Vulnerability scanning** : scans de sécurité réguliers

### 5.8 Tests et qualité
- **Tests unitaires** : couverture >80% du code métier
- **Tests intégration** : validation flux complets
- **Tests E2E** : scénarios utilisateur automatisés
- **Performance tests** : benchmarks réguliers

### 5.9 Audit mensuel complet
- **Audit de stockage** : détection points d'achoppement
  - Noms de fichiers trop longs (>255 caractères)
  - Espaces et caractères spéciaux dans les noms
  - Profondeur de PATH excessive (>260 caractères Windows)
  - Structures de dossiers non conformes
- **Audit sécurité RGPD** : analyse intelligente des fichiers
  - **Mistral PRO** : compte configuré pour analyse avancée
  - Détection automatique des données personnelles
  - Recherche de credentials et mots de passe
  - Identification documents sensibles (bancaires, médicaux)
- **Rapport détaillé** : recommandations et corrections
- **Plan d'action** : priorisation des corrections
- **Historique** : suivi des audits mensuels et évolutions

## Phase 6 — Déploiement LXC & Validation Industrielle de l'Indexeur

### 6.1 Infrastructure LXC (substitution à Docker)
- **Abandon de Docker** : remplacement de l'orchestration Docker Compose par un déploiement LXC natif
- **Conteneurs LXC dédiés** : un conteneur par service (postgresql, api, frontend, worker-indexer, worker-archive, scheduler)
- **Réseau LXC bridge** : communication inter-conteneurs via réseau LVC natif
- **Stockage** : montage de partages SBM directement dans le conteneur worker-indexer
- **Persistance** : données PostgreSQL sur volume LXC lié à l'hôte

### 6.2 Installateur automatisé
- **Script unique** : `scripts/install_lxc.sh` — déploiement complet en une commande
- **Prérequis vérifiés** : détection et installation des dépendances (lxc, lxc-config, smbclient, etc.)
- **Configuration interactive** : wizard de paramétrage (IP, chemins SMB, credentials)
- **Idempotence** : installation reproductible, sans effets de bord
- **Mise à jour** : support du upgrade des conteneurs sans perte de données

### 6.3 Validation complète de l'indexeur
- **Tests d'intégration réels** : validation du pipeline complet sur PostgreSQL + SMB simulé
- **Correction des anomalies résiduelles** :
  - Erreur de syntaxe `_handle_file_conflict()` (`backend/src/workers/indexer_worker.py:1078`)
  - Alignement des `max_attempts` (5 essais partout)
  - Tests Priority 4 avec vrai mock DB
- **Benchmark capacitaire** : validation avec 166k+ fichiers, mesure de performance
- **DoD finale** : PR + version bump 0.7.0 + tag

### 6.4 Documentation opérationnelle
- **Guide d'installation LXC** : procédure complète pas-à-pas
- **Guide d'exploitation** : démarrage, arrêt, monitoring des conteneurs
- **Procédure de recovery** : restauration après incident
- **Runbook** : opérations courantes (sauvegarde, mise à jour, diagnostic)

### 6.5 Schéma cible
```
Hôte LXC (Debian/Ubuntu)
├── lxc-openindex-pgsql    # PostgreSQL 16
├── lxc-openindex-api      # FastAPI (uvicorn)
├── lxc-openindex-frontend # Nginx (frontend statique)
├── lxc-openindex-worker   # Indexeur SMB + workers
└── lxc-openindex-pb       # PocketBase (auth)
       Réseau bridge lxcbr0 (10.0.3.0/24)
```

---

## Cap J6 (phase en cours — Déploiement LXC & Validation)

La **phase J6** marque le basculement vers une infrastructure LXC industrialisée :

- Installateur LXC automatisé, testé et documenté.
- Indexeur validé fonctionnellement et en charge.
- Docker déprécié comme socle de déploiement (maintenu pour compatibilité temporaire).
- DoD de la version 0.7.0 complétée.

## Cap J5 (historique — Qualité et observabilité)

Le **jour J5** marque la phase de qualité et observabilité industrielle :

- Couverture de tests mesurée et suivie.
- Dashboards de santé et alerting.
- Processus de release strict (DoD + checklist publication).

## Cap J1-J4 (historique)

- Stabiliser le cadre documentaire (vision, roadmap, suivi, changelog).
- Poser un cadre d'exécution hebdomadaire clair (priorités + done).
- Conserver la stack technique actuelle comme base d'itération rapide.
- Préparer les conditions de passage en J2/J3 sans dette d'organisation.
- Fiabilisation tests + exploitation.
- Stabilisation applicative renforcée.
- Consolidation PostgreSQL.

## Périmètre actuel

- Indexeur SMB : queues fast/slow/retry ✅, xxHash ✅, incrémentiel ✅
- **Écarts constatés** :
  - Alimentation de la table `directories` ❌ (schéma existant, jamais peuplée par le worker d'indexation)
  - Protocole 2 phases (BFS dossiers → bottom-up fichiers) ❌ (implémente un DFS mono-phase)
  - Table cible `indexed_files_optimized` ❌ (le worker écrit dans la table legacy `files`)
  - Contrôle d'existence sur 4 métadonnées (nom+taille+created+modified) ❌ (seulement hash+size+mtime)
  - Gestion des raccourcis/symlinks ❌ (non implémentée)
- Archivage avec queue de jobs persistants et worker dédié ✅
- Authentification PocketBase ✅
- API FastAPI, frontend statique, détection de doublons ✅

## Livrables disponibles

- Worker d'indexation SMB (`backend/src/workers/indexer_worker.py`) — **refonte protocolaire en cours**
- Scheduler cron (`backend/src/workers/indexer_scheduler.py`)
- API indexeur (`backend/src/api/indexer_router.py`)
- Client SMB (`backend/src/utils/crawl_utils.py`)
- API FastAPI (`backend/src/api/main.py`)
- Frontend (`frontend/index.html`)
- Déploiement via Docker Compose (`docker-compose.yml`) — **en cours de remplacement par LXC**
- Installateur LXC automatisé (`scripts/install_lxc.sh`) — **à construire**

## Trajectoire

- **J1** : cadrage et discipline d'exécution.
- **J2** : fiabilisation tests + exploitation.
- **J3** : stabilisation applicative renforcée.
- **J4** : consolidation PostgreSQL.
- **J5** : observabilité et qualité industrielle.
- **J6** : déploiement LXC & validation de l'indexeur (phase en cours).
