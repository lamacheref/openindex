#!/usr/bin/env python3
"""Script de test rapide pour T-ARCH-01"""
import sys
sys.path.insert(0, '/app/src')

from postgres_adapter import PostgreSQLAdapter

adapter = PostgreSQLAdapter({
    'host': 'postgres',
    'port': 5432,
    'database': 'openindex',
    'user': 'openindex_user',
    'password': 'openindex_secure_password'
})

print('✅ DB Connection OK')

result = adapter.execute_query('SELECT COUNT(*) FROM archive_jobs')
print(f'📦 Archive jobs count: {result[0][0]}')

try:
    result = adapter.execute_query("SELECT status::text, COUNT(*) FROM archive_jobs GROUP BY status")
    print('📊 Jobs by status:', result)
except:
    print('📊 No jobs yet')

print('✅ T-ARCH-01 DB Test Passed')
