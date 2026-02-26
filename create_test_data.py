#!/usr/bin/env python3
"""
Script pour créer des données de test dans SQLite et migrer vers PostgreSQL
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

def create_test_data():
    """Crée des données de test réalistes dans SQLite"""
    
    # Supprimer l'ancienne base si elle existe
    if os.path.exists('openindex.db'):
        os.remove('openindex.db')
    
    conn = sqlite3.connect('openindex.db')
    cursor = conn.cursor()
    
    # Créer la table
    cursor.execute('''
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            size INTEGER,
            checksum TEXT,
            last_modified TEXT,
            is_directory BOOLEAN NOT NULL DEFAULT 0,
            is_duplicate BOOLEAN DEFAULT 0,
            duplicate_of TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Données de test réalistes
    base_time = datetime.now()
    test_data = []
    
    # Dossiers
    folders = [
        ('\\\\172.16.252.34\\Public\\SEPM\\ACCUEIL', 'ACCUEIL', True, base_time - timedelta(days=30)),
        ('\\\\172.16.252.34\\Public\\SEPM\\TECHNIQUE', 'TECHNIQUE', True, base_time - timedelta(days=25)),
        ('\\\\172.16.252.34\\Public\\SEPM\\ADMIN', 'ADMIN', True, base_time - timedelta(days=20)),
        ('\\\\172.16.252.34\\Public\\SEPM\\RAPPORTS', 'RAPPORTS', True, base_time - timedelta(days=15)),
        ('\\\\172.16.252.34\\Public\\SEPM\\ARCHIVES', 'ARCHIVES', True, base_time - timedelta(days=365)),
    ]
    
    for path, name, is_dir, mod_time in folders:
        test_data.append((
            path, name, None, None, 
            mod_time.isoformat(), is_dir, False, None,
            base_time.isoformat(), base_time.isoformat()
        ))
    
    # Fichiers avec différentes tailles et types
    files = [
        # Documents
        ('\\\\172.16.252.34\\Public\\SEPM\\ACCUEIL\\README.pdf', 'README.pdf', 1024000, 'a1b2c3d4', base_time - timedelta(hours=2)),
        ('\\\\172.16.252.34\\Public\\SEPM\\ACCUEIL\\presentation.pptx', 'presentation.pptx', 5120000, 'e5f6g7h8', base_time - timedelta(hours=4)),
        ('\\\\172.16.252.34\\Public\\SEPM\\TECHNIQUE\\config.ini', 'config.ini', 2048, 'i9j0k1l2', base_time - timedelta(hours=6)),
        ('\\\\172.16.252.34\\Public\\SEPM\\TECHNIQUE\\script.py', 'script.py', 8192, 'm3n4o5p6', base_time - timedelta(hours=8)),
        
        # Fichiers Excel avec doublons
        ('\\\\172.16.252.34\\Public\\SEPM\\ADMIN\\budget2024.xlsx', 'budget2024.xlsx', 2048000, 'q7r8s9t0', base_time - timedelta(days=1)),
        ('\\\\172.16.252.34\\Public\\SEPM\\ADMIN\\budget2024_backup.xlsx', 'budget2024_backup.xlsx', 2048000, 'q7r8s9t0', base_time - timedelta(days=2)),  # doublon
        ('\\\\172.16.252.34\\Public\\SEPM\\ADMIN\\effectifs.csv', 'effectifs.csv', 512000, 'u1v2w3x4', base_time - timedelta(days=3)),
        
        # Rapports
        ('\\\\172.16.252.34\\Public\\SEPM\\RAPPORTS\\rapport_mensuel.docx', 'rapport_mensuel.docx', 1536000, 'y5z6a7b8', base_time - timedelta(days=5)),
        ('\\\\172.16.252.34\\Public\\SEPM\\RAPPORTS\\rapport_mensuel_v2.docx', 'rapport_mensuel_v2.docx', 1536000, 'y5z6a7b8', base_time - timedelta(days=4)),  # doublon
        ('\\\\172.16.252.34\\Public\\SEPM\\RAPPORTS\\analyse.pdf', 'analyse.pdf', 3072000, 'c9d0e1f2', base_time - timedelta(days=6)),
        
        # Archives (gros fichiers)
        ('\\\\172.16.252.34\\Public\\SEPM\\ARCHIVES\\archive_2023.zip', 'archive_2023.zip', 104857600, 'g3h4i5j6', base_time - timedelta(days=200)),
        ('\\\\172.16.252.34\\Public\\SEPM\\ARCHIVES\\backup_complet.tar', 'backup_complet.tar', 209715200, 'k7l8m9n0', base_time - timedelta(days=300)),
    ]
    
    for path, name, size, checksum, mod_time in files:
        test_data.append((
            path, name, size, checksum,
            mod_time.isoformat(), False, False, None,
            base_time.isoformat(), base_time.isoformat()
        ))
    
    # Insérer les données
    cursor.executemany('''
        INSERT OR REPLACE INTO files (path, name, size, checksum, last_modified, is_directory, is_duplicate, duplicate_of, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', test_data)
    
    # Marquer les doublons
    duplicates = [
        ('\\\\172.16.252.34\\Public\\SEPM\\ADMIN\\budget2024_backup.xlsx', 'q7r8s9t0'),
        ('\\\\172.16.252.34\\Public\\SEPM\\RAPPORTS\\rapport_mensuel_v2.docx', 'y5z6a7b8'),
    ]
    
    for path, checksum in duplicates:
        cursor.execute('''
            UPDATE files 
            SET is_duplicate = 1 
            WHERE checksum = ? AND path != ?
        ''', (checksum, path))
    
    conn.commit()
    
    # Statistiques
    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 1")
    directories = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 0")
    files_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE is_duplicate = 1")
    duplicates_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(size) FROM files WHERE is_directory = 0")
    total_size = cursor.fetchone()[0] or 0
    
    print(f"✅ Base de données SQLite créée avec succès:")
    print(f"   📁 Total enregistrements: {total}")
    print(f"   📂 Dossiers: {directories}")
    print(f"   📄 Fichiers: {files_count}")
    print(f"   🔄 Doublons: {duplicates_count}")
    print(f"   💾 Taille totale: {total_size:,} octets ({total_size / 1024 / 1024:.1f} MB)")
    
    conn.close()

if __name__ == "__main__":
    create_test_data()
