"""Tests unitaires pour la protection contre les deadlocks PostgreSQL.

Ces tests valident:
- La vérification préalable de l'existence des colonnes
- Le paramètre lock_timeout
- La gestion de LockNotAvailable
- Le rétro-remplissage conditionnel
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'api'))

import pytest


class FakeCursor:
    """Simule un curseur PostgreSQL pour les tests."""
    
    def __init__(self, column_exists=True, has_null_values=False):
        self.queries = []
        self._column_exists = column_exists
        self._has_null_values = has_null_values
        self._rowcount = 0
    
    def execute(self, query, params=None):
        """Enregistre la requête exécutée."""
        normalized = " ".join(query.split())
        self.queries.append(normalized)
    
    def fetchone(self):
        """Simule le retour de résultats selon la requête."""
        if "information_schema.columns" in self.queries[-1]:
            return [self._column_exists]
        if "SELECT EXISTS (SELECT 1 FROM files WHERE crawl_config_id IS NULL" in self.queries[-1]:
            return [self._has_null_values]
        return [0]
    
    @property
    def rowcount(self):
        return self._rowcount


class FakeConn:
    """Simule une connexion PostgreSQL pour les tests."""
    
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
    
    def cursor(self):
        return self._cursor
    
    def commit(self):
        self.committed = True
    
    def rollback(self):
        self.rolled_back = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnectionManager:
    """Context manager pour simuler get_connection."""
    
    def __init__(self, conn):
        self.conn = conn
    
    def __enter__(self):
        return self.conn
    
    def __exit__(self, exc_type, exc, tb):
        return False


class TestEnsureFileSpaceLinking:
    """Tests pour ensure_file_space_linking avec protection anti-deadlock."""
    
    def test_column_exists_skips_alter_table(self, monkeypatch):
        """Si la colonne existe déjà, ALTER TABLE ne doit pas être exécuté."""
        from postgres_adapter import PostgreSQLAdapter
        
        adapter = PostgreSQLAdapter({})
        cursor = FakeCursor(column_exists=True, has_null_values=False)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        adapter.ensure_file_space_linking()
        
        # Vérifier que le lock_timeout est défini
        assert any("SET LOCAL lock_timeout = '5s'" in q for q in cursor.queries)
        
        # Vérifier la vérification d'existence
        assert any("information_schema.columns" in q for q in cursor.queries)
        
        # Vérifier qu'ALTER TABLE n'est PAS exécuté
        assert not any("ALTER TABLE files ADD COLUMN crawl_config_id" in q for q in cursor.queries)
        
        # La transaction doit être commitée
        assert conn.committed
        assert not conn.rolled_back
    
    def test_column_missing_executes_alter_table(self, monkeypatch):
        """Si la colonne n'existe pas, ALTER TABLE doit être exécuté."""
        from postgres_adapter import PostgreSQLAdapter
        
        adapter = PostgreSQLAdapter({})
        cursor = FakeCursor(column_exists=False, has_null_values=False)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        adapter.ensure_file_space_linking()
        
        # Vérifier qu'ALTER TABLE EST exécuté
        assert any("ALTER TABLE files ADD COLUMN crawl_config_id" in q for q in cursor.queries)
        
        # L'index doit être créé
        assert any("CREATE INDEX IF NOT EXISTS idx_files_crawl_config_id" in q for q in cursor.queries)
        
        assert conn.committed
    
    def test_no_null_values_skips_update(self, monkeypatch):
        """Si aucune valeur NULL, l'UPDATE ne doit pas être exécuté."""
        from postgres_adapter import PostgreSQLAdapter
        
        adapter = PostgreSQLAdapter({})
        cursor = FakeCursor(column_exists=True, has_null_values=False)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        adapter.ensure_file_space_linking()
        
        # Vérifier que l'UPDATE n'est PAS exécuté
        assert not any("UPDATE files AS f SET crawl_config_id" in q for q in cursor.queries)
        
        assert conn.committed
    
    def test_has_null_values_executes_update(self, monkeypatch):
        """Si des valeurs NULL existent, l'UPDATE doit être exécuté."""
        from postgres_adapter import PostgreSQLAdapter
        
        adapter = PostgreSQLAdapter({})
        cursor = FakeCursor(column_exists=True, has_null_values=True)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        adapter.ensure_file_space_linking()
        
        # Vérifier que l'UPDATE EST exécuté
        assert any("UPDATE files AS f SET crawl_config_id" in q for q in cursor.queries)
        
        assert conn.committed


class TestLockTimeout:
    """Tests pour le paramètre lock_timeout."""
    
    def test_lock_timeout_is_set(self, monkeypatch):
        """Le lock_timeout de 5s doit être défini dans toutes les transactions DDL."""
        from postgres_adapter import PostgreSQLAdapter
        
        adapter = PostgreSQLAdapter({})
        cursor = FakeCursor(column_exists=True, has_null_values=False)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        adapter.ensure_file_space_linking()
        
        # Vérifier que SET LOCAL lock_timeout est appelé en premier
        first_query = cursor.queries[0]
        assert "SET LOCAL lock_timeout = '5s'" in first_query


class TestLockNotAvailableHandling:
    """Tests pour la gestion de LockNotAvailable."""
    
    def test_lock_timeout_rollback_and_reraise(self, monkeypatch):
        """En cas de LockNotAvailable, doit faire rollback et re-propager l'exception."""
        from postgres_adapter import PostgreSQLAdapter
        import psycopg2.errors
        
        adapter = PostgreSQLAdapter({})
        
        class LockTimeoutCursor(FakeCursor):
            def execute(self, query, params=None):
                super().execute(query, params)
                if "SET LOCAL lock_timeout" in query:
                    return
                if "information_schema.columns" in query:
                    raise psycopg2.errors.LockNotAvailable("lock timeout")
        
        cursor = LockTimeoutCursor(column_exists=True, has_null_values=False)
        conn = FakeConn(cursor)
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConnectionManager(conn))
        
        with pytest.raises(psycopg2.errors.LockNotAvailable):
            adapter.ensure_file_space_linking()
        
        # Vérifier que rollback a été appelé
        assert conn.rolled_back
        assert not conn.committed


class TestEnsureCrawlTables:
    """Tests pour ensure_crawl_tables dans api/main.py."""
    
    def test_column_checks_before_alter_table(self, monkeypatch):
        """Vérifie que les colonnes sont checkées avant ALTER TABLE."""
        import main as api_main
        
        calls = {'queries': []}
        
        class TrackingCursor:
            def __init__(self):
                self._column_checks = {
                    'crawl_config_id': False,  # N'existe pas encore
                    'is_archive': True,  # Existe déjà
                }
                self._check_index = 0
            
            def execute(self, query, params=None):
                calls['queries'].append(" ".join(query.split()))
                
                # Simuler la vérification d'existence des colonnes
                if "information_schema.columns" in query:
                    if "crawl_config_id" in query:
                        self._check_index += 1
                    return
                
                # Les ALTER TABLE pour crawl_config_id doivent être exécutés
                if "ALTER TABLE files ADD COLUMN crawl_config_id" in query:
                    return
                
                # L'ALTER TABLE pour is_archive ne doit PAS être exécuté
                if "ALTER TABLE crawl_configs ADD COLUMN is_archive" in query:
                    raise AssertionError("is_archive ALTER should not be called - column exists")
            
            def fetchone(self):
                if "crawl_config_id" in calls['queries'][-1]:
                    return [self._column_checks['crawl_config_id']]
                if "is_archive" in calls['queries'][-1]:
                    return [self._column_checks['is_archive']]
                if "SELECT EXISTS (SELECT 1 FROM files" in calls['queries'][-1]:
                    return [False]  # No null values
                return [0]
            
            @property
            def rowcount(self):
                return 0
        
        class FakeConn:
            def cursor(self):
                return TrackingCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
        
        adapter = api_main.PostgreSQLAdapter({})
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConn())
        
        adapter.ensure_crawl_tables()
        
        # Vérifier que le lock_timeout est défini
        assert any("SET LOCAL lock_timeout = '5s'" in q for q in calls['queries'])
        
        # Vérifier que la vérification de colonne est faite
        assert any("information_schema.columns" in q for q in calls['queries'])
    
    def test_lock_timeout_not_raised(self, monkeypatch):
        """LockNotAvailable ne doit pas propager l'erreur (permettre le démarrage de l'API)."""
        import main as api_main
        import psycopg2.errors
        
        class LockTimeoutCursor:
            def execute(self, query, params=None):
                if "SET LOCAL lock_timeout" in query:
                    return
                if "CREATE TABLE IF NOT EXISTS crawl_configs" in query:
                    return
                raise psycopg2.errors.LockNotAvailable("lock timeout")
            
            def fetchone(self):
                return [True]
            
            @property
            def rowcount(self):
                return 0
        
        class FakeConn:
            def cursor(self):
                return LockTimeoutCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
        
        adapter = api_main.PostgreSQLAdapter({})
        monkeypatch.setattr(adapter, 'get_connection', lambda: FakeConn())
        
        # Ne doit pas lever d'exception
        adapter.ensure_crawl_tables()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
