# Correction de l'UI/XI d'OPENINDEX

## Base de l'interface:

### Entête
- L'entête doit impérativement être fixe au scroll
- L'entête doit prendre toute la largeur de la page,
- Le logo doit se trouver à 1 EM à gauche de l'entête
- Les icônes de droite devront être : La cloche de notification (qui ne doit pas avoir de notification par défaut), L'engrenage de configuration et le logo de profil utilisateur. pas besoin du menu "hamburger", tout se trouve dans la barre gauche.

### Barre gauche
- la barre gauche doit donner les informations suivantes sous le forme de blocs : l'espace actuellement choisi pour le crawl, le dernier lancement de celui-ci, s'il est actif ou pas (à la place de "ESPACES aucun espace détecté"
- La barre comprends aussi un menu qui comprends pour l'instant uniquement "Tableau de bord"
(les références à fichiers et doublons ne sont pas nécessaires)
- dans le bas de la barre, il faut une indication de version avec le hash commit et la date du dernier build et un accès à la licence copyright 2026 SMIDEN ) les uns au dessus des autres dans cet ordre et centrée dans la barre gauche, la version doit passer en orange avec un lien vers le github si un version de l'image est plus réscente.

### bloc centrale
- le tableau de bord doit se trouver dans un zone scrollable (uniquement cette partie)
- il faut un minimum de place (cohérente avec le reste des espacements de la page) entre la titre "tableau de bord" et l'entête,
- Les KPI doivent être actif et mis à jour au fur et à mesure du remplissage de la base de données si le crawler est en activité, 
- La barre d'avancement du crawl doit être dynamique (un calcul de la masse d'information doit avoir lieu préalablement au crawl pour pouvoir avoir une barre de défilement fiable.
- Dans le bloc de la barre d'avancement, il doit y avoir des informations sur chaque queue en cours (si le crawl est actif)
- Ajoute un bouton pour faire apparaitre le suivi de log du crawler dans la barre d'avancement. Il se déplira sous la forme d'un textarea de la largueur du bloc et de la hauteur du reste de la page lors du clic
- Retire la partie "Evolution du crawl"

## Autres pages dans le menu

### Gestionnaire de fichiers
- La gestion des fichiers se fera dans une zone "Explorateur de fichiers" (à mettre dans la barre de gauche dans le menu)
- La "page" Explorateur de Fichiers devra se comporter comme l'explorateur de fichier Windows / Dolphin avec deux espaces pour pouvoir faire passer les fichiers de l'un à l'autre par le bais de bouton
- Cette partie doit être ajouter au TODO.md (un développement avec réflexion est nécessaire.)

### Traitements des artefacts
- Une page "Traitements des artefacts" devra apparaitre dans le menu de gauche,
- Cette partie aura pour objet la suppression des fichiers temporaires, des doublons, etc.
- Elle comportera des KPI donnant des informations sur les fichiers problèmatiques, (quantité, type - fichier "temporaire" office, fichier thumbs.db, etc.)
- Elle comportera aussi une liste de ces fichiers avec des informations claires pour permettre à l'utilisateur de savoir s'il doit les supprimer ou les ignorer.
- les boutons d'actions: Supprimer, Ignorer et Archiver devront être présents pour chaque fichier mais aussi une case à cocher (avec selectionner tout) devra permettre de faire des interventions "massives"

# PR #44

## CORRECTIONS COSMETIQUES

- Espace choisi > il faut permettre de mettre un nom distinctif à un espace (comme SMIDEN),
- Dernier lancement > sans information, mettre "non défini",
- Zone version > trop gros, ce n'est pas indispensable il doit être en petit,
- Le sous-titre (en dessous de "Tableau de bord") est inutile à retirer,
- Volume indexé > attention à kilo c'est un k minuscule le K majuscule ce sont des kelvins. En outre je préférerais des octets plutôt que des bytes.
- avancement du crawl le texte sous le titre n'a rien à faire dans l'interface, il doit se trouver dans le TODO.md,
- le bouton "Voir les logs" devrait se trouver sous "Progression actuelle", il devrait être inaccessible si le crawler n'est pas activé,

## AJOUTS INDISPENSABLES
- rendre actif "engrenage" pour faire apparaitre la configuration par un glissement de droite à gauche une zone overlay pour configurer : 1. les configurations des espaces crawler, 2. gestion de la base de données, 3. inscription des utilisateurs (quand l'utilisateur connecter est admin, 4. le profil de l'utilisateur (si utilisateur admin ou utilisateur).
- Rendre actif "Cloche" pour indiquer les notifications nécessaire à l'utilisateur.
- Rendre actif "Piloter le crawl" pour permettre de lancer / forcer un crawl ou l'arreter (lightbox).


Fabrice 18/03/2026
