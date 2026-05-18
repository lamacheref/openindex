"""
Router pour les détails des doublons (T-ART-02)
Endpoints pour afficher et gérer les occurrences de doublons
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

# Configuration du logging
logger = logging.getLogger("openindex.api.duplicate_details")

router = APIRouter(
    prefix="/api/duplicates",
    tags=["duplicates"]
)


# Modèles Pydantic
class DuplicateOccurrence(BaseModel):
    id: str
    path: str
    name: str
    size: Optional[int] = None
    checksum: Optional[str] = None
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    crawl_config_id: Optional[str] = None
    crawl_config_name: Optional[str] = None


class DuplicateFileDetails(BaseModel):
    checksum: str
    name: str
    size: Optional[int] = None
    total_occurrences: int
    occurrences: List[DuplicateOccurrence]


# Fonction utilitaire pour obtenir l'adaptateur de base de données
def get_db_adapter():
    """Retourne l'adaptateur de base de données"""
    try:
        from backend.src.postgres_adapter import PostgreSQLAdapter
        import os
        
        # Configuration PostgreSQL depuis les variables d'environnement
        config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        return PostgreSQLAdapter(config)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'adaptateur DB: {e}")
        raise HTTPException(status_code=500, detail="Erreur de configuration de la base de données")


@router.get("/{checksum}/details", response_model=DuplicateFileDetails)
async def get_duplicate_file_details(
    checksum: str,
    limit: int = Query(50, description="Nombre maximum d'occurrences à retourner"),
    offset: int = Query(0, description="Offset pour la pagination")
):
    """
    Récupère les détails d'un fichier en doublon par son checksum
    
    Args:
        checksum: Checksum du fichier à analyser
        limit: Nombre maximum d'occurrences à retourner
        offset: Offset pour la pagination
    
    Returns:
        - Détails du fichier (nom, taille, checksum)
        - Liste de toutes les occurrences avec leurs métadonnées
        - Nombre total d'occurrences
    """
    try:
        db = get_db_adapter()
        logger.info(f"Récupération des détails pour checksum: {checksum}")
        
        # Récupérer les détails du fichier principal (première occurrence)
        main_file_query = """
            SELECT 
                f.id, f.path, f.name, f.size, f.checksum, f.last_modified, f.last_accessed, f.crawl_config_id
            FROM files f
            WHERE f.checksum = %s
            ORDER BY f.last_modified DESC
            LIMIT 1
        """
        main_file = db.execute_query(main_file_query, (checksum,))
        logger.info(f"Résultat main_file: {main_file}")
        
        if not main_file:
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
        
        main_file_data = main_file[0]
        
        # Récupérer toutes les occurrences du fichier
        occurrences_query = """
            SELECT 
                f.id, f.path, f.name, f.size, f.checksum, f.last_modified, f.last_accessed, f.crawl_config_id, 
                cc.name as crawl_config_name
            FROM files f
            LEFT JOIN crawl_configs cc ON f.crawl_config_id = cc.id
            WHERE f.checksum = %s
            ORDER BY f.path
            LIMIT %s OFFSET %s
        """
        occurrences = db.execute_query(occurrences_query, (checksum, limit, offset))
        
        # Récupérer le nom du crawl config pour le fichier principal
        crawl_config_name = None
        # if main_file_data[7]:  # crawl_config_id
        #     config_query = """
        #         SELECT name FROM crawl_configs WHERE id = %s
        #     """
        #     config_result = db.execute_query(config_query, (main_file_data[7],))
        #     crawl_config_name = config_result[0][0] if config_result else None
        
        # Compter le nombre total d'occurrences
        count_query = """
            SELECT COUNT(*)
            FROM files f
            WHERE f.checksum = %s
        """
        total_count = db.execute_query(count_query, (checksum,))[0][0]
        
        # Formater les résultats
        logger.info(f"Nombre d'occurrences: {len(occurrences)}")
        if occurrences:
            logger.info(f"Première occurrence: {occurrences[0]}")
        
        formatted_occurrences = []
        for occ in occurrences:
            try:
                formatted_occurrences.append(DuplicateOccurrence(
                    id=occ[0],
                    path=occ[1],
                    name=occ[2],
                    size=occ[3],
                    checksum=occ[4],
                    last_modified=occ[5],
                    last_accessed=occ[6],
                    crawl_config_id=occ[7],
                    crawl_config_name=occ[8] if len(occ) > 8 else None
                ))
            except IndexError as e:
                logger.error(f"Erreur de formatage de l'occurrence {occ}: {e}")
                raise
        
        return DuplicateFileDetails(
            checksum=main_file_data[4],
            name=main_file_data[2],
            size=main_file_data[3],
            total_occurrences=total_count,
            occurrences=formatted_occurrences
        )
        
    except HTTPException:
        # Laisser passer les HTTPException (404, 400, etc.)
        raise
    except Exception as e:
        logger.error(f"Erreur get_duplicate_file_details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/{checksum}/keep")
async def keep_duplicate_occurrence(
    checksum: str,
    occurrence_id: str
):
    """
    Marque une occurrence comme à conserver (les autres seront supprimées)
    
    Args:
        checksum: Checksum du fichier
        occurrence_id: ID de l'occurrence à conserver
    
    Returns:
        Message de confirmation
    """
    try:
        db = get_db_adapter()
        
        # Vérifier que l'occurrence existe et appartient au checksum
        verify_query = """
            SELECT 1 FROM files 
            WHERE id = %s AND checksum = %s
        """
        verify_result = db.execute_query(verify_query, (occurrence_id, checksum))
        
        if not verify_result:
            raise HTTPException(status_code=404, detail="Occurrence non trouvée")
        
        # Marquer cette occurrence comme principale (à conserver)
        # Note: Dans une implémentation complète, cela pourrait impliquer
        # de mettre à jour un champ `is_primary` ou similaire
        
        return {
            "success": True,
            "message": f"Occurrence {occurrence_id} marquée comme à conserver",
            "checksum": checksum
        }
        
    except HTTPException:
        # Laisser passer les HTTPException (404, 400, etc.)
        raise
    except Exception as e:
        logger.error(f"Erreur keep_duplicate_occurrence: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.delete("/{checksum}/occurrences")
async def delete_duplicate_occurrences(
    checksum: str,
    keep_occurrence_id: str
):
    """
    Supprime toutes les occurrences d'un doublon sauf une
    
    Args:
        checksum: Checksum du fichier
        keep_occurrence_id: ID de l'occurrence à conserver
    
    Returns:
        Nombre d'occurrences supprimées
    """
    try:
        db = get_db_adapter()
        
        # Vérifier que l'occurrence à conserver existe
        verify_query = """
            SELECT 1 FROM files 
            WHERE id = %s AND checksum = %s
        """
        verify_result = db.execute_query(verify_query, (keep_occurrence_id, checksum))
        
        if not verify_result:
            raise HTTPException(status_code=404, detail="Occurrence à conserver non trouvée")
        
        # Supprimer toutes les autres occurrences
        delete_query = """
            DELETE FROM files 
            WHERE checksum = %s AND id != %s
            RETURNING id
        """
        deleted = db.execute_query(delete_query, (checksum, keep_occurrence_id))
        
        return {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_ids": [d[0] for d in deleted],
            "kept_occurrence_id": keep_occurrence_id
        }
        
    except HTTPException:
        # Laisser passer les HTTPException (404, 400, etc.)
        raise
    except Exception as e:
        logger.error(f"Erreur delete_duplicate_occurrences: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")
