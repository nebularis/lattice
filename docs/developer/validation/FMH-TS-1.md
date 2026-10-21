# FMH-TS-1. Validation Pack: the speed of check:persistence

Status: authored, all runs below were made on a machine shared with other agents (load average 35 to 110), so the times are upper bounds.

## What was slow

`mise run check:persistence` took 4m12s serial (4258 passed, 1 xfailed). A profile of the serial run showed:

| Cause | Share |
|---|---|
| Three sixteen-seed sweeps (`test_membership` t6, `test_tsd_34_builders` t2 and t4) in child processes, each child re-parsing the same update texts | about a third of CPU |
| `witness._observations` (compile and validate every fixture), parsing every constraint query once per focus node, and parsing each fixture twice | 25 to 30 s per process |
| `templatecheck.analyse` parsing the same generated texts for six tests (5901 parses of 1675 distinct texts overall) | about 25 s |
| Nothing ran in parallel | all |
| 2998 warnings | rdflib deprecations inside rdflib (`Dataset.contexts`), not ours. Not changed |

## What changed

| Change | Where |
|---|---|
| `-n auto --dist loadgroup` for the task | `mise.toml` check:persistence |
| Session fixture `sparql_translated_once` (efficient-queries H1) used by an autouse fixture, so every `pyshacl.validate` and every rdflib read parses and translates a text once. Evaluation is unchanged | `tools/conftest.py`, `tools/persistence/tests/conftest.py` |
| Sweeps run their children side by side in a thread pool, and the children translate each read once | `tsd34_support.py`, `test_store_probes.py` |
| `analyse` memoised on (text, parameters), returns a new list | `persistence/templatecheck.py` |
| Fixture documents parsed once per process, copied with their prefix bindings | `persistence/witness.py` |
| Witness module is one xdist group | `test_witness_coverage.py` |

No test was edited in its assertions. Tests whose helpers changed, for countersignature: `test_membership` t6, `test_tsd_34_builders` t2 and t4, `test_store_probes` (P1 and the TSD-34 probe), and all of `test_witness_coverage.py` (module mark only). Passed count is 4346 against 4258 because another agent added tests meanwhile, no parametrisation was merged or split.

## Measured (wall, `-n N --dist loadgroup`, same loaded machine)

| Workers | 2 | 4 | 6 | 8 | auto (task, three runs) |
|---|---|---|---|---|---|
| Wall | 117 s | 90 s | 88 s | 90 s | 99 s, 103 s, 105 s |
| Summed user CPU | 398 s | 446 s | 516 s | 557 s | |

Summed CPU rises with workers, as on the efficiency cores (H5). The task keeps `auto`, which `PYTEST_XDIST_AUTO_NUM_WORKERS` sets. Other tasks: check:persistence-oxigraph 15 s (368 passed), check:persistence-library 1 s, check:persistence-expected-profiles 4 s.

## Not met

The 60 s target was not reached or shown. The floor is the three seed sweeps: about 7 s of CPU per child, 70 percent of it rdflib parsing update texts that differ per history, times 16 seeds. Sharing the parse between children by pickle was tried and abandoned (`ParseResults` did not round-trip). Options for the maintainer: fewer histories per seed, or accept the floor. A quiet machine run is needed to confirm.

## Decisions taken alone

- The session-wide translate-once patch also covers tests that run rdflib directly. It skips only parse and translation, not evaluation.
- No change to `check:persistence-oxigraph`, and no test moved to Oxigraph or to benchmark/, since none was found whose subject allowed it.
- TSD file not edited (another agent has it open).
