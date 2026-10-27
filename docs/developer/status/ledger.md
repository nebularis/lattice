<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger — Status

**Unit ID:** `ledger`
**Status:** 🚧 LG-0 and LG-1 built and verified, not yet committed. LG-2 not started.
**Last updated:** 2026-10-22
**Plan:** [ledger.md](../plans/ledger.md)
**Validation Packs:** [LG-0](../validation/ledger-lg-0.md), [LG-1](../validation/ledger-lg-1.md)

---

## Is this unit complete?

**No.** LG-0 (examples first) and LG-1 (the configuration document) are built and verified. LG-2
(runtime document) is briefed in the plan but not started. LG-3 (Behaviour's migration), LG-4
(allocation) and LG-5 (benchmark) are not briefed.

## Current state

**2026-10-22.** Built on `docs/placement-vehicles-structure`, not on the dedicated
`ledger/lg-0-examples` branch the plan names: for this session, the maintainer asked that every
slice land as commits on the current branch, so one bundle carries the whole session to machine R.
Machine S, working autonomously a slice at a time with a pause for the maintainer to review between
each (credit budget).

Ten files written under `ontology/ledger/examples/`, one per row of LG-0's table: `licence-seats.ttl`,
`revolving-facility.ttl`, `research-grant.ttl`, `authority-aggregate.ttl`, `insurance-aggregate.ttl`,
and the five refusals (`refusal-cycle.ttl`, `refusal-unit.ttl`, `refusal-overdraw.ttl`,
`refusal-proportional-unrounded.ttl`, `refusal-intensive-unit.ttl`). Full detail, including what
passed, what is hand-checked only, and two points for the maintainer (a gap in `fnd:Identified`, since resolved, and
a modelling choice in the reinstatement example), is in the [LG-0 Validation Pack](../validation/ledger-lg-0.md)'s
Handoff section.

**Blocker met, not this unit's to fix:** `mise run bootstrap` fails in this environment with an HTTP
403 from the configured package mirror while installing build dependencies, so `rdflib` is not
available and LG0-01 (parse every example) could not be machine-run. Per `lattice-toolchain`, handed
to the maintainer rather than retried.

**Gap found, cross-cutting:** the plan's vocabulary tables for Ledger (`ldg:AccountDefinition`,
`ldg:Grant`) and for Ensemble (`ens:Membership`, `ens:Relation`, `ens:Endpoint`) and the
instrument-relations sketch (`ins:InstrumentRelation`) all declare terms `⊑ fnd:Identified`, a class
that does not yet exist in `ontology/foundation`.

**Resolved 2026-10-23:** the maintainer decided to drop `fnd:Identified` everywhere rather than add a class to Foundation. A named node already has a stable identity, its IRI. Account definitions, grants, memberships and endpoints are parts of their owners, plain classes as `ins:Term` and `bhv:AllowanceDefinition` are, and `ens:Relation` is only `fnd:TemporallyScoped`. The plans, the relations sketch, Ledger's README and six examples were corrected the same day.

**Next action:** the maintainer reviews LG-0 and LG-1 (see below), publishes ADR-A131 (and ideally
ADR-A01's 2026-10-19 addendum), and creates the pending release tags. If accepted, LG-2 (runtime
document) is next, per the plan.

## 2026-10-22, LG-1 built and verified

Built on `docs/placement-vehicles-structure`, same session convention as LG-0 (one branch, one
bundle). Full detail in the [LG-1 Validation Pack](../validation/ledger-lg-1.md)'s Handoff and
Results sections. In short:

- `ontology/ledger/README.md` written in ADR-A126's layout and extracted: `spec/ledger.ttl`,
  `vocab/ledger-vocab.ttl`, `shapes/structural.ttl`, `shapes/constraints.ttl` (six SHACL-SPARQL
  constraints). Registered in the root catalogue after `quantification`, in the ontology
  architecture document and the root README. `tools/test_ledger.py` added to
  `check:ontology-catalog`'s list (13 tests, all passing).
- **The substrate release moved to 0.19.0.** Ledger joining the release changes every member's
  version IRI under ADR-A129's one-release model, which cascaded into five applied modules that pin
  the substrate (each bumped one MINOR of their own, per ADR-A86's re-pinned-import rule, with their
  test files' hardcoded version strings updated to match): `applied/capacity` 0.17.0,
  `applied/classification` 0.4.0, `insurance/common` 0.8.0, `insurance/exposure` 0.3.0,
  `insurance/peril` 0.7.0. Release-notes lines added to every affected README that has one.
- **🔴 RELEASE TAGS REQUIRED**, once this is merged (`mise run build:ontology-releases` already lists
  them; repeated here per the lifecycle skill):
  ```
  git tag applied-capacity-execution-v0.16.0 applied-capacity-execution-v0.17.0 applied-classification-v0.3.0 applied-classification-v0.4.0 applied-classification-vocab-v0.3.0 applied-classification-vocab-v0.4.0 insurance-common-v0.7.0 insurance-common-v0.8.0 insurance-common-vocab-v0.7.0 insurance-common-vocab-v0.8.0 insurance-exposure-v0.2.0 insurance-exposure-v0.3.0 insurance-exposure-vocab-v0.2.0 insurance-exposure-vocab-v0.3.0 insurance-peril-v0.6.0 insurance-peril-v0.7.0 insurance-peril-intensity-v0.6.0 insurance-peril-intensity-v0.7.0 insurance-peril-vocab-v0.6.0 insurance-peril-vocab-v0.7.0 ontologies-v0.18.0 ontologies-v0.19.0
  ```
  (most of these pre-date this slice and were already pending; `ontologies-v0.19.0` and the
  `v0.17.0`/`v0.4.0`/`v0.8.0`/`v0.3.0`/`v0.7.0` members are new here.)
- **🔴 `check:published-decisions` cannot go green without the maintainer.** Ledger's README and
  `shapes/constraints.ttl` cite ADR-A131 throughout, since the whole document describes that
  decision, which is Accepted but not Published. Publishing is the maintainer's act (ADR-A127
  decision 1), the same as accepting. ADR-A01's 2026-10-19 addendum (also cited, also Accepted) has
  the same gate.
- Two small, low-risk fixes made to pass this environment's checks honestly rather than skip them:
  `tools/import_guard.py`'s violation renderer now prints `Path.as_posix()` (was bare `Path`,
  backslash-separated on Windows, failing five of its own test's fixtures), and
  `tools/test_import_guard.py`'s diagram-order check now reads `ontology-architecture.md` with
  `encoding="utf-8"` explicitly (was defaulting to the Windows locale codec).
- Three LG-0 refusal fixtures gained a missing `qnt:Difference` capability so each isolates exactly
  the one shape it is meant to test (see LG-1 Validation Pack for which).
- A real scaling limit found, not a defect: rdflib's SPARQL property-path evaluator recurses past
  Python's call stack on a 10,000-deep `ldg:partOf+` chain. No real account tree is anywhere near
  that deep; LG1-09's test now uses a shallow, wide tree instead, which is also the shape real trees
  have.
- `check:full-sweep`'s other failures (`build:mtp`/`check:mtp`, `check:persistence`,
  `check:agent-guidance`, and one flaky `reasoning_server` timing test) are pre-existing and
  unrelated, each confirmed in isolation. `check:site-sections` failed once (my edit to
  `eligibility/README.md` left its site copy stale) and is fixed (`build:site-sections` run).
