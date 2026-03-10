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
            assert query == 'SELECT 1'

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

    def fake_connect(**kwargs):
        calls['count'] += 1
        assert kwargs['dbname']
        return FakeConn()

    monkeypatch.setattr(api_main.psycopg2, 'connect', fake_connect)

    adapter = api_main.get_db_adapter()
    assert isinstance(adapter, api_main.PostgreSQLAdapter)
    assert calls['count'] == 1
