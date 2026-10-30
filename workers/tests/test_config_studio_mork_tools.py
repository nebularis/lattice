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
