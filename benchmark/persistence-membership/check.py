# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What it costs to keep the members of a set of 500 across 1, 10 and 100 versions, on rdflib and Oxigraph (ADR-A124, formal-methods H2.6f).

Three strategies hold the same history, a set of 500 members where each version replaces one member.

* **full**, `dal:AppendVersions` with `dal:FullMembership`. Each version lists all 500 members.
* **delta**, `dal:DeltaMembership` with a checkpoint every 16 versions. Each version states one add and one drop, and a read follows the
  chain back to the nearest checkpoint with the generated `members` query.
* **in-place**, a composite replace under `dal:PatchLog`. The aggregate holds the current 500 members, and each write logs the one triple added
  and the one removed in its delta graphs.

**Pass criterion.** After the N-th version, on each engine, the members read are exactly the model's, and the stored triples have the count the
strategy's arithmetic gives (`expected_stored`). A wrong member set or count fails the check. **Time never fails it.** The seconds of the last
write, of all N writes, and of one read of the current members go to `report.json` and `report.md` here, which are generated and git-ignored.

Run `mise run check:persistence-membership`. `MEMBERSHIP_COST_MAX` caps the versions (default 100). The guards are off, as in the composite replace benchmark."""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = HERE.parents[1] / "tools" / "persistence" / "tests"
sys.path.insert(0, str(TESTS))

from rdflib import RDF, Literal, URIRef  # noqa: E402
from rdflib.namespace import XSD  # noqa: E402

import engines  # noqa: E402
import membership_fixtures as mf  # noqa: E402
from persistence.builders import build  # noqa: E402
from persistence.members import is_checkpoint  # noqa: E402

VERSIONS = (1, 10, 100)
SIZE = 500
EVERY = 16
STRATEGIES = ("full", "delta", "in-place")
PAT = mf.PAT
LONG = lambda n: Literal(n, datatype=XSD.long)
ROOT = URIRef("urn:project:1")
PROJECTS = "https://example.org/projects#"
MILESTONE = URIRef(PROJECTS + "hasMilestone")
PROJECT_DATA = URIRef("urn:g:projects")


class WrongResult(AssertionError):
    """A member set or a stored count that is not what the history gives. The one way the check fails."""


@dataclass
class Measurement:
    engine: str
    strategy: str
    versions: int
    stored_triples: int
    last_write_seconds: float
    total_write_seconds: float
    read_seconds: float


@dataclass
class Report:
    measurements: list[Measurement] = field(default_factory=list)


def _nt(triples) -> str:
    return mf._nt(triples)


def history(n: int) -> list[set]:
    """The members of each version 1 to n: member 0 goes at version 2, member 1 at version 3, and a new one comes in each time."""
    state = {mf.member(i) for i in range(SIZE)}
    out = [set(state)]
    for k in range(2, n + 1):
        state = (state - {mf.member(k - 2)}) | {mf.member(SIZE + k - 2)}
        out.append(set(state))
    return out


def expected_stored(strategy: str, n: int) -> tuple[int, int]:
    """(triples in the data graph, triples in the delta graphs) after n versions, by the strategy's arithmetic."""
    if strategy == "full":
        return n * (3 + SIZE) - 1 + 1, 0  # each version: type, revision, previous (not the first), 500 members. The first adds its marker.
    if strategy == "delta":
        total = 0
        for v in range(1, n + 1):
            total += (2 + SIZE + 1) if v == 1 else (3 + SIZE + 1) if is_checkpoint(v, EVERY) else 5
        return total, 0
    return SIZE, 2 * (n - 1)


def _in_place_operation() -> str:
    from persistence import witness
    from persistence.compiler import compile_to_graph
    from persistence.instantiate import instantiate_by_target

    compiled, _ = compile_to_graph(witness._load_fixture(Path(witness.EXAMPLES_DIR) / "composite-project-ownership.ttl"))
    (by_target,) = instantiate_by_target(compiled, guards=False).values()
    text = by_target["cas-replace"]
    return text, re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1)


def _timed(f):
    start = time.perf_counter()
    result = f()
    return result, time.perf_counter() - start


def _rows(result) -> set:
    return {row[0] for row in result}


def run_strategy(strategy: str, n: int) -> tuple[Measurement, int, int]:
    """Writes n versions on the current engine and reads the last. Returns the measurement (engine unset) and the stored counts."""
    model = history(n)
    writes: list[float] = []
    if strategy in ("full", "delta"):
        ds = mf.new_store()
        ds = _on_engine(ds)
        data_graph = mf.DATA
        for v in range(1, n + 1):
            header = [(mf.version(v), RDF.type, URIRef(mf.EX + "MemberSet"))]
            if strategy == "full" or is_checkpoint(v, EVERY):
                payload = header + [(mf.version(v), mf.MEMBER, m) for m in sorted(model[v - 1], key=str)]
                if strategy == "delta":
                    payload.append((mf.version(v), URIRef(PAT + "checkpoint"), Literal(True)))
                if strategy == "full" and v == 1:
                    payload.append((mf.version(v), URIRef(PAT + "checkpoint"), Literal(True)))
                added = dropped = ()
            else:
                payload = header
                added = [(mf.version(v), URIRef(PAT + "addsMember"), m) for m in sorted(model[v - 1] - model[v - 2], key=str)]
                dropped = [(mf.version(v), URIRef(PAT + "dropsMember"), m) for m in sorted(model[v - 2] - model[v - 1], key=str)]
            _, seconds = _timed(lambda: _append(ds, v, strategy, payload, added, dropped))
            writes.append(seconds)
        if strategy == "full":
            text = f"SELECT ?m WHERE {{ GRAPH <{mf.DATA}> {{ <{mf.version(n)}> <{mf.MEMBER}> ?m }} }}"
            rows, read = _timed(lambda: _rows(ds.query(text)))
        else:
            text = _members_text()
            rows, read = _timed(lambda: _rows(ds.query(text, initBindings={"version": mf.version(n), "membershipProperty": mf.MEMBER})))
        data = sum(1 for s, p, o in ds.graph(data_graph) if p != URIRef(PAT + "recordedAt"))
        patch = 0
    else:
        text, meta = _in_place_operation()
        ds = _on_engine(mf.new_store())
        meta_graph = ds.graph(URIRef(meta))
        meta_graph.add((ROOT, URIRef(PAT + "epoch"), LONG(1)))
        meta_graph.add((ROOT, URIRef(PAT + "seq"), LONG(1)))
        for m in model[0]:
            ds.graph(PROJECT_DATA).add((ROOT, MILESTONE, m))
        for v in range(2, n + 1):
            payload = [(ROOT, MILESTONE, m) for m in sorted(model[v - 1], key=str)]
            add = [(ROOT, MILESTONE, m) for m in model[v - 1] - model[v - 2]]
            delete = [(ROOT, MILESTONE, m) for m in model[v - 2] - model[v - 1]]
            filled = text.replace("{{{payloadTriples}}}", _nt(payload)).replace("{{{assertTriples}}}", _nt(add)).replace("{{{retractTriples}}}", _nt(delete))
            _, seconds = _timed(lambda: ds.update(filled, initBindings={
                "root": ROOT, "epoch": LONG(1), "expectedSeq": LONG(v - 1), "nextSeq": LONG(v), "newRev": URIRef(f"urn:rev:project/{v}"),
                "txnId": URIRef(f"urn:txn:{v}"), "requestDigest": Literal("ab" * 32),
            }))
            writes.append(seconds)
        read_text = f"SELECT ?m WHERE {{ GRAPH <{PROJECT_DATA}> {{ <{ROOT}> <{MILESTONE}> ?m }} }}"
        rows, read = _timed(lambda: _rows(ds.query(read_text)))
        data = sum(1 for _ in ds.graph(PROJECT_DATA))
        patch = sum(1 for g in ds.graphs() if str(g.identifier).startswith("urn:rev:") for _ in g)
    if rows != model[n - 1]:
        raise WrongResult(f"{engines.CURRENT} {strategy} {n}: read {len(rows)} members, {len(rows ^ model[n - 1])} differ from the model")
    if (data, patch) != expected_stored(strategy, n):
        raise WrongResult(f"{engines.CURRENT} {strategy} {n}: stored (data, patch) {(data, patch)}, expected {expected_stored(strategy, n)}")
    last = writes[-1] if writes else 0.0
    return Measurement("", strategy, n, data + patch, last, sum(writes), read), data, patch


def _on_engine(seed):
    """The seeded rdflib dataset, moved to the current engine."""
    if engines.CURRENT == "rdflib":
        return seed
    ds = engines.dataset()
    for s, p, o, g in seed.quads((None, None, None, None)):
        ds.graph(g.identifier if hasattr(g, "identifier") else g).add((s, p, o))
    return ds


def _append(ds, v, strategy, payload, added, dropped):
    stem = "append-version-delta" if strategy == "delta" else "append-version"
    text = engines_render(stem)
    text = text.replace("{{{payloadTriples}}}", _nt(payload))
    if strategy == "delta":
        text = text.replace("{{{addedMembers}}}", _nt(added)).replace("{{{droppedMembers}}}", _nt(dropped))
    ds.update(text, initBindings={
        "root": mf.ROOT, "epoch": LONG(1), "expectedSeq": LONG(v - 1), "nextSeq": LONG(v), "newRev": URIRef(f"urn:rev:set/{v}"),
        "txnId": URIRef(f"urn:txn:{v}"), "requestDigest": Literal("ab" * 32), "newVersion": mf.version(v),
    })


def engines_render(stem: str) -> str:
    from persistence.ir_render import render

    return render(build(stem, mf.CONTEXT, guards=False))


def _members_text() -> str:
    from persistence.ir_render import render

    return render(build("members", {"dataGraph": mf.CONTEXT["dataGraph"]}, guards=False))


def available_engines() -> list[str]:
    try:
        import lattice_testing_oxigraph  # noqa: F401
    except ImportError:
        return ["rdflib"]
    return ["rdflib", "oxigraph"]


def run(max_versions: int = VERSIONS[-1], engine_names=None) -> Report:
    report = Report()
    for name in engine_names or available_engines():
        engines.CURRENT = name
        for strategy in STRATEGIES:
            for n in VERSIONS:
                if n > max_versions:
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    m, _, _ = run_strategy(strategy, n)
                m.engine = name
                report.measurements.append(m)
                print(f"{name:9} {strategy:9} versions {n:4}  stored {m.stored_triples:7}  last write {m.last_write_seconds:8.4f} s  "
                      f"all writes {m.total_write_seconds:9.3f} s  read {m.read_seconds:8.4f} s", flush=True)
    engines.CURRENT = "rdflib"
    return report


def environment() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    versions = {}
    for package in ("rdflib", "pyoxigraph"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}", **versions}


def write_report(report: Report, directory: Path = HERE) -> None:
    data = {"environment": environment(), "measurements": [m.__dict__ for m in report.measurements]}
    (directory / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# Membership cost (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "",
             "| engine | strategy | versions | stored triples | last write s | all writes s | read s |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {m.engine} | {m.strategy} | {m.versions} | {m.stored_triples} | {m.last_write_seconds:.4f} | {m.total_write_seconds:.3f} | {m.read_seconds:.4f} |" for m in report.measurements]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        report = run(int(os.environ.get("MEMBERSHIP_COST_MAX", VERSIONS[-1])))
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(report)
    print(f"report written to {HERE / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
