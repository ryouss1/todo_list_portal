"""Remote file access abstraction for FTP and SMB connections."""

import ftplib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import List, Optional

logger = logging.getLogger("app.services.remote_connector")


@dataclass
class RemoteFileInfo:
    """Metadata for a remote file."""

    name: str
    size: int
    modified_at: Optional[datetime]


class RemoteConnector(ABC):
    """Abstract interface for remote file access."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def list_files(self, path: str, pattern: str, modified_since: Optional[date] = None) -> List[RemoteFileInfo]: ...

    @abstractmethod
    def read_lines(
        self,
        path: str,
        file_name: str,
        offset: int = 0,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> List[str]: ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class FTPConnector(RemoteConnector):
    """FTP connection using ftplib (passive mode)."""

    def __init__(
        self,
        host: str,
        port: int = 21,
        username: str = "",
        password: str = "",
        connect_timeout: int = 30,
        read_timeout: int = 60,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._ftp: Optional[ftplib.FTP] = None

    def connect(self) -> None:
        self._ftp = ftplib.FTP()
        self._ftp.connect(self.host, self.port, timeout=self.connect_timeout)
        self._ftp.login(self.username, self.password)
        self._ftp.set_pasv(True)
        logger.info("FTP connected to %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                try:
                    self._ftp.close()
                except Exception:
                    pass
            self._ftp = None

    def list_files(self, path: str, pattern: str, modified_since: Optional[date] = None) -> List[RemoteFileInfo]:
        import fnmatch

        if not self._ftp:
            raise RuntimeError("Not connected")
        files = []
        skipped = 0
        try:
            # Iterate MLSD as generator (avoid loading all entries into memory)
            for name, facts in self._ftp.mlsd(path):
                if facts.get("type", "") != "file":
                    continue
                if not fnmatch.fnmatch(name, pattern):
                    continue
                size = int(facts.get("size", 0))
                modify = facts.get("modify", "")
                mod_dt = None
                if modify:
                    try:
                        mod_dt = datetime.strptime(modify, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
                # Early date filter: skip files older than modified_since
                if modified_since is not None:
                    if mod_dt is None or mod_dt.date() < modified_since:
                        skipped += 1
                        continue
                files.append(RemoteFileInfo(name=name, size=size, modified_at=mod_dt))
        except ftplib.error_perm:
            # Fallback to LIST if MLSD not supported
            logger.warning("MLSD not supported, falling back to LIST for %s", path)
            dir_lines: List[str] = []
            self._ftp.dir(path, dir_lines.append)

            for line in dir_lines:
                parts = line.split()
                if len(parts) < 9:
                    continue
                name = parts[-1]
                if not line.startswith("-"):
                    continue
                if not fnmatch.fnmatch(name, pattern):
                    continue
                try:
                    size = int(parts[4])
                except ValueError:
                    size = 0
                # LIST doesn't provide reliable timestamps, include all
                files.append(RemoteFileInfo(name=name, size=size, modified_at=None))

        if skipped > 0:
            logger.debug(
                "FTP list_files %s: %d matched, %d skipped (before modified_since=%s)",
                path,
                len(files),
                skipped,
                modified_since,
            )
        return files

    def read_lines(
        self,
        path: str,
        file_name: str,
        offset: int = 0,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> List[str]:
        import io

        if not self._ftp:
            raise RuntimeError("Not connected")
        full_path = f"{path.rstrip('/')}/{file_name}" if path else file_name
        data = io.BytesIO()
        self._ftp.retrbinary(f"RETR {full_path}", data.write)
        data.seek(0)
        text = data.read().decode(encoding, errors="replace")
        all_lines = text.splitlines()
        start = offset
        end = start + limit if limit else len(all_lines)
        return all_lines[start:end]


class SMBConnector(RemoteConnector):
    """SMB/CIFS connection using smbprotocol."""

    def __init__(
        self,
        host: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        domain: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.domain = domain or ""

    def connect(self) -> None:
        try:
            import smbclient

            smbclient.register_session(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
            )
            logger.info("SMB connected to %s:%d", self.host, self.port)
        except ImportError:
            raise RuntimeError("smbprotocol is not installed. Run: pip install smbprotocol")

    def disconnect(self) -> None:
        # smbprotocol manages connection pooling internally
        pass

    @staticmethod
    def _build_smb_path(host: str, path: str) -> str:
        """Build UNC path: \\\\host\\share\\subdir. Strips leading slashes from path."""
        backslash = "\\"
        clean_path = path.strip("/").strip("\\")
        return backslash * 2 + host + backslash + clean_path.replace("/", backslash)

    def list_files(self, path: str, pattern: str, modified_since: Optional[date] = None) -> List[RemoteFileInfo]:
        import fnmatch

        try:
            import smbclient
        except ImportError:
            raise RuntimeError("smbprotocol is not installed")

        smb_path = self._build_smb_path(self.host, path)
        files = []
        skipped = 0
        for entry in smbclient.scandir(smb_path):
            # Check name pattern BEFORE is_file/stat (avoids network round-trips)
            if not fnmatch.fnmatch(entry.name, pattern):
                continue
            if not entry.is_file():
                continue
            stat = entry.stat()
            mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            # Early date filter: skip files older than modified_since
            if modified_since is not None:
                if mod_dt.date() < modified_since:
                    skipped += 1
                    continue
            files.append(
                RemoteFileInfo(
                    name=entry.name,
                    size=stat.st_size,
                    modified_at=mod_dt,
                )
            )

        if skipped > 0:
            logger.debug(
                "SMB list_files %s: %d matched, %d skipped (before modified_since=%s)",
                path,
                len(files),
                skipped,
                modified_since,
            )
        return files

    def read_lines(
        self,
        path: str,
        file_name: str,
        offset: int = 0,
        limit: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> List[str]:
        try:
            import smbclient
        except ImportError:
            raise RuntimeError("smbprotocol is not installed")

        smb_path = self._build_smb_path(self.host, path + "/" + file_name)
        with smbclient.open_file(smb_path, mode="rb") as f:
            data = f.read()
        text = data.decode(encoding, errors="replace")
        all_lines = text.splitlines()
        start = offset
        end = start + limit if limit else len(all_lines)
        return all_lines[start:end]


def create_connector(
    access_method: str,
    host: str,
    port: Optional[int],
    username: str,
    password: str,
    domain: Optional[str] = None,
) -> RemoteConnector:
    """Factory to create the appropriate connector."""
    if access_method == "ftp":
        from app.config import LOG_FTP_CONNECT_TIMEOUT, LOG_FTP_READ_TIMEOUT

        return FTPConnector(
            host=host,
            port=port or 21,
            username=username,
            password=password,
            connect_timeout=LOG_FTP_CONNECT_TIMEOUT,
            read_timeout=LOG_FTP_READ_TIMEOUT,
        )
    elif access_method == "smb":
        return SMBConnector(
            host=host,
            port=port or 445,
            username=username,
            password=password,
            domain=domain,
        )
    else:
        raise ValueError(f"Unsupported access method: {access_method}")
