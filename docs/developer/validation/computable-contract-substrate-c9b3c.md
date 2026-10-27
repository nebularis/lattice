<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b3c, hierarchical matching walks the relation the condition names

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c9b3c-hierarchy-relation`, examples and tests first (ADR-A-C2, commit `092a7dd6`)
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), "C9b3 in detail"
**Decisions:** C9b3-Q4 (a), answered 2026-10-27, and C9b0-Q2 (the no-applicable-binding case) by precedent.
[ADR-A85](../../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md), [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md), [ADR-A129](../../architecture/decisions/ADR-A129-one-release-for-the-substrate.md)

## Invariant

Hierarchical matching walks the ordering relation the condition names, never a relation of another kind. `elg:hierarchyRelation` names `skos:broader` or a property declared a sub-property of it, and absent means `skos:broader`, so existing data keeps its meaning. L9 and L11 read that relation, L14 asks whether it has a link between two members of the resolved scheme, and L9's acyclicity requirement is over it. A condition that needs its scheme whose contract's bindings apply at no instant compiles to a plan that answers Undetermined for every candidate, with `exe:NoApplicableBinding`. Conflicting bindings are still refused (ADR-A85). The OWL and SWRL backends refuse a plan with no scheme.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C9b3c-01 | `hierarchy-relation.ttl` / the layer's shapes / no result | L1 | + |
| C9b3c-02 | the example / read / two conditions name `ex:kind-of` and `ex:part-of` over one scheme, and a third names none | L1 | + |
| C9b3c-03 | the example with `ex:kind-of`'s sub-property declaration removed / shapes / `elg:HierarchyRelationShape` reports the condition | L1 | − |
| C9b3c-04 | a condition naming `skos:broader`, and one naming a two-step sub-property / shapes / no violation | L1 | + |
| C9b3c-05 | a condition naming two relations / shapes / reported (cardinality above one) | L1 | − |
| C9b3c-06 | a set-membership condition naming a relation / shapes / a warning, no violation | L1 | − |
| C9b3c-07 | the kind condition / SPARQL / the lung carcinoma Permitted, the tumour margin Denied, where the condition naming none admits it | L2 | + − |
| C9b3c-08 | the part condition / SPARQL / the margin Permitted, the carcinoma Denied | L2 | + − |
| C9b3c-09 | a condition naming no relation / SPARQL / walks `skos:broader`, admits both | L2 | + |
| C9b3c-10 | the kind condition / the query text / a constant path over `ex:kind-of`, no other relation, no `skos:broader*` | L1 | + − |
| C9b3c-11 | every member, each relation and the territory licence / SPARQL against the plan's expansion / equal | L2 | + − |
| C9b3c-12 | every member, each relation / SPARQL against SHACL / equal | L2 | + − |
| C9b3c-13 | the territory licence / SPARQL / a city in a country in Europe Permitted by two part steps, the overseas region Denied | L2 | + − |
| C9b3c-14 | a relation with no route to `skos:broader` / compile / refused | L1 | − |
| C9b3c-15 | two relations on one condition / compile / refused | L1 | − |
| C9b3c-16 | the scheme with no kind link / the kind condition / L14: the named concept Permitted, others Undetermined with `exe:NoHierarchy` (zero links) | L2 | + − |
| C9b3c-17 | the same scheme / the part condition and the default / still have a hierarchy | L1 | + |
| C9b3c-18 | a part-link cycle / compile / refused for the part condition, not for the kind condition | L1 | + − |
| C9b3c-19 | a contract whose bindings apply at no instant / SPARQL / Undetermined with `exe:NoApplicableBinding` for one candidate, several, and none (zero) | L2 | + − |
| C9b3c-20 | an applicable instant / compile / resolves, not unresolved | L1 | + |
| C9b3c-21 | the unresolved plan / SHACL / every question Undetermined | L2 | + − |
| C9b3c-22 | two bindings of equal specificity / compile / refused | L1 | − |
| C9b3c-23 | a profile over an unresolved condition / compile / compiles | L1 | + |
| C9b3c-24 | an unresolved plan, and a hand-built hierarchical plan with no scheme / SWRL and OWL / refused with "no resolved scheme" | L1 | − |
| C9b3c-25 | a hand-built schemeless hierarchical plan not marked unresolved / SPARQL and SHACL / refused | L1 | − |
| C9b3c-26 | kind and part conditions in one OWL module / compile / refused, where each compiles alone | L1 | − |
| C9b3c-27 | the kind condition with an excluded concept / SPARQL / L10 and L11 over kind links | L2 | + − |
| C9b3c-28 | every relation, three required sets, three excluded sets, every member (27 cases) / the reference against SPARQL and SHACL / equal, with the reference's scheme built from the graph's links | L2 | + − |
| C9b3c-29 | a relation with no link in the scheme / the reference, SPARQL, SHACL / L14 in all three (zero links) | L2 | + − |
| C9b3c-30 | the named relation read as `skos:broader` / the differential test / the disagreement is seen | L2 | − |
| C9b3c-31 | L9, L10, L14 over an arbitrary relation, and the kind and part fixture / Isabelle2025-2 / `TH1` to `TH4` and `AQH` proved, gate passes | L3 | + − |
| C9b3c-32 | `exe:NoApplicableBinding` / the pinned diagnostic set in `test_concept_backends.py` / declared, and no other new diagnostic | L1 | + |
| C9b3c-33 | the README / literate check, formal freshness / consistent | L0 | + |

## One command

```bash
mise run check:full-sweep
```

The sweep runs `check:mork-compilers` (rows 07 to 27 and 32, in `test_hierarchy_relation.py` and `test_concept_backends.py`), `check:reference-eligibility` (rows 28 to 30), `check:ontology-catalog` with `test_eligibility_examples.py` (rows 01 to 06 and 33), and `check:formal-freshness` (row 33). Rows 07 to 27 run on rdflib in `check:mork-compilers` and on Oxigraph in `check:mork-compilers-conformance`. Row 31 is its own task:

```bash
mise run check:proofs -- eligibility
mise run check:mork-compilers-conformance
```

The examples-first commit is red until the model commit. To see the new tests alone:

```bash
MORK_SPARQL_ENGINE=oxigraph mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_hierarchy_relation.py -q
mise exec -- python -m pytest tools/test_eligibility_examples.py tools/reference/eligibility/tests/test_differential.py -q
```

## Artefacts to inspect

- `ontology/eligibility/README.md`: section 5.1 (the relation and its table), 5.8 (what the compilers refuse and what they compile), 6.2 (`elg:hierarchyRelation`), 7 (the two shapes and the note on the two that read `skos:broader`), 8.5 (the example), 10 and 12 (formalisation and the release note)
- `ontology/eligibility/examples/hierarchy-relation.ttl`
- `ontology/mork/spec/Executable.ttl`: `exe:NoApplicableBinding`
- `tools/mork_compilers/src/mork_compilers/eligibility_ir.py`: `hierarchy_relation`, `_resolve_scheme`, `refuse_without_scheme`, `ConceptPlan.relation` and `unresolved`
- `tools/mork_compilers/src/mork_compilers/sparql_backend.py`: the module docstring's cost statement (STD-020), `_hierarchical_decision`, `_concept_core`
- `tools/mork_compilers/src/mork_compilers/shacl_backend.py`, `owl_backend.py`, `swrl_backend.py`
- `tools/reference/eligibility/src/reference_eligibility/denotation.py`: `Scheme.over`
- `tools/proofs/eligibility/Hierarchy.thy` and its claims `TH1` to `TH4` and `AQH`. Adding definitions to the layer changes every claim's digest (gate rule E1.4), so all 13 earlier claim records carry a recomputed digest and no changed statement
- `docs/developer/mechanisms.md` (MEC-84) and `docs/developer/technical-debt.md` (TD-94)

## Deliberate non-coverage

- **Versions.** None moves on this branch. `check:ontology-versioning` reports `UNBUMPED` for `ontology/mork/spec/Executable.ttl` and four release members, as expected until `release:prepare` runs at the merge (ADR-A129).
- **The two static shapes** that still read `skos:broader` (L13 and L9's cycle shape) are exact for a condition naming no relation and conservative otherwise. The compilers check the named relation exactly. TD-94 holds it.
- **A relation asserted only under a sub-property of the named one** is not read. The walk follows the named property, and a scheme that wants a plain SKOS consumer to see the hierarchy asserts each link under both.
- **The OWL `Within` class** is one per concept, so two conditions walking different relations over one scheme cannot share a module where the relations place a member differently (row 26). A class per relation and concept is not built.
- **Design-time reasoner checks** (`needs_reasoner`) skip here, since the reasoning test kit and Java are not installed. No row relies on them.
- **ADR-A100's text** still says "a `skos:broader` link". We did not amend an Accepted ADR.
- **Measured cost.** The generated query's cost is stated, not measured, on either engine.

## Handoff

**Placement:** substrate semantics, laws, proofs and compilers, all open.

**Built:**

- `elg:hierarchyRelation` on a condition, functional, range `rdf:Property`. `elg:HierarchyRelationShape` refuses a value that is not `skos:broader` or declared a sub-property of it, and a second value. `elg:HierarchyRelationNeedsHierarchicalMatchShape` warns where the strategy is not hierarchical. L9, L11 and L14 are restated, and the README, its table and its decision flow follow. A release note is in "Next release".
- The IR reads exactly the named property, refuses an undeclared relation and a cycle in it, and records `relation` and `unresolved` on the plan. `NoApplicableBindingError` gives an unresolved plan, `BindingConflictError` still refuses.
- SPARQL walks a constant path over the relation. An unresolved plan answers Undetermined with `exe:NoApplicableBinding`. SHACL gives an unresolved plan one determinacy shape every focus node violates. OWL and SWRL refuse a plan with no scheme.
- The reference: `Scheme.over` builds a scheme from the links of one relation. The differential tests build theirs from the graph, so a compiler walking another relation disagrees.
- Isabelle: `Hierarchy.thy`, L9, L10 and L14 over a relation taken as a parameter, with the kind and part fixture.

**Decisions taken without the maintainer, for countersignature:**

1. **An exclusion-only condition that is not hierarchical** also compiles to an unresolved plan when its contract has no applicable binding, since it takes the same code path and needs its scheme the same way. The brief named hierarchical conditions.
2. **Acyclicity per relation** is checked exactly in the IR over the named relation. The two static shapes stay on `skos:broader` and are conservative (TD-94). A generated shape per relation would make them exact.
3. **Isabelle adds a theory** rather than editing one, since L9 and L14 had no statement in the existing theories. The kernel is untouched and generated files are unchanged.
4. **MEC-84** is added to the mechanism register as not yet ratified, in the form CAP-84 and CAP-85 take.

**What to check first:** `hierarchy_relation` and `_resolve_scheme` in `eligibility_ir.py`, then `_hierarchical_decision` in `sparql_backend.py`, then README 5.1 against the laws' comments in 6.

## Results

Run on 2026-10-27 in the worktree, against `main` for versions. pyoxigraph 0.5.13 is installed, since the lock's 0.5.11 conflicts with `lattice-testing-oxigraph`'s requirement (see the report).

| ID | Result |
|---|---|
| 01 to 06, 33 | `test_eligibility_examples.py`: 33 passed. `check:ontology-catalog` in the sweep: 1128 passed, 79 skipped |
| 07 to 27, 32 | `check:mork-compilers`: 140 passed, 7 skipped. `test_hierarchy_relation.py` alone: 21 passed on rdflib, 21 passed on Oxigraph |
| 07 to 27, 32 | `check:mork-compilers-conformance`: 139 passed, 1 failed, 7 skipped. The failure is `test_closure_readings.py` `RelianceTests::test_a_profile_row_names_the_union_of_its_conditions_closures`, TSD-41, known and fixed on another branch |
| 28 to 30 | `check:reference-eligibility`: 63 passed, on rdflib and on Oxigraph |
| 31 | `check:proofs -- eligibility`: Eligibility session built, 18 claims, assumption audit clean, `GATE: pass` |
| 33 | `check:formal-freshness`: 2 artefacts consistent. The literate check for Eligibility: 7 consistent. For MORK: 0 extracted, consistent |
| sweep | `check:full-sweep`: 15 of 17 passed. Failed: `ontology versions` (UNBUMPED, expected) and `check:persistence` (`test_h2_4b_t4_p3` on Oxigraph, a ratio of 68 against a bound of 8, with pyoxigraph 0.5.13, unrelated to this change) |
| other | `build:knowledge`, `check:identifiers` 9 passed, `check:deny-terms` 0 findings, `check:knowledge` 84 passed, `check:agent-guidance` 9 passed, `check:site-sections` 6 passed |

## Adversarial probes

Each broke one place, ran the tests that guard it on Oxigraph, and restored the file from a copy. No probe used a constant `FILTER`.

| Artefact | Defect introduced | Caught by |
|---|---|---|
| SPARQL `_hierarchical_decision` | the walk reads `skos:broader` whatever the plan names | 6 fail: rows 07, 08, 09, 10, 11 and 12 |
| SPARQL `_hierarchical_decision` | the `+` path from an excluded concept runs in the wrong direction | 1 fails: row 27. Rows 11 and 12 did not cover an exclusion, so row 27 was added for it |
| IR `_ordering` | reads `skos:broader` instead of the plan's relation | 5 fail: rows 11, 12, 16, 18 and 26 |
| IR `_resolve_scheme` | `NoApplicableBindingError` refused again | 4 fail: rows 19, 21, 23 and 24 |
| SHACL determinacy select | an extra triple pattern no question has | 1 fails: row 21 |
| IR `refuse_without_scheme` | the guard disabled | 4 fail, row 24 and the rows that need an unresolved plan to compile |
| shape `elg:HierarchyRelationShape` | the path reaches `skos:broader` in one step only | 1 fails: row 04 |
| the differential test | the compiler reads the named relation as `skos:broader` | row 30 sees the disagreement |

## Acceptance

Awaiting the maintainer. The items under "Decisions taken without the maintainer" want a countersignature, and the merge into `main`, with `release:prepare`, is the sign-off.

## OWL `Within` class per relation (C9b3c-OWL)

Run on 2026-10-27 in the worktree `ccs-c9b3c-owl-per-relation`. This section supersedes row 26, which asserted the refusal and is replaced by C9b3c-OWL-01, and the deliberate non-coverage line on the OWL `Within` class above.

`within(concept, relation)` mints one class per relation and concept. For `skos:broader` the IRI is `mint(concept, "within")`, unchanged. For another relation it is `mint(concept, "within-" + local name of the relation)`, for example `.../tumour-within-part-of`. `_hierarchy` keys by (relation, member), sibling disjointness is computed per relation, and a module is still refused where one relation places one member differently across schemes, or where two relations share a local name.

| ID | Scenario / Action / Expected | Test |
|---|---|---|
| C9b3c-OWL-01 | kind and part conditions over one scheme / compile one module / separate classes with each relation's subclass axioms and none across | `OwlModuleTests::test_a_kind_and_a_part_condition_compile_into_separate_within_classes` |
| C9b3c-OWL-02 | a `skos:broader` condition / compile / the `Within` IRIs are the literal old ones | `OwlModuleTests::test_a_skos_broader_condition_keeps_the_iri_it_always_had` |
| C9b3c-OWL-03 | kind and part conditions, siblings disjoint / compile / one disjointness group per relation, none mixing relations | `OwlModuleTests::test_sibling_disjointness_is_computed_per_relation` |
| C9b3c-OWL-04 | one relation placing a member differently in two schemes / compile / refused naming the relation. Kind and part together compile | `OwlModuleTests::test_one_relation_placing_a_member_differently_in_two_schemes_is_refused` |
| C9b3c-OWL-05 | no hierarchical condition / compile / no `Within` class | `OwlModuleTests::test_a_module_with_no_hierarchical_condition_mints_no_within_class` |
| C9b3c-OWL-06 | two relations with one local name / compile / refused, since their classes would collide | `OwlModuleTests::test_two_relations_with_one_local_name_are_refused` |
| C9b3c-OWL-07 | a patient with one diagnosis, a tumour margin, part-linked / subsumption by the reasoner / under the part condition, not under the kind condition | `OwlReasonerTests::test_a_part_linked_member_is_not_under_the_kind_relation_class` |
| C9b3c-OWL-08 | a patient with one diagnosis, a lung carcinoma, kind-linked / subsumption by the reasoner / under the kind condition, not under the part condition | `OwlReasonerTests::test_a_kind_linked_member_is_not_under_the_part_relation_class` |

Command, from the worktree: `mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_hierarchy_relation.py -q`. A pass is 28 passed with the reasoning test kit built, so rows 07 and 08 run.

### Results

| ID | Result |
|---|---|
| 01 to 08 | `test_hierarchy_relation.py`: 28 passed, 6 subtests passed, reasoner tests included |
| all | `check:mork-compilers` (Oxigraph): 185 passed, 753 subtests passed. `check:mork-compilers-conformance` (rdflib): 185 passed, 753 subtests passed |
| other | `build:knowledge` built. `check:deny-terms`: 0 findings. `check:identifiers`: failed on five identifiers mentioned in `docs/developer/plans/multi-store-conformance.md:33` (CAP-99, STD-290, STD-299, TSD-50, TSD-69), a file from `ccs-trunk` this unit does not touch |

### Probes

Each broke one place, ran `test_hierarchy_relation.py` and restored the file.

| Defect introduced | Caught by |
|---|---|
| `within` ignores the relation | 4 fail: 01, 03, 07 and 08 |
| `_hierarchy` keyed by member only again | 6 fail: 01, 03, 04, 06, 07 and 08 |
| sibling grouping ignores the relation | 1 fails: 03 |
