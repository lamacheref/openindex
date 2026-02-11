# PROPOSITION D'ARCHITECTURE POUR OPENINDEX

## Introduction
Ce document propose une architecture technique pour le projet OpenIndex, visant à permettre aux utilisateurs d'archiver et de reclasser leurs fichiers professionnels de manière simple et efficace.

## Objectifs
- **Court terme** : Crawler un partage SMB, générer des checksums, et fournir une interface web pour visualiser les données.
- **Moyen terme** : Interface de gestion des fichiers avec archivage et duplication.
- **Long terme** : Fonctionnalités avancées comme l'archivage récursif basé sur des dates.

## Contraintes et Optimisations
- **Performance du crawler SMB** : Le crawler est conçu pour minimiser l'impact sur le serveur distant, même si cela prend plusieurs jours. Un état d'avancement sera affiché dans l'interface utilisateur pour suivre la progression.
- **Fréquence de mise à jour** : Les données seront mises à jour de manière hebdomadaire ou à la demande, avec une indication claire de la date de dernière mise à jour.
- **Sécurité** : Aucune contrainte de sécurité particulière, car le réseau est isolé.
- **Interface utilisateur** : Conception simple et intuitive, avec des fonctionnalités pratiques comme un indicateur de progression et des informations claires sur les mises à jour.

## Architecture Technique

### 1. Infrastructure
- **Conteneurisation** : Utilisation de Docker pour encapsuler l'application, facilitant l'intégration avec Proxmox.
- **Base de données** : PostgreSQL pour stocker les métadonnées des fichiers (chemins, checksums, dates, etc.).
- **Backend** : Serveur en Python (FastAPI ou Flask) pour gérer les opérations de crawl, d'archivage, et les interactions avec la base de données.
- **Frontend** : Interface web légère en Streamlit ou Gradio pour une gestion simple et intuitive.

### 2. Modules Fonctionnels

#### Crawler SMB
- **Bibliothèque** : Utilisation de `smbprotocol` pour parcourir les partages SMB.
- **Fonctionnalités** :
  - Collecte des métadonnées des fichiers (chemins, dates de création/modification).
  - Génération de checksums (SHA-256) pour identifier les doublons.
  - Stockage des données dans la base de données PostgreSQL.

#### Gestion des Checksums
- **Algorithme** : SHA-256 pour générer des checksums uniques.
- **Fonctionnalités** :
  - Identification des doublons.
  - Vérification de l'intégrité des fichiers lors de l'archivage.

#### Archivage
- **Fonctionnalités** :
  - Copie des fichiers vers un NAS.
  - Vérification des checksums pour garantir l'intégrité.
  - Suppression des fichiers du cloud après archivage.
  - Archivage instantané ou programmé.

#### Interface Utilisateur
- **Technologie** : Streamlit ou Gradio pour une interface simple et intuitive.
- **Fonctionnalités** :
  - Visualisation de l'arborescence des fichiers.
  - Sélection des fichiers à archiver via des cases à cocher.
  - Bouton pour déclencher l'archivage instantané.
  - Génération de sommaires récursifs.

### 3. Intégration avec Proxmox
- **Déploiement** : L'application sera déployée dans un conteneur Docker sur Proxmox.
- **Stockage** : Utilisation d'un volume Docker pour le stockage des données de l'application et de la base de données.

### 4. Workflow
1. **Crawl** : L'utilisateur lance le crawler via l'interface web.
2. **Stockage** : Les métadonnées des fichiers sont stockées dans la base de données.
3. **Sélection** : L'utilisateur sélectionne les fichiers à archiver via des cases à cocher.
4. **Archivage** : Les fichiers sont copiés vers le NAS, vérifiés, et supprimés du cloud si nécessaire.

## Conclusion
Cette architecture propose une solution technique simple et efficace pour répondre aux besoins du projet OpenIndex. Elle est conçue pour être facile à déployer, à utiliser, et à maintenir, tout en offrant des fonctionnalités avancées pour l'archivage et la gestion des fichiers.