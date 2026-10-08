<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA5, Fuseki, RabbitMQ and the runnable service

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA5
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

WA4 proved the service's logic against in-memory test seams. This slice proves the same logic
survives contact with the two real backing services it will actually run against, and gives it an
entry point that can start, stop and be probed like any other container in the compose stack
(WA10). Three invariants carry it.

First, **the service recovers from its dependencies starting in any order.** `FusekiAuthoringStore`
and `RabbitMqAnalysisBus` both retry their connection (up to 30 attempts, 2 seconds apart) rather
than fail fast on construction, because `docker compose up` gives no ordering guarantee between
containers. Second, **a result the worker cannot produce never jams the queue.** Rejecting a
delivery with `basicNack(tag, false, false)` relies on the dead-letter exchange named in
`amqp-topology.json`: lose that wiring and a malformed message would either requeue forever or
vanish silently. `Topology` is the single place that wiring is declared, so it can be checked
against the committed file by comparison rather than by trusting two hand-maintained copies agree.
Third, **the shaded jar is a faithful standalone artefact**, not merely "the classes compile": Jena
registers its RDF, SPARQL, SHACL and RDFS subsystems through `META-INF/services` files that five
different `jena-*` jars each contribute one line to, and a plain shade (last file wins) silently
drops four of those five lines.

## Test cases

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| S5-01 | `AuthoringConfig` / defaults, overrides, port `abc`, base without `/`, missing password / values, then three exceptions naming the variable, none containing the password value | L1 | +/− | pass |
| S5-02 | Fuseki container / `ensureReady` twice, put then get a graph, get an absent graph / no error, isomorphic, empty | L4 | + | pass |
| S5-03 | RabbitMQ container / declare twice, publish a request / no error, the message on the requested queue with the four properties | L4 | + | pass |
| S5-04 | RabbitMQ container / a valid result and a malformed one on the completed queue / the handler gets the first, the second lands on `lattice.authoring.dead` | L4 | +/− | pass |
| S5-05 | both containers, the real store, bus and API, and an in-test consumer that answers each request with a completed result from a fixture / a sample submitted / the job completes within 10 seconds and the analysis view and the wording Turtle are served | L4 | + | pass |
| S5-06 | `HealthProbe` against a stub server answering 200, then 503, then a closed port / exit codes 0, 1, 1 | L1 | +/− | pass |
| S5-07 | the shaded jar / `java -jar target/authoring-service.jar --self-check` run from an IT / exit 0 and `self-check ok` (proves Jena initialises from the jar) | L4 | + | pass |
| S5-08 | `Topology` / compared with `amqp-topology.json` / equal | L3 | + | pass |

Carried by seven test classes: `AuthoringConfigTest` (S5-01, 6 cases), `HealthProbeTest` (S5-06),
`TopologyTest` (S5-08) run under the regular unit-test command; `FusekiAuthoringStoreIT` (S5-02),
`RabbitMqAnalysisBusIT` (S5-03, S5-04), `AuthoringServiceStackIT` (S5-05) and `SelfCheckIT` (S5-07,
plus the self-probe's own test, below) run under the `authoring-it` profile. The module runs 85
tests under the regular command (WA2's 48, WA3's 15, WA4's 14, WA5's 8) and a further 6 under the
IT profile, 91 in total.

## One command

From the repository root:

```
mise run check:authoring-service
```

prints `Tests run: 85, Failures: 0, Errors: 0, Skipped: 0` and `BUILD SUCCESS` with no containers
needed. Then, with Docker running:

```
mise run check:authoring-service-it
```

prints `Tests run: 6, Failures: 0, Errors: 0, Skipped: 0` and `BUILD SUCCESS`. Expect this to take
about a minute (container pulls, if not already cached, plus two container startups).

Re-run `mise run check:java` and `mise run check:authoring-contracts` to confirm nothing else moved.

## Artefacts to inspect

| What | Where | Look for |
|---|---|---|
| retry loops | [FusekiAuthoringStore.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/store/FusekiAuthoringStore.java), [RabbitMqAnalysisBus.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/messaging/RabbitMqAnalysisBus.java) | 30 attempts, 2 seconds apart, in `ensureReady`/the constructor |
| the topology, once | [Topology.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/messaging/Topology.java) and [amqp-topology.json](../../../contracts/authoring/amqp-topology.json) | the same three queues, the same dead-letter wiring |
| the entry point | [AuthoringServiceMain.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/app/AuthoringServiceMain.java) | `--self-check` needs no network; `run()` builds exactly WA4's collaborators plus the WA5 store and bus |
| the merge defect and the probe that actually finds it | [SelfCheckIT.java](../../../platform/authoring-service/src/test/java/org/nebularis/lattice/authoring/app/SelfCheckIT.java) | `theShadedJarMergesEveryJenaSubsystemRegistration`, and "Self-probe" below |
| configuration and the IT command | [README.md](../../../platform/authoring-service/README.md) | the eight environment variables, `mise run check:authoring-service-it` |

## Self-probe

The plan's prescribed break — remove `ServicesResourceTransformer` from the shade configuration —
was made, and **`SelfCheckIT.theShadedJarsSelfCheckExitsZero` (the test the plan names) still
passes.** Run directly, to rule out a test-harness artefact:

```
java -jar platform/authoring-service/target/authoring-service.jar --self-check
```

prints `self-check ok` and exits 0 whether or not the transformer is present. The reason is
checkable directly. With the transformer removed, the shaded jar's
`META-INF/services/org.apache.jena.sys.JenaSubsystemLifecycle` holds only:

```
org.apache.jena.riot.system.InitRIOT
org.apache.jena.sparql.system.InitARQ
org.apache.jena.rdfs.sys.InitRDFS
```

against five lines with it restored (`org.apache.jena.sys.InitJenaCore` and
`org.apache.jena.shacl.sys.InitShacl` are also present). The self-check's own code path — loading
the vocabulary, shapes, schemas, templates and samples, then validating each with
`ShaclValidator.get().validate(...)` called directly — evidently does not exercise anything that
needs those two subsystems' registrations, so nothing observably breaks. This is WA3's finding
repeated: a plan-prescribed probe can be non-vacuous in general and still miss the one code path a
given test happens to exercise.

**A probe that does bite was added instead**, as a second test in the same class,
`theShadedJarMergesEveryJenaSubsystemRegistration`, which opens the built jar and asserts its
`JenaSubsystemLifecycle` services file contains all five expected provider class names — the actual
thing the transformer is responsible for, checked directly rather than through a side effect that
may or may not depend on it. With the transformer removed:

```
SelfCheckIT.theShadedJarMergesEveryJenaSubsystemRegistration:61
expected [org.apache.jena.sys.InitJenaCore, org.apache.jena.riot.system.InitRIOT,
org.apache.jena.sparql.system.InitARQ, org.apache.jena.shacl.sys.InitShacl,
org.apache.jena.rdfs.sys.InitRDFS] but the merged jar only has
[org.apache.jena.riot.system.InitRIOT, org.apache.jena.sparql.system.InitARQ,
org.apache.jena.rdfs.sys.InitRDFS]
```

The transformer was restored and `mise run check:authoring-service-it` re-run green at 6 tests.

## Implementer choices

| Left open | Chosen | Why |
|---|---|---|
| `FusekiAuthoringStore`'s exact 404-handling API | catch `org.apache.jena.atlas.web.HttpException`, compare `getStatusCode()` to `HttpSC.NOT_FOUND_404` | confirmed against Jena 5.1.0 by compiling, not guessed from documentation |
| the shared `HttpClient`'s `Authenticator` | one instance, used both by `RDFConnectionRemote`'s internal requests and this class's own admin GET/POST calls | matches the plan's wording exactly ("an HttpClient whose java.net.Authenticator answers with the admin credentials ... Uses java.net.http.HttpClient for the admin calls"), and Java's `HttpClient` Authenticator responds automatically to Fuseki's 401 challenge, so no header is built by hand |
| `RabbitMqAnalysisBus`'s exchange type | the string literal `"topic"`, not `BuiltinExchangeType.TOPIC` | matches the existing convention in `platform-outbox`'s `RabbitMqEventPublisher` |
| the dead-letter queue's binding | bound to `DEAD_LETTER_EXCHANGE` with routing key `#`, not to the main exchange | a dead-lettered message is republished to the configured dead-letter exchange under its original routing key, so the catch-all queue has to listen there, not on the main exchange |
| S5-05's "in-test consumer" | a raw RabbitMQ consumer (not an `AnalysisBus`) that reads `REQUESTED_QUEUE`, copies the three job fields and the `proposalGraphIri` into the `wording-analysis-result--completed-minimal.json` fixture, and publishes it | stands in for the WA6/WA7 worker, which does not exist yet. Using the real fixture, not a hand-built object, keeps this test honest about the real event shape |
| `AuthoringConfig`'s secret-safety test | asserted on all three exception paths that can fire while a password is present (port, base IRI, missing AMQP URI with the password supplied), not only the "missing password" case | the plan's "none containing the password value" reads as a property of every exception the type can throw, not of one case |

## Deliberate non-coverage

- **The S5-07 probe's non-bite**, covered in full under Self-probe above, with a second test added
  to give the slice a probe that actually fails on the regression it targets.
- **Fuseki or RabbitMQ going down after the service has started** (mid-run reconnection). The retry
  loops run once, at construction; `ping()`/`health()` report the failure but nothing reconnects
  automatically. A POC-grade limitation, consistent with ADR-A118's scope.
- **The admin dataset-creation path when a dataset of the same name already exists with a different
  type** (e.g. `mem` instead of `tdb2`). `ensureReady` only distinguishes "exists" from "absent".
- **Message redelivery after a worker crash mid-processing** (RabbitMQ's own redelivery-on-requeue
  semantics for an unacked, disconnected consumer). Not exercised; S5-04 only covers the
  reject-and-dead-letter path.
- **Running the compose stack itself.** WA10.

Unit-wide non-coverage, cited by every pack: CCS assembly, amendments, tables and versioned
elements. LE2 parsing of the generated program. Concurrent editing. Authentication. Poison-message
retry limits. Real Word, except through WA11's manual checklist.
