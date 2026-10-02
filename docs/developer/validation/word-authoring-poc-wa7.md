<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA7, Worker runtime

**Unit:** `word-authoring-poc` (WAP), ADR-A114
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA7: Worker runtime"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

The wording analysis worker is the one place a `wording-analysis-request` event becomes a
`wording-analysis-result` event: it reads the Wording graph named by the request (never RDF on
the wire), reasons about it with the WA6 `wording_le` reading, writes the proposed `ins:` graph
back to the same store under the requested IRI, and publishes a result that validates against the
committed schema. Acknowledgement follows the request's fate precisely: a successful publish acks,
a message that fails validation is dead-lettered without a retry (it will never become valid by
being retried), and an infrastructure failure (the store is unreachable) is nacked with a requeue
and re-raised, so the broker retries and the fault is still visible to the operator.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| S7-01 | the facility `.nt` fixture as the wording graph in a fake store / a valid request consumed through the adapter / the proposal graph is put at `proposalGraphIri`, one `completed` result is published that validates against `wording-analysis-result`, the delivery is acked | L1 | the happy path writes back and publishes a schema-valid result, and acks | `test_a_valid_request_is_analysed_proposed_published_and_acked` passes | + |
| S7-02 | an empty fake store / consumed / one `failed` result with error `wording graph not found`, acked (not nacked: this is a valid, handled business outcome) | L1 | a missing graph is a normal, ack-worthy outcome, not a delivery fault | passes | - |
| S7-03 | malformed JSON, and separately a message missing `proposalGraphIri` / handled through the adapter / nacked without requeue, nothing published | L1 | an unparseable or contract-violating message is dead-lettered, never retried, never published | both `test_malformed_json_is_nacked_without_requeue_and_nothing_is_published` and `test_a_request_missing_a_required_field_is_nacked_without_requeue_and_nothing_is_published` pass | - |
| S7-04 | a store whose `put_graph` raises `OSError` / handled / nacked with requeue, the exception re-raised, nothing published | L1 | an infrastructure fault is retried and surfaced, not swallowed as a business failure | `test_a_put_graph_failure_is_nacked_with_requeue_propagates_and_publishes_nothing` passes | - |
| S7-05 | the packaged topology (`lattice_workers/amqp-topology.json`) / compared with `contracts/authoring/amqp-topology.json` / equal | L3 | the worker declares exactly the topology the contract and the Java service agree on | `test_the_packaged_topology_matches_the_committed_contract` passes | + |
| S7-06 | a local `http.server` stub in a thread / `get_graph` and `put_graph` / the URL carries the encoded graph IRI, the Basic auth header is present only when configured, a 404 raises `GraphNotFound` | L1 | the Graph Store Protocol client forms requests Fuseki actually accepts, and never guesses at a missing graph | five tests (`test_get_graph_url_carries_the_encoded_graph_iri`, `test_put_graph_sends_turtle_with_content_type`, `test_basic_auth_header_is_present_when_configured`, `test_no_auth_header_when_not_configured`, `test_a_404_raises_graph_not_found`) pass | +/- |
| S7-07 | `wording_analysis_main.read_config` / a required variable missing / `ValueError` naming the variable; both present / the optional variables default or read through | L1 | the process fails fast and names the problem, rather than connecting with a blank URL | four `test_config_reader_*` tests pass | - |
| S7-08 | `RabbitMqResultPublisher` / one result published / the four message properties (`content_type`, `message_id`, `correlation_id`, `delivery_mode`) are set, and both `message_id` and `correlation_id` are the job ID | L1 | a result is correlatable back to its request on the wire, not just in the JSON body | `test_the_publisher_sets_the_four_message_properties` passes | + |

All 16 WA7 tests pass. `mise run check:authoring-worker` reports 83 passed (32 from WA6's
`test_wording_le.py`, 16 new, 35 from `test_authoring_contracts.py`).

## One command

```
mise run check:authoring-worker
```

## Artefacts to inspect

- [`workers/src/lattice_workers/fuseki_gsp.py`](../../../workers/src/lattice_workers/fuseki_gsp.py)
- [`workers/src/lattice_workers/wording_analysis_worker.py`](../../../workers/src/lattice_workers/wording_analysis_worker.py)
- [`workers/src/lattice_workers/wording_analysis_main.py`](../../../workers/src/lattice_workers/wording_analysis_main.py)
- [`workers/src/lattice_workers/amqp-topology.json`](../../../workers/src/lattice_workers/amqp-topology.json), the packaged copy
- [`workers/tests/test_wording_analysis_worker.py`](../../../workers/tests/test_wording_analysis_worker.py)

## Self-probe

Plan: "make the adapter requeue on `ValueError`. S7-03 fails."

Changed `RabbitMqWordingAnalysisWorker.handle`'s `except (ValueError, UnicodeDecodeError,
json.JSONDecodeError)` branch from `requeue=False` to `requeue=True`, and ran only the S7-03
tests. Both failed as predicted:

```
FAILED test_malformed_json_is_nacked_without_requeue_and_nothing_is_published
FAILED test_a_request_missing_a_required_field_is_nacked_without_requeue_and_nothing_is_published
2 failed, 14 deselected
```

Reverted. This is the first of WA3, WA5, WA6 and WA7's prescribed self-probes to actually bite as
written, with no replacement test needed. No corresponding "vacuous probe" entry is added to the
status record's open question for this slice.

## Implementer choices

| Choice | Reasoning |
|---|---|
| `wordingGraph` field validation reuses `graph_validation.GraphReference.from_payload` | it is exactly the same `GraphRef` shape already validated elsewhere in this worker package; avoids a second, slightly different implementation of the same four-field check |
| The topology JSON is copied verbatim into `lattice_workers/amqp-topology.json` (package root, not under `wording_le/`) | `wording_le` is the LE-reading package; the topology is a worker-runtime concern, so it sits beside `wording_analysis_worker.py` instead |
| `declare_topology` reads the topology data structure directly (not hardcoded constants, unlike Java's `Topology.java`) | Python has no compile-time constant-folding benefit here, and reading the data keeps the single packaged copy the only place that can drift from the contract (S7-05 already guards the copy itself) |
| The graph content hash (`_graph_hash`) is a local `sha256` over sorted N-Triples lines, mirroring the shape of Java's `CanonicalHash` but implemented independently with `rdflib` | the plan explicitly says this hash is "worker-local... not comparable with Java's"; no shared library exists across the Java/Python boundary for this POC |
| `RabbitMqResultPublisher` sets both `message_id` and `correlation_id` to the job ID (not the request's own `correlationId` field) | this is what the plan's `consume` step 6 specifies, literally and deliberately differing from the existing `RabbitMqSurfaceResultPublisher` (Surface jobs), which correlates on the result's own `correlationId` field |
| `wording_analysis_main._clock()` formats to millisecond precision (`...%f`, truncated to 3 digits, plus `Z`) | matches the common schema's `Timestamp` pattern (`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z`) while staying human-readable; the `WordingAnalysisConsumer`'s own `clock` parameter accepts any zero-argument callable, so tests inject a fixed string instead |

## Deliberate non-coverage

- No test exercises `wording_analysis_main.main()` end to end (a real RabbitMQ and Fuseki
  connection): that is WA9/system-level territory (`check:authoring-stack`), not this slice.
- The retry loop in `_connect` (every 2 seconds on `AMQPConnectionError`) is not under test: it has
  no branching logic to assert on beyond "it loops", and a real sleep-based test would be slow and
  flaky. Covered qualitatively by code review only.
- `declare_topology`'s idempotency (safe to call more than once) is asserted by the Java side's
  equivalent `TopologyTest`; this slice only checks the Python copy of the data matches the
  contract (S7-05), not that re-declaring is harmless against a real broker.
