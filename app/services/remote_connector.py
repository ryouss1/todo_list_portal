"""Remote file access abstraction for FTP and SMB connections."""

import fnmatch
import ftplib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import List, Optional

from app.config import LOG_FTP_CONNECT_TIMEOUT, LOG_FTP_READ_TIMEOUT
from app.constants import AccessMethod

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


def _make_ftp_session_class(port: int, timeout: int) -> type:
    """ftputil 用カスタム FTP セッションクラスを生成する。"""

    class _FTPSession(ftplib.FTP):
        def __init__(self, host: str, user: str, passwd: str):
            super().__init__(timeout=timeout)
            self.connect(host, port, timeout=timeout)
            self.login(user, passwd)
            self.set_pasv(True)

    return _FTPSession


class FTPConnector(RemoteConnector):
    """FTP connection using ftputil (high-level ftplib wrapper)."""

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
        self._ftp: Optional[object] = None

    def connect(self) -> None:
        import ftputil

        session_cls = _make_ftp_session_class(self.port, self.connect_timeout)
        self._ftp = ftputil.FTPHost(
            self.host,
            self.username,
            self.password,
            session_factory=session_cls,
        )
        logger.info("FTP connected to %s:%d", self.host, self.port)

    def disconnect(self) -> None:
        if self._ftp:
            try:
                self._ftp.close()
            except Exception:
                pass
            self._ftp = None

    def list_files(self, path: str, pattern: str, modified_since: Optional[date] = None) -> List[RemoteFileInfo]:
        if not self._ftp:
            raise RuntimeError("Not connected")
        files = []
        skipped = 0
        try:
            names = self._ftp.listdir(path)
        except Exception as e:
            logger.warning("FTP: cannot list %s: %s", path, e)
            return files

        for name in names:
            if not fnmatch.fnmatch(name, pattern):
                continue
            full_path = f"{path.rstrip('/')}/{name}"
            try:
                if not self._ftp.path.isfile(full_path):
                    continue
                stat = self._ftp.stat(full_path)
                size = stat.st_size
                mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc) if stat.st_mtime else None
            except Exception:
                size = 0
                mod_dt = None
            if modified_since is not None:
                if mod_dt is None or mod_dt.date() < modified_since:
                    skipped += 1
                    continue
            files.append(RemoteFileInfo(name=name, size=size, modified_at=mod_dt))

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
        if not self._ftp:
            raise RuntimeError("Not connected")
        full_path = f"{path.rstrip('/')}/{file_name}" if path else file_name
        with self._ftp.open(full_path, "rb") as f:
            data = f.read()
        text = data.decode(encoding, errors="replace")
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
    if access_method == AccessMethod.FTP:
        return FTPConnector(
            host=host,
            port=port or 21,
            username=username,
            password=password,
            connect_timeout=LOG_FTP_CONNECT_TIMEOUT,
            read_timeout=LOG_FTP_READ_TIMEOUT,
        )
    elif access_method == AccessMethod.SMB:
        return SMBConnector(
            host=host,
            port=port or 445,
            username=username,
            password=password,
            domain=domain,
        )
    else:
        raise ValueError(f"Unsupported access method: {access_method!r}. Expected one of: ftp, smb")
