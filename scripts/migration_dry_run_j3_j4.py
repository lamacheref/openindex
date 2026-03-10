#!/usr/bin/env python3
"""Dry-run de migration J3 (SQLite) -> J4 (PostgreSQL) avec journal JSON."""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

try:
    import psycopg2
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None


def sqlite_stats(sqlite_path: str) -> dict:
    with sqlite3.connect(sqlite_path) as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM files')
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM files WHERE is_duplicate = 1')
        duplicates = cur.fetchone()[0]
    return {'total_files': total, 'duplicate_files': duplicates}


def postgres_stats(pg_config: dict) -> dict:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 non disponible")

    with psycopg2.connect(**pg_config) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM files')
            total = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM files WHERE is_duplicate = TRUE')
            duplicates = cur.fetchone()[0]
    return {'total_files': total, 'duplicate_files': duplicates}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite-path', default=os.getenv('OPENINDEX_DB_PATH', 'openindex.db'))
    parser.add_argument('--journal', default='docs/artifacts/migration_dry_run_j3_j4.json')
    parser.add_argument('--dry-run', action='store_true', default=True)
    args = parser.parse_args()

    if not os.path.exists(args.sqlite_path):
        raise SystemExit(f'SQLite introuvable: {args.sqlite_path}')

    pg_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'dbname': os.getenv('POSTGRES_DB', 'openindex'),
        'user': os.getenv('POSTGRES_USER', 'openindex_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password'),
    }

    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'mode': 'dry-run' if args.dry_run else 'apply',
        'sqlite': sqlite_stats(args.sqlite_path),
        'postgres_before': None,
        'delta_estimate': None,
        'rollback_plan': [
            '1) Stopper l\'API et figer les écritures.',
            '2) Rebasculer OPENINDEX_DB_BACKEND=sqlite.',
            '3) Restaurer le fichier SQLite depuis la dernière sauvegarde.',
            '4) Vérifier /health et /api/stats.',
        ],
    }

    try:
        report['postgres_before'] = postgres_stats(pg_config)
    except Exception as exc:
        report['postgres_before'] = {'error': str(exc)}

    if isinstance(report['postgres_before'], dict) and 'total_files' in report['postgres_before']:
        report['delta_estimate'] = {
            'files_to_sync': max(report['sqlite']['total_files'] - report['postgres_before']['total_files'], 0),
            'duplicates_to_sync': max(report['sqlite']['duplicate_files'] - report['postgres_before']['duplicate_files'], 0),
        }

    os.makedirs(os.path.dirname(args.journal), exist_ok=True)
    with open(args.journal, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
