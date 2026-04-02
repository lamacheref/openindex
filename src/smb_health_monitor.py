#!/usr/bin/env python3
"""
SMB Health Monitor - Surveillance de l'état des serveurs SMB
"""

import threading
import time
import logging
from enum import Enum
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import smbclient
from smbprotocol.exceptions import SMBConnectionError


class SMBServerStatus(Enum):
    """États possibles d'un serveur SMB."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"  # Répond mais avec latence élevée


@dataclass
class SMBServerState:
    """État courant d'un serveur SMB."""
    server: str
    status: SMBServerStatus
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    response_time_ms: float = 0.0
    error_message: Optional[str] = None


class SMBHealthMonitor:
    """
    Monitors the health of SMB servers with automatic detection
    of outages and recovery.
    """

    def __init__(
        self,
        check_interval: int = 30,
        failure_threshold: int = 3,
        timeout: int = 10,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the SMB health monitor.

        Args:
            check_interval: Seconds between health checks
            failure_threshold: Number of consecutive failures before marking offline
            timeout: Connection timeout in seconds
            logger: Optional logger instance
        """
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        # Server states: {server_address: SMBServerState}
        self._servers: Dict[str, SMBServerState] = {}
        self._lock = threading.RLock()

        # Callbacks for state changes
        self._on_server_down: List[Callable[[str], None]] = []
        self._on_server_up: List[Callable[[str], None]] = []
        self._on_status_change: List[Callable[[str, SMBServerStatus], None]] = []

        # Control flags
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._is_running = False

    def add_server(self, server: str, username: str = "", password: str = "", domain: str = "") -> None:
        """Add a server to monitor."""
        with self._lock:
            if server not in self._servers:
                self._servers[server] = SMBServerState(
                    server=server,
                    status=SMBServerStatus.UNKNOWN
                )
                self.logger.info(f"Added server to monitoring: {server}")

    def remove_server(self, server: str) -> None:
        """Remove a server from monitoring."""
        with self._lock:
            if server in self._servers:
                del self._servers[server]
                self.logger.info(f"Removed server from monitoring: {server}")

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for server state changes.

        Events:
            - 'server_down': Called when server goes offline
            - 'server_up': Called when server comes back online
            - 'status_change': Called on any status change
        """
        if event == 'server_down':
            self._on_server_down.append(callback)
        elif event == 'server_up':
            self._on_server_up.append(callback)
        elif event == 'status_change':
            self._on_status_change.append(callback)
        else:
            raise ValueError(f"Unknown event: {event}")

    def unregister_callback(self, event: str, callback: Callable) -> None:
        """Unregister a callback."""
        if event == 'server_down':
            self._on_server_down.remove(callback)
        elif event == 'server_up':
            self._on_server_up.remove(callback)
        elif event == 'status_change':
            self._on_status_change.remove(callback)

    def start(self) -> None:
        """Start the monitoring thread."""
        if self._is_running:
            self.logger.warning("Monitor already running")
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._is_running = True
        self.logger.info("SMB Health Monitor started")

    def stop(self) -> None:
        """Stop the monitoring thread."""
        if not self._is_running:
            return

        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self._is_running = False
        self.logger.info("SMB Health Monitor stopped")

    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._is_running

    def get_server_status(self, server: str) -> Optional[SMBServerStatus]:
        """Get current status of a server."""
        with self._lock:
            state = self._servers.get(server)
            return state.status if state else None

    def get_all_statuses(self) -> Dict[str, SMBServerStatus]:
        """Get all server statuses."""
        with self._lock:
            return {server: state.status for server, state in self._servers.items()}

    def is_server_healthy(self, server: str) -> bool:
        """Check if a server is considered healthy."""
        status = self.get_server_status(server)
        return status == SMBServerStatus.ONLINE

    def check_server_now(self, server: str) -> SMBServerState:
        """Perform an immediate health check on a server."""
        with self._lock:
            if server not in self._servers:
                raise ValueError(f"Server not registered: {server}")
            return self._check_server_health(server)

    def _check_server_health(self, server: str) -> SMBServerState:
        """Perform health check on a single server."""
        state = self._servers[server]
        start_time = time.time()

        try:
            # Attempt to list root of server to verify connectivity
            smbclient.ClientConfig(connection_timeout=self.timeout)
            # Just try to connect to the server root
            smbclient.listdir(f"\\\\{server}")

            response_time = (time.time() - start_time) * 1000  # ms

            # Update state on success
            state.last_success = datetime.now()
            state.response_time_ms = response_time
            state.consecutive_failures = 0
            state.error_message = None

            # Check if recovering from offline
            old_status = state.status
            if old_status in (SMBServerStatus.OFFLINE, SMBServerStatus.UNKNOWN):
                state.status = SMBServerStatus.ONLINE
                self._trigger_callbacks('server_up', server)
                self.logger.info(
                    f"Server {server} is BACK ONLINE (response: {response_time:.1f}ms)"
                )
            elif old_status != SMBServerStatus.ONLINE:
                state.status = SMBServerStatus.ONLINE
                self.logger.info(f"Server {server} status: ONLINE")

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            state.response_time_ms = response_time
            state.last_failure = datetime.now()
            state.consecutive_failures += 1
            state.error_message = str(e)

            # Check if should mark as offline
            old_status = state.status
            if state.consecutive_failures >= self.failure_threshold:
                if old_status != SMBServerStatus.OFFLINE:
                    state.status = SMBServerStatus.OFFLINE
                    self._trigger_callbacks('server_down', server)
                    self.logger.error(
                        f"Server {server} is OFFLINE ({state.consecutive_failures} "
                        f"consecutive failures): {e}"
                    )
            elif old_status == SMBServerStatus.ONLINE:
                # Degraded but not yet offline
                state.status = SMBServerStatus.DEGRADED
                self.logger.warning(
                    f"Server {server} is DEGRADED (failure {state.consecutive_failures}/"
                    f"{self.failure_threshold}): {e}"
                )

        state.last_check = datetime.now()
        return state

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in separate thread."""
        self.logger.info("Monitor loop started")

        while not self._stop_event.is_set():
            try:
                with self._lock:
                    servers = list(self._servers.keys())

                for server in servers:
                    if self._stop_event.is_set():
                        break

                    old_status = self.get_server_status(server)
                    new_state = self._check_server_health(server)

                    # Trigger status change callback if changed
                    if old_status != new_state.status:
                        self._trigger_callbacks('status_change', server, new_state.status)

                    # Small delay between checks to avoid overwhelming network
                    time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")

            # Wait for next check cycle
            self._stop_event.wait(self.check_interval)

        self.logger.info("Monitor loop ended")

    def _trigger_callbacks(self, event: str, server: str, status=None) -> None:
        """Trigger registered callbacks for an event."""
        callbacks = []
        if event == 'server_down':
            callbacks = self._on_server_down
        elif event == 'server_up':
            callbacks = self._on_server_up
        elif event == 'status_change':
            callbacks = self._on_status_change

        for callback in callbacks:
            try:
                if event == 'status_change':
                    callback(server, status)
                else:
                    callback(server)
            except Exception as e:
                self.logger.error(f"Callback error for {event}: {e}")


class SMBHealthMonitorContext:
    """Context manager for easy monitor usage."""

    def __init__(self, monitor: SMBHealthMonitor, servers: List[str] = None):
        self.monitor = monitor
        self.servers = servers or []

    def __enter__(self):
        for server in self.servers:
            self.monitor.add_server(server)
        self.monitor.start()
        return self.monitor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.stop()
        return False
