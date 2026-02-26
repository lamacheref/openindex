# Protocoles Automatisés

## Nettoyer les fichiers windows inutiles

Les fichiers windows inutiles sont :
- Les fichiers de preview (Ex. Thumbs.db)
- Les fichiers de cache (Ex. desktop.ini)
- Les fichiers de systeme (Ex. desktop.ini)
- Les liens symboliques (Ex. .lnk)

## Supprimer les dossiers vides

Les dossiers vides sont supprimés automatiquement.

## Identifier les fichiers dupliqués

Les fichiers dupliqués sont identifiés par leur hash MD5.

## Identifier les fichiers corrompus

Les fichiers corrompus sont identifiés par leur extension et leur taille.

## Identifier les fichiers temporaires de la suite office

Les fichiers temporaires de la suite office sont identifiés par leur extension et leur taille ou par leur format de nommage (ex: ~$nomdufichier.docx).

## Identifier les fichiers volumineux

Les fichiers volumineux sont identifiés par leur taille.

## Identifier les fichiers anciens

Les fichiers anciens sont identifiés par leur date de modification.

## Identifier les fichiers potentiellement non professionnels

Les fichiers potentiellement non professionnels sont identifiés par 
- leurs noms qui contiennent des mots-clés non professionnels, (Ex. "Mariage", "Anniversaire", "Fête", "Soirée", "Week-end", "Vacances")
- leurs extensions qui ne sont pas professionnelles, (Ex. .mkv, .mp4, .avi, .mov, .wmv, .flv, .webm, .m4v, .3gp, .mpg, .mpeg, .m2v, .mpe, .mp4v, .mpg4, .m4p, .m4b, .m4r, .m4a, .m4v, .m4b, .m4r, .m4a, .mp3, .wav, .aiff, .flac, .ogg, .wma, .m4a, .m4b, .m4r, .m4a, .mts)
- leurs tailles qui sont anormales, (Ex. < 1KB, > 150MB)

Il doivent être marqué comme "potentiellement non professionnels" et nécessiter une vérification manuelle.

# Reflections de l'utilisateur

## Il faut un accès à un IA locale
Dans le stack technique, il faut intégrer un modèle d'IA locale pour identifier les cas spécifiques. (type ollama)
particulièrement pour détecter les fichiers qui ne respectent pas les normes professionnelles.(Copyright, Marques, etc.)
Mais aussi capable de faire un résumé du contenu des fichiers en mode RAG.

## Il faut un moyen de communication avec l'utilisateur
Pour les fichiers potentiellement non professionnels, il faut un moyen de communication avec l'utilisateur pour lui demander de vérifier manuellement.

## Il faut que le crawler puisse enregistrer l'utilisateur d'un fichier.
Cela permettra de savoir qui a créé le fichier et de le contacter si nécessaire, mais aussi de lui permettre de supprimer le fichier s'il le souhaite depuis l'interface.

## Il faut trouver une solution pour permettre un backup automatique des fichiers trop anciens.
Ils doivent être déplacés sur nos NAS internes mais il faut aussi trouver un moyen pour qu'il reste une méthode pour y accéder facilement. (faire un lien symbolique ?)

## Il faut prévoir une solution pour permettre un backup automatique des fichiers très gros (particulièrement les archives)
Ils doivent être déplacés sur nos NAS internes mais il faut aussi trouver un moyen pour qu'il reste une méthode pour y accéder facilement. (faire un lien symbolique ?)

## Il faut pouvoir configurer le blocage de sécurité du crawler
Il faut pouvoir régler suivant le type de scan (par exemple suivant l'heure de la journée.) le timeout de sécurité pour ne pas surcharger le serveur cloud de fichier.

## il faut prévoir un retry de scan à partir de l'emplacement où le crawler s'est arrêté
Les serveurs redémarrent en nuit pour mise à jour ou backup, il faut donc prévoir un retry de scan à partir de l'emplacement où le crawler s'est arrêté, toutes les 1mn, 5mn, 10mn, 30mn, 1h, 2h, 4h, 8h, 12h, 24h.
Il faut aussi laisser tourner en week-end.

## il pourrait être intéressant de prévoir une queue spécialisée dans le calcul des SHA256 des fichiers les plus gros > 100MB
Pour permettre un scan plus rapide des fichiers plus petits.

# Préconisations matériels

## stockage sur le territoire
- Acheter un serveur NAS QNAP 8 disques 4To à part adapté à la quantité de données à stocker des collectivités à placer dans la baie de l'ECM de Laigné-en-belin pour une synchronisation des fichiers déplacés du cloud.
- Prévoir de configurer les NAS en cluster pour une haute disponibilitée. (voir la faisabilité technique, les QNAP possédent de quoi mettre en place des VMs)
