<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK transform backends

Compiles a MORK mapping scheme over an XML source to an XSLT 3.0 stylesheet, and one over a JSON source to a JOLT chain, so a reviewed mapping runs on the engine an adopter already has ([ADR-A148](../../docs/architecture/decisions/ADR-A148-mork-transform-backends.md)). [`tools/mork_rdf`](../mork_rdf) compiles the same vocabulary for an RDF source, and its reader classifies every mapping for both.

```python
from datetime import datetime, timezone
from mork_transforms import plan, compile_xslt
from mork_transforms.jolt import compile_jolt

p = plan(graph, scheme, "xml", base="https://example.org/data/", at=datetime(2026, 1, 1, tzinfo=timezone.utc))
stylesheet = compile_xslt(p)                     # XSLT 3.0, writes canonical N-Triples
chain, findings = compile_jolt(plan(graph, other, "json", base=..., at=...))  # JOLT, writes expanded JSON-LD
```

`p.findings` holds what the reader and the plan found, among them every mapping refused because a transform cannot carry it, and `compile_jolt` adds what JOLT alone cannot. `platform/mork-transforms` runs both, and `mork_transforms.engine.run` calls it. `source_formats(graph, scheme)` gives the formats a scheme reads, and `attribution(plan)` the table that attributes what a run writes to its mappings, which the studio's transforms worker reads.

## The source

A scheme's source concepts are in a representation scheme with `mork:format mork:XML` or `mork:format mork:JSON`. A root datum iterates what its concept's `mork:path` reaches from the document, and a child datum what its concept's path reaches from its parent's focus, or its parent's focus when it has none. `mork:dataRef` is read in the format's subset, given in `paths.py`.

- **XML.** `/` for the document, child steps by qualified name with the scheme's `sh:declare` prefixes, `*`, `@attribute` and `.`. A value is an element's or attribute's string value, written as a string.
- **JSON.** `$` for the document, `.key` and `[*]`, one `[*]` in a path. A value is written as JSON-LD reads it, so a number is an xsd:integer or xsd:double and a boolean an xsd:boolean.

A correspondence matches the value its source individual's `skos:notation` gives, or `mork:conceptId` or `mork:identifier`.

## Identity

The SPARQL backend's rules (`tools/mork_rdf` README §6), except that a datum with no key has a positional identity, for example `cover/policies/1/policy/2/cover/1` in XML, counted from 1 as XPath counts, and `cover/policies/0/covers/1` in JSON, counted from 0 as JSON Pointer counts. It is reported as `PositionalIdentity`, since it changes when a node is inserted before it. JOLT has no URI encoding, so a key it writes into an IRI is reported as `KeyNotEncoded`.

## Not carried yet

Lookups, guards, class and property creation, and a deferred reference to data or to an outcome off the context chain, refused in both backends with a finding on the mapping. The JOLT backend also refuses a child datum with no glue property, two mappings writing one property on one node, a path that iterates twice and a literal its `concat` cannot hold. Neither backend writes the SPARQL backend's check queries.

## Tests

`mise run check:mork-transforms` builds the engines, runs their tests, then compiles each example under `tests/examples/` and checks that Saxon-HE and JOLT give its `expected.nt`, positional identities compared as blank nodes. `tests/examples/policies/compiled/` holds what the studio's compile job writes for that example, which the transforms worker's tests run, and a test keeps it equal to the compiler's output (`LATTICE_REWRITE_FIXTURES=1` writes it afresh).
