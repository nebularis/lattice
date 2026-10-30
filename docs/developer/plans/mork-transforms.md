<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: MORK transform backends, XSLT and JOLT

**Unit ID:** `mork-transforms` (XJ)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** decisions XJ-Q1 to XJ-Q7 answered 2026-10-30. ADR-A148 Proposed. XJ1 to XJ5 built 2026-10-30. XJ6 and XJ7 wait for XJ-Q8 to XJ-Q12
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

Later, outside this unit: lookups, guards and creations in XSLT.

## 5. The studio's slices

The maintainer asked on 2026-10-30 for the studio's mapping mode to run an XML or JSON sample through a worker on RabbitMQ (ADR-A148 decision 7). Today a dry run of the mapping part (`kind=dry-run&target=mapping`) takes one Turtle sample, and the Python worker compiles each scheme with `tools/mork_rdf`, runs it on Oxigraph and returns one N-Triples artefact for each mapping and stratum, which the canvas counts, the stepper and the mapping card read. Measured 2026-10-30 on a laptop with the `policies` example: compiling a plan takes about 5 ms, and one engine run through the command line about 150 ms for JOLT and 290 to 450 ms for XSLT, nearly all of it the JVM starting.

| ID | Question | Options | Recommendation |
|---|---|---|---|
| XJ-Q8 | Where the engines run for a dry run | (a) the Python worker runs the jar once per job, about 0.15 to 0.45 s each, with no new component. (b) a Java worker on a queue of its own, `lattice.studio.transforms`, which the Python worker asks for each run and waits on, a warm JVM and a component to deploy, with a timeout when it is down. (c) the Python worker compiles and hands the job on to the Java worker, which runs it and sends the job's update to the writer itself, so no job waits on another, and two workers each finish some jobs | (b), since decision 7 names a worker on RabbitMQ and an ingress endpoint later can use the same queue |
| XJ-Q9 | Which mapping wrote each triple | (a) after the run, the worker attributes each triple through the plan: a type to its datum, a glue property to the child datum, an asserted property to its assertion, and a triple two mappings could have written to both. (b) a traced variant of each transform that writes the mapping beside each triple, which JOLT cannot do without a second form of the chain. (c) no attribution, so the canvas counts and the card's output are hidden for these runs | (a), with what the engine runs left as it is published |
| XJ-Q10 | How the sample's format is chosen | (a) a format selector beside the sample, Turtle, XML or JSON, set from the text when it is pasted, and each scheme whose `mork:format` matches is run while the others are reported as not run. (b) one sample for each scheme | (a) |
| XJ-Q11 | What else the studio gives | (a) the dry run also returns each scheme's stylesheet or chain as an artefact to read and download, and the `compile` job of the mapping part writes them beside the SPARQL. (b) only the run's output | (a), since the stylesheet or chain is what an adopter takes |
| XJ-Q12 | A sample workspace | (a) a sample, "Policies from XML and JSON", from the `policies` example, with both schemes and both sources. (b) none | (a) |

| Slice | What | Done when |
|---|---|---|
| XJ6 | the engine path XJ-Q8 chooses, with the topology and the operations guide | a dry run of an XML or JSON sample returns its output, and the worker's tests run it |
| XJ7 | attribution, the format selector, the artefacts and the sample, in the worker, the contract and the browser | the `policies` sample's runs show each mapping's output on the canvas, checked live in the browser |

