// SPDX-License-Identifier: MPL-2.0
// Track C2: binding resolution with scheme composition, ahead of CCS's HQ-4 and
// insurml-alignment's IMA-D4a (formal-methods-track-c.md plan, slice C2;
// formal-methods-track-c.md sketch §4-§5).
//
// ADR-A85 resolves ONE scheme per (Contract, Context): among the candidates that apply, the
// most specific wins, equal specificity conflicts, and `boundScheme` is the unscoped fallback.
// Modelled here, restricted to one Source, as the `single` field. Composition generalises this:
// several Sources (Instrument's baseline, another layer, a wording's own dates -- HQ-4) each
// resolve independently under the SAME ADR-A85 rule, and a Contract's composed answer in a
// Context is the union of what each Source resolves to (insurml-typing.md §6.1's own words:
// "membership the union of theirs").
//
// `single` stands in for ADR-A85's whole resolver (candidate bindings, specificity, conflict):
// modelling that resolver's internals is not this check's job -- `tools/vocabulary/` already
// implements it, and its determinism/conflict-reporting/fallback properties are assumed to hold
// of each Source's own resolution before composition is asked to do anything with the result.
// What composition adds -- union across Sources -- is what these two checks examine.

sig Concept {}

sig Scheme {
  members: set Concept,
  broader: Concept -> Concept
} {
  broader in members -> members          -- a scheme's hierarchy only relates its own members
}

sig Context {}
sig Source {}

sig Contract {
  single: Source -> Context -> lone Scheme   -- ADR-A85: at most one scheme per source, per context
}

-- Composition: the set of schemes a contract's sources resolve to, in a context.
fun composed[c: Contract, ctx: Context]: set Scheme {
  { s: Scheme | some src: Source | s = c.single[src][ctx] }
}

-- PROPERTY 1 (HQ-4's own statement, made checkable): every source that resolves alone under
-- ADR-A85 still resolves under composition. Expected: no counterexample, since `composed` is
-- defined as that very union -- this is a self-consistency check on the model, not a deep claim.
assert EverySourceResolves {
  all c: Contract, ctx: Context, src: Source |
    some c.single[src][ctx] implies c.single[src][ctx] in composed[c, ctx]
}
check EverySourceResolves for 4

-- A composition "disagrees" when two of its schemes share a member concept with each recording
-- a different broader parent for it -- the sketch's open question (§2, §5): union alone says
-- nothing about what happens when the inputs to the union overlap.
pred overlapDisagrees[c: Contract, ctx: Context] {
  some disj s1, s2: composed[c, ctx] |
    some concept: s1.members & s2.members |
      some s1.broader[concept] and some s2.broader[concept] and
      s1.broader[concept] != s2.broader[concept]
}

-- PROPERTY 2: does the union-of-members, union-of-hierarchies proposal, by itself, already rule
-- out disagreement? Expected: a counterexample IS found -- confirming the sketch's open question
-- is real, not hypothetical, and an explicit rule (forbid overlap, order the sources, or require
-- agreement) must be added to whichever ADR accepts composition, not left to the union to settle
-- on its own.
assert NoOverlapDisagreement {
  all c: Contract, ctx: Context | not overlapDisagrees[c, ctx]
}
check NoOverlapDisagreement for 4
