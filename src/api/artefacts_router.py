"""
Router pour la gestion des artefacts (T-ART-01)
Endpoints pour filtrer et gérer les fichiers problématiques
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

# Configuration du logging
logger = logging.getLogger("openindex.api.artefacts")

router = APIRouter(
    prefix="/api/artefacts",
    tags=["artefacts"]
)


# Modèles Pydantic
class ArtefactFile(BaseModel):
    id: str
    path: str
    name: str
    size: Optional[int] = None
    checksum: Optional[str] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    days_since_modified: Optional[int] = None
    days_since_access: Optional[int] = None
    size_gb: Optional[float] = None
    duplicate_count: Optional[int] = None


class ArtefactCategoryStats(BaseModel):
    category: str
    count: int
    total_size: int


class ArtefactCategoryResponse(BaseModel):
    category: str
    files: List[ArtefactFile]
    stats: ArtefactCategoryStats


# Fonction utilitaire pour obtenir l'adaptateur de base de données
def get_db_adapter():
    """Retourne l'adaptateur de base de données"""
    try:
        from src.postgres_adapter import PostgreSQLAdapter
        from src.config import POSTGRES_CONFIG
        return PostgreSQLAdapter(POSTGRES_CONFIG)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'adaptateur DB: {e}")
        raise HTTPException(status_code=500, detail="Erreur de configuration de la base de données")


@router.get("/duplicates", response_model=ArtefactCategoryResponse)
async def get_duplicate_files(
    limit: int = Query(100, description="Nombre maximum de fichiers à retourner"),
    offset: int = Query(0, description="Offset pour la pagination")
):
    """
    Liste les fichiers en doublon
    
    Returns:
        - Liste des fichiers avec leur checksum et nombre de doublons
        - Statistiques (nombre total, taille totale)
    """
    try:
        db = get_db_adapter()
        
        # Récupérer les fichiers en doublon avec pagination
        query = """
            SELECT 
                id, path, name, size, checksum, last_modified, last_accessed, duplicate_count
            FROM duplicate_files
            ORDER BY duplicate_count DESC, size DESC
            LIMIT %s OFFSET %s
        """
        files = db.execute_query(query, (limit, offset))
        
        # Calculer les statistiques
        stats_query = """
            SELECT 
                COUNT(*) as count,
                SUM(size) as total_size
            FROM duplicate_files
        """
        stats = db.execute_query(stats_query)[0]
        
        # Formater les résultats
        formatted_files = [
            ArtefactFile(
                id=file[0],
                path=file[1],
                name=file[2],
                size=file[3],
                checksum=file[4],
                last_modified=file[5],
                last_accessed=file[6],
                duplicate_count=file[7]
            )
            for file in files
        ]
        
        return ArtefactCategoryResponse(
            category="duplicates",
            files=formatted_files,
            stats=ArtefactCategoryStats(
                category="duplicates",
                count=stats[0],
                total_size=stats[1] or 0
            )
        )
        
    except Exception as e:
        logger.error(f"Erreur get_duplicate_files: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/large", response_model=ArtefactCategoryResponse)
async def get_large_files(
    min_size_gb: float = Query(1.0, description="Taille minimale en Go"),
    limit: int = Query(100, description="Nombre maximum de fichiers à retourner"),
    offset: int = Query(0, description="Offset pour la pagination")
):
    """
    Liste les gros fichiers
    
    Args:
        min_size_gb: Taille minimale en Go (défaut: 1.0)
    
    Returns:
        - Liste des fichiers avec leur taille en Go
        - Statistiques (nombre total, taille totale)
    """
    try:
        db = get_db_adapter()
        
        # Convertir la taille en octets
        min_size_bytes = int(min_size_gb * 1073741824)
        
        # Récupérer les gros fichiers avec pagination
        query = """
            SELECT 
                id, path, name, size, checksum, last_modified, last_accessed, size / 1073741824 as size_gb
            FROM large_files
            WHERE size > %s
            ORDER BY size DESC
            LIMIT %s OFFSET %s
        """
        files = db.execute_query(query, (min_size_bytes, limit, offset))
        
        # Calculer les statistiques
        stats_query = """
            SELECT 
                COUNT(*) as count,
                SUM(size) as total_size
            FROM large_files
            WHERE size > %s
        """
        stats = db.execute_query(stats_query, (min_size_bytes,))[0]
        
        # Formater les résultats
        formatted_files = [
            ArtefactFile(
                id=file[0],
                path=file[1],
                name=file[2],
                size=file[3],
                checksum=file[4],
                last_modified=file[5],
                last_accessed=file[6],
                size_gb=file[7]
            )
            for file in files
        ]
        
        return ArtefactCategoryResponse(
            category="large",
            files=formatted_files,
            stats=ArtefactCategoryStats(
                category="large",
                count=stats[0],
                total_size=stats[1] or 0
            )
        )
        
    except Exception as e:
        logger.error(f"Erreur get_large_files: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/old", response_model=ArtefactCategoryResponse)
async def get_old_files(
    min_days: int = Query(730, description="Nombre minimum de jours depuis la dernière modification"),
    limit: int = Query(100, description="Nombre maximum de fichiers à retourner"),
    offset: int = Query(0, description="Offset pour la pagination")
):
    """
    Liste les fichiers anciens
    
    Args:
        min_days: Nombre minimum de jours depuis la dernière modification (défaut: 730 = 2 ans)
    
    Returns:
        - Liste des fichiers avec leur nombre de jours depuis la modification
        - Statistiques (nombre total, taille totale)
    """
    try:
        db = get_db_adapter()
        
        # Récupérer les fichiers anciens avec pagination
        query = """
            SELECT 
                id, path, name, size, checksum, last_modified, last_accessed, 
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_modified)) / 86400 as days_since_modified
            FROM old_files
            WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_modified)) / 86400 > %s
            ORDER BY last_modified ASC
            LIMIT %s OFFSET %s
        """
        files = db.execute_query(query, (min_days, limit, offset))
        
        # Calculer les statistiques
        stats_query = """
            SELECT 
                COUNT(*) as count,
                SUM(size) as total_size
            FROM old_files
            WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_modified)) / 86400 > %s
        """
        stats = db.execute_query(stats_query, (min_days,))[0]
        
        # Formater les résultats
        formatted_files = [
            ArtefactFile(
                id=file[0],
                path=file[1],
                name=file[2],
                size=file[3],
                checksum=file[4],
                last_modified=file[5],
                last_accessed=file[6],
                days_since_modified=file[7]
            )
            for file in files
        ]
        
        return ArtefactCategoryResponse(
            category="old",
            files=formatted_files,
            stats=ArtefactCategoryStats(
                category="old",
                count=stats[0],
                total_size=stats[1] or 0
            )
        )
        
    except Exception as e:
        logger.error(f"Erreur get_old_files: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/unused", response_model=ArtefactCategoryResponse)
async def get_unused_files(
    min_days: int = Query(365, description="Nombre minimum de jours depuis le dernier accès"),
    limit: int = Query(100, description="Nombre maximum de fichiers à retourner"),
    offset: int = Query(0, description="Offset pour la pagination")
):
    """
    Liste les fichiers inutilisés
    
    Args:
        min_days: Nombre minimum de jours depuis le dernier accès (défaut: 365 = 1 an)
    
    Returns:
        - Liste des fichiers avec leur nombre de jours depuis le dernier accès
        - Statistiques (nombre total, taille totale)
    """
    try:
        db = get_db_adapter()
        
        # Récupérer les fichiers inutilisés avec pagination
        query = """
            SELECT 
                id, path, name, size, checksum, last_modified, last_accessed, 
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed)) / 86400 as days_since_access
            FROM unused_files
            WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed)) / 86400 > %s
            ORDER BY last_accessed ASC
            LIMIT %s OFFSET %s
        """
        files = db.execute_query(query, (min_days, limit, offset))
        
        # Calculer les statistiques
        stats_query = """
            SELECT 
                COUNT(*) as count,
                SUM(size) as total_size
            FROM unused_files
            WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed)) / 86400 > %s
        """
        stats = db.execute_query(stats_query, (min_days,))[0]
        
        # Formater les résultats
        formatted_files = [
            ArtefactFile(
                id=file[0],
                path=file[1],
                name=file[2],
                size=file[3],
                checksum=file[4],
                last_modified=file[5],
                last_accessed=file[6],
                days_since_access=file[7]
            )
            for file in files
        ]
        
        return ArtefactCategoryResponse(
            category="unused",
            files=formatted_files,
            stats=ArtefactCategoryStats(
                category="unused",
                count=stats[0],
                total_size=stats[1] or 0
            )
        )
        
    except Exception as e:
        logger.error(f"Erreur get_unused_files: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/stats", response_model=List[ArtefactCategoryStats])
async def get_artefacts_stats():
    """
    Récupère les statistiques pour toutes les catégories d'artefacts
    
    Returns:
        Liste des statistiques pour chaque catégorie (doublons, gros fichiers, anciens, inutilisés)
    """
    try:
        db = get_db_adapter()
        
        # Statistiques pour chaque catégorie
        categories = [
            ("duplicates", "SELECT COUNT(*) as count, SUM(size) as total_size FROM duplicate_files"),
            ("large", "SELECT COUNT(*) as count, SUM(size) as total_size FROM large_files"),
            ("old", "SELECT COUNT(*) as count, SUM(size) as total_size FROM old_files"),
            ("unused", "SELECT COUNT(*) as count, SUM(size) as total_size FROM unused_files")
        ]
        
        results = []
        for category, query in categories:
            stats = db.execute_query(query)[0]
            results.append(ArtefactCategoryStats(
                category=category,
                count=stats[0],
                total_size=stats[1] or 0
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur get_artefacts_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")
