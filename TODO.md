# TODO.md

Ce fichier contient la liste des tâches à effectuer pour le projet OpenIndex, classées par ordre d'importance et organisées par phases.

## Tâches à effectuer

### Phase 1 : Préparation et Configuration (Date butoir : 2026-02-15) - ✅ **TERMINÉE**

### Phase 2 : Développement du Crawler et de l'Interface (Date butoir : 2026-02-22) - ✅ **TERMINÉE**

### Phase 0 : Test Crawler Immédiat (25 février 2026) - 🚀 **À FAIRE MAINTENANT**
- [ ] 🧪 **Tester le crawler existant** : Lancer crawl sur répertoire de test
- [ ] ✅ **Valider les données SQLite** : Vérifier structure et checksums
- [ ] 🖥️ **Confirmer interface Streamlit** : Affichage des données réelles
- [ ] � **Quantifier les données** : Estimer volumétrie et performance

### Phase 1 : Déploiement Crawler & Données Réelles (15-19 mars 2026)
- [ ] 🚀 **Déployer crawler existant** : Mettre en production le crawler SMB fonctionnel
- [ ] 🗄️ **Migrer vers PostgreSQL** : Configurer base de données robuste avec scripts de migration
- [ ] 📊 **Lancer crawl complet** : Collecter données réelles depuis SMB (>2 To)
- [ ] 🔌 **Créer API FastAPI minimale** : Endpoints de lecture pour les données collectées
- [ ] ✅ **Valider données réelles** : Vérifier accessibilité et intégrité des données

### Phase 2 : Frontend React avec Données Réelles (22-26 mars 2026)
- [ ] ⚛️ **Structure React + Material-UI** : Base de l'interface moderne
- [ ] 🌳 **Arborescence avec vraies données** : Composant tree utilisant données réelles
- [ ] 📈 **Dashboard avec métriques réelles** : Statistiques et visualisations
- [ ] 🔍 **Gestion des doublons réels** : Interface avec vrais fichiers doublons
- [ ] 🤖 **Intégrer service IA Ollama** : Configuration Docker et modèles
- [ ] 🧠 **Développer API IA** : Endpoints pour résumés et analyse
- [ ] 📄 **Résumés automatiques PDF/DOCX** : Traitement par lots en nuit
- [ ] 📊 **Extraction données Excel** : Analyse structurée des tableurs
- [ ] 🖼️ **Description images/vidéos** : Modèles LLaVA pour contenus visuels
- [ ] 🎨 **Design responsive final** : Adaptation mobile/tablette/desktop

### Phase 3 : Finalisation & Production (29 mars - 2 avril 2026)
- [ ] 🐳 **Dockerisation complète** : Frontend + Backend + Base de données + Service IA
- [ ] 🤖 **Configuration Ollama** : Modèles Llama3.2, LLaVA, CodeLlama déployés
- [ ] 🔄 **Tests d'intégration E2E** : Validation complète avec données réelles et IA
- [ ] 📚 **Documentation déploiement** : Guide d'installation et maintenance IA incluse
- [ ] 🚀 **Livraison production** : Version finale avec IA intégrée (deadline 19 mars)

### Phase 4 : Fonctionnalités IA Avancées (Date butoir : 2026-04-15) - 📋 **PLANIFIÉ**
- [ ] 🧹 **Nettoyage fichiers Windows inutiles** : Thumbs.db, desktop.ini, .lnk automatiquement filtrés
- [ ] 📁 **Suppression dossiers vides** : Nettoyage automatique de l'arborescence
- [ ] 🔍 **Détection fichiers corrompus** : Analyse par extension et taille anormale
- [ ] 🗑️ **Fichiers temporaires Office** : Identification automatique ~$*.tmp, ~$*.docx
- [ ] 📏 **Identification fichiers volumineux** : Alertes et suggestions d'archivage
- [ ] 📅 **Fichiers anciens** : Détection et propositions de backup automatique
- [ ] ⚠️ **Fichiers non-professionnels** : IA locale pour détecter contenus inappropriés
- [ ] 👤 **Traçabilité propriétaires** : Intégration SMB owner pour gestion utilisateur
- [ ] 🔄 **Retry intelligent** : Pattern exponentiel pour scans interrompus (1, 5, 15, 30, 60, 120, 240, 480min)
- [ ] ⏱️ **Timeouts configurables** : Adaptation horaire pour ne pas surcharger serveur
- [ ] 🚀 **Queue prioritaire gros fichiers** : Traitement séparé >100MB vs <100MB
- [ ] � **Email digest hebdomadaire** : Résumé post-crawl avec actions requises
- [ ] 🔔 **Notifications in-app** : Alertes temps réel pour actions critiques
- [ ] 🔗 **Webhooks one-click** : Boutons dans email pour archiver/refuser fichiers
- [ ] 🏖️ **Configuration vacances** : Périodes flexibles (2 sem. mars, 5 sem. été)
- [ ] ⚙️ **Workflow validation admin** : Gestion faux-positifs fichiers non-professionnels
- [ ] �🗂️ **Déployer l'application dans un conteneur Docker** : Configuration Docker pour production
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
| 2026-02-25 | `e7bbc0a` | Finaliser le crawler SMB récursif : Crawler récursif complet avec multi-threading et queues | ✅     |
| 2026-02-25 | `e7bbc0a` | Optimiser les performances du crawler : Multi-threading, reprise après interruption, gestion des erreurs | ✅     |
| 2026-02-25 | `e7bbc0a` | Ajouter un état d'avancement : Barre de progression et statistiques en temps réel | ✅     |
| 2026-02-25 | `e7bbc0a` | Créer l'interface web : Interface Streamlit v2 avec onglets multiples | ✅     |
| 2026-02-25 | `e7bbc0a` | Ajouter un tableau de bord statistique : Métriques complètes et graphiques interactifs | ✅     |
| 2026-02-25 | `e7bbc0a` | Détecter et afficher les doublons : Détection SHA-256 avec interface détaillée | ✅     |
| 2026-02-25 | `e7bbc0a` | Ajouter des filtres par date/taille/type : Filtres complets et recherche | ✅     |
| 2026-02-25 | `e7bbc0a` | Exporter les inventaires en CSV : Export des données et statistiques | ✅     |
| 2026-02-25 | `e7bbc0a` | Interface web v2 complète : Streamlit avec onglets, arborescence, visualisation | ✅     |
| 2026-02-25 | `e7bbc0a` | streamlit-tree-select intégré : Arborescence professionnelle et interactive | ✅     |
| 2026-02-25 | `e7bbc0a` | streamlit-elements intégré : Visualisation directe des fichiers (PDF, images, Excel) | ✅     |
| 2026-02-25 | `e7bbc0a` | Panneau latéral moderne : Actions contextuelles (correction en cours) | ⚠️     |

## Instructions pour la gestion des tâches

1. **Suivi en temps réel** : Ce fichier doit être mis à jour à chaque commit pour refléter l'état actuel des tâches.
2. **Archivage des tâches terminées** : Les tâches terminées doivent être déplacées dans la section "Tâches terminées" avec la date de complétion et le numéro de commit associé.
