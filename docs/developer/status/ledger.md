<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger — Status

**Unit ID:** `ledger`
**Status:** 🚧 LG-0 built, hand-checked, not yet committed. LG-1 and LG-2 not started.
**Last updated:** 2026-10-22
**Plan:** [ledger.md](../plans/ledger.md)
**Validation Packs:** [LG-0](../validation/ledger-lg-0.md)

---

## Is this unit complete?

**No.** LG-0 (examples first) is built and hand-checked. LG-1 (configuration document) and LG-2
(runtime document) are briefed in the plan but not started. LG-3 (Behaviour's migration), LG-4
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
passed, what is hand-checked only, and two points for the maintainer (a gap in `fnd:Identified` and
a modelling choice in the reinstatement example), is in the [LG-0 Validation Pack](../validation/ledger-lg-0.md)'s
Handoff section.

**Blocker met, not this unit's to fix:** `mise run bootstrap` fails in this environment with an HTTP
403 from the configured package mirror while installing build dependencies, so `rdflib` is not
available and LG0-01 (parse every example) could not be machine-run. Per `lattice-toolchain`, handed
to the maintainer rather than retried.

**Gap found, cross-cutting:** the plan's vocabulary tables for Ledger (`ldg:AccountDefinition`,
`ldg:Grant`) and for Ensemble (`ens:Membership`, `ens:Relation`, `ens:Endpoint`) and the
instrument-relations sketch (`ins:InstrumentRelation`) all declare terms `⊑ fnd:Identified`, a class
that does not yet exist in `ontology/foundation`. Someone needs to add it to Foundation, with its own
bump, before any of these slices' specs can be written.

**Next action:** the maintainer reviews LG-0 (examples, Validation Pack, the two open points above),
and once the environment blocker is resolved, runs LG0-01's parse check. If LG-0 is accepted, LG-1
(configuration document) is next, per the plan.
