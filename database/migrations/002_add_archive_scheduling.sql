-- ============================================================
-- Migration 002: Ajout du scheduling et monitoring d'archivage (T-ARCH-02)
-- Date: 2026-04-08
-- Description: Configuration cron, règles d'archivage automatique, et monitoring
-- ============================================================

-- Table pour les règles de scheduling cron
CREATE TABLE IF NOT EXISTS archive_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cron_expression VARCHAR(100) NOT NULL,  -- ex: "0 2 * * *" pour 2h du matin
    timezone VARCHAR(50) DEFAULT 'Europe/Paris',
    is_active BOOLEAN NOT NULL DEFAULT true,
    job_type archive_job_type NOT NULL DEFAULT 'copy',
    source_pattern TEXT NOT NULL,  -- Pattern de fichiers à archiver (regex ou glob)
    dest_path TEXT,  -- Destination pour copy/move (NULL pour delete)
    priority INTEGER NOT NULL DEFAULT 5,
    max_age_days INTEGER,  -- Archiver les fichiers plus anciens que X jours
    min_size_bytes BIGINT,  -- Archiver les fichiers plus gros que X bytes
    max_size_bytes BIGINT,  -- Archiver les fichiers plus petits que X bytes
    file_extensions TEXT[],  -- Extensions de fichiers à cibler
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER NOT NULL DEFAULT 0,
    created_by VARCHAR(255)
);

-- Table pour l'historique des exécutions de schedules
CREATE TABLE IF NOT EXISTS archive_schedule_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES archive_schedules(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'running',  -- running, completed, failed
    jobs_created INTEGER NOT NULL DEFAULT 0,
    jobs_completed INTEGER NOT NULL DEFAULT 0,
    jobs_failed INTEGER NOT NULL DEFAULT 0,
    total_bytes_processed BIGINT NOT NULL DEFAULT 0,
    error_message TEXT,
    log_output TEXT
);

-- Table pour les paramètres d'archivage globaux
CREATE TABLE IF NOT EXISTS archive_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Vue pour le monitoring de la queue
CREATE OR REPLACE VIEW archive_queue_monitoring AS
SELECT 
    aj.id,
    aj.job_type,
    aj.source_path,
    aj.dest_path,
    aj.status,
    aj.priority,
    aj.retry_count,
    aj.max_retries,
    aj.error_message,
    aj.created_at,
    aj.started_at,
    aj.completed_at,
    aj.source_size,
    aj.bytes_transferred,
    EXTRACT(EPOCH FROM (COALESCE(aj.completed_at, CURRENT_TIMESTAMP) - aj.started_at)) as duration_seconds,
    CASE 
        WHEN aj.source_size > 0 AND aj.bytes_transferred > 0 
        THEN ROUND((aj.bytes_transferred::numeric / aj.source_size::numeric) * 100, 2)
        ELSE 0 
    END as progress_percent,
    CASE
        WHEN aj.status = 'running' THEN 'En cours'
        WHEN aj.status = 'pending' THEN 'En attente'
        WHEN aj.status = 'completed' THEN 'Terminé'
        WHEN aj.status = 'failed' THEN 'Échoué'
        WHEN aj.status = 'cancelled' THEN 'Annulé'
        ELSE aj.status::text
    END as status_label
FROM archive_jobs aj
ORDER BY 
    CASE aj.status 
        WHEN 'running' THEN 1 
        WHEN 'pending' THEN 2 
        WHEN 'failed' THEN 3 
        ELSE 4 
    END,
    aj.priority ASC,
    aj.created_at ASC;

-- Vue pour les statistiques agrégées par jour
CREATE OR REPLACE VIEW archive_daily_stats AS
SELECT 
    DATE(created_at) as date,
    job_type,
    status,
    COUNT(*) as job_count,
    SUM(source_size) as total_source_size,
    SUM(bytes_transferred) as total_transferred,
    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, CURRENT_TIMESTAMP) - started_at))) as avg_duration_seconds
FROM archive_jobs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), job_type, status
ORDER BY date DESC, job_type, status;

-- Fonction pour calculer la prochaine exécution d'un cron
CREATE OR REPLACE FUNCTION calculate_next_run(cron_expr VARCHAR, tz VARCHAR DEFAULT 'Europe/Paris')
RETURNS TIMESTAMP WITH TIME ZONE AS $$
DECLARE
    next_run TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Simplification: calcul basique pour les patterns courants
    -- Pour des calculs cron complets, utiliser une extension comme pg_cron ou un service externe
    
    IF cron_expr = '0 2 * * *' THEN  -- Tous les jours à 2h
        next_run := DATE_TRUNC('day', CURRENT_TIMESTAMP AT TIME ZONE tz) + INTERVAL '2 hours';
        IF next_run <= CURRENT_TIMESTAMP THEN
            next_run := next_run + INTERVAL '1 day';
        END IF;
    ELSIF cron_expr = '0 0 * * 0' THEN  -- Tous les dimanches à minuit
        next_run := DATE_TRUNC('week', CURRENT_TIMESTAMP AT TIME ZONE tz) + INTERVAL '7 days';
    ELSIF cron_expr = '0 */6 * * *' THEN  -- Toutes les 6 heures
        next_run := DATE_TRUNC('hour', CURRENT_TIMESTAMP AT TIME ZONE tz);
        next_run := next_run + INTERVAL '6 hours';
        WHILE next_run <= CURRENT_TIMESTAMP LOOP
            next_run := next_run + INTERVAL '6 hours';
        END LOOP;
    ELSE
        -- Par défaut: dans 1 heure
        next_run := CURRENT_TIMESTAMP + INTERVAL '1 hour';
    END IF;
    
    RETURN next_run;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour mettre à jour le next_run_at automatiquement
CREATE OR REPLACE FUNCTION update_schedule_next_run()
RETURNS TRIGGER AS $$
BEGIN
    NEW.next_run_at := calculate_next_run(NEW.cron_expression, NEW.timezone);
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_schedule_next_run
    BEFORE INSERT OR UPDATE OF cron_expression, timezone, is_active ON archive_schedules
    FOR EACH ROW
    WHEN (NEW.is_active = true)
    EXECUTE FUNCTION update_schedule_next_run();

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_archive_schedules_active ON archive_schedules(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_archive_schedules_next_run ON archive_schedules(next_run_at) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_archive_schedule_runs_schedule ON archive_schedule_runs(schedule_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_created_at ON archive_jobs(created_at DESC);

-- Insertion des paramètres par défaut
INSERT INTO archive_settings (key, value, description) VALUES
    ('archive.default_priority', '5', 'Priorité par défaut pour les nouveaux jobs'),
    ('archive.max_retries', '3', 'Nombre maximum de tentatives pour un job'),
    ('archive.worker.poll_interval', '5', 'Intervalle de polling du worker (secondes)'),
    ('archive.worker.max_concurrent', '3', 'Nombre maximum de transferts parallèles'),
    ('archive.retention_days', '30', 'Durée de conservation des jobs terminés en jours'),
    ('archive.cleanup_interval_hours', '24', 'Intervalle de nettoyage des vieux jobs (heures)')
ON CONFLICT (key) DO NOTHING;

-- Commentaires
COMMENT ON TABLE archive_schedules IS 'Configuration des tâches d\'archivage planifiées (cron)';
COMMENT ON TABLE archive_schedule_runs IS 'Historique des exécutions des schedules d\'archivage';
COMMENT ON TABLE archive_settings IS 'Paramètres globaux de configuration de l\'archivage';
COMMENT ON VIEW archive_queue_monitoring IS 'Vue de monitoring temps réel de la queue d\'archivage';
COMMENT ON VIEW archive_daily_stats IS 'Statistiques quotidiennes d\'archivage';
