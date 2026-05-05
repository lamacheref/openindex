"""
Utilitaires de crawl SMB pour l'indexeur
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, CreateDisposition, FilePipePrinterAccessMask
from smbprotocol.file_information import FileInformationClass

logger = logging.getLogger(__name__)


class SMBClient:
    """Client SMB simplifié utilisant smbprotocol"""
    
    def __init__(self, host: str, share: str, username: str, password: str, domain: str = ""):
        self.host = host
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain or "WORKGROUP"
        self.connection = None
        self.session = None
        self.tree = None
        self.connected = False
    
    def connect(self) -> bool:
        """Établit la connexion SMB"""
        try:
            # Créer la connexion
            self.connection = Connection(self.host, self.host, 445)
            self.connection.connect()
            
            # Créer la session
            self.session = Session(
                self.connection,
                self.username,
                self.password,
                domain=self.domain
            )
            self.session.connect()
            
            # Connecter au partage
            share_path = f"\\\\{self.host}\\{self.share}"
            self.tree = TreeConnect(self.session, share_path)
            self.tree.connect()
            
            self.connected = True
            logger.info(f"Connecté à {share_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur connexion SMB à {self.host}/{self.share}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Ferme la connexion SMB"""
        try:
            if self.tree:
                self.tree.disconnect()
        except:
            pass
        try:
            if self.session:
                self.session.disconnect()
        except:
            pass
        try:
            if self.connection:
                self.connection.disconnect()
        except:
            pass
        self.connected = False
        logger.info(f"Déconnecté de {self.host}/{self.share}")
    
    def list_dir(self, remote_path: str = "") -> List[Dict[str, Any]]:
        """Liste le contenu d'un répertoire distant"""
        if not self.connected:
            raise ConnectionError("Non connecté au partage SMB")
        
        entries = []
        try:
            # Normaliser le chemin
            path = normalize_smb_path(remote_path)
            
            # Ouvrir le répertoire
            dir_open = Open(
                self.tree,
                path,
                desired_access=FilePipePrinterAccessMask.FILE_LIST_DIRECTORY,
                create_disposition=CreateDisposition.FILE_OPEN
            )
            dir_open.open()
            
            # Lister les entrées
            file_infos = dir_open.query_directory(
                pattern="*",
                file_information_class=FileInformationClass.FILE_BOTH_DIRECTORY_INFORMATION
            )
            
            for info in file_infos:
                name = info['file_name'].get_value().decode('utf-16-le').rstrip('\x00')
                if name in ('.', '..'):
                    continue
                
                is_dir = bool(info['file_attributes'].get_value() & 0x10)  # FILE_ATTRIBUTE_DIRECTORY
                size = info['end_of_file'].get_value()
                mtime = info['last_write_time'].get_value()
                
                # Convertir Windows FILETIME (100-nanosecond intervals since 1601) à datetime
                try:
                    mtime_dt = datetime.fromtimestamp((mtime - 116444736000000000) / 10000000)
                except:
                    mtime_dt = datetime.now()
                
                entries.append({
                    'name': name,
                    'is_directory': is_dir,
                    'size': size if not is_dir else 0,
                    'mtime': mtime_dt,
                    'path': f"{path}/{name}".lstrip('/')
                })
            
            dir_open.close()
            
        except Exception as e:
            logger.error(f"Erreur listage {remote_path}: {e}")
            raise
        
        return entries
    
    def file_exists(self, remote_path: str) -> bool:
        """Vérifie si un fichier existe"""
        try:
            path = normalize_smb_path(remote_path)
            file_open = Open(
                self.tree,
                path,
                desired_access=FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
                create_disposition=CreateDisposition.FILE_OPEN
            )
            file_open.open()
            file_open.close()
            return True
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
        
        # Ouvrir le fichier
        file_open = Open(
            client.tree,
            path,
            desired_access=FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
            create_disposition=CreateDisposition.FILE_OPEN
        )
        file_open.open()
        
        # Récupérer les informations
        info = file_open.get_file_information(FileInformationClass.FILE_BASIC_INFORMATION)
        
        file_open.close()
        
        # Extraire les attributs
        attrs = info['file_attributes'].get_value()
        is_dir = bool(attrs & 0x10)
        
        size = info['end_of_file'].get_value() if hasattr(info, 'end_of_file') else 0
        
        # Convertir les timestamps
        try:
            ctime = info['creation_time'].get_value()
            ctime_dt = datetime.fromtimestamp((ctime - 116444736000000000) / 10000000)
        except:
            ctime_dt = datetime.now()
        
        try:
            mtime = info['last_write_time'].get_value()
            mtime_dt = datetime.fromtimestamp((mtime - 116444736000000000) / 10000000)
        except:
            mtime_dt = datetime.now()
        
        return {
            'path': path,
            'name': os.path.basename(path),
            'is_directory': is_dir,
            'size': size,
            'created_at': ctime_dt,
            'modified_at': mtime_dt,
            'checksum': None  # Calculé plus tard si nécessaire
        }
        
    except Exception as e:
        logger.warning(f"Impossible d'obtenir les infos de {remote_path}: {e}")
        return None
