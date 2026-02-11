# OPENINDEX

## PROJET

### Objectifs généraux :

OPENINDEX (OpenIndex) est un projet qui a pour objectif de permettre aux utilisateurs d'archiver simplement et de reclasser dans une nouvelle arborescence leurs fichiers professionnels. Les fonctionnalités à implémenter sont les suivantes :

- [court terme] Générer une arborescence de la zone de partages (SMB) indiqué et la placer en base de données.
  - crawler l'ensemble du partages (dépot de fichiers SMB) pour l'intégrer dans une base de données,
  - faire un checksum des fichiers lors du crawl pour permettre d'identifier les doublons par autre chose que par leur nom,
  - noter les informations de date disponible (création, dernière modification, ...) pour permettre d'indiquer si le fichier dois être archivé,
  - générer un affichage par navigateur web sur la base d'un framework existant pour visualiser les fonctions ci-dessus
- [moyen terme] Créer une interface de gestion des fichiers présent
  - permettre par le biais d'une case à cocher de dupliquer l'arborescence actuelle dans la zone d'archive sur un NAS dupliqué, (administrateur)
  - permettre par le biais d'une case à cocher d'indiquer ce qui doit être archiver lors du prochain crawl - implique la copie des fichiers de l'actif cloud vers le NAS, la vérification des états et des checksums pour être sûr que les fichiers sont valides et identiques, suppression du fichier dans le cloud.)
  - permettre par le biais d'un bouton d'effectuer des archives instantanées par le même processus que dans le cas précédent mais groupes de fichiers par groupes de fichiers avec une limite de taille, et un indicateur de temps (instantannée / programmer / ...)
  - Permettre de faire des sommaires recursifs à partir d'un point (sous la forme d'un simple bouton).
- [long terme] Créer des fonctionnalités complémentaires
  - permettre d'indiquer une date d'archivage sur un dossier qui sera appliquer à l'ensemble des fichiers et dossiers réccursivement. (Ex. le dossier A est indiqué comme "A archivé après 30 jours", les fichiers et dossiers à l'intérieur de ce dossier sont automatiquement déplacé depuis le cloud vers le NAS au bout de 30 jours)

Tu peux proposer d'autre fonction qui te paraissent pertinente ici.

- Propose une infrastructure, la plus simple possible pour réaliser ce projet,
- Détaille les solutions à mettre en place avec les contraites suivantes :
  - Doit être intégrable à un Proxmox (VM, LXC, Container docker),
  - Doit être controlable facilement par une Interface graphique (streamlit, gradio, dash...),
  - Doit être simple pour l'utilisateur comme pour l'administrateur
