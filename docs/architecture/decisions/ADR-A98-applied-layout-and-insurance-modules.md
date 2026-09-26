<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A98: Applied layout and insurance modules

**Status:** Proposed
**Date:** 2026-09-26 (proposed)
**Related:** ADR-A86 (semantic versioning), ADR-A88 (import resolution), ADR-A-C1, ADR-A-C2, ADR-A99, ADR-A100, ADR-A102
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (AIR-0.1, epic decisions D1, D5 to D9)

## Context

`ontology/applied/` holds two things. `capacity/` is designed as a cross-domain module that
insurance, lending and other domains import, with no domain vocabulary and a promotion path into
Behaviour ([architecture overview](../../../ontology/applied/capacity/docs/architecture-overview.md),
CP-9). `insurance/` holds one legacy contract module whose spec does not parse as Turtle, imports
pre-LATTICE namespaces, and shares one `shapes/` directory and `.version` across everything in
the domain. Nothing imports it.

The applied insurance reference epic adds a peril vocabulary, an exposure ontology, submission
and claims modules, shared insurance contracts and classifications other domains also need. Under
ADR-A86 a `shapes/` directory is versioned by one `.version` file, so modules sharing a directory
bump each other. And without a rule for where shared content goes, content used by two domains
lands in the first domain to need it and must later move, which changes its IRIs and breaks every
importer.

## Decision

1. **Three levels of sharing.** A module sits at the lowest level that covers every module that
   uses it or is planned to:

   | Level | Location | Content | Moving up |
   |---|---|---|---|
   | substrate | `ontology/<layer>/` | domain-neutral mechanisms with stated laws | clean-room promotion (ADR-A-C2) |
   | cross-domain applied | `ontology/applied/<module>/` | domain-neutral mechanisms and classifications not yet promoted. No domain vocabulary | criteria of the module's own design, as Capacity's CP-9 |
   | domain-shared | `ontology/applied/<domain>/common/` | content meaningful only in one domain and used by two or more of its modules | to cross-domain, when a second domain needs it |

2. **Cross-domain modules.** `capacity/` (unchanged), `classification/` (territory, asset class
   and industry scheme contracts) and `scheme-profile/` (ADR-A100).
3. **Domains.** A domain is a directory `applied/<domain>/` with a `domain-README.md` and one
   directory per module. Each module has `spec/<module>.ttl`, `vocab/` where it declares concepts,
   `shapes/` with its own `.version`, and a `README.md`. `applied/README.md` explains the domains
   and the levels of sharing.
4. **Insurance modules.** `common/` (insurance scheme contracts, liability role types per
   ADR-A102, the loss event), `peril/` (ADR-A99), `exposure/`, `submission/` and `claims/`. A new
   `contract/` module is deferred (epic D2).
5. **Dependencies run one way.** `classification/` and `scheme-profile/` import the substrate
   only. `insurance/common/` imports those and the substrate. `peril/` imports `common/`.
   `exposure/` imports `common/` and `peril/`. `submission/` imports `exposure/`. `claims/`
   imports `exposure/` and `contract/`. A cross-domain module never imports a domain module.
6. **Namespaces and prefixes.**

   | Module | Namespace | Prefix |
   |---|---|---|
   | cross-domain `<module>` | `https://www.nebularis.org/neuro-semantic/lattice/applied/<module>#` | per module |
   | `classification/` | as above | `cls:` |
   | insurance `<module>` | `https://www.nebularis.org/neuro-semantic/insurance/<module>#` | per module |
   | `insurance/common/` | as above | `icm:` |
   | `insurance/peril/` | as above | `prl:` |
   | `insurance/exposure/` | as above | `aeo:` |

   Version IRIs append `/<semver>` to the namespace without its `#`. A module's `vocab/`
   document uses `<namespace-without-#>/vocab#` and the version IRI `…/<module>-vocab/<semver>`.
   `ins:` stays Instrument's. Submission and claims prefixes are fixed when those modules are
   built.
7. **Imports.** Every applied module imports LATTICE layers and other applied modules by exact
   version IRI, resolved through the catalog (ADR-A88).
8. **The legacy contract module is dropped** (epic D1). Its files and its `KNOWN_DEFECTS` entry
   in `tools/ontology_catalog.py` are removed.

## Consequences

- Every module versions independently under ADR-A86. A shapes change in one module never
  requires another module's `.version` to move.
- Territory, asset class and industry are cross-domain from the start, so a lending domain reuses
  them without an IRI move.
- Moving a module up a level changes its namespace and is MAJOR for every importer. The
  lowest-level rule keeps such moves rare and deliberate.
- `ontology/applied/README.md`, a new `insurance/domain-README.md` and
  `docs/architecture/ontology-architecture.md` §3 describe the layout (AIR-1.1).
- Applied content is not substrate, so ADR-A-C2 governs only the substrate changes it motivates.
  Cross-domain modules keep their text and examples free of domain vocabulary so that promotion
  stays possible.
