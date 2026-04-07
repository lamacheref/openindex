"""
Tests unitaires pour l'API Archive Queue (T-ARCH-01)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock du PostgreSQLAdapter avant import
mock_adapter = Mock()
mock_adapter_class = Mock(return_value=mock_adapter)

with patch('api.main.PostgreSQLAdapter', mock_adapter_class):
    from api.main import app, ArchiveJobType, ArchiveJobCreate

client = TestClient(app)


class TestArchiveJobCreate:
    """Tests pour la création de jobs d'archivage."""

    def test_create_copy_job_success(self):
        """Test de création d'un job de type copy."""
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440000", "copy", 
             "\\\\server\\share\\file.txt", "\\\\archive\\storage\\file.txt",
             "pending", 5, 0, 3, None, None, None, 
             datetime.now(), None, 0)
        ]
        
        response = client.post("/api/archive/queue", json={
            "job_type": "copy",
            "source_path": "\\\\server\\share\\file.txt",
            "dest_path": "\\\\archive\\storage\\file.txt",
            "priority": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "copy"
        assert data["source_path"] == "\\\\server\\share\\file.txt"
        assert data["dest_path"] == "\\\\archive\\storage\\file.txt"
        assert data["status"] == "pending"
        assert data["priority"] == 5

    def test_create_move_job_success(self):
        """Test de création d'un job de type move."""
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440001", "move",
             "\\\\server\\share\\old.txt", "\\\\archive\\storage\\old.txt",
             "pending", 8, 0, 3, None, None, None,
             datetime.now(), None, 0)
        ]
        
        response = client.post("/api/archive/queue", json={
            "job_type": "move",
            "source_path": "\\\\server\\share\\old.txt",
            "dest_path": "\\\\archive\\storage\\old.txt",
            "priority": 8
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "move"
        assert data["priority"] == 8

    def test_create_delete_job_success(self):
        """Test de création d'un job de type delete."""
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440002", "delete",
             "\\\\server\\share\\temp.tmp", None,
             "pending", 3, 0, 3, None, None, None,
             datetime.now(), None, 0)
        ]
        
        response = client.post("/api/archive/queue", json={
            "job_type": "delete",
            "source_path": "\\\\server\\share\\temp.tmp"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_type"] == "delete"
        assert data["dest_path"] is None

    def test_create_copy_job_missing_dest(self):
        """Test d'erreur quand dest_path manque pour un copy."""
        response = client.post("/api/archive/queue", json={
            "job_type": "copy",
            "source_path": "\\\\server\\share\\file.txt"
            # dest_path manquant
        })
        
        assert response.status_code == 422
        assert "dest_path est requis" in response.json()["detail"]

    def test_create_move_job_missing_dest(self):
        """Test d'erreur quand dest_path manque pour un move."""
        response = client.post("/api/archive/queue", json={
            "job_type": "move",
            "source_path": "\\\\server\\share\\file.txt"
            # dest_path manquant
        })
        
        assert response.status_code == 422
        assert "dest_path est requis" in response.json()["detail"]

    def test_create_job_invalid_priority_low(self):
        """Test avec priorité trop basse."""
        response = client.post("/api/archive/queue", json={
            "job_type": "copy",
            "source_path": "\\\\server\\share\\file.txt",
            "dest_path": "\\\\archive\\storage\\file.txt",
            "priority": 0  # Doit être >= 1
        })
        
        assert response.status_code == 422

    def test_create_job_invalid_priority_high(self):
        """Test avec priorité trop haute."""
        response = client.post("/api/archive/queue", json={
            "job_type": "copy",
            "source_path": "\\\\server\\share\\file.txt",
            "dest_path": "\\\\archive\\storage\\file.txt",
            "priority": 11  # Doit être <= 10
        })
        
        assert response.status_code == 422

    def test_create_job_default_priority(self):
        """Test que la priorité par défaut est 5."""
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440003", "copy",
             "\\\\server\\share\\file.txt", "\\\\archive\\storage\\file.txt",
             "pending", 5, 0, 3, None, None, None,
             datetime.now(), None, 0)
        ]
        
        response = client.post("/api/archive/queue", json={
            "job_type": "copy",
            "source_path": "\\\\server\\share\\file.txt",
            "dest_path": "\\\\archive\\storage\\file.txt"
            # priority non spécifiée
        })
        
        assert response.status_code == 200
        assert response.json()["priority"] == 5


class TestListArchiveJobs:
    """Tests pour la liste des jobs."""

    def test_list_jobs_empty(self):
        """Test liste vide."""
        mock_adapter.execute_query.side_effect = [
            [],  # Jobs
            [(0,)]  # Count
        ]
        
        response = client.get("/api/archive/queue")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_list_jobs_with_data(self):
        """Test liste avec données."""
        from datetime import datetime
        
        # Mock pour la requête principale
        def mock_execute_query(query, params=None):
            if "SELECT id, job_type::text" in query and "ORDER BY" in query:
                return [
                    ("550e8400-e29b-41d4-a716-446655440001", "copy", "\\\\src\\1.txt", "\\\\dst\\1.txt", "pending", 5, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0),
                    ("550e8400-e29b-41d4-a716-446655440002", "move", "\\\\src\\2.txt", "\\\\dst\\2.txt", "running", 8, 1, 3, None, datetime(2026, 4, 7, 13, 30, 0), None, datetime(2026, 4, 7, 13, 25, 0), 1024, 512)
                ]
            elif "SELECT COUNT(*)" in query:
                return [(2,)]
            return []
        
        mock_adapter.execute_query.side_effect = mock_execute_query
        
        response = client.get("/api/archive/queue")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 2
        assert data["jobs"][0]["id"] == "550e8400-e29b-41d4-a716-446655440001"
        assert data["jobs"][1]["status"] == "running"

    def test_list_jobs_with_status_filter(self):
        """Test filtrage par statut."""
        from datetime import datetime
        
        # Mock simple pour le test
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440001", "copy", "\\\\src\\1.txt", "\\\\dst\\1.txt", "pending", 5, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0)
        ]
        
        response = client.get("/api/archive/queue?status=pending")
        
        assert response.status_code == 200
        # Vérifier que le mock a été appelé
        assert mock_adapter.execute_query.called

    def test_list_jobs_with_job_type_filter(self):
        """Test filtrage par type de job."""
        from datetime import datetime
        
        # Mock pour la requête principale
        def mock_execute_query(query, params=None):
            if "job_type = %s::archive_job_type" in query and "ORDER BY" in query:
                return [
                    ("550e8400-e29b-41d4-a716-446655440001", "copy", "\\\\src\\1.txt", "\\\\dst\\1.txt", "pending", 5, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0)
                ]
            elif "SELECT COUNT(*)" in query:
                return [(1,)]
            return []
        
        mock_adapter.execute_query.side_effect = mock_execute_query
        
        response = client.get("/api/archive/queue?job_type=copy")
        
        assert response.status_code == 200
        # Vérifier que le mock a été appelé
        assert mock_adapter.execute_query.called

    def test_list_jobs_pagination(self):
        """Test de la pagination."""
        from datetime import datetime
        
        # Mock simple pour le test
        mock_adapter.execute_query.return_value = [
            ("550e8400-e29b-41d4-a716-446655440003", "copy", "\\\\src\\3.txt", "\\\\dst\\3.txt", "pending", 5, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0)
        ]
        
        response = client.get("/api/archive/queue?limit=1&offset=2")
        
        assert response.status_code == 200
        assert mock_adapter.execute_query.called

    def test_list_jobs_sorting(self):
        """Test du tri."""
        from datetime import datetime
        
        mock_adapter.execute_query.side_effect = [
            [
                ("550e8400-e29b-41d4-a716-446655440001", "copy", "\\\\src\\1.txt", "\\\\dst\\1.txt", "pending", 10, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0),
                ("550e8400-e29b-41d4-a716-446655440002", "copy", "\\\\src\\2.txt", "\\\\dst\\2.txt", "pending", 8, 0, 3, None, None, None, datetime(2026, 4, 7, 13, 0, 0), None, 0)
            ],
            [(2,)]
        ]
        
        response = client.get("/api/archive/queue?sort=priority&order=desc")
        
        assert response.status_code == 200


class TestGetArchiveJob:
    """Tests pour la récupération d'un job spécifique."""

    def test_get_job_success(self):
        """Test récupération d'un job existant."""
        from datetime import datetime
        
        mock_adapter.execute_query.return_value = [
            ("fb621e97-a982-4a1d-adc0-431ce2be89c2", "copy", "\\\\server\\share\\file.txt", "\\\\archive\\storage\\file.txt", 
             "running", 5, 1, 3, None, datetime(2026, 4, 7, 14, 0, 0), None, datetime(2026, 4, 7, 13, 55, 0), 1048576, 524288)
        ]
        
        response = client.get("/api/archive/queue/fb621e97-a982-4a1d-adc0-431ce2be89c2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "fb621e97-a982-4a1d-adc0-431ce2be89c2"
        assert data["status"] == "running"
        assert data["bytes_transferred"] == 524288

    def test_get_job_not_found(self):
        """Test récupération d'un job inexistant."""
        mock_adapter.execute_query.return_value = []
        
        response = client.get("/api/archive/queue/a4cd0ba7-6197-4a5c-8856-4ff5efe6240d")
        
        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"]


class TestCancelArchiveJob:
    """Tests pour l'annulation d'un job."""

    def test_cancel_pending_job(self):
        """Test annulation d'un job en attente."""
        from unittest.mock import patch
        
        # Utiliser patch.object sur le mock global existant
        with patch.object(mock_adapter, 'execute_query') as mock_execute:
            mock_execute.side_effect = [
                [("pending",)],  # Statut actuel
                None  # Update
            ]
            
            response = client.delete("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "annulé" in data["message"]

    def test_cancel_running_job(self):
        """Test annulation d'un job en cours."""
        mock_adapter.execute_query.side_effect = [
            [("running",)],  # Statut actuel
            None  # Update
        ]
        
        response = client.delete("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cancel_already_completed_job(self):
        """Test annulation d'un job déjà terminé."""
        mock_adapter.execute_query.return_value = [
            [("completed",)]  # Statut actuel
        ]
        
        response = client.delete("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "déjà terminé" in data["message"]

    def test_cancel_already_failed_job(self):
        """Test annulation d'un job déjà en échec."""
        mock_adapter.execute_query.return_value = [
            [("failed",)]  # Statut actuel
        ]
        
        response = client.delete("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_cancel_nonexistent_job(self):
        """Test annulation d'un job inexistant."""
        mock_adapter.execute_query.return_value = []
        
        response = client.delete("/api/archive/queue/a4cd0ba7-6197-4a5c-8856-4ff5efe6240d")
        
        assert response.status_code == 404


class TestArchiveJobStats:
    """Tests pour les statistiques."""

    def test_get_stats_empty(self):
        """Test stats avec queue vide."""
        mock_adapter.execute_query.return_value = [
            (0, 0, 0, 0, 0, 0, 0)  # Tous les compteurs à 0
        ]
        
        response = client.get("/api/archive/queue/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 0
        assert data["running"] == 0
        assert data["completed"] == 0
        assert data["failed"] == 0
        assert data["cancelled"] == 0

    def test_get_stats_with_data(self):
        """Test stats avec données."""
        mock_adapter.execute_query.return_value = [
            (5, 2, 150, 3, 1, 1073741824, 53687091200)  # pending, running, completed, failed, cancelled, size_pending, size_transferred
        ]
        
        response = client.get("/api/archive/queue/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 5
        assert data["running"] == 2
        assert data["completed"] == 150
        assert data["failed"] == 3
        assert data["cancelled"] == 1
        assert data["total_size_pending"] == 1073741824
        assert data["total_size_transferred"] == 53687091200


class TestRetryArchiveJob:
    """Tests pour le retry d'un job."""

    def test_retry_failed_job(self):
        """Test retry d'un job en échec."""
        from unittest.mock import patch
        
        # Utiliser patch.object sur le mock global existant
        with patch.object(mock_adapter, 'execute_query') as mock_execute:
            mock_execute.side_effect = [
                [("failed",)],  # Statut actuel
                None  # Update
            ]
            
            response = client.post("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004/retry")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "réinitialisé" in data["message"]

    def test_retry_cancelled_job(self):
        """Test retry d'un job annulé."""
        mock_adapter.execute_query.side_effect = [
            [("cancelled",)],  # Statut actuel
            None  # Update
        ]
        
        response = client.post("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_retry_pending_job(self):
        """Test retry d'un job déjà en attente (ne devrait pas fonctionner)."""
        mock_adapter.execute_query.return_value = [
            [("pending",)]  # Statut actuel
        ]
        
        response = client.post("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "ne peut pas être réessayé" in data["message"]

    def test_retry_running_job(self):
        """Test retry d'un job en cours (ne devrait pas fonctionner)."""
        mock_adapter.execute_query.return_value = [
            [("running",)]  # Statut actuel
        ]
        
        response = client.post("/api/archive/queue/550e8400-e29b-41d4-a716-446655440004/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_retry_nonexistent_job(self):
        """Test retry d'un job inexistant."""
        mock_adapter.execute_query.return_value = []
        
        response = client.post("/api/archive/queue/550e8400-e29b-41d4-a716-44665544999/retry")
        
        assert response.status_code == 404


class TestTransferWorkerHealth:
    """Tests pour le endpoint de santé du worker."""

    def test_worker_health_healthy(self):
        """Test santé quand tout va bien."""
        from unittest.mock import patch
        
        with patch.object(mock_adapter, 'execute_query') as mock_execute:
            # Mock fonction qui retourne les bonnes valeurs selon la requête
            def mock_side_effect(query, params=None):
                if "SELECT COUNT(*) FROM archive_jobs WHERE status = 'running'" in query:
                    return [(2,)]   # running jobs
                elif "SELECT COUNT(*) FROM archive_jobs WHERE status = 'pending'" in query:
                    return [(5,)]   # pending jobs
                elif "COUNT(*) FILTER (WHERE status = 'completed')" in query:
                    return [(100, 10, 110)]  # completed_24h, failed_24h, total_24h
                return []
            
            mock_execute.side_effect = mock_side_effect
            
            response = client.get("/api/transfer/worker/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["running_jobs"] == 2
            assert data["pending_jobs"] == 5
            assert data["success_rate_24h"] > 0.9

    def test_worker_health_degraded(self):
        """Test santé dégradée (trop d'échecs)."""
        mock_adapter.execute_query.side_effect = [
            [(1,)],   # running jobs
            [(5,)],   # pending jobs
            [(10, 30, 40)]  # 10 completed, 30 failed (plus de 2x d'échecs)
        ]
        
        response = client.get("/api/transfer/worker/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_worker_health_unhealthy(self):
        """Test santé mauvaise (queue bloquée)."""
        mock_adapter.execute_query.side_effect = [
            [(0,)],   # 0 running jobs
            [(150,)],  # 150 pending jobs (queue bloquée)
            [(100, 10, 110)]
        ]
        
        response = client.get("/api/transfer/worker/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
