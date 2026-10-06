<!-- SPDX-License-Identifier: MPL-2.0 -->

# Scheme composition (track C2)

An Alloy model checking two properties of **scheme composition** — a Vocabulary contract resolving
to a *set* of `voc:ConceptScheme`s in a context, with membership and `skos:broader` hierarchy the
union of theirs — ahead of the shared Vocabulary ADR that CCS's HQ-4 and insurml-alignment's
IMA-D4a both wait on. See the
[track C sketch](../../../docs/developer/sketches/formal-methods-track-c.md) for the full problem
statement and [the plan](../../../docs/developer/plans/formal-methods-track-c.md) for this slice's
scope and validation criteria.

## What the model is not

It does not mechanise [ADR-A85](../../../docs/architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md)'s
resolver (candidate bindings, specificity, conflict) — `tools/vocabulary/` already implements that,
and its properties (determinism, reported conflict, unscoped fallback) are assumed to hold of each
`Source`'s own resolution before composition does anything with the result. `single` stands in for
the whole of that resolver, collapsed to "at most one scheme, per source, per context" (Alloy's
`lone`). The model does not touch SHACL structure, `boundScheme`'s precedence-tie rule, or
Eligibility's own hierarchical-match reading of a composition (`insurml-typing.md` §6.1's dependent
follow-on, out of this slice's scope).

## Run it

```powershell
# Alloy Analyzer 6.2.0, a single JAR, installed locally (not tracked in this repository):
# https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar
java -jar <path-to>\alloy.jar exec SchemeComposition.als
```

Needs a JDK new enough to run Alloy's own dispatcher (confirmed working under OpenJDK 25). `exec`
writes a `SchemeComposition/` directory next to the model: one `<check-name>-solution-N.md` per
counterexample found, and a `receipt.json` with every command's structured result.

## Results (2026-10-06, Alloy 6.2.0, scope 4)

| Check | Result | Reading |
|---|---|---|
| `EverySourceResolves` | **UNSAT — no counterexample** | every source that resolves alone under ADR-A85 still resolves under composition (HQ-4's own property, "every role a layer needs resolves"), confirmed up to scope 4. This is a self-consistency check on the model's own definition of `composed` (the union, by construction, contains every source's own resolution) rather than a deep claim, and is recorded as such |
| `NoOverlapDisagreement` | **SAT — a counterexample found** | the union-of-members, union-of-hierarchies proposal does **not**, by itself, rule out two composed schemes disagreeing about a shared concept's `broader` parent |

`NoOverlapDisagreement`'s counterexample (`SchemeComposition/NoOverlapDisagreement-solution-0.md`,
`receipt.json`), read directly rather than only reported as a pass/fail count: two schemes
(`Scheme$1`, `Scheme$2`) share the same two members (`Concept$0`, `Concept$1`); `Scheme$1` records
`Concept$1`'s own broader parent as `Concept$1` itself, `Scheme$2` records it as `Concept$0`. A
contract whose composed answer in one context includes both schemes would then have no single
answer to "what is `Concept$1`'s broader parent" — exactly the disagreement the track C sketch's
open question (§2, §5) named without yet knowing whether it was reachable.

**Finding, for whichever ADR accepts scheme composition:** the overlap rule cannot be left
unstated. The checked candidates (sketch §5) are: forbid overlapping membership between composed
schemes by a new Vocabulary shape (closest to ADR-A85's own "no OWL axiom silently selects," and
the simplest to state); let one source's hierarchy take precedence over another's on a shared
concept (needs an explicit precedence rule, parallel to ADR-A85's specificity ordering); or allow
free union and require `skos:broader`'s transitive closure to stay acyclic, deferring disagreement
to whatever reads the hierarchy (weakest guarantee, cheapest to state). This model does not choose
among them — that is the human's decision, informed by this evidence, not this track's to take.
