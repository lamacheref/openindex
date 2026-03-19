import stat
import sys
import time as pytime
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import smb_crawler_postgresql as crawler_module


class DummyLogger:
    def info(self, message):
        return None

    def warning(self, message):
        return None

    def error(self, message):
        return None

    def debug(self, message):
        return None


class FakePostgresAdapter:
    def __init__(self, *_args, **_kwargs):
        self.saved_batches = []
        self.saved_stats = []
        self.updated_statuses = []
        self._wait_calls = 0

    def initialize_database(self):
        return None

    def save_files_batch(self, batch_files):
        self.saved_batches.append([item["path"] for item in batch_files])
        return len(batch_files)

    def calculate_duplicates(self):
        return 0

    def save_crawl_statistics(self, crawl_stats):
        self.saved_stats.append(crawl_stats)

    def get_crawl_run_status(self, _run_id):
        return "running"

    def get_files_by_paths(self, paths, crawl_config_id=None):
        return {}

    def get_last_completed_crawl_triggered_at(self, crawl_config_id, exclude_run_id=None):
        return None

    def reset_stale_running_runs(self):
        return None

    def wait_for_next_run(self, poll_interval_seconds=5):
        self._wait_calls += 1
        if self._wait_calls == 1:
            return {
                "run_id": "run-1",
                "config_id": "cfg-1",
                "name": "SMIDEN",
                "start_path": r"\\srv\share",
                "connection_username": "user",
                "connection_password": "pass",
                "connection_domain": "",
            }
        raise KeyboardInterrupt

    def update_crawl_run_status(self, run_id, status):
        self.updated_statuses.append((run_id, status))


def test_start_crawl_waits_for_inflight_subdirectory_processing(monkeypatch):
    original_sleep = pytime.sleep
    root_path = r"\\srv\share"
    child_path = root_path + r"\dirA"
    file_path = child_path + r"\deep.txt"

    fake_adapter = FakePostgresAdapter()

    monkeypatch.setattr(crawler_module, "PostgreSQLAdapter", lambda *_args, **_kwargs: fake_adapter)
    monkeypatch.setattr(crawler_module.SMBCrawlerPostgreSQL, "setup_logging", lambda self: setattr(self, "logger", DummyLogger()))
    monkeypatch.setattr(crawler_module.SMBCrawlerPostgreSQL, "_calculate_full_checksum", lambda self, _path: "checksum")

    def fast_sleep(seconds):
        original_sleep(min(seconds, 0.01))

    monkeypatch.setattr(crawler_module.time, "sleep", fast_sleep)

    def fake_listdir(path):
        if path == root_path:
            return ["dirA"]
        if path == child_path:
            original_sleep(0.05)
            return ["deep.txt"]
        raise AssertionError(f"Unexpected path listed: {path}")

    def fake_stat(path):
        if path == child_path:
            return SimpleNamespace(st_size=0, st_mode=stat.S_IFDIR, st_mtime=1_710_000_000)
        if path == file_path:
            return SimpleNamespace(st_size=3, st_mode=stat.S_IFREG, st_mtime=1_710_000_001)
        raise AssertionError(f"Unexpected path stat'ed: {path}")

    monkeypatch.setattr(crawler_module.smbclient, "listdir", fake_listdir)
    monkeypatch.setattr(crawler_module.smbclient, "stat", fake_stat)

    crawler = crawler_module.SMBCrawlerPostgreSQL(
        server="srv",
        username="user",
        password="pass",
        share_name="share",
        max_workers=4,
        delay_between_requests=0,
        max_queue_size=100,
    )

    stats = crawler.start_crawl(base_path=root_path)

    assert stats["total_directories"] == 2
    assert stats["total_files"] == 1
    assert any(child_path in batch for batch in fake_adapter.saved_batches)
    assert any(file_path in batch for batch in fake_adapter.saved_batches)


def test_worker_loop_marks_timed_out_run_as_failed(monkeypatch):
    fake_adapter = FakePostgresAdapter()

    monkeypatch.setattr(crawler_module, "PostgreSQLAdapter", lambda *_args, **_kwargs: fake_adapter)
    monkeypatch.setattr(
        crawler_module,
        "run_single_crawl",
        lambda _run_payload: {"timed_out": True, "cancelled": False},
    )

    with pytest.raises(KeyboardInterrupt):
        crawler_module.worker_loop(poll_interval_seconds=0)

    assert fake_adapter.updated_statuses == [("run-1", "failed")]


def test_start_crawl_skips_unchanged_known_file_before_checksum(monkeypatch):
    original_sleep = pytime.sleep
    root_path = r"\\srv\share"
    file_path = root_path + r"\report.txt"
    checksum_calls = []

    class SkipAwareAdapter(FakePostgresAdapter):
        def get_files_by_paths(self, paths, crawl_config_id=None):
            assert crawl_config_id == "cfg-1"
            return {
                file_path: {
                    "path": file_path,
                    "size": 3,
                    "last_modified": datetime(2026, 3, 18, 10, 0, 0).isoformat(),
                    "checksum": "existing",
                    "crawl_config_id": "cfg-1",
                }
            }

        def get_last_completed_crawl_triggered_at(self, crawl_config_id, exclude_run_id=None):
            assert crawl_config_id == "cfg-1"
            return datetime(2026, 3, 18, 12, 0, 0)

    fake_adapter = SkipAwareAdapter()

    monkeypatch.setattr(crawler_module, "PostgreSQLAdapter", lambda *_args, **_kwargs: fake_adapter)
    monkeypatch.setattr(crawler_module.SMBCrawlerPostgreSQL, "setup_logging", lambda self: setattr(self, "logger", DummyLogger()))

    def fake_checksum(self, _path):
        checksum_calls.append(_path)
        return "checksum"

    monkeypatch.setattr(crawler_module.SMBCrawlerPostgreSQL, "_calculate_full_checksum", fake_checksum)

    def fast_sleep(seconds):
        original_sleep(min(seconds, 0.01))

    monkeypatch.setattr(crawler_module.time, "sleep", fast_sleep)

    def fake_listdir(path):
        if path == root_path:
            return ["report.txt"]
        raise AssertionError(f"Unexpected path listed: {path}")

    def fake_stat(path):
        if path == file_path:
            return SimpleNamespace(st_size=3, st_mode=stat.S_IFREG, st_mtime=datetime(2026, 3, 18, 10, 0, 0).timestamp())
        raise AssertionError(f"Unexpected path stat'ed: {path}")

    monkeypatch.setattr(crawler_module.smbclient, "listdir", fake_listdir)
    monkeypatch.setattr(crawler_module.smbclient, "stat", fake_stat)

    crawler = crawler_module.SMBCrawlerPostgreSQL(
        server="srv",
        username="user",
        password="pass",
        share_name="share",
        crawl_config_id="cfg-1",
        max_workers=4,
        delay_between_requests=0,
        max_queue_size=100,
        pre_estimation_enabled=False,
    )
    crawler.run_id = "run-current"

    stats = crawler.start_crawl(base_path=root_path)

    assert stats["total_files"] == 0
    assert checksum_calls == []
    assert not any(file_path in batch for batch in fake_adapter.saved_batches)
