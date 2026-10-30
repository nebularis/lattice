# SPDX-License-Identifier: MPL-2.0
"""RML read into MORK: the loan example's RML comes back the same through mork2rml, and what MORK cannot say is reported."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from rdflib.compare import isomorphic

import mork2rml
import rml2mork

LOAN = Path(__file__).resolve().parents[3] / "ontology" / "mork" / "examples" / "Mork2RML" / "loan_mapping.rml"


def test_the_loan_rml_round_trips_through_mork_and_mork2rml():
    rml = Graph().parse(LOAN, format="turtle")
    read = rml2mork.read(rml, "http://example.org/mapping#")
    assert read.findings == []
    back = mork2rml.MorkToRmlCompiler(read.graph, base_iri="http://example.org/fin/", default_source="loan.json").compile()
    assert isomorphic(back, rml)


def test_what_mork_cannot_say_is_reported_and_constants_are_kept():
    rml = Graph().parse(data="""@prefix rr: <http://www.w3.org/ns/r2rml#> . @prefix rml: <http://semweb.mmlab.be/ns/rml#> .
        @prefix ql: <http://semweb.mmlab.be/ns/ql#> . @prefix fnml: <http://semweb.mmlab.be/ns/fnml#> . @prefix ex: <http://example.org/> .
        ex:TM rml:logicalSource [ rml:source "people.csv" ; rml:referenceFormulation ql:CSV ] ;
          rr:subjectMap [ rr:template "http://example.org/person-{id}" ] ;
          rr:predicateObjectMap [ rr:predicate ex:name ; rr:objectMap [ rml:reference "name" ; rr:language "en" ] ] ,
            [ rr:predicate ex:kind ; rr:objectMap [ rr:constant ex:Person ] ] ,
            [ rr:predicate ex:score ; rr:objectMap [ fnml:execution [] ] ] .""", format="turtle")
    read = rml2mork.read(rml, "http://example.org/m#")
    assert any("subject template" in f for f in read.findings)
    assert any("a language" in f for f in read.findings)
    assert any("function" in f for f in read.findings)
    assert (None, rml2mork.MORK.exactABoxMatch, rml2mork.URIRef("http://example.org/Person")) in read.graph
    assert (None, rml2mork.MORK["format"], rml2mork.MORK.CSV) in read.graph
