# SPDX-License-Identifier: MPL-2.0
"""A publish job names the version a unit would be published as (ADR-A149 decisions 2 and 3)."""

from __future__ import annotations

import re

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS

from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_publish import HAS_IDENTITY, prepare

JOB = URIRef("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000cc")
PERILS = URIRef("https://example.org/perils")
TURTLE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> . @prefix ex: <https://example.org/> .
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
ex:perils a skos:ConceptScheme ; skos:prefLabel "Perils" .
ex:fire a skos:Concept ; skos:inScheme ex:perils ; skos:prefLabel "Fire" ; skos:notation "FIRE" .
ex:flood a skos:Concept ; skos:inScheme ex:perils ; skos:prefLabel "Flood" .
ex:perils\\/note a skos:Concept ; skos:prefLabel "minted under the root" .
ex:colours a skos:ConceptScheme . ex:red a skos:Concept ; skos:inScheme ex:colours .
ex:scheme a mork:MappingScheme .
ex:m1 a mork:DataMapping ; mork:mappingScheme ex:scheme ; mork:appliesWhen [ mork:dataRef "x" ] .
"""


def published(g: Graph, root: URIRef) -> tuple[Graph, Graph]:
    out = prepare(JOB, g, root)
    artefact = next(out.objects(JOB, CST.artefact))
    return out, Graph().parse(data=str(out.value(artefact, CST.content)), format="nt")


def test_a_concept_scheme_is_published_with_its_concepts_under_a_content_addressed_version():
    g = Graph().parse(data=TURTLE, format="turtle")
    out, version_graph = published(g, PERILS)
    version = out.value(JOB, CST.version)
    assert re.fullmatch(re.escape(str(PERILS)) + r"/rev/1-[0-9a-f]{16}", str(version))
    assert str(out.value(JOB, CST.digest)).startswith(str(version).rsplit("-", 1)[1])
    assert out.value(JOB, CST.lineage) == PERILS
    assert (version, HAS_IDENTITY, PERILS) in version_graph
    members = set(version_graph.subjects(SKOS.inScheme, version))
    assert members == {URIRef("https://example.org/fire"), URIRef("https://example.org/flood")}
    assert (URIRef("https://example.org/perils/note"), SKOS.prefLabel, None) in version_graph
    assert not any(version_graph.triples((URIRef("https://example.org/red"), None, None)))
    assert not any(version_graph.triples((PERILS, SKOS.prefLabel, None)))


def test_the_same_content_names_the_same_version_and_a_change_names_another():
    g = Graph().parse(data=TURTLE, format="turtle")
    first = prepare(JOB, g, PERILS).value(JOB, CST.version)
    assert prepare(JOB, Graph().parse(data=TURTLE, format="turtle"), PERILS).value(JOB, CST.version) == first
    g.add((URIRef("https://example.org/fire"), SKOS.altLabel, URIRef("https://example.org/x")))
    assert prepare(JOB, g, PERILS).value(JOB, CST.version) != first
    # A change outside the aggregate changes nothing.
    other = Graph().parse(data=TURTLE, format="turtle")
    other.add((URIRef("https://example.org/red"), SKOS.prefLabel, URIRef("https://example.org/y")))
    assert prepare(JOB, other, PERILS).value(JOB, CST.version) == first


def test_a_mapping_scheme_takes_its_mappings_and_their_blank_nodes():
    g = Graph().parse(data=TURTLE, format="turtle")
    out, version_graph = published(g, URIRef("https://example.org/scheme"))
    version = out.value(JOB, CST.version)
    mapping = URIRef("https://example.org/m1")
    assert (mapping, URIRef("http://www.nebularis.org/ontologies/Mork#mappingScheme"), version) in version_graph
    guard = version_graph.value(mapping, URIRef("http://www.nebularis.org/ontologies/Mork#appliesWhen"))
    assert guard is not None and any(version_graph.triples((guard, None, None)))


@pytest.mark.parametrize("root, message", [
    (URIRef("https://example.org/fire"), "no unit"),
    (URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001"), "named by the studio"),
])
def test_a_root_that_is_no_unit_or_is_the_studio_s_own_fails(root, message):
    with pytest.raises(ValueError, match=message):
        prepare(JOB, Graph().parse(data=TURTLE, format="turtle"), root)
