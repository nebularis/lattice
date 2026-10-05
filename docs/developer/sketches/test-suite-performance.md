<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Test suite performance

**Unit:** none yet. **Status:** unplanned sketch, 2026-10-05. Registered as technical debt TD-18,
with TD-19 for the gap found while writing it.
**Reads with:** [technical-debt.md](../plans/technical-debt.md), `mise.toml`.

---

## 1. Premise

The Python test suites under `tools/` now take minutes to run. Ten of the ontology test modules
together took 129 seconds for 383 tests during CCS C7b (2026-10-05). `tools/test_regimes.py` alone
takes about 18 seconds for 61 tests, and `tools/test_terms_in_time.py` about 12 seconds for 30. Most
of that time appears to go to repeated setup, not to what each test checks. This sketch records how
to measure where the time goes, the likely causes, and the fixes worth trying once the measurements
confirm them. Nothing here has been measured with a profiler yet.

## 2. Measuring

Each command below writes nothing to the repository. `cProfile`'s output goes to `/tmp`.

**The slowest tests.** pytest reports the setup, call and teardown time of each test:

```bash
python -m pytest tools -q -p no:cacheprovider --durations=30 --durations-min=1.0
```

**Collection.** The test modules parse the ontology stack at import time (`MODEL = _graph(...)` at
module level), so that cost lands in collection, which `--durations` does not show:

```bash
time python -m pytest tools --collect-only -q -p no:cacheprovider
```

**Each module on its own**, slowest first:

```bash
for f in tools/test_*.py; do /usr/bin/time -p python -m pytest "$f" -q -p no:cacheprovider 2>&1 | awk -v f="$f" '/^real/ {print $2, f}'; done | sort -rn | head -20
```

**Inside a test.** `cProfile` is in the standard library. Sorted by cumulative time, it shows whether
a run is dominated by rdflib parsing, pySHACL validation, owlrl closure or waiting on a subprocess:

```bash
python -m cProfile -o /tmp/pytest.prof -m pytest tools/test_regimes.py -q -p no:cacheprovider
```

```bash
python -c "import pstats; pstats.Stats('/tmp/pytest.prof').sort_stats('cumulative').print_stats(30)"
```

`pyinstrument` gives a more readable call tree, but is a new dependency, worth adding only if
`cProfile`'s output proves too noisy.

## 3. Likely causes

| Suspect | Why it is slow | Where |
|---|---|---|
| **Parsing the ontology stack at import** | each module parses about 13 spec and vocab files with rdflib, and many modules do so separately | every `tools/test_*.py` with a module-level `MODEL` |
| **pySHACL against every layer's shapes** | `EVERY_SHAPE` with `advanced=True` runs every SHACL-SPARQL constraint over the model and an example, once per example | rows C7a-02 and C7b-02 |
| **Reasoner consistency tests** | each test starts a Java subprocess, paying JVM start-up and an OWL API parse every time | rows C6-03, C7a-03, C7b-03 and others |
| **OWL RL closures** | owlrl closes a full graph in pure Python | rows C7a-15 to C7a-18 and C7b-11 |
| **`git grep` and subprocess checks** | cheap one at a time, but they add up | rows C6-10, C7b-17, the import guard test |

## 4. Fixes to try, once measured

1. **Parse the stack once per session.** A shared `tools/conftest.py` with a session-scoped fixture
   holding the parsed model and shapes, in place of each module parsing its own. If parsing
   dominates, this is likely the largest single gain.
2. **Batch the reasoner.** One Java run that checks every example's consistency, in place of one
   JVM per example.
3. **Narrow the shapes.** Run each negative test against the shapes it exercises. Keep validation
   against every layer's shapes for the conformance rows only.
4. **Run in parallel.** `pytest-xdist` (`-n auto`) shortens wall-clock time without removing any
   of the above. It is a new dependency.
5. **Mark the slow rows.** A `slow` marker on the reasoner and OWL RL rows lets a quick local run
   skip them, with the full run kept for CI and before a merge.

Each fix keeps every test's assertion unchanged. A fix is accepted only if the suite's results
are identical before and after it.

## 5. Found while writing: tests no task runs

`mise run check:ontology-catalog` runs a fixed list of test modules. `tools/test_regimes.py` (CCS
C7a) and `tools/test_terms_in_time.py` (CCS C7b) are not on it, so no `mise` task, and therefore no
CI run, executes them. They have so far been run by hand during each slice. Adding them to the task
lengthens it, which makes the work above more pressing. Recorded as TD-19.
