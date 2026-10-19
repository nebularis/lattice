<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Python test speed

**Unit ID:** `python-test-melting`
**Status:** Done, 2026-10-09, branch `test/slow-py`. TM0-TM3, TM6-TM8 built and validated. TM4 and TM5
deferred, with reasoning recorded (slices table). All of TM-Q1 to TM-Q5 decided (status record).
**Trigger:** request, 2026-10-09. The `check:ontology-catalog` run took 19 minutes in a fresh
cloud environment, and about 31 s for one test locally.
**Status record:** [python-test-melting.md](../status/python-test-melting.md)
**Sketches:** [python-test-melting.md](../sketches/python-test-melting.md) (diagnosis),
[test-suite-performance.md](../sketches/test-suite-performance.md) (earlier, unmeasured)
**Takes on:** TD-18 and TD-29, both in the [technical debt register](technical-debt.md)
**Shares work with:** [repository-catalogue](../sketches/repository-catalogue.md) (§8.1)
**Governing decisions:** none new. No ADR is needed, since only test code changes. [ADR-A29](../../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise` is the entry point)

## Problem

`mise run check:ontology-catalog` runs 22 test modules in one `pytest` process. Reading the code, most of
the time looks like pySHACL validation repeated many times, not the tests' own logic. Re-read on
2026-10-09, the facts that hold are:

- `validate(...)` is called at 27 sites in 16 test modules, most with `advanced=True`.
- Those modules each declare their own `LOWER`, `MODEL`, `SHAPES` and `EVERY_SHAPE` at import. Eight layers
  contribute 16 shape files to `EVERY_SHAPE`, and Instrument's `constraints.ttl` alone holds 40
  `sh:sparql` constraints.
- `test_amendments`, `test_instrument` and `test_regimes` import constants from `test_parameter_bindings`,
  so a test module is also a library.
- `test_wording._vocab_closure()` rebuilds its closure on every call.
- Nothing passes `inplace`, so pySHACL clones the data graph after the caller has already built a fresh
  `MODEL + data` copy.
- Five tests shell out to `git grep` (`test_instrument`, `test_constitutive_terms`, `test_terms_in_time`,
  `test_wording`, `test_keys`).

Everything about relative cost is a hypothesis until TM0 profiles it.

## Principles

1. **Measure first.** TM0 decides which later slices run, and in what order.
2. **No test changes meaning.** Every assertion is unchanged. A slice is accepted only when the
   per-test outcomes before and after are identical (the comparison is under Validation).
3. **A cache must not hide a failure.** Cached results are keyed on everything that changes the result,
   and a graph a test has mutated is never served from it.
4. **No catalogue dependency.** Nothing here waits on RC-Q1 to RC-Q8. The support module holds the
   locations as plain constants, so the repository catalogue can replace them later without touching a
   caller.

## Slices

| Slice | Scope | Test modules touched | Level | Estimate | Status |
|---|---|---|---|---|---|
| TM0 | Measure and baseline. No behaviour change | none (and `tools/time_ontology_tests.py`) | L7 | 30k | **done** |
| TM1 | Shared, session-scoped graph cache in `tools/conftest.py` (TM-Q2: option B) | all 16 modules with a `validate()` call site | L1, L2 | 60k | **done**, rolled out to every module, not piloted on two |
| TM2 | Validation cache, keyed on graph content (fixed mid-roll-out: a test that mutates its own graph in place and revalidates must not see a stale report) | same 16 | L1, L2 | 50k | **done** |
| TM3a | Roll out to the Instrument family | `test_instrument`, `test_regimes`, `test_terms_in_time`, `test_amendments`, `test_parameter_bindings`, `test_constitutive_terms` | L1 | 60k | **done** |
| TM3b | Roll out to Behaviour, Wording and Keys | `test_behaviour_split`, `test_behaviour_records`, `test_behaviour_nested`, `test_wording`, `test_keys` | L1 | 70k | **done** |
| TM3c | Roll out to the rest | `test_eligibility_examples`, `test_peril_vocabulary`, `test_mork_order_relations`, `test_substrate_extensions`, `test_applied_shared_contracts` | L1 | 50k | **done** |
| TM4 | Narrow shapes in one-triple mutation tests. Only if TM0 shows it matters | the slowest of those | L1 | 60k | **deferred**. TM3's own measurement shows validate() call volume (SHACL-SPARQL evaluation over necessarily-distinct mutated graphs) dominates, which TM4 would help; but the target is already met by a wide margin (TM7) and TM4 carries real, stated correctness risk (a narrowed shape set silently missing a message another shape file would add). Not worth the risk without a stronger forcing need |
| TM5 | Reasoner rows: skip condition, `slow` marker, batching. Only if TM0 shows it matters | those with `needs_reasoner` | L1, L4 | 60k | **deferred**. Step 1 (skip condition) already holds: `reasoning.available()` skips without starting a JVM when the jar is not built, confirmed by every run in this environment. Steps 2 and 3 are unmeasurable here (the jar is never built in this sandbox, so every reasoner row already skips) and step 3 is explicitly its own slice, briefed on `main`, crossing into Java |
| TM6 | Repository scans in Python, not `git grep` (TD-29) | the five that shell out | L1 | 50k | **done**. Also fixed a real, pre-existing Windows-only `UnicodeDecodeError` in `test_c6_10` (git grep's subprocess output decoded with the console codepage, not UTF-8); that test now fails with its true, pre-existing `AssertionError` (retired terms in `ontology/examples/insure-o/`, out of this plan's scope) on every platform instead of crashing on one |
| TM7 | Parallel run with `pytest-xdist`. Only if TM0 and TM3 leave it worthwhile | none | L7 | 25k | **done**. The dominant lever: 456s serial to ~124-139s with `-n auto --dist loadfile`, confirmed byte-identical outcomes |
| TM8 | Close out. TD-18 and TD-29 rows removed, developer guide updated | none | L0 | 25k |

About 540k tokens in all. TM4, TM5 and TM7 may be dropped, so the realistic total is 400k to 540k.

Order is TM0, TM1, TM2, TM3a to TM3c, then TM4 to TM7 in the order the profile ranks them. TM6 is
independent of TM1 to TM5 and can run at any point after TM0.

### TM0. Measure and baseline

Run on the maintainer's machine first. The cloud figure in TD-18 (19 minutes) has not been reproduced
locally, so TM0 also records the vCPU count and elapsed time of one CI run for comparison.

1. Record the baseline of per-test outcomes (see Validation) and keep it outside the repository.
2. `python -m pytest tools -q -p no:cacheprovider --durations=40 --durations-min=1.0` for the slowest tests.
3. `python -m pytest tools --collect-only -q -p no:cacheprovider` timed, for import-time parsing.
4. `tools/time_ontology_tests.py` for per-module wall time. Its docstring still says `.local/`. Fix it, and
   add a `mise` task for it, since `mise` is the only entry point (ADR-A29). The name is settled in TM0.
5. `cProfile` on `test_c8_02_every_instrument_example_conforms`, as the sketch gives it, then the
   cumulative-time table. It shows whether time sits under rdflib's SPARQL evaluation, graph merge and
   clone, or parsing.
6. Record in the status record each of the sketch's six suspects as confirmed, refuted or unclear, with
   the number that shows it, and the order TM4 to TM7 will run in. Add `--durations` output for the
   five slowest modules.

Pass criterion: the status record holds a ranked table of measured costs, and we have set TM-Q1.

### TM1. Test support module and cached graphs

Adds `tools/ontology_test_support.py` (name settled under TM-Q2), importable by sibling tests as
`reasoning` already is, with no `sys.path.insert`. It holds:

- the one place a test finds the repository root, and the ontology root
- the layer stack as constants (`LOWER`, the layer order, `ALL_SHAPES`), and the Instrument extraction
  shape list now repeated in four tests
- `graph(*sources)`, memoised on the resolved source paths, returning a graph no caller mutates
- `stack(...)` and `shapes(...)` helpers that return the same object for the same arguments

`test_parameter_bindings` and `test_constitutive_terms` use it, and the three modules that import
constants from `test_parameter_bindings` still work through re-exports until TM3a moves them.

A guard checks that no cached graph changes size during a session. It runs once, at session end, in
`tools/conftest.py`.

New tests in `tools/test_ontology_test_support.py` (about 8): same arguments return the same object,
different paths return different graphs, a mutated cached graph is detected by the guard, the layer
stack matches the files on disk, and every path constant exists.

### TM2. Validation cache and `inplace`

`validated(example, shape_set, *, advanced, inference)` in the support module returns the whole pySHACL
result for an unmodified example file, keyed on (stack, shape set, example path, options). The report is
kept whole, so the violation and the warning views of `_results()` come from one run. A graph built or
changed by the test is validated directly and never cached.

`inplace=True` is passed where the data graph is a fresh `MODEL + data` copy, which pySHACL would
otherwise clone again. This needs a check first. With `advanced=True`, SHACL rules may add triples to the
data graph, which is why `inplace` defaults to false. A fresh copy makes that harmless, and TM2 states in
its Validation Pack that no test reads the data graph after validation.

New tests (about 7): a repeated call is a cache hit, a different shape set or option is a miss, severity
views agree with a direct run, a mutated graph bypasses the cache, and a shape that fails still reports
the failure through the cached path.

Pass criterion: the baseline comparison is identical and the pilot modules' durations fall. The
`framework-lots` and `EVERY_SHAPE` pair, validated by eight tests today, by the sketch's count, runs once.

### TM3a to TM3c. Roll out

Each module drops its own `LOWER`, `MODEL`, `SHAPES`, `EVERY_SHAPE` and `_graph`, calls the support module,
and routes repeated `validate` calls through `validated` where the input is an unmodified example.
`test_wording` replaces `_vocab_closure()` with a cached call. Sibling imports of `test_parameter_bindings`
are repointed at the support module, so a test module stops being a library. Each slice ends with the
baseline comparison identical for its modules. TM3 is mechanical and adds no test cases. See TM-Q3 on
slice size.

### TM4. Narrow shapes in one-triple mutation tests

Tests such as `test_c8_08`, `test_c8_09` and `test_c7c_09` change one triple and read one message, but run
the whole Instrument shape set for 2 s to 5 s. Where the profile shows the cost is validation, each is
pointed at the shape file it exercises. Two risks, and the slice checks both.

- SPARQL constraints depend on prefixes declared in their shape graph, so a narrowed graph must carry
  them.
- A narrowed run could miss a message that another shape file would add. Each narrowed test asserts the
  same message as before and the slice's probe breaks the targeted constraint and shows the test fails.

Conformance rows keep validating against every layer's shapes.

### TM5. Reasoner rows

HermiT rows start one JVM each (5.1 s and 2.7 s observed). Work in this order, stopping when the profile
says the gain is small.

1. Check the skip condition. A cloud runner that builds the testkit jar runs them, one that does not
   skips them silently. Record which, since it changes what "green" means.
2. Register a `slow` marker in `pyproject.toml` and apply it, so a quick local run can deselect them. The
   full run in CI and before a merge keeps them.
3. Batch consistency checks into one Java run per module. This changes `platform/reasoning-testkit`
   (ADR-A83) and the Python call into it, which is two modules, and is the only part of this plan that
   crosses into Java. It is its own slice, briefed on `main` before a branch.

### TM6. Repository scans in Python (TD-29)

Five tests run `git grep` to find a retired term or a pinned version. TM6 adds `repo_files(roots,
patterns)` to the support module and moves them to it. It takes its roots as arguments, so the catalogue
can supply them later. It also removes the macOS regex failure of TD-29 and a dependence on `.git` that a
source archive does not have. TM-Q4 decides what the scan lists. The open half of TD-29, a check that no
other test builds a `git grep` pattern from a Perl-style escape, becomes a test over the same files.

### TM7. Parallel run

`pytest-xdist` with `--dist loadfile` suits independent files, and each worker repeats the import-time work
that TM1 to TM3 share only within a process. It is added only if TM0 shows the runner has several vCPUs and
the remaining time justifies a new dependency in `pyproject.toml` and `uv.lock`. The `mise` task keeps
a serial form.

### TM8. Close

Remove the TD-18 and TD-29 rows, naming this plan, and repoint the TD-18 reference in the
[formal methods plan](formal-methods.md) (CI time), which would otherwise dangle. Add the support module and
the timing task to the developer guide. The two sketches are superseded and the maintainer decides whether
they are deleted. Record final timings against the TM0 baseline.

## Design questions

Each follows the [lattice-design](../../../.claude/skills/lattice-design/SKILL.md) form. Leanings are
hypotheses and wait for the maintainer.

### TM-Q1. What is the target?

**Decided 2026-10-09:** any speedup is beneficial; target 3-4 minutes or under, otherwise
split long and short runs for CI. Met: ~124-139s under `pytest-xdist` (status record).

Not asked until TM0 gives numbers. Leaning is to state it as a ratio to the TM0 baseline on one machine,
plus an absolute ceiling for the cloud run, so that a slow runner does not hide a gain.

### TM-Q2. Where do the shared graphs and the validation cache live? (blocks TM1)

**Decided 2026-10-09: option B,** session-scoped fixtures in `tools/conftest.py` only. Built
with a deliberate reading recorded in the status record: the cache (`graph_cache`, `validated`) is the
fixture; each adopting module declares one `@pytest.fixture(scope="module", autouse=True)` that assigns
its own `MODEL`/`SHAPES`/`validate` names onto `request.module`, so no sibling support module exists and
no call site outside that one fixture per module was rewritten.

| Option | Design overheads | Runtime overheads |
|---|---|---|
| **A.** A sibling module `tools/ontology_test_support.py` with memoised functions, and a small `tools/conftest.py` for the end-of-session guard | tests keep their module-level constants and call sites. Works at import and collection time. Sibling imports need no `sys.path.insert`, since pytest puts `tools/` on the path | one copy per process |
| **B.** Session-scoped fixtures in `tools/conftest.py` only | idiomatic pytest. Every test that uses `MODEL` changes its signature, which touches hundreds of tests across 16 modules. Module-level uses, such as `parametrize` lists, cannot use a fixture | one copy per process |
| **C.** A package under `packages/`, like `packages/minting` | usable from other projects. Packaging and bootstrap work for a test helper that nothing outside this repository needs | one copy per process |

**Leaning A.** It changes the fewest lines, which keeps the outcome comparison meaningful. If a downstream
project needs the helper, C can wrap it later.

### TM-Q3. Slice size for TM3 (blocks TM3a)

**Decided 2026-10-09:** the agent's choice, per the maintainer. Option A, batches of four to six, one commit
per batch (TM3a, TM3b, TM3c, as the plan already had them).

The lifecycle splits a slice at more than two modules touched. TM3a to TM3c touch four or five test
modules each, with no new test cases.

| Option | Consequences |
|---|---|
| **A.** Accept batches of four or five, as the plan has them | three reviews. Each batch is a mechanical edit checked by one outcome comparison |
| **B.** Seven slices of two modules | seven reviews for the same edit |
| **C.** One slice for all 14 | one review, but a large diff to read. A failure is harder to place |

**Leaning A,** since the size rule exists to keep review tractable and each batch has one command and one
comparison.

### TM-Q4. What do the Python scans list? (blocks TM6)

**Decided 2026-10-09: option A.** Built as `repo_files` in `tools/conftest.py`. The known
risk (untracked files the old `git grep` would not see) was hit for real during the roll-out, by this
unit's own new `test_repo_files.py` matching its own fixture text; fixed by allow-listing that one file,
the same precedent `test_instrument.py` already set for its own `RETIRED` constant.

| Option | Design overheads | Runtime overheads |
|---|---|---|
| **A.** Walk the tree from given roots, skipping a named list of build and dependency directories | no `.git` needed, so it works in a source archive. Includes untracked files, which a `git grep` would not, so the skip list must be right | one pass per call, cacheable |
| **B.** `git ls-files`, read in Python | tracked files only, as `ontology_catalog.py` and the link repair plan already do. Fails without `.git` | one subprocess per call |
| **C.** Keep `git grep` and only forbid Perl escapes | smallest change. Keeps the `.git` dependence and a subprocess per check | unchanged |

**Leaning A,** to match the catalogue sketch's rule that nothing depends on `.git` of LATTICE's own.

### TM-Q5. May TM7 add `pytest-xdist`?

**Decided 2026-10-09:** yes, if it can be made to work in this environment. Confirmed
working (16 vCPUs on the machine that measured it); added to `pyproject.toml`'s `test` extra and wired
into `check:ontology-catalog`.

Decide after TM3, with the TM0 vCPU figure. A new dependency changes what `bootstrap` installs for
everyone. Leaning is yes only if the remaining serial time is still too long and the runner has at least
four vCPUs.

## Validation

**One comparison, used by every slice.** Per-test outcomes must match the TM0 baseline exactly.

```bash
python -m pytest tools -q -p no:cacheprovider -rA 2>&1 | grep -E '^(PASSED|FAILED|SKIPPED|ERROR)' | sort > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt && echo identical
```

`/tmp/before.txt` is written the same way at TM0, on the same machine and with the same jar built or not
built. Run from the repository root. A pass is `identical`, and a faster `mise run check:ontology-catalog`.
The Validation Packs add each slice's own new tests, a slice-specific adversarial probe and the artefacts to inspect.

| Slice | Probe shown at the gate |
|---|---|
| TM1 | change one triple in a cached graph during a test and show the session guard fails |
| TM2 | break one SHACL constraint and show every test that uses it still fails through the cached path |
| TM3 | reintroduce a module-level `MODEL` copy and show the modules' import time rises again |
| TM4 | disable the targeted constraint and show its narrowed test fails |
| TM6 | plant a retired term in a scanned directory and show the test fails on macOS and Linux |

## Deliberate non-coverage

- Making individual SHACL-SPARQL constraints faster, or replacing rdflib's evaluator. TM0 may show it
  dominates, in which case it becomes a new plan.
- Other test suites (`tools/persistence`, `tools/vocabulary`, `workers`, the Java and frontend suites).
  The support module can serve them later.
- Version literals in tests, which TD-26 covers. The support module is a natural home for a
  `current_version(module)` helper, but where a version is stated once is an ontology decision, not a
  test one.
- The repository catalogue itself. Its RC3 slice replaces this plan's path constants (sketch §8.1).
