<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-0.1, Phase 0 decisions

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Decisions:** [A-98](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md),
[A-99](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md),
[A-100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md),
[A-102](../../architecture/decisions/ADR-A102-liability-direction-from-party-roles.md),
[A-103](../../architecture/decisions/ADR-A103-eligibility-set-readings.md). A-98, A-99 and A-102
Accepted. A-100 (reduced), A-103 and A-98's addendum Proposed

## Invariant

The epic's decisions D1, D5 to D9, D11 and D12 are recorded as ADRs before any ontology changes. The
sketches agree with the ADRs on paths and prefixes, name the repository of every Open CBAA
document they cite, and link only to files that exist.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR01-01 | the four ADRs, the epic, its plans and the five sketches / local link check / no broken link | L0 | + |
| AIR01-02 | the ADR catalogue / read / rows for A-98, A-99, A-100, A-102 and A-103, and A-101 recorded as reserved | L0 | + |
| AIR01-03 | the sketches and phase plans / search for `brg:`, `spf:`, `scheme-profile`, tier letters as terms, `common:` followed by a class name, and `reference/peril` / no match | L0 | − |
| AIR01-04 | the sketches / read against ADR-A100 and ADR-A103 / no scheme profiles or capabilities, flat lists and missing characteristics are Undetermined, crosswalks are SKOS with Foundation provenance, checks across characteristics are profiles over `aeo:LossCause` | L0 | + |

## One command

Run from the repository root. It prints nothing when the slice passes. The full link check fails
on links outside this slice that were broken before it.

```bash
mise run topology:links 2>&1 | grep -E "applied-insurance|sketches/(peril|asset|term|mork-bridge)|ADR-A(98|99|100|102|103)"; grep -rnE "\b(brg|spf):|\bcommon:[A-Z]|reference/peril|scheme-profile|\btier (F|H|R|N)\b" docs/developer/sketches/{peril-vocabulary,asset-exposure-ontology,term-parameters,mork-bridge,peril-structure-whitepaper}.md docs/developer/plans/applied-insurance-reference-phase-*.md docs/developer/plans/applied-insurance-reference-lanes.md
```

## Artefacts to inspect

- The four ADRs, in particular A-99 decision 2 (nested binding scopes), A-98 decision 6
  (namespaces and prefixes: `cls:`, `icm:`, `prl:`, `aeo:`) and its addendum, and the premises
  and examples of A-100 and A-103 (ADR-A-C2).
- Peril vocabulary §6.8, the check across cause, agency and mechanism.
- `docs/architecture/decisions/README.md`: the index rows and the numbering note.
- The citation note under each sketch's header.

## Deliberate non-coverage

No ontology file changes, so no versioning or catalog check applies. The layout is created and
checked in AIR-1.1, and the shared contracts and role types in AIR-1.2.
