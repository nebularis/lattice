# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The pytest fixtures of the PostgreSQL test-support package, loaded through its ``pytest11`` entry point (ADR-A125).

A test that uses either fixture is given the ``requires`` marker for the server package and psycopg at collection, so the
requires plugin skips it, naming the package, where either cannot be imported. It never fails for want of a server.
"""

from __future__ import annotations

from typing import NamedTuple

import pytest

NEEDS = ("postgresql_binaries", "psycopg")
FIXTURES = {"postgres_server", "postgres_database"}
_VERSION = pytest.StashKey[str]()


class Database(NamedTuple):
    name: str
    conninfo: str
    server_version: str


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if not FIXTURES & set(getattr(item, "fixturenames", ())):
            continue
        named = {name for marker in item.iter_markers("requires") for name in marker.args}
        if absent := [name for name in NEEDS if name not in named]:
            item.add_marker(pytest.mark.requires(*absent))


@pytest.fixture(scope="session")
def postgres_server(request: pytest.FixtureRequest):
    """One server for the test session, or for one worker of a parallel run, stopped and removed at its end."""
    from lattice_testing_postgres import PostgresServer

    with PostgresServer() as server:
        request.config.stash[_VERSION] = server.server_version
        yield server


@pytest.fixture
def postgres_database(postgres_server) -> Database:
    """An empty database for one test, created from ``template0`` and dropped after it."""
    name = postgres_server.create_database()
    try:
        yield Database(name, postgres_server.conninfo(name), postgres_server.server_version)
    finally:
        postgres_server.drop_database(name)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    version = config.stash.get(_VERSION, None)
    if version:
        terminalreporter.write_line(f"lattice: PostgreSQL tests ran on server version {version}")
