"""
API FastAPI pour OpenIndex
Backend moderne avec WebSocket et monitoring temps réel
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import asyncio
import hashlib
import html
import http.client
import io
import json
import logging
import mimetypes
import os
import re
import socket
import shutil
import sys
import time
import base64
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree

try:
    import smbclient
except ModuleNotFoundError:  # pragma: no cover
    smbclient = None

try:
    from backend.src.smb_mount_manager import smb_to_local_path, ensure_mounted, get_mount_manager, SMBMountManager
except ModuleNotFoundError:  # pragma: no cover
    try:
        from smb_mount_manager import smb_to_local_path, ensure_mounted, get_mount_manager, SMBMountManager
    except ModuleNotFoundError:
        smb_to_local_path = None
        ensure_mounted = None
        get_mount_manager = None
        SMBMountManager = None

try:
    import openpyxl
except ModuleNotFoundError:  # pragma: no cover
    openpyxl = None
try:
    from backend.src.versioning import get_current_version
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
LOG_LEVEL = os.getenv("OPENINDEX_LOG_LEVEL", "INFO").strip().upper()
class _PlainInfoFormatter(logging.Formatter):
    _RESET = '\033[0m'
    _YELLOW = '\033[33m'
    _RED = '\033[31m'
    def format(self, record):
        level = record.levelname
        if record.levelno == logging.WARNING:
            record.levelname = f"{self._YELLOW}{level}{self._RESET}"
        elif record.levelno >= logging.ERROR:
            record.levelname = f"{self._RED}{level}{self._RESET}"
        return super().format(record)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_PlainInfoFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
))
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[_handler]
)
logger = logging.getLogger("openindex.api")

# Initialisation de FastAPI
app = FastAPI(
    title="OpenIndex API",
    description="API moderne pour l'exploration SMB",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Inclusion du router pour les artefacts (T-ART-01)
from backend.src.api.artefacts_router import router as artefacts_router
app.include_router(artefacts_router)

# Inclusion du router pour les détails des doublons (T-ART-02)
from backend.src.api.duplicate_details_router import router as duplicate_details_router
app.include_router(duplicate_details_router)

# Inclusion du router pour les filtres configurables (T-ART-03)
from backend.src.api.artefact_filters_router import router as artefact_filters_router
app.include_router(artefact_filters_router)

# Inclusion du router pour le service d'indexation (Indexer Worker)
from backend.src.api.indexer_router import router as indexer_router
app.include_router(indexer_router)

# Inclusion du router pour les schedules d'indexation (T-INDEX-01)
from backend.src.api.indexer_schedule_router import router as indexer_schedule_router
app.include_router(indexer_schedule_router)

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


class ExplorerItem(BaseModel):
    path: str
    name: str
    is_directory: bool
    size: Optional[int] = None
    last_modified: Optional[datetime] = None
    created_at: Optional[datetime] = None
    extension: Optional[str] = None
    crawl_config_id: Optional[str] = None
    has_duplicates: bool = False
    duplicate_count: int = 0
    is_duplicate: bool = False
    is_large: bool = False
    is_old: bool = False
    is_garbage: bool = False
    has_flagged_files: bool = False


class ArchiveFileRequest(BaseModel):
    source_path: str
    target_directory_path: str
    mode: str = Field(pattern="^(copy|move)$")
    overwrite: bool = False
    leave_link: bool = False


class ArchiveFileResult(BaseModel):
    source_path: str
    target_path: str
    mode: str
    source_deleted: bool
    link_path: Optional[str] = None
    checksum_verified: bool = False
    checksum: Optional[str] = None


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
    total_size: int = 0
    config_id: Optional[str] = None
    is_archive: bool = False
    linked_archive_config_id: Optional[str] = None
    linked_archive_space: Optional[str] = None


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


def _normalize_unc_path(v: str) -> str:
    if not v.startswith('//'):
        return v
    prefix = '//'
    rest = v[2:].lstrip('/')
    rest = '/'.join(p for p in rest.split('/') if p)
    return prefix + rest


class CrawlConfigCreate(BaseModel):
    name: str
    domain_zone: str
    start_path: str
    is_archive: bool = False
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    max_depth: int = 5
    linked_archive_config_id: Optional[str] = None
    connection: CrawlConnectionConfig

    @field_validator('start_path')
    @classmethod
    def normalize_start_path(cls, v):
        return _normalize_unc_path(v)


class CrawlConnectionUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    domain: Optional[str] = None


class CrawlConfigUpdate(BaseModel):
    name: str
    domain_zone: str
    start_path: str
    is_archive: bool = False
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    max_depth: int = 5
    linked_archive_config_id: Optional[str] = None
    connection: CrawlConnectionUpdate

    @field_validator('start_path')
    @classmethod
    def normalize_start_path(cls, v):
        return _normalize_unc_path(v)


class CrawlConfigPublic(BaseModel):
    id: str
    name: str
    domain_zone: str
    start_path: str
    is_archive: bool = False
    include_paths: List[str]
    exclude_paths: List[str]
    max_depth: int = 5
    linked_archive_config_id: Optional[str] = None
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
    build_timestamp: str = ""
    env_type: str = "DEV"
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
    status_label: str = ""
    progress_percent: Optional[float] = None
    processed_bytes: int = 0
    discovered_bytes: int = 0
    discovered_files: int = 0
    discovered_directories: int = 0
    large_files_detected: int = 0
    large_files_bytes: int = 0
    progress_hint: str = ""
    last_activity_at: Optional[str] = None
    last_engine_signal_at: Optional[str] = None
    db_write_active: bool = False
    db_recent_writes: int = 0
    db_last_write_at: Optional[str] = None
    db_activity_hint: str = ""
    activity_warning: str = ""
    progress_indicators: List[ProgressIndicator]
    queue_indicators: List[QueueIndicator]
    log_lines: List[str]
    log_source: str


class OperationalCheck(BaseModel):
    key: str
    label: str
    status: str
    detail: str


class OperationalIncident(BaseModel):
    key: str
    severity: str
    summary: str
    detail: str
    action: str


class OperationsStatus(BaseModel):
    status: str
    generated_at: str
    system_status: SystemStatus
    monitoring: MonitoringSummary
    runtime: CrawlerRuntime
    checks: List[OperationalCheck]
    incidents: List[OperationalIncident]


# ============================================================
# T-ARCH-01: Archive Queue Models
# ============================================================

class ArchiveJobType(str, Enum):
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"


class ArchiveJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArchiveJobCreate(BaseModel):
    job_type: ArchiveJobType = ArchiveJobType.COPY
    source_path: str
    dest_path: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)


class ArchiveJobResponse(BaseModel):
    id: str
    job_type: str
    source_path: str
    dest_path: Optional[str]
    status: str
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    source_size: Optional[int]
    bytes_transferred: int


class ArchiveJobList(BaseModel):
    jobs: List[ArchiveJobResponse]
    total: int


class ArchiveJobStats(BaseModel):
    pending: int
    running: int
    completed: int
    failed: int
    cancelled: int
    total_size_pending: int
    total_size_transferred: int


class ArchiveJobActionResult(BaseModel):
    job_id: str
    success: bool
    message: str


STALE_RUN_TIMEOUT_SECONDS = int(os.getenv("OPENINDEX_CRAWLER_STALE_TIMEOUT_SECONDS", "1200"))
ACTIVE_RUN_STATUSES = {"queued", "pending", "running", "in_progress", "cancelling"}
RUNNING_RUN_STATUSES = {"running", "in_progress"}
DOCKER_SOCKET_PATH = os.getenv("OPENINDEX_DOCKER_SOCKET_PATH", "/var/run/docker.sock")
CRAWLER_CONTAINER_NAME = os.getenv("OPENINDEX_CRAWLER_CONTAINER_NAME", "").strip()
DEFAULT_CRAWLER_CONTAINER_NAMES = ("openindex-crawler", "openindex-crawler-preprod")
CRAWLER_FORCE_KILL_DELAY_SECONDS = int(os.getenv("OPENINDEX_CRAWLER_FORCE_KILL_DELAY_SECONDS", "15"))


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 10.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def extract_space_prefix(path: str) -> Optional[str]:
    r"""
    Extract space prefix from file path, handling various formats including PKI paths.
    
    Examples:
        \\server\share\folder\file.txt -> \\server\\share
        /mount/share/folder/file.txt -> /mount
        C:\\data\\file.txt -> C:
        /pki/certs/server.crt -> /pki
        server/share/folder -> server (relative path)
    """
    normalized = path.strip()
    if not normalized:
        return None

    # Handle Windows UNC paths (\\server\share...)
    if normalized.startswith("\\"):
        parts = [part for part in normalized.split("\\") if part]
        if len(parts) >= 2:
            return f"\\{parts[0]}\\{parts[1]}"
        elif len(parts) == 1:
            return f"\\{parts[0]}\\"
        return None

    # Handle Unix absolute paths (/path/to/file)
    if normalized.startswith("/"):
        parts = [part for part in normalized.split("/") if part]
        if parts:
            return f"/{parts[0]}"
        return "/"

    # Handle Windows drive letters (C:\path\to\file)
    if len(normalized) >= 2 and normalized[1] == ':':
        drive_letter = normalized[:2].upper()
        return drive_letter

    # Handle relative paths (server/share or path/to/file)
    parts = [part for part in normalized.replace("\\", "/").split("/") if part]
    if parts:
        # For potential PKI paths like "pki/certs", return "pki"
        # For server/share patterns, return the first part
        return parts[0]

    return None

class PostgreSQLAdapter:
    """Adaptateur PostgreSQL minimal pour l'API."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._pool = None
        self.logger = logging.getLogger(__name__)

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

    def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        fetch: bool = True,
        commit: bool = False,
    ) -> List[tuple]:
        params = params or []
        pg_query = query.replace("?", "%s")
        if pg_query.startswith("EXPLAIN QUERY PLAN"):
            pg_query = pg_query.replace("EXPLAIN QUERY PLAN", "EXPLAIN", 1)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(pg_query, params)
                rows: List[tuple] = []
                if fetch and cursor.description is not None:
                    rows = cursor.fetchall()
                if commit or not fetch or cursor.description is None:
                    conn.commit()
                return rows

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
        space_id = self._resolve_space_id_from_path(space) if space else None

        file_query = """
            SELECT COUNT(*),
                   COALESCE(SUM(CASE WHEN is_duplicate THEN 1 ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN NOT is_duplicate AND NOT is_deleted THEN size ELSE 0 END), 0)
            FROM indexed_files_optimized
            WHERE NOT is_deleted
        """
        dir_query = "SELECT COUNT(*) FROM directories"
        file_params: List[Any] = []
        dir_params: List[Any] = []

        if space_id:
            file_query += " AND space_id::text = %s"
            file_params.append(space_id)
            dir_query += " WHERE space_id::text = %s"
            dir_params.append(space_id)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(file_query, file_params)
                file_row = cursor.fetchone() or (0, 0, 0)
                cursor.execute(dir_query, dir_params)
                dir_row = cursor.fetchone() or (0,)

        return {
            "total_files": file_row[0] or 0,
            "total_directories": dir_row[0] or 0,
            "total_size": file_row[2] or 0,
            "duplicate_files": file_row[1] or 0,
            "crawl_duration": None,
        }

    def get_files_by_type(self, space: Optional[str] = None) -> List[Dict[str, Any]]:
        space_id = self._resolve_space_id_from_path(space) if space else None
        query = """
            SELECT
              CASE
                WHEN LTRIM(LOWER(extension), '.') IN ('jpg','jpeg','png','gif','bmp','webp','svg','ico','tiff','tif') THEN 'images'
                WHEN LTRIM(LOWER(extension), '.') IN ('pdf','doc','docx','xls','xlsx','xlsm','ppt','pptx','odt','ods','odp','txt','csv','rtf','md','log') THEN 'documents'
                WHEN LTRIM(LOWER(extension), '.') IN ('zip','rar','7z','tar','gz','bz2','xz','zst','tgz') THEN 'archives'
                WHEN LTRIM(LOWER(extension), '.') IN ('mp4','avi','mkv','mov','wmv','flv','webm') THEN 'vidéos'
                WHEN LTRIM(LOWER(extension), '.') IN ('mp3','wav','flac','ogg','aac','wma') THEN 'audio'
                WHEN LTRIM(LOWER(extension), '.') IN ('py','js','ts','html','htm','css','php','java','c','cpp','h','sql','sh','yaml','json','xml','yml','rb','go','rs','db') THEN 'code'
                ELSE 'autres'
              END as category,
              COUNT(*) as count,
              COALESCE(SUM(CASE WHEN NOT is_duplicate AND NOT is_deleted THEN size ELSE 0 END), 0) as total_size
            FROM indexed_files_optimized
            WHERE NOT is_deleted
        """
        params: List[Any] = []
        if space_id:
            query += " AND space_id::text = %s"
            params.append(space_id)
        query += " GROUP BY category ORDER BY total_size DESC"

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

        return [
            {"category": r[0], "count": r[1] or 0, "total_size": r[2] or 0}
            for r in rows
        ]

    def get_hash_progress(self, space: Optional[str] = None) -> Dict[str, Any]:
        space_id = self._resolve_space_id_from_path(space) if space else None

        file_query = """
            SELECT
              COUNT(*) as total,
              COUNT(CASE WHEN hash_xxh64 IS NOT NULL AND hash_xxh64 != '' THEN 1 END) as hashed
            FROM indexed_files_optimized
            WHERE NOT is_deleted
        """
        scan_query = """
            SELECT MAX(started_at)
            FROM indexer_jobs ij
            JOIN crawl_configs cc ON cc.id = ij.config_id
        """
        file_params: List[Any] = []
        scan_params: List[Any] = []

        if space_id:
            file_query += " AND space_id::text = %s"
            file_params.append(space_id)
            scan_query += " WHERE cc.start_path = %s"
            scan_params.append(space)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(file_query, file_params)
                row = cursor.fetchone()
                cursor.execute(scan_query, scan_params)
                scan_row = cursor.fetchone()

        return {
            "total": row[0] or 0,
            "hashed": row[1] or 0,
            "last_hash_scan": scan_row[0].isoformat() if scan_row and scan_row[0] else None,
        }

    def _resolve_space_id_from_path(self, path: str) -> Optional[str]:
        path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', path) if path else None
        if path_match:
            rows = self.execute_query(
                "SELECT id::text FROM smb_spaces WHERE host = %s AND share = %s AND remote_path = %s",
                [path_match.group(1), path_match.group(2), path_match.group(3) or '']
            )
            return rows[0][0] if rows else None

        parts = path.replace('//', '').split('/') if path else []
        if len(parts) >= 2:
            remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''
            rows = self.execute_query(
                "SELECT id::text FROM smb_spaces WHERE host = %s AND share = %s AND remote_path = %s",
                [parts[0], parts[1], remote_path]
            )
            return rows[0][0] if rows else None
        return None

    def get_indexed_file_checksum(self, file_path: str) -> Optional[str]:
        rows = self.execute_query(
            """
            SELECT checksum
            FROM files
            WHERE path = %s
              AND is_directory = FALSE
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 1
            """,
            [file_path],
        )
        if not rows:
            return None
        return rows[0][0]

    def upsert_file_record(
        self,
        *,
        path: str,
        name: str,
        size: int,
        checksum: Optional[str],
        last_modified: Optional[datetime],
        crawl_config_id: Optional[str],
        created_at: Optional[datetime] = None,
    ) -> None:
        created_at = created_at or datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO files (
                        path, name, size, checksum, last_modified,
                        is_directory, is_duplicate, duplicate_of, crawl_config_id,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, NULL, %s, %s, %s)
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        size = EXCLUDED.size,
                        checksum = EXCLUDED.checksum,
                        last_modified = EXCLUDED.last_modified,
                        is_directory = FALSE,
                        is_duplicate = FALSE,
                        duplicate_of = NULL,
                        crawl_config_id = EXCLUDED.crawl_config_id,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [
                        path,
                        name,
                        size,
                        checksum,
                        last_modified,
                        crawl_config_id,
                        created_at,
                        updated_at,
                    ],
                )
            conn.commit()

    def delete_file_record(self, path: str) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM files WHERE path = %s", [path])
            conn.commit()

    def get_spaces(self) -> List[Dict[str, Any]]:
        self.ensure_crawl_tables()
        # Backfill: ensure every crawl_config has a matching smb_spaces entry
        all_configs = self.execute_query(
            """
            SELECT id::text, name, domain_zone, start_path, is_archive,
                   include_paths, exclude_paths,
                   connection_username, connection_password, connection_domain,
                   created_at::text
            FROM crawl_configs
            """
        )
        for row in all_configs:
            self._sync_smb_space({
                "id": row[0],
                "name": row[1],
                "domain_zone": row[2],
                "start_path": row[3],
                "is_archive": bool(row[4]),
                "include_paths": row[5] or [],
                "exclude_paths": row[6] or [],
                "connection_username": row[7],
                "connection_password": row[8],
                "connection_domain": row[9],
                "created_at": row[10],
            })
        config_rows = self.execute_query(
            """
            SELECT c.id::text, c.name, c.start_path, c.is_archive,
                   c.linked_archive_config_id,
                   la.start_path AS linked_archive_path
            FROM crawl_configs c
            LEFT JOIN crawl_configs la ON la.id = c.linked_archive_config_id
            ORDER BY c.name ASC, c.created_at DESC
            """
        )
        if not config_rows:
            return []

        space_stats_rows = self.execute_query(
            """
            SELECT s.id::text, s.host, s.share, s.remote_path,
                   COUNT(f.id)::bigint,
                   COALESCE(SUM(CASE WHEN NOT f.is_duplicate AND NOT f.is_deleted THEN f.size ELSE 0 END), 0)::bigint
            FROM smb_spaces s
            LEFT JOIN indexed_files_optimized f ON f.space_id = s.id AND NOT f.is_deleted
            GROUP BY s.id, s.host, s.share, s.remote_path
            """
        )
        space_stats = {}
        for row in space_stats_rows:
            key = (row[1], row[2], row[3])
            space_stats[key] = {"file_count": row[4], "total_size": row[5]}

        result = []
        for row in config_rows:
            start_path = row[2] or ''
            path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', start_path) if start_path else None
            if path_match:
                key = (path_match.group(1), path_match.group(2), path_match.group(3) or '')
                stats = space_stats.get(key, {"file_count": 0, "total_size": 0})
            else:
                stats = {"file_count": 0, "total_size": 0}
            result.append({
                "config_id": row[0],
                "name": row[1],
                "path_prefix": start_path,
                "is_archive": bool(row[3]),
                "linked_archive_config_id": row[4],
                "linked_archive_space": row[5],
                "file_count": stats["file_count"],
                "total_size": stats["total_size"],
            })
        return result


    def ensure_crawl_tables(self) -> None:
        """Initialise les tables de crawl avec protection contre les deadlocks.
        
        Cette méthode est protégée contre les deadlocks par:
        - Vérification préalable de l'existence des colonnes (évite ALTER TABLE inutile)
        - Lock timeout de 5 secondes (évite attente infinie)
        - Exécution des ALTER TABLE seulement si nécessaire
        """
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS crawl_configs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name TEXT NOT NULL,
                domain_zone TEXT NOT NULL,
                start_path TEXT NOT NULL,
                is_archive BOOLEAN NOT NULL DEFAULT FALSE,
                include_paths TEXT[] NOT NULL DEFAULT '{}',
                exclude_paths TEXT[] NOT NULL DEFAULT '{}',
                max_depth INTEGER NOT NULL DEFAULT 5,
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
            CREATE TABLE IF NOT EXISTS crawl_run_checkpoints (
                run_id UUID PRIMARY KEY REFERENCES crawl_runs(id) ON DELETE CASCADE,
                base_path TEXT NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                total_directories INTEGER NOT NULL DEFAULT 0,
                total_size BIGINT NOT NULL DEFAULT 0,
                processed_size BIGINT NOT NULL DEFAULT 0,
                large_files INTEGER NOT NULL DEFAULT 0,
                estimated_total_size BIGINT NOT NULL DEFAULT 0,
                phase TEXT NOT NULL DEFAULT 'crawl',
                last_activity_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS crawl_run_queue_items (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                run_id UUID NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
                queue_name TEXT NOT NULL,
                path TEXT NOT NULL,
                name TEXT,
                size BIGINT,
                last_modified TIMESTAMP WITH TIME ZONE,
                is_directory BOOLEAN NOT NULL DEFAULT FALSE,
                crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_crawl_run_queue_items_run_id ON crawl_run_queue_items(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_crawl_run_queue_items_run_queue ON crawl_run_queue_items(run_id, queue_name)",
        ]
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Set lock timeout to avoid infinite waits
                    cursor.execute("SET LOCAL lock_timeout = '5s'")
                    
                    # Execute DDL statements (CREATE TABLE, CREATE INDEX - idempotents)
                    for statement in ddl_statements:
                        cursor.execute(statement)
                    
                    # Vérifier si la colonne crawl_config_id existe déjà sur files
                    cursor.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'files' 
                            AND column_name = 'crawl_config_id'
                        )
                        """
                    )
                    has_crawl_config_id = cursor.fetchone()[0]
                    
                    if not has_crawl_config_id:
                        cursor.execute(
                            """
                            ALTER TABLE files
                            ADD COLUMN crawl_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
                            """
                        )
                        self.logger.info("Colonne crawl_config_id ajoutée à files via ensure_crawl_tables")
                    
                    # Vérifier si la colonne is_archive existe déjà sur crawl_configs
                    cursor.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'crawl_configs' 
                            AND column_name = 'is_archive'
                        )
                        """
                    )
                    has_is_archive = cursor.fetchone()[0]
                    
                    if not has_is_archive:
                        cursor.execute(
                            """
                            ALTER TABLE crawl_configs
                            ADD COLUMN is_archive BOOLEAN NOT NULL DEFAULT FALSE
                            """
                        )
                        self.logger.info("Colonne is_archive ajoutée à crawl_configs via ensure_crawl_tables")
                    
                    # Vérifier si la colonne linked_archive_config_id existe déjà sur crawl_configs
                    cursor.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'crawl_configs' 
                            AND column_name = 'linked_archive_config_id'
                        )
                        """
                    )
                    has_linked_archive = cursor.fetchone()[0]
                    
                    if not has_linked_archive:
                        cursor.execute(
                            """
                            ALTER TABLE crawl_configs
                            ADD COLUMN linked_archive_config_id UUID REFERENCES crawl_configs(id) ON DELETE SET NULL
                            """
                        )
                        self.logger.info("Colonne linked_archive_config_id ajoutée à crawl_configs via ensure_crawl_tables")
                    
                    # Créer l'index si nécessaire
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_files_crawl_config_id ON files(crawl_config_id)"
                    )
                    
                    # Rétro-remplissage uniquement si des lignes n'ont pas de crawl_config_id
                    cursor.execute("SELECT EXISTS (SELECT 1 FROM files WHERE crawl_config_id IS NULL LIMIT 1)")
                    needs_backfill = cursor.fetchone()[0]
                    
                    if needs_backfill:
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
                        self.logger.info(f"Rétro-remplissage de {cursor.rowcount} fichiers via ensure_crawl_tables")
                    
                    conn.commit()
                    
                except psycopg2.errors.LockNotAvailable:
                    # Lock timeout reached - rollback and continue
                    conn.rollback()
                    self.logger.warning("Lock timeout dans ensure_crawl_tables - schema update reporté")
                    # Ne pas propager l'erreur pour permettre le démarrage de l'API
                except Exception:
                    conn.rollback()
                    raise

    def list_crawl_configs(self) -> List[Dict[str, Any]]:
        query = """
            SELECT id::text, name, domain_zone, start_path,
                   is_archive,
                   include_paths, exclude_paths,
                   connection_username, connection_domain,
                   linked_archive_config_id,
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
                "is_archive": bool(row[4]),
                "include_paths": row[5] or [],
                "exclude_paths": row[6] or [],
                "connection_username": row[7],
                "connection_domain": row[8],
                "linked_archive_config_id": row[9],
                "created_at": row[10],
            }
            for row in rows
        ]

    def get_crawl_config_by_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(
            """
            SELECT
                id::text,
                name,
                domain_zone,
                start_path,
                is_archive,
                include_paths,
                exclude_paths,
                connection_username,
                connection_password,
                connection_domain,
                linked_archive_config_id,
                created_at::text
            FROM crawl_configs
            WHERE id::text = %s
            LIMIT 1
            """,
            [config_id],
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row[0],
            "name": row[1],
            "domain_zone": row[2],
            "start_path": row[3],
            "is_archive": bool(row[4]),
            "include_paths": row[5] or [],
            "exclude_paths": row[6] or [],
            "connection_username": row[7],
            "connection_password": row[8],
            "connection_domain": row[9],
            "linked_archive_config_id": row[10],
            "created_at": row[11],
        }

    def get_crawl_config_for_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        if not file_path:
            return None
        # Normaliser le chemin pour correspondre au format stocké (forward slashes)
        db_path = file_path.replace("\\", "/")
        rows = self.execute_query(
            """
            SELECT
                id::text,
                name,
                domain_zone,
                start_path,
                is_archive,
                include_paths,
                exclude_paths,
                connection_username,
                connection_password,
                connection_domain,
                linked_archive_config_id,
                created_at::text
            FROM crawl_configs
            WHERE starts_with(%s, start_path)
            ORDER BY LENGTH(start_path) DESC, created_at DESC
            LIMIT 1
            """,
            [db_path],
        )
        if not rows:
            return None
        row = rows[0]
        start_path = row[3]
        path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', start_path) if start_path else None
        connection_server = path_match.group(1) if path_match else ''
        return {
            "id": row[0],
            "name": row[1],
            "domain_zone": row[2],
            "start_path": start_path,
            "connection_server": connection_server,
            "is_archive": bool(row[4]),
            "include_paths": row[5] or [],
            "exclude_paths": row[6] or [],
            "connection_username": row[7],
            "connection_password": row[8],
            "connection_domain": row[9],
            "linked_archive_config_id": row[10],
            "created_at": row[11],
        }

    def _sync_smb_space(self, config: Dict[str, Any]) -> None:
        """Upsert smb_spaces depuis une config crawl_config."""
        start_path = config.get('start_path', '')
        path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', start_path) if start_path else None
        if path_match:
            host = path_match.group(1)
            share = path_match.group(2)
            remote_path = path_match.group(3) or ''
        else:
            parts = start_path.replace('//', '').split('/')
            host = parts[0] if len(parts) > 0 else ''
            share = parts[1] if len(parts) > 1 else ''
            remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''

        if not host or not share:
            return

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO smb_spaces (name, host, share, remote_path, domain_zone, connection_username, connection_password, connection_domain)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (host, share, remote_path) DO UPDATE SET
                        name = EXCLUDED.name,
                        domain_zone = EXCLUDED.domain_zone,
                        connection_username = EXCLUDED.connection_username,
                        connection_password = EXCLUDED.connection_password,
                        connection_domain = EXCLUDED.connection_domain,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [
                        config.get('name', 'Unnamed'),
                        host,
                        share,
                        remote_path,
                        config.get('domain_zone') or 'WORKGROUP',
                        config.get('connection_username') or '',
                        config.get('connection_password') or '',
                        config.get('connection_domain') or config.get('domain_zone') or '',
                    ],
                )
            conn.commit()

    def _unsync_smb_space(self, config: Dict[str, Any]) -> None:
        """Supprime l'entrée smb_spaces correspondant à une config."""
        start_path = config.get('start_path', '')
        path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', start_path) if start_path else None
        if path_match:
            host = path_match.group(1)
            share = path_match.group(2)
            remote_path = path_match.group(3) or ''
        else:
            parts = start_path.replace('//', '').split('/')
            host = parts[0] if len(parts) > 0 else ''
            share = parts[1] if len(parts) > 1 else ''
            remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''

        if not host or not share:
            return

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM smb_spaces WHERE host = %s AND share = %s AND remote_path = %s",
                    [host, share, remote_path],
                )
            conn.commit()

    def create_crawl_config(self, payload: CrawlConfigCreate) -> Dict[str, Any]:
        query = """
            INSERT INTO crawl_configs (
                name, domain_zone, start_path,
                is_archive,
                include_paths, exclude_paths,
                linked_archive_config_id,
                connection_username, connection_password, connection_domain
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, name, domain_zone, start_path, is_archive,
                      include_paths, exclude_paths,
                      connection_username, connection_domain,
                      linked_archive_config_id,
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
                        payload.is_archive,
                        payload.include_paths,
                        payload.exclude_paths,
                        payload.linked_archive_config_id or None,
                        payload.connection.username,
                        payload.connection.password,
                        payload.connection.domain,
                    ],
                )
                row = cursor.fetchone()
            conn.commit()

        config = {
            "id": row[0],
            "name": row[1],
            "domain_zone": row[2],
            "start_path": row[3],
            "is_archive": bool(row[4]),
            "include_paths": row[5] or [],
            "exclude_paths": row[6] or [],
            "connection_username": row[7],
            "connection_domain": row[8],
            "linked_archive_config_id": row[9],
            "created_at": row[10],
        }
        self._sync_smb_space(config)
        return config

    def update_crawl_config(self, config_id: str, payload: CrawlConfigUpdate) -> Optional[Dict[str, Any]]:
        old_config = self.get_crawl_config_by_id(config_id)
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if payload.connection.password:
                    cursor.execute(
                        """
                        UPDATE crawl_configs
                        SET name = %s,
                            domain_zone = %s,
                            start_path = %s,
                            is_archive = %s,
                            include_paths = %s,
                            exclude_paths = %s,
                            linked_archive_config_id = %s,
                            connection_username = %s,
                            connection_password = %s,
                            connection_domain = %s
                        WHERE id::text = %s
                        RETURNING id::text, name, domain_zone, start_path, is_archive,
                                  include_paths, exclude_paths,
                                  connection_username, connection_domain,
                                  linked_archive_config_id,
                                  created_at::text
                        """,
                        [
                            payload.name,
                            payload.domain_zone,
                            payload.start_path,
                            payload.is_archive,
                            payload.include_paths,
                            payload.exclude_paths,
                            payload.linked_archive_config_id or None,
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
                            is_archive = %s,
                            include_paths = %s,
                            exclude_paths = %s,
                            linked_archive_config_id = %s,
                            connection_username = %s,
                            connection_domain = %s
                        WHERE id::text = %s
                        RETURNING id::text, name, domain_zone, start_path, is_archive,
                                  include_paths, exclude_paths,
                                  connection_username, connection_domain,
                                  linked_archive_config_id,
                                  created_at::text
                        """,
                        [
                            payload.name,
                            payload.domain_zone,
                            payload.start_path,
                            payload.is_archive,
                            payload.include_paths,
                            payload.exclude_paths,
                            payload.linked_archive_config_id or None,
                            payload.connection.username,
                            payload.connection.domain,
                            config_id,
                        ],
                    )
                row = cursor.fetchone()
            conn.commit()

        if not row:
            return None

        config = {
            "id": row[0],
            "name": row[1],
            "domain_zone": row[2],
            "start_path": row[3],
            "is_archive": bool(row[4]),
            "include_paths": row[5] or [],
            "exclude_paths": row[6] or [],
            "connection_username": row[7],
            "connection_domain": row[8],
            "linked_archive_config_id": row[9],
            "created_at": row[10],
        }
        if old_config and old_config.get('start_path') != payload.start_path:
            self._unsync_smb_space(old_config)
        self._sync_smb_space(config)
        return config

    def delete_crawl_config(self, config_id: str) -> bool:
        """Supprime une configuration de crawl par son ID"""
        try:
            config = self.get_crawl_config_by_id(config_id)
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM crawl_configs WHERE id::text = %s RETURNING id",
                        [config_id]
                    )
                    result = cursor.fetchone()
                    conn.commit()
                    if result and config:
                        self._unsync_smb_space(config)
                    return result is not None
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la config {config_id}: {e}")
            return False

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

    def mark_run_pending(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE crawl_runs
                    SET status = 'pending'
                    WHERE id::text = %s
                      AND LOWER(status) IN ('queued', 'running', 'in_progress', 'cancelling')
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
                    WHERE LOWER(status) IN ('running', 'in_progress')
                    """
                )
                updated = cursor.rowcount or 0
            conn.commit()
        return updated

    def cancel_stale_cancelling_runs(self) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE crawl_runs
                    SET status = 'cancelled'
                    WHERE LOWER(status) = 'cancelling'
                    """
                )
                updated = cursor.rowcount or 0
            conn.commit()
        return updated

    def revive_latest_terminal_run(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    WITH latest_run AS (
                        SELECT id
                        FROM crawl_runs
                        ORDER BY triggered_at DESC
                        LIMIT 1
                    )
                    UPDATE crawl_runs
                    SET status = 'running'
                    WHERE id IN (SELECT id FROM latest_run)
                      AND LOWER(status) IN ('failed', 'error', 'completed', 'cancelled')
                    RETURNING id::text, status
                    """
                )
                row = cursor.fetchone()
            conn.commit()
        if not row:
            return None
        return {"run_id": row[0], "status": row[1]}

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


def _require_smbclient() -> None:
    if smbclient is None:
        raise HTTPException(status_code=500, detail="smbclient non disponible sur l'API")


def _normalize_smb_path(path: str) -> str:
    normalized = (path or "").strip().replace("/", "\\")
    if not normalized.startswith("\\\\"):
        normalized = "\\\\" + normalized.lstrip("\\")
    return normalized.rstrip("\\") or normalized


def _fix_smb_encoding(name: str) -> str:
    try:
        if any(0x80 <= ord(c) <= 0x9f for c in name):
            return name.encode("latin-1").decode("cp850")
    except Exception:
        pass
    return name


def _join_smb_path(base_path: str, name: str) -> str:
    base = _normalize_smb_path(base_path).rstrip("\\")
    child = (name or "").strip("\\/")
    if not child:
        return base
    return f"{base}\\{child}"


def _parent_smb_path(path: str, root_path: str) -> str:
    normalized = _normalize_smb_path(path)
    normalized_root = _normalize_smb_path(root_path)
    if normalized == normalized_root:
        return normalized_root
    parent = normalized.rsplit("\\", 1)[0]
    if len(parent.strip("\\")) < len(normalized_root.strip("\\")):
        return normalized_root
    return parent or normalized_root


def _smb_extension(path: str) -> Optional[str]:
    suffix = Path(path).suffix.lower()
    return suffix or None


def _smb_name(path: str) -> str:
    normalized = _normalize_smb_path(path)
    return normalized.rsplit("\\", 1)[-1]


def _guess_media_type(path: str) -> str:
    extension = _smb_extension(path)
    explicit_mapping = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".odt": "application/vnd.oasis.opendocument.text",
        ".ods": "application/vnd.oasis.opendocument.spreadsheet",
        ".odp": "application/vnd.oasis.opendocument.presentation",
    }
    if extension in explicit_mapping:
        return explicit_mapping[extension]
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def _unc_to_file_url(path: str) -> str:
    normalized = _normalize_smb_path(path).lstrip("\\")
    return "file://" + normalized.replace("\\", "/")


def _render_html_document(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; }}
    .page {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 24px; box-shadow: 0 10px 30px rgba(15,23,42,.06); }}
    h1, h2, h3 {{ margin: 0 0 16px 0; }}
    p, li {{ line-height: 1.55; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    .muted {{ color: #64748b; font-size: 14px; }}
    .sheet {{ margin-top: 24px; }}
    .pre {{ white-space: pre-wrap; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="card">
      {body}
    </div>
  </div>
</body>
</html>"""


def _xml_text_nodes(xml_bytes: bytes, tags: set[str]) -> List[str]:
    root = ElementTree.fromstring(xml_bytes)
    values: List[str] = []
    for element in root.iter():
        local_name = element.tag.split("}", 1)[-1]
        if local_name in tags:
            text = "".join(element.itertext()).strip()
            if text:
                values.append(text)
    return values


def _preview_docx(raw_bytes: bytes, title: str) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        paragraphs = _xml_text_nodes(archive.read("word/document.xml"), {"p"})
    body = "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs[:400]) or "<p class='muted'>Aucun contenu textuel détecté.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _preview_odt(raw_bytes: bytes, title: str) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        paragraphs = _xml_text_nodes(archive.read("content.xml"), {"p", "h"})
    body = "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs[:400]) or "<p class='muted'>Aucun contenu textuel détecté.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _preview_pptx(raw_bytes: bytes, title: str) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        slide_names = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        slides_html: List[str] = []
        for index, slide_name in enumerate(slide_names[:80], start=1):
            texts = _xml_text_nodes(archive.read(slide_name), {"t"})
            slide_body = "".join(f"<p>{html.escape(text)}</p>" for text in texts) or "<p class='muted'>Slide sans texte détecté.</p>"
            slides_html.append(f"<section class='sheet'><h2>Slide {index}</h2>{slide_body}</section>")
    body = "".join(slides_html) or "<p class='muted'>Aucun texte détecté dans la présentation.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _preview_odp(raw_bytes: bytes, title: str) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        texts = _xml_text_nodes(archive.read("content.xml"), {"p", "h"})
    slides_html = []
    chunk_size = 12
    for index in range(0, len(texts[:240]), chunk_size):
        block = texts[index:index + chunk_size]
        slide_body = "".join(f"<p>{html.escape(text)}</p>" for text in block)
        slides_html.append(f"<section class='sheet'><h2>Slide {len(slides_html) + 1}</h2>{slide_body}</section>")
    body = "".join(slides_html) or "<p class='muted'>Aucun texte détecté dans la présentation.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _preview_xlsx(raw_bytes: bytes, title: str) -> str:
    if openpyxl is None:
        raise ValueError("openpyxl indisponible")
    workbook = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    sheets_html: List[str] = []
    for worksheet in workbook.worksheets[:8]:
        rows_html: List[str] = []
        for row in worksheet.iter_rows(min_row=1, max_row=40, values_only=True):
            cells = "".join(f"<td>{html.escape('' if value is None else str(value))}</td>" for value in row[:12])
            rows_html.append(f"<tr>{cells}</tr>")
        table_html = "<table>" + "".join(rows_html) + "</table>" if rows_html else "<p class='muted'>Feuille vide.</p>"
        sheets_html.append(f"<section class='sheet'><h2>{html.escape(worksheet.title)}</h2>{table_html}</section>")
    body = "".join(sheets_html) or "<p class='muted'>Aucune feuille exploitable.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _preview_ods(raw_bytes: bytes, title: str) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        root = ElementTree.fromstring(archive.read("content.xml"))
    tables_html: List[str] = []
    for table in [element for element in root.iter() if element.tag.split("}", 1)[-1] == "table"][:8]:
        name = table.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name", "Feuille")
        rows_html: List[str] = []
        for row in [element for element in table if element.tag.split('}', 1)[-1] == "table-row"][:40]:
            cells = []
            for cell in [element for element in row if element.tag.split('}', 1)[-1] == "table-cell"][:12]:
                text = " ".join(part.strip() for part in cell.itertext() if part.strip())
                cells.append(f"<td>{html.escape(text)}</td>")
            rows_html.append(f"<tr>{''.join(cells)}</tr>")
        table_html = "<table>" + "".join(rows_html) + "</table>" if rows_html else "<p class='muted'>Feuille vide.</p>"
        tables_html.append(f"<section class='sheet'><h2>{html.escape(name)}</h2>{table_html}</section>")
    body = "".join(tables_html) or "<p class='muted'>Aucune feuille exploitable.</p>"
    return _render_html_document(title, f"<h1>{html.escape(title)}</h1>{body}")


def _libreoffice_convert_to_html(raw_bytes: bytes, extension: str) -> Optional[str]:
    try:
        soffice = shutil.which("libreoffice") or shutil.which("soffice")
        if not soffice:
            return None
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp_in:
            tmp_in.write(raw_bytes)
            tmp_in_path = tmp_in.name
        tmp_out_dir = tempfile.mkdtemp()
        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "html:HTML", "--outdir", tmp_out_dir, tmp_in_path],
            capture_output=True, timeout=60,
        )
        html_path = Path(tmp_out_dir) / (Path(tmp_in_path).stem + ".html")
        if not html_path.exists():
            os.unlink(tmp_in_path)
            shutil.rmtree(tmp_out_dir, ignore_errors=True)
            return None
        html_content = html_path.read_text(encoding="utf-8", errors="replace")
        # Embed images as base64 data URIs
        out_dir = str(tmp_out_dir)
        def _replace_img_src(match: re.Match) -> str:
            src = match.group(1)
            img_path = Path(out_dir) / src
            if img_path.exists():
                img_bytes = img_path.read_bytes()
                mime = "image/png"
                if src.lower().endswith((".jpg", ".jpeg")):
                    mime = "image/jpeg"
                elif src.lower().endswith(".gif"):
                    mime = "image/gif"
                elif src.lower().endswith(".svg"):
                    mime = "image/svg+xml"
                b64 = base64.b64encode(img_bytes).decode()
                return f'src="data:{mime};base64,{b64}"'
            return match.group(0)
        html_content = re.sub(r'src="([^"]+)"', _replace_img_src, html_content)
        os.unlink(tmp_in_path)
        shutil.rmtree(tmp_out_dir, ignore_errors=True)
        return html_content
    except Exception:
        return None


def _generate_office_preview_html(path: str, raw_bytes: bytes) -> str:
    extension = (_smb_extension(path) or "").lower()
    title = _smb_name(path)

    html_content = _libreoffice_convert_to_html(raw_bytes, extension)
    if html_content:
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
        body_content = body_match.group(1) if body_match else html_content
        style_match = re.search(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL)
        lo_style = style_match.group(1) if style_match else ""
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#fff;font-family:sans-serif;padding:16px;overflow-x:auto}}
img{{max-width:100%;height:auto}}{lo_style}</style>
</head><body>{body_content}</body></html>"""

    if extension in {".docx", ".doc"}:
        return _preview_docx(raw_bytes, title)
    if extension == ".odt":
        return _preview_odt(raw_bytes, title)
    if extension in {".xlsx", ".xls"}:
        return _preview_xlsx(raw_bytes, title)
    if extension == ".ods":
        return _preview_ods(raw_bytes, title)
    if extension in {".pptx", ".ppt"}:
        return _preview_pptx(raw_bytes, title)
    if extension == ".odp":
        return _preview_odp(raw_bytes, title)
    raise ValueError("Format bureautique non pris en charge")


# Cache des sessions SMB par serveur
_SMB_SESSIONS: Dict[str, Any] = {}


def _get_smb_session(config: Dict[str, Any]) -> Any:
    """
    Récupère ou crée une session SMB pour la configuration donnée.
    Chaque session est isolée et identifiée par le serveur.
    """
    _require_smbclient()
    server = config.get("connection_server", "")
    username = config.get("connection_username")
    password = config.get("connection_password")
    domain = config.get("connection_domain") or ""
    
    # Clé unique pour cette session
    session_key = f"{server}_{username}"
    
    if session_key not in _SMB_SESSIONS:
        # Créer une nouvelle connexion et session
        from smbprotocol.connection import Connection
        from smbprotocol.session import Session
        
        connection = Connection(server, server)
        connection.connect()
        session = Session(connection, username, password, domain=domain)
        session.connect()
        
        _SMB_SESSIONS[session_key] = (connection, session)
    
    return _SMB_SESSIONS[session_key]


def _configure_smb_session(config: Dict[str, Any]) -> str:
    """
    Configure une session SMB et retourne le serveur pour identifier la session.
    Cette fonction est gardée pour compatibilité avec le code existant.
    """
    server = config.get("connection_server", "")
    _get_smb_session(config)
    return server


def _is_smb_sharing_violation(exc: Exception) -> bool:
    message = str(exc)
    return "0xc0000043" in message or "being used by another process" in message


def _read_smb_file_bytes(
    file_path: str, 
    retries: int = 2, 
    retry_delay: float = 0.15, 
    server: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Lit un fichier SMB avec gestion des sessions explicites.
    
    Args:
        file_path: Chemin du fichier
        retries: Nombre de tentatives
        retry_delay: Délai entre tentatives
        server: Serveur SMB (optionnel, pour compatibilité)
        config: Configuration SMB avec credentials (optionnel)
    """
    normalized_path = _normalize_smb_path(file_path)
    last_error: Optional[Exception] = None
    
    # Si config fournie, enregistrer une session temporaire
    if config:
        _smb_register_session_for_config(config)
    
    for attempt in range(retries + 1):
        try:
            with smbclient.open_file(normalized_path, mode="rb") as handle:
                return handle.read()
        except OSError as exc:
            last_error = exc
            if attempt >= retries or not _is_smb_sharing_violation(exc):
                raise
            time.sleep(retry_delay)
    if last_error is not None:
        raise last_error
    raise OSError(f"Lecture SMB impossible pour {normalized_path}")


def _get_config_for_path_or_404(file_path: str) -> Dict[str, Any]:
    db = get_db_adapter()
    config = db.get_crawl_config_for_path(_normalize_smb_path(file_path))
    if not config:
        raise HTTPException(status_code=404, detail="Aucune configuration SMB ne couvre ce chemin")
    return config


def _smb_register_session_for_config(config: Dict[str, Any]) -> None:
    _require_smbclient()
    start_path = config.get("start_path", "")
    path_match = re.match(r'^//([^/]+)/([^/]+)', start_path) if start_path else None
    host = path_match.group(1) if path_match else ""
    username = config.get("connection_username") or ""
    password = config.get("connection_password") or ""
    domain = config.get("connection_domain") or config.get("domain_zone") or ""
    if host:
        smbclient.register_session(
            host,
            username=f"{domain}\\{username}" if domain and username else username,
            password=password,
            connection_timeout=10,
        )


def _ensure_parent_directories(target_directory_path: str) -> None:
    segments = [segment for segment in _normalize_smb_path(target_directory_path).split("\\") if segment]
    if len(segments) < 2:
        return
    current = f"\\\\{segments[0]}\\{segments[1]}"
    for segment in segments[2:]:
        current = _join_smb_path(current, segment)
        try:
            smbclient.mkdir(current)
        except OSError:
            continue


def _safe_queue_crawl_for_config(db: Any, config_id: Optional[str]) -> None:
    if not config_id or not hasattr(db, "start_crawl"):
        return
    try:
        db.start_crawl(config_id)
    except ValueError:
        logger.info("Run deja actif pour la configuration %s, nouveau lancement ignore.", config_id)
    except Exception as exc:
        logger.warning("Impossible de lancer automatiquement le crawl pour %s: %s", config_id, exc)


def _sync_archived_file_in_db(
    db: Any,
    *,
    source_path: str,
    target_path: str,
    checksum: str,
    file_size: int,
    source_config_id: Optional[str],
    target_config_id: Optional[str],
    source_deleted: bool,
) -> None:
    now = datetime.now(timezone.utc)
    if hasattr(db, "upsert_file_record"):
        db.upsert_file_record(
            path=target_path,
            name=_smb_name(target_path),
            size=file_size,
            checksum=checksum,
            last_modified=now,
            crawl_config_id=target_config_id,
            created_at=now,
        )
        if source_deleted and hasattr(db, "delete_file_record"):
            db.delete_file_record(source_path)
        return

    if hasattr(db, "save_files_batch"):
        db.save_files_batch(
            [
                {
                    "path": target_path,
                    "name": _smb_name(target_path),
                    "size": file_size,
                    "checksum": checksum,
                    "last_modified": now,
                    "is_directory": False,
                    "is_duplicate": False,
                    "duplicate_of": None,
                    "crawl_config_id": target_config_id,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )
    if source_deleted and hasattr(db, "delete_file_record"):
        db.delete_file_record(source_path)


def _compute_smb_sha256(file_path: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Calcule le SHA256 d'un fichier SMB (fallback pour compatibilité).
    Privilégier smb_to_local_path + _compute_local_sha256.
    """
    # Essayer d'abord avec le montage local si disponible
    if smb_to_local_path and config:
        local_path = smb_to_local_path(file_path, config)
        if local_path:
            return _compute_local_sha256(local_path)
    
    # Fallback vers smbclient direct
    digest = hashlib.sha256()
    normalized_path = _normalize_smb_path(file_path)
    
    if config:
        _configure_smb_session(config)
    
    with smbclient.open_file(normalized_path, mode="rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _compute_local_sha256(file_path: str) -> str:
    """
    Calcule le SHA256 d'un fichier local.
    
    Args:
        file_path: Chemin du fichier local
    
    Returns:
        Hash SHA256 hexadécimal
    """
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


# Gestionnaire WebSocket pour le monitoring
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connecté. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client déconnecté. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
            return True
        except Exception:
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


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
        WHERE f1.is_duplicate = TRUE
        ORDER BY f1.size DESC
        LIMIT 100
    """,
    "stats": """
        SELECT
            COUNT(*) as total_files,
            SUM(CASE WHEN is_directory = FALSE THEN 1 ELSE 0 END) as files_only,
            SUM(CASE WHEN is_directory = TRUE THEN 1 ELSE 0 END) as directories,
            SUM(CASE WHEN is_duplicate = TRUE THEN 1 ELSE 0 END) as duplicates,
            COALESCE(SUM(CASE WHEN is_directory = FALSE THEN size ELSE 0 END), 0) as total_size
        FROM files
    """,
}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/explorer/live-items", response_model=List[ExplorerItem])
async def get_live_explorer_items(
    root: str = Query(...),
    current_path: Optional[str] = Query(default=None),
):
    """Liste les fichiers SMB en temps reel via smbclient.listdir sans passer par la base."""
    try:
        normalized_root = _normalize_smb_path(root)
        normalized_current_path = _normalize_smb_path(current_path or root)
        config = _get_config_for_path_or_404(normalized_current_path)

        start_path = config.get("start_path", "")
        path_match = re.match(r'^//([^/]+)/([^/]+)', start_path) if start_path else None
        host = path_match.group(1) if path_match else ""
        username = config.get("connection_username") or ""
        password = config.get("connection_password") or ""
        domain = config.get("connection_domain") or config.get("domain_zone") or ""
        if host:
            smbclient.register_session(
                host,
                username=f"{domain}\\{username}" if domain and username else username,
                password=password,
                connection_timeout=10,
            )

        entries = smbclient.listdir(normalized_current_path)
        items: List[ExplorerItem] = []

        now_ts = time.time()
        large_threshold_bytes = 1073741824
        old_threshold_seconds = 730 * 86400

        for entry_name in entries:
            if entry_name in {".", ".."}:
                continue
            entry_name = _fix_smb_encoding(entry_name)
            child_path = _join_smb_path(normalized_current_path, entry_name)
            try:
                stat_info = smbclient.stat(child_path)
                is_directory = bool(stat_info.st_file_attributes & 0x10) if hasattr(stat_info, 'st_file_attributes') else False
                entry_size = None if is_directory else getattr(stat_info, 'st_size', 0)
                entry_mtime = getattr(stat_info, 'st_mtime', 0)
                is_garbage = False
                is_large = False
                is_old = False
                if not is_directory:
                    lowered = entry_name.lower()
                    is_garbage = any(p in entry_name or lowered.endswith(p) for p in ('~$', '.tmp', '.lock', '.lnk')) or entry_name in ('Thumbs.db', 'desktop.ini')
                    is_large = entry_size is not None and entry_size > large_threshold_bytes
                    is_old = entry_mtime and (now_ts - entry_mtime) > old_threshold_seconds
                items.append(ExplorerItem(
                    path=child_path,
                    name=entry_name,
                    is_directory=is_directory,
                    size=entry_size,
                    last_modified=datetime.fromtimestamp(entry_mtime, tz=timezone.utc) if entry_mtime else None,
                    created_at=datetime.fromtimestamp(getattr(stat_info, 'st_ctime', 0), tz=timezone.utc),
                    extension=None if is_directory else _smb_extension(child_path),
                    crawl_config_id=config.get("id"),
                    has_duplicates=False,
                    duplicate_count=0,
                    is_garbage=is_garbage,
                    is_large=is_large,
                    is_old=is_old,
                ))
            except OSError:
                items.append(ExplorerItem(
                    path=child_path,
                    name=entry_name,
                    is_directory=True,
                    crawl_config_id=config.get("id"),
                    has_duplicates=False,
                    duplicate_count=0,
                ))

        return sorted(items, key=lambda item: (not item.is_directory, item.name.lower()))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_live_explorer_items: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du scan SMB en direct: {e}")


@app.get("/api/explorer/items", response_model=List[ExplorerItem])
async def get_explorer_items(
    root: str = Query(...),
    current_path: Optional[str] = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=10000),
):
    try:
        db = get_db_adapter()
        normalized_root = _normalize_smb_path(root)
        normalized_current_path = _normalize_smb_path(current_path or root)

        # Use forward-slash version for parsing
        fs_root = root.replace("\\", "/")
        fs_current = (current_path or root).replace("\\", "/")

        path_match = re.match(r'^//([^/]+)/([^/]+)(?:/(.*))?$', fs_root) if fs_root else None
        host = path_match.group(1) if path_match else ''
        share = path_match.group(2) if path_match else ''
        remote_path = path_match.group(3) or '' if path_match else ''

        space_rows = db.execute_query(
            "SELECT id::text FROM smb_spaces WHERE host = %s AND share = %s AND remote_path = %s",
            [host, share, remote_path],
        )
        space_id = space_rows[0][0] if space_rows else None

        prefix = f"//{host}/{share}/"
        rel_path = fs_current.removeprefix(prefix) if fs_current else remote_path
        if not rel_path:
            rel_path = remote_path or ''

        items: List[ExplorerItem] = []

        if space_id:
            try:
                pref_rows = db.execute_query(
                    "SELECT large_file_threshold_mb, old_file_threshold_days FROM current_artefact_filters"
                )
                if pref_rows:
                    large_threshold_mb = pref_rows[0][0]
                    old_threshold_days = pref_rows[0][1]
                else:
                    large_threshold_mb = 1024
                    old_threshold_days = 730
            except Exception:
                large_threshold_mb = 1024
                old_threshold_days = 730
            large_threshold_bytes = large_threshold_mb * 1024 * 1024

            dir_rows = db.execute_query(
                """
                SELECT d.path, d.name,
                       EXISTS (
                           SELECT 1 FROM indexed_files_optimized fi
                           WHERE fi.directory_id = d.id AND NOT fi.is_deleted
                             AND (fi.is_duplicate OR fi.is_garbage
                                  OR fi.size > %s
                                  OR fi.last_modified < CURRENT_TIMESTAMP - make_interval(days => %s))
                       ) AS has_flagged_files
                FROM directories d
                WHERE d.space_id::text = %s AND d.parent_path = %s
                ORDER BY d.name ASC
                LIMIT %s
                """,
                [large_threshold_bytes, old_threshold_days, space_id, rel_path, limit],
            )
            for row in dir_rows:
                child_path = _join_smb_path(normalized_current_path, row[1])
                items.append(ExplorerItem(
                    path=child_path,
                    name=row[1],
                    is_directory=True,
                    crawl_config_id=space_id,
                    has_flagged_files=bool(row[2]),
                ))

            remaining = limit - len(items)
            if remaining > 0:
                dir_id_rows = db.execute_query(
                    "SELECT id::text FROM directories WHERE space_id::text = %s AND path = %s",
                    [space_id, rel_path],
                )
                if dir_id_rows:
                    dir_id = dir_id_rows[0][0]
                    file_rows = db.execute_query(
                        """
                        SELECT f.path, f.name, f.size, f.last_modified, f.created_at, f.hash_xxh64,
                               f.is_garbage,
                               (SELECT COUNT(*) FROM indexed_files_optimized d
                                WHERE d.hash_xxh64 = f.hash_xxh64 AND d.size = f.size
                                  AND d.space_id = f.space_id AND NOT d.is_deleted
                                  AND d.id <> f.id) > 0 AS is_duplicate,
                               f.size > %s AS is_large,
                               f.last_modified < CURRENT_TIMESTAMP - make_interval(days => %s) AS is_old
                        FROM indexed_files_optimized f
                        WHERE f.space_id::text = %s AND f.directory_id::text = %s AND NOT f.is_deleted
                        ORDER BY f.name ASC
                        LIMIT %s
                        """,
                        [large_threshold_bytes, old_threshold_days, space_id, dir_id, remaining],
                    )
                    for row in file_rows:
                        child_path = _join_smb_path(normalized_current_path, row[1])
                        items.append(ExplorerItem(
                            path=child_path,
                            name=row[1],
                            is_directory=False,
                            size=row[2],
                            last_modified=row[3],
                            created_at=row[4],
                            crawl_config_id=space_id,
                            has_duplicates=bool(row[7]),
                            is_duplicate=bool(row[7]),
                            is_garbage=bool(row[6]),
                            is_large=bool(row[8]),
                            is_old=bool(row[9]),
                        ))
        return items
    except Exception as e:
        logger.error(f"Erreur get_explorer_items: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement de l'explorateur")


@app.get("/api/file-content")
async def get_file_content(path: str, download: bool = False):
    try:
        normalized_path = _normalize_smb_path(path)
        config = _get_config_for_path_or_404(normalized_path)
        _smb_register_session_for_config(config)
        media_type = _guess_media_type(normalized_path)
        filename = _smb_name(normalized_path) or "document"
        payload = _read_smb_file_bytes(normalized_path)

        headers = {
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(filename)}"
                if download
                else f"inline; filename*=UTF-8''{quote(filename)}"
            )
        }
        return Response(content=payload, media_type=media_type, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_file_content: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la lecture du fichier SMB")


@app.get("/api/file-preview")
async def get_file_preview(path: str):
    try:
        normalized_path = _normalize_smb_path(path)
        config = _get_config_for_path_or_404(normalized_path)
        _smb_register_session_for_config(config)
        payload = _read_smb_file_bytes(normalized_path)
        html_document = _generate_office_preview_html(normalized_path, payload)
        return HTMLResponse(content=html_document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_file_preview: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de l'aperçu bureautique")


@app.post("/api/archive/file", response_model=ArchiveFileResult)
async def archive_file(payload: ArchiveFileRequest):
    """
    Archive un fichier avec montage SMB prioritaire et fallback programmatique.
    Les partages sont vérifiés/remontés automatiquement si nécessaire.
    """
    use_mount = ensure_mounted is not None
    
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        normalized_source_path = _normalize_smb_path(payload.source_path)
        normalized_target_directory = _normalize_smb_path(payload.target_directory_path)
        source_config = _get_config_for_path_or_404(normalized_source_path)
        target_config = _get_config_for_path_or_404(normalized_target_directory)
        source_checksum = db.get_indexed_file_checksum(normalized_source_path) if hasattr(db, "get_indexed_file_checksum") else None
        if not source_checksum:
            raise HTTPException(
                status_code=409,
                detail="Checksum source introuvable en base. Le fichier doit d'abord etre indexe et checksumme avant archivage.",
            )
        
        # Essayer d'abord avec les montages SMB
        local_source = None
        local_target_dir = None
        
        if use_mount:
            logger.info("Tentative avec montage SMB...")
            local_source = ensure_mounted(source_config)
            local_target_dir = ensure_mounted(target_config)
        
        # Fallback vers mode programmatique si montage échoue ou non disponible
        if not local_source or not local_target_dir:
            if not use_mount:
                logger.info("Mode programmatique (montage non disponible)")
            else:
                logger.warning("Fallback vers mode programmatique SMB")
            use_mount = False
        
        if use_mount:
            # === MODE MONTAGE (prioritaire) ===
            local_target_path = os.path.join(
                local_target_dir, 
                _smb_name(normalized_source_path)
            )
            
            # Vérifier que la cible n'existe pas déjà
            if not payload.overwrite and os.path.exists(local_target_path):
                raise HTTPException(status_code=409, detail="Le fichier cible existe déjà")
            
            # Créer les répertoires parents si nécessaire
            os.makedirs(os.path.dirname(local_target_path), exist_ok=True)
            
            # Copier le fichier
            copied_size = 0
            with open(local_source, "rb") as source_handle:
                with open(local_target_path, "wb") as target_handle:
                    while True:
                        chunk = source_handle.read(1024 * 1024)
                        if not chunk:
                            break
                        copied_size += len(chunk)
                        target_handle.write(chunk)
            
            # Vérifier le checksum
            archived_checksum = _compute_local_sha256(local_target_path)
            
        else:
            # === MODE PROGRAMMATIQUE (fallback) ===
            # Configurer session source et lire
            _configure_smb_session(source_config)
            file_content = _read_smb_file_bytes(normalized_source_path, config=source_config)
            copied_size = len(file_content)
            
            # Configurer session cible et écrire
            _configure_smb_session(target_config)
            
            target_path = _join_smb_path(normalized_target_directory, _smb_name(normalized_source_path))
            if not payload.overwrite:
                try:
                    smbclient.stat(target_path)
                    raise HTTPException(status_code=409, detail="Le fichier cible existe déjà")
                except OSError:
                    pass
            
            _ensure_parent_directories(normalized_target_directory)
            
            with smbclient.open_file(target_path, mode="wb") as target_handle:
                target_handle.write(file_content)
            
            archived_checksum = _compute_smb_sha256(target_path, config=target_config)
            local_target_path = None  # Pas de chemin local en mode programmatique
        
        # Vérification checksum commune
        if archived_checksum.lower() != source_checksum.lower():
            try:
                if use_mount and local_target_path:
                    os.remove(local_target_path)
                elif not use_mount:
                    smbclient.remove(target_path)
            except OSError:
                pass
            raise HTTPException(
                status_code=409,
                detail="Verification SHA-256 echouee apres copie. La source est conservee et l'archive est rejetee.",
            )
        
        # Suppression source si mode=move
        source_deleted = False
        link_path = None
        if payload.mode == "move":
            try:
                if use_mount:
                    os.remove(local_source)
                else:
                    _configure_smb_session(source_config)
                    smbclient.remove(normalized_source_path)
                
                source_deleted = True
                
                if payload.leave_link:
                    target_smb_path = _join_smb_path(
                        normalized_target_directory, 
                        _smb_name(normalized_source_path)
                    )
                    if use_mount:
                        link_local_path = f"{local_source}.url"
                        with open(link_local_path, "w") as link_handle:
                            link_handle.write(
                                "[InternetShortcut]\n"
                                f"URL={_unc_to_file_url(target_smb_path)}\n"
                                "IconIndex=0\n"
                            )
                    else:
                        link_smb_path = f"{normalized_source_path}.url"
                        with smbclient.open_file(link_smb_path, mode="w") as link_handle:
                            link_handle.write(
                                "[InternetShortcut]\n"
                                f"URL={_unc_to_file_url(target_smb_path)}\n"
                                "IconIndex=0\n"
                            )
                    link_path = f"{normalized_source_path}.url"
            except OSError as e:
                logger.error(f"Erreur lors de la suppression de la source: {e}")
                source_deleted = False

        # Construire le chemin SMB cible final
        final_target_path = _join_smb_path(
            normalized_target_directory, 
            _smb_name(normalized_source_path)
        )
        
        _sync_archived_file_in_db(
            db,
            source_path=normalized_source_path,
            target_path=final_target_path,
            checksum=archived_checksum,
            file_size=copied_size,
            source_config_id=source_config.get("id"),
            target_config_id=target_config.get("id"),
            source_deleted=source_deleted,
        )
        _safe_queue_crawl_for_config(db, target_config.get("id"))
        if payload.mode == "move":
            _safe_queue_crawl_for_config(db, source_config.get("id"))

        return ArchiveFileResult(
            source_path=normalized_source_path,
            target_path=final_target_path,
            mode=payload.mode,
            source_deleted=source_deleted,
            link_path=link_path,
            checksum_verified=True,
            checksum=archived_checksum,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur archive_file: {e}")
        error_detail = str(e)
        lowered_detail = error_detail.lower()

        if (
            "status_logon_failure" in lowered_detail
            or "logon is invalid" in lowered_detail
            or "authentication" in lowered_detail
            or "nt_status" in lowered_detail
        ):
            raise HTTPException(status_code=502, detail=error_detail)

        raise HTTPException(status_code=500, detail="Erreur lors de l'archivage du fichier")


class DeleteFileRequest(BaseModel):
    path: str


@app.post("/api/file/delete")
async def delete_file(payload: DeleteFileRequest):
    """Supprime un fichier SMB"""
    try:
        normalized_path = _normalize_smb_path(payload.path)
        config = _get_config_for_path_or_404(normalized_path)

        start_path = config.get("start_path", "")
        path_match = re.match(r'^//([^/]+)/([^/]+)', start_path) if start_path else None
        host = path_match.group(1) if path_match else ""
        username = config.get("connection_username") or ""
        password = config.get("connection_password") or ""
        domain = config.get("connection_domain") or config.get("domain_zone") or ""
        if host:
            smbclient.register_session(
                host,
                username=f"{domain}\\{username}" if domain and username else username,
                password=password,
            )

        smbclient.remove(normalized_path)
        return {"status": "deleted", "path": normalized_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_file: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du fichier")


@app.get("/api/smb-mounts")
async def get_smb_mounts():
    """Liste les montages SMB actifs avec leur temps d'inactivité."""
    if get_mount_manager is None:
        raise HTTPException(status_code=503, detail="Gestionnaire de montages non disponible")
    
    try:
        mounts = get_mount_manager().list_active_mounts()
        idle_timeout = 30
        if SMBMountManager and hasattr(SMBMountManager, 'IDLE_TIMEOUT_MINUTES'):
            idle_timeout = SMBMountManager.IDLE_TIMEOUT_MINUTES
        return {
            "mounts": mounts,
            "total": len(mounts),
            "timeout_minutes": idle_timeout
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des montages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/smb-mounts/{config_id}/unmount")
async def unmount_smb(config_id: str):
    """Démonte manuellement un partage SMB."""
    if get_mount_manager is None:
        raise HTTPException(status_code=503, detail="Gestionnaire de montages non disponible")
    
    try:
        success = get_mount_manager()._unmount(config_id)
        if success:
            return {"message": f"Partage {config_id} démonté avec succès"}
        else:
            raise HTTPException(status_code=500, detail=f"Échec du démontage de {config_id}")
    except Exception as e:
        logger.error(f"Erreur lors du démontage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/stats/files-by-type")
async def get_stats_files_by_type(space: Optional[str] = None):
    try:
        db = get_db_adapter()
        return db.get_files_by_type(space=space)
    except Exception as e:
        logger.error(f"Erreur get_files_by_type: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des types de fichiers")


@app.get("/api/stats/hash-progress")
async def get_stats_hash_progress(space: Optional[str] = None):
    try:
        db = get_db_adapter()
        return db.get_hash_progress(space=space)
    except Exception as e:
        logger.error(f"Erreur get_hash_progress: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du statut du hashage")


@app.get("/api/duplicates")
async def get_duplicates(space: Optional[str] = None):
    try:
        db = get_db_adapter()
        query = """
            SELECT f1.id, f1.path, f1.name, f1.size, f1.hash_xxh64,
                   f1.last_modified, f1.created_at, f1.updated_at,
                   f2.path as duplicate_of_path
            FROM indexed_files_optimized f1
            JOIN indexed_files_optimized f2
              ON f1.hash_xxh64 = f2.hash_xxh64 AND f1.space_id = f2.space_id
             AND f1.size = f2.size AND f1.id != f2.id
             AND f1.is_duplicate = TRUE AND f2.is_deleted = FALSE
             AND f1.is_deleted = FALSE
            WHERE f1.is_duplicate = TRUE
        """
        params: List[Any] = []
        if space:
            config_id = db.resolve_space_config_id(space) if hasattr(db, "resolve_space_config_id") else None
            if config_id:
                query += " AND f1.space_id::text = %s"
                params.append(config_id)
            else:
                query += " AND f1.path LIKE %s"
                params.append(f"%{space}%")
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
                        "is_archive": False,
                        "file_count": 0,
                        "total_size": 0,
                    }
                spaces_map[prefix]["file_count"] += 1
            spaces = sorted(spaces_map.values(), key=lambda item: item["name"].lower())

        # Log spaces for debugging PKI synchronization issues
        logger.info(f"get_spaces: Found {len(spaces)} spaces: {[space['name'] for space in spaces]}")
        
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

LOG_TIMESTAMP_RE = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
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
            "progress_hint": "",
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


def _docker_api_request(method: str, path: str) -> Dict[str, Any]:
    connection = UnixSocketHTTPConnection(DOCKER_SOCKET_PATH, timeout=10.0)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        payload = response.read()
    finally:
        connection.close()

    body: Any = None
    if payload:
        try:
            body = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = payload.decode("utf-8", errors="replace")

    return {
        "status": response.status,
        "reason": response.reason,
        "body": body,
    }


def _docker_api_raw_request(method: str, path: str) -> Dict[str, Any]:
    connection = UnixSocketHTTPConnection(DOCKER_SOCKET_PATH, timeout=10.0)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        reason = response.reason
    finally:
        connection.close()

    return {
        "status": status,
        "reason": reason,
        "body": payload,
    }


def _crawler_container_candidates() -> List[str]:
    if CRAWLER_CONTAINER_NAME:
        return [CRAWLER_CONTAINER_NAME]
    return list(DEFAULT_CRAWLER_CONTAINER_NAMES)


def _resolve_crawler_container_name() -> Optional[str]:
    if not DOCKER_SOCKET_PATH or not Path(DOCKER_SOCKET_PATH).exists():
        return None

    for container_name in _crawler_container_candidates():
        inspect_response = _docker_api_request("GET", f"/containers/{container_name}/json")
        if inspect_response["status"] < 400:
            return container_name
    return None


def _decode_docker_log_stream(payload: bytes) -> List[str]:
    if not payload:
        return []

    lines: List[str] = []
    cursor = 0
    payload_length = len(payload)

    while cursor + 8 <= payload_length:
        stream_type = payload[cursor]
        frame_size = int.from_bytes(payload[cursor + 4:cursor + 8], byteorder="big")
        frame_start = cursor + 8
        frame_end = frame_start + frame_size
        if frame_end > payload_length:
            break
        if stream_type in {1, 2}:
            chunk = payload[frame_start:frame_end].decode("utf-8", errors="replace")
            lines.extend(line for line in chunk.splitlines() if line.strip())
        cursor = frame_end

    if not lines:
        text_payload = payload.decode("utf-8", errors="replace")
        lines = [line for line in text_payload.splitlines() if line.strip()]

    return lines


def _read_crawler_docker_log_lines(limit: int = 80) -> Optional[List[str]]:
    try:
        container_name = _resolve_crawler_container_name()
        if not container_name:
            return None

        request_path = (
            f"/containers/{container_name}/logs?"
            f"stdout=1&stderr=1&timestamps=1&tail={max(1, int(limit))}"
        )
        response = _docker_api_raw_request("GET", request_path)
    except OSError as exc:
        logger.warning("Lecture docker logs indisponible: %s", exc)
        return None

    if response["status"] >= 400:
        logger.warning("Lecture docker logs impossible pour %s: %s", container_name, response)
        return None
    return _decode_docker_log_stream(response["body"])


def _read_runtime_log_lines(db: Any, limit: int = 200) -> List[str]:
    docker_log_lines = _read_crawler_docker_log_lines(limit=limit)
    if docker_log_lines is not None:
        return docker_log_lines
    return _read_log_lines(_resolve_runtime_log_path(db))


def _force_kill_crawler_container() -> bool:
    if not DOCKER_SOCKET_PATH or not Path(DOCKER_SOCKET_PATH).exists():
        logger.warning("Socket Docker introuvable, kill du crawler impossible: %s", DOCKER_SOCKET_PATH)
        return False

    container_name = _resolve_crawler_container_name()
    if not container_name:
        logger.warning("Conteneur crawler introuvable parmi: %s", ", ".join(_crawler_container_candidates()))
        return False

    inspect_response = _docker_api_request("GET", f"/containers/{container_name}/json")
    if inspect_response["status"] >= 400:
        logger.error("Inspection Docker impossible pour %s: %s", container_name, inspect_response)
        return False

    state = (inspect_response["body"] or {}).get("State") or {}
    if not state.get("Running", False):
        logger.info("Le conteneur crawler %s est deja arrete", container_name)
        return True

    kill_response = _docker_api_request("POST", f"/containers/{container_name}/kill")
    if kill_response["status"] >= 400:
        logger.error("Kill Docker impossible pour %s: %s", container_name, kill_response)
        return False

    logger.warning("Conteneur crawler %s tue par l'API apres annulation bloquee", container_name)
    return True


async def _force_stop_cancelling_run_after_delay(run_id: str, delay_seconds: int) -> None:
    await asyncio.sleep(max(delay_seconds, 1))
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        status = (db.get_crawl_run_status(run_id) or "").lower()
        if status != "cancelling":
            return

        logger.warning(
            "Run %s toujours en cancelling apres %ss, tentative de kill du crawler",
            run_id,
            delay_seconds,
        )
        if _force_kill_crawler_container():
            db.update_crawl_run_status(run_id, "cancelled")
    except Exception as exc:
        logger.error("Echec du watchdog d'annulation pour le run %s: %s", run_id, exc)


def _format_rate(value_per_second: float, suffix: str = "it/s") -> str:
    if value_per_second <= 0:
        return f"0 {suffix}"
    return f"{value_per_second:.2f} {suffix}"


def _compute_integrity_processed_items(
    runtime_metrics: Dict[str, int],
    queue_snapshot: Dict[str, int],
    large_file_metrics: Dict[str, int],
) -> int:
    normal_files_discovered = max(
        runtime_metrics["discovered_files"] - max(large_file_metrics["count"], runtime_metrics["large_files_detected"]),
        0,
    )
    return max(normal_files_discovered - queue_snapshot["checksums"], 0)


def _extract_last_progress_timestamp(log_lines: List[str]) -> Optional[datetime]:
    for line in reversed(log_lines):
        if not PROGRESS_RE.search(line):
            continue
        parsed = _extract_line_timestamp(line)
        if parsed is not None:
            return parsed
    return None


def _extract_last_log_timestamp(log_lines: List[str]) -> Optional[datetime]:
    for line in reversed(log_lines):
        parsed = _extract_line_timestamp(line)
        if parsed is not None:
            return parsed
    return None


def _extract_line_timestamp(line: str) -> Optional[datetime]:
    match = LOG_TIMESTAMP_RE.search(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _is_recent_signal(timestamp: Optional[datetime], window_seconds: int = 300) -> bool:
    if timestamp is None:
        return False
    return (datetime.utcnow() - timestamp).total_seconds() <= window_seconds


def _get_recent_write_activity_safe(db: Any, window_seconds: int = 300) -> Dict[str, Any]:
    if not hasattr(db, "get_recent_write_activity"):
        return {"recent_writes": 0, "last_write_at": None}
    try:
        return db.get_recent_write_activity(window_seconds=window_seconds)
    except Exception as exc:
        logger.warning("Sonde d'activité DB indisponible pour le runtime: %s", exc)
        return {"recent_writes": 0, "last_write_at": None}


def _translate_runtime_status(status: Optional[str], *, idle: bool = False, active: bool = False) -> str:
    normalized = (status or "").strip().lower()
    if idle:
        return "En veille"
    if active:
        return "Exploration active"
    if normalized in {"queued", "pending"}:
        return "En file"
    if normalized in {"running", "in_progress"}:
        return "En cours"
    if normalized == "cancelling":
        return "Arrêt en cours"
    if normalized == "cancelled":
        return "Arrêté"
    if normalized in {"failed", "error"}:
        return "En échec"
    if normalized in {"completed", "done", "success"}:
        return "Terminé"
    return "Explorateur inactif"


def _resolve_reconciliation_reference(
    raw_log_lines: List[str],
    latest_run_triggered_at: Optional[str],
) -> Optional[datetime]:
    last_activity = _extract_last_progress_timestamp(raw_log_lines)
    if last_activity is not None:
        return last_activity

    last_log_activity = _extract_last_log_timestamp(raw_log_lines)
    if last_log_activity is not None:
        return last_log_activity

    triggered_at = _parse_db_timestamp(latest_run_triggered_at)
    if triggered_at is None:
        return None

    return triggered_at.astimezone(timezone.utc).replace(tzinfo=None)


def _reconcile_stale_running_runs(db, raw_log_lines: List[str]) -> Dict[str, Any]:
    monitoring = db.get_monitoring_summary()
    latest_status = (monitoring.get("latest_run_status") or "").strip().lower()
    if latest_status not in ACTIVE_RUN_STATUSES:
        return monitoring

    reference_time = _resolve_reconciliation_reference(
        raw_log_lines,
        monitoring.get("latest_run_triggered_at"),
    )
    if reference_time is None:
        return monitoring

    stale_seconds = (datetime.utcnow() - reference_time).total_seconds()
    if stale_seconds <= STALE_RUN_TIMEOUT_SECONDS:
        return monitoring

    updated = 0
    if latest_status == "cancelling" and hasattr(db, "cancel_stale_cancelling_runs"):
        updated = db.cancel_stale_cancelling_runs()
        if updated:
            logger.warning(
                "Run(s) marques en cancelled apres %.1f s bloques en cancelling.",
                stale_seconds,
            )
            return db.get_monitoring_summary()
    elif latest_status in RUNNING_RUN_STATUSES and hasattr(db, "fail_active_runs"):
        updated = db.fail_active_runs()
        if updated:
            logger.warning(
                "Run(s) marques en echec apres %.1f s sans signal moteur recent.",
                stale_seconds,
            )
            return db.get_monitoring_summary()

    return monitoring


def _has_completion_markers(raw_log_lines: List[str]) -> bool:
    """Check if logs contain clear completion markers."""
    completion_patterns = [
        "🏁 Fin de crawl avec statut final=",
        "🎉 CRAWL TERMINÉ - STATISTIQUES FINALES",
        "✅ Run terminé:",
        "Worker d'exploration prêt, en attente de runs...",
    ]
    return any(pattern in line for line in raw_log_lines for pattern in completion_patterns)


def _reconcile_terminal_run_with_recent_activity(
    db,
    monitoring: Dict[str, Any],
    *,
    recent_engine_signal: bool,
    db_write_active: bool,
    raw_log_lines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    latest_status = (monitoring.get("latest_run_status") or "").strip().lower()
    has_running_run = int(monitoring.get("running_runs") or 0) > 0
    if has_running_run or latest_status not in {"failed", "error", "completed", "cancelled"}:
        return monitoring
    if not (recent_engine_signal or db_write_active):
        return monitoring
    if not hasattr(db, "revive_latest_terminal_run"):
        return monitoring

    # Check if logs show clear completion markers
    if raw_log_lines and _has_completion_markers(raw_log_lines):
        logger.info(
            "Run %s non revive: marqueurs de completion detectes dans les logs.",
            monitoring.get("latest_run_id"),
        )
        return monitoring

    revived = db.revive_latest_terminal_run()
    if not revived:
        return monitoring

    logger.warning(
        "Run %s repasse en running: activite recente detectee cote explorateur.",
        revived["run_id"],
    )
    return db.get_monitoring_summary()


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


def _build_system_status_payload() -> SystemStatus:
    try:
        from backend.src.versioning import get_current_version
        version_from_file = get_current_version()
    except ImportError:
        version_from_file = "0.4.19"

    env_type = os.getenv("OPENINDEX_ENV_TYPE", "DEV")
    build_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    timezone_name = os.getenv("OPENINDEX_TIMEZONE") or os.getenv("TZ") or "UTC"

    if os.getenv("OPENINDEX_APP_VERSION"):
        version = version_from_file
    else:
        version = version_from_file

    commit_hash = os.getenv("OPENINDEX_BUILD_COMMIT", "dev")
    build_date_iso = os.getenv("OPENINDEX_BUILD_DATE", datetime.now().date().isoformat())
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
        env_type=env_type,
        build_timestamp=build_timestamp,
        commit_hash=commit_hash,
        build_date=build_date_iso,
        timezone=timezone_name,
        license_label="Licence",
        license_owner="Copyright 2026 SMIDEN",
        repository_url=repository_url,
        newer_version_available=newer_version_available,
        newest_version_url=newest_version_url if newer_version_available else None,
    )


def _build_operational_checks(monitoring: MonitoringSummary, runtime: CrawlerRuntime) -> List[OperationalCheck]:
    checks: List[OperationalCheck] = [
        OperationalCheck(
            key="api_health",
            label="Disponibilite API",
            status="healthy",
            detail="API joignable et synthese operatoire calculee.",
        ),
        OperationalCheck(
            key="configs_defined",
            label="Configurations d'exploration",
            status="healthy" if monitoring.total_configs > 0 else "warning",
            detail=(
                f"{monitoring.total_configs} configuration(s) disponible(s)."
                if monitoring.total_configs > 0
                else "Aucune configuration d'exploration definie."
            ),
        ),
        OperationalCheck(
            key="run_failures",
            label="Runs en echec",
            status="critical" if monitoring.failed_runs > 0 else "healthy",
            detail=(
                f"{monitoring.failed_runs} run(s) en echec a traiter."
                if monitoring.failed_runs > 0
                else "Aucun run en echec detecte."
            ),
        ),
        OperationalCheck(
            key="crawler_idle",
            label="Activite crawler",
            status="critical" if runtime.idle else "healthy",
            detail=(
                runtime.progress_hint or "Aucun signal moteur recent."
                if runtime.idle
                else "Aucune derive d'activite detectee."
            ),
        ),
    ]

    active_run_count = monitoring.running_runs + monitoring.queued_runs
    checks.append(
        OperationalCheck(
            key="active_runs",
            label="Runs actifs",
            status="critical" if active_run_count > 1 else "healthy",
            detail=(
                f"{active_run_count} runs actifs ou en attente detectes."
                if active_run_count > 1
                else f"{active_run_count} run actif ou en attente."
            ),
        )
    )

    integrity_queue = next((item for item in runtime.queue_indicators if item.key == "checksums"), None)
    backlog_value = integrity_queue.value if integrity_queue else 0
    checks.append(
        OperationalCheck(
            key="integrity_backlog",
            label="Backlog d'integrite",
            status="warning" if backlog_value > 0 and not runtime.active else "healthy",
            detail=(
                f"{backlog_value} fichier(s) en attente d'integrite sans run actif."
                if backlog_value > 0 and not runtime.active
                else f"{backlog_value} fichier(s) en attente d'integrite."
            ),
        )
    )

    return checks


def _build_operational_incidents(checks: List[OperationalCheck]) -> List[OperationalIncident]:
    action_map = {
        "configs_defined": "Creer ou corriger au moins une configuration d'exploration avant nouveau lancement.",
        "run_failures": "Inspecter les logs crawler/API, corriger la cause puis relancer un run controle.",
        "crawler_idle": "Verifier le run en cours, les logs runtime et requalifier le run si necessaire.",
        "active_runs": "Verifier les runs concurrents et requalifier les etats incoherents avant merge ou exploitation.",
        "integrity_backlog": "Verifier la file d'integrite et relancer ou reprendre le crawler si le backlog n'evolue plus.",
    }
    incidents: List[OperationalIncident] = []
    for check in checks:
        if check.status == "healthy":
            continue
        incidents.append(
            OperationalIncident(
                key=check.key,
                severity=check.status,
                summary=check.label,
                detail=check.detail,
                action=action_map.get(check.key, "Verifier les journaux et la documentation operatoire."),
            )
        )
    return incidents


def _aggregate_operational_status(checks: List[OperationalCheck]) -> str:
    if any(check.status == "critical" for check in checks):
        return "critical"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "healthy"


def _slice_current_run_log_lines(raw_log_lines: List[str]) -> List[str]:
    last_run_start_index = 0
    for index, line in enumerate(raw_log_lines):
        if (
            "Démarrage de l'exploration SMB avec PostgreSQL" in line
            or "Démarrage du crawl SMB avec PostgreSQL" in line
        ):
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


@app.delete("/api/crawl-configs/{config_id}")
async def delete_crawl_config_endpoint(config_id: str):
    """Supprime une configuration de crawl"""
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        
        # Vérifier d'abord si la config existe
        config = db.get_crawl_config_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration introuvable")
        
        # Supprimer la config
        success = db.delete_crawl_config(config_id)
        if success:
            return {"success": True, "message": "Configuration supprimée avec succès"}
        else:
            raise HTTPException(status_code=500, detail="Échec de la suppression")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_crawl_config: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {e}")


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
        if (result.get("status") or "").lower() == "cancelling":
            asyncio.create_task(
                _force_stop_cancelling_run_after_delay(
                    run_id,
                    CRAWLER_FORCE_KILL_DELAY_SECONDS,
                )
            )
        return CrawlRunActionResult(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur stop_crawl_run: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'arrêt de l'exploration")


@app.post("/api/crawls/{run_id}/pending", response_model=CrawlRunActionResult)
async def mark_crawl_run_pending(run_id: str):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        result = db.mark_run_pending(run_id)
        if not result:
            raise HTTPException(status_code=409, detail="Mise en attente impossible pour ce run")
        return CrawlRunActionResult(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mark_crawl_run_pending: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise en attente du run")


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
        raw_log_lines = _read_runtime_log_lines(db, limit=400)
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
            _read_runtime_log_lines(db, limit=400),
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
        return _build_system_status_payload()
    except Exception as e:
        logger.error(f"Erreur get_system_status: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du statut système")


@app.get("/api/crawler/runtime", response_model=CrawlerRuntime)
async def get_crawler_runtime(log_limit: int = 80):
    try:
        db = get_db_adapter()
        ensure_crawl_storage_ready(db)
        log_path = _resolve_runtime_log_path(db)
        docker_log_lines = _read_crawler_docker_log_lines(limit=max(log_limit * 3, 200))
        raw_log_lines = docker_log_lines if docker_log_lines is not None else _read_log_lines(log_path)
        current_run_log_lines = _slice_current_run_log_lines(raw_log_lines)
        monitoring = _reconcile_stale_running_runs(db, current_run_log_lines)
        log_lines = [_normalize_runtime_log_line(line) for line in current_run_log_lines[-log_limit:]]
        runtime_metrics = _extract_runtime_metrics(log_lines)
        large_file_metrics = _extract_large_file_metrics(current_run_log_lines)
        queue_snapshot = _extract_queue_snapshot(log_lines)
        last_progress_activity = _extract_last_progress_timestamp(current_run_log_lines)
        last_engine_signal = _extract_last_log_timestamp(current_run_log_lines)
        last_activity = last_progress_activity or last_engine_signal
        has_running_run = monitoring["running_runs"] > 0
        started_at = _parse_db_timestamp(monitoring.get("latest_run_triggered_at"))
        recent_engine_signal = _is_recent_signal(last_engine_signal)
        db_activity = _get_recent_write_activity_safe(db, window_seconds=300)
        db_last_write = db_activity.get("last_write_at")
        db_last_write_utc: Optional[datetime] = None
        if isinstance(db_last_write, datetime):
            db_last_write_utc = (
                db_last_write.astimezone(timezone.utc).replace(tzinfo=None)
                if db_last_write.tzinfo
                else db_last_write
            )
        db_recent_writes = int(db_activity.get("recent_writes") or 0)
        db_write_active = db_recent_writes > 0 and _is_recent_signal(db_last_write_utc)
        monitoring = _reconcile_terminal_run_with_recent_activity(
            db,
            monitoring,
            recent_engine_signal=recent_engine_signal,
            db_write_active=db_write_active,
            raw_log_lines=current_run_log_lines,
        )
        has_running_run = monitoring["running_runs"] > 0
        idle = False
        if has_running_run and (recent_engine_signal or db_write_active):
            idle = False
        elif has_running_run and last_activity is not None:
            idle = (datetime.utcnow() - last_activity).total_seconds() > 300
        elif has_running_run and not log_lines:
            idle = True

        residual_activity = (recent_engine_signal or db_write_active) and not has_running_run
        runtime_active = (has_running_run and not idle) or residual_activity
        latest_status = monitoring["latest_run_status"]
        normalized_status = (latest_status or "").strip().lower()
        status_label = _translate_runtime_status(latest_status, idle=idle, active=runtime_active)
        activity_warning = ""
        if normalized_status in {"failed", "error", "completed", "cancelled"} and (recent_engine_signal or db_write_active):
            status_label = "Statut incohérent, activité détectée"
            activity_warning = (
                "Le run est marqué terminé ou en échec, mais le moteur ou la base montrent encore une activité récente."
            )
        elif has_running_run and idle:
            activity_warning = "Le run est toujours enregistré comme actif, mais aucun signal récent n'a été vu."

        db_activity_hint = (
            f"{db_recent_writes} écriture(s) DB observée(s) sur les 5 dernières minutes."
            if db_recent_writes > 0 and db_last_write_utc is not None
            else ""
        )

        files_rate = _compute_rate(runtime_metrics["discovered_files"], started_at) if has_running_run else 0.0
        directories_rate = _compute_rate(runtime_metrics["discovered_directories"], started_at) if has_running_run else 0.0
        processed_volume_rate = _compute_rate(runtime_metrics["processed_bytes"], started_at) if has_running_run else 0.0
        integrity_processed_items = _compute_integrity_processed_items(
            runtime_metrics,
            queue_snapshot,
            large_file_metrics,
        )
        integrity_rate = _compute_rate(integrity_processed_items, started_at) if has_running_run else 0.0

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
                detail=f"Fichiers normaux en attente ({_format_rate(integrity_rate)})",
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
                detail=f"Débit actuel ({_format_rate(integrity_rate)})",
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
            active=runtime_active,
            idle=idle,
            latest_status=latest_status,
            latest_config_name=monitoring["latest_run_config_name"],
            status_label=status_label,
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
            last_engine_signal_at=last_engine_signal.isoformat() if last_engine_signal else None,
            db_write_active=db_write_active,
            db_recent_writes=db_recent_writes,
            db_last_write_at=db_last_write_utc.isoformat() if db_last_write_utc else None,
            db_activity_hint=db_activity_hint,
            activity_warning=activity_warning,
            progress_indicators=progress_indicators,
            queue_indicators=queue_indicators,
            log_lines=log_lines,
            log_source=(
                f"docker:{_resolve_crawler_container_name()}"
                if docker_log_lines is not None
                else str(log_path)
            ),
        )
    except Exception as e:
        logger.error(f"Erreur get_crawler_runtime: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du runtime explorateur")


@app.get("/api/operations/status", response_model=OperationsStatus)
async def get_operations_status(log_limit: int = 80):
    try:
        monitoring = await get_monitoring_summary()
        runtime = await get_crawler_runtime(log_limit=log_limit)
        system_status = _build_system_status_payload()
        checks = _build_operational_checks(monitoring, runtime)
        incidents = _build_operational_incidents(checks)
        return OperationsStatus(
            status=_aggregate_operational_status(checks),
            generated_at=datetime.now(timezone.utc).isoformat(),
            system_status=system_status,
            monitoring=monitoring,
            runtime=runtime,
            checks=checks,
            incidents=incidents,
        )
    except Exception as e:
        logger.error(f"Erreur get_operations_status: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du statut operatoire")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(5)
            try:
                db = get_db_adapter()
                stats = db.get_statistics()
                sent = await manager.send_personal_message(
                    WebSocketMessage(type="stats_update", data=stats, timestamp=datetime.now()).json(),
                    websocket,
                )
                if not sent:
                    break
                if hasattr(db, "get_monitoring_summary"):
                    sent = await manager.send_personal_message(
                        WebSocketMessage(
                            type="monitoring_update",
                            data=db.get_monitoring_summary(),
                            timestamp=datetime.now(),
                        ).json(),
                        websocket,
                    )
                    if not sent:
                        break
            except Exception as e:
                logger.error(f"Erreur WebSocket stats: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html><head><title>OpenIndex API</title><meta charset="utf-8"></head>
    <body><h1>🚀 OpenIndex API</h1><p><a href="/docs">Swagger UI</a></p></body></html>
    """


# ============================================================
# T-ARCH-01: Archive Queue API Endpoints
# ============================================================

def _row_to_archive_job_response(row: tuple) -> ArchiveJobResponse:
    """Convertit une ligne de résultat SQL en ArchiveJobResponse"""
    return ArchiveJobResponse(
        id=str(row[0]),
        job_type=row[1],
        source_path=row[2],
        dest_path=row[3],
        status=row[4],
        priority=row[5],
        retry_count=row[6],
        max_retries=row[7],
        error_message=row[8],
        started_at=row[9].isoformat() if row[9] else None,
        completed_at=row[10].isoformat() if row[10] else None,
        created_at=row[11].isoformat() if row[11] else None,
        source_size=row[12],
        bytes_transferred=row[13] if len(row) > 13 else 0
    )


@app.post("/api/archive/queue", response_model=ArchiveJobResponse)
async def create_archive_job(payload: ArchiveJobCreate):
    """Crée un nouveau job d'archivage dans la queue"""
    try:
        db = get_db_adapter()
        
        # Validation: dest_path requis pour copy/move
        if payload.job_type in [ArchiveJobType.COPY, ArchiveJobType.MOVE] and not payload.dest_path:
            raise HTTPException(
                status_code=422,
                detail=f"dest_path est requis pour le job_type '{payload.job_type.value}'"
            )
        
        # Insérer le job
        query = """
            INSERT INTO archive_jobs (
                job_type, source_path, dest_path, status, priority,
                retry_count, max_retries, created_at, updated_at
            ) VALUES (
                %s::archive_job_type, %s, %s, 'pending', %s,
                0, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id, job_type::text, source_path, dest_path, status::text, priority,
                      retry_count, max_retries, error_message, started_at, completed_at,
                      created_at, source_size, bytes_transferred
        """
        
        results = db.execute_query(
            query,
            [
                payload.job_type.value,
                payload.source_path,
                payload.dest_path,
                payload.priority
            ]
        )
        
        if not results:
            raise HTTPException(status_code=500, detail="Échec de la création du job")
        
        job = _row_to_archive_job_response(results[0])
        logger.info(f"📦 Archive job created: {job.id} ({job.job_type}: {job.source_path})")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur create_archive_job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du job: {e}")


@app.get("/api/archive/queue", response_model=ArchiveJobList)
async def list_archive_jobs(
    status: Optional[str] = Query(default=None, description="Filtrer par statut: pending, running, completed, failed, cancelled"),
    job_type: Optional[str] = Query(default=None, description="Filtrer par type: copy, move, delete"),
    priority: Optional[int] = Query(default=None, ge=1, le=10, description="Filtrer par priorité exacte"),
    limit: int = Query(default=50, ge=1, le=1000, description="Nombre maximum de résultats"),
    offset: int = Query(default=0, ge=0, description="Offset pour pagination"),
    sort: str = Query(default="created_at", description="Champ de tri: created_at, priority, status"),
    order: str = Query(default="desc", description="Ordre: asc, desc")
):
    """Liste les jobs d'archivage avec pagination et filtrage"""
    try:
        db = get_db_adapter()
        
        # Construire la clause WHERE
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = %s::archive_job_status")
            params.append(status)
        
        if job_type:
            where_conditions.append("job_type = %s::archive_job_type")
            params.append(job_type)
        
        if priority is not None:
            where_conditions.append("priority = %s")
            params.append(priority)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Validation du champ de tri
        allowed_sort_fields = {"created_at", "priority", "status", "updated_at", "started_at"}
        if sort not in allowed_sort_fields:
            sort = "created_at"
        
        order_clause = "DESC" if order.lower() == "desc" else "ASC"
        
        # Requête pour les jobs
        query = f"""
            SELECT id, job_type::text, source_path, dest_path, status::text, priority,
                   retry_count, max_retries, error_message, started_at, completed_at,
                   created_at, source_size, bytes_transferred
            FROM archive_jobs
            {where_clause}
            ORDER BY {sort} {order_clause}
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        results = db.execute_query(query, params)
        
        # Requête pour le total
        count_query = f"""
            SELECT COUNT(*) FROM archive_jobs {where_clause}
        """
        count_params = params[:-2]  # Exclure limit et offset
        count_results = db.execute_query(count_query, count_params)
        total = count_results[0][0] if count_results else 0
        
        jobs = [_row_to_archive_job_response(row) for row in results]
        
        return ArchiveJobList(jobs=jobs, total=total)
        
    except Exception as e:
        logger.error(f"Erreur list_archive_jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des jobs: {e}")


@app.get("/api/archive/queue/stats", response_model=ArchiveJobStats)
async def get_archive_job_stats():
    """Récupère les statistiques de la queue d'archivage"""
    try:
        db = get_db_adapter()

        query = """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending,
                COALESCE(SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END), 0) as running,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed,
                COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) as cancelled,
                COALESCE(SUM(CASE WHEN status = 'pending' THEN COALESCE(source_size, 0) ELSE 0 END), 0) as total_size_pending,
                COALESCE(SUM(bytes_transferred), 0) as total_size_transferred
            FROM archive_jobs
        """

        results = db.execute_query(query)

        if not results:
            return ArchiveJobStats(
                pending=0, running=0, completed=0, failed=0, cancelled=0,
                total_size_pending=0, total_size_transferred=0
            )

        row = results[0]
        return ArchiveJobStats(
            pending=row[0],
            running=row[1],
            completed=row[2],
            failed=row[3],
            cancelled=row[4],
            total_size_pending=row[5],
            total_size_transferred=row[6]
        )

    except Exception as e:
        logger.error(f"Erreur get_archive_job_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {e}")


@app.get("/api/archive/queue/{job_id}", response_model=ArchiveJobResponse)
async def get_archive_job(job_id: str):
    """Récupère les détails d'un job d'archivage spécifique"""
    try:
        db = get_db_adapter()

        query = """
            SELECT id, job_type::text, source_path, dest_path, status::text, priority,
                   retry_count, max_retries, error_message, started_at, completed_at,
                   created_at, source_size, bytes_transferred
            FROM archive_jobs
            WHERE id = %s
        """

        results = db.execute_query(query, [job_id])

        if not results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} introuvable")

        return _row_to_archive_job_response(results[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_archive_job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du job: {e}")


@app.delete("/api/archive/queue/{job_id}", response_model=ArchiveJobActionResult)
async def cancel_archive_job(job_id: str):
    """Annule un job d'archivage (si en attente ou en cours)"""
    try:
        db = get_db_adapter()
        
        # Vérifier le statut actuel
        check_query = "SELECT status::text FROM archive_jobs WHERE id = %s"
        check_results = db.execute_query(check_query, [job_id])
        
        if not check_results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} introuvable")
        
        current_status = check_results[0][0]
        
        # Vérifier si le job peut être annulé
        if current_status in ["completed", "failed", "cancelled"]:
            return ArchiveJobActionResult(
                job_id=job_id,
                success=False,
                message=f"Job déjà terminé avec statut '{current_status}'"
            )
        
        # Annuler le job
        update_query = """
            UPDATE archive_jobs
            SET status = 'cancelled',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        
        db.execute_query(update_query, [job_id])
        
        logger.info(f"🚫 Archive job cancelled: {job_id}")
        
        return ArchiveJobActionResult(
            job_id=job_id,
            success=True,
            message="Job annulé avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur cancel_archive_job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'annulation du job: {e}")


@app.post("/api/archive/queue/{job_id}/retry", response_model=ArchiveJobActionResult)
async def retry_archive_job(job_id: str):
    """Réinitialise un job échoué pour qu'il soit réessayé"""
    try:
        db = get_db_adapter()
        
        # Vérifier le statut actuel
        check_query = "SELECT status::text FROM archive_jobs WHERE id = %s"
        check_results = db.execute_query(check_query, [job_id])
        
        if not check_results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} introuvable")
        
        current_status = check_results[0][0]
        
        # Vérifier si le job peut être réessayé
        if current_status not in ["failed", "cancelled"]:
            return ArchiveJobActionResult(
                job_id=job_id,
                success=False,
                message=f"Job ne peut pas être réessayé (statut: '{current_status}')"
            )
        
        # Réinitialiser le job
        update_query = """
            UPDATE archive_jobs
            SET status = 'pending',
                retry_count = 0,
                error_message = NULL,
                started_at = NULL,
                completed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        
        db.execute_query(update_query, [job_id])
        
        logger.info(f"🔄 Archive job reset for retry: {job_id}")
        
        return ArchiveJobActionResult(
            job_id=job_id,
            success=True,
            message="Job réinitialisé pour retry"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur retry_archive_job: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du retry du job: {e}")


# ============================================================
# T-ARCH-02: Archive Scheduling API Endpoints
# ============================================================

class ArchiveScheduleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cron_expression: str = Field(..., description="Expression cron (ex: '0 2 * * *')")
    timezone: str = Field(default="Europe/Paris")
    job_type: ArchiveJobType
    source_pattern: str = Field(..., description="Pattern de fichiers (ex: '\\\\server\\share\\*.txt')")
    dest_path: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    max_age_days: Optional[int] = None
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    file_extensions: Optional[List[str]] = None


class ArchiveScheduleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    is_active: bool
    job_type: str
    source_pattern: str
    dest_path: Optional[str]
    priority: int
    max_age_days: Optional[int]
    min_size_bytes: Optional[int]
    max_size_bytes: Optional[int]
    file_extensions: Optional[List[str]]
    created_at: str
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    run_count: int


class ArchiveScheduleRun(BaseModel):
    id: str
    schedule_id: Optional[str]
    schedule_name: Optional[str]
    started_at: str
    completed_at: Optional[str]
    status: str
    jobs_created: int
    jobs_completed: int
    jobs_failed: int
    total_bytes_processed: int
    error_message: Optional[str]


class ArchiveSettings(BaseModel):
    default_priority: int = 5
    max_retries: int = 3
    worker_poll_interval: int = 5
    worker_max_concurrent: int = 3
    retention_days: int = 30
    cleanup_interval_hours: int = 24


class ArchiveQueueMonitoring(BaseModel):
    id: str
    job_type: str
    source_path: str
    dest_path: Optional[str]
    status: str
    status_label: str
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    source_size: Optional[int]
    bytes_transferred: int
    duration_seconds: Optional[float]
    progress_percent: float


def get_scheduler():
    """Factory pour obtenir l'instance du scheduler"""
    from backend.src.workers.archive_scheduler import ArchiveScheduler
    return ArchiveScheduler()


@app.post("/api/archive/schedules", response_model=ArchiveScheduleResponse)
async def create_archive_schedule(payload: ArchiveScheduleCreate):
    """Crée une nouvelle tâche planifiée d'archivage"""
    try:
        scheduler = get_scheduler()
        
        config = {
            'name': payload.name,
            'description': payload.description,
            'cron_expression': payload.cron_expression,
            'timezone': payload.timezone,
            'is_active': True,
            'job_type': payload.job_type.value,
            'source_pattern': payload.source_pattern,
            'dest_path': payload.dest_path,
            'priority': payload.priority,
            'max_age_days': payload.max_age_days,
            'min_size_bytes': payload.min_size_bytes,
            'max_size_bytes': payload.max_size_bytes,
            'file_extensions': payload.file_extensions or [],
            'created_by': 'api'
        }
        
        schedule_id = scheduler.create_schedule(config)
        
        # Récupérer le schedule créé
        schedules = scheduler.get_schedules()
        for schedule in schedules:
            if schedule['id'] == schedule_id:
                return ArchiveScheduleResponse(**schedule)
        
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du schedule créé")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur create_archive_schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du schedule: {e}")


@app.get("/api/archive/schedules", response_model=List[ArchiveScheduleResponse])
async def list_archive_schedules(active_only: bool = False):
    """Liste les tâches planifiées d'archivage"""
    try:
        scheduler = get_scheduler()
        schedules = scheduler.get_schedules(active_only=active_only)
        return [ArchiveScheduleResponse(**s) for s in schedules]
        
    except Exception as e:
        logger.error(f"Erreur list_archive_schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des schedules: {e}")


@app.get("/api/archive/schedules/{schedule_id}", response_model=ArchiveScheduleResponse)
async def get_archive_schedule(schedule_id: str):
    """Récupère les détails d'une tâche planifiée"""
    try:
        scheduler = get_scheduler()
        schedules = scheduler.get_schedules()
        
        for schedule in schedules:
            if schedule['id'] == schedule_id:
                return ArchiveScheduleResponse(**schedule)
        
        raise HTTPException(status_code=404, detail="Schedule introuvable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_archive_schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du schedule: {e}")


@app.put("/api/archive/schedules/{schedule_id}")
async def update_archive_schedule(schedule_id: str, payload: ArchiveScheduleCreate):
    """Met à jour une tâche planifiée"""
    try:
        scheduler = get_scheduler()
        
        updates = {
            'name': payload.name,
            'description': payload.description,
            'cron_expression': payload.cron_expression,
            'timezone': payload.timezone,
            'job_type': payload.job_type.value,
            'source_pattern': payload.source_pattern,
            'dest_path': payload.dest_path,
            'priority': payload.priority,
            'max_age_days': payload.max_age_days,
            'min_size_bytes': payload.min_size_bytes,
            'max_size_bytes': payload.max_size_bytes,
            'file_extensions': payload.file_extensions or []
        }
        
        success = scheduler.update_schedule(schedule_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        return {"success": True, "message": "Schedule mis à jour"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update_archive_schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour du schedule: {e}")


@app.delete("/api/archive/schedules/{schedule_id}")
async def delete_archive_schedule(schedule_id: str):
    """Supprime une tâche planifiée"""
    try:
        scheduler = get_scheduler()
        success = scheduler.delete_schedule(schedule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        return {"success": True, "message": "Schedule supprimé"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_archive_schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression du schedule: {e}")


@app.post("/api/archive/schedules/{schedule_id}/toggle")
async def toggle_archive_schedule(schedule_id: str):
    """Active/désactive une tâche planifiée"""
    try:
        scheduler = get_scheduler()
        
        # Récupérer le statut actuel
        schedules = scheduler.get_schedules()
        current = None
        for s in schedules:
            if s['id'] == schedule_id:
                current = s
                break
        
        if not current:
            raise HTTPException(status_code=404, detail="Schedule introuvable")
        
        new_status = not current['is_active']
        success = scheduler.update_schedule(schedule_id, {'is_active': new_status})
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")
        
        status_text = "activé" if new_status else "désactivé"
        return {"success": True, "message": f"Schedule {status_text}", "is_active": new_status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur toggle_archive_schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/archive/schedules/{schedule_id}/runs", response_model=List[ArchiveScheduleRun])
async def get_archive_schedule_runs(schedule_id: str, limit: int = 10):
    """Récupère l'historique des exécutions d'un schedule"""
    try:
        scheduler = get_scheduler()
        runs = scheduler.get_schedule_runs(schedule_id=schedule_id, limit=limit)
        return [ArchiveScheduleRun(**r) for r in runs]
        
    except Exception as e:
        logger.error(f"Erreur get_archive_schedule_runs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/archive/monitoring/queue", response_model=List[ArchiveQueueMonitoring])
async def get_archive_queue_monitoring(
    status: Optional[str] = Query(default=None, description="Filtrer par statut"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Récupère la vue de monitoring temps réel de la queue"""
    try:
        db = get_db_adapter()
        
        where_clause = "WHERE status_label = %s" if status else ""
        params = (status,) if status else ()
        params += (limit,)
        
        query = f"""
            SELECT id, job_type, source_path, dest_path, status, status_label, priority,
                   retry_count, max_retries, error_message, created_at, started_at, completed_at,
                   source_size, bytes_transferred, duration_seconds, progress_percent
            FROM archive_queue_monitoring
            {where_clause}
            LIMIT %s
        """
        
        results = db.execute_query(query, params)
        
        monitoring = []
        for row in results:
            monitoring.append(ArchiveQueueMonitoring(
                id=str(row[0]),
                job_type=row[1],
                source_path=row[2],
                dest_path=row[3],
                status=row[4],
                status_label=row[5],
                priority=row[6],
                retry_count=row[7],
                max_retries=row[8],
                error_message=row[9],
                created_at=row[10].isoformat() if row[10] else None,
                started_at=row[11].isoformat() if row[11] else None,
                completed_at=row[12].isoformat() if row[12] else None,
                source_size=row[13],
                bytes_transferred=row[14] or 0,
                duration_seconds=row[15],
                progress_percent=row[16] or 0
            ))
        
        return monitoring
        
    except Exception as e:
        logger.error(f"Erreur get_archive_queue_monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/archive/monitoring/dashboard")
async def get_archive_dashboard():
    """Récupère les données agrégées pour le dashboard de monitoring"""
    try:
        db = get_db_adapter()
        
        # Stats par statut
        status_stats = db.execute_query(
            "SELECT status::text, COUNT(*), SUM(bytes_transferred) FROM archive_jobs GROUP BY status"
        )
        
        # Stats des 24 dernières heures
        recent_stats = db.execute_query(
            """
            SELECT 
                COUNT(*) FILTER (WHERE status = 'completed') as completed_24h,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_24h,
                SUM(bytes_transferred) FILTER (WHERE status = 'completed') as bytes_24h
            FROM archive_jobs
            WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """
        )
        
        # Taux de succès global
        success_rate_query = """
            SELECT 
                COUNT(*) FILTER (WHERE status = 'completed') as completed_total,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_total,
                COUNT(*) as total
            FROM archive_jobs
        """
        success_results = db.execute_query(success_rate_query)
        completed_total, failed_total, total_jobs = success_results[0] if success_results else (0, 0, 0)
        
        success_rate = completed_total / (completed_total + failed_total) if (completed_total + failed_total) > 0 else 0
        
        # Schedules actifs
        scheduler = get_scheduler()
        active_schedules = len(scheduler.get_schedules(active_only=True))
        
        return {
            "queue_status": {
                stat[0]: {"count": stat[1], "bytes_transferred": stat[2] or 0}
                for stat in status_stats
            },
            "recent_activity": {
                "completed_24h": recent_stats[0][0] if recent_stats else 0,
                "failed_24h": recent_stats[0][1] if recent_stats else 0,
                "bytes_transferred_24h": recent_stats[0][2] or 0 if recent_stats else 0
            },
            "overall_success_rate": round(success_rate, 4),
            "total_jobs": total_jobs,
            "active_schedules": active_schedules,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur get_archive_dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.get("/api/archive/settings", response_model=ArchiveSettings)
async def get_archive_settings():
    """Récupère les paramètres d'archivage"""
    try:
        scheduler = get_scheduler()
        settings = scheduler.get_settings()
        
        return ArchiveSettings(
            default_priority=int(settings.get('archive.default_priority', 5)),
            max_retries=int(settings.get('archive.max_retries', 3)),
            worker_poll_interval=int(settings.get('archive.worker.poll_interval', 5)),
            worker_max_concurrent=int(settings.get('archive.worker.max_concurrent', 3)),
            retention_days=int(settings.get('archive.retention_days', 30)),
            cleanup_interval_hours=int(settings.get('archive.cleanup_interval_hours', 24))
        )
        
    except Exception as e:
        logger.error(f"Erreur get_archive_settings: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


@app.put("/api/archive/settings")
async def update_archive_settings(payload: ArchiveSettings):
    """Met à jour les paramètres d'archivage"""
    try:
        scheduler = get_scheduler()
        
        settings_map = {
            'archive.default_priority': str(payload.default_priority),
            'archive.max_retries': str(payload.max_retries),
            'archive.worker.poll_interval': str(payload.worker_poll_interval),
            'archive.worker.max_concurrent': str(payload.worker_max_concurrent),
            'archive.retention_days': str(payload.retention_days),
            'archive.cleanup_interval_hours': str(payload.cleanup_interval_hours)
        }
        
        for key, value in settings_map.items():
            scheduler.update_setting(key, value, updated_by='api')
        
        return {"success": True, "message": "Paramètres mis à jour"}
        
    except Exception as e:
        logger.error(f"Erreur update_archive_settings: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


# ============================================================
# T-ARCH-01: Transfer Worker Health Endpoint
# ============================================================

@app.get("/api/transfer/worker/health")
async def get_transfer_worker_health():
    """Récupère l'état de santé du transfer worker"""
    try:
        db = get_db_adapter()
        
        # Vérifier si des jobs sont en cours
        running_count = db.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE status = 'running'"
        )[0][0]
        
        # Vérifier la taille de la queue
        pending_count = db.execute_query(
            "SELECT COUNT(*) FROM archive_jobs WHERE status = 'pending'"
        )[0][0]
        
        # Calculer le taux de réussite récent (dernières 24h)
        stats_query = """
            SELECT 
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) as total
            FROM archive_jobs
            WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """
        stats_results = db.execute_query(stats_query)
        completed, failed, total = stats_results[0] if stats_results else (0, 0, 0)
        
        success_rate = completed / total if total > 0 else 1.0
        
        status = "healthy"
        if failed > completed * 2:  # Plus de 2x d'échecs que de succès
            status = "degraded"
        if running_count == 0 and pending_count > 100:  # Queue bloquée
            status = "unhealthy"
        
        return {
            "status": status,
            "running_jobs": running_count,
            "pending_jobs": pending_count,
            "success_rate_24h": success_rate,
            "completed_24h": completed,
            "failed_24h": failed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur get_transfer_worker_health: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la santé du worker: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
