"""
API FastAPI pour OpenIndex
Backend moderne avec WebSocket et monitoring temps réel
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import logging
import os
from datetime import datetime
from uuid import uuid4

try:
    import psycopg2
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None


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


class SpaceInfo(BaseModel):
    name: str
    path_prefix: str
    file_count: int


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime


class ExplainPlan(BaseModel):
    query_name: str
    analyze: bool
    plan: List[str]


class CrawlConnectionConfig(BaseModel):
    username: str
    password: str
    domain: Optional[str] = None


class CrawlConfigCreate(BaseModel):
    name: str
    domain_zone: str
    start_path: str
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    connection: CrawlConnectionConfig


class CrawlConfigPublic(BaseModel):
    id: str
    name: str
    domain_zone: str
    start_path: str
    include_paths: List[str]
    exclude_paths: List[str]
    connection_username: str
    connection_domain: Optional[str] = None
    created_at: str


class CrawlStartRequest(BaseModel):
    config_id: str


class CrawlRun(BaseModel):
    run_id: str
    config_id: str
    status: str
    triggered_at: str


def extract_space_prefix(path: str) -> Optional[str]:
    normalized = path.strip()
    if not normalized:
        return None

    if normalized.startswith("\\"):
        parts = [part for part in normalized.split("\\") if part]
        if len(parts) >= 2:
            return f"\\{parts[0]}\\{parts[1]}"
        return None

    if normalized.startswith("/"):
        parts = [part for part in normalized.split("/") if part]
        if parts:
            return f"/{parts[0]}"
        return "/"

    parts = [part for part in normalized.replace("\\", "/").split("/") if part]
    if parts:
        return parts[0]

    return None

class PostgreSQLAdapter:
    """Adaptateur PostgreSQL minimal pour l'API."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[tuple]:
        params = params or []
        pg_query = query.replace("?", "%s")
        if pg_query.startswith("EXPLAIN QUERY PLAN"):
            pg_query = pg_query.replace("EXPLAIN QUERY PLAN", "EXPLAIN", 1)

        with psycopg2.connect(**self.config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(pg_query, params)
                return cursor.fetchall()

    def get_statistics(self, space: Optional[str] = None) -> Dict[str, Any]:
        query = """
            SELECT
                COUNT(*) as total_files,
                SUM(CASE WHEN is_directory = TRUE THEN 1 ELSE 0 END) as total_directories,
                COALESCE(SUM(CASE WHEN is_directory = FALSE THEN size ELSE 0 END), 0) as total_size,
                SUM(CASE WHEN is_duplicate = TRUE THEN 1 ELSE 0 END) as duplicate_files
            FROM files
        """
        params: List[Any] = []
        if space:
            query += " WHERE path LIKE %s"
            params.append(f"{space}%")

        with psycopg2.connect(**self.config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone() or (0, 0, 0, 0)
                return {
                    "total_files": row[0] or 0,
                    "total_directories": row[1] or 0,
                    "total_size": row[2] or 0,
                    "duplicate_files": row[3] or 0,
                    "crawl_duration": None,
                }

    def get_spaces(self) -> List[Dict[str, Any]]:
        paths = self.execute_query("SELECT path FROM files WHERE path IS NOT NULL")
        spaces: Dict[str, Dict[str, Any]] = {}

        for row in paths:
            path = row[0]
            if not path:
                continue

            prefix = extract_space_prefix(path)
            if not prefix:
                continue

            if prefix not in spaces:
                spaces[prefix] = {
                    "name": prefix.replace("/", "").replace("\\", "") or prefix,
                    "path_prefix": prefix,
                    "file_count": 0,
                }
            spaces[prefix]["file_count"] += 1

        return sorted(spaces.values(), key=lambda item: item["name"].lower())


    def ensure_crawl_tables(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS crawl_configs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name TEXT NOT NULL,
                domain_zone TEXT NOT NULL,
                start_path TEXT NOT NULL,
                include_paths TEXT[] NOT NULL DEFAULT '{}',
                exclude_paths TEXT[] NOT NULL DEFAULT '{}',
                connection_username TEXT NOT NULL,
                connection_password TEXT NOT NULL,
                connection_domain TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_crawl_configs_created_at ON crawl_configs(created_at)",
            """
            CREATE TABLE IF NOT EXISTS crawl_runs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                config_id UUID NOT NULL REFERENCES crawl_configs(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'queued',
                triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_crawl_runs_triggered_at ON crawl_runs(triggered_at)",
        ]
        with psycopg2.connect(**self.config) as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
            conn.commit()

    def list_crawl_configs(self) -> List[Dict[str, Any]]:
        query = """
            SELECT id::text, name, domain_zone, start_path,
                   include_paths, exclude_paths,
                   connection_username, connection_domain,
                   created_at::text
            FROM crawl_configs
            ORDER BY created_at DESC
        """
        rows = self.execute_query(query)
        return [
            {
                "id": row[0],
                "name": row[1],
                "domain_zone": row[2],
                "start_path": row[3],
                "include_paths": row[4] or [],
                "exclude_paths": row[5] or [],
                "connection_username": row[6],
                "connection_domain": row[7],
                "created_at": row[8],
            }
            for row in rows
        ]

    def create_crawl_config(self, payload: CrawlConfigCreate) -> Dict[str, Any]:
        query = """
            INSERT INTO crawl_configs (
                name, domain_zone, start_path,
                include_paths, exclude_paths,
                connection_username, connection_password, connection_domain
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, name, domain_zone, start_path,
                      include_paths, exclude_paths,
                      connection_username, connection_domain,
                      created_at::text
        """
        with psycopg2.connect(**self.config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    [
                        payload.name,
                        payload.domain_zone,
                        payload.start_path,
                        payload.include_paths,
                        payload.exclude_paths,
                        payload.connection.username,
                        payload.connection.password,
                        payload.connection.domain,
                    ],
                )
                row = cursor.fetchone()
            conn.commit()

        return {
            "id": row[0],
            "name": row[1],
            "domain_zone": row[2],
            "start_path": row[3],
            "include_paths": row[4] or [],
            "exclude_paths": row[5] or [],
            "connection_username": row[6],
            "connection_domain": row[7],
            "created_at": row[8],
        }

    def start_crawl(self, config_id: str) -> Optional[Dict[str, Any]]:
        query = """
            INSERT INTO crawl_runs (config_id, status)
            SELECT id, 'queued'
            FROM crawl_configs
            WHERE id::text = %s
            RETURNING id::text, config_id::text, status, triggered_at::text
        """
        with psycopg2.connect(**self.config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, [config_id])
                row = cursor.fetchone()
            conn.commit()

        if not row:
            return None

        return {
            "run_id": row[0],
            "config_id": row[1],
            "status": row[2],
            "triggered_at": row[3],
        }


# Connexion à la base de données
def get_db_adapter():
    """Récupère l'adaptateur PostgreSQL (backend unique)."""
    backend = os.getenv("OPENINDEX_DB_BACKEND", "postgresql").strip().lower()

    if backend == "postgresql":
        if psycopg2 is None:
            raise HTTPException(status_code=500, detail="psycopg2 non disponible pour le backend PostgreSQL")

        pg_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB", "openindex"),
            "user": os.getenv("POSTGRES_USER", "openindex_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "openindex_secure_password"),
        }
        try:
            with psycopg2.connect(**pg_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            adapter = PostgreSQLAdapter(pg_config)
            adapter.ensure_crawl_tables()
            return adapter
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Base PostgreSQL indisponible: {exc}") from exc

    raise HTTPException(status_code=500, detail=f"Backend OPENINDEX_DB_BACKEND invalide: {backend}")


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
            except Exception:
                self.active_connections.remove(connection)


manager = ConnectionManager()

EXPLAIN_QUERIES = {
    "files_list": """
        SELECT id, path, name, size, checksum, last_modified,
               is_directory, is_duplicate, duplicate_of,
               created_at, updated_at
        FROM files
        ORDER BY is_directory DESC, name ASC
        LIMIT 100
    """,
    "duplicates": """
        SELECT f1.id, f1.path, f1.name, f1.size, f1.checksum,
               f2.path as duplicate_of_path
        FROM files f1
        JOIN files f2 ON f1.checksum = f2.checksum AND f1.id != f2.id
        WHERE f1.is_duplicate = 1
        ORDER BY f1.size DESC
        LIMIT 100
    """,
    "stats": """
        SELECT
            COUNT(*) as total_files,
            SUM(CASE WHEN is_directory = 0 THEN 1 ELSE 0 END) as files_only,
            SUM(CASE WHEN is_directory = 1 THEN 1 ELSE 0 END) as directories,
            SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as duplicates,
            COALESCE(SUM(CASE WHEN is_directory = 0 THEN size ELSE 0 END), 0) as total_size
        FROM files
    """,
}

CRAWL_CONFIGS: List[Dict[str, Any]] = []
CRAWL_RUNS: List[Dict[str, Any]] = []



@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/files", response_model=List[FileInfo])
async def get_files(path: Optional[str] = None, limit: int = 100, offset: int = 0, search: Optional[str] = None, space: Optional[str] = None):
    try:
        db = get_db_adapter()
        where_clause = "1=1"
        params = []

        if search:
            where_clause += " AND (name LIKE ? OR path LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if path:
            where_clause += " AND path LIKE ?"
            params.append(f"{path}%")

        if space:
            where_clause += " AND path LIKE ?"
            params.append(f"{space}%")

        query = f"""
            SELECT id, path, name, size, checksum, last_modified,
                   is_directory, is_duplicate, duplicate_of,
                   created_at, updated_at
            FROM files
            WHERE {where_clause}
            ORDER BY is_directory DESC, name ASC
            LIMIT ? OFFSET ?
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
                is_directory=bool(row[6]),
                is_duplicate=bool(row[7]),
                duplicate_of=row[8],
                created_at=row[9],
                updated_at=row[10],
            )
            for row in results
        ]
    except Exception as e:
        logger.error(f"Erreur get_files: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des fichiers")


@app.get("/api/stats", response_model=CrawlStats)
async def get_crawl_stats(space: Optional[str] = None):
    try:
        db = get_db_adapter()
        stats = db.get_statistics(space=space)
        return CrawlStats(
            total_files=stats.get("total_files", 0),
            total_directories=stats.get("total_directories", 0),
            total_size=stats.get("total_size", 0),
            duplicate_files=stats.get("duplicate_files", 0),
            crawl_duration=stats.get("crawl_duration"),
            status="completed",
        )
    except Exception as e:
        logger.error(f"Erreur get_stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")


@app.get("/api/duplicates")
async def get_duplicates(space: Optional[str] = None):
    try:
        db = get_db_adapter()
        query = """
            SELECT f1.id, f1.path, f1.name, f1.size, f1.checksum,
                   f1.last_modified, f1.created_at, f1.updated_at,
                   f2.path as duplicate_of_path
            FROM files f1
            JOIN files f2 ON f1.checksum = f2.checksum AND f1.id != f2.id
            WHERE f1.is_duplicate = 1
        """
        params: List[Any] = []
        if space:
            query += " AND f1.path LIKE ?"
            params.append(f"{space}%")
        query += " ORDER BY f1.size DESC"
        results = db.execute_query(query, params)
        return [
            {
                "id": str(row[0]),
                "path": row[1],
                "name": row[2],
                "size": row[3],
                "checksum": row[4],
                "last_modified": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "duplicate_of": row[8],
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Erreur get_duplicates: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des doublons")


@app.get("/api/spaces", response_model=List[SpaceInfo])
async def get_spaces():
    try:
        db = get_db_adapter()

        if hasattr(db, "get_spaces"):
            spaces = db.get_spaces()
        else:
            # Compatibilité rétroactive: certains doubles de test/anciens adaptateurs
            # n'exposent que execute_query. On reconstruit alors la liste des espaces.
            paths = db.execute_query("SELECT path FROM files WHERE path IS NOT NULL")
            spaces_map: Dict[str, Dict[str, Any]] = {}
            for row in paths:
                raw_path = row[0] if row else None
                if not raw_path:
                    continue
                prefix = extract_space_prefix(raw_path)
                if not prefix:
                    continue
                if prefix not in spaces_map:
                    spaces_map[prefix] = {
                        "name": prefix.replace("/", "").replace("\\", "") or prefix,
                        "path_prefix": prefix,
                        "file_count": 0,
                    }
                spaces_map[prefix]["file_count"] += 1
            spaces = sorted(spaces_map.values(), key=lambda item: item["name"].lower())

        return [SpaceInfo(**space) for space in spaces]
    except Exception as e:
        logger.error(f"Erreur get_spaces: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des espaces")


@app.get("/api/db-explain", response_model=ExplainPlan)
async def get_db_explain(query_name: str = "files_list", analyze: bool = True):
    if query_name not in EXPLAIN_QUERIES:
        raise HTTPException(status_code=400, detail=f"query_name invalide. Valeurs autorisées: {', '.join(EXPLAIN_QUERIES.keys())}")

    try:
        db = get_db_adapter()
        if analyze:
            db.execute_query("ANALYZE")
        explain_query = f"EXPLAIN QUERY PLAN {EXPLAIN_QUERIES[query_name]}"
        results = db.execute_query(explain_query)
        plan_lines = [" | ".join(str(cell) for cell in row) for row in results]
        return ExplainPlan(query_name=query_name, analyze=analyze, plan=plan_lines)
    except Exception as e:
        logger.error(f"Erreur get_db_explain: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du plan EXPLAIN")


@app.get("/api/crawl-configs", response_model=List[CrawlConfigPublic])
async def list_crawl_configs():
    try:
        db = get_db_adapter()
        return [CrawlConfigPublic(**config) for config in db.list_crawl_configs()]
    except Exception as e:
        logger.error(f"Erreur list_crawl_configs: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement des configurations de crawl")


@app.post("/api/crawl-configs", response_model=CrawlConfigPublic)
async def create_crawl_config(payload: CrawlConfigCreate):
    try:
        db = get_db_adapter()
        config = db.create_crawl_config(payload)
        return CrawlConfigPublic(**config)
    except Exception as e:
        logger.error(f"Erreur create_crawl_config: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la configuration de crawl")


@app.post("/api/crawls/start", response_model=CrawlRun)
async def start_crawl(payload: CrawlStartRequest):
    try:
        db = get_db_adapter()
        run = db.start_crawl(payload.config_id)
        if not run:
            raise HTTPException(status_code=404, detail="Configuration de crawl introuvable")
        return CrawlRun(**run)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur start_crawl: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du lancement du crawl")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(5)
            try:
                db = get_db_adapter()
                stats = db.get_statistics()
                message = WebSocketMessage(type="stats_update", data=stats, timestamp=datetime.now())
                await manager.send_personal_message(message.json(), websocket)
            except Exception as e:
                logger.error(f"Erreur WebSocket stats: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html><head><title>OpenIndex API</title><meta charset="utf-8"></head>
    <body><h1>🚀 OpenIndex API</h1><p><a href="/docs">Swagger UI</a></p></body></html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
