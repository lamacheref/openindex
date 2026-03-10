# Runbook hebdo J1 (court)

## Objectif

Standardiser un démarrage hebdomadaire en moins de 20 minutes avec un lot de contrôles reproductibles.

## Checklist de démarrage (ordre recommandé)

- [ ] Vérifier la version et le contexte de branche.
- [ ] Vérifier que les services montent (`api`, `web`, `db` SQLite via volume).
- [ ] Exécuter le jeu de tests API critique J1.
- [ ] Vérifier rapidement la santé applicative et les stats.
- [ ] Contrôler la présence du fichier SQLite actif.
- [ ] Archiver les constats dans `docs/` (date + anomalies).

## Commandes opératoires

```bash
# 1) Contexte git
python3 -V
git rev-parse --abbrev-ref HEAD
git status --short

# 2) Démarrage stack (variante active J3)
docker compose -f docker-compose.j3.yml up -d

# 3) Jeu de tests API critique reproductible
pytest -q tests/test_api_smoke_critical.py

# 4) Test incident SQLite (simulation absence/corruption + temps de recovery)
python3 scripts/test_sqlite_incident_runbook.py

# 5) Smoke runtime (optionnel mais recommandé)
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/stats
curl -s "http://localhost:8000/api/files?limit=5&offset=0"
curl -s "http://localhost:8000/api/db-explain?query_name=files_list"
```

## Procédure de reprise sur incident SQLite (absence/corruption)

### Symptômes typiques

- API indisponible au démarrage avec erreurs SQLite (`database disk image is malformed`, `unable to open database file`).
- Endpoint `/health` indisponible ou en erreur.
- Requêtes `/api/stats` ou `/api/files` en 5xx.

### Procédure pas-à-pas

1. **Stopper les écritures applicatives**
   - Arrêter temporairement l'API pour figer l'état.
2. **Sauvegarder l'état courant avant action**
   - Copier le fichier DB actuel vers un répertoire de quarantaine daté.
3. **Tenter une vérification d'intégrité**
   - `sqlite3 <db_path> "PRAGMA integrity_check;"`
4. **Si corruption confirmée, tenter une reconstruction**
   - `sqlite3 <db_path> ".recover" | sqlite3 <db_recovered_path>`
5. **Basculer l'API sur la base reconstruite**
   - Mettre à jour `OPENINDEX_DB_PATH` puis redémarrer l'API.
6. **Valider le service**
   - Vérifier `/health`, `/api/stats`, `/api/files`, `/api/db-explain`.
7. **Si reconstruction impossible**
   - Recréer une base SQLite saine (fichier neuf) puis relancer un crawl complet pour réindexation.
8. **Documenter l'incident**
   - Date, impact, cause probable, action corrective et action préventive dans `docs/`.

### Commandes utiles (exemple)

```bash
# Variables d'exemple
export OPENINDEX_DB_PATH=/data/openindex/index.db
export DB_BAK_DIR=/data/openindex/backup/$(date +%F_%H%M)
mkdir -p "$DB_BAK_DIR"

# 1) Backup
cp "$OPENINDEX_DB_PATH" "$DB_BAK_DIR/index.db.before_recovery"

# 2) Diagnostic
sqlite3 "$OPENINDEX_DB_PATH" "PRAGMA integrity_check;"

# 3) Reconstruction
sqlite3 "$OPENINDEX_DB_PATH" ".recover" | sqlite3 "$DB_BAK_DIR/index.recovered.db"

# 4) Validation minimale
sqlite3 "$DB_BAK_DIR/index.recovered.db" "PRAGMA integrity_check;"
```

## Critère de validation hebdo

Le démarrage hebdo est validé si :

- Le test `tests/test_api_smoke_critical.py` passe sans modification locale.
- Les 4 endpoints critiques répondent en 2xx.
- Aucun incident bloquant SQLite n'est ouvert.

## Validation testée du runbook incident

Une simulation locale est disponible via `scripts/test_sqlite_incident_runbook.py` pour vérifier:
- création/reprise depuis DB absente,
- détection de corruption,
- récupération depuis sauvegarde,
- mesure de temps de recovery.
