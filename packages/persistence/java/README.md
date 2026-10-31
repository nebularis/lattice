<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-persistence (Java)

The caller library of [ADR-A132](../../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md) for Java, the sibling of the [Python library](../python/README.md). JDK 25 or later. Apache Jena ARQ is its only dependency, used to read a compiled profile as RDF, and JUnit is at test scope only. Package `org.nebularis.lattice.persistence`, with the same concepts as the Python library.

It is not published to a Maven repository, and it is not a module of `platform/pom.xml`. Build and install it from the repository root:

```bash
mvn -f packages/persistence/java/pom.xml install
```

| Type | Holds |
|---|---|
| `Iri`, `Lit`, `Term`, `Var`, `SparqlInteger` | the term encoders. An `Iri` or a `Lit` that would break out of a SPARQL request cannot be built. A blank node has no type, so no payload holds one |
| `Triple`, `Payload`, `EventRow`, `Rows` | ground triples rendered as sorted canonical N-Triples for the digest and as encoded SPARQL for a slot |
| `OperationContract` | `OperationContract.read(model)`, which reads each generated operation's kind, parameters, payload contract and digest contract from a compiled profile held in a Jena `Model` |
| `RequestDigest` | `requestDigest`, which hashes a request as the profile's digest contract says |
| `Bound` | `outsideBound` and `outsideEvents`, the subjects of a payload that are neither the root nor reached from it by owned edges, and the subjects of an append's triples that belong to no event of the batch |
| `CallerCheck`, `CallerCheckException`, `Refusal` | `refusals` and `check`, the caller check. Every parameter present and of its kind, an `xsd:long` exactly, a caller-named graph equal to the naming rule, `logGraphs` non-empty IRIs, the payload and event bounds, the reference modes and the checkpoint list. Every reason is named, before anything is sent |
| `Audit`, `AuditOutcome`, `AuditResult`, `SelectClient` | `Audit.outcome` (clean, failed or nothing examined), `Audit.run`, `Audit.examinedQuery`, and `SelectClient`, the one method of the adopter's client that the library asks for |

The library makes no store call.

## Use

```java
Model profile = RDFDataMgr.loadModel("compiled-profile.ttl");
OperationContract replace = OperationContract.read(profile).stream()
    .filter(o -> o.templateId().equals("cas-replace-named-graph-patch-log")).findFirst().orElseThrow();

Payload payload = Payload.of(new Triple(Iri.of("urn:ex:a"), Iri.of("urn:ex:name"), new Lit("Ada")));
Map<String, Object> values = Map.of("root", "urn:ex:a", "expectedSeq", 3, "payloadTriples", payload,
    "assertTriples", Payload.of(), "retractTriples", Payload.of());
String digest = RequestDigest.requestDigest(replace, values);   // the value of $requestDigest
String text = payload.sparql();                                  // the value of {{{payloadTriples}}}
```

Before sending, `CallerCheck.check(replace, values)` throws `CallerCheckException` naming every reason a request is refused. The options of `CallerCheck.refusals` are `allowEmptyLogGraphs` (an audit over no graph then reports `NothingExamined`), `versionOf` (what is a version, to check the reference modes) and `membership` (a checkpoint's full list).

The values are keyed by the names of the operation's parameters and slots. A value is an `Iri`, a `Lit`, a `Payload`, a `Rows`, a `String`, an integral number, or an `Iterable` for a `RegistryList`. A slot is a `Payload`, or `Rows` for `eventRows`. A Jena literal node is read as a literal where a `Long` or a `Position` is declared. `Payload.ofJena` builds a payload from Jena triples and refuses a blank node.

In the instantiated SPARQL a slot is the plain-text marker `{{{name}}}`. The caller replaces the marker with the `sparql()` text of the value, by substitution and with no template engine. `Audit.run` does this for `logGraphs`. An unfilled marker is a syntax error, so a forgotten slot fails closed.

## Differences from the Python library

* A term has a type, so the Python tests that pass a bare string or a blank node where a term is expected have no Java counterpart. They do not compile.
* `versionOf` is a `Predicate<Iri>`, so what the caller does not know to be a version is not one.
* Lines and names sort by code point, which is the order of the UTF-8 bytes, and not by UTF-16 code unit as `String.compareTo` does.
* The patterns for a language tag, a digest and an `xsd:long` lexical form match the whole text. Python's `$` also accepts a trailing line feed, which Java refuses.
* The vectors are not validated against `vectors.schema.json`, which needs a JSON Schema library. `verify-vectors.py` and the Python test do that.

## Tests

```bash
mise run check:persistence-library-java
```

The tests run every vector of [`contracts/persistence/vectors.json`](../../../contracts/persistence/README.md) and read the compiled profiles kept in `../python/tests/data/`, through the `persistence.dir` system property that `pom.xml` sets. They port the Python library's payload, contract, caller check and slot-injection tests, and run the slot text through Jena's SPARQL parser.

## Licence

MPL-2.0.
