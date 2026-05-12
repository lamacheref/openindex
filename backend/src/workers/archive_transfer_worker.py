#!/usr/bin/env python3
"""
Archive Transfer Worker - Worker de transfert entre espaces SMB
T-ARCH-01: Worker de transfert dédié avec queue et retry
"""

import os
import sys
import time
import argparse
import threading
import hashlib
import shutil
import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import smbclient
from smbprotocol.exceptions import SMBConnectionClosed, SMBAuthenticationError


# Configuration du retry avec backoff exponentiel
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # secondes
DEFAULT_MAX_DELAY = 60.0  # secondes
DEFAULT_EXPONENTIAL_BASE = 2.0


def calculate_backoff_delay(
    retry_count: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exponential_base: float = DEFAULT_EXPONENTIAL_BASE,
    jitter: bool = True
) -> float:
    """
    Calcule le délai de retry avec backoff exponentiel et jitter.
    
    Formule: min(base_delay * (exponential_base ^ retry_count), max_delay)
    Avec jitter aléatoire pour éviter les thundering herds.
    
    Args:
        retry_count: Numéro de la tentative (0-indexed)
        base_delay: Délai de base en secondes
        max_delay: Délai maximum en secondes
        exponential_base: Base pour l'exponentiation
        jitter: Ajouter un jitter aléatoire
        
    Returns:
        Délai en secondes
    """
    # Calcul exponentiel
    delay = base_delay * (exponential_base ** retry_count)
    
    # Cap à max_delay
    delay = min(delay, max_delay)
    
    # Ajouter du jitter (±25% aléatoire) pour éviter les requêtes simultanées
    if jitter:
        jitter_factor = 0.75 + (random.random() * 0.5)  # 0.75 à 1.25
        delay *= jitter_factor
    
    return delay


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable_exceptions: tuple = (SMBConnectionClosed, SMBAuthenticationError, OSError)
):
    """
    Décorateur pour retry avec backoff exponentiel.
    
    Exemple:
        @retry_with_backoff(max_retries=3)
        def transfer_file(source, dest):
            # code qui peut échouer
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    
                    if attempt < max_retries:
                        delay = calculate_backoff_delay(
                            retry_count=attempt,
                            base_delay=base_delay,
                            max_delay=max_delay
                        )
                        
                        # Log le retry
                        func_name = getattr(func, '__name__', 'decorated_function')
                        if args and hasattr(args[0], 'logger'):
                            args[0].logger.warning(
                                f"â ï¸  {func_name} ï¿½chouï¿½ (tentative {attempt + 1}/{max_retries + 1}): {exc}"
                            )
                            args[0].logger.info(f"â³ï¸ Retry dans {delay:.2f}s...")
                        else:
                            print(f"â ï¸  {func_name} ï¿½chouï¿½ (tentative {attempt + 1}/{max_retries + 1}): {exc}")
                            print(f"â³ï¸ Retry dans {delay:.2f}s...")
                        
                        time.sleep(delay)
                    else:
                        # Dernière tentative échouée
                        func_name = getattr(func, '__name__', 'decorated_function')
                        if args and hasattr(args[0], 'logger'):
                            args[0].logger.error(
                                f"â  {func_name} ï¿½chouï¿½ aprï¿½s {max_retries + 1} tentatives: {exc}"
                            )
                        else:
                            print(f"â  {func_name} ï¿½chouï¿½ aprï¿½s {max_retries + 1} tentatives: {exc}")
                        raise last_exception
            
            raise last_exception
        
        return wrapper
    return decorator

# Ajouter le dossier src au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.src.database.postgres_adapter import PostgreSQLAdapter
from backend.src.core.logging_config import get_logger_manager


class TransferStatus(Enum):
    """Statuts possibles pour un transfert."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransferJob:
    """Représentation d'un job de transfert."""
    id: str
    job_type: str  # 'copy', 'move', 'delete'
    source_path: str
    dest_path: Optional[str]
    priority: int
    retry_count: int
    max_retries: int
    source_size: Optional[int] = None
    source_checksum: Optional[str] = None


class ArchiveTransferWorker:
    """
    Worker dédié pour les opérations de transfert entre espaces SMB.
    Consomme la queue archive_jobs et exécute les transferts avec retry.
    """

    def __init__(
        self,
        poll_interval: int = 5,
        max_concurrent: int = 3,
        chunk_size: int = 8192,  # 8KB pour transfert par chunks
        postgres_config: Optional[Dict] = None
    ):
        """
        Initialise le worker de transfert.

        Args:
            poll_interval: Intervalle de polling de la queue (secondes)
            max_concurrent: Nombre maximum de transferts parallèles
            chunk_size: Taille des chunks pour le transfert (bytes)
            postgres_config: Configuration PostgreSQL
        """
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.stop_event = threading.Event()
        self.active_transfers: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()

        # Configuration PostgreSQL
        self.postgres_config = postgres_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }

        # Initialiser PostgreSQL
        self.adapter = PostgreSQLAdapter(self.postgres_config)
        self.adapter.initialize_database()

        # Logging
        self.logger_manager = get_logger_manager()
        self.logger = self.logger_manager.get_logger("archive_transfer_worker")

        self.logger.info(f"🚀 Archive Transfer Worker initialisé")
        self.logger.info(f"   - Poll interval: {poll_interval}s")
        self.logger.info(f"   - Max concurrent: {max_concurrent}")
        self.logger.info(f"   - Chunk size: {chunk_size} bytes")

    def start(self) -> None:
        """Démarre le worker."""
        self.logger.info("▶️  Démarrage du Archive Transfer Worker...")
        self.stop_event.clear()

        # Thread principal pour consommer la queue
        self.main_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.main_thread.start()

        self.logger.info("✅ Worker démarré et prêt à traiter les jobs")

    def stop(self) -> None:
        """Arrête le worker proprement."""
        self.logger.info("🛑 Arrêt du worker demandé...")
        self.stop_event.set()

        # Attendre la fin des transferts actifs
        with self.lock:
            active_count = len(self.active_transfers)

        if active_count > 0:
            self.logger.info(f"⏳ Attente de {active_count} transferts actifs...")
            for job_id, thread in list(self.active_transfers.items()):
                thread.join(timeout=30)
                if thread.is_alive():
                    self.logger.warning(f"⚠️  Transfert {job_id} toujours actif après timeout")

        if self.main_thread.is_alive():
            self.main_thread.join(timeout=5)

        self.logger.info("✅ Worker arrêté")

    def _worker_loop(self) -> None:
        """Boucle principale du worker."""
        while not self.stop_event.is_set():
            try:
                # Vérifier combien de transferts sont actifs
                with self.lock:
                    active_count = len(self.active_transfers)

                if active_count < self.max_concurrent:
                    # Récupérer le prochain job
                    job = self._get_next_job()
                    if job:
                        self._start_transfer(job)

                # Attendre avant le prochain poll
                self.stop_event.wait(self.poll_interval)

            except Exception as exc:
                self.logger.error(f"❌ Erreur dans worker_loop: {exc}")
                self.stop_event.wait(5)  # Attendre plus longtemps en cas d'erreur

    def _get_next_job(self) -> Optional[TransferJob]:
        """Récupère le prochain job à traiter depuis la DB."""
        try:
            # Utiliser la fonction PostgreSQL pour récupérer et verrouiller le job
            result = self.adapter.execute_query(
                "SELECT * FROM get_next_archive_job()"
            )

            if result and len(result) > 0:
                row = result[0]
                job = TransferJob(
                    id=str(row[0]),
                    job_type=row[1],
                    source_path=row[2],
                    dest_path=row[3],
                    priority=row[4],
                    retry_count=row[5],  # current_retry_count from function
                    max_retries=3
                )
                self.logger.info(f"📦 Job récupéré: {job.id} ({job.job_type}) - {job.source_path}")
                return job

            return None

        except Exception as exc:
            self.logger.error(f"❌ Erreur récupération job: {exc}")
            return None

    def _start_transfer(self, job: TransferJob) -> None:
        """Démarre un transfert dans un thread séparé."""
        thread = threading.Thread(
            target=self._execute_transfer,
            args=(job,),
            name=f"transfer-{job.id[:8]}"
        )

        with self.lock:
            self.active_transfers[job.id] = thread

        thread.start()
        self.logger.info(f"🚀 Transfert démarré: {job.id}")

    def _execute_transfer(self, job: TransferJob) -> None:
        """Exécute le transfert d'un job."""
        start_time = time.time()
        success = False
        error_msg = None
        bytes_transferred = 0

        try:
            self.logger.info(f"▶️  Exécution job {job.id}: {job.job_type}")
            self.logger.info(f"   Source: {job.source_path}")
            if job.dest_path:
                self.logger.info(f"   Dest: {job.dest_path}")

            if job.job_type == 'copy':
                bytes_transferred = self._copy_file(job)
            elif job.job_type == 'move':
                bytes_transferred = self._move_file(job)
            elif job.job_type == 'delete':
                self._delete_file(job)
            else:
                raise ValueError(f"Type de job inconnu: {job.job_type}")

            success = True
            duration = time.time() - start_time
            self.logger.info(f"✅ Job {job.id} terminé en {duration:.2f}s")
            self.logger.info(f"   Bytes transférés: {bytes_transferred:,}")

        except Exception as exc:
            duration = time.time() - start_time
            error_msg = str(exc)
            self.logger.error(f"❌ Job {job.id} échoué après {duration:.2f}s: {error_msg}")

        finally:
            # Mettre à jour le statut dans la DB
            self._update_job_status(job.id, success, error_msg, bytes_transferred)

            # Retirer des transferts actifs
            with self.lock:
                self.active_transfers.pop(job.id, None)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _copy_file(self, job: TransferJob) -> int:
        """Copie un fichier via SMB avec suivi de progression et retry."""
        source_size = job.source_size or 0
        bytes_copied = 0

        self.logger.info(f"📄 Copie: {job.source_path} -> {job.dest_path}")

        # Ouvrir le fichier source
        with smbclient.open_file(job.source_path, mode='rb') as src:
            # Créer le fichier destination
            with smbclient.open_file(job.dest_path, mode='wb') as dst:
                while True:
                    chunk = src.read(self.chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    bytes_copied += len(chunk)

                    # Log de progression tous les 10MB
                    if bytes_copied % (10 * 1024 * 1024) < self.chunk_size:
                        progress = (bytes_copied / source_size * 100) if source_size > 0 else 0
                        self.logger.info(f"   Progress: {bytes_copied:,} bytes ({progress:.1f}%)")

        # Vérifier le checksum si disponible
        if job.source_checksum:
            self.logger.info(f"🔍 Vérification checksum...")
            dest_checksum = self._calculate_checksum(job.dest_path)
            if dest_checksum != job.source_checksum:
                raise ValueError(f"Checksum mismatch: source={job.source_checksum}, dest={dest_checksum}")
            self.logger.info(f"✅ Checksum OK: {dest_checksum[:16]}...")

        return bytes_copied

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _move_file(self, job: TransferJob) -> int:
        """Déplace un fichier (copie + suppression source) avec retry."""
        self.logger.info(f"📄 Déplacement: {job.source_path} -> {job.dest_path}")

        # Copier d'abord
        bytes_moved = self._copy_file(job)

        # Puis supprimer la source
        self.logger.info(f"🗑️  Suppression source: {job.source_path}")
        smbclient.remove(job.source_path)

        return bytes_moved

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _delete_file(self, job: TransferJob) -> int:
        """Supprime un fichier avec retry."""
        self.logger.info(f"🗑️  Suppression: {job.source_path}")
        smbclient.remove(job.source_path)
        return 0

    def _calculate_checksum(self, file_path: str) -> str:
        """Calcule le SHA256 d'un fichier SMB."""
        hash_sha256 = hashlib.sha256()
        with smbclient.open_file(file_path, mode='rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _update_job_status(
        self,
        job_id: str,
        success: bool,
        error_msg: Optional[str],
        bytes_transferred: int
    ) -> None:
        """Met à jour le statut du job dans la DB."""
        try:
            if success:
                self.adapter.execute_query(
                    """
                    UPDATE archive_jobs 
                    SET status = 'completed'::archive_job_status, 
                        completed_at = CURRENT_TIMESTAMP,
                        bytes_transferred = %s,
                        error_message = NULL,
                        retry_count = 0
                    WHERE id = %s
                    """,
                    (bytes_transferred, job_id)
                )
                self.logger.info(f"✅ Job {job_id} marqué comme completed")
            else:
                # Incrémenter retry_count et marquer failed ou retry
                new_retry_count = self.adapter.execute_query(
                    """
                    UPDATE archive_jobs 
                    SET retry_count = retry_count + 1,
                        status = CASE 
                            WHEN retry_count + 1 >= max_retries THEN 'failed'::archive_job_status
                            ELSE 'failed'::archive_job_status
                        END,
                        error_message = %s,
                        bytes_transferred = %s
                    WHERE id = %s
                    RETURNING retry_count, max_retries
                    """,
                    (error_msg, bytes_transferred, job_id)
                )

                if new_retry_count:
                    retry, max_r = new_retry_count[0]
                    if retry >= max_r:
                        self.logger.error(f"❌ Job {job_id} marqué comme failed (max retries atteint)")
                    else:
                        self.logger.info(f"🔄 Job {job_id} échoué, retry {retry}/{max_r}")

        except Exception as exc:
            self.logger.error(f"❌ Erreur mise à jour statut job {job_id}: {exc}")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du worker."""
        try:
            result = self.adapter.execute_query(
                "SELECT * FROM archive_jobs_stats"
            )

            stats = {"active_transfers": len(self.active_transfers)}
            for row in result:
                status, count, total_size = row
                stats[status] = {"count": count, "total_size": total_size}

            return stats

        except Exception as exc:
            self.logger.error(f"❌ Erreur récupération stats: {exc}")
            return {"error": str(exc)}


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Archive Transfer Worker")
    parser.add_argument("--poll-interval", type=int, default=5, help="Intervalle de polling (s)")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Transferts parallèles max")
    parser.add_argument("--chunk-size", type=int, default=8192, help="Taille des chunks (bytes)")
    args = parser.parse_args()

    worker = ArchiveTransferWorker(
        poll_interval=args.poll_interval,
        max_concurrent=args.max_concurrent,
        chunk_size=args.chunk_size
    )

    try:
        worker.start()

        # Boucle principale pour afficher les stats
        while True:
            time.sleep(60)
            stats = worker.get_stats()
            print(f"\n📊 Stats: {stats}\n")

    except KeyboardInterrupt:
        print("\n🛑 Interruption par l'utilisateur")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
