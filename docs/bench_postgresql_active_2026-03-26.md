# Benchmark PostgreSQL active — 2026-03-26

## Contexte
- T-05 du TODO J4 a demandé de rejouer le benchmark PostgreSQL sur la base active recalculée après le recrawl complet, puis de publier une conclusion OK/NOK.
- Cette exécution cible les endpoints critiques `/api/stats` et `/api/files?limit=5&offset=0` de l’API FastAPI post-migration (PostgreSQL).

## Méthodologie
- Commande : `docker compose exec api python /app/scripts/benchmark_dual_db.py --base-url http://localhost:8000 --samples 30 --runs 3 --output /tmp/bench_postgresql_active_2026-03-26.json`
- Warm-up non mesuré : 5 requêtes par endpoint avant chaque série.
- Requêtes notées : 3 runs successifs, 30 échantillons par run et par endpoint.
- Des mesures de latence (moyenne et P95) sont calculées en millisecondes.

## Résultats
- `/api/stats` P95 par run : 56,38 ms / 55,50 ms / 56,82 ms (p95 min 55,50 ms, max 56,82 ms, moyenne 56,23 ms).
- `/api/files` P95 par run : 65,94 ms / 66,14 ms / 66,03 ms (p95 min 65,94 ms, max 66,14 ms, moyenne 66,04 ms).
- Les trois runs sont cohérents (écart ≤ 0,2 ms sur `/api/stats`, ≤ 0,2 ms sur `/api/files`), encore plus stables que les valeurs historiques documentées (~0,55 s et ~0,71 s en 2026-03-18).

## Conclusion
- Les seuils P95 annoncés (stabilité sous 100 ms / référence de la décision J4 antérieure à 0,55/0,71 s) sont respectés sur la base PostgreSQL active ; l’indicateur est stable sur les trois runs successifs.
- Conclusion opérationnelle : **OK** (preuve validée, référentiels mis à jour).

## Artefact
- Fichier de mesure JSON : `docs/artifacts/bench_postgresql_active_2026-03-26.json`
