#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Records every SHACL validation the ontology test suite makes, and replays them against the
shapes in the working tree, to show whether a change to a shape or to the validator changed what
any validation reports.

Why. A rewrite of a constraint query for speed ought to change nothing about what it accepts
(docs/architecture/efficient-queries-and-shapes.md, rule R7). The tests check the cases their
authors thought of. A recording holds every case the suite builds, several thousand graphs,
each with the full report the shapes gave, so a replay compares the lot.

Run from the repository root, through mise:

    mise run dev:record-validations -- [--out DIR] [--workers N]
    mise run dev:replay-validations -- DIR [--workers N] [--baseline FILE] [--write-baseline FILE]

record  runs the pytest command of `check:ontology-catalog` with this module as a plugin.
        Each call to the suite's validation cache (`tools/conftest.py`, `ValidationCache`) whose
        shapes came from `graph_cache` is written to DIR: the shapes' source files, the data graph
        (N-Triples, once per distinct content), its namespace bindings, the options and the
        report's rows (severity, source shape, focus node, message, value).
replay  parses each recorded data graph, validates it against the shapes' source files as they
        are now, and compares the rows with the recorded ones. Blank nodes are masked, since two
        parses of one document never give equal labels (TSD-29).

To check a change, record at the commit before it and replay at the commit after:

    git switch --detach <before>      && mise run dev:record-validations -- --out /tmp/rec
    mise run dev:replay-validations -- /tmp/rec --write-baseline /tmp/baseline.json
    git switch <after>
    mise run dev:replay-validations -- /tmp/rec --baseline /tmp/baseline.json

The first replay runs the old shapes against their own recording. A case that differs there does
not reproduce even without the change, for example because a result depends on the order the
engine produced it in. Its identity goes in the baseline file, and the second replay does not
count it. The exit status is 1 when a case outside the baseline differs.

A validation is not recorded when its shapes did not come from `graph_cache`. A data graph that
N-Triples cannot be read back from (a literal in subject position, which two graphs in the suite
have) is recorded, and the replay counts it as unreadable and compares nothing for it. Tests that
call `pyshacl.validate` directly are not seen. An option that is a graph, such as a mix-in ontology
(`ont_graph`), is recorded as text and not given back at replay, so a validation that needs one
may differ in both runs. The baseline absorbs it (four eligibility validations, on 2026-10-17).
"""

from __future__ import annotations

import argparse
import atexit
import gzip
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SH = "http://www.w3.org/ns/shacl#"
TASK = "check:ontology-catalog"
RECORD_DIR_VARIABLE = "LATTICE_RECORD_VALIDATIONS"
MASK = re.compile(r"_:\w+|\bN[0-9a-f]{32}\b")


def result_rows(report) -> list[list[str]]:
    """The rows of a validation report graph, sorted: severity, source shape, focus node, message, value."""
    from rdflib import URIRef
    from rdflib.namespace import RDF

    def text(result, name):
        value = report.value(result, URIRef(SH + name))
        return "" if value is None else value.n3()

    return sorted(
        [text(r, "resultSeverity"), text(r, "sourceShape"), text(r, "focusNode"), text(r, "resultMessage"), text(r, "value")]
        for r in report.subjects(RDF.type, URIRef(SH + "ValidationResult"))
    )


def masked(rows: Iterable[list[str]]) -> list[list[str]]:
    """`rows` with every blank node label replaced by one placeholder, sorted."""
    return sorted([MASK.sub("_:b", cell) for cell in row] for row in rows)


def describe_sources(sources: Iterable[Any]) -> list[dict[str, str]]:
    """A shapes graph's sources as `graph_cache` was given them: a path under the repository,
    kept relative so a recording replays in another checkout, or inline Turtle."""
    described = []
    for source in sources:
        if isinstance(source, Path):
            resolved = source.resolve()
            try:
                described.append({"path": resolved.relative_to(ROOT).as_posix()})
            except ValueError:
                described.append({"path": str(resolved)})
        else:
            described.append({"turtle": str(source)})
    return described


def call_identity(call: dict) -> str:
    """A stable name for a recorded call: its shapes, data, options and namespaces."""
    key = json.dumps([call["shapes"], call["data"], call["options"], call.get("namespaces")], sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()


class Recorder:
    """Writes `calls-<pid>.jsonl` and `data/<sha1>.nt.gz` under `directory`."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        (self.directory / "data").mkdir(parents=True, exist_ok=True)
        self._calls = open(self.directory / f"calls-{os.getpid()}.jsonl", "a")
        self.not_recorded = 0
        atexit.register(self._write_counts)

    def _write_counts(self) -> None:
        (self.directory / f"not-recorded-{os.getpid()}.count").write_text(str(self.not_recorded))

    def record(self, sources, data_nt: str, namespaces: dict[str, str], options: dict[str, Any], conforms: bool, rows) -> None:
        digest = hashlib.sha1(data_nt.encode()).hexdigest()
        path = self.directory / "data" / f"{digest}.nt.gz"
        if not path.exists():
            with gzip.open(path, "wt") as handle:
                handle.write(data_nt)
        self._calls.write(json.dumps({
            "shapes": describe_sources(sources), "data": digest, "namespaces": namespaces,
            "options": {k: str(v) for k, v in options.items()}, "conforms": bool(conforms), "results": rows,
        }) + "\n")
        self._calls.flush()


def install(conftest, recorder: Recorder) -> None:
    """Wraps `conftest.ValidationCache.__call__` so that each validation is recorded.
    Recording never changes a test's outcome: a failure to record is counted and reported."""
    original = conftest.ValidationCache.__call__

    def sources_of(graph):
        return next((key for key, cached in conftest._GRAPH_CACHE._by_key.items() if cached is graph), None)

    def recording(self, data_graph, *args, shacl_graph, **options):
        sources = sources_of(shacl_graph)
        data_nt = namespaces = None
        if sources is not None:
            try:
                data_nt = data_graph.serialize(format="nt")   # before validating, which may add to the graph
                namespaces = {prefix: str(namespace) for prefix, namespace in data_graph.namespaces()}
            except Exception:
                recorder.not_recorded += 1
        result = original(self, data_graph, *args, shacl_graph=shacl_graph, **options)
        if data_nt is not None:
            try:
                recorder.record(sources, data_nt, namespaces, options, result[0], result_rows(result[1]))
            except Exception as error:
                recorder.not_recorded += 1
                sys.stderr.write(f"validation_replay: not recorded: {error!r}\n")
        return result

    conftest.ValidationCache.__call__ = recording


def pytest_collection_finish(session) -> None:
    """The pytest hook that starts recording, when $LATTICE_RECORD_VALIDATIONS names a directory."""
    directory = os.environ.get(RECORD_DIR_VARIABLE)
    if directory and "conftest" in sys.modules and not getattr(sys.modules["conftest"], "_RECORDING", False):
        sys.modules["conftest"]._RECORDING = True
        install(sys.modules["conftest"], Recorder(Path(directory)))


def load_calls(directory: Path) -> list[dict]:
    """Every distinct recorded call, in file order."""
    seen, calls = set(), []
    for path in sorted(Path(directory).glob("calls-*.jsonl")):
        for line in path.read_text().splitlines():
            call = json.loads(line)
            identity = call_identity(call)
            if identity not in seen:
                seen.add(identity)
                calls.append(call)
    return calls


_shapes_by_sources: dict[str, Any] = {}


def shapes_for(sources: list[dict[str, str]], root: Path):
    """The shapes graph for `sources`, read from the files as they are now, once per process."""
    from rdflib import Graph

    key = json.dumps(sources, sort_keys=True)
    if key not in _shapes_by_sources:
        graph = Graph()
        for source in sources:
            if "path" in source:
                path = Path(source["path"])
                graph.parse(path if path.is_absolute() else root / path)
            else:
                graph.parse(data=source["turtle"], format="turtle")
        _shapes_by_sources[key] = graph
    return _shapes_by_sources[key]


def replay_call(call: dict, directory: Path, root: Path = ROOT) -> tuple[bool | None, list[list[str]], float]:
    """Validates a recorded call's data against the shapes now. Returns (conforms, masked rows, seconds),
    or conforms None when the recorded data graph cannot be read back."""
    from rdflib import Graph
    from pyshacl import validate

    data = Graph()
    try:
        with gzip.open(Path(directory) / "data" / f"{call['data']}.nt.gz", "rt") as handle:
            data.parse(data=handle.read(), format="nt")
    except Exception:
        return None, [], 0.0
    for prefix, namespace in (call.get("namespaces") or {}).items():
        data.bind(prefix, namespace, override=True)
    options = call["options"]
    keywords = {
        "advanced": options.get("advanced") == "True",
        "inference": options.get("inference", "none"),
        "allow_warnings": options.get("allow_warnings") == "True",
    }
    shapes = shapes_for(call["shapes"], root)
    started = time.perf_counter()
    try:
        from conftest import _sparql_translated_once
        with _sparql_translated_once():
            conforms, report, _ = validate(data, shacl_graph=shapes, **keywords)
    except ImportError:
        conforms, report, _ = validate(data, shacl_graph=shapes, **keywords)
    return bool(conforms), masked(result_rows(report)), time.perf_counter() - started


def differs(call: dict, conforms: bool | None, rows: list[list[str]]) -> bool:
    return conforms != call["conforms"] or rows != masked(call["results"])


def _replay_task(arguments):
    call, directory = arguments
    conforms, rows, seconds = replay_call(call, Path(directory))
    return call, conforms, rows, seconds


def replay(directory: Path, workers: int, baseline: set[str] | None = None, out=print) -> dict:
    """Replays every call in `directory`. Returns counts and the identities of the calls that differ."""
    calls = load_calls(directory)
    out(f"replaying {len(calls)} distinct validations on {workers} workers")
    started = time.perf_counter()
    summary = {"calls": len(calls), "unreadable": 0, "differing": [], "known": 0, "seconds": 0.0}
    with Pool(workers) as pool:
        for call, conforms, rows, seconds in pool.imap_unordered(_replay_task, [(c, str(directory)) for c in calls], chunksize=4):
            summary["seconds"] += seconds
            if conforms is None:
                summary["unreadable"] += 1
            elif differs(call, conforms, rows):
                identity = call_identity(call)
                if baseline is not None and identity in baseline:
                    summary["known"] += 1
                    continue
                summary["differing"].append(identity)
                out(describe_difference(call, conforms, rows))
    summary["wall"] = time.perf_counter() - started
    return summary


def describe_difference(call: dict, conforms: bool, rows: list[list[str]]) -> str:
    shapes = [s.get("path", "inline Turtle").rsplit("/", 1)[-1] for s in call["shapes"]]
    recorded = masked(call["results"])
    lines = [f"DIFFERENT: shapes={shapes} data={call['data'][:10]} conforms recorded {call['conforms']}, now {conforms}"]
    lines += [f"   only recorded: {r[1][-40:]} {r[2][-30:]} {r[3][:80]}" for r in recorded if r not in rows][:2]
    lines += [f"   only now:      {r[1][-40:]} {r[2][-30:]} {r[3][:80]}" for r in rows if r not in recorded][:2]
    return "\n".join(lines)


def record_command(workers: str | None) -> list[str]:
    """The pytest command of `check:ontology-catalog`, with this module loaded as a plugin."""
    run = tomllib.loads((ROOT / "mise.toml").read_text())["tasks"][TASK]["run"]
    tokens = shlex.split(run.split("&&")[0].strip())
    flags = tokens[3:]                                          # after `python -m pytest`
    if workers:
        kept, skip = [], False
        for flag in flags:
            if skip:
                skip = False
            elif flag == "-n":
                skip = True
            else:
                kept.append(flag)
        flags = [*kept, "-n", workers]
    return [sys.executable, "-m", "pytest", "-p", "validation_replay", "-p", "no:cacheprovider", *flags]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record", help="run the suite and record every validation")
    record.add_argument("--out", type=Path, help="the directory to write (default: a new temporary directory)")
    record.add_argument("--workers", help="xdist workers, replacing the task's -n")
    replaying = commands.add_parser("replay", help="validate the recorded graphs against the shapes now and compare")
    replaying.add_argument("directory", type=Path)
    replaying.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    replaying.add_argument("--baseline", type=Path, help="a file from --write-baseline whose cases are not counted")
    replaying.add_argument("--write-baseline", type=Path, help="write the cases that differ to this file, and exit 0")
    args = parser.parse_args(argv)

    if args.command == "record":
        directory = args.out or Path(tempfile.mkdtemp(prefix="lattice-validations-"))
        directory.mkdir(parents=True, exist_ok=True)
        environment = {**os.environ, RECORD_DIR_VARIABLE: str(directory), "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT / "tools"), os.environ.get("PYTHONPATH")]))}
        started = time.perf_counter()
        status = subprocess.run(record_command(args.workers), cwd=ROOT, env=environment).returncode
        calls = load_calls(directory)
        skipped = sum(int(path.read_text() or 0) for path in directory.glob("not-recorded-*.count"))
        print(f"recorded {len(calls)} distinct validations in {directory}, {skipped} not recorded ({time.perf_counter() - started:.0f}s, pytest exit {status})")
        return status

    baseline = set(json.loads(args.baseline.read_text())) if args.baseline else None
    summary = replay(args.directory, args.workers, baseline)
    print(f"done: {len(summary['differing'])} differences, {summary['known']} in the baseline, "
          f"{summary['unreadable']} graphs could not be read back, validation time summed {summary['seconds']:.0f}s, wall {summary['wall']:.0f}s")
    if args.write_baseline:
        args.write_baseline.write_text(json.dumps(sorted(summary["differing"])))
        print(f"wrote {len(summary['differing'])} cases to {args.write_baseline}")
        return 0
    return 1 if summary["differing"] else 0


if __name__ == "__main__":
    sys.exit(main())
