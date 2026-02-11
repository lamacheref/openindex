#!/usr/bin/env python3
"""
Script pour afficher les métadonnées de la base de données SQLite.
Ce script permet de visualiser les fichiers indexés dans la base de données.
"""

import sqlite3
import pandas as pd

def view_metadata(db_path='openindex.db'):
    """
    Affiche les métadonnées des fichiers stockés dans la base de données.

    Args:
        db_path (str): Chemin vers la base de données SQLite.
    """
    # Connexion à la base de données
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Exécuter une requête pour récupérer toutes les métadonnées
    cursor.execute("""
        SELECT path, name, size, checksum, last_modified, is_directory FROM files
    """)

    # Récupérer les résultats
    rows = cursor.fetchall()

    # Fermer la connexion
    conn.close()

    if not rows:
        print("Aucune métadonnée trouvée dans la base de données.")
        return

    # Afficher les résultats sous forme de tableau
    df = pd.DataFrame(rows, columns=['Chemin', 'Nom', 'Taille (octets)', 'Checksum SHA-256', 'Dernière modification', 'Est un dossier'])
    print(df.to_string(index=False))

if __name__ == "__main__":
    view_metadata()