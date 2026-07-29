-- Migration 012: Recreate artefact views on indexed_files_optimized instead of files
-- The old files table is no longer populated; all data lives in indexed_files_optimized

DROP VIEW IF EXISTS large_files;
DROP VIEW IF EXISTS old_files;
DROP VIEW IF EXISTS unused_files;

CREATE OR REPLACE VIEW large_files AS
 SELECT id,
    path,
    name,
    size,
    hash_xxh64 AS checksum,
    last_modified,
    created_at,
    updated_at,
    space_id,
    size / 1073741824 AS size_gb
   FROM indexed_files_optimized
  WHERE size > 1073741824 AND NOT is_deleted
  ORDER BY size DESC;

COMMENT ON VIEW large_files IS 'Fichiers dépassant 1 Go de taille';

CREATE OR REPLACE VIEW old_files AS
 SELECT id,
    path,
    name,
    size,
    hash_xxh64 AS checksum,
    last_modified,
    created_at,
    updated_at,
    space_id,
    EXTRACT(epoch FROM CURRENT_TIMESTAMP - last_modified) / 86400::numeric AS days_since_modified
   FROM indexed_files_optimized
  WHERE last_modified < (CURRENT_TIMESTAMP - '2 years'::interval) AND NOT is_deleted
  ORDER BY last_modified;

COMMENT ON VIEW old_files IS 'Fichiers non modifies depuis plus de 2 ans';

CREATE OR REPLACE VIEW unused_files AS
 SELECT id,
    path,
    name,
    size,
    hash_xxh64 AS checksum,
    last_modified,
    created_at,
    updated_at,
    space_id,
    EXTRACT(epoch FROM CURRENT_TIMESTAMP - last_accessed) / 86400::numeric AS days_since_access
   FROM indexed_files_optimized
  WHERE last_accessed IS NOT NULL AND last_accessed < (CURRENT_TIMESTAMP - '1 year'::interval) AND NOT is_deleted
  ORDER BY last_accessed;

COMMENT ON VIEW unused_files IS 'Fichiers non accedes depuis plus de 1 an';
