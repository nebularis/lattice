<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A86: Semantic versioning for ontology documents

**Status:** Proposed
**Date:** 2026-09-25
**Related:** ADR-A07b (Instrument's per-instance `fnd:Version`/`supersededBy`
versioning contract — a distinct concern, see "Consequences"), ADR-A22 (MORK
governance/versioning via Foundation alignment — likewise instance-level, not
document-level)

## Context

Every `owl:Ontology` document under `ontology/` carries an `owl:versionIRI`,
or does not, with no documented rule for when or how far that number moves.
The current inventory (full table in the
[design sketch](../../developer/sketches/ontology-semantic-versioning.md))
shows the cost of that absence: seven core layers' spec and vocab files sit
at inconsistent, ungoverned numbers (`0.0.1` through `0.1.1`); two ontologies
(MORK's `Mork.ttl`, SPC's `spc.ttl`) carry no version identity at all; one
(`applied/insurance/contract.ttl`) carries two disagreeing version signals on
the same document; and every core layer's `owl:versionIRI` base URI except
Persistence, MORK's `Executable.ttl`, and `applied/capacity`'s already
disagrees with the namespace convention `ontology-architecture.md` §2
documents. Neither a human contributor nor an agentic coding assistant has
anything to check a proposed change against today.

## Decision

**Adopt [Semantic Versioning 2.0.0](https://semver.org/) for every ontology
document under `ontology/` that declares `owl:Ontology`.**

- **Versioning unit:** one `owl:versionIRI` per `owl:Ontology` document.
  `spec/<layer>.ttl` and `vocab/<layer>-vocab.ttl` remain two independently
  versioned documents, as they already are; a change to `shapes/*.ttl` or
  `projection/*.ttl` is covered by whichever of a layer's `spec` or `vocab`
  version it motivates a bump of, rather than gaining independent version
  identity of its own.
- **Bump rule** (full table and rationale in the sketch): PATCH corrects
  prose or a shape to match already-documented intent, with no change to what
  a correctly governed consumer graph experiences. MINOR adds anything
  backward compatible — a new class, property, individual, optional SHACL
  shape, or a widened cardinality — or marks a term deprecated while it still
  works. MAJOR removes, renames, or narrows anything such that a previously
  conformant consumer graph, or a previously valid statement's meaning, can
  stop holding — including a silent redefinition of a layer's own documented
  semantics with no axiom change, which stays a documented judgement call,
  not a mechanical diff.
- **Import pinning is retained as-is.** `owl:imports` continues to pin an
  exact `owl:versionIRI`. Bumping a layer obliges updating every importer's
  `owl:imports` statement (and README `turtle-spec` source) in the same
  change. A dependency-range import mechanism is not adopted by this
  decision; it remains an open question for a future ADR if the cascade cost
  becomes a real source of friction.
- **One-time baseline reset**, gated on this ADR's ratification: every
  in-scope document (including MORK's and SPC's, first-assigned) resets to
  **`0.2.0`**, and every core-layer `owl:versionIRI` base URI is normalised to
  match its own namespace convention (`https://www.nebularis.org/neuro-semantic/lattice/<layer>/<version>`).
  `applied/insurance/contract.ttl`'s separate `owl:versionInfo "3.5.1"`
  annotation is reconciled into the single `owl:versionIRI` signal; its
  namespace family (outside `lattice/`) is left as a separate, applied-layer
  question, not assumed to be a bug. The reset is recorded, in each affected
  layer's own document, as an administrative normalisation — not seven or
  more MINOR releases that never happened.
- **Documentation home:** a new `docs/architecture/ontology-versioning-policy.md`,
  cross-referenced from `CONTRIBUTING.md` and `ontology-architecture.md` §2,
  written for both a human contributor and an agentic coding assistant to
  apply mid-PR without further judgement calls beyond the one flagged
  exception above.
- **Tooling stays narrow.** No automatic MAJOR/MINOR/PATCH classifier is
  built — that is a research problem. A mechanical "content changed, version
  literal did not" nudge is the only enforcement this decision calls for.

Major version zero keeps its ordinary SemVer meaning throughout: the
baseline reset is not a stability claim, and `1.0.0` remains reserved for
whichever future decision asserts a layer's public API stable.

## Consequences

- Every future ontology change gets classified against a documented table
  before merge, by whoever is making the change, human or agentic.
- Bumping a layer's version continues to require updating every importer's
  `owl:imports` in the same change; this is accepted friction, not a defect
  this decision resolves.
- This is a document-versioning decision. It does not change, supersede, or
  otherwise interact with ADR-A07b's or ADR-A22's `fnd:Version`/
  `fnd:supersededBy` pattern for versioning *instances* inside a populated
  graph — those remain a distinct mechanism at a distinct layer of the
  system, and both ADRs are cited above only to make that boundary explicit.
- MORK and SPC gain version identity for the first time; nothing else about
  how either is governed changes.
- The exact baseline number (`0.2.0`) and the applied-insurance namespace
  question are the two open points this ADR states a recommendation for
  rather than treating as beyond dispute; ratification is the point at which
  either is confirmed or amended.

## Proposed addendum (2026-09-25): guarantees consumers rely on

Raised by the [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)
unit. An applied ontology pins LATTICE by version IRI and relies on a version
IRI identifying one content. This addendum is ratified or amended together
with the decision above.

1. **Bump level propagates through imports.** A document whose only change is
   an `owl:imports` update takes the bump level of the imported change, since
   its own consumers see that change through its import closure. Every bump,
   PATCH included, runs the cascade checklist. This replaces the policy's
   statement that a PATCH never changes the version IRI, which contradicts its
   own "PATCH still bumps the version" section.
2. **A missing version IRI is flagged.** `tools/ontology_version_check.py`
   fails for an in-scope document that declares `owl:Ontology` without an
   `owl:versionIRI`, instead of skipping it.
3. **The check runs in CI**, against the merge base of the change.
4. **Ontology IRIs stay as they are.** The ontology IRIs
   (`…/neuro-semantic/<layer>`) differ from the version-IRI base
   (`…/neuro-semantic/lattice/<layer>/<version>`). Changing them is MAJOR for
   every layer and buys nothing until documents are served at their IRIs, which
   [ADR-A88](ADR-A88-ontology-import-resolution-for-consumers.md) defers.
