import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from postgres_adapter import PostgreSQLAdapter


class FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, query):
        self.queries.append(" ".join(query.split()))

    def fetchone(self):
        return [7]


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        raise AssertionError("rollback should not be called")


class FakeConnectionManager:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def test_calculate_duplicates_ensures_function_and_uses_public_schema(monkeypatch):
    adapter = PostgreSQLAdapter({})
    cursor = FakeCursor()
    conn = FakeConn(cursor)

    monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))

    result = adapter.calculate_duplicates()

    assert result == 7
    assert conn.committed is True
    assert any('CREATE OR REPLACE FUNCTION public.calculate_duplicates()' in q for q in cursor.queries)
    assert any('SELECT public.calculate_duplicates()' in q for q in cursor.queries)
