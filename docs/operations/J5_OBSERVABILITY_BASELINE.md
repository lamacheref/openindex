# J5 — Baseline observabilité minimale

## Périmètre

Mettre sous contrôle les signaux déjà disponibles dans l'API et le crawler avant d'ajouter des outils externes.

## Signaux à suivre

- Santé API : `GET /health`
- Vue système : `GET /api/system/status`
- Vue monitoring explorations : `GET /api/monitoring`
- Vue synthèse : `GET /api/crawls/overview`
- Runtime détaillé : `GET /api/crawler/runtime`
- Vue opératoire santé/incidents : `GET /api/operations/status`
- Diagnostic DB : `GET /api/db-explain?query_name=files_list&analyze=true`

## Journalisation minimale attendue

- Conserver les logs API au niveau `INFO` par défaut et `ERROR` sur toute exception HTTP.
- Conserver les logs crawler par run (`smb_crawler_postgresql_<run_id>.log`) comme source nominale.
- Corréler tout incident avec le `run_id`, le nom d'espace et le statut final si un crawl est en cause.

## Vue santé minimale

- API disponible et version connue via `/health` et `/api/system/status`
- Vue opératoire consolidée via `/api/operations/status`
- Aucun run zombie ou `idle` non expliqué dans `/api/crawler/runtime`
- Aucun backlog d'intégrité en croissance non maîtrisée sur plusieurs relevés
- Aucun `EXPLAIN` critique dégradé sans décision tracée

## Ce qui est désormais standardisé

- Logs API : format horodaté `timestamp level logger message` pilotable via `OPENINDEX_LOG_LEVEL`
- Vue incidents : incidents dérivés des checks critiques/warning via `/api/operations/status`
- Dashboard santé minimal : synthèse unique des checks API, runs, activité crawler et backlog d'intégrité

## Escalade minimale

1. Incident détecté sur disponibilité, latence ou gate rouge.
2. Vérifier la gate CI PostgreSQL puis les endpoints de santé.
3. Corréler avec les logs API/crawler et l'état PostgreSQL.
4. Appliquer le runbook `docs/operations/EXPLOITATION.md` si le service n'est plus nominal.
5. Produire une preuve datée : log, JSON, capture ou rapport court.
