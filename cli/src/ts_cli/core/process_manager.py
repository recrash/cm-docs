"""
Cross-platform process management for preventing duplicate CLI instances.

This module provides platform-specific implementations for:
- Detecting existing CLI processes
- Preventing duplicate session execution
- Gracefully terminating previous instances
- Managing session registry
"""

import os
import sys
import signal
import time
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Session information for tracking active processes."""
    session_id: str
    pid: int
    repo_path: str
    start_time: datetime
    status: str = "active"  # active, completed, failed


class BaseProcessManager(ABC):
    """Abstract base class for platform-specific process managers."""

    def __init__(self, session_id: str, repo_path: str):
        self.session_id = session_id
        self.repo_path = repo_path
        self.session_info = SessionInfo(
            session_id=session_id,
            pid=os.getpid(),
            repo_path=repo_path,
            start_time=datetime.now()
        )

    @abstractmethod
    def check_existing_process(self) -> Optional[SessionInfo]:
        """Check if there's an existing process for this session."""
        pass

    @abstractmethod
    def terminate_existing_process(self, session_info: SessionInfo) -> bool:
        """Terminate an existing process gracefully."""
        pass

    @abstractmethod
    def register_session(self) -> bool:
        """Register current session in the system."""
        pass

    @abstractmethod
    def cleanup_session(self) -> bool:
        """Clean up session resources."""
        pass

    def get_session_registry_path(self) -> Path:
        """Get platform-appropriate session registry path."""
        if sys.platform == "win32":
            # Windows: Use APPDATA
            base_path = Path(os.environ.get('APPDATA', Path.home()))
        else:
            # Unix-like: Use home directory
            base_path = Path.home()

        return base_path / ".testscenariomaker" / "sessions"

    def load_session_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load existing session registry."""
        registry_path = self.get_session_registry_path()
        registry_file = registry_path / "registry.json"

        if not registry_file.exists():
            return {}

        try:
            with open(registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert datetime strings back to datetime objects
                for session_id, info in data.items():
                    if 'start_time' in info:
                        info['start_time'] = datetime.fromisoformat(info['start_time'])
                return data
        except Exception as e:
            logger.warning(f"Failed to load session registry: {e}")
            return {}

    def save_session_registry(self, registry: Dict[str, Dict[str, Any]]) -> bool:
        """Save session registry to disk."""
        registry_path = self.get_session_registry_path()
        registry_file = registry_path / "registry.json"

        try:
            # Ensure directory exists
            registry_path.mkdir(parents=True, exist_ok=True)

            # Convert datetime objects to strings for JSON serialization
            serializable_registry = {}
            for session_id, info in registry.items():
                serializable_info = info.copy()
                if 'start_time' in serializable_info and isinstance(serializable_info['start_time'], datetime):
                    serializable_info['start_time'] = serializable_info['start_time'].isoformat()
                serializable_registry[session_id] = serializable_info

            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_registry, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"Failed to save session registry: {e}")
            return False

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """Remove stale sessions from registry."""
        registry = self.load_session_registry()
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0

        sessions_to_remove = []
        for session_id, info in registry.items():
            try:
                start_time = info.get('start_time', datetime.now())
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)

                # Remove old sessions or sessions with dead processes
                if start_time < cutoff_time or not self._is_process_alive(info.get('pid')):
                    sessions_to_remove.append(session_id)
            except Exception as e:
                logger.warning(f"Error checking session {session_id}: {e}")
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del registry[session_id]
            removed_count += 1

        if removed_count > 0:
            self.save_session_registry(registry)
            logger.info(f"Cleaned up {removed_count} stale sessions")

        return removed_count

    def _is_process_alive(self, pid: Optional[int]) -> bool:
        """Check if a process is still alive."""
        if not pid:
            return False

        try:
            if sys.platform == "win32":
                import psutil
                return psutil.pid_exists(pid)
            else:
                # Unix-like systems
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError, ImportError):
            return False


class WindowsProcessManager(BaseProcessManager):
    """Windows-specific process manager using Named Mutex and psutil."""

    def __init__(self, session_id: str, repo_path: str):
        super().__init__(session_id, repo_path)
        self.mutex_name = f"Global\\TestscenarioMaker_{session_id}"
        self.mutex_handle = None

        try:
            import win32event
            import win32api
            import win32con
            self.win32event = win32event
            self.win32api = win32api
            self.win32con = win32con
        except ImportError:
            logger.error("pywin32 package required for Windows process management")
            raise

    def check_existing_process(self) -> Optional[SessionInfo]:
        """Check for existing process using Named Mutex."""
        try:
            # Try to open existing mutex
            mutex = self.win32event.OpenMutex(
                self.win32con.SYNCHRONIZE, False, self.mutex_name
            )
            if mutex:
                # Mutex exists, there's already a process
                registry = self.load_session_registry()
                session_data = registry.get(self.session_id)
                if session_data:
                    return SessionInfo(
                        session_id=self.session_id,
                        pid=session_data.get('pid', 0),
                        repo_path=session_data.get('repo_path', ''),
                        start_time=session_data.get('start_time', datetime.now()),
                        status=session_data.get('status', 'active')
                    )
                self.win32api.CloseHandle(mutex)
        except Exception:
            # Mutex doesn't exist or error accessing it
            pass

        return None

    def terminate_existing_process(self, session_info: SessionInfo) -> bool:
        """Terminate existing process using Windows APIs."""
        try:
            import psutil

            # Find and terminate the process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if (proc.info['pid'] == session_info.pid and
                        proc.info['name'] and 'ts-cli' in proc.info['name']):

                        logger.info(f"Terminating existing process PID {proc.info['pid']}")

                        # Try graceful termination first
                        proc.terminate()

                        # Wait for graceful termination
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            # Force kill if necessary
                            logger.warning(f"Force killing process PID {proc.info['pid']}")
                            proc.kill()

                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return False
        except ImportError:
            logger.error("psutil package required for Windows process management")
            return False

    def register_session(self) -> bool:
        """Register session using Named Mutex."""
        try:
            # Create named mutex
            self.mutex_handle = self.win32event.CreateMutex(
                None, False, self.mutex_name
            )

            # Update session registry
            registry = self.load_session_registry()
            registry[self.session_id] = {
                'pid': self.session_info.pid,
                'repo_path': self.session_info.repo_path,
                'start_time': self.session_info.start_time,
                'status': self.session_info.status,
                'platform': 'windows'
            }

            return self.save_session_registry(registry)
        except Exception as e:
            logger.error(f"Failed to register Windows session: {e}")
            return False

    def cleanup_session(self) -> bool:
        """Clean up Windows session resources."""
        try:
            # Close mutex handle
            if self.mutex_handle:
                self.win32api.CloseHandle(self.mutex_handle)
                self.mutex_handle = None

            # Remove from registry
            registry = self.load_session_registry()
            if self.session_id in registry:
                del registry[self.session_id]
                return self.save_session_registry(registry)

            return True
        except Exception as e:
            logger.error(f"Failed to cleanup Windows session: {e}")
            return False


class UnixProcessManager(BaseProcessManager):
    """Unix-like process manager using PID files and signals."""

    def __init__(self, session_id: str, repo_path: str):
        super().__init__(session_id, repo_path)
        self.pid_file = self.get_session_registry_path() / f"{session_id}.pid"

    def check_existing_process(self) -> Optional[SessionInfo]:
        """Check for existing process using PID file."""
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process is still alive
            if self._is_process_alive(pid):
                registry = self.load_session_registry()
                session_data = registry.get(self.session_id)
                if session_data:
                    return SessionInfo(
                        session_id=self.session_id,
                        pid=pid,
                        repo_path=session_data.get('repo_path', ''),
                        start_time=session_data.get('start_time', datetime.now()),
                        status=session_data.get('status', 'active')
                    )
            else:
                # PID file exists but process is dead, clean it up
                self.pid_file.unlink(missing_ok=True)
        except (ValueError, OSError) as e:
            logger.warning(f"Error reading PID file: {e}")
            self.pid_file.unlink(missing_ok=True)

        return None

    def terminate_existing_process(self, session_info: SessionInfo) -> bool:
        """Terminate existing process using signals."""
        try:
            pid = session_info.pid
            logger.info(f"Terminating existing process PID {pid}")

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful termination
            for _ in range(10):  # Wait up to 5 seconds
                if not self._is_process_alive(pid):
                    return True
                time.sleep(0.5)

            # Force kill if necessary
            logger.warning(f"Force killing process PID {pid}")
            os.kill(pid, signal.SIGKILL)

            # Wait a bit more
            time.sleep(1)
            return not self._is_process_alive(pid)

        except (OSError, ProcessLookupError) as e:
            logger.warning(f"Error terminating process: {e}")
            return False

    def register_session(self) -> bool:
        """Register session using PID file."""
        try:
            # Ensure directory exists
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)

            # Write PID file
            with open(self.pid_file, 'w') as f:
                f.write(str(self.session_info.pid))

            # Update session registry
            registry = self.load_session_registry()
            registry[self.session_id] = {
                'pid': self.session_info.pid,
                'repo_path': self.session_info.repo_path,
                'start_time': self.session_info.start_time,
                'status': self.session_info.status,
                'platform': 'unix'
            }

            return self.save_session_registry(registry)
        except Exception as e:
            logger.error(f"Failed to register Unix session: {e}")
            return False

    def cleanup_session(self) -> bool:
        """Clean up Unix session resources."""
        try:
            # Remove PID file
            self.pid_file.unlink(missing_ok=True)

            # Remove from registry
            registry = self.load_session_registry()
            if self.session_id in registry:
                del registry[self.session_id]
                return self.save_session_registry(registry)

            return True
        except Exception as e:
            logger.error(f"Failed to cleanup Unix session: {e}")
            return False


def ProcessManager(session_id: str, repo_path: str) -> BaseProcessManager:
    """Factory function to create platform-appropriate ProcessManager."""
    if sys.platform == "win32":
        return WindowsProcessManager(session_id, repo_path)
    else:
        return UnixProcessManager(session_id, repo_path)


def handle_duplicate_session(session_id: str, repo_path: str, force: bool = False) -> bool:
    """
    Handle duplicate session execution.

    Args:
        session_id: Session identifier
        repo_path: Repository path
        force: If True, forcefully terminate existing session

    Returns:
        True if it's safe to proceed, False if should exit
    """
    try:
        manager = ProcessManager(session_id, repo_path)

        # Clean up stale sessions first
        manager.cleanup_stale_sessions()

        # Check for existing process
        existing = manager.check_existing_process()
        if existing:
            logger.warning(f"Found existing session {session_id} with PID {existing.pid}")

            if force:
                logger.info("Forcing termination of existing session")
                if manager.terminate_existing_process(existing):
                    logger.info("Successfully terminated existing session")
                else:
                    logger.error("Failed to terminate existing session")
                    return False
            else:
                logger.error(f"Session {session_id} is already running. Use --force to terminate it.")
                return False

        # Register current session
        if not manager.register_session():
            logger.error("Failed to register session")
            return False

        # Set up cleanup on exit
        import atexit
        atexit.register(manager.cleanup_session)

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, cleaning up...")
            manager.cleanup_session()
            sys.exit(0)

        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)

        return True

    except Exception as e:
        logger.error(f"Error handling duplicate session: {e}")
        return False