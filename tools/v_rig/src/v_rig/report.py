# SPDX-License-Identifier: MPL-2.0
"""P4, the report. Rendered from the findings graph alone, never written by hand, sorted by document id and locator
so that two runs of one rig revision give the same bytes. It names document ids, locators, keys and the findings'
generic messages, and no text of a rig."""

from __future__ import annotations

from collections import Counter
from urllib.parse import unquote

from rdflib import RDF, Graph, URIRef

from . import canon
from .lift import VRIG

KIND_ORDER = ("UnmappedKey", "UncertainMapping", "ShapeViolation", "EmptyQuery", "UnresolvedReference", "Disagreement",
              "ProseOnlyMeaning", "UnknownFact", "Inconsistent", "ReasonerUnavailable")


def _local(node) -> str:
    return str(node).rsplit("#", 1)[-1]


def locator_string(graph: Graph, locator: URIRef) -> str:
    return str(locator)[len(canon.locator_iri("")):]


def position(graph: Graph, locator: URIRef) -> str:
    """The locator's position fields as `section 1, clause 1.1`, without the document id and view."""
    parts = []
    for name, predicate in (("section", VRIG.section), ("clause", VRIG.clause), ("row", VRIG.row), ("key", VRIG.keyPath)):
        value = graph.value(locator, predicate)
        if value is not None:
            parts.append(f"{name} {value}")
    view = graph.value(locator, VRIG.view)
    view_name = "declared" if view == VRIG.Declared else "blind" if view == VRIG.Blind else f"rendering {graph.value(view, VRIG.renderingName)}"
    return (", ".join(parts) or "whole") + f" ({view_name})"


def render(graph: Graph, run_info: dict) -> str:
    findings = list(graph.subjects(RDF.type, VRIG.Finding))
    rows = []
    for finding in findings:
        locator = graph.value(finding, VRIG.locator)
        document = str(graph.value(locator, VRIG.documentId)) if locator is not None else ""
        rows.append((document, locator_string(graph, locator) if locator is not None else "", _local(graph.value(finding, VRIG.findingKind)),
                     str(graph.value(finding, VRIG.key) or ""), str(graph.value(finding, VRIG.message) or ""), locator, str(finding)))
    rows.sort(key=lambda r: (r[0], r[1], KIND_ORDER.index(r[2]) if r[2] in KIND_ORDER else 99, r[3], r[4], r[6]))
    by_kind = Counter(r[2] for r in rows)
    lines = [
        "# Verification rig run",
        "",
        "| | |",
        "|---|---|",
        f"| Rig digest | `{run_info.get('rig_digest', '')}` |",
        f"| Format version | {run_info.get('format_version', '')} |",
        f"| Checkout commit | `{run_info.get('checkout_commit', '')}` |",
        f"| Substrate release | {run_info.get('substrate_release', '')} |",
        f"| Vocabulary | v-rig {run_info.get('vocabulary_version', '')}, canonicalisation {run_info.get('canonicalisation', canon.VERSION)} |",
        f"| Vector schema | {run_info.get('vector_schema_version') or 'none'} |",
        f"| Findings | {len(rows)} |",
        "",
        "## Findings by kind",
        "",
        "| Kind | Count |",
        "|---|---|",
    ]
    lines += [f"| {kind} | {by_kind[kind]} |" for kind in KIND_ORDER if by_kind[kind]]
    lines += [f"| {kind} | {count} |" for kind, count in sorted(by_kind.items()) if kind not in KIND_ORDER]
    current = None
    for document, _, kind, key, message, locator, iri in rows:
        if document != current:
            current = document
            lines += ["", f"## {document or 'unlocated'}", "", "| Where | Kind | Key | Finding | Id |", "|---|---|---|---|---|"]
        where = position(graph, locator) if locator is not None else ""
        short = iri.rsplit(":", 1)[-1][:12]
        lines.append(f"| {where} | {kind} | {key} | {message.replace('|', '\\\\|')} | `{short}` |")
    lines.append("")
    return "\n".join(lines)
