# TODO - Problèmes à résoudre après l'audit

## Erreurs PostgreSQL

### 1. Fonction `calculate_duplicates()` manquante
**Problème**: La fonction `calculate_duplicates()` n'existe pas dans la base de données
**Impact**: Le crawler ne peut pas calculer les doublons et échoue
**Fichiers concernés**:
- `docs/audit/openindex-crawler.md` (erreurs répétées)
- `docs/audit/openindex-postgres.md` (tentatives d'appel de la fonction)

**Solution implémentée**:
- ✅ Création de la fonction `calculate_duplicates()` dans `database/init.sql`
- ✅ La fonction met à jour les fichiers en doublon et retourne le nombre total de doublons
- ✅ La fonction est exécutée lors de l'initialisation de la base de données

### 2. Vue `file_size_distribution` mal formée
**Problème**: Erreur SQL dans la création de la vue `file_size_distribution`
**Erreur**: `column "files.size" must appear in the GROUP BY clause or be used in an aggregate function`
**Fichier concerné**: `docs/audit/openindex-postgres.md`

**Solution implémentée**:
- ✅ Correction de la requête SQL dans `database/init.sql`
- ✅ Le GROUP BY utilise maintenant l'expression CASE complète au lieu de `size_category`
- ✅ La vue est maintenant valide et fonctionnelle

## Erreurs API

### 3. Module `src.api` non trouvé
**Problème**: L'API ne peut pas importer le module `src.api`
**Impact**: Le service API ne démarre pas
**Fichier concerné**: `docs/audit/openindex-api.md`

**Solution à implémenter**:
- Vérifier la structure du projet dans le conteneur
- Corriger le PYTHONPATH dans le Dockerfile API
- S'assurer que le module est correctement installé

## Problèmes de configuration

### 4. Variables d'environnement à sécuriser
**Problème**: Les mots de passe sont en dur dans le `.env`
**Fichier concerné**: `.env`

**Solution à implémenter**:
- Remplacer les mots de passe par des variables d'environnement sécurisées
- Utiliser un gestionnaire de secrets pour les mots de passe

## Actions prioritaires

1. **Haute priorité**: Corriger la fonction `calculate_duplicates()` et la vue `file_size_distribution`
2. **Haute priorité**: Résoudre le problème d'import du module `src.api`
3. **Moyenne priorité**: Sécuriser les variables d'environnement
4. **Basse priorité**: Améliorer la robustesse des logs et de la gestion des erreurs

## Tests à effectuer après corrections

1. Vérifier que le crawler démarre sans erreurs
2. Vérifier que l'API démarre et est accessible
3. Vérifier que les calculs de doublons fonctionnent correctement
4. Vérifier que la vue `file_size_distribution` est créée sans erreurs