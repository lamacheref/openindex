# ROADMAP POUR LE PROJET OPENINDEX

## Introduction
Ce document présente une feuille de route détaillée pour le développement du projet OpenIndex, basée sur une charge de travail de 7 heures par jour. Le projet est divisé en phases, chacune incluant des tâches spécifiques et une estimation du temps nécessaire pour les accomplir. Cette feuille de route est alignée avec les spécifications détaillées dans le fichier `PROJET.md`.

## Phases du Projet

### Phase 1 : Préparation et Configuration (3 jours)
- **Jour 1** :
  - ✅ Configuration de l'environnement de développement (Docker, SQLite, Python).
  - ✅ Installation des bibliothèques nécessaires (`smbprotocol`, FastAPI, Streamlit).
  - ✅ Création des scripts de base pour le crawler SMB avec pagination et indexation progressive.
- **Jour 2** :
  - ⏳ Configuration de la base de données SQLite (schéma, tables pour les métadonnées des fichiers).
  - ⏳ Développement des fonctions de base pour le crawler (lecture des fichiers, génération de checksums SHA-256).
- **Jour 3** :
  - ⏳ Intégration du crawler avec la base de données.
  - ⏳ Tests initiaux pour vérifier la collecte et le stockage des métadonnées avec optimisation pour la grande volumétrie.

### Phase 2 : Développement du Crawler et de l'Interface (5 jours)
- **Jour 4** :
  - Développement des fonctionnalités avancées du crawler (gestion des erreurs, reprise après interruption, multi-threading).
  - Ajout d'un état d'avancement pour le crawler dans l'interface utilisateur avec barre de progression et temps estimé restant.
- **Jour 5** :
  - Création de l'interface utilisateur de base (Streamlit) pour visualiser l'arborescence des fichiers.
  - Intégration des données de la base de données dans l'interface avec filtres par date/taille/type.
- **Jour 6** :
  - Développement des fonctionnalités de sélection des fichiers (cases à cocher, boutons d'action).
  - Ajout de la fonctionnalité de mise à jour à la demande avec indication de la date de dernière mise à jour.
- **Jour 7** :
  - Tests complets du crawler et de l'interface utilisateur.
  - Corrections des bugs identifiés.
- **Jour 8** :
  - Optimisation des performances du crawler pour minimiser l'impact sur le serveur distant avec gestion de la grande volumétrie.
  - Finalisation de l'interface utilisateur avec des indicateurs de progression et tableau de bord statistique.

### Phase 3 : Fonctionnalités d'Archivage (4 jours)
- **Jour 9** :
  - Développement du module d'archivage (copie des fichiers vers le NAS, vérification des checksums).
  - Intégration avec l'interface utilisateur pour déclencher l'archivage avec gestion multi-utilisateurs.
- **Jour 10** :
  - Ajout de la fonctionnalité de suppression des fichiers du cloud après archivage.
  - Tests des fonctionnalités d'archivage et de suppression avec vérification de l'intégrité des fichiers.
- **Jour 11** :
  - Développement de la fonctionnalité d'archivage instantané et programmé.
  - Intégration avec l'interface utilisateur et gestion des notifications pour les utilisateurs.
- **Jour 12** :
  - Tests complets des fonctionnalités d'archivage avec simulation de grande volumétrie.
  - Corrections des bugs identifiés et optimisation des performances.

### Phase 4 : Fonctionnalités Complémentaires (3 jours)
- **Jour 13** :
  - Développement de la fonctionnalité de sommaires récursifs avec export CSV/Excel.
  - Intégration avec l'interface utilisateur et ajout de tags personnalisés.
- **Jour 14** :
  - Développement de la fonctionnalité d'archivage récursif basé sur des dates.
  - Tests des fonctionnalités complémentaires avec validation des performances.
- **Jour 15** :
  - Finalisation des tests et corrections des bugs.
  - Préparation de la documentation utilisateur et technique avec guides d'administration.

### Phase 5 : Déploiement et Tests Finaux (2 jours)
- **Jour 16** :
  - Déploiement de l'application dans un conteneur Docker sur Proxmox avec configuration optimisée.
  - Configuration des volumes Docker pour le stockage des données et gestion des permissions.
- **Jour 17** :
  - Tests finaux de l'application dans l'environnement de production avec validation des fonctionnalités livrables pour le 3 mars.
  - Corrections des derniers bugs et optimisations pour la grande volumétrie.

## Conclusion
Cette feuille de route détaille les étapes nécessaires pour développer et déployer le projet OpenIndex en respectant une charge de travail de 7 heures par jour. Chaque phase est conçue pour être réalisable dans le temps imparti, avec des tests réguliers pour garantir la qualité du produit final. Les fichiers TODO.md, README.md, CHANGELOG.md, et ROADMAP.md ont été mis à jour pour refléter l'état actuel du projet.