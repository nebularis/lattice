<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A113: Breaking changes at major version zero

**Status:** Accepted
**Date:** 2026-10-01 (proposed), 2026-10-01 (accepted, Gate A)
**Related:** ADR-A86 (semantic versioning, clarified here), ADR-A104, ADR-A106, ADR-A112
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)
(C0, decision CC-D4)

## Context

ADR-A86 adopts Semantic Versioning for every ontology document and classes a change that removes,
renames or narrows a term as MAJOR. It also keeps major version zero's ordinary meaning: no layer
is yet declared stable, and `1.0.0` is reserved for the decision that declares one so. Every layer
is at `0.x`. Read literally, the bump table would take Instrument from `0.7.0` to `1.0.0` when it
is rewritten, claiming a stability no decision has granted. SemVer item 4 says anything may change
at `0.x`, but neither A-86 nor the versioning policy says how such a change is numbered.

The computable contract substrate rewrites Instrument, splits Behaviour and creates Wording, each
with breaking changes (ADR-A104, ADR-A106, ADR-A112), so the rule is needed before any of them
lands.

## Decision

1. **At major version zero, a breaking change takes a MINOR bump.** For any ontology document,
   shapes directory or projection directory whose version is `0.x`, a change that ADR-A86's table
   classes as MAJOR increments the MINOR number instead.
2. **The change is marked breaking** in the ADR that authorises it and in a "Release notes"
   section of the layer's README, one line per breaking version, which the layer's first breaking
   change creates. The release register (`ontology-releases.md`) is unchanged: its rows stay
   generated and add-only.
3. **Importers follow the existing rules.** They re-pin in the same change, and an import-only
   change takes the imported level (ADR-A86's addendum), so an importer of a breaking `0.x` change
   takes a MINOR bump too, marked breaking where its own consumers are affected.
4. **Scope.** Every document at `0.x`, not only the layers this unit changes (CC-D4).
5. **`1.0.0` stays reserved** for a decision declaring a layer's interface stable. From then on
   ADR-A86's table applies unchanged.

## Consequences

- `docs/architecture/ontology-versioning-policy.md` gains this rule beside its bump table when
  this ADR is accepted, before CCS slice C3.
- A consumer pinned to an exact version IRI is unaffected, as before. A consumer that reads `0.x`
  MINOR numbers as compatible must read the layer README's release notes, as SemVer already
  advises for `0.x`.
- Instrument (C6) and Behaviour (C10) are the first layers to gain a release notes section.
- No tool changes. The version check (`check:ontology-versioning`) still checks only that content
  and version moved together.
