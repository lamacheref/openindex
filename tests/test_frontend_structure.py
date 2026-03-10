import re
from pathlib import Path


def read_frontend_html() -> str:
    return Path("frontend/index.html").read_text(encoding="utf-8")


def test_frontend_has_expected_views_and_bindings():
    html = read_frontend_html()

    assert "Tableau de bord" in html
    assert "x-data=\"openIndexApp()\"" in html

    expected_views = {
        "dashboard": "Tableau de bord",
        "files": "Fichiers",
        "duplicates": "Doublons",
        "monitoring": "Monitoring",
    }

    for view_key, view_label in expected_views.items():
        assert f"currentView = '{view_key}'" in html
        assert f"x-show=\"currentView === '{view_key}'\"" in html
        assert view_label in html


def test_frontend_uses_realtime_and_chart_libs():
    html = read_frontend_html()

    assert "chart.js" in html.lower()
    assert "WebSocket" in html
    assert "crawlChart" in html


def test_frontend_nav_switches_cover_all_main_views():
    html = read_frontend_html()

    view_switches = set(re.findall(r"currentView\s*=\s*'([a-z_]+)'", html))
    assert {"dashboard", "files", "duplicates", "monitoring"}.issubset(view_switches)


def test_frontend_main_views_are_declared_once_each():
    html = read_frontend_html()

    for view_key in ("dashboard", "files", "duplicates", "monitoring"):
        occurrences = len(re.findall(rf"x-show=\"currentView === '{view_key}'\"", html))
        assert occurrences == 1, f"La vue {view_key} doit être déclarée exactement une fois"
