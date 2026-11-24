<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-postgres

A throwaway PostgreSQL server at a pinned version for LATTICE's tests, checks and benchmarks. It gives each test a clean database and reports the server version the test ran on.

It is **not a store SPI** and **not a runtime backend**. Its methods carry no promise to adopters, and only tests, checks and benchmarks import it.

## What it does

`PostgresServer` runs `initdb` into a temporary directory, starts the server on a free port of 127.0.0.1 with `pg_ctl start -w`, and stops it and removes the directory on `stop()` or at the end of a `with` block. The superuser is `postgres` with trust authentication. The server opens no Unix socket and listens on no other address. `create_database()` makes an empty database from `template0`, `drop_database()` drops one, and `server_version` holds what `SHOW server_version` answered. `settings` adds lines to `postgresql.conf` before the start. A server that cannot be set up, started or stopped raises `PostgresError` with the end of its output and log.

Two pytest fixtures come with it, loaded through the package's `pytest11` entry point, so a suite needs no `conftest.py`.

| Fixture | Scope | Gives |
|---|---|---|
| `postgres_server` | session, or one worker of a parallel run | a started `PostgresServer`, stopped and removed at the end |
| `postgres_database` | function | a `Database(name, conninfo, server_version)`, an empty database created for the test and dropped after it |

```python
import psycopg

def test_a_row_reads_back(postgres_database):
    with psycopg.connect(postgres_database.conninfo) as connection:
        connection.execute("CREATE TABLE t (x integer)")
```

A run that used the fixtures ends with a line naming the server version it ran on.

## The server and its version

The server is the build the [`postgresql-binaries`](https://pypi.org/project/postgresql-binaries/) wheel carries, pinned at 16.15.0, whose version is the PostgreSQL version. Major version 16 is the one the local environment's compose file runs. The wheel unpacks the server beside itself on first use, and the bootstrap task does that once. It is a test dependency only, declared in this package's `server` extra and in `requirements-lock.txt`.

The same task gives the server on the three machines LATTICE is run on, with no container.

| Machine | Wheel | What it needs besides |
|---|---|---|
| Windows | `win_amd64` | nothing |
| macOS | `macosx_11_0_arm64` or `macosx_10_9_x86_64` | nothing. The server uses the system's libxml2 and zlib and carries its own OpenSSL |
| Linux, a cloud session included | `manylinux_2_17_x86_64` or `manylinux_2_17_aarch64` | the shared libraries libzstd, liblz4, libxml2, OpenSSL 3, the Kerberos GSSAPI library and zlib |

`initdb` and the server refuse to run as root. Where the test process is root, as in a cloud session, the server runs as the account `LATTICE_POSTGRES_RUN_AS` names, `nobody` by default, from a copy of the server in its temporary directory that the account owns. `LATTICE_POSTGRES_START_TIMEOUT` (seconds, default 60) bounds the start.

## When the server is absent

A test that uses either fixture is given the `requires` marker for `postgresql_binaries` and `psycopg` when it is collected. The [requires plugin](../requires/README.md) skips it where either cannot be imported, and its reason names the package. A test that uses `PostgresServer` directly carries the marker itself. So a test never fails for want of a server, and `LATTICE_REQUIRE_ALL=1` fails it instead, for a run that must show every test ran.

## Install and run

```bash
mise run bootstrap:testing-postgres   # installs this package with its server and unpacks the server
mise run check:testing-postgres       # this package's own tests
```

`mise run bootstrap` installs this package without its server, so its tests skip until `bootstrap:testing-postgres` has run.

Run `mise run bootstrap` once in a checkout before `check:testing-postgres`, as for every check. The task installs only this package and its server, and pytest also loads `tools/conftest.py`, which imports pySHACL, and needs the [requires plugin](../requires/README.md) to register the `requires` marker. Both come with `mise run bootstrap`. In a checkout that was never bootstrapped, the run stops with `ModuleNotFoundError: No module named 'pyshacl'` before any test runs.

## Design decisions

- **A test-support package under `tools/testing/`** ([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Only tests, checks and benchmarks import it, and a suite that uses it skips without it.
- **A server in a wheel, not a container or a download of our own.** The wheel installs through pip and the mirror as every other test dependency does, on Windows, macOS and Linux, and needs no Docker, which macOS and a cloud session lack. A bootstrap task that downloads official builds would need a download, a checksum and a cache of its own for each platform.
