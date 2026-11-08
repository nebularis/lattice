# SPDX-License-Identifier: MPL-2.0
"""What P1 is asked once it exists: each target layer's shapes over the layer graph, the reasoning test kit's consistency
check, and the competency queries tracked beside the scheme. Every answer that is not clean is a finding. A finding
about a node the projection made is located at the node of the representation it came from, found back through the
locator the projection's identifiers carry, and a finding about the encoding itself, a query with no answer or the
consistency of the whole, is located at the tracked file that asked."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from pyshacl import validate
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import SH

from . import canon
from .lift import VRIG
from .p1 import BASE, TARGET_MODULES, _catalogue

log = logging.getLogger("v_rig")

_QUESTION = re.compile(r"^# question ([A-Za-z0-9_-]+): (.*)$")
LAYERS_FILE = "p1/layers.ttl"


@dataclass
class ChecksResult:
    findings: list[tuple[URIRef, URIRef, str | None, str, URIRef | None]] = field(default_factory=list)
    shape_reports: dict[str, str] = field(default_factory=dict)
    competency: dict[str, int] = field(default_factory=dict)
    consistent: bool | None = None


# ---- locating a finding ---------------------------------------------------------------

def back_locator(ir: Graph, node: str) -> URIRef | None:
    """The representation's locator a projected node's identifier carries, or the locator of the document, programme or
    event whose id ends it."""
    tail = unquote(str(node).rsplit("/", 1)[-1])
    if tail.startswith(canon.locator_iri("")):
        locator = URIRef(tail)
        return locator if (locator, RDF.type, VRIG.Locator) in ir else None
    for carrier in ir.subjects(VRIG.rigId, Literal(tail)):
        return ir.value(carrier, VRIG.locator)
    return None


def encoding_locator(ir: Graph, file: str, key_path: str) -> URIRef:
    """A locator for a finding about the encoding, at the tracked file that asked."""
    string = canon.locator_string(file, "declared", key_path=key_path)
    locator = URIRef(canon.locator_iri(string))
    ir.add((locator, RDF.type, VRIG.Locator))
    ir.add((locator, VRIG.documentId, Literal(file)))
    ir.add((locator, VRIG.view, VRIG.Declared))
    ir.add((locator, VRIG.keyPath, Literal(key_path)))
    return locator


def _about(ir: Graph, locator: URIRef) -> URIRef | None:
    return next((s for s in ir.subjects(VRIG.locator, locator) if (s, RDF.type, VRIG.Locator) not in ir), None)


# ---- the layers' shapes ---------------------------------------------------------------

def layer_graphs() -> dict[str, tuple[Graph, Graph]]:
    """Each target module's specification and shapes, by module name. A module without shapes has an empty shapes graph."""
    catalogue = _catalogue()
    out: dict[str, tuple[Graph, Graph]] = {}
    for name in TARGET_MODULES:
        module = catalogue.module(name)
        spec, shapes = Graph(), Graph()
        for role in ("spec", "vocab"):
            if role in module.roles:
                for path in sorted((catalogue.root / module.directory(role)).glob("*.ttl")):
                    spec.parse(path, format="turtle")
        if "shapes" in module.roles:
            for path in sorted((catalogue.root / module.directory("shapes")).glob("*.ttl")):
                shapes.parse(path, format="turtle")
        out[name] = (spec, shapes)
    return out


def validate_layers(ir: Graph, layers: Graph, result: ChecksResult, modules: dict[str, tuple[Graph, Graph]] | None = None) -> None:
    modules = modules if modules is not None else layer_graphs()
    ontology = Graph()
    for spec, _ in modules.values():
        ontology += spec
    for name, (_, shapes) in modules.items():
        if len(shapes) == 0:
            continue
        conforms, report, text = validate(layers, shacl_graph=shapes, ont_graph=ontology, inference="rdfs", advanced=True)
        result.shape_reports[name] = text
        rows = report.subjects(SH.resultSeverity, SH.Violation)
        for row in sorted(rows, key=lambda r: (str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultMessage)), str(report.value(r, SH.sourceShape)))):
            focus = report.value(row, SH.focusNode)
            message = str(report.value(row, SH.resultMessage) or "")
            shape = report.value(row, SH.sourceShape)
            path = report.value(row, SH.resultPath)
            component = str(report.value(row, SH.sourceConstraintComponent) or "").rsplit("#", 1)[-1]
            # The key names the projected node's role and the constraint that fired, so two violations on one node of the
            # representation, or on two nodes projected from it, have two identifiers. A property shape is a blank node,
            # so its path stands for it.
            named = path if path is not None else shape if isinstance(shape, URIRef) else None
            role = str(focus)[len(BASE):].split("/", 1)[0] if str(focus).startswith(BASE) else "node"
            key = f"{role}/{str(named).rsplit('#', 1)[-1].rsplit('/', 1)[-1] if named is not None else 'node'}/{component}"
            locator = back_locator(ir, focus) if focus is not None else None
            if locator is None:
                locator = encoding_locator(ir, LAYERS_FILE, str(focus))
            result.findings.append((VRIG.ShapeViolation, locator, key, f"{name}: {message or key}".strip(), _about(ir, locator)))
        log.info("shapes of %s: %s, %d violation(s)", name, "conforms" if conforms else "refused",
                 len(list(report.subjects(SH.resultSeverity, SH.Violation))))


# ---- consistency ------------------------------------------------------------------

def check_consistency(ir: Graph, layers: Graph, result: ChecksResult, modules: dict[str, tuple[Graph, Graph]] | None = None) -> None:
    locator = encoding_locator(ir, LAYERS_FILE, "consistency")
    try:
        from mork_compilers import reasoning
    except ImportError:
        reasoning = None
    if reasoning is None or not reasoning.available():
        result.findings.append((VRIG.ReasonerUnavailable, locator, None, "The consistency check did not run, since the reasoning test kit is not available here.", None))
        log.info("reasoner unavailable, consistency not checked")
        return
    modules = modules if modules is not None else layer_graphs()
    consistent = reasoning.run("consistent", graphs=[spec for spec, _ in modules.values()] + [layers])
    result.consistent = bool(consistent)
    if not consistent:
        result.findings.append((VRIG.Inconsistent, locator, None, "The projected graph with the layers' specifications is inconsistent.", None))
    log.info("consistency: %s", "consistent" if consistent else "inconsistent")


# ---- competency -------------------------------------------------------------------

def competency_files() -> list[Path]:
    catalogue = _catalogue()
    directory = catalogue.root / catalogue.module("v-rig").directory("projection") / "competency"
    return sorted(directory.glob("*.rq"))


def questions(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """A file's prologue and its (name, question, query) triples."""
    prologue: list[str] = []
    found: list[tuple[str, str, list[str]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _QUESTION.match(line)
        if match:
            found.append((match.group(1), match.group(2).strip(), []))
        elif found:
            found[-1][2].append(line)
        elif not line.startswith("#"):
            prologue.append(line)
    text = "\n".join(prologue)
    return text, [(name, question, "\n".join(lines).strip()) for name, question, lines in found]


def ask_competency(ir: Graph, layers: Graph, result: ChecksResult, files: list[Path] | None = None) -> None:
    files = files if files is not None else competency_files()
    for path in files:
        layer = path.stem
        prologue, asked = questions(path)
        for name, question, query in asked:
            rows = len(list(layers.query(f"{prologue}\n{query}")))
            result.competency[f"{layer}/{name}"] = rows
            if rows == 0:
                locator = encoding_locator(ir, f"projection/competency/{path.name}", name)
                result.findings.append((VRIG.EmptyQuery, locator, name, f"{layer}: {question}", None))
        log.info("competency %s: %d question(s)", layer, len(asked))


def check_all(ir: Graph, layers: Graph, *, reasoner: bool = True) -> ChecksResult:
    result = ChecksResult()
    modules = layer_graphs()
    validate_layers(ir, layers, result, modules)
    if reasoner:
        check_consistency(ir, layers, result, modules)
    ask_competency(ir, layers, result)
    return result
