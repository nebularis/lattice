<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-0.1, Phase 0 decisions

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Decisions:** [A-98](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md),
[A-99](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md),
[A-100](../../architecture/decisions/ADR-A100-scheme-profiles-and-capability-tiers.md),
[A-102](../../architecture/decisions/ADR-A102-liability-direction-from-party-roles.md), all Proposed

## Invariant

The epic's decisions D1 and D5 to D10 are recorded as ADRs before any ontology changes. The
sketches agree with the ADRs on paths and prefixes, name the repository of every Open CBAA
document they cite, and link only to files that exist.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR01-01 | the four ADRs, the epic, its plans and the five sketches / local link check / no broken link | L0 | + |
| AIR01-02 | the ADR catalogue / read / rows for A-98, A-99, A-100 and A-102, and A-101 recorded as reserved | L0 | + |
| AIR01-03 | the sketches and plans / search for `brg:`, `common:` followed by a class name, and `reference/peril` / no match | L0 | − |

## One command

Run from the repository root. It prints nothing when the slice passes. The full link check fails
on links outside this slice that were broken before it.

```bash
mise run topology:links 2>&1 | grep -E "applied-insurance|sketches/(peril|asset|term|mork-bridge)|ADR-A(98|99|100|102)"; grep -rnE "\bbrg:|\bcommon:[A-Z]|reference/peril" docs/developer/sketches/{peril-vocabulary,asset-exposure-ontology,term-parameters,mork-bridge,peril-structure-whitepaper}.md docs/developer/plans/applied-insurance-reference*.md
```

## Artefacts to inspect

- The four ADRs, in particular A-99 decision 2 (nested binding scopes) and A-98 decision 6
  (namespaces and prefixes: `cls:`, `icm:`, `prl:`, `aeo:`, and `spf:` in A-100).
- `docs/architecture/decisions/README.md`: the index rows and the numbering note.
- The citation note under each sketch's header.

## Deliberate non-coverage

No ontology file changes, so no versioning or catalog check applies. The layout is created and
checked in AIR-1.1, and the shared contracts and role types in AIR-1.2.
