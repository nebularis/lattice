# SPDX-License-Identifier: MPL-2.0
"""MORK's proposal tools that need a source or a sample, run for the studio's MCP server (contracts/config-studio/README.md,
MCP). The service hands each call over as a tool job, whose input holds one `cst:ToolRequest`, naming the tool and its
arguments as JSON, and the documents it reads, each a `cst:ImportDocument` with its `cst:documentRole`. The result is one
artefact, `result`. The tools that need neither, the teaching pack, the target cards and one term in depth, are staged
with the studio's assets and served by the service itself."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .config_studio_jobs import CST, _Result, catalogue

TOOLS = ("source_cards", "candidate_terms", "check_mapping", "decode_mcn")
LAYERS = ["instrument", "eligibility", "party", "behaviour", "quantification"]
_FORMATS = {"text/turtle": "ttl", "application/n-triples": "nt"}


def _document(config: Graph, role: URIRef, folder: Path) -> Optional[Path]:
    docs = [d for d in config.subjects(RDF.type, CST.ImportDocument) if (d, CST.documentRole, role) in config]
    if len(docs) > 1:
        raise ValueError(f"a tool reads at most one document of role {role}")
    if not docs:
        return None
    media = str(config.value(docs[0], CST.documentMediaType))
    if media not in _FORMATS:
        raise ValueError(f"a tool's documents are Turtle or N-Triples, not {media}")
    path = folder / f"{str(role).rsplit('#', 1)[-1]}.{_FORMATS[media]}"
    path.write_text(str(config.value(docs[0], CST.documentContent)), encoding="utf-8")
    Graph().parse(path)  # refuses a document that does not parse before a tool reads it
    return path


def run_tool(job: URIRef, config: Graph) -> Graph:
    catalogue()  # puts the catalogue reader, which mork_propose finds its files with, on the path of an installed worker
    from mork_propose import server

    requests = list(config.subjects(RDF.type, CST.ToolRequest))
    if len(requests) != 1:
        raise ValueError("a tool job holds exactly one cst:ToolRequest")
    name = str(config.value(requests[0], CST.toolName))
    if name not in TOOLS:
        raise ValueError(f"no tool is named {name}: the worker runs {', '.join(TOOLS)}")
    args = json.loads(str(config.value(requests[0], CST.toolArguments) or "{}"))
    if not isinstance(args, dict):
        raise ValueError("a tool's arguments are a JSON object")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = _document(config, CST.SourceVocabulary, folder)
        sample = _document(config, CST.SampleSource, folder)
        namespace = str(args.get("namespace") or "")
        if name in ("source_cards", "candidate_terms") and source is None:
            raise ValueError(f"{name} reads a source vocabulary")
        if name == "source_cards":
            out, media = server.source_cards(str(source), namespace), "text/plain"
        elif name == "candidate_terms":
            out, media = server.candidate_terms(str(source), str(args["term"]), LAYERS, int(args.get("k") or 8), namespace), "text/plain"
        elif name == "check_mapping":
            out, media = server.check_mapping(str(args["mcn"]), str(sample) if sample else ""), "application/json"
        else:
            import mcn_decoder

            out, media = mcn_decoder.decode(str(args["mcn"])).serialize(format="turtle"), "text/turtle"
    result = _Result(job)
    result.artefact("result", media, out, name)
    result.conforms(True)
    return result.graph
