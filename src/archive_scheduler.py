"""
Archive Scheduler - Gestionnaire de tâches planifiées d'archivage (T-ARCH-02)
Permet le scheduling des jobs via configuration cron
"""

import os
import re
import time
import threading
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from croniter import croniter

from postgres_adapter import PostgreSQLAdapter
from logger_manager import get_logger_manager


@dataclass
class ScheduleConfig:
    """Configuration d'une tâche planifiée"""
    id: str
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    is_active: bool
    job_type: str  # 'copy', 'move', 'delete'
    source_pattern: str
    dest_path: Optional[str]
    priority: int
    max_age_days: Optional[int]
    min_size_bytes: Optional[int]
    max_size_bytes: Optional[int]
    file_extensions: Optional[List[str]]
    next_run_at: Optional[datetime]


class ArchiveScheduler:
    """
    Gestionnaire de scheduling pour les jobs d'archivage automatique.
    Supporte les expressions cron standard et exécute les jobs périodiquement.
    """

    def __init__(self, poll_interval: int = 60, postgres_config: Optional[Dict] = None):
        """
        Initialise le scheduler.
        
        Args:
            poll_interval: Intervalle de vérification des schedules (secondes)
            postgres_config: Configuration PostgreSQL
        """
        self.poll_interval = poll_interval
        self.stop_event = threading.Event()
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # Configuration PostgreSQL
        self.postgres_config = postgres_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        
        self.adapter = PostgreSQLAdapter(self.postgres_config)
        self.adapter.initialize_database()
        
        # Logging
        self.logger_manager = get_logger_manager()
        self.logger = self.logger_manager.get_logger("archive_scheduler")
        
        self.logger.info(f"📅 Archive Scheduler initialisé")
        self.logger.info(f"   - Poll interval: {poll_interval}s")
        
        # Appliquer les migrations si nécessaire
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Vérifie et crée les tables nécessaires"""
        try:
            # Vérifier si la table archive_schedules existe
            result = self.adapter.execute_query(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'archive_schedules')",
                fetch=True
            )
            if result and not result[0][0]:
                self.logger.warning("⚠️  Table archive_schedules non trouvée. Exécutez la migration 002.")
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification schema: {e}")
    
    def start(self) -> None:
        """Démarre le scheduler"""
        self.logger.info("▶️  Démarrage de l'Archive Scheduler...")
        self.stop_event.clear()
        
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("✅ Scheduler démarré")
    
    def stop(self) -> None:
        """Arrête le scheduler"""
        self.logger.info("🛑 Arrêt du scheduler...")
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("✅ Scheduler arrêté")
    
    def _scheduler_loop(self) -> None:
        """Boucle principale du scheduler"""
        while not self.stop_event.is_set():
            try:
                self._check_and_run_schedules()
                self.stop_event.wait(self.poll_interval)
            except Exception as e:
                self.logger.error(f"❌ Erreur dans scheduler_loop: {e}")
                self.stop_event.wait(5)
    
    def _check_and_run_schedules(self) -> None:
        """Vérifie et exécute les schedules dus"""
        try:
            # Récupérer les schedules actifs dont le next_run_at est passé
            schedules = self.adapter.execute_query(
                """
                SELECT id, name, description, cron_expression, timezone, job_type,
                       source_pattern, dest_path, priority, max_age_days,
                       min_size_bytes, max_size_bytes, file_extensions
                FROM archive_schedules
                WHERE is_active = true
                  AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP)
                ORDER BY priority ASC
                """,
                fetch=True
            )
            
            if not schedules:
                return
            
            self.logger.info(f"📅 {len(schedules)} schedule(s) à exécuter")
            
            for row in schedules:
                config = ScheduleConfig(
                    id=str(row[0]),
                    name=row[1],
                    description=row[2],
                    cron_expression=row[3],
                    timezone=row[4],
                    is_active=True,
                    job_type=row[5],
                    source_pattern=row[6],
                    dest_path=row[7],
                    priority=row[8],
                    max_age_days=row[9],
                    min_size_bytes=row[10],
                    max_size_bytes=row[11],
                    file_extensions=row[12],
                    next_run_at=None
                )
                
                self._execute_schedule(config)
                
                # Mettre à jour le next_run_at
                next_run = self._calculate_next_run(config.cron_expression, config.timezone)
                self.adapter.execute_query(
                    """
                    UPDATE archive_schedules
                    SET last_run_at = CURRENT_TIMESTAMP,
                        next_run_at = %s,
                        run_count = run_count + 1
                    WHERE id = %s
                    """,
                    (next_run, config.id),
                    fetch=False
                )
                
        except Exception as e:
            self.logger.error(f"❌ Erreur check_and_run_schedules: {e}")
    
    def _execute_schedule(self, config: ScheduleConfig) -> None:
        """Exécute un schedule et crée les jobs correspondants"""
        self.logger.info(f"▶️  Exécution du schedule: {config.name} ({config.id})")
        
        try:
            # Créer un record de run
            run_result = self.adapter.execute_query(
                """
                INSERT INTO archive_schedule_runs (schedule_id, status)
                VALUES (%s, 'running')
                RETURNING id
                """,
                (config.id,),
                fetch=True
            )
            run_id = run_result[0][0] if run_result else None
            
            # Rechercher les fichiers correspondants
            files = self._find_matching_files(config)
            
            jobs_created = 0
            
            for file_info in files:
                try:
                    # Créer un job d'archivage
                    dest = self._resolve_dest_path(config, file_info)
                    
                    self.adapter.execute_query(
                        """
                        INSERT INTO archive_jobs (
                            job_type, source_path, dest_path, status, priority,
                            retry_count, max_retries, source_size, created_at
                        ) VALUES (
                            %s::archive_job_type, %s, %s, 'pending', %s,
                            0, 3, %s, CURRENT_TIMESTAMP
                        )
                        """,
                        (
                            config.job_type,
                            file_info['path'],
                            dest,
                            config.priority,
                            file_info.get('size', 0)
                        ),
                        fetch=False
                    )
                    jobs_created += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Erreur création job pour {file_info['path']}: {e}")
            
            # Mettre à jour le statut du run
            if run_id:
                self.adapter.execute_query(
                    """
                    UPDATE archive_schedule_runs
                    SET status = 'completed',
                        completed_at = CURRENT_TIMESTAMP,
                        jobs_created = %s
                    WHERE id = %s
                    """,
                    (jobs_created, run_id),
                    fetch=False
                )
            
            self.logger.info(f"✅ Schedule {config.name}: {jobs_created} job(s) créé(s)")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur exécution schedule {config.id}: {e}")
            # Marquer le run comme échoué
            if run_id:
                self.adapter.execute_query(
                    """
                    UPDATE archive_schedule_runs
                    SET status = 'failed',
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = %s
                    WHERE id = %s
                    """,
                    (str(e)[:1000], run_id),
                    fetch=False
                )
    
    def _find_matching_files(self, config: ScheduleConfig) -> List[Dict[str, Any]]:
        """Recherche les fichiers correspondant aux critères du schedule"""
        files = []
        
        try:
            # Construire la requête dynamique
            where_clauses = []
            params = []
            
            # Pattern de source (chemin de départ)
            where_clauses.append("path LIKE %s")
            # Extraire le préfixe du pattern (avant les wildcards)
            prefix = config.source_pattern.split('*')[0].split('?')[0]
            params.append(f"{prefix}%")
            
            # Filtre par âge
            if config.max_age_days:
                where_clauses.append("last_modified <= CURRENT_TIMESTAMP - INTERVAL '%s days'")
                params.append(config.max_age_days)
            
            # Filtre par taille
            if config.min_size_bytes:
                where_clauses.append("size >= %s")
                params.append(config.min_size_bytes)
            
            if config.max_size_bytes:
                where_clauses.append("size <= %s")
                params.append(config.max_size_bytes)
            
            # Filtre par extension
            if config.file_extensions:
                ext_placeholders = ','.join(['%s'] * len(config.file_extensions))
                where_clauses.append(f"name ILIKE ANY(ARRAY[{ext_placeholders}])")
                for ext in config.file_extensions:
                    params.append(f"%.{ext}")
            
            # Exclure les répertoires
            where_clauses.append("is_directory = false")
            
            query = f"""
                SELECT path, name, size, last_modified, checksum
                FROM files
                WHERE {' AND '.join(where_clauses)}
                LIMIT 1000
            """
            
            results = self.adapter.execute_query(query, params, fetch=True)
            
            # Filtrer avec le pattern complet (regex/glob)
            pattern = config.source_pattern.replace('*', '.*').replace('?', '.')
            regex = re.compile(pattern, re.IGNORECASE)
            
            for row in results:
                path = row[0]
                if regex.search(path):
                    files.append({
                        'path': path,
                        'name': row[1],
                        'size': row[2],
                        'last_modified': row[3],
                        'checksum': row[4]
                    })
            
            self.logger.info(f"🔍 {len(files)} fichier(s) trouvé(s) pour {config.name}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur recherche fichiers: {e}")
        
        return files
    
    def _resolve_dest_path(self, config: ScheduleConfig, file_info: Dict[str, Any]) -> Optional[str]:
        """Résout le chemin de destination pour un fichier"""
        if config.job_type == 'delete':
            return None
        
        if not config.dest_path:
            return None
        
        # Si le dest_path se termine par / ou \, c'est un répertoire
        if config.dest_path.endswith(('/', '\\')):
            filename = os.path.basename(file_info['path'])
            return os.path.join(config.dest_path, filename)
        
        return config.dest_path
    
    def _calculate_next_run(self, cron_expression: str, timezone: str = 'Europe/Paris') -> datetime:
        """Calcule la prochaine exécution à partir d'une expression cron"""
        try:
            if croniter.is_valid(cron_expression):
                itr = croniter(cron_expression, datetime.now(timezone.utc))
                return itr.get_next(datetime)
        except Exception:
            pass
        
        # Fallback: dans 1 heure
        return datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=1)
    
    def create_schedule(self, config: Dict[str, Any]) -> str:
        """Crée un nouveau schedule"""
        try:
            result = self.adapter.execute_query(
                """
                INSERT INTO archive_schedules (
                    name, description, cron_expression, timezone, is_active,
                    job_type, source_pattern, dest_path, priority, max_age_days,
                    min_size_bytes, max_size_bytes, file_extensions, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s::archive_job_type, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    config['name'],
                    config.get('description'),
                    config['cron_expression'],
                    config.get('timezone', 'Europe/Paris'),
                    config.get('is_active', True),
                    config['job_type'],
                    config['source_pattern'],
                    config.get('dest_path'),
                    config.get('priority', 5),
                    config.get('max_age_days'),
                    config.get('min_size_bytes'),
                    config.get('max_size_bytes'),
                    config.get('file_extensions', []),
                    config.get('created_by', 'system')
                ),
                fetch=True
            )
            
            schedule_id = str(result[0][0])
            
            # Calculer et mettre à jour le next_run_at
            next_run = self._calculate_next_run(config['cron_expression'], config.get('timezone', 'Europe/Paris'))
            self.adapter.execute_query(
                "UPDATE archive_schedules SET next_run_at = %s WHERE id = %s",
                (next_run, schedule_id),
                fetch=False
            )
            
            self.logger.info(f"✅ Schedule créé: {config['name']} ({schedule_id})")
            return schedule_id
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création schedule: {e}")
            raise
    
    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour un schedule existant"""
        try:
            # Construire la requête dynamique
            allowed_fields = [
                'name', 'description', 'cron_expression', 'timezone', 'is_active',
                'job_type', 'source_pattern', 'dest_path', 'priority', 'max_age_days',
                'min_size_bytes', 'max_size_bytes', 'file_extensions'
            ]
            
            set_clauses = []
            params = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            params.append(schedule_id)
            
            query = f"""
                UPDATE archive_schedules
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
            """
            
            result = self.adapter.execute_query(query, params, fetch=True)
            
            if result:
                self.logger.info(f"✅ Schedule mis à jour: {schedule_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erreur mise à jour schedule {schedule_id}: {e}")
            return False
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Supprime un schedule"""
        try:
            result = self.adapter.execute_query(
                "DELETE FROM archive_schedules WHERE id = %s RETURNING id",
                (schedule_id,),
                fetch=True
            )
            
            if result:
                self.logger.info(f"✅ Schedule supprimé: {schedule_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erreur suppression schedule {schedule_id}: {e}")
            return False
    
    def get_schedules(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Récupère la liste des schedules"""
        try:
            where_clause = "WHERE is_active = true" if active_only else ""
            
            results = self.adapter.execute_query(
                f"""
                SELECT id, name, description, cron_expression, timezone, is_active,
                       job_type, source_pattern, dest_path, priority, max_age_days,
                       min_size_bytes, max_size_bytes, file_extensions,
                       created_at, last_run_at, next_run_at, run_count
                FROM archive_schedules
                {where_clause}
                ORDER BY is_active DESC, priority ASC, name ASC
                """,
                fetch=True
            )
            
            schedules = []
            for row in results:
                schedules.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'cron_expression': row[3],
                    'timezone': row[4],
                    'is_active': row[5],
                    'job_type': row[6],
                    'source_pattern': row[7],
                    'dest_path': row[8],
                    'priority': row[9],
                    'max_age_days': row[10],
                    'min_size_bytes': row[11],
                    'max_size_bytes': row[12],
                    'file_extensions': row[13],
                    'created_at': row[14],
                    'last_run_at': row[15],
                    'next_run_at': row[16],
                    'run_count': row[17]
                })
            
            return schedules
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération schedules: {e}")
            return []
    
    def get_schedule_runs(self, schedule_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère l'historique des exécutions"""
        try:
            where_clause = "WHERE schedule_id = %s" if schedule_id else ""
            params = (schedule_id,) if schedule_id else ()
            
            results = self.adapter.execute_query(
                f"""
                SELECT r.id, r.schedule_id, s.name as schedule_name, r.started_at,
                       r.completed_at, r.status, r.jobs_created, r.jobs_completed,
                       r.jobs_failed, r.total_bytes_processed, r.error_message
                FROM archive_schedule_runs r
                LEFT JOIN archive_schedules s ON r.schedule_id = s.id
                {where_clause}
                ORDER BY r.started_at DESC
                LIMIT %s
                """,
                params + (limit,),
                fetch=True
            )
            
            runs = []
            for row in results:
                runs.append({
                    'id': str(row[0]),
                    'schedule_id': str(row[1]) if row[1] else None,
                    'schedule_name': row[2],
                    'started_at': row[3],
                    'completed_at': row[4],
                    'status': row[5],
                    'jobs_created': row[6],
                    'jobs_completed': row[7],
                    'jobs_failed': row[8],
                    'total_bytes_processed': row[9],
                    'error_message': row[10]
                })
            
            return runs
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération runs: {e}")
            return []
    
    def get_settings(self) -> Dict[str, str]:
        """Récupère les paramètres d'archivage"""
        try:
            results = self.adapter.execute_query(
                "SELECT key, value FROM archive_settings ORDER BY key",
                fetch=True
            )
            return {row[0]: row[1] for row in results}
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération settings: {e}")
            return {}
    
    def update_setting(self, key: str, value: str, updated_by: str = 'system') -> bool:
        """Met à jour un paramètre"""
        try:
            self.adapter.execute_query(
                """
                INSERT INTO archive_settings (key, value, updated_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, updated_by),
                fetch=False
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Erreur mise à jour setting {key}: {e}")
            return False


def main():
    """Point d'entrée pour exécuter le scheduler en standalone"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Archive Scheduler")
    parser.add_argument("--poll-interval", type=int, default=60, help="Intervalle de polling (s)")
    parser.add_argument("--run-once", action="store_true", help="Exécute une fois et quitte")
    args = parser.parse_args()
    
    scheduler = ArchiveScheduler(poll_interval=args.poll_interval)
    
    if args.run_once:
        scheduler._check_and_run_schedules()
    else:
        scheduler.start()
        
        try:
            while True:
                time.sleep(60)
                stats = scheduler.get_schedules(active_only=True)
                print(f"\n📅 Schedules actifs: {len(stats)}\n")
        except KeyboardInterrupt:
            print("\n🛑 Interruption par l'utilisateur")
        finally:
            scheduler.stop()


if __name__ == "__main__":
    main()
