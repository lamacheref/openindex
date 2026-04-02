-- ============================================================
-- Migration 000: Initialisation du système de migrations
-- Date: 2026-04-02
-- Description: Création de la table de suivi des migrations
-- ============================================================

-- Table pour suivre les migrations appliquées
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum VARCHAR(64)
);

COMMENT ON TABLE schema_migrations IS 'Suivi des migrations de schéma appliquées';
