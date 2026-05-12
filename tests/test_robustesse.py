#!/usr/bin/env python3
"""
Script de test de robustesse du crawler avec gestion améliorée des erreurs.
"""

import time
from backend.src.crawlers.smb_crawler import SMBCrawler

def robust_callback(stats):
    """Callback pour tester la robustesse."""
    print(f"\r📁 {stats['processed_directories']}/{stats['total_directories']} "
          f"📄 {stats['processed_files']}/{stats['total_files']} "
          f"❌ {stats['errors']} "
          f"📦 D:{stats['queue_size_directories']} F:{stats['queue_size_files']} R:{stats['queue_size_results']} "
          f"⏱️ {stats.get('elapsed_time', 0):.1f}s", end="")
    import sys
    sys.stdout.flush()

def main():
    """Test de robustesse avec gestion d'erreurs."""
    print("🛡️ TEST DE ROBUSTESSE DU CRAWLER")
    print("=" * 70)
    print("🎯 Objectif: Valider que le crawler continue malgré les erreurs")
    print("📂 Test path: SMIDEN/Technique")
    print("⏱️  Timeout: 5 minutes maximum")
    print("🚨 Le crawler DOIT continuer même avec des erreurs de fichiers")
    
    # Configuration optimisée pour la robustesse
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere", 
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN",
        max_workers=6,              # 6 workers
        delay_between_requests=0.05, # 50ms
        max_queue_size=100,         # Queue moyenne
        max_depth=2                # 2 niveaux pour test rapide
    )
    
    crawler.init_db()
    
    print("\n🚀 Démarrage du test de robustesse...")
    print("⚠️  Le crawler doit IGNORER les erreurs de fichiers et continuer")
    print("⚠️  Appuyez sur Ctrl+C pour arrêter manuellement")
    
    start_time = time.time()
    
    try:
        # Lancer le crawl avec timeout de 5 minutes
        import signal
        
        def timeout_handler(signum, frame):
            print(f"\n\n⏰ Timeout de 5 minutes atteint - Arrêt propre")
            crawler.stop()
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(300)  # 5 minutes
        
        crawler.crawl(base_path="SMIDEN/Technique", progress_callback=robust_callback)
        
        signal.alarm(0)  # Annuler le timeout
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n\n🎉 TEST DE ROBUSTESSE TERMINÉ!")
        print(f"⏱️  Durée: {total_time:.2f}s")
        
        # Statistiques finales
        final_stats = crawler.get_stats()
        print(f"\n📊 RÉSULTATS FINAUX:")
        print(f"   📁 Répertoires: {final_stats['processed_directories']}/{final_stats['total_directories']}")
        print(f"   📄 Fichiers: {final_stats['processed_files']}/{final_stats['total_files']}")
        print(f"   ❌ Erreurs: {final_stats['errors']}")
        
        # Vérification de la robustesse
        success_rate = ((final_stats['processed_files'] + final_stats['processed_directories']) / 
                      max(final_stats['total_files'] + final_stats['total_directories'], 1) * 100)
        
        print(f"\n🎯 VALIDATION:")
        if success_rate >= 95:
            print(f"   ✅ EXCELLENT: {success_rate:.1f}% de succès")
            print("   ✅ Le crawler est robuste et continue malgré les erreurs")
        elif success_rate >= 80:
            print(f"   ⚠️  BON: {success_rate:.1f}% de succès")
            print("   ⚠️  Quelques améliorations possibles")
        else:
            print(f"   ❌ INSUFFISANT: {success_rate:.1f}% de succès")
            print("   ❌ Le crawler s'arrête trop souvent sur les erreurs")
        
        # Vérification des queues
        if (final_stats['queue_size_directories'] == 0 and 
            final_stats['queue_size_files'] == 0 and 
            final_stats['queue_size_results'] == 0):
            print("   ✅ Toutes les queues sont vides")
        else:
            print("   ⚠️  Il reste des éléments dans les queues")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  TEST INTERROMPU manuellement")
        
    except Exception as e:
        print(f"\n\n❌ ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
