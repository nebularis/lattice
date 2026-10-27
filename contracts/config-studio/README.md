<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio contracts

The data contracts between the [Configuration Studio](../../apps/config-studio)'s browser code, its [service](../../platform/config-studio-service) and its [worker](../../workers/README.md#configuration-studio-jobs-adr-a136) ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). A proof of concept, so nothing outside the studio may depend on them.

Every body is RDF. The terms are in [`studio-vocabulary.ttl`](studio-vocabulary.ttl), prefix `cst:`, and the configurations themselves use `dal:` and `srf:` unchanged. The one JSON document is [`amqp-topology.json`](amqp-topology.json).

| File | Holds |
|---|---|
| `studio-vocabulary.ttl` | workspaces, samples, jobs, job status, artefacts and gaps |
| `amqp-topology.json` | the exchange, the job queue and the dead-letter queue, declared identically by the service and the worker |
| `samples/samples.ttl` | the samples, each a list of repository files |
| `samples/lending-baseline.ttl` | a baseline for the lending sample, which the persistence example it pairs with does not declare |

## Graphs

| Graph IRI | Written by | Holds |
|---|---|---|
| `urn:lattice:studio:ws:{ws}` | service | the `cst:Workspace` node, whose IRI is the graph's: `rdfs:label`, `cst:createdAt`, `cst:modifiedAt`, `cst:baselineGraph`, `cst:baselineRevision`, `cst:surfaceRevision`, `cst:persistenceRevision` |
| `urn:lattice:studio:ws:{ws}:baseline:{n}` | service, once | baseline revision n, from 1 |
| `urn:lattice:studio:ws:{ws}:surface` | service | the saved `srf:` configuration |
| `urn:lattice:studio:ws:{ws}:persistence` | service | the saved `dal:` configuration |
| `urn:lattice:studio:job:{job}` | service, then worker | the `cst:Job` node, whose IRI is the graph's |
| `urn:lattice:studio:job:{job}:input` | service, once | the configuration as submitted |

`{ws}` and `{job}` are lower-case UUIDs.

## HTTP

Every request and response body is `text/turtle` in UTF-8, unless the table says otherwise. A request body with another content type is refused with `415`, a body over 5 MiB with `413`, Turtle that does not parse with `400`, an unknown workspace or job with `404`.

| Method and path | Request | Response |
|---|---|---|
| `GET /api/health` | | `200`, `text/plain`, `ok` |
| `GET /api/vocabulary` | | `200`, the `dal:`, `srf:`, `fnd:` and `voc:` specifications and vocabularies merged, with an `ETag`. `304` for a matching `If-None-Match` |
| `GET /api/samples` | | `200`, every `cst:Sample` with its label and comment |
| `GET /api/samples/{id}` | | `200`, the sample's files merged into one graph |
| `GET /api/workspaces` | | `200`, every workspace's description |
| `POST /api/workspaces` | the baseline. `Slug` header, percent-encoded UTF-8, is the label | `201`, `Location: /api/workspaces/{ws}`, the description |
| `GET /api/workspaces/{ws}` | | `200`, the description |
| `DELETE /api/workspaces/{ws}` | | `204`. Drops the description, every baseline revision and both configurations |
| `GET /api/workspaces/{ws}/graphs/{name}` | `name` is `baseline`, `surface` or `persistence` | `200`, the graph, `ETag: "{revision}"` |
| `PUT /api/workspaces/{ws}/graphs/{name}` | the new graph. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision. `428` without `If-Match`, `412` when it is not the current revision. A baseline is written as a new revision graph |
| `POST /api/workspaces/{ws}/jobs?kind={validate,compile}&target={surface,persistence}` | the configuration to check, which need not be saved | `202`, `Location: /api/jobs/{job}`, the job graph. `400` for another kind or target |
| `GET /api/workspaces/{ws}/jobs` | | `200`, the description of each compile job of the workspace: status, kind, target and times, without report or artefacts |
| `GET /api/jobs/{job}` | | `200`, the job graph |
| `DELETE /api/jobs/{job}` | | `204`. Drops the job graph and its input graph |

Every response carries `X-Content-Type-Options: nosniff`, and every `/api` response `Cache-Control: no-store`, except the vocabulary, which is revalidated by its `ETag`. No response carries `Access-Control-Allow-Origin`.

## Jobs

The service writes the job graph and publishes the job's IRI. The message body is that IRI in UTF-8, `content_type` `text/plain`, persistent, routed with `lattice.studio.jobs` on exchange `lattice.studio`. The worker refuses, without requeuing, a body that is not `urn:lattice:studio:job:` followed by a lower-case UUID, and the broker dead-letters it.

As written by the service:

```turtle
<urn:lattice:studio:job:{job}> a cst:Job ;
    cst:kind cst:Validate ;                     # or cst:Compile
    cst:target cst:Persistence ;                # or cst:Surface
    cst:workspace <urn:lattice:studio:ws:{ws}> ;
    cst:configGraph <urn:lattice:studio:job:{job}:input> ;
    cst:baselineGraph <urn:lattice:studio:ws:{ws}:baseline:{n}> ;
    cst:status cst:Queued ;
    cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .
```

The worker replaces the whole job graph twice, keeping every triple above but `cst:status`. When it starts, it sets `cst:status cst:Running` and adds `cst:startedAt`. When it ends, it sets `cst:Succeeded` or `cst:Failed` and adds `cst:finishedAt`, and then:

- for `cst:Failed`, `cst:failureMessage`, saying why the job could not run, for example a missing input graph. A configuration that does not validate or compile is not a failure.
- for `cst:Succeeded`, `cst:conforms`, and `cst:report` naming an `sh:ValidationReport` in the same graph. Its `sh:result`s are pySHACL's for a validation. For a compilation they are the compiler's refusal, an `sh:Violation`, and its warnings, each `sh:Warning`, each with `cst:code` the compiler's name for it, `sh:resultMessage`, and `sh:focusNode` where the compiler names a node.
- for a successful compilation, one `cst:artefact` per file, with `cst:path`, `cst:mediaType`, `cst:content` and `cst:group`. For persistence these are `compiled-profile.ttl` and each SPARQL file `instantiate` writes, grouped by target. For surface, each file `compile` writes, grouped by contract.
- for a persistence compilation, one `cst:gap` per entry of `python -m persistence gaps`, with `cst:group`, `cst:obligation` and `cst:message`.

Running a job twice gives the same graph but for its times, so a redelivered message is harmless.
