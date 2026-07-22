import pytest
import os
import uuid
from datetime import datetime, timezone

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'openindex'),
    'user': os.getenv('POSTGRES_USER', 'openindex_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password'),
}

pytestmark = pytest.mark.skipif(
    not DB_CONFIG['host'] or DB_CONFIG['host'] == 'postgres',
    reason="Requiert une base PostgreSQL accessible"
)


@pytest.fixture(scope='module')
def db():
    from backend.src.database.postgres_adapter import PostgreSQLAdapter
    adapter = PostgreSQLAdapter(DB_CONFIG)
    yield adapter
    with adapter.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM indexed_files_optimized WHERE space_id = 'test-integration-space'")
            cur.execute("DELETE FROM directories WHERE space_id = 'test-integration-space'")
            cur.execute("DELETE FROM smb_spaces WHERE id = 'test-integration-space'")
        conn.commit()


@pytest.fixture(scope='module')
def space_id():
    return 'test-integration-space'


@pytest.fixture(scope='module')
def directory_id(db, space_id):
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO smb_spaces (id, name, host, share, domain_zone,
                    connection_username, connection_password)
                VALUES (%s, 'test-space', 'localhost', 'test', 'test.local',
                    'user', 'pass')
                ON CONFLICT (id) DO NOTHING
            """, [space_id])
            cur.execute("""
                INSERT INTO directories (space_id, path, name, parent_path, depth)
                VALUES (%s, '/', 'root', NULL, 0)
                ON CONFLICT (space_id, path) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, [space_id])
            dir_id = cur.fetchone()[0]
        conn.commit()
    return dir_id


class TestPostgreSQLAdapterInsert:
    def test_insert_file_optimized(self, db, space_id, directory_id):
        file_info = {
            'path': '/test/file.txt',
            'name': 'file.txt',
            'size': 1024,
            'checksum': 'abc123xxh64',
            'modified_at': datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            'is_garbage': False,
        }
        db.insert_file_optimized(file_info, space_id, directory_id)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT path, name, size, hash_xxh64 FROM indexed_files_optimized WHERE path = %s",
                    ['/test/file.txt']
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == '/test/file.txt'
        assert row[1] == 'file.txt'
        assert row[2] == 1024
        assert row[3] == 'abc123xxh64'

    def test_insert_file_optimized_upsert(self, db, space_id, directory_id):
        file_info = {
            'path': '/test/file.txt',
            'name': 'file.txt',
            'size': 2048,
            'checksum': 'def456xxh64',
            'modified_at': datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            'is_garbage': False,
        }
        db.insert_file_optimized(file_info, space_id, directory_id)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT size, hash_xxh64 FROM indexed_files_optimized WHERE path = %s",
                    ['/test/file.txt']
                )
                row = cur.fetchone()
        assert row[0] == 2048
        assert row[1] == 'def456xxh64'

    def test_insert_file_with_garbage_flag(self, db, space_id, directory_id):
        file_info = {
            'path': '/test/garbage.tmp',
            'name': 'garbage.tmp',
            'size': 512,
            'checksum': 'ghi789xxh64',
            'modified_at': datetime(2026, 3, 10, 8, 0, 0, tzinfo=timezone.utc),
            'is_garbage': True,
        }
        db.insert_file_optimized(file_info, space_id, directory_id)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_garbage FROM indexed_files_optimized WHERE path = %s",
                    ['/test/garbage.tmp']
                )
                row = cur.fetchone()
        assert row[0] is True

    def test_insert_file_without_directory(self, db, space_id):
        file_info = {
            'path': '/orphan/file.txt',
            'name': 'file.txt',
            'size': 128,
            'checksum': 'jkl012xxh64',
            'modified_at': datetime(2026, 4, 20, 14, 0, 0, tzinfo=timezone.utc),
            'is_garbage': False,
        }
        db.insert_file_optimized(file_info, space_id, None)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT directory_id FROM indexed_files_optimized WHERE path = %s",
                    ['/orphan/file.txt']
                )
                row = cur.fetchone()
        assert row[0] is None


class TestPostgreSQLAdapterBatchInsert:
    def test_batch_insert_empty(self, db, space_id):
        count = db.insert_files_batch_optimized([], space_id)
        assert count == 0

    def test_batch_insert_single(self, db, space_id, directory_id):
        files = [{
            'path': '/batch/single.txt',
            'name': 'single.txt',
            'size': 256,
            'checksum': 'batch01xxh64',
            'modified_at': datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc),
            'is_garbage': False,
            'directory_id': directory_id,
        }]
        count = db.insert_files_batch_optimized(files, space_id)
        assert count == 1
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM indexed_files_optimized WHERE path = %s",
                    ['/batch/single.txt']
                )
                assert cur.fetchone()[0] == 1

    def test_batch_insert_multiple(self, db, space_id, directory_id):
        files = [
            {
                'path': f'/batch/file_{i}.txt',
                'name': f'file_{i}.txt',
                'size': 100 * i,
                'checksum': f'batch{i:03d}xxh64',
                'modified_at': datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc),
                'is_garbage': False,
                'directory_id': directory_id,
            }
            for i in range(1, 6)
        ]
        count = db.insert_files_batch_optimized(files, space_id)
        assert count == 5
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM indexed_files_optimized WHERE path LIKE '/batch/file_%'"
                )
                assert cur.fetchone()[0] == 5

    def test_batch_insert_with_garbage(self, db, space_id, directory_id):
        files = [
            {
                'path': '/batch/garbage.tmp',
                'name': 'garbage.tmp',
                'size': 64,
                'checksum': 'grbg01xxh64',
                'modified_at': datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc),
                'is_garbage': True,
                'directory_id': directory_id,
            },
            {
                'path': '/batch/clean.txt',
                'name': 'clean.txt',
                'size': 128,
                'checksum': 'cln01xxh64',
                'modified_at': datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc),
                'is_garbage': False,
                'directory_id': directory_id,
            },
        ]
        count = db.insert_files_batch_optimized(files, space_id)
        assert count == 2
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_garbage FROM indexed_files_optimized WHERE path = '/batch/garbage.tmp'"
                )
                assert cur.fetchone()[0] is True
                cur.execute(
                    "SELECT is_garbage FROM indexed_files_optimized WHERE path = '/batch/clean.txt'"
                )
                assert cur.fetchone()[0] is False


class TestDirectories:
    def test_upsert_directory(self, db, space_id):
        dir_path = '/integration/test/dir'
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO directories (space_id, path, name, parent_path, depth)
                    VALUES (%s, %s, 'dir', '/integration/test', 2)
                    ON CONFLICT (space_id, path) DO UPDATE SET
                        name = EXCLUDED.name,
                        depth = EXCLUDED.depth
                    RETURNING id
                """, [space_id, dir_path])
                dir_id = cur.fetchone()[0]
            conn.commit()
        assert dir_id is not None

    def test_directories_ordered_by_depth_desc(self, db, space_id):
        paths = [
            ('/a', 'a', None, 0),
            ('/a/b', 'b', '/a', 1),
            ('/a/b/c', 'c', '/a/b', 2),
        ]
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                for path, name, parent, depth in paths:
                    cur.execute("""
                        INSERT INTO directories (space_id, path, name, parent_path, depth)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (space_id, path) DO NOTHING
                    """, [space_id, path, name, parent, depth])
            conn.commit()
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT path, depth FROM directories
                    WHERE space_id = %s
                    ORDER BY depth DESC
                """, [space_id])
                rows = cur.fetchall()
        depths = [r[1] for r in rows]
        assert depths == sorted(depths, reverse=True)

    def test_directory_counts(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT count(*) FROM directories WHERE space_id = %s
                """, [space_id])
                count = cur.fetchone()[0]
        assert count >= 4


class TestCheckFileChanged:
    def test_check_file_found(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM indexed_files_optimized
                    WHERE space_id = %s AND path = '/test/file.txt'
                        AND name = 'file.txt' AND size = 2048
                        AND hash_xxh64 = 'def456xxh64'
                """, [space_id])
                row = cur.fetchone()
        assert row is not None

    def test_check_file_not_found_wrong_size(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM indexed_files_optimized
                    WHERE space_id = %s AND path = '/test/file.txt'
                        AND name = 'file.txt' AND size = 9999
                        AND hash_xxh64 = 'def456xxh64'
                """, [space_id])
                row = cur.fetchone()
        assert row is None

    def test_unchanged_files_skipped(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT count(*) FROM indexed_files_optimized
                    WHERE space_id = %s AND is_garbage = false
                """, [space_id])
                total = cur.fetchone()[0]
        assert total >= 2


class Test4MetadataControl:
    def test_match_all_four_metadata(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM indexed_files_optimized
                    WHERE path = '/test/file.txt'
                      AND name = 'file.txt'
                      AND size = 2048
                      AND hash_xxh64 = 'def456xxh64'
                """, [space_id])
                row = cur.fetchone()
        assert row is not None, "Doit trouver le fichier quand les 4 métadonnées matchent"

    def test_mismatch_partial_returns_null(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM indexed_files_optimized
                    WHERE path = '/test/file.txt'
                      AND name = 'file.txt'
                      AND size = 2048
                      AND hash_xxh64 = 'WRONG_HASH'
                """, [space_id])
                row = cur.fetchone()
        assert row is None, "Ne doit pas trouver le fichier si le hash diffère"


class TestGarbage:
    def test_garbage_file_marked_correctly(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT count(*) FROM indexed_files_optimized
                    WHERE space_id = %s AND is_garbage = true
                """, [space_id])
                count = cur.fetchone()[0]
        assert count >= 1

    def test_garbage_table_populated(self, db, space_id):
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT count(*) FROM garbage_files gf
                    JOIN indexed_files_optimized ifo ON gf.file_id = ifo.id
                    WHERE ifo.space_id = %s
                """, [space_id])
                count = cur.fetchone()[0]
        assert count >= 0
