# SPDX-License-Identifier: MPL-2.0
"""A publish job names the version a unit would be published as (ADR-A149 decisions 2 and 3)."""

from __future__ import annotations

import re

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS

from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_jobs import catalogue
from lattice_workers.config_studio_publish import HAS_IDENTITY, prepare, registry_graph, version_graph

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


def _version_of(turtle: str, root: URIRef) -> tuple[URIRef, Graph]:
    out = prepare(JOB, Graph().parse(data=turtle, format="turtle"), root)
    artefact = next(out.objects(JOB, CST.artefact))
    return out.value(JOB, CST.version), Graph().parse(data=str(out.value(artefact, CST.content)), format="nt")


BINDING = """
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> . @prefix ex: <https://example.org/> .
ex:binding a voc:SchemeBinding ; voc:boundScheme ex:perils ; ex:default ex:fire .
"""


def test_a_reference_to_a_followed_lineage_is_pinned_to_its_current_version_and_a_member_pins_its_version():
    """ADR-A149 decision 5: publishing resolves a followed reference and records every version the unit read."""
    perils, perils_graph = _version_of(TURTLE, PERILS)
    binding = URIRef("https://example.org/binding")
    out = prepare(JOB, Graph().parse(data=BINDING, format="turtle"), binding, perils_graph)
    version = out.value(JOB, CST.version)
    content = Graph().parse(data=str(out.value(next(out.objects(JOB, CST.artefact)), CST.content)), format="nt")
    assert (version, URIRef("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#boundScheme"), perils) in content
    assert (URIRef("https://example.org/binding"), None, PERILS) not in content
    assert set(out.objects(JOB, CST.pins)) == {perils}
    assert (version, CST.pins, perils) in content
    # A later edition of the scheme names another version of the binding, since what it pins changed.
    changed = TURTLE.replace('"Fire"', '"Fire and lightning"')
    later, later_graph = _version_of(changed, PERILS)
    assert later != perils
    assert prepare(JOB, Graph().parse(data=BINDING, format="turtle"), binding, later_graph).value(JOB, CST.version) != version


def test_a_followed_lineage_is_found_in_the_registry_when_no_context_holds_it():
    perils, perils_graph = _version_of(TURTLE, PERILS)
    from lattice_workers.config_studio_publish import registry_graph

    lineage_graph = Graph()
    lineage_graph.add((PERILS, CST.current, perils))
    read = {registry_graph(str(PERILS)): lineage_graph}
    out = prepare(JOB, Graph().parse(data=BINDING, format="turtle"), URIRef("https://example.org/binding"), Graph(), lambda iri: read.get(iri, Graph()))
    assert set(out.objects(JOB, CST.pins)) == {perils}


def test_a_reference_to_an_unpublished_unit_fails():
    with pytest.raises(ValueError, match="not published"):
        prepare(JOB, Graph().parse(data=BINDING + TURTLE, format="turtle"), URIRef("https://example.org/binding"))


def test_a_fence_job_digests_an_import_so_equal_imports_name_one_graph():
    """ADR-A149 decision 6."""
    from lattice_workers.config_studio_publish import fence

    a = fence(JOB, Graph().parse(data=TURTLE, format="turtle")).value(JOB, CST.digest)
    b = fence(JOB, Graph().parse(data=TURTLE, format="turtle")).value(JOB, CST.digest)
    assert a == b and len(str(a)) == 64
    with pytest.raises(ValueError, match="no triple"):
        fence(JOB, Graph())


def _encode_for_uri(text: str) -> str:
    """SPARQL's ENCODE_FOR_URI, written out byte by byte so the test does not rest on the code it holds equal."""
    return "".join(chr(b) if chr(b) in "-_.~" or chr(b).isascii() and chr(b).isalnum() else f"%{b:02X}" for b in text.encode("utf-8"))


@pytest.mark.parametrize("lineage", ["https://example.org/perils", "urn:example:unit?a=b&c=\u00e9 #f"])
def test_the_registry_graphs_are_named_by_the_profiles_rule(lineage):
    """The persistence profile names a root's graph by a prefix and the root encoded, which the writer's operations apply."""
    c = catalogue()
    profile = Graph().parse(c.root / c.area("contracts") / "config-studio" / "persistence-profile.ttl", format="turtle")
    dal = "https://www.nebularis.org/neuro-semantic/lattice/persistence#graphIriTemplate"
    cst = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#"
    lineage_prefix = str(profile.value(URIRef(cst + "LineageProfile"), URIRef(dal))).removesuffix("{id}")
    version_prefix = str(profile.value(URIRef(cst + "VersionProfile"), URIRef(dal))).removesuffix("{id}")
    version = f"{lineage}/rev/1-0123456789abcdef"
    assert registry_graph(lineage) == lineage_prefix + _encode_for_uri(lineage)
    assert version_graph(version) == version_prefix + _encode_for_uri(version)
