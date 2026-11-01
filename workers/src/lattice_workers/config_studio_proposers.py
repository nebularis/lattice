# SPDX-License-Identifier: MPL-2.0
"""The contract builder's proposers (ADR-A138 decision 5) and the `propose` job, as contracts/config-studio/README.md
describes them. A proposer reads one clause and returns candidates, each a relation kind, two roles and an activity the
workspace declares. The job turns each into a `cst:Proposal` waiting for review, carrying its stated term and relation
as a payload, so nothing becomes stated meaning before a reviewer decides. Two proposers: the sentence-form reader, and
a language model over the Chat Completions wire format with a pack the deployment supplies, never one of the repository's."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional, Protocol, Sequence

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SH, SKOS, XSD

from .config_studio_jobs import CST, _Result
from .llm_providers import LLMProvider, provider_from_env

WRD = Namespace("https://www.nebularis.org/neuro-semantic/lattice/wording#")
INS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument#")
INS_VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#")
PTY = Namespace("https://www.nebularis.org/neuro-semantic/lattice/party#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")


@dataclass(frozen=True)
class Clause:
    iri: URIRef
    object_id: str
    text: str
    definition: bool


@dataclass(frozen=True)
class Context:
    """What a candidate may name, each by its label: the relation kinds, with whether each is an obligation, the
    workspace's roles, and the activities of the activity scheme."""

    kinds: Mapping[str, URIRef]
    obligations: frozenset
    roles: Mapping[str, URIRef]
    activities: Mapping[str, URIRef]


@dataclass(frozen=True)
class Candidate:
    kind: URIRef
    role: Optional[URIRef]
    counter_role: Optional[URIRef]
    activity: Optional[URIRef]
    evidence: str


class Proposer(Protocol):
    name: str
    version: str

    def propose(self, clause: Clause, context: Context) -> Sequence[Candidate]:
        """The candidates for one clause, none when it reads no relation."""


# ---- reading the workspace ------------------------------------------------------------------------------------------


def _label(g: Graph, node) -> Optional[str]:
    for p in (RDFS.label, SKOS.prefLabel):
        value = g.value(node, p)
        if value is not None:
            return str(value)
    return None


def context_of(config: Graph, spec: Graph) -> Context:
    """The kinds from Instrument's specification, the roles the workspace declares, and the activity scheme's concepts."""
    world = spec + config
    kinds, obligations = {}, set()
    for kind in world.transitive_subjects(RDFS.subClassOf, INS.LegalRelation):
        if kind == INS.LegalRelation or not isinstance(kind, URIRef):
            continue
        label = _label(world, kind) or str(kind).rsplit("#", 1)[-1]
        kinds[label] = kind
        if INS.Obligation in set(world.transitive_objects(kind, RDFS.subClassOf)):
            obligations.add(kind)
    roles = {lbl: r for r in config.subjects(RDF.type, PTY.Role) if isinstance(r, URIRef) and (lbl := _label(config, r))}
    activities = {}
    for concept in world.subjects(SKOS.inScheme, INS_VOC.Activities):
        if isinstance(concept, URIRef) and (lbl := _label(world, concept)):
            activities[lbl] = concept
    return Context(kinds=kinds, obligations=frozenset(obligations), roles=roles, activities=activities)


def _text(g: Graph, element) -> str:
    parts = sorted(g.objects(element, WRD.hasTextPart), key=lambda p: int(g.value(p, WRD.partIndex) or 0))
    out = []
    for part in parts:
        text = g.value(part, WRD.partText)
        if text is not None:
            out.append(str(text))
        else:
            # A part names its variable by identity, and the text shows the variable's key, as the library outline does.
            identity = g.value(part, WRD.refersToVariable)
            variable = g.value(None, FND.hasIdentity, identity) if identity is not None else None
            key = g.value(variable, WRD.variableKey) if variable is not None else None
            out.append("{" + (str(key) if key is not None else str(identity or "").rsplit("/", 1)[-1]) + "}")
    return "".join(out)


def clauses_wanting_meaning(config: Graph) -> list[Clause]:
    """Every text of a form, not of an assembled wording, with no stated term in meaning and no proposal waiting."""
    stated = set(config.objects(None, INS.expressedIn))
    waiting = {config.value(p, CST.span) for p in config.subjects(RDF.type, CST.Proposal) if config.value(p, CST.decision) is None}
    out = []
    for element in config.subjects(RDF.type, WRD.Text):
        if not isinstance(element, URIRef) or element in stated or element in waiting:
            continue
        text = _text(config, element)
        if not text.strip():
            continue
        definition = (element, WRD.elementType, URIRef("https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#Definition")) in config
        out.append(Clause(element, str(config.value(element, WRD.objectId) or ""), text, definition))
    return sorted(out, key=lambda c: (c.object_id, str(c.iri)))


# ---- the sentence-form proposer -------------------------------------------------------------------------------------


def _mentions(text: str, labels: Mapping[str, URIRef]) -> list[tuple[int, URIRef]]:
    """Where each label first occurs in the text, as a word or its plural, case aside."""
    found = []
    for label, node in labels.items():
        m = re.search(r"(?<![\w])" + re.escape(label) + r"(?:s|es)?(?![\w])", text, re.IGNORECASE)
        if m:
            found.append((m.start(), node))
    return sorted(found, key=lambda x: (x[0], str(x[1])))


@dataclass
class SentenceFormProposer:
    """The worker's sentence-form reader classifies the clause's relation. The roles are the workspace's roles its text
    names, the first bearing the relation and the next owed it, and the activity the first activity its text names."""

    name: str = "sentence-forms"
    version: str = field(default="")

    def __post_init__(self) -> None:
        from .wording_le.forms import load_profile

        self._profile = load_profile()
        self.version = f"sentence-forms {self._profile.profile_id} {self._profile.version}"

    def propose(self, clause: Clause, context: Context) -> Sequence[Candidate]:
        from .wording_le import model
        from .wording_le.analyse import analyse_wording

        element = model.Element(
            element_id="00000000-0000-4000-8000-000000000000", iri=str(clause.iri), object_id=clause.object_id, section_key="",
            kind="definition" if clause.definition else "clause", defined_term=None,
            parts=(model.Part(index=0, kind="literal", text=clause.text),),
        )
        wording = model.Wording(iri="urn:x:wording", document_id="", title="", template_id="", revision=1, elements=(element,), variables=())
        relation = analyse_wording(wording, self._profile)["elements"][0].get("relationClass")
        kind = INS[relation] if relation else None
        if kind is None or kind not in set(context.kinds.values()):
            return []
        roles = [node for _, node in _mentions(clause.text, context.roles)]
        activity = next((node for _, node in _mentions(clause.text, context.activities)), None)
        return [Candidate(kind, roles[0] if roles else None, roles[1] if len(roles) > 1 else None, activity, clause.text)]


# ---- the language-model proposer ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pack:
    name: str
    version: str
    system: str
    prompt: str
    temperature: Optional[float]

    @staticmethod
    def load(folder: Path) -> "Pack":
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        return Pack(
            name=str(manifest["name"]), version=str(manifest["version"]),
            system=(folder / manifest["system"]).read_text(encoding="utf-8"),
            prompt=(folder / manifest["prompt"]).read_text(encoding="utf-8"),
            temperature=float(manifest["temperature"]) if "temperature" in manifest else None,
        )


def _schema() -> dict:
    from .config_studio_jobs import catalogue

    cat = catalogue()
    return json.loads((cat.root / cat.area("contracts") / "config-studio" / "proposal-candidates.schema.json").read_text(encoding="utf-8"))


@dataclass
class LanguageModelProposer:
    """A model behind an `LLMProvider`, asked with the deployment's pack. Its reply is checked against the contract's
    schema, and a label the workspace does not declare is dropped and said so in the evidence."""

    provider: LLMProvider
    pack: Pack
    name: str = "language-model"

    @property
    def version(self) -> str:
        return f"language-model {self.provider.name}, pack {self.pack.name} {self.pack.version}"

    def _ask(self, system: str, prompt: str) -> str:
        message, _, _ = self.provider.chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}], [], self.pack.temperature)
        return message["content"] or ""

    def propose(self, clause: Clause, context: Context) -> Sequence[Candidate]:
        import jsonschema

        schema = _schema()
        values = {
            "clause": clause.text, "roles": ", ".join(sorted(context.roles)), "activities": ", ".join(sorted(context.activities)),
            "kinds": ", ".join(sorted(context.kinds)), "schema": json.dumps(schema),
        }
        render = lambda template: re.sub(r"\{(clause|roles|activities|kinds|schema)\}", lambda m: values[m.group(1)], template)
        content = self._ask(render(self.pack.system), render(self.pack.prompt))
        # A reply may wrap its JSON in a code fence.
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        reply = json.loads(content)
        jsonschema.validate(reply, schema)
        out = []
        for item in reply["candidates"]:
            kind = context.kinds.get(item["kind"])
            if kind is None:
                continue
            notes = []

            def pick(label, table, what):
                if label in (None, ""):
                    return None
                node = table.get(label)
                if node is None:
                    notes.append(f"no {what} {label!r} is declared")
                return node

            role = pick(item.get("role"), context.roles, "role")
            counter = pick(item.get("counterRole"), context.roles, "role")
            activity = pick(item.get("activity"), context.activities, "activity")
            evidence = item["evidence"] + (f" ({'; '.join(notes)})" if notes else "")
            out.append(Candidate(kind, role, counter, activity, evidence))
        return out


def language_model_from_env(env: Mapping[str, str]) -> LanguageModelProposer:
    pack = (env.get("LATTICE_PROPOSER_PACK") or "").strip()
    if not pack:
        raise ValueError("no language model is configured: set LATTICE_PROPOSER_PACK, and the provider's settings")
    return LanguageModelProposer(provider_from_env(env), Pack.load(Path(pack)))


# ---- the job --------------------------------------------------------------------------------------------------------


def _payload(clause: Clause, candidate: Candidate, base: str, context: Context) -> Graph:
    g = Graph()
    g.bind("ins", INS)
    g.bind("ins-voc", INS_VOC)
    term, relation = URIRef(f"{base}/term"), URIRef(f"{base}/relation")
    g.add((term, RDF.type, INS.Term))
    g.add((term, RDF.type, INS.Template))
    g.add((term, INS.expressedIn, clause.iri))
    g.add((relation, RDF.type, candidate.kind))
    g.add((relation, RDF.type, INS.Template))
    g.add((relation, INS.arisesUnder, term))
    first, second = (INS.obligor, INS.obligee) if candidate.kind in context.obligations else (INS.holder, INS.counterparty)
    if candidate.role is not None:
        g.add((relation, first, candidate.role))
    if candidate.counter_role is not None:
        g.add((relation, second, candidate.counter_role))
    if candidate.activity is not None:
        g.add((relation, INS.activity, candidate.activity))
    return g


def propose_all(job: URIRef, config: Graph, spec: Graph, proposer: Proposer, submitted_at: str) -> Graph:
    """The job's result: its findings, and the waiting proposals as the artefact `review.ttl`."""
    context = context_of(config, spec)
    result = _Result(job)
    review = Graph()
    review.bind("cst", CST)
    at = Literal(datetime.fromisoformat(submitted_at.replace("Z", "+00:00")).isoformat(), datatype=XSD.dateTime)
    n = 0
    for clause in clauses_wanting_meaning(config):
        try:
            candidates = proposer.propose(clause, context)
        except Exception as error:  # one clause's failure is reported and the others still proposed
            result.finding(SH.Warning, f"{clause.object_id}: the proposer failed: {type(error).__name__}: {error}", "propose", clause.iri)
            continue
        if not candidates:
            result.finding(SH.Info, f"{clause.object_id}: no candidate", "propose", clause.iri)
        for candidate in candidates:
            n += 1
            base = f"{job}:proposal/{n}"
            proposal = URIRef(base)
            payload = _payload(clause, candidate, base, context)
            review.add((proposal, RDF.type, CST.Proposal))
            review.add((proposal, CST.span, clause.iri))
            for node in (URIRef(f"{base}/term"), URIRef(f"{base}/relation")):
                review.add((proposal, CST.proposes, node))
            review.add((proposal, CST.proposer, Literal(proposer.name)))
            review.add((proposal, CST.proposerVersion, Literal(proposer.version)))
            review.add((proposal, CST.proposedAt, at))
            review.add((proposal, CST.evidence, Literal(candidate.evidence)))
            review.add((proposal, CST.payload, Literal(payload.serialize(format="turtle"))))
    result.artefact("review.ttl", "text/turtle", review.serialize(format="turtle"), "review")
    result.conforms(True)
    return result.graph
