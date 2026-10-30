<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: MORK transform backends, XSLT and JOLT

**Unit ID:** `mork-transforms` (XJ)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** decisions XJ-Q1 to XJ-Q7 answered 2026-10-30. ADR-A148 Proposed. XJ1 to XJ5 built 2026-10-30. XJ-Q9 to XJ-Q12 answered 2026-10-30. XJ6 and XJ7 wait for XJ-Q8 and XJ-Q13
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

The maintainer asked on 2026-10-30 for the studio's mapping mode to run an XML or JSON sample through a worker on RabbitMQ (ADR-A148 decision 7). Today a dry run of the mapping part (`kind=dry-run&target=mapping`) takes one Turtle sample, and the Python worker compiles each scheme with `tools/mork_rdf`, runs it on Oxigraph and returns one N-Triples artefact for each mapping and stratum, which the canvas counts, the stepper and the mapping card read. Profiled 2026-10-30 on a laptop with the `policies` example, warm:

| Step | Time | Where it goes |
|---|---|---|
| parse the mapping, rdflib | about 1 ms | Turtle parsing, plus 150 ms to import rdflib once per process |
| plan | about 1 ms | the reader's graph lookups |
| compile to XSLT or JOLT | about 0.1 ms | |
| XSLT run in a warm JVM | 5 to 10 ms | Saxon compiles the stylesheet on each call, and caching the compiled stylesheet by its digest is the next lever |
| JOLT run in a warm JVM | about 1 ms | |
| the first run in a JVM | 240 ms XSLT, 90 ms JOLT | class loading and interpreted code, so a command line pays it on every run (0.3 s and 0.15 s) |

So a run's cost is a cold JVM, which a resident worker removes, and neither rdflib nor memory pressure is the cause, since the in-JVM loop runs in milliseconds on the same machine.

The maintainer set a principle on 2026-10-30. When a user journey needs several routes or more than one communicating worker, a coordinator owns the unit of work, with its timeouts, circuit breaking and error handling, and supervises the jobs inside it. A job that waits on another job, or creates one, is that case.

| ID | Question | Options | Recommendation |
|---|---|---|---|
| XJ-Q8 | How a transform's result reaches the browser | (a) request-reply. The service publishes the run to the Java worker's queue, `lattice.studio.transforms`, with a reply queue, waits as it waits on the writer for a save, and answers the HTTP request with the output. The output is not stored, since a dry run is derived and can be rerun. (b) push. The service answers 202 with the job's IRI as its transaction id, and the Java worker publishes the result to an events exchange with that IRI in its headers, which RabbitMQ's Web STOMP plugin serves to the browser over a WebSocket. A message the service sends to a queue with a TTL dead-letters into the same exchange with the same key, so the worker and the timeout race and the browser takes the first per IRI and ignores the rest. Replacing the polling of every job kind this way is a unit of its own, amending ADR-A136 | (a) for this case, since a warm run takes milliseconds and the pattern already exists for saves. (b) as its own unit for the jobs that run long |
| XJ-Q13 | How the compile and the run are sequenced, since the compiler is Python and the engines Java | (a) two jobs the browser sequences. The `compile` job of XJ-Q11 writes each scheme's stylesheet or chain and its attribution table to its job graph, and the transform names that job and the sample, so no job waits on or creates another, and a changed sample reuses the compiled artefacts. (b) one dry run owned by a coordinator, which runs the compile and then the transform and owns their timeouts and errors | (a), with (b) when a journey chains jobs itself |
| XJ-Q9 | Which mapping wrote each triple | (a) after the run, the worker attributes each triple through the plan: a type to its datum, a glue property to the child datum, an asserted property to its assertion, and a triple two mappings could have written to both. (b) a traced variant of each transform that writes the mapping beside each triple, which JOLT cannot do without a second form of the chain. (c) no attribution, so the canvas counts and the card's output are hidden for these runs | (a), answered 2026-10-30. The attribution table travels with the compiled artefacts, and the Java worker applies it |
| XJ-Q10 | How the sample's format is chosen | (a) a format selector beside the sample, Turtle, XML or JSON, set from the text when it is pasted, and each scheme whose `mork:format` matches is run while the others are reported as not run. (b) one sample for each scheme | (a), answered 2026-10-30 |
| XJ-Q11 | What else the studio gives | (a) the dry run also returns each scheme's stylesheet or chain as an artefact to read and download, and the `compile` job of the mapping part writes them beside the SPARQL. (b) only the run's output | (a), answered 2026-10-30 |
| XJ-Q12 | A sample workspace | (a) a sample, "Policies from XML and JSON", from the `policies` example, with both schemes and both sources. (b) none | (a), answered 2026-10-30 |

| Slice | What | Done when |
|---|---|---|
| XJ6 | a Java worker in `workers/` consuming `lattice.studio.transforms`, the route XJ-Q8 and XJ-Q13 choose, with the topology and the operations guide | a transform of an XML or JSON sample returns each mapping's output, and the worker's tests run it on RabbitMQ |
| XJ7 | attribution, the format selector, the artefacts and the sample, in the worker, the contract and the browser | the `policies` sample's runs show each mapping's output on the canvas, checked live in the browser |

