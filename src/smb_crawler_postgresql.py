#!/usr/bin/env python3
"""
Crawler SMB avec PostgreSQL direct
Version modifiée pour utiliser PostgreSQL au lieu de SQLite
"""

import os
import sys
import hashlib
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import smbclient
from logging_config import get_logger_manager
from postgres_adapter import PostgreSQLAdapter
from config_manager import ConfigManager


class SMBCrawlerPostgreSQL:
    """Classe principale pour le crawler SMB avec PostgreSQL."""

    def __init__(self, server, username, password, share_name, domain='', 
                 postgres_config=None, max_workers=4, delay_between_requests=0.1, 
                 max_queue_size=1000, max_depth=None, debug=False, 
                 large_file_threshold=104857600):
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
        
        # Initialiser PostgreSQL
        self.postgres_adapter = PostgreSQLAdapter(self.postgres_config)
        self.postgres_adapter.initialize_database()
        
        # Patterns de fichiers à exclure
        self.exclude_patterns = ['~$', '.tmp', '.lock', '.lnk', 'Thumbs.db', 'desktop.ini']
        
        # Cache des répertoires avec accès refusé
        self.denied_directories = set()
        
        # Queues pour le traitement parallèle
        self.directory_queue = Queue(maxsize=max_queue_size)  # Queue pour les répertoires à traiter
        self.directory_result_queue = Queue(maxsize=max_queue_size)  # Queue pour les répertoires traités
        self.file_queue = Queue(maxsize=max_queue_size)
        self.large_file_queue = Queue(maxsize=max_queue_size)  # Queue séparée pour les gros fichiers
        self.result_queue = Queue(maxsize=max_queue_size)
        
        # Événement pour arrêter le crawler
        self.stop_event = threading.Event()
        
        # Statistiques
        self.stats = {
            'total_directories': 0,
            'total_files': 0,
            'total_size': 0,
            'large_files': 0,  # Nouveau: compteur de gros fichiers
            'duplicate_files': 0,
            'duplicate_size': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
            'last_activity': None
        }
        
        # Configuration du logging
        self.setup_logging()

    def setup_logging(self):
        """Configure le logging avec rotation automatique."""
        self.logger_manager = get_logger_manager()
        self.logger = self.logger_manager.get_logger("smb_crawler_postgresql")

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
                    'last_modified': datetime.now().isoformat(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                items.append(file_data)
        
        return items

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
                
                # Temporisation entre les requêtes
                if self.delay_between_requests > 0:
                    time.sleep(self.delay_between_requests)
                
                # Vérifier si le répertoire a déjà été refusé
                if current_path in self.denied_directories:
                    self.logger.debug(f"Répertoire déjà refusé: {current_path}")
                    continue
                
                # Lister le contenu du répertoire
                try:
                    self.setup_smb_credentials()
                    items = smbclient.listdir(current_path)
                    
                    # Traiter chaque élément
                    for item_name in items:
                        if self.stop_event.is_set():
                            break
                        
                        item_path = f"{current_path}\\{item_name}"
                        
                        try:
                            stat = smbclient.stat(item_path)
                            
                            # Créer les métadonnées
                            file_data = {
                                'path': item_path,
                                'name': item_name,
                                'size': stat.st_size,
                                'is_directory': stat.st_mode & 0o040000 == 0o040000,
                                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'created_at': datetime.now(),
                                'updated_at': datetime.now()
                            }
                            
                            # Vérifier si le fichier doit être exclu
                            if not file_data['is_directory']:
                                should_exclude, reason = self.should_exclude_file(item_name)
                                if should_exclude:
                                    self.logger.debug(f"Fichier exclu: {item_name} ({reason})")
                                    continue
                            
                            # Ajouter à la queue appropriée
                            if file_data['is_directory']:
                                self.directory_result_queue.put(file_data)  # Mettre dans la queue des répertoires traités
                                self.stats['total_directories'] += 1
                            else:
                                # Séparer les gros fichiers des fichiers normaux
                                if file_data['size'] > self.large_file_threshold:
                                    self.large_file_queue.put(file_data)
                                    self.stats['large_files'] += 1
                                    self.logger.info(f"📦 Gros fichier détecté: {item_name} ({file_data['size']:,} bytes)")
                                else:
                                    self.file_queue.put(file_data)
                                
                                self.stats['total_files'] += 1
                                self.stats['total_size'] += file_data['size']
                            
                        except Exception as e:
                            self.logger.warning(f"Erreur traitement {item_path}: {e}")
                            self.stats['errors'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Erreur listing {current_path}: {e}")
                    
                    # Essayer avec la méthode de secours
                    try:
                        items = self.list_directory_fallback(current_path)
                        if items:
                            for item_data in items:
                                if self.stop_event.is_set():
                                    break
                                
                                # Vérifier si le fichier doit être exclu
                                if not item_data['is_directory']:
                                    should_exclude, reason = self.should_exclude_file(item_data['name'])
                                    if should_exclude:
                                        self.logger.debug(f"Fichier exclu: {item_data['name']} ({reason})")
                                        continue
                                
                                # Ajouter à la queue appropriée
                                if item_data['is_directory']:
                                    self.directory_result_queue.put(item_data)  # Mettre dans la queue des répertoires traités
                                    self.stats['total_directories'] += 1
                                else:
                                    # Séparer les gros fichiers des fichiers normaux
                                    if item_data['size'] > self.large_file_threshold:
                                        self.large_file_queue.put(item_data)
                                        self.stats['large_files'] += 1
                                        self.logger.info(f"📦 Gros fichier détecté: {item_data['name']} ({item_data['size']:,} bytes)")
                                    else:
                                        self.file_queue.put(item_data)
                                    
                                    self.stats['total_files'] += 1
                                    self.stats['total_size'] += item_data['size']
                        else:
                            self.logger.error(f"Échec complet pour {current_path}")
                            self.stats['errors'] += 1
                    except Exception as fallback_error:
                        self.logger.error(f"Erreur fallback {current_path}: {fallback_error}")
                        self.stats['errors'] += 1
                
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
                
                # Ajouter au lot
                batch_directories.append(directory_data)
                
                # Sauvegarder le lot si nécessaire
                if len(batch_directories) >= batch_size:
                    self._save_batch_to_postgres(batch_directories)
                    batch_directories = []
                
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
                
                self.logger.info(f"🔧 Traitement gros fichier: {file_data['name']} ({file_data['size']:,} bytes)")
                
                # Calculer le checksum avec timeout plus long
                try:
                    self.setup_smb_credentials()
                    
                    # Construire le chemin UNC
                    if file_data['path'].startswith('\\\\'):
                        file_unc_path = file_data['path']
                    else:
                        file_unc_path = rf"\\{self.server}\{self.share_name}"
                    
                    # Timeout plus long pour les gros fichiers
                    file_data["checksum"] = self._calculate_partial_checksum_with_timeout(
                        file_unc_path, timeout=300  # 5 minutes max par fichier
                    )
                    
                    if file_data["checksum"]:
                        self.logger.info(f"✅ Checksum calculé: {file_data['name']} -> {file_data['checksum'][:16]}...")
                    else:
                        self.logger.warning(f"❌ Échec checksum: {file_data['name']}")
                    
                except Exception as e:
                    self.logger.error(f"Erreur calcul checksum gros fichier {file_data['name']}: {e}")
                    file_data["checksum"] = None
                
                # Ajouter au lot
                batch_files.append(file_data)
                
                # Sauvegarder le lot si nécessaire
                if len(batch_files) >= batch_size:
                    self._save_batch_to_postgres(batch_files)
                    batch_files = []
                
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
                
                # Temporisation entre les requêtes
                if self.delay_between_requests > 0:
                    time.sleep(self.delay_between_requests)
                
                # Calculer le checksum
                try:
                    self.setup_smb_credentials()
                    
                    # Construire le chemin UNC
                    if file_data['path'].startswith('\\\\'):
                        file_unc_path = file_data['path']
                    else:
                        file_unc_path = rf"\\{self.server}\{self.share_name}"
                    
                    # Fichiers normaux : checksum complet
                    file_data["checksum"] = self._calculate_full_checksum(file_unc_path)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur calcul checksum {file_data['name']}: {e}")
                    file_data["checksum"] = None
                
                # Ajouter au lot
                batch_files.append(file_data)
                
                # Sauvegarder le lot si nécessaire
                if len(batch_files) >= batch_size:
                    self._save_batch_to_postgres(batch_files)
                    batch_files = []
                
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
        
        # Ajouter le répertoire racine à la queue
        self.directory_queue.put(base_path)
        self.stats['total_directories'] = 1
        
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
                        batch.append(file_data)
                        
                        # Sauvegarder par lots
                        if len(batch) >= 100:
                            self._save_batch_to_postgres(batch)
                            batch = []
                            
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
                    if (self.directory_queue.empty() and 
                        self.file_queue.empty() and 
                        self.large_file_queue.empty() and 
                        self.directory_result_queue.empty() and
                        self.result_queue.empty()):
                        
                        # Attendre un peu pour s'assurer que tout est traité
                        time.sleep(2)
                        
                        if (self.directory_queue.empty() and 
                            self.file_queue.empty() and 
                            self.large_file_queue.empty() and 
                            self.directory_result_queue.empty() and
                            self.result_queue.empty()):
                            print("\n🏁 Toutes les queues sont vides - Fin du crawl")
                            break
                    
                    # Timeout de sécurité (20 minutes sans activité)
                    if time.time() - self.stats['last_activity'] > 1200:
                        print("\n⏰ Timeout de sécurité (20 min) - Fin du crawl")
                        break
                    
                    # Callback de progression
                    self._progress_callback()
                    time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n⚠️ Arrêt demandé par l'utilisateur...")
            finally:
                # Arrêter tous les workers
                self.stop_event.set()
                
                # Attendre que tous les workers se terminent
                for worker in directory_workers + file_workers + large_file_workers + directory_result_workers + [saver_worker]:
                    worker.cancel()
        
        # Calculer les doublons
        self.logger.info("🔄 Calcul des doublons...")
        duplicate_count = self.postgres_adapter.calculate_duplicates()
        self.stats['duplicate_files'] = duplicate_count
        
        # Finaliser
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        # Sauvegarder les statistiques
        crawl_stats = {
            'total_files': self.stats['total_files'],
            'total_directories': self.stats['total_directories'],
            'total_size': self.stats['total_size'],
            'duplicate_files': self.stats['duplicate_files'],
            'duplicate_size': 0,  # TODO: calculer
            'crawl_duration_seconds': int(duration),
            'server_info': f"{self.server}\\{self.share_name}",
            'status': 'completed'
        }
        
        self.postgres_adapter.save_crawl_statistics(crawl_stats)
        
        # Afficher les statistiques finales
        self._print_final_stats()
        
        return self.stats

    def _progress_callback(self):
        """Callback pour afficher la progression."""
        duration = time.time() - self.stats['start_time']
        dirs_in_queue = self.directory_queue.qsize()
        dirs_result_in_queue = self.directory_result_queue.qsize()
        files_in_queue = self.file_queue.qsize()
        large_files_in_queue = self.large_file_queue.qsize()
        
        print(f"\r📊 Progression: {self.stats['total_files']} fichiers, "
              f"{self.stats['total_directories']} répertoires, "
              f"{self.stats['large_files']} gros fichiers | "
              f"Queue: {dirs_in_queue} dirs → {dirs_result_in_queue} saved, "
              f"{files_in_queue} files, {large_files_in_queue} large | "
              f"Durée: {duration:.1f}s | Erreurs: {self.stats['errors']}", end="")

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


def main():
    """Fonction principale pour tester le crawler PostgreSQL."""
    
    # Configuration
    config_manager = ConfigManager()
    
    # Configuration SMB
    smb_config = config_manager.get_smb_credentials()
    
    # Configuration du crawler
    crawler_config = config_manager.get_crawler_config()
    
    # Mode debug
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print("🚀 Démarrage du crawler SMB avec PostgreSQL...")
    print(f"🖥️ Serveur: {smb_config['server']}")
    print(f"📁 Partage: {smb_config['share_name']}")
    print(f"👤 Utilisateur: {smb_config['username']}")
    print(f"🔧 Workers: {crawler_config['max_workers']}")
    print(f"⏱️ Délai: {crawler_config['delay_between_requests']}s")
    
    # Créer le crawler
    crawler = SMBCrawlerPostgreSQL(
        server=smb_config["server"],
        username=smb_config["username"],
        password=smb_config["password"],
        share_name=smb_config["share_name"],
        domain=smb_config["domain"],
        postgres_config={
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        },
        max_workers=crawler_config["max_workers"],
        delay_between_requests=crawler_config["delay_between_requests"],
        max_queue_size=crawler_config["max_queue_size"],
        max_depth=crawler_config["max_depth"],
        large_file_threshold=crawler_config["large_file_threshold"],
        debug=debug_mode
    )
    
    # Afficher la configuration du logging
    print(f"📝 Logs configurés dans: logs/openindex.log")
    print(f"🔧 Seuil des gros fichiers: {crawler_config['large_file_threshold'] / 1024 / 1024:.1f} MB")
    print(f"🐘 Base de données: PostgreSQL 17")
    
    print("\nDémarrage du crawl récursif complet...")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        # Démarrer le crawl
        stats = crawler.start_crawl()
        
        print("\n✅ Crawl terminé avec succès!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Arrêt demandé par l'utilisateur")
        crawler.stop()
    except Exception as e:
        print(f"\n❌ Erreur lors du crawl: {e}")
        crawler.stop()


if __name__ == "__main__":
    main()
