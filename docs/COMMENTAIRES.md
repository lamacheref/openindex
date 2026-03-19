# COMMENTAIRES

## 2026-03-19T10:44:31Z — build local à régénérer

- Version cible au moment de la note: `0.3.2`
- Commit de référence avant commit local de travail: `8859575`

### Décisions UI / moteur en cours

- Les commentaires explicatifs ne doivent plus apparaître dans l'interface opérateur.
- Les arbitrages de lecture, de progression et de protocole doivent être consignés ici ou dans la documentation d'exploitation.
- La progression actuelle doit évoluer vers une phase explicite de pré-estimation volumétrique avant exploration.
- Les indicateurs de progression doivent devenir la lecture principale ; les queues restent un outil de diagnostic.
- Les métadonnées de build locales doivent être injectées à chaque compilation d'image pour éviter l'état `unknown`.
