# Issues OpenIndex - Problèmes Connus

## 🔴 Issues Critiques

### ✅ Issue #1: Échec des tests d'archive dû à des problèmes de connexion PostgreSQL (RÉSOLUE)
**Fichiers affectés**: `tests/test_archive_*.py`
**Statut**: CORRIGÉ
**Solution appliquée**:
1. Création de la base de données `openindex_test`
2. Création de l'utilisateur `test_user` avec mot de passe `test_pass`
3. Grant des permissions nécessaires sur la base de test
4. Les 53 tests API passent maintenant avec succès
**Résultat**: Tous les tests d'archive passent (53/53) ✅

### ✅ Issue #1: Échec des tests d'archive dû à des problèmes de connexion PostgreSQL (RÉSOLUE)
**Fichiers affectés**: `tests/test_archive_*.py`
**Statut**: CORRIGÉ
**Solution appliquée**:
1. Création de la base de données `openindex_test`
2. Création de l'utilisateur `test_user` avec mot de passe `test_pass`
3. Grant des permissions nécessaires sur la base de test
4. Les 53 tests API passent maintenant avec succès
**Résultat**: Tous les tests d'archive passent (53/53) ✅

### ✅ Issue #80: Archivage 'Copier vers archives' échoue (Fermée)
**Fichiers affectés**: `frontend/index.html`, `src/api/main.py`
**Statut**: CORRIGÉ CÔTÉ APPLICATION - issue GitHub fermée, suivi de configuration déplacé vers l'issue #86
**Problème initial**: Le flux "Copier vers archives" échouait depuis l'explorateur avec un message d'erreur générique.

**Corrections appliquées**:

1. **Script Alpine cassé** (RÉSOLU)
   - Problème: une portion de `openIndexApp()` était tronquée, ce qui empêchait l'initialisation de l'interface et provoquait une cascade d'erreurs console
   - Solution: restauration des méthodes JS manquantes et remise en cohérence du composant Alpine
   - Fichier modifié: `frontend/index.html`

2. **Flux d'archivage UI trop fragile** (RÉSOLU)
   - Problème: l'interface utilisait un chemin d'archivage indirect moins robuste pour l'action utilisateur
   - Solution: bascule du bouton d'archivage vers l'endpoint direct `/api/archive/file`, déjà couvert par les tests backend
   - Fichier modifié: `frontend/index.html`

3. **Erreur backend trop générique** (RÉSOLU)
   - Problème: l'API retournait "Erreur lors de l'archivage du fichier" sans exposer la cause réelle
   - Solution: remontée explicite des erreurs SMB d'authentification pour affichage dans l'UI
   - Fichier modifié: `src/api/main.py`

**Résultats obtenus**:
- ✅ Le frontend se charge de nouveau correctement
- ✅ Le flux d'archivage depuis l'explorateur utilise désormais un endpoint direct plus fiable
- ✅ Les erreurs SMB réelles remontent à l'utilisateur au lieu d'un message 500 générique
- ✅ L'issue GitHub #80 a été fermée avec note de synthèse

**Diagnostic final**:
- Le bug applicatif de #80 était réel et a été corrigé
- L'échec restant en environnement local n'était plus un bug de code
- La cause résiduelle était une mauvaise configuration SMB sur `\\172.16.252.34\Public\SMIDEN`

**Suivi restant**:
- Voir **Issue #86**: utiliser `adminsmiden` pour `Public\SMIDEN` au lieu de `admin` (compte Typhon)

**Commit de référence**: `9f2f366` (diagnostic local avant commit final)

### Issue #2: Problèmes de queue system dans les tests
**Fichiers affectés**: `tests/test_queue_system.py`
**Nombre de tests échoués**: 4 échecs
**Problèmes spécifiques**:
- `test_queue_initialization`: La queue n'est pas initialisée
- `test_queue_usage_in_crawl`: Argument inattendu 'page_size'
- `test_error_handling`: Argument inattendu 'page_size'
- `test_database_integration`: Table 'files' non créée

**Solution proposée**:
1. Initialiser correctement la queue avant les tests
2. Corriger la signature de la méthode crawl() pour accepter page_size
3. Vérifier que la base de données de test est correctement initialisée

### Issue #3: Problèmes de SMBCrawler dans les tests
**Fichiers affectés**: `tests/test_smb_crawler.py`
**Nombre de tests échoués**: 6 échecs
**Problèmes spécifiques**:
- Méthodes manquantes: `calculate_sha256`, `disconnect`
- Module manquant: `Connection`
- Chemin de base de données incorrect: attend `:memory:` mais trouve `openindex.db`
- Table manquante: `files`

**Solution proposée**:
1. Implémenter les méthodes manquantes dans SMBCrawler
2. Corriger les imports
3. Configurer correctement la base de données de test
4. Créer les tables nécessaires avant les tests

### Issue #4: Problèmes de crawler runtime
**Fichiers affectés**: `tests/test_api_fastapi.py`
**Nombre de tests échoués**: 2 échecs
**Problèmes spécifiques**:
- `test_get_crawler_runtime_endpoint`: Logs inattendus au lieu des lignes de test
- `test_get_crawler_runtime_reconciles_terminal_run_with_recent_db_activity`: Statut "completed" au lieu de "running"

**Solution proposée**:
1. Isoler les tests du crawler runtime pour éviter les interférences
2. Utiliser des mocks plus précis pour simuler le comportement attendu
3. Vérifier la logique de détermination du statut du run

### Issue #5: Problème de timeout dans test_worker_loop_marks_timed_out_run_as_failed
**Fichiers affectés**: `tests/test_smb_crawler_postgresql.py`
**Problème**: Le test attend que le run soit marqué comme "failed" mais il reste "completed"

**Solution proposée**:
1. Vérifier la logique de timeout dans le worker
2. Ajuster les délais de test si nécessaire
3. S'assurer que le run est correctement marqué comme timed out

## 🟡 Issues Mineures (Corrigées)

### ✅ Issue #6: Problème de version dans test_get_system_status_endpoint
**Statut**: CORRIGÉ
**Solution**: Modifié `src/versioning.py` et `src/api/main.py` pour supporter les variables d'environnement
**Commit**: f3a568f

### ✅ Issue #7: Tests de doublons échouant avec code 500 au lieu de 404
**Statut**: CORRIGÉ
**Solution**: 
1. Ajouté les variables d'environnement PostgreSQL dans les fixtures de test
2. Modifié les blocs try/except pour ne pas attraper les HTTPException
**Commit**: (à commiter)

### ✅ Issue #8: Incohérence de version entre package.json et VERSION
**Statut**: CORRIGÉ
**Solution**: Mis à jour package.json pour correspondre à la version dans VERSION (0.6.6)
**Commit**: (à commiter)

## 📋 Tâches de Suivi

### Pour les développeurs:
- [ ] Configurer un environnement de test PostgreSQL avec Docker
- [ ] Créer des fixtures pour mocker l'adaptateur PostgreSQL
- [ ] Implémenter les méthodes manquantes dans SMBCrawler
- [ ] Corriger la logique de queue system
- [ ] Vérifier et corriger la logique de timeout des workers

### Pour les tests CI/CD:
- [ ] Ajouter la configuration PostgreSQL aux workflows GitHub Actions
- [ ] Configurer les variables d'environnement nécessaires
- [ ] Isoler les tests qui nécessitent une base de données

## 🔧 Configuration Recommandée

### Variables d'environnement pour les tests:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=openindex_test
export POSTGRES_USER=test_user
export POSTGRES_PASSWORD=test_password
```

### Commande pour exécuter les tests:
```bash
# Tests unitaires (sans base de données)
pytest tests/test_search_api.py tests/test_artefacts_api.py tests/test_artefact_filters_api.py tests/test_duplicate_details_api.py -v

# Tests d'intégration (nécessitent une base de données)
pytest tests/test_archive_*.py tests/test_smb_crawler_postgresql.py -v
```

## 📊 Statistiques Actuelles

- **Tests passant**: 163
- **Tests échouant**: 17
- **Erreurs**: 31 (principalement liées à la base de données)
- **Taux de réussite**: 80%

*Dernière mise à jour: 2024-04-08*
