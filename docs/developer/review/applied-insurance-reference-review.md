<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review Request: Applied Insurance Reference, Phase 0

**Unit:** `applied-insurance-reference`
**Status record:** [applied-insurance-reference.md](../status/applied-insurance-reference.md)
**Plan:** [applied-insurance-reference-phase-0.md](../plans/applied-insurance-reference-phase-0.md)
**Date:** 2026-09-26
**Requested by:** agent, autonomous session

## Scope

| Item | Subject | Record |
|---|---|---|
| ADR-A98 | applied layout, three levels of sharing, insurance modules, namespaces and prefixes | [ADR](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md) |
| ADR-A99 | reference editions as fallback, nested binding scopes, peril structure beyond SKOS | [ADR](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md) |
| ADR-A100 | scheme profiles, capability tiers, crosswalks, published crosswalks (MB-Q3) | [ADR](../../architecture/decisions/ADR-A100-scheme-profiles-and-capability-tiers.md) |
| ADR-A102 | liability role types, unfilled occupancies, derived direction | [ADR](../../architecture/decisions/ADR-A102-liability-direction-from-party-roles.md) |
| AIR-0.1 | catalogue rows, sketch citation notes and prefix alignment | [VP](../validation/applied-insurance-reference-0.1.md) |

## Command

Run from the repository root. Passing prints nothing.

```bash
mise run topology:links 2>&1 | grep -E "applied-insurance|sketches/(peril|asset|term|mork-bridge)|ADR-A(98|99|100|102)"; grep -rnE "\bbrg:|\bcommon:[A-Z]|reference/peril" docs/developer/sketches/{peril-vocabulary,asset-exposure-ontology,term-parameters,mork-bridge,peril-structure-whitepaper}.md docs/developer/plans/applied-insurance-reference*.md
```

## Pass criteria

The command prints nothing, and each ADR is accepted, amended or rejected.

## Questions for the reviewer

1. **Prefixes (A-98, A-100).** `cls:` for classification, `icm:` for insurance common, `spf:` for
   scheme profiles. Each can change until Phase 1 creates the files.
2. **Nested scopes (A-99 decision 2).** An agreement binding must repeat its drafting
   organisation's and market's scopes, or ADR-A85's strict-superset rule reports a tie. This puts
   the burden on whoever authors the agreement binding. The alternative is an upstream
   precedence change to Vocabulary.
3. **Published crosswalks (A-100 decision 5).** Only where the list owner's terms allow it. Is
   that the right condition, or should LATTICE publish none?
4. **Direction shape (A-102 decision 3).** A direction value without a derivation is reported.
   Should the shape be a violation or a warning?
