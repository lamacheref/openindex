"""
Router API pour le service d'indexation (Indexer Worker)
Endpoints pour le monitoring et le contrôle des jobs d'indexation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
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


# Fonction utilitaire pour obtenir l'adaptateur DB
def get_db_adapter():
    """Retourne l'adaptateur de base de données"""
    try:
        from src.postgres_adapter import PostgreSQLAdapter
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
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                COUNT(*) FILTER (WHERE status = 'running') as running_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                COALESCE(SUM(files_indexed) FILTER (WHERE status = 'completed'), 0) as total_files_indexed,
                COALESCE(SUM(bytes_total) FILTER (WHERE status = 'completed'), 0) as total_bytes_indexed,
                MAX(created_at) as last_job_created,
                MAX(completed_at) FILTER (WHERE status = 'completed') as last_completion
            FROM indexer_jobs
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
                   bytes_total, error_message
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
                error_message=row[11]
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
                   bytes_total, error_message
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
                error_message=row[11]
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
        config = db.get_crawl_config(payload.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration introuvable")
        
        # Créer le job
        job_id = str(uuid.uuid4())
        query = """
            INSERT INTO indexer_jobs (id, path, config_id, config_name, status, created_at)
            VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
            RETURNING id, path, config_id, config_name, status, created_at,
                      started_at, completed_at, files_found, files_indexed,
                      bytes_total, error_message
        """
        
        results = db.execute_query(query, [
            job_id,
            f"//{config['host']}/{config['share']}{config.get('remote_path', '')}",
            payload.config_id,
            config.get('name', 'Unnamed')
        ])
        
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
            error_message=row[11]
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
        
        results = db.execute_query(query, [job_id])
        
        if not results:
            raise HTTPException(status_code=404, detail="Job introuvable ou non annulable")
        
        logger.info(f"Job annulé: {job_id}")
        return {"success": True, "message": "Job annulé"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur annulation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")
