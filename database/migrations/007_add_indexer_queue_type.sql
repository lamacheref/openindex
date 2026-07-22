-- ============================================================
-- Migration 007: Ajout du type de queue pour files différenciées
-- Date: 2026-05-18
-- Description: Séparation rapide/lente pour les jobs d'indexation
-- ============================================================

-- Ajout du champ queue_type à indexer_jobs
ALTER TABLE indexer_jobs
ADD COLUMN IF NOT EXISTS queue_type VARCHAR(10) DEFAULT 'fast';

-- Contrainte sur les valeurs possibles
ALTER TABLE indexer_jobs
DROP CONSTRAINT IF EXISTS valid_queue_type;

ALTER TABLE indexer_jobs
ADD CONSTRAINT valid_queue_type CHECK (queue_type IN ('fast', 'slow'));

-- Index pour prioriser la queue rapide
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_pending_fast
ON indexer_jobs(status, created_at)
WHERE status = 'pending' AND queue_type = 'fast';

-- Index pour la queue lente
CREATE INDEX IF NOT EXISTS idx_indexer_jobs_pending_slow
ON indexer_jobs(status, created_at)
WHERE status = 'pending' AND queue_type = 'slow';

-- Vue pour le monitoring des queues par type
CREATE OR REPLACE VIEW indexer_queue_stats AS
SELECT
    queue_type,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status = 'running') as running_count,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    COALESCE(SUM(files_indexed) FILTER (WHERE status = 'completed'), 0) as total_files_indexed,
    COALESCE(SUM(bytes_total) FILTER (WHERE status = 'completed'), 0) as total_bytes_indexed
FROM indexer_jobs
GROUP BY queue_type
ORDER BY queue_type;

COMMENT ON COLUMN indexer_jobs.queue_type IS 'Type de queue: fast (<200Mo), slow (>=200Mo)';
COMMENT ON VIEW indexer_queue_stats IS 'Statistiques par type de queue d''indexation';