<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-persistence (Python)

The caller library of [ADR-A132](../../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md), slices H2.8a and H2.8b.
Standard library and rdflib only. It never imports the compiler, and the compiler imports it for the shared types.

| Module | Holds |
|---|---|
| `lattice_persistence.terms` | the term encoders (`Iri`, `Literal`, `Var`, `Integer`) that make text safe to place in a SPARQL request. A bare string is not accepted where one of these is |
| `lattice_persistence.payload` | `Payload`, `Rows`, `EventRow`, `Triple` and `Lit`. Ground triples, no blank node, rendered as sorted canonical N-Triples for the digest and as encoded SPARQL for a slot |
| `lattice_persistence.contract` | `read_contracts`, which reads each generated operation's kind, parameters, payload contract and digest contract from a compiled profile, and the data classes the compiler shares |
| `lattice_persistence.digest` | `request_digest`, which hashes a request as the profile's digest contract says |
| `lattice_persistence.bound` | `outside_bound` and `outside_events`, the subjects of a payload that are neither the root nor reached from it by owned edges, and the subjects of an append's triples that belong to no event of the batch |
| `lattice_persistence.check` | `refusals` and `check_request`, the caller check. Every parameter present and of its kind, an `xsd:long` exactly, a caller-named graph equal to the naming rule, `logGraphs` non-empty IRIs, the payload and event bounds, the reference modes and the checkpoint list. Every reason is named, before anything is sent |
| `lattice_persistence.audit` | `audit_outcome` (clean, failed or nothing examined), `run_audit`, `examined_query`, and `SparqlClient`, the one method of the adopter's client that the library asks for |

## Use

```python
from rdflib import Graph
from lattice_persistence import Iri, Lit, Payload, Triple, read_contracts, request_digest

profile = Graph().parse("compiled-profile.ttl")
replace = next(o for o in read_contracts(profile) if o.template_id == "cas-replace-named-graph-patch-log")

payload = Payload.of(Triple(Iri.encode("urn:ex:a"), Iri.encode("urn:ex:name"), Lit("Ada")))
values = {"root": "urn:ex:a", "expectedSeq": 3, "payloadTriples": payload,
          "assertTriples": Payload.of(), "retractTriples": Payload.of()}
digest = request_digest(replace, values)     # the value of $requestDigest
text = payload.sparql()                      # the value of {{{payloadTriples}}}
```

Before sending, `check_request(replace, values)` raises `CallerCheckError` naming every reason a request is refused. The options of `refusals` are
`allow_empty_log_graphs` (an audit over no graph then reports `NothingExamined`), `version_of` (what is a version, to check the reference modes)
and `membership` (a checkpoint's full list).

The values are keyed by the names of the operation's parameters and slots. A slot is a `Payload`, or `Rows` for `eventRows`.

## Tests

```bash
mise run check:persistence-library
```

The tests run every vector of [`contracts/persistence/vectors.json`](../../../contracts/persistence/README.md), read compiled profiles kept in `tests/data/`, and
hold the library to its dependencies. `tools/persistence/tests/test_library_contract.py` keeps those profiles and the library's reading of them
equal to what the compiler emits.

## Licence

MPL-2.0.
