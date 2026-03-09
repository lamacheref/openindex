import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Permet d'importer src/api/main.py et ses dépendances locales
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "api"))

import main as api_main


class DummyDB:
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


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: DummyDB())
    return TestClient(api_main.app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_files_endpoint(client):
    response = client.get("/api/files", params={"search": "readme", "limit": 50, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["is_directory"] is True


def test_get_stats_endpoint(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["total_files"] == 2


def test_get_duplicates_endpoint(client):
    response = client.get("/api/duplicates")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["duplicate_of"] == "/share/original/a.txt"


def test_get_spaces_endpoint(client):
    response = client.get("/api/spaces")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["path_prefix"] == "/share"
    assert payload[0]["file_count"] == 2


@pytest.mark.asyncio
async def test_api_concurrent_health_requests():
    transport = ASGITransport(app=api_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        responses = await asyncio.gather(*[ac.get("/health") for _ in range(250)])

    assert all(resp.status_code == 200 for resp in responses)


@pytest.mark.asyncio
async def test_connection_manager_broadcast_removes_dead_connection():
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

    await manager.broadcast('{"type":"test"}')

    assert manager.active_connections == [ok]


def test_get_db_explain_endpoint(client):
    response = client.get('/api/db-explain', params={'query_name': 'files_list', 'analyze': True})
    assert response.status_code == 200
    payload = response.json()
    assert payload['query_name'] == 'files_list'
    assert payload['analyze'] is True
    assert any('SCAN files' in line for line in payload['plan'])


def test_get_db_explain_invalid_query(client):
    response = client.get('/api/db-explain', params={'query_name': 'not_allowed'})
    assert response.status_code == 400
