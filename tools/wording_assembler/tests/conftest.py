# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

from __future__ import annotations

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from helpers import FIXTURES, WRD
from wording_assembler import load_layer
from wording_assembler.layer import catalogue


@pytest.fixture(scope="session")
def layer():
    return load_layer()


@pytest.fixture(scope="session")
def facility_form() -> Graph:
    """The facility form of the Wording examples, without the facility assembled from it."""
    cat = catalogue()
    g = Graph().parse(cat.root / cat.module("wording").directory("examples") / "facility-form.ttl")
    for record in list(g.subjects(RDF.type, WRD.AssembledWording)):
        for value in list(g.objects(record, WRD.hasValue)):
            g.remove((value, None, None))
        g.remove((record, None, None))
    return g


@pytest.fixture(scope="session")
def licence_form() -> Graph:
    return Graph().parse(FIXTURES / "software-licence-form.ttl")
