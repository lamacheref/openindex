# PROPOSITION D'ÉVOLUTION OPENINDEX V2.0

## Contexte et Objectifs

### Deadline
- **Date limite** : 19 mars 2026
- **Durée** : 3 semaines pour migration complète

### Objectifs Principaux
1. **Design moderne** : Interface belle et pratique (UX/UI professionnelle)
2. **Performance fluide** : Actions instantanées sans rechargements
3. **Base de données robuste** : Support multi-utilisateurs et grande volumétrie
4. **Dockerisation** : Installation simple et déploiement automatisé

## Architecture Technique Proposée

### Frontend : React + TypeScript + Material-UI
```
├── Interface moderne et responsive
├── Navigation instantanée (SPA)
├── Composants personnalisés illimités
├── État géré avec Zustand
└── Animations et transitions fluides
```

### Backend : FastAPI + Python
```
├── API REST performante
├── WebSocket pour temps réel
├── Authentification JWT
├── Gestion multi-utilisateurs
└── Logique métier existante préservée
```

### Base de Données : PostgreSQL
```
├── Support multi-utilisateurs natif
├── Performance supérieure à SQLite
├── Transactions ACID robustes
├── Indexation optimisée
└── Migration automatique des données
```

### Déploiement : Docker + Docker Compose
```
├── Conteneurisation complète
├── Configuration en un clic
├── Volumes persistants
├── Réseau isolé et sécurisé
└── Mise à jour simplifiée
```

## Plan de Migration - 3 Semaines (Réorganisé)

### Semaine 1 : Déploiement Crawler & Collecte Données (15-19 mars)
**Objectifs :**
- ✅ Déployer le crawler existant en mode "pré-production"
- ✅ Collecter des données réelles depuis le SMB (>2 To)
- ✅ Préparer la base PostgreSQL pour recevoir les données
- ✅ Créer l'API FastAPI de base pour lire les données

**Tâches détaillées :**
- **Lundi 15 mars** : Déployer crawler existant sur environnement de test
- **Mardi 16 mars** : Configurer PostgreSQL + scripts de migration SQLite→PostgreSQL
- **Mercredi 17 mars** : Lancer crawl complet et collecter données réelles
- **Jeudi 18 mars** : Créer API FastAPI minimale pour lire les données
- **Vendredi 19 mars** : Valider données réelles accessibles via API

**Livrables :**
- Crawler déployé et fonctionnel
- Base PostgreSQL avec données réelles
- API FastAPI minimale opérationnelle
- Données testables pour développement frontend

### Semaine 2 : Frontend React avec Données Réelles (22-26 mars)
**Objectifs :**
- ✅ Développer interface React avec vraies données
- ✅ Composants UI modernes et responsive
- ✅ Intégration complète avec l'API existante
- ✅ Tests avec données réelles
- ✅ **Intégrer IA locale pour analyse de contenu**

**Tâches détaillées :**
- **Lundi 22 mars** : Structure React + Material-UI + connexion API
- **Mardi 23 mars** : Composants arborescence avec vraies données
- **Mercredi 24 mars** : Dashboard et visualisations avec métriques réelles
- **Jeudi 25 mars** : Gestion des doublons et actions avec vrais fichiers
- **Vendredi 26 mars** : **Intégration IA locale Ollama + résumés automatiques**

**Livrables :**
- Interface React complète avec vraies données
- Design moderne et responsive validé
- Tests utilisateur avec données réelles
- Performance optimisée
- **Service IA local opérationnel pour résumés de documents**

### Semaine 3 : Finalisation & Production (29 mars - 2 avril)
**Objectifs :**
- ✅ Dockerisation complète de l'application
- ✅ Tests d'intégration finaux
- ✅ Documentation déploiement
- ✅ Livraison production-ready

**Tâches détaillées :**
- **Lundi 29 mars** : Dockerisation + Docker Compose
- **Mardi 30 mars** : Tests E2E + validation finale
- **Mercredi 31 mars** : Documentation complète
- **Jeudi 1er avril** : Tests recette + corrections
- **Vendredi 2 avril** : Livraison finale

**Livrables :**
- Application Dockerisée complète
- Documentation déploiement
- Tests recette validés
- Version production ready

## Spécifications Techniques Détaillées

### Frontend React - Stack Technique
```json
{
  "framework": "React 18 + TypeScript",
  "ui_library": "Material-UI v5",
  "state_management": "Zustand",
  "routing": "React Router v6",
  "http_client": "Axios",
  "testing": "Jest + React Testing Library",
  "bundler": "Vite"
}
```

### Backend FastAPI - Stack Technique
```json
{
  "framework": "FastAPI + Uvicorn",
  "database": "PostgreSQL 15 + asyncpg",
  "orm": "SQLAlchemy 2.0 + Alembic",
  "auth": "JWT + bcrypt",
  "validation": "Pydantic v2",
  "testing": "pytest + httpx",
  "documentation": "Swagger UI automatique"
}
```

### Service IA Locale - Ollama Stack
```json
{
  "ia_engine": "Ollama + Docker",
  "models": {
    "document_analysis": "llama3.2:8b",
    "image_analysis": "llava:7b",
    "spreadsheet_analysis": "codellama:7b",
    "video_analysis": "llava:7b"
  },
  "hardware": "32 vCPU + 128GB RAM",
  "processing_mode": "batch_night_weekend",
  "capabilities": [
    "PDF summarization",
    "Excel data extraction",
    "Image description",
    "Video content analysis"
  ]
}
```

### Base de Données PostgreSQL
```sql
-- Utilisateurs et permissions (intégration AD)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    domain VARCHAR(50) NOT NULL DEFAULT 'SMIDEN',
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    ad_username VARCHAR(100) UNIQUE NOT NULL, -- Format: SMIDEN\flamachere
    password_hash VARCHAR(255), -- Optionnel si auth AD
    role VARCHAR(20) DEFAULT 'user', -- 'admin', 'user'
    is_ad_user BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configuration Active Directory
CREATE TABLE ad_config (
    id SERIAL PRIMARY KEY,
    server_address VARCHAR(100) NOT NULL DEFAULT '172.16.252.33',
    domain_name VARCHAR(50) NOT NULL DEFAULT 'SMIDEN',
    base_dn VARCHAR(200), -- ex: OU=Users,DC=SMIDEN,DC=local
    bind_user VARCHAR(100), -- Utilisateur de connexion AD
    bind_password VARCHAR(255), -- Mot de passe connexion AD
    port INTEGER DEFAULT 389,
    use_ssl BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Fichiers (schema amélioré avec IA)
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    path VARCHAR(1000) NOT NULL,
    name VARCHAR(255) NOT NULL,
    size BIGINT,
    checksum VARCHAR(64),
    last_modified TIMESTAMP,
    is_directory BOOLEAN DEFAULT FALSE,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES files(id),
    file_owner VARCHAR(100),  -- Propriétaire du fichier
    ai_summary TEXT,  -- Résumé généré par l'IA
    ai_analysis JSONB,  -- Analyse structurée par l'IA
    ai_processed BOOLEAN DEFAULT FALSE,  -- Si l'IA a traité le fichier
    ai_model_version VARCHAR(50),  -- Version du modèle IA utilisé
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tâches IA pour traitement par lots
CREATE TABLE ai_tasks (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    task_type VARCHAR(50) NOT NULL, -- 'summarize', 'analyze_image', 'extract_data'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    model_used VARCHAR(50),
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Notifications et alertes utilisateurs
CREATE TABLE user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(50) NOT NULL, -- 'digest', 'alert', 'webhook'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    action_required BOOLEAN DEFAULT FALSE,
    action_url VARCHAR(500),
    action_deadline TIMESTAMP,
    status VARCHAR(20) DEFAULT 'unread', -- 'unread', 'read', 'actioned'
    created_at TIMESTAMP DEFAULT NOW(),
    read_at TIMESTAMP
);

-- Configuration des périodes de vacances
CREATE TABLE vacation_periods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    default_days INTEGER DEFAULT 14, -- Jours par défaut pendant cette période
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Configuration backup et archivage
CREATE TABLE backup_config (
    id SERIAL PRIMARY KEY,
    max_age_days INTEGER DEFAULT 730, -- 2 ans par défaut
    large_file_threshold_mb INTEGER DEFAULT 100, -- 100MB par défaut
    backup_path VARCHAR(500) NOT NULL DEFAULT '/mnt/nas/archives',
    create_symlinks BOOLEAN DEFAULT TRUE,
    admin_validation_required BOOLEAN DEFAULT FALSE, -- FALSE pour automatique
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configuration retry et résilience
CREATE TABLE retry_config (
    id SERIAL PRIMARY KEY,
    retry_intervals INTEGER[] DEFAULT ARRAY[1, 2, 5, 15, 30, 60, 120], -- en minutes
    server_timeout_minutes INTEGER DEFAULT 2, -- timeout détection serveur
    vm_reboot_min_minutes INTEGER DEFAULT 2, -- temps min reboot VM
    vm_reboot_max_minutes INTEGER DEFAULT 20, -- temps max reboot VM
    continue_on_server_error BOOLEAN DEFAULT TRUE, -- continuer scan si possible
    max_consecutive_failures INTEGER DEFAULT 3, -- arrêt après N échecs consécutifs
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Historique des retries et erreurs
CREATE TABLE retry_history (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100),
    error_type VARCHAR(50), -- 'server_timeout', 'connection_error', 'scan_error'
    retry_attempt INTEGER,
    retry_interval_minutes INTEGER,
    success BOOLEAN,
    error_message TEXT,
    server_downtime_minutes INTEGER, -- durée d'indisponibilité serveur
    created_at TIMESTAMP DEFAULT NOW()
);

-- État des workers en temps réel
CREATE TABLE worker_status (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'idle', -- 'idle', 'running', 'error', 'retrying'
    last_activity TIMESTAMP DEFAULT NOW(),
    current_path VARCHAR(1000),
    files_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    server_reachable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configuration monitoring crawler
CREATE TABLE crawler_monitoring_config (
    id SERIAL PRIMARY KEY,
    metrics_priority VARCHAR(50) DEFAULT 'files_per_second', -- 'files_per_second', 'errors', 'worker_status'
    real_time_alerts BOOLEAN DEFAULT TRUE, -- WebSocket alerts
    history_retention_days INTEGER DEFAULT 0, -- 0 = illimité, backup externe
    performance_tracking BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Historique des archivages
CREATE TABLE archive_history (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    original_path VARCHAR(1000) NOT NULL,
    archive_path VARCHAR(1000) NOT NULL,
    symlink_path VARCHAR(1000),
    archive_reason VARCHAR(100), -- 'old_file', 'large_file', 'manual'
    archived_by INTEGER REFERENCES users(id),
    archive_date TIMESTAMP DEFAULT NOW(),
    file_size BIGINT,
    is_symlink_valid BOOLEAN DEFAULT TRUE
);

-- Webhooks pour actions one-click
CREATE TABLE webhooks (
    id SERIAL PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- 'archive', 'delete', 'approve'
    file_id INTEGER REFERENCES files(id),
    user_id INTEGER REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index optimisés pour performance
CREATE INDEX idx_files_path ON files(path);
CREATE INDEX idx_files_checksum ON files(checksum);
CREATE INDEX idx_files_duplicate ON files(is_duplicate);
CREATE INDEX idx_files_ai_processed ON files(ai_processed);
CREATE INDEX idx_files_owner ON files(file_owner);
CREATE INDEX idx_ai_tasks_status ON ai_tasks(status);
CREATE INDEX idx_ai_tasks_type ON ai_tasks(task_type);
CREATE INDEX idx_notifications_user_status ON user_notifications(user_id, status);
CREATE INDEX idx_notifications_type ON user_notifications(notification_type);
CREATE INDEX idx_webhooks_token ON webhooks(token);
CREATE INDEX idx_webhooks_expires ON webhooks(expires_at);
CREATE INDEX idx_users_ad_username ON users(ad_username);
CREATE INDEX idx_users_domain ON users(domain);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_archive_history_file ON archive_history(file_id);
CREATE INDEX idx_archive_history_date ON archive_history(archive_date);
CREATE INDEX idx_archive_history_reason ON archive_history(archive_reason);
CREATE INDEX idx_retry_history_worker ON retry_history(worker_id);
CREATE INDEX idx_retry_history_created ON retry_history(created_at);
CREATE INDEX idx_worker_status_id ON worker_status(worker_id);
CREATE INDEX idx_worker_status_status ON worker_status(status);
```

### Docker Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/openindex
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - OLLAMA_URL=http://ai-service:11434
    depends_on:
      - postgres
      - ai-service

  ai-service:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    deploy:
      resources:
        limits:
          cpus: '16'
          memory: 64G
        reservations:
          cpus: '8'
          memory: 32G

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=openindex
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  ollama_data:
```

## Fonctionnalités Améliorées

### Expérience Utilisateur
- **Navigation instantanée** : SPA sans rechargement
- **Design moderne** : Material-UI professionnel
- **Responsive** : Adapté mobile/tablette/desktop
- **Animations fluides** : Transitions et micro-interactions
- **Thème personnalisable** : Clair/sombre automatique
- **Résumés IA intégrés** : Aperçu du contenu sans ouvrir les fichiers
- **Analyse intelligente** : Extraction données Excel, description images/vidéos

### Performance
- **Base de données PostgreSQL** : 10x plus performante que SQLite
- **API asynchrone** : FastAPI avec support concurrence
- **Cache intelligent** : Redis pour données fréquemment accédées
- **Pagination optimisée** : Streaming pour grandes volumétries
- **Traitement IA par lots** : Analyse en nuit/week-end pour optimiser ressources

### Multi-Utilisateurs
- **Authentification JWT** : Sécurisée et stateless
- **Intégration Active Directory** : Connexion au serveur 172.16.252.33
- **Format utilisateur** : Domaine\username (ex: SMIDEN\flamachere)
- **Gestion des rôles** : Admin (technicien SMIDEN, DGS) vs Utilisateurs
- **Permissions granulaires** : Lecture/écriture sur ses propres fichiers uniquement
- **Sessions simultanées** : Support 15 utilisateurs
- **Propriétaires fichiers** : Traçabilité utilisateur SMB + AD

### Intelligence Artificielle Locale
- **Ollama intégré** : Modèles spécialisés par type de fichier
- **Traitement par lots** : Analyse automatique en nuit/week-end
- **Résumés documents** : PDF, DOCX, TXT synthétisés
- **Extraction données** : Tableurs Excel analysés et structurés
- **Description visuelle** : Images et vidéos analysées
- **Multi-modèles** : Llama3.2 pour textes, LLaVA pour images, CodeLlama pour données structurées

### Interface Utilisateur React
- **Layout fixe avec onglets** : Structure VanillaJS, pas de personnalisation utilisateur
- **Mode focus** : Panneau principal + volets latéraux repliables
- **Responsive desktop** : Priorité bureau (mobile/tablette plus tard)
- **Navigation par onglets** : Tableau de bord, Fichiers, Doublons, Configuration, Export
- **Panneaux interactifs** : Tous sur la même page avec communication entre panneaux
- **Email digest hebdomadaire** : Résumé post-crawl avec actions requises
- **Notifications in-app** : Alertes temps réel pour actions critiques
- **Webhooks d'archivage** : Bouton one-click dans email pour archiver/refuser
- **Validation fichiers non-professionnels** : Workflow admin avec faux-positifs
- **Configuration vacances** : Périodes flexibles (ex: 2 semaines mars, 5 semaines été)
- **Digest personnalisable** : Fréquence et contenu adaptés aux rôles

### Authentification & SSO
- **Keycloak intégré** : Active Directory local (fédération possible)
- **Gestion des rôles** : Agents/Modérateur de groupe, Modérateur (DGS), Administrateur
- **Session timeout** : 20 minutes d'inactivité par défaut
- **Support multi-fédération** : Azure AD, Google Workspace extensibles

### Activité Crawler & Monitoring
- **Métriques prioritaires** : Fichiers/secondes (pas %), erreurs, état workers
- **Alertes temps réel** : WebSocket pour légèreté maximale
- **Historique illimité** : Backup journalier externe, pas de rétention en base

### Monitoring & Maintenance
- **Logs structurés** : Suivi des actions utilisateurs
- **Métriques temps réel** : Performance et utilisation
- **Alertes automatiques** : Erreurs et seuils
- **Sauvegardes automatiques** : Base de données PostgreSQL

### Backup Automatique & Archivage
- **Seuil ancienneté** : 2 ans par défaut (configurable)
- **Taille critique** : Fichiers >100MB considérés comme "très gros"
- **Archivage transparent** : Déplacement automatique vers NAS locaux (23To)
- **Liens symboliques** : Création automatique pour transparence utilisateur
- **Infrastructure hybride** : 2To cloud + 23To NAS/SAN locaux
- **Validation admin** : Optionnelle pour gros volumes critiques

### Retry & Résilience Avancée
- **Pattern personnalisé** : 1, 2, 5, 15, 30, 60, 120 minutes
- **Détection intelligente** : Validation base de données (2min timeout)
- **Reboot serveur** : Adapté aux VMs (2-20min temps de redémarrage)
- **Continuation scan** : Poursuite si possible, erreur seulement si scan impossible
- **Workers automatiques** : Relance individuelle des workers en échec
- **Arrêt gracieux** : Détection serveur actif vs timeout

## Migration des Données

### Script de Migration SQLite → PostgreSQL
```python
# migration_script.py
import sqlite3
import asyncpg
import asyncio

async def migrate_data():
    # Connexion SQLite (source)
    sqlite_conn = sqlite3.connect('openindex.db')
    
    # Connexion PostgreSQL (cible)
    pg_conn = await asyncpg.connect(
        'postgresql://user:pass@localhost/openindex'
    )
    
    # Migration des tables
    await migrate_files(sqlite_conn, pg_conn)
    await migrate_users(sqlite_conn, pg_conn)
    
    # Vérification intégrité
    await verify_migration(pg_conn)
```

### Validation Post-Migration
- **Intégrité des checksums** : Vérification SHA-256
- **Comptage des enregistrements** : SQLite vs PostgreSQL
- **Tests de performance** : Requêtes typiques
- **Validation UI** : Affichage correct des données

## Risques et Mitigations

### Risques Techniques
| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Délai serré | Élevée | Critique | Priorisation features, travail parallèle |
| Migration données | Moyenne | Critique | Scripts automatisés, tests validation |
| Apprentissage React | Faible | Moyenne | Documentation, composants réutilisables |
| Performance PostgreSQL | Faible | Moyenne | Tests charge, optimisation queries |

### Risques Fonctionnels
| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Perte fonctionnalités | Faible | Critique | Tests exhaustifs, rétrocompatibilité |
| UX dégradée | Faible | Moyenne | Tests utilisateurs, itérations rapides |
| Multi-utilisateurs | Moyenne | Moyenne | Tests concurrence, gestion erreurs |

## Livrables Finale

### Application Complète
- **Frontend React** : Interface moderne et responsive
- **Backend FastAPI** : API performante et sécurisée
- **Base PostgreSQL** : Données migrées et optimisées
- **Docker Compose** : Déploiement en une commande

### Documentation
- **README technique** : Architecture et installation
- **Guide utilisateur** : Fonctionnalités et utilisation
- **Documentation API** : Swagger UI automatique
- **Guide déploiement** : Docker et maintenance

### Tests et Qualité
- **Tests unitaires** : Backend et frontend
- **Tests d'intégration** : E2E automatisés
- **Tests de charge** : Performance multi-utilisateurs
- **Tests de sécurité** : Authentification et permissions

## Conclusion

Cette proposition offre une évolution majeure vers une application moderne, performante et professionnelle, tout en respectant la deadline du 19 mars 2026.

**Avantages clés :**
- ✅ Interface moderne et agréable
- ✅ Performance optimale pour 15 utilisateurs
- ✅ Base de données robuste et scalable
- ✅ Déploiement Docker simplifié
- ✅ Maintenance facilitée

**Investissement :**
- 3 semaines de développement intensif
- Migration technologique complète
- Gain en expérience utilisateur significatif
- Base technique solide pour évolutions futures

Cette migration positionnera OpenIndex comme une solution professionnelle moderne, adaptée aux besoins réels des utilisateurs et évolutive pour les années à venir.
