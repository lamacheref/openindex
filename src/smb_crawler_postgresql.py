#!/usr/bin/env python3
"""
Crawler SMB avec PostgreSQL direct
Version modifiée pour utiliser PostgreSQL au lieu de SQLite
"""

import os
import sys
import hashlib
import time
import argparse
import threading
import subprocess
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import smbclient
import pytz
from logging_config import get_logger_manager
from postgres_adapter import PostgreSQLAdapter
from config_manager import ConfigManager


class SMBCrawlerPostgreSQL:
    """Classe principale pour le crawler SMB avec PostgreSQL."""

    def __init__(self, server, username, password, share_name, domain='',
                 crawl_config_id=None, postgres_config=None, max_workers=4, delay_between_requests=0.1,
                 max_queue_size=1000, max_depth=None, debug=False,
                 large_file_threshold=104857600, pre_estimation_enabled=True,
                 pre_estimation_mode="smb", pre_estimation_mount_path="",
                 pre_estimated_total_size=0):
        """
        Initialise le crawler SMB avec PostgreSQL.

        Args:
            server (str): Adresse du serveur SMB.
            username (str): Nom d'utilisateur pour la connexion.
            password (str): Mot de passe pour la connexion.
            share_name (str): Nom du partage SMB à parcourir.
            domain (str): Domaine pour la connexion.
            postgres_config (dict): Configuration PostgreSQL.
            max_workers (int): Nombre de workers parallèles.
            delay_between_requests (float): Délai entre les requêtes.
            max_queue_size (int): Taille maximale des queues.
            max_depth (int): Profondeur maximale de crawl.
            debug (bool): Active le mode debug.
            large_file_threshold (int): Seuil pour les gros fichiers.
        """
        self.server = server
        self.username = username
        self.password = password
        self.share_name = share_name
        self.domain = domain
        self.crawl_config_id = crawl_config_id
        self.run_id = None
        self.postgres_config = postgres_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        self.max_workers = max_workers
        self.delay_between_requests = delay_between_requests
        self.max_queue_size = max_queue_size
        self.max_depth = max_depth
        self.debug = debug
        self.large_file_threshold = large_file_threshold
        self.pre_estimation_enabled = pre_estimation_enabled
        self.pre_estimation_mode = (pre_estimation_mode or "smb").strip().lower()
        self.pre_estimation_mount_path = (pre_estimation_mount_path or "").strip()
        self.pre_estimated_total_size = int(pre_estimated_total_size or 0)
        
        # Initialiser PostgreSQL
        self.postgres_adapter = PostgreSQLAdapter(self.postgres_config)
        self.postgres_adapter.initialize_database()
        
        # Patterns de fichiers à exclure
        self.exclude_patterns = ['~$', '.tmp', '.lock', '.lnk', 'Thumbs.db', 'desktop.ini']
        
        # Cache des répertoires avec accès refusé
        self.denied_directories = set()
        
        # Queues pour le traitement parallèle
        self.directory_queue = Queue()  # Queue pour les répertoires à traiter
        self.directory_result_queue = Queue()  # Queue pour les répertoires traités
        self.file_queue = Queue()
        self.large_file_queue = Queue()  # Queue séparée pour les gros fichiers
        self.result_queue = Queue()
        
        # Événement pour arrêter le crawler
        self.stop_event = threading.Event()
        self.user_cancelled = False  # Flag pour distinguer cancellation utilisateur vs fin normale
        self.activity_lock = threading.Lock()
        self.active_tasks = {
            'directories': 0,
            'directory_results': 0,
            'files': 0,
            'large_files': 0,
            'results': 0,
        }
        
        # Statistiques
        self.stats = {
            'total_directories': 0,
            'total_files': 0,
            'total_size': 0,
            'processed_size': 0,
            'large_files': 0,  # Nouveau: compteur de gros fichiers
            'duplicate_files': 0,
            'duplicate_size': 0,
            'estimated_total_size': 0,
            'estimated_total_files': 0,
            'estimated_total_directories': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
            'last_activity': None,
            'timed_out': False,
            'final_status': 'running',
            'phase': 'idle',
        }
        
        # Configuration du logging
        self.setup_logging()

        if self.pre_estimated_total_size > 0:
            self.stats['estimated_total_size'] = self.pre_estimated_total_size
        self.last_completed_crawl_triggered_at = None
        self.pause_requested = False
        self.base_path = None

    def setup_logging(self):
        """Configure le logging avec rotation automatique."""
        self.logger_manager = get_logger_manager()
        self.logger = self.logger_manager.get_logger("smb_crawler_postgresql")

    @contextmanager
    def _track_active_task(self, task_type):
        """Suit le travail en cours pour éviter les fins de crawl prématurées."""
        with self.activity_lock:
            self.active_tasks[task_type] += 1
        try:
            yield
        finally:
            with self.activity_lock:
                self.active_tasks[task_type] -= 1

    def _has_active_work(self):
        with self.activity_lock:
            return any(count > 0 for count in self.active_tasks.values())

    def should_stop_requested_run(self):
        if not self.run_id:
            return False
        try:
            status = self.postgres_adapter.get_crawl_run_status(self.run_id)
        except Exception as exc:
            self.logger.warning(f"Impossible de verifier le statut du run {self.run_id}: {exc}")
            return False
        return (status or "").lower() == "cancelling"

    def should_pause_requested_run(self):
        if not self.run_id:
            return False
        try:
            status = self.postgres_adapter.get_crawl_run_status(self.run_id)
        except Exception as exc:
            self.logger.warning(f"Impossible de verifier le statut du run {self.run_id}: {exc}")
            return False
        return (status or "").lower() == "pending"

    def setup_smb_credentials(self):
        """Configure smbclient avec les informations d'identification fournies."""
        smbclient.ClientConfig(
            username=self.username,
            password=self.password,
            domain=self.domain
        )

    def should_exclude_file(self, file_name):
        """
        Vérifie si un fichier doit être exclu du crawl.
        
        Args:
            file_name (str): Nom du fichier à vérifier.
            
        Returns:
            tuple: (should_exclude, reason)
        """
        # Vérifier les patterns d'exclusion
        for pattern in self.exclude_patterns:
            if pattern in file_name:
                return True, f"Fichier exclu (pattern: {pattern})"
        
        # Vérifier les fichiers temporaires Office
        if file_name.startswith('~$') and file_name.endswith('.tmp'):
            return True, "Fichier temporaire Office"
        
        # Vérifier les fichiers système Windows
        if file_name in ['Thumbs.db', 'desktop.ini']:
            return True, "Fichier système Windows"
        
        return False, None

    def _get_path_depth(self, path):
        """Retourne la profondeur relative à la racine du partage."""
        root_prefix = rf"\\{self.server}\{self.share_name}"
        if not path.startswith(root_prefix):
            return 0
        relative_path = path[len(root_prefix):].strip("\\")
        if not relative_path:
            return 0
        return relative_path.count("\\")

    def list_directory_fallback(self, unc_path):
        """
        Méthode de secours utilisant smbclient en ligne de commande
        quand la bibliothèque Python échoue.
        """
        try:
            # Extraire les composants du chemin UNC
            parts = unc_path.replace('\\\\', '').split('\\')
            server = parts[0]
            share = parts[1]
            subdir = '\\'.join(parts[2:]) if len(parts) > 2 else ''
            
            # Construire la commande smbclient
            if subdir:
                cmd = f'cd "{subdir}" && ls'
            else:
                cmd = 'ls'
            
            smb_cmd = [
                'smbclient',
                f'//{server}/{share}',
                '-U', f'{self.username}%{self.password}',
                '-W', self.domain,
                '-c', cmd
            ]
            
            # Exécuter la commande
            result = subprocess.run(
                smb_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return self._parse_smbclient_output(result.stdout, unc_path)
            else:
                self.logger.error(f"smbclient fallback failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur dans list_directory_fallback: {e}")
            return None

    def _parse_smbclient_output(self, output, base_path):
        """
        Parse la sortie de smbclient pour extraire les fichiers et répertoires.
        """
        items = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('  .') or line.startswith('  ..'):
                continue
            
            # Parser le format:  type  size  date  time  name
            parts = line.split()
            if len(parts) >= 4:
                name = parts[-1]
                size_str = parts[-3] if parts[-3].isdigit() else '0'
                
                # Déterminer si c'est un répertoire
                is_directory = line.startswith('  D')
                
                # Construire le chemin complet
                if base_path == f'\\\\{self.server}\\{self.share_name}':
                    full_path = f'{base_path}\\{name}'
                else:
                    full_path = f'{base_path}\\{name}'
                
                # Créer les métadonnées
                file_data = {
                    'path': full_path,
                    'name': name,
                    'size': int(size_str) if size_str.isdigit() else 0,
                    'is_directory': is_directory,
                    'crawl_config_id': self.crawl_config_id,
                    'last_modified': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                items.append(file_data)
        
        return items

    def _list_directory_entries(self, current_path):
        try:
            self.setup_smb_credentials()
            item_names = smbclient.listdir(current_path)
            items = []
            for item_name in item_names:
                item_path = f"{current_path}\\{item_name}"
                stat_result = smbclient.stat(item_path)
                items.append({
                    'path': item_path,
                    'name': item_name,
                    'size': stat_result.st_size,
                    'is_directory': stat_result.st_mode & 0o040000 == 0o040000,
                    'crawl_config_id': self.crawl_config_id,
                    'last_modified': datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
            return items
        except Exception as e:
            self.logger.warning(f"Erreur listing {current_path}: {e}")
            items = self.list_directory_fallback(current_path)
            if items is None:
                self.logger.error(f"Échec complet pour {current_path}")
                self.stats['errors'] += 1
                return []
            return items

    def _run_pre_estimation(self, base_path):
        self.stats['phase'] = 'pre_estimation'
        started_at = time.time()
        self.stats['last_activity'] = time.time()

        if self.pre_estimation_mode == "du":
            if self._run_du_pre_estimation(base_path):
                return
            self.logger.warning("⚠️ Pré-estimation `du -sb` indisponible, fallback SMB activé")

        pending_directories = [base_path]
        estimated_directories = 1
        estimated_files = 0
        estimated_total_size = 0
        scanned_directories = 0

        self.logger.info("🔎 Pré-estimation démarrée")

        while pending_directories and not self.stop_event.is_set():
            current_path = pending_directories.pop(0)
            self.stats['last_activity'] = time.time()
            scanned_directories += 1

            items = self._list_directory_entries(current_path)
            for item_data in items:
                if item_data['is_directory']:
                    current_depth = self._get_path_depth(item_data['path'])
                    if self.max_depth is None or current_depth < self.max_depth:
                        pending_directories.append(item_data['path'])
                    estimated_directories += 1
                    continue

                should_exclude, _reason = self.should_exclude_file(item_data['name'])
                if should_exclude:
                    continue

                estimated_files += 1
                estimated_total_size += item_data['size']

            if scanned_directories == 1 or scanned_directories % 50 == 0:
                duration = time.time() - started_at
                self.logger.info(
                    f"🔎 Pré-estimation: {estimated_files} fichiers, {estimated_directories} dossiers | "
                    f"Volume cible={estimated_total_size} octets | Dossiers restants={len(pending_directories)} | "
                    f"Durée: {duration:.1f}s | Erreurs: {self.stats['errors']}"
                )

        self.stats['estimated_total_files'] = estimated_files
        self.stats['estimated_total_directories'] = estimated_directories
        self.stats['estimated_total_size'] = estimated_total_size
        self.logger.info(
            f"✅ Pré-estimation terminée: {estimated_files} fichiers, {estimated_directories} dossiers | "
            f"Volume cible={estimated_total_size} octets"
        )

    def _map_unc_to_mount_path(self, base_path):
        mount_root = Path(self.pre_estimation_mount_path).expanduser()
        if not self.pre_estimation_mount_path:
            return None
        if not mount_root.exists():
            self.logger.warning(f"Chemin de montage de pré-estimation introuvable: {mount_root}")
            return None

        normalized = base_path.strip("\\")
        parts = [part for part in normalized.split("\\") if part]
        if len(parts) < 2:
            return None
        relative_parts = parts[2:]
        return mount_root.joinpath(*relative_parts)

    def _run_du_pre_estimation(self, base_path):
        target_path = self._map_unc_to_mount_path(base_path)
        if target_path is None or not target_path.exists():
            return False

        if shutil.which("du") is None:
            self.logger.warning("Commande `du` indisponible pour la pré-estimation")
            return False

        started_at = time.time()
        self.logger.info(f"🔎 Pré-estimation `du -sb` sur {target_path}")
        try:
            du_result = subprocess.run(
                ["du", "-sb", str(target_path)],
                capture_output=True,
                text=True,
                timeout=3600,
                check=True,
            )
            total_bytes = int(du_result.stdout.split()[0])
        except Exception as exc:
            self.logger.warning(f"Échec `du -sb` pour la pré-estimation: {exc}")
            return False

        try:
            files_result = subprocess.run(
                ["find", str(target_path), "-type", "f"],
                capture_output=True,
                text=True,
                timeout=3600,
                check=True,
            )
            directories_result = subprocess.run(
                ["find", str(target_path), "-type", "d"],
                capture_output=True,
                text=True,
                timeout=3600,
                check=True,
            )
            estimated_files = sum(1 for line in files_result.stdout.splitlines() if line.strip())
            estimated_directories = sum(1 for line in directories_result.stdout.splitlines() if line.strip())
        except Exception as exc:
            self.logger.warning(f"Échec du comptage `find` pour la pré-estimation: {exc}")
            return False

        self.stats['estimated_total_files'] = estimated_files
        self.stats['estimated_total_directories'] = estimated_directories
        self.stats['estimated_total_size'] = total_bytes
        self.stats['last_activity'] = time.time()
        duration = time.time() - started_at
        self.logger.info(
            f"✅ Pré-estimation terminée: {estimated_files} fichiers, {estimated_directories} dossiers | "
            f"Volume cible={total_bytes} octets | Source=du -sb | Durée: {duration:.1f}s"
        )
        return True

    def _parse_timestamp(self, value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        try:
            dt = datetime.fromisoformat(str(value))
            # Si le datetime n'a pas de timezone mais nous savons que les dates de la base sont offset-aware,
            # nous devons ajouter un timezone pour permettre la comparaison
            if dt.tzinfo is None:
                # Utiliser le timezone UTC par défaut pour les dates sans timezone
                import pytz
                dt = pytz.UTC.localize(dt)
            return dt
        except ValueError:
            return None

    def _should_skip_known_file(self, file_data, existing_file):
        """Ignore les fichiers déjà connus et non modifiés depuis le dernier crawl terminé."""
        if not existing_file or file_data.get("is_directory"):
            return False, None

        existing_size = existing_file.get("size")
        existing_modified = self._parse_timestamp(existing_file.get("last_modified"))
        current_modified = self._parse_timestamp(file_data.get("last_modified"))

        if existing_size == file_data.get("size") and existing_modified == current_modified:
            return True, "Fichier identique (même chemin, taille et date de modification)"

        if (
            self.last_completed_crawl_triggered_at is not None
            and current_modified is not None
            and current_modified <= self.last_completed_crawl_triggered_at
        ):
            return True, "Fichier déjà crawlé et non modifié depuis le dernier crawl terminé"

        return False, None

    def _get_existing_files_map(self, items):
        file_paths = [item["path"] for item in items if not item.get("is_directory")]
        return self.postgres_adapter.get_files_by_paths(
            file_paths,
            crawl_config_id=self.crawl_config_id,
        )

    def _drain_queue_items(self, queue_obj):
        drained = []
        while True:
            try:
                drained.append(queue_obj.get_nowait())
            except Empty:
                break
        return drained

    def _persist_pending_checkpoint(self):
        if not self.run_id or not self.base_path:
            return

        checkpoint_stats = {
            "total_files": self.stats.get("total_files", 0),
            "total_directories": self.stats.get("total_directories", 0),
            "total_size": self.stats.get("total_size", 0),
            "processed_size": self.stats.get("processed_size", 0),
            "large_files": self.stats.get("large_files", 0),
            "estimated_total_size": self.stats.get("estimated_total_size", 0),
            "phase": "pending",
            "last_activity_at": datetime.utcfromtimestamp(self.stats["last_activity"]) if self.stats.get("last_activity") else None,
        }
        queues = {
            "directory_queue": self._drain_queue_items(self.directory_queue),
            "directory_result_queue": self._drain_queue_items(self.directory_result_queue),
            "file_queue": self._drain_queue_items(self.file_queue),
            "large_file_queue": self._drain_queue_items(self.large_file_queue),
        }
        self.postgres_adapter.save_crawl_run_checkpoint(
            self.run_id,
            self.base_path,
            checkpoint_stats,
            queues,
        )
        self.logger.info(
            "⏸️ Checkpoint de reprise sauvegarde pour %s: %s dossiers, %s fichiers, %s gros fichiers",
            self.run_id,
            len(queues["directory_queue"]),
            len(queues["file_queue"]),
            len(queues["large_file_queue"]),
        )

    def _restore_pending_checkpoint(self) -> bool:
        if not self.run_id:
            return False
        checkpoint = self.postgres_adapter.load_crawl_run_checkpoint(self.run_id)
        if not checkpoint:
            return False

        self.base_path = checkpoint["base_path"] or self.base_path
        for key, value in checkpoint["stats"].items():
            if value is None:
                continue
            self.stats[key] = value
        self.stats["phase"] = "crawl"

        restored_queues = checkpoint["queues"]
        for path in restored_queues["directory_queue"]:
            self.directory_queue.put(path)
        for item in restored_queues["directory_result_queue"]:
            self.directory_result_queue.put(item)
        for item in restored_queues["file_queue"]:
            self.file_queue.put(item)
        for item in restored_queues["large_file_queue"]:
            self.large_file_queue.put(item)

        self.logger.info("♻️ Reprise du run %s depuis checkpoint persistant", self.run_id)
        return True

    def _directory_worker(self):
        """
        Worker thread pour traiter les répertoires.
        """
        while not self.stop_event.is_set():
            try:
                # Vérifier si la queue est vide
                if self.directory_queue.empty():
                    time.sleep(0.1)
                    continue
                    
                # Récupérer un répertoire à traiter
                current_path = self.directory_queue.get(timeout=1)
                self.stats['last_activity'] = time.time()

                try:
                    with self._track_active_task('directories'):
                        # Temporisation entre les requêtes
                        if self.delay_between_requests > 0:
                            time.sleep(self.delay_between_requests)

                        # Vérifier si le répertoire a déjà été refusé
                        if current_path in self.denied_directories:
                            self.logger.debug(f"Répertoire déjà refusé: {current_path}")
                            continue

                        # Lister le contenu du répertoire
                        items = self._list_directory_entries(current_path)
                        existing_files = self._get_existing_files_map(items)

                        # Traiter chaque élément
                        for file_data in items:
                            if self.stop_event.is_set():
                                break
                            try:
                                if not file_data['is_directory']:
                                    should_exclude, reason = self.should_exclude_file(file_data['name'])
                                    if should_exclude:
                                        self.logger.debug(f"Fichier exclu: {file_data['name']} ({reason})")
                                        continue

                                if file_data['is_directory']:
                                    current_depth = self._get_path_depth(file_data['path'])
                                    if self.max_depth is None or current_depth < self.max_depth:
                                        self.directory_queue.put(file_data['path'])
                                    self.directory_result_queue.put(file_data)
                                    self.stats['total_directories'] += 1
                                else:
                                    should_skip, reason = self._should_skip_known_file(
                                        file_data,
                                        existing_files.get(file_data["path"]),
                                    )
                                    if should_skip:
                                        self.logger.debug(f"Fichier ignoré: {file_data['name']} ({reason})")
                                        continue

                                    if file_data['size'] > self.large_file_threshold:
                                        self.large_file_queue.put(file_data)
                                        self.stats['large_files'] += 1
                                        self.logger.info(f"📦 Gros fichier détecté: {file_data['name']} ({file_data['size']:,} bytes)")
                                    else:
                                        self.file_queue.put(file_data)

                                    self.stats['total_files'] += 1
                                    self.stats['total_size'] += file_data['size']
                            except Exception as e:
                                self.logger.warning(f"Erreur traitement {file_data['path']}: {e}")
                                self.stats['errors'] += 1
                        if self.pause_requested and current_path:
                            self.directory_queue.put(current_path)
                finally:
                    self.directory_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erreur dans le directory worker: {e}")
                self.stats['errors'] += 1

    def _directory_result_worker(self):
        """
        Worker thread pour traiter les répertoires terminés (sauvegarde en base).
        Ce worker permet de faire décroître la queue des répertoires comme pour les fichiers.
        """
        batch_directories = []
        batch_size = 200  # Plus grand lot pour les répertoires (plus légers)
        
        self.logger.info("📂 Worker répertoires résultats démarré")
        
        while not self.stop_event.is_set():
            try:
                # Vérifier si la queue est vide
                if self.directory_result_queue.empty():
                    # Traiter le lot restant
                    if batch_directories:
                        self._save_batch_to_postgres(batch_directories)
                        batch_directories = []
                    time.sleep(0.5)
                    continue
                
                # Récupérer un répertoire traité à sauvegarder
                directory_data = self.directory_result_queue.get(timeout=2)
                self.stats['last_activity'] = time.time()
                try:
                    with self._track_active_task('directory_results'):
                        batch_directories.append(directory_data)
                        if len(batch_directories) >= batch_size:
                            self._save_batch_to_postgres(batch_directories)
                            batch_directories = []
                finally:
                    self.directory_result_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erreur dans le directory result worker: {e}")
                self.stats['errors'] += 1
        
        # Sauvegarder le dernier lot
        if batch_directories:
            self._save_batch_to_postgres(batch_directories)
        
        self.logger.info("📂 Worker répertoires résultats terminé")

    def _large_file_worker(self):
        """
        Worker thread dédié pour traiter les gros fichiers (calcul de checksum).
        Ce worker utilise des timeouts plus longs et traite les fichiers séquentiellement.
        """
        batch_files = []
        batch_size = 50  # Plus petit lot pour les gros fichiers
        
        self.logger.info("🐘 Worker gros fichiers démarré")
        
        while not self.stop_event.is_set():
            try:
                # Vérifier si la queue est vide
                if self.large_file_queue.empty():
                    # Traiter le lot restant
                    if batch_files:
                        self._save_batch_to_postgres(batch_files)
                        batch_files = []
                    time.sleep(1)  # Pause plus longue pour les gros fichiers
                    continue
                
                # Récupérer un gros fichier à traiter
                file_data = self.large_file_queue.get(timeout=5)
                self.stats['last_activity'] = time.time()
                try:
                    with self._track_active_task('large_files'):
                        self.logger.info(f"🔧 Traitement gros fichier: {file_data['name']} ({file_data['size']:,} bytes)")

                        try:
                            self.setup_smb_credentials()
                            if file_data['path'].startswith('\\\\'):
                                file_unc_path = file_data['path']
                            else:
                                file_unc_path = rf"\\{self.server}\{self.share_name}"

                            file_data["checksum"] = self._calculate_partial_checksum_with_timeout(
                                file_unc_path, timeout=300
                            )

                            if file_data["checksum"]:
                                self.logger.info(f"✅ Checksum calculé: {file_data['name']} -> {file_data['checksum'][:16]}...")
                            else:
                                self.logger.warning(f"❌ Échec checksum: {file_data['name']}")

                        except Exception as e:
                            self.logger.error(f"Erreur calcul checksum gros fichier {file_data['name']}: {e}")
                            file_data["checksum"] = None

                        batch_files.append(file_data)
                        self.stats['processed_size'] += file_data.get('size', 0) or 0
                        
                        # Track processed files for cleanup
                        if 'processed_files' not in self.stats:
                            self.stats['processed_files'] = []
                        self.stats['processed_files'].append(file_data['path'])

                        if len(batch_files) >= batch_size:
                            self._save_batch_to_postgres(batch_files)
                            batch_files = []
                finally:
                    self.large_file_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erreur dans le large file worker: {e}")
                self.stats['errors'] += 1
        
        # Sauvegarder le dernier lot
        if batch_files:
            self._save_batch_to_postgres(batch_files)
        
        self.logger.info("🐘 Worker gros fichiers terminé")

    def _calculate_partial_checksum_with_timeout(self, file_unc_path, timeout=300):
        """
        Calcule un checksum partiel avec timeout pour les gros fichiers.
        
        Args:
            file_unc_path: Chemin UNC du fichier
            timeout: Timeout en secondes
            
        Returns:
            Checksum partiel ou None si timeout
        """
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def calculate_checksum():
            try:
                with smbclient.open_file(file_unc_path, mode='rb') as f:
                    hash_sha256 = hashlib.sha256()
                    
                    # Lire le premier 1MB
                    first_chunk = f.read(1024 * 1024)
                    if first_chunk:
                        hash_sha256.update(first_chunk)
                    
                    # Aller à la fin et lire le dernier 1MB
                    if f.seek(0, 2) > 1024 * 1024:
                        f.seek(-1024 * 1024, 2)
                        last_chunk = f.read(1024 * 1024)
                        if last_chunk:
                            hash_sha256.update(last_chunk)
                    
                    result_queue.put(f"partial_{hash_sha256.hexdigest()}")
            except Exception as e:
                result_queue.put(e)
        
        # Lancer le calcul dans un thread séparé
        thread = threading.Thread(target=calculate_checksum)
        thread.daemon = True
        thread.start()
        
        # Attendre le résultat avec timeout
        try:
            result = result_queue.get(timeout=timeout)
            if isinstance(result, Exception):
                raise result
            return result
        except queue.Empty:
            self.logger.warning(f"⏰ Timeout calcul checksum pour {file_unc_path}")
            return None

    def _file_worker(self):
        """
        Worker thread pour traiter les fichiers normaux (calcul de checksum).
        """
        batch_files = []
        batch_size = 100  # Taille du lot pour PostgreSQL
        
        while not self.stop_event.is_set():
            try:
                # Vérifier si la queue est vide
                if self.file_queue.empty():
                    # Traiter le lot restant
                    if batch_files:
                        self._save_batch_to_postgres(batch_files)
                        batch_files = []
                    time.sleep(0.1)
                    continue
                
                # Récupérer un fichier à traiter
                file_data = self.file_queue.get(timeout=1)
                self.stats['last_activity'] = time.time()
                try:
                    with self._track_active_task('files'):
                        if self.delay_between_requests > 0:
                            time.sleep(self.delay_between_requests)

                        try:
                            self.setup_smb_credentials()
                            if file_data['path'].startswith('\\\\'):
                                file_unc_path = file_data['path']
                            else:
                                file_unc_path = rf"\\{self.server}\{self.share_name}"

                            file_data["checksum"] = self._calculate_full_checksum(file_unc_path)

                        except Exception as e:
                            self.logger.warning(f"Erreur calcul checksum {file_data['name']}: {e}")
                            file_data["checksum"] = None

                        batch_files.append(file_data)
                        self.stats['processed_size'] += file_data.get('size', 0) or 0
                        
                        # Track processed files for cleanup
                        if 'processed_files' not in self.stats:
                            self.stats['processed_files'] = []
                        self.stats['processed_files'].append(file_data['path'])
                        
                        if len(batch_files) >= batch_size:
                            self._save_batch_to_postgres(batch_files)
                            batch_files = []
                finally:
                    self.file_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erreur dans le file worker: {e}")
                self.stats['errors'] += 1
        
        # Sauvegarder le dernier lot
        if batch_files:
            self._save_batch_to_postgres(batch_files)

    def _save_batch_to_postgres(self, batch_files):
        """
        Sauvegarde un lot de fichiers dans PostgreSQL.
        """
        try:
            count = self.postgres_adapter.save_files_batch(batch_files)
            self.logger.debug(f"💾 Sauvegardé {count} fichiers dans PostgreSQL")
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde PostgreSQL: {e}")
            self.stats['errors'] += 1

    def _cleanup_deleted_files(self):
        """
        Nettoie les fichiers qui existent dans la base mais plus dans le système de fichiers.
        Seuls les fichiers de la configuration de crawl actuelle sont considérés.
        """
        try:
            self.logger.info("🧹 Nettoyage des fichiers supprimés...")
            
            # Récupérer tous les fichiers existants dans la base pour cette configuration
            existing_files = self.postgres_adapter.get_files_by_config(self.crawl_config_id)
            
            if not existing_files:
                self.logger.info("📝 Aucun fichier existant trouvé pour cette configuration")
                return
            
            # Créer un ensemble des chemins de fichiers traités pendant ce crawl
            processed_paths = set()
            # Ajouter les fichiers traités
            processed_paths.update(self.stats.get('processed_files', []))
            # Ajouter les fichiers en cours de traitement
            processed_paths.update([file_data['path'] for file_data in list(self.file_queue.queue)])
            
            # Identifier les fichiers qui sont dans la base mais pas dans le crawl actuel
            deleted_files = []
            for db_file in existing_files:
                file_path = db_file.get('path')
                if file_path and file_path not in processed_paths:
                    # Vérifier si le fichier existe vraiment en essayant d'y accéder
                    try:
                        file_unc_path = file_path if file_path.startswith('\\') else rf"\\{self.server}\\{self.share_name}\\{file_path.lstrip('/')}"
                        # Essayer d'ouvrir le fichier pour vérifier son existence
                        with smbclient.open_file(file_unc_path, mode='rb') as f:
                            pass  # Fichier existe, ne rien faire
                    except Exception:
                        # Fichier n'existe pas, marquer pour suppression
                        deleted_files.append(file_path)
            
            if deleted_files:
                self.logger.info(f"🗑️ Trouvé {len(deleted_files)} fichiers supprimés à nettoyer")
                
                # Supprimer les fichiers de la base de données
                deleted_count = self.postgres_adapter.delete_files_by_paths(deleted_files)
                self.logger.info(f"🧹 {deleted_count} fichiers supprimés ont été nettoyés de la base")
                self.stats['deleted_files_cleaned'] = deleted_count
            else:
                self.logger.info("📝 Aucun fichier supprimé trouvé")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du nettoyage des fichiers supprimés: {e}")
            self.stats['errors'] += 1

    def _calculate_full_checksum(self, file_unc_path):
        """
        Calcule le checksum SHA-256 complet d'un fichier.
        """
        try:
            with smbclient.open_file(file_unc_path, mode='rb') as f:
                hash_sha256 = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
                return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Erreur calcul checksum complet {file_unc_path}: {e}")
            return None

    def _calculate_partial_checksum(self, file_unc_path):
        """
        Calcule un checksum partiel pour les gros fichiers (premier et dernier 1MB).
        """
        try:
            with smbclient.open_file(file_unc_path, mode='rb') as f:
                hash_sha256 = hashlib.sha256()
                
                # Lire le premier 1MB
                first_chunk = f.read(1024 * 1024)
                if first_chunk:
                    hash_sha256.update(first_chunk)
                
                # Aller à la fin et lire le dernier 1MB
                if f.seek(0, 2) > 1024 * 1024:
                    f.seek(-1024 * 1024, 2)
                    last_chunk = f.read(1024 * 1024)
                    if last_chunk:
                        hash_sha256.update(last_chunk)
                
                return f"partial_{hash_sha256.hexdigest()}"
        except Exception as e:
            self.logger.error(f"Erreur calcul checksum partiel {file_unc_path}: {e}")
            return None

    def start_crawl(self, base_path=None):
        """
        Démarre le crawl récursif du partage SMB.
        
        Args:
            base_path (str): Chemin de base pour commencer le crawl.
        """
        self.logger.info("🚀 Démarrage du crawl SMB avec PostgreSQL...")
        self.stats['start_time'] = time.time()
        
        # Utiliser le chemin de base par défaut si non spécifié
        if base_path is None:
            base_path = rf"\\{self.server}\{self.share_name}"
        self.base_path = base_path

        restored_from_checkpoint = self._restore_pending_checkpoint()
        
        if not restored_from_checkpoint and self.pre_estimation_enabled and self.stats['estimated_total_size'] <= 0:
            self._run_pre_estimation(base_path)
        elif not restored_from_checkpoint and self.stats['estimated_total_size'] > 0:
            self.logger.info(
                "✅ Baseline volumétrique injectée avant crawl: Volume cible=%s octets",
                self.stats['estimated_total_size'],
            )

        if self.crawl_config_id:
            self.last_completed_crawl_triggered_at = self._parse_timestamp(
                self.postgres_adapter.get_last_completed_crawl_triggered_at(
                    self.crawl_config_id,
                    exclude_run_id=self.run_id,
                )
            )

        if not restored_from_checkpoint:
            self.directory_queue.put(base_path)
            self.stats['total_directories'] = 1
            self.stats['phase'] = 'crawl'

        # Démarrer les workers
        with ThreadPoolExecutor(max_workers=self.max_workers + 2) as executor:  # +2 pour les workers dédiés (gros fichiers + répertoires résultats)
            # Calculer le nombre de workers pour chaque type
            if self.max_workers == 1:
                # Avec un seul worker, il gère tout
                dir_workers_count = 1
                file_workers_count = 0  # Les workers dédiés géreront les fichiers
                large_file_workers_count = 1
                directory_result_workers_count = 0
            elif self.max_workers <= 3:
                # Pour petits nombres : plus de workers répertoires
                dir_workers_count = max(1, self.max_workers - 2)
                file_workers_count = 0  # Les workers dédiés géreront les fichiers
                large_file_workers_count = 1
                directory_result_workers_count = 1
            else:
                # Pour plus de workers : répartir entre tous les types
                dir_workers_count = max(2, (self.max_workers * 2) // 4)
                file_workers_count = max(1, (self.max_workers * 1) // 4)
                large_file_workers_count = 1
                directory_result_workers_count = 1
            
            # Lancer les workers de répertoires (exploration)
            directory_workers = []
            for i in range(dir_workers_count):
                worker = executor.submit(self._directory_worker)
                directory_workers.append(worker)
            
            # Lancer les workers de fichiers normaux
            file_workers = []
            for i in range(file_workers_count):
                worker = executor.submit(self._file_worker)
                file_workers.append(worker)
            
            # Lancer le worker dédié aux gros fichiers
            large_file_workers = []
            for i in range(large_file_workers_count):
                worker = executor.submit(self._large_file_worker)
                large_file_workers.append(worker)
            
            # Lancer le worker dédié aux répertoires résultats
            directory_result_workers = []
            for i in range(directory_result_workers_count):
                worker = executor.submit(self._directory_result_worker)
                directory_result_workers.append(worker)
            
            # Thread pour sauvegarder les résultats
            def result_saver():
                batch = []
                while not self.stop_event.is_set():
                    try:
                        # Récupérer un résultat
                        file_data = self.result_queue.get(timeout=1)
                        try:
                            with self._track_active_task('results'):
                                batch.append(file_data)
                                if len(batch) >= 100:
                                    self._save_batch_to_postgres(batch)
                                    batch = []
                        finally:
                            self.result_queue.task_done()
                            
                    except Empty:
                        # Sauvegarder le lot restant
                        if batch:
                            self._save_batch_to_postgres(batch)
                            batch = []
                        continue
                    except Exception as e:
                        self.logger.error(f"Erreur dans result_saver: {e}")
            
            # Lancer le sauvegardeur
            saver_worker = executor.submit(result_saver)
            
            try:
                # Attendre que toutes les queues soient vides
                while True:
                    self._progress_callback()
                    if self.stop_event.is_set() and not self._has_active_work():
                        break

                    last_activity = self.stats['last_activity'] or self.stats['start_time']

                    if (self.directory_queue.empty() and 
                        self.file_queue.empty() and 
                        self.large_file_queue.empty() and 
                        self.directory_result_queue.empty() and
                        self.result_queue.empty() and
                        not self._has_active_work()):
                        
                        # Attendre un peu pour s'assurer que tout est traité
                        time.sleep(2)
                        
                        if (self.directory_queue.empty() and 
                            self.file_queue.empty() and 
                            self.large_file_queue.empty() and 
                            self.directory_result_queue.empty() and
                            self.result_queue.empty() and
                            not self._has_active_work()):
                            print("\n🏁 Toutes les queues sont vides - Fin du crawl")
                            break
                    
                    # Timeout de sécurité (20 minutes sans activité)
                    if time.time() - last_activity > 1200:
                        self.stats['timed_out'] = True
                        self.stats['final_status'] = 'failed'
                        self.logger.error("⏰ Timeout de sécurité (20 min) - arrêt en échec du crawl")
                        print("\n⏰ Timeout de sécurité (20 min) - Fin du crawl")
                        break

                    time.sleep(5)
                
            except KeyboardInterrupt:
                self.stats['final_status'] = 'cancelled'
                self.user_cancelled = True  # Marquer comme cancellation utilisateur
                print("\n⚠️ Arrêt demandé par l'utilisateur...")
            finally:
                # Arrêter tous les workers
                self.stop_event.set()
        
        if self.pause_requested:
            self._persist_pending_checkpoint()
            self.stats['end_time'] = time.time()
            self.stats['final_status'] = 'pending'
            self.logger.info(f"🏁 Run mis en attente avec checkpoint={self.run_id}")
            return self.stats
        
        # Réinitialiser le flag cancelled si le run s'est terminé normalement
        # (et non pas à cause d'un vrai cancellation)
        if not self.user_cancelled:
            self.stats['cancelled'] = False
        
        # Nettoyer les fichiers supprimés (optionnel, peut être désactivé pour les gros crawls)
        if self.crawl_config_id and not self.stats.get('timed_out', False):
            self._cleanup_deleted_files()
        
        # Calculer les doublons
        self.logger.info("🔄 Calcul des doublons...")
        duplicate_count = self.postgres_adapter.calculate_duplicates()
        self.stats['duplicate_files'] = duplicate_count
        
        # Finaliser
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        if self.stats['timed_out']:
            self.stats['final_status'] = 'failed'
        elif self.stop_event.is_set():
            self.stats['final_status'] = 'cancelled'
        else:
            self.stats['final_status'] = 'completed'

        if self.run_id:
            self.postgres_adapter.clear_crawl_run_checkpoint(self.run_id)

        # Sauvegarder les statistiques
        crawl_stats = {
            'total_files': self.stats['total_files'],
            'total_directories': self.stats['total_directories'],
            'total_size': self.stats['total_size'],
            'duplicate_files': self.stats['duplicate_files'],
            'duplicate_size': 0,  # TODO: calculer
            'crawl_duration_seconds': int(duration),
            'server_info': f"{self.server}\\{self.share_name}",
            'status': self.stats['final_status']
        }

        self.postgres_adapter.save_crawl_statistics(crawl_stats)
        self.logger.info(f"🏁 Fin de crawl avec statut final={self.stats['final_status']}")

        # Afficher les statistiques finales
        self._print_final_stats()
        
        return self.stats

    def _progress_callback(self):
        """Callback pour afficher la progression."""
        if self.should_stop_requested_run():
            self.logger.info(f"⏹️ Arrêt demandé pour le run {self.run_id}")
            self.user_cancelled = True  # Marquer comme cancellation utilisateur
            self.stop()
            return
        if self.should_pause_requested_run():
            self.logger.info(f"⏸️ Mise en attente demandée pour le run {self.run_id}")
            self.pause_requested = True
            self.stop_event.set()
            return

        duration = time.time() - self.stats['start_time']
        dirs_in_queue = self.directory_queue.qsize()
        dirs_result_in_queue = self.directory_result_queue.qsize()
        files_in_queue = self.file_queue.qsize()
        large_files_in_queue = self.large_file_queue.qsize()
        known_total_bytes = self.stats['total_size']
        target_total_bytes = self.stats['estimated_total_size'] or known_total_bytes
        processed_bytes = min(self.stats['processed_size'], target_total_bytes) if target_total_bytes > 0 else 0
        progress_percent = round((processed_bytes / target_total_bytes) * 100, 1) if target_total_bytes > 0 else 0.0

        progress_line = (
            f"📊 Progression: {self.stats['total_files']} fichiers, "
            f"{self.stats['total_directories']} dossiers, "
            f"{self.stats['large_files']} gros fichiers | "
            f"Queues: Dossiers à explorer={dirs_in_queue}, "
            f"Dossiers à indexer={dirs_result_in_queue}, "
            f"Vérification d'intégrité={files_in_queue}, "
            f"Gros fichiers en attente={large_files_in_queue} | "
            f"Volume cible={target_total_bytes} octets, "
            f"Volume traité={processed_bytes} octets, "
            f"Volume découvert={known_total_bytes} octets, "
            f"Progression volume={progress_percent}% | "
            f"Durée: {duration:.1f}s | Erreurs: {self.stats['errors']}"
        )

        self.logger.info(progress_line)

    def _print_final_stats(self):
        """Affiche les statistiques finales du crawl."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n" + "="*60)
        print("🎉 CRAWL TERMINÉ - STATISTIQUES FINALES")
        print("="*60)
        print(f"📁 Répertoires explorés: {self.stats['total_directories']:,}")
        print(f"📄 Fichiers trouvés: {self.stats['total_files']:,}")
        print(f"� Gros fichiers traités: {self.stats['large_files']:,}")
        print(f"�� Taille totale: {self.stats['total_size']:,} octets ({self.stats['total_size'] / 1024 / 1024:.1f} MB)")
        print(f"🔄 Fichiers en double: {self.stats['duplicate_files']:,}")
        print(f"⏱️ Durée totale: {duration:.1f} secondes ({duration/60:.1f} minutes)")
        print(f"❌ Erreurs rencontrées: {self.stats['errors']:,}")
        
        if self.stats['total_files'] > 0:
            print(f"🚀 Vitesse moyenne: {self.stats['total_files']/duration:.1f} fichiers/seconde")
            print(f"📊 Débit moyen: {(self.stats['total_size']/duration/1024/1024):.1f} MB/seconde")
            
        if self.stats['large_files'] > 0:
            print(f"🐘 Pourcentage gros fichiers: {(self.stats['large_files']/self.stats['total_files']*100):.1f}%")
        
        print("="*60)

    def stop(self):
        """Arrête le crawler."""
        self.stop_event.set()


def parse_unc_start_path(start_path):
    """Extrait serveur, partage et chemin UNC normalisé depuis start_path."""
    normalized = start_path.strip().rstrip("\\")
    parts = [part for part in normalized.split("\\") if part]
    if len(parts) < 2:
        raise ValueError(f"Chemin de départ invalide: {start_path}")
    server = parts[0]
    share_name = parts[1]
    base_path = f"\\\\{server}\\{share_name}"
    if len(parts) > 2:
        base_path += "\\" + "\\".join(parts[2:])
    return server, share_name, base_path


def build_postgres_config():
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'openindex'),
        'user': os.getenv('POSTGRES_USER', 'openindex_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
    }


def rotate_runtime_log_for_run(run_id):
    log_path = Path(os.getenv("OPENINDEX_CRAWLER_LOG_PATH", "logs/smb_crawler_postgresql.log"))
    if not log_path.exists():
        return
    archived_path = log_path.with_name(f"{log_path.stem}_{run_id}{log_path.suffix}")
    archived_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.replace(archived_path)


def run_single_crawl(run_payload):
    """Exécute une exploration à partir d'un run réservé en base."""
    config_manager = ConfigManager()
    crawler_config = config_manager.get_crawler_config()
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    log_path = Path(os.getenv("OPENINDEX_CRAWLER_LOG_PATH", "logs/smb_crawler_postgresql.log"))
    server, share_name, base_path = parse_unc_start_path(run_payload["start_path"])
    rotate_runtime_log_for_run(run_payload["run_id"])

    print("🚀 Démarrage de l'exploration SMB avec PostgreSQL...")
    print(f"🖥️ Serveur: {server}")
    print(f"📁 Partage: {share_name}")
    print(f"📍 Chemin: {base_path}")
    print(f"👤 Utilisateur: {run_payload['connection_username']}")
    print(f"🔧 Workers: {crawler_config['max_workers']}")
    print(f"⏱️ Délai: {crawler_config['delay_between_requests']}s")

    crawler = SMBCrawlerPostgreSQL(
        server=server,
        username=run_payload["connection_username"],
        password=run_payload["connection_password"],
        share_name=share_name,
        domain=run_payload.get("connection_domain") or '',
        crawl_config_id=run_payload["config_id"],
        postgres_config=build_postgres_config(),
        max_workers=crawler_config["max_workers"],
        delay_between_requests=crawler_config["delay_between_requests"],
        max_queue_size=crawler_config["max_queue_size"],
        max_depth=crawler_config["max_depth"],
        large_file_threshold=crawler_config["large_file_threshold"],
        pre_estimation_enabled=(
            crawler_config.get("pre_estimation_enabled", False)
            and int(run_payload.get("estimated_total_size") or 0) <= 0
        ),
        pre_estimation_mode=crawler_config.get("pre_estimation_mode", "smb"),
        pre_estimation_mount_path=crawler_config.get("pre_estimation_mount_path", ""),
        pre_estimated_total_size=run_payload.get("estimated_total_size") or 0,
        debug=debug_mode
    )
    crawler.run_id = run_payload["run_id"]

    print(f"📝 Logs configurés dans: {log_path}")
    print(f"🔧 Seuil des gros fichiers: {crawler_config['large_file_threshold'] / 1024 / 1024:.1f} MB")
    print(f"🐘 Base de données: PostgreSQL 17")

    print("\nDémarrage de l'exploration récursive...")
    print("Appuyez sur Ctrl+C pour arrêter")

    stats = crawler.start_crawl(base_path=base_path)
    stats["cancelled"] = crawler.stop_event.is_set() and not stats.get("timed_out", False)
    stats["pending"] = crawler.pause_requested
    return stats


def cleanup_stale_runs(adapter, interval_seconds=60):
    """Tâche en arrière-plan pour corriger les statuts des runs bloqués."""
    import time
    from datetime import datetime, timedelta
    
    while True:
        try:
            # Trouver les runs qui sont en cours depuis trop longtemps
            stale_runs = adapter.get_stale_running_runs()
            
            for run in stale_runs:
                run_id = run['id']
                triggered_at = datetime.fromisoformat(run['triggered_at'].replace('Z', '+00:00'))
                duration = datetime.now() - triggered_at
                
                # Si un run est en cours depuis plus de 2 heures, le marquer comme cancelled
                if duration > timedelta(hours=2):
                    print(f"⚠️  Run {run_id} bloqué depuis {duration} - Correction du statut")
                    adapter.update_crawl_run_status(run_id, "cancelled")
                    print(f"✅ Run {run_id} marqué comme cancelled (blocage détecté)")
                
        except Exception as e:
            print(f"❌ Erreur dans cleanup_stale_runs: {e}")
        
        time.sleep(interval_seconds)


def worker_loop(poll_interval_seconds=5):
    """Boucle principale du service d'exploration, pilotée par crawl_runs."""
    adapter = PostgreSQLAdapter(build_postgres_config())
    adapter.initialize_database()
    adapter.reset_stale_running_runs()
    print("👂 Worker d'exploration prêt, en attente de runs...")
    
    # Lancer la tâche de nettoyage en arrière-plan
    import threading
    cleanup_thread = threading.Thread(
        target=cleanup_stale_runs,
        args=(adapter,),
        daemon=True
    )
    cleanup_thread.start()
    print("🔄 Tâche de nettoyage des runs lancée (vérification toutes les 60s)")

    while True:
        run_payload = adapter.wait_for_next_run(poll_interval_seconds=poll_interval_seconds)
        run_id = run_payload["run_id"]
        try:
            print(f"▶️ Run réservé: {run_id} pour {run_payload['name']} ({run_payload['start_path']})")
            stats = run_single_crawl(run_payload)
            if stats.get("timed_out"):
                final_status = "failed"
            elif stats.get("pending"):
                final_status = "pending"
            elif stats.get("cancelled"):
                final_status = "cancelled"
            else:
                final_status = "completed"
            adapter.update_crawl_run_status(run_id, final_status)
            print(f"✅ Run terminé: {run_id} ({final_status})")
        except KeyboardInterrupt:
            adapter.update_crawl_run_status(run_id, "cancelled")
            raise
        except Exception as exc:
            adapter.update_crawl_run_status(run_id, "failed")
            print(f"❌ Run en échec {run_id}: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Service d'exploration OpenIndex")
    parser.add_argument("mode", nargs="?", default="worker", choices=["worker"])
    parser.add_argument("--poll-interval", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "worker":
        worker_loop(poll_interval_seconds=args.poll_interval)


if __name__ == "__main__":
    main()
