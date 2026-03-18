from pathlib import Path


def read_frontend_html() -> str:
    return Path("frontend/index.html").read_text(encoding="utf-8")


def test_frontend_has_expected_views_and_bindings():
    html = read_frontend_html()

    assert "Tableau de bord" in html
    assert "x-data=\"openIndexApp()\"" in html

    expected_main_views = {
        "dashboard": "Tableau de bord",
        "fileExplorer": "Explorateur de fichiers",
        "artifacts": "Traitements des artefacts",
        "configuration": "Configuration",
    }

    for view_key, view_label in expected_main_views.items():
        assert f"currentView = '{view_key}'" in html
        assert view_label in html

    assert "Implémentation rapide" in html
    assert "Monitoring temps réel" in html
    assert "Explain / Analyze DB" in html
    assert "Journal du crawler" in html
    assert "Version" in html


def test_frontend_uses_realtime_libs_and_fixed_header_shell():
    html = read_frontend_html()

    assert "chart.js" in html.lower()
    assert "WebSocket" in html
    assert "fixed top-0 left-0 right-0" in html
    assert "overflow-y-auto" in html


def test_frontend_sidebar_contains_expected_operator_navigation():
    html = read_frontend_html()

    nav_start = html.index('<nav class="space-y-2">')
    nav_end = html.index('</nav>', nav_start)
    nav_html = html[nav_start:nav_end]

    assert "Tableau de bord" in nav_html
    assert "Explorateur de fichiers" in nav_html
    assert "Traitements des artefacts" in nav_html
    assert "Monitoring" not in nav_html
    assert "DB Explain" not in nav_html
    assert "Implémentation rapide" not in nav_html
    assert "fa-bars" not in html


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


def test_dashboard_has_active_crawl_block_and_log_toggle():
    html = read_frontend_html()

    assert "Avancement du crawl" in html
    assert "Voir les logs" in html
    assert "showCrawlerLogs" in html
    assert "Journal du crawler" in html
