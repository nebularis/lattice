# SPDX-License-Identifier: MPL-2.0

"""
Calls the test-only reasoning harness (ADR-A83), ``platform/reasoning-testkit``,
as a subprocess. No reasoner is a dependency of this package: build the jar
with ``mise run bootstrap:reasoning-testkit``, and callers skip when
``available()`` is false. ``LATTICE_REASONING_TESTKIT`` overrides the jar path.
``LATTICE_REASONING_TIMEOUT`` (seconds, default 300) bounds one call, so a stalled JVM fails
the test instead of hanging the run (TD-31).

Each call starts a JVM, and for the closures the tests send, starting it and loading the OWL API
and HermiT classes is about half of a call. ``jvm_options`` shortens that with a class-data
archive that the JVM builds beside the jar on first use, a serial collector, and C1-only
compilation. Over 41 closures from the ontology tests that took 51.8s to 29.9s. The archive
is rebuilt by the JVM when the jar changes. ``LATTICE_REASONING_JVM_OPTIONS`` replaces the
options, for example with an empty string to run the JVM with its defaults.
"""

from __future__ import annotations

import json
import os
import shlex
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


TIMEOUT = int(os.environ.get("LATTICE_REASONING_TIMEOUT", "300"))


def jvm_options() -> list[str]:
    """JVM startup options for one testkit call. The archive sits beside the jar, in a
    directory that is build output. Logging is off so that a missing or stale archive, or an
    unwritable directory, does not print anything and the call simply runs without it."""
    override = os.environ.get("LATTICE_REASONING_JVM_OPTIONS")
    if override is not None:
        return shlex.split(override)
    return [
        "-XX:+AutoCreateSharedArchive",
        f"-XX:SharedArchiveFile={JAR.with_suffix('.jsa')}",
        "-XX:+UseSerialGC",
        "-XX:TieredStopAtLevel=1",
        "-Xlog:disable",
    ]


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
            ["java", *jvm_options(), "--sun-misc-unsafe-memory-access=allow", "-jar", str(JAR), command, *iris, str(path)], capture_output=True, text=True, check=True, timeout=TIMEOUT
        ).stdout
    return json.loads(output.strip().splitlines()[-1])["result"]
