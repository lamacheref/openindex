#!/usr/bin/env python3
"""
Script de base pour le crawler SMB avec pagination et indexation progressive.
Ce script utilise la bibliothèque smbclient pour parcourir les partages SMB.
"""

import os
import hashlib
import sqlite3
from datetime import datetime
import smbclient


class SMBCrawler:
    """Classe principale pour le crawler SMB."""

    def __init__(self, server, username, password, share_name, domain='', db_path='openindex.db'):
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

    def calculate_sha256(self, file_path):
        """
        Calcule le checksum SHA-256 d'un fichier.

        Args:
            file_path (str): Chemin vers le fichier.

        Returns:
            str: Checksum SHA-256 du fichier.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def init_db(self):
        """
        Initialise la base de données SQLite avec les tables nécessaires.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                size INTEGER,
                checksum TEXT,
                last_modified TEXT,
                is_directory BOOLEAN
            )
        """)
        conn.commit()
        conn.close()

    def crawl(self, base_path="", page_size=100):
        """
        Parcourt les fichiers dans le partage SMB avec pagination.

        Args:
            base_path (str): Chemin de base pour le crawl.
            page_size (int): Nombre de fichiers à traiter par page.

        Yields:
            dict: Métadonnées des fichiers.
        """
        # Construire le chemin UNC
        unc_path = f"\\\\{self.server}\\{self.share_name}\\{base_path}"
        
        # Lister les fichiers dans le répertoire de base
        files = list(smbclient.scandir(unc_path))

        for i in range(0, len(files), page_size):
            page = files[i:i + page_size]
            for file_info in page:
                if file_info.name in ['.', '..']:
                    continue

                file_data = {
                    "path": os.path.join(base_path, file_info.name),
                    "name": file_info.name,
                    "size": file_info.stat().st_size,
                    "last_modified": datetime.fromtimestamp(file_info.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    "is_directory": file_info.is_dir()
                }

                # Calculer le checksum uniquement pour les fichiers
                if not file_data["is_directory"]:
                    # Construire le chemin complet du fichier sur le partage SMB
                    file_unc_path = f"\\\\{self.server}\\{self.share_name}\\{file_data['path']}"
                    # Ouvrir le fichier via smbclient
                    with smbclient.open_file(file_unc_path, mode='rb') as f:
                        sha256_hash = hashlib.sha256()
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                        file_data["checksum"] = sha256_hash.hexdigest()

                yield file_data

    def save_to_db(self, file_data):
        """
        Enregistre les métadonnées d'un fichier dans la base de données.

        Args:
            file_data (dict): Métadonnées du fichier.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (path, name, size, checksum, last_modified, is_directory)
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
        conn.close()


if __name__ == "__main__":
    # Exemple d'utilisation
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere",
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN"
    )

    crawler.init_db()
    for file_data in crawler.crawl(base_path="SMIDEN/Technique", page_size=10):
        print(f"Indexation de {file_data['path']}")
        crawler.save_to_db(file_data)