# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The PostgreSQL test-support package (ADR-A125). Test IDs are PG-Tn. They skip, naming the package, where the server
package or psycopg cannot be imported."""

from __future__ import annotations

import pytest


def _major_minor(version: str) -> list[str]:
    return version.split(".")[:2]


@pytest.mark.requires("postgresql_binaries", "psycopg")
def test_pg_t1_a_server_starts_a_row_written_in_a_transaction_reads_back_and_the_server_stops():
    from lattice_testing_postgres import PostgresServer, pinned_version

    server = PostgresServer().start()
    base = server.base
    try:
        assert _major_minor(server.server_version) == _major_minor(pinned_version())
        name = server.create_database()
        with server.connect(name) as connection:
            with connection.transaction():
                connection.execute("CREATE TABLE note (id integer PRIMARY KEY, body text NOT NULL)")
                connection.execute("INSERT INTO note (id, body) VALUES (%s, %s)", (1, "written"))
                assert connection.execute("SELECT body FROM note WHERE id = 1").fetchone() == ("written",)
        with server.connect(name) as other:
            assert other.execute("SELECT id, body FROM note").fetchall() == [(1, "written")]
    finally:
        server.stop()
    assert server.base is None and not base.exists()


def test_pg_t2_the_fixture_gives_a_test_an_empty_database_and_the_version_it_ran_on(postgres_database):
    import psycopg

    from lattice_testing_postgres import pinned_version

    with psycopg.connect(postgres_database.conninfo) as connection:
        assert connection.execute("SELECT current_database()").fetchone() == (postgres_database.name,)
        assert connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'").fetchone() == (0,)
    assert _major_minor(postgres_database.server_version) == _major_minor(pinned_version())
