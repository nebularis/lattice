<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Store isolation probes

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md) that checks, on PostgreSQL and on Fuseki over TDB2, the store behaviours the protocol models of [`tools/models/multi-store-protocols`](../../tools/models/multi-store-protocols/README.md) assume. A model checker explores every interleaving of the steps a model has, so a model is only as good as its steps. Where a model takes a request, a guard or a read to be one step, a store has to make it one, and these probes show where each store does.

## The assumptions and the probes

| Probe | Assumption | Models and configurations that rest on it |
|---|---|---|
| ISO-01 | A guarded compare-and-set request is one atomic step. Of two writers that read the same version, one applies and the other changes nothing | Model A (`ModelA_Atomic`), the guard in each store of X1 (`X1_Applied*`), X5's per-step guards, Protocol A's pass (`PA_OnRead*`), each pass of X6 (`X6_Closed`) |
| ISO-02 | The same, for four writers that loop until the version reaches a target | Model A with three writers, X1 with a zombie (`X1_AppliedZombie*`) |
| ISO-03 | A store answers a command that has a receipt and applies any other in one step, so two deliveries of one command apply it once | X1 with receipts only (`X1R_Applied`, `X1R_AppliedZombie2`), X1's `Duplicate` answer, X5's receipts |
| ISO-04 | A request is applied all or nothing, and a reader never sees a request that is later rolled back | Model A's atomic step, X5's one request (`X5_Whole*`, `X5_Fenced*`), Protocol A's pass written in one request (`PA_*`) |
| ISO-05 | Two requests that write the same two rows are each applied whole, never interleaved step by step | X5 (`X5_Built*`, `X5_Whole*`, `X5_Fenced*`), Protocol A (`PA_OnRead*`) |
| ISO-06 | A reader of one store sees a request's effects together or not at all. Two separate reads may see two states | X1's reader (`X1_Torn*`), torn only across stores, X5's plan read in one step, X2's read set (`ReadSetTrue`) |
| ISO-07 | A write whose reply has come is seen by the next read from any client | X1's `Duplicate` answer from a receipt, X5's read of the receipt after its request, X3's relay reading committed receipts |
| ISO-08 | A relay that has published every position up to its mark never finds a lower position committed later | X2's watermark (`X2_Watermark*`, which takes commits to be in position order), X3 (`X3_ByPosition*` shows the skip, `X3_PerStream*` the relay that avoids it) |
| ISO-09 | A fenced store refuses every write that commits after the fence, so a copy taken after the fence holds every acknowledged write | X4's fenced cutover (`X4_Fenced`, `X4_FencedTimeouts` and their wide instances) |
| ISO-10 | A refused guarded write can return the version it found, which differs from the version the writer expected | X6 with the refusal returning the revision (`X6_Closed`, `X6_StartOpen*`), Protocol A's refusal (`PA_OnRead*`) |
| ISO-11 | A check of another row and a write made on it are not interleaved with another writer's, so two writers cannot each take one of the last two rows | Model A's `Atomic` against `SnapshotNoWWDetect`, and the catalogue's single-store transaction row, "isolated to the store's level" |

Each probe runs in several forms. A form that does what the model assumes is expected to show the anomaly in no repetition. A control, a form that breaks the assumption on purpose, for example a guard checked by an earlier read instead of in the request, is expected to show it in every repetition, which shows that the clients really did interleave as the probe says. On PostgreSQL a form also runs under each isolation level that changes its answer, and some forms show the anomaly at one level and not at another, as PostgreSQL documents.

| Probe | PostgreSQL forms | Fuseki and TDB2 forms |
|---|---|---|
| ISO-01 | guarded, unguarded | guarded, unguarded |
| ISO-02 | guarded, four writers to 200 | guarded, four clients to 40 |
| ISO-03 | receipt checked by an earlier read, with a unique key, inserted first with `ON CONFLICT DO NOTHING` | receipt checked by an earlier read, checked in the request |
| ISO-04 | a reader during the transaction, which then fails on a division by zero | a reader polling over HTTP while a request of 20,000 triples runs and then fails on `CLEAR GRAPH` of a graph that holds nothing, and a TDB2 read transaction on another thread during a write transaction that aborts |
| ISO-05 | two transactions each moving rows a and b in opposite orders, each step guarded on its own row | two requests doing the same, sent at once |
| ISO-06 | two reads in one transaction, two reads in two transactions | one query and two queries over HTTP, one TDB2 read transaction and two |
| ISO-07 | a new transaction, a transaction begun before the commit | a new request from another client |
| ISO-08 | a position from a sequence, from a counter row the transaction locks | a position computed in the request by four clients, taken by a request of its own |
| ISO-09 | the fence read in the write's transaction, read `FOR SHARE` | the fence checked by an earlier read, checked in the write's request |
| ISO-10 | one statement with the version from its snapshot, a locking read before the guard, the version read by a later statement | the version read after the refusal |
| ISO-11 | the check by an earlier read, in the write's statement | the check by an earlier read, in the request |

`EXPECTED` in [`check.py`](check.py) holds the expected answer of every row, and the report prints it beside what each store did.

## How the clients are interleaved

**On PostgreSQL** one thread drives every connection, each in autocommit with its transactions begun and ended by the probe, step by step in the order the probe states. A statement that has to wait on another transaction's lock runs on a thread of its own, and the next step is taken once `pg_stat_activity` shows it waiting on a lock, never after a sleep. The server is the fixture's, [`tools/testing/postgres`](../../tools/testing/postgres/README.md), with `deadlock_timeout` at 50 ms, since ISO-05 meets a deadlock in every repetition.

**On Fuseki** the Maven project here starts Fuseki main in its own JVM over a TDB2 dataset in a temporary directory, on a free port of the loopback interface, and sends each request over HTTP from clients that each hold connections of their own. Two clients that must act at the same moment wait on a barrier and then send. A step that must follow another is taken once the first has had its reply. Since each HTTP request is one transaction, a probe that needs a transaction held open, ISO-04 and ISO-06, also runs on TDB2 called in process, with transactions on two threads held apart by barriers. The project runs once for each Jena version, 5.1.0, the platform's, and 6.2.0, the Fuseki release the studio's stack downloads, each compiled into `target/jena-<version>/`. Fuseki main serves the same engine as the Fuseki server jar without its user interface.

Every repetition writes under keys or IRIs of its own, so no repetition reads another's state.

## Pass criterion

Every row does what `EXPECTED` says of its store, form and mode. A row with no expectation, an expected row that no run produced, a row with no repetitions, and a row of a probe that counts reads beside the writes or races lost where that count is 0 fail. **Time never fails it.** The report is `report.md` and `report.json` here, generated and git-ignored, with each row's outcomes, for example "the second refused: serialization failure (50)", and its counts.

A row that fails means a store did something other than what is recorded of it, for example after an upgrade. Read the row's outcomes before changing its expectation.

## Run it

```bash
mise run check:store-isolation-probes
STORE_ISOLATION_QUICK=1 mise run check:store-isolation-probes          # 10 repetitions on PostgreSQL and 5 on Jena
STORE_ISOLATION_ARMS=postgresql mise run check:store-isolation-probes  # one arm, postgresql or jena
STORE_ISOLATION_JENA_VERSIONS=6.2.0 mise run check:store-isolation-probes
```

On Windows, in PowerShell, set a variable with `$env:STORE_ISOLATION_QUICK = '1'` before the same `mise run` line. The task installs the PostgreSQL fixture first, then runs this directory's tests, then both arms. `STORE_ISOLATION_PG_REPS` and `STORE_ISOLATION_JENA_REPS` set the repetitions, 50 and 20 by default. It is never a dependency of `check`.

An arm whose server or tool is absent is skipped with the reason, and the run exits 0 where nothing else failed. The PostgreSQL arm needs the fixture's server, which `mise run bootstrap:testing-postgres` installs. The Jena arm needs `mvn` and `java`, which `mise` puts on the path, and resolves Jena from the Maven repository on its first run at each version.

A pass prints the tests' "13 passed", a line for each PostgreSQL row as it runs, then `PASS` with the store, version, form and mode and "n of m, expected never" or "m of m, expected always" for each of the 48 PostgreSQL rows and 20 rows at each Jena version, and ends with the line below and exit 0.

```text
isolation probes: 88 as expected, 0 failed, 0 skipped, <seconds> s
```

A figure from the report quoted elsewhere states its run, which the report's first line gives: the date, the Python version, the kind of machine, the PostgreSQL and psycopg versions, and the Jena, TDB2, Fuseki and Java versions of each Jena run.

| File | Role |
|---|---|
| `check.py` | the assumptions, `EXPECTED`, the PostgreSQL probes, the run of the Jena arm, the verdict and the report |
| `test_check.py` | the check's own tests: the expectations against the probes and the Java arm's rows, the verdict, the reading of the Jena results, and three PostgreSQL probes on the fixture's server, which skip where it is absent |
| `pom.xml` | a standalone Maven project, outside the platform reactor, depending on `jena-tdb2` and `jena-fuseki-main` at `jena.version` |
| `src/main/java/.../IsolationProbes.java` | the Jena arm. It writes what it observed to `target/jena-<version>/results.json` and judges nothing |
