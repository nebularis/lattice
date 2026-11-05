## Parse once, copy, never share a mutable graph

- **Parse once, copy, never share a mutable graph.** Session-scoped fixtures parse a document once per process, and a test that
  changes a graph changes a copy. `_sparql_translated_once` (H1) parses and translates each query text once. A pure function that
  parses SPARQL is memoised on its input and returns a fresh value.

## The parse and validation cache

Two session-scoped fixtures, available to every test under `tools/`:

```python
@pytest.fixture(scope="module", autouse=True)
def _cached_graphs(request: pytest.FixtureRequest, graph_cache, validated) -> None:
    module = request.module
    module.MODEL = graph_cache(*[ONTOLOGY / p for p in LOWER], SPEC, VOCAB)
    module.SHAPES = graph_cache(LAYER / "shapes" / "structural.ttl", LAYER / "shapes" / "constraints.ttl")
    module.validate = validated
```

## Pitfalls found by building this, not predicted in advance

- **A cache must still catch a real test mutating shared state.** `tools/conftest.py`'s
  `_graph_cache_not_mutated` fixture runs once, at session end, and asserts no cached graph's triple
  count drifted from what it was when built (aside from the one pySHACL exception above). Probe it
  for real before trusting it: add a throwaway test that does `graph_cache(...).add((s, p, o))` and
  confirm the session fails at teardown, then delete the probe.

## Writing a new SHACL-validating test

1. Does an existing module already parse the same layer stack or shape files? If so, reuse
   `graph_cache` rather than a fresh `Graph().parse(...)` — check `tools/conftest.py`'s own tests
   (`test_graph_cache.py`) for the exact call pattern.

3. Call `validate(...)` exactly as `pyshacl.validate` is documented (`shacl_graph=`, not a bare
   positional second argument) if the module has substituted `validated` in for it — this is what
   makes the substitution a true drop-in.
4. If the test will shell out for a repository-wide check, use `repo_files` instead, not a fresh
   `subprocess.run(["git", "grep", ...])` call.
