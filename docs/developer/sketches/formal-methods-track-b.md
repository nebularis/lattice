<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track B: the reference semantics and the oracle (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track B
**Status:** sketch, 2026-10-07. Nothing here is ratified
**Reads with:** [reference-evaluator.md](reference-evaluator.md) (the full track B/B4 and track E
design, §1-§7), [formal-methods.md](formal-methods.md) §8.4 (Eligibility), §8.8 (Surface, MORK,
Persistence), [formal-methods-track-c.md](formal-methods-track-c.md) (the sibling track's sketch,
same phase-document shape)

## 1. Why this, and why now

The epic's own stagger (epic plan §3) puts B1 and B2 "now, alongside the spike and CCS," with no
dependency on CCS's main-branch progress at all — unlike B4 (the evaluation-context reference and
C12's conformance kit), which waits on CCS's C11a (merged, done) **and** C12 (not yet built,
several CCS slices away, confirmed by reading `main` directly on 2026-10-07). This phase scopes
only what is ready now: **B1, B2 and B3**. B4 is named for completeness (§6) and left for its own
later phase document, exactly as track E left E1.3 for track C to unblock.

Track B's job, stated once in the reference-evaluator sketch and not restated here: the compilers
(SPARQL, SHACL, SWRL, OWL backends today; CCS's C12/C13 tomorrow) can only be compared with each
other until something independent states what they are all claiming to compute. A hand-written
Python reference, with its semantics stated precisely in the literate README, is that independent
statement. It is not a proof. Differential and property tests against it are track B's job; track
E mechanises the same statements later, where it proceeds, as a cheaper formalisation of the
reference than of prose (reference-evaluator.md §1).

## 2. B1: the kernel and Eligibility's denotation, in Python

**What exists already, read before proposing anything new:** `tools/proofs/eligibility/` (track
E) already mechanises the same three-valued kernel in Isabelle/HOL — `KernelLaws.thy`'s
`or3`/`and3`/`neg3` and `decision_leq`, `Eligibility.thy`'s `some_value`/`every_value` and their
monotonicity (TL1-TL3b), `Adequacy.thy`'s 15 fixture lemmas matching
`tools/mork_compilers/src/mork_compilers/test_set_readings.py`'s `MIXES` data. No Python reference
exists anywhere today: the compilers' own tests (`test_set_readings.py` and siblings) assert
against SPARQL/SHACL query results directly, never against an independent hand-written function.
B1 writes that function, for the first time, which is exactly the gap the reference-evaluator
sketch names.

**Scope**, from Eligibility's law register (`ontology/eligibility/README.md` §6) and the
conditions table (`tools/mork_compilers/README.md`):

| Law | What it states | B1 covers it as |
|---|---|---|
| L9 | hierarchical match closure (reflexive-transitive closure of `skos:broader`, restricted to the bound scheme's members, acyclic) | a closure function over a scheme's membership and ordering |
| L10 | exclusion precedence (an excluded match never satisfies, even if also required) | a rule in the single-candidate decision function |
| L11 | exclusion granularity (strictly above an excluded concept, otherwise admitted, is Undetermined) | the same function's third case — B2's named negative fixture (§3) exercises exactly this law |
| L12 | default inclusion (exclusions only, no required concept, admits every unexcluded member) | the same function |
| L14 | hierarchy precondition (no broader member anywhere in the resolved scheme: Undetermined before L12 applies) | a guard checked before L9-L12's closure runs |
| L15 | set readings (`SomeValue`/`EveryValue` over several values, combined by strong Kleene logic) | `some_value`/`every_value`, ported from the Isabelle kernel's own names and statements, not reinvented |
| L16 | negation (swap Permitted/Denied, Undetermined unchanged) | `neg3`, the same function the kernel already proves involutive and monotone (TA2) |

B1 is a faithful **port** of the Isabelle kernel's statements into Python, not an independent
re-derivation — cheap to write, and the two representations of the same law disagreeing is itself
a finding worth having, caught by comparing fixture outputs. Where Eligibility's prose says more
than the kernel formalises (L9's closure, L14's guard, the condition/profile layer above the
kernel), B1 writes it directly from the README's own words, matching Isabelle's `Eligibility.thy`
docstring convention: the statement's wording is kept close enough to `ontology/eligibility/README.md`'s
own that a later reviewer can align them without guessing.

**What B1 is not**: a model of `ConceptPlan`/`IntervalPlan`/`ProfilePlan`, the IR the compilers
share (ADR-A89) — that IR is itself one more artefact to check against the reference, not part of
the reference. B1 decides conditions and profiles directly from their RDF declarations (candidate
concepts, scheme membership, value readings, negation), the same inputs the compilers read,
without routing through their shared plan representation.

## 3. B2: differential tests against the existing compilers

Runs B1 against `tools/mork_compilers`' SPARQL and SHACL backends — the two backends the sketch's
own compiler-correctness claim is scoped to (`formal-methods.md` §8.4: "SPARQL first, over a
formal semantics of the algebra fragment the compiler emits"). SWRL and OWL are included only
where they do not already refuse the input by their own documented restrictions (SWRL assumes one
candidate per question and currently refuses negated set-reading conditions "until AIR-3.3", the
OWL backend refuses a plan without a hierarchy) — B2 tests what each backend claims to compute,
not more.

- **Fixtures**: the existing `MIXES`-style fixture family (`test_set_readings.py` and its
  siblings) reused, not duplicated, plus shape-derived generators (property-based, from
  `ontology/eligibility/shapes/constraints.ttl`) producing conditions and profiles at random
  within the shapes' own constraints.
- **The named negative fixture** the epic plan calls for (B2's own row, `formal-methods.md` §4):
  hierarchical match with exclusions, under L11 specifically — evidence that an exclusion applies
  may move a candidate's outcome only from Undetermined, never from Permitted. The property is
  checked, not merely illustrated: generate candidates at every position relative to an excluded
  concept in the hierarchy, and assert the exclusion's effect never promotes a Permitted
  candidate.
- **"Not a value" first** (sketch §8.4's own ordering): the compiler's and the reference's
  agreement on unbound variables, absent solutions and `FILTER` errors all mapping to Undetermined
  is the first thing B2 checks, before any law-by-law comparison, matching the sketch's own stated
  priority.

## 4. B3: a property test for Surface (MORK and MCN deferred)

Three items are named in the epic plan's B3 row (`formal-methods.md` §4, sketch §8.8). This phase
builds only the first, by our own call (2026-10-07): MORK's lattice-law claim has always
been the least certain of the three, worth confirming properly in its own slice later rather than
carried along here on the strength of a plausible-looking docstring:

| Item | This phase? | Why |
|---|---|---|
| regeneration as naturality (ADR-A27) | **yes** | `tools/surface/src/surface/invalidation.py` already implements `RegenerationPlan` and minimal-scope planning; `test_regeneration_is_deterministic` already exists. The property itself — regenerating after a change equals applying the change's image to the old output — is not yet stated as a property test (only as example tests), which is exactly B3's job. ADR-A27 itself already requires this: "Fixture tests are required to demonstrate minimal-scope regeneration before this policy is considered discharged, not merely stated" |
| MORK's lattice laws (the intent graph is a join-semilattice; co-occurrence axioms reject exactly the incomplete mappings) | **no, deferred by our own call** | a questionable claim as it stands — `IntentNodeSpec.refines` (`tools/mork/src/mork_schemas.py`) and `mork_validation.py`'s co-occurrence checks exist, but whether the refinement relation actually forms a join-semilattice has not been confirmed against the code, and is not this phase's job to find out. Left for a later slice to state and check properly, not carried here on an assumption |
| MCN's round trip through RDFC-1.0 (decode after encode is the identity up to graph isomorphism) | **no, found blocked** | `tools/mork/src/mtp/mcnio.py`'s `NullTool.encode()` returns `None` — there is no RDF-to-MCN encoder anywhere in the repository today (confirmed also by `docs/developer/sketches/mtp-implementation-plan.md`: "MCN encoder (spec §15, RDF → MCN) | **Not built**"). A round-trip property needs both directions |

B3 therefore covers only the Surface item this phase. MORK's lattice laws and MCN's round trip
are both recorded as deferred, for different reasons (one a premature claim, the other a missing
encoder), with their own lines in the plan's dependency table, rather than this track inventing
work nobody asked for or asserting a property nobody has confirmed.

## 5. The ADR this track needs

The epic's own dependency table (`formal-methods.md` §3) names "its ADR" as track B's
prerequisite, the same shape as track A's A1. Proposed content, to be drafted as the first action
of the phase (not here — this is a sketch, not the ADR):

- **Home.** A new top-level tool package, `tools/reference/`, one subdirectory per layer
  (`tools/reference/eligibility/` first), parallel in spirit to `tools/proofs/` (mechanised
  theories) and `tools/models/` (design-time models) but for a third kind of artefact: a
  hand-written executable oracle, verified by test, not proved and not merely checked at a bounded
  scope.
  Naming it `reference` rather than `oracle` matches the reference-evaluator sketch's own
  vocabulary throughout.
- **Scope for this ADR**: B1-B3 only. B4 (the evaluation-context reference, `DesignEnv`/`RunEnv`,
  the rounding and residual rule, conformance kits for C12) is explicitly out of scope until CCS's
  C12 is far enough along to brief against, and gets its own ADR extension when that phase starts
  — not decided now, by this track, ahead of the CCS work it would otherwise have to guess at.
- **Restates E3** (no generated OCaml or Haskell runs against the live graph; the reference
  evaluator is no exception — it is a test-time oracle, never a runtime path) and **E1** (the
  literate README stays the one normative source; B1's Python module states the law it implements
  in its own docstring, close enough in wording to `ontology/eligibility/README.md`'s own that the
  two can be aligned by inspection, the same discipline the Isabelle kernel already uses).
- **Numbering**: continues the non-colliding `A-FM` block (`ADR-A-FM3`), for the same reason
  ADR-A-FM1/ADR-A-FM2 do — this epic's branch and the concurrently active CCS/insurml-alignment
  work on `main` both draft ADRs in real time, and a plain next-number would collide on merge.

## 6. Out of scope for this phase (named, not detailed)

**B4**, the evaluation-context reference and Behaviour's macrostep reference, with the rounding
and residual rule (RE6, reference-evaluator.md §3) and CCS C12's conformance kit. Confirmed
blocked by reading `main` directly: CCS's C12 is "waiting," blocked on C9, C11, C11a, AIR-3.3 and
NRS N1, several tranche-D slices away from being briefable. Left for a later phase document, the
same rolling-wave discipline track E used for E1.3 (blocked on track C's C2) and track C used for
C3 (blocked on CCS C13a).

**A finding worth recording now, for whoever starts B4 later**: the reference-evaluator sketch's
RE6 and RE-Q4 state that the rounding and residual-allocation rule for `split`/`proRata` belongs
to the evaluation context's combinator algebra (B4), with a leaning already recorded ("largest
remainder, with ties broken by a total order of accounts, declared per combinator use") — **not**
to Quantification's ontology, where track E's E1.2 went looking for it and found nothing
(`formal-methods-track-e.md` status, "blocked, not merely unstarted"). This is the answer to
E1.2's open question, read directly from a sketch already in the repository, not inferred: the
theorem belongs with track B's own B4 and track E's own E3/E4 (the combinator algebra and the
evaluation context), not with Eligibility's or Quantification's kernel. Track E's own status
record should be corrected once this phase's sketch is accepted, not held open on a question this
sketch already answers.

## 7. Non-goals

Mechanising B1 or B3's properties in Isabelle (track E's job, later, where it proceeds). Changing
`tools/mork_compilers`, `tools/surface` or `tools/mork`'s own production code to make a property
hold — B2 and B3 find disagreements and report them; fixing what they find is the owning tool's
own slice, not this track's. Building an MCN encoder (§4) — named as a gap, not undertaken here.
Stating or checking MORK's join-semilattice claim (§4) — deferred by our own call, a
later slice's job, not assumed true here.
