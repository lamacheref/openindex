#!/usr/bin/env python3
"""
Script de test pour le crawler SMB avec queues et temporisation.
Ce script permet de tester les nouvelles fonctionnalités du crawler.
"""

import time
from smb_crawler import SMBCrawler

def test_progress_callback(stats):
    """Callback pour afficher la progression de manière détaillée."""
    print(f"\n{'='*60}")
    print(f"📊 STATISTIQUES DU CRAWLER")
    print(f"{'='*60}")
    print(f"📁 Répertoires: {stats['processed_directories']}/{stats['total_directories']}")
    print(f"📄 Fichiers: {stats['processed_files']}/{stats['total_files']}")
    print(f"❌ Erreurs: {stats['errors']}")
    
    if stats.get('elapsed_time'):
        print(f"⏱️  Temps écoulé: {stats['elapsed_time']:.2f}s")
        print(f"🚀 Vitesse répertoires: {stats.get('directories_per_second', 0):.2f}/s")
        print(f"🚀 Vitesse fichiers: {stats.get('files_per_second', 0):.2f}/s")
        
        if stats.get('estimated_remaining_time'):
            print(f"⏳ Temps restant estimé: {stats['estimated_remaining_time']:.1f}s")
    
    print(f"📦 Queue répertoires: {stats.get('queue_size_directories', 'N/A')}")
    print(f"📦 Queue fichiers: {stats.get('queue_size_files', 'N/A')}")
    print(f"{'='*60}")

def main():
    """Fonction principale de test."""
    print("🚀 DÉMARRAGE DU TEST DU CRAWLER SMB AVEC QUEUES")
    print("=" * 60)
    
    # Configuration du crawler avec paramètres optimisés pour le test
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere", 
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN",
        max_workers=2,              # Réduit pour le test
        delay_between_requests=0.2,  # 200ms entre requêtes
        max_queue_size=100          # Queue plus petite pour le test
    )
    
    # Initialisation de la base de données
    print("📋 Initialisation de la base de données...")
    crawler.init_db()
    
    # Test sur un petit répertoire pour commencer
    test_path = "SMIDEN/Technique"
    
    print(f"\n🔍 Démarrage du crawl test sur: {test_path}")
    print("⚠️  Appuyez sur Ctrl+C pour arrêter le test")
    print("⏸️  Le crawler peut être mis en pause avec crawler.pause()")
    
    start_time = time.time()
    
    try:
        # Lancer le crawl avec callback de progression
        crawler.crawl(base_path=test_path, progress_callback=test_progress_callback)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n\n✅ TEST TERMINÉ AVEC SUCCÈS!")
        print(f"⏱️  Durée totale: {total_time:.2f}s")
        
        # Afficher les statistiques finales
        final_stats = crawler.get_stats()
        print(f"\n📈 STATISTIQUES FINALES:")
        print(f"   📁 Répertoires traités: {final_stats['processed_directories']}")
        print(f"   📄 Fichiers traités: {final_stats['processed_files']}")
        print(f"   ❌ Erreurs: {final_stats['errors']}")
        print(f"   📊 Pourcentage de réussite: {((final_stats['processed_files'] + final_stats['processed_directories']) / max(final_stats['total_files'] + final_stats['total_directories'], 1) * 100):.1f}%")
        
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
