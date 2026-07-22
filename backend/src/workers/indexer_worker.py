#!/usr/bin/env python3
"""
Indexer Worker - Service d'indexation simplifié et robuste
Gère l'indexation de fichiers par chemin avec isolation des sources
"""

import os
import sys
import time
import json
import signal
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import logging.config

# Configuration du logging JSON
def setup_json_logging():
    """Configure le logging en format JSON structuré"""
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(job_id)s %(config_id)s %(files_processed)s %(duration)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO'
        }
    }

    try:
        logging.config.dictConfig(logging_config)
    except Exception as e:
        # Fallback au format basique si JSON échoue
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logger.warning(f"JSON logging non disponible: {e}")

logger = logging.getLogger("indexer.worker")
setup_json_logging()


class IndexerStatus(str, Enum):
    """Statuts possibles d'un job d'indexation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class IndexerJob:
    """Représente un job d'indexation"""
    id: str
    path: str
    config_id: str
    config_name: str
    status: IndexerStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files_found: int = 0
    files_indexed: int = 0
    bytes_total: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le job en dictionnaire sérialisable"""
        return {
            "id": self.id,
            "path": self.path,
            "config_id": self.config_id,
            "config_name": self.config_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files_found": self.files_found,
            "files_indexed": self.files_indexed,
            "bytes_total": self.bytes_total,
            "error_message": self.error_message
        }


class IndexerWorker:
    """
    Worker d'indexation simplifié
    - Gère une queue de jobs par chemin
    - Isole les sources (pas de mélange entre chemins)
    - Fournit des métriques en temps réel
    """
    
    def __init__(self, poll_interval: int = 5, slow_queue_enabled: bool = True):
        self.poll_interval = poll_interval
        self.slow_queue_enabled = slow_queue_enabled
        self.SLOW_THRESHOLD_BYTES = 200 * 1024 * 1024  # 200 Mo
        self.running = False
        self.current_job: Optional[IndexerJob] = None
        self.jobs_history: List[IndexerJob] = []
        self.max_history = 100
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Verrou pour accès thread-safe aux jobs
        self._jobs_lock = threading.Lock()

        # Métriques temps réel
        self._metrics = {
            'files_processed': 0,
            'errors_count': 0,
            'start_time': datetime.now(timezone.utc),
            'last_reset': datetime.now(timezone.utc)
        }
        self._metrics_lock = threading.Lock()

        # Batch insert optimization
        self._batch_insert_enabled = True
        self._batch_size = 100  # Taille optimale pour les insertions par lots
        self._file_batch: List[Dict[str, Any]] = []
        self._batch_lock = threading.Lock()

        logger.info("IndexerWorker initialisé avec optimisation batch insert")
    
    def start(self):
        """Démarre le worker dans un thread séparé"""
        if self.running:
            logger.warning("Worker déjà en cours d'exécution")
            return
        
        self.running = True
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._run, daemon=True)
        self._worker_thread.start()
        logger.info("Worker d'indexation démarré")
    
    def stop(self):
        """Arrête le worker proprement"""
        if not self.running:
            return
        
        logger.info("Arrêt du worker demandé...")
        self.running = False
        self._stop_event.set()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=30)
        
        logger.info("Worker arrêté")
    
    def _run(self):
        """Boucle principale du worker"""
        logger.info("Boucle principale du worker démarrée")
        
        while self.running and not self._stop_event.is_set():
            try:
                # Chercher un job pending dans la base
                job = self._fetch_next_job()
                
                if job:
                    self._process_job(job)
                else:
                    # Pas de job, attendre
                    self._stop_event.wait(self.poll_interval)
                    
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}", exc_info=True)
                self._stop_event.wait(self.poll_interval)
        
        logger.info("Boucle principale terminée")
    
    def _fetch_next_job(self) -> Optional[IndexerJob]:
        """Récupère le prochain job pending depuis la base de données"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os
            
            # Configuration DB
            config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            
            db = PostgreSQLAdapter(config)
            
            # Récupérer le plus ancien job pending
            # Priorité à la queue rapide (fast) → slow traitée entre deux fast
            query = """
                SELECT id, path, config_id, config_name, status, created_at,
                       started_at, completed_at, files_found, files_indexed, 
                       bytes_total, error_message, queue_type
                FROM indexer_jobs
                WHERE status = 'pending'
                ORDER BY 
                    CASE WHEN queue_type = 'fast' THEN 0 ELSE 1 END,
                    created_at ASC
                LIMIT 1
            """
            
            results = db.execute_query(query)
            
            if results:
                row = results[0]
                job = IndexerJob(
                    id=row[0],
                    path=row[1],
                    config_id=row[2],
                    config_name=row[3],
                    status=IndexerStatus(row[4]),
                    created_at=row[5],
                    started_at=row[6],
                    completed_at=row[7],
                    files_found=row[8] or 0,
                    files_indexed=row[9] or 0,
                    bytes_total=row[10] or 0,
                    error_message=row[11]
                )
                queue_type = row[12] if len(row) > 12 else 'fast'
                logger.info(f"Job {job.id} récupéré (queue: {queue_type})")
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du job: {e}")
            return None
    
    def _process_job(self, job: IndexerJob):
        """Traite un job d'indexation"""
        logger.info(f"Traitement du job {job.id} pour {job.path}", extra={
            'job_id': job.id,
            'config_id': job.config_id
        })

        self.current_job = job
        job.status = IndexerStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        # Réinitialiser les métriques pour ce job
        self._reset_metrics()

        # Mettre à jour le statut dans la DB
        self._update_job_status(job)

        try:
            # Indexer les fichiers
            self._index_path(job)

            job.status = IndexerStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            logger.info(f"Job {job.id} terminé avec succès: {job.files_indexed} fichiers indexés", extra={
                'job_id': job.id,
                'config_id': job.config_id,
                'files_processed': job.files_indexed,
                'duration': (job.completed_at - job.started_at).total_seconds()
            })

        except Exception as e:
            job.status = IndexerStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(e)
            logger.error(f"Job {job.id} échoué: {e}", extra={
                'job_id': job.id,
                'config_id': job.config_id,
                'error': str(e)
            })
            self._increment_error_count()

        finally:
            self._update_job_status(job)
            self._add_to_history(job)
            self.current_job = None
    
    def _get_queue_type(self, file_size: int) -> str:
        """Détermine le type de queue en fonction de la taille du fichier"""
        return 'slow' if file_size >= self.SLOW_THRESHOLD_BYTES else 'fast'

    def _resolve_space_id(self, config: Dict) -> str:
        from backend.src.database.postgres_adapter import PostgreSQLAdapter
        import os

        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        db = PostgreSQLAdapter(db_config)

        result = db.execute_query(
            """
            INSERT INTO smb_spaces (name, host, share, domain_zone, connection_username, connection_password, connection_domain)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (host, share) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            [
                config.get('name', 'Unnamed'),
                config['host'],
                config['share'],
                config.get('domain', 'WORKGROUP'),
                config.get('username', ''),
                config.get('password', ''),
                config.get('domain', '')
            ]
        )
        return result[0][0] if result else ''

    def _index_path(self, job: IndexerJob):
        """Indexe un chemin via le protocole 2 phases : BFS répertoires → bottom-up fichiers"""
        from backend.src.utils.crawl_utils import SMBClient, get_file_info
        
        logger.info(f"Indexation de {job.path} (protocole 2 phases)")
        
        config = self._get_smb_config(job.config_id)
        if not config:
            raise ValueError(f"Configuration SMB introuvable pour {job.config_id}")
        
        space_id = self._resolve_space_id(config)
        
        client = SMBClient(
            host=config['host'],
            share=config['share'],
            username=config['username'],
            password=config['password'],
            domain=config.get('domain', '')
        )
        
        try:
            client.connect()
            remote_path = config.get('remote_path', '')
            
            dir_count = self._phase_a_bfs_directories(client, remote_path, space_id, job)
            logger.info(f"Phase A terminée: {dir_count} répertoires découverts", extra={
                'job_id': job.id, 'config_id': job.config_id
            })
            
            file_count = self._phase_b_bottom_up_files(client, space_id, job, config)
            logger.info(f"Phase B terminée: {file_count} fichiers traités", extra={
                'job_id': job.id, 'config_id': job.config_id
            })
            
            self._mark_deleted_files(job, space_id)
        finally:
            client.disconnect()
    
    def _phase_a_bfs_directories(self, client, root_path: str, space_id: str, job: IndexerJob) -> int:
        from collections import deque
        from backend.src.database.postgres_adapter import PostgreSQLAdapter
        import os

        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        db = PostgreSQLAdapter(db_config)

        queue = deque()
        queue.append((root_path, 0, ''))
        dir_count = 0

        while queue:
            if self._stop_event.is_set():
                raise InterruptedError("Indexation interrompue")

            current_path, depth, parent_path = queue.popleft()
            dir_name = os.path.basename(current_path) if current_path else '/'

            try:
                db.execute_query(
                    """
                    INSERT INTO directories (space_id, path, name, parent_path, depth)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (space_id, path) DO UPDATE SET
                        name = EXCLUDED.name,
                        depth = EXCLUDED.depth
                    """,
                    [space_id, current_path, dir_name, parent_path, depth],
                    fetch=False
                )
                dir_count += 1

                if dir_count % 500 == 0:
                    logger.info(f"Phase A progression: {dir_count} répertoires découverts (profondeur {depth})")

                entries = client.list_dir(current_path)
                for entry in entries:
                    if isinstance(entry, dict):
                        entry_name = entry.get('name', '')
                        is_dir = entry.get('is_directory', False)
                    else:
                        entry_name = getattr(entry, 'filename', '')
                        is_dir = getattr(entry, 'isDirectory', False)

                    if is_dir:
                        full_path = f"{current_path}/{entry_name}" if current_path else entry_name
                        queue.append((full_path, depth + 1, current_path))

            except Exception as e:
                logger.warning(f"Erreur BFS répertoire {current_path}: {e}")
                self._increment_error_count()

        return dir_count

    def _phase_b_bottom_up_files(self, client, space_id: str, job: IndexerJob, config: Dict) -> int:
        from backend.src.database.postgres_adapter import PostgreSQLAdapter
        from backend.src.utils.crawl_utils import get_file_info
        import os

        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        db = PostgreSQLAdapter(db_config)

        dirs = db.execute_query(
            "SELECT id, path, name FROM directories WHERE space_id = %s ORDER BY depth DESC",
            [space_id]
        )
        if not dirs:
            logger.warning("Aucun répertoire trouvé pour Phase B")
            return 0

        skipped = 0
        for dir_id, dir_path, dir_name in dirs:
            if self._stop_event.is_set():
                raise InterruptedError("Indexation interrompue")

            try:
                entries = client.list_dir(dir_path)
            except Exception as e:
                logger.warning(f"Erreur liste répertoire {dir_path}: {e}")
                continue

            for entry in entries:
                if isinstance(entry, dict):
                    entry_name = entry.get('name', '')
                    is_dir = entry.get('is_directory', False)
                    entry_size = entry.get('size', 0)
                    entry_mtime = entry.get('mtime')
                else:
                    entry_name = getattr(entry, 'filename', '')
                    is_dir = getattr(entry, 'isDirectory', False)
                    entry_size = getattr(entry, 'size', 0)
                    entry_mtime = getattr(entry, 'mtime', None)

                if is_dir:
                    continue

                full_path = f"{dir_path}/{entry_name}" if dir_path else entry_name
                job.files_found += 1

                existing = db.execute_query(
                    """
                    SELECT id FROM indexed_files_optimized
                    WHERE path = %s AND name = %s AND size = %s
                      AND created_at = %s AND last_modified = %s
                    """,
                    [full_path, entry_name, entry_size, entry_mtime, entry_mtime]
                )

                if existing:
                    skipped += 1
                    continue

                try:
                    file_info = get_file_info(client, full_path)
                    if not file_info:
                        continue

                    file_info['is_garbage'] = self._is_garbage_file(entry_name)
                    file_queue_type = self._get_queue_type(entry_size)

                    if file_queue_type == 'slow' and self.slow_queue_enabled:
                        self._create_slow_file_job(file_info, job)
                    else:
                        if self._batch_insert_enabled:
                            self._add_to_batch({**file_info, 'space_id': space_id, 'directory_id': dir_id}, job.config_id)
                        else:
                            db.insert_file_optimized(file_info, space_id, dir_id)
                        job.files_indexed += 1
                        job.bytes_total += entry_size
                        self._increment_files_processed()
                except Exception as e:
                    logger.warning(f"Erreur indexation fichier {full_path}: {e}")
                    self._increment_error_count()

                if job.files_found % 100 == 0:
                    self._update_job_progress(job)

        logger.info(f"Phase B: {job.files_found} fichiers trouvés, {skipped} ignorés (inchangés), {job.files_indexed} indexés", extra={
            'job_id': job.id, 'config_id': job.config_id
        })
        return job.files_indexed
    
    def _create_slow_file_job(self, file_info: Dict, parent_job: IndexerJob):
        """Crée un job séparé pour un fichier >= 200Mo dans la queue lente"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os
            import uuid
            
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            
            db = PostgreSQLAdapter(db_config)
            slow_job_id = str(uuid.uuid4())
            
            db.execute_query(
                """
                INSERT INTO indexer_jobs (id, path, config_id, config_name, status, 
                                          created_at, queue_type)
                VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP, 'slow')
                """,
                [slow_job_id, file_info.get('path', ''), parent_job.config_id,
                 parent_job.config_name],
                fetch=False
            )
            
            logger.info(f"Job lent créé: {slow_job_id} pour {file_info.get('path', '')}")
            
        except Exception as e:
            logger.warning(f"Erreur création job lent: {e}")
    
    def _get_smb_config(self, config_id: str) -> Optional[Dict]:
        """Récupère la configuration SMB depuis la DB"""
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
            
            db = PostgreSQLAdapter(config)
            result = db.get_crawl_config_by_id(config_id)
            
            if result:
                # Parser start_path pour extraire host, share et remote_path
                # Format attendu: //host/share/remote_path
                import re
                start_path = result.get('start_path', '')
                path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', start_path) if start_path else None
                
                if path_match:
                    host = path_match.group(1)
                    share = path_match.group(2)
                    remote_path = path_match.group(3) or ''
                else:
                    # Fallback: essayer de parser manuellement
                    parts = start_path.replace('//', '').split('/')
                    host = parts[0] if len(parts) > 0 else ''
                    share = parts[1] if len(parts) > 1 else ''
                    remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''
                
                return {
                    'id': result['id'],
                    'host': host,
                    'share': share,
                    'remote_path': remote_path,
                    'username': result.get('connection_username', ''),
                    'password': result.get('connection_password', ''),  # Récupéré directement depuis la DB via postgres_adapter
                    'domain': result.get('connection_domain', ''),
                    'name': result.get('name', 'Unnamed')
                }
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération config: {e}")
            return None
    
    def _is_garbage_file(self, file_name: str) -> bool:
        """Détecte si un fichier correspond à un pattern indésirable"""
        garbage_patterns = ['.tmp', '~', 'Thumbs.db', '.DS_Store', '.bak', '.swp']
        return any(file_name.endswith(pattern) or file_name.startswith(pattern) for pattern in garbage_patterns)

    def _insert_file(self, file_info: Dict, config_id: str, space_id: str = '', directory_id: str = ''):
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            db = PostgreSQLAdapter(db_config)

            file_path = file_info.get('path', '')
            file_name = file_info.get('name', '')
            is_garbage = self._is_garbage_file(file_name)
            file_info['is_garbage'] = is_garbage

            db.insert_file_optimized(file_info, space_id, directory_id)

            if is_garbage:
                db.execute_query(
                    """
                    INSERT INTO garbage_files (file_id, pattern, detected_at)
                    VALUES (
                        (SELECT id FROM indexed_files_optimized WHERE path = %s),
                        %s,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (file_id) DO NOTHING
                    """,
                    [file_path, self._get_garbage_pattern(file_name)],
                    fetch=False
                )

        except Exception as e:
            error_message = str(e)
            file_path = file_info.get('path', '')

            # Vérifier si c'est une erreur de fichier verrouillé
            if self._is_file_locked(error_message):
                # Vérifier si le fichier doit être réessayé
                if self._should_retry_file(file_path):
                    logger.warning(f"Fichier verrouillé - ajouté à la queue de réessai: {file_path}", extra={
                        'job_id': self.current_job.id if self.current_job else None,
                        'config_id': config_id,
                        'file_path': file_path,
                        'error': error_message,
                        'retry_attempt': self._get_retry_count(file_path) + 1
                    })

                    # Ajouter à la queue de réessai
                    if self.current_job:
                        self._add_file_to_retry(file_path, self.current_job.id, config_id, error_message)

                    # Ne pas incrémenter le compteur d'erreurs pour les fichiers verrouillés
                    return

                else:
                    logger.error(f"Fichier verrouillé - tentatives épuisées: {file_path}", extra={
                        'job_id': self.current_job.id if self.current_job else None,
                        'config_id': config_id,
                        'file_path': file_path,
                        'error': error_message,
                        'max_attempts_reached': True
                    })
                    # Incrémenter le compteur d'erreurs car le max de tentatives est atteint
                    self._increment_error_count()
            else:
                logger.warning(f"Erreur insertion fichier: {e}", extra={
                    'job_id': self.current_job.id if self.current_job else None,
                    'config_id': config_id,
                    'file_path': file_path,
                    'error': error_message
                })
                # Incrémenter le compteur d'erreurs pour les autres types d'erreurs
                self._increment_error_count()

    def _get_garbage_pattern(self, file_name: str) -> str:
        """Retourne le pattern correspondant au fichier indésirable"""
        if file_name.endswith('.tmp'):
            return '*.tmp'
        elif file_name.startswith('~'):
            return '~*'
        elif file_name == 'Thumbs.db':
            return 'Thumbs.db'
        elif file_name == '.DS_Store':
            return '.DS_Store'
        elif file_name.endswith('.bak'):
            return '*.bak'
        elif file_name.endswith('.swp'):
            return '*.swp'
        return 'unknown'
    
    def _mark_deleted_files(self, job: IndexerJob, space_id: str = ''):
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            db.execute_query(
                """
                UPDATE indexed_files_optimized
                SET is_deleted = true, deleted_at = CURRENT_TIMESTAMP
                WHERE space_id = %s
                  AND path LIKE %s
                  AND is_deleted = false
                  AND updated_at < CURRENT_TIMESTAMP - INTERVAL '1 hour'
                """,
                [space_id, f"{job.path}%"],
                fetch=False
            )

            deleted_count = db.execute_query(
                "SELECT COUNT(*) FROM indexed_files_optimized WHERE space_id = %s AND path LIKE %s AND is_deleted = true",
                [space_id, f"{job.path}%"]
            )
            count = deleted_count[0][0] if deleted_count else 0
            logger.info(f"Fichiers marqués comme supprimés: {count}")

        except Exception as e:
            logger.warning(f"Erreur marquage fichiers supprimés: {e}")
    
    def _update_job_status(self, job: IndexerJob):
        """Met à jour le statut du job dans la DB"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os
            
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            
            db = PostgreSQLAdapter(db_config)
            
            query = """
                UPDATE indexer_jobs
                SET status = %s,
                    started_at = %s,
                    completed_at = %s,
                    files_found = %s,
                    files_indexed = %s,
                    bytes_total = %s,
                    error_message = %s
                WHERE id = %s
            """
            
            db.execute_query(query, [
                job.status.value,
                job.started_at,
                job.completed_at,
                job.files_found,
                job.files_indexed,
                job.bytes_total,
                job.error_message,
                job.id
            ])
            
        except Exception as e:
            logger.error(f"Erreur mise à jour job: {e}")
    
    def _update_job_progress(self, job: IndexerJob):
        """Met à jour la progression du job"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os
            
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            
            db = PostgreSQLAdapter(db_config)
            
            query = """
                UPDATE indexer_jobs
                SET files_found = %s,
                    files_indexed = %s,
                    bytes_total = %s
                WHERE id = %s
            """
            
            db.execute_query(query, [
                job.files_found,
                job.files_indexed,
                job.bytes_total,
                job.id
            ])
            
        except Exception as e:
            logger.error(f"Erreur mise à jour progression: {e}")
    
    def _add_to_history(self, job: IndexerJob):
        """Ajoute un job à l'historique"""
        with self._jobs_lock:
            self.jobs_history.append(job)
            # Garder seulement les N derniers
            if len(self.jobs_history) > self.max_history:
                self.jobs_history = self.jobs_history[-self.max_history:]
    
    def get_current_job(self) -> Optional[Dict[str, Any]]:
        """Retourne le job en cours"""
        if self.current_job:
            return self.current_job.to_dict()
        return None
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retourne l'historique des jobs"""
        with self._jobs_lock:
            return [job.to_dict() for job in self.jobs_history[-limit:]]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance temps réel"""
        with self._metrics_lock:
            metrics = self._metrics.copy()

            # Calculer les taux
            now = datetime.now(timezone.utc)
            elapsed = (now - metrics['last_reset']).total_seconds() or 1

            files_per_second = metrics['files_processed'] / elapsed if elapsed > 0 else 0
            error_rate = metrics['errors_count'] / max(1, metrics['files_processed']) if metrics['files_processed'] > 0 else 0

            return {
                "files_processed": metrics['files_processed'],
                "errors_count": metrics['errors_count'],
                "files_per_second": round(files_per_second, 2),
                "error_rate": round(error_rate, 4),
                "uptime_seconds": (now - metrics['start_time']).total_seconds(),
                "last_reset": metrics['last_reset'].isoformat()
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Retourne l'état de santé du worker"""
        try:
            # Vérifier la connexion à la base de données
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)
            db.execute_query("SELECT 1")  # Test de connexion

            return {
                "status": "healthy",
                "worker_running": self.running,
                "database_connected": True,
                "current_job": self.current_job is not None,
                "pending_jobs": self._count_pending_jobs(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "worker_running": self.running,
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _reset_metrics(self):
        """Réinitialise les métriques pour un nouveau job"""
        with self._metrics_lock:
            self._metrics['files_processed'] = 0
            self._metrics['errors_count'] = 0
            self._metrics['last_reset'] = datetime.now(timezone.utc)

    def _increment_files_processed(self):
        """Incrémente le compteur de fichiers traités"""
        with self._metrics_lock:
            self._metrics['files_processed'] += 1

    def _increment_error_count(self):
        """Incrémente le compteur d'erreurs"""
        with self._metrics_lock:
            self._metrics['errors_count'] += 1

    def _count_pending_jobs(self) -> int:
        """Compte le nombre de jobs en attente"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)
            results = db.execute_query("SELECT COUNT(*) FROM indexer_jobs WHERE status = 'pending'")
            return results[0][0] if results else 0
        except Exception:
            return 0

    def _should_retry_file(self, file_path: str) -> bool:
        """Vérifie si un fichier doit être réessayé (max 5 tentatives via DB)"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            # Obtenir le file_id à partir du chemin
            file_id_result = db.execute_query(
                "SELECT id FROM indexed_files_optimized WHERE path = %s",
                [file_path]
            )

            if not file_id_result:
                return True  # Fichier non encore indexé, peut être réessayé

            file_id = file_id_result[0][0]

            # Vérifier si le fichier doit être réessayé
            should_retry = db.execute_query(
                "SELECT should_retry_file(%s)",
                [file_id]
            )

            return should_retry[0][0] if should_retry else False

        except Exception as e:
            logger.warning(f"Erreur vérification retry pour {file_path}: {e}")
            return False

    def _add_file_to_retry(self, file_path: str, job_id: str, config_id: str, error_message: str):
        """Ajoute un fichier à la queue de réessai"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            # Obtenir le file_id à partir du chemin
            file_id_result = db.execute_query(
                "SELECT id FROM indexed_files_optimized WHERE path = %s",
                [file_path]
            )

            if not file_id_result:
                logger.warning(f"Fichier non trouvé pour retry: {file_path}")
                return

            file_id = file_id_result[0][0]

            # Ajouter à la queue de réessai
            db.execute_query(
                "SELECT add_file_to_retry(%s, %s, %s, %s, %s)",
                [file_id, job_id, config_id, file_path, error_message],
                fetch=False
            )

            logger.info(f"Fichier ajouté à la queue de réessai: {file_path} (attempt {self._get_retry_count(file_path) + 1})")

        except Exception as e:
            logger.warning(f"Erreur ajout retry pour {file_path}: {e}")

    def _get_retry_count(self, file_path: str) -> int:
        """Retourne le nombre de tentatives pour un fichier"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            # Obtenir le file_id à partir du chemin
            file_id_result = db.execute_query(
                "SELECT id FROM indexed_files_optimized WHERE path = %s",
                [file_path]
            )

            if not file_id_result:
                return 0

            file_id = file_id_result[0][0]

            # Obtenir le compteur de tentatives
            retry_count = db.execute_query(
                "SELECT attempt_count FROM indexer_retries WHERE file_id = %s",
                [file_id]
            )

            return retry_count[0][0] if retry_count else 0

        except Exception:
            return 0

    def _is_file_locked(self, error_message: str) -> bool:
        """Détecte si une erreur est due à un fichier verrouillé"""
        locked_patterns = [
            'access denied',
            'permission denied',
            'file in use',
            'sharing violation',
            'locked by another process',
            'being used by another process'
        ]

        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in locked_patterns)

    def _is_file_missing(self, error_message: str) -> bool:
        """Détecte si une erreur est due à un fichier disparu"""
        missing_patterns = [
            'file not found',
            'no such file',
            'does not exist',
            'not exist',
            'file disappeared',
            'path not found'
        ]
        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in missing_patterns)

    def _is_file_conflict(self, error_message: str) -> bool:
        """Détecte si une erreur est due à un conflit de fichier"""
        conflict_patterns = [
            'already exists',
            'file exists',
            'conflict',
            'duplicate',
            'hash mismatch',
            'checksum mismatch',
            'different content'
        ]
        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in conflict_patterns)

    def _mark_file_as_missing(self, file_path: str, config_id: str, error_message: str):
        """Marque un fichier comme disparu dans la base de données"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            # Marquer le fichier comme disparu
            db.execute_query(
                """
                INSERT INTO missing_files (file_path, config_id, error_message, detected_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (file_path) DO UPDATE SET
                    error_message = EXCLUDED.error_message,
                    detected_at = CURRENT_TIMESTAMP,
                    occurrence_count = missing_files.occurrence_count + 1
                """,
                [file_path, config_id, error_message],
                fetch=False
            )

            logger.info(f"Fichier marqué comme disparu: {file_path}")

        except Exception as e:
            logger.warning(f"Erreur marquage fichier disparu: {e}", extra={
                'file_path': file_path,
                'error': str(e),
                'error_type': 'missing_file_marking_error'
            })

    def _handle_file_conflict(self, file_info: Dict, config_id: str, error_message: str, space_id: str = '', directory_id: str = ''):
        """Gère les conflits de fichiers en utilisant une stratégie de résolution"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            file_path = file_info.get('path', '')
            file_name = file_info.get('name', '')
            file_hash = file_info.get('checksum', '')
            file_size = file_info.get('size', 0)

            # Stratégie de résolution: renommer le fichier avec un suffixe de conflit
            conflict_suffix = "_conflict_1"
            if file_name.endswith(conflict_suffix):
                # Si déjà un conflit, essayer un autre suffixe
                import re
                match = re.match(r'^(.+)_conflict_(\d+)$', file_name)
                if match:
                    base_name = match.group(1)
                    conflict_num = int(match.group(2)) + 1
                    new_file_name = f"{base_name}_conflict_{conflict_num}"
                else:
                    new_file_name = f"{file_name}{conflict_suffix}"
            else:
                new_file_name = f"{file_name}{conflict_suffix}"

            # Mettre à jour le chemin du fichier avec le nouveau nom
            new_file_path = file_path.rsplit('/', 1)[0] + '/' + new_file_name if '/' in file_path else new_file_name
            file_info['path'] = new_file_path
            file_info['name'] = new_file_name

            # Enregistrer le conflit dans la base de données
            db.execute_query(
                """
                INSERT INTO file_conflicts (
                    original_path, conflict_path, config_id,
                    original_hash, conflict_hash, resolution_strategy,
                    detected_at, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                [
                    file_path, new_file_path, config_id,
                    file_hash, file_hash,  # Même hash pour le moment
                    'rename', 'resolved'
                ],
                fetch=False
            )

            # Essayer d'insérer le fichier avec le nouveau nom
            logger.info(f"Tentative d'insertion du fichier renommé: {new_file_path}")
            self._insert_file(file_info, config_id, space_id, directory_id)

            logger.info(f"Conflit résolu par renommage: {file_path} -> {new_file_path}")

        except Exception as e:
            logger.warning(f"Erreur gestion conflit: {e}", extra={
                'file_path': file_info.get('path', ''),
                'error': str(e),
                'error_type': 'conflict_handling_error'
            })
            # Si la résolution échoue, incrémenter le compteur d'erreurs
            self._increment_error_count()

    def _add_to_batch(self, file_info: Dict[str, Any], config_id: str):
        with self._batch_lock:
            self._file_batch.append({
                'path': file_info.get('path', ''),
                'name': file_info.get('name', ''),
                'size': file_info.get('size', 0),
                'checksum': file_info.get('checksum'),
                'last_modified': file_info.get('last_modified'),
                'modified_at': file_info.get('modified_at'),
                'config_id': config_id,
                'space_id': file_info.get('space_id', ''),
                'directory_id': file_info.get('directory_id', ''),
            })

            if len(self._file_batch) >= self._batch_size:
                self._flush_batch()

    def _flush_batch(self):
        if not self._file_batch:
            return

        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            import os

            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }

            db = PostgreSQLAdapter(db_config)

            with self._batch_lock:
                batch_copy = self._file_batch.copy()
                self._file_batch.clear()

            space_id = batch_copy[0].get('space_id', '') if batch_copy else ''

            db.insert_files_batch_optimized(batch_copy, space_id)

            logger.info(f"Batch insert optimized: {len(batch_copy)} fichiers", extra={
                'job_id': self.current_job.id if self.current_job else None,
                'files_processed': len(batch_copy),
                'batch_size': self._batch_size
            })

        except Exception as e:
            logger.error(f"Erreur batch insert optimized: {e}", extra={
                'job_id': self.current_job.id if self.current_job else None,
                'error': str(e)
            })
            with self._batch_lock:
                failed_batch = self._file_batch.copy()
                self._file_batch.clear()

            for file_info in failed_batch:
                try:
                    self._insert_file(
                        file_info,
                        file_info.get('config_id', ''),
                        file_info.get('space_id', ''),
                        file_info.get('directory_id', '')
                    )
                except Exception as retry_error:
                    logger.warning(f"Échec retry fichier {file_info.get('path', '')}: {retry_error}", extra={
                'file_path': file_info.get('path', ''),
                'error': str(retry_error),
                'error_type': 'batch_retry_error'
            })

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du worker"""
        return {
            "running": self.running,
            "current_job": self.get_current_job(),
            "history_count": len(self.jobs_history),
            "poll_interval": self.poll_interval,
            "slow_queue_enabled": self.slow_queue_enabled,
            "slow_threshold_bytes": self.SLOW_THRESHOLD_BYTES,
            "batch_insert_enabled": self._batch_insert_enabled,
            "batch_size": self._batch_size,
            "batch_pending": len(self._file_batch)
        }


# Instance globale du worker
_worker_instance: Optional[IndexerWorker] = None


def get_worker() -> IndexerWorker:
    """Retourne l'instance globale du worker"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = IndexerWorker()
    return _worker_instance


def start_worker():
    """Démarre le worker"""
    worker = get_worker()
    worker.start()
    return worker


def stop_worker():
    """Arrête le worker"""
    global _worker_instance
    if _worker_instance:
        _worker_instance.stop()
        _worker_instance = None


if __name__ == "__main__":
    # Mode standalone pour tests
    print("Starting Indexer Worker standalone...")
    worker = start_worker()
    
    try:
        # Garder le processus en vie
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping worker...")
        stop_worker()
        print("Worker stopped.")
