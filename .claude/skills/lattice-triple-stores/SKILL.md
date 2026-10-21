---
name: lattice-triple-stores
description: How triple stores really behave, and how to record what we find. Use before relying on what a store does with SPARQL (an update's order, scope, datatypes, escapes, atomicity, cost), when running generated SPARQL on rdflib, Oxigraph or another engine, when writing a probe or an engine test, and whenever a store does something unexpected. The record is docs/architecture/triple-store-discovery.md.
---

# Triple stores in LATTICE

The record of how each store behaves is
[docs/architecture/triple-store-discovery.md](../../../docs/architecture/triple-store-discovery.md). It is a source of truth for
the project. Every claim about a store elsewhere, in a sketch, an ADR, a Validation Pack or a code comment, cites a finding there
(`TSD-nn`), or adds one.

## Before relying on a store

1. Read the findings at a glance (§5 of the record) and every finding that touches what you are doing.
2. Check the versions. A finding holds for the versions it names. If yours differ, treat it as a hypothesis and re-run its
   reproduction.
3. If the record is silent, do not reason from memory about what SPARQL or a store does. Probe it. Two of the typed IR's first
   rules were written from memory and were wrong (record §7.2).

## Probing a store

- **Run the smallest query that shows the behaviour,** on every store you have, and record each result.
- **Read the source where you can,** at the version you ran. Name the file and function. Source tells you the mechanism, and an
  observation tells you it really happens. Aim for both.
- **Fix what the engine is free to vary.** On rdflib, the order of solutions from a non-lazy join follows `PYTHONHASHSEED`
  (TSD-01), so a probe whose answer depends on order fixes the seed or sweeps it, in child processes. A probe that runs once in
  the test process measures luck.
- **Trace as lightly as you can.** Read one variable of a solution, not all of it. A heavy trace once gave a result we did not
  reproduce (record §7.1).
- **Say how parameters reached the store,** as initial bindings or as substituted text (record §4.4). Some findings depend on it.
- **When a probe contradicts the source, re-read the source** before recording anything.

## Recording a finding

Add an entry to the record in the shape of its §6.0, and a row to its §5 table.

| Part | Holds |
|---|---|
| identifier | the next `TSD-nn`, never reused |
| evidence | Source, Observed, Documented or Reasoned, as §1 defines, and the run record (date, store and version, Python, kind of machine, never the machine or person) |
| context | what you were building or testing, and why it mattered |
| how we found it | the steps in order, with what each showed |
| what the store does | the smallest SPARQL, and the result on each store |
| why | the mechanism, citing the source |
| what it means for LATTICE | the decisions, debt, tests and documents it touches |
| reproduce it | a query to run, or a short plan for a script when the setup has layers |

Then:

- Turn the probe into a test, under `tools/persistence/tests/test_store_probes.py` or the tool it concerns, opting in to every
  engine with `@engines.each_engine`, so a change in a store fails a test.
- Point the documents that rely on the behaviour at the finding, and correct any that it contradicts, with a dated note.
- A finding that turns out wrong is corrected in place, dated, and its story goes in the record's §7.

## Stores and how to reach them

| Store | Reached through | Install | Run its cases |
|---|---|---|---|
| rdflib | `rdflib.Dataset`, in the test process, parameters as `initBindings` | part of every Python bootstrap | `mise run check:persistence` |
| Oxigraph | `tools/testing/oxigraph` (ADR-A125), parameters substituted as text | `mise run bootstrap:testing-oxigraph` | `mise run check:persistence` (the default engine), `mise run check:persistence-conformance` |

A measurement of cost belongs in a benchmark under `benchmark/` (ADR-A124), which fails on a wrong result and never on time.
`benchmark/sparql-constraint-query-cost` is the one for query forms, and `mise run check:sparql-constraint-query-cost` runs it.

## Findings about cost

How to write a query so that it runs in reasonable time is a design record, not a finding:
[docs/architecture/efficient-queries-and-shapes.md](../../../docs/architecture/efficient-queries-and-shapes.md) (ADR-A128). A cost
finding goes in the discovery record as TSD-22 to TSD-33 do, with its engine and version, and the design record's rule that rests on
it cites it. When you find that a rule holds on one engine only, say so in both places, and mark it in the design record's table of
what is specific to rdflib. A result on one engine is a hypothesis for the others until it is run on them.
