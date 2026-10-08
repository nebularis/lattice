<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A116: Vocabulary scheme composition

**Status:** Proposed
**Date:** 2026-10-07
**Related:** [ADR-A85](ADR-A85-vocabulary-scoped-temporal-binding-resolution.md) (scoped and
temporal binding resolution, extended here, not superseded), [ADR-A100](ADR-A100-hierarchical-match-over-flat-schemes.md)
(hierarchical match over flat schemes; its own Eligibility-level addendum for a composed scheme
is a follow-on, not decided here), [ADR-A87](ADR-A87-eligibility-concept-inclusion-and-exclusion.md)
(concept inclusion and exclusion, read by `tools/mork_compilers`, also a follow-on consumer, not
changed here)
**Shared with:** CCS's held design question HQ-4 (`computable-contract-substrate.md`, found
building C7b, 2026-10-05) and insurml-alignment's IMA-D4a (`insurml-alignment.md`), both of which
name this exact construct and wait on it. One ADR answers both, as `insurml-alignment.md`'s own
IMA-D4a row recommends ("a Vocabulary ADR shared with CCS HQ-4, or none")
**Evidence:** the formal-methods epic's track C2, a checked Alloy model
([sketch](../../developer/sketches/formal-methods-track-c.md),
[plan](../../developer/plans/formal-methods-track-c.md),
[status](../../developer/status/formal-methods-track-c.md),
[the model itself](../../../tools/models/vocabulary-scheme-composition/)). Track C2 produced the
checked evidence this ADR cites; it did not draft the ADR, by its own stated scope — this does.

## Context

**HQ-4**, verbatim: "Quantification's role contract resolves to one scheme in a context
(Vocabulary, ADR-A85), and two unscoped bindings conflict. Roles come from several places:
Instrument's baseline (arising, inception, ending, period start and end), other layers (an
allowance reset, a policy year), and each wording's defined dates (the Expiry Date, the Break
Date). C7b binds Instrument's baseline. The lease example's own date roles are left unbound... a
deployment that uses Instrument and another layer's roles, or a wording's own dates, cannot bind
them all to one contract today." Not because two sources' schemes compete for the *same* concern
— ADR-A85 already settles that case — but because ADR-A85's resolver returns **one** scheme per
contract per context, and each of HQ-4's sources needs its own, **simultaneously**.

**IMA-D4a**, fullest statement in `insurml-typing.md` §6.1: a publisher's profile needs
`wrd:elementType` to draw on *both* InsurML's own type scheme and a profile-local scheme for what
InsurML lacks, without a second `skos:inScheme` assertion on each concept (which
`imlsh:ConceptShape` already rejects, correctly — scheme membership is a fact about the concept,
not about who is asking). The same sketch names the general answer and notes HQ-4 is the same
problem under a different name.

**What ADR-A85 already settles, and what this decision must not undo.** ADR-A85's resolver
(`tools/vocabulary`) answers "which scheme applies" for one contract in one context, with three
properties that must still hold once an answer can be a *set*: resolution stays deterministic
(same context and time, same answer); a genuine conflict is always reported, never resolved by
iteration order or any other incidental property; an unscoped `voc:boundScheme` stays valid for
inputs with no scoped bindings.

**The evidence, not re-argued here.** Track C2's Alloy model checked two properties of the
candidate composition rule ("membership the union of theirs, hierarchy the union of their
`skos:broader` links," `insurml-typing.md`'s own words) rather than assuming it sound:
`EverySourceResolves` (HQ-4's own property, "every role a layer needs resolves") held with no
counterexample up to scope 4. `NoOverlapDisagreement` did **not** hold: the model found a
contract composing two schemes that share a member concept with each recording a different
`skos:broader` parent for it — the union is silent on what to do, and must not be silently
resolved either way. This ADR states the rule the model found missing.

## Decision

**A contract may resolve, in one context, to a set of schemes — one per independently declared
*aspect* — rather than exactly one.** ADR-A85's own resolution algorithm is reused unchanged, per
aspect; composition is additive on top of it, not a replacement for it.

1. **`voc:BindingAspect`**, a new class. Individuals are opaque tags a deployment mints, naming
   one of the "several places" HQ-4 describes (for example, `ex:instrument-baseline-dates`,
   `ex:allowance-reset-dates`, `ex:wording-defined-dates`) — the same role `voc:BindingScope`
   already plays for scope tags, not a controlled enumeration this ADR closes.
2. **`voc:forAspect`**, a new property, domain `voc:SchemeBinding`, range `voc:BindingAspect`.
   States which aspect a binding resolves a scheme for. Not named `voc:role` (`pty:Role` already
   names a different thing, an actor's capacity to occupy an occupancy, and the collision would
   read as the same concept from two layers) and not named with `purpose` (`ins:forPurposeOf`
   already names a deeming's own limitation to named relations, a different concept again).
3. **Resolution runs once per aspect, under ADR-A85's own algorithm, untouched.** A binding
   naming no `voc:forAspect` is, as today, the single implicit aspect every existing consumer
   already uses — composition is purely additive, and no existing graph or caller changes
   behaviour because of this ADR. Two bindings conflict (ADR-A85's existing rule: equal or
   incomparable scope-set specificity) only when they share both a contract **and** an aspect.
   Two bindings for *different* aspects of the same contract never conflict with each other,
   whatever their scopes — this is HQ-4's own point, made precise.
4. **The composed answer, for one contract in one context, is the set of (aspect, scheme) pairs
   each aspect's own ADR-A85 resolution yields** — `EverySourceResolves`, checked, not assumed.
5. **The overlap rule track C2 found missing: forbidden, not merely discouraged.** Two schemes
   resolved for *different* aspects of the same contract may not share a `skos:inScheme` member.
   Checked statically, conservatively, the same discipline ADR-A85 already uses for structural
   shapes: for one `voc:SchemeContract`, no two of its candidate schemes (every scheme reachable
   through any binding or `voc:boundScheme`, grouped by declared aspect, including the unscoped
   fallback's own implicit aspect) share a member, regardless of whether their scopes or times
   could ever let them resolve together. This is stricter than necessary in principle — two
   schemes that could never actually co-resolve (disjoint time scopes, say) would still be
   rejected — and is the deliberate trade: cheap to state and check without a resolution context,
   matching the sketch's own "simplest, matches ADR-A85's own 'no OWL axiom silently selects'"
   recommendation, over a context-dependent check only the resolver could make. A later ADR may
   relax this if a real deployment needs the relaxation; none does yet.
6. **The unscoped `voc:boundScheme` fallback keeps exactly ADR-A85's meaning: one scheme, the
   single implicit aspect.** It is not extended to carry an aspect of its own (it has no
   reified node to attach `voc:forAspect` to). A deployment needing several simultaneously
   resolved aspects states at least one `voc:SchemeBinding` per aspect — even an unscoped one,
   naming no `voc:bindingScope`, if an aspect is always to resolve the same scheme regardless of
   context. This is a real, stated limitation, not an oversight: it keeps `voc:boundScheme`'s own
   shape and meaning untouched for every consumer that does not compose.
7. **Eligibility's hierarchical match reading a composed scheme** (`insurml-typing.md` §6.1: "an
   ADR-A100 addendum") **is explicitly out of scope, a follow-on, not decided here.** This ADR is
   Vocabulary-only. Whether and how a hierarchical match's closure reads the union of two
   composed schemes' `skos:broader` relations is ADR-A100's own later decision, informed by this
   one, not folded into it.
8. **Answers HQ-4 and IMA-D4a identically, as one shared ADR.** HQ-4: Instrument's baseline, an
   allowance reset, and a wording's own defined dates each become their own aspect; C8's parameter
   bindings give the wording-date aspect its values, as CCS's own plan already anticipates.
   IMA-D4a: InsurML's type scheme and a profile-local scheme become two aspects of
   `wrd:elementType`; T4 (`insurml-typing.md` §8) can proceed once this lands.

## Consequences

- **`tools/vocabulary`** needs a new entry point resolving every aspect of a contract at once
  (reusing `resolve()` per aspect, unchanged) and a new `CompositionOverlapError`, raised when the
  overlap rule above is violated — defence in depth alongside the static shape, for a graph that
  was not validated against it. Existing callers of `resolve()` are unaffected: its own signature
  and behaviour do not change.
- **`ontology/vocabulary`** needs `voc:BindingAspect` and `voc:forAspect` declared (its README,
  the one normative source, first — `vocab/vocabulary-vocab.ttl` is generated from it) and a new
  SHACL-SPARQL shape for the overlap rule, following the authoring rules already in
  `.github/copilot-instructions.md` (inline `PREFIX`, `OPTIONAL` around every counted pattern, a
  grouped sub-query per independent count). **Not done by this ADR**: this is implementation,
  the next slice once this ADR is accepted, and must follow
  `docs/architecture/ontology-versioning-policy.md` in full when it happens (a MINOR bump to
  Vocabulary, since this is additive at major version zero, per ADR-A113).
- **CCS's C8** can write the lease example's own date-role bindings once this lands — the
  deferral in C8's own validation pack ("waiting for HQ-4 and track C2") is clear to close. CCS's
  and insurml-alignment's own plan documents (`computable-contract-substrate.md`,
  `insurml-alignment.md`) are Machine R's, not edited by this ADR — their HQ-4 and IMA-D4a rows
  are for that plan's own owner to update once this ADR is reviewed.
- **Eligibility's own addendum** (consequence 7) is tracked as a follow-on against ADR-A100, not
  opened as work by this ADR.
- **Numbering.** Plain `A116`, not the formal-methods epic's non-colliding `A-FM` block: this is a
  Vocabulary-layer decision CCS and insurml-alignment both need, not an epic-scoped artefact, and
  belongs in the same sequential family as ADR-A85 and ADR-A100. Confirmed against both this
  branch's and `main`'s decisions catalogues before drafting (both agree up to A115, 2026-10-07) —
  still worth re-checking against `main`'s latest state immediately before the bundle in this
  session's plan is pushed, in case a concurrent CCS slice has minted a new number since.
