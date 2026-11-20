<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I13, the PostgreSQL test fixture

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I13
**Brief:** [machine S brief of 2026-11-19, the multi-store half](../notes/machine-s-brief-2026-11-19-multi-store.md), section 4.1.
**Decisions:** [ADR-A125](../../architecture/decisions/ADR-A125-test-support-tooling.md) (test-support packages), STD-323 (the `requires` marker).
**Machine:** machine S, Windows, Python 3.14.7 from the worktree's `.venv` through mise. **Placement:** T0, public. Test support, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

A test that asks for `postgres_database` gets an empty database of its own on a PostgreSQL server at the pinned version, 16.15, and the run reports the server version it ran on. Where the server package or psycopg cannot be imported, the test is skipped by the `requires` plugin with the package named, and never fails for want of a server. No product code imports the package.

## What changed

- `tools/testing/postgres/`, a test-support package beside Oxigraph and Jena. `PostgresServer` runs `initdb` into a temporary directory, starts the server on a free port of 127.0.0.1 with `pg_ctl start -w`, and stops it and removes the directory. The pytest plugin gives the fixtures `postgres_server` (session) and `postgres_database` (function, `CREATE DATABASE` from `template0`, dropped after), and gives any test using them the `requires` marker for `postgresql_binaries` and `psycopg` at collection.
- `mise.toml`: `bootstrap:testing-postgres` installs the package with its `server` extra and unpacks the server once. `check:testing-postgres` runs the package's tests. `bootstrap:python`'s single resolve installs the package without the server, as it installs the Jena package without the jar. Neither task joins `check`, as ADR-A125 decision 4 says.
- `requirements-lock.txt`: `postgresql-binaries==16.15.0`, with a header line, as ADR-A125 records a test-support package's dependency.
- `repository-catalogue.md`: the row `testing/postgres`. It reaches no path outside its own tree.

## How the server is provided: the options and the choice

What was reachable on machine S on 2026-11-19, through the local PyPI mirror and the existing Maven setup:

| Probe | Result |
|---|---|
| `pg_ctl`, `initdb`, `postgres` on PATH | none |
| `docker` on PATH | present, on machine S only |
| `pip download pgserver` | refused by the mirror, "No matching distribution" |
| `pip download postgresql-wheel` | refused by the mirror, "No matching distribution" |
| `pip download pixeltable-pgserver` | served, 0.7.2. Wheels for Windows, macOS arm64, Linux x86_64 and aarch64 at cp314. No macOS x86_64 wheel at 0.7.2 (only 0.4.0). Brings `fasteners`, `platformdirs`, `psutil` and `typing-extensions` |
| `pip download postgresql-binaries` | served, versions 14.22.0 to 18.6.0. At 16.15.0 wheels for `win_amd64`, `macosx_11_0_arm64`, `macosx_10_9_x86_64`, `manylinux_2_17_x86_64` and `manylinux_2_17_aarch64`. No Python dependencies |
| `mvn dependency:get io.zonky.test.postgres:embedded-postgres-binaries-windows-amd64:16.4.0` | served, a 22.5 MB jar in the local Maven repository |

| Option | What it needs on Windows, macOS and a cloud session | Costs |
|---|---|---|
| A container (`postgres:16.4-alpine`, as compose runs) | Docker on all three | Fails the three-machine rule. The brief assumes no Docker on macOS or a cloud session |
| A server already on PATH | an installation on each machine, of the right version | No pin. Each machine's version differs, and none is on machine S |
| Official binaries a bootstrap task downloads (EnterpriseDB zips, or zonky's per-OS Maven artefacts) | Java and Maven for zonky, which mise gives all three, or a direct download for EnterpriseDB | A download, a checksum, a per-OS artefact name and a cache to write and keep, and xz unpacking for zonky. EnterpriseDB publishes no Linux tarball. Zonky's Maven artefacts are reachable here |
| A packaged server, `pixeltable-pgserver` | pip and the mirror | Four more Python dependencies, a version tied to the package's release and not to PostgreSQL's, and no macOS x86_64 wheel at the current release |
| A packaged server, `postgresql-binaries` | pip and the mirror. On Linux, system shared libraries (below) | One test-only dependency, packaged by one maintainer from the builds of the `theseus-rs/postgresql-binaries` project, not by the PostgreSQL project. The package version is the PostgreSQL version |

**Chosen: `postgresql-binaries`, pinned at 16.15.0.** It installs through pip and the mirror as every other test dependency does, on all three machines with no Docker, and its version is the PostgreSQL version, so the pin is one line in `pyproject.toml` and the lock file. It needs no download code, checksum or cache of our own, which the zonky route would. Major version 16 is the one `deployment/compose/docker-compose.yml` runs (`postgres:16.4-alpine`). The mirror serves 16.13.0 to 16.15.0 and not 16.4, so the latest 16 is taken.

**New dependency for the maintainer:** `postgresql-binaries==16.15.0`, test only, in the package's `server` extra and in `requirements-lock.txt`. Licence: the PostgreSQL licence. Each wheel holds one PostgreSQL tarball, unpacked beside itself on first use.

What each platform's build needs, read from the binaries' headers:

| Platform | Needs |
|---|---|
| Windows | nothing beyond the wheel |
| macOS, arm64 and x86_64 | `/usr/lib/libxml2.2.dylib`, `/usr/lib/libz.1.dylib` and `libSystem`, all part of macOS. OpenSSL is carried in the wheel |
| Linux x86_64 | `postgres` needs `libzstd.so.1`, `liblz4.so.1`, `libxml2.so.2`, `libssl.so.3`, `libcrypto.so.3`, `libgssapi_krb5.so.2` and `libz.so.1`. `initdb` and `pg_ctl` need only libc and the bundled `libpq` |

`initdb` and `postgres` refuse to run as root, and a cloud session's setup runs as root (`tools/claude-cloud-setup.sh` calls `apt-get` with no `sudo`). Where the process is root, `PostgresServer` copies the server into its temporary directory, gives the directory to the account `LATTICE_POSTGRES_RUN_AS` names (`nobody` by default) and runs `initdb` and `pg_ctl` as that account.

## Test cases

| ID | Given, when, then | Level | Pass criterion | Kind |
|---|---|---|---|---|
| PG-T1 | given the pinned server, when a `PostgresServer` starts, a database is created, a table and a row are written and the row is read inside one transaction, and the server stops, then the row reads back in the transaction and from a second connection, the reported version has the pin's major and minor, and the temporary directory is gone | L3 | `test_pg_t1_a_server_starts_a_row_written_in_a_transaction_reads_back_and_the_server_stops` passes | positive |
| PG-T2 | given the session fixture, when a test asks for `postgres_database`, then it is connected to a database of its own name with no table in `public`, and the version it carries has the pin's major and minor | L3 | `test_pg_t2_the_fixture_gives_a_test_an_empty_database_and_the_version_it_ran_on` passes | positive |
| PG-T3 | given no server package, when the two tests run, then both skip and each reason names `postgresql_binaries`. PG-T2 has no marker of its own, so its skip shows the plugin marked it | L3 | `2 skipped`, reason "needs postgresql_binaries, which cannot be imported here" | negative |
| PG-T4 | given no server package and `LATTICE_REQUIRE_ALL=1`, when the two tests run, then both fail instead of skipping | L3 | `2 errors`, exit 1 | negative |

PG-T3 and PG-T4 are runs of PG-T1 and PG-T2 with the server made absent, not tests of their own.

## One command

```bash
mise run check:testing-postgres
```

A pass is `2 passed` and the line `lattice: PostgreSQL tests ran on server version 16.15`.

## What was run, in full

Run on machine S on 2026-11-19, from the worktree, with `PYTHONUTF8=1` and the mirror's constraint file set.

| Command | Result |
|---|---|
| `mise run bootstrap:testing-postgres` | `Successfully installed lattice-testing-postgres-0.1.0 postgresql-binaries-16.15.0`, `PostgreSQL 16.15.0 from postgresql-binaries, unpacked in` the venv's `postgresql_binaries` directory, `Finished in 23.60s` |
| `mise run check:testing-postgres` | `lattice: PostgreSQL tests ran on server version 16.15`, `2 passed in 19.18s`, `Finished in 34.18s`. Afterwards no `lattice-postgres-*` directory in the temporary directory and no `postgres` process |
| `python -m pip uninstall -y postgresql-binaries`, then `python -m pytest tools/testing/postgres/tests -q -rs` | `1 failed, 1 error`: `AttributeError: module 'postgresql_binaries' has no attribute 'bin'`. See the finding below |
| the unpacked server directory removed from the venv, then `python -m pytest tools/testing/postgres/tests -q -rs` | `SKIPPED [2] ... needs postgresql_binaries, which cannot be imported here`, `lattice: not run for a package this environment lacks: postgresql_binaries (2 tests). LATTICE_REQUIRE_ALL=1 fails them`, `2 skipped in 0.05s`, exit 0 |
| the same with `LATTICE_REQUIRE_ALL=1` | `2 errors in 0.06s`, exit 1 |
| `mise run bootstrap:testing-postgres`, then `mise run check:testing-postgres` | `PostgreSQL 16.15.0 from postgresql-binaries, unpacked in` the venv, `lattice: PostgreSQL tests ran on server version 16.15`, `2 passed in 19.46s` |
| `mise run check:catalogue` | `repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)` |
| `python -m pytest tools/test_lattice_repo_catalogue.py -q -n auto` | `139 passed, 1 warning in 19.52s` |
| `mise run check:identifiers` | `identifier check passed: 2379 identifiers mentioned in 1018 files, 0 unresolved, 0 defined twice` |
| `mise run check:portability` | fails, `portability: 10 problem(s)`, all text calls without an encoding in `benchmark/ledger-credit-kinds-jvm`, `tools/bootstrap_erlang.py`, `tools/test_asset_class.py`, `tools/test_hooks.py`, `tools/test_v_rig.py` and `tools/v_rig/tests`. None is in a file this slice touched, and no task problem is reported for `mise.toml` |
| `python -m pytest tools/test_portability.py tools/test_clean.py -q` | `1 failed, 24 passed`. The failure is `test_the_repository_passes`, over the same 10 problems |
| `python tools/writing_rules.py tools/testing/postgres/README.md docs/developer/validation/MSA-I13.md` | `writing rules: 0 failure(s), 0 warning(s)` |

No test in `tools/` counts the tool packages by number. `test_lattice_repo_catalogue.py` compares the declared packages with the tree, and it passes.

## Finding

**MSAI13-01. `pip uninstall postgresql-binaries` leaves the unpacked server behind.** The unpacked tree is not in the wheel's record, so pip leaves the `postgresql_binaries` directory in `site-packages`. Python then imports it as a namespace package, the `requires` plugin finds it, and a test errors on `postgresql_binaries.bin()` instead of skipping. A machine that never installed the package skips as it should. Removing the directory, or running `bootstrap:testing-postgres` again, restores the right behaviour.

## Not run on macOS and a cloud session

Only Windows is on machine S. Neither macOS nor Linux has run this package, and the path that runs the server as another account where the process is root has never run. On each, from a checkout:

```bash
mise run bootstrap:testing-postgres
mise run check:testing-postgres
```

A pass is `2 passed` and `server version 16.15`. In a cloud session, where a shared library is missing the start fails with the loader's message in the error, and `apt-get install -y libzstd1 liblz4-1 libxml2 libssl3 libgssapi-krb5-2 zlib1g` provides them on Ubuntu. Where `nobody` is not usable, `LATTICE_POSTGRES_RUN_AS` names another account.

## Deliberate non-coverage

- **No test on macOS or Linux, and none as root.** As above.
- **No server settings for measurement.** The server runs with PostgreSQL's defaults apart from the address, port and socket. MSA-I7 sets what its figures need through `settings`.
- **No parallel run.** Each worker of a parallel run starts a server of its own on a free port. Not exercised.
- **A port taken between choosing it and the start fails the start.** It is not retried.
- **The import guard does not cover `tools/testing/`**, as ADR-A125 records. Nothing imports this package outside its tests, read by search.

## Doc delta

- New: `tools/testing/postgres/README.md`, and this pack.
- Changed: `repository-catalogue.md` (one tool row), `mise.toml` (two tasks and one entry in `bootstrap:python`), `requirements-lock.txt` (one pin and one header line).

## Questions for the maintainer

1. Accept `postgresql-binaries`, a repackaging by one maintainer of the `theseus-rs` builds, as a test dependency, or prefer the zonky Maven artefacts behind a download task of our own.
2. Accept 16.15 as the pin, the latest 16 the mirror serves, where compose runs 16.4.
