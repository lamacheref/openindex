#!/usr/bin/env python3
"""
Adaptateur PostgreSQL pour OpenIndex
Remplace les fonctions SQLite par des équivalents PostgreSQL
"""

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

class PostgreSQLAdapter:
    """Adaptateur PostgreSQL pour OpenIndex"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'adaptateur PostgreSQL
        
        Args:
            config: Configuration de la base de données
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    @contextmanager
    def get_connection(self):
        """Context manager pour la connexion PostgreSQL"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5432),
                database=self.config.get('database', 'openindex'),
                user=self.config.get('user', 'openindex_user'),
                password=self.config.get('password', 'openindex_secure_password')
            )
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erreur de connexion PostgreSQL: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize_database(self):
        """Initialise la base de données (crée les tables si nécessaire)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'files'
                )
                """
            )
            files_table_exists = cursor.fetchone()[0]

            if files_table_exists:
                self.logger.info("Base de données PostgreSQL initialisée et accessible")
                return

            init_sql_path = Path(__file__).resolve().parents[1] / "database" / "init.sql"
            with init_sql_path.open("r", encoding="utf-8") as sql_file:
                cursor.execute(sql_file.read())
            conn.commit()
            self.logger.info(f"Schéma PostgreSQL initialisé depuis {init_sql_path}")

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Any]:
        """Exécute une requête SQL simple et retourne toutes les lignes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            rows = cursor.fetchall()
            conn.commit()
            return rows
    
    def save_files_batch(self, files_data: List[Dict[str, Any]]) -> int:
        """
        Sauvegarde un lot de fichiers dans PostgreSQL
        
        Args:
            files_data: Liste des métadonnées de fichiers
            
        Returns:
            Nombre de fichiers sauvegardés
        """
        if not files_data:
            return 0
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Préparer les valeurs pour l'insertion
                values = []
                for file_data in files_data:
                    values.append((
                        file_data.get('path'),
                        file_data.get('name'),
                        file_data.get('size'),
                        file_data.get('checksum'),
                        file_data.get('last_modified'),
                        file_data.get('is_directory', False),
                        file_data.get('is_duplicate', False),
                        file_data.get('duplicate_of'),
                        file_data.get('created_at', datetime.now()),
                        file_data.get('updated_at', datetime.now())
                    ))
                
                # Insertion par lot avec gestion des doublons
                execute_values(
                    cursor,
                    """
                    INSERT INTO files (
                        path, name, size, checksum, last_modified,
                        is_directory, is_duplicate, duplicate_of,
                        created_at, updated_at
                    ) VALUES %s
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        size = EXCLUDED.size,
                        checksum = EXCLUDED.checksum,
                        last_modified = EXCLUDED.last_modified,
                        is_directory = EXCLUDED.is_directory,
                        is_duplicate = EXCLUDED.is_duplicate,
                        duplicate_of = EXCLUDED.duplicate_of,
                        updated_at = EXCLUDED.updated_at
                    """,
                    values
                )
                
                conn.commit()
                self.logger.debug(f"Sauvegardé {len(files_data)} fichiers dans PostgreSQL")
                return len(files_data)
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Erreur lors de la sauvegarde du lot: {e}")
                raise
    
    def calculate_duplicates(self) -> int:
        """
        Calcule et marque les doublons
        
        Returns:
            Nombre de doublons trouvés
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Garantir la présence de la fonction même sur une base déjà existante
                self._ensure_calculate_duplicates_function(conn)

                # Utiliser explicitement le schéma public pour éviter les problèmes de search_path
                cursor.execute("SELECT public.calculate_duplicates()")
                duplicate_count = cursor.fetchone()[0]
                
                conn.commit()
                self.logger.info(f"Doublons calculés: {duplicate_count} fichiers")
                return duplicate_count
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Erreur lors du calcul des doublons: {e}")
                raise

    def _ensure_calculate_duplicates_function(self, conn):
        """
        Crée la fonction calculate_duplicates() si elle est absente.
        
        Args:
            conn: Connexion PostgreSQL active
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION public.calculate_duplicates()
            RETURNS INTEGER AS $$
            DECLARE
                duplicate_count INTEGER;
            BEGIN
                UPDATE files
                SET is_duplicate = TRUE,
                    duplicate_of = (
                        SELECT id
                        FROM files f2
                        WHERE f2.checksum = files.checksum
                          AND f2.id != files.id
                          AND f2.is_directory = FALSE
                        LIMIT 1
                    )
                WHERE checksum IN (
                    SELECT checksum
                    FROM files
                    WHERE checksum IS NOT NULL
                      AND is_directory = FALSE
                    GROUP BY checksum
                    HAVING COUNT(*) > 1
                )
                AND is_directory = FALSE;

                SELECT COUNT(*) INTO duplicate_count
                FROM files
                WHERE is_duplicate = TRUE;

                RETURN duplicate_count;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        conn.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de la base de données
        
        Returns:
            Dictionnaire avec les statistiques
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            stats = {}
            
            # Statistiques générales
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    COUNT(CASE WHEN is_directory = FALSE THEN 1 END) as files_only,
                    COUNT(CASE WHEN is_directory = TRUE THEN 1 END) as directories,
                    COUNT(CASE WHEN is_duplicate = TRUE THEN 1 END) as duplicates,
                    COALESCE(SUM(CASE WHEN is_directory = FALSE THEN size END), 0) as total_size
                FROM files
            """)
            general_stats = cursor.fetchone()
            stats.update(general_stats)
            
            # Distribution par taille
            cursor.execute("SELECT * FROM file_size_distribution ORDER BY file_count DESC")
            stats['size_distribution'] = [dict(row) for row in cursor.fetchall()]
            
            # Fichiers les plus volumineux
            cursor.execute("""
                SELECT name, size, path 
                FROM files 
                WHERE is_directory = FALSE AND size IS NOT NULL
                ORDER BY size DESC 
                LIMIT 10
            """)
            stats['largest_files'] = [dict(row) for row in cursor.fetchall()]
            
            # Doublons récents
            cursor.execute("""
                SELECT f.name, f.size, f.checksum, COUNT(*) as count
                FROM files f
                WHERE f.checksum IS NOT NULL AND f.is_duplicate = TRUE
                GROUP BY f.name, f.size, f.checksum
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, f.size DESC
                LIMIT 10
            """)
            stats['top_duplicates'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def search_files(self, query: str = "", limit: int = 1000, 
                    file_type: str = None, size_min: int = None, 
                    size_max: int = None, duplicates_only: bool = False) -> List[Dict[str, Any]]:
        """
        Recherche des fichiers avec critères multiples
        
        Args:
            query: Recherche textuelle dans le nom
            limit: Limite de résultats
            file_type: Type de fichier (extension)
            size_min: Taille minimum
            size_max: Taille maximum
            duplicates_only: Uniquement les doublons
            
        Returns:
            Liste des fichiers trouvés
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Construction de la requête
            sql = """
                SELECT id, path, name, size, checksum, last_modified,
                       is_directory, is_duplicate, duplicate_of,
                       created_at, updated_at
                FROM files
                WHERE 1=1
            """
            params = []
            
            # Filtres
            if query:
                sql += " AND (name ILIKE %s OR path ILIKE %s)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if file_type:
                sql += " AND LOWER(name) LIKE %s"
                params.append(f"%.{file_type.lower()}")
            
            if size_min is not None:
                sql += " AND size >= %s"
                params.append(size_min)
            
            if size_max is not None:
                sql += " AND size <= %s"
                params.append(size_max)
            
            if duplicates_only:
                sql += " AND is_duplicate = TRUE"
            
            sql += " ORDER BY name LIMIT %s"
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_crawl_statistics(self, stats: Dict[str, Any]):
        """
        Sauvegarde les statistiques d'une session de crawl
        
        Args:
            stats: Statistiques à sauvegarder
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO crawl_statistics (
                        total_files, total_directories, total_size,
                        duplicate_files, duplicate_size, crawl_duration_seconds,
                        server_info, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    stats.get('total_files', 0),
                    stats.get('total_directories', 0),
                    stats.get('total_size', 0),
                    stats.get('duplicate_files', 0),
                    stats.get('duplicate_size', 0),
                    stats.get('crawl_duration_seconds', 0),
                    stats.get('server_info', ''),
                    stats.get('status', 'completed')
                ))
                
                conn.commit()
                self.logger.info("Statistiques de crawl sauvegardées")
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Erreur lors de la sauvegarde des statistiques: {e}")
                raise
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à la base de données
        
        Returns:
            True si la connexion fonctionne
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.logger.info(f"Connexion PostgreSQL réussie: {version}")
                return True
        except Exception as e:
            self.logger.error(f"Échec de connexion PostgreSQL: {e}")
            return False

# Fonction utilitaire pour créer l'adaptateur à partir de la configuration
def create_postgres_adapter(config_manager) -> PostgreSQLAdapter:
    """
    Crée un adaptateur PostgreSQL à partir du gestionnaire de configuration
    
    Args:
        config_manager: Gestionnaire de configuration OpenIndex
        
    Returns:
        Instance de PostgreSQLAdapter
    """
    db_config = config_manager.get_database_config()
    
    # Configuration PostgreSQL (peut être surchargée par variables d'environnement)
    postgres_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'openindex'),
        'user': os.getenv('POSTGRES_USER', 'openindex_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
    }
    
    return PostgreSQLAdapter(postgres_config)
