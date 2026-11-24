<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I7, the PostgreSQL arm of the ledger benchmark

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I7
**Brief:** [machine S brief of 2026-11-19, the multi-store half](../notes/machine-s-brief-2026-11-19-multi-store.md), sections 4.5, 4.9, 6 and 7, with the [handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), section 3, and the [ledger's note of 2026-11-23](../notes/ledger-to-multi-store-2026-11-23.md), sections 3, 5, 6 and 7.
**Decisions:** [ADR-A124](../../architecture/decisions/ADR-A124-benchmark-root.md) (a benchmark fails on a wrong result, never on time), [ADR-A125](../../architecture/decisions/ADR-A125-test-support-tooling.md) (the PostgreSQL fixture), ADR-A131's addendum of 2026-11-23 (a balance is read against the latest version in force), PRI-55 (no string concatenation into a query).
**Machine:** machine S, Windows, Python 3.14.7 from the worktree's `.venv` through mise, pyoxigraph 0.5.13, rdflib 7.6.0, psycopg 3.3.6, PostgreSQL 16.15 from the fixture. **Placement:** T0, public. A benchmark and test support, nothing domain-specific.
**Status:** built 2026-11-23, not verified.

## Invariant

On PostgreSQL, a balance read against the latest version in force equals the model's at every sampled account and revision, as on the RDF engines. The arm holds the two forms of the record the layer built, `ldg:Supersession` naming its owner, in a relational layout of the benchmark's own, decoded from the same triples the RDF engines load. Each triple becomes exactly one fact of the layout, so the stored count is held to the same arithmetic. A wrong value or count fails the run, and time never does. Where the server is absent, the arm is skipped with the package it needs named.

## What changed

- `benchmark/ledger-supersession-read/check.py`, the benchmark of LG-32:
  - A fourth engine, `postgresql`, in `ENGINES`. `PostgresBackend` creates a database of its own on the fixture's server for each history, creates the layout, copies the history in with `COPY` in one transaction, analyses the tables, and copies the last change of terms in a timed transaction of its own. It drops its database when the history is done.
  - The layout, stated once as data (`TABLES`, `LINKS`, `INDEXES`), from which `schema()` writes the DDL, `decode()` places each triple and `stored_facts_query()` counts what is stored.
  - `as_layer_terms()` gives the benchmark's stand-in terms the layer's names before the decode: `b:Supersession`, `b:owner` and `b:supersedingVersion` become `ldg:Supersession`, `ldg:forOwner` and `ldg:supersedingVersion`. The decode's layout names only the layer's terms and Foundation's, Quantification's and RDFS's, so a stand-in term that reached it would fail as a predicate with no column.
  - Four SQL statements, one for each read, with bound parameters, in place of the SPARQL where the backend is PostgreSQL. `stated_in_force`, `balance_at`, `ancestor_balance` and `bulk_in_force` dispatch to them.
  - `variants_for()` runs per-version and per-pass on PostgreSQL, and all four variants on the RDF engines as before.
  - `postgres_absent()` says why the arm cannot run, and `postgres_running()` starts one server for the run and stops it at the end, including on failure. `main()` prints `postgresql not run:` with the reason, or the server version and the variants it runs.
  - `Result.decode_ms`, the share of the timed write that the decode took, and a `decode ms` column in `report.md`.
  - A fix to the corpus, finding MSAI7-01 below. The aggregate's later versions named `urn:bench:def/cap/v<k>` as their parent, a version never written. They now name the cap's one version.
- `benchmark/ledger-supersession-read/test_check.py`: eight tests, SS4c and SS10 to SS16, 19 cases, nine of them on the server. LG-32's 21 cases are unchanged, so the file holds 40.
- `benchmark/ledger-supersession-read/README.md`: a section on the PostgreSQL arm, its layout, its statements and its stored count, and the parent's correction, the run's skip and the files.
- `mise.toml`: `check:ledger-supersession-read` runs `bootstrap:testing-postgres` as its first step, and its description names the arm.
- `tools/testing/postgres/README.md`: a paragraph on what `check:testing-postgres` needs that its own task does not install.
- Nothing under `ontology/ledger/`, `tools/proofs/`, `tools/persistence`, the port or the store SPI.

## The layout and the reads

The README's section "The PostgreSQL arm" states both in full. In short:

- **Eleven tables.** One for each type the corpus writes, keyed by the subject's IRI, with a column for each functional predicate: `persistent_identity`, `merge_policy`, `quantity`, `account_definition` (one row for each version), `ledger`, `account`, `ledger_pass`, `posting` and `supersession`. Two link tables, `supersession_version` for `ldg:supersedingVersion`, which holds one value or more, and `definition_succession` for `fnd:supersededBy`, which a later write states of an earlier version.
- **Constraints.** Every reference a foreign key checked at commit, every exactly-one predicate `NOT NULL`, every position and revision at least 0, a pass's revision unique, a posting's direction debit or credit.
- **V.** A scalar subquery from the account's definition to its identity, to every version of the identity that a supersession for the account's owner names at or before the revision, ordered by the pass revision and limited to one, and the account's own version by `COALESCE` where none is.
- **R1 and R2.** One row, the latest posting's running balance and revision by a lateral join, with V at the read's revision and V at the posting's, so the read is the owner's supersessions for the account's definition beside the running balance on the latest posting, as the ledger's note says.
- **R3.** V now, and the signed sum over a recursive walk of `part_of_account`.
- **B.** Every account joined to its version's stated amount, left joined to the latest version for each owner and identity, by `DISTINCT ON`.

No query uses `NOT EXISTS` or an `EXISTS` of two patterns, the two forms of the ledger's note's warnings, and no SPARQL query was added or changed.

## Finding

**MSAI7-01. The corpus named a version that was never written.** `version_triples` gave each later version of the aggregate the parent `cap/v<k>`, but a change of terms never reaches the cap, so only `cap/v1` exists. No RDF read follows `ldg:partOf`, so no value or count was wrong, and LG-32's figures stand. The arm's foreign key refused it at the first commit, `Key (part_of)=(urn:bench:def/cap/v2) is not present in table "account_definition"`. The fix keeps the cap's one version as the parent, one triple's object for each change, with the same counts. SS4c holds every version and account a triple names to a written node, under every variant. This changes LG-32's corpus, which is the ledger unit's, so the maintainer may want its session to know.

## The check:testing-postgres finding from macOS

**Said in the package's README, and the task's dependency left as it is.** The run on macOS found `check:testing-postgres` fails on a worktree that was never bootstrapped. We reproduced it on machine S, in a virtual environment outside the tree holding only the fixture with its server and its own dependencies: `ImportError while loading conftest ... tools\conftest.py:84 ... ModuleNotFoundError: No module named 'pyshacl'`, exit 4. With `--confcutdir=tools/testing/postgres` the two tests passed, with `PytestUnknownMarkWarning: Unknown pytest.mark.requires`, since the requires plugin is a second package only `mise run bootstrap` installs.

The README is the right place because:

- `mise install` and `mise run bootstrap` are what every check needs, as the skill `lattice-mise` states, and every other test-support check task has the same shape, for example `check:testing-jena`.
- Adding `bootstrap:python` to the task's dependencies would run its single resolve beside `bootstrap:testing-postgres`'s pip in the same environment, since mise runs a task's dependencies in parallel, which the comment above `bootstrap:python` in `mise.toml` says corrupts `site-packages`. This run saw that hazard once, below.
- `--confcutdir` alone leaves the skip on an absent server unregistered, and adding the requires package as a dependency brings the same parallel pips back.

Question 3 below offers the alternative.

## Tests

| ID | Given, when, then | Level | Positive or negative | Pass criterion |
|---|---|---|---|---|
| I7-T1 | a history of 90 events with K = 3 under each variant | L1 | positive | `test_ss4c`: every version and account a triple names is a written node |
| I7-T2 | per-version and per-pass at K = 0 and 4, given the layer's terms and decoded | L1 | positive | `test_ss10`: no stand-in term is left, the facts the decode places equal the triples and `expected_stored`, and the supersessions and their versions number what the variant writes |
| I7-T3 | an untyped subject, a predicate with no column, a functional predicate twice, a term of the wrong kind, and a per-account record | L1 | negative | `test_ss11`: each fails the decode as a wrong result, the last as a predicate with no column |
| I7-T4 | the engines | L1 | positive | `test_ss12`: PostgreSQL runs per-version and per-pass, and the RDF engines all four |
| I7-T5 | each layer variant on PostgreSQL at K = 0 and 2 | L2 | positive | `test_ss13`: every sampled read equals the model, the stored count equals the arithmetic, a write and decode time exist only where there is a change, and no test database is left |
| I7-T6 | V, R1 or R3 on PostgreSQL one too high | L2 | negative | `test_ss14`: the run fails naming the variant, `postgresql`, the account and the two values |
| I7-T7 | B on PostgreSQL one too high for one account | L2 | negative | `test_ss15`: the run fails naming that account |
| I7-T8 | a write that loses one link row | L2 | negative | `test_ss16`: the run fails on the stored count |
| I7-T9 | the server absent | L2 | negative | the arm's nine cases skip, `needs postgresql_binaries, which cannot be imported here`, and the run prints `postgresql not run:` and exits 0 |
| I7-T10 | the old parent restored, in a script outside the tree | L2 | negative | the arm raises `ForeignKeyViolation` on `account_definition_part_of_fkey`, and the server stops and the process exits |
| I7-T11 | the full check task at its quick size | L3 | positive | `check.py` exits 0, so every read on every engine run matched the model |
| I7-T12 | the check task with PostgreSQL alone, at 2,000 and 20,000 events | L3 | positive | `check.py` exits 0, and each stored count equals the RDF engines' for the same history |

The tests above are run by the benchmark's own task. SS1 to SS9 are LG-32's and unchanged.

## One command

Run on macOS from the root of a bootstrapped checkout:

```bash
mise run check:ledger-supersession-read
```

It installs the fixture and its server, runs the 40 tests, then the benchmark at 2,000 and 20,000 events. A pass prints `40 passed` with `lattice: PostgreSQL tests ran on server version 16.15`, then `postgresql runs on server version 16.15, with the variants per-version, per-pass only, since the layer has no supersession on an account`, one line for each engine, variant, size and K, the `postgresql` lines for per-version and per-pass, and `report written to` the benchmark's `report.md`, with exit 0. Jena runs too where `mise run bootstrap:sparql-testkit` has built its jar. The figures are in `report.md` and `report.json`, each with the engine versions and the server version of the run. `LEDGER_SUPERSESSION_ENGINES=postgresql` runs the arm alone.

## What was run, in full

Run on machine S on 2026-11-23 and 2026-11-24, from the worktree, with `PYTHONUTF8=1` and the mirror's constraint files set. Another sub-agent worked on `tools/models/` in the same tree throughout. No figure below is a result of the benchmark.

- `mise run work:here`: one session, this one.
- With the server not installed, `mise exec -- python -m pytest benchmark/ledger-supersession-read -q -p no:cacheprovider -rs`: `SKIPPED [9] ... needs postgresql_binaries, which cannot be imported here`, `lattice: not run for a package this environment lacks: postgresql_binaries (9 tests)`, `27 passed, 9 skipped, 1 warning in 3.56s`, exit 0. SS4c was not written yet.
- With the server not installed, `LEDGER_SUPERSESSION_ENGINES=postgresql LEDGER_SUPERSESSION_QUICK=1 mise exec -- python benchmark/ledger-supersession-read/check.py`: `postgresql not run: needs postgresql_binaries, which cannot be imported here (mise run bootstrap:testing-postgres)`, `report written to` the benchmark's `report.md`, exit 0.
- A virtual environment outside the tree with the fixture, its server and its own dependencies only, then `python -m pytest tools/testing/postgres/tests -q` from the repository root: `ImportError while loading conftest ... tools\conftest.py`, `tools\conftest.py:84: in <module> from pyshacl import validate as _pyshacl_validate`, `ModuleNotFoundError: No module named 'pyshacl'`, exit 4. The same with `--confcutdir=tools/testing/postgres`: two `PytestUnknownMarkWarning: Unknown pytest.mark.requires`, `lattice: PostgreSQL tests ran on server version 16.15`, `2 passed, 2 warnings in 18.09s`, exit 0.
- `mise run check:testing-postgres`: `Successfully installed lattice-testing-postgres-0.1.0 postgresql-binaries-16.15.0`, `PostgreSQL 16.15.0 from postgresql-binaries, unpacked in` the venv, `lattice: PostgreSQL tests ran on server version 16.15`, `2 passed in 20.90s`, `Finished in 49.11s`, exit 0.
- `mise exec -- python -m pytest benchmark/ledger-supersession-read -q -p no:cacheprovider -rs`, the first run with the server: the nine cases on the server failed at the history's commit. The server's log, read from its directory, holds `ERROR: insert or update on table "account_definition" violates foreign key constraint "account_definition_part_of_fkey"`, `DETAIL: Key (part_of)=(urn:bench:def/cap/v2) is not present in table "account_definition"`, which is MSAI7-01. The run's output, captured in a terminal another session also used, never came back, and the terminal was stopped.
- After the fix, the same with `-x -v`: `collected 40 items`, `lattice: PostgreSQL tests ran on server version 16.15`, `40 passed, 1 warning in 27.63s`, exit 0. The warning is `Unknown config option: cache_dir`, as in every run of this suite.
- The probe of I7-T10, a script outside the tree, writing its own log: `server 16.15`, `raised ForeignKeyViolation insert or update on table "account_definition" violates foreign key constraint "account_definition_part_of_fkey"`, `stopped, exiting`, `atexit reached`, exit 0.
- `LEDGER_SUPERSESSION_QUICK=1 mise run check:ledger-supersession-read`, with `bootstrap:testing-postgres` then a dependency of the task: the two bootstraps ran their pips at the same time, and one printed `WARNING: Ignoring invalid distribution ~attice-testing-postgres`. Both ended `Successfully installed`, and no directory starting `~` was left in `site-packages`. Then `40 passed, 1 warning in 30.69s`, `jena not run: its test kit is not built or there is no java`, `postgresql runs on server version 16.15, with the variants per-version, per-pass only, since the layer has no supersession on an account`, 30 result lines at 2,000 events, four variants on Oxigraph and on rdflib and two on PostgreSQL at K = 0, 1 and 10, `report written to`, `Finished in 982.12s`, exit 0. The task now runs the fixture's bootstrap as its first step.
- `LEDGER_SUPERSESSION_ENGINES=postgresql mise run check:ledger-supersession-read`, with the task as it now is: the Oxigraph package's install and then the fixture's, one after the other, `40 passed, 1 warning in 29.82s`, `postgresql runs on server version 16.15, with the variants per-version, per-pass only, since the layer has no supersession on an account`, 12 result lines, `report written to`, `Finished in 103.68s`, exit 0. The stored counts are 29,232, 29,464, 29,412, 31,552 and 31,032 at 2,000 events, and 245,232, 245,464, 245,412, 247,552 and 247,032 at 20,000 events, for K = 0 and for per-version and per-pass at K = 1 and 10, the counts the RDF engines store in LG-32's table. No `lattice-postgres-*` directory was left in the temporary directory.
- `mise run check:portability`: exit 1, `portability: 10 problem(s)`, each in a file this slice did not touch, the same ten MSA-I13's and MSA-I5's packs list (TD-154). None names a file under `benchmark/ledger-supersession-read/`, and no task problem is reported for `mise.toml`.
- `mise run check:identifiers`: `identifier check passed: 2438 identifiers mentioned in 1048 files, 0 unresolved, 0 defined twice`.
- `mise exec -- python tools/writing_rules.py` on this pack and the two READMEs: `writing rules: 0 failure(s), 0 warning(s)`.

## Deliberate non-coverage

- **The figures.** None is reported here as the result. They are run on macOS from the one command, as the brief says.
- **Jena.** The test kit jar is not built on machine S, so Jena did not run here. It runs on macOS where the jar is built.
- **The per-account variants on PostgreSQL.** The layer has no supersession on an account. LG-Q58's option (c) would add one, `ldg:onAccount` on a supersession, and the arm would then gain the form.
- **The ordered folds of ledger-folds section 9, and receipts.** The sketch's row for MSA-I7 names the ordered folds and every constraint and receipt, and its falsifier is a gain on the ordered folds. This arm reads a balance, as the brief and the handover ask. The studio's receipts are not part of a ledger corpus. Question 2 asks whether the folds are wanted on PostgreSQL.
- **The decode of every write.** The timed write is the last change of terms alone, 232 or 180 triples, so `decode ms` measures one write of configuration and records, not a posting's. The history's load is decoded too and not timed.
- **A partitioned store.** One database, one schema. Where a supersession lives beside a root's units is MSA-Q20, answered by MSA-I10.
- **The account's key.** The layout keys an account by its IRI and states no unique constraint on its definition's identity, owner, key and period, which the decode cannot see without a join.
- **LG-34's laws of a balance.** Not built yet. The arm reads a balance as the ledger's note's section 6 says it is read now.
- **Server settings.** PostgreSQL's defaults apart from the fixture's address, port and socket.
- **Concurrency.** One writer and one reader.

## Doc delta

- `benchmark/ledger-supersession-read/README.md`: the section "The PostgreSQL arm", the parent's correction, the skip and server lines under "Run it", a row of "What it tests", and the files.
- `tools/testing/postgres/README.md`: one paragraph under "Install and run".
- `mise.toml`: one task's run steps and description.
- This pack. No ontology README changed, so no release note and no version.

## Index report

- **Asked.** `find ledger benchmark balance read backends` answered with MSC-Q2, ADR-A124 and MEC-56 at 0.71, and did not name the benchmark this slice extends, which reading the three READMEs found. `find query for absence and latest version --kind standard --activity query-writing` answered with RDF-4 at 0.73 and RDF-1 at 0.67, both read, and STD-128, read. They are SPARQL's, and no standard answers for an SQL read.
- **Gap recorded.** Against MEC-56, at the benchmark README's line 5: the benchmark measures a read of a balance against the version in force on Oxigraph, Jena, rdflib and PostgreSQL. A `measured by` edge from MEC-56, or from LG-Q52, to the benchmark would carry it.
- **`misses --near`.** It lists both of this slice's questions among the near answers, at 0.71 each, and 13 misses, none from this slice.

## Questions for the maintainer

1. **The RDF arms' stand-in terms.** LG-29 declared the record the benchmark's per-version and per-pass write as `b:` terms. The arm gives them the layer's names before the decode, and the RDF arms are unchanged. The options are (a) keep it so, as built, (b) the ledger unit moves the RDF arms to `ldg:Supersession` and `ldg:forOwner`, which changes their query text and so the query forms its LG-33 probes, since `ldg:forOwner` also matches every account, or (c) we move them here. We lean to (b).
2. **The ordered folds.** The sketch's row asks whether PostgreSQL gains on the ordered folds, a capped restoration over k postings through a window. Is a PostgreSQL arm of `benchmark/ledger-credit-kinds` wanted for MSA-I7, or is the balance read enough until MSA-I8?
3. **`check:testing-postgres` on a worktree never bootstrapped.** Built: a paragraph in the package's README. The alternative is `--confcutdir=tools/testing/postgres` in the task's command with `bootstrap:testing-requires` run as a step of the task, which frees it from `tools/conftest.py` at the cost of a pattern no other test-support task has.
4. **MSAI7-01 in LG-32's corpus.** Accept the fix here, or hand it to the ledger unit.
