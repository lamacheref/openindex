#!/usr/bin/env python3
"""
Script de debug pour identifier les problèmes du crawler SMB.
"""

import time
import threading
from smb_crawler import SMBCrawler

def debug_callback(stats):
    """Callback détaillé pour le debug."""
    print(f"\n[DEBUG] {'='*50}")
    print(f"[DEBUG] Timestamp: {time.strftime('%H:%M:%S')}")
    print(f"[DEBUG] Répertoires: {stats['processed_directories']}/{stats['total_directories']}")
    print(f"[DEBUG] Fichiers: {stats['processed_files']}/{stats['total_files']}")
    print(f"[DEBUG] Erreurs: {stats['errors']}")
    print(f"[DEBUG] Queue répertoires: {stats['queue_size_directories']}")
    print(f"[DEBUG] Queue fichiers: {stats['queue_size_files']}")
    print(f"[DEBUG] Queue résultats: {stats['queue_size_results']}")
    
    if stats.get('elapsed_time'):
        print(f"[DEBUG] Temps écoulé: {stats['elapsed_time']:.1f}s")
        print(f"[DEBUG] Vitesse répertoires: {stats.get('directories_per_second', 0):.2f}/s")
        print(f"[DEBUG] Vitesse fichiers: {stats.get('files_per_second', 0):.2f}/s")
    
    print(f"[DEBUG] {'='*50}")

def main():
    """Test avec debug détaillé."""
    print("🔍 DÉBUG DU CRAWLER SMB")
    print("=" * 60)
    
    # Configuration avec plus de workers pour tester
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere", 
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN",
        max_workers=6,              # 6 workers pour tester
        delay_between_requests=0.05, # 50ms seulement
        max_queue_size=50          # Petite queue
    )
    
    crawler.init_db()
    
    print("\n🚀 Démarrage du debug sur un petit répertoire...")
    test_path = "SMIDEN/Technique"
    
    # Lancer le crawl avec debug
    try:
        crawler.crawl(base_path=test_path, progress_callback=debug_callback)
        print("\n✅ Debug terminé!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Debug interrompu")
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
