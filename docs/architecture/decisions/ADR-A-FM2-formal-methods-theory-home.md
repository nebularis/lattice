<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-FM2: Home of the formal-methods prover programme's theories

**Status:** Accepted
**Date:** 2026-10-06
**Related:** [ADR-A-FM1](ADR-A-FM1-formal-methods-prover-choice.md) (prover choice, Isabelle/HOL),
the formal-methods epic plan, [the Track E sketch](../../developer/sketches/formal-methods-track-e.md)
and [plan](../../developer/plans/formal-methods-track-e.md),
[ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (repository topology)
**Unit:** [`formal-methods`](../../developer/plans/formal-methods.md) (epic), track E, decision FM-D2

## Context

Track D's spike kept its Rocq and Isabelle theories under `spikes/formal-prover/`, a location the
epic plan (§7.1) and the repository topology rules allow only for an unmerged spike branch built
to compare two provers, never as a permanent home. Track E needs one. The Track E sketch (§1, §4)
named FM-D2 as its first open question and narrowed it to two candidates without deciding between
them:

1. **Beside each layer**, e.g. `ontology/eligibility/theory/`, paralleling that layer's existing
   `shapes/` and `projection/` directories, on the strength of the literate-generation direction
   (epic principle E1): a theory's closed datatypes are generated from the same README as that
   layer's `.ttl`, so keeping the generated file beside its source has some appeal.
2. **A new `tools/formal/`**, alongside `tools/mork_compilers` and `tools/persistence`, on the
   strength of the repository topology rules themselves
   (`.github/copilot-instructions.md`, repeated in ADR-A77): `ontology/` "owns semantic assets
   only: normative ontology sources, shapes, vocabularies, projections, semantic examples,
   semantic fixtures, and semantic documentation"; `tools/` "owns executable reference
   implementations and developer-facing toolchains." A mechanised proof, with its own build
   project, session roots and compiled artefacts, is an executable reference implementation's
   assurance evidence, not a semantic asset the ontology itself consists of: nothing under
   `ontology/` today is a build project with its own compiler invocation, and a theory is exactly
   that.

The two candidates do not disagree about where the *narrative source* lives. Both keep
`ontology/<layer>/README.md` as the one normative, literate source a theory's datatypes are
generated from (epic principle E1), unchanged by this decision either way. They disagree only
about where the *generated build project* (the `.thy` files, the Isabelle `ROOT` session
definitions, claim records and compiled heaps) physically sits.

A second, attached sketch (`docs/developer/sketches/improved-ontology-documentation.md`,
unplanned, not implemented by this ADR or by track E) proposes injecting README narrative into
generated `.ttl` files' own annotation properties (`rdfs:comment`, `skos:scopeNote`, …), via a new
pair of HTML-comment markers the literate-extraction tooling would recognise, orthogonal to the
existing fenced-code-block mechanism (`` ```turtle-spec ``, `` ```turtle-vocab ``, …). Track E's
theories are a second, independent extraction target from the same README (fenced-code-block
generated, the same pattern `literate_extract.py` already uses, not HTML-comment generated), so
this ADR's choice of home does not bear on whether that sketch is later adopted: neither candidate
location changes which README is authoritative, or what mechanism reads it.

## Decision

**Track E's theories, and their build project, live under a new top-level toolchain directory:
`tools/proofs/`.** Not beside each layer under `ontology/`, and not named `tools/formal/`
(`formal` as a word collides with "formal-methods" at epic scope without saying what the directory
actually contains; `proofs` says exactly that).

1. `tools/proofs/<layer>/` mirrors `ontology/<layer>/`'s own layer names (`tools/proofs/
   foundation/`, `tools/proofs/eligibility/`, …), one Isabelle session per layer, each generated
   from that layer's `ontology/<layer>/README.md`, the same literate source its `.ttl` already
   comes from. A layer with no formalised law yet has no corresponding `tools/proofs/<layer>/`
   until one does: this is additive, never a parallel tree every layer must populate.
2. The repository topology rules (`tools/` as "executable reference implementations and
   developer-facing toolchains") govern `tools/proofs/` the same way they already govern
   `tools/mork_compilers` and `tools/persistence`: its own `pyproject.toml`-equivalent or build
   file, its own `mise` tasks, its own tests, reviewed and merged the same way.
3. The generation direction itself (which tool extends `literate_extract.py`, or a new generator,
   to produce Isabelle `.thy` datatypes from a README's fenced blocks) is **not** decided by this
   ADR: it is track E's plan's own open question (FME-1.0), decided when that slice starts.
4. This ADR does not adopt, and does not block adopting, the attached improved-ontology-
   documentation sketch. If it is later taken up, its HTML-comment-marker mechanism writes richer
   annotations into `ontology/<layer>/spec/*.ttl` and friends; `tools/proofs/<layer>/`'s own
   generation (whatever FME-1.0 decides) is a second, independent consumer of the same README, and
   needs no rework because of where its own output sits.

## Consequences

- The Track E sketch's open-questions table (§4) marks FM-D2 resolved, citing this ADR. The Track
  E plan's FME-1.0 slice is unblocked and may start: its own first task is scaffolding
  `tools/proofs/`'s build project and deciding the generation-direction question this ADR leaves
  open.
- The Track E status record's "next action" moves from "decide FM-D2" to "start E1.0."
- Root `README.md` gains an entry for `tools/proofs/` once FME-1.0 creates it (repository topology
  governance: "any new structure/folders/projects must be documented" there), not by this ADR
  itself, which creates no files under `tools/`.
- `spikes/formal-prover/` is unaffected: it remains the track D record, on this branch, per
  ADR-A-FM1. Nothing moves from it into `tools/proofs/`; track E's theories are freshly generated
  from the README, not ported from the spike's hand-written ones (epic principle E1, Track E
  sketch §1).

## Addendum (2026-11-07): an applied development's general core

Decided by the maintainer on 2026-11-07, answering WPG-Q4 of the waterfall proofs sketch, and first applied by the ledger unit's LG-7. A proof development whose terms are a domain's stays outside the repository and is cited nowhere in it. Only its domain-neutral core enters `tools/proofs/<layer>/`, restated in the layer's own terms and re-proved there under the gate, and the session's README attributes it as an external development of ours whose general core was rebuilt here, never as a proof imported. A spike session without claim records and gate markers, such as `spikes/isabelle-layers`, is not a home for a claim either track cites. The same day, the spike's own `gate.py` and `claim-schema.json` were removed, since `tools/proofs/` holds the gate `check:proofs` runs and the second copy misled a reader. This narrows the consequence above that nothing moves from the spike: its theories, claims, defects and `env/` scripts stay, and the gate's history is in git.

## Addendum (proposed 2026-11-08): a prelude session the layer sessions parent on

**Status of this addendum:** Proposed, for the maintainer's acceptance. It records the formal-methods epic's decision FM-D18, taken on 2026-11-08 after `HOL-Library` was built on one development machine under a memory limit, and it is first applied by track E's FME-0.

Decision 1 names one Isabelle session per layer, each generated from its layer's README and parented on `HOL`. A layer's laws reach for theories of `HOL-Library`, `Multiset` for order independence, the order and fixpoint theories for a composition stated as a least fixpoint, `Interval` and the partition theories for terms in time, the code-generation adaptations for every export, and the same few are wanted by several layers. A session reaches a library theory in one of two ways. Parented on `HOL-Library`, it starts from that session's heap, which every machine that builds it must first build, a heap of some hundreds of megabytes taking minutes under a memory cap, with a cache to keep in continuous integration. Parented on `HOL` with a `sessions "HOL-Library"` clause, it loads the theories it imports from source, needing no heap, and every session that imports a theory checks it again on every build.

This addendum adds one session that is not a layer's. `tools/proofs/base/` holds the session `LatticeBase`, `session LatticeBase = HOL +` with `sessions "HOL-Library"`, `document = false` and `quick_and_dirty = false`, whose one theory imports the `HOL-Library` theories the layers' proofs reach for and nothing else. It states no law and carries no claim record, and the gate reports it as a session with nothing to gate. Every layer session parents on it, `session <Layer> = LatticeBase +`, so a library theory is checked once per machine into the prelude's heap, no machine builds the `HOL-Library` heap, and a session kept outside the repository has a public heap to parent on. The kernel a layer's README generates keeps importing `Main` or `Complex_Main`, and a library theory is imported by a layer's theorem theories alone, so no README moves for the library's sake.

The prelude's heap is built on first use and never by `bootstrap` (STD-324). `tools/proofs/check.py` builds `LatticeBase` before any layer's session and passes `-d tools/proofs/base` to every build, and `isabelle build` builds the parent where its heap is missing and rebuilds it where its sources changed, by its own source digests, so nothing else pins it, and `-f` is never passed. Adding a theory to the prelude is one import in its theory, reviewed as any change under `tools/proofs/` is, and the developer documentation records why each theory is there. A theory outside `HOL-Library` that a layer's proofs might one day need, `HOLCF` for a composition stated over a complete partial order, would make that session the prelude's parent, a decision for the slice that needs it and not taken here.

Everything else in this record stands. Decision 1's rule, one session per layer generated from its README, holds for every directory under `tools/proofs/` but `base/`, and decision 2's topology rules govern `base/` as they govern the layer directories.
