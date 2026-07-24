import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from workers.indexer_worker import (
    IndexerWorker,
    IndexerJob,
    IndexerStatus,
)

import backend.src
import types
_crawl_utils_mod = types.ModuleType('backend.src.crawl_utils')
_crawl_utils_mod.get_file_info = MagicMock()
_crawl_utils_mod.SMBClient = MagicMock()
backend.src.crawl_utils = _crawl_utils_mod
sys.modules['backend.src.crawl_utils'] = _crawl_utils_mod


class FakePhaseClient:
    def __init__(self, dir_tree=None):
        self.dir_tree = dir_tree or {}
        self.list_dir_calls = []

    def list_dir(self, path):
        self.list_dir_calls.append(path)
        return self.dir_tree.get(path, [])


class TestPhaseABFSDirectories:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w._stop_event = threading.Event()
        yield w

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_traverses_breadth_first(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        root = '//SHARE/root'
        client = FakePhaseClient({
            root: [
                {'name': 'dir_a', 'is_directory': True},
                {'name': 'dir_b', 'is_directory': True},
                {'name': 'file1.txt', 'is_directory': False},
            ],
            f'{root}/dir_a': [
                {'name': 'dir_a1', 'is_directory': True},
                {'name': 'f_a.txt', 'is_directory': False},
            ],
            f'{root}/dir_b': [
                {'name': 'dir_b1', 'is_directory': True},
            ],
            f'{root}/dir_a/dir_a1': [
                {'name': 'f_a1.txt', 'is_directory': False},
            ],
            f'{root}/dir_b/dir_b1': [],
        })

        job = IndexerJob(
            id='job-bfs', path=root, config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        dir_count = worker._phase_a_bfs_directories(client, root, 'space-1', job)

        assert dir_count == 5
        expected_order = [root, f'{root}/dir_a', f'{root}/dir_b', f'{root}/dir_a/dir_a1', f'{root}/dir_b/dir_b1']
        inserted_paths = [
            c[0][1][1] for c in mock_db.execute_query.call_args_list
            if 'INSERT INTO directories' in c[0][0]
        ]
        assert inserted_paths == expected_order

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_upsert_on_conflict(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.execute_query.return_value = None

        client = FakePhaseClient({
            '/root': [
                {'name': 'sub', 'is_directory': True},
            ],
            '/root/sub': [],
        })

        job = IndexerJob(
            id='job-ups', path='/root', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_a_bfs_directories(client, '/root', 'space-u1', job)

        for call_args in mock_db.execute_query.call_args_list:
            sql = call_args[0][0]
            assert 'ON CONFLICT' in sql
            assert 'DO UPDATE SET' in sql

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_depth_and_parent_path(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        client = FakePhaseClient({
            '/top': [
                {'name': 'mid', 'is_directory': True},
            ],
            '/top/mid': [
                {'name': 'bot', 'is_directory': True},
            ],
            '/top/mid/bot': [],
        })

        job = IndexerJob(
            id='job-depth', path='/top', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_a_bfs_directories(client, '/top', 'space-d1', job)

        inserted = [
            c[0][1] for c in mock_db.execute_query.call_args_list
            if 'INSERT INTO directories' in c[0][0]
        ]
        assert len(inserted) == 3

        root_params = inserted[0]
        assert root_params[3] == ''
        assert root_params[4] == 0

        mid_params = inserted[1]
        assert mid_params[3] == '/top'
        assert mid_params[4] == 1

        bot_params = inserted[2]
        assert bot_params[3] == '/top/mid'
        assert bot_params[4] == 2

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_stop_event_interrupts(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        root = '//SHARE/root'
        client = FakePhaseClient({
            root: [
                {'name': 'a', 'is_directory': True},
            ],
            f'{root}/a': [],
        })

        def side_effect(*args, **kwargs):
            worker._stop_event.set()
            return None

        mock_db.execute_query.side_effect = side_effect

        job = IndexerJob(
            id='job-stop', path=root, config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        with pytest.raises(InterruptedError, match='interrompue'):
            worker._phase_a_bfs_directories(client, root, 'space-s1', job)

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_handles_list_error(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.execute_query.side_effect = [None, None, None]

        root = '//SHARE/root'
        bad_dir = f'{root}/bad'

        class ErrorClient:
            def __init__(self):
                self.calls = []

            def list_dir(self, path):
                self.calls.append(path)
                if path == bad_dir:
                    raise Exception('list_dir failed')
                return [{'name': 'bad', 'is_directory': True}]

        client = ErrorClient()

        job = IndexerJob(
            id='job-err', path=root, config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_a_bfs_directories(client, root, 'space-e1', job)

        assert bad_dir in client.calls
        assert worker._metrics['errors_count'] >= 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_counts_correctly(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        client = FakePhaseClient({
            '/': [{'name': 'only_file.txt', 'is_directory': False}],
        })

        job = IndexerJob(
            id='job-count', path='/', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        count = worker._phase_a_bfs_directories(client, '/', 'space-c1', job)
        assert count == 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_bfs_empty_root(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        client = FakePhaseClient({'/': []})

        job = IndexerJob(
            id='job-empty', path='/', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        count = worker._phase_a_bfs_directories(client, '/', 'space-em', job)
        assert count == 1


class TestPhaseBListFiles:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w._stop_event = threading.Event()
        yield w

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_processes_by_path_asc(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [
                ('dir-3', '/a/b/c', 'c'),
                ('dir-2', '/a/b', 'b'),
                ('dir-1', '/a', 'a'),
            ],
            [],
            [],
            [],
        ]

        mock_get_info.side_effect = lambda client, path: {
            'path': path, 'name': 'x.txt', 'size': 100,
            'checksum': 'h1', 'modified_at': datetime.now(timezone.utc),
        }.get('path') and {
            'path': path, 'name': 'x.txt', 'size': 100,
            'checksum': 'h1', 'modified_at': datetime.now(timezone.utc),
        }

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'x.txt', 'is_directory': False, 'size': 100, 'mtime': datetime.now(timezone.utc)},
        ]

        job = IndexerJob(
            id='job-bu', path='/a', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        config = {'id': 'c1', 'name': 'T'}

        worker._phase_b_list_files(client, 'space-bu1', job, config)

        dir_query = mock_db.execute_query.call_args_list[0]
        assert 'ORDER BY path ASC' in dir_query[0][0]

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_metadata_change_detection(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/root', 'root')],
            [('existing-id',)],   # file already exists -> skip
            None,
        ]

        mock_get_info.return_value = None

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'f.txt', 'is_directory': False, 'size': 500, 'mtime': datetime(2026, 1, 1, tzinfo=timezone.utc)},
        ]

        job = IndexerJob(
            id='job-md', path='/root', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_b_list_files(client, 'space-md1', job, {'id': 'c1', 'name': 'T'})

        check_query = mock_db.execute_query.call_args_list[1]
        sql, params = check_query[0]

        assert 'indexed_files_optimized' in sql
        assert params[0] == '/root/f.txt'
        assert params[1] == 'f.txt'
        assert params[2] == 500

        assert params[3] is not None
        assert params[4] is not None

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_fast_queue_dispatch(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/small', 'small')],
            [],
            None,
        ]

        mock_get_info.return_value = {
            'path': '/small/tiny.txt', 'name': 'tiny.txt', 'size': 1024,
            'checksum': 'h1', 'modified_at': datetime.now(timezone.utc),
        }

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'tiny.txt', 'is_directory': False, 'size': 1024, 'mtime': datetime.now(timezone.utc)},
        ]

        job = IndexerJob(
            id='job-fq', path='/small', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_b_list_files(client, 'space-fq1', job, {'id': 'c1', 'name': 'T'})

        assert job.files_indexed == 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_large_file_listed_in_phase_b(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/big', 'big')],
            [],
        ]

        mock_get_info.return_value = {
            'path': '/big/huge.iso', 'name': 'huge.iso', 'size': 300 * 1024 * 1024,
            'checksum': None, 'modified_at': datetime.now(timezone.utc),
        }

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'huge.iso', 'is_directory': False, 'size': 300 * 1024 * 1024, 'mtime': datetime.now(timezone.utc)},
        ]

        job = IndexerJob(
            id='job-sq', path='/big', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_b_list_files(client, 'space-sq1', job, {'id': 'c1', 'name': 'T'})

        assert job.files_indexed == 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_unchanged_files_skipped(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/root', 'root')],
            [('existing-file-id',)],
        ]

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'same.txt', 'is_directory': False, 'size': 200, 'mtime': datetime(2026, 1, 1, tzinfo=timezone.utc)},
        ]

        job = IndexerJob(
            id='job-skp', path='/root', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        worker._phase_b_list_files(client, 'space-skp1', job, {'id': 'c1', 'name': 'T'})

        assert job.files_found == 1
        assert job.files_indexed == 0
        mock_get_info.assert_not_called()

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_phase_b_batch_insert(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/batch', 'batch')],
            [],
        ]

        mock_get_info.return_value = {
            'path': '/batch/f1.txt', 'name': 'f1.txt', 'size': 100,
            'checksum': None, 'modified_at': datetime.now(timezone.utc),
        }

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'f1.txt', 'is_directory': False, 'size': 100, 'mtime': datetime.now(timezone.utc)},
        ]

        job = IndexerJob(
            id='job-bt', path='/batch', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        with patch.object(worker, '_flush_file_batch') as mock_flush:
            worker._phase_b_list_files(client, 'space-bt1', job, {'id': 'c1', 'name': 'T'})
            mock_flush.assert_called_once()

        assert job.files_indexed == 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_garbage_flag_in_phase_b(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.side_effect = [
            [('dir-1', '/garb', 'garb')],
            [],
        ]

        mock_get_info.return_value = {
            'path': '/garb/temp.tmp', 'name': 'temp.tmp', 'size': 50,
            'checksum': None, 'modified_at': datetime.now(timezone.utc),
        }

        client = MagicMock()
        client.list_dir.return_value = [
            {'name': 'temp.tmp', 'is_directory': False, 'size': 50, 'mtime': datetime.now(timezone.utc)},
        ]

        job = IndexerJob(
            id='job-gb', path='/garb', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        with patch.object(worker, '_flush_file_batch') as mock_flush:
            worker._phase_b_list_files(client, 'space-gb1', job, {'id': 'c1', 'name': 'T'})
            flushed = mock_flush.call_args[0][0]
            assert len(flushed) == 1
            assert flushed[0].get('is_garbage') is True

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_phase_b_stop_event(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.return_value = [
            ('dir-1', '/first', 'first'),
            ('dir-2', '/second', 'second'),
        ]

        def list_dir_side_effect(path):
            worker._stop_event.set()
            return []

        client = MagicMock()
        client.list_dir.side_effect = list_dir_side_effect

        job = IndexerJob(
            id='job-stp', path='/', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        with patch.object(worker, '_flush_file_batch') as mock_flush:
            with pytest.raises(InterruptedError, match='interrompue'):
                worker._phase_b_list_files(client, 'space-stp1', job, {'id': 'c1', 'name': 'T'})

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    @patch('backend.src.crawl_utils.get_file_info')
    def test_phase_b_no_directories(self, mock_get_info, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_db.execute_query.return_value = None

        client = MagicMock()

        job = IndexerJob(
            id='job-nod', path='/empty', config_id='c1', config_name='T',
            status=IndexerStatus.PENDING, created_at=datetime.now(timezone.utc))

        result = worker._phase_b_list_files(client, 'space-nod1', job, {'id': 'c1', 'name': 'T'})
        assert result == 0


class TestInsertFileIndexedOptimized:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w.current_job = MagicMock()
        w.current_job.id = 'test-job'
        return w

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_calls_optimized_method(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/test/doc.txt',
            'name': 'doc.txt',
            'size': 1024,
            'checksum': 'xxh64_hash',
            'modified_at': datetime.now(timezone.utc),
        }

        worker._insert_file(file_info, 'cfg-1', 'space-1', 'dir-1')

        mock_db.insert_file_optimized.assert_called_once_with(
            file_info, 'space-1', 'dir-1',
        )

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_detects_garbage_tmp(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/test/scratch.tmp',
            'name': 'scratch.tmp',
            'size': 200,
            'checksum': 'h6',
            'modified_at': datetime.now(timezone.utc),
        }

        worker._insert_file(file_info, 'cfg-2', 'space-2', 'dir-2')

        assert file_info.get('is_garbage') is True
        mock_db.execute_query.assert_called_once()
        sql = mock_db.execute_query.call_args[0][0]
        assert 'garbage_files' in sql

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_detects_garbage_thumbs_db(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/test/Thumbs.db',
            'name': 'Thumbs.db',
            'size': 100,
            'checksum': 'h7',
            'modified_at': datetime.now(timezone.utc),
        }

        worker._insert_file(file_info, 'cfg-3', 'space-3', 'dir-3')

        assert file_info.get('is_garbage') is True

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_clean_file_not_garbage(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/test/report.pdf',
            'name': 'report.pdf',
            'size': 5000,
            'checksum': 'h8',
            'modified_at': datetime.now(timezone.utc),
        }

        worker._insert_file(file_info, 'cfg-4', 'space-4', 'dir-4')

        assert file_info.get('is_garbage') is False
        mock_db.execute_query.assert_not_called()

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_locked_file_triggers_retry(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.insert_file_optimized.side_effect = Exception('Sharing violation')

        file_info = {
            'path': '/test/locked.xlsx',
            'name': 'locked.xlsx',
            'size': 3000,
            'checksum': 'h9',
            'modified_at': datetime.now(timezone.utc),
        }

        with patch.object(worker, '_should_retry_file', return_value=True), \
             patch.object(worker, '_add_file_to_retry') as mock_add_retry:
            worker._insert_file(file_info, 'cfg-5', 'space-5', 'dir-5')
            mock_add_retry.assert_called_once()

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_locked_file_exhausted_retries(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.insert_file_optimized.side_effect = Exception('Permission denied')

        file_info = {
            'path': '/test/stuck.docx',
            'name': 'stuck.docx',
            'size': 2000,
            'checksum': 'h10',
            'modified_at': datetime.now(timezone.utc),
        }

        with patch.object(worker, '_should_retry_file', return_value=False), \
             patch.object(worker, '_add_file_to_retry') as mock_add_retry:
            worker._insert_file(file_info, 'cfg-6', 'space-6', 'dir-6')
            mock_add_retry.assert_not_called()

        assert worker._metrics['errors_count'] >= 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_generic_error_increments_count(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.insert_file_optimized.side_effect = Exception('Network timeout')

        file_info = {
            'path': '/test/remote.bin',
            'name': 'remote.bin',
            'size': 1000,
            'checksum': 'h11',
            'modified_at': datetime.now(timezone.utc),
        }

        worker._is_file_locked = MagicMock(return_value=False)
        errors_before = worker._metrics['errors_count']

        worker._insert_file(file_info, 'cfg-7', 'space-7', 'dir-7')

        assert worker._metrics['errors_count'] == errors_before + 1

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_insert_generic_db_error_does_not_call_mark_missing(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.insert_file_optimized.side_effect = Exception('no such file')

        file_info = {
            'path': '/test/ghost.txt',
            'name': 'ghost.txt',
            'size': 100,
            'checksum': 'h12',
            'modified_at': datetime.now(timezone.utc),
        }

        with patch.object(worker, '_mark_file_as_missing') as mock_mark:
            worker._insert_file(file_info, 'cfg-8', 'space-8', 'dir-8')
            mock_mark.assert_not_called()
        assert worker._metrics['errors_count'] >= 1


class TestIsFileLocked:
    @pytest.fixture
    def worker(self):
        return IndexerWorker(poll_interval=1)

    def test_locked_patterns_detected(self, worker):
        for msg in [
            'Access denied',
            'Permission denied',
            'File is locked by another process',
            'Sharing violation on path',
            'being used by another process',
        ]:
            assert worker._is_file_locked(msg), f'Should detect: {msg}'

    def test_non_locked_patterns(self, worker):
        for msg in [
            'File not found',
            'Network timeout',
            'Disk full',
            'Generic IO error',
        ]:
            assert not worker._is_file_locked(msg), f'Should NOT detect: {msg}'


class TestIsFileMissing:
    @pytest.fixture
    def worker(self):
        return IndexerWorker(poll_interval=1)

    def test_missing_patterns_detected(self, worker):
        for msg in [
            'File not found',
            'No such file or directory',
            'The file does not exist',
            'Path not found',
            'File disappeared during processing',
        ]:
            assert worker._is_file_missing(msg), f'Should detect: {msg}'

    def test_non_missing_patterns(self, worker):
        for msg in [
            'Access denied',
            'File is locked',
            'Network error',
            'Disk full',
        ]:
            assert not worker._is_file_missing(msg), f'Should NOT detect: {msg}'


class TestIsFileConflict:
    @pytest.fixture
    def worker(self):
        return IndexerWorker(poll_interval=1)

    def test_conflict_patterns_detected(self, worker):
        for msg in [
            'File already exists',
            'Conflict detected during write',
            'Duplicate file entry',
            'Hash mismatch for file',
            'Checksum mismatch',
            'Different content at path',
        ]:
            assert worker._is_file_conflict(msg), f'Should detect: {msg}'

    def test_non_conflict_patterns(self, worker):
        for msg in [
            'File not found',
            'Access denied',
            'Network error',
            'Generic error',
        ]:
            assert not worker._is_file_conflict(msg), f'Should NOT detect: {msg}'


class TestIsGarbageFile:
    @pytest.fixture
    def worker(self):
        return IndexerWorker(poll_interval=1)

    @pytest.mark.parametrize('name', [
        'temp.tmp', '~backup.txt', 'Thumbs.db', '.DS_Store',
        'old.bak', 'edit.swp',
    ])
    def test_garbage_patterns(self, worker, name):
        assert worker._is_garbage_file(name), f'{name} should be garbage'

    @pytest.mark.parametrize('name', [
        'document.pdf', 'image.jpg', 'notes.txt', 'script.py',
        'data.csv', 'index.html',
    ])
    def test_clean_patterns(self, worker, name):
        assert not worker._is_garbage_file(name), f'{name} should NOT be garbage'


class TestGetQueueType:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w.SLOW_THRESHOLD_BYTES = 200 * 1024 * 1024
        return w

    def test_small_file_is_fast(self, worker):
        assert worker._get_queue_type(1024) == 'fast'

    def test_large_file_is_slow(self, worker):
        assert worker._get_queue_type(300 * 1024 * 1024) == 'slow'

    def test_exact_threshold_is_slow(self, worker):
        assert worker._get_queue_type(200 * 1024 * 1024) == 'slow'

    def test_zero_size_is_fast(self, worker):
        assert worker._get_queue_type(0) == 'fast'


class TestHandleFileConflict:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w.current_job = MagicMock()
        w.current_job.id = 'conflict-job'
        return w

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_conflict_renames_file(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/share/doc.txt',
            'name': 'doc.txt',
            'checksum': 'abc123',
            'size': 1024,
        }

        worker._handle_file_conflict(file_info, 'cfg-c1', 'already exists')

        assert file_info['name'] == 'doc.txt_conflict_1'
        assert file_info['path'] == '/share/doc.txt_conflict_1'

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_conflict_without_extension(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/share/README',
            'name': 'README',
            'checksum': 'def456',
            'size': 2048,
        }

        worker._handle_file_conflict(file_info, 'cfg-c2', 'conflict')

        assert file_info['name'] == 'README_conflict_1'

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_increments_existing_conflict_suffix(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/share/README_conflict_1',
            'name': 'README_conflict_1',
            'checksum': 'def456',
            'size': 2048,
        }

        worker._handle_file_conflict(file_info, 'cfg-c3', 'conflict')

        assert file_info['name'] == 'README_conflict_2'

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_records_conflict_in_db(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/share/data.csv',
            'name': 'data.csv',
            'checksum': 'ghi789',
            'size': 512,
        }

        worker._handle_file_conflict(file_info, 'cfg-c3', 'duplicate entry')

        calls = mock_db.execute_query.call_args_list
        conflict_call = calls[0]
        sql = conflict_call[0][0]
        assert 'file_conflicts' in sql
        assert 'original_path' in sql
        assert 'conflict_path' in sql

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_conflict_calls_insert_file(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        file_info = {
            'path': '/share/conflict.txt',
            'name': 'conflict.txt',
            'checksum': 'jkl012',
            'size': 256,
        }

        with patch.object(worker, '_insert_file') as mock_insert:
            worker._handle_file_conflict(file_info, 'cfg-c4', 'already exists', 'space-c', 'dir-c')
            mock_insert.assert_called_once_with(
                file_info, 'cfg-c4', 'space-c', 'dir-c',
            )


class TestGetGarbagePattern:
    @pytest.fixture
    def worker(self):
        return IndexerWorker(poll_interval=1)

    def test_tmp_pattern(self, worker):
        assert worker._get_garbage_pattern('file.tmp') == '*.tmp'

    def test_tilde_pattern(self, worker):
        assert worker._get_garbage_pattern('~backup') == '~*'

    def test_thumbs_db(self, worker):
        assert worker._get_garbage_pattern('Thumbs.db') == 'Thumbs.db'

    def test_ds_store(self, worker):
        assert worker._get_garbage_pattern('.DS_Store') == '.DS_Store'

    def test_bak_pattern(self, worker):
        assert worker._get_garbage_pattern('archive.bak') == '*.bak'

    def test_swp_pattern(self, worker):
        assert worker._get_garbage_pattern('file.swp') == '*.swp'

    def test_unknown_pattern(self, worker):
        assert worker._get_garbage_pattern('random.txt') == 'unknown'


class TestBatchInsert:
    @pytest.fixture
    def worker(self):
        w = IndexerWorker(poll_interval=1)
        w._file_batch = []
        w._batch_size = 100
        w.current_job = MagicMock()
        w.current_job.id = 'batch-job'
        return w

    def test_add_to_batch_appends(self, worker):
        file_info = {
            'path': '/test/a.txt', 'name': 'a.txt', 'size': 100,
            'checksum': 'h1', 'last_modified': None, 'modified_at': None,
            'space_id': 's1', 'directory_id': 'd1',
        }

        worker._add_to_batch(file_info, 'cfg-b1')
        assert len(worker._file_batch) == 1
        assert worker._file_batch[0]['path'] == '/test/a.txt'

    def test_add_to_batch_triggers_flush_at_limit(self, worker):
        worker._batch_size = 3

        with patch.object(worker, '_flush_batch') as mock_flush:
            for i in range(3):
                worker._add_to_batch({
                    'path': f'/test/f{i}.txt', 'name': f'f{i}.txt', 'size': 10,
                    'checksum': f'h{i}', 'space_id': 's1', 'directory_id': 'd1',
                }, 'cfg-b2')

            mock_flush.assert_called_once()

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_flush_batch_calls_batch_optimized(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        worker._file_batch = [
            {'path': '/test/f1.txt', 'space_id': 's1'},
            {'path': '/test/f2.txt', 'space_id': 's1'},
        ]

        worker._flush_batch()

        mock_db.insert_files_batch_optimized.assert_called_once()
        args = mock_db.insert_files_batch_optimized.call_args[0]
        assert len(args[0]) == 2
        assert args[1] == 's1'

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_flush_empty_batch_does_nothing(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        worker._file_batch = []
        worker._flush_batch()

        mock_db.insert_files_batch_optimized.assert_not_called()

    @patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
    def test_flush_batch_cleared_before_db_call(self, mock_db_class, worker):
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.insert_files_batch_optimized.side_effect = Exception('DB Error')

        worker._file_batch = [
            {'path': '/test/f1.txt', 'config_id': 'cfg', 'space_id': 's1', 'directory_id': 'd1'},
        ]

        with patch.object(worker, '_insert_file') as mock_insert:
            worker._flush_batch()
            mock_insert.assert_not_called()
        assert len(worker._file_batch) == 0
