import stat
import sys
import time as pytime
from pathlib import Path
from types import SimpleNamespace

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
