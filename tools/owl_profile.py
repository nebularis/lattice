# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The structural part of the OWL 2 DL profile, over every ontology document.

A DL reasoner rejects a document that redeclares reserved vocabulary, uses a class as a predicate,
or gives one IRI two incompatible kinds. The 2026-10-28 design review found four layers redeclaring
``rdf:Property`` or ``rdfs:Datatype`` as ``owl:Class`` and SPC using a class as a predicate, and no
check that would have said so. This check is that check, for the rules a graph can show without a
reasoner. It is not a profile checker: an expressivity violation (a non-simple property in a
cardinality restriction, say) needs a reasoner and is out of scope.

Four rules, each a finding of the form ``kind iri``:

``reserved``
    an IRI in the ``rdf:``, ``rdfs:``, ``owl:`` or ``xsd:`` namespace declared as a class, a property
    or a datatype
``class-as-predicate``
    an IRI declared ``owl:Class`` and used as the predicate of a triple
``two-property-kinds``
    an IRI declared both ``owl:ObjectProperty`` and ``owl:DatatypeProperty``
``class-and-datatype``
    an IRI declared both ``owl:Class`` and ``rdfs:Datatype``

Documents are the ``spec/*.ttl`` and ``vocab/*.ttl`` files ``git ls-files`` lists under ``ontology/``,
never a filesystem walk. ``owl-profile-exceptions.txt`` beside this file lists findings allowed to
stay, one per line as ``kind iri``, each with its reason after ``#``.

Usage, from the repository root::

    mise run check:owl-profile
    mise exec -- python tools/owl_profile.py --report
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

ROOT = lattice_repo_catalogue.load().root
EXCEPTIONS_PATH = Path(__file__).resolve().parent / "owl-profile-exceptions.txt"
RESERVED = (str(RDF), str(RDFS), str(OWL), str(XSD))
DECLARATIONS = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, RDFS.Datatype)


@dataclass(frozen=True)
class Finding:
    kind: str
    iri: str
    path: str

    @property
    def key(self) -> str:
        return f"{self.kind} {self.iri}"


def documents() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--", "ontology/*/spec/*.ttl", "ontology/*/vocab/*.ttl",
                          "ontology/applied/*/spec/*.ttl", "ontology/applied/*/vocab/*.ttl",
                          "ontology/applied/*/*/spec/*.ttl", "ontology/applied/*/*/vocab/*.ttl"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return sorted({ROOT / line for line in out.splitlines() if line.strip()})


def findings_in(graph: Graph, path: str) -> list[Finding]:
    found: list[Finding] = []
    declared: dict[URIRef, set[URIRef]] = {}
    for kind in DECLARATIONS:
        for subject in graph.subjects(RDF.type, kind):
            if isinstance(subject, URIRef):
                declared.setdefault(subject, set()).add(kind)
    for iri, kinds in sorted(declared.items()):
        if str(iri).startswith(RESERVED):
            found.append(Finding("reserved", str(iri), path))
        if OWL.ObjectProperty in kinds and OWL.DatatypeProperty in kinds:
            found.append(Finding("two-property-kinds", str(iri), path))
        if OWL.Class in kinds and RDFS.Datatype in kinds:
            found.append(Finding("class-and-datatype", str(iri), path))
    predicates = {p for p in graph.predicates() if isinstance(p, URIRef)}
    for iri in sorted(predicates):
        if OWL.Class in declared.get(iri, ()):
            found.append(Finding("class-as-predicate", str(iri), path))
    return found


def excepted() -> set[str]:
    if not EXCEPTIONS_PATH.is_file():
        return set()
    keys = set()
    for line in EXCEPTIONS_PATH.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.lstrip().startswith("#"):
            keys.add(f"{parts[0]} {parts[1]}")
    return keys


def scan() -> list[Finding]:
    found: list[Finding] = []
    for path in documents():
        graph = Graph()
        try:
            graph.parse(path, format="turtle")
        except Exception as error:  # noqa: BLE001
            found.append(Finding("unparseable", str(error).splitlines()[0][:120], str(path.relative_to(ROOT))))
            continue
        found.extend(findings_in(graph, str(path.relative_to(ROOT))))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--report", action="store_true", help="print every finding, excepted or not, and do not fail")
    arguments = parser.parse_args(argv)
    found = scan()
    baseline = excepted()
    if arguments.report:
        for f in found:
            print(f"{'excepted' if f.key in baseline else 'FINDING '} {f.kind:<22} {f.iri}  ({f.path})")
        print(f"{len(found)} finding(s) in {len(documents())} document(s), {len(baseline)} excepted")
        return 0
    new = [f for f in found if f.key not in baseline]
    stale = baseline - {f.key for f in found}
    for f in new:
        print(f"OWL-DL {f.path}: {f.kind} {f.iri}")
    for key in sorted(stale):
        print(f"OWL-DL stale exception, remove it from {EXCEPTIONS_PATH.name}: {key}")
    if new or stale:
        return 1
    print(f"owl profile: {len(documents())} document(s), {len(found)} known finding(s), none new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
