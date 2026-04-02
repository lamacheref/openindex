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
import time
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
            # Set transaction isolation level to SERIALIZABLE for stronger consistency
            cursor = conn.cursor()
            cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            cursor.close()
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
                init_sql_path = Path(__file__).resolve().parents[1] / "database" / "init.sql"
                with init_sql_path.open("r", encoding="utf-8") as sql_file:
                    cursor.execute(sql_file.read())
                conn.commit()
                self.ensure_file_space_linking()
                self.logger.info("Base de données PostgreSQL initialisée et accessible")
                return

            init_sql_path = Path(__file__).resolve().parents[1] / "database" / "init.sql"
            with init_sql_path.open("r", encoding="utf-8") as sql_file:
                cursor.execute(sql_file.read())
            conn.commit()
            self.logger.info(f"Schéma PostgreSQL initialisé depuis {init_sql_path}")
        self.ensure_file_space_linking()

    def ensure_file_space_linking(self):
        """Ajoute et rétro-remplit le lien entre fichiers et configuration de crawl."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                ALTER TABLE files
                ADD COLUMN IF NOT EXISTS crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_files_crawl_config_id ON files(crawl_config_id)"
            )
            cursor.execute(
                """
                UPDATE files AS f
                SET crawl_config_id = matched.config_id
                FROM (
                    SELECT DISTINCT ON (f.id)
                        f.id AS file_id,
                        c.id AS config_id
                    FROM files AS f
                    JOIN crawl_configs AS c
                      ON f.path LIKE c.start_path || '%%'
                    WHERE f.crawl_config_id IS NULL
                    ORDER BY f.id, LENGTH(c.start_path) DESC, c.created_at DESC
                ) AS matched
                WHERE f.id = matched.file_id
                  AND f.crawl_config_id IS NULL
                """
            )
            conn.commit()

    def _normalize_timestamp_value(self, value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

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
                        file_data.get('crawl_config_id'),
                        file_data.get('created_at', datetime.now()),
                        file_data.get('updated_at', datetime.now())
                    ))
                
                # Insertion par lot avec gestion des doublons
                execute_values(
                    cursor,
                    """
                    INSERT INTO files (
                        path, name, size, checksum, last_modified,
                        is_directory, is_duplicate, duplicate_of, crawl_config_id,
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
                        crawl_config_id = COALESCE(EXCLUDED.crawl_config_id, files.crawl_config_id),
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

    def get_files_by_paths(
        self,
        paths: List[str],
        crawl_config_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Retourne les métadonnées existantes indexées par chemin."""
        if not paths:
            return {}

        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sql = """
                SELECT path, size, last_modified, checksum, crawl_config_id::text AS crawl_config_id
                FROM files
                WHERE path = ANY(%s)
                  AND is_directory = FALSE
            """
            params: List[Any] = [paths]
            if crawl_config_id:
                sql += " AND crawl_config_id::text = %s"
                params.append(crawl_config_id)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.commit()
            return {row["path"]: dict(row) for row in rows}

    def get_last_completed_crawl_triggered_at(
        self,
        crawl_config_id: str,
        exclude_run_id: Optional[str] = None,
    ) -> Optional[datetime]:
        """Retourne la date du dernier run terminé avec succès pour un espace."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT triggered_at
                FROM crawl_runs
                WHERE config_id::text = %s
                  AND LOWER(status) = 'completed'
            """
            params: List[Any] = [crawl_config_id]
            if exclude_run_id:
                sql += " AND id::text <> %s"
                params.append(exclude_run_id)
            sql += " ORDER BY triggered_at DESC LIMIT 1"

            cursor.execute(sql, params)
            row = cursor.fetchone()
            conn.commit()
            if not row:
                return None
            return row[0]
    
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

    def save_crawl_run_checkpoint(
        self,
        run_id: str,
        base_path: str,
        stats: Dict[str, Any],
        queues: Dict[str, List[Any]],
    ) -> None:
        """Persiste un snapshot minimal permettant de reprendre un run pending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO crawl_run_checkpoints (
                        run_id, base_path, total_files, total_directories, total_size,
                        processed_size, large_files, estimated_total_size, phase,
                        last_activity_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        base_path = EXCLUDED.base_path,
                        total_files = EXCLUDED.total_files,
                        total_directories = EXCLUDED.total_directories,
                        total_size = EXCLUDED.total_size,
                        processed_size = EXCLUDED.processed_size,
                        large_files = EXCLUDED.large_files,
                        estimated_total_size = EXCLUDED.estimated_total_size,
                        phase = EXCLUDED.phase,
                        last_activity_at = EXCLUDED.last_activity_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [
                        run_id,
                        base_path,
                        stats.get("total_files", 0),
                        stats.get("total_directories", 0),
                        stats.get("total_size", 0),
                        stats.get("processed_size", 0),
                        stats.get("large_files", 0),
                        stats.get("estimated_total_size", 0),
                        stats.get("phase", "crawl"),
                        stats.get("last_activity_at"),
                    ],
                )
                cursor.execute("DELETE FROM crawl_run_queue_items WHERE run_id::text = %s", [run_id])

                values = []
                for queue_name, items in queues.items():
                    for item in items:
                        if isinstance(item, str):
                            values.append(
                                (
                                    run_id,
                                    queue_name,
                                    item,
                                    None,
                                    None,
                                    None,
                                    queue_name == "directory_queue",
                                    None,
                                )
                            )
                            continue
                        values.append(
                            (
                                run_id,
                                queue_name,
                                item.get("path"),
                                item.get("name"),
                                item.get("size"),
                                self._normalize_timestamp_value(item.get("last_modified")),
                                bool(item.get("is_directory", False)),
                                item.get("crawl_config_id"),
                            )
                        )

                if values:
                    execute_values(
                        cursor,
                        """
                        INSERT INTO crawl_run_queue_items (
                            run_id, queue_name, path, name, size,
                            last_modified, is_directory, crawl_config_id
                        ) VALUES %s
                        """,
                        values,
                    )

                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def load_crawl_run_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Charge le dernier snapshot persistant d'un run."""
        with self.get_connection() as conn:
            checkpoint_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            queue_cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            checkpoint_cursor.execute(
                """
                SELECT
                    run_id::text AS run_id,
                    base_path,
                    total_files,
                    total_directories,
                    total_size,
                    processed_size,
                    large_files,
                    estimated_total_size,
                    phase,
                    last_activity_at,
                    updated_at
                FROM crawl_run_checkpoints
                WHERE run_id::text = %s
                """,
                [run_id],
            )
            checkpoint = checkpoint_cursor.fetchone()
            if not checkpoint:
                conn.commit()
                return None

            queue_cursor.execute(
                """
                SELECT
                    queue_name,
                    path,
                    name,
                    size,
                    last_modified,
                    is_directory,
                    crawl_config_id::text AS crawl_config_id
                FROM crawl_run_queue_items
                WHERE run_id::text = %s
                ORDER BY created_at ASC
                """,
                [run_id],
            )
            queue_rows = queue_cursor.fetchall()
            conn.commit()

        queues: Dict[str, List[Any]] = {
            "directory_queue": [],
            "directory_result_queue": [],
            "file_queue": [],
            "large_file_queue": [],
        }
        for row in queue_rows:
            queue_name = row["queue_name"]
            if queue_name not in queues:
                continue
            if queue_name == "directory_queue":
                queues[queue_name].append(row["path"])
                continue
            queues[queue_name].append(
                {
                    "path": row["path"],
                    "name": row["name"],
                    "size": row["size"],
                    "last_modified": row["last_modified"].isoformat() if row["last_modified"] else None,
                    "is_directory": row["is_directory"],
                    "crawl_config_id": row["crawl_config_id"],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }
            )

        return {
            "base_path": checkpoint["base_path"],
            "stats": {
                "total_files": checkpoint["total_files"] or 0,
                "total_directories": checkpoint["total_directories"] or 0,
                "total_size": checkpoint["total_size"] or 0,
                "processed_size": checkpoint["processed_size"] or 0,
                "large_files": checkpoint["large_files"] or 0,
                "estimated_total_size": checkpoint["estimated_total_size"] or 0,
                "phase": checkpoint["phase"] or "crawl",
                "last_activity": checkpoint["last_activity_at"].timestamp() if checkpoint["last_activity_at"] else None,
            },
            "queues": queues,
        }

    def clear_crawl_run_checkpoint(self, run_id: str) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM crawl_run_queue_items WHERE run_id::text = %s", [run_id])
                cursor.execute("DELETE FROM crawl_run_checkpoints WHERE run_id::text = %s", [run_id])
                conn.commit()
            except Exception:
                conn.rollback()
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

    def claim_next_crawl_run(self) -> Optional[Dict[str, Any]]:
        """Réserve le prochain run en attente et retourne sa configuration complète."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cursor.execute(
                    """
                    WITH next_run AS (
                        SELECT id
                        FROM crawl_runs
                        WHERE LOWER(status) IN ('queued', 'pending')
                        ORDER BY triggered_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE crawl_runs AS r
                    SET status = 'running'
                    FROM next_run
                    WHERE r.id = next_run.id
                    RETURNING
                        r.id::text AS run_id,
                        r.config_id::text AS config_id,
                        r.triggered_at::text
                    """
                )
                run = cursor.fetchone()
                if not run:
                    conn.commit()
                    return None

                cursor.execute(
                    """
                    SELECT
                        id::text AS config_id,
                        name,
                        domain_zone,
                        start_path,
                        include_paths,
                        exclude_paths,
                        connection_username,
                        connection_password,
                        connection_domain
                    FROM crawl_configs
                    WHERE id::text = %s
                    """,
                    [run["config_id"]],
                )
                config = cursor.fetchone()
                conn.commit()
                if not config:
                    return None
                payload = dict(run)
                payload.update(dict(config))
                return payload
            except Exception:
                conn.rollback()
                raise

    def update_crawl_run_status(self, run_id: str, status: str) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE crawl_runs SET status = %s WHERE id::text = %s",
                    [status, run_id],
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_crawl_run_status(self, run_id: str) -> Optional[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status FROM crawl_runs WHERE id::text = %s",
                [run_id],
            )
            row = cursor.fetchone()
            conn.commit()
            if not row:
                return None
            return row[0]

    def get_recent_write_activity(self, window_seconds: int = 300) -> Dict[str, Any]:
        """Retourne les écritures récentes observées dans la table files."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS recent_writes,
                    MAX(updated_at) AS last_write_at
                FROM files
                WHERE updated_at >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 second')
                """,
                [max(int(window_seconds), 1)],
            )
            row = cursor.fetchone() or {}
            conn.commit()
            return {
                "recent_writes": int(row.get("recent_writes") or 0),
                "last_write_at": row.get("last_write_at"),
            }

    def mark_crawl_run_pending(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Replace un run actif ou en file d'attente dans l'état pending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE crawl_runs
                    SET status = 'pending'
                    WHERE id::text = %s
                      AND LOWER(status) IN ('queued', 'running', 'in_progress', 'cancelling')
                    RETURNING id::text, status
                    """,
                    [run_id],
                )
                row = cursor.fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        if not row:
            return None
        return {"run_id": row[0], "status": row[1]}

    def get_stale_running_runs(self) -> List[Dict[str, Any]]:
        """Récupère les runs qui sont en cours depuis trop longtemps."""
        from typing import List
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, triggered_at
                FROM crawl_runs
                WHERE LOWER(status) IN ('running', 'in_progress')
                ORDER BY triggered_at ASC
                """
            )
            return [dict(id=row[0], triggered_at=row[1]) for row in cursor.fetchall()]

    def reset_stale_running_runs(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE crawl_runs
                SET status = 'failed'
                WHERE LOWER(status) IN ('running', 'in_progress')
                """
            )
            cursor.execute(
                """
                UPDATE crawl_runs
                SET status = 'cancelled'
                WHERE LOWER(status) = 'cancelling'
                """
            )
            conn.commit()

    def wait_for_next_run(self, poll_interval_seconds: int = 5) -> Dict[str, Any]:
        """Boucle de polling simple jusqu'à trouver un run à traiter."""
        while True:
            run = self.claim_next_crawl_run()
            if run:
                return run
            time.sleep(poll_interval_seconds)

    def get_files_by_config(self, crawl_config_id: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les fichiers pour une configuration de crawl donnée.
        
        Args:
            crawl_config_id: ID de la configuration de crawl
            
        Returns:
            Liste des fichiers avec leurs métadonnées
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                """
                SELECT path, name, size, checksum, last_modified, is_directory
                FROM files
                WHERE crawl_config_id::text = %s
                """,
                (crawl_config_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_files_by_paths(self, file_paths: List[str]) -> int:
        """
        Supprime les fichiers spécifiés de la base de données.
        
        Args:
            file_paths: Liste des chemins de fichiers à supprimer
            
        Returns:
            Nombre de fichiers supprimés
        """
        if not file_paths:
            return 0
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Utiliser une requête paramétrée pour éviter les injections SQL
            cursor.execute(
                """
                DELETE FROM files
                WHERE path = ANY(%s)
                """,
                (file_paths,)
            )
            conn.commit()
            return cursor.rowcount

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
