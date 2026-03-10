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

CREATE INDEX IF NOT EXISTS idx_crawl_runs_config_id ON crawl_runs(config_id);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_status ON crawl_runs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_triggered_at ON crawl_runs(triggered_at);

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
    CASE 
        WHEN size < 1024 THEN '< 1 KB'
        WHEN size < 1024*1024 THEN '1 KB - 1 MB'
        WHEN size < 1024*1024*10 THEN '1 MB - 10 MB'
        WHEN size < 1024*1024*100 THEN '10 MB - 100 MB'
        WHEN size < 1024*1024*1024 THEN '100 MB - 1 GB'
        ELSE '> 1 GB'
    END as size_category,
    COUNT(*) as file_count,
    SUM(size) as total_size
FROM files 
WHERE is_directory = FALSE
GROUP BY size_category
ORDER BY 
    CASE 
        WHEN size < 1024 THEN 1
        WHEN size < 1024*1024 THEN 2
        WHEN size < 1024*1024*10 THEN 3
        WHEN size < 1024*1024*100 THEN 4
        WHEN size < 1024*1024*1024 THEN 5
        ELSE 6
    END;

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
