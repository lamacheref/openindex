-- Migration pour ajouter la table indexer_retries
-- Cette table gère les tentatives de réessai pour les fichiers verrouillés

BEGIN;

CREATE TABLE IF NOT EXISTS indexer_retries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL,
    job_id UUID NOT NULL,
    config_id VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    next_retry_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_file_id FOREIGN KEY (file_id) REFERENCES indexed_files_optimized(id) ON DELETE CASCADE,
    CONSTRAINT fk_job_id FOREIGN KEY (job_id) REFERENCES indexer_jobs(id) ON DELETE CASCADE
);

-- Index pour les requêtes de réessai
CREATE INDEX IF NOT EXISTS idx_indexer_retries_next_retry ON indexer_retries(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_indexer_retries_file_id ON indexer_retries(file_id);
CREATE INDEX IF NOT EXISTS idx_indexer_retries_job_id ON indexer_retries(job_id);

-- Fonction pour vérifier si un fichier doit être réessayé
CREATE OR REPLACE FUNCTION should_retry_file(file_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    retry_count INTEGER;
    max_attempts INTEGER;
BEGIN
    SELECT attempt_count, max_attempts INTO retry_count, max_attempts
    FROM indexer_retries
    WHERE file_id = should_retry_file.file_id;

    IF retry_count IS NULL THEN
        RETURN TRUE; -- Pas encore de tentative, peut être réessayé
    ELSIF retry_count < max_attempts THEN
        RETURN TRUE; -- Peut être réessayé
    ELSE
        RETURN FALSE; -- Nombre maximal de tentatives atteint
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour incrémenter le compteur de tentatives
CREATE OR REPLACE FUNCTION increment_retry_attempt(file_id UUID, error_message TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE indexer_retries
    SET
        attempt_count = attempt_count + 1,
        next_retry_at = CURRENT_TIMESTAMP + INTERVAL '5 minutes' * (attempt_count + 1),
        last_error = error_message,
        updated_at = CURRENT_TIMESTAMP
    WHERE file_id = increment_retry_attempt.file_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour ajouter un fichier à la queue de réessai
CREATE OR REPLACE FUNCTION add_file_to_retry(
    p_file_id UUID,
    p_job_id UUID,
    p_config_id VARCHAR(255),
    p_file_path TEXT,
    p_error_message TEXT
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO indexer_retries (
        file_id,
        job_id,
        config_id,
        file_path,
        attempt_count,
        next_retry_at,
        last_error
    ) VALUES (
        p_file_id,
        p_job_id,
        p_config_id,
        p_file_path,
        0,
        CURRENT_TIMESTAMP + INTERVAL '5 minutes',
        p_error_message
    )
    ON CONFLICT (file_id)
    DO UPDATE SET
        attempt_count = indexer_retries.attempt_count + 1,
        next_retry_at = CURRENT_TIMESTAMP + INTERVAL '5 minutes' * (indexer_retries.attempt_count + 1),
        last_error = p_error_message,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

COMMIT;