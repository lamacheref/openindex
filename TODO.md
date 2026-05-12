# TODO OpenIndex — Refonte selon PROJET.md

## Objectif

**Implémenter les 5 phases définies dans PROJET.md** avec un ordre de priorité clair pour la préproduction :
1. Indexeur efficace (Phase 1)
2. UI admin (Phase 4)  
3. UI Utilisateur sans authentification (archivage + suppression)

---

## 1) Priorité Critique — Indexeur Efficace (Phase 1)

### T-INDEX-01 — Refonte complète du système d'indexation
- [ ] **Scrutation périodique** : Scheduler configurable (22h-6h)
- [ ] **Multi-espaces SMB** : Configuration de plusieurs partages distincts
- [ ] **Files différenciées** : Queue rapide (<200Mo) et queue lente (≥200Mo)
- [ ] **Hashage xxHash** : Remplacer SHA256 par xxHash pour performance
- [ ] **Détection changements** : Mode incrémentiel avec hash + timestamps
- [ ] **Gestion des ordures** : Détection automatique (*.tmp, ~*, Thumbs.db)
- [ ] **Base PostgreSQL** : Schéma optimisé avec tables smb_spaces, directories, files
- [ ] **Tests de charge** : Validation avec 166k+ fichiers
- [ ] **Documentation** : Guide d'administration de l'indexation

### T-INDEX-02 — Optimisation et monitoring
- [ ] **Métriques temps réel** : Vitesse d'indexation, erreurs, files traitées
- [ ] **Health checks** : Endpoints de santé pour le crawler
- [ ] **Gestion des erreurs** : Queue retry pour fichiers verrouillés
- [ ] **Performance** : Optimisation des requêtes PostgreSQL
- [ ] **Logs structurés** : Format JSON pour tous les composants

---

## 2) Priorité Haute — UI Administrateur (Phase 4.1)

### T-ADMIN-01 — Tableau de bord admin
- [ ] **Métriques principales** : Fichiers indexés, espace utilisé, erreurs/warnings
- [ ] **Contrôles manuels** : Lancement/arrêt/pause/resume des indexations
- [ ] **Notifications temps réel** : WebSocket pour erreurs et warnings
- [ ] **Gestion des ordures** : Interface de validation pour fichiers problématiques
- [ ] **Dashboard Grafana** : Visualisation des métriques système

### T-ADMIN-02 — Gestion des espaces et configurations
- [ ] **Configuration SMB** : Interface pour ajouter/modifier/supprimer les espaces
- [ ] **Test de connexion** : Validation des credentials SMB
- [ ] **Scheduler** : Configuration des plages horaires d'indexation
- [ ] **Seuils configurables** : Taille files, patterns d'exclusion

### T-ADMIN-03 — Gestion des doublons avancée
- [ ] **Détection** : Hash + nom avec affichage groupé
- [ ] **Actions multiples** : Suppression individuelle/multiple + archivage
- [ ] **Corbeille 30 jours** : Traçabilité complète avec restauration
- [ ] **Confirmation requise** : Validation avant toute suppression

---

## 3) Priorité Moyenne — UI Utilisateur Simplifiée (Phase 4.3)

### T-USER-01 — Interface sans authentification
- [ ] **Navigation simple** : Explorateur de fichiers intuitif
- [ ] **Actions de base** : Archivage manuel et suppression de fichiers
- [ ] **Visualisation** : Aperçus pour images, PDF, bureautique
- [ ] **Recherche** : Recherche par nom et type de fichier
- [ ] **Design Material** : Interface moderne et responsive

### T-USER-02 — Archivage manuel simplifié
- [ ] **Sélection multiple** : Interface pour choisir les fichiers à archiver
- [ ] **Prévisualisation** : Espace requis et durée estimée
- [ ] **Progression** : Barre de progression pour les transferts
- [ ] **Raccourcis optionnels** : Création de liens symboliques

---

## 4) Priorité Moyenne — Archivage Intelligent (Phase 2)

### T-ARCH-01 — Système d'archivage robuste
- [ ] **Zones miroir** : Configuration multi-zones d'archivage
- [ ] **Workflow sécurisé** : Vérification hash avant/après copie
- [ ] **Retry automatique** : Max 5 tentatives avec logging détaillé
- [ ] **Gestion des erreurs** : Fichiers disparus, verrouillés, conflits
- [ ] **Traçabilité** : Logs complets des opérations d'archivage

### T-ARCH-02 — Archivage automatique (post-v1.0.0)
- [ ] **Règles configurables** : Type "archive" ET taille >500Mo
- [ ] **Exécution nocturne** : Avant indexation pour éviter surcharge
- [ ] **Raccourcis obligatoires** : Création automatique pour archivage auto
- [ ] **Validation admin** : Interface de validation des règles

## 5) Priorité Basse — Sommaires IA (Phase 3)

### T-AI-01 — Infrastructure IA locale
- [ ] **Ollama Docker** : Déploiement de Mistral-Nemo
- [ ] **Configuration** : 32GB RAM, 8 threads CPU
- [ ] **Tests performance** : Validation sur CPU seul sans GPU

### T-AI-02 — Génération asynchrone des sommaires
- [ ] **Site dynamique** : Base de données mise à jour lors de l'indexation
- [ ] **Statut "en cours"** : Affichage "traitement IA" si résumé non généré
- [ ] **Extraction texte** : Pour fichiers ≤100Mo
- [ ] **Base dédiée** : Tables ai_summaries, file_previews, summary_cache

### T-AI-03 — Visualisation multi-formats
- [ ] **OnlyOffice** : Intégration bureautique (Word, Excel, PowerPoint)
- [ ] **PDF.js** : Visualisation native PDF
- [ ] **Galerie images** : Thumbnails automatiques
- [ ] **Players HTML5** : Vidéos et audio natifs

### T-AI-04 — Interface Material Design
- [ ] **Cards visuelles** : Aperçus immédiats avec métadonnées
- [ ] **Recherche plein texte** : Dans sommaires IA et métadonnées
- [ ] **Export avancé** : PDF/Word des sommaires générés

---

## 6) Priorité Basse — Production et Exploitation (Phase 5)

### T-PROD-01 — Monitoring et observabilité
- [ ] **Métriques système** : CPU, RAM, disque utilisés par processus
- [ ] **Alerting** : Seuils d'alerte (espace disque, performances IA)
- [ ] **Logs centralisés** : Stack ELK avec rétention 30 jours
- [ ] **Dashboard Grafana** : Visualisation temps réel

### T-PROD-02 — Sauvegarde et recovery
- [ ] **Backup PostgreSQL** : pg_dump quotidien + WAL archiving
- [ ] **Backup configurations** : Paramètres SMB, modèles IA, certificats
- [ ] **Plan de recovery** : Procédures de restauration testées
- [ ] **RTO/RPO** : Objectifs de recovery time/point

### T-PROD-03 — Audit mensuel complet
- [ ] **Audit stockage** : Noms trop longs, espaces, profondeur PATH
- [ ] **Mistral PRO** : Compte configuré pour analyse RGPD
- [ ] **Détection données personnelles** : Scan intelligent des fichiers
- [ ] **Recherche credentials** : Mots de passe et informations sensibles
- [ ] **Rapport détaillé** : Recommandations et plan d'action

### T-PROD-04 — CI/CD et sécurité
- [ ] **Pipeline GitLab** : Build/test/déploiement automatisé
- [ ] **Blue-green deployment** : Déploiement sans coupure
- [ ] **Tests qualité** : Couverture >80% + tests E2E
- [ ] **Sécurité avancée** : Audit trails, rate limiting, vulnerability scanning

---

## Éléments Terminés à Revoir (Vérifié, Aligné, Testé)

### ✅ T-ARCH-04 — Correction SMB SMIDEN (Issue #85)
**Statut:** ✅ **VÉRIFIÉ** | **Alignement:** Phase 2.1 | **Tests:** À refaire selon nouvelle architecture
- [x] **Module gestionnaire** : `src/smb_mount_manager.py` - À aligner avec Phase 2
- [x] **Mode hybride** : Priorité montage SMB - Conserver pour Phase 2
- [ ] **Tests selon Phase 1** : Adapter les tests pour le nouvel indexeur
- [ ] **Documentation** : Mettre à jour selon PROJET.md

### ✅ T-AUTH-01 — Authentification PocketBase
**Statut:** ✅ **VÉRIFIÉ** | **Alignement:** Phase 4.2 | **Tests:** À intégrer
- [x] **Système complet** : JWT, rôles, permissions - Conserver pour Phase 4
- [ ] **Intégration AD** : Remplacer PocketBase par LDAP (Windows Server 2019)
- [ ] **Mapping permissions** : Basé sur groupes AD et permissions SMB
- [ ] **Fallback local** : Accès admin DB si AD indisponible

### ✅ T-ART-01/02/03 — Gestion des artefacts
**Statut:** ✅ **VÉRIFIÉ** | **Alignement:** Phase 4.4 | **Tests:** À adapter
- [x] **Doublons avancés** : Détection et actions - Intégrer dans Phase 4.3
- [x] **Filtres configurables** : Seuils et préférences - Adapter pour UI admin
- [ ] **Corbeille 30 jours** : Implémenter selon Phase 4.4
- [ ] **Interface utilisateur** : Simplifier pour Phase 4.3 (sans authentification)

---

## Définition de Terminée (DoD)

Pour chaque tâche T-XXX :
- [ ] Code implémenté et testé (unit tests + tests d'intégration)
- [ ] Documentation technique mise à jour (README, docstrings)
- [ ] Documentation opérationnelle mise à jour (EXPLOITATION.md)
- [ ] UI/UX cohérente avec Material Design
- [ ] Migrations DB créées si nécessaire
- [ ] Preuve de fonctionnement (logs, captures d'écran)
- [ ] Commit clair et traçable dans Git
- [ ] Alignement avec PROJET.md validé

---

## Notes de Pilotage

**Ordre de priorité préproduction :**
1. **T-INDEX-01/02** : Indexeur efficace (fondation)
2. **T-ADMIN-01/02/03** : UI admin (contrôle)
3. **T-USER-01/02** : UI utilisateur simplifiée (usage)
4. **T-ARCH-01/02** : Archivage intelligent (fonctionnalité)
5. **T-AI-01/02/03/04** : Sommaires IA (valeur ajoutée)
6. **T-PROD-01/02/03/04** : Production et exploitation (industrialisation)

**Dépendances clés :**
- T-INDEX-* requis avant T-ADMIN-* (données à afficher)
- T-ADMIN-* requis avant T-USER-* (infrastructure partagée)
- T-ARCH-* dépend de T-INDEX-* (données indexées)

**Architecture cible :**
- Approche "queue-based" pour toutes opérations lourdes
- Material Design pour toutes les interfaces
- PostgreSQL comme source de vérité unique
- WebSocket pour temps réel

---

*Dernière mise à jour : 2026-05-12*
*Aligné avec PROJET.md v5 phases*