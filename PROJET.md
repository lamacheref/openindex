# PROJET — OpenIndex

## Objectifs du projet

OpenIndex fournit un socle d'indexation de fichiers SMB avec restitution via API et interface web légère.

## Phase 1 - Indexation intelligente des espaces SMB

### 1.1 Scrutation périodique et multi-espaces
- **Scheduler configurable** : exécution hors heures de travail (22h-6h)
- **Surveillance incrémentielle** : détection des changements entre scrutations
- **Gestion multi-espaces** : configuration de plusieurs partages SMB distincts

### 1.2 Collecte des métadonnées
**Fichiers :**
- Nom, type, taille, dates création/modification
- Hash **xxHash** pour unicité et détection modifications
- Chemin complet et relation avec dossier parent

**Dossiers :**
- Métadonnées complètes (pas de hashage nécessaire)
- Structure hiérarchique avec auto-incrémentation
- Calcul de taille récursive

### 1.3 Files de traitement différenciées
- **Queue rapide** : fichiers <200Mo (hashage immédiat)
- **Queue lente** : fichiers ≥200Mo (traitement nocturne)
- **Queue retry** : fichiers verrouillés/en utilisation

### 1.4 Gestion intelligente des contenus
- **Raccourcis** : traités comme fichiers standards avec détection cible
- **Déchets** : marquage automatique des patterns suspects (*.tmp, ~*, etc.)
- **Fichiers déplacés/renommés** : détectés comme nouveaux via hash+chemin

### 1.5 Base de données PostgreSQL
```sql
smb_spaces (id, name, path, credentials, active)
directories (id, space_id, parent_id, name, full_path, created_at, modified_at, size)
files (id, space_id, directory_id, name, full_path, size, created_at, modified_at, hash_xxhash, status)
```

### 1.6 Stratégie de mise à jour
- **Mode incrémentiel** : comparaison hash + timestamps
- **Réindexation manuelle** : disponible pour l'administrateur
- **Volume cible** : 166k+ fichiers avec évolutivité

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

- Collecte et inventaire des fichiers/répertoires.
- Exposition des données via API FastAPI.
- Consultation, recherche et visualisation depuis frontend statique.
- Détection de doublons et indicateurs globaux.
- Indexation SMB complète avec files différenciées, xxHash, détection incrémentielle.
- Archivage avec queue de jobs persistants et worker dédié.
- Authentification PocketBase.

## Livrables disponibles

- Crawler Python SMB (base existante + historique d'optimisations).
- API FastAPI (`src/api/main.py`).
- Frontend (`frontend/index.html`).
- Déploiement via Docker Compose (`docker-compose.yml`) — **en cours de remplacement**.
- Installateur LXC automatisé (`scripts/install_lxc.sh`) — **à construire**.

## Trajectoire

- **J1** : cadrage et discipline d'exécution.
- **J2** : fiabilisation tests + exploitation.
- **J3** : stabilisation applicative renforcée.
- **J4** : consolidation PostgreSQL.
- **J5** : observabilité et qualité industrielle.
- **J6** : déploiement LXC & validation de l'indexeur (phase en cours).
