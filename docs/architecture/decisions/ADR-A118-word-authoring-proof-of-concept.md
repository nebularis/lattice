<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A118: Word authoring proof of concept

**Status:** Proposed
**Date:** 2026-10-01 (proposed)
**Related:** ADR-A29 (mise), ADR-A54 (dataset topology), ADR-A71 (SPI seam), ADR-A75 (store SPI),
ADR-A83 (reasoner isolation), ADR-A112 (Wording layer), ADR-A-C2
**Unit:** [`word-authoring-poc`](../../developer/plans/word-authoring-poc.md)

## Context

Drafters write contracts in Word. The Wording layer (ADR-A112) models a text as ordered parts, and
the [Logical English alignment](../../developer/sketches/logical-english-alignment.md) argues that
marked parts make a clause matchable to a sentence form without parsing English. Neither claim has
been tried where drafters work. The design of a spike that tries both is in the
[sketch](../../developer/sketches/word-authoring-poc.md).

A spike must not commit the platform to what it builds. It needs new code in four roots, a first
HTTP service in `platform/`, wording terms that have no ontology document yet, and a store that
bypasses the store SPI.

## Decision

1. **Status.** The unit is a proof of concept. Its code, contracts and vocabulary are not platform
   contracts. Nothing outside the unit may depend on them, and they may be removed without
   deprecation.
2. **Placement**, inside existing roots:

   | Path | Holds |
   |---|---|
   | `apps/word-authoring-addin` | the Office web add-in, its manifest, harness and tests |
   | `platform/authoring-service` | the Java service, a Maven module of `platform/pom.xml` |
   | `workers/src/lattice_workers/wording_le`, `wording_analysis_*.py` | the Python analysis job |
   | `contracts/authoring` | schemas, templates, samples and fixtures |
   | `deployment/compose/authoring` | a compose stack separate from `deployment/compose/docker-compose.yml` |
   | `tools/authoring_stage.py` | staging of build artefacts for the images |

3. **Delivery.** An Office web add-in with an XML add-in-only manifest, served over HTTPS from the
   compose stack. No VSTO, COM or other installed component.
4. **Store.** The service uses Apache Jena and Fuseki directly, through the Graph Store Protocol. It
   does not use or extend the semantic dataset SPI (ADR-A71, ADR-A75), and its graph names do not
   follow ADR-A54. An in-memory store behind a package interface exists for tests only.
5. **Vocabulary.** The service and worker use the IRIs that the computable contract substrate sketch
   §4 gives `wrd:` terms, held in a provisional resource outside `ontology/`, with a POC namespace
   `wap:` for the rest. No ontology document, version or release tag changes. When CCS C3 to C5
   land, the POC either moves to the published terms or is retired.
6. **Runtimes.** Java handles HTTP, through Javalin behind a framework-neutral API class, and the
   synchronous checks. Python runs as a RabbitMQ job, given graph
   references, never RDF. SHACL validation in the service is not reasoning, so ADR-A83 is unaffected.

**Rejected.** A VSTO or COM add-in, which needs installation. Running LE2 or any Prolog, which the
rule-layers boundary keeps out of runtimes. Adding `ontology/wording` before Gate A of CCS, which
would pre-empt C3. Extending the store SPI for a spike.

## Consequences

- The root README and the READMEs of the touched roots list the new paths, marked as a proof of
  concept.
- `mise run check:java`, `check:workers` and `check:frontend` cover the new code. The stack has its
  own tasks.
- The gaps the POC finds in the Wording sketch (plan §2.4) are inputs to CCS C3.
- A decision to keep any part beyond the spike needs a new ADR.
