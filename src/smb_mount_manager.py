"""
Gestionnaire de montages SMB dynamiques avec timeout d'inactivité.
Monte les partages SMB à la volée et les démonte après inactivité.
"""
import os
import time
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, NamedTuple
from pathlib import Path
import logging
import atexit

logger = logging.getLogger(__name__)


class MountInfo(NamedTuple):
    """Informations sur un montage SMB."""
    server: str
    share: str
    mount_point: Path
    last_access: datetime
    config_id: str


class SMBMountManager:
    """
    Gère les montages SMB dynamiques dans /tmp/smb_mnt/
    Démonte automatiquement après 30min d'inactivité.
    """
    
    IDLE_TIMEOUT_MINUTES = 30
    CHECK_INTERVAL_SECONDS = 60
    
    def __init__(self):
        self.mount_base = Path("/tmp/smb_mnt")
        self._mounts: Dict[str, MountInfo] = {}  # config_id -> MountInfo
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None
        
        # Créer le répertoire de base
        self.mount_base.mkdir(parents=True, exist_ok=True)
        
        # Démarrer le thread de nettoyage
        self._start_cleanup_thread()
        
        # Nettoyage à la sortie
        atexit.register(self.stop)
        
        logger.info(f"SMBMountManager initialisé (base: {self.mount_base})")
    
    def _start_cleanup_thread(self):
        """Démarre le thread de nettoyage périodique."""
        def cleanup_loop():
            while not self._stop_event.wait(self.CHECK_INTERVAL_SECONDS):
                self._cleanup_idle_mounts()
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def stop(self):
        """Arrête le gestionnaire et démonte tous les partages."""
        logger.info("Arrêt du SMBMountManager...")
        self._stop_event.set()
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        # Démonter tous les partages
        with self._lock:
            for config_id in list(self._mounts.keys()):
                self._unmount(config_id)
        
        logger.info("SMBMountManager arrêté")
    
    def _get_mount_point(self, config_id: str, server: str, share: str) -> Path:
        """Génère un point de montage unique et sûr."""
        # Nettoyer les caractères spéciaux
        safe_server = server.replace(".", "_").replace(":", "_")
        safe_share = share.replace("\\", "_").replace("/", "_")
        mount_name = f"{config_id}_{safe_server}_{safe_share}"
        return self.mount_base / mount_name
    
    def _is_mounted(self, mount_point: Path) -> bool:
        """Vérifie si un point est déjà monté."""
        try:
            result = subprocess.run(
                ["mountpoint", "-q", str(mount_point)],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _mount(self, server: str, share: str, username: str, password: str,
               domain: str, mount_point: Path) -> bool:
        """Monte un partage SMB avec mount.cifs."""
        try:
            # Créer le point de montage
            mount_point.mkdir(parents=True, exist_ok=True)
            
            # Vérifier si déjà monté
            if self._is_mounted(mount_point):
                logger.debug(f"Déjà monté: {mount_point}")
                return True
            
            # Construire le chemin UNC
            unc_path = f"//{server}/{share.replace('\\', '/')}"
            
            # Options de montage sécurisées
            options = f"username={username},password={password},domain={domain},rw,iocharset=utf8,vers=3.0"
            
            logger.info(f"Montage de {unc_path} sur {mount_point}")
            
            result = subprocess.run(
                ["mount", "-t", "cifs", unc_path, str(mount_point), "-o", options],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Montage réussi: {mount_point}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Échec du montage {mount_point}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors du montage: {e}")
            return False
    
    def _unmount(self, config_id: str) -> bool:
        """Démonte un partage SMB."""
        with self._lock:
            if config_id not in self._mounts:
                return True
            
            mount_info = self._mounts[config_id]
            mount_point = mount_info.mount_point
            
            try:
                logger.info(f"Démontage de {mount_point}")
                
                subprocess.run(
                    ["umount", str(mount_point)],
                    capture_output=True,
                    check=True
                )
                
                # Supprimer le répertoire vide
                if mount_point.exists():
                    mount_point.rmdir()
                
                del self._mounts[config_id]
                logger.info(f"Démontage réussi: {mount_point}")
                return True
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Échec du démontage {mount_point}: {e.stderr}")
                # Forcer le démontage si busy
                try:
                    subprocess.run(
                        ["umount", "-l", str(mount_point)],
                        capture_output=True,
                        check=False
                    )
                    logger.warning(f"Démontage forcé: {mount_point}")
                    return True
                except Exception:
                    return False
            except Exception as e:
                logger.error(f"Erreur lors du démontage: {e}")
                return False
    
    def _cleanup_idle_mounts(self):
        """Démonte les partages inactifs depuis trop longtemps."""
        now = datetime.now()
        timeout = timedelta(minutes=self.IDLE_TIMEOUT_MINUTES)
        
        with self._lock:
            idle_mounts = [
                config_id for config_id, info in self._mounts.items()
                if (now - info.last_access) > timeout
            ]
        
        for config_id in idle_mounts:
            logger.info(f"Démontage pour inactivité: {config_id}")
            self._unmount(config_id)
    
    def get_mount_point(self, config: Dict) -> Optional[Path]:
        """
        Récupère ou crée un point de montage pour une configuration SMB.
        
        Args:
            config: Dict avec connection_server, connection_share, 
                   connection_username, connection_password, connection_domain, id
        
        Returns:
            Path du point de montage ou None si échec
        """
        config_id = config.get("id", "unknown")
        server = config.get("connection_server", "")
        share = config.get("connection_share", "")
        username = config.get("connection_username", "")
        password = config.get("connection_password", "")
        domain = config.get("connection_domain", "") or "WORKGROUP"
        
        if not all([server, share, username, password]):
            logger.error(f"Configuration SMB incomplète pour {config_id}")
            return None
        
        with self._lock:
            # Si déjà monté, mettre à jour l'accès
            if config_id in self._mounts:
                mount_info = self._mounts[config_id]
                self._mounts[config_id] = MountInfo(
                    server=mount_info.server,
                    share=mount_info.share,
                    mount_point=mount_info.mount_point,
                    last_access=datetime.now(),
                    config_id=config_id
                )
                return mount_info.mount_point
            
            # Nouveau montage
            mount_point = self._get_mount_point(config_id, server, share)
            
            if self._mount(server, share, username, password, domain, mount_point):
                self._mounts[config_id] = MountInfo(
                    server=server,
                    share=share,
                    mount_point=mount_point,
                    last_access=datetime.now(),
                    config_id=config_id
                )
                return mount_point
            
            return None
    
    def smb_path_to_local(self, smb_path: str, config: Dict) -> Optional[str]:
        """
        Convertit un chemin SMB en chemin local monté.
        
        Args:
            smb_path: Chemin UNC (ex: \\server\share\path\file.txt)
            config: Configuration SMB
        
        Returns:
            Chemin local ou None si échec
        """
        mount_point = self.get_mount_point(config)
        if not mount_point:
            return None
        
        # Extraire le chemin relatif
        server = config.get("connection_server", "")
        share = config.get("connection_share", "")
        
        # Formats possibles: \\server\share\path ou //server/share/path
        normalized = smb_path.replace("/", "\\")
        prefix = f"\\\\{server}\\{share}\\"
        
        if normalized.startswith(prefix):
            relative = normalized[len(prefix):]
        else:
            # Essayer sans le share complet
            prefix_short = f"\\\\{server}\\"
            if normalized.startswith(prefix_short):
                parts = normalized[len(prefix_short):].split("\\", 1)
                relative = parts[1] if len(parts) > 1 else ""
            else:
                logger.error(f"Chemin SMB ne correspond pas à la config: {smb_path}")
                return None
        
        local_path = mount_point / relative.replace("\\", "/")
        return str(local_path)
    
    def ensure_mounted(self, config: Dict) -> Optional[str]:
        """
        Vérifie qu'un partage est monté, le remonte si nécessaire.
        Retourne le chemin local ou None si impossible.
        """
        config_id = config.get("id", "unknown")
        
        with self._lock:
            # Vérifier si déjà monté et accessible
            if config_id in self._mounts:
                mount_info = self._mounts[config_id]
                
                # Vérifier que le montage est toujours valide
                if self._is_mounted(mount_info.mount_point):
                    # Mettre à jour l'accès
                    self._mounts[config_id] = MountInfo(
                        server=mount_info.server,
                        share=mount_info.share,
                        mount_point=mount_info.mount_point,
                        last_access=datetime.now(),
                        config_id=config_id
                    )
                    # Retourner le chemin local
                    return self.smb_path_to_local(config.get("connection_path", ""), config)
                else:
                    # Le montage n'est plus valide, supprimer de la liste
                    logger.warning(f"Montage invalide détecté pour {config_id}, suppression")
                    del self._mounts[config_id]
        
        # Pas monté ou montage invalide, tenter de monter
        logger.info(f"Remontage nécessaire pour {config_id}")
        return self.smb_path_to_local(config.get("connection_path", ""), config)
    
    def list_active_mounts(self) -> Dict[str, Dict]:
        """Liste les montages actifs avec leur temps d'inactivité."""
        now = datetime.now()
        with self._lock:
            # Vérifier l'état réel des montages
            active_mounts = {}
            for config_id, info in list(self._mounts.items()):
                if self._is_mounted(info.mount_point):
                    active_mounts[config_id] = {
                        "mount_point": str(info.mount_point),
                        "server": info.server,
                        "share": info.share,
                        "idle_minutes": (now - info.last_access).total_seconds() / 60
                    }
                else:
                    # Nettoyer les entrées obsolètes
                    logger.warning(f"Nettoyage du montage obsolète: {config_id}")
                    del self._mounts[config_id]
            return active_mounts


# Instance globale
_smb_mount_manager: Optional[SMBMountManager] = None


def get_mount_manager() -> SMBMountManager:
    """Récupère l'instance globale du gestionnaire de montages."""
    global _smb_mount_manager
    if _smb_mount_manager is None:
        _smb_mount_manager = SMBMountManager()
    return _smb_mount_manager


def stop_mount_manager():
    """Arrête proprement le gestionnaire de montages."""
    global _smb_mount_manager
    if _smb_mount_manager:
        _smb_mount_manager.stop()
        _smb_mount_manager = None


# Fonctions utilitaires simplifiées
def smb_to_local_path(smb_path: str, config: Dict) -> Optional[str]:
    """Convertit un chemin SMB en chemin local."""
    return get_mount_manager().smb_path_to_local(smb_path, config)


def ensure_mounted(config: Dict) -> Optional[str]:
    """
    Vérifie qu'un partage est monté, le remonte si nécessaire.
    Retourne le chemin local ou None si impossible.
    """
    return get_mount_manager().ensure_mounted(config)


def get_active_mounts() -> Dict[str, Dict]:
    """Liste les montages actifs."""
    return get_mount_manager().list_active_mounts()


def manual_unmount(config_id: str) -> bool:
    """Démonte manuellement un partage."""
    return get_mount_manager()._unmount(config_id)
