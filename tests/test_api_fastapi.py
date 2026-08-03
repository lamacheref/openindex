import asyncio
import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Permet d'importer src/api/main.py et ses dépendances locales
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "api"))

import main as api_main


class DummyDB:
    def __init__(self):
        self.crawl_configs = []
        self.crawl_runs = []
        self.space_stats = {}
        self.files_by_config = {}
        self.duplicates_by_config = {}
        self._file_id_seq = 100

    def execute_query(self, query, params=None):
        params = params or []
        config_id = None
        if "crawl_config_id::text" in query:
            for value in reversed(params):
                if isinstance(value, str) and value.startswith("cfg-"):
                    config_id = value
                    break

        if query.strip() == "ANALYZE":
            return []

        if "EXPLAIN QUERY PLAN" in query:
            return [
                (3, 0, 0, "SCAN files"),
            ]

        if "FROM files" in query and "JOIN files f2" in query:
            if config_id is not None:
                return self.duplicates_by_config.get(config_id, [])
            return [
                (
                    "00000000-0000-0000-0000-000000000001",
                    "/share/a.txt",
                    "a.txt",
                    42,
                    "abc",
                    "2026-02-27T10:00:00Z",
                    None,
                    None,
                    "/share/original/a.txt",
                )
            ]

        if "current_artefact_filters" in query:
            return [(1024, 730)]

        if "AS is_large" in query:
            large_threshold_bytes = (params[0] if params else 1024 * 1024 * 1024)
            return [
                # path, name, size, last_modified, created_at, hash_xxh64, is_garbage, is_duplicate, is_large, is_old
                ("/share/docs/old_report.pdf", "old_report.pdf", 5_000_000, "2018-01-01T10:00:00Z", "2018-01-01T10:00:00Z", "oldhash", False, True, False, True),
                ("/share/docs/readme.md", "readme.md", 128, "2026-02-27T10:00:00Z", "2026-02-27T10:00:00Z", "xyz", False, False, False, False),
                ("/share/docs/big.iso", "big.iso", 2_147_483_648, "2026-02-27T10:00:00Z", "2026-02-27T10:00:00Z", "bighash", False, False, True, False),
            ]

        if "FROM directories d" in query and "parent_path" in query:
            return []

        if "FROM directories" in query and "id::text" in query:
            return [("dir-uuid",)]

        if "FROM smb_spaces WHERE host" in query:
            return [("space-uuid",)]

        if "SELECT path FROM files WHERE path IS NOT NULL" in query:
            return [
                ("/share/docs",),
                ("/share/original/a.txt",),
            ]

        if config_id is not None:
            if "duplicate_count" in query:
                return self.files_by_config.get(config_id, [
                    (
                        "\\\\srv\\share\\docs",
                        "docs",
                        None,
                        None,
                        True,
                        config_id,
                        "2024-01-01T10:00:00Z",
                        0,
                    ),
                    (
                        "\\\\srv\\share\\docs\\readme.md",
                        "readme.md",
                        128,
                        "2026-02-27T10:00:00Z",
                        False,
                        config_id,
                        "2024-02-27T10:00:00Z",
                        2,
                    ),
                ])
            return self.files_by_config.get(config_id, [])

        # /api/files
        return [
            (
                "00000000-0000-0000-0000-000000000010",
                "/share/docs",
                "docs",
                None,
                None,
                None,
                True,
                False,
                None,
                None,
                None,
            ),
            (
                "00000000-0000-0000-0000-000000000011",
                "/share/docs/readme.md",
                "readme.md",
                128,
                "xyz",
                "2026-02-27T10:00:00Z",
                False,
                False,
                None,
                None,
                None,
            ),
        ]

    def get_statistics(self, space=None):
        if space is not None:
            return self.space_stats.get(
                space,
                {
                    "total_files": 0,
                    "total_directories": 0,
                    "total_size": 0,
                    "duplicate_files": 0,
                    "crawl_duration": None,
                },
            )
        return {
            "total_files": 2,
            "total_directories": 1,
            "total_size": 128,
            "duplicate_files": 1,
            "crawl_duration": 4.2,
        }

    def resolve_space_config_id(self, space):
        for config in self.crawl_configs:
            if config["start_path"] == space:
                return config["id"]
        return None

    def get_spaces(self):
        return [
            {"name": "share", "path_prefix": "/share", "file_count": 2},
        ]

    def get_crawl_config_for_path(self, file_path):
        normalized = file_path.replace("/", "\\")
        for config in self.crawl_configs:
            if normalized.startswith(config["start_path"].replace("/", "\\")):
                return {
                    **config,
                    "connection_password": "secret",
                }
        return None

    def get_indexed_file_checksum(self, file_path):
        normalized = file_path.replace("/", "\\")
        if normalized == "\\\\srv\\source\\docs\\budget.xlsx":
            return "41d9004d230e506cf4224fc2f98dc4e95a9a1d25a1806ad08046e00685b4d354"
        if normalized == "\\\\srv\\share\\docs\\readme.pdf":
            return "dummy"
        return None

    def upsert_file_record(self, *, path, name, size, checksum, last_modified, crawl_config_id, created_at=None):
        rows = self.files_by_config.setdefault(crawl_config_id, [])
        row = (
            path,
            name,
            size,
            last_modified.isoformat() if hasattr(last_modified, "isoformat") else last_modified,
            False,
            crawl_config_id,
            created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            0,
        )
        for index, existing in enumerate(rows):
            if existing[0] == path:
                rows[index] = row
                break
        else:
            rows.append(row)

    def delete_file_record(self, path):
        for config_id, rows in list(self.files_by_config.items()):
            self.files_by_config[config_id] = [row for row in rows if row[0] != path]


    def list_crawl_configs(self):
        return list(self.crawl_configs)

    def create_crawl_config(self, payload):
        config_index = len(self.crawl_configs) + 1
        item = {
            "id": f"cfg-{config_index}",
            "name": payload.name,
            "domain_zone": payload.domain_zone,
            "start_path": payload.start_path,
            "is_archive": payload.is_archive,
            "include_paths": payload.include_paths,
            "exclude_paths": payload.exclude_paths,
            "connection_username": payload.connection.username,
            "connection_domain": payload.connection.domain,
            "created_at": "2026-03-10T12:00:00+00:00",
        }
        self.crawl_configs.append(item)
        return item

    def update_crawl_config(self, config_id, payload):
        for item in self.crawl_configs:
            if item["id"] != config_id:
                continue
            item["name"] = payload.name
            item["domain_zone"] = payload.domain_zone
            item["start_path"] = payload.start_path
            item["is_archive"] = payload.is_archive
            item["include_paths"] = payload.include_paths
            item["exclude_paths"] = payload.exclude_paths
            item["connection_username"] = payload.connection.username
            item["connection_domain"] = payload.connection.domain
            return item
        return None

    def start_crawl(self, config_id):
        if any(run["config_id"] == config_id and run["status"] in {"queued", "running", "pending", "in_progress", "cancelling"} for run in self.crawl_runs):
            raise ValueError("Une exploration est deja active pour cette configuration (queued).")
        if not any(cfg["id"] == config_id for cfg in self.crawl_configs):
            return None
        run = {
            "run_id": f"run-{len(self.crawl_runs) + 1}",
            "config_id": config_id,
            "status": "queued",
            "triggered_at": "2026-03-10T12:05:00+00:00",
        }
        self.crawl_runs.append(run)
        return run

    def request_stop_run(self, run_id):
        for run in self.crawl_runs:
            if run["run_id"] != run_id:
                continue
            if run["status"] in {"queued", "pending"}:
                run["status"] = "cancelled"
            elif run["status"] in {"running", "in_progress"}:
                run["status"] = "cancelling"
            return {"run_id": run_id, "status": run["status"]}
        return None

    def mark_run_pending(self, run_id):
        for run in self.crawl_runs:
            if run["run_id"] != run_id:
                continue
            if run["status"] in {"queued", "running", "in_progress", "cancelling"}:
                run["status"] = "pending"
                return {"run_id": run_id, "status": run["status"]}
            return None
        return None

    def delete_run(self, run_id):
        for index, run in enumerate(self.crawl_runs):
            if run["run_id"] != run_id:
                continue
            if run["status"] in {"queued", "pending", "running", "in_progress", "cancelling"}:
                return False
            del self.crawl_runs[index]
            return True
        return False

    def fail_active_runs(self):
        updated = 0
        for run in self.crawl_runs:
            if run["status"] in {"running", "in_progress", "cancelling"}:
                run["status"] = "failed"
                updated += 1
        return updated

    def cancel_stale_cancelling_runs(self):
        updated = 0
        for run in self.crawl_runs:
            if run["status"] == "cancelling":
                run["status"] = "cancelled"
                updated += 1
        return updated

    def revive_latest_terminal_run(self):
        if not self.crawl_runs:
            return None
        latest = self.crawl_runs[-1]
        if latest["status"] not in {"failed", "error", "completed", "cancelled"}:
            return None
        latest["status"] = "running"
        return {"run_id": latest["run_id"], "status": latest["status"]}

    def get_monitoring_summary(self):
        latest = self.crawl_runs[-1] if self.crawl_runs else None
        return {
            "total_configs": len(self.crawl_configs),
            "total_runs": len(self.crawl_runs),
            "queued_runs": sum(1 for run in self.crawl_runs if run["status"] == "queued"),
            "running_runs": sum(1 for run in self.crawl_runs if run["status"] in {"running", "in_progress"}),
            "completed_runs": sum(1 for run in self.crawl_runs if run["status"] == "completed"),
            "failed_runs": sum(1 for run in self.crawl_runs if run["status"] == "failed"),
            "latest_run_status": latest["status"] if latest else "Aucun run",
            "latest_run_config_name": self.crawl_configs[0]["name"] if latest and self.crawl_configs else "-",
            "latest_run_triggered_at": latest["triggered_at"] if latest else "-",
            "progress_percent": 0.0,
        }

    def list_recent_crawl_runs(self, limit=10):
        runs = list(reversed(self.crawl_runs))[:limit]
        config_names = {cfg["id"]: cfg["name"] for cfg in self.crawl_configs}
        config_zones = {cfg["id"]: cfg["domain_zone"] for cfg in self.crawl_configs}
        config_paths = {cfg["id"]: cfg["start_path"] for cfg in self.crawl_configs}
        return [
            {
                "run_id": run["run_id"],
                "config_id": run["config_id"],
                "config_name": config_names.get(run["config_id"], "Unknown"),
                "domain_zone": config_zones.get(run["config_id"], ""),
                "start_path": config_paths.get(run["config_id"], ""),
                "status": run["status"],
                "triggered_at": run["triggered_at"],
            }
            for run in runs
        ]

    def get_crawl_overview(self, limit=10):
        return {
            "monitoring": self.get_monitoring_summary(),
            "configs": self.list_crawl_configs(),
            "recent_runs": self.list_recent_crawl_runs(limit=limit),
        }


def run_request(method, path, *, params=None, json=None):
    async def _request():
        async with AsyncClient(
            transport=ASGITransport(app=api_main.app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, params=params, json=json)

    return asyncio.run(_request())


@pytest.fixture
def client(monkeypatch):
    db = DummyDB()
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: db)
    return run_request


def test_health_endpoint(client):
    response = client("GET", "/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_extract_runtime_metrics_handles_runtime_progress_line():
    metrics = api_main._extract_runtime_metrics(
        [
            "2026-03-19 13:00:00 - smb_crawler_postgresql - INFO - 📊 Progression: 120 fichiers, 15 dossiers, 2 gros fichiers | Queues: Dossiers à explorer=3, Dossiers à indexer=4, Vérification d'intégrité=5, Gros fichiers en attente=1 | Volume cible=11051758928 octets, Volume traité=2048 octets, Volume découvert=4096 octets, Progression volume=0.02%"
        ]
    )

    assert metrics["discovered_files"] == 120
    assert metrics["discovered_directories"] == 15
    assert metrics["target_bytes"] == 11051758928
    assert metrics["queue_dirs"] == 3
    assert metrics["processed_bytes"] == 2048


def test_get_files_endpoint(client):
    response = client("GET", "/api/files", params={"search": "readme", "limit": 50, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["is_directory"] is True


def test_get_stats_endpoint(client):
    response = client("GET", "/api/stats")
    assert response.status_code == 200
    assert response.json()["total_files"] == 2


def test_get_duplicates_endpoint(client):
    response = client("GET", "/api/duplicates")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["duplicate_of"] == "/share/original/a.txt"


def test_get_spaces_endpoint(client):
    response = client("GET", "/api/spaces")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["path_prefix"] == "/share"
    assert payload[0]["file_count"] == 2


def test_get_explorer_items_endpoint_exposes_highlighting_metadata(client):
    db = api_main.get_db_adapter()
    config = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="Share",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(
                username="svc_share",
                password="secret",
                domain=None,
            ),
        )
    )

    response = client(
        "GET",
        "/api/explorer/items",
        params={"root": config["start_path"], "current_path": "\\\\srv\\share\\docs"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["is_directory"] is False
    assert payload[0]["has_duplicates"] is True
    assert payload[0]["is_duplicate"] is True
    assert payload[0]["is_old"] is True
    assert payload[0]["is_large"] is False
    assert payload[0]["is_garbage"] is False


def test_get_explorer_items_keeps_rows_without_config_link_when_under_root(client):
    db = api_main.get_db_adapter()
    config = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="Share",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(
                username="svc_share",
                password="secret",
                domain=None,
            ),
        )
    )
    db.files_by_config[config["id"]] = [
        (
            "\\\\srv\\share\\docs\\indexed.txt",
            "indexed.txt",
            12,
            "2026-03-31T10:00:00Z",
            False,
            config["id"],
            "2026-03-31T10:00:00Z",
            0,
        ),
        (
            "\\\\srv\\share\\docs\\orphan.txt",
            "orphan.txt",
            15,
            "2026-03-31T10:00:00Z",
            False,
            None,
            "2026-03-31T10:00:00Z",
            0,
        ),
    ]

    response = client(
        "GET",
        "/api/explorer/items",
        params={"root": config["start_path"], "current_path": "\\\\srv\\share\\docs"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(item["path"] == "\\\\srv\\share\\docs\\indexed.txt" for item in payload)
    assert any(item["path"] == "\\\\srv\\share\\docs\\orphan.txt" for item in payload)


def test_space_scoping_uses_config_link_instead_of_path_guessing(client):
    db = api_main.get_db_adapter()

    smiden = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SMIDEN",
            domain_zone="FR",
            start_path="\\\\172.16.252.34\\Public\\SMIDEN",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(
                username="svc_smiden",
                password="secret",
                domain=None,
            ),
        )
    )
    finance = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="FINANCE",
            domain_zone="FR",
            start_path="\\\\172.16.252.34\\Public\\FINANCE",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(
                username="svc_finance",
                password="secret",
                domain=None,
            ),
        )
    )

    db.space_stats[smiden["start_path"]] = {
        "total_files": 0,
        "total_directories": 0,
        "total_size": 0,
        "duplicate_files": 0,
        "crawl_duration": None,
    }
    db.space_stats[finance["start_path"]] = {
        "total_files": 1,
        "total_directories": 1,
        "total_size": 128,
        "duplicate_files": 1,
        "crawl_duration": 3.1,
    }
    db.files_by_config[finance["id"]] = [
        (
            "00000000-0000-0000-0000-000000000021",
            "\\\\172.16.252.34\\Public\\FINANCE\\budget.xlsx",
            "budget.xlsx",
            128,
            "xyz",
            "2026-02-27T10:00:00Z",
            False,
            False,
            None,
            None,
            None,
        ),
    ]
    db.duplicates_by_config[finance["id"]] = [
        (
            "00000000-0000-0000-0000-000000000022",
            "\\\\172.16.252.34\\Public\\FINANCE\\copy.xlsx",
            "copy.xlsx",
            128,
            "xyz",
            "2026-02-27T10:00:00Z",
            None,
            None,
            "\\\\172.16.252.34\\Public\\FINANCE\\budget.xlsx",
        )
    ]

    stats = client("GET", "/api/stats", params={"space": smiden["start_path"]})
    assert stats.status_code == 200
    assert stats.json()["total_files"] == 0

    files = client("GET", "/api/files", params={"space": smiden["start_path"]})
    assert files.status_code == 200
    assert files.json() == []

    duplicates = client("GET", "/api/duplicates", params={"space": smiden["start_path"]})
    assert duplicates.status_code == 200
    assert duplicates.json() == []


def test_api_concurrent_health_requests():
    async def _run():
        async with AsyncClient(
            transport=ASGITransport(app=api_main.app),
            base_url="http://test",
        ) as client:
            return await asyncio.gather(*[client.get("/health") for _ in range(250)])

    responses = asyncio.run(_run())

    assert all(resp.status_code == 200 for resp in responses)


def test_connection_manager_broadcast_removes_dead_connection():
    manager = api_main.ConnectionManager()

    class WsOK:
        async def send_text(self, message):
            return None

    class WsDead:
        async def send_text(self, message):
            raise RuntimeError("dead")

    ok = WsOK()
    dead = WsDead()
    manager.active_connections = [ok, dead]

    # Use asyncio.run to handle the async broadcast
    import asyncio
    asyncio.run(manager.broadcast('{"type":"test"}'))

    assert manager.active_connections == [ok]


def test_get_db_explain_endpoint(client):
    response = client("GET", "/api/db-explain", params={"query_name": "files_list", "analyze": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload['query_name'] == 'files_list'
    assert payload['analyze'] is True
    assert any('SCAN files' in line for line in payload['plan'])


def test_get_db_explain_invalid_query(client):
    response = client("GET", "/api/db-explain", params={"query_name": "not_allowed"})
    assert response.status_code == 400


def test_create_and_list_crawl_configs(client):
    payload = {
        "name": "Crawl Finance",
        "domain_zone": "EMEA",
        "start_path": "\\\\srv\\finance",
        "include_paths": ["\\\\srv\\finance\\public"],
        "exclude_paths": ["\\\\srv\\finance\\temp"],
        "connection": {
            "username": "svc_finance",
            "password": "secret",
            "domain": "CORP",
        },
    }

    create_response = client("POST", "/api/crawl-configs", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()
    assert created['name'] == 'Crawl Finance'
    assert 'connection_username' in created
    assert '_secret_password' not in created

    list_response = client("GET", "/api/crawl-configs")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]['domain_zone'] == 'EMEA'


def test_update_crawl_config(client):
    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl Finance",
            "domain_zone": "EMEA",
            "start_path": "\\\\srv\\finance",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "svc_finance",
                "password": "secret",
                "domain": "CORP",
            },
        },
    ).json()

    response = client(
        "PUT",
        f"/api/crawl-configs/{created['id']}",
        json={
            "name": "Crawl Finance Prod",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\finance-prod",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "svc_finance_prod",
                "password": "",
                "domain": "CORP",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Crawl Finance Prod"
    assert payload["start_path"] == "\\\\srv\\finance-prod"
    assert payload["connection_username"] == "svc_finance_prod"


def test_start_crawl_requires_existing_config(client):

    missing = client("POST", "/api/crawls/start", json={"config_id": "missing"})
    assert missing.status_code == 404

    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl RH",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\rh",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "svc_rh",
                "password": "secret",
                "domain": "CORP",
            },
        },
    ).json()

    started = client("POST", "/api/crawls/start", json={"config_id": created["id"]})
    assert started.status_code == 200
    payload = started.json()
    assert payload['status'] == 'queued'
    assert payload['config_id'] == created['id']

    duplicated = client("POST", "/api/crawls/start", json={"config_id": created["id"]})
    assert duplicated.status_code == 409


def test_stop_and_delete_run_endpoints(client):
    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl Stop",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\stop",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "svc_stop",
                "password": "secret",
                "domain": "CORP",
            },
        },
    ).json()

    started = client("POST", "/api/crawls/start", json={"config_id": created["id"]}).json()
    stopped = client("POST", f"/api/crawls/{started['run_id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "cancelled"

    deleted = client("DELETE", f"/api/crawls/{started['run_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"


def test_mark_run_pending_endpoint(client):
    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl Pending",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\pending",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "svc_pending",
                "password": "secret",
                "domain": "CORP",
            },
        },
    ).json()

    started = client("POST", "/api/crawls/start", json={"config_id": created["id"]}).json()
    pending = client("POST", f"/api/crawls/{started['run_id']}/pending")
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"


def test_get_crawl_overview_returns_real_operational_data(client):
    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl SMIDEN",
            "domain_zone": "FR",
            "start_path": "\\\\172.16.252.34\\Public\\SMIDEN",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "adminsmiden",
                "password": "secret",
                "domain": None,
            },
        },
    ).json()

    client("POST", "/api/crawls/start", json={"config_id": created["id"]})

    response = client("GET", "/api/crawls/overview", params={"limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["monitoring"]["total_configs"] == 1
    assert payload["monitoring"]["total_runs"] == 1
    assert payload["configs"][0]["name"] == "Crawl SMIDEN"
    assert payload["recent_runs"][0]["config_name"] == "Crawl SMIDEN"
    assert payload["recent_runs"][0]["start_path"] == "\\\\172.16.252.34\\Public\\SMIDEN"


def test_get_system_status_endpoint(client, monkeypatch):
    monkeypatch.setenv("OPENINDEX_APP_VERSION", "1.4.0")
    monkeypatch.setenv("OPENINDEX_BUILD_COMMIT", "abc1234")
    monkeypatch.setenv("OPENINDEX_BUILD_DATE", "2026-03-18")
    monkeypatch.setenv("OPENINDEX_NEWER_VERSION_AVAILABLE", "true")
    monkeypatch.setenv("OPENINDEX_NEWEST_VERSION_URL", "https://github.com/lamacheref/openindex/releases/tag/v1.4.1")

    response = client("GET", "/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_version"] == "1.4.0"
    assert payload["commit_hash"] == "abc1234"
    assert payload["build_date"] == "2026-03-18"
    assert payload["newer_version_available"] is True


def test_get_crawler_runtime_endpoint(client, monkeypatch, tmp_path):
    log_file = tmp_path / "smb_crawler_postgresql.log"
    log_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    monkeypatch.setenv("OPENINDEX_CRAWLER_LOG_PATH", str(log_file))

    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl Runtime",
            "domain_zone": "FR",
            "start_path": "\\\\172.16.252.34\\Public\\SMIDEN",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "adminsmiden",
                "password": "secret",
                "domain": None,
            },
        },
    ).json()
    client("POST", "/api/crawls/start", json={"config_id": created["id"]})

    response = client("GET", "/api/crawler/runtime", params={"log_limit": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_config_name"] == "Crawl Runtime"
    assert len(payload["queue_indicators"]) == 4
    assert payload["log_lines"] == ["line 2", "line 3"]
    integrity_queue = next(item for item in payload["queue_indicators"] if item["key"] == "checksums")
    integrity_progress = next(item for item in payload["progress_indicators"] if item["key"] == "integrity_backlog")
    assert "it/s" in integrity_queue["detail"]
    assert "it/s" in integrity_progress["detail"]


def test_get_crawler_runtime_reconciles_terminal_run_with_recent_db_activity(monkeypatch, tmp_path):
    db = DummyDB()
    db.crawl_configs.append(
        {
            "id": "cfg-1",
            "name": "Crawl Runtime",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\runtime",
            "include_paths": [],
            "exclude_paths": [],
            "connection_username": "svc_runtime",
            "connection_domain": "CORP",
            "created_at": "2026-03-10T12:00:00+00:00",
        }
    )
    db.crawl_runs.append(
        {
            "run_id": "run-1",
            "config_id": "cfg-1",
            "status": "completed",
            "triggered_at": "2026-03-10T12:05:00+00:00",
        }
    )

    log_file = tmp_path / "smb_crawler_postgresql.log"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENINDEX_CRAWLER_LOG_PATH", str(log_file))
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: db)
    monkeypatch.setattr(
        api_main,
        "_get_recent_write_activity_safe",
        lambda _db, window_seconds=300: {
            "recent_writes": 4,
            "last_write_at": datetime.utcnow() - timedelta(seconds=30),
        },
    )

    response = run_request("GET", "/api/crawler/runtime")

    assert response.status_code == 200
    assert db.crawl_runs[-1]["status"] == "running"
    assert response.json()["db_write_active"] is True


def test_get_operations_status_endpoint_nominal(client, monkeypatch, tmp_path):
    log_file = tmp_path / "smb_crawler_postgresql.log"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENINDEX_CRAWLER_LOG_PATH", str(log_file))

    created = client(
        "POST",
        "/api/crawl-configs",
        json={
            "name": "Crawl Ops",
            "domain_zone": "FR",
            "start_path": "\\\\172.16.252.34\\Public\\OPS",
            "include_paths": [],
            "exclude_paths": [],
            "connection": {
                "username": "adminops",
                "password": "secret",
                "domain": None,
            },
        },
    ).json()
    assert created["name"] == "Crawl Ops"

    response = client("GET", "/api/operations/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["monitoring"]["total_configs"] == 1
    assert payload["incidents"] == []
    assert any(check["key"] == "api_health" and check["status"] == "healthy" for check in payload["checks"])


def test_get_operations_status_endpoint_reports_critical_incidents(monkeypatch, tmp_path):
    db = DummyDB()
    db.crawl_configs.append(
        {
            "id": "cfg-1",
            "name": "Crawl Incident",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\incident",
            "include_paths": [],
            "exclude_paths": [],
            "connection_username": "svc_incident",
            "connection_domain": "CORP",
            "created_at": "2026-03-10T12:00:00+00:00",
        }
    )
    db.crawl_runs.append(
        {
            "run_id": "run-1",
            "config_id": "cfg-1",
            "status": "failed",
            "triggered_at": "2026-03-10T12:05:00+00:00",
        }
    )

    log_file = tmp_path / "smb_crawler_postgresql.log"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENINDEX_CRAWLER_LOG_PATH", str(log_file))
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: db)

    response = run_request("GET", "/api/operations/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "critical"
    assert any(incident["key"] == "run_failures" for incident in payload["incidents"])
    assert any(check["key"] == "run_failures" and check["status"] == "critical" for check in payload["checks"])


def test_monitoring_reconciles_stale_cancelling_run_to_cancelled(monkeypatch, tmp_path):
    db = DummyDB()
    db.crawl_configs.append(
        {
            "id": "cfg-1",
            "name": "Crawl Cancel",
            "domain_zone": "FR",
            "start_path": "\\\\srv\\cancel",
            "include_paths": [],
            "exclude_paths": [],
            "connection_username": "svc_cancel",
            "connection_domain": "CORP",
            "created_at": "2026-03-10T12:00:00+00:00",
        }
    )
    db.crawl_runs.append(
        {
            "run_id": "run-1",
            "config_id": "cfg-1",
            "status": "cancelling",
            "triggered_at": "2026-03-10T12:05:00+00:00",
        }
    )

    monkeypatch.setattr(api_main, "get_db_adapter", lambda: db)
    monkeypatch.setattr(api_main, "STALE_RUN_TIMEOUT_SECONDS", 1)
    log_file = tmp_path / "smb_crawler_postgresql.log"
    log_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENINDEX_CRAWLER_LOG_PATH", str(log_file))

    response = run_request("GET", "/api/monitoring")
    assert response.status_code == 200
    assert response.json()["latest_run_status"] == "cancelled"


def test_connection_manager_removes_closed_websocket():
    class ClosedWebSocket:
        async def send_text(self, _message):
            raise RuntimeError('Cannot call "send" once a close message has been sent.')

    async def _run():
        local_manager = api_main.ConnectionManager()
        websocket = ClosedWebSocket()
        local_manager.active_connections.append(websocket)

        sent = await local_manager.send_personal_message("payload", websocket)

        assert sent is False
        assert websocket not in local_manager.active_connections

    asyncio.run(_run())


def test_file_content_endpoint_streams_data(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SMIDEN",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc", password="secret", domain="CORP"),
        )
    )

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def open_file(self, path, mode="rb"):
            assert path == "\\\\srv\\share\\docs\\readme.pdf"
            return io.BytesIO(b"pdf-data")

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client("GET", "/api/file-content", params={"path": "\\\\srv\\share\\docs\\readme.pdf"})

    assert response.status_code == 200
    assert response.content == b"pdf-data"
    assert response.headers["content-type"] == "application/pdf"


def test_file_preview_endpoint_retries_transient_smb_sharing_violation(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SMIDEN",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc", password="secret", domain="CORP"),
        )
    )

    docx_buffer = io.BytesIO()
    with api_main.zipfile.ZipFile(docx_buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>Retry OK</w:t></w:r></w:p></w:body></w:document>"
            ),
        )

    class FakeSMBClient:
        def __init__(self):
            self.calls = 0

        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def open_file(self, path, mode="rb"):
            assert path == "\\\\srv\\share\\docs\\locked.docx"
            self.calls += 1
            if self.calls == 1:
                raise OSError("[Error 1] [NtStatus 0xc0000043] The process cannot access the file because it is being used by another process")
            return io.BytesIO(docx_buffer.getvalue())

    fake_smb = FakeSMBClient()
    monkeypatch.setattr(api_main, "smbclient", fake_smb)
    monkeypatch.setattr(api_main.time, "sleep", lambda _seconds: None)

    response = client("GET", "/api/file-preview", params={"path": "\\\\srv\\share\\docs\\locked.docx"})

    assert response.status_code == 200
    assert "Retry OK" in response.text
    assert fake_smb.calls == 2


def test_file_preview_endpoint_renders_docx_html(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SMIDEN",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc", password="secret", domain="CORP"),
        )
    )

    docx_buffer = io.BytesIO()
    with api_main.zipfile.ZipFile(docx_buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>Bonjour OpenIndex</w:t></w:r></w:p></w:body></w:document>"
            ),
        )

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def open_file(self, path, mode="rb"):
            assert path == "\\\\srv\\share\\docs\\preview.docx"
            return io.BytesIO(docx_buffer.getvalue())

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client("GET", "/api/file-preview", params={"path": "\\\\srv\\share\\docs\\preview.docx"})

    assert response.status_code == 200
    assert "Bonjour OpenIndex" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_file_preview_endpoint_renders_xlsx_html(client, monkeypatch):
    if api_main.openpyxl is None:
        pytest.skip("openpyxl indisponible")

    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SMIDEN",
            domain_zone="FR",
            start_path="\\\\srv\\share",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc", password="secret", domain="CORP"),
        )
    )

    workbook = api_main.openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Budget"
    worksheet["A1"] = "Libelle"
    worksheet["B1"] = "Montant"
    worksheet["A2"] = "Serveurs"
    worksheet["B2"] = 2025
    xlsx_buffer = io.BytesIO()
    workbook.save(xlsx_buffer)

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def open_file(self, path, mode="rb"):
            assert path == "\\\\srv\\share\\docs\\2025.xlsx"
            return io.BytesIO(xlsx_buffer.getvalue())

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client("GET", "/api/file-preview", params={"path": "\\\\srv\\share\\docs\\2025.xlsx"})

    assert response.status_code == 200
    assert "Budget" in response.text
    assert "Serveurs" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_archive_file_endpoint_moves_file_between_spaces(client, monkeypatch):
    db = api_main.get_db_adapter()
    source_config = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SOURCE",
            domain_zone="FR",
            start_path="\\\\srv\\source",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_source", password="secret", domain=None),
        )
    )
    archive_config = db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="ARCHIVE",
            domain_zone="FR",
            start_path="\\\\srv\\archive",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_archive", password="secret", domain=None),
        )
    )

    writes = {}
    removed = []

    class WritableBuffer(io.BytesIO):
        def __init__(self, path):
            super().__init__()
            self.path = path

        def close(self):
            writes[self.path] = self.getvalue()
            super().close()

    class TextWritableBuffer(io.StringIO):
        def __init__(self, path):
            super().__init__()
            self.path = path

        def close(self):
            writes[self.path] = self.getvalue().encode("utf-8")
            super().close()

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def stat(self, path):
            raise OSError("missing")

        def mkdir(self, path):
            return None

        def open_file(self, path, mode="rb"):
            if mode == "rb":
                return io.BytesIO(b"archive-me")
            if mode == "w":
                return TextWritableBuffer(path)
            return WritableBuffer(path)

        def remove(self, path):
            removed.append(path)

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client(
        "POST",
        "/api/archive/file",
        json={
            "source_path": "\\\\srv\\source\\docs\\budget.xlsx",
            "target_directory_path": "\\\\srv\\archive\\2026",
            "mode": "move",
            "overwrite": False,
            "leave_link": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["target_path"] == "\\\\srv\\archive\\2026\\budget.xlsx"
    assert payload["source_deleted"] is True
    assert payload["link_path"] == "\\\\srv\\source\\docs\\budget.xlsx.url"
    assert payload["checksum_verified"] is True
    assert payload["checksum"] == "41d9004d230e506cf4224fc2f98dc4e95a9a1d25a1806ad08046e00685b4d354"
    assert writes["\\\\srv\\archive\\2026\\budget.xlsx"] == b"archive-me"
    assert b"file://srv/archive/2026/budget.xlsx" in writes["\\\\srv\\source\\docs\\budget.xlsx.url"]
    assert removed == ["\\\\srv\\source\\docs\\budget.xlsx"]
    archive_files = db.files_by_config[archive_config["id"]]
    assert any(row[0] == "\\\\srv\\archive\\2026\\budget.xlsx" for row in archive_files)
    assert any(run["config_id"] == archive_config["id"] for run in db.crawl_runs)
    assert any(run["config_id"] == source_config["id"] for run in db.crawl_runs)

    explorer_response = client(
        "GET",
        "/api/explorer/items",
        params={"root": archive_config["start_path"], "current_path": "\\\\srv\\archive\\2026"},
    )
    assert explorer_response.status_code == 200
    explorer_payload = explorer_response.json()
    assert any(item["path"] == "\\\\srv\\archive\\2026\\budget.xlsx" for item in explorer_payload)


def test_archive_file_refuses_delete_when_checksum_verification_fails(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SOURCE",
            domain_zone="FR",
            start_path="\\\\srv\\source",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_source", password="secret", domain=None),
        )
    )
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="ARCHIVE",
            domain_zone="FR",
            start_path="\\\\srv\\archive",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_archive", password="secret", domain=None),
        )
    )

    removed = []

    class WritableBuffer(io.BytesIO):
        def __init__(self, path):
            super().__init__()
            self.path = path

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def stat(self, path):
            raise OSError("missing")

        def mkdir(self, path):
            return None

        def open_file(self, path, mode="rb"):
            if mode == "rb" and path == "\\\\srv\\source\\docs\\budget.xlsx":
                return io.BytesIO(b"archive-me")
            if mode == "rb" and path == "\\\\srv\\archive\\2026\\budget.xlsx":
                return io.BytesIO(b"tampered-copy")
            return WritableBuffer(path)

        def remove(self, path):
            removed.append(path)

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client(
        "POST",
        "/api/archive/file",
        json={
            "source_path": "\\\\srv\\source\\docs\\budget.xlsx",
            "target_directory_path": "\\\\srv\\archive\\2026",
            "mode": "move",
            "overwrite": False,
            "leave_link": False,
        },
    )

    assert response.status_code == 409
    assert "Verification SHA-256 echouee" in response.json()["detail"]
    assert removed == ["\\\\srv\\archive\\2026\\budget.xlsx"]


def test_archive_file_refuses_existing_target_without_overwrite(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SOURCE",
            domain_zone="FR",
            start_path="\\\\srv\\source",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_source", password="secret", domain=None),
        )
    )
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="ARCHIVE",
            domain_zone="FR",
            start_path="\\\\srv\\archive",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_archive", password="secret", domain=None),
        )
    )

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def stat(self, path):
            return object()

        def mkdir(self, path):
            return None

        def open_file(self, path, mode="rb"):
            raise AssertionError("open_file ne doit pas etre appele si la cible existe sans overwrite")

        def remove(self, path):
            raise AssertionError("remove ne doit pas etre appele si la cible existe sans overwrite")

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client(
        "POST",
        "/api/archive/file",
        json={
            "source_path": "\\\\srv\\source\\docs\\budget.xlsx",
            "target_directory_path": "\\\\srv\\archive\\2026",
            "mode": "copy",
            "overwrite": False,
            "leave_link": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Le fichier cible existe déjà"


def test_archive_file_allows_overwrite_when_requested(client, monkeypatch):
    db = api_main.get_db_adapter()
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="SOURCE",
            domain_zone="FR",
            start_path="\\\\srv\\source",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_source", password="secret", domain=None),
        )
    )
    db.create_crawl_config(
        api_main.CrawlConfigCreate(
            name="ARCHIVE",
            domain_zone="FR",
            start_path="\\\\srv\\archive",
            include_paths=[],
            exclude_paths=[],
            connection=api_main.CrawlConnectionConfig(username="svc_archive", password="secret", domain=None),
        )
    )

    writes = {}

    class WritableBuffer(io.BytesIO):
        def __init__(self, path):
            super().__init__()
            self.path = path

        def close(self):
            writes[self.path] = self.getvalue()
            super().close()

    class FakeSMBClient:
        def ClientConfig(self, **kwargs):
            self.config = kwargs

        def stat(self, path):
            return object()

        def mkdir(self, path):
            return None

        def open_file(self, path, mode="rb"):
            if mode == "rb" and path == "\\\\srv\\source\\docs\\budget.xlsx":
                return io.BytesIO(b"archive-me")
            if mode == "rb" and path == "\\\\srv\\archive\\2026\\budget.xlsx":
                return io.BytesIO(b"archive-me")
            return WritableBuffer(path)

        def remove(self, path):
            raise AssertionError("remove ne doit pas etre appele en mode copy")

    monkeypatch.setattr(api_main, "smbclient", FakeSMBClient())

    response = client(
        "POST",
        "/api/archive/file",
        json={
            "source_path": "\\\\srv\\source\\docs\\budget.xlsx",
            "target_directory_path": "\\\\srv\\archive\\2026",
            "mode": "copy",
            "overwrite": True,
            "leave_link": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["target_path"] == "\\\\srv\\archive\\2026\\budget.xlsx"
    assert response.json()["checksum_verified"] is True
    assert writes["\\\\srv\\archive\\2026\\budget.xlsx"] == b"archive-me"
