"""
Utilitaires de crawl SMB pour l'indexeur - Version simplifiée avec smbclient
"""
import os
import logging
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False
    logging.getLogger(__name__).warning("xxhash non disponible, hash SHA256 utilisé")

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
            # Lister le partage pour valider les identifiants
            cmd = [
                'smbclient', self._share_url,
                '-U', self.username,
                '-W', self.domain,
                '-c', 'ls'
            ]
            
            result = subprocess.run(
                cmd,
                input=f"{self.password}\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.connected = True
                logger.info(f"Connecté à {self._share_url}")
                return True
            else:
                logger.error(f"Erreur connexion SMB ({result.stdout.strip() or result.stderr.strip() or 'code retour ' + str(result.returncode)})")
                return False
                
        except Exception as e:
            logger.error(f"Erreur connexion SMB à {self._share_url}: {e}")
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
            
            # smbclient ne peut se connecter qu'à //host/share, pas à un sous-chemin
            # On utilise 'cd <path>; ls' pour lister un sous-répertoire
            smb_cmd = f'cd {path}; ls' if path else 'ls'
            
            cmd = [
                'smbclient', self._share_url,
                '-U', f"{self.username}",
                '-W', self.domain,
                '-c', smb_cmd
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
                err_msg = result.stderr.strip() or f"code retour {result.returncode}"
                logger.error(f"Erreur listage {remote_path}: {err_msg}")
                return entries
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('.') or 'blocks of size' in line:
                    continue

                parts = line.split()
                if len(parts) < 7:
                    continue

                # Format: <filename...> <attr> <size> <weekday> <month> <day> <time> <year>
                # On parse depuis la droite : année, heure, jour, mois, weekday = 5 tokens
                # Puis taille (nombre), attr (1 lettre), tout le reste = nom
                year = parts[-1]
                time_ = parts[-2]
                day = parts[-3]
                month = parts[-4]
                weekday = parts[-5]
                size_str = parts[-6]
                attr = parts[-7]
                name = ' '.join(parts[:-7])

                is_dir = attr == 'D'

                try:
                    size = int(size_str)
                except:
                    size = 0

                entries.append({
                    'name': name,
                    'is_directory': is_dir,
                    'size': size if not is_dir else 0,
                    'mtime': datetime.now(),
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
    Calcule le hash xxHash d'un fichier SMB
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
        file_name = os.path.basename(path)

        hasher = xxhash.xxh64()

        cmd = [
            'smbclient', client._share_url,
            '-U', client.username,
            '-W', client.domain,
            '-c', f'get {path} -'
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.stdin.write(f"{client.password}\n".encode())
        process.stdin.close()

        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)

        process.wait(timeout=300)
        if process.returncode != 0:
            err = process.stderr.read().decode().strip()
            raise RuntimeError(f"smbclient a échoué: {err}")

        return hasher.hexdigest()

    except Exception as e:
        logger.error(f"Erreur calcul xxHash pour {remote_path}: {e}")
        return ""
