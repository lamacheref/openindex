# Lightbox "Détails des doublons" en lecture seule + comptage réel (issue #3)

## Objectif
Depuis n'importe quelle occurrence d'un doublon dans l'explorateur, ouvrir un lightbox listant
**toutes** les occurrences (chemins) du même contenu, et afficher le nombre réel d'occurrences
dans le badge "Doublon (n)".

## Fait (commit à venir)
- **Backend `GET /api/explorer/items`** : chaque fichier expose désormais
  - `checksum` = `hash_xxh64`
  - `duplicate_count` = nombre total d'occurrences du même `hash_xxh64`+`size`+`space_id`,
    **excluant** `is_deleted` et `is_garbage` (le fichier lui-même est inclus)
  - `is_duplicate` = `duplicate_count > 1` et le fichier n'est pas `is_garbage`
- **Backend `GET /api/duplicates/{checksum}/details`** (`duplicate_details_router.py`) : migré de la
  table obsolète `files` vers `indexed_files_optimized` (colonne `hash_xxh64`), avec jointure sur
  `smb_spaces` pour le nom d'espace. **Lecture seule** (SELECT uniquement).
- **Frontend** : le badge "Doublon (n)" est cliquable dans l'explorateur (vues Sources et Archive)
  et ouvre le lightbox. Le modal est **en lecture seule** : suppression/déduplication désactivée,
  boutons "Garder"/"Supprimer tout sauf le gardé" retirés.
- **Tests** : fixture `test_duplicate_details_api.py` corrigée (patch vers `backend.src.api.
  duplicate_details_router.get_db_adapter`), DummyDB de `test_api_fastapi.py` aligné sur
  `duplicate_count`. 35 passed / 5 pre-existing failures (SMB `archive_file` + orphelin).

## Prochaines étapes (à valider)
- Mécanisme d'archivage des doublons : déplacer les occurrences vers un espace d'archive
  (share `Archives_SEM`/`//192.168.10.241/Archives_SEM`) puis **soft-delete**
  (`is_deleted = true`, `deleted_at = NOW()`) des originaux, pour ne conserver qu'une copie
  physique → **dump PostgreSQL préalable requis** avant toute écriture.
- Réactiver ensuite les boutons du lightbox une fois la déduplication opérationnelle.

## Vérif (prod)
`GET /api/duplicates/64eccafcddcb64f2/details` renvoie 16 occurrences (RIB PERCEPTION MONTVAL
SUR LOIR.pdf ×14 + RIB COM COM.pdf + RIB.pdf), et l'explorateur affiche le badge "Doublon (16)".
