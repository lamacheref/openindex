"""
Router API pour le service d'indexation (Indexer Worker)
Endpoints pour le monitoring et le contrôle des jobs d'indexation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import uuid
import logging

logger = logging.getLogger("openindex.api.indexer")

router = APIRouter(
    prefix="/api/indexer",
    tags=["indexer"]
)

# Modèles Pydantic
class IndexerStats(BaseModel):
    pending_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_files_indexed: int = 0
    total_bytes_indexed: int = 0
    last_job_created: Optional[datetime] = None
    last_completion: Optional[datetime] = None

class IndexerJobCreate(BaseModel):
    config_id: str

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
    dirs_found: int = 0
    phase: str = ""
    phase_b_done: bool = False
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

class IndexerPerformance(BaseModel):
    files_processed: int = 0
    errors_count: int = 0
    files_per_second: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0
    last_reset: Optional[str] = None

class IndexerHealth(BaseModel):
    status: str
    worker_running: bool = False
    database_connected: bool = False
    current_job: bool = False
    pending_jobs: int = 0
    timestamp: Optional[str] = None
    error: Optional[str] = None

class IndexerRetry(BaseModel):
    file_id: str
    file_path: str
    job_id: str
    config_id: str
    attempt_count: int = 0
    max_attempts: int = 5
    next_retry_at: Optional[str] = None
    last_error: Optional[str] = None
    created_at: Optional[str] = None

class IndexerRetriesList(BaseModel):
    retries: List[IndexerRetry]
    total: int = 0

class LogEntry(BaseModel):
    timestamp: str
    message: str

class LogsResponse(BaseModel):
    service: str
    lines: List[LogEntry]

# Fonction utilitaire pour obtenir l'adaptateur DB
def get_db_adapter():
    """Retourne l'adaptateur de base de données"""
    try:
        from backend.src.api.main import PostgreSQLAdapter
        import os

        config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        return PostgreSQLAdapter(config)
    except Exception as e:
        logger.error(f"Erreur DB: {e}")
        raise HTTPException(status_code=500, detail="Erreur de base de données")

@router.get("/stats", response_model=IndexerStats)
async def get_indexer_stats():
    """Récupère les statistiques globales de l'indexation"""
    try:
        db = get_db_adapter()

        query = """
            SELECT
                (
                    SELECT COUNT(*) FROM crawl_runs WHERE LOWER(status) = 'queued'
                ) + (
                    SELECT COUNT(*) FROM indexer_jobs WHERE LOWER(status) IN ('pending', 'queued')
                ) as pending_count,
                (
                    SELECT COUNT(*) FROM crawl_runs WHERE LOWER(status) IN ('running', 'in_progress')
                ) + (
                    SELECT COUNT(*) FROM indexer_jobs WHERE LOWER(status) = 'running'
                ) as running_count,
                (
                    SELECT COUNT(*) FROM crawl_runs WHERE LOWER(status) = 'completed'
                ) + (
                    SELECT COUNT(*) FROM indexer_jobs WHERE LOWER(status) = 'completed'
                ) as completed_count,
                (
                    SELECT COUNT(*) FROM crawl_runs WHERE LOWER(status) = 'failed'
                ) + (
                    SELECT COUNT(*) FROM indexer_jobs WHERE LOWER(status) = 'failed'
                ) as failed_count,
                (SELECT COUNT(*) FROM indexed_files_optimized WHERE NOT is_deleted AND NOT is_duplicate) as total_files_indexed,
                (SELECT COALESCE(SUM(size), 0) FROM indexed_files_optimized WHERE NOT is_deleted AND NOT is_duplicate) as total_bytes_indexed,
                COALESCE(
                    (SELECT MAX(triggered_at) FROM crawl_runs),
                    (SELECT MAX(created_at) FROM indexer_jobs)
                ) as last_job_created,
                COALESCE(
                    (SELECT MAX(triggered_at) FROM crawl_runs WHERE LOWER(status) = 'completed'),
                    (SELECT MAX(completed_at) FROM indexer_jobs WHERE LOWER(status) = 'completed')
                ) as last_completion
        """

        results = db.execute_query(query)

        if results:
            row = results[0]
            return IndexerStats(
                pending_count=row[0] or 0,
                running_count=row[1] or 0,
                completed_count=row[2] or 0,
                failed_count=row[3] or 0,
                total_files_indexed=row[4] or 0,
                total_bytes_indexed=row[5] or 0,
                last_job_created=row[6],
                last_completion=row[7]
            )

        return IndexerStats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.get("/current-job", response_model=CurrentJobResponse)
async def get_current_job():
    """Récupère le job d'indexation en cours"""
    try:
        db = get_db_adapter()

        # Chercher le job en cours
        query = """
            SELECT id, path, config_id, config_name, status, created_at,
                   started_at, completed_at, files_found, files_indexed,
                   bytes_total, dirs_found, phase, phase_b_done, error_message
            FROM indexer_jobs
            WHERE status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """

        results = db.execute_query(query)

        job = None
        if results:
            row = results[0]
            job = IndexerJobResponse(
                id=str(row[0]),
                path=row[1],
                config_id=str(row[2]),
                config_name=row[3],
                status=row[4],
                created_at=row[5],
                started_at=row[6],
                completed_at=row[7],
                files_found=row[8] or 0,
                files_indexed=row[9] or 0,
                bytes_total=row[10] or 0,
                dirs_found=row[11] or 0,
                phase=row[12] or '',
                phase_b_done=row[13] if len(row) > 13 else False,
                error_message=row[14] if len(row) > 14 else None
            )

        # Vérifier si le worker tourne (via présence d'un job running)
        worker_running = job is not None

        return CurrentJobResponse(
            worker_running=worker_running,
            job=job
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur current job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.get("/jobs", response_model=IndexerJobsList)
async def list_indexer_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filtrer par statut")
):
    """Liste les jobs d'indexation"""
    try:
        db = get_db_adapter()

        # Construire la requête avec filtres
        where_conditions = []
        params = []

        if status:
            where_conditions.append("status = %s")
            params.append(status)

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # Requête principale
        query = f"""
            SELECT id, path, config_id, config_name, status, created_at,
                   started_at, completed_at, files_found, files_indexed,
                   bytes_total, dirs_found, phase, phase_b_done, error_message
            FROM indexer_jobs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])
        results = db.execute_query(query, params)

        jobs = []
        for row in results:
            jobs.append(IndexerJobResponse(
                id=str(row[0]),
                path=row[1],
                config_id=str(row[2]),
                config_name=row[3],
                status=row[4],
                created_at=row[5],
                started_at=row[6],
                completed_at=row[7],
                files_found=row[8] or 0,
                files_indexed=row[9] or 0,
                bytes_total=row[10] or 0,
                dirs_found=row[11] or 0,
                phase=row[12] or '',
                phase_b_done=row[13] if len(row) > 13 else False,
                error_message=row[14] if len(row) > 14 else None
            ))

        # Compter le total
        count_query = f"SELECT COUNT(*) FROM indexer_jobs {where_clause}"
        count_params = params[:-2] if where_conditions else []
        count_results = db.execute_query(count_query, count_params)
        total = count_results[0][0] if count_results else 0

        return IndexerJobsList(jobs=jobs, total=total)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/jobs", response_model=IndexerJobResponse)
async def create_indexer_job(payload: IndexerJobCreate):
    """Crée un nouveau job d'indexation"""
    try:
        db = get_db_adapter()

        # Vérifier que la config existe
        config = db.get_crawl_config_by_id(payload.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration introuvable")

        # Créer le job
        job_id = str(uuid.uuid4())
        query = """
            INSERT INTO indexer_jobs (id, path, config_id, config_name, status, created_at)
            VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
            RETURNING id, path, config_id, config_name, status, created_at,
                      started_at, completed_at, files_found, files_indexed,
                      bytes_total, dirs_found, phase, phase_b_done, error_message
        """

        results = db.execute_query(query, [
            job_id,
            config.get('start_path', ''),
            payload.config_id,
            config.get('name', 'Unnamed')
        ], commit=True)

        if not results:
            raise HTTPException(status_code=500, detail="Échec de la création du job")

        row = results[0]
        logger.info(f"Job créé: {job_id} pour config {payload.config_id}")

        return IndexerJobResponse(
            id=str(row[0]),
            path=row[1],
            config_id=str(row[2]),
            config_name=row[3],
            status=row[4],
            created_at=row[5],
            started_at=row[6],
            completed_at=row[7],
            files_found=row[8] or 0,
            files_indexed=row[9] or 0,
            bytes_total=row[10] or 0,
            dirs_found=row[11] if len(row) > 11 else 0,
            phase=row[12] if len(row) > 12 else '',
            phase_b_done=row[13] if len(row) > 13 else False,
            error_message=row[14] if len(row) > 14 else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/start", response_model=WorkerActionResponse)
async def start_worker():
    """Démarre le worker d'indexation (mode API - le worker doit être lancé via Docker)"""
    try:
        # Le worker tourne en tant que service séparé
        # On vérifie juste qu'il y a des jobs pending
        db = get_db_adapter()

        query = "SELECT COUNT(*) FROM indexer_jobs WHERE status = 'pending'"
        results = db.execute_query(query)
        pending_count = results[0][0] if results else 0

        return WorkerActionResponse(
            success=True,
            message=f"Worker démarré (service Docker). {pending_count} jobs en attente.",
            worker_running=True
        )

    except Exception as e:
        logger.error(f"Erreur démarrage: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/stop", response_model=WorkerActionResponse)
async def stop_worker():
    """Arrête le worker d'indexation (mode API)"""
    try:
        # Le worker s'arrête via Docker
        # On vérifie s'il y a un job running
        db = get_db_adapter()

        query = "SELECT COUNT(*) FROM indexer_jobs WHERE status = 'running'"
        results = db.execute_query(query)
        running_count = results[0][0] if results else 0

        return WorkerActionResponse(
            success=True,
            message=f"Arrêt demandé. {running_count} jobs en cours seront interrompus.",
            worker_running=running_count > 0
        )

    except Exception as e:
        logger.error(f"Erreur arrêt: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.get("/jobs/{job_id}", response_model=IndexerJobResponse)
async def get_indexer_job(job_id: str):
    """Récupère un job d'indexation par son ID"""
    try:
        db = get_db_adapter()

        query = """
            SELECT id, path, config_id, config_name, status, created_at,
                   started_at, completed_at, files_found, files_indexed,
                   bytes_total, dirs_found, phase, phase_b_done, error_message
            FROM indexer_jobs
            WHERE id = %s
        """

        results = db.execute_query(query, [job_id])

        if not results:
            raise HTTPException(status_code=404, detail="Job introuvable")

        row = results[0]
        return IndexerJobResponse(
            id=str(row[0]),
            path=row[1],
            config_id=str(row[2]),
            config_name=row[3],
            status=row[4],
            created_at=row[5],
            started_at=row[6],
            completed_at=row[7],
            files_found=row[8] or 0,
            files_indexed=row[9] or 0,
            bytes_total=row[10] or 0,
            dirs_found=row[11] or 0,
            phase=row[12] or '',
            phase_b_done=row[13] if len(row) > 13 else False,
            error_message=row[14] if len(row) > 14 else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Annule un job en attente"""
    try:
        db = get_db_adapter()

        query = """
            UPDATE indexer_jobs
            SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status = 'pending'
            RETURNING id
        """

        results = db.execute_query(query, [job_id], commit=True)

        if not results:
            raise HTTPException(status_code=404, detail="Job introuvable ou non annulable")

        logger.info(f"Job annulé: {job_id}")
        return {"success": True, "message": "Job annulé"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur annulation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """Arrête un job d'indexation (pending ou running)"""
    try:
        db = get_db_adapter()

        # Vérifier le statut actuel du job
        check_query = "SELECT status FROM indexer_jobs WHERE id = %s"
        results = db.execute_query(check_query, [job_id])
        if not results:
            raise HTTPException(status_code=404, detail="Job introuvable")

        current_status = results[0][0]

        if current_status == "pending":
            # Job en attente : annuler directement
            db.execute_query(
                """
                UPDATE indexer_jobs
                SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                [job_id], fetch=False
            )
            logger.info(f"Job pending annulé: {job_id}")
            return {"success": True, "message": "Job annulé"}

        elif current_status == "running":
            # Job en cours : signaler l'arrêt au worker
            from backend.src.workers.indexer_worker import get_worker
            worker = get_worker()
            worker.stop_current_job()

            # Marquer comme cancelled dans la DB (le worker finira la mise à jour)
            db.execute_query(
                """
                UPDATE indexer_jobs
                SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP,
                    error_message = 'Arrêt demandé'
                WHERE id = %s AND status = 'running'
                """,
                [job_id], fetch=False
            )
            logger.info(f"Job running annulé: {job_id}")
            return {"success": True, "message": "Arrêt du job en cours..."}

        else:
            raise HTTPException(
                status_code=409,
                detail=f"Impossible d'arrêter un job en statut '{current_status}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur arrêt job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.post("/jobs/purge")
async def purge_jobs():
    """Supprime les jobs terminés, annulés ou échoués"""
    try:
        db = get_db_adapter()
        result = db.execute_query(
            "DELETE FROM indexer_jobs WHERE status IN ('completed', 'cancelled', 'failed') RETURNING id",
            commit=True
        )
        count = len(result) if result else 0
        logger.info(f"{count} jobs purgés")
        return {"success": True, "purged": count}
    except Exception as e:
        logger.error(f"Erreur purge: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Remet un job en attente pour reprise (running orphelin)"""
    try:
        db = get_db_adapter()
        result = db.execute_query(
            "UPDATE indexer_jobs SET status = 'pending' WHERE id = %s AND status = 'running' RETURNING id",
            [job_id], commit=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Job introuvable ou déjà traité")
        logger.info(f"Job remis en attente: {job_id}")
        return {"success": True, "message": "Job remis en attente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur reprise job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/performance", response_model=IndexerPerformance)
async def get_indexer_performance():
    """Récupère les métriques de performance temps réel de l'indexeur"""
    try:
        # Importer le worker pour accéder aux métriques
        from backend.src.workers.indexer_worker import get_worker

        worker = get_worker()
        metrics = worker.get_performance_metrics()

        return IndexerPerformance(
            files_processed=metrics['files_processed'],
            errors_count=metrics['errors_count'],
            files_per_second=metrics['files_per_second'],
            error_rate=metrics['error_rate'],
            uptime_seconds=metrics['uptime_seconds'],
            last_reset=metrics['last_reset']
        )

    except Exception as e:
        logger.error(f"Erreur performance: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.get("/health", response_model=IndexerHealth)
async def get_indexer_health():
    """Récupère l'état de santé de l'indexeur"""
    try:
        # Importer le worker pour accéder à l'état de santé
        from backend.src.workers.indexer_worker import get_worker

        worker = get_worker()
        health = worker.get_health_status()

        return IndexerHealth(
            status=health['status'],
            worker_running=health['worker_running'],
            database_connected=health['database_connected'],
            current_job=health['current_job'],
            pending_jobs=health['pending_jobs'],
            timestamp=health['timestamp'],
            error=health.get('error')
        )

    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.get("/retries", response_model=IndexerRetriesList)
async def list_indexer_retries():
    """Liste les fichiers en attente de réessai"""
    try:
        db = get_db_adapter()

        query = """
            SELECT
                r.id, r.file_id, r.file_path, r.job_id, r.config_id,
                r.attempt_count, r.max_attempts, r.next_retry_at,
                r.last_error, r.created_at
            FROM indexer_retries r
            ORDER BY r.next_retry_at ASC
        """

        results = db.execute_query(query)

        retries = []
        for row in results:
            retries.append(IndexerRetry(
                file_id=str(row[1]),
                file_path=row[2],
                job_id=str(row[3]),
                config_id=str(row[4]),
                attempt_count=row[5] or 0,
                max_attempts=row[6] or 5,
                next_retry_at=row[7].isoformat() if row[7] else None,
                last_error=row[8],
                created_at=row[9].isoformat() if row[9] else None
            ))

        # Compter le total
        count_results = db.execute_query("SELECT COUNT(*) FROM indexer_retries")
        total = count_results[0][0] if count_results else 0

        return IndexerRetriesList(retries=retries, total=total)

    except Exception as e:
        logger.error(f"Erreur list retries: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

LOG_FILES = {
    "worker": "/var/log/openindex/indexer-worker.log",
    "api": "/var/log/openindex/indexer-api.log",
    "scheduler": "/var/log/openindex/indexer-scheduler.log"
}

@router.get("/logs", response_model=LogsResponse)
async def get_logs(service: str = Query("worker", description="Service: worker, api, scheduler"), lines: int = Query(200, ge=10, le=2000)):
    """Récupère les dernières lignes du fichier de log d'un service"""
    log_path = LOG_FILES.get(service)
    if not log_path:
        raise HTTPException(status_code=400, detail=f"Service inconnu: {service}. Choisir: worker, api, scheduler")

    try:
        if not os.path.exists(log_path):
            return LogsResponse(service=service, lines=[])

        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        # Prendre les N dernières lignes non vides
        last_lines = [l.rstrip('\n') for l in all_lines if l.strip()]
        last_lines = last_lines[-lines:]

        entries = []
        for line in last_lines:
            # Format: [2026-07-22 17:05:00] LEVEL - message
            if line.startswith('[') and '] ' in line:
                bracket_end = line.index('] ')
                timestamp = line[1:bracket_end]
                message = line[bracket_end + 2:]
            else:
                timestamp = ''
                message = line
            entries.append(LogEntry(timestamp=timestamp, message=message))

        return LogsResponse(service=service, lines=entries)

    except Exception as e:
        logger.error(f"Erreur lecture logs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")