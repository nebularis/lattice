<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Semantic Versioning - Design Sketch

**Unit ID:** `ontology-semantic-versioning`
**Status:** Design sketch for human review. No implementation is claimed.
**Trigger:** human request, 2026-09-25 — "we currently update our ontologies
regularly, without any thought to a versioning approach."
**Source of truth for the proposal:** [Semantic Versioning 2.0.0](https://semver.org/).

## Problem

Every layer under `ontology/` that declares `owl:Ontology` also declares
`owl:versionIRI`, or fails to, or declares something adjacent that does not
agree with it. There is no documented rule anywhere in this repository for
when that number changes, so it has drifted into an inventory that tells a
reviewer nothing:

| Artefact | Current `owl:versionIRI` | Base URI matches the layer's own hash namespace (`ontology-architecture.md` §2)? |
|---|---|---|
| `foundation/spec/foundation.ttl` | `.../neuro-semantic/foundation/0.0.7` | No — missing `lattice/` |
| `foundation/vocab/foundation-vocab.ttl` | `.../neuro-semantic/foundation-vocab/0.0.1` | No — missing `lattice/` |
| `vocabulary/spec/vocabulary.ttl` | `.../neuro-semantic/vocabulary/0.0.2` | No — missing `lattice/` |
| `quantification/spec/quantification.ttl` | `.../neuro-semantic/quantification/0.0.1` | No — missing `lattice/` |
| `party/spec/party.ttl` | `.../neuro-semantic/party/0.0.3` | No — missing `lattice/` |
| `party/vocab/party-vocab.ttl` | `.../neuro-semantic/party-vocab/0.0.1` | No — missing `lattice/` |
| `eligibility/spec/eligibility.ttl` | `.../neuro-semantic/eligibility/0.0.1` | No — missing `lattice/` |
| `eligibility/vocab/eligibility-vocab.ttl` | `.../neuro-semantic/eligibility-vocab/0.0.1` | No — missing `lattice/` |
| `instrument/spec/instrument.ttl` | `.../neuro-semantic/instrument/0.0.1` | No — missing `lattice/` |
| `instrument/vocab/instrument-vocab.ttl` | `.../neuro-semantic/instrument-vocab/0.0.1` | No — missing `lattice/` |
| `behaviour/spec/behaviour.ttl` | `.../neuro-semantic/behaviour/0.0.1` | No — missing `lattice/` |
| `behaviour/vocab/behaviour-vocab.ttl` | `.../neuro-semantic/behaviour-vocab/0.0.1` | No — missing `lattice/` |
| `surface/spec/surface.ttl` | `.../neuro-semantic/surface/0.0.1` | No — missing `lattice/` |
| `surface/vocab/surface-vocab.ttl` | `.../neuro-semantic/surface-vocab/0.0.1` | No — missing `lattice/` |
| `persistence/spec/persistence.ttl` | `.../neuro-semantic/lattice/persistence/0.1.0` | Yes |
| `mork/spec/Executable.ttl` | `.../neuro-semantic/lattice/executable/0.0.1` | Yes |
| `mork/spec/Mork.ttl` | **none** — `owl:Ontology` declared, no `owl:versionIRI` at all | n/a |
| `spc/spec/spc.ttl` | **none** — `owl:Ontology` declared, no `owl:versionIRI` at all | n/a |
| `applied/capacity/.../applied_capacity_execution_spec_capx_Version2.ttl` | `.../neuro-semantic/lattice/applied/capacity/execution/0.0.1` | Yes |
| `applied/insurance/spec/structure/contract.ttl` | `.../neuro-semantic/insurance/contract/0.1.1` **and separately** `owl:versionInfo "3.5.1"` | No — different namespace family entirely, and carries two disagreeing version signals on the same ontology |

Four distinct problems sit inside that one table, and the proposal below has
to answer all four, not just "add a number":

1. **No rule exists for what changes the number.** Every bump so far —
   `0.0.1` here, `0.0.7` there, `0.1.0`/`0.1.1` elsewhere — reflects however
   many times someone happened to touch the file, not a classification of
   what the change actually was. `vocabulary/README.md`'s own §"Version" note
   ("the additions are backward compatible... has not been advanced") is the
   *only* place in the repository that reasons about this at all, and it
   reasons about it ad hoc, once, for one layer.
2. **The versioning unit is inconsistent.** `spec/*.ttl` and `vocab/*.ttl`
   are separately versioned artefacts today (each is its own `owl:Ontology`
   document with its own IRI), and `foundation`'s two artefacts have already
   drifted apart (`0.0.7` vs `0.0.1`) with no record of why. `shapes/*.ttl`
   and `projection/*.ttl` declare no `owl:Ontology` at all and carry no
   version identity of their own, even though they change just as often.
3. **Two ontologies (MORK, SPC) have no version identity at all**, and one
   (`applied/insurance/contract.ttl`) has two disagreeing ones on the same
   document.
4. **The `owl:versionIRI` base URI silently disagrees with the namespace
   convention** `ontology-architecture.md` §2 already documents (one hash
   namespace per layer under `https://www.nebularis.org/neuro-semantic/lattice/`)
   for every one of the seven core literate-spec layers plus Surface. This
   predates this proposal and is a pre-existing defect this proposal's
   baseline-reset step is well placed to fix in the same pass, since every
   one of those files has to be touched anyway.

None of this is a new gap the project introduced carelessly — `foundation`
alone went to seven patch-shaped bumps and `party` to three without a rule
existing to check them against, which is exactly the working-without-a-plan
pattern semantic versioning exists to replace.

## What "the public API" means for an OWL/SHACL/SKOS ontology

Software semver (`semver.md`, attached to this request) defines API breakage
in terms of function signatures. An ontology's public API is what a
*consumer's data* is checked against: what a reasoner or a SHACL engine will
accept or reject, and what a term is documented to mean. Translating
`semver.md`'s three rules (§6–8) into that vocabulary:

| Bump | An ontology change is this kind when it... | Examples from this repository's own history |
|---|---|---|
| **PATCH** (Z) | Corrects prose or a shape so that it now matches what was already documented as intended, with no change to what a *correctly governed* consumer graph experiences. | Fixing an `rdfs:comment` or `fnd:utility` string that misdescribed a term; fixing a SHACL `sh:message`; a Turtle whitespace/syntax fix with no triple-level change; a broken cross-reference. |
| **MINOR** (Y) | Adds something backward compatible: a consumer graph that conformed before still conforms, unchanged in meaning, after. | A new class, property, or `vocab/` individual; a new *optional* SHACL property shape (`sh:minCount 0`) or a `sh:Warning`-severity shape; widening a cardinality restriction; marking a term deprecated while it still works (`semver.md` §7 requires this one). Foundation's `voc:SchemeBinding` addition (commit `65ac4a85e`, `vocabulary-temporal-binding`) is exactly this shape. |
| **MAJOR** (X) | Removes, renames, or narrows something such that a previously conformant consumer graph can stop conforming, or a previously valid statement can stop meaning what it meant. | Removing/renaming a class, property, or individual; narrowing a cardinality restriction; a new `sh:Violation`-severity shape, `sh:closed true`, or `owl:disjointWith` that a real existing graph could now fail; a domain/range narrowing; changing the ontology IRI itself. |

Two categories do not reduce to axiom-diffing and need a documented rationale
in the PR rather than an automated check:

- **Silent semantic redefinition** — the IRI and the axioms are unchanged,
  but the layer's own "Design decisions" prose now means something different.
  This is a MAJOR change even when no SHACL shape moves, and it is the one
  case where classification is a judgement call, for a human or an agent to
  make against the layer's own README, not a mechanical diff.
- **Cross-layer import pinning.** `owl:imports` in this repository pins an
  *exact* `owl:versionIRI` (`vocabulary/README.md`: "Quantification and
  Instrument import `vocabulary/0.0.2` by exact IRI"). Bumping any layer's
  version therefore obliges updating every importing layer's `owl:imports`
  statement (and its README `turtle-spec` source) in the *same* change, or
  the graph stops resolving. This is unlike a software dependency range —
  there is no "compatible with ^0.2" import statement available today. The
  ADR needs to either accept this cascade cost as the standing discipline, or
  propose a resolution mechanism; see "Open questions" below.

## Invariants to protect

1. Every `owl:Ontology` document under `ontology/` that this proposal brings
   into scope carries exactly one unambiguous `owl:versionIRI`, in a base URI
   consistent with `ontology-architecture.md` §2's namespace convention.
2. A version number changes only according to a documented, checkable rule —
   never "because the file was touched."
3. The versioning *unit* (which files share one version number) is stated
   explicitly per artefact kind, not left to accumulate by precedent the way
   `spec/*.ttl` vs `vocab/*.ttl` already has.
4. `owl:imports` continues to resolve after every bump: no layer is bumped
   without its importers being updated in the same change.
5. The one-time baseline reset this request asks for is clearly marked as an
   administrative normalisation, not a claim that any layer just became
   "0.2.0 stable" in the SemVer sense — `semver.md` §4 ("major version zero
   ... is for initial development. Anything MAY change at any time.") keeps
   applying after the reset exactly as it did before.
6. The documentation this unit produces is usable by a human contributor
   *and* by an agentic coding assistant mid-PR, as a checklist it can apply
   without external judgement calls beyond the one flagged exception above.

## Proposed deliverables

### ADR

Author ADR-A86 (Proposed) recording: SemVer 2.0.0 adopted for ontology
documents; the MAJOR/MINOR/PATCH mapping table above; the versioning unit
(one version per `owl:Ontology` document — `spec/*.ttl` and `vocab/*.ttl`
remain separately versioned, exactly as today, rather than merging or further
subdividing); the import-pinning cascade rule retained as-is; and the
baseline-reset target number.

### Baseline reset

A single mechanical pass, gated on ADR ratification, that:

- Assigns every ontology document currently missing `owl:versionIRI` (MORK's
  `Mork.ttl`, SPC's `spc.ttl`) its first one.
- Reconciles `applied/insurance/contract.ttl`'s two disagreeing version
  signals (`owl:versionIRI 0.1.1` vs `owl:versionInfo "3.5.1"`) into one.
- Normalises every core-layer `owl:versionIRI` base URI to match its own
  namespace convention (adds the missing `lattice/` segment) — **except**
  `applied/insurance/contract.ttl`'s namespace family, which is a separate,
  applied-layer-specific question (see "Open questions").
- Resets every in-scope document to one common version number. Recommended:
  **`0.2.0`** — safely above every current value (the highest today is
  `0.1.1`), and, per `semver.md`'s own FAQ ("the simplest thing to do is
  start your initial development release at 0.1.0 and then increment the
  minor version for each subsequent release"), leaves the entire `0.3.0`
  through `0.99.0` minor-version range — effectively unlimited — as room to
  grow before any layer's API is asserted stable enough for `1.0.0`. This one
  number is the proposal's single open numeric parameter; the ADR states it
  as Proposed pending human confirmation, not as settled.
- Records the reset itself as one entry in each affected layer's own
  "Open items"/changelog note, so a future reader does not mistake the jump
  from, say, `0.0.7` to `0.2.0` for seven MINOR releases that never happened.

### Developer and agent guidance

A new document, `docs/architecture/ontology-versioning-policy.md`, holding:
the MAJOR/MINOR/PATCH table; the versioning-unit rule; the import-pinning
cascade checklist (enumerate every importer via `grep owl:imports` before
bumping, update all in the same change); where the number physically lives
for the seven literate-spec layers (the README's own `turtle-spec` block,
propagated by `tools/literate_extract.py`, never edited directly in the
generated `spec/*.ttl`); and a short worked example of classifying a real
past change (the `vocabulary-temporal-binding` unit's own MINOR addition is a
ready-made one). Cross-referenced from `CONTRIBUTING.md`'s "Where new content
belongs" section and from `docs/architecture/ontology-architecture.md` §2.

### Tooling (deliberately narrow for this unit)

Automatically *classifying* a change as MAJOR/MINOR/PATCH is not proposed —
that is a research problem, not a checklist. What is proposed is a narrow,
mechanical nudge: a check (in the spirit of `tools/repository_topology_check.py`
and `literate_extract.py --check`) that fails when an in-scope `.ttl` file's
content differs from its last committed state but its `owl:versionIRI`
literal did not change at all. This catches "forgot to bump," not "bumped the
wrong amount" — classification stays a human/agent judgement call against the
documented table.

## Proposed slice boundaries

| Slice | Scope | Validation level | Completion gate |
|---|---|---|---|
| 1 | ADR-A86, this sketch, plan, status record, traceability skeleton | L0 | Human review of the mapping table, versioning unit, and baseline number |
| 2 | `docs/architecture/ontology-versioning-policy.md`, `CONTRIBUTING.md` and `ontology-architecture.md` §2 cross-references | L0 | Docs read coherently end to end; no dangling cross-reference (`mise run topology:links`) |
| 3 | Baseline reset across every in-scope `.ttl` file, plus every importer's `owl:imports` update in the same change | L0, L3 (`literate_extract.py --check` where applicable; `reuse lint`) | Every in-scope ontology parses, every import resolves, no version left unreconciled |
| 4 | The narrow "changed but not bumped" check, wired into `mise` | L0 | The check fires on a deliberately-mutated fixture and stays silent on an untouched one (mutation probe) |

## Deliberate non-coverage

- Automatic MAJOR/MINOR/PATCH classification of a change (a research problem,
  not this unit's job — the table is a human/agent checklist, not a linter).
- A dependency-range import mechanism replacing exact-IRI `owl:imports`
  pinning (see "Open questions" — a real option, not decided here).
- Re-versioning `shapes/*.ttl` or `projection/*.ttl` as independent
  `owl:Ontology` documents with their own `owl:versionIRI` — this proposal
  keeps today's asymmetry (spec and vocab carry version identity; shapes and
  projection changes are covered by whichever of those two artefacts' bump
  they motivate) rather than adding a third or fourth independently-versioned
  artefact per layer.
- Any change to what a layer's ontology *says* — this is a versioning-process
  unit, not an occasion to also fix unrelated content.
- MORK and SPC's own internal versioning conventions beyond assigning them a
  first `owl:versionIRI` consistent with the rest of the repository — MORK in
  particular is flagged elsewhere in this repository as "pre-existing/
  independent... richer and older in style," and this unit does not propose
  changing how MORK is otherwise governed.

## Open questions

- **Import-pinning cost.** Exact-IRI `owl:imports` pinning is precise and
  reproducible but means every MINOR/PATCH bump of a widely-imported layer
  (Foundation, Vocabulary) cascades into an edit of every importer's
  `owl:imports` statement in the same change. Keep this discipline as-is
  (recommended default — matches current practice, and the import graph is
  still small), or invest in a "latest-within-major" import IRI convention
  now, before the cascade cost grows with the graph? This sketch recommends
  keeping exact pinning and revisiting only if the cascade becomes a real
  source of friction.
- **`applied/insurance/contract.ttl`'s namespace family.** Its `owl:versionIRI`
  base (`.../neuro-semantic/insurance/...`) sits entirely outside the
  `lattice/` namespace tree, unlike `applied/capacity`'s. Is this deliberate —
  an applied ontology may legitimately choose its own namespace family,
  independent of the framework's own — or an oversight to correct alongside
  the version reset? This sketch does not assume an answer.
- **The baseline number itself.** `0.2.0` is recommended, not decided — see
  "Baseline reset" above.
