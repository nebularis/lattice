<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A100: Scheme profiles and capability tiers

**Status:** Proposed
**Date:** 2026-09-26 (proposed)
**Related:** ADR-A13 (graph roles), ADR-A92 (derived artefacts), ADR-A98, ADR-A99, ADR-A-C2
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (AIR-0.1, epic decision D10)
**Sketch:** [mork-bridge.md](../../developer/sketches/mork-bridge.md)

## Context

A consumer binds whatever scheme it is given: a flat code list, a two-level taxonomy, a scheme
crosswalked to a reference, or a reference edition itself (ADR-A99). Checks differ in the
structure they need. Hierarchical matching needs `skos:broader`. Overlap warnings need
`prl:overlaps`. A bundle check needs collections. Run against a scheme lacking that structure, a
check either fails or, worse, answers wrongly without saying so.

The same problem arises in any domain that binds external lists against a reference (industry
codes in lending, product categories in retail), so the mechanism belongs in no single domain.

## Decision

1. **A cross-domain module.** `ontology/applied/scheme-profile/`, prefix `spf:`, namespace
   `https://www.nebularis.org/neuro-semantic/lattice/applied/scheme-profile#` (ADR-A98). Its
   text and examples use no domain vocabulary.
2. **Profiles.** A bound scheme may have an `spf:SchemeProfile ⊑ fnd:DerivedArtefact`, derived
   from the scheme and its crosswalks, never asserted by hand. It states one tier and the
   capabilities the scheme supports:

   | Tier | Scheme |
   |---|---|
   | F, flat | no hierarchy |
   | H, taxonomic | `skos:broader` only |
   | R, reference-aligned | crosswalked to a reference edition, with exact and inexact coverage stated |
   | N, native | carries the reference's structure |

3. **Checks are gated.** A check declares the capabilities it requires
   (`spf:requiresCapability`). When the profile lacks one, the check returns Undetermined with
   reason `spf:InsufficientSchemeStructure`. It never falls back to a weaker check silently, and
   an inexact mapping never counts as exact.
4. **Crosswalks.** An `spf:Crosswalk` cites its source edition, target edition and MORK mapping
   graph. Mappings live in the Mapping graph role (ADR-A13) and are promoted into a crosswalk
   only after review. A crosswalk and every profile derived from it are invalidated when either
   edition changes.
5. **Published crosswalks (MB-Q3).** LATTICE may publish a reviewed crosswalk of a widely used
   market list beside the reference edition, so consumers of that list start at tier R. Each is
   published only where the list owner's terms allow it.
6. **Promotion.** The module is a candidate for Vocabulary once the mechanism is shown generic,
   with two non-insurance examples, under ADR-A-C2.

## Consequences

- A consumer with a flat list gets correct answers where its list suffices, and explicit
  Undetermined results elsewhere, which it can route to review.
- Profiles are derived artefacts with read sets (ADR-A92), so a changed scheme or crosswalk makes
  its profile detectably stale.
- The sketches' `brg:` prefix becomes `spf:`.
- Built in Phase 3 of the epic. Slices 3.1 to 3.3 need no peril content, and use non-insurance
  test schemes.
