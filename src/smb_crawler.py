#!/usr/bin/env python3
"""
Script de base pour le crawler SMB avec pagination et indexation progressive.
Ce script utilise la bibliothèque smbclient pour parcourir les partages SMB.
"""

import os
import hashlib
import sqlite3
import time
import threading
from datetime import datetime
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import smbclient


class SMBCrawler:
    """Classe principale pour le crawler SMB."""

    def __init__(self, server, username, password, share_name, domain='', db_path='openindex.db', max_workers=4, delay_between_requests=0.1, max_queue_size=1000, max_depth=None):
        """
        Initialise le crawler SMB.

        Args:
            server (str): Adresse du serveur SMB.
            username (str): Nom d'utilisateur pour la connexion.
            password (str): Mot de passe pour la connexion.
            share_name (str): Nom du partage SMB à parcourir.
            domain (str): Domaine pour la connexion.
            db_path (str): Chemin vers la base de données SQLite.
        """
        self.server = server
        self.username = username
        self.password = password
        self.share_name = share_name
        self.domain = domain
        self.db_path = db_path
        self.max_workers = max_workers
        self.delay_between_requests = delay_between_requests
        self.max_queue_size = max_queue_size
        self.max_depth = max_depth
        
        # Queues pour la gestion des tâches
        self.directory_queue = Queue(maxsize=max_queue_size)
        self.file_queue = Queue(maxsize=max_queue_size)
        self.result_queue = Queue()
        
        # Statistiques
        self.stats = {
            'total_directories': 0,
            'processed_directories': 0,
            'total_files': 0,
            'processed_files': 0,
            'errors': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Contrôle du flux
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        self.load_credentials()
        self.configure_smbclient()

    def load_credentials(self):
        """
        Charge les informations d'identification depuis le fichier .smb-credential.
        """
        try:
            with open('.smb-credential', 'r') as f:
                for line in f:
                    if line.startswith('username='):
                        self.username = line.split('=')[1].strip()
                    elif line.startswith('password='):
                        self.password = line.split('=')[1].strip()
                    elif line.startswith('domain='):
                        self.domain = line.split('=')[1].strip()
        except FileNotFoundError:
            print("Aucun fichier .smb-credential trouvé, utilisation des informations fournies.")

    def configure_smbclient(self):
        """
        Configure smbclient avec les informations d'identification.
        """
        smbclient.ClientConfig(
            username=self.username,
            password=self.password,
            domain=self.domain
        )

    def get_stats(self):
        """
        Retourne les statistiques actuelles du crawler.
        
        Returns:
            dict: Statistiques du crawler.
        """
        stats = self.stats.copy()
        if stats['start_time']:
            stats['elapsed_time'] = time.time() - stats['start_time']
            stats['directories_per_second'] = stats['processed_directories'] / stats['elapsed_time'] if stats['elapsed_time'] > 0 else 0
            stats['files_per_second'] = stats['processed_files'] / stats['elapsed_time'] if stats['elapsed_time'] > 0 else 0
        
        # Ajouter les tailles des queues
        stats['queue_size_directories'] = self.directory_queue.qsize()
        stats['queue_size_files'] = self.file_queue.qsize()
        stats['queue_size_results'] = self.result_queue.qsize()
        
        # Estimation du temps restant
        remaining_dirs = stats['total_directories'] - stats['processed_directories']
        if stats['directories_per_second'] > 0:
            stats['estimated_remaining_time'] = remaining_dirs / stats['directories_per_second']
        else:
            stats['estimated_remaining_time'] = None
            
        return stats
    
    def pause(self):
        """Met en pause le crawler."""
        self.pause_event.set()
        
    def resume(self):
        """Reprend le crawler."""
        self.pause_event.clear()
        
    def stop(self):
        """Arrête le crawler."""
        self.stop_event.set()
    
    def _directory_worker(self):
        """
        Worker thread pour traiter les répertoires.
        """
        while not self.stop_event.is_set():
            try:
                # Vérifier si on est en pause
                if self.pause_event.is_set():
                    time.sleep(0.1)
                    continue
                    
                # Récupérer un répertoire à traiter
                current_path = self.directory_queue.get(timeout=1)
                self.stats['last_activity'] = time.time()
                
                # Temporisation entre les requêtes
                if self.stats['last_activity'] and self.stats['last_activity'] != self.stats.get('start_time'):
                    time.sleep(self.delay_between_requests)
                
                # Construire le chemin UNC
                if current_path:
                    unc_path = f"\\\\{self.server}\\{self.share_name}\\{current_path}"
                else:
                    unc_path = f"\\\\{self.server}\\{self.share_name}"
                
                print(f"🔍 Chemin UNC testé : {unc_path}")
                
                # Lister les fichiers dans le répertoire courant
                try:
                    files = list(smbclient.scandir(unc_path))
                    self.stats['processed_directories'] += 1
                except Exception as e:
                    error_msg = f"Erreur lors de l'accès au répertoire {unc_path}: {e}"
                    print(error_msg)
                    
                    # Si erreur d'accès, arrêter le crawler
                    if "NtStatus error returned" in str(e):
                        print(f"\n🛑 Erreur d'accès détectée : {e}")
                        print("🛑 Arrêt du crawler suite à l'erreur d'accès")
                        self.stop()
                        break
                    
                    self.stats['errors'] += 1
                    continue
                
                # Traiter les fichiers et sous-répertoires
                for file_info in files:
                    if file_info.name in ['.', '..']:
                        continue
                    
                    file_data = {
                        "path": current_path + '\\' + file_info.name if current_path else file_info.name,
                        "name": file_info.name,
                        "size": file_info.stat().st_size,
                        "last_modified": datetime.fromtimestamp(file_info.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        "is_directory": file_info.is_dir(),
                        "depth": current_path.count('\\') if current_path else 0
                    }
                    
                    if file_data["is_directory"]:
                        # Vérifier la profondeur maximale
                        if self.max_depth is None or file_data["depth"] < self.max_depth:
                            # Ajouter le sous-répertoire à la queue pour exploration
                            self.directory_queue.put(file_data["path"])
                            self.stats['total_directories'] += 1
                            
                            # ET ajouter le dossier à la queue de résultats pour sauvegarde
                            self.result_queue.put(file_data)
                        else:
                            print(f"🚫 Profondeur maximale ({self.max_depth}) atteinte pour : {file_data['path']}")
                            # Même les dossiers à la profondeur max doivent être sauvegardés
                            self.result_queue.put(file_data)
                    else:
                        # Ajouter le fichier à la queue de traitement
                        self.file_queue.put(file_data)
                        self.stats['total_files'] += 1
                
                self.directory_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                print(f"Erreur dans le directory worker: {e}")
                self.stats['errors'] += 1
    
    def _file_worker(self):
        """
        Worker thread pour traiter les fichiers (calcul de checksum).
        """
        while not self.stop_event.is_set():
            try:
                # Vérifier si on est en pause
                if self.pause_event.is_set():
                    time.sleep(0.1)
                    continue
                    
                # Récupérer un fichier à traiter
                file_data = self.file_queue.get(timeout=1)
                self.stats['last_activity'] = time.time()
                
                # Temporisation entre les requêtes
                time.sleep(self.delay_between_requests)
                
                # Calculer le checksum
                try:
                    if file_data['path']:
                        file_unc_path = f"\\\\{self.server}\\{self.share_name}\\{file_data['path']}"
                    else:
                        file_unc_path = f"\\\\{self.server}\\{self.share_name}"
                    with smbclient.open_file(file_unc_path, mode='rb') as f:
                        sha256_hash = hashlib.sha256()
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                        file_data["checksum"] = sha256_hash.hexdigest()
                    
                    self.stats['processed_files'] += 1
                    print(f"✅ Fichier traité: {file_data['path']}")
                    
                except Exception as e:
                    error_msg = f"Erreur lors du calcul du checksum pour {file_data['path']}: {e}"
                    print(f"❌ {error_msg}")
                    
                    # Si erreur d'accès au fichier, arrêter le crawler
                    if "NtStatus error returned" in str(e):
                        print(f"\n🛑 Erreur d'accès fichier détectée : {e}")
                        print("🛑 Arrêt du crawler suite à l'erreur d'accès")
                        self.stop()
                        break
                    
                    # Continuer le traitement même en cas d'erreur
                    self.stats['processed_files'] += 1
                    print(f"❌ {error_msg}")
                    self.stats['errors'] += 1
                    file_data["checksum"] = None
                    file_data["error"] = str(e)
                    
                    # Continuer le traitement même en cas d'erreur
                    self.stats['processed_files'] += 1
                
                # Mettre le résultat dans la queue
                self.result_queue.put(file_data)
                self.file_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                print(f"Erreur dans le file worker: {e}")
                self.stats['errors'] += 1
    def crawl(self, base_path="", progress_callback=None):
        """
        Parcourt les fichiers dans le partage SMB avec queues multi-threadées et temporisation.

        Args:
            base_path (str): Chemin de base pour le crawl.
            progress_callback (callable): Fonction appelée périodiquement avec les statistiques.

        Yields:
            dict: Métadonnées des fichiers.
        """
        # Réinitialiser les statistiques
        self.stats = {
            'total_directories': 0,
            'processed_directories': 0,
            'total_files': 0,
            'processed_files': 0,
            'errors': 0,
            'start_time': time.time(),
            'last_activity': None
        }
        
        # Vider les queues
        while not self.directory_queue.empty():
            try:
                self.directory_queue.get_nowait()
            except Empty:
                break
                
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except Empty:
                break
                
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except Empty:
                break
        
        # Initialiser la queue avec le chemin de base
        self.directory_queue.put(base_path)
        self.stats['total_directories'] = 1
        
        # Démarrer les workers
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Calculer le nombre de workers pour chaque type
            if self.max_workers == 1:
                # Avec un seul worker, il gère tout
                dir_workers_count = 1
                file_workers_count = 1
            elif self.max_workers <= 3:
                # Pour petits nombres : plus de workers répertoires
                dir_workers_count = max(1, self.max_workers - 1)
                file_workers_count = 1
            else:
                # Pour plus de workers : 2/3 pour répertoires, 1/3 pour fichiers
                dir_workers_count = max(2, (self.max_workers * 2) // 3)
                file_workers_count = max(1, self.max_workers - dir_workers_count)
            
            # Lancer les workers de répertoires
            directory_workers = []
            for i in range(dir_workers_count):
                worker = executor.submit(self._directory_worker)
                directory_workers.append(worker)
            
            # Lancer les workers de fichiers
            file_workers = []
            for i in range(file_workers_count):
                worker = executor.submit(self._file_worker)
                file_workers.append(worker)
            
            # Thread pour sauvegarder les résultats
            def result_saver():
                batch_size = 100
                batch = []
                
                while not self.stop_event.is_set():
                    try:
                        # Récupérer un résultat
                        file_data = self.result_queue.get(timeout=1)
                        batch.append(file_data)
                        
                        # Sauvegarder par lots
                        if len(batch) >= batch_size:
                            self._save_batch(batch)
                            batch = []
                            
                        # Callback de progression
                        if progress_callback and len(batch) % 10 == 0:
                            progress_callback(self.get_stats())
                        
                        self.result_queue.task_done()
                        
                    except Empty:
                        # Sauvegarder le batch restant
                        if batch:
                            self._save_batch(batch)
                            batch = []
                        continue
                    except Exception as e:
                        print(f"Erreur dans le result saver: {e}")
                        self.stats['errors'] += 1
            
            saver_thread = threading.Thread(target=result_saver)
            saver_thread.daemon = True
            saver_thread.start()
            
            # Attendre que toutes les queues soient vides
            try:
                last_activity_time = time.time()
                no_progress_count = 0
                
                while True:
                    time.sleep(1)
                    
                    # Vérifier si on doit s'arrêter
                    if self.stop_event.is_set():
                        break
                    
                    # Récupérer les statistiques actuelles
                    current_stats = self.get_stats()
                    
                    # Détecter si plus aucune progression
                    if (current_stats['processed_directories'] == self.stats['processed_directories'] and 
                        current_stats['processed_files'] == self.stats['processed_files']):
                        no_progress_count += 1
                    else:
                        no_progress_count = 0
                        self.stats.update(current_stats)
                    
                    # Si pas de progression depuis 60 secondes ET queues vides => terminé
                    if (no_progress_count > 60 and 
                        current_stats['queue_size_directories'] == 0 and 
                        current_stats['queue_size_files'] == 0 and
                        current_stats['queue_size_results'] == 0):
                        print("\n🏁 Plus de progression depuis 60s et toutes les queues vides - Fin du crawl")
                        break
                    
                    # Si toutes les queues sont vides ET qu'on a traité tous les répertoires découverts
                    if (current_stats['queue_size_directories'] == 0 and 
                        current_stats['queue_size_files'] == 0 and 
                        current_stats['queue_size_results'] == 0 and
                        current_stats['processed_directories'] > 0):
                        print("\n🏁 Toutes les queues sont vides - Fin du crawl")
                        break
                    
                    # Timeout de sécurité (20 minutes sans activité)
                    if time.time() - last_activity_time > 1200:
                        print("\n⏰ Timeout de sécurité (20 min) - Fin du crawl")
                        break
                    
                    # Callback de progression
                    if progress_callback:
                        progress_callback(current_stats)
                        
            except KeyboardInterrupt:
                print("\nInterruption du crawler...")
                self.stop()
            
            # Arrêter proprement
            self.stop()
            
            # Sauvegarder les derniers résultats
            try:
                while not self.result_queue.empty():
                    file_data = self.result_queue.get_nowait()
                    self.save_to_db(file_data)
                    self.result_queue.task_done()
            except Empty:
                pass
    
    def _should_skip_file(self, file_data, cursor):
        """
        Vérifie si un fichier doit être ignoré car déjà existant avec les mêmes caractéristiques.
        
        Args:
            file_data (dict): Données du fichier à vérifier
            cursor: Curseur de base de données
            
        Returns:
            tuple: (should_skip, reason)
        """
        # Pour les répertoires, toujours traiter (structure peut changer)
        if file_data["is_directory"]:
            return False, None
        
        # Vérifier si le fichier existe déjà au même chemin
        cursor.execute("""
            SELECT id, size, last_modified, checksum 
            FROM files 
            WHERE path = ? AND is_directory = 0
        """, (file_data["path"],))
        
        existing_file = cursor.fetchone()
        
        if existing_file:
            existing_id, existing_size, existing_modified, existing_checksum = existing_file
            
            # Critères de comparaison complets
            size_match = existing_size == file_data["size"]
            modified_match = existing_modified == file_data["last_modified"]
            name_match = True  # Le chemin est identique donc le nom aussi
            
            # Si tous les critères correspondent, le fichier n'a pas changé
            if size_match and modified_match and name_match:
                return True, "Fichier identique (même chemin, taille, et date de modification)"
            
            # Si la taille ou la date a changé, mettre à jour
            if not size_match or not modified_match:
                # Supprimer l'ancien enregistrement et permettre la mise à jour
                cursor.execute("DELETE FROM files WHERE id = ?", (existing_id,))
                print(f"🔄 Fichier modifié détecté: {file_data['name']}")
                print(f"   Ancienne taille: {existing_size}, Nouvelle: {file_data['size']}")
                print(f"   Ancienne date: {existing_modified}")
                print(f"   Nouvelle date: {file_data['last_modified']}")
                return False, "Fichier modifié - mise à jour requise"
        
        return False, None
    
    def _check_duplicates(self, file_data, cursor):
        """
        Vérifie si un fichier est un doublon basé sur le checksum.
        
        Args:
            file_data (dict): Données du fichier à vérifier
            cursor: Curseur de base de données
            
        Returns:
            list: Liste des chemins des doublons existants
        """
        if file_data["is_directory"] or not file_data.get("checksum"):
            return []
        
        cursor.execute("""
            SELECT path FROM files 
            WHERE checksum = ? AND is_directory = 0 AND path != ?
        """, (file_data["checksum"], file_data["path"]))
        
        duplicates = [dup[0] for dup in cursor.fetchall()]
        return duplicates
    
    def _save_batch(self, batch):
        """
        Sauvegarde un batch de fichiers dans la base de données avec déduplication intelligente.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for file_data in batch:
                # Vérifier si le fichier doit être ignoré (logique complète)
                should_skip, skip_reason = self._should_skip_file(file_data, cursor)
                
                if should_skip:
                    print(f"⏭️  Ignoré: {file_data['name']} - {skip_reason}")
                    continue
                
                # Vérifier les doublons par checksum
                duplicates = self._check_duplicates(file_data, cursor)
                
                if duplicates:
                    # C'est un doublon de contenu mais à un endroit différent
                    print(f"🔄 Doublon détecté: {file_data['name']}")
                    print(f"   Nouvel emplacement: {file_data['path']}")
                    print(f"   Déjà présent à: {', '.join(duplicates[:3])}{'...' if len(duplicates) > 3 else ''}")
                    
                    # Marquer comme doublon mais quand même l'insérer
                    file_data["is_duplicate"] = True
                    file_data["duplicate_of"] = duplicates[0]  # Premier emplacement connu
                else:
                    file_data["is_duplicate"] = False
                    file_data["duplicate_of"] = None
                
                # Insérer le fichier
                cursor.execute("""
                    INSERT INTO files (path, name, size, checksum, last_modified, is_directory, is_duplicate, duplicate_of)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_data["path"],
                    file_data["name"],
                    file_data["size"],
                    file_data.get("checksum"),
                    file_data["last_modified"],
                    file_data["is_directory"],
                    file_data.get("is_duplicate", False),
                    file_data.get("duplicate_of")
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du batch: {e}")
            self.stats['errors'] += 1
            
    def init_db(self):
        """
        Initialise la base de données SQLite avec les tables nécessaires.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                size INTEGER,
                checksum TEXT,
                last_modified TEXT,
                is_directory BOOLEAN NOT NULL DEFAULT 0,
                is_duplicate BOOLEAN DEFAULT 0,
                duplicate_of TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()


    def save_to_db(self, file_data):
        """
        Enregistre les métadonnées d'un fichier dans la base de données.

        Args:
            file_data (dict): Métadonnées du fichier.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO files (path, name, size, checksum, last_modified, is_directory)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_data["path"],
                file_data["name"],
                file_data["size"],
                file_data.get("checksum"),
                file_data["last_modified"],
                file_data["is_directory"]
            ))
            conn.commit()
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion en base : {e}")
            print(f"   Path: {file_data.get('path', 'N/A')}")
        finally:
            conn.close()


if __name__ == "__main__":
    import sys
    
    def progress_callback(stats):
        """Callback pour afficher la progression."""
        print(f"\rRépertoires: {stats['processed_directories']}/{stats['total_directories']} "
              f"Fichiers: {stats['processed_files']}/{stats['total_files']} "
              f"Erreurs: {stats['errors']} "
              f"Temps restant: {stats.get('estimated_remaining_time', 0):.1f}s", end="")
        sys.stdout.flush()
    
    # Exemple d'utilisation avec le nouveau système de queues
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="adminsmiden",
        password="Us52uK",
        share_name="Public/SEPM",
        domain="SMIDEN",
        max_workers=4,           # 4 threads au total
        delay_between_requests=0.1,  # 100ms entre les requêtes
        max_queue_size=1000      # Maximum 1000 éléments en queue
    )

    print("Initialisation de la base de données...")
    crawler.init_db()
    
    print("\nDémarrage du crawl récursif complet...")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        crawler.crawl(base_path="", progress_callback=progress_callback)
        print("\n\nCrawl terminé!")
        
        # Afficher les statistiques finales
        final_stats = crawler.get_stats()
        print(f"\nStatistiques finales:")
        print(f"- Répertoires traités: {final_stats['processed_directories']}")
        print(f"- Fichiers traités: {final_stats['processed_files']}")
        print(f"- Erreurs: {final_stats['errors']}")
        print(f"- Temps total: {final_stats.get('elapsed_time', 0):.2f}s")
        
    except KeyboardInterrupt:
        print("\n\nCrawl interrompu par l'utilisateur.")
        
        # Afficher les statistiques partielles
        partial_stats = crawler.get_stats()
        print(f"\nStatistiques partielles:")
        print(f"- Répertoires traités: {partial_stats['processed_directories']}")
        print(f"- Fichiers traités: {partial_stats['processed_files']}")
        print(f"- Erreurs: {partial_stats['errors']}")