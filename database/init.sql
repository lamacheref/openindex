-- Script d'initialisation PostgreSQL pour OpenIndex
-- Création de la base de données et des tables optimisées

-- Extensions PostgreSQL recommandées pour les performances
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Table principale des fichiers avec optimisations PostgreSQL
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    size BIGINT,
    checksum TEXT,
    last_modified TIMESTAMP WITH TIME ZONE,
    is_directory BOOLEAN NOT NULL DEFAULT FALSE,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of UUID REFERENCES files(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_checksum ON files(checksum);
CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);
CREATE INDEX IF NOT EXISTS idx_files_is_directory ON files(is_directory);
CREATE INDEX IF NOT EXISTS idx_files_is_duplicate ON files(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_files_duplicate_of ON files(duplicate_of);
CREATE INDEX IF NOT EXISTS idx_files_last_modified ON files(last_modified);

-- Index GIN pour la recherche textuelle (si besoin futur)
CREATE INDEX IF NOT EXISTS idx_files_name_trgm ON files USING gin(name gin_trgm_ops);

-- Table pour les statistiques et métriques
CREATE TABLE IF NOT EXISTS crawl_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_files INTEGER DEFAULT 0,
    total_directories INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    duplicate_files INTEGER DEFAULT 0,
    duplicate_size BIGINT DEFAULT 0,
    crawl_duration_seconds INTEGER DEFAULT 0,
    server_info TEXT,
    status TEXT DEFAULT 'completed'
);



-- Table des configurations de crawl
CREATE TABLE IF NOT EXISTS crawl_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    domain_zone TEXT NOT NULL,
    start_path TEXT NOT NULL,
    include_paths TEXT[] NOT NULL DEFAULT '{}',
    exclude_paths TEXT[] NOT NULL DEFAULT '{}',
    connection_username TEXT NOT NULL,
    connection_password TEXT NOT NULL,
    connection_domain TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crawl_configs_domain_zone ON crawl_configs(domain_zone);
CREATE INDEX IF NOT EXISTS idx_crawl_configs_created_at ON crawl_configs(created_at);

-- Table des exécutions de crawl
CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_id UUID NOT NULL REFERENCES crawl_configs(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued',
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE files
ADD COLUMN IF NOT EXISTS crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_files_crawl_config_id ON files(crawl_config_id);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_config_id ON crawl_runs(config_id);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_status ON crawl_runs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_triggered_at ON crawl_runs(triggered_at);

CREATE TABLE IF NOT EXISTS crawl_run_checkpoints (
    run_id UUID PRIMARY KEY REFERENCES crawl_runs(id) ON DELETE CASCADE,
    base_path TEXT NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    total_directories INTEGER NOT NULL DEFAULT 0,
    total_size BIGINT NOT NULL DEFAULT 0,
    processed_size BIGINT NOT NULL DEFAULT 0,
    large_files INTEGER NOT NULL DEFAULT 0,
    estimated_total_size BIGINT NOT NULL DEFAULT 0,
    phase TEXT NOT NULL DEFAULT 'crawl',
    last_activity_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crawl_run_queue_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
    queue_name TEXT NOT NULL,
    path TEXT NOT NULL,
    name TEXT,
    size BIGINT,
    last_modified TIMESTAMP WITH TIME ZONE,
    is_directory BOOLEAN NOT NULL DEFAULT FALSE,
    crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crawl_run_queue_items_run_id ON crawl_run_queue_items(run_id);
CREATE INDEX IF NOT EXISTS idx_crawl_run_queue_items_run_queue ON crawl_run_queue_items(run_id, queue_name);

-- Table pour les logs de crawl (optionnel)
CREATE TABLE IF NOT EXISTS crawl_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    message TEXT,
    file_path TEXT,
    details JSONB
);

-- Index pour les logs
CREATE INDEX IF NOT EXISTS idx_crawl_logs_level ON crawl_logs(level);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_crawl_date ON crawl_logs(crawl_date);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_file_path ON crawl_logs(file_path);

-- Trigger pour mettre à jour automatiquement updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_files_updated_at ON files;
CREATE TRIGGER update_files_updated_at 
    BEFORE UPDATE ON files 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Vue pour les doublons
CREATE OR REPLACE VIEW duplicate_files AS
SELECT 
    f1.id,
    f1.path,
    f1.name,
    f1.size,
    f1.checksum,
    f1.last_modified,
    f1.created_at,
    COUNT(*) OVER (PARTITION BY f1.checksum) as duplicate_count
FROM files f1
WHERE f1.checksum IS NOT NULL 
  AND f1.is_duplicate = TRUE
ORDER BY f1.checksum, f1.path;

-- Vue pour les statistiques par taille
CREATE OR REPLACE VIEW file_size_distribution AS
SELECT 
    size_category,
    COUNT(*) as file_count,
    SUM(size) as total_size
FROM (
    SELECT
        size,
        CASE
            WHEN size < 1024 THEN '< 1 KB'
            WHEN size < 1024*1024 THEN '1 KB - 1 MB'
            WHEN size < 1024*1024*10 THEN '1 MB - 10 MB'
            WHEN size < 1024*1024*100 THEN '10 MB - 100 MB'
            WHEN size < 1024*1024*1024 THEN '100 MB - 1 GB'
            ELSE '> 1 GB'
        END as size_category,
        CASE
            WHEN size < 1024 THEN 1
            WHEN size < 1024*1024 THEN 2
            WHEN size < 1024*1024*10 THEN 3
            WHEN size < 1024*1024*100 THEN 4
            WHEN size < 1024*1024*1024 THEN 5
            ELSE 6
        END as size_order
    FROM files
    WHERE is_directory = FALSE
) AS categorized_files
GROUP BY size_category, size_order
ORDER BY size_order;

-- Fonction pour calculer les doublons
CREATE OR REPLACE FUNCTION calculate_duplicates()
RETURNS INTEGER AS $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    -- Marquer les doublons
    UPDATE files 
    SET is_duplicate = TRUE,
        duplicate_of = (
            SELECT id 
            FROM files f2 
            WHERE f2.checksum = files.checksum 
              AND f2.id != files.id
              AND f2.is_directory = FALSE
            LIMIT 1
        )
    WHERE checksum IN (
        SELECT checksum 
        FROM files 
        WHERE checksum IS NOT NULL 
          AND is_directory = FALSE
        GROUP BY checksum 
        HAVING COUNT(*) > 1
    )
    AND is_directory = FALSE;
    
    -- Compter les doublons
    SELECT COUNT(*) INTO duplicate_count
    FROM files 
    WHERE is_duplicate = TRUE;
    
    RETURN duplicate_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE files IS 'Table principale contenant les métadonnées des fichiers et répertoires';
COMMENT ON TABLE crawl_statistics IS 'Statistiques des sessions de crawl';
COMMENT ON TABLE crawl_logs IS 'Logs détaillés des opérations de crawl';
COMMENT ON VIEW duplicate_files IS 'Vue affichant tous les fichiers en double';
COMMENT ON VIEW file_size_distribution IS 'Distribution des fichiers par taille';

-- ============================================================
-- T-ARCH-01 : Table des jobs d'archivage/transfert (Queue)
-- ============================================================

-- Types de job possibles (création conditionnelle)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'archive_job_type') THEN
        CREATE TYPE archive_job_type AS ENUM ('copy', 'move', 'delete');
    END IF;
END $$;

-- Statuts possibles pour un job (création conditionnelle)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'archive_job_status') THEN
        CREATE TYPE archive_job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
    END IF;
END $$;

-- Table des jobs d'archivage avec persistance
CREATE TABLE IF NOT EXISTS archive_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type archive_job_type NOT NULL DEFAULT 'copy',
    source_path TEXT NOT NULL,
    dest_path TEXT,
    status archive_job_status NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 5,  -- 1=haute, 10=basse
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Métadonnées du fichier source (pour suivi)
    source_size BIGINT,
    source_checksum TEXT,
    -- Résultat
    bytes_transferred BIGINT DEFAULT 0,
    -- Configuration source/destination
    source_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL,
    dest_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
);

-- Index pour optimiser les performances de la queue
CREATE INDEX IF NOT EXISTS idx_archive_jobs_status ON archive_jobs(status);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_status_priority ON archive_jobs(status, priority);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_created_at ON archive_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_source_config ON archive_jobs(source_config_id);
CREATE INDEX IF NOT EXISTS idx_archive_jobs_dest_config ON archive_jobs(dest_config_id);

-- Vue pour les jobs prêts à être traités (pending, ordonnés par priorité)
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

COMMENT ON TABLE archive_jobs IS 'Queue de jobs pour les opérations de transfert/archivage entre espaces SMB';
COMMENT ON TYPE archive_job_type IS 'Type d''opération: copy (copier), move (déplacer), delete (supprimer)';
COMMENT ON TYPE archive_job_status IS 'Statut du job: pending, running, completed, failed, cancelled';
COMMENT ON FUNCTION get_next_archive_job() IS 'Récupère et verrouille le prochain job pending pour traitement';

