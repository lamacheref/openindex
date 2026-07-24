-- Migration 011: Rendre hash_xxh64 et hash_sha256 nullable + ajout phase
-- Permet d'insérer des fichiers sans hash (Phase B) puis de les hasher (Phase C)

ALTER TABLE indexed_files_optimized ALTER COLUMN hash_xxh64 DROP NOT NULL;
ALTER TABLE indexed_files_optimized ALTER COLUMN hash_sha256 DROP NOT NULL;

-- Ajout colonne phase pour tracker la phase d'indexation (A/B/C)
ALTER TABLE indexer_jobs ADD COLUMN IF NOT EXISTS phase VARCHAR(1) DEFAULT '';
ALTER TABLE indexer_jobs ADD COLUMN IF NOT EXISTS phase_b_done BOOLEAN DEFAULT false;
