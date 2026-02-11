#!/usr/bin/env python3
"""
Test unitaire pour vérifier le bon fonctionnement du système de queue dans le crawler SMB.
"""

import os
import sys
import sqlite3
from unittest.mock import Mock, patch, MagicMock

# Ajouter le chemin du projet au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.smb_crawler import SMBCrawler


def test_queue_initialization():
    """Test l'initialisation de la queue dans le crawler."""
    crawler = SMBCrawler(
        server='test_server',
        username='test_user',
        password='test_password',
        share_name='test_share',
        domain='test_domain'
    )
    
    # Vérifier que la queue est initialisée
    assert hasattr(crawler, 'queue'), "La queue n'est pas initialisée dans le crawler."
    print("✓ La queue est correctement initialisée dans le crawler.")


def test_queue_usage_in_crawl():
    """Test l'utilisation de la queue dans la méthode crawl."""
    crawler = SMBCrawler(
        server='test_server',
        username='test_user',
        password='test_password',
        share_name='test_share',
        domain='test_domain'
    )
    
    # Mock des fonctions smbclient
    with patch('smbclient.scandir') as mock_scandir, \
         patch('smbclient.open_file') as mock_open_file:
        
        # Configuration du mock pour scandir
        mock_file_info = Mock()
        mock_file_info.name = 'test_file.txt'
        mock_file_info.is_dir.return_value = False
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1234567890
        mock_file_info.stat.return_value = mock_stat
        
        mock_dir_info = Mock()
        mock_dir_info.name = 'test_directory'
        mock_dir_info.is_dir.return_value = True
        mock_stat_dir = Mock()
        mock_stat_dir.st_size = 4096
        mock_stat_dir.st_mtime = 1234567890
        mock_dir_info.stat.return_value = mock_stat_dir
        
        mock_scandir.return_value = [mock_file_info, mock_dir_info]
        
        # Configuration du mock pour open_file
        mock_file = MagicMock()
        mock_file.read.return_value = b'test content'
        mock_open_file.return_value.__enter__.return_value = mock_file
        
        # Exécuter la méthode crawl
        files = list(crawler.crawl(base_path='test_path', page_size=10))
        
        # Vérifier que la queue est utilisée
        assert len(files) == 2, "Le nombre de fichiers retournés est incorrect."
        
        # Vérifier que les sous-dossiers sont ajoutés à la queue
        assert not crawler.queue.empty(), "Les sous-dossiers n'ont pas été ajoutés à la queue."
        
        print("✓ La queue est correctement utilisée dans la méthode crawl.")


def test_error_handling():
    """Test la gestion des erreurs dans la méthode crawl."""
    crawler = SMBCrawler(
        server='test_server',
        username='test_user',
        password='test_password',
        share_name='test_share',
        domain='test_domain'
    )
    
    # Mock des fonctions smbclient pour simuler une erreur
    with patch('smbclient.scandir') as mock_scandir:
        
        # Configuration du mock pour lever une exception
        mock_scandir.side_effect = Exception("Erreur d'accès au répertoire")
        
        # Exécuter la méthode crawl
        files = list(crawler.crawl(base_path='test_path', page_size=10))
        
        # Vérifier que l'erreur est gérée correctement
        assert len(files) == 0, "Aucun fichier ne devrait être retourné en cas d'erreur."
        
        print("✓ La gestion des erreurs fonctionne correctement.")


def test_database_integration():
    """Test l'intégration avec la base de données."""
    crawler = SMBCrawler(
        server='test_server',
        username='test_user',
        password='test_password',
        share_name='test_share',
        domain='test_domain',
        db_path=':memory:'
    )
    
    # Initialiser la base de données
    crawler.init_db()
    
    # Vérifier que la table est créée
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    table_exists = cursor.fetchone() is not None
    conn.close()
    
    assert table_exists, "La table 'files' n'a pas été créée dans la base de données."
    
    print("✓ L'intégration avec la base de données fonctionne correctement.")


if __name__ == '__main__':
    print("Exécution des tests unitaires pour le système de queue...")
    
    test_queue_initialization()
    test_queue_usage_in_crawl()
    test_error_handling()
    test_database_integration()
    
    print("\n✓ Tous les tests ont été passés avec succès.")