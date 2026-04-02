#!/usr/bin/env python3
"""
SMB Crawler Worker avec monitoring intégré
Extension du worker_loop pour gérer les pauses automatiques
"""

import time
import threading
from typing import Dict, Any
from datetime import datetime

from smb_health_monitor import SMBHealthMonitor, SMBServerStatus
from postgres_adapter import PostgreSQLAdapter


def _extract_server_from_path(path: str) -> str:
    """Extrait le serveur d'un chemin UNC."""
    path = path.strip("\\")
    parts = path.split("\\")
    return parts[0] if parts else ""


def _build_postgres_config() -> Dict[str, Any]:
    """Construit la config PostgreSQL."""
    import os
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'openindex'),
        'user': os.getenv('POSTGRES_USER', 'openindex_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
    }


def check_smb_server_health(server: str, timeout: int = 10) -> bool:
    """Vérifie rapidement si un serveur SMB est accessible."""
    try:
        import smbclient
        smbclient.ClientConfig(connection_timeout=timeout)
        smbclient.listdir(f"\\\\{server}")
        return True
    except Exception:
        return False


def worker_loop_with_monitoring(poll_interval_seconds: int = 5):
    """
    Boucle principale du worker avec monitoring SMB intégré.
    
    Gère automatiquement:
    - Les runs en attente (queued)
    - Les runs mis en pause (pending) suite a panne SMB
    - La reprise automatique quand le SMB revient
    """
    adapter = PostgreSQLAdapter(_build_postgres_config())
    adapter.initialize_database()
    adapter.reset_stale_running_runs()
    
    print("👂 Worker d'exploration avec monitoring SMB prêt")
    print("   - Surveillance active des serveurs SMB")
    print("   - Reprise automatique apres panne")
    
    # Thread de nettoyage
    from smb_crawler_postgresql import cleanup_stale_runs
    cleanup_thread = threading.Thread(
        target=cleanup_stale_runs,
        args=(adapter,),
        daemon=True
    )
    cleanup_thread.start()
    
    # Dictionnaire pour suivre les runs en attente de reprise
    pending_runs: Dict[str, Dict] = {}
    
    while True:
        try:
            # 1. Verifier d'abord si des runs pending peuvent reprendre
            _check_pending_runs(adapter, pending_runs)
            
            # 2. Attendre le prochain run
            run_payload = adapter.wait_for_next_run(
                poll_interval_seconds=poll_interval_seconds
            )
            run_id = run_payload["run_id"]
            
            # 3. Executer le run avec monitoring
            _execute_run_with_monitoring(adapter, run_payload, pending_runs)
            
        except KeyboardInterrupt:
            print("\n🛑 Interruption par l'utilisateur")
            break
        except Exception as exc:
            print(f"❌ Erreur dans worker_loop: {exc}")
            time.sleep(5)


def _check_pending_runs(adapter: PostgreSQLAdapter, pending_runs: Dict) -> None:
    """Verifie si des runs pending peuvent reprendre."""
    runs_to_check = list(pending_runs.keys())
    
    for run_id in runs_to_check:
        run_info = pending_runs[run_id]
        server = run_info.get("server")
        start_path = run_info.get("start_path")
        
        print(f"🔍 [Reprise] Verification du serveur {server} pour run {run_id}")
        
        if check_smb_server_health(server):
            print(f"✅ [Reprise] Serveur {server} est accessible!")
            print(f"   - Reprise du run {run_id}")
            
            # Le serveur est revenu, on passe le run en queued
            try:
                adapter.update_crawl_run_status(run_id, "queued")
                del pending_runs[run_id]
                print(f"   - Run {run_id} passe de PENDING a QUEUED")
            except Exception as exc:
                print(f"⚠️  Erreur mise a jour statut: {exc}")
        else:
            downtime = time.time() - run_info.get("paused_at", time.time())
            print(f"⏳ [Reprise] Serveur {server} toujours inaccessible")
            print(f"   - Downtime: {downtime:.0f}s")


def _execute_run_with_monitoring(
    adapter: PostgreSQLAdapter,
    run_payload: Dict[str, Any],
    pending_runs: Dict
) -> None:
    """Execute un run avec monitoring actif."""
    run_id = run_payload["run_id"]
    start_path = run_payload.get("start_path", "")
    server = _extract_server_from_path(start_path)
    
    print(f"▶️  Run reserve: {run_id} - {run_payload.get('name')}")
    print(f"   - Serveur: {server}")
    print(f"   - Chemin: {start_path}")
    
    # Creer le health monitor pour ce run
    health_monitor = SMBHealthMonitor(
        check_interval=30,
        failure_threshold=2,
        timeout=10
    )
    
    server_down = threading.Event()
    server_down_time: float = 0.0
    
    def on_server_down(srv: str) -> None:
        nonlocal server_down_time
        server_down_time = time.time()
        server_down.set()
        print(f"\n🚨 [Monitoring] SERVEUR {srv} INACCESSIBLE!")
        print(f"   - Timestamp: {datetime.now().isoformat()}")
        
        # Mettre le run en pending
        try:
            adapter.update_crawl_run_status(run_id, "pending")
            pending_runs[run_id] = {
                "server": srv,
                "start_path": start_path,
                "paused_at": server_down_time,
                "run_payload": run_payload
            }
            print(f"   - Run {run_id} mis en PENDING")
        except Exception as exc:
            print(f"⚠️  Erreur mise a jour statut: {exc}")
    
    health_monitor.register_callback('server_down', on_server_down)
    health_monitor.add_server(server)
    health_monitor.start()
    
    try:
        # Verifier si le serveur est accessible avant de commencer
        if not check_smb_server_health(server, timeout=5):
            print(f"⚠️  Serveur {server} inaccessible au demarrage")
            on_server_down(server)
            return
        
        # Executer le crawl
        from smb_crawler_postgresql import run_single_crawl
        stats = run_single_crawl(run_payload)
        
        # Si le serveur est tombe pendant le crawl
        if server_down.is_set():
            print(f"\n⏸️  Crawl interrompu par panne SMB")
            print(f"   - Run {run_id} en attente de reprise")
            return
        
        # Crawl termine normalement
        final_status = stats.get("final_status", "completed")
        adapter.update_crawl_run_status(run_id, final_status)
        print(f"✅ Run termine: {run_id} ({final_status})")
        
        # Nettoyer si le run etait dans pending_runs
        if run_id in pending_runs:
            del pending_runs[run_id]
            
    except Exception as exc:
        print(f"❌ Erreur run {run_id}: {exc}")
        
        # Si erreur SMB, mettre en pending
        if server_down.is_set():
            print(f"   - Erreur liee a SMB, run mis en PENDING")
        else:
            # Autre erreur, marquer comme failed
            adapter.update_crawl_run_status(run_id, "failed")
            
    finally:
        health_monitor.stop()
        print(f"🛑 Monitoring arrete pour {server}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Worker SMB avec monitoring")
    parser.add_argument("--poll-interval", type=int, default=5)
    args = parser.parse_args()
    
    worker_loop_with_monitoring(poll_interval_seconds=args.poll_interval)
