<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio contracts

The data contracts between the [Configuration Studio](../../apps/config-studio)'s browser code, its [service](../../platform/config-studio-service) and its [worker](../../workers/README.md#configuration-studio-jobs-adr-a136) ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). They are contracts of a supported component: a change that would break a client is announced here and deprecated before it is removed, by the release policy once it is defined.

Every body is RDF. The terms are in [`studio-vocabulary.ttl`](studio-vocabulary.ttl), prefix `cst:`, and the configurations themselves use `dal:` and `srf:` unchanged. The one JSON document is [`amqp-topology.json`](amqp-topology.json).

| File | Holds |
|---|---|
| `studio-vocabulary.ttl` | workspaces, samples, jobs, job status, artefacts and gaps |
| `amqp-topology.json` | the exchange, the job queue, the dead-letter queue, and the writes exchange with its partition queues, declared identically by the service and the worker |
| `samples/samples.ttl` | the samples, each a list of repository files |
| `samples/lending-baseline.ttl` | a baseline for the lending sample, which the persistence example it pairs with does not declare |
| `samples/facility-baseline.ttl` | the facility agreement sample's baseline, which extends `lending-baseline.ttl` with a facility, lenders and drawdowns, the boundary shape of the facility and the carrier data |
| `samples/facility-{vocabulary,quantification,eligibility,persistence,surface}.ttl` | the facility agreement sample's five configurations, one file each, which refer to one another: eligibility draws on the schemes and range sets, persistence scopes a key by a vocabulary property, and surface reads a population from a scheme contract. [`tools/config_studio_stage.py`](../../tools/config_studio_stage.py) stages them merged as sample `facility`, and [`test_config_studio_facility_sample.py`](../../workers/tests/test_config_studio_facility_sample.py) checks each part and the deliberate resolution cases |

## Graphs

| Graph IRI | Written by | Holds |
|---|---|---|
| `urn:lattice:studio:ws:{ws}` | writer | the `cst:Workspace` node, whose IRI is the graph's: `rdfs:label`, `cst:createdAt`, `cst:modifiedAt`, `cst:baselineGraph`, `cst:fromSample` when it was made from a sample, and `cst:{name}Revision` for each graph name below. A revision the description lacks reads as 0 |
| `urn:lattice:studio:ws:{ws}:baseline:{n}` | writer, once | baseline revision n, from 1 |
| `urn:lattice:studio:ws:{ws}:{name}` | writer | the saved configuration `{name}`: `vocabulary` (`voc:` and `skos:`), `quantification` (`qnt:`), `eligibility` (`elg:`), `persistence` (`dal:`) or `surface` (`srf:`) |
| `urn:lattice:studio:job:{job}` | writer, for the service and then the worker | the `cst:Job` node, whose IRI is the graph's |
| `urn:lattice:studio:job:{job}:input` | writer, once | the configuration as submitted |

`{ws}` and `{job}` are lower-case UUIDs. Only the writers write these graphs (see Writes). The service and the worker read them from the store.

## HTTP

Every request and response body is RDF in UTF-8, unless the table says otherwise: `text/turtle` by default, or `application/rdf+xml`. A request body may be either, named by its `Content-Type`. A response is RDF/XML when the request's `Accept` ranks `application/rdf+xml` above `text/turtle` (a range without `q` counts 1, `*/*` favours Turtle), and every RDF response carries `Vary: Accept`. RDF/XML is written plain, one `rdf:Description` per subject, so an XSLT reads one regular shape. A graph whose predicate RDF/XML cannot write, one whose IRI does not end in an XML name, answers `406` in RDF/XML and stays readable as Turtle. An ETag names a graph's revision, the same in either syntax. A request body with another content type is refused with `415`, a body over 5 MiB with `413`, a body that does not parse, or RDF/XML that declares a DTD, with `400`, an unknown workspace or job with `404`.

| Method and path | Request | Response |
|---|---|---|
| `GET /api/health` | | `200`, `text/plain`, `ok` |
| `GET /api/vocabulary` | | `200`, the `dal:`, `srf:`, `fnd:` and `voc:` specifications and vocabularies merged, with an `ETag`. `304` for a matching `If-None-Match` |
| `GET /api/samples` | | `200`, every `cst:Sample` with its label and comment |
| `GET /api/samples/{id}` | | `200`, the sample's files merged into one graph |
| `GET /api/workspaces` | | `200`, every workspace's description |
| `POST /api/workspaces[?sample={id}]` | the baseline. `Slug` header, percent-encoded UTF-8, is the label. `sample` names the staged sample it was made from, which the description records | `201`, `Location: /api/workspaces/{ws}`, the description. `400` for a sample that is not staged, `422` for a baseline holding a subject of another part, by the rule of `PUT` below |
| `POST /api/workspaces` with `Content-Type: application/trig` | a file `GET …/export` wrote, here or elsewhere. `Slug`, when given, replaces its label | `201`, as above, a new workspace with the export's graphs and revisions. `422` for TriG that is not one workspace's export, or a graph holding another part's subject |
| `GET /api/workspaces/{ws}` | | `200`, the description |
| `DELETE /api/workspaces/{ws}` | | `204`. Drops the description, every baseline revision, the configurations and the workspace's jobs |
| `GET /api/workspaces/{ws}/export` | | `200`, `application/trig`, `Content-Disposition: attachment`, every graph of the workspace but its jobs |
| `GET /api/workspaces/{ws}/graphs/{name}` | `name` is `baseline` or a configuration's name | `200`, the graph, `ETag: "{revision}"` |
| `PUT /api/workspaces/{ws}/graphs/{name}` | the new graph. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision. `428` without `If-Match`, `412` when it is not the current revision, `422` when a subject belongs to another part by the rule the browser's import uses (a named subject belongs to the first of persistence, surface, eligibility, quantification and vocabulary whose namespace its type or predicates use, a SKOS concept or scheme to vocabulary, anything else to the baseline, and a blank node to the subject that refers to it). A baseline is written as a new revision graph |
| `POST /api/workspaces/{ws}/jobs?kind={validate,compile}&target={name}` | the configuration to check, which need not be saved, and the other configurations beside it as context | `202`, `Location: /api/jobs/{job}`, the job graph. `400` for another kind or target. Every configuration validates. `eligibility`, `persistence` and `surface` compile |
| `GET /api/workspaces/{ws}/jobs` | | `200`, the description of each compile job of the workspace: status, kind, target and times, without report or artefacts |
| `GET /api/jobs/{job}` | | `200`, the job graph |
| `DELETE /api/jobs/{job}` | | `204`. Drops the job graph and its input graph |

A write that no store writer answers within 10 seconds is `503`, and is dropped rather than applied later.

Every response carries `X-Content-Type-Options: nosniff`, and every `/api` response `Cache-Control: no-store`, except the vocabulary, which is revalidated by its `ETag`. No response carries `Access-Control-Allow-Origin`.

## Jobs

The service has the job graph written (see Writes) and publishes the job's IRI. The message body is that IRI in UTF-8, `content_type` `text/plain`, persistent, routed with `lattice.studio.jobs` on exchange `lattice.studio`. The worker refuses, without requeuing, a body that is not `urn:lattice:studio:job:` followed by a lower-case UUID, and the broker dead-letters it.

As written by the service:

```turtle
<urn:lattice:studio:job:{job}> a cst:Job ;
    cst:kind cst:Validate ;                     # or cst:Compile
    cst:target cst:Persistence ;                # or cst:Vocabulary, cst:Quantification, cst:Eligibility, cst:Surface
    cst:workspace <urn:lattice:studio:ws:{ws}> ;
    cst:configGraph <urn:lattice:studio:job:{job}:input> ;
    cst:baselineGraph <urn:lattice:studio:ws:{ws}:baseline:{n}> ;
    cst:status cst:Queued ;
    cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .
```

The worker replaces the whole job graph twice, each time as a `job-update` to the job's workspace's writer, keeping every triple above but `cst:status`. When it starts, it sets `cst:status cst:Running` and adds `cst:startedAt`. When it ends, it sets `cst:Succeeded` or `cst:Failed` and adds `cst:finishedAt`, and then:

- for `cst:Failed`, `cst:failureMessage`, saying why the job could not run, for example a missing input graph. A configuration that does not validate or compile is not a failure.
- for `cst:Succeeded`, `cst:conforms`, and `cst:report` naming an `sh:ValidationReport` in the same graph. Its `sh:result`s are pySHACL's for a validation. For a compilation they are the compiler's refusal, an `sh:Violation`, and its warnings, each `sh:Warning`, each with `cst:code` the compiler's name for it, `sh:resultMessage`, and `sh:focusNode` where the compiler names a node.
- for a successful compilation, one `cst:artefact` per file, with `cst:path`, `cst:mediaType`, `cst:content` and `cst:group`. For persistence these are `compiled-profile.ttl` and each SPARQL file `instantiate` writes, grouped by target. For surface, each file `compile` writes, grouped by contract.
- for a persistence compilation, one `cst:gap` per entry of `python -m persistence gaps`, with `cst:group`, `cst:obligation` and `cst:message`.
- for a persistence validation, the compiler's refusal and warnings too, since the `dal:` shapes do not see a `dal:DataAccessProfile` that declares several dimensions.
- for a vocabulary validation, one `cst:resolution` per scheme contract, time segment and set of active scopes, with `cst:contract`, `cst:validFrom` and `cst:validTo` where bounded, `cst:context` per active scope, `cst:outcome`, and `cst:scheme` and `cst:binding`, or `cst:tied` for a conflict, as `tools/vocabulary` resolves it.
- for an eligibility validation, each condition compiled by `tools/mork_compilers`, its refusal an `sh:Violation` with `cst:code` `IRCompileError`. One `cst:expansion` per member of a concept condition's resolved scheme, with `cst:condition`, `cst:concept` and `cst:decision`. One `cst:testResult` per `elg:Question`, decided by the condition's compiled SPARQL, with `cst:question`, `cst:condition`, `cst:decision`, `cst:diagnostic` when Undetermined, and `cst:passed` against the question's `cst:expectedDecision`. A failed test is an `sh:Violation` with `cst:code` `TestFailed`, and makes the job not conform. A condition or question may name `cst:resolutionTime` and `cst:resolutionScope`, and otherwise resolves at the job's submission time with no scope.
- for an eligibility compilation, `decision.rq` and `shapes.ttl` for each condition and admission profile, grouped by its local name.

The configuration a job checks is its input graph. The worker reads a missing baseline graph as empty, since the store keeps no empty graph, and fails a job whose input graph is missing.

Running a job twice gives the same graph but for its times, so a redelivered message is harmless.

## Writes

Every write to the store is a command to the writer of its workspace (ADR-A136, amendment on partitioned writers). A command is published to exchange `lattice.studio.writes`, of type `x-consistent-hash` (RabbitMQ's `rabbitmq_consistent_hash_exchange` plugin), with the workspace's id as its routing key. The exchange routes it to one of the 8 queues `lattice.studio.writes.0` to `.7`, each bound with weight `1`, durable, dead-lettering to `lattice.studio.dlx`, and with a single active consumer, so one writer applies a workspace's commands in order. The number of partitions is fixed here, since changing it moves workspaces between queues.

A command's fields are AMQP headers, and the graphs it carries are its body, `content_type` `application/n-quads`, persistent. Every command carries `id`, a lower-case UUID its sender chooses, and `sender`, `service` or `worker`.

| `command` | Other headers | Body | Sent by |
|---|---|---|---|
| `create` | `workspace`, `label`, `at`, `sample` when made from one | the baseline, in the default graph | service |
| `save` | `workspace`, `part`, `expect` (the revision `If-Match` named, a number), `at` | the graph, in the default graph | service |
| `import` | `workspace` (the new id), `label`, `at` | every graph of the export, already named under the new id | service |
| `delete-workspace` | `workspace` | none | service |
| `submit-job` | `workspace`, `job` | the job graph and its input graph, named | service |
| `job-update` | `workspace`, `job` | the job graph, named | worker, or the service when the job could not be published |
| `delete-job` | `workspace`, `job` | none | service, and its sweep of jobs finished longer ago than the retention |

`workspace` and `job` are the ids, `at` an `xsd:dateTime`. The service sets `reply_to` to `amq.rabbitmq.reply-to`, a `correlation_id`, and an `expiration` of its 10-second wait, and the writer answers with headers alone: `status` (200 applied, 400 refused, 404 no such workspace or job, 412 a stale `expect`), `revision` (the new one, or the current one for 412) and `message`. The worker publishes with confirms and no reply.

The writer checks every command, whatever its sender checked: the ids, that a command carries only the graphs its kind may, part membership by the rule of `PUT`, that a job names its workspace, its own input, the workspace's baseline and `cst:Queued`, and that a `job-update` changes nothing on the job node but `cst:status`, `cst:startedAt`, `cst:finishedAt`, `cst:failureMessage`, `cst:conforms`, `cst:report`, `cst:artefact`, `cst:gap`, `cst:resolution`, `cst:expansion` and `cst:testResult`, compared by value. A `job-update` for a deleted job is dropped. A refused command is dead-lettered.

A writer applies the commands waiting for it, up to 64, in one SPARQL Update request, one transaction. Each command's first operation inserts its `cst:Receipt` only where its precondition holds in the store: a save's expected revision, a creation's or an import's absent workspace, a job's workspace. Its other operations require that receipt, so a command applies whole or not at all, and the receipts present after the commit are the commands applied. A command whose receipt already exists, such as one redelivered after a lost acknowledgement, is answered from its receipt and not applied again. A batch the store refuses is retried whole.

| Receipt graph | Holds |
|---|---|
| `urn:lattice:studio:ws:{ws}:receipts` | the receipts of the workspace's own writes and of its jobs' deletions, deleted with the workspace |
| `urn:lattice:studio:job:{job}:receipts` | the receipts of a job's submission and updates, deleted with the job |
| `urn:lattice:studio:receipts` | the receipt of each workspace's deletion |

A receipt, `urn:lattice:studio:receipt:{id}`, has `cst:commandId`, `cst:command` (the cause), `cst:sender`, `cst:workspace`, `cst:job` where there is one, `cst:requestedAt` where the command has a time, `cst:committedAt` (the transaction time), `cst:wrote` for each graph and `cst:receiptRevision` for a save or a creation. No principal is recorded, since the studio authenticates no one. An export holds no receipt.

