"""
Tests pour les endpoints de détails des doublons (T-ART-02)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime

# Importer l'application FastAPI
from backend.src.api.main import app

client = TestClient(app)


# Fixture pour mocker l'adaptateur de base de données
@pytest.fixture
def mock_db_adapter(monkeypatch):
    """Mock de l'adaptateur de base de données"""
    # Définir les variables d'environnement PostgreSQL pour éviter les erreurs de connexion
    monkeypatch.setenv('POSTGRES_HOST', 'localhost')
    monkeypatch.setenv('POSTGRES_PORT', '5432')
    monkeypatch.setenv('POSTGRES_DB', 'openindex')
    monkeypatch.setenv('POSTGRES_USER', 'openindex_user')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'openindex_secure_password')
    
    with patch('backend.src.api.duplicate_details_router.get_db_adapter') as mock:
        yield mock


# Données de test pour les occurrences de doublons
DUPLICATE_OCCURRENCES_DATA = [
    (
        '9f634870-8881-4a7f-9eef-e23b180d3aab',
        '\\172.16.252.34\Public\SMIDEN\Technique\test.pdf',
        'test.pdf',
        8376878,
        '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363',
        datetime(2026, 1, 14, 11, 53, 8),
        None,
        'config-uuid-1'
    ),
    (
        'dd22238e-070a-4780-afdd-1f577ef913ca',
        '\\172.16.252.34\Public\SMIDEN\coordination\test.pdf',
        'test.pdf',
        8376878,
        '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363',
        datetime(2026, 1, 16, 11, 14, 5),
        None,
        'config-uuid-2'
    ),
    (
        '2eb28c02-1ddd-44fd-8ea6-31ff28b7665d',
        '\\172.16.252.34\Public\SMIDEN\archive\test.pdf',
        'test.pdf',
        8376878,
        '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363',
        datetime(2026, 1, 15, 9, 30, 0),
        None,
        'config-uuid-3'
    )
]


class TestDuplicateDetailsAPI:
    """Tests pour les endpoints de détails des doublons"""

    def test_get_duplicate_file_details(self, mock_db_adapter):
        """Test la récupération des détails d'un fichier en doublon"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            DUPLICATE_OCCURRENCES_DATA[:1],  # Fichier principal
            DUPLICATE_OCCURRENCES_DATA,  # Toutes les occurrences
            [(3,)],  # Nombre total d'occurrences
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363'
        response = client.get(f"/api/duplicates/{checksum}/details?limit=10&offset=0")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["checksum"] == checksum
        assert data["name"] == "test.pdf"
        assert data["size"] == 8376878
        assert data["total_occurrences"] == 3
        assert len(data["occurrences"]) == 3
        
        # Vérifier les occurrences
        assert data["occurrences"][0]["path"] == '\\172.16.252.34\Public\SMIDEN\Technique\test.pdf'
        assert data["occurrences"][0]["crawl_config_name"] is None  # Non implémenté dans cette version
        assert data["occurrences"][1]["path"] == '\\172.16.252.34\Public\SMIDEN\coordination\test.pdf'
        assert data["occurrences"][1]["crawl_config_name"] is None  # Non implémenté dans cette version

    def test_get_duplicate_file_details_not_found(self, mock_db_adapter):
        """Test le cas où le fichier n'est pas trouvé"""
        # Configurer le mock pour retourner aucun résultat
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [],  # Aucun fichier principal
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = 'nonexistent_checksum'
        response = client.get(f"/api/duplicates/{checksum}/details")
        
        # Vérifications
        assert response.status_code == 404
        assert "non trouvé" in response.json()["detail"]

    def test_keep_duplicate_occurrence(self, mock_db_adapter):
        """Test le marquage d'une occurrence comme à conserver"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [(1,)],  # Vérification réussie
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363'
        occurrence_id = '9f634870-8881-4a7f-9eef-e23b180d3aab'
        response = client.post(f"/api/duplicates/{checksum}/keep?occurrence_id={occurrence_id}")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == f"Occurrence {occurrence_id} marquée comme à conserver"
        assert data["checksum"] == checksum

    def test_keep_duplicate_occurrence_not_found(self, mock_db_adapter):
        """Test le cas où l'occurrence n'est pas trouvée"""
        # Configurer le mock pour retourner aucun résultat
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [],  # Vérification échouée
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363'
        occurrence_id = 'nonexistent_id'
        response = client.post(f"/api/duplicates/{checksum}/keep?occurrence_id={occurrence_id}")
        
        # Vérifications
        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"]

    def test_delete_duplicate_occurrences(self, mock_db_adapter):
        """Test la suppression de toutes les occurrences sauf une"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [(1,)],  # Vérification réussie
            [
                ('dd22238e-070a-4780-afdd-1f577ef913ca',),
                ('2eb28c02-1ddd-44fd-8ea6-31ff28b7665d',)
            ]  # Occurrences supprimées
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363'
        keep_occurrence_id = '9f634870-8881-4a7f-9eef-e23b180d3aab'
        response = client.delete(f"/api/duplicates/{checksum}/occurrences?keep_occurrence_id={keep_occurrence_id}")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["deleted_count"] == 2
        assert len(data["deleted_ids"]) == 2
        assert data["kept_occurrence_id"] == keep_occurrence_id

    def test_delete_duplicate_occurrences_not_found(self, mock_db_adapter):
        """Test le cas où l'occurrence à conserver n'est pas trouvée"""
        # Configurer le mock pour retourner aucun résultat
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [],  # Vérification échouée
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        checksum = '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363'
        keep_occurrence_id = 'nonexistent_id'
        response = client.delete(f"/api/duplicates/{checksum}/occurrences?keep_occurrence_id={keep_occurrence_id}")
        
        # Vérifications
        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"]
