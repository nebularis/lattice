<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b3a, set comparisons

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c9b3a-set-comparisons`, examples first (ADR-A-C2), then the model, reference and proofs in one commit and the compilers in a second
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), "C9b3a in detail"
**Decisions:** C9b3-Q2 (a′), C9b3a-Q1 (a), Q2 (c), Q3 (a) and Q4 (a), answered 2026-10-27. [ADR-A136](../../architecture/decisions/ADR-A136-set-comparisons-and-aggregate-bindings.md) (Proposed), [ADR-A103](../../architecture/decisions/ADR-A103-eligibility-set-readings.md), [ADR-A105](../../architecture/decisions/ADR-A105-closure-declarations.md), [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md), [ADR-A90](../../architecture/decisions/ADR-A90-eligibility-design-time-owl-class-backend.md)

## Invariant

A set comparison relates the values two bindings read from one subject, by one of three comparisons whose meaning is the per-value membership decision read by L15. It counts nothing. What it decides follows only from the records and from each set's own closure. A tested value is Permitted when found among the reference values, Denied when not found and the reference binding names a closure in force, and otherwise Undetermined. Subset reads the outcomes as every value, Intersects as some value, Disjoint as some value negated, under the tested binding's closure (L18). A requirement that a set have a member is a count and is not stated by a comparison.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C9b3a-01 | the licensing, trial and bonds examples / the layer's shapes / no result | L1 | + |
| C9b3a-02 | each example / read / two distinct bindings, both naming the comparison, one subject class | L1 | + |
| C9b3a-03 | a comparison naming no concept, and a bare concept condition / the declaration warning / none for the comparison, one for the bare condition | L1 | + − |
| C9b3a-04 | a comparison with no `elg:comparison`, and with two / shapes / reported (zero and above one) | L1 | − |
| C9b3a-05 | a comparison with no tested binding, no reference binding, and a second of each / shapes / reported (zero and above one) | L1 | − |
| C9b3a-06 | one binding named as both tested and reference / `elg:SetComparisonBindingsShape` / reported | L1 | − |
| C9b3a-07 | a reference binding that does not name the comparison / shapes / reported | L1 | − |
| C9b3a-08 | a reference binding over another subject class / shapes / reported | L1 | − |
| C9b3a-09 | either binding with a value reading, and with a value space / shapes / reported (four cases) | L1 | − |
| C9b3a-10 | a third binding naming the comparison / `elg:SetComparisonBindingShape` / reported, and nothing else | L1 | − |
| C9b3a-11 | a comparison matching by set membership, naming a required concept, naming an excluded concept / shapes / reported | L1 | − |
| C9b3a-12 | an ordinary binding naming a closure with no reading / shapes / still reported, the exemption being for a comparison's bindings | L1 | − |
| C9b3a-13 | Subset over neither, one and both closures / the reference / the table of the README | L2 | + − |
| C9b3a-14 | Intersects over the same / the reference / the table | L2 | + − |
| C9b3a-15 | Disjoint against Intersects, every closure combination, four tested sets / the reference / the swap of L16 | L2 | + − |
| C9b3a-16 | an empty tested set under each comparison / the reference / L15's reading, closed and open | L2 | + − |
| C9b3a-17 | hierarchical membership over part-of / the reference / a part of a licensed territory found, the territory above it not | L2 | + − |
| C9b3a-18 | a negated Subset / the reference / Permitted and Denied swapped | L2 | + − |
| C9b3a-19 | hierarchical match with no scheme, and with no applicable binding / the reference / Undetermined | L2 | + |
| C9b3a-20 | each comparison / reliance / the closures that decided: tested, reference, both, neither | L2 | + − |
| C9b3a-21 | the licensing example / SPARQL / lic-1 and lic-4 Permitted, lic-2 and lic-3 Denied | L2 | + − |
| C9b3a-22 | the licensing example with the grant closure removed / SPARQL / the Denied rows Undetermined with `exe:NoClosureLicence` | L2 | + − |
| C9b3a-23 | the trial example / SPARQL / pat-1 and pat-3 Permitted, pat-2 Denied, over a two-step reference path | L2 | + − |
| C9b3a-24 | the bonds example, the reference set open / SPARQL / a holder not found is Undetermined and never Denied, and no holders gives Permitted and Denied | L2 | + − |
| C9b3a-25 | each comparison, neither, one and both closures, five subjects (60 cases) / SPARQL / equal to an oracle written in the test | L2 | + − |
| C9b3a-26 | a few rows of the oracle written out / SPARQL / equal, so a wrong oracle cannot hide a wrong compiler | L2 | + − |
| C9b3a-27 | an empty tested set under each comparison, closed and open / SPARQL / the L15 outcome, or Undetermined with `exe:MissingCandidate` (zero) | L2 | + − |
| C9b3a-28 | a tested value that is part of a reference value / SPARQL / found under hierarchical match, not under exact | L2 | + − |
| C9b3a-29 | a negated Subset / SPARQL / every outcome swapped | L2 | + − |
| C9b3a-30 | a value not found in an open reference set / SPARQL / Undetermined with `exe:NoClosureLicence` | L2 | + − |
| C9b3a-31 | Subset Permitted and Denied, Intersects Permitted and Denied, Intersects over no tested value / SPARQL `?closure` and `?referenceClosure` / the tested IRI, the reference IRI, neither, both, the tested only | L2 | + − |
| C9b3a-32 | both bond comparisons in an AllRequired profile / SPARQL and SHACL / the profile's decision and its closures | L2 | + − |
| C9b3a-33 | the trial comparison in a profile / SPARQL / `?closures` lists both of its closures, one when the tested set is empty | L2 | + − |
| C9b3a-34 | the four example conditions, and 12 closure and strategy combinations of each comparison / SPARQL against SHACL / equal | L2 | + − |
| C9b3a-35 | a hierarchical comparison whose binding applies from 2030 / SPARQL and SHACL at 2026 / Undetermined for every subject with `exe:NoApplicableBinding`, and resolved at 2031 | L2 | + − |
| C9b3a-36 | a comparison / OWL and SWRL / refused, citing ADR-A90 | L1 | − |
| C9b3a-37 | a profile holding a comparison / OWL and SWRL / refused | L1 | − |
| C9b3a-38 | 14 malformed comparisons / compile / each refused | L1 | − |
| C9b3a-39 | a condition that is not an `elg:SetComparison` / compile / refused | L1 | − |
| C9b3a-40 | hierarchical and exact comparisons / the query text / the reference path starts from the bound subject, the walk is a constant path over the named relation, no `skos:broader*` | L1 | + − |
| C9b3a-41 | each comparison / SPARQL / one row and a bound `?decision` per subject, the plan typed `exe:SetComparisonPlan` | L2 | + |
| C9b3a-42 | a comparison / the SHACL shapes / typed `exe:SetComparisonPlan` | L1 | + |
| C9b3a-43 | `Executable.ttl` / read / the plan class declared and disjoint from the other plans, and the pinned diagnostic set unchanged | L1 | + |
| C9b3a-44 | 48 cases (three comparisons, both closures, both strategies, negated or not) / the reference against SPARQL and SHACL / equal, and the `?closure` column equal to the reference's reliance | L2 | + − |
| C9b3a-45 | a compiler that matches exactly under hierarchical match / the differential test / the disagreement is seen | L2 | − |
| C9b3a-46 | a reference value outside the scheme, and a tested value outside it / SPARQL and SHACL / the first matches nothing (Denied), the second is Undetermined with `exe:OutsideScheme` | L2 | − |
| C9b3a-47 | the same in the reference / `decide_set_comparison` / Denied for the reference value, Undetermined for the tested one | L2 | − |
| C9b3a-48 | L18 over the match predicate, equality and part-of, with a value outside the scheme and a scheme with no hierarchy / Isabelle2025-2 / `TS1` to `TS10` and `ASC` proved, gate passes | L3 | + − |
| C9b3a-49 | the README / literate check, formal freshness / consistent | L0 | + |
| C9b3a-50 | a scheme with no link, every comparison and closure combination, and the reference / SPARQL and SHACL / L14: an equal value found, any other member Undetermined with `exe:NoHierarchy` whatever the closures, a value outside Undetermined (zero links) | L2 | + − |
| C9b3a-51 | the same scheme with one link / SPARQL / the unfound member is Denied under a closed reference set | L2 | + − |
| C9b3a-52 | the zero-link scheme, 12 cases / the reference against SPARQL and SHACL / equal | L2 | + − |

## One command

```bash
mise run check:full-sweep
```

The sweep runs `check:mork-compilers` (rows 21 to 43, 46), `check:reference-eligibility` (rows 13 to 20, 44, 45, 47), `check:ontology-catalog` with `test_eligibility_examples.py` (rows 01 to 12 and 49) and `check:formal-freshness`. The compilers' rows run on Oxigraph there. On rdflib and Jena:

```bash
mise run check:mork-compilers-conformance
mise run check:reference-eligibility-conformance
mise run check:proofs -- eligibility
```

To see the new tests alone:

```bash
mise exec -- python -m pytest tools/test_eligibility_examples.py tools/mork_compilers/src/mork_compilers/test_set_comparisons.py tools/reference/eligibility/tests -q
```

## Artefacts to inspect

- `ontology/eligibility/README.md`: section 5.9 (the model and its table), 6.1 to 6.4 (`elg:SetComparison`, `elg:Comparison`, the three properties and individuals), 6.6 (L18), 7.2 (the two shapes and the exemption in the closure shape), 8.6 (the examples), 10, 12 and 13
- `ontology/eligibility/examples/set-comparison-licensing.ttl`, `set-comparison-trial.ttl`, `set-comparison-bonds.ttl`
- `ontology/mork/spec/Executable.ttl`: `exe:SetComparisonPlan`. No new diagnostic
- `tools/mork_compilers/src/mork_compilers/eligibility_ir.py`: `SetComparisonPlan`, `compile_set_comparison`, `read_binding`, `refuse_set_comparison`
- `tools/mork_compilers/src/mork_compilers/sparql_backend.py`: the module docstring's cost statement (STD-020), `_comparison_core`, `_match`, `set_comparison_select`, and `_read_set`'s `comparison` mode
- `tools/reference/eligibility/src/reference_eligibility/denotation.py`: `decide_member`, `decide_set_comparison`
- `tools/proofs/eligibility/SetComparison.thy` and claims `TS1` to `TS10` and `ASC`. Adding definitions changes every claim's digest (gate rule E1.4), so the 22 earlier claim records carry a recomputed digest and no changed statement
- `docs/architecture/decisions/ADR-A136-set-comparisons-and-aggregate-bindings.md` and `docs/developer/mechanisms.md` (MEC-86)

## Deliberate non-coverage

- **Versions.** None moves. `check:ontology-versioning` reports `UNBUMPED` for `Executable.ttl` and the release members, as expected until `release:prepare` runs at the merge (ADR-A129).
- **Literal-valued sets** are refused by a shape on a value space and are not compared (Q3 (a)).
- **Existence** is not stated by a comparison. A count over a binding states it once aggregate bindings are built, and no example or term for it is added here.
- **Aggregate bindings** are decided in ADR-A136 and not built.
- **Measured cost.** The query's cost is stated, not measured, on any engine.
- **The reasoner tests** (`needs_reasoner`) are not relied on by any row.

## Handoff

**Placement:** substrate semantics, laws, proofs and compilers, all open (T0, T1).

**Built:**

- `elg:SetComparison`, `elg:comparison` with the closed class `elg:Comparison` (`elg:Subset`, `elg:Intersects`, `elg:Disjoint`), `elg:testedBinding`, `elg:referenceBinding`, L18, two shapes and the structural shapes, three examples and a release note.
- The IR's `SetComparisonPlan`, the SPARQL and SHACL compilers, and OWL and SWRL refusals.
- The reference `decide_set_comparison` and the Isabelle theory. Under hierarchical match a tested value outside the scheme is Undetermined with `exe:OutsideScheme` (L9), and over a scheme with no link a value not equal to a reference value is Undetermined with `exe:NoHierarchy` (L14), both as the maintainer ruled. A comparison's `?closure` and `?referenceClosure` are two IRI columns.
- ADR-A136 (Proposed) and MEC-86.

**Decisions taken without the maintainer, for countersignature:**

1. **The reference binding's closure is reported as relied on** when a Denied value decided, in its own column, `?referenceClosure`. `?closure` stays the tested binding's closure and a single IRI for every condition. The profile's `?closures` tests both columns with equality.
2. **Values the scheme cannot place** (ruled by the lead): a tested value outside the scheme is Undetermined with `exe:OutsideScheme`, a reference value outside it matches nothing, and L14 applies to a comparison over a scheme with no link. Both are stated once, in L18.
3. **`exe:SetComparisonPlan`** is a new plan class in `Executable.ttl`, a subclass of `exe:ConditionPlan` disjoint from the two others, since a comparison is neither an interval nor a concept match. Accepted by the lead.
4. **`exe:NoClosureLicence`** is reused for a value not found in an open reference set. Its definition ("the outcome needs the records a binding reaches to be complete, and no closure in force licenses that") fits. No new diagnostic.
5. **`elg:ClosureNeedsSetReadingShape` and `elg:ConceptConditionDeclarationShape`** are amended, to allow a closure on a comparison's binding without a value reading and to exempt a comparison from the "states nothing to match" warning. Without them every example would report.
6. **`SetComparison.thy` imports `Eligibility` and `Hierarchy`**, not `KernelLaws` and `Hierarchy`, since `some_value` and `every_value` are defined in `Eligibility`, which imports `KernelLaws`.
7. **Isabelle statements** take the form `subset_decide match A closedA B closedB`. All of TS1 to TS7 were proved as stated in the brief. TS2 reads "Denied iff `closedB` and not `set A ⊆ set B`", as the brief has it.
8. **MEC-86** is added to the mechanism register as not yet ratified.

**What to check first:** `compile_set_comparison` in `eligibility_ir.py`, then `_comparison_core` and `_read_set` in `sparql_backend.py`, then README 5.9 against L18 in 6.6.

## Results

Run on 2026-10-27 in the worktree, against `main` for versions.

| ID | Result |
|---|---|
| 01 to 12, 49 | `test_eligibility_examples.py`: 47 passed. `check:ontology-catalog` in the sweep: 1223 passed |
| 21 to 43, 46, 50, 51 | `test_set_comparisons.py`: 26 passed, 14 subtests. `check:mork-compilers`: 195 passed, 44 subtests |
| 21 to 43, 46, 50, 51 | `check:mork-compilers-conformance`: rdflib 195 passed, Jena 195 passed, each 44 subtests |
| 13 to 20, 47 | `test_denotation.py`: 41 passed |
| 44, 45, 52 | `check:reference-eligibility`: 81 passed. `check:reference-eligibility-conformance`: rdflib 81 passed, Jena 81 passed |
| 48 | `check:proofs -- eligibility`: Eligibility session built, 33 claims, assumption audit clean, `GATE: pass` |
| 49 | `check:formal-freshness`: 2 artefacts consistent. The literate check for Eligibility: 7 consistent |
| sweep | `check:full-sweep`: 16 of 17 passed. Failed: `ontology versions` (UNBUMPED, expected) |
| other | `build:knowledge`, `check:identifiers` 9 passed, `check:knowledge` 89 passed, `check:deny-terms` 0 findings |

## Adversarial probes

Each broke one place, ran the tests that guard it, and restored the file from a copy. No probe used a constant `FILTER`.

| Artefact | Defect introduced | Caught by |
|---|---|---|
| SPARQL `_match`, exact | the reference path runs backwards, from the value to the subject | 9 fail: rows 23, 24, 25, 26, 31, 32, 40 and 44 |
| SPARQL `_match`, hierarchical | the walk runs from the reference value to the tested one | 5 fail: rows 21, 22, 28, 40 and 44 |
| SPARQL `_comparison_core` | the tested values are read through the reference path | 15 fail, among them rows 21 to 25, 27 to 30 and 33 |
| SPARQL `_match`, hierarchical | the reference value need not be a scheme member | no test failed on the first run, so row 46 was added. It now fails there |
| SPARQL `_match`, hierarchical | the tested value need not be a scheme member | row 46 |
| SPARQL `_read_set` | the reference closure is reported whenever any value was Denied | 1 fails: row 44's closure-column test. Row 31 did not cover an Intersects with a Denied value and a Permitted one |
| SPARQL `_comparison_core` | subjects not selected by class | 16 fail |
| IR `compile_set_comparison` | the reference binding's closure is not resolved | 11 fail, among them rows 21 and 23 to 25 and 44 |
| shape `elg:SetComparisonBindingsShape` | the two bindings need not differ (second pattern renamed) | rows 01 and 06 |
| shape `elg:SetComparisonBindingsShape` | "names the comparison" pattern reversed | rows 01 and 07 |
| shape `elg:SetComparisonBindingShape` | the stray-binding pattern broken | row 10 |
| shape `elg:SetComparisonBindingsShape` | the subject class compared with itself | row 08 |
| shape `elg:SetComparisonBindingsShape` | the value space dropped from the refused properties | row 09 |
| the differential test | a compiler matches exactly under hierarchical match | row 45 sees the disagreement |
| SPARQL `_comparison_core` | the outside-scheme test on a tested value matches anything (point of L9) | 9 fail, among them rows 21, 22, 46, 50, 51 and 44 |
| IR `SetComparisonPlan.no_hierarchy` | the test is inverted (L14) | rows 50 and 52 fail, with the sweep's zero-link cases |
| reference `decide_member` | the L14 rule dropped | row 52 fails. The differential test sees the reference answer Denied where SPARQL and SHACL answer Undetermined |
| SPARQL `_read_set` | `?referenceClosure` never bound | rows 31, 33 and 44 (the per-column closure test) |

## Acceptance

Awaiting the maintainer. The items under "Decisions taken without the maintainer" want a countersignature, and the merge into `main`, with `release:prepare`, is the sign-off.
