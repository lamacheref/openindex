"""
Tests pour les endpoints de filtres configurables (T-ART-03)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Importer l'application FastAPI
from src.api.main import app

client = TestClient(app)


# Fixture pour mocker l'adaptateur de base de données
@pytest.fixture
def mock_db_adapter():
    """Mock de l'adaptateur de base de données"""
    with patch('src.api.artefact_filters_router.get_db_adapter') as mock:
        yield mock


class TestArtefactFiltersAPI:
    """Tests pour les endpoints de filtres configurables"""

    def test_get_artefact_filter_preferences_default(self, mock_db_adapter):
        """Test la récupération des préférences par défaut"""
        # Configurer le mock pour retourner aucun résultat (valeurs par défaut)
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefact-filters/preferences")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["large_file_threshold_mb"] == 1024
        assert data["old_file_threshold_days"] == 730
        assert data["unused_file_threshold_days"] == 365

    def test_get_artefact_filter_preferences_custom(self, mock_db_adapter):
        """Test la récupération des préférences personnalisées"""
        # Configurer le mock pour retourner des préférences personnalisées
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [(2048, 1095, 730)]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefact-filters/preferences")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["large_file_threshold_mb"] == 2048
        assert data["old_file_threshold_days"] == 1095
        assert data["unused_file_threshold_days"] == 730

    def test_update_artefact_filter_preferences(self, mock_db_adapter):
        """Test la mise à jour des préférences"""
        # Configurer le mock
        mock_db = MagicMock()
        
        # Simuler que les préférences n'existent pas encore, puis retourner les valeurs mises à jour
        mock_db.execute_query.side_effect = [
            [],  # Aucune préférence existante pour large_file_threshold_mb
            [],  # Aucune préférence existante pour old_file_threshold_days
            [],  # Aucune préférence existante pour unused_file_threshold_days
            None,  # INSERT ne retourne rien
            None,  # INSERT ne retourne rien
            None,  # INSERT ne retourne rien
            [(2048, 1095, 730)]  # Résultat final après mise à jour
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.put("/api/artefact-filters/preferences", json={
            "large_file_threshold_mb": 2048,
            "old_file_threshold_days": 1095,
            "unused_file_threshold_days": 730
        })
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["large_file_threshold_mb"] == 2048
        assert data["old_file_threshold_days"] == 1095
        assert data["unused_file_threshold_days"] == 730

    def test_reset_artefact_filter_preferences(self, mock_db_adapter):
        """Test la réinitialisation des préférences"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = None
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.post("/api/artefact-filters/preferences/reset")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["large_file_threshold_mb"] == 1024
        assert data["old_file_threshold_days"] == 730
        assert data["unused_file_threshold_days"] == 365

    def test_get_artefact_filter_presets(self):
        """Test la récupération des préréglages"""
        # Appeler l'endpoint (pas de mock nécessaire, données statiques)
        response = client.get("/api/artefact-filters/presets")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier les préréglages
        assert "conservateur" in data
        assert "standard" in data
        assert "agressif" in data
        
        # Vérifier les valeurs du préréglage conservateur
        assert data["conservateur"]["large_file_threshold_mb"] == 2048
        assert data["conservateur"]["old_file_threshold_days"] == 1095
        assert data["conservateur"]["unused_file_threshold_days"] == 730
        
        # Vérifier les valeurs du préréglage agressif
        assert data["agressif"]["large_file_threshold_mb"] == 512
        assert data["agressif"]["old_file_threshold_days"] == 365
        assert data["agressif"]["unused_file_threshold_days"] == 180
