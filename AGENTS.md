# Règles pour l'agent OpenCode

## Database safety
- **NE JAMAIS** modifier, reset, dropper, truncater ou supprimer des données de base de données sans avoir préalablement fait un dump/backup complet et informé l'utilisateur.
- Un dump PostgreSQL doit être fait via `pg_dump` avant toute manipulation destructive (ALTER TABLE DROP COLUMN, DROP TABLE, DELETE FROM, TRUNCATE, etc.).
- Ceci s'applique à toutes les tables et toutes les raisons, sans exception.
- En cas de doute, demander à l'utilisateur avant toute action.
