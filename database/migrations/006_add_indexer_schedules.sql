-- ============================================================
-- Migration 006: Table indexer_schedules pour le scheduling
-- Date: 2026-05-18
-- Description: Configuration des tâches d'indexation planifiées
-- ============================================================

-- Table des schedules d'indexation
CREATE TABLE IF NOT EXISTS indexer_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cron_expression VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Europe/Paris',
    is_active BOOLEAN NOT NULL DEFAULT true,
    config_id UUID REFERENCES crawl_configs(id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER NOT NULL DEFAULT 0,
    created_by VARCHAR(255)
);

-- Index pour les schedules actifs
CREATE INDEX IF NOT EXISTS idx_indexer_schedules_active ON indexer_schedules(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_indexer_schedules_next_run ON indexer_schedules(next_run_at) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_indexer_schedules_config ON indexer_schedules(config_id);

-- Fonction helper pour calculer le prochain run (basée sur l'existante)
CREATE OR REPLACE FUNCTION calculate_indexer_next_run(cron_expr VARCHAR, tz VARCHAR DEFAULT 'Europe/Paris')
RETURNS TIMESTAMP WITH TIME ZONE AS $$
DECLARE
    next_run TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Expressions cron courantes pour l'indexation
    IF cron_expr = '0 22 * * *' THEN
        -- Tous les jours à 22h
        next_run := DATE_TRUNC('day', CURRENT_TIMESTAMP AT TIME ZONE tz) + INTERVAL '22 hours';
        IF next_run <= CURRENT_TIMESTAMP THEN
            next_run := next_run + INTERVAL '1 day';
        END IF;
    ELSIF cron_expr = '0 6 * * *' THEN
        -- Tous les jours à 6h
        next_run := DATE_TRUNC('day', CURRENT_TIMESTAMP AT TIME ZONE tz) + INTERVAL '6 hours';
        IF next_run <= CURRENT_TIMESTAMP THEN
            next_run := next_run + INTERVAL '1 day';
        END IF;
    ELSIF cron_expr = '0 */6 * * *' THEN
        -- Toutes les 6 heures
        next_run := DATE_TRUNC('hour', CURRENT_TIMESTAMP AT TIME ZONE tz);
        next_run := next_run + INTERVAL '6 hours';
        WHILE next_run <= CURRENT_TIMESTAMP LOOP
            next_run := next_run + INTERVAL '6 hours';
        END LOOP;
    ELSIF cron_expr = '0 0 * * 0' THEN
        -- Tous les dimanches à minuit
        next_run := DATE_TRUNC('week', CURRENT_TIMESTAMP AT TIME ZONE tz);
        WHILE next_run <= CURRENT_TIMESTAMP LOOP
            next_run := next_run + INTERVAL '7 days';
        END LOOP;
    ELSE
        -- Fallback: dans 1 heure
        next_run := CURRENT_TIMESTAMP + INTERVAL '1 hour';
    END IF;

    RETURN next_run;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour mettre à jour next_run_at automatiquement
CREATE OR REPLACE FUNCTION update_indexer_schedule_next_run()
RETURNS TRIGGER AS $$
BEGIN
    NEW.next_run_at := calculate_indexer_next_run(NEW.cron_expression, NEW.timezone);
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_indexer_schedule_next_run ON indexer_schedules;
CREATE TRIGGER trigger_update_indexer_schedule_next_run
    BEFORE INSERT OR UPDATE OF cron_expression, timezone, is_active ON indexer_schedules
    FOR EACH ROW
    WHEN (NEW.is_active = true)
    EXECUTE FUNCTION update_indexer_schedule_next_run();

-- Commentaires
COMMENT ON TABLE indexer_schedules IS 'Configuration des tâches d''indexation planifiées (cron)';
COMMENT ON COLUMN indexer_schedules.cron_expression IS 'Expression cron pour la planification';
COMMENT ON COLUMN indexer_schedules.config_id IS 'Configuration SMB à indexer (NULL = toutes les configs actives)';
COMMENT ON COLUMN indexer_schedules.next_run_at IS 'Prochaine exécution calculée automatiquement';

-- Insertion d'un schedule par défaut : indexation nocturne à 22h
INSERT INTO indexer_schedules (name, description, cron_expression, timezone, priority)
VALUES (
    'Indexation nocturne',
    'Indexation automatique de tous les espaces configurés, exécutée chaque nuit à 22h',
    '0 22 * * *',
    'Europe/Paris',
    5
) ON CONFLICT DO NOTHING;