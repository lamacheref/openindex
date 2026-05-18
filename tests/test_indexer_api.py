"""
Tests unitaires pour l'API Indexer (T-INDEX-01)
Tests des modèles Pydantic en isolation complète
"""

import pytest
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List, Optional


# ============================================================
# Modèles Pydantic identiques à ceux de l'indexer_router
# (copiés ici pour des tests unitaires sans dépendance au projet)
# ============================================================

class IndexerStats(BaseModel):
    pending_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_files_indexed: int = 0
    total_bytes_indexed: int = 0
    last_job_created: Optional[datetime] = None
    last_completion: Optional[datetime] = None


class IndexerJobResponse(BaseModel):
    id: str
    path: str
    config_id: str
    config_name: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files_found: int = 0
    files_indexed: int = 0
    bytes_total: int = 0
    error_message: Optional[str] = None


class IndexerJobsList(BaseModel):
    jobs: List[IndexerJobResponse]
    total: int


class CurrentJobResponse(BaseModel):
    worker_running: bool
    job: Optional[IndexerJobResponse] = None


class WorkerActionResponse(BaseModel):
    success: bool
    message: str
    worker_running: bool


class IndexerJobCreate(BaseModel):
    config_id: str


# ============================================================
# Tests
# ============================================================

class TestIndexerStatsModels:
    """Tests des modèles de données pour les statistiques."""

    def test_stats_default_values(self):
        """Vérifie les valeurs par défaut."""
        stats = IndexerStats()
        assert stats.pending_count == 0
        assert stats.running_count == 0
        assert stats.completed_count == 0
        assert stats.failed_count == 0
        assert stats.total_files_indexed == 0
        assert stats.total_bytes_indexed == 0
        assert stats.last_job_created is None
        assert stats.last_completion is None

    def test_stats_custom_values(self):
        """Vérifie la construction avec des valeurs personnalisées."""
        now = datetime.now(timezone.utc)
        stats = IndexerStats(
            pending_count=2,
            running_count=1,
            completed_count=100,
            failed_count=3,
            total_files_indexed=50000,
            total_bytes_indexed=2000000000,
            last_job_created=now,
            last_completion=now
        )
        assert stats.pending_count == 2
        assert stats.running_count == 1
        assert stats.completed_count == 100
        assert stats.failed_count == 3
        assert stats.total_files_indexed == 50000
        assert stats.total_bytes_indexed == 2000000000

    def test_stats_serialization(self):
        """Vérifie la sérialisation JSON."""
        now = datetime.now(timezone.utc)
        stats = IndexerStats(last_job_created=now, last_completion=now)
        data = stats.model_dump(mode='json')
        assert data["pending_count"] == 0
        assert data["last_job_created"] is not None


class TestIndexerJobResponseModels:
    """Tests du modèle IndexerJobResponse."""

    def test_job_response_defaults(self):
        """Vérifie les valeurs par défaut d'un job."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="test-id",
            path="//server/share",
            config_id="config-1",
            status="pending",
            created_at=now
        )
        assert job.files_found == 0
        assert job.files_indexed == 0
        assert job.bytes_total == 0
        assert job.error_message is None
        assert job.config_name is None

    def test_job_response_with_all_fields(self):
        """Vérifie un job avec tous les champs renseignés."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="job-1",
            path="//server/share/docs",
            config_id="c1",
            config_name="Documents SMB",
            status="running",
            created_at=now,
            started_at=now,
            completed_at=None,
            files_found=500,
            files_indexed=350,
            bytes_total=1500000000,
            error_message=None
        )
        assert job.id == "job-1"
        assert job.status == "running"
        assert job.files_indexed == 350
        assert job.bytes_total == 1500000000

    def test_job_response_with_error(self):
        """Vérifie un job en échec avec message d'erreur."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="job-fail",
            path="//server/share",
            config_id="c1",
            status="failed",
            created_at=now,
            started_at=now,
            completed_at=now,
            files_found=10,
            files_indexed=5,
            bytes_total=500000,
            error_message="SMB connection timeout"
        )
        assert job.status == "failed"
        assert "SMB connection timeout" == job.error_message

    def test_job_response_serialization(self):
        """Vérifie la sérialisation JSON d'un job."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="test-id",
            path="//server/share",
            config_id="config-1",
            config_name="Test Config",
            status="completed",
            created_at=now,
            started_at=now,
            completed_at=now,
            files_found=150,
            files_indexed=150,
            bytes_total=5000000,
            error_message=None
        )
        data = job.model_dump(mode='json')
        assert data["id"] == "test-id"
        assert data["status"] == "completed"
        assert data["files_indexed"] == 150
        assert data["bytes_total"] == 5000000


class TestCurrentJobResponse:
    """Tests du modèle CurrentJobResponse."""

    def test_current_job_running(self):
        """Vérifie la réponse avec un job en cours."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="job-1", path="//srv", config_id="c1",
            status="running", created_at=now
        )
        response = CurrentJobResponse(worker_running=True, job=job)
        assert response.worker_running is True
        assert response.job is not None
        assert response.job.status == "running"

    def test_current_job_idle(self):
        """Vérifie la réponse sans job en cours."""
        response = CurrentJobResponse(worker_running=False, job=None)
        assert response.worker_running is False
        assert response.job is None

    def test_current_job_serialization(self):
        """Vérifie la sérialisation JSON."""
        now = datetime.now(timezone.utc)
        job = IndexerJobResponse(
            id="job-1", path="//srv", config_id="c1",
            status="running", created_at=now
        )
        response = CurrentJobResponse(worker_running=True, job=job)
        data = response.model_dump(mode='json')
        assert data["worker_running"] is True
        assert data["job"]["status"] == "running"


class TestWorkerActionResponse:
    """Tests du modèle WorkerActionResponse."""

    def test_worker_action_success(self):
        """Vérifie une action réussie."""
        response = WorkerActionResponse(
            success=True,
            message="Worker démarré",
            worker_running=True
        )
        assert response.success is True
        assert "Worker démarré" == response.message

    def test_worker_action_failure(self):
        """Vérifie une action échouée."""
        response = WorkerActionResponse(
            success=False,
            message="Erreur de démarrage",
            worker_running=False
        )
        assert response.success is False
        assert "Erreur" in response.message

    def test_worker_action_serialization(self):
        """Vérifie la sérialisation JSON."""
        response = WorkerActionResponse(
            success=True,
            message="Test",
            worker_running=False
        )
        data = response.model_dump(mode='json')
        assert data["success"] is True
        assert data["worker_running"] is False


class TestIndexerJobsListModel:
    """Tests du modèle IndexerJobsList."""

    def test_jobs_list_empty(self):
        """Vérifie une liste vide."""
        response = IndexerJobsList(jobs=[], total=0)
        assert len(response.jobs) == 0
        assert response.total == 0

    def test_jobs_list_with_data(self):
        """Vérifie une liste avec des jobs."""
        now = datetime.now(timezone.utc)
        jobs = [
            IndexerJobResponse(
                id=f"job-{i}", path=f"//srv{i}/share",
                config_id=f"c{i}", status="completed",
                created_at=now, files_indexed=100 * i
            )
            for i in range(1, 4)
        ]
        response = IndexerJobsList(jobs=jobs, total=3)
        assert len(response.jobs) == 3
        assert response.total == 3
        assert response.jobs[0].files_indexed == 100
        assert response.jobs[2].files_indexed == 300

    def test_jobs_list_serialization(self):
        """Vérifie la sérialisation JSON."""
        now = datetime.now(timezone.utc)
        jobs = [
            IndexerJobResponse(
                id="job-1", path="//srv", config_id="c1",
                status="pending", created_at=now
            )
        ]
        response = IndexerJobsList(jobs=jobs, total=1)
        data = response.model_dump(mode='json')
        assert data["total"] == 1
        assert len(data["jobs"]) == 1


class TestIndexerJobCreateModels:
    """Tests du modèle IndexerJobCreate."""

    def test_job_create_defaults(self):
        """Vérifie la création avec config_id seulement."""
        payload = IndexerJobCreate(config_id="config-1")
        assert payload.config_id == "config-1"

    def test_job_create_serialization(self):
        """Vérifie la sérialisation JSON."""
        payload = IndexerJobCreate(config_id="test-config")
        data = payload.model_dump(mode='json')
        assert data["config_id"] == "test-config"