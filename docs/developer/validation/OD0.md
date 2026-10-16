<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD0, the ADRs, the agent rule and the conventions document

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD0
([plan](../plans/improved-ontology-documentation.md#slices)).
**Delivers:** ADR-A121, ADR-A126 and ADR-A127 drafted as Proposed, the AGENTS.md rule of OD-D21 and OD-D28,
and `docs/architecture/literate-specifications.md` started. No code, ontology or generated file changes.
**Decisions needing confirmation:** six drafting choices, listed below.

## Invariant

Every decision the maintainer took for this unit (OD-D1 to OD-D31 and the answers to RC-Q1 to RC-Q8) is
stated once, in the ADR whose subject it is, and the conventions document restates none of it beyond what a
README author needs. The three ADRs and the conventions document refer to working documents only in a
closing Provenance section (OD-D21, OD-D25), so they can be published as they stand.

## What changed

| File | Change |
|---|---|
| `docs/architecture/decisions/ADR-A121-repository-catalogue.md` | new, Proposed |
| `docs/architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md` | new, Proposed |
| `docs/architecture/decisions/ADR-A127-published-architecture-decisions.md` | new, Proposed |
| `docs/architecture/decisions/README.md` | three index rows |
| `docs/architecture/literate-specifications.md` | new, marked Proposed with ADR-A126 |
| `AGENTS.md` | one rule under "A public repository" |

`.github/copilot-instructions.md` is generated from `AGENTS.md` and has not been regenerated (the command
is below).

## Where each decision is stated

| Decisions | Stated in |
|---|---|
| OD-D1, OD-D9 | ADR-A126 decision 12 |
| OD-D2, OD-D19, OD-D27 | ADR-A126 decision 1 |
| OD-D3, OD-D12, OD-D16 | ADR-A126 decisions 3 and 7 |
| OD-D4, OD-D10 | ADR-A126 decision 5 and its consequences |
| OD-D5, OD-D11 | ADR-A126 decisions 8 and 9 |
| OD-D6, OD-D8 | ADR-A126 decision 1 (section 8) and the conventions document |
| OD-D7, OD-D13 | ADR-A126 decision 10 |
| OD-D14, OD-D16, RC-Q1 to RC-Q8 | ADR-A121 decisions 1 to 9 |
| OD-D15 | ADR-A126 decision 4 |
| OD-D17, OD-D18 | ADR-A126 decision 10 |
| OD-D20 | ADR-A126 decision 13 |
| OD-D21, OD-D22, OD-D25, OD-D28 | ADR-A127 decisions 1, 2 and 4, and the AGENTS.md rule |
| OD-D23 | the plan only. Migration order is delivery, not architecture |
| OD-D24 | the three ADRs themselves |
| OD-D26 | ADR-A126 decision 11 |
| OD-D29 to OD-D31 | ADR-A121 decision 1 (site sections in the root file) and ADR-A127 decision 5 |

## Drafting choices, for the maintainer

1. **Published is a fourth status** after Accepted, set by the maintainer with a date (ADR-A127 decision 1).
2. **The list of published decisions is generated** from the ADRs' Status lines and checked (ADR-A127
   decision 3). Our discussion did not settle whether it is generated or kept by hand.
3. **Accepted ADRs leave the site until published.** Until a README is migrated and the decisions it cites
   are published, the sources check reports a citation of an Accepted ADR rather than failing (ADR-A127
   consequences). Without this, every README would fail the check on the day it lands.
4. **The AGENTS.md rule tells agents to cite Accepted ADRs until decisions are published.** That is the same
   transition, stated for agents.
5. **ADR-A01's convention note** (the ontology header in a README's first `turtle-spec` block) gains an
   addendum when ADR-A126 is accepted, since section 2 then holds the header (ADR-A126 consequences).
6. **A change to the substrate's import order in the catalogue needs an amendment to ADR-A01** (ADR-A121
   decision 2). This keeps ADR-A01 as the decision while the catalogue becomes where tools read it
   (RC-Q3 option C).

## Test cases

All are L0, documentation only.

| ID | Given / When / Then | +/- |
|---|---|---|
| OD0-T1 | `AGENTS.md` / `build:agent-guidance`, then `check:agent-guidance` / the Copilot copy matches and every link resolves | + |
| OD0-T2 | the three ADRs and the conventions document / every relative link / resolves to a file | + |
| OD0-T3 | the three ADRs / a search for links to sketches, plans, status records, reviews, validation or notes / every match is in the Provenance section | + |
| OD0-T4 | the conventions document / the same search / no match | + |
| OD0-T5 | the changed files / the personal boundaries search and `check:deny-terms` / no finding | + |
| OD0-T6 | the ADR catalogue / A121, A126 and A127 / each is listed once, Proposed, and no other branch has claimed the number | + |

T2, T5 (the boundaries search only) and T6 were run while drafting, on 2026-10-16, and passed. T6 was
checked against every local and remote branch.

## One command

Run from the repository root. A pass is the build writing `.github/copilot-instructions.md` and the check
reporting no problem.

```bash
mise run build:agent-guidance && mise run check:agent-guidance
```

T3 and T4, from the repository root. A pass prints only lines inside a Provenance section of an ADR:

```bash
grep -n -E "developer/(sketches|plans|status|review|validation|notes)|developer/INDEX" docs/architecture/decisions/ADR-A121-repository-catalogue.md docs/architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md docs/architecture/decisions/ADR-A127-published-architecture-decisions.md docs/architecture/literate-specifications.md
```

T5, once the files are staged. A pass reports no finding:

```bash
mise run check:deny-terms
```

## Deliberate non-coverage

- The addenda to ADR-A120 and ADR-A01, written when ADR-A126 is accepted.
- Links to the conventions document from `tools/README.md`, `ontology-architecture.md`, the glossary and the
  ontology authoring skill. Those land with OD1, when the conventions start to apply.
- The decision catalogue's convention paragraph, which gains the Published status when ADR-A127 is accepted.
