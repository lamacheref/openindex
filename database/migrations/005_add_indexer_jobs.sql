-- ============================================================
-- Migration 004: Table indexer_jobs pour le worker d'indexation
-- Date: 2026-05-05
-- Description: Crée la table de queue pour les jobs d'indexation
-- ============================================================

-- Table des jobs d'indexation
CREATE TABLE IF NOT EXISTS indexer_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    config_id UUID NOT NULL REFERENCES crawl_configs(id) ON DELETE CASCADE,
    config_name TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    files_found INTEGER DEFAULT 0,
    files_indexed INTEGER DEFAULT 0,
    bytes_total BIGINT DEFAULT 0,
    error_message TEXT,
    
    -- Contraintes
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Index pour accès rapide
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_status ON indexer_jobs(status);
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_created ON indexer_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_config ON indexer_jobs(config_id);

-- Index pour chercher les jobs pending ordonnés par date
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_pending ON indexer_jobs(status, created_at) 
    WHERE status = 'pending';

-- Vue pour le monitoring des jobs actifs
CREATE OR REPLACE VIEW indexer_jobs_monitoring AS
SELECT 
    id,
    path,
    config_name,
    status,
    created_at,
    started_at,
    completed_at,
    files_found,
    files_indexed,
    bytes_total,
    error_message,
    CASE 
        WHEN started_at IS NOT NULL THEN 
            EXTRACT(EPOCH FROM (COALESCE(completed_at, CURRENT_TIMESTAMP) - started_at)) / 60
        ELSE NULL
    END as duration_minutes,
    CASE 
        WHEN files_found > 0 THEN 
            ROUND(100.0 * files_indexed / files_found, 2)
        ELSE 0
    END as progress_percent
FROM indexer_jobs
ORDER BY created_at DESC;

-- Vue des statistiques d'indexation
CREATE OR REPLACE VIEW indexer_stats AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status = 'running') as running_count,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    COALESCE(SUM(files_indexed) FILTER (WHERE status = 'completed'), 0) as total_files_indexed,
    COALESCE(SUM(bytes_total) FILTER (WHERE status = 'completed'), 0) as total_bytes_indexed,
    MAX(created_at) as last_job_created,
    MAX(completed_at) FILTER (WHERE status = 'completed') as last_completion
FROM indexer_jobs;

-- Commentaires
COMMENT ON TABLE indexer_jobs IS 'Queue des jobs d\'indexation de fichiers';
COMMENT ON COLUMN indexer_jobs.status IS 'Statut: pending, running, completed, failed, cancelled';
COMMENT ON VIEW indexer_jobs_monitoring IS 'Vue de monitoring des jobs d\'indexation';
COMMENT ON VIEW indexer_stats IS 'Statistiques globales de l\'indexation';
