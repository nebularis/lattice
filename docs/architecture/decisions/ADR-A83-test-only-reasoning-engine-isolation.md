<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A83: Test-only reasoning engine isolation

**Status:** Proposed
**Date:** 2026-09-25
**Related:** ADR-A24 (backend strategy), ADR-A28 (parity gate), ADR-A29
(toolchain boundary), ADR-A71 (platform licence and SPI seam), ADR-A90
(design-time OWL backend)
**Source plan:** [eligibility-compiler](../../developer/plans/eligibility-compiler.md), Part B
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md) (AOR-10, AOR-11)

## Context

Several checks need a DL reasoner or a rules engine, and none is available:

- ADR-A90's checks (subsumption, satisfiability, overlap of generated classes)
  need an OWL 2 DL reasoner. The repository's `reasoning` extra provides
  `owlrl`, an OWL RL engine, which cannot decide them.
- ADR-A24's SWRL artefacts have never been loaded into a reasoner. The
  compiler tests apply builtin-free rules with a query evaluator, which is
  exact for those rules but is not a reasoner.
- Interval SWRL rules use `swrlb` comparison builtins.

The `eligibility-compiler` plan (Part B) sets the constraints: no product
package depends on a reasoner or rules engine, the harness is shared across
compiler families and ecosystems, and Maven, Python tooling and `mise` each
keep their own dependency authority. It found Openllet to be AGPL-3.0 and
HermiT LGPL-3.0, and left the engine choice to this ADR.

## Decision

1. **A test-only Maven module, `platform/reasoning-testkit`.** Java 25, under
   `platform/pom.xml`. Engine libraries are declared only here. The module
   ships a library for Java test suites (`<scope>test</scope>` only) and a
   shaded CLI jar for everything else.
2. **A CLI contract, not a library binding, for non-JVM consumers.**
   `reasoning-testkit classify|satisfiable|subsumes|entails|apply-rules`,
   taking ontology files and a catalog (ADR-A88), writing JSON to stdout.
   Python tests call it as a subprocess and skip, with a named reason, when
   the jar is absent. No `pyproject.toml` declares a reasoner or a JVM bridge.
3. **Engines sit behind adapters.** The CLI's own code depends on the OWL API
   interfaces only. Each engine is one adapter, selected by a flag.
4. **HermiT is the first adapter.** It decides OWL 2 DL, which ADR-A90 needs,
   and applies DL-safe SWRL rules, which covers every builtin-free rule the
   compilers emit (concept, profile and bound-subject rules). Its LGPL-3.0
   licence places no obligation on code that calls it out of process.
5. **Openllet is a later, optional adapter.** Interval rules need `swrlb`
   builtins, which HermiT does not evaluate. If verifying them is wanted,
   Openllet is added as a second adapter under the same isolation. Its
   AGPL-3.0 licence is compatible only because nothing links it and nothing
   serves it over a network, so the guardrail in item 6 becomes load-bearing
   the day it is added.
6. **A guardrail check.** `mise run check:reasoning-isolation` fails when any
   `pom.xml` other than the testkit's declares a reasoner or rules-engine
   artefact, when any module depends on the testkit outside `test` scope, or
   when any `pyproject.toml` declares a reasoner, a rules engine or a JVM
   bridge. It has a violating fixture that must fail.
7. **Drools is deferred** until a consumer needs a general rules engine.
8. **`mise` tasks.** `bootstrap:reasoning-testkit` builds the jar,
   `check:reasoning-testkit` runs its self-tests.

## Consequences

- AOR-10 and AOR-11 can verify ADR-A90's checks, and ADR-A24 gains an
  independent load of every builtin-free SWRL artefact.
- Interval SWRL rules stay verified only by their structure until the Openllet
  adapter exists. The VP of any slice relying on them says so.
- Python tests that need the harness are L4 and skip without the jar, so the
  default Python run needs no JVM.
- `platform/reasoning-testkit` is a new directory, introduced by this decision
  under an existing root.

## Open questions

- Confirm, in the skeleton slice, that HermiT and the OWL API run on Java 25,
  and that HermiT refuses rather than ignores a rule with builtins.
- Whether the CLI should also accept Turtle and resolve imports through the
  catalog, or require a pre-merged closure. This ADR proposes the catalog.
