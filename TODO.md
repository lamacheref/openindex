# TODO.md

Ce fichier contient la liste des tâches à effectuer pour le projet OpenIndex, classées par ordre d'importance et organisées par phases.

## Tâches à effectuer

### Phase 1 : Préparation et Configuration (Date butoir : 2026-02-15) - ✅ **TERMINÉE**
- [x] 🛠️ **Configurer l'environnement de développement** : Installer Docker, SQLite, et Python pour le projet.
- [x] 📦 **Installer les bibliothèques nécessaires** : Ajouter les dépendances (`smbprotocol`, FastAPI, Streamlit).
- [x] 📄 **Créer le script de base pour le crawler SMB** : Développer le script avec pagination et indexation progressive.
- [x] 📜 **Finaliser la documentation technique** : Compléter les sections manquantes dans le fichier `PROJET.md` et s'assurer que toutes les spécifications techniques sont à jour.
- [x] 🔄 **Finaliser le crawler SMB** : Le crawler actuel ne scanne que le premier niveau (/SMIDEN/Technique), il doit parcourir récursivement toute l'arborescence (>2 To).
- [x] 🗄️ **Configurer la base de données SQLite** : Optimiser le schéma pour la grande volumétrie avec WAL mode et transactions par lots.
- [x] 🧪 **Tester le crawler avec grande volumétrie** : Valider les performances avec pagination et indexation progressive.

### Phase 2 : Développement du Crawler et de l'Interface (Date butoir : 2026-02-22) - ✅ **TERMINÉE**
- [x] 🔄 **Finaliser le crawler SMB récursif** : ✅ Crawler récursif complet avec multi-threading et queues
- [x] ⚡ **Optimiser les performances du crawler** : ✅ Multi-threading, reprise après interruption, gestion des erreurs
- [x] 📊 **Ajouter un état d'avancement** : ✅ Barre de progression et statistiques en temps réel
- [x] 🌐 **Créer l'interface web** : ✅ Interface Streamlit v2 avec onglets multiples
- [x] 📈 **Ajouter un tableau de bord statistique** : ✅ Métriques complètes et graphiques interactifs
- [x] 🔍 **Détecter et afficher les doublons** : ✅ Détection SHA-256 avec interface détaillée
- [x] 📥 **Ajouter des filtres par date/taille/type** : ✅ Filtres complets et recherche
- [x] 📤 **Exporter les inventaires en CSV** : ✅ Export des données et statistiques

### Phase 3 : Migration Technologique (Date butoir : 2026-03-19) - 🔄 **NOUVELLE APPROCHE**
- [ ] 🚀 **Analyse de faisabilité** : Évaluer migration Streamlit → React + FastAPI
- [ ] 🏗️ **Créer l'architecture FastAPI** : Migrer logique SMB vers API REST performante
- [ ] 🗄️ **Migrer vers PostgreSQL** : Base de données robuste pour multi-utilisateurs
- [ ] ⚛️ **Développer frontend React** : Interface moderne avec Material-UI
- [ ] 🐳 **Dockeriser l'application** : Déploiement simplifié et production-ready
- [ ] 🔄 **Intégration complète** : Tests E2E et validation fonctionnelle

### Phase 4 : Fonctionnalités Avancées (Date butoir : 2026-03-28) - � **REPORTÉE**
- [x] 🎯 **Interface avec streamlit-tree-select** : ✅ Arborescence interactive professionnelle
- [x] 👁️ **Visualisation de fichiers intégrée** : ✅ streamlit-elements pour documents, images, Excel
- [x] 🎨 **Panneau latéral moderne** : ⚠️ **À CORRIGER** : Panneau qui s'affiche en bas au lieu de la droite
- [ ] 📱 **Responsive design** : Adapter l'interface pour mobiles et tablettes
- [ ] 🔄 **Actions en temps réel** : Actions de crawl et visualisation sans rechargement
- [ ] 📊 **Visualisation avancée** : PDF viewer, lecteur audio/vidéo intégré
- [ ] 🗂️ **Gestion des favoris** : Marquer des dossiers/fichiers comme favoris
- [ ] 🔔 **Notifications système** : Alertes pour crawl terminé, erreurs, etc.

### Phase 4 : Déploiement et Production (Date butoir : 2026-03-05)
- [ ] 🗂️ **Déployer l'application dans un conteneur Docker** : Configuration Docker pour production
- [ ] 🚀 **Optimisation des performances** : Cache intelligent, indexation progressive
- [ ] 🔐 **Gestion des utilisateurs** : Authentification et permissions multi-utilisateurs
- [ ] 📈 **Monitoring avancé** : Logs, métriques, alertes de performance
- [ ] � **Mises à jour automatiques** : Système de mise à jour du crawler et interface

### Phase 5 : Maintenance et Évolution (Date butoir : 2026-03-10)
- [ ] 🧪 **Tests automatisés** : Suite de tests complète pour CI/CD
- [ ] 📚 **Documentation utilisateur** : Guide d'utilisation complet
- [ ] 🎯 **Analyse de l'utilisation** : Statistiques d'utilisation et optimisations
- [ ] 🔄 **Version 2.0** : Planification des fonctionnalités avancées

### Phase 3 : Fonctionnalités d'Archivage (Date butoir : 2026-02-28)
- [ ] 🗃️ **Implémenter le module d'archivage** : Développer le module pour copier les fichiers vers le NAS, vérifier les checksums, et supprimer les fichiers du cloud.
- [ ] 📅 **Ajouter l'archivage instantané et programmé** : Permettre l'archivage instantané ou planifié avec notifications.
- [ ] 🏷️ **Ajouter des tags personnalisés** : Permettre l'étiquetage des dossiers/fichiers pour une meilleure organisation.

### Phase 4 : Fonctionnalités Complémentaires (Date butoir : 2026-03-05)
- [ ] 📧 **Ajouter des notifications email** : Envoyer des alertes automatiques pour les archives et les erreurs.
- [ ] 🧪 **Implémenter des tests unitaires** : Créer des tests pour les modules critiques afin d'assurer la stabilité du code.
- [ ] 🔍 **Corriger les bugs signalés** : Résoudre les problèmes identifiés dans le suivi des bugs.

### Phase 5 : Déploiement et Tests Finaux (Date butoir : 2026-03-10)
- [ ] 🐳 **Déployer l'application dans un conteneur Docker** : Configurer et déployer l'application sur Proxmox avec gestion des volumes.
- [ ] 🧪 **Effectuer des tests finaux** : Valider toutes les fonctionnalités et optimiser les performances pour la grande volumétrie.
- [ ] 📦 **Préparer la prochaine version** : Finaliser les fonctionnalités prévues pour la prochaine release.

## Tâches terminées

| Date       | Commit    | Description                                                                 | Statut |
|------------|-----------|-----------------------------------------------------------------------------|--------|
| 2026-02-11 | `bdfd46d` | Ajout crawler SMB avec smbclient et nettoyage du code                    | ✅     |
| 2026-02-11 | `c654cf8` | Mise à jour du TODO.md avec hiérarchie, granularité et dates butoirs        | ✅     |
| 2026-02-11 | `3b23b5d` | Ajout des fichiers .clinerules et .roo/mcp.json                          | ✅     |
| 2026-02-11 | `cf8d598` | Ajout du fichier TODO.md et mise à jour des règles                     | ✅     |
| 2026-02-11 | `9f94586` | Mise à jour du README.md avec liens vers les fichiers .md                | ✅     |
| 2026-02-11 | `2194040` | Ajout des fichiers PROJET.md et ROADMAP.md                           | ✅     |
| 2026-02-11 | `22f3593` | Ajout des fichiers d'archives (PROJET.MD, PROPOSITION.md, PROPOSITION_WS.md) | ✅     |
| 2026-02-11 | `dc3b0bd` | Ajout du CHANGELOG.md comme fichier cœur dans les règles de gestion       | ✅     |
| 2026-02-11 | `f394576` | Ajout des règles pour les fichiers cœur et création du CHANGELOG.md      | ✅     |
| 2026-02-11 | `d559a3e` | Ajout du fichier VERSION à la racine du projet (0.1.0)                  | ✅     |
| 2026-02-11 | `ae5270a` | Ajout de la règle de versionnement pour le projet OpenIndex               | ✅     |
| 2026-02-11 | `2a75d16` | Ajout des règles Cline pour le projet OpenIndex                         | ✅     |
| 2026-02-11 | `XXXXXXX` | Correction du TODO.md : Mise à jour de l'état réel du crawler (scan niveau 1 uniquement). | ✅     |
| 2026-02-11 | `XXXXXXX` | Implémentation système de queues : Ajout du multi-threading, temporisation, et statistiques détaillées. | ✅     |
| 2026-02-11 | `XXXXXXX` | Correction deadlock crawler : Détection de fin améliorée et suivi des queues. | ✅     |
| 2026-02-11 | `XXXXXXX` | Création dossier docs/ : Documentation quotidienne du développement.        | ✅     |
| 2026-02-11 | `XXXXXXX` | Interface web v2 complète : Streamlit avec onglets, arborescence, visualisation | ✅     |
| 2026-02-11 | `XXXXXXX` | streamlit-tree-select intégré : Arborescence professionnelle et interactive | ✅     |
| 2026-02-11 | `XXXXXXX` | streamlit-elements intégré : Visualisation directe des fichiers (PDF, images, Excel) | ✅     |
| 2026-02-11 | `XXXXXXX` | Panneau latéral moderne : Actions contextuelles (correction en cours) | ⚠️     |

## Instructions pour la gestion des tâches

1. **Suivi en temps réel** : Ce fichier doit être mis à jour à chaque commit pour refléter l'état actuel des tâches.
2. **Archivage des tâches terminées** : Les tâches terminées doivent être déplacées dans la section "Tâches terminées" avec la date de complétion et le numéro de commit associé.
