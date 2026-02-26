#!/usr/bin/env python3
"""
Configuration centralisée du logging pour OpenIndex
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any

class OpenIndexLogger:
    """Gestionnaire de logging centralisé pour OpenIndex"""
    
    def __init__(self, log_dir: str = "logs", app_name: str = "openindex"):
        """
        Initialise le gestionnaire de logging
        
        Args:
            log_dir: Répertoire pour les fichiers de log
            app_name: Nom de l'application pour les logs
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.loggers = {}
        
        # Créer le répertoire de logs
        self.log_dir.mkdir(exist_ok=True)
        
        # Configuration par défaut
        self.default_config = {
            'level': logging.INFO,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'max_bytes': 10 * 1024 * 1024,  # 10MB
            'backup_count': 5,
            'console_level': logging.INFO
        }
    
    def setup_logger(self, name: str, config: Dict[str, Any] = None) -> logging.Logger:
        """
        Configure un logger avec rotation et compression
        
        Args:
            name: Nom du logger
            config: Configuration personnalisée
            
        Returns:
            Logger configuré
        """
        if name in self.loggers:
            return self.loggers[name]
        
        # Fusionner avec la configuration par défaut
        final_config = self.default_config.copy()
        if config:
            final_config.update(config)
        
        # Créer le logger
        logger = logging.getLogger(name)
        logger.setLevel(final_config['level'])
        
        # Éviter les doublons de handlers
        if logger.handlers:
            return logger
        
        # Formatter
        formatter = logging.Formatter(
            final_config['format'],
            datefmt=final_config['date_format']
        )
        
        # Handler pour les fichiers avec rotation et compression
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=final_config['max_bytes'],
            backupCount=final_config['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(final_config['level'])
        file_handler.setFormatter(formatter)
        
        # Ajouter la compression des fichiers de rotation
        file_handler.rotator = self._compress_log_file
        file_handler.namer = self._name_rotated_file
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(final_config['console_level'])
        console_handler.setFormatter(formatter)
        
        # Ajouter les handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Stocker le logger
        self.loggers[name] = logger
        
        return logger
    
    def _compress_log_file(self, source, dest):
        """
        Compresse un fichier de log lors de la rotation
        
        Args:
            source: Chemin du fichier source
            dest: Chemin de destination souhaité
        """
        import gzip
        import shutil
        import os
        
        # Compresser le fichier source
        compressed_dest = dest + '.gz'
        with open(source, 'rb') as f_in:
            with gzip.open(compressed_dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Supprimer le fichier source non compressé
        os.remove(source)
        
        return compressed_dest
    
    def _name_rotated_file(self, name):
        """
        Génère un nom pour le fichier de rotation
        
        Args:
            name: Nom de base du fichier
            
        Returns:
            Nom du fichier de rotation
        """
        return name + ".rotated"
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Récupère un logger existant ou le crée
        
        Args:
            name: Nom du logger
            
        Returns:
            Logger existant ou nouveau
        """
        return self.loggers.get(name) or self.setup_logger(name)
    
    def setup_crawler_logger(self, debug: bool = False) -> logging.Logger:
        """
        Configure le logger spécifique pour le crawler SMB
        
        Args:
            debug: Mode debug activé
            
        Returns:
            Logger configuré pour le crawler
        """
        config = {
            'console_level': logging.DEBUG if debug else logging.INFO,
            'level': logging.DEBUG if debug else logging.INFO,
            'max_bytes': 5 * 1024 * 1024,  # 5MB pour le crawler
            'backup_count': 10  # Garder plus de rotations pour le crawler
        }
        
        return self.setup_logger('smb_crawler', config)
    
    def setup_api_logger(self) -> logging.Logger:
        """
        Configure le logger pour l'API FastAPI
        
        Returns:
            Logger configuré pour l'API
        """
        return self.setup_logger('openindex_api')
    
    def setup_db_logger(self) -> logging.Logger:
        """
        Configure le logger pour les opérations de base de données
        
        Returns:
            Logger configuré pour la BDD
        """
        return self.setup_logger('openindex_db')
    
    def list_log_files(self) -> list:
        """
        Liste tous les fichiers de log disponibles
        
        Returns:
            Liste des fichiers de log
        """
        log_files = []
        for log_file in self.log_dir.glob("*.log*"):
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': log_file.stat().st_size,
                'modified': log_file.stat().st_mtime
            })
        
        return sorted(log_files, key=lambda x: x['modified'], reverse=True)
    
    def cleanup_old_logs(self, days: int = 30):
        """
        Nettoie les anciens fichiers de log
        
        Args:
            days: Nombre de jours à conserver
        """
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    print(f"🗑️  Fichier de log supprimé: {log_file.name}")
                except Exception as e:
                    print(f"❌ Erreur suppression {log_file.name}: {e}")

# Instance globale pour l'application
_logger_manager = None

def get_logger_manager() -> OpenIndexLogger:
    """
    Récupère l'instance globale du gestionnaire de logging
    
    Returns:
        Instance du gestionnaire de logging
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = OpenIndexLogger()
    return _logger_manager

def setup_app_logging(debug: bool = False) -> Dict[str, logging.Logger]:
    """
    Configure tous les loggers de l'application
    
    Args:
        debug: Mode debug activé
        
    Returns:
        Dictionnaire des loggers configurés
    """
    manager = get_logger_manager()
    
    return {
        'crawler': manager.setup_crawler_logger(debug),
        'api': manager.setup_api_logger(),
        'db': manager.setup_db_logger(),
        'main': manager.setup_logger('openindex_main')
    }

if __name__ == "__main__":
    # Test du logging
    print("🧪 Test du système de logging...")
    
    loggers = setup_app_logging(debug=True)
    
    # Test des différents loggers
    loggers['crawler'].info("🔧 Test du logger crawler")
    loggers['crawler'].debug("🐛 Message debug du crawler")
    loggers['crawler'].warning("⚠️ Message warning du crawler")
    loggers['crawler'].error("❌ Message error du crawler")
    
    loggers['api'].info("🌐 Test du logger API")
    loggers['db'].info("🗄️ Test du logger BDD")
    loggers['main'].info("📝 Test du logger principal")
    
    # Lister les fichiers de log
    manager = get_logger_manager()
    log_files = manager.list_log_files()
    
    print(f"\n📁 Fichiers de log créés:")
    for log_file in log_files:
        print(f"   - {log_file['name']} ({log_file['size']} bytes)")
    
    print("\n✅ Test du logging terminé")
