"""
Utilitaires de crawl SMB pour l'indexeur - Version simplifiée avec smbclient
"""
import os
import logging
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SMBClient:
    """Client SMB utilisant smbclient via subprocess"""
    
    def __init__(self, host: str, share: str, username: str, password: str, domain: str = ""):
        self.host = host
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain or "WORKGROUP"
        self.connected = False
        self._share_url = f"//{host}/{share}"
    
    def connect(self) -> bool:
        """Test la connexion SMB avec smbclient"""
        try:
            # Test simple avec smbclient -L pour lister les partages
            cmd = [
                'smbclient',
                '-L', self.host,
                '-U', f"{self.username}%",
                '-W', self.domain
            ]
            
            # Ajouter le mot de passe via variable d'environnement pour éviter l'affichage dans ps
            env = os.environ.copy()
            env['PASSWD'] = self.password
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            if result.returncode == 0:
                self.connected = True
                logger.info(f"Connecté à {self._share_url}")
                return True
            else:
                logger.error(f"Erreur connexion SMB: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur connexion SMB à {self.host}/{self.share}: {e}")
            return False
    
    def disconnect(self):
        """Déconnexion (aucune action nécessaire avec subprocess)"""
        self.connected = False
        logger.info(f"Déconnecté de {self._share_url}")
    
    def list_dir(self, remote_path: str = "") -> List[Dict[str, Any]]:
        """Liste le contenu d'un répertoire distant avec smbclient"""
        entries = []
        try:
            path = normalize_smb_path(remote_path)
            
            # Construire la commande smbclient
            full_path = f"{self._share_url}/{path}" if path else self._share_url
            
            cmd = [
                'smbclient', full_path,
                '-U', f"{self.username}",
                '-W', self.domain,
                '-c', 'ls'
            ]
            
            # Passer le mot de passe via stdin
            result = subprocess.run(
                cmd,
                input=f"{self.password}\n",
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Erreur listage {remote_path}: {result.stderr}")
                return entries
            
            # Parser la sortie de smbclient
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('.') or 'blocks of size' in line:
                    continue
                
                # Format typique: "filename                     D      0  Mon Jan  1 00:00:00 2024"
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[0]
                    is_dir = parts[1] == 'D' if len(parts) > 1 else False
                    size_str = parts[2] if len(parts) > 2 else '0'
                    
                    try:
                        size = int(size_str)
                    except:
                        size = 0
                    
                    entries.append({
                        'name': name,
                        'is_directory': is_dir,
                        'size': size if not is_dir else 0,
                        'mtime': datetime.now(),  # Simplifié
                        'path': f"{path}/{name}".lstrip('/') if path else name
                    })
            
            logger.info(f"Listé {len(entries)} entrées dans {remote_path or 'root'}")
            
        except Exception as e:
            logger.error(f"Erreur listage {remote_path}: {e}")
        
        return entries
    
    def file_exists(self, remote_path: str) -> bool:
        """Vérifie si un fichier existe"""
        try:
            path = normalize_smb_path(remote_path)
            dir_path = os.path.dirname(path) if '/' in path else ''
            file_name = os.path.basename(path)
            
            entries = self.list_dir(dir_path)
            return any(e['name'] == file_name for e in entries)
            
        except:
            return False


def normalize_smb_path(path: str) -> str:
    """Normalise un chemin SMB (retire les slashes initiaux/finaux)"""
    if not path:
        return ""
    path = path.replace('\\', '/')
    path = path.strip('/')
    return path


def get_file_info(client: SMBClient, remote_path: str) -> Optional[Dict[str, Any]]:
    """Récupère les informations d'un fichier distant"""
    try:
        path = normalize_smb_path(remote_path)
        dir_path = os.path.dirname(path) if '/' in path else ''
        file_name = os.path.basename(path)
        
        entries = client.list_dir(dir_path)
        for entry in entries:
            if entry['name'] == file_name:
                return {
                    'path': path,
                    'name': entry['name'],
                    'is_directory': entry['is_directory'],
                    'size': entry['size'],
                    'created_at': entry['mtime'],
                    'modified_at': entry['mtime'],
                    'checksum': None
                }
        
        return None
        
    except Exception as e:
        logger.warning(f"Impossible d'obtenir les infos de {remote_path}: {e}")
        return None
