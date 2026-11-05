# SPDX-License-Identifier: MPL-2.0
"""LATTICE's extractor for Вивід: the architectural quanta of the data and software views, and the catalogue's units, so
an Owner cell of a register names a module (ADR-A152 decision 1, ADR-A134 addendum of 2026-10-25).

`vyd build` runs it as the command the `[[project.extractors]]` entry of vyvid.toml declares, in the checkout's root, with
one JSON request on standard input, and reads `quads.nq` and `result.json` from the output folder the request names. The
rules of a quantum are in quanta.py. The catalogue is read by its own reader (ADR-A121), never from a path written here."""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import pyoxigraph as ox
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lattice_repo_catalogue  # noqa: E402
import quanta  # noqa: E402

VERSION = "1"
RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
RDFS_LABEL = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
OWL = "http://www.w3.org/2002/07/owl#"
VIEW = {"data": "DataView", "software": "SoftwareView"}
KI = "https://www.nebularis.org/vyvid/knowledge#"


def normalise(identifier: str) -> str:
    """Вивід's key for an identifier: letters, digits and dots, upper case, so `read data/substrate` finds the node."""
    return re.sub(r"[^A-Z0-9.]", "", identifier.upper())


def units(catalogue) -> dict[str, list[str]]:
    """The units an Owner value may name, each to the units it stands for: a module by name, a tool package by name
    or path, a root or documentation area by path, and a module kind for every module of that kind."""
    out: dict[str, list[str]] = {}
    for tool in catalogue.tools:
        out[tool.name] = out[tool.path] = [tool.path]
    for area in catalogue.roots + catalogue.docs:
        out[area.path.rstrip("/")] = [area.path.rstrip("/")]
    for kind in {m.kind for m in catalogue.modules.values()}:
        out[kind] = [m.name for m in catalogue.modules_of_kind(kind)]
    for name in catalogue.modules:
        out[name] = [name]
    return out


def imports_between(root: Path, files: list[Path], module_of) -> tuple[set[tuple[str, str]], list[str]]:
    """The imports between modules, read from every ontology document's owl:imports, and the documents that do not parse."""
    declared: dict[str, str] = {}
    imports: list[tuple[str, str]] = []
    problems: list[str] = []
    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        try:
            triples = list(ox.parse(path=str(path), format=ox.RdfFormat.TURTLE))
        except (OSError, SyntaxError, ValueError) as error:
            problems.append(f"{rel} does not parse ({error.__class__.__name__}), so its imports are not read")
            continue
        for t in triples:
            if t.predicate == RDF_TYPE and t.object == ox.NamedNode(OWL + "Ontology"):
                declared[t.subject.value] = rel
            elif t.predicate == ox.NamedNode(OWL + "versionIRI"):
                declared[t.object.value] = rel
            elif t.predicate == ox.NamedNode(OWL + "imports"):
                imports.append((rel, t.object.value))
    edges = set()
    for rel, target in imports:
        importer, imported = module_of(rel), module_of(declared.get(target, ""))
        if importer and imported and importer != imported:
            edges.add((importer, imported))
    return edges, problems


def whole(root: Path, rel: str) -> str:
    """A pointer at a whole file, as `path:1-n`."""
    try:
        lines = (root / rel).read_text(encoding="utf-8").count("\n")
    except OSError:
        lines = 1
    return f"{rel}:1-{max(lines, 1)}"


def extract(request: dict) -> tuple[list[ox.Quad], dict]:
    root = Path(request["root"]).resolve()
    scope = request["scope"]
    graph = ox.NamedNode(request["graphs"]["index"])
    files = sorted({Path(p) for pattern in request["paths"] for p in glob.glob(pattern, recursive=True)})
    catalogue = lattice_repo_catalogue.load(root)
    modules = {m.name: m for m in catalogue.modules.values()}
    paths = sorted(((Path(m.path).resolve().relative_to(root).as_posix(), m.name) for m in modules.values()),
                   key=lambda pair: -len(pair[0]))

    def module_of(rel: str) -> str | None:
        return next((name for path, name in paths if rel == path or rel.startswith(path + "/")), None)

    imports, problems = imports_between(root, [f for f in files if f.suffix == ".ttl"], module_of)
    readme = {name: f"{path}/README.md" for path, name in paths if (root / path / "README.md").exists()}
    found, straddling = quanta.data_quanta({n: m.kind for n, m in modules.items()}, imports,
                                           {m.name for m in catalogue.release_members()}, readme)
    findings = [f"{name} shares the substrate's release number although nothing in the substrate imports it, so the "
                f"release policy places it across a quantum boundary" for name in straddling]
    for path in (f for f in files if f.name == "docker-compose.yml"):
        rel = path.resolve().relative_to(root).as_posix()
        deployment = "/".join(Path(rel).parts[1:-1])
        found += quanta.software_quanta(deployment, yaml.safe_load(path.read_text(encoding="utf-8")) or {}, rel)

    def ki(local: str) -> ox.NamedNode:
        return ox.NamedNode(KI + local)

    quads: list[ox.Quad] = []
    texts: dict[str, str] = {}
    counts: dict[str, int] = {}
    for q in found:
        subject = ki(f"node/{scope}/{normalise(q.identifier)}")
        texts[subject.value] = q.claim
        counts[f"quantum:{q.view}"] = counts.get(f"quantum:{q.view}", 0) + 1
        quads += [ox.Quad(subject, RDF_TYPE, ki("Quantum"), graph),
                  ox.Quad(subject, ki("identifier"), ox.Literal(q.identifier), graph),
                  ox.Quad(subject, ki("claim"), ox.Literal(q.claim), graph),
                  ox.Quad(subject, ki("pointer"), ox.Literal(whole(root, q.pointer)), graph),
                  ox.Quad(subject, ki("view"), ki(VIEW[q.view]), graph)]
        if q.deployment:
            quads.append(ox.Quad(subject, ki("deployment"), ox.Literal(q.deployment), graph))
        for part in q.parts:
            # A module's IRI is the one Вивід gives a declared unit, so an Owner edge and a quantum's part meet.
            if q.view == "data":
                iri, kind = ki(f"module/{scope}/{part}"), "Module"
            else:
                iri, kind = ki(f"component/{scope}/{q.deployment}/{part}"), "Component"
            quads += [ox.Quad(subject, ki("includes"), iri, graph),
                      ox.Quad(iri, RDF_TYPE, ki(kind), graph),
                      ox.Quad(iri, RDFS_LABEL, ox.Literal(part), graph)]
    result = {"protocol": request["protocol"], "version": VERSION, "problems": problems, "findings": findings,
              "texts": texts, "prefixes": {}, "counts": counts, "units": units(catalogue)}
    return quads, result


def main() -> int:
    request = json.load(sys.stdin)
    quads, result = extract(request)
    output = Path(request["output"])
    output.mkdir(parents=True, exist_ok=True)
    ox.serialize(quads, output=str(output / "quads.nq"), format=ox.RdfFormat.N_QUADS)
    (output / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
