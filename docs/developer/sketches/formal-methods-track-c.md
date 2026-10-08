<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track C: the design-time models (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track C
**Status:** sketch, 2026-10-06. Nothing here is ratified; a plan follows once the open questions
below are settled
**Follows:** HQ-4 (CCS, found building C7b), IMA-D4a (insurml-alignment). Neither is decided; C2
exists to let them be decided on a checked model rather than on prose alone
**Reads with:** [formal-methods.md](formal-methods.md) §3 ("Track C"), §4 ("Track C: the
design-time models"), [ADR-A85](../../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md)
(the current single-scheme resolution law), [insurml-typing.md](insurml-typing.md) §6.1, §8
(scheme composition's fullest statement so far)

## 1. The problem, restated precisely from its two sources

Neither CCS's C8 nor insurml-alignment resolved this; both deferred to it explicitly (confirmed
by reading `main`'s C8 validation pack and the CCS/insurml-alignment plans directly, not assumed).

**HQ-4** (`computable-contract-substrate.md`, found building C7b): Quantification's role contract
resolves to **one** scheme in a context (ADR-A85). Context roles come from several independent
sources at once: Instrument's baseline roles (arising, inception, ending, period start/end),
another layer's roles (an allowance reset, a policy year), and each wording's own defined dates
(the Expiry Date, the Break Date). A deployment using more than one of these sources cannot bind
them all to one contract today — not because the sources' schemes compete for the *same* role
(ADR-A85's existing conflict case), but because the current resolver returns **one** scheme and
each source needs its own.

**IMA-D4a** (`insurml-alignment.md`; fullest statement in `insurml-typing.md` §6.1, §8): a
publisher's profile needs `wrd:elementType` to draw on *both* InsurML's own type scheme and a
profile-local scheme for what InsurML lacks, without putting each concept in two schemes via a
second `skos:inScheme` assertion (which `imlsh:ConceptShape` already rejects, correctly, since a
concept's scheme membership is a fact about the concept, not about who is asking). The same
sketch names the general answer: **scheme composition** — "a Vocabulary construct that makes a
contract resolve to a set of schemes in one context, with membership the union of theirs and the
hierarchy the union of their `skos:broader` links, without stating `skos:inScheme` again" — and
notes HQ-4 is the same problem under a different name, recommending one shared Vocabulary ADR.

**Both wait on it.** CCS C8 shipped with "the lease's date words... not written, waiting for
HQ-4 and track C2" (its validation pack, verbatim). IMA-D4a is listed in insurml-alignment's own
decision table as "needed by: CCS C8" and still open.

## 2. What ADR-A85 already settles, and what composition must not undo

ADR-A85's resolver (`tools/vocabulary/`) answers "which scheme applies" for **one** contract in
**one** context, with three properties composition must keep: resolution is deterministic (same
context and time, same answer); a genuine conflict is always reported as a conflict, never
resolved by iteration order or any other incidental property; and an unscoped `boundScheme` stays
valid for inputs with no scoped bindings. Composition changes the *shape* of an applicable
answer (a set of schemes, not one), not these three properties, which must still hold of the
*set*-valued resolution: deterministic, conflicts reported (not silently dropped), existing
single-scheme consumers unaffected.

**The genuine open question is not "can several schemes apply" (sketches already answer that:
yes, by union) but what composition must refuse.** Two candidates for what still counts as a
conflict under composition, neither obviously right without a checked model:

- Two sources both resolve to schemes that **share a concept IRI** with different
  `skos:broader` parents — composition's claimed "union of memberships, union of hierarchies" is
  silent on what happens when the inputs to that union actually overlap, rather than being
  disjoint by construction.
- Two sources resolve to the **same scheme under different precedence** (one source's binding
  names it with a narrower scope than another's) — does composition let the narrower scope's
  binding stand for that source alone, or does ADR-A85's existing "strict superset wins, equal
  specificity conflicts" rule need restating per-source, per-scheme, or across the whole set?

## 3. Why Alloy, not SMT, for this model

The epic plan's own track C split is followed, not re-derived: C2 (this slice) is relational —
contracts, contexts, schemes, bindings and the roles that need them, and the properties to check
are about which relations can coexist and which combinations are forced to conflict — Alloy's
native ground (binary relations, relational image, transitive closure for `skos:broader`,
counterexample-by-construction when an assertion fails). C3 (slot exclusivity and exhaustiveness,
a numeric/combinatorial satisfiability question over condition slots) is SMT's ground instead,
per the plan's own words, and is a separate slice, not this one's job.

Both tools are MIT/BSD-family permissively licensed (`.local/formal-methods-eval-feedback.md`'s
licensing survey, reused here rather than re-litigated): Alloy MIT, Z3 MIT, cvc5 BSD. Track C
carries no runtime dependency either way — a design-time model is evidence for an ADR, not code
that ships.

## 4. The model's shape, proposed (not yet written)

An Alloy module, roughly:

```alloy
sig Scheme { broader: Scheme -> Scheme }          -- skos:broader, per scheme
sig Context {}                                     -- the active binding scope set
sig Source {}                                      -- a role-needing source: Instrument's
                                                    -- baseline, another layer, a wording's dates
sig Contract {
  needs: Source -> Context -> lone Scheme,         -- ADR-A85 today: one scheme per source+context
  resolvesTo: Context -> set Scheme                -- the composed answer this model adds
}
```

with facts encoding ADR-A85's existing precedence/conflict rule per `(source, context)` pair,
and the composed `resolvesTo` as the union over sources that successfully resolve, then two
assertions checked, not assumed:

- **Every source resolves.** For any contract and context where each source's own single-scheme
  resolution succeeds, the composed set contains that source's scheme — HQ-4's "every role a
  layer needs resolves," made checkable.
- **Composition does not silently merge overlap.** If two sources' resolved schemes share a
  member with different `broader` parents, the model should either find this `unsat` under a
  "composition is well-formed" predicate (meaning overlap must be forbidden by a shape, a Vocabulary
  constraint IMA-D4a's own concern), or exhibit the counterexample so the ADR can state the rule
  the sketch's prose does not yet (§2's second open question).

This is this sketch's proposal, not the plan's commitment: the plan that follows this sketch
fixes the actual sigs, facts and run commands, and may find the shape above wrong once a real
`run`/`check` is attempted.

## 5. Open questions, for the plan

| # | Question | Candidates |
|---|---|---|
| overlap rule | what composition does when two composed schemes share a member with different `broader` parents | forbid by a new Vocabulary shape (simplest, matches ADR-A85's "no OWL axiom silently selects"); allow with one source's hierarchy taking precedence (needs a rule); allow and let `skos:broader`'s own transitive closure merge freely (needs checking it stays acyclic) |
| scope of "composition" | does a composed `Contract` answer stay a Vocabulary-level construct only (a new `voc:` term), or does it also need an Eligibility-level reading, since `insurml-typing.md` §6.1 names "Eligibility's hierarchical match reading the composition (an ADR-A100 addendum)" as a second, dependent change | Vocabulary alone first, Eligibility's addendum as a follow-on once the Vocabulary ADR is accepted |
| who writes the shared ADR | `insurml-alignment.md`'s own IMA-D4a row says "a Vocabulary ADR shared with CCS HQ-4" | this track's job is the checked model the ADR cites as evidence, not drafting the ADR itself, which is a human decision this sketch does not take |
| toolchain | Alloy Analyzer (a single JAR, Java 25 already available via `mise`, MIT licensed) | install and smoke-test as C1, the plan's first slice, same shape as track D's D0 |

## 6. Non-goals

Slot exclusivity and exhaustiveness by SMT (C3, CCS C13a — a separate slice, separate tool).
Writing the shared Vocabulary ADR itself (a human decision, informed by this model, not taken by
it). Any ontology change (`ontology/vocabulary/`, `ontology/eligibility/`) — this track produces a
checked model and a recommendation, not a merged ontology edit, until an ADR accepts it.
