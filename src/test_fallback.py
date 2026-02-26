#!/usr/bin/env python3
"""
Test de la méthode fallback pour l'accès SMB
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.smb_crawler import SMBCrawler
from src.config_manager import ConfigManager

def test_fallback():
    """Test la méthode fallback sur un dossier problématique"""
    print("🧪 Test de la méthode fallback...")
    
    # Configuration
    config = ConfigManager()
    smb_config = config.get_smb_credentials()
    
    crawler = SMBCrawler(
        server=smb_config['server'],
        username=smb_config['username'], 
        password=smb_config['password'],
        share_name=smb_config['share_name'],
        domain=smb_config['domain'],
        debug=True
    )
    crawler.configure_smbclient(
        username=smb_config['username'],
        password=smb_config['password'],
        domain=smb_config['domain']
    )
    
    # Test sur plusieurs dossier problématiques
    test_dirs = [
        r'\\172.16.252.34\Public\SEPM\RESSOURCES HUMAINES',
        r'\\172.16.252.34\Public\SEPM\DGS',
        r'\\172.16.252.34\Public\SEPM\SERVICE JURIDIQUE',
        r'\\172.16.252.34\Public\SEPM\ACCUEIL'
    ]
    
    for test_dir in test_dirs:
        print(f"\n📁 Test du dossier: {test_dir}")
        files = crawler.list_directory_fallback(test_dir)
        
        if files:
            print(f"✅ Fallback réussi: {len(files)} éléments trouvés")
            for f in files[:3]:
                file_type = "Dossier" if f.is_dir() else "Fichier"
                print(f"   - {f.name} ({file_type})")
        else:
            print("❌ Fallback échoué")

if __name__ == "__main__":
    test_fallback()
