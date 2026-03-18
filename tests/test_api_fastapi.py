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
