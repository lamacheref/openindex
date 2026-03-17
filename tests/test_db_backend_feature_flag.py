import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'api'))

import main as api_main


def test_get_db_adapter_invalid_backend(monkeypatch):
    monkeypatch.setenv('OPENINDEX_DB_BACKEND', 'sqlite')
    with pytest.raises(api_main.HTTPException) as exc:
        api_main.get_db_adapter()
    assert exc.value.status_code == 500
    assert 'invalide' in exc.value.detail


def test_get_db_adapter_postgresql(monkeypatch):
    monkeypatch.setenv('OPENINDEX_DB_BACKEND', 'postgresql')

    calls = {'count': 0}

    class FakeCursor:
        def execute(self, query):
            # Accept both the initial connection test and the table creation queries
            if query.strip().upper().startswith('SELECT 1'):
                return
            if 'CREATE TABLE IF NOT EXISTS crawl_configs' in query:
                return
            if 'CREATE INDEX IF NOT EXISTS idx_crawl_configs_created_at' in query:
                return
            if 'CREATE TABLE IF NOT EXISTS crawl_runs' in query:
                return
            if 'CREATE INDEX IF NOT EXISTS idx_crawl_runs_triggered_at' in query:
                return
            raise AssertionError(f"Unexpected query: {query}")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            pass

    def fake_connect(**kwargs):
        calls['count'] += 1
        assert kwargs['dbname']
        return FakeConn()

    monkeypatch.setattr(api_main.psycopg2, 'connect', fake_connect)

    adapter = api_main.get_db_adapter()
    assert isinstance(adapter, api_main.PostgreSQLAdapter)
    assert calls['count'] == 2
