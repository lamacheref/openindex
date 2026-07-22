"""
Router API pour la gestion des schedules d'indexation (T-INDEX-01)
Endpoints CRUD pour les tâches planifiées d'indexation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger("openindex.api.indexer_schedules")

router = APIRouter(
    prefix="/api/indexer/schedules",
    tags=["indexer-schedules"]
)


# Modèles Pydantic
class IndexerScheduleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cron_expression: str
    timezone: str = "Europe/Paris"
    is_active: bool = True
    config_id: Optional[str] = None
    config_name: Optional[str] = None
    priority: int = 5
    created_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0


class IndexerScheduleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cron_expression: str
    timezone: str = "Europe/Paris"
    is_active: bool = True
    config_id: Optional[str] = None
    priority: int = 5


class IndexerScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    config_id: Optional[str] = None
    priority: Optional[int] = None


class IndexerSchedulesList(BaseModel):
    schedules: List[IndexerScheduleResponse]
    total: int


class IndexerSpaceStats(BaseModel):
    config_id: str
    config_name: str
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_files_indexed: int = 0
    total_bytes_indexed: int = 0


class IndexerMultiSpaceStats(BaseModel):
    spaces: List[IndexerSpaceStats]
    total_spaces: int


def get_db_adapter():
    """Retourne l'adaptateur de base de données"""
    try:
        from backend.src.database.postgres_adapter import PostgreSQLAdapter
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


# ============================================================
# Endpoints CRUD pour les schedules
# ============================================================

@router.get("", response_model=IndexerSchedulesList)
async def list_schedules(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(False, description="Filtrer seulement les schedules actifs")
):
    """Liste les schedules d'indexation"""
    try:
        db = get_db_adapter()
        
        where_clause = ""
        if active_only:
            where_clause = "WHERE s.is_active = true"
        
        query = f"""
            SELECT s.id::text, s.name, s.description, s.cron_expression, s.timezone,
                   s.is_active, s.config_id::text, s.priority,
                   s.created_at, s.last_run_at, s.next_run_at, s.run_count,
                   c.name as config_name
            FROM indexer_schedules s
            LEFT JOIN crawl_configs c ON c.id = s.config_id
            {where_clause}
            ORDER BY s.priority ASC, s.name ASC
            LIMIT %s OFFSET %s
        """
        results = db.execute_query(query, [limit, offset])
        
        count_query = f"SELECT COUNT(*) FROM indexer_schedules s {where_clause}"
        count_results = db.execute_query(count_query)
        total = count_results[0][0] if count_results else 0
        
        schedules = []
        for row in results:
            schedules.append(IndexerScheduleResponse(
                id=row[0], name=row[1], description=row[2],
                cron_expression=row[3], timezone=row[4],
                is_active=row[5], config_id=row[6], priority=row[7],
                created_at=row[8], last_run_at=row[9], next_run_at=row[10],
                run_count=row[11], config_name=row[12]
            ))
        
        return IndexerSchedulesList(schedules=schedules, total=total)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/{schedule_id}", response_model=IndexerScheduleResponse)
async def get_schedule(schedule_id: str):
    """Récupère un schedule par son ID"""
    try:
        db = get_db_adapter()
        
        results = db.execute_query(
            """
            SELECT s.id::text, s.name, s.description, s.cron_expression, s.timezone,
                   s.is_active, s.config_id::text, s.priority,
                   s.created_at, s.last_run_at, s.next_run_at, s.run_count,
                   c.name as config_name
            FROM indexer_schedules s
            LEFT JOIN crawl_configs c ON c.id = s.config_id
            WHERE s.id::text = %s
            """,
            [schedule_id]
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        row = results[0]
        return IndexerScheduleResponse(
            id=row[0], name=row[1], description=row[2],
            cron_expression=row[3], timezone=row[4],
            is_active=row[5], config_id=row[6], priority=row[7],
            created_at=row[8], last_run_at=row[9], next_run_at=row[10],
            run_count=row[11], config_name=row[12]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.post("", response_model=IndexerScheduleResponse, status_code=201)
async def create_schedule(payload: IndexerScheduleCreate):
    """Crée un nouveau schedule d'indexation"""
    try:
        db = get_db_adapter()
        
        schedule_id = str(uuid.uuid4())
        results = db.execute_query(
            """
            INSERT INTO indexer_schedules (id, name, description, cron_expression, timezone,
                                           is_active, config_id, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s::uuid, %s)
            RETURNING id::text, name, description, cron_expression, timezone,
                      is_active, config_id::text, priority,
                      created_at, last_run_at, next_run_at, run_count
            """,
            [
                schedule_id, payload.name, payload.description,
                payload.cron_expression, payload.timezone,
                payload.is_active, payload.config_id, payload.priority
            ]
        )
        
        if not results:
            raise HTTPException(status_code=500, detail="Échec de la création")
        
        row = results[0]
        logger.info(f"Schedule créé: {schedule_id} - {payload.name}")
        
        # Récupérer le nom de la config si présente
        config_name = None
        if payload.config_id:
            config = db.get_crawl_config_by_id(payload.config_id)
            config_name = config.get('name') if config else None
        
        return IndexerScheduleResponse(
            id=row[0], name=row[1], description=row[2],
            cron_expression=row[3], timezone=row[4],
            is_active=row[5], config_id=row[6], priority=row[7],
            created_at=row[8], last_run_at=row[9], next_run_at=row[10],
            run_count=row[11], config_name=config_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.put("/{schedule_id}", response_model=IndexerScheduleResponse)
async def update_schedule(schedule_id: str, payload: IndexerScheduleUpdate):
    """Met à jour un schedule existant"""
    try:
        db = get_db_adapter()
        
        # Vérifier que le schedule existe
        existing = db.execute_query(
            "SELECT id::text FROM indexer_schedules WHERE id::text = %s",
            [schedule_id]
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        # Construire la requête de mise à jour
        updates = []
        params = []
        
        if payload.name is not None:
            updates.append("name = %s")
            params.append(payload.name)
        if payload.description is not None:
            updates.append("description = %s")
            params.append(payload.description)
        if payload.cron_expression is not None:
            updates.append("cron_expression = %s")
            params.append(payload.cron_expression)
        if payload.timezone is not None:
            updates.append("timezone = %s")
            params.append(payload.timezone)
        if payload.is_active is not None:
            updates.append("is_active = %s")
            params.append(payload.is_active)
        if payload.config_id is not None:
            updates.append("config_id = %s::uuid")
            params.append(payload.config_id)
        if payload.priority is not None:
            updates.append("priority = %s")
            params.append(payload.priority)
        
        if not updates:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(schedule_id)
        
        query = f"""
            UPDATE indexer_schedules
            SET {', '.join(updates)}
            WHERE id::text = %s
        """
        db.execute_query(query, params, fetch=False)
        
        # Retourner le schedule mis à jour
        return await get_schedule(schedule_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Supprime un schedule"""
    try:
        db = get_db_adapter()
        
        results = db.execute_query(
            "DELETE FROM indexer_schedules WHERE id::text = %s RETURNING id::text",
            [schedule_id]
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        logger.info(f"Schedule supprimé: {schedule_id}")
        return {"success": True, "message": "Schedule supprimé"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    """Active/désactive un schedule"""
    try:
        db = get_db_adapter()
        
        results = db.execute_query(
            """
            UPDATE indexer_schedules
            SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
            WHERE id::text = %s
            RETURNING id::text, name, is_active
            """,
            [schedule_id]
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        row = results[0]
        status = "activé" if row[2] else "désactivé"
        logger.info(f"Schedule {row[1]} {status}")
        
        return {
            "success": True,
            "id": row[0],
            "name": row[1],
            "is_active": row[2],
            "message": f"Schedule {status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur toggle schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


# ============================================================
# Endpoints pour les métriques multi-espaces
# ============================================================

@router.get("/spaces/stats", response_model=IndexerMultiSpaceStats)
async def get_spaces_stats():
    """Statistiques d'indexation par espace (crawl_config)"""
    try:
        db = get_db_adapter()
        
        results = db.execute_query(
            """
            SELECT 
                c.id::text as config_id,
                c.name as config_name,
                COUNT(j.id) as total_jobs,
                COUNT(*) FILTER (WHERE j.status = 'pending') as pending_jobs,
                COUNT(*) FILTER (WHERE j.status = 'running') as running_jobs,
                COUNT(*) FILTER (WHERE j.status = 'completed') as completed_jobs,
                COUNT(*) FILTER (WHERE j.status = 'failed') as failed_jobs,
                COALESCE(SUM(j.files_indexed) FILTER (WHERE j.status = 'completed'), 0) as total_files_indexed,
                COALESCE(SUM(j.bytes_total) FILTER (WHERE j.status = 'completed'), 0) as total_bytes_indexed
            FROM crawl_configs c
            LEFT JOIN indexer_jobs j ON j.config_id = c.id
            GROUP BY c.id, c.name
            ORDER BY c.name ASC
            """
        )
        
        spaces = []
        for row in results:
            spaces.append(IndexerSpaceStats(
                config_id=row[0], config_name=row[1],
                total_jobs=row[2] or 0, pending_jobs=row[3] or 0,
                running_jobs=row[4] or 0, completed_jobs=row[5] or 0,
                failed_jobs=row[6] or 0,
                total_files_indexed=row[7] or 0,
                total_bytes_indexed=row[8] or 0
            ))
        
        return IndexerMultiSpaceStats(spaces=spaces, total_spaces=len(spaces))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur spaces stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")