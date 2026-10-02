<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A115: Bidirectional XSLT transformation sidecar

**Status:** Proposed
**Date:** 2026-10-02 (proposed)
**Related:** ADR-A29 (mise), ADR-A71 (SPI seam), ADR-A75 (store SPI), ADR-A78 (persistence profile
substrate), ADR-A79 (persistence compiler toolchain), ADR-A81 (control plane HTTP runtime),
ADR-A83 (reasoner isolation), ADR-A23 (MORK compiler family completion policy)
**Unit:** [`xslt-sidecar`](../../developer/plans/xslt-sidecar.md)

## Context

[`xml-egress-and-transformation-kits.md`](../../developer/sketches/xml-egress-and-transformation-kits.md)
already designed, in detail, a Saxon-hosted XSLT 3.0 projection from SPARQL Query Results XML to
published, versioned "transformation kits." That design assumed the engine lives embedded in one
Java module, projects in one direction (egress), and that each kit's query is hand-written.

Three things have changed the picture since. The persistence compiler (ADR-A79) now produces
portable SPARQL text from a compiled profile, so the shape of a query's results is frequently
already known rather than independently authored. `tools/mork2rml.py` already compiles a MORK
mapping graph into an executable artefact (RML) for one direction (ingestion into RDF). Nothing
compiles a MORK mapping into an XSLT stylesheet for the same purpose. Nothing in the repository runs
as a standalone sidecar process usable outside a JVM-hosted caller.

The design for all three is in the
[sketch](../../developer/sketches/xslt-sidecar.md), which this ADR does not duplicate.

## Decision

1. **Status.** This is a utility, not a vertical proof of concept. It has no owning domain and is
   meant to be glued into other stacks, including stacks this repository does not otherwise host.
2. **Engine.** Saxon-HE, XSLT 3.0 and XPath 3.1, the same choice and the same licence analysis as
   the existing egress sketch (MPL 2.0, no ADR-A83 conflict). One engine serves both directions.
3. **Deployment**, both forms exist: a core Java library (the existing egress sketch's
   `semantic-xml-egress` module, extended) for an in-process JVM caller, and a standalone sidecar
   process wrapping the same library over HTTP, aligned with ADR-A81's runtime shape, for a caller
   that is not a JVM process.
4. **Direction.** The sidecar supports egress (a graph reference projected through a kit to XML or
   another skin) and ingress (an external XML document lifted through a kit to canonical N-Triples).
   Neither direction gives the sidecar a store, SPARQL endpoint, or message-queue dependency of its
   own: a caller supplies a kit identifier and an input, and consumes an output.
5. **Kit sourcing.** An egress kit's query prefers the output of `persistence instantiate` (or a
   Surface-generated equivalent) where a compiled profile already covers its target, over an
   independently hand-written query answering the same question. An ingress kit's stylesheet may be
   hand-written or compiled from a MORK mapping graph by a new compiler backend.
6. **MORK compiler family.** A new backend, sibling to `mork2rml.py`, compiles a MORK mapping graph
   to a static XSLT 3.0 stylesheet (`MorkDAG → XSLT`), sharing its DAG-walking logic with `mork2rml`
   rather than duplicating it, following the same shared-IR, multiple-backend shape ADR-A23 already
   establishes for the Eligibility compiler family.
7. **Publication.** Every kit, either direction, is published under `contracts/xml/` as a versioned
   directory with a manifest, exactly as the existing egress sketch's §8 already requires, with no
   Saxon extension function in any published stylesheet, so any conformant XSLT 3.0 processor
   reproduces the kit's output without our code.

**Rejected.** Embedding the engine only, with no standalone process, which would not satisfy "glued
into some other stack." A bespoke HTTP runtime for the sidecar, which would be a second convention
alongside ADR-A81's. Folding the LegalRuleML-specific ingress pipeline
(`legalruleml-runtime-pipeline.md`'s Route B) into this unit, which keeps its own OASIS-specific
stylesheets and its own RML-based execution. RDF/XML, or a SPARQL `INSERT DATA` block, as the
ingress output form, in favour of the repository's existing canonical sorted N-Triples convention.

## Consequences

- A new Maven module (or an extension of the existing egress sketch's planned
  `platform/semantic-xml-egress`) hosts the core library. A further module or packaging hosts the
  standalone sidecar process.
- `tools/mork2rml.py` is refactored to expose its DAG-walking logic to a second backend before that
  backend is added, with its own existing tests as the regression guard for the refactor.
- `contracts/xml/` becomes a real directory, shared by egress and ingress kits, distinguished by a
  manifest field.
- No ontology document changes. This unit consumes existing ontology-described shapes. It does not
  define new ones.
- A decision to retire or materially change the kit publication model needs a new ADR, not an
  amendment to this one or to the existing egress sketch.
