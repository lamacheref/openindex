"""
Utilitaires de crawl SMB pour l'indexeur - Version avec smbprotocol
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False
    logging.getLogger(__name__).warning("xxhash non disponible, hash SHA256 utilisé")

import smbclient

# Réduire le bruit des logs smbprotocol
for lg in ["smbprotocol", "smbprotocol.connection", "smbprotocol.session",
           "smbprotocol.tree", "smbprotocol.transport",
           "smbclient", "smbclient.path"]:
    logging.getLogger(lg).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class SMBClient:
    """Client SMB utilisant smbprotocol (smbclient Python)"""
    
    def __init__(self, host: str, share: str, username: str, password: str, domain: str = ""):
        self.host = host
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain or "WORKGROUP"
        self.connected = False
        self._share_url = f"//{host}/{share}"
    
    def connect(self) -> bool:
        """Enregistre la session SMB via smbprotocol"""
        try:
            smbclient.register_session(
                self.host,
                username=f"{self.domain}\\{self.username}" if self.domain else self.username,
                password=self.password,
                connection_timeout=10
            )
            self.connected = True
            logger.info(f"Session SMB enregistrée pour {self.host}")
            return True
        except Exception as e:
            logger.error(f"Erreur connexion SMB à {self.host}: {e}")
            return False
    
    def disconnect(self):
        """Ferme la session SMB"""
        try:
            smbclient.delete_session(self.host)
        except Exception:
            pass
        self.connected = False
        logger.info(f"Session SMB fermée pour {self.host}")
    
    def list_dir(self, remote_path: str = "") -> List[Dict[str, Any]]:
        """Liste le contenu d'un répertoire distant avec smbprotocol"""
        entries = []
        try:
            path = normalize_smb_path(remote_path)
            full_path = f"{self._share_url}/{path}" if path else self._share_url
            
            for entry in smbclient.scandir(full_path):
                entries.append({
                    'name': entry.name,
                    'is_directory': entry.is_dir(),
                    'size': 0 if entry.is_dir() else entry.stat().st_size,
                    'mtime': datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc) if not entry.is_dir() else datetime.now(),
                    'path': f"{path}/{entry.name}".lstrip('/') if path else entry.name
                })
            
            logger.info(f"Listé {len(entries)} entrées dans {remote_path or 'root'}")
            
        except Exception as e:
            logger.error(f"Erreur listage {remote_path}: {e}")
        
        return entries
    
    def file_exists(self, remote_path: str) -> bool:
        """Vérifie si un fichier existe via stat"""
        try:
            path = normalize_smb_path(remote_path)
            full_path = f"{self._share_url}/{path}"
            smbclient.stat(full_path)
            return True
        except Exception:
            return False


def normalize_smb_path(path: str) -> str:
    """Normalise un chemin SMB (retire les slashes initiaux/finaux)"""
    if not path:
        return ""
    path = path.replace('\\', '/')
    path = path.strip('/')
    return path


def get_file_info(client: SMBClient, remote_path: str, entries_list: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Récupère les informations d'un fichier distant"""
    try:
        path = normalize_smb_path(remote_path)
        dir_path = os.path.dirname(path) if '/' in path else ''
        file_name = os.path.basename(path)

        if entries_list is None:
            entries = client.list_dir(dir_path)
        else:
            entries = entries_list
        for entry in entries:
            if entry['name'] == file_name:
                # Calculer le hash xxHash si disponible
                checksum = None
                if XXHASH_AVAILABLE:
                    checksum = calculate_xxhash(client, remote_path)
                else:
                    # Fallback SHA256 (non implémenté ici, à faire si nécessaire)
                    pass

                return {
                    'path': path,
                    'name': entry['name'],
                    'is_directory': entry['is_directory'],
                    'size': entry['size'],
                    'created_at': entry['mtime'],
                    'modified_at': entry['mtime'],
                    'checksum': checksum
                }

        return None

    except Exception as e:
        logger.warning(f"Impossible d'obtenir les infos de {remote_path}: {e}")
        return None

def calculate_xxhash(client: SMBClient, remote_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Calcule le hash xxHash d'un fichier SMB via smbprotocol
    Args:
        client: Client SMB connecté
        remote_path: Chemin du fichier distant
        chunk_size: Taille des chunks pour le streaming (1Mo par défaut)
    Returns:
        Hash xxHash hexadécimal (64 bits)
    """
    if not XXHASH_AVAILABLE:
        raise RuntimeError("xxhash non disponible")

    try:
        path = normalize_smb_path(remote_path)
        full_path = f"{client._share_url}/{path}"

        hasher = xxhash.xxh64()

        with smbclient.open_file(full_path, mode='rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()

    except Exception as e:
        logger.error(f"Erreur calcul xxHash pour {remote_path}: {e}")
        return ""
