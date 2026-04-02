-- ============================================================
-- Migration 001: Ajout de la table archive_jobs (T-ARCH-01)
-- Date: 2026-04-02
-- Description: Queue de jobs pour les opérations de transfert/archivage
-- ============================================================

-- Types de job possibles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'archive_job_type') THEN
        CREATE TYPE archive_job_type AS ENUM ('copy', 'move', 'delete');
    END IF;
END
$$;

-- Statuts possibles pour un job
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'archive_job_status') THEN
        CREATE TYPE archive_job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
    END IF;
END
$$;

-- Table des jobs d'archivage avec persistance
CREATE TABLE IF NOT EXISTS archive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type archive_job_type NOT NULL DEFAULT 'copy',
    source_path TEXT NOT NULL,
    dest_path TEXT,
    status archive_job_status NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 5,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source_size BIGINT,
    source_checksum TEXT,
    bytes_transferred BIGINT DEFAULT 0,
    source_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL,
    dest_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
);

-- Index pour optimiser les performances de la queue
CREATE INDEX IF NOT EXISTS idx_archive_jobs_status ON archive_jobs(status);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_status_priority ON archive_jobs(status, priority);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_created_at ON archive_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_source_config ON archive_jobs(source_config_id);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_dest_config ON archive_jobs(dest_config_id);

-- Vue pour les jobs prêts à être traités
CREATE OR REPLACE VIEW archive_jobs_pending AS
SELECT *
FROM archive_jobs
WHERE status = 'pending'
   OR (status = 'failed' AND retry_count < max_retries)
ORDER BY priority ASC, created_at ASC;

-- Vue pour les statistiques de la queue
CREATE OR REPLACE VIEW archive_jobs_stats AS
SELECT 
    status,
    COUNT(*) as count,
    SUM(CASE WHEN source_size IS NOT NULL THEN source_size ELSE 0 END) as total_size
FROM archive_jobs
GROUP BY status;

-- Fonction pour récupérer le prochain job à traiter
CREATE OR REPLACE FUNCTION get_next_archive_job()
RETURNS TABLE (
    job_id UUID,
    job_type archive_job_type,
    source_path TEXT,
    dest_path TEXT,
    priority INTEGER,
    retry_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    UPDATE archive_jobs
    SET status = 'running', started_at = CURRENT_TIMESTAMP
    WHERE id = (
        SELECT id 
        FROM archive_jobs 
        WHERE status = 'pending' 
           OR (status = 'failed' AND retry_count < max_retries)
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING 
        archive_jobs.id,
        archive_jobs.job_type,
        archive_jobs.source_path,
        archive_jobs.dest_path,
        archive_jobs.priority,
        archive_jobs.retry_count;
END;
$$ LANGUAGE plpgsql;

-- Commentaires
COMMENT ON TABLE archive_jobs IS 'Queue de jobs pour les opérations de transfert/archivage entre espaces SMB';
COMMENT ON TYPE archive_job_type IS 'Type d''opération: copy (copier), move (déplacer), delete (supprimer)';
COMMENT ON TYPE archive_job_status IS 'Statut du job: pending, running, completed, failed, cancelled';
COMMENT ON FUNCTION get_next_archive_job() IS 'Récupère et verrouille le prochain job pending pour traitement';
