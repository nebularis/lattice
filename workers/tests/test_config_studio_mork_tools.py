# SPDX-License-Identifier: MPL-2.0
"""MORK's proposal tools run for the studio's MCP server: each reads only its job's documents, and an unknown tool is refused."""

from __future__ import annotations

import json

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_mork_tools import run_tool

ROOT = jobs.find_root()
ODRL = ROOT / "contracts" / "config-studio" / "odrl"
JOB = URIRef("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000bb")


def _input(tool: str, args: dict, source: bool = True, sample: bool = False) -> Graph:
    g = Graph()
    request = URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:tool/1")
    g.add((request, RDF.type, CST.ToolRequest))
    g.add((request, CST.toolName, Literal(tool)))
    g.add((request, CST.toolArguments, Literal(json.dumps(args))))
    for on, role, path in ((source, CST.SourceVocabulary, ODRL / "odrl22.ttl"), (sample, CST.SampleSource, ODRL / "trial" / "software-licence.ttl")):
        if on:
            doc = URIRef(f"{request}/{str(role).rsplit('#', 1)[-1]}")
            g.add((doc, RDF.type, CST.ImportDocument))
            g.add((doc, CST.documentRole, role))
            g.add((doc, CST.documentContent, Literal(path.read_text(encoding="utf-8"))))
            g.add((doc, CST.documentMediaType, Literal("text/turtle")))
    return g


def _result(g: Graph) -> str:
    return str(g.value(next(g.objects(JOB, CST.artefact)), CST.content))


def test_the_tools_read_the_job_s_documents():
    assert "odrl:Permission" in _result(run_tool(JOB, _input("source_cards", {"namespace": "http://www.w3.org/ns/odrl/2/"})))
    assert "ins:Permission" in _result(run_tool(JOB, _input("candidate_terms", {"term": "odrl:Permission", "namespace": "http://www.w3.org/ns/odrl/2/"})))
    mcn = (ODRL / "trial" / "run-2" / "proposal.mcn").read_text(encoding="utf-8")
    checked = json.loads(_result(run_tool(JOB, _input("check_mapping", {"mcn": mcn}, source=False, sample=True))))
    assert checked["errors"] == 0 and checked["output_triples"] > 0
    decoded = Graph().parse(data=_result(run_tool(JOB, _input("decode_mcn", {"mcn": mcn}, source=False))), format="turtle")
    assert len(decoded) > 100


def test_an_unknown_tool_or_a_missing_source_is_refused():
    with pytest.raises(ValueError, match="no tool is named"):
        run_tool(JOB, _input("read_file", {"path": "/etc/passwd"}))
    with pytest.raises(ValueError, match="reads a source vocabulary"):
        run_tool(JOB, _input("source_cards", {}, source=False))


def test_an_rml_mapping_imports_and_compiles_back_to_the_same_rml():
    from rdflib.compare import isomorphic

    from lattice_workers.config_studio_mork_tools import import_rml

    loan = ROOT / "ontology" / "mork" / "examples" / "Mork2RML" / "loan_mapping.rml"
    g = Graph()
    doc = URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:import/1")
    g.add((doc, RDF.type, CST.ImportDocument))
    g.add((doc, CST.documentContent, Literal(loan.read_text(encoding="utf-8"))))
    g.add((doc, CST.documentMediaType, Literal("text/turtle")))
    imported = import_rml(JOB, g)
    artefact = next(a for a in imported.objects(JOB, CST.artefact) if str(imported.value(a, CST.group)) == "mapping")
    scheme = Graph().parse(data=str(imported.value(artefact, CST.content)), format="turtle")
    assert (URIRef("http://example.org/fin/Scheme"), RDF.type, URIRef("http://www.nebularis.org/ontologies/Mork#MappingScheme")) in scheme
    compiled = jobs.run_job(JOB, "compile", "mapping", scheme, Graph(), str(ROOT), "2026-10-30T00:00:00Z")
    rml = next(a for a in compiled.objects(JOB, CST.artefact) if str(compiled.value(a, CST.path)) == "mapping.rml.ttl")
    assert isomorphic(Graph().parse(data=str(compiled.value(rml, CST.content)), format="turtle"), Graph().parse(loan, format="turtle"))
    with pytest.raises(ValueError, match="already holds"):
        import_rml(JOB, g + scheme)


def test_a_mapping_compilation_writes_each_xml_and_json_schemes_transform_and_its_attribution_table():
    """ADR-A148: the transforms worker runs what a compile job of the mapping part writes."""
    policies = ROOT / jobs.catalogue().area("tools") / "mork_transforms" / "tests" / "examples" / "policies"
    schemes = Graph().parse(policies / "xml.mork.ttl").parse(policies / "json.mork.ttl")
    compiled = jobs.run_job(JOB, "compile", "mapping", schemes, Graph(), str(ROOT), "2026-10-30T00:00:00Z")
    files = {(str(compiled.value(a, CST.group)).rsplit("/", 1)[-1], str(compiled.value(a, CST.path)), str(compiled.value(a, CST.mediaType)))
             for a in compiled.objects(JOB, CST.artefact)}
    assert {("xml#Scheme", "Scheme.xsl", "application/xslt+xml"), ("xml#Scheme", "Scheme.xsl.attribution.json", "application/json"),
            ("json#Scheme", "Scheme.jolt.json", "application/json"), ("json#Scheme", "Scheme.jolt.json.attribution.json", "application/json")} <= files
    codes = {str(c) for c in compiled.objects(None, CST.code)}
    assert {"PositionalIdentity", "KeyNotEncoded"} <= codes


def test_a_mapping_compilation_reads_the_source_codes_the_vocabulary_part_holds_as_context():
    """ADR-A149 decision 7: a job reads the workspace's other parts, so a correspondence finds its source's codes."""
    policies = ROOT / jobs.catalogue().area("tools") / "mork_transforms" / "tests" / "examples" / "policies"
    schemes = Graph().parse(policies / "xml.mork.ttl")
    codes = Graph()
    for concept in (URIRef("urn:example:source/xml#Fire"), URIRef("urn:example:source/xml#Flood")):
        for triple in list(schemes.triples((concept, None, None))):
            schemes.remove(triple)
            codes.add(triple)
    alone = jobs.run_job(JOB, "compile", "mapping", schemes, Graph(), str(ROOT), "2026-10-31T00:00:00Z")
    assert "CorrespondenceKey" in {str(c) for c in alone.objects(None, CST.code)}
    read = jobs.run_job(JOB, "compile", "mapping", schemes, Graph(), str(ROOT), "2026-10-31T00:00:00Z", codes)
    assert "CorrespondenceKey" not in {str(c) for c in read.objects(None, CST.code)}


def test_a_validation_reports_on_its_target_part_never_on_the_context_it_reads():
    """ADR-A149 decision 7: a finding about a subject only the context holds is that part's own validation's to report."""
    scheme = Graph().parse(data="""
        @prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
        <urn:x:Perils> a voc:ConceptScheme .""", format="turtle")
    own = jobs.run_job(JOB, "validate", "vocabulary", scheme, Graph(), str(ROOT), "2026-10-31T00:00:00Z")
    assert URIRef("urn:x:Perils") in set(own.objects(None, jobs.SH.focusNode))
    assert own.value(JOB, CST.conforms) == Literal(False)
    context = jobs.run_job(JOB, "validate", "vocabulary", Graph(), Graph(), str(ROOT), "2026-10-31T00:00:00Z", scheme)
    assert URIRef("urn:x:Perils") not in set(context.objects(None, jobs.SH.focusNode))
    assert context.value(JOB, CST.conforms) == Literal(True)
