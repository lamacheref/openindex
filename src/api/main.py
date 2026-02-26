"""
API FastAPI pour OpenIndex
Backend moderne avec WebSocket et monitoring temps réel
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import logging
from datetime import datetime

from postgres_adapter import PostgreSQLAdapter
from config_manager import ConfigManager


# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de FastAPI
app = FastAPI(
    title="OpenIndex API",
    description="API moderne pour l'indexation SMB",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8502"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modèles Pydantic
class FileInfo(BaseModel):
    id: str
    path: str
    name: str
    size: Optional[int] = None
    checksum: Optional[str] = None
    last_modified: Optional[str] = None
    is_directory: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CrawlStats(BaseModel):
    total_files: int
    total_directories: int
    total_size: int
    duplicate_files: int
    crawl_duration: Optional[float] = None
    status: str


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime


# Connexion à la base de données
def get_db_adapter():
    """Récupère l'adaptateur PostgreSQL"""
    try:
        config = ConfigManager()
        postgres_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'openindex',
            'user': 'openindex_user',
            'password': 'openindex_secure_password'
        }
        return PostgreSQLAdapter(postgres_config)
    except Exception as e:
        logger.error(f"Erreur connexion BDD: {e}")
        raise HTTPException(status_code=500, detail="Erreur de connexion à la base de données")


# Gestionnaire WebSocket pour le monitoring
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connecté. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client déconnecté. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Retirer les connexions mortes
                self.active_connections.remove(connection)


manager = ConnectionManager()


# Routes API
@app.get("/health")
async def health_check():
    """Health check pour Docker"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/files", response_model=List[FileInfo])
async def get_files(
    path: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None
):
    """Récupérer la liste des fichiers avec pagination et recherche"""
    try:
        db = get_db_adapter()
        
        # Construction de la requête
        where_clause = "1=1"
        params = []
        
        if search:
            where_clause += " AND (name ILIKE %s OR path ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if path:
            where_clause += " AND path LIKE %s"
            params.append(f"{path}%")
        
        query = f"""
            SELECT id, path, name, size, checksum, last_modified, 
                   is_directory, is_duplicate, duplicate_of,
                   created_at, updated_at
            FROM files 
            WHERE {where_clause}
            ORDER BY is_directory DESC, name ASC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        results = db.execute_query(query, params)
        
        return [
            FileInfo(
                id=str(row[0]),
                path=row[1],
                name=row[2],
                size=row[3],
                checksum=row[4],
                last_modified=row[5],
                is_directory=row[6],
                is_duplicate=row[7],
                duplicate_of=row[8],
                created_at=row[9].isoformat() if row[9] else None,
                updated_at=row[10].isoformat() if row[10] else None
            )
            for row in results
        ]
        
    except Exception as e:
        logger.error(f"Erreur get_files: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des fichiers")


@app.get("/api/stats", response_model=CrawlStats)
async def get_crawl_stats():
    """Récupérer les statistiques du crawl"""
    try:
        db = get_db_adapter()
        
        # Statistiques de base
        stats = db.get_statistics()
        
        return CrawlStats(
            total_files=stats.get('total_files', 0),
            total_directories=stats.get('total_directories', 0),
            total_size=stats.get('total_size', 0),
            duplicate_files=stats.get('duplicate_files', 0),
            crawl_duration=stats.get('crawl_duration'),
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Erreur get_stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")


@app.get("/api/duplicates")
async def get_duplicates():
    """Récupérer la liste des fichiers en double"""
    try:
        db = get_db_adapter()
        
        query = """
            SELECT f1.id, f1.path, f1.name, f1.size, f1.checksum,
                   f1.last_modified, f1.created_at, f1.updated_at,
                   f2.path as duplicate_of_path
            FROM files f1
            JOIN files f2 ON f1.checksum = f2.checksum AND f1.id != f2.id
            WHERE f1.is_duplicate = TRUE
            ORDER BY f1.size DESC
        """
        
        results = db.execute_query(query)
        
        return [
            {
                "id": str(row[0]),
                "path": row[1],
                "name": row[2],
                "size": row[3],
                "checksum": row[4],
                "last_modified": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
                "duplicate_of": row[8]
            }
            for row in results
        ]
        
    except Exception as e:
        logger.error(f"Erreur get_duplicates: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des doublons")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour le monitoring temps réel"""
    await manager.connect(websocket)
    try:
        while True:
            # Envoyer les statistiques actuelles toutes les 5 secondes
            await asyncio.sleep(5)
            
            try:
                db = get_db_adapter()
                stats = db.get_statistics()
                
                message = WebSocketMessage(
                    type="stats_update",
                    data=stats,
                    timestamp=datetime.now()
                )
                
                await manager.send_personal_message(
                    message.json(), 
                    websocket
                )
            except Exception as e:
                logger.error(f"Erreur WebSocket stats: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client WebSocket déconnecté")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Page d'accueil avec redirection vers le frontend"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OpenIndex API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 OpenIndex API</h1>
            <div class="card">
                <h2>📚 Documentation</h2>
                <p><a href="/docs" class="btn">📖 Swagger UI</a></p>
                <p><a href="/redoc" class="btn">📋 ReDoc</a></p>
            </div>
            <div class="card">
                <h2>🌐 Frontend</h2>
                <p><a href="http://localhost:3000" class="btn">🎨 Interface Web</a></p>
            </div>
            <div class="card">
                <h2>📊 Monitoring</h2>
                <p><a href="/ws" class="btn">🔌 WebSocket</a></p>
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
