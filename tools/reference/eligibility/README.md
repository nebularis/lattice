<!-- SPDX-License-Identifier: MPL-2.0 -->

# Eligibility's reference semantics (track B1)

A hand-written, independent Python reference for Eligibility's logic kernel and denotation
(`ontology/eligibility/README.md` §6, laws L9-L16), for the formal-methods epic's track B
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
  `tools/mork_compilers`' job (`eligibility_ir.py`), and B2 (not yet built) is where this
  reference meets that extraction, for differential testing against the real compilers.
- **Never runs against the live graph** (ADR-A-FM3, restating epic principle E3): this package is
  a test-time oracle only, imported by its own tests and by B2's differential-test suite, never by
  a runtime path.

## Install and test

```bash
mise exec -- python -m pip install -e ./tools/reference/eligibility[test]
mise exec -- python -m pytest tools/reference/eligibility/tests -q
```
