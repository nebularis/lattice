<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: python-test-melting TM11, the engine split

**Unit:** `python-test-melting` ([plan](../plans/python-test-melting.md), TM11's row)
**Machine:** S, Windows. **Branch:** `py-test-xtra`, from `docs/placement-vehicles-structure`. Commits are the maintainer's.
**Plan and test cases:** [python-test-melting plan](../plans/python-test-melting.md), TM11's row
**Decisions:** the maintainer confirmed `check:mork-compilers` is in TM11's scope (2026-10-27) and asked for the agent's own leaning on ordering against TM12, recorded in TM10's Validation Pack and acted on here
**Depends on:** [TM9](python-test-melting-tm9.md), [TM10](python-test-melting-tm10.md)

## Invariant

A suite TM9 found running generated SPARQL with no engine opt-in gets one: its behaviour tests run on the default engine, and a test whose subject is one engine's behaviour runs in its own `check:<suite>-conformance` task, with every engine, on demand and before a merge, never in `check`. No behaviour change to `check:mork-compilers` itself: every one of its 126 tests passes exactly as before.

## What changed, and why it is not what the brief's letter asks for

TM11 reads: "Their behaviour tests run on Oxigraph" (the skill's usual default, STD-153). Building the engine abstraction `tools/mork_compilers' own test suite needed (it had none: eight files called `Graph.query()` directly, with no `@engines.each_engine`-style opt-in) and running the whole suite on Oxigraph found a real divergence on one of its 126 tests, not a defect in the new wrapper. Flipping the default would have turned a passing test into a failing one for a reason this unit does not fix, so **`check:mork-compilers` keeps rdflib as its default**, exactly as it has always run, and `check:mork-compilers-conformance` is the task that runs Oxigraph. This departs from TM11's literal brief, is recorded here per `lattice-design`'s rule for a design question the brief does not answer, and is evidenced by [TSD-41](../../architecture/triple-store-discovery.md#tsd-41-an-aggregate-over-an-expression-that-errors-on-one-row-of-a-group-is-unbound-on-oxigraph-and-skips-the-row-on-rdflib) and the new standard it grounds, [STD-274](../standards.md).

## What changed

- **`tools/mork_compilers/src/mork_compilers/engines.py`** (new). `run_query(graph, text)` in place of `graph.query(text)`, dispatching on `MORK_SPARQL_ENGINE` (`rdflib` by default). On rdflib it returns `graph.query(text)` unchanged, so every existing call site's attribute access (`row.question`), positional access (`row[0]`) and `.asdict()` keep working. On Oxigraph the graph's triples are loaded into a disposable in-memory store, queried through `pyoxigraph`, and each solution's terms converted back to rdflib terms, with the same three access patterns reproduced by a small `_Row` wrapper.
- **Eight test files** (`test_alternative_bounds.py`, `test_closure_readings.py`, `test_concept_backends.py`, `test_concept_conditions.py`, `test_evidence_bindings.py`, `test_hierarchical_conditions.py`, `test_profiles.py`, `test_set_readings.py`) now call `run_query(graph, text)` in place of `graph.query(text)`, one import and one call-site change each, no test logic touched. Two module docstrings that said "with rdflib's own engine" corrected to say Oxigraph is tried by the conformance task.
- **`check:mork-compilers`**: `-n auto`, sized by the shared `pytest_xdist_auto_num_workers` hook `tools/conftest.py` already carries (TM10), since `tools/mork_compilers` is a subdirectory of `tools/` and pytest discovers that `conftest.py` walking up from the test files. `MORK_SPARQL_ENGINE = "rdflib"` stated explicitly, matching its own default, so the task's intent reads without opening the module.
- **`check:mork-compilers-conformance`** (new). Same command, `MORK_SPARQL_ENGINE = "oxigraph"`, not in `check`'s own dependency list, run on demand and before a merge (skill `lattice-lifecycle`).

## A real divergence found, not fixed here (TSD-41, TD-92)

`check:mork-compilers-conformance` fails exactly one test, every run: `test_closure_readings.py::RelianceTests::test_a_profile_row_names_the_union_of_its_conditions_closures`. A `GROUP_CONCAT` over a `UNION` of nested aggregate sub-selects drops one record's (`ada`'s) contribution on Oxigraph and keeps it on rdflib. The mechanism is not yet traced to either engine's source (TSD-Q20). Recorded in [triple-store-discovery.md](../../architecture/triple-store-discovery.md) (TSD-41) and [technical-debt.md](../technical-debt.md) (TD-92), not fixed by this unit: `python-test-melting` is about test speed and defaults, not compiler correctness.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TM11-01 | `check:mork-compilers`, unchanged default (rdflib) / run / 126 passed, 2 subtests passed, identical to before this unit | L1 | + |
| TM11-02 | `check:mork-compilers-conformance` (Oxigraph) / run / exactly 1 failed (TSD-41), 125 passed, 2 subtests passed, every run | L1 | + (the failure is expected and named) |
| TM11-03 | every other backend test's rows, both engines / compared field by field / identical except the one named field of the one named record | L3 | + |

## One command

```bash
mise run check:mork-compilers
mise run check:mork-compilers-conformance
```

## Artefacts to inspect

`tools/mork_compilers/src/mork_compilers/engines.py`. The eight call-site changes. `mise.toml`'s two task definitions.

## Deliberate non-coverage

- Tracing TSD-41's mechanism to either engine's source (TSD-Q20): a separate investigation, not this unit's.
- A dedicated `PER_WORKER` constant for `tools/mork_compilers`: the shared one from TM10 (900 MiB, measured on the larger `check:ontology-catalog`) already applies, since pytest discovers `tools/conftest.py` for any test file under `tools/`, and this suite's own peak (0.32 GB tree, one worker) is comfortably under it. A suite-specific constant would only run more workers on a short machine, which this suite's own small size (126 tests, under 25s) does not need.

## Handoff

Built on `py-test-xtra`, autonomously, per the maintainer's instruction this session. Registers updated in a separate commit before this one (TSD-41, STD-274, STD-275, TD-91, TD-92, TD-87 corrected), per the project's own convention that a finding is recorded before, or in the same unit as, the code that found it.

**For TM12:** `check:mork-compilers` no longer needs its own entry in TM12's six-item list, since it already runs on the defaults (`-n auto` with `mem_check`) as part of this slice. TM12's remaining five: `check:workers`, `check:vocabulary`, `check:reference-eligibility`, `check:minting-python`, `check:persistence-library`.
