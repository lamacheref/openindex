"""
Tests unitaires pour les fonctionnalités de Priorité 4
- Retry automatique avec 5 tentatives
- Gestion des fichiers disparus
- Gestion des conflits
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid
import os
import sys

# Ajouter le chemin du backend pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from workers.indexer_worker import IndexerWorker
from api.indexer_router import IndexerRetry

def test_indexer_retry_max_attempts():
    """Test que le nombre maximum de tentatives est bien de 5"""
    retry = IndexerRetry()
    assert retry.max_attempts == 5, "Le nombre maximum de tentatives devrait être 5"

def test_is_file_missing_detection():
    """Test la détection des fichiers disparus"""
    worker = IndexerWorker()

    # Test avec différents messages d'erreur
    missing_errors = [
        "File not found",
        "No such file or directory",
        "The file does not exist",
        "Path not found",
        "File disappeared during processing"
    ]

    for error in missing_errors:
        assert worker._is_file_missing(error), f"Should detect missing file: {error}"

    # Test avec des erreurs qui ne sont pas des fichiers disparus
    non_missing_errors = [
        "Access denied",
        "Permission denied",
        "File is locked",
        "Network error",
        "Generic error"
    ]

    for error in non_missing_errors:
        assert not worker._is_file_missing(error), f"Should not detect missing file: {error}"

def test_is_file_conflict_detection():
    """Test la détection des conflits de fichiers"""
    worker = IndexerWorker()

    # Test avec différents messages d'erreur de conflit
    conflict_errors = [
        "File already exists",
        "Conflict detected",
        "Duplicate file",
        "Hash mismatch",
        "Checksum mismatch",
        "Different content"
    ]

    for error in conflict_errors:
        assert worker._is_file_conflict(error), f"Should detect file conflict: {error}"

    # Test avec des erreurs qui ne sont pas des conflits
    non_conflict_errors = [
        "File not found",
        "Access denied",
        "Network error",
        "Generic error"
    ]

    for error in non_conflict_errors:
        assert not worker._is_file_conflict(error), f"Should not detect file conflict: {error}"

@patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
def test_mark_file_as_missing(mock_db):
    """Test le marquage des fichiers disparus"""
    worker = IndexerWorker()

    # Configuration du mock
    mock_db_instance = mock_db.return_value
    mock_db_instance.execute_query.return_value = None

    # Test de la méthode
    file_path = "/test/file.txt"
    config_id = "test-config"
    error_message = "File not found"

    worker._mark_file_as_missing(file_path, config_id, error_message)

    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_db_instance.execute_query.assert_called_once()
    call_args = mock_db_instance.execute_query.call_args[0][0]
    assert "missing_files" in call_args
    assert file_path in call_args
    assert config_id in call_args
    assert error_message in call_args

@patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
def test_handle_file_conflict(mock_db):
    """Test la gestion des conflits de fichiers"""
    worker = IndexerWorker()

    # Configuration du mock
    mock_db_instance = mock_db.return_value
    mock_db_instance.execute_query.return_value = None

    # Test de la méthode
    file_info = {
        'path': '/test/file.txt',
        'name': 'file.txt',
        'checksum': 'abc123',
        'size': 1024
    }
    config_id = "test-config"
    error_message = "File already exists"

    worker._handle_file_conflict(file_info, config_id, error_message)

    # Vérifier que la méthode a été appelée avec les bons paramètres
    calls = mock_db_instance.execute_query.call_args_list
    assert len(calls) == 2  # Une pour le conflit, une pour l'insertion

    # Vérifier le premier appel (enregistrement du conflit)
    first_call = calls[0][0][0]
    assert "file_conflicts" in first_call
    assert "original_path" in first_call
    assert "conflict_path" in first_call

    # Vérifier que le fichier a été renommé
    assert file_info['name'] == 'file_conflict_1.txt'
    assert file_info['path'] == '/test/file_conflict_1.txt'

@patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
def test_retry_logging_improvements(mock_db):
    """Test les améliorations du logging pour les retries"""
    worker = IndexerWorker()

    # Configuration du mock
    mock_db_instance = mock_db.return_value
    mock_db_instance.execute_query.return_value = None

    # Test avec un fichier verrouillé
    file_info = {
        'path': '/test/locked_file.txt',
        'name': 'locked_file.txt',
        'checksum': 'abc123',
        'size': 1024
    }
    config_id = "test-config"
    error_message = "File is locked by another process"

    # Simuler un current_job
    worker.current_job = Mock()
    worker.current_job.id = "test-job-123"

    # Appeler la méthode d'insertion qui devrait déclencher le retry
    worker._insert_file(file_info, config_id)

    # Vérifier que le logging a été appelé avec les bons paramètres
    # (Ceci est un test simplifié - dans un vrai test, on utiliserait un mock pour le logger)

@patch('backend.src.database.postgres_adapter.PostgreSQLAdapter')
def test_missing_file_handling(mock_db):
    """Test la gestion complète des fichiers disparus"""
    worker = IndexerWorker()

    # Configuration du mock
    mock_db_instance = mock_db.return_value
    mock_db_instance.execute_query.return_value = None

    # Test avec un fichier disparu
    file_info = {
        'path': '/test/missing_file.txt',
        'name': 'missing_file.txt',
        'checksum': 'abc123',
        'size': 1024
    }
    config_id = "test-config"
    error_message = "File not found"

    # Simuler un current_job
    worker.current_job = Mock()
    worker.current_job.id = "test-job-123"

    # Appeler la méthode d'insertion qui devrait déclencher la gestion des fichiers disparus
    worker._insert_file(file_info, config_id)

    # Vérifier que le fichier a été marqué comme disparu
    mock_db_instance.execute_query.assert_called_once()
    call_args = mock_db_instance.execute_query.call_args[0][0]
    assert "missing_files" in call_args

def test_retry_count_increment():
    """Test l'incrémentation du compteur de tentatives"""
    worker = IndexerWorker()

    # Simuler un fichier avec plusieurs tentatives
    file_path = "/test/file.txt"

    # Vérifier que le compteur commence à 0
    assert worker._get_retry_count(file_path) == 0

    # Note: Ce test est simplifié car la méthode _get_retry_count
    # dépend de la base de données. Dans un vrai test, on mockerait
    # la base de données pour retourner des valeurs spécifiques.

if __name__ == "__main__":
    pytest.main([__file__, "-v"])