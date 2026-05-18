# SMB Health Monitoring System

## Overview

Le SMB Health Monitoring System surveille l'état des serveurs SMB et gère automatiquement les crawls en cas de panne. Il permet de mettre en pause les crawls quand un serveur devient inaccessible et de les reprendre automatiquement quand il revient en ligne.

## Architecture

### Composants principaux

1. **SMBHealthMonitor** (`src/smb_health_monitor.py`)
   - Surveillance périodique des serveurs SMB
   - Détection des changements d'état (online/offline/degraded)
   - Callbacks pour notifier les changements

2. **Integration Crawler** (`src/smb_crawler_monitoring.py`)
   - Wrapper pour `run_single_crawl` avec monitoring
   - Gestion automatique des pauses/reprises
   - Maintien de l'état du crawl

3. **Worker Loop** (`src/smb_crawler_worker_monitoring.py`)
   - Boucle principale avec monitoring intégré
   - Reprise automatique des crawls en statut 'pending'
   - Gestion des runs interrompus

## SMBHealthMonitor

### Configuration

```python
class SMBHealthMonitor:
    def __init__(
        self,
        check_interval: float = 30.0,  # secondes
        timeout: float = 5.0,            # timeout ping
        max_failures: int = 3,           # échecs consécutifs avant offline
        callbacks: Dict[str, Callable] = None
    )
```

### États surveillés

- **ONLINE** : Serveur accessible et fonctionnel
- **OFFLINE** : Serveur inaccessible (échecs > max_failures)
- **DEGRADED** : Serveur accessible mais lent (latence > 2x normale)

### Callbacks

```python
def on_server_down(server_name: str, last_error: Exception):
    """Appelé quand un serveur devient inaccessible"""
    logger.warning(f"🔴 Server {server_name} down: {last_error}")
    # Mettre en pause les crawls actifs

def on_server_up(server_name: str):
    """Appelé quand un serveur revient en ligne"""
    logger.info(f"🟢 Server {server_name} back online")
    # Reprendre les crawls en attente
```

## Intégration avec le Crawler

### Modification de SMBCrawlerPostgreSQL

```python
# Ajout dans __init__
self.health_monitor = SMBHealthMonitor(
    check_interval=30.0,
    callbacks={
        'server_down': self._handle_server_down,
        'server_up': self._handle_server_up
    }
)

# Handlers
def _handle_server_down(self, server_name: str, error: Exception):
    """Met en pause le crawl courant"""
    if self.run_id and self.postgres_adapter:
        self.postgres_adapter.update_crawl_run_status(
            self.run_id, "pending"
        )
        self.logger.warning(f"Crawl paused due to SMB server {server_name} down")

def _handle_server_up(self, server_name: str):
    """Reprend le crawl si possible"""
    if self.run_id and self.postgres_adapter:
        status = self.postgres_adapter.get_crawl_run_status(self.run_id)
        if status == "pending":
            self.postgres_adapter.update_crawl_run_status(
                self.run_id, "running"
            )
            self.logger.info(f"Crawl resumed for SMB server {server_name}")
```

### Wrapper run_single_crawl

```python
def run_single_crawl_with_monitoring(
    config: Dict[str, Any],
    postgres_adapter: Any,
    run_id: Optional[str] = None
) -> None:
    """Exécute un crawl avec monitoring SMB actif"""
    crawler = SMBCrawlerPostgreSQL(config, postgres_adapter)
    
    # Démarrer le monitoring
    crawler.health_monitor.start()
    
    try:
        if run_id:
            crawler.run_id = run_id
            # Vérifier si le run a été mis en pause
            status = postgres_adapter.get_crawl_run_status(run_id)
            if status == "pending":
                # Attendre que le serveur SMB revienne en ligne
                crawler.health_monitor.wait_for_server()
        
        crawler.run_single_crawl()
    finally:
        crawler.health_monitor.stop()
```

## Worker avec Monitoring

### Boucle principale

```python
def worker_loop_with_monitoring():
    """Boucle worker avec gestion des pannes SMB"""
    health_monitor = SMBHealthMonitor(
        callbacks={
            'server_down': pause_active_crawls,
            'server_up': resume_pending_crawls
        }
    )
    
    health_monitor.start()
    
    while True:
        try:
            # Récupérer les crawls en attente
            pending_runs = get_pending_crawl_runs()
            
            for run in pending_runs:
                if health_monitor.is_server_available(run['config']):
                    start_crawl_run(run)
                else:
                    logger.info(f"Skipping {run['id']}: server down")
            
            time.sleep(10)  # Pause entre vérifications
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(30)
```

### Gestion des runs interrompus

```python
def resume_pending_crawls():
    """Reprend les crawls qui étaient en attente"""
    pending_runs = postgres_adapter.list_crawl_runs(
        status="pending",
        limit=50
    )
    
    for run in pending_runs:
        config = postgres_adapter.get_crawl_config(run['config_id'])
        if health_monitor.is_server_available(config['server']):
            logger.info(f"Resuming crawl {run['id']}")
            postgres_adapter.update_crawl_run_status(
                run['id'], "running"
            )
            # Démarrer le crawl dans un thread séparé
            start_crawl_thread(config, run['id'])
```

## Configuration

### Variables d'environnement

```bash
# Monitoring SMB
OPENINDEX_SMB_CHECK_INTERVAL=30    # secondes
OPENINDEX_SMB_TIMEOUT=5.0          # secondes
OPENINDEX_SMB_MAX_FAILURES=3       # échecs consécutifs
OPENINDEX_SMB_DEGRADED_LATENCY=2.0 # seuil latence dégradée

# Gestion des crawls
OPENINDEX_CRAWL_PAUSE_ON_SMB_DOWN=true
OPENINDEX_CRAWL_AUTO_RESUME=true
OPENINDEX_CRAWL_MAX_PENDING_TIME=3600  # secondes
```

### Configuration par code

```python
# Dans smb_crawler_postgresql.py
self.health_monitor = SMBHealthMonitor(
    check_interval=float(os.getenv("OPENINDEX_SMB_CHECK_INTERVAL", "30.0")),
    timeout=float(os.getenv("OPENINDEX_SMB_TIMEOUT", "5.0")),
    max_failures=int(os.getenv("OPENINDEX_SMB_MAX_FAILURES", "3")),
    callbacks={
        'server_down': self._handle_server_down,
        'server_up': self._handle_server_up,
        'server_degraded': self._handle_server_degraded
    }
)
```

## Métriques et Monitoring

### États des serveurs

```python
class ServerState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class ServerMetrics:
    def __init__(self):
        self.server_name: str
        self.state: ServerState
        self.last_check: datetime
        self.failure_count: int
        self.latency_ms: float
        self.last_error: Optional[Exception]
```

### Logs structurés

```python
logger.info(f"🟢 SMB server {server_name} online (latency: {latency:.0f}ms)")
logger.warning(f"🟡 SMB server {server_name} degraded (latency: {latency:.0f}ms)")
logger.error(f"🔴 SMB server {server_name} offline (failures: {failures})")
logger.info(f"▶️  Crawl {run_id} paused due to SMB server {server_name} down")
logger.info(f"▶️  Crawl {run_id} resumed (SMB server {server_name} back online)")
```

## Dépannage

### Problèmes courants

1. **Faux positifs offline**
   - Augmenter `max_failures`
   - Vérifier latence réseau
   - Adapter `timeout`

2. **Crawls bloqués en pending**
   - Vérifier logs health monitor
   - Forcer reprise manuelle
   - Configurer auto-resume

3. **Performance impact**
   - Augmenter `check_interval`
   - Optimiser callbacks
   - Limiter nombre de serveurs surveillés

### Logs utiles

```bash
# Logs monitoring SMB
tail -f logs/smb_health_monitor.log

# Logs crawler avec monitoring
tail -f logs/smb_crawler_monitoring.log

# Logs worker
tail -f logs/smb_crawler_worker_monitoring.log
```

### Commandes de debug

```python
# État des serveurs
python -c "
from src.smb_health_monitor import SMBHealthMonitor
monitor = SMBHealthMonitor()
monitor.print_server_status()
"

# Forcer reprise crawl
python -c "
from src.smb_crawler_monitoring import resume_pending_crawls
resume_pending_crawls()
"
```

## Performance

### Impact sur les performances

- **CPU** : < 1% par serveur surveillé (ping + callbacks)
- **Réseau** : 1KB par check (ping SMB)
- **Mémoire** : ~1MB par health monitor

### Optimisations

- **Batch checks** : Vérification parallèle des serveurs
- **Callback async** : Non bloquant pour le crawler
- **Cache états** : Éviter vérifications répétées

## Sécurité

### Permissions requises

- Accès ping SMB sur les serveurs cibles
- Lecture/écriture status crawls en base
- Logs structurés pour audit

### Isolation

- Pas d'impact sur les crawls actifs
- Callbacks limités aux changements d'état
- Pas d'accès direct aux fichiers SMB

## Roadmap

### Améliorations futures

- [ ] Interface web de monitoring
- [ ] Notifications webhook/email
- [ ] Support des clusters SMB
- [ ] Prédictions de pannes (ML)
- [ ] Auto-scaling basé sur charge

### Tests

```bash
# Tests unitaires monitoring
pytest tests/test_smb_health_monitor.py

# Tests intégration crawler
pytest tests/test_smb_crawler_monitoring.py

# Tests end-to-end
python scripts/e2e_smb_monitoring_test.py
```
