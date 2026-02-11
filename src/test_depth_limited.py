#!/usr/bin/env python3
"""
Script de test du crawler avec limitation de profondeur à 2 niveaux.
"""

import time
from smb_crawler import SMBCrawler

def test_callback(stats):
    """Callback pour afficher la progression du test."""
    print(f"\r📁 Répertoires: {stats['processed_directories']}/{stats['total_directories']} "
          f"📄 Fichiers: {stats['processed_files']}/{stats['total_files']} "
          f"❌ Erreurs: {stats['errors']} "
          f"⏱️ Temps: {stats.get('elapsed_time', 0):.1f}s", end="")
    import sys
    sys.stdout.flush()

def main():
    """Test avec limitation de profondeur."""
    print("🧪 TEST DU CRAWLER AVEC PROFONDEUR LIMITÉE (2 niveaux)")
    print("=" * 70)
    
    # Configuration avec limitation de profondeur
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere", 
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN",
        max_workers=6,              # 6 workers
        delay_between_requests=0.05, # 50ms
        max_queue_size=50,          # Petite queue
        max_depth=2                # LIMITE CRUCIALE : 2 niveaux seulement !
    )
    
    crawler.init_db()
    
    print("\n🚀 Démarrage du test limité à 2 niveaux de profondeur...")
    print("📂 Test path: SMIDEN/Technique")
    print("🎯 Objectif: Valider que le crawler termine complètement")
    print("⏱️  Temps estimé: ~2-3 minutes")
    print("⚠️  Appuyez sur Ctrl+C pour arrêter")
    
    start_time = time.time()
    
    try:
        # Lancer le crawl avec limitation de profondeur
        crawler.crawl(base_path="SMIDEN/Technique", progress_callback=test_callback)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n\n🎉 TEST TERMINÉ AVEC SUCCÈS!")
        print(f"⏱️  Durée totale: {total_time:.2f}s")
        
        # Afficher les statistiques finales
        final_stats = crawler.get_stats()
        print(f"\n📊 STATISTIQUES FINALES:")
        print(f"   📁 Répertoires traités: {final_stats['processed_directories']}")
        print(f"   📄 Fichiers traités: {final_stats['processed_files']}")
        print(f"   ❌ Erreurs: {final_stats['errors']}")
        print(f"   📊 Pourcentage de réussite: {((final_stats['processed_files'] + final_stats['processed_directories']) / max(final_stats['total_files'] + final_stats['total_directories'], 1) * 100):.1f}%")
        
        # Vérifier si tout est terminé
        if (final_stats['queue_size_directories'] == 0 and 
            final_stats['queue_size_files'] == 0 and 
            final_stats['queue_size_results'] == 0):
            print("✅ Toutes les queues sont vides - Succès total!")
        else:
            print("⚠️  Certaines queues ne sont pas vides")
            print(f"   Queue répertoires: {final_stats['queue_size_directories']}")
            print(f"   Queue fichiers: {final_stats['queue_size_files']}")
            print(f"   Queue résultats: {final_stats['queue_size_results']}")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  TEST INTERROMPU par l'utilisateur")
        
        # Afficher les statistiques partielles
        partial_stats = crawler.get_stats()
        print(f"\n📊 STATISTIQUES PARTIELLES:")
        print(f"   📁 Répertoires traités: {partial_stats['processed_directories']}")
        print(f"   📄 Fichiers traités: {partial_stats['processed_files']}")
        print(f"   ❌ Erreurs: {partial_stats['errors']}")
        
    except Exception as e:
        print(f"\n\n❌ ERREUR PENDANT LE TEST: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
