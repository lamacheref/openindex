# API Reference - Archive Queue

## Overview

L'API Archive Queue fournit des endpoints REST pour gérer les opérations d'archivage de fichiers SMB avec support des retries, suivi de progression et priorisation.

## Base URL

```
http://localhost:8000/api/archive/queue
```

## Authentication

Toutes les requêtes nécessitent une authentification via header `Authorization` :

```bash
Authorization: Bearer <token>
```

## Endpoints

### 1. Créer un job d'archivage

**POST** `/api/archive/queue`

Crée un nouveau job dans la queue d'archivage.

#### Request Body

```json
{
  "job_type": "copy|move|delete",
  "source_path": "\\\\server\\share\\file.txt",
  "dest_path": "\\\\archive\\storage\\file.txt",
  "priority": 5
}
```

#### Champs

| Champ | Type | Requis | Description |
|-------|------|---------|-------------|
| job_type | string | ✅ | Type d'opération : `copy`, `move`, `delete` |
| source_path | string | ✅ | Chemin source SMB |
| dest_path | string | ❌ | Chemin destination (requis pour copy/move) |
| priority | integer | ❌ | Priorité 1-10 (défaut: 5) |

#### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "job_type": "copy",
  "source_path": "\\\\server\\share\\file.txt",
  "dest_path": "\\\\archive\\storage\\file.txt",
  "status": "pending",
  "priority": 5,
  "retry_count": 0,
  "max_retries": 3,
  "error_message": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2026-04-02T16:00:00Z",
  "source_size": null,
  "bytes_transferred": 0
}
```

#### Exemples

```bash
# Copie de fichier
curl -X POST http://localhost:8000/api/archive/queue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "job_type": "copy",
    "source_path": "\\\\server\\share\\document.pdf",
    "dest_path": "\\\\archive\\storage\\document.pdf",
    "priority": 8
  }'

# Déplacement avec priorité haute
curl -X POST http://localhost:8000/api/archive/queue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "job_type": "move",
    "source_path": "\\\\server\\share\\old_file.txt",
    "dest_path": "\\\\archive\\storage\\old_file.txt",
    "priority": 10
  }'

# Suppression
curl -X POST http://localhost:8000/api/archive/queue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "job_type": "delete",
    "source_path": "\\\\server\\share\\temp_file.tmp"
  }'
```

### 2. Lister les jobs

**GET** `/api/archive/queue`

Liste les jobs avec pagination et filtrage.

#### Query Parameters

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| status | string | all | Filtre par statut : `pending`, `running`, `completed`, `failed`, `cancelled` |
| job_type | string | all | Filtre par type : `copy`, `move`, `delete` |
| priority | integer | all | Filtre par priorité exacte |
| limit | integer | 50 | Nombre maximum de résultats |
| offset | integer | 0 | Offset pour pagination |
| sort | string | created_at | Champ de tri : `created_at`, `priority`, `status` |
| order | string | desc | Ordre : `asc`, `desc` |

#### Response

```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "job_type": "copy",
      "source_path": "\\\\server\\share\\file.txt",
      "dest_path": "\\\\archive\\storage\\file.txt",
      "status": "completed",
      "priority": 5,
      "retry_count": 0,
      "max_retries": 3,
      "error_message": null,
      "started_at": "2026-04-02T16:01:00Z",
      "completed_at": "2026-04-02T16:02:30Z",
      "created_at": "2026-04-02T16:00:00Z",
      "source_size": 1048576,
      "bytes_transferred": 1048576
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### Exemples

```bash
# Jobs en attente
curl "http://localhost:8000/api/archive/queue?status=pending&priority=8"

# Jobs de type copie
curl "http://localhost:8000/api/archive/queue?job_type=copy&sort=priority&order=desc"

# Pagination
curl "http://localhost:8000/api/archive/queue?limit=10&offset=20"

# Jobs échoués
curl "http://localhost:8000/api/archive/queue?status=failed"
```

### 3. Détails d'un job

**GET** `/api/archive/queue/{job_id}`

Récupère les détails complets d'un job spécifique.

#### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "job_type": "copy",
  "source_path": "\\\\server\\share\\file.txt",
  "dest_path": "\\\\archive\\storage\\file.txt",
  "status": "running",
  "priority": 5,
  "retry_count": 1,
  "max_retries": 3,
  "error_message": "Connection timeout, retrying...",
  "started_at": "2026-04-02T16:01:00Z",
  "completed_at": null,
  "created_at": "2026-04-02T16:00:00Z",
  "source_size": 1048576,
  "bytes_transferred": 524288,
  "progress": 50
}
```

#### Exemple

```bash
curl "http://localhost:8000/api/archive/queue/550e8400-e29b-41d4-a716-446655440000"
```

### 4. Annuler un job

**DELETE** `/api/archive/queue/{job_id}`

Annule un job en attente ou en cours.

#### Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "message": "Job cancelled successfully"
}
```

#### Exemple

```bash
curl -X DELETE "http://localhost:8000/api/archive/queue/550e8400-e29b-41d4-a716-446655440000"
```

### 5. Statistiques de la queue

**GET** `/api/archive/queue/stats`

Récupère les statistiques globales de la queue.

#### Response

```json
{
  "pending": 5,
  "running": 2,
  "completed": 150,
  "failed": 3,
  "cancelled": 1,
  "total_size_pending": 1073741824,
  "total_size_transferred": 53687091200,
  "avg_execution_time_seconds": 45.2,
  "success_rate": 0.97
}
```

#### Champs

| Champ | Type | Description |
|-------|------|-------------|
| pending | integer | Nombre de jobs en attente |
| running | integer | Nombre de jobs en cours |
| completed | integer | Nombre de jobs terminés |
| failed | integer | Nombre de jobs échoués |
| cancelled | integer | Nombre de jobs annulés |
| total_size_pending | integer | Volume total en attente (bytes) |
| total_size_transferred | integer | Volume total transféré (bytes) |
| avg_execution_time_seconds | float | Temps moyen d'exécution |
| success_rate | float | Taux de réussite (0-1) |

#### Exemple

```bash
curl "http://localhost:8000/api/archive/queue/stats"
```

### 6. Réessayer un job échoué

**POST** `/api/archive/queue/{job_id}/retry`

Réinitialise un job échoué pour qu'il soit réessayé.

#### Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "message": "Job reset for retry"
}
```

#### Exemple

```bash
curl -X POST "http://localhost:8000/api/archive/queue/550e8400-e29b-41d4-a716-446655440000/retry"
```

## Codes d'erreur

| Code | Description | Solution |
|------|-------------|----------|
| 400 | Requête invalide | Vérifier les paramètres |
| 401 | Non authentifié | Fournir token valide |
| 403 | Permission refusée | Vérifier permissions |
| 404 | Job introuvable | Vérifier job_id |
| 409 | Conflit | Job déjà traité ou fichier existe |
| 422 | Validation échouée | Corriger les données |
| 429 | Trop de requêtes | Limiter le taux |
| 500 | Erreur serveur | Contacter support |

## Modèles de données

### ArchiveJobType

```typescript
enum ArchiveJobType {
  COPY = "copy"
  MOVE = "move"
  DELETE = "delete"
}
```

### ArchiveJobStatus

```typescript
enum ArchiveJobStatus {
  PENDING = "pending"
  RUNNING = "running"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"
}
```

### ArchiveJobCreate

```typescript
interface ArchiveJobCreate {
  job_type: ArchiveJobType
  source_path: string
  dest_path?: string
  priority?: number  // 1-10
}
```

### ArchiveJobResponse

```typescript
interface ArchiveJobResponse {
  id: string
  job_type: string
  source_path: string
  dest_path?: string
  status: string
  priority: number
  retry_count: number
  max_retries: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
  source_size?: number
  bytes_transferred: number
}
```

## Exemples d'utilisation

### Workflow complet

```bash
# 1. Créer un job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/archive/queue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "job_type": "copy",
    "source_path": "\\\\server\\share\\important.doc",
    "dest_path": "\\\\archive\\storage\\important.doc",
    "priority": 10
  }' | jq -r '.id')

# 2. Suivre la progression
curl "http://localhost:8000/api/archive/queue/$JOB_ID"

# 3. Vérifier le statut final
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/archive/queue/$JOB_ID" | jq -r '.status')
  echo "Status: $STATUS"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "cancelled" ]]; then
    break
  fi
  sleep 5
done

# 4. Afficher les détails finaux
curl "http://localhost:8000/api/archive/queue/$JOB_ID" | jq .
```

### Monitoring avec curl

```bash
# Statistiques en temps réel
watch -n 5 'curl -s "http://localhost:8000/api/archive/queue/stats" | jq'

# Jobs en cours
watch -n 2 'curl -s "http://localhost:8000/api/archive/queue?status=running" | jq ".jobs[]"'

# Jobs échoués récents
curl -s "http://localhost:8000/api/archive/queue?status=failed&sort=created_at&order=desc&limit=5" | jq ".jobs[]"
```

### Scripts batch

```bash
#!/bin/bash
# create_archive_jobs.sh

# Fichier de configuration
CONFIG_FILE="jobs_to_archive.csv"

# Lire et créer les jobs
while IFS=, read -r source dest priority; do
  echo "Creating job: $source -> $dest (priority: $priority)"
  
  curl -s -X POST http://localhost:8000/api/archive/queue \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{
      \"job_type\": \"copy\",
      \"source_path\": \"$source\",
      \"dest_path\": \"$dest\",
      \"priority\": $priority
    }" | jq -r '.id'
done < "$CONFIG_FILE"

echo "All jobs created. Check status with:"
echo "curl \"http://localhost:8000/api/archive/queue/stats\""
```

## WebSocket (Monitoring temps réel)

Pour le monitoring en temps réel, connectez-vous au WebSocket :

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/archive/queue');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'job_created':
      console.log('New job:', data.job);
      break;
    case 'job_updated':
      console.log('Job updated:', data.job);
      break;
    case 'job_completed':
      console.log('Job completed:', data.job);
      break;
    case 'job_failed':
      console.error('Job failed:', data.job);
      break;
  }
};
```

## Rate Limiting

L'API est limitée pour éviter les abus :

| Endpoint | Limite | Période |
|---------|-------|--------|
| POST /queue | 10 req/min | Par utilisateur |
| GET /queue | 100 req/min | Par utilisateur |
| DELETE /queue/{id} | 20 req/min | Par utilisateur |
| GET /stats | 60 req/min | Par utilisateur |

## SDK / Client Libraries

### Python

```python
import requests
from typing import List, Optional

class ArchiveQueueClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_job(self, job_type: str, source_path: str, 
                   dest_path: Optional[str] = None, priority: int = 5) -> dict:
        data = {
            'job_type': job_type,
            'source_path': source_path,
            'dest_path': dest_path,
            'priority': priority
        }
        response = requests.post(f'{self.base_url}/api/archive/queue', 
                                json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_job(self, job_id: str) -> dict:
        response = requests.get(f'{self.base_url}/api/archive/queue/{job_id}',
                               headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self, status: Optional[str] = None, 
                   limit: int = 50, offset: int = 0) -> dict:
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        
        response = requests.get(f'{self.base_url}/api/archive/queue',
                               params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

# Utilisation
client = ArchiveQueueClient('http://localhost:8000', 'your-token')
job = client.create_job('copy', '\\server\\share\\file.txt', 
                        '\\archive\\storage\\file.txt', 8)
print(f"Job created: {job['id']}")
```

### JavaScript/TypeScript

```typescript
class ArchiveQueueClient {
  constructor(private baseUrl: string, private token: string) {}

  private headers = {
    'Authorization': `Bearer ${this.token}`,
    'Content-Type': 'application/json'
  };

  async createJob(jobType: string, sourcePath: string, 
                   destPath?: string, priority = 5): Promise<ArchiveJobResponse> {
    const response = await fetch(`${this.baseUrl}/api/archive/queue`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        job_type: jobType,
        source_path: sourcePath,
        dest_path: destPath,
        priority
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  }

  async getJob(jobId: string): Promise<ArchiveJobResponse> {
    const response = await fetch(`${this.baseUrl}/api/archive/queue/${jobId}`, {
      headers: this.headers
    });
    
    return response.json();
  }

  async listJobs(options: {
    status?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<ArchiveJobList> {
    const params = new URLSearchParams();
    if (options.status) params.append('status', options.status);
    if (options.limit) params.append('limit', options.limit.toString());
    if (options.offset) params.append('offset', options.offset.toString());
    
    const response = await fetch(`${this.baseUrl}/api/archive/queue?${params}`, {
      headers: this.headers
    });
    
    return response.json();
  }
}

// Utilisation
const client = new ArchiveQueueClient('http://localhost:8000', 'your-token');

client.createJob('copy', '\\\\server\\share\\file.txt', 
                   '\\\\archive\\storage\\file.txt', 8)
  .then(job => console.log('Job created:', job))
  .catch(error => console.error('Error:', error));
```
