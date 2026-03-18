import sys
import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "api"))

import main as api_main


class DummyDB:
    def execute_query(self, query, params=None):
        params = params or []

        if query.strip() == "ANALYZE":
            return []

        if "EXPLAIN QUERY PLAN" in query:
            return [(3, 0, 0, "SCAN files")]

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
            )
        ]

    def get_statistics(self, space=None):
        return {
            "total_files": 1,
            "total_directories": 1,
            "total_size": 0,
            "duplicate_files": 0,
            "crawl_duration": 0.1,
        }


def run_request(method, path, *, params=None):
    async def _request():
        async with AsyncClient(
            transport=ASGITransport(app=api_main.app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, params=params)

    return asyncio.run(_request())


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: DummyDB())
    return run_request


@pytest.mark.parametrize("repeat_index", range(5))
def test_critical_health(client, repeat_index):
    response = client("GET", "/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.parametrize("repeat_index", range(5))
def test_critical_stats(client, repeat_index):
    response = client("GET", "/api/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files"] == 1
    assert payload["duplicate_files"] == 0


@pytest.mark.parametrize("repeat_index", range(5))
def test_critical_files(client, repeat_index):
    response = client("GET", "/api/files", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["path"] == "/share/docs"


@pytest.mark.parametrize("repeat_index", range(5))
def test_critical_db_explain(client, repeat_index):
    response = client("GET", "/api/db-explain", params={"query_name": "files_list", "analyze": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query_name"] == "files_list"
    assert payload["analyze"] is True
    assert any("SCAN files" in line for line in payload["plan"])
