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
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
try:
    from src.versioning import get_current_version
except ModuleNotFoundError:  # pragma: no cover
    from versioning import get_current_version

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None
    SimpleConnectionPool = None


APP_VERSION = get_current_version()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de FastAPI
app = FastAPI(
    title="OpenIndex API",
    description="API moderne pour l'exploration SMB",
    version=APP_VERSION,
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
    last_modified: Optional[datetime] = None
    is_directory: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    config_id: Optional[str] = None


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


class CrawlConnectionUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    domain: Optional[str] = None


class CrawlConfigUpdate(BaseModel):
    name: str
    domain_zone: str
    start_path: str
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    connection: CrawlConnectionUpdate


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


class CrawlRunHistoryItem(BaseModel):
    run_id: str
    config_id: str
    config_name: str
    domain_zone: str
    start_path: str
    status: str
    triggered_at: str


class CrawlRunActionResult(BaseModel):
    run_id: str
    status: str


class MonitoringSummary(BaseModel):
    total_configs: int
    total_runs: int
    queued_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int
    latest_run_status: str
    latest_run_config_name: str
    latest_run_triggered_at: str
    progress_percent: float


class CrawlOverview(BaseModel):
    monitoring: MonitoringSummary
    configs: List[CrawlConfigPublic]
    recent_runs: List[CrawlRunHistoryItem]


class SystemStatus(BaseModel):
    app_version: str
    commit_hash: str
    build_date: str
    timezone: str
    license_label: str
    license_owner: str
    repository_url: str
    newer_version_available: bool
    newest_version_url: Optional[str] = None


class QueueIndicator(BaseModel):
    key: str
    label: str
    value: int
    detail: str


class ProgressIndicator(BaseModel):
    key: str
    label: str
    value: str
    detail: str


class CrawlerRuntime(BaseModel):
    active: bool
    idle: bool = False
    latest_status: str
    latest_config_name: str
    progress_percent: Optional[float] = None
    processed_bytes: int = 0
    discovered_bytes: int = 0
    discovered_files: int = 0
    discovered_directories: int = 0
    large_files_detected: int = 0
    large_files_bytes: int = 0
    progress_hint: str = ""
    last_activity_at: Optional[str] = None
    progress_indicators: List[ProgressIndicator]
    queue_indicators: List[QueueIndicator]
    log_lines: List[str]
    log_source: str


STALE_RUN_TIMEOUT_SECONDS = int(os.getenv("OPENINDEX_CRAWLER_STALE_TIMEOUT_SECONDS", "1200"))
ACTIVE_RUN_STATUSES = {"queued", "pending", "running", "in_progress", "cancelling"}


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
        self._pool = None

    def _get_pool(self):
        if self._pool is None:
            if SimpleConnectionPool is None:
                raise RuntimeError("SimpleConnectionPool indisponible")
            self._pool = SimpleConnectionPool(1, 5, **self.config)
        return self._pool

    @contextmanager
    def get_connection(self):
        conn = self._get_pool().getconn()
        try:
            yield conn
        finally:
            self._get_pool().putconn(conn)

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[tuple]:
        params = params or []
        pg_query = query.replace("?", "%s")
        if pg_query.startswith("EXPLAIN QUERY PLAN"):
            pg_query = pg_query.replace("EXPLAIN QUERY PLAN", "EXPLAIN", 1)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(pg_query, params)
                return cursor.fetchall()

    def resolve_space_config_id(self, space: Optional[str]) -> Optional[str]:
        if not space:
            return None

        rows = self.execute_query(
            """
            SELECT id::text
            FROM crawl_configs
            WHERE start_path = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [space],
        )
        if not rows:
            return None
        return rows[0][0]

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
            config_id = self.resolve_space_config_id(space)
            if config_id:
                query += " WHERE crawl_config_id::text = %s"
                params.append(config_id)
            else:
                query += " WHERE path LIKE %s"
                params.append(f"{space}%")

        with self.get_connection() as conn:
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
        self.ensure_crawl_tables()
        config_rows = self.execute_query(
            """
            SELECT
                c.id::text,
                c.name,
                c.start_path,
                COUNT(f.id)
            FROM crawl_configs c
            LEFT JOIN files f ON f.crawl_config_id = c.id
            GROUP BY c.id, c.name, c.start_path
            ORDER BY c.name ASC, c.created_at DESC
            """
        )
        if config_rows:
            return [
                {
                    "config_id": row[0],
                    "name": row[1],
                    "path_prefix": row[2],
                    "file_count": row[3] or 0,
                }
                for row in config_rows
            ]

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
                    "config_id": None,
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
            """
            ALTER TABLE files
            ADD COLUMN IF NOT EXISTS crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
            """,
            "CREATE INDEX IF NOT EXISTS idx_files_crawl_config_id ON files(crawl_config_id)",
        ]
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute(
                    """
                    UPDATE files AS f
                    SET crawl_config_id = matched.config_id
                    FROM (
                        SELECT DISTINCT ON (f.id)
                            f.id AS file_id,
                            c.id AS config_id
                        FROM files AS f
                        JOIN crawl_configs AS c
                          ON f.path LIKE c.start_path || '%%'
                        WHERE f.crawl_config_id IS NULL
                        ORDER BY f.id, LENGTH(c.start_path) DESC, c.created_at DESC
                    ) AS matched
                    WHERE f.id = matched.file_id
                      AND f.crawl_config_id IS NULL
                    """
                )
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
        with self.get_connection() as conn:
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

    def update_crawl_config(self, config_id: str, payload: CrawlConfigUpdate) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if payload.connection.password:
                    cursor.execute(
                        """
                        UPDATE crawl_configs
                        SET name = %s,
                            domain_zone = %s,
                            start_path = %s,
                            include_paths = %s,
                            exclude_paths = %s,
                            connection_username = %s,
                            connection_password = %s,
                            connection_domain = %s
                        WHERE id::text = %s
                        RETURNING id::text, name, domain_zone, start_path,
                                  include_paths, exclude_paths,
                                  connection_username, connection_domain,
                                  created_at::text
                        """,
                        [
                            payload.name,
                            payload.domain_zone,
                            payload.start_path,
                            payload.include_paths,
                            payload.exclude_paths,
                            payload.connection.username,
                            payload.connection.password,
                            payload.connection.domain,
                            config_id,
                        ],
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE crawl_configs
                        SET name = %s,
                            domain_zone = %s,
                            start_path = %s,
                            include_paths = %s,
                            exclude_paths = %s,
                            connection_username = %s,
                            connection_domain = %s
                        WHERE id::text = %s
                        RETURNING id::text, name, domain_zone, start_path,
                                  include_paths, exclude_paths,
                                  connection_username, connection_domain,
                                  created_at::text
                        """,
                        [
                            payload.name,
                            payload.domain_zone,
                            payload.start_path,
                            payload.include_paths,
                            payload.exclude_paths,
                            payload.connection.username,
                            payload.connection.domain,
                            config_id,
                        ],
                    )
                row = cursor.fetchone()
            conn.commit()

        if not row:
            return None

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
        existing_run = self.execute_query(
            """
            SELECT id::text, status
            FROM crawl_runs
            WHERE config_id::text = %s
              AND LOWER(status) IN ('queued', 'pending', 'running', 'in_progress', 'cancelling')
            ORDER BY triggered_at DESC
            LIMIT 1
            """,
            [config_id],
        )
        if existing_run:
            raise ValueError(
                f"Une exploration est deja active pour cette configuration ({existing_run[0][1]})."
            )

        query = """
            INSERT INTO crawl_runs (config_id, status)
            SELECT id, 'queued'
            FROM crawl_configs
            WHERE id::text = %s
            RETURNING id::text, config_id::text, status, triggered_at::text
        """
        with self.get_connection() as conn:
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

    def get_crawl_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(
            """
            SELECT
                r.id::text,
                r.config_id::text,
                r.status,
                r.triggered_at::text,
                c.name,
                c.domain_zone,
                c.start_path,
                c.connection_username,
                c.connection_password,
                c.connection_domain
            FROM crawl_runs r
            JOIN crawl_configs c ON c.id = r.config_id
            WHERE r.id::text = %s
            LIMIT 1
            """,
            [run_id],
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "run_id": row[0],
            "config_id": row[1],
            "status": row[2],
            "triggered_at": row[3],
            "name": row[4],
            "domain_zone": row[5],
            "start_path": row[6],
            "connection_username": row[7],
            "connection_password": row[8],
            "connection_domain": row[9],
        }

    def request_stop_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE crawl_runs
                    SET status = CASE
                        WHEN LOWER(status) IN ('queued', 'pending') THEN 'cancelled'
                        WHEN LOWER(status) IN ('running', 'in_progress') THEN 'cancelling'
                        ELSE status
                    END
                    WHERE id::text = %s
                    RETURNING id::text, status
                    """,
                    [run_id],
                )
                row = cursor.fetchone()
            conn.commit()

        if not row:
            return None
        return {"run_id": row[0], "status": row[1]}

    def delete_run(self, run_id: str) -> bool:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM crawl_runs
                    WHERE id::text = %s
                      AND LOWER(status) NOT IN ('running', 'in_progress', 'cancelling')
                    RETURNING id::text
                    """,
                    [run_id],
                )
                row = cursor.fetchone()
            conn.commit()
        return bool(row)

    def fail_active_runs(self) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE crawl_runs
                    SET status = 'failed'
                    WHERE LOWER(status) IN ('running', 'in_progress', 'cancelling')
                    """
                )
                updated = cursor.rowcount or 0
            conn.commit()
        return updated

    def get_monitoring_summary(self) -> Dict[str, Any]:
        total_configs = self.execute_query("SELECT COUNT(*) FROM crawl_configs")[0][0] or 0
        total_runs = self.execute_query("SELECT COUNT(*) FROM crawl_runs")[0][0] or 0

        status_rows = self.execute_query(
            "SELECT LOWER(status), COUNT(*) FROM crawl_runs GROUP BY LOWER(status)"
        )
        status_counts = {str(row[0] or ""): row[1] or 0 for row in status_rows}

        latest_run_rows = self.execute_query(
            """
            SELECT r.status, c.name, r.triggered_at::text
            FROM crawl_runs r
            JOIN crawl_configs c ON c.id = r.config_id
            ORDER BY r.triggered_at DESC
            LIMIT 1
            """
        )

        latest_run_status = "Aucun run"
        latest_run_config_name = "-"
        latest_run_triggered_at = "-"
        if latest_run_rows:
            latest_run_status = latest_run_rows[0][0] or "unknown"
            latest_run_config_name = latest_run_rows[0][1] or "-"
            latest_run_triggered_at = latest_run_rows[0][2] or "-"

        completed_runs = (
            status_counts.get("completed", 0)
            + status_counts.get("done", 0)
            + status_counts.get("success", 0)
        )
        failed_runs = status_counts.get("failed", 0) + status_counts.get("error", 0)
        running_runs = (
            status_counts.get("running", 0)
            + status_counts.get("in_progress", 0)
        )
        queued_runs = status_counts.get("queued", 0) + status_counts.get("pending", 0)

        progress_percent = 0.0
        if total_runs > 0:
            progress_percent = round((completed_runs / total_runs) * 100, 1)

        return {
            "total_configs": total_configs,
            "total_runs": total_runs,
            "queued_runs": queued_runs,
            "running_runs": running_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "latest_run_status": latest_run_status,
            "latest_run_config_name": latest_run_config_name,
            "latest_run_triggered_at": latest_run_triggered_at,
            "progress_percent": progress_percent,
        }

    def list_recent_crawl_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self.execute_query(
            """
            SELECT
                r.id::text,
                r.config_id::text,
                c.name,
                c.domain_zone,
                c.start_path,
                r.status,
                r.triggered_at::text
            FROM crawl_runs r
            JOIN crawl_configs c ON c.id = r.config_id
            ORDER BY r.triggered_at DESC
            LIMIT %s
            """,
            [limit],
        )
        return [
            {
                "run_id": row[0],
                "config_id": row[1],
                "config_name": row[2],
                "domain_zone": row[3],
                "start_path": row[4],
                "status": row[5],
                "triggered_at": row[6],
            }
            for row in rows
        ]

    def get_crawl_overview(self, limit: int = 10) -> Dict[str, Any]:
        return {
            "monitoring": self.get_monitoring_summary(),
            "configs": self.list_crawl_configs(),
            "recent_runs": self.list_recent_crawl_runs(limit=limit),
        }


# Connexion à la base de données
@lru_cache(maxsize=1)
def _build_postgres_adapter(host: str, port: int, dbname: str, user: str, password: str):
    adapter = PostgreSQLAdapter(
        {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
        }
    )
    adapter.ensure_crawl_tables()
    return adapter


def get_db_adapter():
    """Récupère l'adaptateur PostgreSQL (backend unique)."""
    backend = os.getenv("OPENINDEX_DB_BACKEND", "postgresql").strip().lower()

    if backend == "postgresql":
        if psycopg2 is None:
            raise HTTPException(status_code=500, detail="psycopg2 non disponible pour le backend PostgreSQL")

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        dbname = os.getenv("POSTGRES_DB", "openindex")
        user = os.getenv("POSTGRES_USER", "openindex_user")
        password = os.getenv("POSTGRES_PASSWORD", "openindex_secure_password")
        try:
            return _build_postgres_adapter(host, port, dbname, user, password)
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
            config_id = db.resolve_space_config_id(space) if hasattr(db, "resolve_space_config_id") else None
            if config_id:
                where_clause += " AND crawl_config_id::text = ?"
                params.append(config_id)
            else:
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
            config_id = db.resolve_space_config_id(space) if hasattr(db, "resolve_space_config_id") else None
            if config_id:
                query += " AND f1.crawl_config_id::text = ?"
                params.append(config_id)
            else:
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


def ensure_crawl_storage_ready(db: Any) -> None:
    if hasattr(db, "ensure_crawl_tables"):
        db.ensure_crawl_tables()


def _read_log_lines(log_path: Path) -> List[str]:
    if not log_path.exists() or not log_path.is_file():
        return []

    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            return [line.rstrip("\n") for line in handle.readlines()]
    except OSError:
        return []


def _build_run_log_path(base_log_path: Path, run_id: str) -> Path:
    return base_log_path.with_name(f"{base_log_path.stem}_{run_id}{base_log_path.suffix}")


def _resolve_runtime_log_path(db: Any) -> Path:
    base_log_path = Path(os.getenv("OPENINDEX_CRAWLER_LOG_PATH", "logs/smb_crawler_postgresql.log"))
    recent_runs = []
    if hasattr(db, "list_recent_crawl_runs"):
        recent_runs = db.list_recent_crawl_runs(limit=20)

    for run in recent_runs:
        run_id = run.get("run_id")
        status = (run.get("status") or "").lower()
        if not run_id or status not in ACTIVE_RUN_STATUSES:
            continue
        candidate_path = _build_run_log_path(base_log_path, run_id)
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    for run in recent_runs:
        run_id = run.get("run_id")
        if not run_id:
            continue
        candidate_path = _build_run_log_path(base_log_path, run_id)
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    return base_log_path


def _tail_log_lines(log_path: Path, limit: int = 80) -> List[str]:
    lines = _read_log_lines(log_path)
    return [_normalize_runtime_log_line(line) for line in lines[-limit:]]


def _normalize_runtime_log_line(line: str) -> str:
    if "Queues:" not in line:
        return line
    return (
        line.replace(" répertoires, ", " dossiers, ")
        .replace("Queues: Dossiers=", "Queues: Dossiers à explorer=")
        .replace(", Fichiers=", ", Dossiers à indexer=")
        .replace(", Somme de contrôle=", ", Vérification d'intégrité=")
        .replace(", Gros fichiers=", ", Gros fichiers en attente=")
    )


PROGRESS_RE = re.compile(
    r"Progression:\s*(?P<files>\d+)\s*fichiers,\s*"
    r"(?P<dirs>\d+)\s*(?:répertoires|dossiers),\s*"
    r"(?P<large_files_seen>\d+)\s*gros fichiers\s*\|\s*"
    r"Queues:\s*(?:Dossiers|Dossiers à explorer)=(?P<queue_dirs>\d+),\s*"
    r"(?:Fichiers|Dossiers à indexer)=(?P<queue_files>\d+),\s*"
    r"(?:Somme de contrôle|Fichiers à checksumer|Vérification d'intégrité)=(?P<queue_checksums>\d+),\s*"
    r"(?:Gros fichiers|Gros fichiers en attente)=(?P<queue_large>\d+)\s*\|\s*"
    r"Volume cible=(?P<target_bytes>\d+)\s*octets,\s*"
    r"Volume traité=(?P<processed_bytes>\d+)\s*octets,\s*"
    r"Volume découvert=(?P<discovered_bytes>\d+)\s*octets,\s*"
    r"Progression volume=(?P<progress_percent>\d+(?:\.\d+)?)%",
    re.IGNORECASE,
)

LOG_TIMESTAMP_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
LARGE_FILE_RE = re.compile(r"Gros fichier détecté: .*?\((?P<size>[\d,]+) bytes\)")


def _extract_progress_percent(log_lines: List[str]) -> float:
    for line in reversed(log_lines):
        match = PROGRESS_RE.search(line)
        if not match:
            continue
        return float(match.group("progress_percent"))
    return 0.0


def _extract_queue_snapshot(log_lines: List[str]) -> Dict[str, int]:
    for line in reversed(log_lines):
        match = PROGRESS_RE.search(line)
        if not match:
            continue
        return {
            "directories": int(match.group("queue_dirs")),
            "files": int(match.group("queue_files")),
            "checksums": int(match.group("queue_checksums")),
            "large_files": int(match.group("queue_large")),
        }
    return {
        "directories": 0,
        "files": 0,
        "checksums": 0,
        "large_files": 0,
    }


def _extract_volume_snapshot(log_lines: List[str]) -> Dict[str, int]:
    for line in reversed(log_lines):
        match = PROGRESS_RE.search(line)
        if not match:
            continue
        return {
            "processed_bytes": int(match.group("processed_bytes")),
            "discovered_bytes": int(match.group("discovered_bytes")),
        }
    return {
        "processed_bytes": 0,
        "discovered_bytes": 0,
    }


def _extract_runtime_metrics(log_lines: List[str]) -> Dict[str, Any]:
    for line in reversed(log_lines):
        match = PROGRESS_RE.search(line)
        if not match:
            continue
        queue_dirs = int(match.group("queue_dirs"))
        queue_files = int(match.group("queue_files"))
        queue_checksums = int(match.group("queue_checksums"))
        queue_large = int(match.group("queue_large"))
        discovered_bytes = int(match.group("discovered_bytes"))
        processed_bytes = int(match.group("processed_bytes"))
        target_bytes = int(match.group("target_bytes"))
        return {
            "discovered_files": int(match.group("files")),
            "discovered_directories": int(match.group("dirs")),
            "large_files_detected": int(match.group("large_files_seen")),
            "processed_bytes": processed_bytes,
            "discovered_bytes": discovered_bytes,
            "target_bytes": target_bytes,
            "queue_dirs": queue_dirs,
            "queue_files": queue_files,
            "queue_checksums": queue_checksums,
            "queue_large": queue_large,
            "progress_percent": float(match.group("progress_percent")),
            "progress_hint": "Le volume cible est stabilisé. La progression reflète maintenant le traitement restant.",
        }
    return {
        "discovered_files": 0,
        "discovered_directories": 0,
        "large_files_detected": 0,
        "large_files_bytes": 0,
        "processed_bytes": 0,
        "discovered_bytes": 0,
        "target_bytes": 0,
        "queue_dirs": 0,
        "queue_files": 0,
        "queue_checksums": 0,
        "queue_large": 0,
        "progress_percent": None,
        "progress_hint": "Aucune exploration active.",
        "last_activity_at": None,
    }


def _format_volume_compact(bytes_value: int) -> str:
    if bytes_value <= 0:
        return "0 o"
    if bytes_value < 1000:
        return f"{bytes_value} o"

    units = ["ko", "Mo", "Go", "To", "Po"]
    value = float(bytes_value)
    unit_index = -1

    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1

    return f"{value:.3f} {units[unit_index]}"


def _parse_db_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value or value == "-":
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _compute_rate(value: int, started_at: Optional[datetime]) -> float:
    if value <= 0 or started_at is None:
        return 0.0
    elapsed_seconds = max((datetime.now(timezone.utc) - started_at).total_seconds(), 1.0)
    return value / elapsed_seconds


def _format_rate(value_per_second: float, suffix: str = "it/s") -> str:
    if value_per_second <= 0:
        return f"0 {suffix}"
    return f"{value_per_second:.2f} {suffix}"


def _extract_last_progress_timestamp(log_lines: List[str]) -> Optional[datetime]:
    for line in reversed(log_lines):
        if not PROGRESS_RE.search(line):
            continue
        match = LOG_TIMESTAMP_RE.match(line)
        if not match:
            continue
        try:
            return datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return None


def _reconcile_stale_running_runs(db, raw_log_lines: List[str]) -> Dict[str, Any]:
    monitoring = db.get_monitoring_summary()
    if monitoring["running_runs"] <= 0:
        return monitoring

    last_activity = _extract_last_progress_timestamp(raw_log_lines)
    if last_activity is None:
        return monitoring

    stale_seconds = (datetime.utcnow() - last_activity).total_seconds()
    if stale_seconds <= STALE_RUN_TIMEOUT_SECONDS:
        return monitoring

    updated = 0
    if hasattr(db, "fail_active_runs"):
        updated = db.fail_active_runs()

    if updated:
        logger.warning(
            "Run(s) marques en echec apres %.1f s sans signal moteur recent.",
            stale_seconds,
        )
        return db.get_monitoring_summary()

    return monitoring


def _extract_large_file_metrics(raw_log_lines: List[str]) -> Dict[str, int]:
    last_run_start_index = 0
    for index, line in enumerate(raw_log_lines):
        if "Démarrage du crawl SMB avec PostgreSQL" in line:
            last_run_start_index = index

    count = 0
    total_bytes = 0
    for line in raw_log_lines[last_run_start_index:]:
        match = LARGE_FILE_RE.search(line)
        if not match:
            continue
        count += 1
        total_bytes += int(match.group("size").replace(",", ""))

    return {
        "count": count,
        "bytes": total_bytes,
    }


def _slice_current_run_log_lines(raw_log_lines: List[str]) -> List[str]:
    last_run_start_index = 0
    for index, line in enumerate(raw_log_lines):
        if "Démarrage du crawl SMB avec PostgreSQL" in line:
            last_run_start_index = index
    return raw_log_lines[last_run_start_index:]


@app.get("/api/crawl-configs", response_model=List[CrawlConfigPublic])
async def list_crawl_configs():
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        return [CrawlConfigPublic(**config) for config in db.list_crawl_configs()]
    except Exception as e:
        logger.error(f"Erreur list_crawl_configs: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement des configurations d'exploration")


@app.post("/api/crawl-configs", response_model=CrawlConfigPublic)
async def create_crawl_config(payload: CrawlConfigCreate):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        config = db.create_crawl_config(payload)
        return CrawlConfigPublic(**config)
    except Exception as e:
        logger.error(f"Erreur create_crawl_config: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la configuration d'exploration")


@app.put("/api/crawl-configs/{config_id}", response_model=CrawlConfigPublic)
async def update_crawl_config(config_id: str, payload: CrawlConfigUpdate):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        config = db.update_crawl_config(config_id, payload)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration d'exploration introuvable")
        return CrawlConfigPublic(**config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update_crawl_config: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour de la configuration d'exploration")


@app.post("/api/crawls/start", response_model=CrawlRun)
async def start_crawl(payload: CrawlStartRequest):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        run = db.start_crawl(payload.config_id)
        if not run:
            raise HTTPException(status_code=404, detail="Configuration d'exploration introuvable")
        return CrawlRun(**run)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur start_crawl: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du lancement de l'exploration")


@app.post("/api/crawls/{run_id}/stop", response_model=CrawlRunActionResult)
async def stop_crawl_run(run_id: str):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        result = db.request_stop_run(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="Run d'exploration introuvable")
        return CrawlRunActionResult(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stop_crawl_run: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'arrêt de l'exploration")


@app.delete("/api/crawls/{run_id}", response_model=CrawlRunActionResult)
async def delete_crawl_run(run_id: str):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        if not db.delete_run(run_id):
            raise HTTPException(status_code=409, detail="Suppression impossible pour un run actif ou introuvable")
        return CrawlRunActionResult(run_id=run_id, status="deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_crawl_run: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du run")


@app.get("/api/monitoring", response_model=MonitoringSummary)
async def get_monitoring_summary():
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        raw_log_lines = _read_log_lines(_resolve_runtime_log_path(db))
        summary = _reconcile_stale_running_runs(db, raw_log_lines)
        return MonitoringSummary(**summary)
    except Exception as e:
        logger.error(f"Erreur get_monitoring_summary: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du monitoring")


@app.get("/api/crawls/overview", response_model=CrawlOverview)
async def get_crawl_overview(limit: int = 10):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        _reconcile_stale_running_runs(
            db,
            _read_log_lines(_resolve_runtime_log_path(db)),
        )
        overview = db.get_crawl_overview(limit=limit)
        return CrawlOverview(
            monitoring=MonitoringSummary(**overview["monitoring"]),
            configs=[CrawlConfigPublic(**config) for config in overview["configs"]],
            recent_runs=[CrawlRunHistoryItem(**run) for run in overview["recent_runs"]],
        )
    except Exception as e:
        logger.error(f"Erreur get_crawl_overview: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement de la vue d'ensemble des explorations")


@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    try:
        version = os.getenv("OPENINDEX_APP_VERSION", app.version)
        commit_hash = os.getenv("OPENINDEX_BUILD_COMMIT", "dev")
        build_date = os.getenv("OPENINDEX_BUILD_DATE", datetime.now().date().isoformat())
        timezone_name = os.getenv("OPENINDEX_TIMEZONE") or os.getenv("TZ") or "UTC"
        repository_url = os.getenv("OPENINDEX_REPOSITORY_URL", "https://github.com/lamacheref/openindex")
        newer_version_available = os.getenv("OPENINDEX_NEWER_VERSION_AVAILABLE", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        newest_version_url = os.getenv("OPENINDEX_NEWEST_VERSION_URL") or repository_url

        return SystemStatus(
            app_version=version,
            commit_hash=commit_hash,
            build_date=build_date,
            timezone=timezone_name,
            license_label="Licence",
            license_owner="Copyright 2026 SMIDEN",
            repository_url=repository_url,
            newer_version_available=newer_version_available,
            newest_version_url=newest_version_url if newer_version_available else None,
        )
    except Exception as e:
        logger.error(f"Erreur get_system_status: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du statut système")


@app.get("/api/crawler/runtime", response_model=CrawlerRuntime)
async def get_crawler_runtime(log_limit: int = 80):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        log_path = _resolve_runtime_log_path(db)
        raw_log_lines = _read_log_lines(log_path)
        current_run_log_lines = _slice_current_run_log_lines(raw_log_lines)
        monitoring = _reconcile_stale_running_runs(db, current_run_log_lines)
        log_lines = [_normalize_runtime_log_line(line) for line in current_run_log_lines[-log_limit:]]
        runtime_metrics = _extract_runtime_metrics(log_lines)
        large_file_metrics = _extract_large_file_metrics(current_run_log_lines)
        queue_snapshot = _extract_queue_snapshot(log_lines)
        last_activity = _extract_last_progress_timestamp(current_run_log_lines)
        has_running_run = monitoring["running_runs"] > 0
        started_at = _parse_db_timestamp(monitoring.get("latest_run_triggered_at"))
        idle = False
        if has_running_run and last_activity is not None:
            idle = (datetime.utcnow() - last_activity).total_seconds() > 300
        elif has_running_run and not log_lines:
            idle = True

        files_rate = _compute_rate(runtime_metrics["discovered_files"], started_at) if has_running_run else 0.0
        directories_rate = _compute_rate(runtime_metrics["discovered_directories"], started_at) if has_running_run else 0.0
        processed_volume_rate = _compute_rate(runtime_metrics["processed_bytes"], started_at) if has_running_run else 0.0

        queue_indicators = [
            QueueIndicator(
                key="directories",
                label="Dossiers à explorer",
                value=queue_snapshot["directories"],
                detail="Dossiers à explorer",
            ),
            QueueIndicator(
                key="files",
                label="Dossiers à indexer",
                value=queue_snapshot["files"],
                detail="Dossiers déjà découverts, en attente d'écriture",
            ),
            QueueIndicator(
                key="checksums",
                label="Vérification d'intégrité",
                value=queue_snapshot["checksums"],
                detail="Fichiers normaux en attente de vérification d'intégrité",
            ),
            QueueIndicator(
                key="large_files",
                label="Gros fichiers en attente",
                value=queue_snapshot["large_files"],
                detail="Fichiers lourds en attente de calcul",
            ),
        ]

        progress_indicators = [
            ProgressIndicator(
                key="discovered_files",
                label="Fichiers",
                value=f"{runtime_metrics['discovered_files']:,}".replace(",", " "),
                detail=f"Fichiers traités ({_format_rate(files_rate)})",
            ),
            ProgressIndicator(
                key="discovered_directories",
                label="Dossiers",
                value=f"{runtime_metrics['discovered_directories']:,}".replace(",", " "),
                detail=f"Dossiers parcourus ({_format_rate(directories_rate)})",
            ),
            ProgressIndicator(
                key="processed_volume",
                label="Volume traité",
                value=_format_volume_compact(runtime_metrics["processed_bytes"]),
                detail=f"Volume vérifié ({_format_volume_compact(int(processed_volume_rate))}/s)",
            ),
            ProgressIndicator(
                key="integrity_backlog",
                label="Vérification d'intégrité",
                value=f"{queue_snapshot['checksums']:,}".replace(",", " "),
                detail="Fichiers en attente",
            ),
            ProgressIndicator(
                key="large_files_detected",
                label="Gros fichiers",
                value=f"{(large_file_metrics['count'] or runtime_metrics['large_files_detected']):,}".replace(",", " "),
                detail=(
                    f"fichiers ({_format_volume_compact(large_file_metrics['bytes'])} soit "
                    f"{((large_file_metrics['bytes'] / runtime_metrics['discovered_bytes']) * 100):.2f} % du total)"
                    if runtime_metrics["discovered_bytes"] > 0
                    else "fichiers (0 o soit 0.00 % du total)"
                ),
            ),
        ]

        return CrawlerRuntime(
            active=has_running_run and not idle,
            idle=idle,
            latest_status=monitoring["latest_run_status"],
            latest_config_name=monitoring["latest_run_config_name"],
            progress_percent=runtime_metrics["progress_percent"] if monitoring["running_runs"] > 0 else monitoring["progress_percent"],
            processed_bytes=runtime_metrics["processed_bytes"],
            discovered_bytes=runtime_metrics["discovered_bytes"],
            discovered_files=runtime_metrics["discovered_files"],
            discovered_directories=runtime_metrics["discovered_directories"],
            large_files_detected=large_file_metrics["count"] or runtime_metrics["large_files_detected"],
            large_files_bytes=large_file_metrics["bytes"],
            progress_hint=(
                "Aucun signal moteur récent. Le run paraît idle et doit être vérifié."
                if idle
                else runtime_metrics["progress_hint"]
            ),
            last_activity_at=last_activity.isoformat() if last_activity else None,
            progress_indicators=progress_indicators,
            queue_indicators=queue_indicators,
            log_lines=log_lines,
            log_source=str(log_path),
        )
    except Exception as e:
        logger.error(f"Erreur get_crawler_runtime: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du runtime explorateur")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(5)
            try:
                db = get_db_adapter()
                stats = db.get_statistics()
                await manager.send_personal_message(
                    WebSocketMessage(type="stats_update", data=stats, timestamp=datetime.now()).json(),
                    websocket,
                )
                if hasattr(db, "get_monitoring_summary"):
                    await manager.send_personal_message(
                        WebSocketMessage(
                            type="monitoring_update",
                            data=db.get_monitoring_summary(),
                            timestamp=datetime.now(),
                        ).json(),
                        websocket,
                    )
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
