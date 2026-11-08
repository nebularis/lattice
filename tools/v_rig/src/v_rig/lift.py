# SPDX-License-Identifier: MPL-2.0
"""Lifting a rig to the intermediate representation. Front matter, programme files and the events file become facts of
carriers in the declared view. A document's body, and each rendering of it, become body nodes in the blind view or the
rendering's view. Every node is located and digested by the rules of canon.py. The lifter interprets nothing: a key is a
fact with its key as a string, a token is a literal, and what a formula or a reference means is left to a mapping."""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from . import canon
from .markdown import Node, parse, references
from .rig import Document, Rig

log = logging.getLogger("v_rig")

VRIG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/v-rig#")
PREFIXES = {"vrig": VRIG, "xsd": XSD}

# A value that reads as an expression over names: a number or a name, an operator, and a name somewhere.
_FORMULA = re.compile(r"^\s*(?:[\d.,]+%?|[A-Za-z_]\w*)\s*(?:[x×*/+\-]|of|times|percent of)\s+.*[A-Za-z_]\w*", re.IGNORECASE)
_IDENTIFIER = re.compile(r"\b(?![xX]\b)[A-Za-z_]\w*\b")
_FORMULA_WORDS = {"of", "times", "percent", "and", "the"}

# The kind a reference names, to the kind of body node that answers it.
_TARGET_KINDS = {"section": ("section",), "item": ("row",), "condition": ("clause",), "clause": ("clause",),
                 "endorsement": ("endorsement",), "schedule": ("schedule", "section"), "part": ("part", "section"),
                 "annex": ("annex", "section")}
_TOWARDS_OTHER_DOCUMENT = ("underlying", "follows_form_of")


@dataclass(frozen=True)
class RunInfo:
    checkout_commit: str
    substrate_release: str
    vocabulary_version: str
    vector_schema_version: str | None = None


def _literal(value) -> Literal:
    if isinstance(value, bool):
        return Literal(value)
    if isinstance(value, int):
        return Literal(value)
    if isinstance(value, float):
        return Literal(Decimal(str(value)))
    if isinstance(value, dt.datetime):
        return Literal(value)
    if isinstance(value, dt.date):
        return Literal(value)
    return Literal(str(value))


class Lifter:
    def __init__(self, rig: Rig, run: RunInfo):
        self.rig = rig
        self.run = run
        self.graph = Graph()
        for prefix, namespace in PREFIXES.items():
            self.graph.bind(prefix, namespace)
        self.run_node = URIRef(canon.run_iri(rig.digest))
        self.documents: dict[str, URIRef] = {}
        self.programmes: dict[str, URIRef] = {}
        self.forms: dict[str, list[URIRef]] = {}
        self.body_index: dict[tuple[str, str, str, str], URIRef] = {}  # (doc, view, kind, number) -> node
        self.facts: list[tuple[URIRef, str, list]] = []  # fact node, its document id, its string values
        self.unresolved: list[tuple[URIRef, URIRef, str]] = []  # reference, its locator, document id
        self.prose_only: list[tuple[URIRef, URIRef, str]] = []

    # ---- locators -----------------------------------------------------------------

    def locate(self, document_id: str, view: str, *, section=None, clause=None, row=None, key_path=None,
               line: int | None = None, view_node: URIRef | None = None) -> tuple[URIRef, URIRef]:
        string = canon.locator_string(document_id, view, section=section, clause=clause, row=row, key_path=key_path)
        node, locator = URIRef(canon.node_iri(string)), URIRef(canon.locator_iri(string))
        g = self.graph
        g.add((locator, RDF.type, VRIG.Locator))
        g.add((locator, VRIG.documentId, Literal(document_id)))
        g.add((locator, VRIG.view, view_node or (VRIG.Declared if view == "declared" else VRIG.Blind)))
        for predicate, value in ((VRIG.section, section), (VRIG.clause, clause), (VRIG.row, row), (VRIG.keyPath, key_path)):
            if value is not None:
                g.add((locator, predicate, Literal(str(value))))
        if line is not None:
            g.add((locator, VRIG.line, Literal(line)))
        g.add((node, VRIG.locator, locator))
        return node, locator

    # ---- facts --------------------------------------------------------------------

    def fact(self, carrier: URIRef, document_id: str, key: str, value, key_path: str, *, unknown: bool = False) -> URIRef:
        node, _ = self.locate(document_id, "declared", key_path=key_path)
        g = self.graph
        g.add((node, RDF.type, VRIG.Fact))
        g.add((node, VRIG.of, carrier))
        g.add((node, VRIG.key, Literal(key)))
        strings: list[str] = []
        if unknown:
            g.add((node, VRIG.unknown, Literal(True)))
            g.add((node, VRIG.digest, Literal(canon.fact_digest(key, unknown=True))))
        elif value is None or value == [] or value == {}:
            g.add((node, VRIG.empty, Literal(True)))
            g.add((node, VRIG.digest, Literal(canon.fact_digest(key, empty=True))))
        else:
            g.add((node, VRIG.digest, Literal(canon.fact_digest(key, value))))
            items = value if isinstance(value, list) else [value]
            for index, item in enumerate(items):
                if isinstance(item, dict):
                    record, _ = self.locate(document_id, "declared", key_path=f"{key_path}[{index}]")
                    g.add((record, RDF.type, VRIG.Record))
                    g.add((record, VRIG["index"], Literal(index)))
                    g.add((record, VRIG.digest, Literal(canon.mapping_digest(item))))
                    g.add((node, VRIG.item, record))
                    for sub_key, sub_value in item.items():
                        self.fact(record, document_id, str(sub_key), sub_value, f"{key_path}[{index}].{sub_key}")
                else:
                    g.add((node, VRIG.value, _literal(item)))
                    if isinstance(item, str):
                        strings.append(item)
            if isinstance(value, str) and _FORMULA.match(value):
                g.add((node, RDF.type, VRIG.Formula))
                g.add((node, VRIG.expression, Literal(value)))
                for name in sorted({m.group(0) for m in _IDENTIFIER.finditer(value)} - _FORMULA_WORDS):
                    g.add((node, VRIG.input, Literal(name)))
        self.facts.append((node, document_id, strings))
        return node

    def facts_of(self, carrier: URIRef, document_id: str, mapping: dict, prefix: str, skip: tuple[str, ...]) -> None:
        for key, value in mapping.items():
            if key in skip:
                continue
            self.fact(carrier, document_id, str(key), value, f"{prefix}{key}")

    # ---- documents ----------------------------------------------------------------

    def document(self, document: Document) -> None:
        g = self.graph
        node, _ = self.locate(document.id, "declared")
        g.add((node, RDF.type, VRIG.Document))
        g.add((node, VRIG.rigId, Literal(document.id)))
        g.add((node, VRIG.formatVersion, Literal(self.rig.format_version)))
        g.add((node, VRIG.digest, Literal(self.rig.file_digests[document.path])))
        self.documents[document.id] = node
        form = document.front.get("form")
        if isinstance(form, str):
            self.forms.setdefault(form, []).append(node)
        self.facts_of(node, document.id, document.front, "", ("id",))
        self.body(document, node, document.body, "blind", None, document.body_line)
        for rendering in document.renderings:
            view = URIRef(canon.view_iri(document.id, rendering.name))
            g.add((view, RDF.type, VRIG.RenderingView))
            g.add((view, VRIG.renderingName, Literal(rendering.name)))
            g.add((node, VRIG.rendered, view))
            self.body(document, node, rendering.text, canon.view_name("rendering", rendering.name), view, 1)

    def body(self, document: Document, root: URIRef, text: str, view: str, view_node: URIRef | None, first_line: int) -> None:
        nodes = parse(text, first_line)
        count = self._children(document.id, root, nodes, view, view_node, section=None, clause=None, row_prefix="")
        log.info("lifted %d body node(s) of %s in view %s", count, document.id, view)

    def _children(self, document_id: str, parent: URIRef, nodes: list[Node], view: str, view_node, *,
                  section, clause, row_prefix: str) -> int:
        count = 0
        for ordinal, node in enumerate(nodes):
            sec, cl, row = section, clause, None
            if node.kind in ("section", "subsection", "endorsement", "schedule", "part", "annex", "appendix", "title"):
                label = node.number if node.number is not None else (node.title or node.kind)
                if node.kind in ("section", "title") or section is None:
                    sec, cl = label if node.kind != "title" else None, None
                    row = f"{row_prefix}{ordinal}" if node.kind == "title" else None
                else:
                    cl = f"{node.kind} {label}"
                child_prefix = ""
            elif node.kind == "clause":
                cl = node.number
                child_prefix = ""
            else:
                row = f"{row_prefix}{ordinal}"
                child_prefix = f"{row}."
            iri, locator = self.locate(document_id, view, section=sec, clause=cl, row=row, line=node.line, view_node=view_node)
            g = self.graph
            g.add((iri, RDF.type, VRIG.BodyNode))
            g.add((iri, VRIG.kind, Literal(node.kind)))
            g.add((iri, VRIG.parent, parent))
            g.add((iri, VRIG.ordinal, Literal(ordinal)))
            pieces = [p for p in (node.number, node.title, node.text) if p]
            g.add((iri, VRIG.digest, Literal(canon.sha256_hex(canon.normalise_text(" ".join(pieces))))))
            if node.number is not None:
                g.add((iri, VRIG.number, Literal(node.number)))
                self.body_index.setdefault((document_id, view, node.kind, node.number), iri)
            if node.title:
                g.add((iri, VRIG["title"], Literal(canon.normalise_text(node.title))))
            if node.text:
                g.add((iri, VRIG.text, Literal(canon.normalise_text(node.text))))
            if node.kind == "definition" and node.term:
                g.add((iri, RDF.type, VRIG.DefinedTerm))
                g.add((iri, VRIG["term"], Literal(canon.normalise_text(node.term))))
                g.add((iri, VRIG.scopedTo, self.documents[document_id]))
            if node.kind == "paragraph":
                g.add((iri, RDF.type, VRIG.ProseOnly))
                self.prose_only.append((iri, locator, document_id))
            for index, (written, kind, number, external) in enumerate(references(node.text or "")):
                ref, ref_locator = self.locate(document_id, view, section=sec, clause=cl,
                                               row=f"{row or ''}{'.' if row else ''}ref{index}", view_node=view_node)
                g.add((ref, RDF.type, VRIG.Reference))
                g.add((ref, VRIG.inNode, iri))
                g.add((ref, VRIG.referenceText, Literal(written)))
                g.add((ref, VRIG.targetKind, Literal(kind)))
                g.add((ref, VRIG.targetNumber, Literal(number)))
                g.add((ref, VRIG.external, Literal(external)))
                g.add((ref, VRIG.digest, Literal(canon.sha256_hex(canon.normalise_text(written)))))
                self.unresolved.append((ref, ref_locator, document_id))
            count += 1 + self._children(document_id, iri, node.children, view, view_node, section=sec, clause=cl,
                                        row_prefix=child_prefix)
        return count

    # ---- programmes and events ----------------------------------------------------

    def programme(self, programme) -> None:
        g = self.graph
        node, _ = self.locate(programme.id, "declared")
        g.add((node, RDF.type, VRIG.Programme))
        g.add((node, VRIG.rigId, Literal(programme.id)))
        g.add((node, VRIG.digest, Literal(canon.mapping_digest(programme.mapping))))
        self.programmes[programme.id] = node
        self.facts_of(node, programme.id, programme.mapping, "", ("id", "layers", "policies"))
        for index, layer in enumerate(programme.mapping.get("layers") or []):
            if not isinstance(layer, dict):
                self.fact(node, programme.id, "layers", layer, f"layers[{index}]")
                continue
            layer_node, _ = self.locate(programme.id, "declared", key_path=f"layers[{index}]")
            g.add((layer_node, RDF.type, VRIG.Layer))
            g.add((layer_node, VRIG.inProgramme, node))
            g.add((layer_node, VRIG["index"], Literal(index)))
            g.add((layer_node, VRIG.layerNumber, Literal(int(layer.get("layer", index + 1)))))
            g.add((layer_node, VRIG.digest, Literal(canon.mapping_digest(layer))))
            self.facts_of(layer_node, programme.id, layer, f"layers[{index}].", ("layer", "insurers"))
            for j, insurer in enumerate(layer.get("insurers") or []):
                mapping = insurer if isinstance(insurer, dict) else {"name": insurer}
                self.placement(node, programme.id, mapping, f"layers[{index}].insurers[{j}]", j, layer_node)
        for j, policy in enumerate(programme.mapping.get("policies") or []):
            mapping = policy if isinstance(policy, dict) else {"document": policy}
            self.placement(node, programme.id, mapping, f"policies[{j}]", j, None)

    def placement(self, programme_node: URIRef, programme_id: str, mapping: dict, key_path: str, index: int, layer) -> None:
        g = self.graph
        node, _ = self.locate(programme_id, "declared", key_path=key_path)
        g.add((node, RDF.type, VRIG.Placement))
        g.add((node, VRIG.inProgramme, programme_node))
        g.add((node, VRIG["index"], Literal(index)))
        g.add((node, VRIG.digest, Literal(canon.mapping_digest(mapping))))
        if layer is not None:
            g.add((node, VRIG.onLayer, layer))
        self.facts_of(node, programme_id, mapping, f"{key_path}.", ())

    def events(self) -> None:
        if self.rig.events is None:
            return
        g = self.graph
        for index, event in enumerate(self.rig.events.events):
            event_id = str(event.get("id", index))
            node, _ = self.locate("events", "declared", key_path=f"events[{index}]")
            g.add((node, RDF.type, VRIG.Event))
            g.add((node, VRIG.rigId, Literal(event_id)))
            g.add((node, VRIG.digest, Literal(canon.mapping_digest(event))))
            self.facts_of(node, "events", event, f"events[{index}].", ("id", "facts", "unknown"))
            facts = event.get("facts") or {}
            if isinstance(facts, dict):
                for key, value in facts.items():
                    self.fact(node, "events", str(key), value, f"events[{index}].facts.{key}")
            for j, key in enumerate(event.get("unknown") or []):
                self.fact(node, "events", str(key), None, f"events[{index}].unknown[{j}]", unknown=True)

    # ---- resolution and findings --------------------------------------------------

    def resolve(self) -> None:
        g = self.graph
        for fact, _, strings in self.facts:
            for value in strings:
                for target in self._targets(value):
                    g.add((fact, VRIG.resolvesTo, target))
        still: list[tuple[URIRef, URIRef, str]] = []
        for ref, locator, document_id in self.unresolved:
            kind = str(g.value(ref, VRIG.targetKind))
            number = str(g.value(ref, VRIG.targetNumber))
            external = bool(g.value(ref, VRIG.external).toPython())
            view = str(g.value(g.value(ref, VRIG.locator), VRIG.view))
            view_name = "blind" if view == str(VRIG.Blind) else "declared" if view == str(VRIG.Declared) else None
            if view_name is None:
                view_name = canon.view_name("rendering", str(g.value(URIRef(view), VRIG.renderingName)))
            candidates = self._other_documents(document_id) if external else [document_id]
            found = [self.body_index[(d, v, k, number)] for d in candidates for v in ([view_name] if not external else ["blind"])
                     for k in _TARGET_KINDS.get(kind, (kind,)) if (d, v, k, number) in self.body_index]
            if found:
                for target in found:
                    g.add((ref, VRIG.resolvesTo, target))
            else:
                still.append((ref, locator, document_id))
        self.unresolved = still

    def _targets(self, value: str) -> list[URIRef]:
        targets = []
        if value in self.documents:
            targets.append(self.documents[value])
        if value in self.programmes:
            targets.append(self.programmes[value])
        targets.extend(self.forms.get(value, []))
        return targets

    def _other_documents(self, document_id: str) -> list[str]:
        document = self.rig.document(document_id)
        if document is None:
            return []
        named: list[str] = []
        for key in _TOWARDS_OTHER_DOCUMENT:
            value = document.front.get(key)
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, str) and item in self.documents and item not in named:
                    named.append(item)
        return named

    def finding(self, kind: URIRef, locator: URIRef, document_id: str, about: URIRef, message: str, key: str | None = None) -> URIRef:
        g = self.graph
        string = str(locator)[len(canon.locator_iri("")):]
        node = URIRef(canon.finding_iri(str(kind).rsplit("#", 1)[-1], document_id, string, key))
        g.add((node, RDF.type, VRIG.Finding))
        g.add((node, VRIG.findingKind, kind))
        g.add((node, VRIG.locator, locator))
        g.add((node, VRIG.about, about))
        g.add((node, VRIG.message, Literal(message)))
        g.add((node, VRIG.fromRun, self.run_node))
        if key is not None:
            g.add((node, VRIG.key, Literal(key)))
        return node

    def findings(self) -> None:
        for ref, locator, document_id in self.unresolved:
            self.finding(VRIG.UnresolvedReference, locator, document_id, ref, "A reference nothing in the rig resolves.")
            log.info("unresolved reference at %s", str(locator)[len(canon.locator_iri("")):])
        for node, locator, document_id in self.prose_only:
            self.finding(VRIG.ProseOnlyMeaning, locator, document_id, node, "A body node whose meaning only its prose carries.")

    def run_record(self) -> None:
        g = self.graph
        g.add((self.run_node, RDF.type, VRIG.Run))
        g.add((self.run_node, VRIG.rigDigest, Literal(self.rig.digest)))
        g.add((self.run_node, VRIG.formatVersion, Literal(self.rig.format_version)))
        g.add((self.run_node, VRIG.checkoutCommit, Literal(self.run.checkout_commit)))
        g.add((self.run_node, VRIG.substrateRelease, Literal(self.run.substrate_release)))
        g.add((self.run_node, VRIG.vocabularyVersion, Literal(self.run.vocabulary_version)))
        if self.run.vector_schema_version:
            g.add((self.run_node, VRIG.vectorSchemaVersion, Literal(self.run.vector_schema_version)))


def lift(rig: Rig, run: RunInfo) -> Graph:
    """The whole representation of a rig, both views, with the run and the lifter's own findings."""
    lifter = Lifter(rig, run)
    lifter.run_record()
    for document in rig.documents:
        lifter.document(document)
    for programme in rig.programmes:
        lifter.programme(programme)
    lifter.events()
    lifter.resolve()
    lifter.findings()
    return lifter.graph


BLIND_TYPES = (VRIG.Document, VRIG.BodyNode, VRIG.Reference, VRIG.RenderingView, VRIG.Run)


def blind(graph: Graph) -> Graph:
    """The blind view: documents reduced to their id, the body nodes and references of every body and rendering, the
    locators and views they use, and the run. No fact, programme, event or record."""
    out = Graph()
    for prefix, namespace in PREFIXES.items():
        out.bind(prefix, namespace)
    subjects = {s for t in BLIND_TYPES for s in graph.subjects(RDF.type, t)}
    for subject in subjects:
        for predicate, obj in graph.predicate_objects(subject):
            if predicate in (VRIG.formatVersion,) and (subject, RDF.type, VRIG.Document) in graph:
                continue
            out.add((subject, predicate, obj))
            if predicate == VRIG.locator:
                for p2, o2 in graph.predicate_objects(obj):
                    out.add((obj, p2, o2))
    return out


def findings_graph(graph: Graph) -> Graph:
    """The findings and the run, with each finding's locator, as a graph of their own."""
    out = Graph()
    for prefix, namespace in PREFIXES.items():
        out.bind(prefix, namespace)
    for subject in list(graph.subjects(RDF.type, VRIG.Finding)) + list(graph.subjects(RDF.type, VRIG.Run)):
        for predicate, obj in graph.predicate_objects(subject):
            out.add((subject, predicate, obj))
            if predicate == VRIG.locator:
                for p2, o2 in graph.predicate_objects(obj):
                    out.add((obj, p2, o2))
    return out


def canonical_turtle(graph: Graph) -> str:
    """Turtle whose bytes depend on the triples alone, never on the order they were added."""
    ordered = Graph()
    for prefix, namespace in PREFIXES.items():
        ordered.bind(prefix, namespace)
    for triple in sorted(graph, key=lambda t: (str(t[0]), str(t[1]), str(t[2]), getattr(t[2], "datatype", None) or "")):
        ordered.add(triple)
    return ordered.serialize(format="turtle")
