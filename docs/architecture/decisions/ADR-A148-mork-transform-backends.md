<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A148: MORK transform backends, XSLT and JOLT

**Status:** Proposed
**Date:** 2026-10-30 (proposed)
**Related:** ADR-A23 (MORK compiler family completion policy), ADR-A119 (XSLT transformation sidecar), ADR-A125 (test-support packages), ADR-A143 (mapping digest)
**Unit:** [`mork-transforms`](../../developer/plans/mork-transforms.md)

## Context

A reviewed MORK mapping runs today on an RDF source, compiled to SPARQL by `tools/mork_rdf`, or on XML and JSON through RML, compiled by `tools/mork/src/mork2rml.py`. An adopter whose sources are XML or JSON often already runs an XSLT processor or JOLT, and would rather run a reviewed mapping on that engine than adopt an RML engine. ADR-A23 names RML, SPARQL, SHACL, SWRL and native IR as targets, and not XSLT or JOLT. ADR-A119 decision 6 plans an XSLT backend on `mork2rml`'s walk, written before `tools/mork_rdf` and its case analysis existed.

## Decision

1. **One reader, one logical plan.** The backends read a mapping scheme with `tools/mork_rdf`'s reader, so the studio, the proposer's check and every backend classify a mapping alike. A format-neutral logical plan, a tree of datums, each with what it iterates, how its identity is formed and what it asserts, is lowered from the reader's output, and the XSLT and JOLT backends are written against it. The SPARQL backend may move onto the plan later. This revises ADR-A119 decision 6, which named `mork2rml`'s walk.
2. **The source format is declared once.** A scheme's source concepts are in a representation scheme with `mork:format mork:XML` or `mork:format mork:JSON`. `mork:dataRef` and `mork:path` are then read in that format's path language, a subset that both targets can carry: for XML, `/` for the document root, child steps by qualified name with prefixes the scheme declares, `*` and `@attribute`, and for JSON, `$` for the document root, `.key` and `[*]`. A path outside the subset is refused with `BadPath`.
3. **XSLT writes N-Triples.** The XSLT backend writes one XSLT 3.0 stylesheet with no processor extension, whose output is canonical N-Triples, each triple once and in code point order, as ADR-A119's ingress kit does.
4. **JOLT writes JSON-LD.** JOLT reshapes JSON into JSON, so the JOLT backend writes a chain of JOLT operations whose output is expanded JSON-LD, which any JSON-LD processor reads as RDF.
5. **An identity with no key is positional, and reported.** Where a mapping forms a node's identity from no value of the source, the identity is the node's position in the document, 1-based element positions for XML as XPath counts them and 0-based array indexes for JSON as JSON Pointer counts them. Such an identity holds for one document and changes when a node is inserted before it, so the compiler reports it on the mapping with `PositionalIdentity` and recommends a key.
6. **A backend refuses what it cannot carry.** A mapping a target cannot express is not compiled, and a finding names it and why, never a partial transform. The first slices refuse lookups, guards, class and property creation and deferred outcomes off the context chain in both backends. XSLT could carry most of these later. JOLT has no URI encoding, so a key read into an IRI by the JOLT backend is reported with `KeyNotEncoded`.
7. **The engines run in Java.** `platform/mork-transforms` is a library that runs a stylesheet on Saxon-HE and a JOLT chain on Bazaarvoice JOLT, with a command line over standard input and output. Python tests call the command line. The studio runs them in a worker, `platform/config-studio-transforms`, which answers each request on RabbitMQ's direct reply-to, so a warm run takes milliseconds and the service waits for it as it waits for a write. The compile job that wrote the transforms and the run are two requests the browser makes in turn, so neither waits on or creates the other. A job that runs long is answered by an event pushed to the browser instead, a decision of its own. Each engine keeps what it compiled, keyed by the digest of the text, since compiling a stylesheet costs more than running it.
8. **Conformance is by example.** Each example has an XML and a JSON rendering of the same data, a mapping scheme for each, and one expected graph. The XSLT output of the one, and the JOLT output of the other read as JSON-LD, each equal the expected graph, up to positional identities, which differ between the formats by decision 5.

ADR-A23's targets gain XSLT and JOLT.

**Rejected.** Building on `mork2rml`'s walk (ADR-A119 decision 6), which would leave two case analyses to keep alike, and a check that does not cover what the transforms do. A separate property for each path language, where the format already says which one. Guessing the format from the path's text, as `mork2rml` does. A JSON shape of our own as JOLT's output, which would need a second step of ours to read. A partial transform with a warning. A Java engine kept only for tests.

## Consequences

- An XML or JSON source can be mapped, reviewed and checked once, and run on an XSLT processor or JOLT without our runtime.
- The logical plan is the start of a shared intermediate form for MORK's backends, the logical plan of the run planner sketch. Moving SPARQL onto it is a later change.
- Positional identities are honest about their limits, but a source without keys still gives identities that change between documents.
- JOLT adds one Java dependency, Apache 2.0.

## Provenance

Raised as a backlog item on 2026-10-30. The maintainer answered questions XJ-Q1 to XJ-Q7 the same day. Path subsets (a), JSON-LD (a), positional identity reported (c) and refusal (a) as recommended, engines in Java as services and workers rather than test-only, and the rest as recommended. The studio's questions XJ-Q8 to XJ-Q13 were answered the same day, request-reply for a run with push kept for jobs that run long, attribution after the run, a format selector, the transforms as artefacts, a sample workspace, and the compile and the run as two requests.
