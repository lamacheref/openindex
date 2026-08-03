-- 013: Associer un espace d'archivage à une source (crawl config)
-- Une source (is_archive = false) peut référencer la config d'archivage vers
-- laquelle ses fichiers doivent être déplacés lors d'un archivage.

ALTER TABLE crawl_configs
    ADD COLUMN IF NOT EXISTS linked_archive_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL;

COMMENT ON COLUMN crawl_configs.linked_archive_config_id IS
    'Config d''archivage associée à cette source (cible d''archivage)';
