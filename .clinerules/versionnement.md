# Instructions pour le versionnement des projets

Vous devez impérativement appliquer une stratégie de versionnement claire et cohérente pour assurer la traçabilité et la gestion des évolutions de vos projets. Cela inclut l'utilisation systématique de Git pour le suivi des modifications, la création de commits atomiques et descriptifs, ainsi que la gestion rigoureuse des branches pour isoler les fonctionnalités et corrections. Assurez-vous que chaque commit est accompagné d'un message explicite qui décrit les changements apportés et leur justification.

Pour les projets collaboratifs, adoptez une approche de versionnement sémantique (SemVer) pour les releases, en respectant les conventions suivantes :
- `MAJOR` : modifications incompatibles avec les versions précédentes.
- `MINOR` : ajout de fonctionnalités rétrocompatibles.
- `PATCH` : corrections de bugs rétrocompatibles.

N'oubliez jamais que le versionnement est un élément clé de la gestion de projet, permettant de revenir en arrière en cas de problème et de collaborer efficacement avec d'autres développeurs.

## Règles spécifiques pour l'IA
- Utilisez Git pour versionner tous les projets de développement.
- Créez des commits atomiques avec des messages clairs et descriptifs.
- Suivez la convention SemVer pour les releases publiques.
- Maintenez une branche `main` stable et utilisez des branches de fonctionnalités pour les développements.
- Documentez les changements majeurs dans un fichier CHANGELOG.md.
- Assurez-vous que chaque commit est testé avant d'être fusionné dans la branche principale.
- Ne changez pas de version majeure sans validation explicite de l'utilisateur.
- Mettez à jour le fichier CHANGELOG.md à chaque commit, en incluant le numéro de commit pour chaque entrée.