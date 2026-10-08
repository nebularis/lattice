<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track H: Persistence (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track H
**Status:** sketch, 2026-10-08. Nothing here is ratified. [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(home and scope) is Proposed, not yet accepted
**Source:** [persistence-fml.md](../notes/rdf-engine/persistence-fml.md), an independent,
exhaustive review applying this epic's own techniques to the Persistence layer. Its section
numbers are cited as "review §n" throughout this sketch and its siblings
**Reads with:** [the protocol-models sketch](formal-methods-track-h-protocols.md) (rung T4, the
centrepiece), [the specification-registry sketch](formal-methods-track-h-specification.md) (the
enabling move), [formal-methods.md](formal-methods.md) §5 (the techniques, by cost), §8 (layer by
layer — Persistence's own row is thin and this track replaces it), the engine notes this review
answers: [compiled persistence profiles](../notes/rdf-engine/compiled-persistence-profiles.md) and
the RDF/SPARQL patterns guide it cites throughout
**Explicitly excludes:** any relational or SQL-compilation work (the separate review at
[sql-feedback.md](../notes/rdf-engine/sql-feedback.md), "paper 5"). See §2 below

---

## 1. Why Persistence, and why now

Tracks B, C and E have so far targeted exactly one layer, Eligibility, and the second review of
this programme ([response](../notes/formal-methods-more-feedback-response.md) §2, review Q5)
makes a fair point: one layer's evidence that three techniques work together is not evidence they
work *in general*, especially since Eligibility is close to a best case for them — a finite
three-valued kernel, decidable case analysis, no concurrency anywhere in sight.

Persistence is a different kind of layer entirely, and that is exactly its value as the next
target:

- **Its specification is already mostly written down and tabular.** Dimensions with enumerated
  values, a baseline per dimension, a precedence algorithm, a refusal/warning table, an
  operation-selection table, a template library, an outcome table (review §1.1). Most of the
  expensive part of formalisation — recovering intent from code — is already done by the
  Persistence engine notes and the compiler's own structure.
- **Its defect history is exactly what cheap techniques catch, and nothing in tracks B/C/E's
  toolkit would have caught most of it.** Three recorded remediation passes (the engine notes'
  own Appendix D) found, over months, a guard that can never match, a shape that can never fire, an
  audit query that cannot detect the loss it claims to detect, a fencing token checked but never
  advanced, an unbounded read that skips a committed write, a digest never computed, a retention
  rule that prunes a live head. Review §1.3 tabulates eleven of twelve such defects against the
  technique that finds each in minutes to hours. **None of the eleven is a T0/T2/T5 problem** (the
  only rungs tracks B, C and E have exercised) **— every one is T4 (a protocol/liveness property)
  or a vacuity/completeness check T0 already covers but Eligibility never needed.**
- **It forces the verification to be parametric**, which the epic's own cost ladder has always
  named but never had to act on: the honest statement of correctness here is not "the generated
  SPARQL is correct" but "for this backend's capability profile, this strategy delivers this
  guarantee level" (review §1.1, point 3). That is a genuinely new shape of claim, a matrix rather
  than a single property, and building the machinery that produces one cell of it is this track's
  first real exercise of the epic's own FP3 ("every claim of assurance names its method, scope,
  bound and assumptions") under conditions where the assumptions actually vary.

**Persistence is therefore a stronger pilot than the alternative the second review itself proposed
(Quantification: arithmetic, rounding, still a sequential, deterministic domain).** It is
structurally unlike Eligibility in the one dimension that matters most for testing whether this
programme's template transfers at all: concurrency.

## 2. Scope, and what is deliberately excluded

**In scope**, following the review's own boundary (its §0 "scope, sources, and how to read this"):
the `dal:` configuration vocabulary (dimensions, scopes, resolution, validation, selection),
`tools/persistence`'s compiler and its generated SPARQL templates and operations, the pluggable
RDF-store backends and their capability profiles (ADR-A75's Core/Extended/Native tiers), the
always-on audits and housekeeping procedures (ADR-A80), and the identity/digest/erasure machinery
`dal:` configures.

**Out of scope, explicitly, for this entire track:**

- **Any relational or SQL-compilation work.** A separate, independent review
  ([sql-feedback.md](../notes/rdf-engine/sql-feedback.md), reviewing a proposal to compile
  LATTICE to a relational model) exists and names its own, different formal-methods programme
  (its own §10): a typed `decision3` IR for SQL's three-valued NULL encoding, Alloy translation
  validation against SHACL shapes, an Isabelle `SqlEncoding.thy`, TLA+ models of PostgreSQL's
  isolation contract, SMT checks for its own regex/IRI-template/range rules. **None of that is
  this track's job.** The two reviews share a family resemblance (both apply the same ladder to a
  persistence-adjacent target) and nothing more; this track does not read the SQL review's content
  as its own scope, and a future relational-compilation formal-methods effort is a sibling track
  with its own ADR, per [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
  decision 1.
- Mechanising SPARQL's semantics in full, or PostgreSQL's (not applicable here) — used
  selectively, for the specific queries where the translation is non-trivial (the as-of query, the
  gap scan, the composite closure), per the review's own §17.3 "what not to do."
- Verifying third-party engines (Jena, RDF4J, Oxigraph, store vendors) — their behaviour is an
  input to this track's capability-record work (§4 below), never its target.
- Building a second conformance/TCK suite from scratch. `tools/persistence`'s existing TCK is
  extended and its coverage made measurable (review §14.3), not replaced.

## 3. The four kinds of content, and the fifteen laws

Review §3.1 identifies four kinds of specification content in the `dal:` material, each wanting a
different technique, already the right shape for this epic's own ladder (`formal-methods.md` §5):

| Content | Character | Technique | Rung |
|---|---|---|---|
| Dimensions, values, baselines | finite enumerations with a default per dimension | typed registry, totality/exhaustiveness checks | T0 |
| Scopes, matching, precedence | a small pure function over a finite lattice, one reasoning-dependent case | Isabelle (determinism, locality, monotonicity); bounded-exhaustive differential | T5/T0 |
| Cross-axis validation | a propositional predicate over a finite product space (≈1.3×10⁸ combinations, review §7.2) | SAT/BDD/SMT, exhaustive, not sampled | T3 |
| Operation selection | a lookup table, dimension → operation set | totality/disjointness check | T0 |
| Templates and their guards | SPARQL text with parameters | typed IR; Alloy for state effects; TLA+ for interleavings; automata for well-designedness | T2/T3/T4 |
| Identity and digests | string functions over Unicode and bytes | Isabelle (injectivity, order); SMT strings; test vectors | T5/T3/T0 |
| Protocols | concurrent, crash-prone, backend-parametric | **TLA+/Quint** | T4 |
| Detection (audits, shapes) | queries claiming to detect violations | Alloy equivalence, witness obligations | T2/T0 |
| Housekeeping and runbooks | procedures outside the compiler | TLA+ for the procedure, monitors for the evidence | T4/T7 |

Fifteen laws, named once (review §2.1, table), state what each stage of the artefact chain
(resolve → validate → select → emit → instantiate → execute → read/audit) must preserve. They are
this track's own register, named L1 to L15 to match the review's own numbering, a sibling register
to Eligibility's L9-L16 and Wording's W1-W8, not a collision with either (each layer and track
keeps its own letter-and-number register, per house convention):

| # | Law | One line |
|---|---|---|
| L1 | Resolution is a function | not of triple order, blank-node labels, file order or machine |
| L2 | Resolution is local | an unrelated profile change leaves other targets' resolution unchanged |
| L3 | Target coverage is a partition | every instance of every configured class belongs to exactly one target — **review finds this false today** (§6.2) |
| L4 | Validation is sound and complete w.r.t. the rule table | the compiler refuses exactly what the table declares unworkable |
| L5 | Selection is total and disjoint | every resolved profile has exactly one operation set |
| L6 | The compiled profile is implemented | every resolved dimension is implemented, a caller/housekeeping obligation, or recorded-only, never silently unimplemented — **review finds gaps today** (§8.4) |
| L7 | Instantiation is substitution | no parameter value can change a query's structure |
| L8 | Operation correctness, sequential | one operation alone preserves the invariants |
| L9 | Operation correctness, concurrent, parametric | **the matrix**: for capability profile *C*, every interleaving preserves the invariants and the declared guarantee level, or the compiler refuses |
| L10 | Outcome soundness | the confirmation procedure's verdict is justified by the history, totally and disjointly |
| L11 | Detection completeness | every invariant has an audit that fires within a stated latency — **review finds nine gaps** (§9.2) |
| L12 | Identity laws | claim/revision/event/key IRIs are deterministic and injective on their declared domains |
| L13 | Erasure boundary | after erasure plus the retention bound, no enumerated store yields the subject's data |
| L14 | Epoch safety | no position/ETag/revision IRI/cursor minted under one epoch is mistaken for another's |
| L15 | Migration/rotation squares | a shard-count, scheme or epoch change commutes with reading |

L1, L2, L4, L5, L7, L8, L10, L12 are cheap (T0/T5) and should be settled by proof or exhaustive
check. **L3, L6, L11 are missing from the design today, not merely from its verification** — this
is the review's own most important distinction (§2.1), and this track's early slices (H1, §5)
target exactly those three first, because they are gaps a proof cannot paper over. L9, L13, L14,
L15 need protocol models and are where the review expects the actual findings (§10).

## 4. The organising idea: a capability × strategy guarantee matrix

The single highest-leverage structural idea in the review (§4), and the reason this track is
worth running as a connected whole rather than a pile of independent checks: everything in
Persistence is conditional on the backend's capabilities, and the honest claim is a matrix cell,
not a flat property.

```
Guarantee(strategy, C) = the strongest level a protocol model preserves under capability profile C
Refuse(family, C)      ⟺ Guarantee(selected(family), C) < declared min_level(family)
```

- The matrix is produced **mechanically**, by model-checking one parametric protocol model per
  pattern family across the capability configuration space (the protocol-models sketch, §4.2).
- It replaces a hand-maintained table (the engine notes' own Chapter 26 store rows, already found
  wrong in at least five cells by Appendix D) with generated evidence.
- It gives the compiler's `min_level` refusal a *reason*, derived from the model: "`PER_STREAM_
  DENSE` requires `detectsWriteWriteConflict ∨ singleWriter`; your TCK report says neither" —
  both a better error message and a reviewable claim.
- It turns "which TCK tests gate which family" from judgement into derivation: the gating tests
  are exactly the TCK tests that discharge the assumptions the family's matrix cell used (review
  §14.3).

This is the idea the rest of this track's slices build toward. H1 to H3 (§5) make the ground it
stands on (a registry of what the rules actually are, a typed IR that cannot emit what the
templates' own hazards need). H4 onward (outlined, §6) build the matrix itself.

## 5. The capability record is the formal environment assumption

Review §4.1: the capability vocabulary `dal:CapabilitySpec` already has (CAS level, reasoning,
commit validation) is strictly narrower than what the protocol models will need as their
assumptions (`atomicUpdateRequest`, `singleWriter`, `detectsWriteWriteConflict`,
`statementLevelConflictDetection`, `multiAggregateAtomicity`, `graphLevelAccessControl`,
`reportsAffectedRows`, the change-feed and time-travel flags, `quadsInUpdateTemplates`,
`unionDefaultGraph`, `requiresSkolemization`, `maxRequestBytes`). Closing this gap (review's
PV-D1: extend to the full capability record, three-valued, `unknown` treated pessimistically,
bound to a TCK report digest) is a prerequisite for the matrix meaning anything, and is this
track's first design-level decision, taken alongside H1 (§5 of the plan).

## 6. Non-goals, for this sketch and all its siblings

Everything named "out of scope" in §2. Mechanising full SPARQL semantics. Replacing
`tools/persistence`'s Python compiler with anything generated wholesale — per the review's own
§17.3 and this epic's existing E3 principle ("no generated OCaml or Haskell runs against the live
graph"), nothing here changes that: generated code from this track's work is data (templates,
specification registries, audit queries), never a runtime substitute for the Python compiler.
Any ontology change to `ontology/persistence/` ahead of a specific slice's own ADR. Any work on
the relational/SQL side (§2).
