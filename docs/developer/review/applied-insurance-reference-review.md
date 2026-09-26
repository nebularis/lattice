<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review Request: Applied Insurance Reference, Phase 0

**Unit:** `applied-insurance-reference`
**Status record:** [applied-insurance-reference.md](../status/applied-insurance-reference.md)
**Plan:** [applied-insurance-reference-phase-0.md](../plans/applied-insurance-reference-phase-0.md)
**Date:** 2026-09-26 (refreshed after A-100's reduction and A-103)
**Requested by:** agent, autonomous session

## Scope

| Item | Subject | Record |
|---|---|---|
| ADR-A98 (Accepted, addendum new) | applied layout, three levels of sharing, insurance modules, namespaces and prefixes | [ADR](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md) |
| ADR-A99 | reference editions as fallback, nested binding scopes, peril structure beyond SKOS | [ADR](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md) |
| ADR-A100 (reduced) | hierarchical match over schemes without a hierarchy, `exe:NoHierarchy`, crosswalks as SKOS with Foundation provenance, published crosswalks (MB-Q3) | [ADR](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md) |
| ADR-A103 | some-value and every-value readings for evidence bindings, and condition negation, in every backend | [ADR](../../architecture/decisions/ADR-A103-eligibility-set-readings.md) |
| ADR-A102 | liability role types, unfilled occupancies, derived direction | [ADR](../../architecture/decisions/ADR-A102-liability-direction-from-party-roles.md) |
| AIR-0.1 | catalogue rows, sketch citation notes and prefix alignment | [VP](../validation/applied-insurance-reference-0.1.md) |

## Command

Run from the repository root. Passing prints nothing.

```bash
mise run topology:links 2>&1 | grep -E "applied-insurance|sketches/(peril|asset|term|mork-bridge)|ADR-A(98|99|100|102|103)"; grep -rnE "\b(brg|spf):|\bcommon:[A-Z]|reference/peril|scheme-profile|\btier (F|H|R|N)\b" docs/developer/sketches/{peril-vocabulary,asset-exposure-ontology,term-parameters,mork-bridge,peril-structure-whitepaper}.md docs/developer/plans/applied-insurance-reference-phase-*.md docs/developer/plans/applied-insurance-reference-lanes.md
```

## Pass criteria

The command prints nothing, and each ADR is accepted, amended or rejected.

## Disposition

A-98 (with addendum), A-99, A-100, A-102 and A-103 (with negation) were accepted on 2026-09-26.
Earlier defaults stand: nested scopes (A-99), crosswalks published only where the owner's terms
allow (A-100), and a violation for a direction without a derivation (A-102). Remaining: record
AIR-0.1 in `LOG.md`, then close this request.
