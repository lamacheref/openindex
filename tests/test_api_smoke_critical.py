import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api_main, "get_db_adapter", lambda: DummyDB())
    return TestClient(api_main.app)


def test_critical_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_critical_stats(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["total_files"] == 1


def test_critical_files(client):
    response = client.get("/api/files", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["path"] == "/share/docs"


def test_critical_db_explain(client):
    response = client.get("/api/db-explain", params={"query_name": "files_list", "analyze": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query_name"] == "files_list"
    assert payload["analyze"] is True
    assert any("SCAN files" in line for line in payload["plan"])
