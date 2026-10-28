<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio contracts

The data contracts between the [Configuration Studio](../../apps/config-studio)'s browser code, its [service](../../platform/config-studio-service) and its [worker](../../workers/README.md#configuration-studio-jobs-adr-a136) ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). They are contracts of a supported component: a change that would break a client is announced here and deprecated before it is removed, by the release policy once it is defined.

Every body is RDF. The terms are in [`studio-vocabulary.ttl`](studio-vocabulary.ttl), prefix `cst:`, and the configurations themselves use `dal:` and `srf:` unchanged. The one JSON document is [`amqp-topology.json`](amqp-topology.json).

| File | Holds |
|---|---|
| `studio-vocabulary.ttl` | workspaces, samples, jobs, job status, artefacts and gaps |
| `amqp-topology.json` | the exchange, the job queue, the dead-letter queue, and the writes super stream with its partitions, declared identically by the service, the writer and the worker |
| `samples/samples.ttl` | the samples, each a list of repository files |
| `samples/lending-baseline.ttl` | a baseline for the lending sample, which the persistence example it pairs with does not declare |
| `samples/facility-baseline.ttl` | the facility agreement sample's baseline, which extends `lending-baseline.ttl` with a facility, lenders and drawdowns, the boundary shape of the facility and the carrier data |
| `samples/facility-{vocabulary,quantification,eligibility,persistence,surface}.ttl` | the facility agreement sample's five configurations, one file each, which refer to one another: eligibility draws on the schemes and range sets, persistence scopes a key by a vocabulary property, and surface reads a population from a scheme contract. [`tools/config_studio_stage.py`](../../tools/config_studio_stage.py) stages them merged as sample `facility`, and [`test_config_studio_facility_sample.py`](../../workers/tests/test_config_studio_facility_sample.py) checks each part and the deliberate resolution cases |

## Graphs

Fuseki serves the one database as two services: `studio` reads only, through query and the graph store protocol's reads, and is given to the service and the worker. `studio-write` also updates, and is given to the store writer alone.

| Graph IRI | Written by | Holds |
|---|---|---|
| `urn:lattice:studio:ws:{ws}` | writer | the `cst:Workspace` node, whose IRI is the graph's: `rdfs:label`, `cst:createdAt`, `cst:modifiedAt`, `cst:baselineGraph`, `cst:fromSample` when it was made from a sample, and `cst:{name}Revision` for each graph name below. A revision the description lacks reads as 0 |
| `urn:lattice:studio:ws:{ws}:baseline:{n}` | writer, once | baseline revision n, from 1 |
| `urn:lattice:studio:ws:{ws}:{name}` | writer | the saved configuration `{name}`: `library` (`wrd:`, forms and their variables, ADR-A138), `assembly` (`cst:Assembly` nodes and the `wrd:VariableValue` records they set), `meaning` (`ins:`, the stated meaning each clause states, ADR-A138), `review` (`cst:Proposal` nodes, each with its decision), `vocabulary` (`voc:` and `skos:`), `quantification` (`qnt:`), `eligibility` (`elg:`), `persistence` (`dal:`) or `surface` (`srf:`) |
| `urn:lattice:studio:ws:{ws}:document:{doc}` | writer | a document of the workspace's library: its Wording graph, which the `document-to-wording` kit gives from its markup under the base `urn:lattice:studio:ws:{ws}/`, and the markup itself as `cst:markup`, a string, on the node whose IRI is the graph's. The workspace description names it with `cst:document`, and gives it `rdf:type` `cst:Document`, `rdfs:label` (the document's title), `cst:template`, `cst:revision` and `cst:modifiedAt` |
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
| `PUT /api/workspaces/{ws}/graphs/{name}` | the new graph. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision. `428` without `If-Match`, `412` when it is not the current revision, `422` when a subject belongs to another part by the rule the browser's import uses (a named subject typed `cst:Assembly` or `wrd:VariableValue`, or using `cst:assembles` or `wrd:forVariable`, belongs to assembly, one typed `cst:Proposal` or using `cst:proposes` to review, and otherwise to the first of meaning (`ins:`), persistence, surface, eligibility, quantification, vocabulary and library whose namespace its type or predicates use, a SKOS concept or scheme to vocabulary, anything else to the baseline, and a blank node to the subject that refers to it). A baseline is written as a new revision graph |
| `POST /api/workspaces/{ws}/jobs?kind={validate,compile}&target={name}` | the configuration to check, which need not be saved, and the other configurations beside it as context | `202`, `Location: /api/jobs/{job}`, the job graph. `400` for another kind or target. Every configuration validates. `eligibility`, `persistence` and `surface` compile |
| `POST /api/workspaces/{ws}/jobs?kind=assemble&target=assembly` | the assembly configuration, which need not be saved, and the other configurations beside it, since a form's inclusion conditions are eligibility's | `202`, as for any job. The worker assembles every `cst:Assembly` of the input under Wording's baseline model (ADR-A139). See Jobs |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target={sentence-forms,language-model}` | the configurations, the library and meaning among them | `202`, as for any job. See Proposers |
| `POST /api/workspaces/{ws}/jobs?kind=dry-run&target=meaning` | the configurations and a `cst:DryRun`, which is never saved | `202`, as for any job. See Dry run |
| `GET /api/workspaces/{ws}/jobs` | | `200`, the description of each compile job of the workspace: status, kind, target and times, without report or artefacts |
| `GET /api/document-templates` | | `200`, every `cst:DocumentTemplate` a document may be drafted from, each with its `cst:templateKey`, `rdfs:label` and its `cst:section`s in `cst:order`, each section with `cst:sectionKey`, `rdfs:label` (its heading), `cst:elementKind` (`clause` or `definition`), `cst:termKind`, `cst:required` and `rdfs:comment` (its guidance) |
| `GET /api/document-samples` | | `200`, every `cst:DocumentSample` with `cst:sampleKey` and `rdfs:label` |
| `GET /api/document-samples/{id}` | | `200`, `application/xml`, the sample document in the markup of `contracts/document` |
| `GET /api/workspaces/{ws}/documents` | | `200`, the node of each document of the workspace, as the description holds it |
| `GET /api/workspaces/{ws}/documents/{doc}` | | `200`, `ETag: "{revision}"`. The markup, `application/xml`, when `Accept` ranks it above `text/turtle`, otherwise the document's graph as RDF. `404` for a document the workspace does not hold |
| `PUT /api/workspaces/{ws}/documents/{doc}` | the document, `application/xml`, in the markup of `contracts/document`. `If-Match: "{revision}"` is required, `"0"` for a new document | `204`, `ETag` of the new revision. `400` for a body that is not well formed or declares a DTD, `422` for one the schema refuses, whose root `id` is not `{doc}`, or whose template is not one of `GET /api/document-templates`, `412` and `428` as for a graph |
| `GET /api/workspaces/{ws}/documents/{doc}/report` | | `200`, `ETag: "{revision}"`, an `sh:ValidationReport` at `urn:lattice:studio:documents/doc/{doc}/report`, computed from the document as saved. Each `sh:ValidationResult` has `sh:resultSeverity`, `sh:resultMessage`, `sh:focusNode` (the element, section or wording it concerns), `cst:check` and `cst:code`. `shacl` results check the Wording graph, `cst:code` naming the shape. `template` results are `required-section-empty`, `unknown-section` and `element-kind-not-allowed`, warnings, and `unmarked-text`, information. `detection` results, information, are constructs not yet marked: `cst:detectionKind` (`placeholder`, `money`, `percentage`, `date`, `duration`, `defined-term` or `cross-reference`), `sh:value` (the text), `cst:partIndex`, `cst:start` and `cst:end` (UTF-16 code units into the element's text, the end exclusive), `cst:action` (`mark-variable`, `mark-reference` or `none`), and `cst:suggestedKey` with `cst:suggestedValueType`, or `cst:suggestedTarget` (the definition's element) |
| `DELETE /api/workspaces/{ws}/documents/{doc}` | | `204`. Drops the document's graph and its node |
| `POST /api/workspaces/{ws}/jobs?kind=analyse&target={doc}` | none | `202`, as for any job. The worker reads each clause of the document as the sentence-form proposer does, and the job's artefacts are `analysis.json`, the analysis view, valid against [`analysis.schema.json`](analysis.schema.json), and `proposals.ttl`, the relations it proposes. `404` for a document the workspace does not hold |
| `GET /api/jobs/{job}` | | `200`, the job graph |
| `DELETE /api/jobs/{job}` | | `204`. Drops the job graph and its input graph |

A write is answered when its writer replies. Past 10 seconds the service looks for the write's receipt: if it is there the write applied and is answered as such, and otherwise the answer is `503`, the write is not applied yet and may still apply, since the stream keeps it until a writer reaches it.

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

### Assembly

A `cst:Assembly` in the assembly configuration names the form it draws from, with `cst:assembles` (a `wrd:Wording` of the library), the optional elements and variants the drafter chose, with `cst:choice`, and the value of each governing variable, with `cst:setting` (a `wrd:VariableValue`). An `assemble` job runs `tools/wording_assembler` on each, in IRI order, at the job's `cst:submittedAt`, minting every new IRI under `urn:lattice:studio:job:{job}:record/`. For each it reports the assembler's findings as `sh:ValidationResult`s, each with `cst:code` the stage (`load`, `validate`, `decide`, `assemble` or `record`) and `sh:focusNode` the element or governing variable, and the job conforms when every assembly gave a record. For each that gave one it adds two artefacts, grouped by the assembly's IRI, `record.ttl`, the assembled wording, and `document.xml`, the assembled document in the markup of `contracts/document`. Every record is also written, in the job's update, to the named graph `urn:lattice:studio:job:{job}:record`, which is deleted with the job. A refused assembly gives no record (law WA6).

### Meaning and its review

The meaning configuration holds stated meaning (ADR-A104, ADR-A138): stated terms, each an `ins:Term` and `ins:Template` with `ins:expressedIn` the clause of the library that states it, and the relations, qualifiers and regimes under them. Every template enters it through a proposal (ADR-A138 decision 4). A `cst:Proposal` in the review configuration names the clause it reads with `cst:span`, the templates it proposes with `cst:proposes`, its proposer with `cst:proposer` (`manual`, `sentence-forms` or `language-model`) and when with `cst:proposedAt`, and the reviewer's decision with `cst:decision` (`cst:Confirm`, `cst:Retarget`, `cst:Decline` or `cst:Defer`, ADR-A42) and `cst:decidedAt`. A proposal carries what it proposes as Turtle in `cst:payload`, so a template waiting for review is never in the meaning configuration, whose subjects the rule above sorts by namespace. Confirming writes the payload into the meaning configuration, retargeting writes it as corrected, and declining or deferring writes nothing. Manual entry is a proposal its author confirms at once. A validation of the meaning configuration checks it, beside the library and the other configurations, against Instrument's structural and constraint shapes, and one of the review configuration reports nothing.

### Proposers

A `propose` job reads every clause of the library's forms that has no stated term in the meaning configuration and no proposal waiting in the review configuration, and asks its proposer for candidates for each (ADR-A138 decision 5). A candidate is a relation kind, the role that bears it and the role it is owed to, and an activity, each one the workspace already declares: a subclass of `ins:LegalRelation`, a `pty:Role` and a concept of the activity scheme. The job gives each candidate as a `cst:Proposal` waiting for review, with `cst:span` the clause, `cst:proposer` the proposer's name, `cst:proposedAt` the job's `cst:submittedAt`, `cst:evidence` the words it rests on, `cst:proposerVersion`, and its stated term and relation in `cst:payload`, minted under `urn:lattice:studio:job:{job}:proposal/`. They are the artefact `review.ttl`, which the browser adds to the review configuration for the author to save and decide. A clause with no candidate is reported as information.

| Proposer | Proposes from | Configured by |
|---|---|---|
| `sentence-forms` | the relation the worker's sentence-form reader classifies the clause as, and the roles and activities whose labels the clause's text names, in their order | nothing |
| `language-model` | a model's reply, over the Chat Completions wire format, to a prompt rendered from a pack, checked against [`proposal-candidates.schema.json`](proposal-candidates.schema.json). The repository holds no clause-reading pack. A deployment supplies one, a folder with a `manifest.json` naming its `name`, `version`, `system` and `prompt` template files and its `temperature`, whose templates may name `{clause}`, `{roles}`, `{activities}`, `{kinds}` and `{schema}` | the worker's environment: `LATTICE_PROPOSER_URL` (the endpoint's base, to which `/chat/completions` is added), `LATTICE_PROPOSER_MODEL`, `LATTICE_PROPOSER_PACK` (the pack's folder) and `LATTICE_PROPOSER_KEY` (sent as a bearer token, never logged). Without the first three the job fails, saying no language model is configured |

### Dry run

A dry run decides a stated term's eligibility conditions over sample facts, without instantiating anything (ADR-A138 decision 7, CB-Q2). The request body holds the configurations and one `cst:DryRun`, with `cst:term` the stated term and a `cst:fact` for each sample: `cst:forCondition` the condition, and `cst:number` a number for an interval condition or `cst:concept` a concept for a concept condition, one fact per concept. The worker finds the conditions the term reads, through its relations and their qualifiers, poses each as an `elg:Question` with the facts as its candidate, and decides it by the condition's compiled SPARQL, as an eligibility validation decides a question, never by the reference evaluator (ADR-A-FM3). The job gives one `cst:testResult` per condition, with `cst:condition`, `cst:decision` and `cst:diagnostic` when Undetermined, and reports as information a condition with no fact, which reads Undetermined, and a fact for a condition the term does not read. The facts live in the job's input only, deleted with the job. Stepping a regime over sample events has no compiled path yet, so a dry run does not step regimes (BQ-1).

## Writes

Every write to the store is a command to the store writer, `config-studio-writer`, the only component that writes the store (ADR-A136). A command is published to the super stream `lattice.studio.writes`, a direct exchange with argument `x-super-stream` whose binding keys `0` to `7` route to the partition streams `lattice.studio.writes-0` to `-7`, each bound with `x-stream-partition-order` and declared with `x-queue-type` `stream`, `x-max-age` `7D` and `x-max-length-bytes` 1 GiB. A command's routing key is its workspace's partition: the id's first 8 hex digits, as an unsigned number, modulo 8. So a workspace's commands stay in order in one partition. The writers are one single-active-consumer group, `lattice.studio.writers`, so each partition is applied by one live writer at a time, and RabbitMQ spreads the partitions across the writers that run. The number of partitions is fixed here, since changing it moves workspaces between partitions.

A command's fields are AMQP headers, and the graphs it carries are its body, `content_type` `application/n-quads`, persistent. Every command carries `id`, a lower-case UUID its sender chooses, and `sender`, `service` or `worker`.

| `command` | Other headers | Body | Sent by |
|---|---|---|---|
| `create` | `workspace`, `label`, `at`, `sample` when made from one | the baseline, in the default graph | service |
| `save` | `workspace`, `part`, `expect` (the revision `If-Match` named, a number), `at` | the graph, in the default graph | service |
| `import` | `workspace` (the new id), `label`, `at` | every graph of the export, already named under the new id | service |
| `delete-workspace` | `workspace` | none | service |
| `submit-job` | `workspace`, `job` | the job graph and its input graph, named | service |
| `job-update` | `workspace`, `job` | the job graph, named | worker, or the service when the job could not be published |
| `save-document` | `workspace`, `part` (the document's id), `expect`, `at`, `label` (its title), `sample` (its template's key) | the document's graph, in the default graph | service |
| `delete-document` | `workspace`, `part` (the document's id) | none | service |
| `delete-job` | `workspace`, `job` | none | service, and the writer's sweep of jobs finished longer ago than the retention |

`workspace` and `job` are the ids, `at` an `xsd:dateTime`. The service publishes with confirms and sets `reply_to` to `amq.rabbitmq.reply-to` and `correlation_id` to the command's id, and the writer answers with headers alone. The stream keeps `reply_to` as an AMQP 1.0 address, `/queues/` and the percent-encoded queue name, which the writer decodes. The reply's headers are `status` (200 applied, 400 refused, 404 no such workspace or job, 412 a stale `expect`), `revision` (the new one, or the current one for 412) and `message`. The worker publishes with confirms and no reply.

The writer checks every command, whatever its sender checked: the ids, that a command carries only the graphs its kind may, part membership by the rule of `PUT`, that a job names its workspace, its own input, the workspace's baseline and `cst:Queued`, that a `job-update` carries the job graph, and for an `assemble` job also its record graph, whose terms are Wording's, PROV's, Foundation's, RDF's and RDFS's only, and that it changes nothing on the job node but `cst:status`, `cst:startedAt`, `cst:finishedAt`, `cst:failureMessage`, `cst:conforms`, `cst:report`, `cst:artefact`, `cst:gap`, `cst:resolution`, `cst:expansion` and `cst:testResult`, compared by value. A `job-update` for a deleted job is dropped. A refused command is logged by the writer and passed over, since a stream has no dead letters, and its absent receipt records that it did not apply. A writer stores each partition's offset after a batch, so a writer that takes a partition over resumes after the last batch applied.

A writer applies the commands waiting for it, up to 64, in one SPARQL Update request, one transaction. Each command's first operation inserts its `cst:Receipt` only where its precondition holds in the store: a save's expected revision, a creation's or an import's absent workspace, a job's workspace. Its other operations require that receipt, so a command applies whole or not at all, and the receipts present after the commit are the commands applied. A command whose receipt already exists, such as one redelivered after a lost acknowledgement, is answered from its receipt and not applied again. A batch the store refuses is retried whole.

| Receipt graph | Holds |
|---|---|
| `urn:lattice:studio:ws:{ws}:receipts` | the receipts of the workspace's own writes and of its jobs' deletions, deleted with the workspace |
| `urn:lattice:studio:job:{job}:receipts` | the receipts of a job's submission and updates, deleted with the job |
| `urn:lattice:studio:receipts` | the receipt of each workspace's deletion |

A receipt, `urn:lattice:studio:receipt:{id}`, has `cst:commandId`, `cst:command` (the cause), `cst:sender`, `cst:workspace`, `cst:job` where there is one, `cst:requestedAt` where the command has a time, `cst:committedAt` (the transaction time), `cst:wrote` for each graph and `cst:receiptRevision` for a save or a creation. No principal is recorded, since the studio authenticates no one. An export holds no receipt.

