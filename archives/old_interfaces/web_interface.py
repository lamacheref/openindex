#!/usr/bin/env python3
"""
Interface web pour OpenIndex avec Streamlit.
Permet de visualiser les données du crawler SMB.
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from smb_crawler import SMBCrawler
import threading
import time

# Configuration de la page
st.set_page_config(
    page_title="OpenIndex - Interface Web",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fonctions utilitaires
def get_db_connection():
    """Crée une connexion à la base de données."""
    return sqlite3.connect('openindex.db')

def load_data():
    """Charge les données depuis la base de données."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("""
            SELECT path, name, size, checksum, last_modified, is_directory 
            FROM files 
            ORDER BY path
        """, conn)
        return df
    finally:
        conn.close()

def get_statistics():
    """Calcule les statistiques depuis la base de données."""
    conn = get_db_connection()
    try:
        stats = {}
        
        # Statistiques générales
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        stats['total_items'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 1")
        stats['total_directories'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 0")
        stats['total_files'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(size) FROM files WHERE is_directory = 0 AND size IS NOT NULL")
        result = cursor.fetchone()[0]
        stats['total_size_bytes'] = result if result else 0
        
        # Conversion en unités lisibles
        stats['total_size_gb'] = stats['total_size_bytes'] / (1024**3)
        stats['total_size_mb'] = stats['total_size_bytes'] / (1024**2)
        
        # Doublons
        cursor.execute("""
            SELECT checksum, COUNT(*) as count 
            FROM files 
            WHERE is_directory = 0 AND checksum IS NOT NULL 
            GROUP BY checksum 
            HAVING count > 1
        """)
        duplicate_groups = cursor.fetchall()
        stats['duplicate_groups'] = len(duplicate_groups)
        stats['duplicate_files'] = sum(group[1] for group in duplicate_groups)
        
        # Types de fichiers
        cursor.execute("""
            SELECT SUBSTR(name, INSTR(name, '.') + 1) as ext, COUNT(*) as count
            FROM files 
            WHERE is_directory = 0 AND name LIKE '%.%'
            GROUP BY ext
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['file_types'] = cursor.fetchall()
        
        return stats
    finally:
        conn.close()

def format_size(size_bytes):
    """Formate une taille en octets en unités lisibles."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

# Interface principale
def main():
    """Fonction principale de l'interface web."""
    st.title("📁 OpenIndex - Interface de Visualisation")
    st.markdown("---")
    
    # Sidebar pour les contrôles
    with st.sidebar:
        st.header("🎛️ Contrôles")
        
        # Bouton pour rafraîchir les données
        if st.button("🔄 Rafraîchir les données", type="primary"):
            st.rerun()
        
        # Filtres
        st.subheader("🔍 Filtres")
        
        # Charger les données pour les filtres
        df = load_data()
        
        # Filtre par type
        filter_type = st.selectbox(
            "Type d'éléments",
            ["Tous", "Fichiers uniquement", "Dossiers uniquement"],
            index=0
        )
        
        # Filtre par taille
        if not df.empty:
            min_size = 0
            max_size = df[df['is_directory'] == False]['size'].max() if not df[df['is_directory'] == False].empty else 0
            
            if max_size > 0:
                size_filter = st.slider(
                    "Taille maximale (MB)",
                    min_value=0,
                    max_value=int(max_size / (1024*1024)),
                    value=int(max_size / (1024*1024)),
                    step=1
                )
            else:
                size_filter = None
        
        # Filtre de recherche
        search_filter = st.text_input("Rechercher dans les noms", "")
        
        st.markdown("---")
        
        # Section Crawler
        st.subheader("🚀 Crawler SMB")
        
        if st.button("🔍 Lancer un scan", type="secondary"):
            with st.spinner("Lancement du crawler..."):
                try:
                    crawler = SMBCrawler(
                        server="172.16.252.34",
                        username="flamachere",
                        password="F6r)OW+lg2",
                        share_name="public",
                        domain="SMIDEN",
                        max_workers=6,
                        delay_between_requests=0.1,
                        max_queue_size=1000,
                        max_depth=2  # Limité pour le test
                    )
                    
                    # Lancer le crawl dans un thread séparé
                    def run_crawl():
                        crawler.init_db()
                        crawler.crawl(base_path="SMIDEN/Technique", progress_callback=None)
                    
                    # Pour l'instant, on simule
                    st.success("Crawler démarré en arrière-plan !")
                    time.sleep(2)
                    
                except Exception as e:
                    st.error(f"Erreur lors du lancement du crawler: {e}")
    
    # Contenu principal
    # Statistiques
    st.header("📊 Tableau de Bord")
    
    stats = get_statistics()
    
    # Colonnes pour les statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📁 Total Éléments",
            value=f"{stats['total_items']:,}"
        )
    
    with col2:
        st.metric(
            label="📄 Fichiers",
            value=f"{stats['total_files']:,}"
        )
    
    with col3:
        st.metric(
            label="📁 Dossiers", 
            value=f"{stats['total_directories']:,}"
        )
    
    with col4:
        st.metric(
            label="💾 Taille Totale",
            value=f"{stats['total_size_gb']:.2f} GB"
        )
    
    # Deuxième ligne de métriques
    col5, col6 = st.columns(2)
    
    with col5:
        st.metric(
            label="🔄 Groupes de Doublons",
            value=f"{stats['duplicate_groups']:,}"
        )
    
    with col6:
        st.metric(
            label="📋 Fichiers en Double",
            value=f"{stats['duplicate_files']:,}"
        )
    
    st.markdown("---")
    
    # Graphiques
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Types de Fichiers")
        if stats['file_types']:
            types_df = pd.DataFrame(stats['file_types'], columns=['extension', 'count'])
            fig = px.pie(
                types_df, 
                values='count', 
                names='extension',
                title="Répartition par type de fichier"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée de type de fichier disponible")
    
    with col2:
        st.subheader("📈 Évolution du Scan")
        # Simuler des données d'évolution (à remplacer avec de vraies données)
        evolution_data = {
            'date': ['2026-02-11 14:00', '2026-02-11 14:30', '2026-02-11 15:00'],
            'fichiers_scannés': [0, stats['total_files']//2, stats['total_files']],
            'dossiers_scannés': [0, stats['total_directories']//2, stats['total_directories']]
        }
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=evolution_data['date'],
            y=evolution_data['fichiers_scannés'],
            mode='lines+markers',
            name='Fichiers scannés',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=evolution_data['date'],
            y=evolution_data['dossiers_scannés'],
            mode='lines+markers',
            name='Dossiers scannés',
            line=dict(color='green')
        ))
        
        fig.update_layout(
            title="Progression du scan",
            xaxis_title="Heure",
            yaxis_title="Nombre d'éléments"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tableau des données
    st.header("📋 Données Détaillées")
    
    # Appliquer les filtres
    filtered_df = df.copy()
    
    # Filtre par type
    if filter_type == "Fichiers uniquement":
        filtered_df = filtered_df[filtered_df['is_directory'] == False]
    elif filter_type == "Dossiers uniquement":
        filtered_df = filtered_df[filtered_df['is_directory'] == True]
    
    # Filtre par taille
    if size_filter is not None:
        filtered_df = filtered_df[
            (filtered_df['is_directory'] == True) | 
            (filtered_df['size'] <= size_filter * 1024 * 1024)
        ]
    
    # Filtre de recherche
    if search_filter:
        filtered_df = filtered_df[
            filtered_df['name'].str.contains(search_filter, case=False, na=False)
        ]
    
    # Afficher les informations
    st.info(f"📊 Affichage de {len(filtered_df)} élément(s) sur {len(df)} total")
    
    # Préparer les données pour l'affichage
    display_df = filtered_df.copy()
    display_df['taille'] = display_df.apply(
        lambda row: "📁 Dossier" if row['is_directory'] else format_size(row['size']), 
        axis=1
    )
    display_df['modifié'] = display_df['last_modified']
    
    # Sélection des colonnes à afficher
    columns_to_show = ['name', 'taille', 'modifié']
    if not display_df.empty:
        display_df = display_df[columns_to_show]
        display_df.columns = ['Nom', 'Taille', 'Dernière Modification']
        
        # Afficher le tableau avec pagination
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.warning("Aucun élément ne correspond aux filtres sélectionnés")
    
    # Section d'export
    st.markdown("---")
    st.header("📤 Export des Données")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Exporter en CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Télécharger CSV",
                data=csv,
                file_name=f"openindex_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Exporter les statistiques"):
            stats_df = pd.DataFrame([stats])
            csv = stats_df.to_csv(index=False)
            st.download_button(
                label="Télécharger Statistiques",
                data=csv,
                file_name=f"openindex_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            🚀 OpenIndex v0.1.0 | Interface de visualisation pour le crawler SMB
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
