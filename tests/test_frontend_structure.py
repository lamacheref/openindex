import re
from pathlib import Path


def read_frontend_html() -> str:
    return Path("frontend/index.html").read_text(encoding="utf-8")


def test_frontend_has_expected_views_and_bindings():
    html = read_frontend_html()

    assert "Tableau de bord" in html
    assert "x-data=\"openIndexApp()\"" in html

    expected_main_views = {
        "dashboard": "Tableau de bord",
        "files": "Fichiers",
        "duplicates": "Doublons",
        "configuration": "Configuration",
    }

    for view_key, view_label in expected_main_views.items():
        assert f"currentView = '{view_key}'" in html
        assert view_label in html

    assert "Implémentation rapide" in html
    assert "Monitoring temps réel" in html
    assert "Explain / Analyze DB" in html


def test_frontend_uses_realtime_and_chart_libs():
    html = read_frontend_html()

    assert "chart.js" in html.lower()
    assert "WebSocket" in html
    assert "crawlChart" in html


def test_frontend_sidebar_limits_main_navigation():
    html = read_frontend_html()

    nav_start = html.index('<nav class="space-y-3">')
    nav_end = html.index('</nav>', nav_start)
    nav_html = html[nav_start:nav_end]

    assert "Tableau de bord" in nav_html
    assert "Fichiers" in nav_html
    assert "Doublons" in nav_html
    assert "Monitoring" not in nav_html
    assert "DB Explain" not in nav_html
    assert "Implémentation rapide" not in nav_html


def test_configuration_access_and_sections_exist():
    html = read_frontend_html()

    assert "title=\"Configuration\"" in html
    assert "fa-gear" in html
    assert "openConfiguration('crawler')" in html

    assert "configSection = 'crawler'" in html
    assert "configSection = 'dbAnalysis'" in html
    assert "configSection = 'monitoring'" in html
    assert "currentView === 'configuration' && configSection === 'crawler'" in html
    assert "currentView === 'configuration' && configSection === 'dbAnalysis'" in html
    assert "currentView === 'configuration' && configSection === 'monitoring'" in html
