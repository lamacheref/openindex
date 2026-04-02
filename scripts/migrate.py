#!/usr/bin/env python3
"""
Système de gestion des migrations PostgreSQL pour OpenIndex
Permet d'appliquer les migrations de schéma de manière contrôlée
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

# Ajouter src au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from postgres_adapter import PostgreSQLAdapter


class MigrationManager:
    """Gestionnaire de migrations de schéma PostgreSQL."""

    def __init__(self, migrations_dir: str = None, postgres_config: dict = None):
        """
        Initialise le gestionnaire de migrations.

        Args:
            migrations_dir: Répertoire contenant les fichiers .sql
            postgres_config: Configuration de connexion PostgreSQL
        """
        self.migrations_dir = Path(migrations_dir or Path(__file__).parent)
        self.postgres_config = postgres_config or {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'openindex'),
            'user': os.getenv('POSTGRES_USER', 'openindex_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'openindex_secure_password')
        }
        self.adapter = PostgreSQLAdapter(self.postgres_config)
        self.adapter.initialize_database()

    def _get_applied_migrations(self) -> List[str]:
        """Récupère la liste des migrations déjà appliquées."""
        try:
            result = self.adapter.execute_query(
                "SELECT version FROM schema_migrations ORDER BY version",
                fetch=True
            )
            return [row[0] for row in result] if result else []
        except Exception:
            # La table n'existe peut-être pas encore
            return []

    def _get_available_migrations(self) -> List[Tuple[str, Path]]:
        """Récupère la liste des fichiers de migration disponibles."""
        migrations = []
        if self.migrations_dir.exists():
            for sql_file in sorted(self.migrations_dir.glob("*.sql")):
                # Extraire le numéro de version (ex: 001_add_archive_jobs.sql -> 001)
                version = sql_file.stem.split('_')[0]
                migrations.append((version, sql_file))
        return migrations

    def _calculate_checksum(self, filepath: Path) -> str:
        """Calcule le SHA256 d'un fichier."""
        hash_sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _apply_migration(self, version: str, filepath: Path) -> bool:
        """Applique une migration."""
        print(f"  🔄 Application de {filepath.name}...")

        try:
            # Lire le contenu du fichier
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Calculer le checksum
            checksum = self._calculate_checksum(filepath)

            # Exécuter la migration dans une transaction
            with self.adapter.get_connection() as conn:
                cursor = conn.cursor()

                # Exécuter le SQL
                cursor.execute(sql_content)

                # Enregistrer la migration
                description = self._extract_description(sql_content)
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, description, checksum)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (version) DO UPDATE SET
                        applied_at = CURRENT_TIMESTAMP,
                        checksum = EXCLUDED.checksum
                    """,
                    (version, description, checksum)
                )

                conn.commit()

            print(f"  ✅ Migration {version} appliquée avec succès")
            return True

        except Exception as exc:
            print(f"  ❌ Erreur lors de l'application de {version}: {exc}")
            return False

    def _extract_description(self, sql_content: str) -> str:
        """Extrait la description depuis les commentaires SQL."""
        for line in sql_content.split('\n'):
            if '-- Description:' in line:
                return line.split('-- Description:')[1].strip()
        return ""

    def migrate(self, target_version: Optional[str] = None) -> bool:
        """
        Applique toutes les migrations en attente.

        Args:
            target_version: Version cible (None = toutes les migrations)

        Returns:
            True si toutes les migrations ont été appliquées avec succès
        """
        print("🔍 Vérification des migrations...")

        # S'assurer que la table de suivi existe
        self._ensure_migrations_table()

        # Récupérer les migrations
        applied = set(self._get_applied_migrations())
        available = self._get_available_migrations()

        # Filtrer les migrations à appliquer
        pending = [(v, f) for v, f in available if v not in applied]

        if target_version:
            pending = [(v, f) for v, f in pending if v <= target_version]

        if not pending:
            print("✅ Toutes les migrations sont à jour")
            return True

        print(f"📦 {len(pending)} migration(s) à appliquer:")
        for version, filepath in pending:
            print(f"   - {filepath.name}")

        success = True
        for version, filepath in sorted(pending):
            if not self._apply_migration(version, filepath):
                success = False
                break

        if success:
            print(f"\n✅ Toutes les migrations ont été appliquées avec succès")
        else:
            print(f"\n⚠️  Certaines migrations ont échoué")

        return success

    def _ensure_migrations_table(self) -> None:
        """S'assure que la table de suivi des migrations existe."""
        try:
            self.adapter.execute_query(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    checksum VARCHAR(64)
                )
                """,
                fetch=False
            )
        except Exception as exc:
            print(f"⚠️  Erreur création table schema_migrations: {exc}")

    def status(self) -> None:
        """Affiche le statut des migrations."""
        print("📊 Statut des migrations:\n")

        # S'assurer que la table existe
        self._ensure_migrations_table()

        applied = set(self._get_applied_migrations())
        available = self._get_available_migrations()

        print(f"{'Version':<10} {'Statut':<12} {'Fichier'}")
        print("-" * 60)

        for version, filepath in available:
            status = "✅ Appliquée" if version in applied else "⏳ En attente"
            print(f"{version:<10} {status:<12} {filepath.name}")

        print(f"\nTotal: {len(available)} migration(s), {len(applied)} appliquée(s)")

    def rollback(self, version: str) -> bool:
        """
        Rollback vers une version spécifique.
        Note: Nécessite des fichiers de rollback .down.sql
        """
        print(f"🔄 Rollback vers la version {version}...")

        # Vérifier si des fichiers de rollback existent
        rollback_files = list(self.migrations_dir.glob(f"{version}_*.down.sql"))

        if not rollback_files:
            print(f"❌ Pas de fichier de rollback trouvé pour {version}")
            return False

        # TODO: Implémenter le rollback
        print("⚠️  Le rollback n'est pas encore implémenté")
        return False

    def create_migration(self, name: str) -> Optional[Path]:
        """
        Crée un nouveau fichier de migration.

        Args:
            name: Nom descriptif de la migration

        Returns:
            Path du fichier créé
        """
        # Trouver le prochain numéro de version
        available = self._get_available_migrations()
        if available:
            last_version = max(int(v) for v, _ in available)
            new_version = last_version + 1
        else:
            new_version = 1

        # Formater le numéro de version (001, 002, etc.)
        version_str = f"{new_version:03d}"

        # Créer le nom de fichier
        safe_name = name.lower().replace(' ', '_')
        filename = f"{version_str}_{safe_name}.sql"
        filepath = self.migrations_dir / filename

        # Template de migration
        template = f"""-- ============================================================
-- Migration {version_str}: {name}
-- Date: {datetime.now().strftime('%Y-%m-%d')}
-- Description: 
-- ============================================================

-- TODO: Ajouter les commandes SQL ici

-- Enregistrement de la migration
INSERT INTO schema_migrations (version, description) 
VALUES ('{version_str}', '{name}')
ON CONFLICT (version) DO NOTHING;
"""

        # Écrire le fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)

        print(f"✅ Migration créée: {filepath}")
        return filepath


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Gestionnaire de migrations PostgreSQL pour OpenIndex"
    )
    parser.add_argument(
        "command",
        choices=["migrate", "status", "rollback", "create"],
        help="Commande à exécuter"
    )
    parser.add_argument(
        "--migrations-dir",
        default=None,
        help="Répertoire des migrations (défaut: database/migrations)"
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Version cible pour migrate/rollback"
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Nom pour la commande create"
    )

    args = parser.parse_args()

    # Déterminer le répertoire des migrations
    migrations_dir = args.migrations_dir
    if not migrations_dir:
        # Par défaut, utiliser le répertoire database/migrations
        base_dir = Path(__file__).parent.parent
        migrations_dir = base_dir / "migrations"

    # Créer le répertoire s'il n'existe pas
    Path(migrations_dir).mkdir(parents=True, exist_ok=True)

    # Initialiser le gestionnaire
    manager = MigrationManager(migrations_dir=migrations_dir)

    # Exécuter la commande
    if args.command == "migrate":
        success = manager.migrate(target_version=args.target)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        manager.status()

    elif args.command == "rollback":
        if not args.target:
            print("❌ --target requis pour rollback")
            sys.exit(1)
        success = manager.rollback(args.target)
        sys.exit(0 if success else 1)

    elif args.command == "create":
        if not args.name:
            print("❌ --name requis pour create")
            sys.exit(1)
        manager.create_migration(args.name)


if __name__ == "__main__":
    main()
