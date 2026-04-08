-- ============================================================
-- Migration 004: Ajout de la table artefact_filters pour T-ART-03
-- Date: 2026-04-08
-- Description: Table pour sauvegarder les préférences utilisateur pour les filtres d'artefacts
-- ============================================================

-- Table pour les préférences utilisateur des filtres d'artefacts
CREATE TABLE IF NOT EXISTS artefact_filters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filter_name VARCHAR(255) NOT NULL,
    filter_value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les requêtes
CREATE INDEX IF NOT EXISTS idx_artefact_filters_name ON artefact_filters(filter_name);

-- Vue pour les préférences courantes
CREATE OR REPLACE VIEW current_artefact_filters AS
SELECT 
    COALESCE(MAX(CASE WHEN filter_name = 'large_file_threshold_mb' THEN filter_value::integer ELSE NULL END), 1024) as large_file_threshold_mb,
    COALESCE(MAX(CASE WHEN filter_name = 'old_file_threshold_days' THEN filter_value::integer ELSE NULL END), 730) as old_file_threshold_days,
    COALESCE(MAX(CASE WHEN filter_name = 'unused_file_threshold_days' THEN filter_value::integer ELSE NULL END), 365) as unused_file_threshold_days
FROM artefact_filters;

-- Fonction pour obtenir l'ID de l'utilisateur courant
-- Note: Dans une implémentation complète, cela serait lié à l'authentification
CREATE OR REPLACE FUNCTION CURRENT_USER_ID()
RETURNS UUID AS $$
BEGIN
    -- Pour l'instant, retourner un UUID par défaut pour le développement
    -- Dans une implémentation complète, cela serait lié à la session utilisateur
    RETURN '00000000-0000-0000-0000-000000000000'::uuid;
END;
$$ LANGUAGE plpgsql;

-- Commentaires
COMMENT ON TABLE artefact_filters IS 'Préférences utilisateur pour les filtres d''artefacts';
COMMENT ON VIEW current_artefact_filters IS 'Vue des préférences courantes pour les filtres d''artefacts';
