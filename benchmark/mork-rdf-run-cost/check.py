# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a MORK run costs in memory and time as its source grows (ADR-A124, the run planner's MP-Q1).

Each size runs in a process of its own, so its peak resident memory is its own, with the catalogue fixture's mapping
of `tools/mork_rdf` over synthetic book records, once kept in memory and once streamed to a sink.

**Pass criterion.** Each record gives nine instance triples, so a run of N records writes 9N distinct triples, kept or
streamed, and finds nothing to report. A wrong count fails the run. **Time and memory never do.** The figures go to
`report.md` and `report.json` here, which are generated and git-ignored.

Run `mise run check:mork-rdf-run-cost`. The sizes are 10,000 and 100,000 records. `MORK_RUN_COST_QUICK=1` runs 2,000
alone, and `MORK_RUN_COST_LARGE=1` adds 1,000,000, which needs about 15 GB and is meant for a machine that has it."""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIPLES_PER_RECORD = 9
RECORD = """ex:b{i} a src:Book ; src:isbn "978-{i}" ; src:title "Title {i}" ; src:format src:Paperback ; src:genre "SF" ;
 src:published "1965"^^xsd:gYear ; src:subtitle "A novel" ; src:shelfmark "823 X{i}" ; src:author [ src:name "Author {a}" ] .
"""
HEAD = "@prefix src: <http://example.org/src#> . @prefix ex: <http://example.org/records/> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"


def sizes() -> list[int]:
    if os.environ.get("MORK_RUN_COST_QUICK"):
        return [2000]
    return [10_000, 100_000] + ([1_000_000] if os.environ.get("MORK_RUN_COST_LARGE") else [])


def source_text(n: int) -> str:
    return HEAD + "".join(RECORD.format(i=i, a=i % 997) for i in range(n))


class TimingSink:
    """Counts the distinct triples it is given, and the seconds between writes, by stratum."""

    def __init__(self) -> None:
        self.seen: set = set()
        self.seconds: dict = {}
        self._last = time.perf_counter()

    def write(self, query, triples) -> None:
        self.seen.update(hash(str(t)) for t in triples if query.box == "abox")  # hashes, so the count costs little memory
        now = time.perf_counter()
        self.seconds[query.stratum] = self.seconds.get(query.stratum, 0.0) + now - self._last
        self._last = now

    def close(self) -> None:
        pass


def measure(n: int, streamed: bool) -> dict:
    """One run, in this process. Called by `main` in a child process per size and mode."""
    import lattice_repo_catalogue as reader
    from rdflib import Graph
    from mork_rdf import compile_scheme, run

    import tempfile

    fixtures = reader.load().root / "tools/mork_rdf/tests/fixtures"
    # The source is a Turtle file Oxigraph parses itself, as a deployment would hand it over, never an rdflib graph.
    directory = tempfile.TemporaryDirectory()
    source = Path(directory.name) / "source.ttl"
    source.write_text(source_text(n), encoding="utf-8")
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    compiled = compile_scheme(Graph().parse(fixtures / "catalogue-mapping.ttl"), "http://example.org/mapping#Catalogue",
                              base="http://example.org/out/", at=datetime(2026, 10, 29, tzinfo=timezone.utc),
                              target_vocabulary=Graph().parse(fixtures / "catalogue-vocabulary.ttl"))
    sink = TimingSink() if streamed else None
    start = time.perf_counter()
    result = run(compiled, source, fixtures / "catalogue-reference.ttl", sink=sink)
    directory.cleanup()
    seconds = time.perf_counter() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    scale = 1 if sys.platform == "darwin" else 1024  # ru_maxrss is bytes on macOS and kilobytes on Linux
    return {"records": n, "mode": "streamed" if streamed else "in memory", "source_triples": 10 * n,
            "written": len(sink.seen) if streamed else len(result.graph), "findings": len(result.findings),
            "before_mb": round(before * scale / 1e6), "peak_mb": round(peak * scale / 1e6), "run_s": round(seconds, 2),
            "strata_s": {str(k): round(v, 2) for k, v in sorted((sink.seconds if streamed else {}).items())}}


def verify(m: dict) -> list[str]:
    errors = []
    if m["written"] != TRIPLES_PER_RECORD * m["records"]:
        errors.append(f"{m['records']} records {m['mode']} wrote {m['written']} triples, not {TRIPLES_PER_RECORD * m['records']}")
    if m["findings"]:
        errors.append(f"{m['records']} records {m['mode']} reported {m['findings']} findings, not none")
    return errors


def main() -> int:
    if len(sys.argv) == 3:  # a child: one size, one mode
        print(json.dumps(measure(int(sys.argv[1]), sys.argv[2] == "streamed")))
        return 0
    results = []
    for n in sizes():
        for mode in ("memory", "streamed"):
            child = subprocess.run([sys.executable, __file__, str(n), mode], capture_output=True, text=True, check=True)
            results.append(json.loads(child.stdout.strip().splitlines()[-1]))
            print(results[-1])
    errors = [e for m in results for e in verify(m)]
    stamp = f"Run of {datetime.now(timezone.utc).date().isoformat()}, Python {sys.version.split()[0]}, {sys.platform}"
    (HERE / "report.json").write_text(json.dumps({"run": stamp, "results": results}, indent=2), encoding="utf-8")
    lines = [stamp, "", "| Records | Mode | Source triples | Written | Before the run MB | Peak MB | Run s |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {m['records']:,} | {m['mode']} | {m['source_triples']:,} | {m['written']:,} | {m['before_mb']:,} | {m['peak_mb']:,} | {m['run_s']} |" for m in results]
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written to {HERE / 'report.md'}")
    for e in errors:
        print("FAIL", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
