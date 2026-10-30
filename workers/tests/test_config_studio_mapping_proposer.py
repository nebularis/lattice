# SPDX-License-Identifier: MPL-2.0
"""The mapping proposer's loop, with a scripted model in place of a language model: it calls the tools, answers with the
ODRL trial's second proposal, and the job returns the proposal for the mapping part with its run and the tokens counted."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, XSD

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_mapping_proposer import propose_mapping

ROOT = jobs.find_root()
ODRL = ROOT / "contracts" / "config-studio" / "odrl"
MORK = "http://www.nebularis.org/ontologies/Mork#"
JOB = URIRef("urn:lattice:studio:job:00000000-0000-0000-0000-0000000000aa")


class Scripted:
    """Answers each turn from a script, and records what the tools gave it."""

    name = "scripted"

    def __init__(self, answer: str):
        self.turns = [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "teaching_pack", "arguments": "{}"}},
                {"id": "2", "type": "function", "function": {"name": "describe_term", "arguments": json.dumps({"term": "ins:Permission"})}}]},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "3", "type": "function", "function": {"name": "check_mapping", "arguments": json.dumps({"mcn": answer})}}]},
            {"role": "assistant", "content": f"Here it is.\n```mcn\n{answer}\n```"},
        ]
        self.seen = []

    def chat(self, messages, tools):
        assert {t["name"] for t in tools} >= {"teaching_pack", "check_mapping", "describe_term"}
        self.seen = messages
        return self.turns.pop(0), 1000, 100


def _config(sample: bool = True) -> Graph:
    g = Graph()
    for n, (role, path) in enumerate([(CST.SourceVocabulary, ODRL / "odrl22.ttl")] + ([(CST.SampleSource, ODRL / "trial" / "software-licence.ttl")] if sample else [])):
        doc = URIRef(f"urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:import/{n + 1}")
        g.add((doc, RDF.type, CST.ImportDocument))
        g.add((doc, CST.documentRole, role))
        g.add((doc, CST.documentContent, Literal(path.read_text(encoding="utf-8"))))
        g.add((doc, CST.documentMediaType, Literal("text/turtle")))
    return g


def test_a_proposal_calls_the_tools_and_returns_the_scheme_with_its_run_and_cost():
    answer = (ODRL / "trial" / "run-2" / "proposal.mcn").read_text(encoding="utf-8")
    model = Scripted(answer)
    times = iter([datetime(2026, 10, 30, 3, tzinfo=timezone.utc), datetime(2026, 10, 30, 3, 2, tzinfo=timezone.utc)])
    g = propose_mapping(JOB, _config(), model, "2026-10-30T03:00:00Z", clock=lambda: next(times))
    assert (JOB, CST.conforms, Literal(True)) in g
    tools = [m for m in model.seen if m["role"] == "tool"]
    assert "MORK" in tools[0]["content"] and "(law I8)" in tools[1]["content"] and json.loads(tools[2]["content"])["errors"] == 0
    artefact = next(a for a in g.objects(JOB, CST.artefact) if str(g.value(a, CST.group)) == "mapping")
    proposal = Graph().parse(data=str(g.value(artefact, CST.content)), format="turtle")
    run = URIRef(f"{JOB}:run")
    assert (run, RDF.type, URIRef(MORK + "ProposalRun")) in proposal
    assert (run, URIRef(MORK + "inputTokens"), Literal(3000, datatype=XSD.nonNegativeInteger)) in proposal
    assert proposal.value(run, PROV.endedAtTime).toPython() - proposal.value(run, PROV.startedAtTime).toPython() == timedelta(minutes=2)
    assert set(proposal.subjects(PROV.wasGeneratedBy, run)) == set(proposal.subjects(URIRef(MORK + "mappingScheme"), None)) != set()


def test_a_proposal_without_a_source_vocabulary_or_naming_the_workspace_s_nodes_is_refused():
    with pytest.raises(ValueError, match="source vocabulary"):
        propose_mapping(JOB, Graph(), Scripted(""), "2026-10-30T03:00:00Z")
    answer = (ODRL / "trial" / "run-2" / "proposal.mcn").read_text(encoding="utf-8")
    config = _config(sample=False)
    config.add((URIRef("https://example.org/lattice/odrl/mapping#Scheme"), RDF.type, URIRef(MORK + "MappingScheme")))
    with pytest.raises(ValueError, match="already holds"):
        propose_mapping(JOB, config, Scripted(answer), "2026-10-30T03:00:00Z")
