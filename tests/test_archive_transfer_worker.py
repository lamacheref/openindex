"""
Tests unitaires pour l'Archive Transfer Worker (T-ARCH-01)
"""

import pytest
import time
import random
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from archive_transfer_worker import (
    ArchiveTransferWorker,
    TransferJob,
    TransferStatus,
    calculate_backoff_delay,
    retry_with_backoff
)


class TestBackoffDelay:
    """Tests pour le calcul du délai de retry avec backoff."""

    def test_calculate_backoff_delay_base(self):
        """Test du délai de base sans retry."""
        delay = calculate_backoff_delay(0, base_delay=1.0, max_delay=60.0, jitter=False)
        assert delay == 1.0

    def test_calculate_backoff_delay_exponential(self):
        """Test de la croissance exponentielle du délai."""
        # Tentative 1: 1.0 * 2^1 = 2.0
        delay = calculate_backoff_delay(1, base_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)
        assert delay == 2.0

        # Tentative 2: 1.0 * 2^2 = 4.0
        delay = calculate_backoff_delay(2, base_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)
        assert delay == 4.0

        # Tentative 3: 1.0 * 2^3 = 8.0
        delay = calculate_backoff_delay(3, base_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)
        assert delay == 8.0

    def test_calculate_backoff_delay_max_cap(self):
        """Test du plafonnement au délai maximum."""
        # Avec max_delay=10.0, même avec retry_count=10, le délai ne doit pas dépasser 10.0
        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=10.0, jitter=False)
        assert delay == 10.0

    def test_calculate_backoff_delay_with_jitter(self):
        """Test que le jitter est appliqué (±25%)."""
        base_delay = 1.0
        delay = calculate_backoff_delay(0, base_delay=base_delay, jitter=True)
        
        # Le délai doit être entre 0.75 et 1.25 du délai de base
        assert 0.75 * base_delay <= delay <= 1.25 * base_delay

    def test_calculate_backoff_delay_different_bases(self):
        """Test avec différentes bases exponentielles."""
        # Base 1.5
        delay = calculate_backoff_delay(2, base_delay=1.0, exponential_base=1.5, max_delay=60.0, jitter=False)
        assert delay == 2.25  # 1.0 * 1.5^2 = 2.25

        # Base 3.0
        delay = calculate_backoff_delay(2, base_delay=1.0, exponential_base=3.0, max_delay=60.0, jitter=False)
        assert delay == 9.0  # 1.0 * 3^2 = 9.0


class TestRetryWithBackoff:
    """Tests pour le décorateur de retry."""

    def test_retry_success_first_attempt(self):
        """Test qu'une fonction réussie du premier coup n'est pas retry."""
        mock_func = Mock(return_value="success")
        
        decorated = retry_with_backoff(max_retries=3, base_delay=0.1)(mock_func)
        result = decorated("arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_retry_success_after_failure(self):
        """Test que la fonction est retry après un échec."""
        mock_func = Mock(side_effect=[ValueError("error"), "success"])
        
        decorated = retry_with_backoff(
            max_retries=3, 
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_exhausted_raises_exception(self):
        """Test que l'exception est propagée après épuisement des retries."""
        mock_func = Mock(side_effect=ValueError("persistent error"))
        
        decorated = retry_with_backoff(
            max_retries=2, 
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )(mock_func)
        
        with pytest.raises(ValueError, match="persistent error"):
            decorated()
        
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_retry_non_retryable_exception(self):
        """Test que les exceptions non retryables ne déclenchent pas de retry."""
        mock_func = Mock(side_effect=KeyError("non retryable"))
        
        decorated = retry_with_backoff(
            max_retries=3, 
            base_delay=0.01,
            retryable_exceptions=(ValueError,)  # KeyError n'est pas dans la liste
        )(mock_func)
        
        with pytest.raises(KeyError):
            decorated()
        
        assert mock_func.call_count == 1  # Pas de retry


class TestTransferJob:
    """Tests pour la classe TransferJob."""

    def test_transfer_job_creation(self):
        """Test de création d'un job de transfert."""
        job = TransferJob(
            id="test-id-123",
            job_type="copy",
            source_path="\\\\server\\share\\file.txt",
            dest_path="\\\\archive\\share\\file.txt",
            priority=5,
            retry_count=0,
            max_retries=3,
            source_size=1024,
            source_checksum="abc123"
        )
        
        assert job.id == "test-id-123"
        assert job.job_type == "copy"
        assert job.source_path == "\\\\server\\share\\file.txt"
        assert job.dest_path == "\\\\archive\\share\\file.txt"
        assert job.priority == 5
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.source_size == 1024
        assert job.source_checksum == "abc123"

    def test_transfer_job_optional_dest(self):
        """Test qu'un job de type 'delete' n'a pas besoin de dest_path."""
        job = TransferJob(
            id="test-id-456",
            job_type="delete",
            source_path="\\\\server\\share\\old.txt",
            dest_path=None,
            priority=3,
            retry_count=1,
            max_retries=3
        )
        
        assert job.job_type == "delete"
        assert job.dest_path is None


class TestArchiveTransferWorkerUnit:
    """Tests unitaires pour ArchiveTransferWorker."""

    @pytest.fixture
    def mock_adapter(self):
        """Fixture pour un adaptateur PostgreSQL mocké."""
        adapter = Mock()
        adapter.execute_query = Mock()
        return adapter

    @pytest.fixture
    def worker(self, mock_adapter):
        """Fixture pour un worker avec adaptateur mocké."""
        with patch('archive_transfer_worker.PostgreSQLAdapter', return_value=mock_adapter):
            with patch('archive_transfer_worker.get_logger_manager'):
                worker = ArchiveTransferWorker(
                    poll_interval=5,
                    max_concurrent=3,
                    chunk_size=8192
                )
                worker.adapter = mock_adapter
                worker.logger = Mock()
                return worker

    def test_worker_initialization(self, worker):
        """Test de l'initialisation du worker."""
        assert worker.poll_interval == 5
        assert worker.max_concurrent == 3
        assert worker.chunk_size == 8192
        assert worker.stop_event.is_set() is False

    def test_get_next_job_success(self, worker, mock_adapter):
        """Test de récupération d'un job."""
        mock_adapter.execute_query.return_value = [
            ("job-123", "copy", "\\\\src\\file.txt", "\\\\dst\\file.txt", 5, 0)
        ]
        
        job = worker._get_next_job()
        
        assert job is not None
        assert job.id == "job-123"
        assert job.job_type == "copy"
        assert job.source_path == "\\\\src\\file.txt"
        assert job.dest_path == "\\\\dst\\file.txt"

    def test_get_next_job_empty_queue(self, worker, mock_adapter):
        """Test quand la queue est vide."""
        mock_adapter.execute_query.return_value = []
        
        job = worker._get_next_job()
        
        assert job is None

    def test_get_next_job_database_error(self, worker, mock_adapter):
        """Test de gestion d'erreur DB."""
        mock_adapter.execute_query.side_effect = Exception("DB error")
        
        job = worker._get_next_job()
        
        assert job is None
        worker.logger.error.assert_called()

    def test_update_job_status_success(self, worker, mock_adapter):
        """Test de mise à jour du statut en cas de succès."""
        worker._update_job_status("job-123", True, None, 1024)
        
        mock_adapter.execute_query.assert_called_once()
        call_args = mock_adapter.execute_query.call_args
        assert "completed" in call_args[0][0]

    def test_update_job_status_failure(self, worker, mock_adapter):
        """Test de mise à jour du statut en cas d'échec."""
        mock_adapter.execute_query.return_value = [(2, 3)]  # retry_count=2, max_retries=3
        
        worker._update_job_status("job-123", False, "Error message", 0)
        
        mock_adapter.execute_query.assert_called_once()
        call_args = mock_adapter.execute_query.call_args
        sql = call_args[0][0]
        assert "failed" in sql or "retry_count" in sql

    def test_get_stats(self, worker, mock_adapter):
        """Test de récupération des statistiques."""
        mock_adapter.execute_query.return_value = [
            ("pending", 5, 1024000),
            ("running", 2, 512000),
            ("completed", 100, 104857600)
        ]
        
        stats = worker.get_stats()
        
        assert "pending" in stats
        assert "running" in stats
        assert "completed" in stats
        assert stats["active_transfers"] == 0  # Pas de transferts actifs dans ce test


class TestArchiveTransferWorkerIntegration:
    """Tests d'intégration légère pour le worker."""

    @pytest.fixture
    def temp_worker(self, tmp_path):
        """Fixture créant un worker avec config temporaire."""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_openindex',
            'user': 'test_user',
            'password': 'test_pass'
        }
        
        with patch('archive_transfer_worker.PostgreSQLAdapter'):
            with patch('archive_transfer_worker.get_logger_manager'):
                worker = ArchiveTransferWorker(
                    poll_interval=1,
                    max_concurrent=2,
                    chunk_size=4096,
                    postgres_config=config
                )
                yield worker

    def test_worker_start_stop(self, temp_worker):
        """Test du démarrage et arrêt du worker."""
        # Démarrer le worker
        temp_worker.start()
        assert temp_worker.main_thread.is_alive()
        
        # Attendre un peu
        time.sleep(0.5)
        
        # Arrêter le worker
        temp_worker.stop()
        assert temp_worker.stop_event.is_set()


class TestEdgeCases:
    """Tests pour les cas limites et erreurs."""

    def test_backoff_delay_with_zero_base(self):
        """Test avec un délai de base nul."""
        delay = calculate_backoff_delay(1, base_delay=0.0, jitter=False)
        assert delay == 0.0

    def test_backoff_delay_with_very_large_retry_count(self):
        """Test avec un très grand nombre de retries."""
        delay = calculate_backoff_delay(1000, base_delay=1.0, max_delay=3600.0, jitter=False)
        assert delay == 3600.0  # Doit être plafonné

    def test_retry_with_zero_max_retries(self):
        """Test avec max_retries=0 (pas de retry autorisé)."""
        mock_func = Mock(side_effect=ValueError("error"))
        
        decorated = retry_with_backoff(
            max_retries=0, 
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        assert mock_func.call_count == 1  # Seulement l'appel initial


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
