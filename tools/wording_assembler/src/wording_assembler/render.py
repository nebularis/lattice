# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""An assembled wording as a document in LATTICE's document markup (ADR-A137, contracts/document).

Numbers are derived here, never stored (ADR-A139 decision 5, law W7): by rank order among the included
siblings, and a chosen variant takes its slot's number. The markup states structure only and has no number
attribute, so each clause opens with its number as text. Deeper levels than a section are flattened into it,
and an element outside any section is written as unmarked text. ponytail: a definition is written as a clause,
add the term when a form marks definitions."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Dict, List, Optional, Set, Tuple
from xml.sax.saxutils import escape, quoteattr

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS

from .layer import Layer
from .model import FND, QNT, WRD, children, instances, is_a, variants_of

NS = "https://www.nebularis.org/neuro-semantic/lattice/document/1"


def _uuid(term) -> str:
    """A version 4 identifier derived from an IRI, the same for the same IRI."""
    return str(uuid.UUID(bytes=hashlib.sha256(str(term).encode()).digest()[:16], version=4))


def _slug(text: str, limit: int, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-")
    return slug if re.fullmatch(r"[a-z][a-z0-9-]*", slug or "") else (f"x-{slug}"[:limit].strip("-") if slug else fallback)


def _label(g: Graph, node, default: str) -> str:
    for p in (SKOS.prefLabel, RDFS.label):
        value = g.value(node, p)
        if value is not None:
            return str(value)
    return default


def _numbered(g: Graph, included: Set, parent, prefix: str) -> List[Tuple[URIRef, str]]:
    """The included elements below `parent` in document order, with their derived numbers."""
    found: List[Tuple[URIRef, str]] = []
    kids = [c for c in children(g, parent) if c in included and not is_a(g, c, WRD.Variable)]
    for position, kid in enumerate(kids, 1):
        number = f"{prefix}.{position}" if prefix else str(position)
        element = kid
        if is_a(g, kid, WRD.VariationSlot):
            chosen = [v for v in variants_of(g, kid) if v in included]
            if not chosen:
                continue
            element = chosen[0]                      # the variant takes its slot's number
        found.append((element, number))
        found += _numbered(g, included, element, number)
    return found


def _value_text(g: Graph, record, variable) -> str:
    texts: List[str] = []
    for value_record in g.objects(record, WRD.hasValue):
        if g.value(value_record, WRD.forVariable) != variable:
            continue
        texts += [str(v) for v in g.objects(value_record, WRD.literalValue)]
        for v in g.objects(value_record, WRD.value):
            number = g.value(v, QNT.numericValue)
            texts.append(str(number) if number is not None else _label(g, v, str(v).rsplit("/", 1)[-1].rsplit("#", 1)[-1]))
    return re.sub(r"\s+", " ", ", ".join(sorted(texts))).strip()


def render(record_graph: Graph, record_iri: URIRef, form: Graph, *, layer: Optional[Layer] = None) -> str:
    """The assembled wording `record_iri` as a document. `record_graph` holds the record and its value records,
    `form` the form it was assembled from. The result is well formed and valid against `document.rnc`."""
    from .layer import load_layer

    layer = layer or load_layer()
    g = record_graph + form + layer.spec
    root = g.value(record_iri, WRD.assembledFrom)
    included = set(g.objects(record_iri, WRD.includes))
    numbered = _numbered(g, included, root, "")

    by_identity: Dict[URIRef, URIRef] = {}
    for element, _ in numbered:
        identity = g.value(element, FND.hasIdentity)
        if identity is not None:
            by_identity[identity] = element
    variables = {g.value(v, FND.hasIdentity): v for v in instances(g, WRD.Variable)}
    used: Dict[str, Tuple[URIRef, str]] = {}

    def inline(element) -> str:
        parts = sorted(g.objects(element, WRD.hasTextPart), key=lambda p: int(g.value(p, WRD.partIndex)))
        out = []
        for part in parts:
            target, variable = g.value(part, WRD.refersToObject), g.value(part, WRD.refersToVariable)
            text = g.value(part, WRD.partText)
            if variable is not None and variables.get(variable) is not None:
                version = variables[variable]
                key = _slug(str(g.value(version, WRD.variableKey) or version), 40, "variable")
                kind = "number" if g.value(version, WRD.valueSpace) is not None else "text"
                used[key] = (version, kind)
                shown = _value_text(g, record_iri, version)
                out.append(f"<var key={quoteattr(key)}>{escape(shown)}</var>")
            elif target is not None:
                shown = str(g.value(part, WRD.displayText) or g.value(by_identity.get(target, target), WRD.objectId) or "reference")
                out.append(f"<ref target={quoteattr(_uuid(by_identity.get(target, target)))}>{escape(shown)}</ref>")
            elif text is not None:
                out.append(escape(str(text)))
        return "".join(out)

    body: List[str] = []
    section: Optional[List[str]] = None
    for element, number in numbered:
        if "." not in number:
            if section is not None:
                body.append("\n".join(section) + "\n    </section>")
                section = None
            if is_a(g, element, WRD.Text):
                body.append(f"    <unmarked>{escape(number)} {escape(re.sub('<[^>]+>', '', inline(element)))}</unmarked>")
            else:
                section = [f"    <section key={quoteattr('section-' + number)}>"]
        elif is_a(g, element, WRD.Text) and section is not None:
            section.append(f"      <clause id={quoteattr(_uuid(element))}>{escape(number)} {inline(element)}</clause>")
    if section is not None:
        body.append("\n".join(section) + "\n    </section>")

    title = _label(g, record_iri, _label(g, root, "Assembled wording"))
    template = _slug(str(root).rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1], 40, "form")
    declared = "".join(
        f"\n    <variable key={quoteattr(key)} type={quoteattr(kind)}>{escape(_label(g, version, key))}</variable>"
        for key, (version, kind) in sorted(used.items()))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<document xmlns="{NS}" id="{_uuid(record_iri)}">\n'
        f"  <meta>\n    <title>{escape(title[:200])}</title>\n    <template>{template}</template>{declared}\n  </meta>\n"
        "  <body>\n" + "\n".join(body) + "\n  </body>\n</document>\n"
    )
