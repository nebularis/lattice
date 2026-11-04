<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DR-3, the callers and the conformance of the delta replace

**Unit:** [`persistence-delta-replace`](../status/persistence-delta-replace.md), slice DR-3 of the [plan](../plans/persistence-delta-replace.md), built before DR-2 on 2026-11-01 because DR-1 left the caller libraries' tests reading the delta replace where they meant the whole one. Autonomous mode.

**For countersignature (non-weakening rule):** no test was weakened or removed. The libraries' tests of the whole replace read the profiles `baseline-single-class-whole-state` and `composite-project-ownership-whole-state`, which declare `dal:WholeState`, so they test what they tested before.

## Invariant

Both caller libraries fill a delta replace's `assertTriples` and `retractTriples` from its contract alone, and compute its request digest over the delta. A delta replace's digest has no payload part, so it never equals the digest of a whole replace of an empty payload with the same delta (DR-Q3 (a)), and the independent verifier recomputes it.

## What changed

- **The digest contract.** `DigestContract.parts()` gives no payload part where a contract has an add or a del part and neither a payload nor an event, which is a delta replace. The compiled profiles, the expected profiles and the library fixtures are regenerated.
- **Vectors.** `digest-replace-delta` in `contracts/persistence/vectors.json`.
- **Library fixtures.** `baseline-single-class-whole-state` and `composite-project-ownership-whole-state`, compiled from the whole-state witnesses and held to compile by `test_library_contract.py`.
- **Library tests.** One in each library, reading the delta replace from a compiled profile.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| DR3-T1 | `digest-replace-delta` / both libraries and `verify-vectors.py` recompute it / equal | L3 | |
| DR3-T2 | the baseline profile's delta replace / read its contract / kind `Replace`, no payload contract, parts kind, target, expected, add, del | L3 | Python and Java |
| DR3-T3 | one delta / digest it as a delta replace and as a whole replace of an empty payload / the digests differ | L3, negative | Python and Java |
| DR3-T4 | the six library fixtures / compile their sources / isomorphic | L3 | |
| DR1-T1 to T5 | the delta replace on every engine | L4 | rdflib, Oxigraph and Jena in memory |

**The one command:** `mise run check:persistence-library`, then `mise run check:persistence-conformance`.

## Results, 2026-11-01

| Command | Result |
|---|---|
| `mise run check:persistence-library` | 94 vector checks, the Java library's tests and 114 Python tests passed |
| `mise run check:persistence` | 4,312 passed |

## Not covered

TDB2 and Fuseki run the delta replace through the studio in DR-4, by the studio harness's integration topology, since the conformance run's engines are in-memory.
