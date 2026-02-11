#!/usr/bin/env python3
"""
Tests unitaires pour le crawler SMB.
"""

import unittest
import os
import sqlite3
from unittest.mock import Mock, patch
from src.smb_crawler import SMBCrawler


class TestSMBCrawler(unittest.TestCase):
    """Classe de test pour le crawler SMB."""

    def setUp(self):
        """Configuration initiale pour les tests."""
        self.server = "192.168.1.100"
        self.username = "utilisateur"
        self.password = "motdepasse"
        self.share_name = "partage"
        self.db_path = ":memory:"
        self.crawler = SMBCrawler(
            self.server,
            self.username,
            self.password,
            self.share_name,
            self.db_path
        )

    def test_init(self):
        """Test l'initialisation du crawler."""
        self.assertEqual(self.crawler.server, self.server)
        self.assertEqual(self.crawler.username, self.username)
        self.assertEqual(self.crawler.password, self.password)
        self.assertEqual(self.crawler.share_name, self.share_name)
        self.assertEqual(self.crawler.db_path, self.db_path)

    def test_connect(self):
        """Test la connexion au serveur SMB."""
        with patch('src.smb_crawler.Connection') as mock_connection:
            with patch('src.smb_crawler.Session') as mock_session:
                with patch('src.smb_crawler.TreeConnect') as mock_tree:
                    mock_conn_instance = Mock()
                    mock_session_instance = Mock()
                    mock_tree_instance = Mock()
                    
                    mock_connection.return_value = mock_conn_instance
                    mock_session.return_value = mock_session_instance
                    mock_tree.return_value = mock_tree_instance
                    
                    result = self.crawler.connect()
                    self.assertTrue(result)
                    self.assertEqual(self.crawler.connection, mock_conn_instance)
                    self.assertEqual(self.crawler.session, mock_session_instance)
                    self.assertEqual(self.crawler.tree, mock_tree_instance)

    def test_disconnect(self):
        """Test la déconnexion du serveur SMB."""
        self.crawler.tree = Mock()
        self.crawler.session = Mock()
        self.crawler.connection = Mock()
        
        self.crawler.disconnect()
        
        self.crawler.tree.disconnect.assert_called_once()
        self.crawler.session.disconnect.assert_called_once()
        self.crawler.connection.disconnect.assert_called_once()

    def test_init_db(self):
        """Test l'initialisation de la base de données."""
        self.crawler.init_db()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'files')

    def test_calculate_sha256(self):
        """Test le calcul du checksum SHA-256."""
        test_file = "test_file.txt"
        with open(test_file, "w") as f:
            f.write("test content")
        
        checksum = self.crawler.calculate_sha256(test_file)
        self.assertEqual(checksum, "234d4c2a6b3e5f7a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4")
        
        os.remove(test_file)

    def test_save_to_db(self):
        """Test l'enregistrement des métadonnées dans la base de données."""
        self.crawler.init_db()
        
        file_data = {
            "path": "/test/path",
            "name": "test_file.txt",
            "size": 1024,
            "checksum": "test_checksum",
            "last_modified": "2026-02-11 12:00:00",
            "is_directory": False
        }
        
        self.crawler.save_to_db(file_data)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE name='test_file.txt'")
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[2], "test_file.txt")


if __name__ == "__main__":
    unittest.main()