-- ============================================================
-- Migration 008: Table indexed_files pour la détection des changements
-- Date: 2026-05-18
-- Description: Stocke les hashs et timestamps pour le mode incrémentiel
-- ============================================================

-- Table des fichiers indexés (pour détection de changements)
CREATE TABLE IF NOT EXISTS indexed_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL UNIQUE,
    config_id UUID REFERENCES crawl_configs(id) ON DELETE CASCADE,
    last_hash VARCHAR(16) NULL,  -- xxHash 64 bits en hexa
    last_size BIGINT NULL,
    last_modified TIMESTAMP WITH TIME ZONE NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- Index pour accès rapide
CREATE INDEX IF NOT EXISTS idx_indexed_files_path ON indexed_files(path);
CREATE INDEX IF NOT EXISTS idx_indexed_files_config ON indexed_files(config_id);
CREATE INDEX IF NOT EXISTS idx_indexed_files_hash ON indexed_files(last_hash);
CREATE INDEX IF NOT EXISTS idx_indexed_files_modified ON indexed_files(last_modified);

-- Fonction pour vérifier si un fichier a changé
CREATE OR REPLACE FUNCTION check_file_changed(
    p_path TEXT,
    p_hash VARCHAR(16),
    p_size BIGINT,
    p_modified TIMESTAMP WITH TIME ZONE
) RETURNS BOOLEAN AS $$
DECLARE
    existing_hash VARCHAR(16);
    existing_size BIGINT;
    existing_modified TIMESTAMP WITH TIME ZONE;
BEGIN
    SELECT last_hash, last_size, last_modified
    INTO existing_hash, existing_size, existing_modified
    FROM indexed_files
    WHERE path = p_path AND is_deleted = false;

    -- Si le fichier n'existe pas encore, il a "changé" (nouveau)
    IF existing_hash IS NULL THEN
        RETURN true;
    END IF;

    -- Comparer hash, taille et timestamp
    IF existing_hash IS DISTINCT FROM p_hash OR
       existing_size IS DISTINCT FROM p_size OR
       existing_modified IS DISTINCT FROM p_modified THEN
        RETURN true;
    END IF;

    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour marquer un fichier comme supprimé
CREATE OR REPLACE FUNCTION mark_file_deleted(p_path TEXT) RETURNS VOID AS $$
BEGIN
    UPDATE indexed_files
    SET is_deleted = true,
        deleted_at = CURRENT_TIMESTAMP
    WHERE path = p_path AND is_deleted = false;
END;
$$ LANGUAGE plpgsql;

-- Vue pour les fichiers modifiés/supprimés
CREATE OR REPLACE VIEW file_changes AS
SELECT
    id,
    path,
    config_id,
    last_hash,
    last_size,
    last_modified,
    first_seen_at,
    last_seen_at,
    is_deleted,
    deleted_at,
    CASE
        WHEN is_deleted THEN 'deleted'
        ELSE 'modified'
    END as change_type
FROM indexed_files
WHERE is_deleted = true OR deleted_at IS NOT NULL
ORDER BY last_seen_at DESC;

COMMENT ON TABLE indexed_files IS 'Fichiers indexés avec hashs pour détection de changements';
COMMENT ON COLUMN indexed_files.last_hash IS 'Dernier hash xxHash calculé';
COMMENT ON COLUMN indexed_files.is_deleted IS 'True si le fichier a été supprimé du disque';
COMMENT ON FUNCTION check_file_changed(text, varchar, bigint, timestamp with time zone) IS 'Vérifie si un fichier a changé depuis la dernière indexation';
COMMENT ON FUNCTION mark_file_deleted(text) IS 'Marque un fichier comme supprimé';
COMMENT ON VIEW file_changes IS 'Vue des fichiers modifiés ou supprimés';