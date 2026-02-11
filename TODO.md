# TODO.md

Ce fichier contient la liste des tâches à effectuer pour le projet OpenIndex, classées par ordre d'importance et organisées par phases.

## Tâches à effectuer

### Phase 1 : Préparation et Configuration (Date butoir : 2026-02-15)
- [ ] 🛠️ **Configurer l'environnement de développement** : Installer Docker, SQLite, et Python pour le projet.
- [ ] 📦 **Installer les bibliothèques nécessaires** : Ajouter les dépendances (`smbprotocol`, FastAPI, Streamlit).
- [ ] 📜 **Créer les scripts de base pour le crawler SMB** : Développer les scripts avec pagination et indexation progressive.
- [ ] � **Finaliser la documentation technique** : Compléter les sections manquantes dans le fichier `PROJET.md` et s'assurer que toutes les spécifications techniques sont à jour.
- [ ] 🔧 **Optimiser les performances du moteur de recherche** : Identifier et corriger les goulots d'étranglement dans l'algorithme de recherche.
- [ ] 📚 **Mettre à jour la documentation utilisateur** : Ajouter des exemples concrets et des captures d'écran pour faciliter la compréhension.

### Phase 2 : Développement du Crawler et de l'Interface (Date butoir : 2026-02-22)
- [ ] 🔄 **Implémenter le crawler SMB** : Développer le module de crawl pour les partages SMB avec génération de checksums SHA-256, pagination pour la grande volumétrie, et indexation progressive.
- [ ] 🌐 **Créer l'interface web** : Développer l'interface de visualisation de l'arborescence des fichiers avec duplication de l'arborescence et sélection des fichiers à archiver.
- [ ] 📊 **Ajouter un tableau de bord statistique** : Intégrer des statistiques sur l'espace utilisé, le nombre de fichiers, etc.
- [ ] 🔍 **Détecter et afficher les doublons** : Implémenter la détection des doublons basée sur les checksums.
- [ ] 📥 **Ajouter des filtres par date/taille/type** : Permettre le filtrage des fichiers dans l'interface.
- [ ] 📤 **Exporter les inventaires en CSV** : Permettre l'export des inventaires pour les rapports.

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
| 2026-02-11 | `cf8d598` | Création du fichier TODO.md : Initialisation du fichier pour suivre les tâches. | ✅     |
| 2026-02-11 | `2194040` | Ajout des fichiers PROJET.md et ROADMAP.md : Documentation technique initiale. | ✅     |
| 2026-02-11 | `22f3593` | Ajout des fichiers d'archives : Archivage des documents historiques.           | ✅     |

## Instructions pour la gestion des tâches

1. **Suivi en temps réel** : Ce fichier doit être mis à jour à chaque commit pour refléter l'état actuel des tâches.
2. **Archivage des tâches terminées** : Les tâches terminées doivent être déplacées dans la section "Tâches terminées" avec la date de complétion et le numéro de commit associé.
