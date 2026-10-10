<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track H: the specification registry and the typed IR (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track H
**Status:** sketch, 2026-10-08. Nothing here is ratified
**Reads with:** [the main track H sketch](formal-methods-track-h.md) (§3's four kinds of content,
which this sketch turns into data), [persistence-fml.md](../notes/rdf-engine/persistence-fml.md)
§7 (exhaustive validation), §8 (templates), §12 (static/value-level checks), §13 (generation)

## 1. The enabling move, stated once

Review §13.1's own judgement, adopted here without qualification: **generate the rules, the
registry, the IR and the emitter, do not generate the resolver.** The resolver is a hundred lines
of a pure function over a finite lattice — proving it (Isabelle, H6) is cheaper than generating
it, and keeping a hand-written resolver plus an independently generated checker gives translation
validation for free (two implementations is a feature here, provided one is derived from a
specification and they are diffed, never a maintenance burden). Everything *tabular* — the
dimension registry, the cross-axis rules, the operation-selection table, the template library's
own structure, the minting recipes, the audits — is generated instead, because five hand-written
copies of one table (the README, the ontology, the compiler, the shapes, the guide's own tables)
is four drift sources, and this is exactly the drift the review found at least once already (its
finding #3: the cross-axis rules exist twice today, in `shapes/constraints.ttl` and in the
compiler, with a known, undocumented asymmetry).

This is the same direction FM-D12 already decided for the rest of this epic ("the literate README
is the one source, generating shapes and the theory's closed datatypes"), extended here to a
second tool (`tools/persistence`) and a wider class of generated artefact (rules and tables, not
only datatypes) — exactly the kind of widening the epic's own second review recommended as FM-D17
for the Eligibility kernel (`formal-methods-more-feedback-response.md` §6). Track H and FM-D17 are
independent decisions about the same principle applied to two different tools; neither depends on
the other being accepted first.

## 2. The specification artefact (proposed shape, not yet built)

One machine-readable registry, Turtle or a validatable tabular format (the review's own example,
§13.2, uses a compact pseudo-syntax; the actual syntax is this slice's own design question, not
pre-decided here), from which are generated:

| Generated | From | Replaces |
|---|---|---|
| `shapes/constraints.ttl`'s cross-axis rules | the registry's rule entries | hand-written SHACL, today's second of two copies |
| the compiler's validation predicate and selection table | the same entries | hand-written Python, today's first of two copies |
| Isabelle definitions (H6) and the exhaustive-validation BDD/SMT input (§4 below) | the same entries | nothing today — these do not exist yet |
| the README's own rule tables | the same entries | hand-written prose tables, a documentation-drift source today |
| the obligation set per generated operation (caller/housekeeping/store) | a new registry field | nothing today — the review's own PV-D2, the largest unverified surface in the whole layer |
| the laws-held list per compiled target | the per-dimension `guarantees`/`forfeits` fields | nothing today |

**What is not generated:** the resolver itself (§1), any ontology content, any protocol model
(those are hand-written per family, track C's and this track's own §4 of the protocol-models
sketch).

## 3. The typed intermediate representation

The single highest-leverage code change the review names (§13.4), because it removes whole defect
classes by construction rather than testing for them after the fact. Give the compiler an IR for
a generated operation: typed parameters (`IRI`, `Long`, `String`, `LangString`, `Payload`,
`Position`, `Digest`), a declared read set and write set (which the protocol models consume
directly as their own read/write sets, closing the loop between this slice and H5), guards tagged
`Term` or `Value` (closing the term-versus-value-comparison divergence the review found at §8.2),
and template variables tagged `Bound` or `OptionalAllowed`.

| Hazard the review found | How the IR removes it, by construction |
|---|---|
| injection (an untyped string reaching query structure) | parameters are typed terms; there is no path from a string to structure |
| untyped position literals | a `Position` parameter always renders through its declared width and datatype |
| an INSERT-template variable that may be unbound in some solution | `Bound` vs `OptionalAllowed` is a type; the renderer refuses an untagged variable |
| blank nodes inside an INSERT template (a retry is not then a no-op) | no blank-node constructor in the IR at all |
| a property path inside a template (illegal; parse failure today only at render time) | paths are a read-set-only construct in the type system |
| an unnamed graph, or reliance on the default graph | every pattern carries an explicit graph role |
| unbound `GRAPH ?g` in an audit or resume query | bucket sets are a typed `RegistryList` parameter, never a free variable |
| a `FILTER`-value comparison on a term-invariant position, or the reverse | `Guard` is tagged `Term`/`Value`; the renderer refuses the wrong one on the wrong position |
| `NOW()` inside a guard | no clock constructor except in an explicitly audit-only position |
| a missing template parameter | the IR's own parameter list is the renderer's domain; completeness is a type check, not a runtime surprise |

### 3.1 From aggregate ownership (2026-10-10)

The [aggregate-ownership sketch](persistence-aggregate-ownership.md#12-what-h2-inherits) adds three
things to the IR, decided (H-D14) after the
[review](../notes/persistence-aggregate-ownership-review.md) of the
[exploration note](../notes/persistence-aggregate-ownership.md) and
[its spike](../../../spikes/persistence-aggregate-ownership/README.md).

| Addition | Hazard it removes |
|---|---|
| the `OwnershipTree` and its compiled `PropertyPath` as typed values. A path parameter is built only from encoded IRIs and a fixed set of operators | a closure that depends on how a shape was written, and a path assembled from strings |
| a payload check: every payload subject is the root or reached from it through owned steps. The IR states it and the runtime caller enforces it, since a payload is a request-time slot | a payload that writes into another aggregate or into reference data |
| a required-parameter guard (H-D12, option D) | TD-34, a partial write when a parameter is missing |
| a composite operation's read set is the closure its path computes at execution, and its write set the delete set, the payload and the version row | protocol models that assume a fixed read set for a write (model A) |
| an explicit graph role for every composite pattern, the profile's named data graph (AO-Q14, decided option a) | TD-40, composite operations that rely on the default graph against static check S-1 |

H2's typing of the closure starts after HO5, when the tree replaces the old walk.

## 4. Exhaustive cross-axis validation, once the registry exists

The cross-axis validation predicate is propositional over finite domains (review §7.1-§7.2):
roughly 1.3×10⁸ combinations before shard-count and identity-role multiplicities, small for a BDD,
too large to sample meaningfully. Ten properties to check exhaustively once the registry is data
(review §7.3, table V1-V10), the two most important named here and the rest left at the review's
own level of detail until this slice starts: **V2** (no combination is both refused by the shapes
and accepted by the compiler, or the reverse — the drift finding #3 found by example, checked
universally instead) and **V10** (every combination that forfeits a guarantee is at least warned,
with the warning naming the specific law it forfeits — directly closing the review's finding #5,
the three default-unsafe baselines that are warned but not gated).

## 5. Non-vacuity, stated once, applied everywhere

The single cheapest technique in the whole review (§7.4), adopted as a standing rule for every
artefact this track touches, not only its own new ones: **for every constraint, refusal, warning,
shape and audit query, a witness fixture that triggers it, generated and checked.** This would
have caught, in seconds, two of the review's own calibration-table defects (D.3 A6's never-firing
fork shape, D.1's `sh:prefixes` defect). Applied to: every SHACL shape (a violating and a
conforming fixture each), every compiler refusal/warning (a configuration fixture — `examples/`
already has many, the obligation is *every* rule has one, checked by coverage), every audit query
(a store state in which it fires). A rule or shape with no witness is a build failure, the same
discipline `tools/check_formal_freshness.py` already applies to Eligibility's laws, extended here
to Persistence's own rule set.

## 6. Static and value-level checks (SMT, automata)

Small, local, fully automatic, run per compile, each tied to a named policy or a recorded defect
(review §12, full table). The four to build first, because they catch a live finding each: the
prefix antichain/overlap check (main sketch's L3 gap — two scopes with different resolved values
matching one instance), the IRI-template injectivity check (Z3 strings: a template's inverse
parser must recover exactly the parameters that produced it), the width-adequacy check (a
declared `epochWidth`/`sequenceWidth` must fit the datatype's own maximum, preventing the review's
own recorded two-widths defect, B13), and the template-variable-discipline check (S-3/S-4: every
INSERT-template variable bound in every solution, no blank nodes in a template — cheap, static,
and the single highest-severity-to-cost static check in the whole review).

The aggregate-ownership design (2026-10-10) adds three to H4's list: the source review's C10 restated
as equality of the compiled path's language and the shape graph's owned-path language (automata, with
no depth bound since depth is gone), the IRI-template injectivity check extended to named-graph
templates across families (review F11 of the ownership review), and C14's request bound with the
largest declared aggregate, since whole-replace sends it all ([ownership sketch §15.1](persistence-aggregate-ownership.md#151-solvers-and-provers-in-summary)).

## 7. Non-goals

Any ontology change. Any protocol model (the protocol-models sketch's own job). The resolver's own
mechanisation (Isabelle, a later slice, H6, outlined in the plan only). Deciding the registry's
exact serialisation syntax here — left to the slice that builds it.
