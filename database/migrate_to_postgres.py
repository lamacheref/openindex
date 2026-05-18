#!/usr/bin/env python3
"""
Script de migration de SQLite vers PostgreSQL pour OpenIndex
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
from datetime import datetime
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SQLiteToPostgresMigrator:
    """Classe pour migrer les données de SQLite vers PostgreSQL"""
    
    def __init__(self, sqlite_path='openindex.db', postgres_config=None):
        self.sqlite_path = sqlite_path
        self.postgres_config = postgres_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'openindex',
            'user': 'openindex_user',
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        
    def connect_sqlite(self):
        """Connexion à la base SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            logger.info(f"Connecté à SQLite: {self.sqlite_path}")
            return conn
        except Exception as e:
            logger.error(f"Erreur connexion SQLite: {e}")
            raise
    
    def connect_postgres(self):
        """Connexion à PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            conn.autocommit = False
            logger.info("Connecté à PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise
    
    def check_sqlite_data(self):
        """Vérifie les données dans SQLite"""
        conn = self.connect_sqlite()
        try:
            cursor = conn.cursor()
            
            # Vérifier si la table existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
            if not cursor.fetchone():
                logger.error("Table 'files' non trouvée dans SQLite")
                return False
            
            # Compter les enregistrements
            cursor.execute("SELECT COUNT(*) as count FROM files")
            count = cursor.fetchone()['count']
            logger.info(f"Nombre d'enregistrements dans SQLite: {count}")
            
            # Afficher quelques exemples
            cursor.execute("SELECT * FROM files LIMIT 3")
            examples = cursor.fetchall()
            logger.info("Exemples d'enregistrements:")
            for row in examples:
                logger.info(f"  {dict(row)}")
            
            return count > 0
            
        finally:
            conn.close()
    
    def migrate_files(self):
        """Migration de la table files"""
        sqlite_conn = self.connect_sqlite()
        pg_conn = self.connect_postgres()
        
        try:
            sqlite_cursor = sqlite_conn.cursor()
            pg_cursor = pg_conn.cursor()
            
            # Lire les données SQLite
            sqlite_cursor.execute("SELECT * FROM files ORDER BY id")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.warning("Aucune donnée à migrer dans la table files")
                return 0
            
            logger.info(f"Début migration de {len(rows)} enregistrements...")
            
            # Préparer les données pour PostgreSQL
            pg_data = []
            for row in rows:
                # Convertir les types SQLite vers PostgreSQL
                pg_row = {
                    'path': row['path'],
                    'name': row['name'],
                    'size': row['size'],
                    'checksum': row['checksum'],
                    'last_modified': datetime.fromisoformat(row['last_modified']) if row['last_modified'] else None,
                    'is_directory': bool(row['is_directory']),
                    'is_duplicate': bool(row['is_duplicate']) if row['is_duplicate'] is not None else False,
                    'duplicate_of': row['duplicate_of'],
                    'created_at': datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                    'updated_at': datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
                }
                pg_data.append(pg_row)
            
            # Insérer par lots pour optimiser les performances
            batch_size = 1000
            migrated_count = 0
            
            for i in range(0, len(pg_data), batch_size):
                batch = pg_data[i:i + batch_size]
                
                values = [(
                    item['path'],
                    item['name'],
                    item['size'],
                    item['checksum'],
                    item['last_modified'],
                    item['is_directory'],
                    item['is_duplicate'],
                    item['duplicate_of'],
                    item['created_at'],
                    item['updated_at']
                ) for item in batch]
                
                execute_values(
                    pg_cursor,
                    """
                    INSERT INTO files (
                        path, name, size, checksum, last_modified,
                        is_directory, is_duplicate, duplicate_of,
                        created_at, updated_at
                    ) VALUES %s
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        size = EXCLUDED.size,
                        checksum = EXCLUDED.checksum,
                        last_modified = EXCLUDED.last_modified,
                        is_directory = EXCLUDED.is_directory,
                        is_duplicate = EXCLUDED.is_duplicate,
                        duplicate_of = EXCLUDED.duplicate_of,
                        updated_at = EXCLUDED.updated_at
                    """,
                    values
                )
                
                migrated_count += len(batch)
                logger.info(f"Migré: {migrated_count}/{len(pg_data)} enregistrements")
            
            pg_conn.commit()
            logger.info(f"Migration terminée: {migrated_count} enregistrements")
            return migrated_count
            
        except Exception as e:
            pg_conn.rollback()
            logger.error(f"Erreur lors de la migration: {e}")
            raise
        finally:
            sqlite_conn.close()
            pg_conn.close()
    
    def verify_migration(self):
        """Vérifie que la migration a réussi"""
        pg_conn = self.connect_postgres()
        try:
            pg_cursor = pg_conn.cursor()
            
            # Compter les enregistrements dans PostgreSQL
            pg_cursor.execute("SELECT COUNT(*) as count FROM files")
            pg_count = pg_cursor.fetchone()[0]
            
            logger.info(f"Nombre d'enregistrements dans PostgreSQL: {pg_count}")
            
            # Vérifier les doublons
            pg_cursor.execute("SELECT COUNT(*) as count FROM files WHERE is_duplicate = TRUE")
            duplicate_count = pg_cursor.fetchone()[0]
            logger.info(f"Nombre de doublons: {duplicate_count}")
            
            # Statistiques par taille
            pg_cursor.execute("SELECT * FROM file_size_distribution ORDER BY file_count DESC")
            size_stats = pg_cursor.fetchall()
            logger.info("Distribution par taille:")
            for stat in size_stats:
                logger.info(f"  {stat[0]}: {stat[1]} fichiers ({stat[2]} octets)")
            
            return pg_count
            
        finally:
            pg_conn.close()
    
    def run_migration(self):
        """Exécute la migration complète"""
        logger.info("Début de la migration SQLite vers PostgreSQL...")
        
        # Vérifier les données SQLite
        if not self.check_sqlite_data():
            logger.error("Aucune donnée à migrer")
            return False
        
        # Migrer les données
        try:
            migrated_count = self.migrate_files()
            
            # Vérifier la migration
            final_count = self.verify_migration()
            
            logger.info(f"Migration réussie: {migrated_count} → {final_count} enregistrements")
            return True
            
        except Exception as e:
            logger.error(f"Échec de la migration: {e}")
            return False

def main():
    """Fonction principale"""
    # Vérifier si le fichier SQLite existe
    sqlite_path = 'openindex.db'
    if not os.path.exists(sqlite_path):
        logger.error(f"Fichier SQLite non trouvé: {sqlite_path}")
        sys.exit(1)
    
    # Créer le migrateur
    migrator = SQLiteToPostgresMigrator(sqlite_path)
    
    # Exécuter la migration
    success = migrator.run_migration()
    
    if success:
        logger.info("✅ Migration terminée avec succès!")
        
        # Créer une sauvegarde du fichier SQLite
        backup_path = f"{sqlite_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(sqlite_path, backup_path)
        logger.info(f"📁 Fichier SQLite sauvegardé: {backup_path}")
        
    else:
        logger.error("❌ Échec de la migration")
        sys.exit(1)

if __name__ == "__main__":
    main()
