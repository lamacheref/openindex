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

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("indexer.worker")


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
        
        logger.info("IndexerWorker initialisé")
    
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
        logger.info(f"Traitement du job {job.id} pour {job.path}")
        
        self.current_job = job
        job.status = IndexerStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        
        # Mettre à jour le statut dans la DB
        self._update_job_status(job)
        
        try:
            # Indexer les fichiers
            self._index_path(job)
            
            job.status = IndexerStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            logger.info(f"Job {job.id} terminé avec succès: {job.files_indexed} fichiers indexés")
            
        except Exception as e:
            job.status = IndexerStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(e)
            logger.error(f"Job {job.id} échoué: {e}")
        
        finally:
            self._update_job_status(job)
            self._add_to_history(job)
            self.current_job = None
    
    def _get_queue_type(self, file_size: int) -> str:
        """Détermine le type de queue en fonction de la taille du fichier"""
        return 'slow' if file_size >= self.SLOW_THRESHOLD_BYTES else 'fast'

    def _index_path(self, job: IndexerJob):
        """Indexe récursivement un chemin"""
        from backend.src.crawl_utils import SMBClient, normalize_smb_path, get_file_info
        
        logger.info(f"Indexation de {job.path}")
        
        # Obtenir la config SMB pour ce chemin
        config = self._get_smb_config(job.config_id)
        if not config:
            raise ValueError(f"Configuration SMB introuvable pour {job.config_id}")
        
        # Créer le client SMB
        client = SMBClient(
            host=config['host'],
            share=config['share'],
            username=config['username'],
            password=config['password']
        )
        
        try:
            client.connect()
            
            # Parcourir récursivement
            remote_path = config.get('remote_path', '')
            self._crawl_recursive(client, remote_path, job, config)
            
        finally:
            client.disconnect()
    
    def _crawl_recursive(self, client, remote_path: str, job: IndexerJob, config: Dict):
        """Parcourt récursivement et indexe les fichiers"""
        from backend.src.crawl_utils import get_file_info
        
        try:
            entries = client.list_dir(remote_path)
            
            for entry in entries:
                if self._stop_event.is_set():
                    raise InterruptedError("Indexation interrompue")
                
                # Support les deux formats : dict (crawl_utils) et objets (smbprotocol)
                if isinstance(entry, dict):
                    entry_name = entry.get('name', '')
                    is_directory = entry.get('is_directory', False)
                else:
                    entry_name = getattr(entry, 'filename', '')
                    is_directory = getattr(entry, 'isDirectory', False)
                
                full_remote = f"{remote_path}/{entry_name}" if remote_path else entry_name
                
                if is_directory:
                    # Récursion dans les sous-dossiers
                    self._crawl_recursive(client, full_remote, job, config)
                else:
                    # Indexer le fichier
                    job.files_found += 1
                    
                    try:
                        file_info = get_file_info(client, full_remote)
                        
                        if not file_info:
                            continue
                        
                        file_size = file_info.get('size', 0)
                        
                        # Files différenciées : si le job est en mode slow et fichier fast,
                        # on l'indexe normalement. Si le fichier est slow et le job fast,
                        # on crée un sous-job dédié pour la queue lente.
                        file_queue_type = self._get_queue_type(file_size)
                        
                        if file_queue_type == 'slow' and self.slow_queue_enabled:
                            # Créer un job dédié pour les gros fichiers
                            self._create_slow_file_job(file_info, job)
                        else:
                            # Insérer directement pour les petits fichiers
                            self._insert_file(file_info, job.config_id)
                            job.files_indexed += 1
                            job.bytes_total += file_size
                        
                        # Mettre à jour les stats toutes les 100 fichiers
                        if job.files_found % 100 == 0:
                            self._update_job_progress(job)
                            logger.info(f"Progression job {job.id}: {job.files_found} fichiers trouvés")
                        
                    except Exception as e:
                        logger.warning(f"Erreur indexation fichier {full_remote}: {e}")
                        
        except Exception as e:
            logger.error(f"Erreur crawl {remote_path}: {e}")
            raise
    
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
    
    def _insert_file(self, file_info: Dict, config_id: str):
        """Insère un fichier dans la base de données"""
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
            db.insert_file(file_info, config_id)
            
        except Exception as e:
            logger.warning(f"Erreur insertion fichier: {e}")
    
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du worker"""
        return {
            "running": self.running,
            "current_job": self.get_current_job(),
            "history_count": len(self.jobs_history),
            "poll_interval": self.poll_interval,
            "slow_queue_enabled": self.slow_queue_enabled,
            "slow_threshold_bytes": self.SLOW_THRESHOLD_BYTES
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
