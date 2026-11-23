<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio contracts

The data contracts between the [Configuration Studio](../../apps/config-studio)'s browser code, its [service](../../platform/config-studio-service) and its [worker](../../workers/README.md#configuration-studio-jobs-adr-a136) ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). They are contracts of a supported component: a change that would break a client is announced here and deprecated before it is removed, by the release policy once it is defined.

Every body is RDF. The terms are in [`studio-vocabulary.ttl`](studio-vocabulary.ttl), prefix `cst:`, and the configurations themselves use `dal:` and `srf:` unchanged. The JSON documents are [`amqp-topology.json`](amqp-topology.json) and, for the frames of a run, [`run-frame.schema.json`](run-frame.schema.json).

| File | Holds |
|---|---|
| `studio-vocabulary.ttl` | workspaces, samples, jobs, runs, job status, artefacts and gaps |
| `amqp-topology.json` | the exchange, the job queues, the transforms queue, the two queues of runs, `lattice.studio.runs.interactive` and `lattice.studio.runs`, the dead-letter queue, and the writes super stream with its partitions, declared identically by the service, the writer and the worker. Each queue's `bindTo` names the exchange it is bound to, `exchange` or `deadLetterExchange`, and only the dead-letter queue is bound to the dead-letter exchange |
| `run-frame.schema.json` | the JSON Schema of one frame of a run, which is the body of a `run.frame` event and an element of a `wait=true` response (see Runs) |
| `samples/run-frames.example.json`, `samples/run-frames-failed.example.json` | a complete small `sample` run as a `wait=true` response gives it, and a run that could not start. Each is valid against `run-frame.schema.json` |
| `promotions.ttl` | the surface promotions of the registry, jobs, holders and terms, their generation profile and the target namespace `prm:` (`https://www.nebularis.org/neuro-semantic/lattice/config-studio/promotion#`). The terms promotion covers `skos:Concept` only, and the members of the other units of `publication-units.ttl` are not covered yet |
| `workspace-summaries.rq` | the query that gives each workspace's summary, evaluated as it is read, kept beside the promotions because it joins a workspace to its parts' version rows, which no read path expresses |
| `samples/samples.ttl` | the samples, each a list of repository files |
| `samples/lending-baseline.ttl` | a baseline for the lending sample, which the persistence example it pairs with does not declare |
| `samples/facility-baseline.ttl` | the facility agreement sample's baseline, which extends `lending-baseline.ttl` with a facility, lenders and drawdowns, the boundary shape of the facility and the carrier data |
| `samples/facility-{vocabulary,quantification,eligibility,persistence,surface}.ttl` | the facility agreement sample's five configurations, one file each, which refer to one another: eligibility draws on the schemes and range sets, persistence scopes a key by a vocabulary property, and surface reads a population from a scheme contract. [`tools/config_studio_stage.py`](../../tools/config_studio_stage.py) stages them merged as sample `facility`, and [`test_config_studio_facility_sample.py`](../../workers/tests/test_config_studio_facility_sample.py) checks each part and the deliberate resolution cases |
| `samples/library-{baseline,vocabulary}.ttl` | the library sample, which imports LATTICE's vocabulary layer by its ontology IRI, a layer that itself imports the foundation layer. The baseline uses a foundation term without importing that layer, and the vocabulary configuration binds a scheme of its own to a property the baseline declares, so once its imports are held the Baseline diagram's import graph draws a stated import, a binds edge and a derived edge. A sample is not rewritten when a layer's version moves, so it names the layer and never a version |

## Graphs

Fuseki serves the one database as two services: `studio` reads only, through query and the graph store protocol's reads, and is given to the service and the worker. `studio-write` also updates, and is given to the store writer alone.

| Graph IRI | Written by | Holds |
|---|---|---|
| `urn:lattice:studio:description/{root}` | writer | the workspace's description aggregate. Its root is `urn:lattice:studio:ws:{ws}`, and `{root}` is the root percent-encoded as SPARQL's `ENCODE_FOR_URI` does, as in every graph below. The `cst:Workspace` node holds `rdfs:label`, `cst:createdAt`, `cst:modifiedAt`, `cst:fromSample` when it was made from a sample, `cst:owner`, `cst:mode`, `cst:dependsOn` and `cst:holdsImport`, with a label on each import's root, and `cst:declaresOntology` and `cst:declaresVersion` there when the import's document declares them (see Jobs, a fence job). It names each document with `cst:document` and gives it `rdf:type` `cst:Document`, `rdfs:label` (the document's title), `cst:template` and `cst:modifiedAt`. It holds no revision. `cst:modifiedAt` moves only when the description is written |
| `urn:lattice:studio:part/{root}` | writer | the saved part `{name}` of a workspace, whose root is `urn:lattice:studio:ws:{ws}/part/{name}`. `baseline` is a part like the others, and its graph is the one jobs read as saved. The names are `baseline`, `library` (`wrd:`, forms and their variables, ADR-A138), `assembly` (`cst:Assembly` nodes and the `wrd:VariableValue` records they set), `meaning` (`ins:`, the stated meaning each clause states, ADR-A138), `review` (`cst:Proposal` nodes, each with its decision), `mapping` (`mork:` mapping schemes and the guards they name), `vocabulary` (`voc:` and `skos:`), `quantification` (`qnt:`), `eligibility` (`elg:`), `persistence` (`dal:`) and `surface` (`srf:`). A part's revision is the sequence of its version row, 0 when it has none. Its history is kept as deltas in the patch log, graphs `urn:rev:studio/{root}/e{epoch}/{seq}/add` and `/del` |
| `urn:lattice:studio:document/{root}` | writer | a document of the workspace's library, whose root is `urn:lattice:studio:ws:{ws}:document:{doc}`: its Wording graph, which the `document-to-wording` kit gives from its markup under the base `urn:lattice:studio:documents/`, and the markup itself as `cst:markup`, a string, on the node `urn:lattice:studio:documents/doc/{doc}/`. Its revision is the sequence of its version row, and its history is kept as a part's is |
| `urn:lattice:studio:job:{job}` | writer, for the service and then the worker | the `cst:Job` node, whose IRI is the graph's |
| `urn:lattice:studio:job:{job}:input` | writer, once | the configuration as submitted |
| `urn:lattice:studio:imported/{root}` | writer, once | a fenced import, whose root is `urn:lattice:studio:import:{digest}`, `{digest}` the SHA-256 of its RDFC-1.0 canonical N-Quads. `cst:holdsImport` names the root. Stored once, whichever workspaces hold it, and never edited or tombstoned (ADR-A149 decision 6) |
| `urn:lattice:studio:lineage/{root}` | writer | a published lineage, whose root is the lineage's IRI: the `fnd:PersistentIdentity`, each `fnd:hasVersion`, the `cst:current` version, each `fnd:supersededBy`, and each `cst:Publication` event. Its sequence counts the lineage's publications. Global, not a workspace's (ADR-A149) |
| `urn:lattice:studio:version/{root}` | writer, once | one version's content, whose root is the version's IRI, `{lineage}/rev/1-{digest}`. Immutable, and created again as a no-op since the same digest is the same content |
| `urn:lattice:studio:promoted:{source}` | the writer, in the request of each write of `{source}`, or a rebuild | the rows of every promotion of `promotions.ttl` over one source, derived and never authoritative. Each promotion names the family it reads with `cst:sourceFamily`: `registry` holds `{lineage} prm:current {version}` over a lineage, `jobs` holds `{job} prm:workspace {ws}` over a job (membership only, a job's status stays in its own graph), the holders promotions hold `{ws} prm:dependsOn {held}` and `{ws} prm:holdsImport {import}` over a description, and the terms promotions hold `{concept} prm:prefLabel {label}` and `{concept} prm:inScheme {version}` over a published version |
| `urn:lattice:studio:promoted-record` | a rebuild | `{contract} cst:contractDigest {hex}` for each promotion the last rebuild read, which a start compares with the staged contracts |

The version rows are in a meta graph of each family, which the persistence profile's generated operations keep, with the claim of each transaction, `urn:txn:{command id}/{n}`. A graph the writer writes from an author's statements holds no blank node, since a generated operation's payload cannot (ADR-A149 decision 13). Each is stored as a skolem IRI, `urn:lattice:studio:genid:{name}`, `{name}` the first 32 hexadecimal digits of the SHA-256 of what the node says and where it is named from, with `-{n}` telling identical nodes apart. The service and the worker read every skolem IRI back as a blank node. The studio's persistence profile, `persistence-profile.ttl`, declares its aggregates, which the stage compiles with the operations the writer runs.

`{ws}` and `{job}` are lower-case UUIDs. Only the writers write these graphs (see Writes). The service and the worker read them from the store.

## HTTP

Every request and response body is RDF in UTF-8, unless the table says otherwise: `text/turtle` by default, or `application/rdf+xml`. A request body may be either, named by its `Content-Type`. A response is RDF/XML when the request's `Accept` ranks `application/rdf+xml` above `text/turtle` (a range without `q` counts 1, `*/*` favours Turtle), and every RDF response carries `Vary: Accept`. RDF/XML is written plain, one `rdf:Description` per subject, so an XSLT reads one regular shape. A graph whose predicate RDF/XML cannot write, one whose IRI does not end in an XML name, answers `406` in RDF/XML and stays readable as Turtle. An ETag names a graph's revision, the same in either syntax. A request body with another content type is refused with `415`, a body over 5 MiB with `413`, a body that does not parse, or RDF/XML that declares a DTD, with `400`, an unknown workspace or job with `404`.

Every route but `/api/health` and `/api/session`, and `/mcp`, answers `401` with `WWW-Authenticate` to a request that does not authenticate: under `local`, one naming a principal the service does not offer in `X-Lattice-Principal`, and under `oidc`, one without a valid `Authorization: Bearer` token.

| Method and path | Request | Response |
|---|---|---|
| `GET /api/health` | | `200`, `text/plain`, `ok` |
| `GET /api/session` | | `200`, `application/json`, how to sign in: `provider` (`local` or `oidc`), with `principalOption` and `administrator` for `local`, or `issuer`, `clientId`, `scope`, `authorizationEndpoint` and `tokenEndpoint` for `oidc`, and `principal` and `admin` when the request authenticates |
| `POST /api/workspaces/{ws}/access?mode=…&owner=…` | | `200`, the workspace's description with its new `cst:mode`, and `cst:owner` when an administrator named one. Only the owner or an administrator may change it, else `403`. `mode` is `locked`, `read-only` or `shared`. A workspace with no owner stays shared |
| `POST /api/workspaces/{ws}/imports?job={job}&label={label}` | | `201`, the workspace's description, holding the import each finished `fence` job digested. A fence job, `POST /api/workspaces/{ws}/jobs?kind=fence&target=import`, takes the imported RDF as its body. `job` is given once or more, at most 64 times, and `label` once for each in the same order, the first `label` for the first `job`, and so on. `label` may be left out for one job, which is then labelled `Import`. `404` when no `job` is given, when one is not a job id, or when one does not exist or is another workspace's. `400` for more than 64 jobs, for a number of `label`s that differs from the number of `job`s (none is allowed only with one job), and for an empty label or one over 200 characters. `409` when a job is not a finished fence job with an import to hold. Any of these refuses the whole request, and nothing is written, so the imports of the other jobs are not held either. Two jobs that digested the same content hold it once, under the first one's label. One request is one command to the workspace's writer (see Writes), so the description is replaced once and no reader sees part of a closure. `Location` names the first import |
| `GET /api/registry/bundle?iri={version}` | | `200`, `application/trig`, the version and every version it pins, transitively, each in a named graph named by the version's own IRI |
| `GET /api/registry/holders?iri={lineage, version or import root}` | | `200`, the workspaces that follow the lineage, pin it or one of its versions (`{ws} cst:dependsOn {iri}`) or hold the import (`{ws} cst:holdsImport {iri}`), each with its summary. Only workspaces the principal may read, so a locked one is left out. `400` when `iri` names none of the three |
| `GET /api/registry/terms?q={text}` | | `200`, at most 50 concepts of the published versions whose `skos:prefLabel` contains the text in any case, each with its label and `skos:inScheme` the version, in label order. `400` without text |
| `GET /api/workspaces/{ws}/imports/{digest}` | | `200`, the import's graph, when the workspace holds it |
| `DELETE /api/workspaces/{ws}/imports/{digest}` | | `204`. The workspace no longer holds it, and the graph stays for any other that does |
| `PUT /api/workspaces/{ws}/dependencies` | `<urn:lattice:studio:ws:{ws}> cst:dependsOn <iri> , …`, each a published lineage, which the workspace follows, or a version, which it pins | `200`, the workspace's description. `422` naming an IRI the registry does not hold, `403` to a principal who may not write the workspace |
| `GET /api/features` | | `200`, `application/json`, `{"features": [...]}`, the optional features the deployment turned on with `LATTICE_STUDIO_FEATURES`, such as `odrl` |
| `GET /api/status` | | `200`, `application/json`, `{"warnings": [...]}`, what the service's start found that an administrator should know, such as a promotion changed since the last rebuild (PM-Q3) |
| `POST /api/admin/rebuild` | | `202`, a rebuild of every promoted partition is queued. `403` for a principal who is not an administrator |
| `POST /api/broker/{secret}/{user,vhost,resource,topic}` | the RabbitMQ HTTP auth backend's form | `200`, `allow` or `deny`, the broker's checks of who a browser is and what it may use, below. `404` when the studio offers no events or the path does not carry `LATTICE_STUDIO_BROKER_SECRET`. A proxy never routes them |
| `GET /api/vocabulary` | | `200`, the `dal:`, `srf:`, `fnd:` and `voc:` specifications and vocabularies merged, with an `ETag`. `304` for a matching `If-None-Match` |
| `GET /api/ontologies` | | `200`, an index of LATTICE's own ontology documents the studio stages, as RDF. Each document is one `owl:Ontology` node, its ontology IRI, with its `owl:versionIRI` where it declares one and each `owl:imports` it states. The staged file's name is not given. It has an `ETag`, and `304` for a matching `If-None-Match`. `404` when the staged folder has no index, as an older stage has not |
| `GET /api/ontologies?iri={iri}` | | `200`, as Turtle, the staged document whose ontology IRI or version IRI is `iri`, with an `ETag`. `404` for an IRI the index does not hold. `400` for a value that is not one absolute IRI. The service finds the document through the index it loaded at start and never through a path or file name from the request, and nothing is fetched from the web |
| `GET /api/samples` | | `200`, every `cst:Sample` with its label and comment |
| `GET /api/samples/{id}` | | `200`, the sample's files merged into one graph |
| `GET /api/workspaces` | | `200`, the summary of every workspace the principal may read, by the summaries query in one read: its label, owner, mode, `cst:modifiedAt`, sample, dependencies, held imports with their labels and the `cst:declaresOntology` and `cst:declaresVersion` each gives, `cst:{name}Revision` for each part, and each document with its `cst:revision` |
| `POST /api/workspaces[?sample={id}]` | the baseline. `Slug` header, percent-encoded UTF-8, is the label. `sample` names the staged sample it was made from, which the description records | `201`, `Location: /api/workspaces/{ws}`, the description. `400` for a sample that is not staged, `422` for a baseline holding a subject of another part, by the rule of `PUT` below |
| `POST /api/workspaces` with `Content-Type: application/trig` | a file `GET …/export` wrote, here or elsewhere. `Slug`, when given, replaces its label | `201`, as above, a new workspace with the export's graphs, each part and document at revision 1. `422` for TriG that is not one workspace's export, or a graph holding another part's subject |
| `GET /api/workspaces/{ws}` | | `200`, the description |
| `DELETE /api/workspaces/{ws}` | | `204`. Drops the description, the parts, the documents, their patch logs and the workspace's jobs, and leaves their version rows tombstoned |
| `GET /api/workspaces/{ws}/export` | | `200`, `application/trig`, `Content-Disposition: attachment`, the description and every part and document that holds a triple, each graph named by its aggregate's root and without the patch log |
| `GET /api/workspaces/{ws}/graphs/{name}[?revision={n}]` | `name` is `baseline` or a configuration's name. `revision`, when given, is a whole number from 1 to the current revision | `200`, the graph, `ETag: "{revision}"`. With `revision`, the part as it was at that revision, rebuilt from the current graph by undoing each later revision's delta from the patch log, with blank nodes read back. `404` for a revision below 1 or above the current one, or for a workspace the principal may not read, `400` for one that is not a number |
| `PUT /api/workspaces/{ws}/graphs/{name}` | the new graph. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision. `428` without `If-Match`, `412` when it is not the current revision, `422` when a subject belongs to another part by the rule the browser's import uses (a named subject typed `cst:Assembly` or `wrd:VariableValue`, or using `cst:assembles` or `wrd:forVariable`, belongs to assembly, one typed `cst:Proposal` or using `cst:proposes` to review, one named by `mork:appliesWhen` to mapping, and otherwise to the first of mapping (`mork:`), meaning (`ins:`), persistence, surface, eligibility, quantification, vocabulary and library whose namespace its type or predicates use, a SKOS concept or scheme to vocabulary, anything else to the baseline, and a blank node to the subject that refers to it). A part is replaced in place, and its earlier revisions stay readable from the patch log |
| `PATCH /api/workspaces/{ws}/graphs/{name}` | `application/trig` holding the graphs `<urn:lattice:studio:patch:add>`, what the save adds, and `<urn:lattice:studio:patch:del>`, what it removes, and nothing else. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision, the part the stored one with the removed triples taken out and the added put in, written by its delta. `412` with the current `ETag` when the revision moved, `428` with no `If-Match`, `415` for another media type, `422` for another graph or a term of another part, `400` for a blank node, which a patch cannot name, so the browser saves such a part whole (DR-Q5 (c), DR-Q7 (b)) |
| `POST /api/workspaces/{ws}/jobs?kind={validate,compile}&target={name}` | the configuration to check, which need not be saved, and the other configurations beside it as context | `202`, `Location: /api/jobs/{job}`, the job graph. `400` for another kind or target. Every configuration validates, and so does the `baseline`, which is the body as sent. The baseline does not compile. Its validation reports an import no held document declares (see Jobs). `eligibility`, `persistence`, `surface` and `mapping` compile. `mapping` validates by compiling each scheme with `tools/mork_rdf`, which checks it against MORK's shapes and its target terms against the layers |
| `POST /api/workspaces/{ws}/jobs?kind=assemble&target=assembly` | the assembly configuration, which need not be saved, and the other configurations beside it, since a form's inclusion conditions are eligibility's | `202`, as for any job. The worker assembles every `cst:Assembly` of the input under Wording's baseline model (ADR-A139). See Jobs |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target={sentence-forms,language-model}` | the configurations, the library and meaning among them | `202`, as for any job. See Proposers |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target=rml` | the mapping configuration and one `cst:ImportDocument`, an RML mapping as Turtle or N-Triples | `202`, as for any job. `422` without exactly one document. The worker reads it into a MORK scheme with `tools/mork/src/rml2mork.py`, named under the base its subject templates share, returned as an artefact grouped `mapping`, with what MORK cannot say as warnings (`RmlNotRead`). One naming a node the workspace holds is refused |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target=mapping-language-model` | the mapping configuration, with one `cst:ImportDocument` of `cst:documentRole` `cst:SourceVocabulary`, its `cst:sourceNamespace` optional, and at most one of role `cst:SampleSource`, each Turtle or N-Triples | `202`, as for any job. `422` otherwise. See Mapping proposals |
| `POST /api/workspaces/{ws}/jobs?kind=dry-run&target=meaning` | the configurations and a `cst:DryRun`, which is never saved | `202`, as for any job. See Dry run |
| `POST /api/workspaces/{ws}/jobs?kind=dry-run&target=mapping` | the mapping configuration and one `cst:ImportDocument`, its sample source in Turtle or N-Triples | `202`, as for any job. `422` without exactly one document with content and a media type. See Dry run |
| `POST /api/workspaces/{ws}/transforms?job={job}` | a sample source in XML or JSON, `Content-Type` `application/xml`, `text/xml` or `application/json` | Deprecated in favour of a `sample` run, which follows, and no longer called by the studio. It stays for one release, answered by the run worker, and is then removed. `200`, the run as a `cst:Transform`. `404` for a job the workspace does not hold, `409` for one that is not a finished compilation of the mapping part, `415` for another media type, `413` over 5 MiB, `504` when no transforms worker answered within 30 seconds. See Transforms |
| `POST /api/workspaces/{ws}/runs?kind={sample,simulate}&target={mapping,persistence,surface}&job={job}&tab={tab}[&deadline={time}][&wait=true]` | the input, at most 5 MiB. A sample source for `sample`, and TriG holding a sample world and a step for `simulate` | Without `wait`, `202`, Turtle, the run as a `cst:Run`, accepted and not yet run. With `wait=true`, `200`, `application/json`, the run's frames. `400`, `404`, `409`, `413`, `415`, `429`, `503` and `504` as Runs states them, and `400` for a run without `wait=true` where the studio offers no events to a browser. See Runs |
| `GET /api/workspaces/{ws}/jobs` | | `200`, the description of each compile job of the workspace: status, kind, target and times, without report or artefacts |
| `GET /api/workspaces/{ws}/jobs?unfinished=true` | | `200`, the description of each job of the workspace that is queued or running, of every kind: status, kind, target, the unit a publish job prepares, and times, without input, report or artefacts. A view that opens reads it to find the job it started before it was closed |
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

## MCP

The service is also a Model Context Protocol server, over MCP's Streamable HTTP transport at `POST /mcp` on the same address, so an MCP host proposes stated meaning with its own model and keys (ADR-A138 BQ-2). It answers JSON-RPC 2.0 requests with `application/json`, never a stream, a notification with `202`, `GET /mcp` with `405`, and a request whose `Origin` is not on `localhost` or `127.0.0.1` with `403`. `initialize` agrees the protocol version, `2025-11-25`, `2025-06-18` or `2025-03-26`, the latest when the client asks for another, and returns an `Mcp-Session-Id` that names the client in the proposals it makes. The server holds no model, calls none, and uses no sampling.

| Tool | Arguments | Gives |
|---|---|---|
| `list_workspaces` | none | each workspace's id and label |
| `list_clauses` | `workspace` | each text of the library's forms with its IRI, number, text, and whether it has stated meaning, a proposal waiting, or neither |
| `read_clause` | `workspace`, `clause` | the clause's text, its stated meaning in plain words, and what a proposal may name: the relation kinds, the workspace's roles and the activities, each by label |
| `propose` | `workspace`, `clause`, `kind`, `evidence`, and `role`, `counterRole` and `activity` where there are | a `cst:Proposal` waiting for review, saved to the review configuration as any save is, with `cst:proposer` `assistant` and `cst:proposerVersion` the client's name and version from `initialize`. A label the workspace does not declare refuses the call, with what it does declare |
| `mork_teaching_pack` | none | MORK's teaching pack, MTP with its cassettes, the translation table and MCN's codebook, as staged |
| `mork_target_cards` | `layers`, comma-separated | one line per term of each named LATTICE layer, as staged |
| `mork_describe_term` | `term`, a CURIE | one term in depth with the laws its layer's shapes state, as staged |
| `mork_source_cards` | `workspace`, `source` as Turtle, `namespace` | one line per term of the source vocabulary, run in the worker |
| `mork_candidate_terms` | `workspace`, `source`, `term`, `namespace` | the likeliest LATTICE terms for one source term, run in the worker |
| `mork_check_mapping` | `workspace`, `mcn`, and a `sample` source as Turtle | the check's findings as JSON, the output on the sample held to the layers' shapes, run in the worker |
| `mork_propose_mapping` | `workspace`, `mcn`, and `model`, `inputTokens` and `outputTokens` where known | the decoded scheme saved to the mapping part with a `mork:ProposalRun`, each mapping naming it, for review in mapping mode. A scheme naming a node the workspace holds, or holding anything but a mapping, is refused |

The MORK tools that read no source are staged by `mise run build:config-studio-assets` under `mork/`, so the service serves them without the worker. Those that read a source or a sample, and decoding a proposal to save it, run in the worker as a tool job (`cst:ToolCall`) whose input holds one `cst:ToolRequest`, naming the tool and its arguments as JSON, and the documents as `cst:ImportDocument`s with their roles. The service waits up to two minutes for it, and the job stays in the store as any job does.

LATTICE's own ontology documents are staged under `ontologies/`. `tools/config_studio_stage.py` reads `ontology/catalog-v001.xml` with the reader of `tools/ontology_catalog.py` and, for each entry whose target is a Turtle file under `ontology/`, copies the file under the SHA-256 of its content, so two IRIs of one file share one copy. `ontologies/index.ttl` describes each distinct document by one `owl:Ontology` node, its ontology IRI, with `owl:versionIRI`, each `owl:imports` and `cst:stagedAs`, the copy's file name, which the service never gives out. An entry that names a web location or a missing file is not staged, and a document that is not Turtle or declares no single named `owl:Ontology` is skipped and counted in what the stage prints. The service reads the index once at start and serves a document by an IRI it holds, so an older stage with no index answers `404` and the service still starts. A catalog directory a deployment configures, to serve its own ontologies the same way, is not yet offered.

A proposal from MCP is decided in the studio like any other, and nothing the server does confirms one.

| Prompt | Gives |
|---|---|
| `mtp-l0` | the first layer of MORK's teaching pack, MTP, from `ontology/mork/mtp/out/l0.txt` |

## Jobs

The service has the job graph written (see Writes) and publishes the job's IRI. The message body is that IRI in UTF-8, `content_type` `text/plain`, persistent, routed with `lattice.studio.jobs` on exchange `lattice.studio`. The worker refuses, without requeuing, a body that is not `urn:lattice:studio:job:` followed by a lower-case UUID, and the broker dead-letters it.

As written by the service:

```turtle
<urn:lattice:studio:job:{job}> a cst:Job ;
    cst:kind cst:Validate ;                     # or cst:Compile
    cst:target cst:Persistence ;                # or cst:Vocabulary, cst:Quantification, cst:Eligibility, cst:Surface, and for a validation cst:Baseline
    cst:workspace <urn:lattice:studio:ws:{ws}> ;
    cst:configGraph <urn:lattice:studio:job:{job}:input> ;
    cst:baselineGraph <urn:lattice:studio:part/{root of the baseline part}> ;   # the baseline as saved when the job runs
    cst:contextGraph <urn:lattice:studio:part/{root of the part}> ;   # one per other configuration part, for a validation, compilation or dry run, and one per version and held import
    cst:status cst:Queued ;
    cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .
```

The worker replaces the whole job graph twice, each time as a `job-update` to the job's workspace's writer, keeping every triple above but `cst:status`. When it starts, it sets `cst:status cst:Running` and adds `cst:startedAt`. When it ends, it sets `cst:Succeeded` or `cst:Failed` and adds `cst:finishedAt`, and then:

- for `cst:Failed`, `cst:failureMessage`, saying why the job could not run, for example a missing input graph. A configuration that does not validate or compile is not a failure.
- for `cst:Succeeded`, `cst:conforms`, and `cst:report` naming an `sh:ValidationReport` in the same graph. Its `sh:result`s are pySHACL's for a validation. For a compilation they are the compiler's refusal, an `sh:Violation`, and its warnings, each `sh:Warning`, each with `cst:code` the compiler's name for it, `sh:resultMessage`, and `sh:focusNode` where the compiler names a node.
- for a successful compilation, one `cst:artefact` per file, with `cst:path`, `cst:mediaType`, `cst:content` and `cst:group`. For persistence these are `compiled-profile.ttl` and each SPARQL file `instantiate` writes, grouped by target. For surface, each file `compile` writes, grouped by contract, and the operations the surface simulator runs, grouped as `maintenance` (see [A surface step](#a-surface-step)).
- for a mapping compilation, two files per scheme, `{scheme}.compiled.ttl`, the compiled mapping as RDF, and `{scheme}.rq`, its queries in the order a run takes them, grouped by the scheme's IRI. Where a representation scheme's format is JSON, XML, CSV or YAML, which `mork_rdf` leaves to another backend, `mapping.rml.ttl` too, the part compiled to RML by `tools/mork/src/mork2rml.py` under the namespace of its scheme.
- a persistence compilation's `compiled-profile.ttl` states where each compiled target's data lands, as the `dal:GraphPlace` nodes its write accesses reach by `dal:landsIn`, with the boundary's `dal:ReferenceEdge`s, the profiles each dimension was won by and the scopes it was won through. A browser draws the persistence canvas from it alone, so there is no further artefact for it. A profile compiled before it stated the places has no `dal:GraphPlace`, and the canvas asks for a new compilation.
- for a persistence compilation, one `cst:gap` per entry of `python -m persistence gaps`, with `cst:group`, `cst:obligation` and `cst:message`.
- for a persistence validation, the compiler's refusal and warnings too, since the `dal:` shapes do not see a `dal:DataAccessProfile` that declares several dimensions.
- for a vocabulary validation, one `cst:resolution` per scheme contract, time segment and set of active scopes, with `cst:contract`, `cst:validFrom` and `cst:validTo` where bounded, `cst:context` per active scope, `cst:outcome`, and `cst:scheme` and `cst:binding`, or `cst:tied` for a conflict, as `tools/vocabulary` resolves it.
- for an eligibility validation, each condition compiled by `tools/mork_compilers`, its refusal an `sh:Violation` with `cst:code` `IRCompileError`. One `cst:expansion` per member of a concept condition's resolved scheme, with `cst:condition`, `cst:concept` and `cst:decision`. One `cst:testResult` per `elg:Question`, decided by the condition's compiled SPARQL, with `cst:question`, `cst:condition`, `cst:decision`, `cst:diagnostic` when Undetermined, and `cst:passed` against the question's `cst:expectedDecision`. A failed test is an `sh:Violation` with `cst:code` `TestFailed`, and makes the job not conform. A condition or question may name `cst:resolutionTime` and `cst:resolutionScope`, and otherwise resolves at the job's submission time with no scope.
- for an eligibility compilation, `decision.rq` and `shapes.ttl` for each condition and admission profile, grouped by its local name.
- for a baseline validation (`cst:target cst:Baseline`, a validation only), one `sh:ValidationResult` with `sh:resultSeverity sh:Warning` and `cst:code` `ImportNotHeld` for each `owl:imports` that no held document declares, so that a missing import is reported and never refused. The importers are every named `owl:Ontology` of the job's input, the baseline as sent, and of each held import among its context graphs, which the worker tells apart from the configuration parts by their graph names. An import is held when its object is the ontology IRI or a version IRI of the one named `owl:Ontology` of some held import, and the baseline's own ontology IRIs and version IRIs count as held. The result has `sh:focusNode` the importing ontology, `sh:resultPath owl:imports`, `sh:value` the imported IRI, and a message naming both. An import a held import states and nothing holds is reported with that held import's ontology as the focus node, since no other finding would say it, so the baseline's own findings are those whose focus node is its ontology. A document with no named `owl:Ontology` states no import. A warning does not stop the job conforming, so `cst:conforms` is true. The results are sorted by importing ontology and then imported IRI, so a repeat gives the same graph.
- for a fence job, the import as the artefact `import.nt` grouped `import`, and `cst:digest`. It also gives `cst:declaresOntology`, the IRI of the one named `owl:Ontology` in the document, and `cst:declaresVersion`, that ontology's `owl:versionIRI` when it has exactly one. A document with no named `owl:Ontology`, or with several, gives neither, and the job says so with one `sh:Info` result of `cst:code` `NoOntologyIri`, and still succeeds. The writer copies both onto the import's root in the workspace's description, beside its label, so the held import can be drawn from the description alone.

The configuration a job checks is its input graph. The worker reads a missing baseline graph as empty, since the store keeps no empty graph, and fails a job whose input graph is missing.

Running a job twice gives the same graph but for its times, so a redelivered message is harmless.

### Assembly

## Completion events

The writer publishes a CloudEvent for each applied update of a job, of type `org.nebularis.lattice.studio.job.updated`, whose subject is the job's IRI and whose data is `{"status": ..., "workspace": ...}`, the job's status and its workspace's id, never its content. It goes on the topic exchange `lattice.studio.events`, with its type as the routing key and its attributes as `cloudEvents:` headers (the CloudEvents AMQP binding's binary mode), once the request that applied the update committed. The run worker publishes a run's frames to the same exchange in the same binding, and they are the one event that holds content (see Runs). Each service instance reads every event through a queue of its own, which lives as long as its connection, so an event published while no instance listens is lost, and a reader that missed one reads the job again.

The broker's MQTT over WebSockets (its Web MQTT plugin) carries the events to the browser, as CloudEvents in JSON in the message body, when `LATTICE_STUDIO_EVENTS_URL` names where a browser reaches it, the broker's own address or a proxy's. `/api/session` names it as `events`, and the page's `Content-Security-Policy` lets it connect there. The broker checks identity only, and the service's relay decides what each tab hears.

A tab connects with its principal's name as the user, the app's own credential as the password, and the client id `studio:<name>:<tab>`, where `<name>` is the principal's name in unpadded base64url and `<tab>` is 1 to 32 of `a-z0-9`. The credential is the OIDC access token, or with the local authenticator, which trusts the name a request gives, the key `/api/session` gives as `eventsPassword`, made at each start. Only a page of the studio's own origin can read the session, and the broker checks no `Origin`, so the key is what keeps a page of another site from connecting as a local principal. The broker's HTTP auth backend asks the service under the secret, after the broker's own users, and the service allows:

| Check | Allowed |
|---|---|
| `user` | the token authenticates as the user named, or the key is the service's and the local authenticator offers the name, from a client id of that user |
| `vhost` | `/` |
| `resource` | the session's own queue, `mqtt-subscription-<client id>qos0` or `qos1`, and reading or writing `amq.topic` |
| `topic` | writing `studio/u/<name>/<tab>/watch` and reading `studio/u/<name>/<tab>/events`, for the client id's own tab |

| On | Frame | Means |
|---|---|---|
| `watch` | `{"type":"subscribe","subject":"<job IRI>","headers":{...}}` | wait for a job's events. The headers are those an HTTP request of the browser carries, and must authenticate as the topic's principal. At most 200 subjects a tab, and 20 tabs a principal |
| `watch` | `{"type":"unsubscribe","subject":"..."}` | stop waiting |
| `watch` | `{"type":"gone"}` | forget the tab. It is also the tab's will message, which the broker sends when the connection drops uncleanly |
| `events` | `{"type":"error","message":"..."}` | a subscription refused. A job the principal may not read answers as one that does not exist |
| `events` | an event, with `specversion` | a job changed |

Whether the principal may read the job is checked at subscription and again at each delivery, by the rule of `GET /api/jobs/{job}`, so an event is withheld once its workspace is locked against the principal, with no change in the broker. A rebuild job's events reach an administrator only. The browser waits on an event between reads of a job, and reads again after five seconds without one, or polls as before when the studio offers no events or the connection is down. A relay that restarts forgets every watch, and the tabs' waits poll until they watch again.

## Runs

A run executes the artefacts of a finished compile job over an input that is not saved, and stores nothing. It is accepted at once, and its result reaches the submitting tab as numbered frames, so no request waits for a worker where the tab has events. A run is a deterministic function of the compile job, the input and a time the request states, so its identifiers and its times come from the request and its output is ordered canonically. It is not listed by `GET /api/workspaces/{ws}/jobs` and cannot be read again. A run that was lost is run again. Compilation, validation, proposal and publication stay jobs.

| `kind` | `target` | Body | Queue | Deadline, default and maximum |
|---|---|---|---|---|
| `sample` | `mapping` | a sample source, `Content-Type` `text/turtle`, `application/n-triples`, `application/xml`, `text/xml` or `application/json`. A run of a compiled mapping over it. A source in Turtle or N-Triples is answered by the studio's worker, and one in XML or JSON by the run worker | `lattice.studio.runs.rdf` for Turtle and N-Triples, `lattice.studio.runs` for the others | 120 seconds, for both queues |
| `simulate` | `persistence` or `surface` | `application/trig`, holding the sample world and the step. For `persistence` it is defined in [A persistence step](#a-persistence-step) and for `surface` in [A surface step](#a-surface-step). One step of a simulator | `lattice.studio.runs.interactive` | 15 seconds |

### The request

`POST /api/workspaces/{ws}/runs` takes these query parameters.

| Parameter | Holds |
|---|---|
| `kind`, `target` | a pair of the table above. Any other pair is `400` |
| `job` | the id of a compile job of the workspace. `404` when the workspace does not hold it, `409` when it is not a finished compilation of the part `target` names, by the rule the transforms route states |
| `tab` | the tab's identifier, 1 to 32 of `a-z0-9`, the one the tab uses for its events. `400` otherwise |
| `deadline` | an absolute time, an `xsd:dateTime` with a time zone. When it is left out the service sets it to now plus the kind's default. `400` when it is in the past or further off than the kind's maximum. The service compares it with its own clock, so a client whose clock runs ahead could be refused, and a client that has no reason to shorten the deadline leaves the parameter out |
| `wait` | `true` to have the service collect the run's frames and answer on the request, as below |

The principal must be one who may read the workspace, by the rule of `GET /api/workspaces/{ws}`, and a workspace it may not read answers `404`. A run writes nothing, so reading is enough. A body over 5 MiB is `413`, and a media type the kind does not take is `415`.

A deployment that offers no events to a browser, whose session description names no `events`, answers `400` to a run sent without `wait=true`, since there is no tab to send the frames to.

Without `wait` the answer is `202`, `Content-Type` `text/turtle` as every other RDF response, with the run as a `cst:Run`. No `Location` is given, since a run cannot be read again. `{uuid}` is a lower-case UUID the service chooses.

```turtle
<urn:lattice:studio:run:{uuid}> a cst:Run ;
    cst:kind cst:SampleRun ;                  # or cst:SimulationStep
    cst:target cst:Mapping ;                  # or cst:Persistence, cst:Surface
    cst:compileJob <urn:lattice:studio:job:{job}> ;
    cst:deadline "2026-11-15T10:02:00Z"^^xsd:dateTime .
```

The service answers `429` when the tab already has 4 runs pending, with `Retry-After` in seconds until the earliest of their deadlines, and `503` when it cannot reach the broker. A run is pending from the `202` until the service has seen its last frame or its deadline has passed.

With `wait=true` the service collects the run's frames from the events it already reads and answers `200`, `application/json`, a JSON array of the frames in sequence order, each exactly the frame object below, so the same schema holds both ways a result arrives. It answers `504` when the deadline passes first. This is how a tab with no events, or whose connection is down, runs. The worker behaves the same either way. A client may close a waiting request before it is answered. The service then stops collecting that run's frames and forgets it, and the run itself still ends at its deadline in the worker.

### Which worker answers a run

The run worker is two workers that keep one protocol, and the queue says which answers. The Java run worker consumes `lattice.studio.runs.interactive` and `lattice.studio.runs`, and answers a simulator's step and a sample over XML or JSON, with Jena, Saxon and JOLT. The studio's Python worker consumes `lattice.studio.runs.rdf` and answers a sample over Turtle or N-Triples with the driver of `tools/mork_rdf`, the one the dry run of a mapping uses, so a sample run and a dry run of the same scheme over the same source write the same triples. It reads the compiled forms the compile job holds, `{scheme}.compiled.ttl`, and refuses one whose queries no longer give the digest it is named by. Each worker keeps every rule below, and a message that reaches the worker that does not answer it is failed with a frame that says it went to the wrong worker. The Python worker takes a bounded number of runs at once, on a connection and a channel of its own, so a sample run never holds a job. Its output says it was evaluated by `mork_rdf` on Oxigraph, as the `cst:engine` of the report, and the Java run worker's report of a sample run names Saxon-HE for an XML source or JOLT for a JSON source the same way, where a simulator's `outcome` says its engine as `engine`.

### The message to the run worker

The service publishes the request to exchange `lattice.studio`, routed with `lattice.studio.runs.interactive` for `simulate`, and for `sample` by the input's media type, with `lattice.studio.runs.rdf` for `text/turtle` and `application/n-triples` and `lattice.studio.runs` for any other. The body is the input as received, `content_type` its media type, not persistent. No reply queue is named.

| Header | Holds |
|---|---|
| `run` | the run's IRI |
| `job` | the compile job's IRI, `urn:lattice:studio:job:` and a lower-case UUID |
| `kind` | `sample` or `simulate` |
| `target` | `mapping`, `persistence` or `surface` |
| `deadline` | the absolute time, as text |

The message's `expiration` is the milliseconds until the deadline, so the broker drops a request no worker took in time. None of the three queues is dead-lettered. The worker reads the compile job from the store, checks the request as the service did, and refuses without requeuing a message that lacks a header or whose run or job IRI is not in the forms above. A message the broker marks as redelivered is not run. The worker publishes one failed frame saying that a worker stopped during the run, and acknowledges it, and the author runs it again. A worker stops an execution that passes the deadline.

### A frame

The run worker publishes each frame to the topic exchange `lattice.studio.events` as a CloudEvent in the AMQP binding's binary mode, as a job's event is published. Its type is `org.nebularis.lattice.studio.run.frame`, which is also its routing key, its subject is the run's IRI, and its body is the frame object, valid against [`run-frame.schema.json`](run-frame.schema.json).

| Field | Holds |
|---|---|
| `run` | the run's IRI |
| `seq` | a whole number from 0, counting the run's frames |
| `last` | `true` on the run's final frame and on no other |
| `part` | optional. The part the frame's text belongs to, given on the first frame of each part only |
| `text` | optional. A piece of the current part's text. A part's text is the concatenation of the `text` of its frames in sequence order. At most 49,152 bytes as UTF-8, and never split inside a character |
| `more` | optional. A hint that the current part continues in the next frame, so that a display can say more of it is coming. A frame with no `part` continues the current part, whatever the frame before it said, and a client must not rely on `more` |
| `status` | on the last frame only, `succeeded` or `failed` |
| `message` | on a last frame whose `status` is `failed`, why, in plain words. A failed last frame settles the run, whatever frames are missing before it |
| `conforms` | optional, on a last frame whose `status` is `succeeded` |

| `part` field | Holds |
|---|---|
| `index` | a whole number from 0, counting the run's parts with no gap |
| `role` | one of `check`, `request`, `report`, `artefact`, `delta` and `outcome` |
| `mediaType` | the media type of the part's text |
| `path`, `group` | optional. As `cst:path` and `cst:group` give them for an artefact |
| `step` | optional. A whole number, the step of the run that wrote the part, as `cst:stratum` is for a dry run |

| `role` | The part is | Defined by |
|---|---|---|
| `report` | an `sh:ValidationReport` as Turtle, the findings as every job gives them. The report of a sample run also has `cst:engine`, the engine that evaluated the mapping | this contract |
| `artefact` | what a mapping wrote, as a mapping dry run's artefact is, with `group` the mapping and `step` the stratum | this contract |
| `check`, `request`, `delta`, `outcome` | the four parts of a persistence step | [A persistence step](#a-persistence-step) |
| `artefact`, `delta`, `outcome` | the parts of a surface step. An `artefact` is the rows one contract holds for the sources the edit changed or reached, before or after it, with `group` the contract's key and `path` `{key}/rows-before.trig` or `{key}/rows-after.trig`. The `delta` is the rows asserted and retracted by contract, and the `outcome` names the engine, the sources the edit changed and reached, and the contracts whose read set the edit touched | [A surface step](#a-surface-step) |

A run sends at most 128 frames. A result that would need more ends the run with a failed last frame whose `message` says the result is too large and to narrow what is run. A run that cannot start, for example one whose compile job it cannot read or whose input it cannot parse, is one frame, `seq` 0, `last` `true` and `failed`. [`samples/run-frames.example.json`](samples/run-frames.example.json) is a complete `sample` run, a report part, one artefact part split across two frames and a succeeded last frame, [`samples/run-frames-failed.example.json`](samples/run-frames-failed.example.json) is a run that could not start, and [`samples/run-frames-deadline.example.json`](samples/run-frames-deadline.example.json) is a run that lost frame 2 and ended with the service's failed frame at the deadline, so the array has a gap.

### A persistence step

The body of a `simulate` run of target `persistence` is TriG. Every graph is the sample world, the default graph included, except the reserved graphs, which are the graph `<urn:lattice:studio:step>` and every graph whose IRI starts with `urn:lattice:studio:step/`. The world is parsed into a dataset made for the step and shared with no other step, and the step is a function of the compile job and the body alone. A blank node keeps the label the TriG gives it. [`samples/facility-step-create.trig`](samples/facility-step-create.trig) and [`samples/facility-step-replace.trig`](samples/facility-step-replace.trig) are complete steps over the facility sample.

The graph `<urn:lattice:studio:step>` holds one `cst:SimulationStepRequest`, with the terms below. The terms are declared in [`studio-vocabulary.ttl`](studio-vocabulary.ttl). The class is named with `cst:forClass` and not `cst:target`, which names a part of the configuration.

| Term | Holds |
|---|---|
| `cst:forClass` | the target class of the compiled profile, as `dal:forTarget` states it. Once, as an IRI |
| `cst:forDeployment` | optional, the profile's `dal:forDeployment`. It is needed only where the class has a profile for more than one deployment |
| `cst:operation` | the operation by the name the compiled profile gives it, `dal:forOperation`, for example `create-if-absent`, `cas-replace` or `tombstone-delete`. A step runs an operation of kind Create, Replace, DeltaReplace or Tombstone |
| `cst:transactionTime` | an `xsd:dateTime` with a time zone. It is the time the step runs at, as below |
| `cst:parameter` | one for each parameter of the operation, a node with `cst:parameterName` and `cst:parameterValue`, both strings. The value is read by the kind the profile declares for the parameter, an IRI as an IRI and a position or an epoch as a whole number. A parameter is given once. `requestDigest` is never given, since the caller library computes it |

The payload of the operation is in the graph `<urn:lattice:studio:step/payload>`, which holds the parameter the operation's payload contract names, such as `payloadTriples` for a create and `assertTriples` for a delta replace. Any other payload parameter of the operation is in `<urn:lattice:studio:step/payload/{name}>`, such as `<urn:lattice:studio:step/payload/retractTriples>`. A payload graph that is not one the operation reads is a malformed part, and a payload the step leaves out is empty. A payload holds no blank node.

**What the studio's simulator sends.** The sample world is the tab's, and the studio builds each step's body from it, so the same world, object, operation and time give the same body. The world is every graph of the dataset the step applies to, written as TriG with each graph's triples in the order of their UTF-8 bytes. The studio mints the identifiers of a step from the step's number, the number of steps the world holds plus one. The revision is `urn:rev:` followed by the local name of the root, a slash and the number. The transaction is `urn:txn:`, the local name, a hyphen and the number. Any other IRI the operation declares, such as a tombstone's `cause` and `actor`, is `urn:simulator:`, the parameter's name, a slash and the number. The local name is what follows the root's last `#` or `/`, percent-encoded. A step the world did not apply does not move the number, so it is sent again with the same identifiers. `epoch` is the dataset's epoch where the profile binds a dataset and the world holds one, and the root's version row's otherwise. `expectedSeq` is the `pat:seq` of the root's version row, and one less when the step is sent as another writer. `nextSeq` is one more than `expectedSeq`. A payload parameter named `payloadTriples` holds the object, `assertTriples` the triples the object has that the aggregate stored in the world lacks, and `retractTriples` the triples the aggregate has that the object lacks, where the aggregate is the root's triples and those of each node reached through an owned edge of the compiled profile. The world moves forward only when the outcome is `applied`, by the delta's removed and added triples.

**The time.** Jena ARQ 6.2.0 reads the clock again for each operation of a request and overwrites a time set in advance, so a time cannot be handed to the engine. The worker parses the bound update and replaces every `NOW()` in its expression tree, in every operation and wherever an expression appears, with `cst:transactionTime` as an `xsd:dateTime` constant, by Jena's own expression and update transforms and never by editing the text. The `request` part shows the update as it ran. A log graph named from `NOW()` is named from the stated time, and `{month}` of a landing place is the first seven characters of its lexical form.

**The run.** The worker reads the compile job as the service checked it, a finished compilation of the `persistence` part, then its `compiled-profile.ttl` and the operation's SPARQL, at `{class}/{operation}.rq` or `{class}.{deployment}/{operation}.rq` with `:` and `/` of the operation's name written `_`. It binds the step with the Java caller library, which checks the parameters and the payload and computes the request digest. A request the check refuses is not sent, and the step ends there. Otherwise the worker runs the update over the world's quads in a dataset of its own, stops it at the run's deadline, and tells the change. Frames, parts and lists are in a canonical order, so the same step gives the same frames on a repeat and when the quads of the world are given in another order.

A step with a missing or malformed part, a job that is not a finished persistence compilation, or an operation the profile does not have is one failed frame whose `message` says which part and why. A refusal by the caller check is not a failure of the step. It is a result, shown as below.

A step's parts are `check`, `request`, `delta` and `outcome`, each with a media type, in that order. A step the check refuses has `check` and `outcome` only. Each JSON part is pretty-printed, with its keys in the order shown.

| `role` | `mediaType` | Holds |
|---|---|---|
| `check` | `application/json` | `operation`, `template`, `kind`, and `checks`, a list of `{name, verdict, reasons}` for `callerCheck` and `payloadCheck`. `verdict` is `passed`, `refused` or `notRun`, and each reason is `{code, where, reason}` in the caller library's order. The payload check is `notRun` for a delta replace, whose bound is checked over the state it leaves, and for an operation with no payload. A `note` says why |
| `request` | `application/sparql-update` | the operation's SPARQL with its parameters bound and its slots filled, as it ran, after a comment line that says each `NOW()` was replaced with the stated time |
| `delta` | `application/json` | `places`, one `{place, role, graphs}` for each landing place of the compiled profile a changed graph lands in, by the place's IRI and role, and `unplaced`. A graph is `{graph, added, removed}`, its quads as N-Triples lines in the order of their UTF-8 bytes. A graph the default graph is has `graph` null |
| `outcome` | `application/json` | `outcome`, `classification`, `reason`, `revision` when the transaction claimed one, and `engine`, the engine that evaluated the update, which a refused step leaves out since nothing was evaluated |

**Landing places.** A changed graph is assigned to a place exactly. A place with `dal:inGraph` is the graph it names. A place with `dal:inGraphNamed` is a template of the closed placeholders `{root}`, `{newRev}` and `{month}`, rendered with the step's own values, `{root}` percent-encoded as `ENCODE_FOR_URI` does, `{newRev}` as given and `{month}` from the stated time, and compared for equality. Nothing is matched by a pattern or a prefix. A graph that two places render is listed under both, and a graph that no place matches is listed under `unplaced` and never dropped, since it says the SPARQL wrote where the profile does not say it lands. The places are those that the accesses of the profile's operations land in, by `dal:landsIn`.

**Outcome.** The worker runs the caller library's confirmation read, which [the persistence contract](../persistence/README.md#the-confirmation) specifies and the Java library gives, over the dataset after the update, and tells the classification it returns. A claim of the transaction with the request's digest is `applied`, `classification` `Applied`. A claim with another digest is `refused`, `IdempotencyKeyReuse`. With no claim, the outcome is `lostRace` and the classification is the guard that failed, `EpochChanged`, `Gone`, `PreconditionFailed` for a position that is not the row's, `AlreadyExists` for a create over a version row or, in a composite family, over triples of the root in the data graph, and else `NotApplied`. A request the caller check refused is `refused`, `RefusedByCallerCheck`.

### A surface step

The body of a `simulate` run of target `surface` is TriG, read as a persistence step's is. Every graph is the sample world as it was before the edit, the default graph included, except the reserved graphs, which are the graph `<urn:lattice:studio:step>` and every graph whose IRI starts with `urn:lattice:studio:step/`. The world is parsed into datasets made for the step and shared with no other step, and the step is a function of the compile job and the body alone. [`samples/facility-surface-step-drawdown.trig`](samples/facility-surface-step-drawdown.trig), [`-borrower`](samples/facility-surface-step-borrower.trig), [`-sector`](samples/facility-surface-step-sector.trig), [`-repay`](samples/facility-surface-step-repay.trig), [`-first`](samples/facility-surface-step-first.trig), [`-subtype`](samples/facility-surface-step-subtype.trig) and [`-vocabulary`](samples/facility-surface-step-vocabulary.trig) are complete steps over the facility sample, whose borrowers are in graphs of their own as its persistence profile places them. Each is a different edit of one world, and together they show each way the parts below differ. The `-sector` and `-vocabulary` steps edit a graph that holds no carrier, and reach the facilities graph that does.

The graph `<urn:lattice:studio:step>` holds one `cst:SimulationStepRequest`, with the terms below. A step that names `cst:forClass` is a persistence step and is refused with a message that says so.

| Term | Holds |
|---|---|
| `cst:forPart` | `cst:Surface`, once, as an IRI. It says which simulator the step is for, and the run's `target` says the same |
| `cst:transactionTime` | an `xsd:dateTime` with a time zone, the time the step runs at, as for a persistence step. Each `NOW()` of an operation the job holds is replaced with it, and a query that reads the clock is refused |

**The edit.** It is the quads a write added and removed, which is what the `delta` part of a persistence step lists, so the surface simulator can run on the persistence simulator's result without the world being stated again after it. The quads added to the default graph are in `<urn:lattice:studio:step/added>` and those removed from it in `<urn:lattice:studio:step/removed>`. The quads added to a named graph are in `<urn:lattice:studio:step/added/{graph}>` and those removed in `<urn:lattice:studio:step/removed/{graph}>`, where `{graph}` is the graph's IRI percent-encoded as `ENCODE_FOR_URI` does. The world after the edit is the world before it, less the quads removed and with the quads added. Removing a quad the world lacks and adding one it holds change nothing. A quad that is both added and removed, an edit of a graph under `urn:lattice:studio:step` or of a derived partition, and any other graph under `urn:lattice:studio:step/` are malformed, and each is one failed frame that names the graph. An edit that changes nothing is a step, and its parts show no change.

**The sources.** The named graphs the edit changes are the sources whose rows are kept, as the studio's writer keeps the rows of each graph it writes, and so are the sources the edit reaches. A promotion's fill reads the world, each hop of its read path in the graph that holds it, so an edit to a borrower's graph changes the rows of the facilities whose carriers pass through that borrower, and an edit that adds `rdfs:subClassOf` to a vocabulary graph changes the rows of every source whose carriers it retypes. The sources an edit reaches are named by each promotion's reach query over the world before the edit, from the triples the edit adds and removes in the named graphs, and the step keeps them beside the graphs the edit changed, as the writer does within the write. The default graph is no source and no fill reads it. The rows of a source are in the partition `urn:lattice:studio:promoted:{source}`, the one the writer keeps (see [Promotions](#promotions)).

**The run.** The worker reads the compile job as the service checked it, a finished compilation of the `surface` part, then its `maintenance` artefacts. They are written by the compile job in the layout the studio stages for its own promotions, and are the operations the writer sends.

| Artefact | Holds |
|---|---|
| `maintenance/manifest.json` | one entry for each contract, ordered by `key`, with `contract`, `kind` (`promotion` or `index`), and where they exist `fill`, `reach`, `readSet` and `reason`. `fill`, `reach` and `readSet` name a file of the group. A contract the write does not keep has a `reason`, in words, and no `fill` |
| `maintenance/partition-clear.rq` | the update that empties a source's partition |
| `maintenance/{key}-fill-all.rq` | the update that fills a source's partition with the rows of the contract's promotion for the carriers the source types, reading each hop of the read path in whichever graph holds it, and a carrier typed by a subclass of the contract's class, whose `rdfs:subClassOf` edges lie in any graph, as a chain that changes graph at most twice |
| `maintenance/{key}-reach.rq` | the `SELECT` that names, as `?src`, the sources whose rows an edit reaches. The slot `{{{delta}}}` holds the triples the edit added and removed, as the rows of a `VALUES (?s ?p ?o)` block |
| `maintenance/{key}-read-set.rq` | the `CONSTRUCT` query for the graph the compiler hashes as the contract's `srf:InstanceGraphSource` read set entry, which is empty where the source holds no instance of the carrier |

The worker keeps the rows of each source the edit changed or reached with the writer's own maintenance, which sends the partition clear and then each contract's fill over the whole source, once in a dataset made from the world before the edit and once in a dataset made from the world after it. A row is the contract's when its fill wrote it, and a row two contracts write is the first one's, in the order of their keys. A source's rows already in the world are cleared first, so what the world holds of them is never read. A fill reads the world, so a read path that leaves the source's graph gives the rows the compiler's rebuild gives over the merged world. The worker then says which contracts the edit touched, by running each contract's read set query over every graph of the world before and after the edit, the default graph included and the derived partitions left out. The compiler records a contract's read set whether or not its source holds an instance of the carrier, with the digest of the empty graph where it holds none, and calls the contract stale when the read set it records now differs. A contract is therefore touched when the read set before the edit is not the read set after it, so the first instance of a class touches its contracts and so does the loss of the last. The read set is the triples of each instance and of each IRI its path ends at, so the world holds the end of the path as the vocabulary states it, as the samples' `<urn:g:vocabulary>` does, or an edit that changes the end of the path leaves the read set as it was. Each update is Jena's and is stopped at the run's deadline. Frames, parts and lists are in a canonical order, so the same step gives the same frames on a repeat and when the quads of the world are given in another order.

A step with a missing or malformed part, a job that is not a finished surface compilation, a job that lacks its manifest or a file the manifest names, or an operation that does not parse or fails is one failed frame whose `message` says which part and why.

A step's parts are, in this order, two `artefact` parts for each contract whose fill the job holds, ordered by `key`, then `delta` and `outcome`. A contract the write does not keep has no `artefact` part. A result that needs more than 128 frames is the failed frame every run has.

| `role` | `mediaType` | Holds |
|---|---|---|
| `artefact` | `application/trig` | the rows of the contract in each partition, as one graph block for each, with the triples in the order of their UTF-8 bytes. `path` is `{key}/rows-before.trig` for the world before the edit and `{key}/rows-after.trig` for the world after it, and `group` is the contract's `key`. A contract with no rows has an empty part |
| `delta` | `application/json` | `contracts`, one `{contract, key, graphs}` for each contract kept, where `graphs` has a `{graph, asserted, retracted}` for each partition the rows changed in, with its triples as N-Triples lines in the order of their UTF-8 bytes |
| `outcome` | `application/json` | `engine`, the engine that ran the operations, `sources`, the graphs the edit changed, `reached`, the other sources whose rows the edit reaches, and `contracts`, one `{contract, key, kind, kept, reason, readSetTouched, asserted, retracted}` for each contract of the job. `reason` is present for a contract that is not kept, and `asserted` and `retracted` count the rows of the `delta` |

### Delivery to the tab

The service instance that accepted the run keeps in memory who submitted it, from which tab, for which workspace and until when. That entry is coordination state, kept outside the graph and not authoritative, and losing it loses only runs in flight. Every instance reads every event, and only the instance holding the entry forwards a run's frames, so a frame reaches a tab once and in the order one consumer read it. It forwards each frame to the submitting tab's events topic, `studio/u/<name>/<tab>/events`, as the CloudEvent in JSON in the message body, the way a job's event reaches a tab, after checking that the principal may read the workspace by the rule of `GET /api/workspaces/{ws}`, from the graph as it is then. A tab sends no `watch` frame for a run. A frame whose run no instance holds is dropped.

| Attribute | Holds |
|---|---|
| `specversion` | `1.0` |
| `id` | a unique identifier of the event |
| `source` | where the event was published |
| `type` | `org.nebularis.lattice.studio.run.frame` |
| `subject` | the run's IRI |
| `time` | when the event was published |
| `datacontenttype` | `application/json` |
| `data` | the frame object |

A client reads the frame from `data` and recognises a frame by `type`, as it recognises a job's event, which has another type and holds no content. A job's event is unchanged.

At the deadline the accepting instance sends a failed last frame for a run it has not seen end, with `seq` one past the last it forwarded, and forgets the run. Its message says the run did not finish by its deadline. When a frame was lost during the run, this frame arrives with a gap before it.

### What a client must do

Events are sent at QoS 0 on a clean session, so a frame can be lost, and a run is not read again from anywhere.

- Keep the first frame it sees for each `seq`.
- Ignore a frame of a run it no longer shows. Frames may reach a tab before the `202` that names the run does, so keep the frames it cannot yet match until it learns the run's IRI, then drop those of other runs.
- Read a part's text from the frames that follow one another from 0. A frame with no `part` continues the current part, and a client does not rely on `more`.
- Treat the run as failed when the frame with `last` true has status `failed`, with that frame's message, even when earlier frames are missing, since its outcome is known and nothing more is coming. Show the parts that are whole and contiguous from 0 as partial output. The last part before a gap is not whole, since the missing frames may continue it.
- Treat the run as complete only when its last frame says `succeeded` and every `seq` from 0 to it is present. A `succeeded` last frame with a gap before it is partial.
- Treat the run as incomplete when it is neither complete nor failed after the deadline and a grace of 2 seconds, and offer to run it again. The grace lets the failed last frame the accepting instance sends at the deadline arrive, so that a client holding the deadline itself would not call the run incomplete just before it.
- Time a run by duration, not by a time to compare with the service's clock. A client that leaves `deadline` out sets its timer to the kind's default plus the grace from when it sent the request. That can only be later than the service's deadline, by the time the request took to arrive, and needs no agreement between clocks.
- Send at most one run a pane at a time, and of the requests waiting behind it only the newest.
- Ask the service to wait, with `wait=true`, where the studio offers no events or the tab's connection is down. Close that request when the run is no longer shown or the timer ends.

### Limits

The limits are held to what the probes of the broker observed it deliver to a slow reader, with a margin, and may be tightened without changing anything else in this contract.

| Limit | Value | Enforced by |
|---|---|---|
| input of a run | 5 MiB | the service, `413` |
| text of a frame | 49,152 bytes as UTF-8 | the worker |
| frames of a run | 128 | the worker |
| pending runs of a tab | 4 | the service, `429` |
| deadline | 15 seconds for `simulate`, 120 seconds for `sample`, each the default and the maximum | the service sets and checks it, and the worker stops an execution that passes it |
| grace after the deadline | 2 seconds | the client, which times a run by the kind's default plus the grace from sending its request |

## Promotions

Each write keeps the promoted partitions of the sources it writes in its own request: the writer sends the staged `maintenance/partition-clear.rq` and each fill of the source's family over the whole source after the write (projection maintenance, PM-2), so a read sees a write's promotions at once. The studio's own promotions each read one family of aggregates that hold the nodes they follow, so their fills read the source alone and no write of another graph reaches their rows. A promotion that reads across graphs, such as the surface compile job holds for a workspace's own contracts, has a reach query too, and the writer then also clears and fills every other source the write reaches, last in the same request, which the one writer of a workspace's commands applies in order. The workspace summaries are not stored: the service evaluates `workspace-summaries.rq` as it reads them. A rebuild job (`cst:kind cst:Rebuild`) names no workspace, target or input. The service submits one at start when no rebuild has recorded the contracts, or when the staged promotions are the recorded ones and new ones alone, and when an administrator posts to `/api/admin/rebuild`. A promotion that changed or went since the last rebuild is not rebuilt, since its old rows would be lost (BL-12): the start logs it, and `/api/status` lists it among its warnings, which the studio shows. The worker rebuilds every source's partition with `tools/surface`, and finishes the job with an update that carries the partitions, an empty one for each whose source is gone, and the record, which the writer replaces whole. The update that succeeds a rebuild deletes the job with its receipts. A rebuild job's commands carry no workspace and route by the job's own id. The writer accepts a promoted partition or the record from a rebuild job's update only, and refuses one that holds a blank node.

A `cst:Assembly` in the assembly configuration names the form it draws from, with `cst:assembles` (a `wrd:Wording` of the library), the optional elements and variants the drafter chose, with `cst:choice`, and the value of each governing variable, with `cst:setting` (a `wrd:VariableValue`). An `assemble` job runs `tools/wording_assembler` on each, in IRI order, at the job's `cst:submittedAt`, minting every new IRI under `urn:lattice:studio:job:{job}:record/`. For each it reports the assembler's findings as `sh:ValidationResult`s, each with `cst:code` the stage (`load`, `validate`, `decide`, `assemble` or `record`) and `sh:focusNode` the element or governing variable, and the job conforms when every assembly gave a record. For each that gave one it adds two artefacts, grouped by the assembly's IRI, `record.ttl`, the assembled wording, and `document.xml`, the assembled document in the markup of `contracts/document`. Every record is also written, in the job's update, to the named graph `urn:lattice:studio:job:{job}:record`, which is deleted with the job. A refused assembly gives no record (law WA6).

### Meaning and its review

The meaning configuration holds stated meaning (ADR-A104, ADR-A138): stated terms, each an `ins:Term` and `ins:Template` with `ins:expressedIn` the clause of the library that states it, and the relations, qualifiers and regimes under them. Every template enters it through a proposal (ADR-A138 decision 4). A `cst:Proposal` in the review configuration names the clause it reads with `cst:span`, the templates it proposes with `cst:proposes`, its proposer with `cst:proposer` (`manual`, `sentence-forms`, `language-model` or `assistant`, an MCP host) and when with `cst:proposedAt`, and the reviewer's decision with `cst:decision` (`cst:Confirm`, `cst:Retarget`, `cst:Decline` or `cst:Defer`, ADR-A42) and `cst:decidedAt`. A proposal carries what it proposes as Turtle in `cst:payload`, so a template waiting for review is never in the meaning configuration, whose subjects the rule above sorts by namespace. Confirming writes the payload into the meaning configuration, retargeting writes it as corrected, and declining or deferring writes nothing. Manual entry is a proposal its author confirms at once. A validation of the meaning configuration checks it, beside the library and the other configurations, against Instrument's structural and constraint shapes, and one of the review configuration reports nothing.

### Proposers

A `propose` job reads every clause of the library's forms that has no stated term in the meaning configuration and no proposal waiting in the review configuration, and asks its proposer for candidates for each (ADR-A138 decision 5). A candidate is a relation kind, the role that bears it and the role it is owed to, and an activity, each one the workspace already declares: a subclass of `ins:LegalRelation`, a `pty:Role` and a concept of the activity scheme. The job gives each candidate as a `cst:Proposal` waiting for review, with `cst:span` the clause, `cst:proposer` the proposer's name, `cst:proposedAt` the job's `cst:submittedAt`, `cst:evidence` the words it rests on, `cst:proposerVersion`, and its stated term and relation in `cst:payload`, minted under `urn:lattice:studio:job:{job}:proposal/`. They are the artefact `review.ttl`, which the browser adds to the review configuration for the author to save and decide. A clause with no candidate is reported as information.

| Proposer | Proposes from | Configured by |
|---|---|---|
| `sentence-forms` | the relation the worker's sentence-form reader classifies the clause as, and the roles and activities whose labels the clause's text names, in their order | nothing |
| `language-model` | a model's reply, through the deployment's language model provider, to a prompt rendered from a pack, checked against [`proposal-candidates.schema.json`](proposal-candidates.schema.json). The repository holds no clause-reading pack. A deployment supplies one, a folder with a `manifest.json` naming its `name`, `version`, `system` and `prompt` template files and optionally a `temperature`, sent only to a Chat Completions provider, whose templates may name `{clause}`, `{roles}`, `{activities}`, `{kinds}` and `{schema}` | the worker's environment: `LATTICE_PROPOSER_PACK` (the pack's folder) and the language model provider's settings, `LATTICE_PROPOSER_PROVIDER`, `LATTICE_PROPOSER_URL`, `LATTICE_PROPOSER_MODEL` and `LATTICE_PROPOSER_KEY`, as the [operations guide](../../docs/operator/configuration-studio-operations.md#worker) describes. Without the pack or the provider's settings the job fails, saying no language model is configured |
| `odrl` | one ODRL 2.2 policy in the job's input, through the studio's MORK mapping scheme, giving a proposal for each rule rather than for each clause (see Importing an ODRL policy) | `LATTICE_STUDIO_FEATURES` naming `odrl`, on the service |

### Importing an ODRL policy

`POST /api/workspaces/{ws}/jobs?kind=propose&target=odrl` imports one ODRL 2.2 policy as proposals (ADR-A144). The service offers it only when the deployment's `LATTICE_STUDIO_FEATURES`, a comma-separated list, names `odrl`, and answers `404` otherwise. The request body holds the configurations and one `cst:ImportDocument`, carrying the policy as received: `cst:documentContent` its text, `cst:documentMediaType` the media type it came with (`application/ld+json`, `text/turtle` or `application/n-triples`), `dct:conformsTo` the profile it says it is, which must be ODRL 2.2's namespace `http://www.w3.org/ns/odrl/2/`, and optionally `cst:importInto` a clause of the library to propose every term on. The browser takes the media type from how the author supplied the file, and the profile from what the author confirms, never from the content (STD-292).

The worker reads JSON-LD with the ODRL context bundled in [`odrl/odrl.jsonld`](odrl/odrl.jsonld) and fetches no remote context, compiles the mapping scheme [`odrl/odrl-instrument.mork.ttl`](odrl/odrl-instrument.mork.ttl) with `tools/mork_rdf`, and runs it over the policy. Each rule becomes one stated term, its relation, and what arises under it:

| ODRL | Stated meaning |
|---|---|
| a permission | an `ins:Permission`, its holder the assignee and its counterparty the assigner, excepting an `ins:Prohibition` of the same act on the same asset between the same parties, under a term `ins:impliedBy` the owner's exclusive rights and proposed on the permission's clause |
| a duty on a permission | what the permission arises on, an `ins:OnAct` of the duty's action by its party |
| a prohibition, and its remedy | an `ins:Prohibition`, and an `ins:Obligation` arising on its breach under the same term |
| an obligation, and its consequence | an `ins:Obligation`, and an `ins:Obligation` arising on its breach under the same term |
| a rule's party | a `pty:Role` for each party, labelled with the party's name |
| a rule's action | its `ins:activity`, a concept of a scheme of ODRL's actions bound to `ins-voc:ActivityContract`, `skos:broader` following ODRL's `includedIn` |
| a rule's target and constraints | its `ins:scope`, an `elg:AdmissionProfile` requiring the asset and each constraint, the operator choosing the condition's kind: `eq` exact, `isAnyOf` set membership, `isA` and `isPartOf` hierarchical, `neq` exact and negated, and `lt`, `lteq`, `gt` and `gteq` an interval over a range set: a range on the left operand's value space, bounded above or below at the right operand, open or closed as the operator says. Guards confine each to its operators (`mork:appliesWhen`). Any other operator, and a literal where a concept is needed, is reported as a warning for the reviewer to complete |

The job's artefacts are one for each configuration the proposals add to, named by `cst:group`, which the browser adds to that configuration for the author to save, except the baseline, which saves at once, so the author saves its new roles with a button of their own: `review.ttl` (the proposals, each payload holding only `ins:` subjects), `eligibility.ttl` (the profiles and conditions), `quantification.ttl` (the comparisons' value spaces, ranges, bounds and values), `baseline.ttl` (the roles of parties whose names match no role of the workspace, case aside, since a matching role is reused), `vocabulary.ttl` (the assets and actions as concepts, and the scheme binding) and, when no clause was picked, `library.ttl` (a form with one clause for each term, its text the rule in plain words). A policy that is not ODRL 2.2, a media type the worker does not read, and a JSON-LD context other than ODRL's own fail the job, saying why.

### Dry run

A dry run decides a stated term's eligibility conditions over sample facts, without instantiating anything (ADR-A138 decision 7, CB-Q2). The request body holds the configurations and one `cst:DryRun`, with `cst:term` the stated term and a `cst:fact` for each sample: `cst:forCondition` the condition, and `cst:number` a number for an interval condition or `cst:concept` a concept for a concept condition, one fact per concept. The worker finds the conditions the term reads, through its relations and their qualifiers, poses each as an `elg:Question` with the facts as its candidate, and decides it by the condition's compiled SPARQL, as an eligibility validation decides a question, never by the reference evaluator (ADR-A-FM3). The job gives one `cst:testResult` per condition, with `cst:condition`, `cst:decision` and `cst:diagnostic` when Undetermined, and reports as information a condition with no fact, which reads Undetermined, and a fact for a condition the term does not read. The facts live in the job's input only, deleted with the job. Stepping a regime over sample events has no compiled path yet, so a dry run does not step regimes (BQ-1).

A dry run of the mapping part compiles each scheme with `tools/mork_rdf` and runs it over the sample source, writing nothing but the job. Its findings are the compiler's and the run's checks, and its artefacts are what each mapping wrote, one N-Triples file for each mapping and stratum, with `cst:group` the mapping and `cst:stratum` the step of the run that wrote it. The browser keeps the sample and its format in its own storage for the workspace and reruns whenever the mapping part or the sample changes. A sample in XML or JSON runs as a transform instead.

### Transforms

A compile job of the mapping part also compiles each scheme over an XML or JSON source with `tools/mork_transforms` (ADR-A148), grouped by the scheme: `{scheme}.xsl`, an XSLT 3.0 stylesheet (`application/xslt+xml`), or `{scheme}.jolt.json`, a JOLT chain (`application/json`), and beside each `{path}.attribution.json`, the table that attributes what a run writes to its mappings. What a backend refuses or warns of is a finding on its mapping.

A transform runs a finished compile job's stylesheets or chains over a sample source in the transforms worker and answers at once. The route is deprecated in favour of a `sample` run (see Runs), which is what the studio's sample pane starts, so the studio no longer calls it. It stays for one release, answered by the run worker, which is the transforms worker generalised, and is then removed. Nothing is stored, since a run is derived and can be repeated. The service checks the request and publishes the sample as the message body, with `content_type` the sample's media type, header `job` the compile job's IRI, a correlation id, RabbitMQ's direct reply-to and an expiration of 30 seconds, routed with `lattice.studio.transforms` on exchange `lattice.studio`. The worker reads the compile job from the store, checks it as the service did, and replies with a Turtle graph. A request without a reply queue, a correlation id or a job IRI is dropped.

```turtle
<urn:lattice:studio:transform:{id}> a cst:Transform ;   # {id} is the request's correlation id
    cst:compileJob <urn:lattice:studio:job:{job}> ;
    cst:status cst:Succeeded ;                           # or cst:Failed, with cst:failureMessage
    cst:conforms true ;
    cst:report <urn:lattice:studio:transform:{id}#report> ;
    cst:artefact <urn:lattice:studio:transform:{id}#artefact-1> .
```

Each scheme with a transform of the sample's format runs, and each mapping's artefact is what it wrote, as a mapping dry run's at stratum 0. A node is a datum's when it has one of the datum's types, its IRI, or an IRI that starts with the constant text its identity starts with, and a triple two mappings could have written is in both artefacts. A scheme with no transform of that format is reported as information with `cst:code` `NotRun`, and a source the engine cannot read fails the run.

### Publication

Publishing a unit is two requests the browser sequences, as a transform is (ADR-A149). A publish job, `POST /api/workspaces/{ws}/jobs?kind=publish&target={part}&unit={root}`, reads the part as saved, not a request body, and names the version the unit's aggregate would be published as. The units, their root classes and the property that names a root's members are `publication-units.ttl`. The job's result names `cst:lineage` (the root), `cst:version` (`{lineage}/rev/1-{digest}`, the first 16 hexadecimal digits of the RDFC-1.0 SHA-256 of the aggregate as drafted), `cst:digest` (all 64), `cst:unitKind`, and one artefact, `version.nt`, the version's content: the aggregate with the root rewritten to the version, which names the lineage with `fnd:hasIdentity`. Only a principal who may write the workspace submits one.

A unit's references to other units are pinned when it is published (decision 5). A reference to a published lineage, which a draft follows, is rewritten to its current version, and a reference to a member of a published version, such as a concept of a scheme's edition, is kept. Either way the version names what it depends on with `cst:pins`, which the digest covers, so a new edition of what it pins makes a new version of it. A reference to the root of a unit nobody has published fails the job. A publish job may take its unit from a held import instead of a part, with `target=import&graph={digest}`. A validation, compilation, dry run or publish job also reads its workspace's held imports and, as context, the version each of its workspace's dependencies resolves to when it is submitted, under the version's IRI and under its lineage's.

`POST /api/workspaces/{ws}/publications?job={job}` then publishes what a finished publish job named, through a `publish` command. The writer creates the version, which is a no-op where it exists, then creates the lineage or replaces it at the sequence it read, with a `cst:Publication` event, `cst:current` and `fnd:supersededBy` (decision 13). A version orphaned by a publish that lost a race is reused by the next publish of the same content. A lineage replaced meanwhile leaves no receipt and the reply says to publish again. A version that is already current changes nothing and answers `200`. The event is, for example:

```turtle
<{lineage}/evt/e1/000002> a cst:Publication , prov:Activity ;
    cst:sequence 2 ;
    prov:generated <{lineage}/rev/1-{digest}> ;
    cst:principal "developer" ;
    cst:fromWorkspace <urn:lattice:studio:ws:{ws}> ;
    cst:publishedAt "2026-10-31T12:00:00Z"^^xsd:dateTime ;
    cst:previousPublication <{lineage}/evt/e1/000001> .
```

A compile job may compile a published version, with `version={version}` in place of a body, and its description names it with `cst:fromVersion`. Each artefact a compile job writes is a `fnd:DerivedArtefact` of kind `fnd:Compiled`, `prov:wasGeneratedBy` the job and `prov:wasDerivedFrom` what it compiled, the version or the job's input, and every published version it read as context (decision 10). A deployment that takes an artefact can so say which versions it came from, and fetch them as a bundle.

### Mapping proposals

A mapping proposal asks the deployment's language model, through the provider the worker is configured with (Chat Completions or Anthropic's Messages API, as the [operations guide](../../docs/operator/configuration-studio-operations.md#worker) describes), for a MORK mapping scheme from the source vocabulary. The worker offers the model `tools/mork`'s proposal tools as functions, the teaching pack, the target and source cards, candidate terms, one term in depth and the check, each bound to the job's own documents, and gives it the rules the workspace's own reviews teach. It calls them until it answers with a scheme in MCN, within `LATTICE_MAPPING_PROPOSER_ROUNDS` turns, 40 by default. The job's findings are the final check's, over the sample source when there is one. Its artefacts are `proposal.ttl`, grouped `mapping`, the decoded scheme with a `mork:ProposalRun` recording the model, its start and end and the tokens the provider counted, each mapping naming the run with `prov:wasGeneratedBy`, and `proposal.mcn`, the model's answer as it gave it. A scheme that names a node the workspace already holds is refused. The author reviews each mapping in mapping mode, which adds a `mork:MappingReview` to the mapping part.

## Writes

Every write to the store is a command to the store writer, `config-studio-writer`, the only component that writes the store (ADR-A136). A command is published to the super stream `lattice.studio.writes`, a direct exchange with argument `x-super-stream` whose binding keys `0` to `7` route to the partition streams `lattice.studio.writes-0` to `-7`, each bound with `x-stream-partition-order` and declared with `x-queue-type` `stream`, `x-max-age` `7D` and `x-max-length-bytes` 1 GiB. A command's routing key is its workspace's partition: the id's first 8 hex digits, as an unsigned number, modulo 8. So a workspace's commands stay in order in one partition. The writers are one single-active-consumer group, `lattice.studio.writers`, so each partition is applied by one live writer at a time, and RabbitMQ spreads the partitions across the writers that run. The number of partitions is fixed here, since changing it moves workspaces between partitions.

A command's fields are AMQP headers, and the graphs it carries are its body, `content_type` `application/n-quads`, persistent. Every command carries `id`, a lower-case UUID its sender chooses, and `sender`, `service` or `worker`. A command the service sends for a request also carries `principal`, the name the service authenticated, and `admin`, `true` when they administer (ADR-A149 decision 8). The writer refuses with `403` a write the workspace's mode does not allow its principal, and answers `404` to one whose workspace the principal may not read (decision 9). A command without a principal is the worker's, for its job.

| `command` | Other headers | Body | Sent by |
|---|---|---|---|
| `create` | `workspace`, `label`, `at`, `sample` when made from one | the baseline, in the default graph | service |
| `save` | `workspace`, `part`, `expect` (the revision `If-Match` named, a number), `at` | the graph, in the default graph | service |
| `import` | `workspace` (the new id), `label`, `at` | every graph of the export, named by its root under the new id | service |
| `delete-workspace` | `workspace` | none | service |
| `submit-job` | `workspace`, `job` | the job graph and its input graph, named | service |
| `job-update` | `workspace`, `job` | the job graph, named | worker, or the service when the job could not be published |
| `save-document` | `workspace`, `part` (the document's id), `expect`, `at`, `label` (its title), `sample` (its template's key) | the document's graph, in the default graph | service |
| `delete-document` | `workspace`, `part` (the document's id) | none | service |
| `delete-job` | `workspace`, `job` | none | service, and the writer's sweep of jobs finished longer ago than the retention |
| `set-access` | `workspace`, `part` (the mode, `locked`, `read-only` or `shared`), `label` (a new owner, from an administrator only) | none | service |
| `publish` | `workspace` (the one it is published from), `part` (the lineage), `label` (the version) | the version's content, in the default graph | service |
| `fence` | `workspace` | the default graph names each import by its root, `urn:lattice:studio:import:{digest}`, with `rdfs:label` and `cst:job`, its fence job's IRI, and holds nothing else. The command carries no content, no named graph and no `part`, since the writer reads each import's graph from its fence job. One to 64 imports. A command with a `part` or a named graph, which was the older form naming no job, is refused || service |

`workspace` and `job` are the ids, `at` an `xsd:dateTime`. The service publishes with confirms and sets `reply_to` to `amq.rabbitmq.reply-to` and `correlation_id` to the command's id, and the writer answers with headers alone. The stream keeps `reply_to` as an AMQP 1.0 address, `/queues/` and the percent-encoded queue name, which the writer decodes. The reply's headers are `status` (200 applied, 400 refused, 404 no such workspace or job, 412 a stale `expect`), `revision` (the new one, or the current one for 412) and `message`. The worker publishes with confirms and no reply.

The writer checks every command, whatever its sender checked: the ids, that a command carries only the graphs its kind may, part membership by the rule of `PUT`, that a job names its workspace, its own input, the workspace's baseline and `cst:Queued`, that a `job-update` carries the job graph, and for an `assemble` job also its record graph, whose terms are Wording's, PROV's, Foundation's, RDF's and RDFS's only, and that it changes nothing on the job node but `cst:status`, `cst:startedAt`, `cst:finishedAt`, `cst:failureMessage`, `cst:conforms`, `cst:report`, `cst:artefact`, `cst:gap`, `cst:resolution`, `cst:expansion`, `cst:testResult`, `cst:declaresOntology` and `cst:declaresVersion`, compared by value. For a `fence` it checks that each job named is a finished fence job of the command's workspace whose `cst:digest` is the import's digest, and reads from that job in the store both what the document declares and the import's graph, which must be the job's one `import.nt` artefact, present, parsing as N-Triples and not empty. The command carries neither, and a command that carries a `part` or a named graph is refused with a message saying that a fence names its imports by their fence jobs. The writer does not recompute the digest from the artefact, so the graph stored under a digest is the one its fence job holds under it, which the worker digested. A `job-update` for a deleted job is dropped, and so is one that would change a job held as `cst:Succeeded` to any other status, since a second worker that took the job for lost may write `cst:Failed` after the first has finished. A refused command is logged by the writer and passed over, since a stream has no dead letters, and its absent receipt records that it did not apply. A writer stores each partition's offset after a batch, so a writer that takes a partition over resumes after the last batch applied.

A writer applies the commands waiting for it, up to 64, in one SPARQL Update request, one transaction. A command that writes the workspace's aggregates, its description, its parts and its documents, runs the generated operation of each aggregate in this order, each guarded by the aggregate's version row and in a transaction of its own, `urn:txn:{command id}/{n}` from 1, and its `cst:Receipt` is the request's last operation for it, guarded on the claim of its last operation. A guard that fails part way therefore leaves no receipt, and the order leaves nothing a reader acts on. A command whose receipt already exists, such as one redelivered after a lost acknowledgement, is answered from its receipt and not applied again, and one retried after a partial application finds the claims of its applied operations and completes the rest. The writer plans from what it read and tracks each aggregate's sequence through the batch, so two commands of one batch on one aggregate see each other.

| `command` | Operations, in order |
|---|---|
| `create` | the baseline part created, then the description created |
| `save` | the part created when `expect` is 0, otherwise replaced in place with the delta of its patch log. The description is not written, so saving two parts never contends |
| `import` | every part and document of the body created, the baseline always, then the description created |
| `delete-workspace` | the description tombstoned, then each part and document with a version row tombstoned, their patch log graphs dropped with `DROP SILENT GRAPH`, and then the workspace's jobs and receipts graph cleared. The receipt is kept in the store's own receipt graph, guarded on the description's tombstone claim |
| `save-document` | the document created or replaced as a part is, then the description replaced when the document is new or its title or template changed |
| `delete-document` | the description replaced without the document, then the document tombstoned and its patch log graphs dropped |
| `set-access`, `set-dependencies`, `release` | the description replaced |
| `fence` | each import created, which writes nothing when it exists since it is stored by its digest, then the description replaced once, naming all of them. An import is never tombstoned, since a tombstoned root cannot be created again |
| `publish` | the version created, then the lineage created or replaced, guarded on the lineage's version row, and the receipt guarded on the lineage's claim. A version that is already current writes nothing |
| `submit-job`, `job-update`, `delete-job` | jobs are coordination data, kept outside the graph and not authoritative, and are written outside the profiles. The command's receipt is its first operation, only where its precondition holds, and its other operations require that receipt |

A batch the store refuses is retried whole.

| Receipt graph | Holds |
|---|---|
| `urn:lattice:studio:ws:{ws}:receipts` | the receipts of the workspace's own writes and of its jobs' deletions, deleted with the workspace |
| `urn:lattice:studio:job:{job}:receipts` | the receipts of a job's submission and updates, deleted with the job |
| `urn:lattice:studio:receipts` | the receipt of each workspace's deletion |

A receipt, `urn:lattice:studio:receipt:{id}`, has `cst:commandId`, `cst:command` (the cause), `cst:sender`, `cst:workspace`, `cst:job` where there is one, `cst:requestedAt` where the command has a time, `cst:committedAt` (the transaction time), `cst:wrote` for each graph and `cst:receiptRevision` for a save or a creation. No principal is recorded, since the studio authenticates no one. An export holds no receipt.

## Design decisions

- [A run in the studio](../../docs/architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md) stores nothing, is accepted at once and reaches the tab as numbered frames.
- [The persistence caller library](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md) checks and binds the generated operations a `simulate` step runs.
