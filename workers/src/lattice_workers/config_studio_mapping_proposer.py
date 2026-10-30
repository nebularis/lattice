# SPDX-License-Identifier: MPL-2.0
"""Proposing a MORK mapping scheme with a language model (MORK README §5.18, the studio's mapping mode).

The model is asked over the Chat Completions wire format, with `mork_propose`'s tools offered as functions: the teaching
pack, the target cards, the source's cards, candidate target terms, one target term in depth, and the check. It calls
them as the trial agents did, until it answers with a scheme in MCN. Every tool reads only the job's own documents, the
source vocabulary and the sample source, so the model never names a file. The workspace's own reviews are given to it as
rules (`History.rules`), so what the author corrected before is said before the model proposes again.

The answer is decoded, checked once more over the sample, and returned as an artefact for the mapping part: the proposal
with a `mork:ProposalRun` that records the model, the pack, the run's start and end and the tokens its provider counted,
each mapping naming the run with `prov:wasGeneratedBy`. The author reviews it in mapping mode, and nothing is saved until
they save. A deployment configures the model with LATTICE_PROPOSER_URL, LATTICE_PROPOSER_MODEL and LATTICE_PROPOSER_KEY,
as for the sentence-level proposer, and LATTICE_MAPPING_PROPOSER_ROUNDS bounds the tool calls, 40 by default."""

from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, SH, XSD

from .config_studio_jobs import CST, _Result

MORK = "http://www.nebularis.org/ontologies/Mork#"
LAYERS = ["instrument", "eligibility", "party", "behaviour", "quantification"]
_FORMATS = {"text/turtle": "turtle", "application/n-triples": "nt"}

TOOLS = [
    {"name": "teaching_pack", "description": "MORK's teaching pack: notation, doctrine, worked cassettes, the translation table of legal words and MCN's codebook. Read it first.", "parameters": {"type": "object", "properties": {}}},
    {"name": "target_cards", "description": "One line per term of the named LATTICE layers.",
     "parameters": {"type": "object", "properties": {"layers": {"type": "array", "items": {"type": "string", "enum": LAYERS}}}, "required": ["layers"]}},
    {"name": "source_cards", "description": "One line per term of the source vocabulary.", "parameters": {"type": "object", "properties": {}}},
    {"name": "candidate_terms", "description": "The LATTICE terms likeliest to match one source term, a CURIE or IRI of the source vocabulary.",
     "parameters": {"type": "object", "properties": {"term": {"type": "string"}, "k": {"type": "integer"}}, "required": ["term"]}},
    {"name": "describe_term", "description": "One LATTICE term in depth, with the laws its layer's shapes state. Read it for each target term you mean to write.",
     "parameters": {"type": "object", "properties": {"term": {"type": "string"}}, "required": ["term"]}},
    {"name": "check_mapping", "description": "Decode, validate and compile a proposal in MCN, run it over the sample source when there is one, and hold what it writes to LATTICE's laws. Findings at severity info are not errors.",
     "parameters": {"type": "object", "properties": {"mcn": {"type": "string"}}, "required": ["mcn"]}},
]


class Model(Protocol):
    """A chat model that may call tools. `chat` returns the assistant's message and the tokens it read and wrote."""

    name: str

    def chat(self, messages: list, tools: list) -> tuple[dict, int, int]: ...


@dataclass
class ChatCompletionsModel:
    endpoint: str
    model: str
    key: Optional[str] = None
    timeout: float = 300.0

    @property
    def name(self) -> str:
        return self.model

    def chat(self, messages: list, tools: list) -> tuple[dict, int, int]:
        body = json.dumps({"model": self.model, "temperature": 0, "messages": messages,
                           "tools": [{"type": "function", "function": t} for t in tools]}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        request = urllib.request.Request(self.endpoint.rstrip("/") + "/chat/completions", data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310, the deployment's own endpoint
            reply = json.loads(response.read().decode("utf-8"))
        usage = reply.get("usage") or {}
        return reply["choices"][0]["message"], int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


def model_from_env(env: Mapping[str, str]) -> ChatCompletionsModel:
    url, model = (env.get(k, "").strip() for k in ("LATTICE_PROPOSER_URL", "LATTICE_PROPOSER_MODEL"))
    if not (url and model):
        raise ValueError("no language model is configured: set LATTICE_PROPOSER_URL and LATTICE_PROPOSER_MODEL")
    return ChatCompletionsModel(url, model, env.get("LATTICE_PROPOSER_KEY") or None)


@dataclass
class _Tools:
    """The tools, bound to the job's documents."""

    source: Path
    sample: Optional[Path]
    namespace: str
    checks: list = field(default_factory=list)

    def call(self, name: str, args: dict) -> str:
        from mork_propose import server

        if name == "teaching_pack":
            return server.teaching_pack()
        if name == "target_cards":
            return server.target_cards([layer for layer in args.get("layers") or LAYERS if layer in LAYERS])
        if name == "source_cards":
            return server.source_cards(str(self.source), self.namespace)
        if name == "candidate_terms":
            return server.candidate_terms(str(self.source), str(args["term"]), LAYERS, int(args.get("k") or 8), self.namespace)
        if name == "describe_term":
            return server.describe_term(str(args["term"]))
        if name == "check_mapping":
            out = server.check_mapping(str(args["mcn"]), str(self.sample) if self.sample else "")
            self.checks.append(out)
            return out
        raise ValueError(f"no tool is named {name}")


def _instructions(namespace: str, base: str, rules: list[str]) -> str:
    lines = [
        "Propose a MORK mapping scheme from the source vocabulary to LATTICE's stated meaning, in MCN.",
        "Read teaching_pack first, then the source's cards and the target cards. Ask candidate_terms where a source term's match is unclear, "
        "and describe_term for each target term you mean to write. Run check_mapping until it reports no error, then answer with the scheme alone "
        "in one fenced block marked mcn.",
        f"The source vocabulary's namespace is {namespace or 'given by its cards'}. Use {base} as the scheme's @b base, so nothing you mint "
        "names a node the workspace already holds.",
        "Map who must, may or must not do what for whom, under which conditions, and what arises on breach. Record confidence as weighting out of "
        "100 and the reason for doubt as a note.",
    ]
    if rules:
        lines += ["The workspace's reviews of earlier proposals teach these rules, the most frequent first:", *(f"- {r}" for r in rules)]
    return "\n".join(lines)


def _mcn(content: str) -> str:
    found = re.search(r"```(?:mcn)?\s*\n(.*?)```", content or "", re.S)
    return (found.group(1) if found else content or "").strip()


def _document(config: Graph, role: URIRef) -> Optional[tuple[str, str, Optional[str]]]:
    docs = [d for d in config.subjects(RDF.type, CST.ImportDocument) if (d, CST.documentRole, role) in config]
    if len(docs) > 1:
        raise ValueError(f"a mapping proposal reads at most one document of role {role}")
    if not docs:
        return None
    content, media = config.value(docs[0], CST.documentContent), str(config.value(docs[0], CST.documentMediaType))
    if content is None or media not in _FORMATS:
        raise ValueError(f"a mapping proposal's documents are Turtle or N-Triples, not {media}")
    return str(content), media, (str(config.value(docs[0], CST.sourceNamespace)) if config.value(docs[0], CST.sourceNamespace) else None)


def propose_mapping(job: URIRef, config: Graph, model: Model, submitted_at: str, rounds: int = 40,
                    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> Graph:
    """The job's result: the final check's findings and one artefact for the mapping part."""
    from .config_studio_jobs import catalogue

    catalogue()  # puts the catalogue reader, which mork_propose finds its files with, on the path of an installed worker
    import mcn_decoder
    from mork_propose.history import History

    source = _document(config, CST.SourceVocabulary)
    if source is None:
        raise ValueError("a mapping proposal needs the source vocabulary, a cst:ImportDocument with cst:documentRole cst:SourceVocabulary")
    sample = _document(config, CST.SampleSource)
    base = f"{job}:proposal#"
    result = _Result(job)
    started = clock()
    with tempfile.TemporaryDirectory() as folder:
        source_path = Path(folder) / ("source." + _FORMATS[source[1]].replace("turtle", "ttl"))
        source_path.write_text(source[0], encoding="utf-8")
        sample_path = None
        if sample is not None:
            sample_path = Path(folder) / ("sample." + _FORMATS[sample[1]].replace("turtle", "ttl"))
            sample_path.write_text(sample[0], encoding="utf-8")
        history = History(Path(folder) / "history.ttl")
        history.graph += config
        tools = _Tools(source_path, sample_path, source[2] or "")
        messages = [{"role": "system", "content": _instructions(source[2] or "", base, history.rules())},
                    {"role": "user", "content": "Propose the mapping scheme."}]
        read = written = 0
        answer = None
        for _ in range(rounds):
            message, used_in, used_out = model.chat(messages, TOOLS)
            read, written = read + used_in, written + used_out
            messages.append({k: v for k, v in message.items() if k in ("role", "content", "tool_calls")})
            calls = message.get("tool_calls") or []
            if not calls:
                answer = _mcn(message.get("content") or "")
                break
            for call in calls:
                fn = call.get("function") or {}
                try:
                    out = tools.call(fn.get("name", ""), json.loads(fn.get("arguments") or "{}"))
                except Exception as error:  # a failing tool call is the model's to read and correct
                    out = f"error: {error}"
                messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": out})
        ended = clock()
        if not answer:
            raise ValueError(f"the model gave no scheme within {rounds} rounds")
        proposal = mcn_decoder.decode(answer)
        clashes = sorted({str(s) for s in proposal.subjects() if isinstance(s, URIRef) and (s, None, None) in config})
        if clashes:
            raise ValueError(f"the proposal names nodes the workspace already holds, such as {clashes[0]}")
        final = json.loads(tools.call("check_mapping", {"mcn": answer}))

    severity = {"error": SH.Violation, "warning": SH.Warning}
    for f in final["findings"]:
        result.finding(severity.get(f["severity"], SH.Info), f["message"], f["code"], URIRef(f["about"]) if f.get("about") else None)
    run = URIRef(f"{job}:run")
    proposal.add((run, RDF.type, URIRef(MORK + "ProposalRun")))
    proposal.add((run, RDF.type, PROV.Activity))
    proposal.add((run, URIRef(MORK + "proposerModel"), Literal(model.name)))
    proposal.add((run, URIRef(MORK + "teachingPackVersion"), Literal("MTP, mork_propose")))
    proposal.add((run, PROV.startedAtTime, Literal(started.isoformat(), datatype=XSD.dateTime)))
    proposal.add((run, PROV.endedAtTime, Literal(ended.isoformat(), datatype=XSD.dateTime)))
    proposal.add((run, URIRef(MORK + "inputTokens"), Literal(read, datatype=XSD.nonNegativeInteger)))
    proposal.add((run, URIRef(MORK + "outputTokens"), Literal(written, datatype=XSD.nonNegativeInteger)))
    for scheme in proposal.subjects(RDF.type, URIRef(MORK + "MappingScheme")):
        for m in list(proposal.subjects(URIRef(MORK + "mappingScheme"), scheme)):
            proposal.add((m, PROV.wasGeneratedBy, run))
    result.artefact("proposal.ttl", "text/turtle", proposal.serialize(format="turtle"), "mapping")
    result.artefact("proposal.mcn", "text/plain", answer + "\n", "proposal")
    result.conforms(final["errors"] == 0)
    return result.graph
