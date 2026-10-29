# SPDX-License-Identifier: MPL-2.0
"""The ODRL proposer (ADR-A144): a `propose` job with target `odrl` reads one ODRL 2.2 policy from its input, maps it to
stated meaning with the studio's MORK mapping scheme compiled by `tools/mork_rdf`, and gives each rule as a proposal
waiting for review, as contracts/config-studio/README.md describes.

The policy says what it is (STD-292): its media type and its profile, `dct:conformsTo` the ODRL 2.2 namespace, travel
with it, and a policy that says otherwise is refused, never sniffed. JSON-LD is read with the ODRL context bundled beside
the mapping scheme, and no other remote context is fetched.

The mapping writes into several configurations, as the studio sorts subjects by namespace, so the job returns one
artefact for each part it adds to: the proposals for review, their conditions for eligibility, their roles for the
baseline, the concepts they name for vocabulary, and, when no clause was picked, a form for the library with one clause
for each term."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SH, SKOS, XSD

from .config_studio_jobs import CST, _Result, catalogue
from .config_studio_proposers import FND, INS, INS_VOC, PTY, VOC, WRD

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
ELG_NS = "https://www.nebularis.org/neuro-semantic/lattice/eligibility#"
ELG = Namespace(ELG_NS)
WRD_VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#")
OM = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio/odrl-mapping#")
SCHEME = OM.Scheme
PROFILE = URIRef("http://www.w3.org/ns/odrl/2/")
CONTEXTS = ("http://www.w3.org/ns/odrl.jsonld", "https://www.w3.org/ns/odrl.jsonld")
MEDIA = {"application/ld+json": "json-ld", "text/turtle": "turtle", "application/n-triples": "nt"}


def _folder() -> Path:
    cat = catalogue()
    return cat.root / cat.area("contracts") / "config-studio" / "odrl"


def read_policy(content: str, media_type: str, profile: Optional[URIRef]) -> Graph:
    """The policy as RDF, from what it says it is. Refused when it does not say it is ODRL 2.2, when its media type is
    not one the job reads, or when a JSON-LD context other than ODRL's own would have to be fetched."""
    if profile != PROFILE:
        raise ValueError(f"the document conforms to {profile or 'no profile'}, not ODRL 2.2 ({PROFILE})")
    fmt = MEDIA.get(media_type.split(";", 1)[0].strip())
    if fmt is None:
        raise ValueError(f"an ODRL policy is read as {', '.join(MEDIA)}, not {media_type}")
    if fmt != "json-ld":
        return Graph().parse(data=content, format=fmt)
    document = json.loads(content)
    bundled = json.loads((_folder() / "odrl.jsonld").read_text(encoding="utf-8"))["@context"]

    def local(context):
        if isinstance(context, str):
            if context not in CONTEXTS:
                raise ValueError(f"the policy names the remote context {context}, and only ODRL's own is read, from the bundled copy")
            return bundled
        if isinstance(context, list):
            return [local(c) for c in context]
        return context

    def walk(node):
        if isinstance(node, dict):
            return {k: (local(v) if k == "@context" else walk(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(n) for n in node]
        return node

    return Graph().parse(data=json.dumps(walk(document)), format="json-ld")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _label(world: Graph, node) -> str:
    for p in (RDFS.label, SKOS.prefLabel):
        value = world.value(node, p)
        if value is not None:
            return str(value)
    text = str(node)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text


def _sentence(meaning: Graph, world: Graph, relation) -> str:
    """The rule in plain words, for the evidence and for a generated clause."""
    def party(p):
        node = meaning.value(relation, p)
        return _label(world, node) if node is not None else "a party"
    act = meaning.value(relation, INS.activity)
    act = _label(world, act).lower() if act is not None else "act"
    kinds = set(meaning.objects(relation, RDF.type))
    if INS.Permission in kinds:
        return f"{party(INS.holder)} may {act}, as {party(INS.counterparty)} permits."
    if INS.Prohibition in kinds:
        return f"{party(INS.obligor)} shall not {act}, as owed to {party(INS.obligee)}."
    if meaning.value(relation, INS.arisesOnBreachOf) is not None:
        return f"On a breach, {party(INS.obligor)} shall {act} for {party(INS.obligee)}."
    return f"{party(INS.obligor)} shall {act} for {party(INS.obligee)}."


def _by_namespace(graph: Graph, namespace: str) -> Graph:
    out = Graph()
    for s in {s for s, _, o in graph.triples((None, RDF.type, None)) if str(o).startswith(namespace)}:
        out += graph.triples((s, None, None))
    return out


def _closure(meaning: Graph, start, stop: set) -> Graph:
    """The ins: nodes a relation or term needs, reached from it, stopping at another term's nodes."""
    out, seen, todo = Graph(), set(), [start]
    while todo:
        node = todo.pop()
        if node in seen:
            continue
        seen.add(node)
        for s, p, o in meaning.triples((node, None, None)):
            out.add((s, p, o))
            if isinstance(o, URIRef) and o not in stop and (o, None, None) in meaning and p != RDF.type:
                todo.append(o)
    return out


def propose_odrl(job: URIRef, config: Graph, spec: Graph, document: URIRef, submitted_at: str) -> Graph:
    """The job's result: its findings, and its artefacts, one for each configuration the proposals add to."""
    from mork_rdf import compile_scheme, run

    result = _Result(job)
    at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    content, media = config.value(document, CST.documentContent), config.value(document, CST.documentMediaType)
    if content is None or media is None:
        raise ValueError("the import document carries no content or no media type")
    policy = read_policy(str(content), str(media), config.value(document, DCTERMS.conformsTo))
    picked = config.value(document, CST.importInto)

    folder = _folder()
    base = f"{job}:import/"
    vocabulary = spec + Graph().parse(folder / "odrl22.ttl")
    compiled = compile_scheme(Graph().parse(folder / "odrl-instrument.mork.ttl"), SCHEME, base=base, at=at, target_vocabulary=vocabulary)
    for f in compiled.findings:
        if f.severity.value != "info":
            result.finding(SH.Warning, f"the mapping scheme: {f.code}: {f.message}", "odrl")
    ran = run(compiled, policy)
    for f in ran.findings:
        what = {"UnmappedValue": "an ODRL operator the mapping has no condition for, so complete the condition by hand",
                "TermKind": "a value of the wrong kind, such as a literal where a concept is needed, so complete the condition by hand"}.get(f.code, f.code)
        result.finding(SH.Warning, f"{what}: {f.value}", "odrl", URIRef(f.focus) if f.focus else None)
    out = ran.graph

    meaning, eligibility, baseline = _by_namespace(out, str(INS)), _by_namespace(out, ELG_NS), _by_namespace(out, str(PTY))
    terms = sorted(meaning.subjects(RDF.type, INS.Term), key=str)
    relations = {t: sorted(meaning.subjects(INS.arisesUnder, t), key=str) for t in terms}
    owned = {r for rs in relations.values() for r in rs} | set(terms)
    world = config + policy + vocabulary + out

    # Vocabulary: the assets and actions the meaning names become concepts, and the actions a scheme bound as activities.
    vocab = Graph()
    assets, actions = URIRef(f"{base}scheme/assets"), URIRef(f"{base}scheme/actions")
    vocab.add((assets, RDF.type, VOC.ConceptScheme)); vocab.add((assets, SKOS.prefLabel, Literal("Imported ODRL assets", lang="en")))
    vocab.add((actions, RDF.type, VOC.ConceptScheme)); vocab.add((actions, SKOS.prefLabel, Literal("ODRL actions", lang="en")))
    binding = URIRef(f"{base}binding/actions")
    vocab.add((binding, RDF.type, VOC.SchemeBinding)); vocab.add((binding, VOC.forContract, INS_VOC.ActivityContract))
    vocab.add((binding, VOC.bindsScheme, actions))
    named = {o for o in eligibility.objects(None, ELG.requiredConcept) if isinstance(o, URIRef)}
    for concept in sorted(named, key=str):
        if (concept, RDF.type, SKOS.Concept) not in config:
            vocab.add((concept, RDF.type, SKOS.Concept)); vocab.add((concept, SKOS.inScheme, assets))
            vocab.add((concept, SKOS.prefLabel, Literal(_label(world, concept), lang="en")))
    used = {o for o in out.objects(None, INS.activity) if isinstance(o, URIRef)}
    for action in sorted(used, key=str):
        vocab.add((action, RDF.type, SKOS.Concept)); vocab.add((action, SKOS.inScheme, actions))
        vocab.add((action, SKOS.prefLabel, Literal(_label(vocabulary, action), lang="en")))
        for broader in vocabulary.objects(action, ODRL.includedIn):
            if broader in used:
                vocab.add((action, SKOS.broader, broader))
    vocab.add((OM.ExclusiveRights, RDF.type, SKOS.Concept))
    vocab.add((OM.ExclusiveRights, RDFS.label, Literal(_label(Graph().parse(folder / "odrl-instrument.mork.ttl"), OM.ExclusiveRights))))

    # The clause each term is proposed on: the one picked, else a generated clause of a generated form.
    library = Graph()
    form = URIRef(f"{base}form")
    clause_of: dict = {}
    if picked is None:
        library.add((form, RDF.type, WRD.Wording))
        library.add((form, RDFS.label, Literal(f"Imported ODRL policy {_label(world, next(iter(policy.subjects(RDF.type, ODRL.Agreement)), job))}")))
        library.add((form, FND.hasIdentity, URIRef(f"{form}/identity"))); library.add((form, FND.hasGovernanceState, FND.Draft))
    explicit = [t for t in terms if (t, INS.impliedBy, None) not in meaning]
    for i, term in enumerate(explicit, start=1):
        if picked is not None:
            clause_of[term] = picked
            continue
        clause = URIRef(f"{base}clause/{i}")
        library.add((form, WRD.directlyComprises, clause))
        library.add((clause, RDF.type, WRD.Text)); library.add((clause, FND.hasIdentity, URIRef(f"{clause}/identity")))
        library.add((clause, FND.hasGovernanceState, FND.Draft)); library.add((clause, WRD.elementType, WRD_VOC.Clause))
        library.add((clause, WRD.objectId, Literal(str(i)))); library.add((clause, WRD.rankKey, Literal(f"a{i:04d}")))
        library.add((clause, WRD.inclusionMode, WRD_VOC.Mandatory))
        part = URIRef(f"{clause}/part/0")
        library.add((clause, WRD.hasTextPart, part)); library.add((part, RDF.type, WRD.TextPart))
        library.add((part, WRD.partIndex, Literal(0)))
        library.add((part, WRD.partText, Literal(" ".join(_sentence(meaning, world, r) for r in relations[term]))))
        clause_of[term] = clause
    # An implied term is proposed on the clause of the permission that excepts its prohibition.
    for term in terms:
        if term in clause_of:
            continue
        excepted = set(relations[term])
        permitting = sorted({p for p in meaning.subjects(INS.excepts, None) if meaning.value(p, INS.excepts) in excepted}, key=str)
        owner = next((t for t in explicit if set(relations[t]) & set(permitting)), None)
        if owner is not None:
            clause_of[term] = clause_of[owner]

    # The proposals, one for each term, carrying the term and every relation and trigger under it.
    review = Graph()
    review.bind("cst", CST)
    stamp = Literal(at.isoformat(), datatype=XSD.dateTime)
    n = 0
    for term in terms:
        if term not in clause_of:
            result.finding(SH.Warning, "an implied term has no permission's clause to be proposed on", "odrl", term)
            continue
        n += 1
        payload = Graph()
        payload.bind("ins", INS)
        for node in [term] + relations[term]:
            payload += _closure(meaning, node, owned - {node})
        if (term, INS.impliedBy, None) not in meaning:
            payload.add((term, INS.expressedIn, clause_of[term]))
        proposal = URIRef(f"{job}:proposal/{n}")
        review.add((proposal, RDF.type, CST.Proposal))
        review.add((proposal, CST.span, clause_of[term]))
        for node in [term] + relations[term]:
            review.add((proposal, CST.proposes, node))
        review.add((proposal, CST.proposer, Literal("odrl")))
        review.add((proposal, CST.proposerVersion, Literal(f"odrl {compiled.compiler}, mapping sha256:{compiled.mapping_digest[:16]}")))
        review.add((proposal, CST.proposedAt, stamp))
        evidence = " ".join(_sentence(meaning, world, r) for r in relations[term])
        if (term, INS.impliedBy, None) in meaning:
            evidence = f"Implied by law and excepted by the permission: {evidence}"
        review.add((proposal, CST.evidence, Literal(evidence)))
        review.add((proposal, CST.payload, Literal(payload.serialize(format="turtle"))))

    for path, graph, group in (("review.ttl", review, "review"), ("eligibility.ttl", eligibility, "eligibility"),
                               ("baseline.ttl", baseline, "baseline"), ("vocabulary.ttl", vocab, "vocabulary"),
                               ("library.ttl", library, "library")):
        if len(graph):
            result.artefact(path, "text/turtle", graph.serialize(format="turtle"), group)
    result.finding(SH.Info, f"{n} proposal(s) from {len(terms)} rule term(s) of the policy", "odrl")
    result.conforms(True)
    return result.graph
