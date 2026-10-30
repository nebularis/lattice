<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: MORK transform backends, XSLT and JOLT

**Unit ID:** `mork-transforms` (XJ)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** decisions XJ-Q1 to XJ-Q7 answered 2026-10-30. ADR-A148 Proposed. XJ1 to XJ5 built 2026-10-30
**Status record:** [mork-transforms.md](../status/mork-transforms.md)
**ADR:** [A-148](../../architecture/decisions/ADR-A148-mork-transform-backends.md), Proposed
**Depends on:** `tools/mork_rdf`'s reader. Independent of the XSLT sidecar unit, which may later host the stylesheets
**Replaces:** backlog item BL-03

## 1. Goal and acceptance

A MORK mapping scheme over an XML or JSON source compiles to an XSLT 3.0 stylesheet or a JOLT chain that writes the graph the mapping describes, run on Saxon-HE or JOLT by `platform/mork-transforms`. Accepted when every example of §3 gives its expected graph on both engines, and every mapping a backend cannot carry is refused with a finding.

## 2. Decisions

| ID | Question | Answer, 2026-10-30 |
|---|---|---|
| XJ-Q1 | Which compiler the backends build on | `tools/mork_rdf`'s reader, lowered to a format-neutral logical plan (ADR-A148 decision 1) |
| XJ-Q2 | How a mapping names a place in XML or JSON | the format on the representation scheme, paths read in that format's subset (decision 2) |
| XJ-Q3 | What JOLT writes | expanded JSON-LD (decision 4) |
| XJ-Q4 | Identity without a key | positional, reported, and a key recommended (decision 5) |
| XJ-Q5 | What a backend cannot carry | refused with a finding (decision 6) |
| XJ-Q6 | Where the engines run | a Java library and command line, with a RabbitMQ worker when the studio needs it (decision 7) |
| XJ-Q7 | Where the work lives | this unit |

## 3. Examples

`tools/mork_transforms/tests/examples/<name>/` holds `source.xml`, `source.json`, `xml.mork.ttl`, `json.mork.ttl` and `expected.nt`. The first, `policies`, covers a root datum with a keyed identity, a nested datum with a positional identity glued to its parent, assertions from a value, an attribute and a constant, an inverse assertion, and a correspondence table.

## 4. Slices

| Slice | What | Done when |
|---|---|---|
| XJ1 | `tools/mork_transforms`: the reader admits an XML or JSON scheme, the path subsets, the logical plan and its refusals | the plan of each example is as expected, and each refused form gives its finding |
| XJ2 | the XSLT backend | each example's stylesheet, run on Saxon-HE, gives `expected.nt` |
| XJ3 | `platform/mork-transforms`: the engines, the command line, `bootstrap:mork-transforms` and `check:mork-transforms` | the Java tests pass and the Python tests run the jar |
| XJ4 | the JOLT backend | each example's chain, run on JOLT and read as JSON-LD, gives `expected.nt` up to positional identities |
| XJ5 | the registers, the catalogue, the developer guide, ADR-A23's targets | `check:knowledge`, `check:catalogue` and `check` pass |

Later, outside this unit: the studio's mapping mode runs an XML or JSON sample through a worker on RabbitMQ, and lookups, guards and creations in XSLT.
