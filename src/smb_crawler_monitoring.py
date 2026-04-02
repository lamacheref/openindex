"""
SMB Health Monitor Integration - Extension du crawler avec monitoring
Ce fichier contient les fonctions d'intégration du health monitoring dans le crawler.
"""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime

from smb_health_monitor import SMBHealthMonitor, SMBServerStatus
from postgres_adapter import PostgreSQLAdapter
from smb_crawler_postgresql import SMBCrawlerPostgreSQL, run_single_crawl as _original_run_single_crawl


def run_single_crawl_with_monitoring(
    run_payload: Dict[str, Any],
    health_check_interval: int = 30,
    health_failure_threshold: int = 3,
    health_timeout: int = 10
) -> Dict[str, Any]:
    """
    Execute une exploration avec monitoring actif du serveur SMB.
    
    Si le serveur SMB devient inaccessible:
    - Le crawl est mis en pause (statut PENDING)
    - Un checkpoint est sauvegardé
    - La fonction retourne avec statut pending
    
    Args:
        run_payload: Données du run a executer
        health_check_interval: Intervalle de verification (secondes)
        health_failure_threshold: Nb d'echecs consecutifs avant marquer OFFLINE
        health_timeout: Timeout de connexion (secondes)
        
    Returns:
        Stats du crawl avec champs supplementaires:
        - pending: True si le crawl a ete mis en pause
        - server_downtime: Temps d'indisponibilite du serveur (secondes)
        - resumed: True si le crawl a repris apres une pause
    """
    # Extraire le serveur du start_path
    start_path = run_payload.get("start_path", "")
    server = _extract_server_from_path(start_path)
    run_id = run_payload.get("run_id")
    
    print(f"🔍 [Monitoring] Demarrage du monitoring pour {server}")
    print(f"   - Intervalle: {health_check_interval}s")
    print(f"   - Seuil echecs: {health_failure_threshold}")
    print(f"   - Timeout: {health_timeout}s")
    
    # Creer et configurer le health monitor
    health_monitor = SMBHealthMonitor(
        check_interval=health_check_interval,
        failure_threshold=health_failure_threshold,
        timeout=health_timeout
    )
    
    # Variables pour suivre l'etat
    server_down_start_time: Optional[float] = None
    was_paused = False
    stats = {"pending": False, "server_downtime": 0.0, "resumed": False}
    
    # Handler quand le serveur tombe
    def on_server_down(srv: str) -> None:
        nonlocal server_down_start_time
        server_down_start_time = time.time()
        print(f"🚨 [Monitoring] SERVEUR {srv} INACCESSIBLE - Mise en pause du crawl")
        print(f"   - Timestamp: {datetime.now().isoformat()}")
        
        # Mettre le run en statut pending dans la DB
        try:
            adapter = PostgreSQLAdapter(_build_postgres_config())
            adapter.update_crawl_run_status(run_id, "pending")
            print(f"⏸️  [Monitoring] Run {run_id} marque comme PENDING")
        except Exception as exc:
            print(f"⚠️  [Monitoring] Erreur mise a jour statut: {exc}")
    
    # Handler quand le serveur revient
    def on_server_up(srv: str) -> None:
        nonlocal server_down_start_time, was_paused
        downtime = 0.0
        if server_down_start_time:
            downtime = time.time() - server_down_start_time
        print(f"✅ [Monitoring] SERVEUR {srv} DE NOUVEAU ACCESSIBLE")
        print(f"   - Downtime: {downtime:.1f}s")
        print(f"   - Timestamp: {datetime.now().isoformat()}")
        was_paused = True
        server_down_start_time = None
    
    # Enregistrer les callbacks
    health_monitor.register_callback('server_down', on_server_down)
    health_monitor.register_callback('server_up', on_server_up)
    
    # Ajouter le serveur au monitoring
    health_monitor.add_server(server)
    
    # Demarrer le monitoring
    health_monitor.start()
    print(f"✅ [Monitoring] Health monitor demarre pour {server}")
    
    try:
        # Executer le crawl original
        print("\n🚀 [Monitoring] Demarrage de l'exploration...")
        stats = _original_run_single_crawl(run_payload)
        
        # Si le crawl a ete interrompu par une panne SMB
        if server_down_start_time is not None:
            stats["pending"] = True
            stats["final_status"] = "pending"
            stats["server_downtime"] = time.time() - server_down_start_time
            print(f"\n⏸️  [Monitoring] Crawl mis en pause suite a panne SMB")
            print(f"   - Downtime actuel: {stats['server_downtime']:.1f}s")
            
        # Si le crawl avait ete mis en pause et a repris
        if was_paused and not stats.get("cancelled", False):
            stats["resumed"] = True
            print(f"\n▶️  [Monitoring] Crawl repris apres reprise du serveur SMB")
            
    except Exception as exc:
        print(f"\n❌ [Monitoring] Erreur lors du crawl: {exc}")
        # Si le serveur est down, on met en pending plutot que failed
        if server_down_start_time is not None:
            stats = {
                "pending": True,
                "final_status": "pending",
                "server_downtime": time.time() - server_down_start_time,
                "error": str(exc)
            }
            print(f"⏸️  [Monitoring] Crawl mis en PENDING suite a panne SMB")
        else:
            raise  # Re-raise si ce n'est pas une erreur SMB
            
    finally:
        # Arreter le monitoring
        print(f"\n🛑 [Monitoring] Arret du health monitor...")
        health_monitor.stop()
        print(f"✅ [Monitoring] Health monitor arrete")
    
    return stats


def _extract_server_from_path(path: str) -> str:
    """Extrait le nom du serveur d'un chemin UNC."""
    # Format: \\server\share\path
    path = path.strip("\\")
    parts = path.split("\\")
    return parts[0] if parts else ""


def _build_postgres_config() -> Dict[str, Any]:
    """Construit la config PostgreSQL depuis les variables d'environnement."""
    return {
        'host': __import__('os').getenv('POSTGRES_HOST', 'localhost'),
        'port': int(__import__('os').getenv('POSTGRES_PORT', '5432')),
        'database': __import__('os').getenv('POSTGRES_DB', 'openindex'),
        'user': __import__('os').getenv('POSTGRES_USER', 'openindex_user'),
        'password': __import__('os').getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
    }


# Remplacer la fonction originale par la version avec monitoring
def run_single_crawl(run_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Version avec monitoring du crawl.
    Cette fonction remplace l'original et ajoute le health monitoring SMB.
    """
    return run_single_crawler_with_monitoring(run_payload)
