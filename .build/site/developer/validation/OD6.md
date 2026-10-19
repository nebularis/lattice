<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD6, the Eligibility pilot

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD6
([plan](../plans/improved-ontology-documentation.md#od6-the-eligibility-pilot)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
for its first module, with OD-D33 to OD-D36, OD-D42 and OD-D43.
**Built autonomously**, at the maintainer's request of 2026-10-18. The decisions taken alone are listed below,
for the maintainer to keep or overrule, with the 32 drafted definitions.

## Invariant

Eligibility's README is in the 13-section layout, and every file it generates is the same graph as at
`dab1c790` except for the 40 differences in [OD6-reconciliations.txt](OD6-reconciliations.txt): 32 new
definitions, and each document's `dct:description` and `dct:creator` with their declarations. No axiom, shape
or individual changed. The Kernel and its Python rendering are unchanged byte for byte.

## What changed

Enumeration and the migration check were committed earlier in this slice (`6bb8c4f2`). This part adds:

- `ontology/eligibility/README.md`, migrated:
  - **§2:** the header, prefix and creator tables (OD-D36).
  - **§3:** the extraction contract rewritten for the layout, with the catalogue entry unchanged.
  - **§4 Overview:** the Core Model introduction and its flowchart, and the generated class diagram, which
    replaces the hand-drawn one.
  - **§5 Detailed Design:** the strategy algebra, conditions, questions, the mechanism types, properties,
    evidence bindings, closures and laws, in eight subsections. Prose about the vocabulary (wildcards, decision
    order, directions, operational profiles, value readings) joined the subsection it explains.
  - **§6:** 52 entries, 10 individuals tables, the one `All disjoint` paragraph, two 6.6 blocks
    (`rdf:Property a owl:Class`, and L9 to L17 whole, OD-D35), and the Axiom Index.
  - **§7:** the structural shapes generated, and the constraints and rules as hidden blocks naming their files.
  - **§8 to §13:** examples, canonicalisation and formalisation as before, dependencies (from §1), release notes
    without slice references, and three open issues.
- `ontology/eligibility/spec/`, `vocab/` and `shapes/structural.ttl`, regenerated. `constraints.ttl`, `rules.ttl`,
  `Kernel.thy` and `_kernel_defs.py` came out byte for byte the same.
- `tools/check_formal_freshness.py`. It passed every block to `plan()` with the catalogue's shape files, which a
  README in the layout refuses, since its blocks need section 6 compiled. It reads only the Isabelle outputs, so
  it now passes only the `isabelle-spec` blocks.
- `docs/architecture/literate-specifications.md`. The status names Eligibility as migrated, enumeration is
  described, 6.6 takes `turtle-vocab` blocks, and the migration check is named.
- `docs/developer/validation/OD6-reconciliations.txt`, the approved differences.

## Tests changed, for countersigning

| Test | Change | Why |
|---|---|---|
| OD1-T1, `tools/test_literate_extract.py` | still asserts every README's blocks scan as the legacy scanner found them, and asserts no regions or hidden blocks only for a README not in the layout | a migrated README has regions and hidden blocks by design |
| RC1-T3, `tools/test_lattice_repo_catalogue.py` | compiles a README in the layout before planning, as `main()` does, with the shape files from `contract_shapes()` | calling `plan()` alone refuses a migrated README, so the test could not check Eligibility's contract |

Neither test is weakened for an unmigrated README.

## Decisions taken alone, for the maintainer

1. **The 32 definitions** (OD-D42), drafted from the README's prose, are in the table below.
2. **The 14 individuals with no comment keep none**: the five match strategies, three compatibility
   operations, three wildcard policies and three decisions. OD-Q5's answer covered the 32 classes and
   properties. They are listed as an open issue in the README's §13, and are a short addition if wanted.
3. **L1 to L8 name no register**, though the laws diagram places them under `elg:StaticConstraint`. We kept the
   graph as it is and recorded this in §13. Adding `elg:lawRegister elg:StaticConstraint` to each is a vocab
   change for OD-REL or a later slice.
4. **Section 1 stays one sentence**, today's, so the `dct:description` says what Eligibility models and nothing
   more. The imports sentence moved to §11.
5. **§10 names no tool.** The paragraph on how the block is extracted, and which files hold the hand-written
   proofs, moved to §3, where the generation is described. The truth tables and the L15 readings stay.
6. **One release note, "Not yet released",** describes the migration, for OD-REL to turn into a version. The
   older notes lost their slice references (CCS, FM-EP, B2.2) and kept their ADRs.
7. **No individual or law changed text.** L9's comment keeps its semicolon, since rewording it changes the
   graph.

### The drafted definitions

| Term | Definition |
|---|---|
| `elg:ExactCondition` | A condition that admits a candidate equal to one of its required concepts (ExactMatch). |
| `elg:SetMembershipCondition` | A condition that admits a candidate that is a member of the set of its required concepts (SetMembership). |
| `elg:IntervalCondition` | A condition that admits a candidate whose value lies within its required range set (IntervalContainment). |
| `elg:WildcardCondition` | A condition that stands in for one or more dimensions of a match, as its wildcard policy allows (Wildcard). |
| `elg:MatchStrategy` | How a condition matches its candidate, one of a closed set of named strategies. |
| `elg:CompatibilityOperation` | How a condition's requirements combine when it states several, one of a closed set of named operations. |
| `elg:WildcardSemantics` | The wildcard policy a condition declares, one of a closed set of named policies. |
| `elg:Decision` | The three-valued outcome of an admissibility decision: Permitted, Denied or Undetermined. |
| `elg:OperationalProfile` | A reference conformance profile that a compiler backend is checked against. Versioned, since the profiles are themselves subject to change control. |
| `elg:Law` | A logical law of the Eligibility layer, a property its declarations or decisions must satisfy, not a law in the legal sense. A law may name how it is discharged (elg:lawRegister). |
| `elg:LawRegister` | How a logical law of the Eligibility layer is discharged, by formal argument or by a static check of declarations. |
| `elg:StepDirection` | The direction in which an evidence step traverses its property. |
| `elg:hasCondition` | A condition an admission profile composes. |
| `elg:forCondition` | The one condition a question is posed against. |
| `elg:requiredRangeSet` | The range set a candidate's value must lie within, for a condition matching by IntervalContainment. |
| `elg:candidateRangeSet` | The range set a question offers as its candidate to a condition matching by IntervalContainment. |
| `elg:candidateValue` | The value a question offers as its candidate. |
| `elg:matchStrategy` | The one match strategy a condition declares. |
| `elg:constrainedByContract` | The scheme contract whose resolved scheme a condition's candidates are matched against (ADR-A85). |
| `elg:compatibilityOperation` | The one compatibility operation a condition declares. |
| `elg:wildcardSemantics` | The one wildcard policy a condition declares. |
| `elg:forProfile` | The one admission profile a decision is for. |
| `elg:hasQuestion` | A question a decision answers. |
| `elg:decisionValue` | The one outcome a decision records: Permitted, Denied or Undetermined. |
| `elg:lawRegister` | How a logical law of the Eligibility layer is discharged. |
| `elg:usesOperationalProfile` | The one operational profile a decision is made under. |
| `elg:subjectRoleOccupancy` | The role occupancy of the subject a question is asked about. |
| `elg:conditionKey` | The canonical identifier of a condition declaration, for comparison, caching and replay. |
| `elg:bindsCondition` | The one condition an evidence binding supplies candidates to. |
| `elg:evidenceStep` | A step of an evidence binding's path. |
| `elg:stepProperty` | The one property an evidence step traverses. |
| `elg:stepDirection` | The one direction in which an evidence step traverses its property. |

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD6-T1 | the migrated README / `check:literate-migration -- eligibility dab1c790` with the reconciliations / passes with 40 reconciled differences | L5 | + |
| OD6-T2 | the README with `elg:hasQuestion` changed to `min 2` / the same check / fails with 14 unreconciled differences, in the spec's restriction and the structural shape | L5 | − |
| OD6-T3 | the migrated README / the extractor with `--check` / every generated file and the README's regions consistent | L4 | + |
| OD6-T4 | the Eligibility, catalogue, extraction and grammar suites, the reference semantics, the compilers and the freshness check / run / pass unchanged, but for the two tests above | L3 | + |

The enumeration and migration-check tests of the slice's first part are in `tools/test_literate_grammar.py`
and `tools/test_literate_migration_check.py`.

## Commands

Run from the repository root. A pass is each command exiting 0, except the last, which reports the three
unbumped files of OD-D43 and nothing else.

```bash
mise run check:literate-migration -- eligibility dab1c790 --reconciliations docs/developer/validation/OD6-reconciliations.txt
```

```bash
mise exec -- python tools/literate_extract.py ontology/eligibility/README.md --layer eligibility --root . --proofs-root tools/proofs --reference-root tools/reference --check
```

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py tools/test_literate_migration_check.py tools/test_lattice_repo_catalogue.py tools/test_eligibility_examples.py tools/test_parameter_bindings.py -q
```

```bash
mise run check:full-sweep
```

## Results

2026-10-18, run while building, from this worktree:

- **OD6-T1:** passes, 40 reconciled differences.
- **OD6-T2:** fails as expected, 14 problems. The README was restored and regenerated, and OD6-T1 passed again.
- **OD6-T3:** 7 extracted artefacts consistent.
- **The six suites above:** 294 passed.
- **`mise run check:full-sweep`:** 13 of 14 checks pass, among them `check:ontology-catalog` (1078 passed), `check:persistence`, `check:mork-compilers`, `check:reference-eligibility` (60 passed) and `check:formal-freshness`. The ontology versions check fails on exactly the three unbumped Eligibility files OD-D43 expects.

The adversarial probes were not run beyond OD6-T2.

## Deliberate non-coverage

- Version bumps and re-pins. OD-REL (OD-D43).
- The class diagram was not rendered in a browser for this README. OD5's render check covered the same
  constructs.
- Vocabulary's migration. OD7.

## Decisions answered

2026-10-18, by the maintainer:

- **The definitions** are agreed, with three changes. The first three condition classes say what they admit
  rather than what they match. `elg:LawRegister` makes clear that the laws are logical laws of the layer, not
  laws in the legal sense, and `elg:Law` and `elg:lawRegister` say the same for consistency.
- **`elg:CompatibilityOperation`'s name** is questioned, since what it describes is a composition. Answered
  2026-10-19 as OD-D44 (renamed, and declared on profiles only) and OD-D45 (`elg:DimensionConsistent` and
  `elg:E6` retired), for slice ELC.
- **Decision 3** (L1 to L8 name no register). OD-REL adds the register.
