-- ============================================================
-- Migration 003: Ajout du champ last_accessed pour T-ART-01
-- Date: 2026-04-08
-- Description: Ajout du champ last_accessed pour suivre la dernière date d'accès aux fichiers
-- ============================================================

-- Ajout du champ last_accessed à la table files
ALTER TABLE files ADD COLUMN last_accessed TIMESTAMP WITH TIME ZONE;

-- Index pour optimiser les requêtes sur last_accessed
CREATE INDEX IF NOT EXISTS idx_files_last_accessed ON files(last_accessed);

-- Supprimer les vues existantes si elles existent avec un ordre de colonnes différent
DROP VIEW IF EXISTS unused_files;
DROP VIEW IF EXISTS large_files;
DROP VIEW IF EXISTS old_files;

-- Vue pour les fichiers inutilisés (accès ancien)
CREATE OR REPLACE VIEW unused_files AS
SELECT 
    id,
    path,
    name,
    size,
    checksum,
    last_modified,
    last_accessed,
    created_at,
    updated_at,
    crawl_config_id,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_accessed)) / 86400 as days_since_access
FROM files
WHERE last_accessed IS NOT NULL
  AND last_accessed < CURRENT_TIMESTAMP - INTERVAL '1 year'
ORDER BY last_accessed ASC;

-- Vue pour les gros fichiers (taille > 1 Go par défaut)
CREATE OR REPLACE VIEW large_files AS
SELECT 
    id,
    path,
    name,
    size,
    checksum,
    last_modified,
    last_accessed,
    created_at,
    updated_at,
    crawl_config_id,
    size / 1073741824 as size_gb
FROM files
WHERE size > 1073741824  -- 1 Go
ORDER BY size DESC;

-- Vue pour les fichiers anciens (modifiés il y a plus de 2 ans)
CREATE OR REPLACE VIEW old_files AS
SELECT 
    id,
    path,
    name,
    size,
    checksum,
    last_modified,
    last_accessed,
    created_at,
    updated_at,
    crawl_config_id,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_modified)) / 86400 as days_since_modified
FROM files
WHERE last_modified < CURRENT_TIMESTAMP - INTERVAL '2 years'
ORDER BY last_modified ASC;

-- Commentaires
COMMENT ON COLUMN files.last_accessed IS 'Date de dernier accès au fichier (si disponible)';
COMMENT ON VIEW unused_files IS 'Fichiers non accédés depuis plus de 1 an';
COMMENT ON VIEW large_files IS 'Fichiers dépassant 1 Go de taille';
COMMENT ON VIEW old_files IS 'Fichiers non modifiés depuis plus de 2 ans';
