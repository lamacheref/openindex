# Instructions pour la validation des règles et des hooks

Vous devez impérativement respecter les règles définies dans les fichiers `.clinerules` et les hooks Git associés. Ces règles sont conçues pour garantir la qualité, la cohérence et la traçabilité des développements. Aucune exception ou passe-droit n'est autorisé.

## Règles générales

- **Respect strict des règles** : Toutes les règles définies dans les fichiers `.clinerules` et les hooks Git doivent être respectées sans exception.
- **Correction obligatoire des erreurs** : Si une erreur est détectée par un hook ou une règle, elle doit être corrigée avant de pouvoir continuer. Aucun contournement n'est autorisé.
- **Validation avant commit** : Avant chaque commit, assurez-vous que toutes les règles sont respectées. Les hooks Git automatiques effectueront ces vérifications.

## Règles spécifiques pour les hooks Git

- **Hook `pre-commit`** : Ce hook vérifie automatiquement les règles pour les fichiers cœur du projet avant chaque commit. Si des erreurs sont détectées, le commit sera bloqué jusqu'à ce que les erreurs soient corrigées.
- **Correction des erreurs** : Si le hook `pre-commit` détecte des erreurs, vous devez les corriger immédiatement. Aucune autre action ne sera possible tant que les erreurs ne sont pas résolues.
- **Interdiction des passes-droits** : Il est strictement interdit de contourner ou de désactiver les hooks Git pour éviter les vérifications. Tout tentative de passe-droit sera considérée comme une violation des règles.

## Règles spécifiques pour l'IA

- **Application automatique des règles** : L'IA doit appliquer automatiquement les règles définies dans les fichiers `.clinerules` et les hooks Git.
- **Signalement des erreurs** : Si une règle n'est pas respectée, l'IA doit signaler immédiatement l'erreur et demander à l'utilisateur de la corriger.
- **Refus des passes-droits** : L'IA ne doit jamais permettre ou suggérer de contourner les règles, même à la demande de l'utilisateur.
- **Documentation des corrections** : Toutes les corrections apportées pour respecter les règles doivent être documentées dans le fichier `CHANGELOG.md`.

## Exemple de processus de correction

1. **Détection d'une erreur** : Le hook `pre-commit` détecte une erreur dans le fichier `TODO.md` (par exemple, une tâche terminée sans numéro de commit).
2. **Signalement de l'erreur** : Le hook affiche un message clair indiquant l'erreur et bloque le commit.
3. **Correction de l'erreur** : L'utilisateur ou l'IA corrige l'erreur en ajoutant le numéro de commit manquant.
4. **Nouvelle tentative de commit** : Une fois l'erreur corrigée, le commit peut être retenté. Le hook vérifie à nouveau les règles et autorise le commit si tout est conforme.

N'oubliez jamais que le respect strict des règles est essentiel pour maintenir la qualité et la cohérence du projet. Aucune exception ne sera tolérée.