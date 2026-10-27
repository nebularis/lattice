<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store conformance: status

**Unit ID:** `multi-store-conformance`
**Plan:** [multi-store-conformance.md](../plans/multi-store-conformance.md)
**Branch:** `multi-store-conformance`, from `ccs-trunk` at `a31dd419`, the only branch this unit commits to.
**Mode:** autonomous across the whole plan, at the maintainer's request on 2026-10-27, with up to two sub-agents. The maintainer reviews before `main`.

## Position

| Slice | State |
|---|---|
| MSC-1 | in progress |
| MSC-2, MSC-3 | planned, wait on MSC-1 |
| MSC-4 | in progress |
| MSC-5 | planned, waits on MSC-2 to MSC-4 |

**Next action, for us:** MSC-1 and MSC-4 in parallel, then MSC-2 and MSC-3, then MSC-5.

## History

- 2026-10-27: unit planned from the CCS unit's C9b3 work, which found rdflib and Oxigraph disagreeing on aggregates over a row with no value (TSD-41, TSD-43) and Oxigraph 0.5.13 changing a left join's cost (TSD-42). The maintainer asked for Jena to join every conformance run in a unit of its own, isolated from CCS. CAP-90 registered
- 2026-10-27: the maintainer handed the whole plan over to be completed autonomously on the `multi-store-conformance` branch. MSC-Q1 to MSC-Q5 answered by us with the leanings, for review. MSC-1 and MSC-4 started
