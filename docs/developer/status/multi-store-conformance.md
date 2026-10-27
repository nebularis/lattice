<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store conformance: status

**Unit ID:** `multi-store-conformance`
**Plan:** [multi-store-conformance.md](../plans/multi-store-conformance.md)
**Branch:** none yet. `msc-trunk` is to be created from `ccs-trunk` at the commit that adds the plan, and each slice branches from `msc-trunk`.
**Mode:** set by the maintainer at hand-off.

## Position

| Slice | State |
|---|---|
| MSC-1 | planned, waits on the answers to MSC-Q1 to MSC-Q5 |
| MSC-2, MSC-3, MSC-4 | planned, wait on MSC-1 |
| MSC-5 | planned, waits on MSC-2 to MSC-4 |

**Next action, for the maintainer:** answer MSC-Q1 to MSC-Q5 in the plan, create `msc-trunk`, and hand the unit to its agent with the mode it works in.

## History

- 2026-10-27: unit planned from the CCS unit's C9b3 work, which found rdflib and Oxigraph disagreeing on aggregates over a row with no value (TSD-41, TSD-43) and Oxigraph 0.5.13 changing a left join's cost (TSD-42). The maintainer asked for Jena to join every conformance run in a unit of its own, isolated from CCS. CAP-90 registered
