# OPENINDEX - PROJET COMPLET

## Introduction
Ce document présente une vue d'ensemble complète du projet OpenIndex, incluant les objectifs, l'architecture technique, et les spécifications détaillées.

## Objectifs Généraux

### Court Terme - ✅ **ACCOMPLI**
- **Crawler SMB** : ✅ Générer une arborescence de la zone de partages SMB et la placer en base de données.
  - ✅ Crawler l'ensemble des partages SMB pour intégrer les données dans une base de données.
  - ✅ Générer des checksums (SHA-256) pour identifier les doublons.
  - ✅ Noter les informations de date (création, modification) pour déterminer les fichiers à archiver.
  - ✅ Fournir une interface web pour visualiser les données.

### Moyen Terme - 🔄 **EN COURS**
- **Interface de gestion des fichiers** :
  - ✅ Permettre de visualiser l'arborescence complète avec navigation interactive
  - ✅ Permettre de détecter et gérer les doublons automatiquement
  - ✅ Permettre de visualiser les fichiers directement dans l'interface
  - ⚠️ **À FAIRE** : Permettre de dupliquer l'arborescence dans la zone d'archive NAS
  - ⚠️ **À FAIRE** : Permettre de sélectionner les fichiers à archiver
  - ⚠️ **À FAIRE** : Effectuer des archives instantanées avec vérification des checksums

### Long Terme - 📋 **PLANIFIÉ**
- **Fonctionnalités complémentaires** :
  - 📋 Permettre d'indiquer une date d'archivage récursive sur un dossier
  - 📋 Gestion des favoris et tags personnalisés
  - 📋 Notifications système et alertes automatiques

## Contraintes et Optimisations

### Performance du Crawler SMB
- Le crawler est conçu pour minimiser l'impact sur le serveur distant, même si cela prend plusieurs jours.
- Un état d'avancement sera affiché dans l'interface utilisateur pour suivre la progression.

### Fréquence de Mise à Jour
- Les données seront mises à jour de manière hebdomadaire ou à la demande.
- Indication claire de la date de dernière mise à jour.

### Sécurité
- Aucune contrainte de sécurité particulière, car le réseau est isolé.

### Interface Utilisateur
- Conception simple et intuitive, avec des fonctionnalités pratiques comme un indicateur de progression et des informations claires sur les mises à jour.

## Architecture Technique

### Infrastructure - ✅ **IMPLÉMENTÉE**
- **Base de données** : ✅ SQLite pour stocker les métadonnées des fichiers (chemins, checksums, dates, etc.).
- **Backend** : ✅ Crawler SMB en Python avec multi-threading et queues optimisées
- **Frontend** : ✅ Interface web moderne en Streamlit avec streamlit-tree-select et streamlit-elements

### Modules Fonctionnels - ✅ **OPÉRATIONNELS**
- **Crawler SMB** : ✅ Module principal avec smbprotocol pour l'accès aux partages réseau
- **Gestion des Checksums** : ✅ Calcul SHA-256 pour déduplication et intégrité
- **Base de Données** : ✅ SQLite avec schéma optimisé pour grande volumétrie
- **Interface Web** : ✅ Streamlit v2 avec onglets multiples et navigation interactive
- **Visualisation** : ✅ streamlit-elements pour documents, images, et fichiers Excel

### Spécifications Techniques - ✅ **VALIDÉES**
- **Grande volumétrie** : ✅ Optimisé pour >2 To avec pagination et indexation progressive
- **Multi-threading** : ✅ Workers dédiés pour répertoires et fichiers avec queues
- **Robustesse** : ✅ Gestion des erreurs, reprise après interruption, détection de fin
- **Déduplication** : ✅ Détection automatique des doublons par checksum
- **Performance** : ✅ Temporisation entre requêtes, queues optimisées, monitoring temps réel

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

### Intégration avec Proxmox
- **Déploiement** : L'application sera déployée dans un conteneur Docker sur Proxmox.
- **Stockage** : Utilisation d'un volume Docker pour le stockage des données de l'application et de la base de données.

### Workflow
1. **Crawl** : L'utilisateur lance le crawler via l'interface web.
2. **Stockage** : Les métadonnées des fichiers sont stockées dans la base de données.
3. **Sélection** : L'utilisateur sélectionne les fichiers à archiver via des cases à cocher.
4. **Archivage** : Les fichiers sont copiés vers le NAS, vérifiés, et supprimés du cloud si nécessaire.

## Spécifications Techniques Finalisées

### Contexte
- **Volume SMB** : > 2 To (très grande volumétrie).
- **Permissions** : Accès complet pour le crawler.
- **Fréquence** : Hebdomadaire ou à la demande.
- **Doublons** : Affichage uniquement (phase 1), RAG et consolidation (phase 2).
- **NAS** : QNAP 23 To sur fibre.
- **Utilisateurs** : 15 maximum.

### Adaptations Techniques Nécessaires

#### Gestion de la Grande Volumétrie (>2 To)
- **Pagination** : Traitement par lots de 1000 fichiers pour éviter la surcharge mémoire.
- **Indexation progressive** : Sauvegarde intermédiaire toutes les 10 000 entrées.
- **Optimisation SQLite** : WAL mode et transactions par lots.
- **Cache intelligent** : Mémorisation de l'arborescence pour accélérer les crawls suivants.

#### Performance pour Crawl Hebdomadaire
- **Comparaison incrémentale** : Basée sur les dates de modification et checksums.
- **Parallélisation** : Multi-threading pour l'analyse des fichiers.
- **Monitoring** : Barre de progression et temps estimé restant.

#### Gestion Multi-Utilisateurs (15 Personnes)
- **Authentification simple** : Base utilisateurs locale avec rôles admin/utilisateur.
- **Sessions simultanées** : Gestion des accès concurrents à la base de données.
- **Interface adaptée** : Vues différenciées admin vs utilisateur.

## Fonctionnalités Complémentaires Suggérées

### Court Terme
- **Recherche plein texte** : Indexation des noms de fichiers pour recherche rapide.
- **Export CSV/Excel** : Extraction des inventaires pour rapports.
- **Tableau de bord statistique** : Espace utilisé, nombre de fichiers, doublons détectés.
- **Tags personnalisés** : Étiquetage des dossiers/fichiers pour organisation.

### Moyen Terme
- **Notifications email** : Alertes automatiques d'archivage.
- **API REST complète** : Intégration avec des outils tiers.
- **Gestion multi-utilisateurs** : Droits et permissions différenciés.
- **Planning d'archivage** : Automatisation des tâches programmées.

## Livrables pour le 3 Mars

### Fonctionnel
- Crawl complet SMB >2 To avec checksum SHA-256.
- Interface web visualisation arborescence.
- Détection et affichage des doublons.
- Filtres par date/taille/type.
- Export CSV des inventaires.
- Tableau de bord statistique.

### Technique
- Conteneur Docker déployable sur Proxmox.
- Base de données SQLite optimisée.
- Authentification pour 15 utilisateurs.
- Crawl hebdomadaire automatique ET à la demande.
- Monitoring progression et performance.

### Documentation
- README technique et utilisateur.
- Configuration déploiement.
- Guide d'administration.

## Conclusion
Ce document combine les informations des fichiers `PROJET.MD`, `PROPOSITION.md`, et `PROPOSITION_WS.md` pour fournir une vue d'ensemble complète du projet OpenIndex. L'architecture proposée est conçue pour être simple, efficace, et adaptée aux contraintes techniques et fonctionnelles du projet.