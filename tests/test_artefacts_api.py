"""
Tests pour les endpoints d'artefacts (T-ART-01)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime

# Importer l'application FastAPI
from src.api.main import app

client = TestClient(app)


# Fixture pour mocker l'adaptateur de base de données
@pytest.fixture
def mock_db_adapter():
    """Mock de l'adaptateur de base de données"""
    with patch('src.api.artefacts_router.get_db_adapter') as mock:
        yield mock


# Données de test pour les doublons
DUPLICATE_FILES_DATA = [
    (
        '9f634870-8881-4a7f-9eef-e23b180d3aab',
        '\\172.16.252.34\Public\SMIDEN\Technique\test.pdf',
        'test.pdf',
        8376878,
        '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363',
        datetime(2026, 1, 14, 11, 53, 8),
        None,
        4
    ),
    (
        'dd22238e-070a-4780-afdd-1f577ef913ca',
        '\\172.16.252.34\Public\SMIDEN\coordination\test.pdf',
        'test.pdf',
        8376878,
        '0011f09e6ab79bad3363239d37cf26c47db32a04f972fab3b741218536067363',
        datetime(2026, 1, 16, 11, 14, 5),
        None,
        4
    )
]

# Données de test pour les gros fichiers
LARGE_FILES_DATA = [
    (
        'file1-uuid',
        '\\server\share\large1.iso',
        'large1.iso',
        2147483648,  # 2 Go
        'checksum1',
        datetime(2025, 1, 1),
        None,
        2.0
    ),
    (
        'file2-uuid',
        '\\server\share\large2.iso',
        'large2.iso',
        1572864000,  # 1.5 Go
        'checksum2',
        datetime(2025, 2, 1),
        None,
        1.5
    )
]

# Données de test pour les fichiers anciens
OLD_FILES_DATA = [
    (
        'old1-uuid',
        '\\server\share\old1.doc',
        'old1.doc',
        1024,
        'checksum-old1',
        datetime(2022, 1, 1),
        None,
        1095  # ~3 ans
    ),
    (
        'old2-uuid',
        '\\server\share\old2.doc',
        'old2.doc',
        2048,
        'checksum-old2',
        datetime(2023, 1, 1),
        None,
        730  # ~2 ans
    )
]


class TestArtefactsAPI:
    """Tests pour les endpoints d'artefacts"""

    def test_get_duplicate_files(self, mock_db_adapter):
        """Test la récupération des fichiers en doublon"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            DUPLICATE_FILES_DATA,  # Résultats des fichiers
            [(2, 16753756)]  # Statistiques (count, total_size)
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefacts/duplicates?limit=10&offset=0")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "duplicates"
        assert len(data["files"]) == 2
        assert data["stats"]["count"] == 2
        assert data["stats"]["total_size"] == 16753756
        assert data["files"][0]["duplicate_count"] == 4

    def test_get_large_files(self, mock_db_adapter):
        """Test la récupération des gros fichiers"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            LARGE_FILES_DATA,  # Résultats des fichiers
            [(2, 3720347648)]  # Statistiques (count, total_size)
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefacts/large?min_size_gb=1.0&limit=10&offset=0")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "large"
        assert len(data["files"]) == 2
        assert data["stats"]["count"] == 2
        assert data["stats"]["total_size"] == 3720347648
        assert data["files"][0]["size_gb"] == 2.0

    def test_get_old_files(self, mock_db_adapter):
        """Test la récupération des fichiers anciens"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            OLD_FILES_DATA,  # Résultats des fichiers
            [(2, 3072)]  # Statistiques (count, total_size)
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefacts/old?min_days=730&limit=10&offset=0")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "old"
        assert len(data["files"]) == 2
        assert data["stats"]["count"] == 2
        assert data["stats"]["total_size"] == 3072
        assert data["files"][0]["days_since_modified"] == 1095

    def test_get_unused_files(self, mock_db_adapter):
        """Test la récupération des fichiers inutilisés"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [],  # Résultats des fichiers (vide car aucun fichier inutilisé)
            [(0, 0)]  # Statistiques (count, total_size)
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefacts/unused?min_days=365&limit=10&offset=0")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "unused"
        assert len(data["files"]) == 0
        assert data["stats"]["count"] == 0
        assert data["stats"]["total_size"] == 0

    def test_get_artefacts_stats(self, mock_db_adapter):
        """Test la récupération des statistiques pour toutes les catégories"""
        # Configurer le mock
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [(3658, 123456789)],  # Doublons
            [(47, 50000000000)],  # Gros fichiers
            [(44144, 1000000000000)],  # Anciens
            [(0, 0)]  # Inutilisés
        ]
        mock_db_adapter.return_value = mock_db
        
        # Appeler l'endpoint
        response = client.get("/api/artefacts/stats")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        
        # Vérifier chaque catégorie
        categories = {stat["category"]: stat for stat in data}
        assert categories["duplicates"]["count"] == 3658
        assert categories["large"]["count"] == 47
        assert categories["old"]["count"] == 44144
        assert categories["unused"]["count"] == 0


class TestArtefactsEdgeCases:
    """Tests des cas limites pour les endpoints d'artefacts"""

    def test_get_duplicate_files_with_pagination(self, mock_db_adapter):
        """Test la pagination pour les doublons"""
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            DUPLICATE_FILES_DATA[:1],  # Un seul fichier
            [(2, 16753756)]  # Statistiques globales
        ]
        mock_db_adapter.return_value = mock_db
        
        response = client.get("/api/artefacts/duplicates?limit=1&offset=0")
        assert response.status_code == 200
        assert len(response.json()["files"]) == 1

    def test_get_large_files_with_custom_threshold(self, mock_db_adapter):
        """Test le seuil personnalisé pour les gros fichiers"""
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            LARGE_FILES_DATA[0:1],  # Un seul fichier
            [(1, 2147483648)]  # Statistiques pour ce seuil
        ]
        mock_db_adapter.return_value = mock_db
        
        response = client.get("/api/artefacts/large?min_size_gb=1.5&limit=10&offset=0")
        assert response.status_code == 200
        assert len(response.json()["files"]) == 1

    def test_get_old_files_with_custom_days(self, mock_db_adapter):
        """Test le seuil personnalisé pour les fichiers anciens"""
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            OLD_FILES_DATA[1:2],  # Un seul fichier
            [(1, 2048)]  # Statistiques pour ce seuil
        ]
        mock_db_adapter.return_value = mock_db
        
        response = client.get("/api/artefacts/old?min_days=1000&limit=10&offset=0")
        assert response.status_code == 200
        assert len(response.json()["files"]) == 1
