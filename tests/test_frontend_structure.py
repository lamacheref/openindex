from pathlib import Path


def test_frontend_has_expected_views_and_bindings():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Tableau de bord" in html
    assert "currentView = 'files'" in html
    assert "currentView = 'duplicates'" in html
    assert "currentView = 'monitoring'" in html
    assert "x-data=\"openIndexApp()\"" in html


def test_frontend_uses_realtime_and_chart_libs():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "chart.js" in html.lower()
    assert "WebSocket" in html
    assert "crawlChart" in html


def test_frontend_main_views_non_regression_scenario():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    expected_views = {
        "dashboard": "Tableau de bord",
        "files": "Fichiers",
        "duplicates": "Doublons",
        "monitoring": "Monitoring",
    }

    for view_key, view_label in expected_views.items():
        assert f"currentView = '{view_key}'" in html
        assert view_label in html
        assert f"x-show=\"currentView === '{view_key}'\"" in html
