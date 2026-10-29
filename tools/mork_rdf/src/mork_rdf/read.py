# SPDX-License-Identifier: MPL-2.0
"""Reads a MORK mapping scheme into one `Spec` per mapping node, the labelling of README §5: what each node targets,
where its values come from, and where it sits in the DAG. Templates are merged here (§8), and time, supersession,
uncertainty and confidence are applied here (§9), so the compiler sees only the mappings in force."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from .model import FND, MORK, SH, Finding, Severity
from . import paths


class Kind(Enum):
    DATUM = "datum"                    # individuates one target node per focus node (Case 2)
    CONTEXTUAL = "contextual"          # a datum in its parent's context, glued to the parent (Case 4)
    ASSERTION = "assertion"            # a property on its parent's target node (Case 3)
    LOOKUP = "lookup"                  # a property whose value is found in reference data (Case 6)
    CORRESPONDENCE = "correspondence"  # one source individual to one target individual, a row of its parent's table
    CLASS_REFERENCE = "class"          # names an existing class, and writes nothing (Case 1b)
    CLASS_CREATION = "new-class"       # a new class beneath a broader one (Case 1a)


@dataclass(frozen=True)
class Strata:
    """The node's matches in each stratum, from the specific properties or inferred from the generic ones."""

    tbox: dict = field(default_factory=dict)  # "exact" | "broad" | "narrow" -> IRI
    rbox: dict = field(default_factory=dict)  # "exact" | "inverse" | "broad" | "narrow" -> IRI
    abox: dict = field(default_factory=dict)  # "exact" | "broad" | "narrow" -> IRI


@dataclass(frozen=True)
class Spec:
    node: URIRef
    kind: Kind
    strata: Strata
    parent: Optional[URIRef] = None
    children: tuple[URIRef, ...] = ()
    sources: tuple[URIRef, ...] = ()        # source classes a root iterates, or the source individual of a correspondence
    data_ref: Optional[paths.Path] = None   # a path from the focus node
    data_ref_text: Optional[str] = None
    data_inline: Optional[Literal] = None
    concept_name: Optional[str] = None
    name_template: Optional[str] = None
    individual_iri: Optional[URIRef] = None
    identity: Optional[URIRef] = None       # a mork:TemplateExpression node
    deferred: Optional[URIRef] = None
    lookup_path: Optional[URIRef] = None    # mork:referenceDataPath, the predicate a Lookup matches on
    weighting: Optional[int] = None
    template: Optional[URIRef] = None       # the template this node instantiates, already merged in


@dataclass
class Reading:
    scheme: URIRef
    mode: str
    prefixes: dict
    specs: dict          # node -> Spec, the mappings in force
    findings: list
    templates: set       # nodes that are only templates, compiled through their instantiations


_TBOX = {"exact": MORK.exactTBoxMatch, "broad": MORK.broadTBoxCategoryMatch, "narrow": MORK.narrowTBoxCategoryMatch}
_RBOX = {"exact": MORK.exactRBoxMatch, "inverse": MORK.inverseRBoxMatch, "broad": MORK.broadRBoxCategoryMatch, "narrow": MORK.narrowRBoxCategoryMatch}
_ABOX = {"exact": MORK.exactABoxMatch, "broad": MORK.broadABoxCategoryMatch, "narrow": MORK.narrowABoxCategoryMatch}
_GENERIC = {"exact": MORK.intransitiveExactMatch, "broad": MORK.broadCategoryMatch, "narrow": MORK.narrowCategoryMatch}
_POSSIBLE = (MORK.possibleMatch, MORK.lexicalMatch, MORK.semanticMatch, MORK.structuralMatch, MORK.partialMatch,
             MORK.pathMatch, MORK.missingOrUnrelatedMatch, MORK.digraphMatch)
_PLACEHOLDER = (MORK.placeholderMapping, MORK.concatenation, MORK.interpolationComponent)
# Properties that change what a mapping writes, which this backend does not compile (README §10.2).
_UNSUPPORTED = (MORK.referenceDataMapping, MORK.propertyMappingAssertions, MORK.assertsPropertyDomains, MORK.assertsPropertyRanges,
                MORK.egressProjection)
_GENERATIVE = (MORK.GenerativeMapping, MORK.ShapeMapping, MORK.RuleMapping, MORK.TransformMapping, MORK.ProjectionMapping)
_MAPPING_TYPES = (MORK.DataMapping, MORK.Datum, MORK.Lookup, MORK.IndexedMapping, MORK.WeightedMatch, MORK.UncertainMapping,
                  MORK.Hypothesis, MORK.DeferredContext) + _GENERATIVE
_MODES = {MORK.DraftMode: "draft", MORK.ReviewMode: "review", MORK.ProductionMode: "production"}


def _one(g: Graph, s, p) -> Optional[object]:
    values = sorted(g.objects(s, p), key=str)
    return values[0] if values else None


def _iri(g: Graph, s, p) -> Optional[URIRef]:
    value = _one(g, s, p)
    return value if isinstance(value, URIRef) else None


def _text(g: Graph, s, p) -> Optional[str]:
    value = _one(g, s, p)
    return str(value) if isinstance(value, Literal) else None


def prefixes(g: Graph, scheme: URIRef) -> dict:
    """The prefixes a scheme declares with SHACL's vocabulary, on itself or on the nodes `sh:prefixes` names."""
    out = {}
    holders = [scheme] + sorted(o for o in g.objects(scheme, SH.prefixes) if isinstance(o, URIRef))
    for holder in holders:
        for declaration in g.objects(holder, SH.declare):
            prefix, namespace = _text(g, declaration, SH.prefix), _one(g, declaration, SH.namespace)
            if prefix is not None and namespace is not None:
                out[prefix] = str(namespace)
    return out


def _effective(g: Graph, node, at: datetime) -> bool:
    start, end = _one(g, node, MORK.effectiveFrom), _one(g, node, MORK.effectiveUntil)
    if isinstance(start, Literal) and start.toPython() > at:
        return False
    if isinstance(end, Literal) and end.toPython() <= at:
        return False
    return True


def _kind_of(target_vocabulary: Graph, term: URIRef) -> Optional[str]:
    """The stratum a generic match targets, from the target vocabulary's typing of the term."""
    types = set(target_vocabulary.objects(term, RDF.type))
    if types & {OWL.Class, RDFS.Class}:
        return "tbox"
    if types & {OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property}:
        return "rbox"
    if types:
        return "abox"
    return None


def _strata(g: Graph, node, target_vocabulary: Graph, findings: list) -> Strata:
    tbox = {k: v for k, p in _TBOX.items() if (v := _iri(g, node, p)) is not None}
    rbox = {k: v for k, p in _RBOX.items() if (v := _iri(g, node, p)) is not None}
    abox = {k: v for k, p in _ABOX.items() if (v := _iri(g, node, p)) is not None}
    for degree, prop in _GENERIC.items():
        term = _iri(g, node, prop)
        if term is None:
            continue
        stratum = _kind_of(target_vocabulary, term)
        box = {"tbox": tbox, "rbox": rbox, "abox": abox}.get(stratum)
        if box is None:
            findings.append(Finding("StratumUnknown", str(node), f"{prop.n3()} targets {term.n3()}, which the target vocabulary does not type, so its stratum is unknown"))
        else:
            box.setdefault(degree, term)
    return Strata(tbox, rbox, abox)


def _mapping_nodes(g: Graph, scheme: URIRef) -> list[URIRef]:
    nodes = {s for s in g.subjects(MORK.mappingScheme, scheme) if isinstance(s, URIRef)}
    return sorted(nodes, key=str)


def _sources(g: Graph, node) -> tuple[URIRef, ...]:
    """The source terms a node is for: each `mork:mappingFor` concept's `mork:representedAs` representations, or the
    concept itself when it represents nothing else (an individual of the source vocabulary)."""
    out = set()
    for concept in g.objects(node, MORK.mappingFor):
        represented = [r for r in g.objects(concept, MORK.representedAs) if isinstance(r, URIRef)]
        represented += [r for r in g.subjects(MORK.representationOf, concept) if isinstance(r, URIRef)]
        if represented:
            out.update(represented)
        elif isinstance(concept, URIRef):
            out.add(concept)
    return tuple(sorted(out, key=str))


def _identity(g: Graph, node) -> Optional[URIRef]:
    """The template expression that forms a node's identity: the target of `mork:identityTemplateMapping`, or the node
    that `mork:resolvesIdentityFor` it, when that is a template expression."""
    candidates = list(g.objects(node, MORK.identityTemplateMapping)) + list(g.subjects(MORK.resolvesIdentityFor, node))
    for candidate in sorted(candidates, key=str):
        if any((candidate, RDF.type, t) in g for t in (MORK.TemplateExpression, MORK.ConcatExpression, MORK.InterpolationExpression,
                                                       MORK.LiteralExpression, MORK.RefExpression, MORK.LookupExpression)):
            return candidate
    return None


def read(g: Graph, scheme: URIRef, at: datetime, target_vocabulary: Optional[Graph] = None, min_confidence: Optional[float] = None) -> Reading:
    target_vocabulary = target_vocabulary if target_vocabulary is not None else Graph()
    findings: list[Finding] = []
    mode = _MODES.get(_iri(g, scheme, MORK.compilationMode), "draft")
    declared = prefixes(g, scheme)
    nodes = _mapping_nodes(g, scheme)
    if not nodes:
        findings.append(Finding("EmptyScheme", str(scheme), "the scheme holds no mapping node (none names it with mork:mappingScheme)"))

    # --- what is in force at `at` (§9.1) ---------------------------------------------------------------------------
    superseded = set()
    for node in nodes:
        for older in list(g.objects(node, MORK.supersedes)) + list(g.subjects(FND.supersededBy, node)):
            if _effective(g, node, at):
                superseded.add(older)
    in_force = []
    for node in nodes:
        if not _effective(g, node, at):
            findings.append(Finding("NotInForce", str(node), f"not in force at {at.isoformat()}", Severity.INFO))
        elif node in superseded:
            findings.append(Finding("Superseded", str(node), "superseded by a mapping in force", Severity.INFO))
        else:
            in_force.append(node)

    # --- excluded outright (§10) -----------------------------------------------------------------------------------
    candidates = []
    for node in in_force:
        if any((node, RDF.type, t) in g for t in _GENERATIVE):
            findings.append(Finding("OtherBackend", str(node), "a generative mapping, compiled by the SHACL, SWRL, projection or RML backend", Severity.INFO))
        elif (node, RDF.type, MORK.UncertainMapping) in g or _one(g, node, MORK.incompleteMapping) == Literal(True):
            findings.append(Finding("Uncertain", str(node), "an uncertain or incomplete mapping is a question for review, never compiled"))
        elif any(_one(g, node, p) is not None for p in _PLACEHOLDER):
            findings.append(Finding("PlaceholderForm", str(node), "the placeholder forms predate template expressions. Write the value as a mork:TemplateExpression"))
        elif (unsupported := next((p for p in _UNSUPPORTED if _one(g, node, p) is not None), None)) is not None:
            findings.append(Finding("NotCompiled", str(node), f"{unsupported.n3()} changes what the mapping writes, and this backend does not compile it"))
        elif any((node, RDF.type, t) in g for t in (MORK.Hypothesis, MORK.WeightedMatch)) and not any(
            _one(g, node, p) is not None for p in list(_TBOX.values()) + list(_RBOX.values()) + list(_ABOX.values())
        ):
            findings.append(Finding("Evidence", str(node), "a hypothesis or weighted match is evidence for review, and writes nothing", Severity.INFO))
        else:
            candidates.append(node)

    # --- the DAG's parent edges (§5.2) -----------------------------------------------------------------------------
    present = set(candidates)
    parents: dict[URIRef, set] = {n: set() for n in candidates}
    for node in candidates:
        for child in g.objects(node, MORK.compositeNarrowerMapping):
            if child in present:
                parents[child].add(node)
        for parent in list(g.objects(node, MORK.compositeBroaderMapping)) + list(g.objects(node, MORK.broaderApplicative)):
            if parent in present:
                parents[node].add(parent)
    templates = {t for n in candidates for t in g.objects(n, MORK.templateMapping) if t in present}
    template_children = {c for c, ps in parents.items() if ps & templates}

    specs: dict[URIRef, Spec] = {}
    for node in candidates:
        if len(parents[node]) > 1:
            findings.append(Finding("SeveralParents", str(node), "names more than one parent mapping: " + ", ".join(sorted(str(p) for p in parents[node]))))
            continue
        data_ref_text = _text(g, node, MORK.dataRef)
        try:
            data_ref = paths.parse(data_ref_text, declared) if data_ref_text is not None else None
        except paths.PathError as error:
            findings.append(Finding("BadPath", str(node), str(error)))
            continue
        weighting = _one(g, node, MORK.weighting)
        specs[node] = Spec(
            node=node,
            kind=Kind.DATUM,  # classified below, once templates are merged
            strata=_strata(g, node, target_vocabulary, findings),
            parent=next(iter(parents[node]), None),
            children=tuple(sorted((c for c in candidates if node in parents[c]), key=str)),
            sources=_sources(g, node),
            data_ref=data_ref,
            data_ref_text=data_ref_text,
            data_inline=_one(g, node, MORK.dataInline) if isinstance(_one(g, node, MORK.dataInline), Literal) else None,
            concept_name=_text(g, node, MORK.conceptName),
            name_template=_text(g, node, MORK.conceptFQNameTemplate) or _text(g, node, MORK.conceptNameTemplate),
            individual_iri=URIRef(v) if (v := _text(g, node, MORK.individualIRI)) else None,
            identity=_identity(g, node),
            deferred=_iri(g, node, MORK.deferredMapping),
            lookup_path=_iri(g, node, MORK.referenceDataPath),
            weighting=int(weighting) if isinstance(weighting, Literal) else None,
            template=_iri(g, node, MORK.templateMapping),
        )

    # --- templates (§8) ----------------------------------------------------------------------------------------------
    for node, spec in list(specs.items()):
        if spec.template is not None and spec.template in specs:
            specs[node] = _merge(g, spec, specs[spec.template], specs)

    # --- classification (§5.1) ---------------------------------------------------------------------------------------
    abstract = {t for t in templates if t in specs and not specs[t].sources and specs[t].parent is None}
    for node in list(specs):
        spec = specs[node]
        if node in abstract:
            continue  # a template is classified only as part of each instantiation it is merged into
        kind, finding = _classify(g, spec, specs)
        if finding is not None:
            findings.append(finding)
            del specs[node]
        else:
            specs[node] = replace(spec, kind=kind)

    # --- confidence (§9.4) -------------------------------------------------------------------------------------------
    if min_confidence is not None:
        for node, value in effective_confidence(specs).items():
            if value < min_confidence and node in specs:
                findings.append(Finding("BelowConfidence", str(node), f"effective confidence {value:.2f} is below {min_confidence:.2f}"))
                del specs[node]

    # A child of a removed node is unreachable.
    changed = True
    while changed:
        changed = False
        for node, spec in list(specs.items()):
            if spec.parent is not None and spec.parent not in specs:
                findings.append(Finding("ParentNotCompiled", str(node), f"its parent {spec.parent.n3()} is not compiled", Severity.WARNING))
                del specs[node]
                changed = True

    return Reading(scheme, mode, declared, specs, findings, abstract | {c for c in template_children if c in specs})


def _merge(g: Graph, instance: Spec, template: Spec, specs: dict) -> Spec:
    """An instantiation's own values first, the template's where it gives none (Definition 3.7). Its children are its
    own, then the template's children that no own child correlates with through `mork:templateBinding`."""
    def pick(a, b):
        return a if a not in (None, (), {}) else b

    bound = {t for c in instance.children for t in g.objects(c, MORK.templateBinding)}
    children = tuple(sorted(set(instance.children) | {c for c in template.children if c not in bound}, key=str))
    strata = Strata(
        {**template.strata.tbox, **instance.strata.tbox},
        {**template.strata.rbox, **instance.strata.rbox},
        {**template.strata.abox, **instance.strata.abox},
    )
    return replace(
        instance,
        strata=strata,
        children=children,
        sources=pick(instance.sources, template.sources),
        data_ref=pick(instance.data_ref, template.data_ref),
        data_ref_text=pick(instance.data_ref_text, template.data_ref_text),
        data_inline=pick(instance.data_inline, template.data_inline),
        concept_name=pick(instance.concept_name, template.concept_name),
        name_template=pick(instance.name_template, template.name_template),
        individual_iri=pick(instance.individual_iri, template.individual_iri),
        identity=pick(instance.identity, template.identity),
        deferred=pick(instance.deferred, template.deferred),
        lookup_path=pick(instance.lookup_path, template.lookup_path),
        weighting=pick(instance.weighting, template.weighting),
    )


def _classify(g: Graph, spec: Spec, specs: dict) -> tuple[Kind, Optional[Finding]]:
    """The node's role, from Definition 10.7's case analysis in the order `mork2rml` uses, so both backends read a
    graph alike. A node that fits no case is an error, never a guess."""
    node, s = str(spec.node), spec.strata
    for box, name in ((s.tbox, "T-Box"), (s.rbox, "R-Box"), (s.abox, "A-Box")):
        if "narrow" in box:
            return Kind.DATUM, Finding("NarrowMatch", node, f"a narrow {name} match says the target is narrower than the source, so a compiled mapping would claim more than the source says")
    has_value = spec.data_ref is not None or spec.data_inline is not None or "exact" in s.abox or "broad" in s.abox
    rbox = s.rbox.get("exact") or s.rbox.get("inverse") or s.rbox.get("broad")
    if (spec.node, RDF.type, MORK.Lookup) in g or spec.lookup_path is not None:
        if rbox is None or spec.lookup_path is None or "exact" not in s.tbox or spec.data_ref is None:
            return Kind.LOOKUP, Finding("LookupIncomplete", node, "a lookup needs an R-Box match, mork:referenceDataPath, the reference class as mork:exactTBoxMatch and mork:dataRef")
        return Kind.LOOKUP, None
    applicative = _iri(g, spec.node, MORK.broaderApplicative)
    if applicative is not None or (spec.deferred is not None and spec.parent is not None and rbox is not None and not has_value):
        if rbox is None:
            return Kind.CONTEXTUAL, Finding("NoGluingProperty", node, "a contextual mapping names the property that joins it to its parent with an R-Box match")
        return Kind.CONTEXTUAL, None
    if spec.deferred is not None or (spec.node, RDF.type, MORK.Datum) in g:
        return Kind.DATUM, None
    if "broad" in s.tbox:
        return Kind.CLASS_CREATION, None
    if "exact" in s.tbox and rbox is None:
        return Kind.CLASS_REFERENCE, None
    if rbox is not None:
        if spec.parent is None:
            return Kind.ASSERTION, Finding("NoParent", node, "a property assertion is made on its parent's target node, and this mapping has no parent")
        if not has_value and not any(specs[c].strata.abox for c in spec.children if c in specs):
            return Kind.ASSERTION, Finding("NoValue", node, "a property assertion takes its value from mork:dataRef, mork:dataInline, an A-Box match or correspondences beneath it")
        return Kind.ASSERTION, None
    parent = specs.get(spec.parent) if spec.parent is not None else None
    if s.abox and parent is not None and parent.strata.rbox:
        if not spec.sources:
            return Kind.CORRESPONDENCE, Finding("CorrespondenceSource", node, "a correspondence names the source individual it is for with mork:mappingFor")
        return Kind.CORRESPONDENCE, None
    if s.abox:
        return Kind.CORRESPONDENCE, Finding("CorrespondenceUnused", node, "a correspondence is a row of its parent assertion's table, and this one has no parent", Severity.WARNING)
    return Kind.DATUM, Finding("Unclassified", node, "matches no case of the compiler: no T-Box, R-Box or A-Box match, and no datum")


def effective_confidence(specs: dict) -> dict:
    """MORK's rule: a node's local confidence times the least of its children's, a node with no weighting counting as
    certain (README §9.4). Values are 0 to 1."""
    out: dict = {}

    def of(node, seen=()):
        if node in out:
            return out[node]
        spec = specs[node]
        local = (spec.weighting / 100) if spec.weighting is not None else 1.0
        kids = [of(c, seen + (node,)) for c in spec.children if c in specs and c not in seen]
        out[node] = local * (min(kids) if kids else 1.0)
        return out[node]

    for node in sorted(specs, key=str):
        of(node)
    return out


def class_of(g: Graph, spec: Spec, specs: dict) -> Optional[URIRef]:
    """The class a datum's target nodes are typed with: its own exact T-Box match, else that of the mapping it defers
    to, resolving a `mork:DeferredContext` through the mapping that yields it."""
    if "exact" in spec.strata.tbox:
        return spec.strata.tbox["exact"]
    target = spec.deferred
    if target is not None and (target, RDF.type, MORK.DeferredContext) in g:
        target = next((s for s in g.subjects(MORK.yieldConcept, target) if s in specs), target)
    if target is not None and target in specs:
        deferred = specs[target]
        if deferred.kind is Kind.CLASS_CREATION:
            return URIRef("urn:mork-rdf:created")  # resolved to the created class by the compiler
        return deferred.strata.tbox.get("exact") or deferred.strata.tbox.get("broad")
    return None


def iter_roots(specs: dict) -> Iterable[Spec]:
    return (specs[n] for n in sorted(specs, key=str) if specs[n].parent is None)
