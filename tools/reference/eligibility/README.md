<!-- SPDX-License-Identifier: MPL-2.0 -->

# Eligibility's reference semantics (track B1/B2)

A hand-written, independent Python reference for Eligibility's logic kernel and denotation
(`ontology/eligibility/README.md` §6, laws L9-L16), differentially tested against
`tools/mork_compilers`' SPARQL and SHACL backends, for the formal-methods epic's track B
([sketch](../../../docs/developer/sketches/formal-methods-track-b.md),
[plan](../../../docs/developer/plans/formal-methods-track-b.md),
[ADR-A-FM3](../../../docs/architecture/decisions/ADR-A-FM3-reference-evaluator-home-and-scope.md)).

## What this is, and is not

- **`kernel.py`** is a direct port of `tools/proofs/eligibility/KernelLaws.thy`'s statements
  (`or3`, `and3`, `neg3`, `decision_leq`, and `Eligibility.thy`'s `some_value`/`every_value`) —
  same names, same case tables, restated in Python so Eligibility's compilers have an independent
  oracle to be checked against. Track E already proved TA1 (`or3`/`and3` monotone in both
  arguments) and TA2 (`neg3` involutive, monotone, fixes `Undetermined`) of the Isabelle original;
  this module is verified by test (`tests/test_kernel.py`), reproducing the same claims by
  exhaustive enumeration over the three-valued domain where the domain is small enough to make
  that a complete check, not merely an example.
- **`denotation.py`** is the single-candidate decision procedure for `elg:ExactMatch`,
  `elg:SetMembership` and `elg:HierarchicalMatch` (laws L9-L12, L14), and the set-reading and
  negation composition on top of it (L15, L16). It was written directly from
  `ontology/eligibility/README.md` §6's law prose, then cross-checked against
  `tools/mork_compilers/src/mork_compilers/eligibility_ir.py`'s `_expand` function only to confirm
  no case was missed — not copied from it. `_expand` is what every compiler backend (SPARQL,
  SHACL, SWRL, OWL) ultimately reads (directly or via its "Expanded" form, ADR-A89), so an
  independent reference that imported it would be comparing `_expand` against itself: B2's
  differential tests would never be able to catch a mistake in `_expand` shared by every backend.
- **Not implemented here**: `elg:IntervalContainment` (L4-L5, a different plan kind,
  `IntervalPlan`, not in track B1's scope per the plan), evidence-path reading from RDF, profile
  aggregation (`elg:AllRequired`/`elg:AnySufficient`, L6-L8). B1 decides a condition's outcome from
  already-extracted Python values (candidates, required/excluded sets, a scheme's membership and
  ordering), not from an `rdflib.Graph` — reading a condition's own declarations out of RDF is
  `tools/mork_compilers`' job (`eligibility_ir.py`); `tests/test_differential.py` (B2) is where
  this reference meets that extraction, for differential testing against the real compilers.
- **`tests/test_differential.py`** (B2) runs `decide_concept_match` against `tools/mork_compilers`'
  compiled SPARQL (executed, not inspected as text) and SHACL (validated with pySHACL), reusing
  that package's own fixtures (`DIAGNOSES`, `ENTITLEMENT`) and one real Eligibility example
  (`ontology/eligibility/examples/flat-scheme-lending.ttl`), rather than duplicating them. Found,
  and fixed in `denotation.py`: the first version of `decide_concept_match` never checked whether
  a candidate was a member of the resolved scheme at all (L9's "restricted to that scheme's
  members"), so a candidate entirely outside the scheme could be wrongly Denied instead of
  Undetermined — caught by comparing against the compilers' own `exe:OutsideScheme` handling, the
  reason an independent oracle exists.
- **Never runs against the live graph** (ADR-A-FM3, restating epic principle E3): this package is
  a test-time oracle only, imported by its own tests and by B2's differential-test suite, never by
  a runtime path.

## What each tested backend is claimed to preserve (B2.1)

The differential harness tests two of the four compiler backends (`tools/mork_compilers`'
SPARQL and SHACL), by design (track B's sketch §3): SWRL and OWL refuse more than this harness
exercises, by their own documented restrictions, and are out of scope until they do not. Each
tested backend projects the reference's three-valued `{Permitted, Denied, Undetermined}` result
differently, and the projection each one is claimed to preserve is stated here, not left implicit:

- **SPARQL**, executed with **rdflib** (the engine the differential harness actually runs
  against, not a production store — a different engine's semantics, for example around `IF`,
  `COUNT` over unbound values, or blank-node handling, is untested by this harness), preserves the
  full three-valued result directly: the compiled query's own result column names one of
  `Permitted`, `Denied` or `Undetermined` (`exe:` individuals), so the comparison is exact, with
  no projection at all.
- **SHACL**, validated with **pySHACL**, is a conformance check, not a three-valued query: it
  reports conforms/does-not-conform plus a results graph. The compiled shapes encode the
  three-valued result as structure (an admitted-members list, an undetermined-members list;
  `shacl_backend.py`'s own `admitted`/`undetermined` lists), which `tools/mork_compilers`' own
  `shacl()` test helper reads back into the same three-valued vocabulary this harness compares
  against — so what is actually tested is that reconstruction agreeing with the reference, not raw
  SHACL conformance alone.

## Adjudication log (B2.1)

Every reference/compiler disagreement this harness has found gets a record here: which side was
wrong, and the normative citation that settled it — never "the compiler says so" alone, since
correcting the reference by reading the compiler's own implementation erodes the independence the
reference exists to provide.

| Found | Disagreement | Which side was wrong | Normative citation |
|---|---|---|---|
| B2 (2026-10-07) | a candidate outside the resolved scheme entirely, under hierarchical match | the reference (`decide_concept_match` checked ancestry but never scheme membership) | L9: "restricted to that scheme's members," `ontology/eligibility/README.md` §6 |
| B2 (2026-10-07) | `SingleValue` reading with more than one candidate | the reference (took `values[0]` regardless of count) | the compiler's own SPARQL template (`exe:SeveralCandidates`) at the time — **recorded here as a reminder that this adjudication's citation is weaker than the others**: it was settled by reading the implementation, not a README law, and should be revisited if `ontology/eligibility/README.md` is ever extended to state `SingleValue`'s several-candidates case directly |
| B2.2 (2026-10-09) | hierarchical match with no resolved scheme at all | the reference (fell through to the unmatched-required branch and returned Denied) | L9 (amended 2026-10-09: "a condition... with no resolved scheme at all has no closure to test a candidate against, and is undetermined for every candidate"), `ontology/eligibility/README.md` §6 |



```bash
mise exec -- python -m pip install -e ./tools/reference/eligibility[test]
mise exec -- python -m pytest tools/reference/eligibility/tests -q
```
