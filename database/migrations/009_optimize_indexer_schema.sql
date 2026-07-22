-- ============================================================
-- Migration 009: Optimisation du schéma PostgreSQL pour l'indexeur
-- Date: 2026-05-18
-- Description: Tables optimisées avec index et contraintes
-- ============================================================

-- Table des espaces SMB (remplace la référence directe dans crawl_configs)
CREATE TABLE IF NOT EXISTS smb_spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    share VARCHAR(255) NOT NULL,
    domain_zone VARCHAR(255) NOT NULL,
    connection_username VARCHAR(255) NOT NULL,
    connection_password TEXT NOT NULL,
    connection_domain VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    total_files_indexed BIGINT DEFAULT 0,
    total_bytes_indexed BIGINT DEFAULT 0,
    UNIQUE (host, share)
);

-- Index pour les espaces actifs
CREATE INDEX IF NOT EXISTS idx_smb_spaces_active ON smb_spaces(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_smb_spaces_host ON smb_spaces(host);
CREATE INDEX IF NOT EXISTS idx_smb_spaces_name ON smb_spaces(name);

-- Table des répertoires (pour navigation rapide)
CREATE TABLE IF NOT EXISTS directories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID NOT NULL REFERENCES smb_spaces(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    parent_path TEXT,
    depth INTEGER NOT NULL,
    file_count INTEGER DEFAULT 0,
    directory_count INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (space_id, path)
);

-- Index pour les répertoires
CREATE INDEX IF NOT EXISTS idx_directories_space ON directories(space_id);
CREATE INDEX IF NOT EXISTS idx_directories_path ON directories(path);
CREATE INDEX IF NOT EXISTS idx_directories_parent ON directories(parent_path);
CREATE INDEX IF NOT EXISTS idx_directories_depth ON directories(depth);

-- Table des fichiers optimisée (remplace la table files existante)
CREATE TABLE IF NOT EXISTS indexed_files_optimized (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID NOT NULL REFERENCES smb_spaces(id) ON DELETE CASCADE,
    directory_id UUID REFERENCES directories(id) ON DELETE SET NULL,
    path TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    extension VARCHAR(50),
    size BIGINT NOT NULL,
    hash_xxh64 VARCHAR(16) NOT NULL,  -- xxHash 64 bits en hexa
    hash_sha256 VARCHAR(64),  -- SHA256 pour compatibilité (optionnel)
    last_modified TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_duplicate BOOLEAN NOT NULL DEFAULT false,
    duplicate_of UUID REFERENCES indexed_files_optimized(id) ON DELETE SET NULL,
    is_garbage BOOLEAN NOT NULL DEFAULT false,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (space_id, path)
);

-- Index optimisés pour les fichiers
CREATE INDEX IF NOT EXISTS idx_files_space ON indexed_files_optimized(space_id);
CREATE INDEX IF NOT EXISTS idx_files_path ON indexed_files_optimized(path);
CREATE INDEX IF NOT EXISTS idx_files_hash_xxh64 ON indexed_files_optimized(hash_xxh64);
CREATE INDEX IF NOT EXISTS idx_files_hash_sha256 ON indexed_files_optimized(hash_sha256);
CREATE INDEX IF NOT EXISTS idx_files_extension ON indexed_files_optimized(extension);
CREATE INDEX IF NOT EXISTS idx_files_size ON indexed_files_optimized(size);
CREATE INDEX IF NOT EXISTS idx_files_modified ON indexed_files_optimized(last_modified);
CREATE INDEX IF NOT EXISTS idx_files_duplicate ON indexed_files_optimized(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_files_garbage ON indexed_files_optimized(is_garbage);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON indexed_files_optimized(is_deleted);

-- Index partiel pour les fichiers actifs (non supprimés)
CREATE INDEX IF NOT EXISTS idx_files_active_path ON indexed_files_optimized(path) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_files_active_hash ON indexed_files_optimized(hash_xxh64) WHERE is_deleted = false;

-- Table des doublons (pour optimiser les requêtes de détection)
CREATE TABLE IF NOT EXISTS file_duplicates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_file_id UUID NOT NULL REFERENCES indexed_files_optimized(id) ON DELETE CASCADE,
    duplicate_file_id UUID NOT NULL REFERENCES indexed_files_optimized(id) ON DELETE CASCADE,
    hash_xxh64 VARCHAR(16) NOT NULL,
    size BIGINT NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (original_file_id, duplicate_file_id)
);

-- Index pour les doublons
CREATE INDEX IF NOT EXISTS idx_duplicates_original ON file_duplicates(original_file_id);
CREATE INDEX IF NOT EXISTS idx_duplicates_duplicate ON file_duplicates(duplicate_file_id);
CREATE INDEX IF NOT EXISTS idx_duplicates_hash ON file_duplicates(hash_xxh64);

-- Table des fichiers indésirables (garbage)
CREATE TABLE IF NOT EXISTS garbage_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES indexed_files_optimized(id) ON DELETE CASCADE,
    pattern VARCHAR(50) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ignored BOOLEAN NOT NULL DEFAULT false
);

-- Index pour les fichiers indésirables
CREATE INDEX IF NOT EXISTS idx_garbage_file ON garbage_files(file_id);
CREATE INDEX IF NOT EXISTS idx_garbage_pattern ON garbage_files(pattern);

-- Fonction pour détecter les doublons
CREATE OR REPLACE FUNCTION detect_duplicates()
RETURNS TABLE (
    original_id UUID,
    duplicate_id UUID,
    hash VARCHAR(16),
    size BIGINT,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH hash_groups AS (
        SELECT
            hash_xxh64,
            size,
            COUNT(*) as count
        FROM indexed_files_optimized
        WHERE is_deleted = false AND is_garbage = false
        GROUP BY hash_xxh64, size
        HAVING COUNT(*) > 1
    )
    SELECT
        f1.id as original_id,
        f2.id as duplicate_id,
        f1.hash_xxh64 as hash,
        f1.size as size,
        g.count
    FROM hash_groups g
    JOIN indexed_files_optimized f1 ON f1.hash_xxh64 = g.hash_xxh64 AND f1.size = g.size
    JOIN indexed_files_optimized f2 ON f2.hash_xxh64 = g.hash_xxh64 AND f2.size = g.size AND f2.id > f1.id
    WHERE f1.is_deleted = false AND f2.is_deleted = false
    ORDER BY f1.hash_xxh64, f1.size, f1.id, f2.id;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour détecter les fichiers indésirables
CREATE OR REPLACE FUNCTION detect_garbage_files()
RETURNS TABLE (
    file_id UUID,
    file_path TEXT,
    pattern VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id as file_id,
        f.path as file_path,
        CASE
            WHEN f.name LIKE '%.tmp' THEN '*.tmp'
            WHEN f.name LIKE '~%' THEN '~*'
            WHEN f.name = 'Thumbs.db' THEN 'Thumbs.db'
            WHEN f.name = '.DS_Store' THEN '.DS_Store'
            WHEN f.name LIKE '%.bak' THEN '*.bak'
            WHEN f.name LIKE '%.swp' THEN '*.swp'
            ELSE 'unknown'
        END as pattern
    FROM indexed_files_optimized f
    WHERE f.is_deleted = false
      AND (
          f.name LIKE '%.tmp' OR
          f.name LIKE '~%' OR
          f.name = 'Thumbs.db' OR
          f.name = '.DS_Store' OR
          f.name LIKE '%.bak' OR
          f.name LIKE '%.swp'
      );
END;
$$ LANGUAGE plpgsql;

-- Vue pour les statistiques par espace
CREATE OR REPLACE VIEW space_stats AS
SELECT
    s.id as space_id,
    s.name as space_name,
    s.host,
    s.share,
    COUNT(f.id) as total_files,
    SUM(CASE WHEN f.is_directory = TRUE THEN 1 ELSE 0 END) as total_directories,
    COALESCE(SUM(CASE WHEN f.is_directory = FALSE THEN f.size ELSE 0 END), 0) as total_size,
    COUNT(*) FILTER (WHERE f.is_duplicate = TRUE) as duplicate_files,
    COUNT(*) FILTER (WHERE f.is_garbage = TRUE) as garbage_files,
    COUNT(*) FILTER (WHERE f.is_deleted = TRUE) as deleted_files,
    s.last_crawled_at,
    s.created_at,
    s.updated_at
FROM smb_spaces s
LEFT JOIN indexed_files_optimized f ON f.space_id = s.id
GROUP BY s.id, s.name, s.host, s.share, s.last_crawled_at, s.created_at, s.updated_at
ORDER BY s.name;

-- Vue pour les fichiers récents
CREATE OR REPLACE VIEW recent_files AS
SELECT
    f.id,
    f.space_id,
    f.path,
    f.name,
    f.size,
    f.hash_xxh64,
    f.last_modified,
    f.created_at,
    f.updated_at,
    f.is_duplicate,
    f.is_garbage,
    f.is_deleted
FROM indexed_files_optimized f
WHERE f.is_deleted = false
ORDER BY f.last_modified DESC NULLS LAST
LIMIT 1000;

-- Commentaires
COMMENT ON TABLE smb_spaces IS 'Espaces SMB configurés pour l''indexation';
COMMENT ON TABLE directories IS 'Répertoires indexés pour navigation rapide';
COMMENT ON TABLE indexed_files_optimized IS 'Fichiers indexés avec hash xxHash et métadonnées';
COMMENT ON TABLE file_duplicates IS 'Relations de doublons entre fichiers';
COMMENT ON TABLE garbage_files IS 'Fichiers indésirables détectés (garbage)';
COMMENT ON COLUMN indexed_files_optimized.hash_xxh64 IS 'Hash xxHash 64 bits pour détection rapide des doublons';
COMMENT ON COLUMN indexed_files_optimized.is_garbage IS 'True si le fichier correspond à un pattern indésirable';
COMMENT ON FUNCTION detect_duplicates() IS 'Détecte les fichiers en double (même hash et taille)';
COMMENT ON FUNCTION detect_garbage_files() IS 'Détecte les fichiers indésirables (patterns connus)';
COMMENT ON VIEW space_stats IS 'Statistiques agrégées par espace SMB';
COMMENT ON VIEW recent_files IS 'Derniers fichiers modifiés (1000 derniers)';