Most of the time is probably pySHACL validation being repeated, not the tests themselves. This comes from reading the code and your durations only. I haven't profiled or changed anything, so treat the ranking as a hypothesis to confirm.

## What the durations show

The slowest tests are almost all calls to `validate(MODEL + data, shacl_graph=..., advanced=True)`. That call is repeated in 16 modules (27 call sites). `test_c8_02_every_instrument_example_conforms` takes 31s because it runs this once for each of 22 example files against `EVERY_SHAPE`. That is all eight layers' shapes, which include dozens of SHACL-SPARQL constraints (40 in Instrument alone). That works out to about 1.4s per validation, so the whole suite is mostly a count of validation calls times that cost.

## Likely causes, most likely first

1. **The same graph is validated against the same shapes many times.** `framework-lots` against `EVERY_SHAPE` is validated by at least these tests:
   - `test_c7c_01` and `test_c7c_02`
   - `test_c8_02` and `test_c8_10`
   - `test_c6_02`, `test_c7a_02` and `test_terms_in_time`
   - `test_c7c_13`, which validates the unmodified example again as its baseline

   The three examples are validated twice in `test_constitutive_terms.py`, once to check for violations and once to collect warnings. `_results()` throws the report away after filtering by one severity. A shared cache keyed on the example, the shape set and the severity would collapse most of these. It should also keep the whole report so both severities come from one run.

2. **Each module rebuilds the same models at import.** `test_parameter_bindings.py`, `test_constitutive_terms.py`, `test_instrument.py`, `test_regimes.py` and others each declare their own `LOWER` and `MODEL`, `SHAPES` and `EVERY_SHAPE`. Each parses about 13 Turtle files and 16 shape files at import. Running everything in one pytest process doesn't share this, because each module builds its own copy. `test_wording.py` is worse. `_vocab_closure()` rebuilds the catalog closure on every call and has no cache. A single shared support module with cached graphs would fix both.

3. **One-triple mutation tests validate everything.** Tests such as `test_c8_08`, `test_c8_09` and `test_c7c_09` change one triple, then run the whole Instrument shape set to see one message. Each takes 2–5s. Passing only the shape under test would cut that, but it needs care to keep SPARQL constraints working with the right prefixes.

4. **Graph copies.** `MODEL + data` builds a fresh copy of tens of thousands of triples. pySHACL then clones the data graph again, because `inplace` defaults to false. Passing `inplace=True` would skip the second copy, since the first is already fresh.

5. **SPARQL constraint evaluation in rdflib.** I expect this to be the cost inside each validation, especially in constraints using `skos:broader+` and `FILTER NOT EXISTS`. I can't tell which shapes dominate without profiling.

6. **The HermiT tests** (5.1s and 2.7s) each start a JVM. Cloud runners likely do this too if the reasoning testkit jar is built, so check the skip condition there.

## How to confirm before changing anything

```bash
python -m cProfile -o /tmp/p.out -m pytest tools/test_parameter_bindings.py::test_c8_02_every_instrument_example_conforms -q -p no:cacheprovider
python -c "import pstats; pstats.Stats('/tmp/p.out').sort_stats('cumtime').print_stats(25)"
```

If most cumulative time is under rdflib's SPARQL evaluation, check the shape constraints (item 5). If it is under the graph merge and clone, check items 3 and 4. A parse-heavy profile points at item 2.

## Cloud versus your Mac

A `pytest-xdist` run (`-n auto --dist loadfile`) is the cheapest experiment, since the files are independent. It only helps if the cloud runner has several vCPUs, and each worker repeats the import-time parsing from item 2. Check the vCPU count before expecting a gain.

TD-18 and `docs/developer/sketches/test-suite-performance.md` already name several of these as unmeasured suspects, so a profile run would settle that open item. I can write the shared cache and support module on the fresh branch if you want.