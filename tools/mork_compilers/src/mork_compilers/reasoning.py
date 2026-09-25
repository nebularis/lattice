# SPDX-License-Identifier: MPL-2.0

"""
Calls the test-only reasoning harness (ADR-A83), ``platform/reasoning-testkit``,
as a subprocess. No reasoner is a dependency of this package: build the jar
with ``mise run bootstrap:reasoning-testkit``, and callers skip when
``available()`` is false. ``LATTICE_REASONING_TESTKIT`` overrides the jar path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from rdflib import BNode, Graph
from rdflib.namespace import RDF

from .namespaces import SWRL

JAR = Path(os.environ.get(
    "LATTICE_REASONING_TESTKIT",
    Path(__file__).resolve().parents[4] / "platform/reasoning-testkit/target/reasoning-testkit.jar",
))


def available() -> bool:
    return JAR.exists() and shutil.which("java") is not None


def anonymise_rules(graph: Graph) -> Graph:
    """A copy with every named ``swrl:Imp`` moved onto a blank node, the only
    form the OWL API parses as a rule."""
    copy = Graph()
    copy += graph
    for rule in list(copy.subjects(RDF.type, SWRL.Imp)):
        if isinstance(rule, BNode):
            continue
        anonymous = BNode()
        for _, p, o in list(copy.triples((rule, None, None))):
            copy.remove((rule, p, o))
            copy.add((anonymous, p, o))
    return copy


def run(command: str, *iris: str, graphs: Iterable[Graph]):
    """The ``result`` of one testkit command over ``graphs``, passed as one
    merged RDF/XML file: the OWL API parses each file on its own, so a data triple in a
    file without its property's declaration would read as an annotation."""
    merged = Graph()
    for graph in graphs:
        merged += graph
    with tempfile.TemporaryDirectory() as directory:
        # RDF/XML: the OWL API's Turtle parser rejects some closures, and its
        # fallback parser needs JAXB, which Java 11 and later do not ship.
        path = Path(directory) / "closure.owl"
        anonymise_rules(merged).serialize(path, format="xml")
        output = subprocess.run(
            ["java", "--sun-misc-unsafe-memory-access=allow", "-jar", str(JAR), command, *iris, str(path)], capture_output=True, text=True, check=True
        ).stdout
    return json.loads(output.strip().splitlines()[-1])["result"]
