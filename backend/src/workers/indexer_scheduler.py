"""
Indexer Scheduler - Gestionnaire de tâches planifiées d'indexation (T-INDEX-01)
Permet le scheduling des jobs d'indexation via configuration cron
"""

import os
import re
import time
import uuid
import threading
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("indexer.scheduler")


@dataclass
class IndexerScheduleConfig:
    """Configuration d'une tâche d'indexation planifiée"""
    id: str
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    is_active: bool
    config_id: Optional[str]
    priority: int
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    run_count: int


class IndexerScheduler:
    """
    Gestionnaire de scheduling pour l'indexation automatique.
    
    - Vérifie périodiquement les schedules dont next_run_at est dépassé
    - Crée les jobs d'indexation correspondants
    - Met à jour les dates de prochain run
    """
    
    def __init__(self, poll_interval: int = 60):
        """
        Initialise le scheduler.
        
        Args:
            poll_interval: Intervalle de vérification des schedules (secondes)
        """
        self.poll_interval = poll_interval
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stats = {
            "checks": 0,
            "jobs_created": 0,
            "errors": 0,
            "last_check": None
        }
        
        logger.info(f"IndexerScheduler initialisé (poll={poll_interval}s)")
    
    def start(self):
        """Démarre le scheduler dans un thread séparé"""
        if self._running:
            logger.warning("Scheduler déjà en cours d'exécution")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler d'indexation démarré")
    
    def stop(self):
        """Arrête le scheduler proprement"""
        if not self._running:
            return
        
        logger.info("Arrêt du scheduler demandé...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=30)
        
        logger.info("Scheduler arrêté")
    
    def _run_loop(self):
        """Boucle principale de vérification des schedules"""
        logger.info("Boucle principale du scheduler démarrée")
        
        while self._running and not self._stop_event.is_set():
            try:
                self._check_schedules()
                self._stop_event.wait(self.poll_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle scheduler: {e}", exc_info=True)
                self._stop_event.wait(self.poll_interval)
        
        logger.info("Boucle principale du scheduler terminée")
    
    def _check_schedules(self):
        """Vérifie les schedules et crée les jobs si nécessaire"""
        db = self._get_db()
        if not db:
            return
        
        try:
            with self._lock:
                self._stats["checks"] += 1
                self._stats["last_check"] = datetime.now(timezone.utc).isoformat()
            
            # Récupérer les schedules actifs dont next_run_at est dépassé
            schedules = self._fetch_due_schedules(db)
            
            for schedule in schedules:
                try:
                    self._execute_schedule(db, schedule)
                except Exception as e:
                    logger.error(f"Erreur exécution schedule {schedule.name}: {e}")
                    with self._lock:
                        self._stats["errors"] += 1
            
        except Exception as e:
            logger.error(f"Erreur vérification schedules: {e}")
    
    def _fetch_due_schedules(self, db) -> List[IndexerScheduleConfig]:
        """Récupère les schedules dont l'exécution est due"""
        try:
            results = db.execute_query(
                """
                SELECT id::text, name, description, cron_expression, timezone,
                       is_active, config_id::text, priority,
                       next_run_at, last_run_at, run_count
                FROM indexer_schedules
                WHERE is_active = true
                  AND next_run_at <= CURRENT_TIMESTAMP
                ORDER BY priority ASC, next_run_at ASC
                LIMIT 10
                """
            )
            
            schedules = []
            for row in results:
                schedules.append(IndexerScheduleConfig(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    cron_expression=row[3],
                    timezone=row[4],
                    is_active=row[5],
                    config_id=row[6],
                    priority=row[7],
                    next_run_at=row[8],
                    last_run_at=row[9],
                    run_count=row[10]
                ))
            
            return schedules
            
        except Exception as e:
            logger.error(f"Erreur récupération schedules: {e}")
            return []
    
    def _execute_schedule(self, db, schedule: IndexerScheduleConfig):
        """
        Exécute un schedule : crée les jobs d'indexation et met à jour les dates.
        
        Si config_id est NULL, crée un job pour chaque configuration active.
        Sinon, crée un job pour la configuration spécifiée.
        """
        configs = self._get_configs_for_schedule(db, schedule)
        
        if not configs:
            logger.warning(f"Aucune config trouvée pour le schedule {schedule.name}")
            return
        
        jobs_created = 0
        for config in configs:
            try:
                job_id = str(uuid.uuid4())
                db.execute_query(
                    """
                    INSERT INTO indexer_jobs (id, path, config_id, config_name, status, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
                    """,
                    [job_id, config['start_path'], config['id'], config['name']],
                    fetch=False
                )
                jobs_created += 1
                logger.info(f"Job créé via scheduler: {job_id} pour {config['name']}")
                
            except Exception as e:
                logger.error(f"Erreur création job pour {config['name']}: {e}")
        
        # Mettre à jour les statistiques du schedule
        try:
            db.execute_query(
                """
                UPDATE indexer_schedules
                SET last_run_at = CURRENT_TIMESTAMP,
                    next_run_at = calculate_indexer_next_run(cron_expression, timezone),
                    run_count = run_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id::text = %s
                """,
                [schedule.id],
                fetch=False
            )
        except Exception as e:
            logger.error(f"Erreur mise à jour schedule {schedule.name}: {e}")
        
        with self._lock:
            self._stats["jobs_created"] += jobs_created
        
        logger.info(f"Schedule {schedule.name}: {jobs_created} job(s) créé(s)")
    
    def _get_configs_for_schedule(self, db, schedule: IndexerScheduleConfig) -> List[Dict[str, Any]]:
        """
        Récupère les configurations de crawl pour un schedule.
        
        Si schedule.config_id est défini, retourne uniquement cette config.
        Sinon, retourne toutes les configurations actives.
        """
        try:
            if schedule.config_id:
                config = db.get_crawl_config_by_id(schedule.config_id)
                return [config] if config else []
            else:
                # Toutes les configurations actives
                return db.list_crawl_configs() if hasattr(db, 'list_crawl_configs') else []
                
        except Exception as e:
            logger.error(f"Erreur récupération configs: {e}")
            return []
    
    def _get_db(self):
        """Retourne l'adaptateur de base de données"""
        try:
            from backend.src.database.postgres_adapter import PostgreSQLAdapter
            
            config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'openindex'),
                'user': os.getenv('POSTGRES_USER', 'openindex_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
            }
            return PostgreSQLAdapter(config)
            
        except Exception as e:
            logger.error(f"Erreur connexion DB scheduler: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du scheduler"""
        with self._lock:
            return dict(self._stats)
    
    def force_check(self) -> int:
        """Déclenche une vérification immédiate et retourne le nombre de jobs créés"""
        old_count = self._stats["jobs_created"]
        self._check_schedules()
        return self._stats["jobs_created"] - old_count


# Instance globale du scheduler
_scheduler_instance: Optional[IndexerScheduler] = None


def get_scheduler() -> IndexerScheduler:
    """Retourne l'instance globale du scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = IndexerScheduler()
    return _scheduler_instance


def start_scheduler():
    """Démarre le scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Arrête le scheduler"""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None


if __name__ == "__main__":
    # Mode standalone pour tests
    print("Starting Indexer Scheduler standalone...")
    scheduler = start_scheduler()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        stop_scheduler()
        print("Scheduler stopped.")