<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Bidirectional XSLT transformation sidecar - Status

**Unit ID:** `xslt-sidecar`
**Status:** 🔵 Drafted, not started. Decisions XS-D1 to XS-D7 awaiting the human
**Last updated:** 2026-10-02
**Plan:** [xslt-sidecar.md](../plans/xslt-sidecar.md)
**Sketch:** [xslt-sidecar.md](../sketches/xslt-sidecar.md)
**ADR:** [A-119](../../architecture/decisions/ADR-A119-xslt-transformation-sidecar.md), Proposed
**Machine:** not yet assigned. No branch created, no code written

## Current position

At the human's request, a sketch and plan were drafted for a new unit: a Saxon-hosted XSLT 3.0
engine, published as both a Java library and a standalone sidecar process, that projects known-shape
SPI data to documents and reports on egress (building on the existing
[xml-egress-and-transformation-kits.md](../sketches/xml-egress-and-transformation-kits.md) sketch),
and lifts external, non-OWL XML into canonical triples on ingress, with a new MORK compiler backend
(`mork2xslt`, sibling to the existing `tools/mork2rml.py`) able to generate an ingress kit's
stylesheet from a MORK mapping graph.

Seven decisions (XS-D1 to XS-D7, sketch §11) are proposed, none recorded. Seven slices (XS0 to XS6,
plan §4/§5) are drafted, none started, totalling about 2.31M tokens. No ADR is Accepted. No code,
branch, or module exists yet.

**Next action, for the human:** review the sketch and plan, record decisions XS-D1 to XS-D7 (plan
§3, sketch §11), and decide whether and when the unit starts.
**Next action, for the agent:** none. No slice may start before the decisions above are recorded.

## Relationship to other units

- Builds on, and does not revise, `xml-egress-and-transformation-kits.md`'s own positions on the
  transform source (SPARQL Query Results XML, not RDF/XML), the Saxon/Java hosting choice, and the
  kit publication model.
- Explicitly out of scope: the LegalRuleML-specific ingress pipeline
  (`legalruleml-runtime-pipeline.md`'s Route B), which keeps its own OASIS stylesheets and RML-based
  execution (sketch §11, XS-D7).
- Unrelated to, and not blocked by, `word-authoring-poc`. The two units share no paths and no
  dependency in either direction.

## History

- 2026-10-02: sketch and plan drafted at the human's request, alongside ADR-A119 (Proposed) and
  this status record. No implementation authorised. Not committed to a feature branch yet, since no
  branch has been assigned to this unit.
