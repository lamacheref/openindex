#!/usr/bin/env python3
"""
Script de test de la déduplication du crawler.
"""

import sqlite3
import os
from backend.src.crawlers.smb_crawler import SMBCrawler

def clean_database():
    """Nettoie la base de données pour un test propre."""
    if os.path.exists('openindex.db'):
        os.remove('openindex.db')
        print("🗑️  Base de données nettoyée")

def analyze_deduplication():
    """Analyse les résultats de la déduplication."""
    conn = sqlite3.connect('openindex.db')
    cursor = conn.cursor()
    
    print("\n📊 ANALYSE DE LA DÉDUPLICATION:")
    print("=" * 60)
    
    # Statistiques générales
    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 0")
    files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 1")
    dirs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_duplicate = 1")
    duplicates = cursor.fetchone()[0]
    
    print(f"📁 Total éléments: {total}")
    print(f"📄 Fichiers: {files}")
    print(f"📁 Dossiers: {dirs}")
    print(f"🔄 Doublons marqués: {duplicates}")
    
    # Vérifier s'il y a encore des doublons par checksum
    cursor.execute("""
        SELECT checksum, COUNT(*) as count 
        FROM files 
        WHERE is_directory = 0 AND checksum IS NOT NULL
        GROUP BY checksum 
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    checksum_duplicates = cursor.fetchall()
    
    if checksum_duplicates:
        print(f"\n⚠️  Attention: {len(checksum_duplicates)} checksums ont encore des doublons:")
        for dup in checksum_duplicates[:5]:
            print(f"   Checksum {dup[0][:16]}...: {dup[1]} occurrences")
    else:
        print("\n✅ Aucun doublon par checksum détecté!")
    
    # Afficher quelques exemples de doublons gérés
    if duplicates > 0:
        cursor.execute("""
            SELECT name, path, duplicate_of 
            FROM files 
            WHERE is_duplicate = 1 
            LIMIT 5
        """)
        
        dup_examples = cursor.fetchall()
        print(f"\n📋 Exemples de doublons gérés:")
        for name, path, dup_of in dup_examples:
            print(f"   📄 {name}")
            print(f"      📍 Nouveau: {path}")
            print(f"      🔄 Original: {dup_of}")
    
    conn.close()

def main():
    """Test principal de déduplication."""
    print("🧪 TEST DE DÉDUPLICATION DU CRAWLER")
    print("=" * 70)
    print("🎯 Objectif: Valider que les doublons sont correctement gérés")
    print("📂 Test path: SMIDEN/Technique")
    
    # Nettoyer la base
    clean_database()
    
    # Configuration du crawler
    crawler = SMBCrawler(
        server="172.16.252.34",
        username="flamachere", 
        password="F6r)OW+lg2",
        share_name="public",
        domain="SMIDEN",
        max_workers=6,
        delay_between_requests=0.05,
        max_queue_size=100,
        max_depth=2  # Limité pour le test
    )
    
    crawler.init_db()
    
    print("\n🚀 Lancement du test de déduplication...")
    print("🔍 Le crawler devrait:")
    print("   - Ignorer les fichiers déjà existants au même endroit")
    print("   - Détecter et marquer les doublons de contenu")
    print("   - Éviter les insertions multiples")
    
    # Lancer le crawl
    try:
        crawler.crawl(base_path="SMIDEN/Technique", progress_callback=None)
        
        print("\n✅ Test terminé!")
        
        # Analyser les résultats
        analyze_deduplication()
        
        # Test de ré-exécution pour vérifier l'ignorage
        print("\n🔄 TEST DE RÉ-EXÉCUTION:")
        print("Lancement du même crawl pour vérifier que les fichiers sont ignorés...")
        
        crawler.crawl(base_path="SMIDEN/Technique", progress_callback=None)
        
        print("\n✅ Ré-exécution terminée!")
        analyze_deduplication()
        
    except Exception as e:
        print(f"\n❌ Erreur pendant le test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
