# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""A throwaway PostgreSQL server for tests, checks and benchmarks (ADR-A125). It is not a store SPI.

The server is the build the ``postgresql-binaries`` wheel carries, whose version is the PostgreSQL version. :class:`PostgresServer`
runs ``initdb`` into a temporary directory, starts the server on a free port of 127.0.0.1 with ``pg_ctl start -w``, and on
:meth:`PostgresServer.stop` stops it and removes the directory. The superuser is ``postgres`` with trust authentication, and the
server opens no Unix socket. ``initdb`` and ``postgres`` refuse to run as root, so where this process is root the server runs as the
account ``LATTICE_POSTGRES_RUN_AS`` names, ``nobody`` by default, from a copy of the server that account can read.

Nothing here imports the server package or psycopg until a server starts, so the pytest plugin loads where neither is installed.
"""

from __future__ import annotations

import importlib.metadata
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Mapping

DISTRIBUTION = "postgresql-binaries"
SUPERUSER = "postgres"
HOST = "127.0.0.1"
RUN_AS = "LATTICE_POSTGRES_RUN_AS"
START_TIMEOUT = int(os.environ.get("LATTICE_POSTGRES_START_TIMEOUT", "60"))


class PostgresError(RuntimeError):
    """The server could not be set up, started or stopped. The message holds the end of its output and log."""


def pinned_version() -> str:
    """The version of the installed server package, which is the PostgreSQL version, for example ``16.15.0``."""
    return importlib.metadata.version(DISTRIBUTION)


def binaries() -> Path:
    """The directory holding ``initdb``, ``pg_ctl`` and ``postgres``. The server package unpacks itself there on first use."""
    import postgresql_binaries

    return postgresql_binaries.bin()


def free_port() -> int:
    """A TCP port of 127.0.0.1 that nothing listens on now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def _account() -> tuple[int, int] | None:
    """The user and group to run the server as where this process is root, and None elsewhere, Windows included."""
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return None
    import pwd

    entry = pwd.getpwnam(os.environ.get(RUN_AS, "nobody"))
    return entry.pw_uid, entry.pw_gid


def _tail(path: Path, size: int = 2000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-size:]
    except OSError:
        return ""


def _remove(path: Path) -> None:
    """Remove a directory. On Windows a file the stopped server held can stay locked for a moment, so this tries again."""
    for attempt in range(40):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == 39:
                raise
            time.sleep(0.25)


class PostgresServer:
    """One PostgreSQL server in a temporary directory. Use it as a context manager, or call :meth:`start` and :meth:`stop`."""

    def __init__(self, settings: Mapping[str, object] | None = None) -> None:
        self.settings = dict(settings or {})
        """Server settings added to ``postgresql.conf`` before the start."""
        self.base: Path | None = None
        self.port: int | None = None
        self.server_version: str | None = None
        """What ``SHOW server_version`` answered once the server started, for example ``16.15``."""
        self._account = _account()
        self._bin: Path | None = None
        self._databases = 0

    @property
    def data(self) -> Path:
        return self.base / "data"

    def __enter__(self) -> "PostgresServer":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> "PostgresServer":
        if self.base is not None:
            raise PostgresError(f"the server in {self.base} is already started")
        self.base = Path(tempfile.mkdtemp(prefix="lattice-postgres-"))
        try:
            self._bin = self._install()
            self._call("initdb", "-D", str(self.data), "-U", SUPERUSER, "-A", "trust", "-E", "UTF8", "--locale=C", "--no-sync", "--no-instructions")
            self.port = free_port()
            self._configure()
            self._call("pg_ctl", "start", "-w", "-t", str(START_TIMEOUT), "-D", str(self.data), "-l", str(self.base / "server.log"))
            with self.connect() as connection:
                self.server_version = connection.execute("SHOW server_version").fetchone()[0]
        except BaseException:
            self.stop()
            raise
        return self

    def stop(self) -> None:
        """Stop the server and remove its directory. It does nothing where the server is not started."""
        if self.base is None:
            return
        try:
            if (self.data / "postmaster.pid").exists():
                self._call("pg_ctl", "stop", "-w", "-m", "fast", "-D", str(self.data))
        finally:
            base, self.base, self.port = self.base, None, None
            _remove(base)

    def _install(self) -> Path:
        source = binaries()
        if self._account is None:
            return source
        target = self.base / "install"
        shutil.copytree(source.parent, target, symlinks=True)
        for path in [self.base, *self.base.rglob("*")]:
            os.chown(path, *self._account, follow_symlinks=False)
        return target / source.name

    def _configure(self) -> None:
        settings = {"listen_addresses": HOST, "port": self.port, "unix_socket_directories": "", **self.settings}
        with open(self.data / "postgresql.conf", "a", encoding="utf-8") as conf:
            for name, value in settings.items():
                quoted = str(value).replace("'", "''")
                conf.write(f"{name} = '{quoted}'\n")

    def _call(self, program: str, *args: str) -> None:
        executable = shutil.which(program, path=str(self._bin))
        if executable is None:
            raise PostgresError(f"{program} is not in {self._bin}")
        output = self.base / f"{program}.out"
        account = {} if self._account is None else {"user": self._account[0], "group": self._account[1], "extra_groups": []}
        with open(output, "ab") as sink:
            result = subprocess.run([executable, *args], stdin=subprocess.DEVNULL, stdout=sink, stderr=subprocess.STDOUT, cwd=self.base, **account)
        if result.returncode != 0:
            raise PostgresError(f"{program} {args[0]} exited with {result.returncode}: {_tail(output)}{_tail(self.base / 'server.log')}")

    def conninfo(self, dbname: str = SUPERUSER) -> str:
        """A libpq connection string for one database of this server."""
        from psycopg.conninfo import make_conninfo

        return make_conninfo(host=HOST, port=self.port, user=SUPERUSER, dbname=dbname)

    def connect(self, dbname: str = SUPERUSER, **options):
        """A psycopg connection to one database of this server."""
        import psycopg

        return psycopg.connect(self.conninfo(dbname), **options)

    def create_database(self) -> str:
        """Create an empty database from ``template0`` and return its name."""
        from psycopg import sql

        self._databases += 1
        name = f"test_{self._databases}"
        with self.connect(autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        return name

    def drop_database(self, name: str) -> None:
        """Drop a database, ending any session still connected to it."""
        from psycopg import sql

        with self.connect(autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


__all__ = ["DISTRIBUTION", "PostgresError", "PostgresServer", "binaries", "free_port", "pinned_version"]
