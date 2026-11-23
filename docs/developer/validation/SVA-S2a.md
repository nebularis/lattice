<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2a, a promotion kept by the compiler's rule

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2a, built on 2026-11-23 in autonomous mode, on the maintainer's decision of the same day that the surface compiler's rule is the promotion's meaning and that the writer keeps the rows of the other sources a write reaches within the write. It pays the debt SVA-S2 recorded between the writer's fills and the compiler's rebuild, which the register no longer holds.

## Invariant

After any write, the rows a promotion holds for a source are the rows the compiler's rebuild gives over the merged world for the carriers that source types, a carrier being typed by the contract's class or by a class below it, and each hop of the read path being read in whichever graph holds it. A write that changes a graph keeps the rows of the sources it changes and of the sources it reaches, in the same request. The surface simulator keeps the same rows, for the same sources.

## What changed

- `persistence.ir` has a graph role `world`, whose graph variable may range over every graph of the store, which every other role refuses (`UnboundGraphVariable`). No template writes it.
- `surface.maintenance.fill_all` has a scope. With `world`, the default, a fill types its carrier in `$source` by the carrier's class or a class below it, whose `rdfs:subClassOf` edges lie in any graph, as a chain of up to three segments each within one graph, and reads each hop in its own graph variable. With `source`, which the studio's own promotions keep, it reads the source alone as before.
- `surface.maintenance.reach` is a new query for each promotion, the sources whose rows the triples of a write change. For the hop whose property a triple has, it reads the carriers that reach the triple's start by the hops before it, backwards from the bound end, and takes the graphs that type them. A triple of `rdfs:subClassOf` reaches the sources that type an instance of its subject or of a class below it.
- The surface compile job carries a `{key}-reach.rq` for each promotion and names it in the manifest. The studio's staged maintenance keeps the single-graph fills and has no reach.
- `Maintenance` in `config-studio-core` loads a reach and gives `reach(family, delta)`, the queries with the triples of the write as typed terms. `StudioStore.sources` runs one. `Writer` collects what each write adds and removes where some promotion reads across graphs, and last in its request keeps every source those queries name. Nothing is read or kept where none does, which is every promotion the studio stages.
- `SurfaceStep` runs the job's reach queries over the world before the edit and keeps the sources they name beside the graphs the edit changed. The outcome part gains `reached`.
- The facility surface steps place each borrower in `urn:g:borrower/{id}` as the facility profile does, and the sector step edits the borrower's graph. Two steps are new, `-subtype`, which adds a drawdown typed by a subclass, and `-vocabulary`, which adds the subclass edge to a vocabulary graph and so retypes a drawdown the facilities graph holds.
- The fixtures that hold the compiler's expectation, the job's maintenance files and `surface-steps/expected.json`, are written by `test_config_studio_surface_step_fixture.py` with `LATTICE_WRITE_SURFACE_STEP_FIXTURE=1`. A second fixture, the operations of the writer's fan-out test, is written by `test_config_studio_fan_out_fixture.py` with `LATTICE_WRITE_FAN_OUT_FIXTURE=1`.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2a-T1 | random worlds of five graphs, three read paths, rdflib and Oxigraph / the fill runs for each source / its rows are the compiler's rebuild over the merged world, kept in the sources that type each carrier | L1 | | |
| S2a-T2 | random edits of random worlds / the reach query runs over the world before / every source whose rows the compiler's rebuild changes, but the graphs the edit writes, is named | L1 | | |
| S2a-T3 | a hand-built world / reach runs for a changed value, a first hop, a property read only from the carrier, an unrelated node, a subclass edge over an instance, and one over a class with none / each names the sources it should and no others | L1 | | |
| S2a-T4 | each of seven steps, the borrowers in graphs of their own / the simulator runs in Jena / each contract's rows before, after, asserted and retracted, the contracts touched and the sources reached are the compiler's | L1 | | |
| S2a-T5 | a publication of a lineage that two workspaces follow / the writer applies it with the staged fan-out operations / the rows of both descriptions move in the request and equal the meaning of the promotion as one query over the store | L1 | the reach query taken out | the rows stayed those of the first version |
| S2a-T6 | a graph of the `world` role / its variable is free in a read, a write to it is built / the first is accepted and the second refused | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `cd tools/surface/src && mise exec -- python -m unittest surface.test_surface surface.test_maintenance` | 82 tests, OK |
| `mise run check:python-root` | 97 tests, OK, and Phase 8 conformance passed |
| `mise exec -- python -m pytest workers/tests -k config_studio -q` | 252 passed, 75 deselected |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py -q` | 60 passed |
| `mise exec -- python -m pytest tools/persistence/tests -q -n 4` | 4981 passed |
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms,config-studio-writer,config-studio-service -am verify` | BUILD SUCCESS. The caller library 128, the outbox 2, the MORK transforms 7, the studio's core 26, the authoring module 9, the service 253, the writer 10, the run worker 77, 0 failures |
| `mise run check:identifiers` | passed |
| `mise run check:knowledge` | two tests fail, `test_a_governed_quantum_exists` for STD-338 and STD-324, and `test_the_build_reports_nothing_but_the_known_notes` for notes on CAP-100 and BL-19. This slice touches none of them |

The real stack was not run.

## What a write fans out to, and what it costs

The sources a write reaches on the samples are in `expected.json`. The borrower, drawdown, first, repay and subtype steps edit the facilities graph, which types every carrier, so they reach no other source. The sector step edits a borrower's graph and reaches the facilities graph, and the vocabulary step edits the vocabulary graph and reaches it too. In the writer's test a publication reaches the two descriptions that follow the lineage.

Costs were measured on Jena's in-memory dataset, the engine of the simulator and the writer's tests, with one facilities graph of 2,000 drawdowns, three hops, and medians of three runs, in milliseconds. A TDB2 store was not measured, since no TDB2 library is available offline.

| Graphs the world holds | Fill, single-graph form | Fill, world form | Reach, one triple | Reach, 100 triples |
|---|---|---|---|---|
| 2, borrowers in the facilities graph | 15 to 27 | 34 to 43 | | |
| 3, borrowers in one graph of their own | reads the facilities graph alone | 65 | 6.2 | 28 |
| 7, borrowers in 5 graphs | reads the facilities graph alone | 103 | 3.5 | 61 |
| 27, borrowers in 25 graphs | reads the facilities graph alone | 228 | 2.6 | 125 |
| 102, borrowers in 100 graphs | reads the facilities graph alone | 730 | 5.2 | 403 |
| 202, borrowers in 200 graphs | reads the facilities graph alone | 1,451 | 8.9 | 780 |

The single-graph form reads the borrowers only where they are in the facilities graph, so it is measured there. Where the graphs are the same the world form costs about twice as much, since each hop reads through a graph variable and the carrier's class through a union of segments. Where the borrowers are in their own graphs the cost follows the graphs times the carriers, about 3.5 microseconds for each pair, since Jena's in-memory dataset runs the pattern once for each graph. That is the shape TSD-75 found on rdflib. A write that reaches one source pays the reach, a few milliseconds for a triple, and then the clear and fill of that source, which is the world fill of its carriers.

## Left open

- The studio's own promotions keep the single-graph fills, since each reads one family of aggregates that hold the nodes it follows, and its rebuild worker reads one source at a time. A fill that read the world would read a workspace's part beside a published version that holds the same concept IRIs, so the rows of an immutable version would follow a draft. The writer's fan-out is built and tested, and has nothing to do for them. Whether a family should read across graphs is the maintainer's to decide, and would bring the rebuild worker to the compiler's rule too.
- The touched-node pair `surface.maintenance.maintenance` of PM-1 still reads the one graph `$source` names. The studio uses neither it nor the cross-graph form, and the tier 2 maintainer of PM-5 is where it would be brought over.
- A chain of subclass edges that changes graph more than twice is not followed. The compiler's rebuild has no such limit. `SUBCLASS_SEGMENTS` names the bound.
- A triple that holds a blank node is left out of the reach query, since a blank node names nothing outside its graph. The studio skolemises on write, and the sample worlds hold none.
- A derived partition is a graph of the world. A promotion that reads a property another promotion writes reads its rows.
- Two batched commands that write one graph are reached through the triples each adds and removes against the graph as the batch leaves it, which `Writer` tracks, and the reach is read from the store before the batch applies. That is exact for the first changed hop of a carrier's path and has not been run against a store with two writers.

## Placement

T0. The IR role, the generators, the run worker, the writer, the contract and the samples are open.
