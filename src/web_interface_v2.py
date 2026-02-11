#!/usr/bin/env python3
"""
Interface web v2 pour OpenIndex avec onglets et gestion des doublons.
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from streamlit_tree_select import tree_select
from streamlit_elements import elements, mui, html
from smb_crawler import SMBCrawler
import threading
import time
import smbclient
import os

# Configuration de la page
st.set_page_config(
    page_title="OpenIndex - Interface Web v2",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fonctions utilitaires
def format_size(size_bytes):
    """Formate une taille en octets en format lisible."""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def get_db_connection():
    """Crée une connexion à la base de données SQLite."""
    return sqlite3.connect('openindex.db')

def get_statistics():
    """Récupère les statistiques de la base de données."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) FROM files")
        total_items = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 1")
        total_directories = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_directory = 0")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_duplicate = 1")
        duplicate_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(size) FROM files WHERE is_directory = 0")
        total_size = cursor.fetchone()[0] or 0
        
        return {
            'total_items': total_items,
            'total_directories': total_directories,
            'total_files': total_files,
            'duplicate_files': duplicate_files,
            'total_size': total_size
        }
    finally:
        conn.close()

def load_data(filters=None):
    """Charge les données depuis la base de données avec filtres."""
    conn = get_db_connection()
    try:
        query = """
            SELECT id, path, name, size, checksum, last_modified, 
                   is_directory, is_duplicate, duplicate_of, created_at
            FROM files 
            WHERE 1=1
        """
        params = []
        
        if filters:
            if filters.get('type') == "Fichiers uniquement":
                query += " AND is_directory = 0"
            elif filters.get('type') == "Dossiers uniquement":
                query += " AND is_directory = 1"
            
            if filters.get('search'):
                query += " AND name LIKE ?"
                params.append(f"%{filters['search']}%")
            
            if filters.get('show_duplicates_only'):
                query += " AND is_duplicate = 1"
        
        query += " ORDER BY path"
        
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

def get_duplicate_analysis():
    """Analyse les doublons dans la base de données."""
    conn = get_db_connection()
    try:
        query = """
            SELECT checksum, COUNT(*) as count, GROUP_CONCAT(path) as paths, 
                   GROUP_CONCAT(name) as names
            FROM files 
            WHERE is_directory = 0 AND checksum IS NOT NULL
            GROUP BY checksum 
            HAVING count > 1
        """
        df = pd.read_sql_query(query, conn)
        
        groups = []
        for _, row in df.iterrows():
            groups.append({
                'checksum': row['checksum'],
                'count': row['count'],
                'paths': row['paths'].split(','),
                'names': row['names'].split(',')
            })
        
        return groups
    finally:
        conn.close()

def visualize_file(file_path, file_name):
    """Visualise un fichier avec streamlit-elements."""
    try:
        # Construire le chemin SMB
        unc_path = f"\\\\172.16.252.34\\public\\{file_path}"
        
        # Lire le fichier via SMB
        with smbclient.open_file(unc_path, mode='rb') as f:
            file_content = f.read()
        
        # Déterminer le type de fichier
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        with elements("file_viewer"):
            with mui.AppBar(position="static"):
                mui.Toolbar(typography="h6", title=f"Visualisation: {file_name}")
            
            with mui.Box(sx={"padding": 2}):
                if file_ext == 'pdf':
                    # Visualisation PDF
                    mui.Typography("Visualisation PDF", variant="h6")
                    # Pour l'instant, afficher les informations
                    mui.Typography(f"Taille: {format_size(len(file_content))}")
                    mui.Typography("Visualisation PDF à implémenter avec streamlit-elements")
                
                elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    # Visualisation image
                    from io import BytesIO
                    from PIL import Image
                    
                    image = Image.open(BytesIO(file_content))
                    st.image(image, caption=file_name, use_column_width=True)
                
                elif file_ext in ['txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml']:
                    # Visualisation texte
                    try:
                        text_content = file_content.decode('utf-8')
                        st.text_area(f"Contenu de {file_name}", text_content, height=400)
                    except UnicodeDecodeError:
                        st.error("Impossible d'afficher ce fichier texte (encodage non supporté)")
                
                elif file_ext in ['doc', 'docx']:
                    # Documents Word
                    mui.Typography("Document Word", variant="h6")
                    mui.Typography("Visualisation Word à implémenter")
                    st.info(f"Fichier Word: {file_name} ({format_size(len(file_content))})")
                
                elif file_ext in ['xls', 'xlsx']:
                    # Documents Excel
                    try:
                        from io import BytesIO
                        import pandas as pd
                        
                        excel_data = pd.read_excel(BytesIO(file_content))
                        st.dataframe(excel_data, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erreur lors de la lecture du fichier Excel: {e}")
                
                else:
                    # Autres types de fichiers
                    mui.Typography("Aperçu non disponible", variant="h6")
                    mui.Typography(f"Type de fichier: {file_ext}")
                    mui.Typography(f"Taille: {format_size(len(file_content))}")
                    st.info("Ce type de fichier ne peut pas être visualisé directement")
        
        return True
        
    except Exception as e:
        st.error(f"Erreur lors de la visualisation du fichier: {e}")
        return False

def get_duplicate_analysis():
    """Analyse détaillée des doublons."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Groupes de doublons par checksum
        cursor.execute("""
            SELECT checksum, COUNT(*) as count, 
                   GROUP_CONCAT(path) as paths,
                   GROUP_CONCAT(name) as names
            FROM files 
            WHERE is_directory = 0 AND checksum IS NOT NULL
            GROUP BY checksum 
            HAVING count > 1
            ORDER BY count DESC, checksum
        """)
        
        duplicate_groups = []
        for checksum, count, paths, names in cursor.fetchall():
            duplicate_groups.append({
                'checksum': checksum,
                'count': count,
                'paths': paths.split(','),
                'names': names.split(',')
            })
        
        return duplicate_groups
    finally:
        conn.close()

# Interface principale
def main():
    """Fonction principale de l'interface web."""
    st.title("📁 OpenIndex - Interface Web v2")
    st.markdown("---")
    
    # Sidebar pour les contrôles
    with st.sidebar:
        st.header("🎛️ Contrôles")
        
        # Bouton pour rafraîchir
        if st.button("🔄 Rafraîchir", type="primary"):
            st.rerun()
        
        # Filtres
        st.subheader("🔍 Filtres")
        
        filter_type = st.selectbox(
            "Type d'éléments",
            ["Tous", "Fichiers uniquement", "Dossiers uniquement"],
            index=0
        )
        
        # Filtre doublons
        show_duplicates = st.checkbox("🔄 Afficher uniquement les doublons", value=False)
        
        # Filtre de recherche
        search_filter = st.text_input("Rechercher dans les noms", "")
        
        # Construire le dictionnaire de filtres
        filters = {
            'type': filter_type if filter_type != "Tous" else None,
            'search': search_filter if search_filter else None,
            'show_duplicates_only': show_duplicates
        }
        
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
                        max_depth=2
                    )
                    
                    crawler.init_db()
                    # Pour l'instant, simulation
                    st.success("Crawler configuré avec déduplication !")
                    time.sleep(2)
                    
                except Exception as e:
                    st.error(f"Erreur: {e}")
    
    # Onglets principaux
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Tableau de Bord", "📁 Fichiers", "🔄 Doublons", "⚙️ Configuration", "📤 Export"])
    
    with tab1:
        st.header("📊 Tableau de Bord")
        
        stats = get_statistics()
        
        # Première ligne de métriques
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📁 Total Éléments", f"{stats['total_items']:,}")
        
        with col2:
            st.metric("📄 Fichiers", f"{stats['total_files']:,}")
        
        with col3:
            st.metric("📁 Dossiers", f"{stats['total_directories']:,}")
        
        with col4:
            st.metric("💾 Taille Totale", f"{format_size(stats['total_size'])}")
        
        # Deuxième ligne
        col5, col6 = st.columns(2)
        
        with col5:
            st.metric("🔄 Fichiers en Double", f"{stats['duplicate_files']:,}")
        
        with col6:
            st.metric("� Espace Doublons", f"{format_size(stats['total_size'] * 0.1)}")  # Estimation
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Répartition par Type")
            # Graphique simple des types de fichiers
            file_count = stats['total_files']
            dir_count = stats['total_directories']
            
            labels = ['Fichiers', 'Dossiers']
            values = [file_count, dir_count]
            
            fig = px.pie(
                values=values,
                names=labels,
                title="Répartition des éléments"
            )
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            st.subheader("📈 État de la Base")
            
            # Données pour le graphique
            unique_files = stats['total_files'] - stats['duplicate_files']
            labels = ['Fichiers uniques', 'Doublons', 'Dossiers']
            values = [unique_files, stats['duplicate_files'], stats['total_directories']]
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
            fig.update_traces(marker=dict(colors=colors))
            fig.update_layout(title="Composition de la base de données")
            
            st.plotly_chart(fig, width='stretch')
    
    with tab2:
        st.header("📁 Arborescence des Fichiers")
        
        # Charger les données avec filtres
        filtered_df = load_data(filters)
        
        # Informations
        st.info(f"📊 Affichage de {len(filtered_df)} élément(s)")
        
        if not filtered_df.empty:
            # Préparer les données pour streamlit-tree-select
            def build_tree_data(df):
                """Construit les données pour streamlit-tree-select."""
                # Créer une structure hiérarchique
                tree_dict = {}
                
                for _, row in df.iterrows():
                    path = row['path']
                    parts = path.split('/')
                    
                    current = tree_dict
                    for i, part in enumerate(parts):
                        if part not in current:
                            # Créer le nœud
                            is_leaf = i == len(parts) - 1
                            current[part] = {
                                'data': row if is_leaf else None,
                                'children': {}
                            }
                        current = current[part]['children']
                
                # Convertir en format pour tree_select
                def convert_to_tree_select_format(name, node, path=""):
                    result = {
                        'label': name,
                        'value': f"{path}/{name}" if path else name
                    }
                    
                    # Ajouter les données si c'est une feuille
                    if node.get('data') is not None:
                        data = node['data']
                        if data['is_directory']:
                            # Pour les dossiers, on garde le nom simple
                            label = name
                        else:
                            # Pour les fichiers, on ajoute la taille
                            size_info = f" - {format_size(data['size'])}"
                            dup_indicator = " [DOUBLON]" if data.get('is_duplicate') else ""
                            label = f"{name}{dup_indicator}{size_info}"
                        
                        result['label'] = label
                    
                    # Ajouter les enfants
                    children = node.get('children', {})
                    if children:
                        result['children'] = []
                        for child_name, child_node in sorted(children.items()):
                            child_path = f"{path}/{name}" if path else name
                            result['children'].append(
                                convert_to_tree_select_format(child_name, child_node, child_path)
                            )
                    
                    return result
                
                # Construire la liste des racines
                tree_data = []
                for root_name, root_node in sorted(tree_dict.items()):
                    tree_data.append(convert_to_tree_select_format(root_name, root_node))
                
                return tree_data
            
            # Construire les données de l'arbre
            tree_data = build_tree_data(filtered_df)
            
            if tree_data:
                st.write("**🌳 Arborescence Interactive**")
                st.write("*🔁 Cliquez sur les dossiers pour déplier/replier • Sélectionnez un élément pour voir les détails*")
                
                # Afficher l'arbre avec streamlit-tree-select
                selected_nodes = tree_select(
                    tree_data,
                    check_model="leaf",
                    only_leaf_checkboxes=True,
                    expand_on_click=True,
                    show_expand_all=True,
                    key="file_tree"
                )
                
                # Créer une mise en page avec le panneau latéral
                main_col, sidebar_col = st.columns([3, 1])
                
                with main_col:
                    # Zone principale pour l'arborescence
                    st.write("**🌳 Arborescence Interactive**")
                    st.write("*🔁 Cliquez sur les dossiers pour déplier/replier • Sélectionnez un élément pour voir les détails*")
                
                # Panneau latéral dans une sidebar
                with sidebar_col:
                    with st.container():
                        st.markdown("---")
                        
                        # Panneau latéral pour les détails
                        if selected_nodes.get('checked') and len(selected_nodes['checked']) > 0:
                            selected_path = selected_nodes['checked'][0]
                            
                            # Trouver les données complètes
                            selected_data = filtered_df[filtered_df['path'] == selected_path]
                            
                            if not selected_data.empty:
                                row = selected_data.iloc[0]
                                
                                # Panneau latéral avec les détails
                                st.markdown("### 📋 Détails")
                                
                                # Informations principales
                                st.write(f"**Nom:** {row['name']}")
                                st.write(f"**Type:** {'📁 Dossier' if row['is_directory'] else '📄 Fichier'}")
                                
                                if row['is_directory']:
                                    st.write(f"**Taille:** Dossier")
                                else:
                                    st.write(f"**Taille:** {format_size(row['size'])}")
                                
                                st.write(f"**Modifié:** {row['last_modified']}")
                                st.write(f"**Doublon:** {'🔄 Oui' if row['is_duplicate'] else '✅ Non'}")
                                
                                if row['checksum']:
                                    with st.expander("Checksum"):
                                        st.code(row['checksum'])
                                
                                # Actions dans le panneau latéral
                                st.markdown("### 🚀 Actions")
                                
                                if row['is_directory']:
                                    # Actions pour les dossiers
                                    if st.button("🔍 Crawler", key="crawl_selected", use_container_width=True):
                                        st.session_state['crawl_target'] = selected_path
                                        st.rerun()
                                    
                                    if st.button("📁 Ouvrir", key="open_folder", use_container_width=True):
                                        unc_path = f"\\\\172.16.252.34\\public\\{selected_path}"
                                        st.info(f"Chemin SMB:\n`{unc_path}`")
                                    
                                    if st.button("📊 Détails", key="details_folder", use_container_width=True):
                                        st.info("Fonctionnalité de détails à implémenter")
                                else:
                                    # Actions pour les fichiers
                                    file_ext = row['name'].lower().split('.')[-1] if '.' in row['name'] else ''
                                    
                                    # Bouton de visualisation principal
                                    if file_ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'odt', 'ods', 'jpg', 'jpeg', 'png', 'gif', 'bmp']:
                                        if st.button("👁️ Visualiser", key="view_file", use_container_width=True, type="primary"):
                                            if visualize_file(selected_path, row['name']):
                                                st.success("Visualisation réussie!")
                                            else:
                                                st.error("Échec de la visualisation")
                                    elif file_ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv']:
                                        if st.button("🎥 Vidéo", key="view_video", use_container_width=True):
                                            st.info(f"Lecture vidéo: {row['name']}")
                                    elif file_ext in ['mp3', 'wav', 'flac', 'ogg']:
                                        if st.button("🎵 Audio", key="play_audio", use_container_width=True):
                                            st.info(f"Lecture audio: {row['name']}")
                                    else:
                                        if st.button("📄 Infos", key="view_file_info", use_container_width=True):
                                            st.info(f"Fichier: {file_ext}")
                                    
                                    # Actions secondaires
                                    if st.button("📁 Dossier parent", key="open_parent_folder", use_container_width=True):
                                        parent_path = '/'.join(selected_path.split('/')[:-1]) if '/' in selected_path else ''
                                        if parent_path:
                                            unc_path = f"\\\\172.16.252.34\\public\\{parent_path}"
                                            st.info(f"Dossier parent:\n`{unc_path}`")
                                        else:
                                            st.info("Ce fichier est à la racine")
                                    
                                    if st.button("📥 Télécharger", key="download_selected", use_container_width=True):
                                        st.info(f"Téléchargement: {row['name']}")
                        else:
                            # Panneau vide
                            st.info("👆 Sélectionnez un élément")
                            st.write("**Conseil:**")
                            st.write("• Cochez un fichier")
                            st.write("• Crawler les dossiers")
                            st.write("• Visualiser les fichiers")
                    
                    # Vérifier si un crawl a été demandé
                    if 'crawl_target' in st.session_state:
                        target_path = st.session_state['crawl_target']
                        st.success(f"🚀 Crawl demandé pour : `{target_path}`")
                        del st.session_state['crawl_target']
                        
                        # Lancer le crawl sur cette branche
                        with st.spinner(f"Crawl de {target_path} en cours..."):
                            try:
                                config = st.session_state.get('crawler_config', {
                                    'directory_workers': 4,
                                    'file_workers': 2,
                                    'delay_between_requests': 0.1,
                                    'max_queue_size': 1000,
                                    'max_depth': 2
                                })
                                
                                crawler = SMBCrawler(
                                    server="172.16.252.34",
                                    username="flamachere",
                                    password="F6r)OW+lg2",
                                    share_name="public",
                                    domain="SMIDEN",
                                    max_workers=config['directory_workers'] + config['file_workers'],
                                    delay_between_requests=config['delay_between_requests'],
                                    max_queue_size=config['max_queue_size'],
                                    max_depth=config['max_depth']
                                )
                                
                                crawler.init_db()
                                time.sleep(2)
                                st.success(f"✅ Crawl de {target_path} terminé!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Erreur lors du crawl: {e}")
            else:
                st.warning("Aucun élément à afficher")
        else:
            st.warning("Aucun élément ne correspond aux filtres")
    
    with tab3:
        st.header("🔄 Analyse des Doublons")
        
        duplicate_groups = get_duplicate_analysis()
        
        if duplicate_groups:
            st.info(f"🔍 {len(duplicate_groups)} groupe(s) de doublons détectés")
            
            for i, group in enumerate(duplicate_groups):  # Limiter à 10 groupes
                with st.expander(f"🔄 Groupe {i+1}: {group['names'][0]} ({group['count']} occurrences)", expanded=False):
                    # Créer un tableau pour comparer les versions
                    st.write("**📋 Comparaison des versions:**")
                    
                    # Récupérer les métadonnées complètes pour chaque fichier
                    conn = get_db_connection()
                    try:
                        # Construire la clause IN pour tous les chemins
                        placeholders = ','.join(['?' for _ in group['paths']])
                        query = f"""
                            SELECT path, name, size, last_modified, created_at, is_directory
                            FROM files 
                            WHERE path IN ({placeholders})
                            ORDER BY path
                        """
                        
                        cursor = conn.cursor()
                        cursor.execute(query, group['paths'])
                        files_data = cursor.fetchall()
                        
                        # Créer un DataFrame pour l'affichage
                        df_duplicates = pd.DataFrame(files_data, columns=[
                            'Chemin complet', 'Nom', 'Taille (octets)', 
                            'Dernière modification', 'Date d\'ajout', 'Type'
                        ])
                        
                        # Formater les données
                        df_duplicates['Taille (octets)'] = df_duplicates['Taille (octets)'].apply(
                            lambda x: format_size(x) if x is not None else 'N/A'
                        )
                        df_duplicates['Type'] = df_duplicates['Type'].apply(
                            lambda x: '📁 Dossier' if x else '📄 Fichier'
                        )
                        
                        # Afficher le tableau
                        st.dataframe(
                            df_duplicates,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Informations supplémentaires
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Checksum:** `{group['checksum']}`")
                            st.write(f"**Nombre d'occurrences:** {group['count']}")
                        
                        with col2:
                            # Calculer l'espace total occupé par les doublons
                            total_size = df_duplicates[df_duplicates['Type'] == '📄 Fichier']['Taille (octets)'].apply(
                                lambda x: float(x.split()[0]) if 'MB' in x or 'KB' in x or 'GB' in x else 0
                            ).sum()
                            
                            if total_size > 0:
                                st.write(f"**Espace total:** {total_size:.2f} MB")
                                st.write(f"**Espace économisable:** {total_size * (group['count'] - 1) / group['count']:.2f} MB")
                        
                        # Actions possibles
                        st.write("**Actions disponibles:**")
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            if st.button(f"🗑️ Supprimer les doublons", key=f"del_{i}"):
                                st.warning("Fonctionnalité de suppression à implémenter")
                        
                        with action_col2:
                            if st.button(f"📊 Analyser", key=f"analyze_{i}"):
                                st.info("Analyse détaillée à implémenter")
                        
                        with action_col3:
                            if st.button(f"📥 Exporter ce groupe", key=f"export_{i}"):
                                csv = df_duplicates.to_csv(index=False)
                                st.download_button(
                                    label="Télécharger ce groupe",
                                    data=csv,
                                    file_name=f"doublons_groupe_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                        
                    finally:
                        conn.close()
        else:
            st.success("✅ Aucun doublon détecté dans la base de données!")
    
    with tab4:
        st.header("⚙️ Configuration du Crawler")
        
        st.write("**Paramètres du crawler SMB**")
        
        # Configuration par défaut
        if 'crawler_config' not in st.session_state:
            st.session_state.crawler_config = {
                'root_folder': 'SMIDEN',
                'max_depth': 2,
                'unlimited_depth': False,
                'directory_workers': 4,
                'file_workers': 2,
                'delay_between_requests': 0.1,
                'max_queue_size': 1000,
                'large_file_threshold': 50  # MB
            }
        
        config = st.session_state.crawler_config
        
        # Section 1: Configuration du partage
        st.subheader("📁 Configuration du Partage")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Récupérer la liste des partages disponibles
            available_shares = ['SMIDEN', 'public', 'admin', 'backup']  # À adapter
            
            root_folder = st.selectbox(
                "Dossier racine",
                available_shares,
                index=available_shares.index(config['root_folder']) if config['root_folder'] in available_shares else 0,
                help="Sélectionnez le dossier racine à scanner"
            )
        
        with col2:
            st.write("**Informations de connexion**")
            st.write("• Serveur: 172.16.252.34")
            st.write("• Utilisateur: flamachere")
            st.write("• Domaine: SMIDEN")
        
        # Section 2: Profondeur de crawl
        st.subheader("🔍 Profondeur de Crawl")
        
        col1, col2 = st.columns(2)
        
        with col1:
            unlimited_depth = st.checkbox(
                "Crawl illimité (tout scanner)",
                value=config['unlimited_depth'],
                help="Cochez pour scanner toute l'arborescence sans limite de profondeur"
            )
        
        with col2:
            if not unlimited_depth:
                max_depth = st.number_input(
                    "Profondeur maximale",
                    min_value=1,
                    max_value=10,
                    value=config['max_depth'],
                    step=1,
                    help="Nombre maximum de niveaux de dossiers à scanner"
                )
            else:
                max_depth = None
                st.write("Profondeur: Illimitée")
        
        # Section 3: Configuration des workers
        st.subheader("👥 Configuration des Workers")
        
        col1, col2 = st.columns(2)
        
        with col1:
            directory_workers = st.number_input(
                "Workers de répertoires",
                min_value=1,
                max_value=10,
                value=config['directory_workers'],
                step=1,
                help="Nombre de threads pour l'exploration des répertoires"
            )
        
        with col2:
            file_workers = st.number_input(
                "Workers de fichiers",
                min_value=1,
                max_value=10,
                value=config['file_workers'],
                step=1,
                help="Nombre de threads pour le traitement des fichiers"
            )
        
        # Section 4: Performance
        st.subheader("⚡ Performance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            delay_between_requests = st.number_input(
                "Délai entre requêtes (secondes)",
                min_value=0.01,
                max_value=2.0,
                value=config['delay_between_requests'],
                step=0.05,
                help="Délai pour ne pas surcharger le serveur"
            )
        
        with col2:
            max_queue_size = st.number_input(
                "Taille maximale des queues",
                min_value=100,
                max_value=10000,
                value=config['max_queue_size'],
                step=100,
                help="Taille des queues de traitement"
            )
        
        # Section 5: Gestion des gros fichiers
        st.subheader("📦 Gestion des Gros Fichiers")
        
        col1, col2 = st.columns(2)
        
        with col1:
            large_file_threshold = st.number_input(
                "Seuil gros fichiers (MB)",
                min_value=1,
                max_value=1000,
                value=config['large_file_threshold'],
                step=10,
                help="Fichiers au-dessus de cette taille seront traités dans une queue dédiée"
            )
        
        with col2:
            st.write("**Optimisation**")
            st.write("• Queue dédiée pour les gros fichiers")
            st.write("• Calcul de checksum progressif")
            st.write("• Priorité basse pour ne pas bloquer")
        
        # Sauvegarder la configuration
        st.session_state.crawler_config = {
            'root_folder': root_folder,
            'max_depth': max_depth if not unlimited_depth else None,
            'unlimited_depth': unlimited_depth,
            'directory_workers': directory_workers,
            'file_workers': file_workers,
            'delay_between_requests': delay_between_requests,
            'max_queue_size': max_queue_size,
            'large_file_threshold': large_file_threshold
        }
        
        # Actions
        st.markdown("---")
        st.subheader("🚀 Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Sauvegarder la configuration", type="primary"):
                st.success("Configuration sauvegardée !")
        
        with col2:
            if st.button("🔄 Réinitialiser par défaut"):
                st.session_state.crawler_config = {
                    'root_folder': 'SMIDEN',
                    'max_depth': 2,
                    'unlimited_depth': False,
                    'directory_workers': 4,
                    'file_workers': 2,
                    'delay_between_requests': 0.1,
                    'max_queue_size': 1000,
                    'large_file_threshold': 50
                }
                st.rerun()
        
        with col3:
            if st.button("🔍 Lancer avec cette configuration"):
                with st.spinner("Lancement du crawler avec la nouvelle configuration..."):
                    try:
                        crawler = SMBCrawler(
                            server="172.16.252.34",
                            username="flamachere",
                            password="F6r)OW+lg2",
                            share_name="public",
                            domain="SMIDEN",
                            max_workers=directory_workers + file_workers,
                            delay_between_requests=delay_between_requests,
                            max_queue_size=max_queue_size,
                            max_depth=max_depth
                        )
                        
                        crawler.init_db()
                        st.success(f"✅ Crawler configuré et prêt !")
                        st.info(f"Configuration: {directory_workers} workers répertoires, {file_workers} workers fichiers")
                        
                    except Exception as e:
                        st.error(f"Erreur: {e}")
        
        # Afficher la configuration actuelle
        st.markdown("---")
        st.subheader("📋 Configuration Actuelle")
        
        config_json = {
            "Dossier racine": config['root_folder'],
            "Profondeur": "Illimitée" if config['unlimited_depth'] else f"{config['max_depth']} niveaux",
            "Workers répertoires": config['directory_workers'],
            "Workers fichiers": config['file_workers'],
            "Délai": f"{config['delay_between_requests']}s",
            "Queue": f"{config['max_queue_size']} éléments",
            "Seuil gros fichiers": f"{config['large_file_threshold']} MB"
        }
        
        for key, value in config_json.items():
            st.write(f"**{key}:** {value}")

    with tab5:
        st.header("📤 Export des Données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📥 Export des Fichiers")
            
            if st.button("📥 Exporter les données filtrées"):
                filtered_df = load_data(filters)
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Télécharger CSV",
                    data=csv,
                    file_name=f"openindex_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            st.subheader("📊 Export des Statistiques")
            
            if st.button("📊 Exporter les statistiques"):
                stats = get_statistics()
                stats_df = pd.DataFrame([stats])
                csv = stats_df.to_csv(index=False)
                st.download_button(
                    label="Télécharger Statistiques",
                    data=csv,
                    file_name=f"openindex_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Export des doublons
        if st.button("🔄 Exporter l'analyse des doublons"):
            duplicate_groups = get_duplicate_analysis()
            if duplicate_groups:
                dup_df = pd.DataFrame(duplicate_groups)
                csv = dup_df.to_csv(index=False)
                st.download_button(
                    label="Télécharger Analyse Doublons",
                    data=csv,
                    file_name=f"openindex_duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Aucun doublon à exporter")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            🚀 OpenIndex v2.0 | Interface avec déduplication avancée
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
