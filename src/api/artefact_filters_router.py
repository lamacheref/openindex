"""
Router pour les filtres configurables (T-ART-03)
Endpoints pour gérer les préférences utilisateur des filtres d'artefacts
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

# Configuration du logging
logger = logging.getLogger("openindex.api.artefact_filters")

router = APIRouter(
    prefix="/api/artefact-filters",
    tags=["artefact-filters"]
)


# Modèles Pydantic
class ArtefactFilterPreferences(BaseModel):
    large_file_threshold_mb: int = 1024
    old_file_threshold_days: int = 730
    unused_file_threshold_days: int = 365


class ArtefactFilterUpdate(BaseModel):
    filter_name: str
    filter_value: str


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


@router.get("/preferences", response_model=ArtefactFilterPreferences)
async def get_artefact_filter_preferences():
    """
    Récupère les préférences courantes pour les filtres d'artefacts
    
    Returns:
        - Seuil pour les gros fichiers (en Mo)
        - Seuil pour les fichiers anciens (en jours)
        - Seuil pour les fichiers inutilisés (en jours)
    """
    try:
        db = get_db_adapter()
        
        # Récupérer les préférences depuis la vue
        query = """
            SELECT 
                large_file_threshold_mb,
                old_file_threshold_days,
                unused_file_threshold_days
            FROM current_artefact_filters
        """
        result = db.execute_query(query)
        
        if result and len(result) > 0:
            row = result[0]
            return ArtefactFilterPreferences(
                large_file_threshold_mb=row[0],
                old_file_threshold_days=row[1],
                unused_file_threshold_days=row[2]
            )
        else:
            # Retourner les valeurs par défaut si aucune préférence n'est définie
            return ArtefactFilterPreferences()
        
    except Exception as e:
        logger.error(f"Erreur get_artefact_filter_preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.put("/preferences", response_model=ArtefactFilterPreferences)
async def update_artefact_filter_preferences(preferences: ArtefactFilterPreferences):
    """
    Met à jour les préférences pour les filtres d'artefacts
    
    Args:
        preferences: Nouveaux seuils pour les filtres
    
    Returns:
        - Les préférences mises à jour
    """
    try:
        db = get_db_adapter()
        
        # Mettre à jour chaque préférence
        filters = [
            ('large_file_threshold_mb', str(preferences.large_file_threshold_mb)),
            ('old_file_threshold_days', str(preferences.old_file_threshold_days)),
            ('unused_file_threshold_days', str(preferences.unused_file_threshold_days))
        ]
        
        for filter_name, filter_value in filters:
            # Vérifier si la préférence existe
            check_query = """
                SELECT 1 FROM artefact_filters WHERE filter_name = %s
            """
            exists = db.execute_query(check_query, (filter_name,))
            
            if exists:
                # Mettre à jour la préférence existante
                update_query = """
                    UPDATE artefact_filters 
                    SET filter_value = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE filter_name = %s
                """
                db.execute_query(update_query, (filter_value, filter_name), fetch=False)
            else:
                # Insérer une nouvelle préférence
                insert_query = """
                    INSERT INTO artefact_filters (filter_name, filter_value)
                    VALUES (%s, %s)
                """
                db.execute_query(insert_query, (filter_name, filter_value), fetch=False)
        
        # Retourner les préférences mises à jour
        return await get_artefact_filter_preferences()
        
    except Exception as e:
        logger.error(f"Erreur update_artefact_filter_preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.post("/preferences/reset", response_model=ArtefactFilterPreferences)
async def reset_artefact_filter_preferences():
    """
    Réinitialise les préférences aux valeurs par défaut
    
    Returns:
        - Les préférences réinitialisées
    """
    try:
        db = get_db_adapter()
        
        # Supprimer toutes les préférences
        delete_query = """
            DELETE FROM artefact_filters
        """
        db.execute_query(delete_query, fetch=False)
        
        # Retourner les valeurs par défaut
        return ArtefactFilterPreferences()
        
    except Exception as e:
        logger.error(f"Erreur reset_artefact_filter_preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@router.get("/presets", response_model=dict)
async def get_artefact_filter_presets():
    """
    Récupère les préréglages disponibles pour les filtres
    
    Returns:
        - Dictionnaire des préréglages (Conservateur, Standard, Agressif)
    """
    return {
        "conservateur": {
            "large_file_threshold_mb": 2048,
            "old_file_threshold_days": 1095,
            "unused_file_threshold_days": 730
        },
        "standard": {
            "large_file_threshold_mb": 1024,
            "old_file_threshold_days": 730,
            "unused_file_threshold_days": 365
        },
        "agressif": {
            "large_file_threshold_mb": 512,
            "old_file_threshold_days": 365,
            "unused_file_threshold_days": 180
        }
    }
