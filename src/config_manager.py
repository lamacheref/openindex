#!/usr/bin/env python3
"""
Configuration Manager pour OpenIndex
Gère la lecture sécurisée des credentials et configuration
"""

import configparser
import os
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """Gestionnaire de configuration sécurisé pour OpenIndex"""
    
    def __init__(self, config_path: str = None):
        """
        Initialise le gestionnaire de configuration
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        if config_path is None:
            # Chemin par défaut relatif au projet
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "admin_credentials.ini"
        
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.config_file_exists = False
        
        # Vérifier que le fichier existe et a les bons droits
        self._validate_config_file()
        
        # Charger la configuration
        if self.config_file_exists:
            self.config.read(self.config_path)
    
    def _validate_config_file(self):
        """Valide que le fichier de configuration existe et a les bons droits"""
        if not self.config_path.exists():
            self.config_file_exists = False
            return

        self.config_file_exists = True
        
        # Vérifier les droits (doit être 600 ou plus restrictif)
        file_stat = self.config_path.stat()
        file_mode = oct(file_stat.st_mode)[-3:]
        
        if file_mode != "600":
            print(f"⚠️  Attention: Le fichier {self.config_path} a des droits {file_mode}")
            print(f"   Recommandation: chmod 600 {self.config_path}")
    
    def get_smb_credentials(self) -> Dict[str, str]:
        """
        Retourne les credentials SMB de manière sécurisée
        
        Returns:
            Dictionnaire avec les credentials SMB
        """
        try:
            return {
                'username': os.getenv('OPENINDEX_SMB_USERNAME') or self.config.get('smb_credentials', 'username', fallback='adminsmiden'),
                'password': os.getenv('OPENINDEX_SMB_PASSWORD') or self.config.get('smb_credentials', 'password', fallback='Us52uK'),
                'domain': os.getenv('OPENINDEX_SMB_DOMAIN') or self.config.get('smb_credentials', 'domain', fallback='SMIDEN'),
                'server': os.getenv('OPENINDEX_SMB_SERVER') or self.config.get('smb_credentials', 'server', fallback='172.16.252.34'),
                'share_name': os.getenv('OPENINDEX_SMB_SHARE_NAME') or self.config.get('smb_credentials', 'share_name', fallback='Public\\SEPM')
            }
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Erreur de configuration SMB: {e}")
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """
        Retourne la configuration du crawler
        
        Returns:
            Dictionnaire avec la configuration du crawler
        """
        try:
            return {
                'max_workers': int(os.getenv('OPENINDEX_CRAWLER_MAX_WORKERS') or self.config.getint('crawler_config', 'max_workers', fallback=8)),
                'delay_between_requests': float(os.getenv('OPENINDEX_CRAWLER_DELAY_BETWEEN_REQUESTS') or self.config.getfloat('crawler_config', 'delay_between_requests', fallback=0.01)),
                'max_depth': int(os.getenv('OPENINDEX_CRAWLER_MAX_DEPTH') or self.config.getint('crawler_config', 'max_depth', fallback=32)),
                'large_file_threshold': int(os.getenv('OPENINDEX_CRAWLER_LARGE_FILE_THRESHOLD') or self.config.getint('crawler_config', 'large_file_threshold', fallback=104857600)),
                'max_queue_size': int(os.getenv('OPENINDEX_CRAWLER_MAX_QUEUE_SIZE') or self.config.getint('crawler_config', 'max_queue_size', fallback=10000)),
                'pre_estimation_enabled': (os.getenv('OPENINDEX_CRAWLER_PRE_ESTIMATION_ENABLED') or str(self.config.getboolean('crawler_config', 'pre_estimation_enabled', fallback=False))).lower() in {'1', 'true', 'yes', 'on'},
                'pre_estimation_mode': os.getenv('OPENINDEX_CRAWLER_PRE_ESTIMATION_MODE') or self.config.get('crawler_config', 'pre_estimation_mode', fallback='smb'),
                'pre_estimation_mount_path': os.getenv('OPENINDEX_CRAWLER_PRE_ESTIMATION_MOUNT_PATH') or self.config.get('crawler_config', 'pre_estimation_mount_path', fallback='')
            }
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Erreur de configuration crawler: {e}")
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Retourne la configuration de la base de données
        
        Returns:
            Dictionnaire avec la configuration BDD
        """
        try:
            return {
                'db_path': os.getenv('OPENINDEX_DB_PATH') or self.config.get('database_config', 'db_path', fallback='openindex.db'),
                'backup_enabled': (os.getenv('OPENINDEX_DB_BACKUP_ENABLED') or str(self.config.getboolean('database_config', 'backup_enabled', fallback=False))).lower() in {'1', 'true', 'yes', 'on'},
                'backup_interval_hours': int(os.getenv('OPENINDEX_DB_BACKUP_INTERVAL_HOURS') or self.config.getint('database_config', 'backup_interval_hours', fallback=24))
            }
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Erreur de configuration BDD: {e}")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Retourne la configuration des logs
        
        Returns:
            Dictionnaire avec la configuration des logs
        """
        try:
            return {
                'log_level': os.getenv('OPENINDEX_LOG_LEVEL') or self.config.get('logging_config', 'log_level', fallback='INFO'),
                'log_file': os.getenv('OPENINDEX_LOG_FILE') or self.config.get('logging_config', 'log_file', fallback='logs/openindex.log'),
                'max_log_size_mb': int(os.getenv('OPENINDEX_LOG_MAX_SIZE_MB') or self.config.getint('logging_config', 'max_log_size_mb', fallback=10)),
                'backup_count': int(os.getenv('OPENINDEX_LOG_BACKUP_COUNT') or self.config.getint('logging_config', 'backup_count', fallback=5))
            }
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Erreur de configuration logs: {e}")
    
    def create_crawler(self):
        """
        Crée une instance de SMBCrawler avec la configuration
        
        Returns:
            Instance de SMBCrawler configurée
        """
        from smb_crawler import SMBCrawler
        
        # Récupérer les credentials
        smb_creds = self.get_smb_credentials()
        crawler_config = self.get_crawler_config()
        
        # Filtrer les paramètres valides pour SMBCrawler
        valid_params = {
            'server': smb_creds['server'],
            'username': smb_creds['username'],
            'password': smb_creds['password'],
            'share_name': smb_creds['share_name'],
            'domain': smb_creds['domain'],
            'max_workers': crawler_config['max_workers'],
            'delay_between_requests': crawler_config['delay_between_requests'],
            'max_queue_size': crawler_config['max_queue_size'],
            'max_depth': crawler_config['max_depth']
        }
        
        # Créer le crawler avec les paramètres valides
        crawler = SMBCrawler(**valid_params)
        
        return crawler

# Point d'entrée principal pour faciliter l'utilisation
def get_config_manager(config_path: str = None) -> ConfigManager:
    """
    Factory function pour créer un ConfigManager
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Instance de ConfigManager
    """
    return ConfigManager(config_path)

# Test de configuration
if __name__ == "__main__":
    try:
        config = get_config_manager()
        
        print("✅ Configuration chargée avec succès:")
        print(f"   Serveur SMB: {config.get_smb_credentials()['server']}")
        print(f"   Share: {config.get_smb_credentials()['share_name']}")
        print(f"   Domaine: {config.get_smb_credentials()['domain']}")
        print(f"   Utilisateur: {config.get_smb_credentials()['username']}")
        print(f"   Workers: {config.get_crawler_config()['max_workers']}")
        print(f"   Profondeur max: {config.get_crawler_config()['max_depth']}")
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
