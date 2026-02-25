# Interface Utilisateur

## Vue d'ensemble

L'interface utilisateur est une application web qui permet de visualiser et de gérer les fichiers indexés par OpenIndex.

## Fonctionnalités

- Affichage des fichiers indexés
- Recherche de fichiers
- Visualisation des métadonnées
- Gestion des fichiers (suppression, renommage, etc.)
- Statistiques et analyses
- Configuration de l'application

## Panneaux
Les panneaux de l'interface utilisateur sont les suivants :

- Panneau de navigation
- Panneau de recherche
- Panneau de visualisation
- Panneau de gestion
- Panneau de statistiques
- Panneau de configuration
- Panneau d'activité du Crawler (Ex. : nombre de fichiers traités, nombre de fichiers volumineux, nombre de fichiers anciens, nombre de fichiers potentiellement non professionnels, queues, retry, etc.)

Ils doivent être sur la même page et être interactifs.

Ils doivent être liés à une authentication native. (il faut laisser un porte ouvert pour la mise en place d'un sso)

Seul l'administrateur peut accéder à la partie "panneau de configuration". il doit aussi être le seul à pouvoir créer des utilisateurs, stopper le crawler, etc.

Les utilisateurs normaux ne doivent pouvoir alterer que leurs propres données. (sur la base de l'utilisateur du fichier identifié par le crawler)