import asyncio
import sys
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

    def execute_query(self, query, params=None):
        params = params or []
        if query.strip() == "ANALYZE":
            return []

        if "EXPLAIN QUERY PLAN" in query:
            return [
                (3, 0, 0, "SCAN files"),
            ]

        if "FROM files" in query and "JOIN files f2" in query:
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

        if "SELECT path FROM files WHERE path IS NOT NULL" in query:
            return [
                ("/share/docs",),
                ("/share/original/a.txt",),
            ]

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
        return {
            "total_files": 2,
            "total_directories": 1,
            "total_size": 128,
            "duplicate_files": 1,
            "crawl_duration": 4.2,
        }

    def get_spaces(self):
        return [
            {"name": "share", "path_prefix": "/share", "file_count": 2},
        ]


    def list_crawl_configs(self):
        return list(self.crawl_configs)

    def create_crawl_config(self, payload):
        item = {
            "id": "cfg-1",
            "name": payload.name,
            "domain_zone": payload.domain_zone,
            "start_path": payload.start_path,
            "include_paths": payload.include_paths,
            "exclude_paths": payload.exclude_paths,
            "connection_username": payload.connection.username,
            "connection_domain": payload.connection.domain,
            "created_at": "2026-03-10T12:00:00+00:00",
        }
        self.crawl_configs = [item]
        return item

    def start_crawl(self, config_id):
        if not any(cfg["id"] == config_id for cfg in self.crawl_configs):
            return None
        run = {
            "run_id": "run-1",
            "config_id": config_id,
            "status": "queued",
            "triggered_at": "2026-03-10T12:05:00+00:00",
        }
        self.crawl_runs.append(run)
        return run

    def get_monitoring_summary(self):
        latest = self.crawl_runs[-1] if self.crawl_runs else None
        return {
            "total_configs": len(self.crawl_configs),
            "total_runs": len(self.crawl_runs),
            "queued_runs": sum(1 for run in self.crawl_runs if run["status"] == "queued"),
            "running_runs": 0,
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
