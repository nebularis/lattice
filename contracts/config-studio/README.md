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
| `urn:lattice:studio:description/{root}` | writer | the workspace's description aggregate. Its root is `urn:lattice:studio:ws:{ws}`, and `{root}` is the root percent-encoded as SPARQL's `ENCODE_FOR_URI` does, as in every graph below. The `cst:Workspace` node holds `rdfs:label`, `cst:createdAt`, `cst:modifiedAt`, `cst:fromSample` when it was made from a sample, `cst:owner`, `cst:mode`, `cst:dependsOn` and `cst:holdsImport`, with a label on each import's root. It names each document with `cst:document` and gives it `rdf:type` `cst:Document`, `rdfs:label` (the document's title), `cst:template` and `cst:modifiedAt`. It holds no revision. `cst:modifiedAt` moves only when the description is written |
| `urn:lattice:studio:part/{root}` | writer | the saved part `{name}` of a workspace, whose root is `urn:lattice:studio:ws:{ws}/part/{name}`. `baseline` is a part like the others, and its graph is the one jobs read as saved. The names are `baseline`, `library` (`wrd:`, forms and their variables, ADR-A138), `assembly` (`cst:Assembly` nodes and the `wrd:VariableValue` records they set), `meaning` (`ins:`, the stated meaning each clause states, ADR-A138), `review` (`cst:Proposal` nodes, each with its decision), `mapping` (`mork:` mapping schemes and the guards they name), `vocabulary` (`voc:` and `skos:`), `quantification` (`qnt:`), `eligibility` (`elg:`), `persistence` (`dal:`) and `surface` (`srf:`). A part's revision is the sequence of its version row, 0 when it has none. Its history is kept as deltas in the patch log, graphs `urn:rev:studio/{root}/e{epoch}/{seq}/add` and `/del` |
| `urn:lattice:studio:document/{root}` | writer | a document of the workspace's library, whose root is `urn:lattice:studio:ws:{ws}:document:{doc}`: its Wording graph, which the `document-to-wording` kit gives from its markup under the base `urn:lattice:studio:documents/`, and the markup itself as `cst:markup`, a string, on the node `urn:lattice:studio:documents/doc/{doc}/`. Its revision is the sequence of its version row, and its history is kept as a part's is |
| `urn:lattice:studio:job:{job}` | writer, for the service and then the worker | the `cst:Job` node, whose IRI is the graph's |
| `urn:lattice:studio:job:{job}:input` | writer, once | the configuration as submitted |
| `urn:lattice:studio:imported/{root}` | writer, once | a fenced import, whose root is `urn:lattice:studio:import:{digest}`, `{digest}` the SHA-256 of its RDFC-1.0 canonical N-Quads. `cst:holdsImport` names the root. Stored once, whichever workspaces hold it, and never edited or tombstoned (ADR-A149 decision 6) |
| `urn:lattice:studio:lineage/{root}` | writer | a published lineage, whose root is the lineage's IRI: the `fnd:PersistentIdentity`, each `fnd:hasVersion`, the `cst:current` version, each `fnd:supersededBy`, and each `cst:Publication` event. Its sequence counts the lineage's publications. Global, not a workspace's (ADR-A149) |
| `urn:lattice:studio:version/{root}` | writer, once | one version's content, whose root is the version's IRI, `{lineage}/rev/1-{digest}`. Immutable, and created again as a no-op since the same digest is the same content |

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
| `POST /api/workspaces/{ws}/imports?job={job}&label={label}` | | `201`, the workspace's description, holding the import a finished `fence` job digested. A fence job, `POST /api/workspaces/{ws}/jobs?kind=fence&target=import`, takes the imported RDF as its body |
| `GET /api/registry/bundle?iri={version}` | | `200`, `application/trig`, the version and every version it pins, transitively, each in a named graph named by the version's own IRI |
| `GET /api/workspaces/{ws}/imports/{digest}` | | `200`, the import's graph, when the workspace holds it |
| `DELETE /api/workspaces/{ws}/imports/{digest}` | | `204`. The workspace no longer holds it, and the graph stays for any other that does |
| `PUT /api/workspaces/{ws}/dependencies` | `<urn:lattice:studio:ws:{ws}> cst:dependsOn <iri> , …`, each a published lineage, which the workspace follows, or a version, which it pins | `200`, the workspace's description. `422` naming an IRI the registry does not hold, `403` to a principal who may not write the workspace |
| `GET /api/features` | | `200`, `application/json`, `{"features": [...]}`, the optional features the deployment turned on with `LATTICE_STUDIO_FEATURES`, such as `odrl` |
| `GET /api/vocabulary` | | `200`, the `dal:`, `srf:`, `fnd:` and `voc:` specifications and vocabularies merged, with an `ETag`. `304` for a matching `If-None-Match` |
| `GET /api/samples` | | `200`, every `cst:Sample` with its label and comment |
| `GET /api/samples/{id}` | | `200`, the sample's files merged into one graph |
| `GET /api/workspaces` | | `200`, every workspace's description |
| `POST /api/workspaces[?sample={id}]` | the baseline. `Slug` header, percent-encoded UTF-8, is the label. `sample` names the staged sample it was made from, which the description records | `201`, `Location: /api/workspaces/{ws}`, the description. `400` for a sample that is not staged, `422` for a baseline holding a subject of another part, by the rule of `PUT` below |
| `POST /api/workspaces` with `Content-Type: application/trig` | a file `GET …/export` wrote, here or elsewhere. `Slug`, when given, replaces its label | `201`, as above, a new workspace with the export's graphs, each part and document at revision 1. `422` for TriG that is not one workspace's export, or a graph holding another part's subject |
| `GET /api/workspaces/{ws}` | | `200`, the description |
| `DELETE /api/workspaces/{ws}` | | `204`. Drops the description, the parts, the documents, their patch logs and the workspace's jobs, and leaves their version rows tombstoned |
| `GET /api/workspaces/{ws}/export` | | `200`, `application/trig`, `Content-Disposition: attachment`, the description and every part and document that holds a triple, each graph named by its aggregate's root and without the patch log |
| `GET /api/workspaces/{ws}/graphs/{name}[?revision={n}]` | `name` is `baseline` or a configuration's name. `revision`, when given, is a whole number from 1 to the current revision | `200`, the graph, `ETag: "{revision}"`. With `revision`, the part as it was at that revision, rebuilt from the current graph by undoing each later revision's delta from the patch log, with blank nodes read back. `404` for a revision below 1 or above the current one, or for a workspace the principal may not read, `400` for one that is not a number |
| `PUT /api/workspaces/{ws}/graphs/{name}` | the new graph. `If-Match: "{revision}"` is required | `204`, `ETag` of the new revision. `428` without `If-Match`, `412` when it is not the current revision, `422` when a subject belongs to another part by the rule the browser's import uses (a named subject typed `cst:Assembly` or `wrd:VariableValue`, or using `cst:assembles` or `wrd:forVariable`, belongs to assembly, one typed `cst:Proposal` or using `cst:proposes` to review, one named by `mork:appliesWhen` to mapping, and otherwise to the first of mapping (`mork:`), meaning (`ins:`), persistence, surface, eligibility, quantification, vocabulary and library whose namespace its type or predicates use, a SKOS concept or scheme to vocabulary, anything else to the baseline, and a blank node to the subject that refers to it). A part is replaced in place, and its earlier revisions stay readable from the patch log |
| `POST /api/workspaces/{ws}/jobs?kind={validate,compile}&target={name}` | the configuration to check, which need not be saved, and the other configurations beside it as context | `202`, `Location: /api/jobs/{job}`, the job graph. `400` for another kind or target. Every configuration validates. `eligibility`, `persistence`, `surface` and `mapping` compile. `mapping` validates by compiling each scheme with `tools/mork_rdf`, which checks it against MORK's shapes and its target terms against the layers |
| `POST /api/workspaces/{ws}/jobs?kind=assemble&target=assembly` | the assembly configuration, which need not be saved, and the other configurations beside it, since a form's inclusion conditions are eligibility's | `202`, as for any job. The worker assembles every `cst:Assembly` of the input under Wording's baseline model (ADR-A139). See Jobs |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target={sentence-forms,language-model}` | the configurations, the library and meaning among them | `202`, as for any job. See Proposers |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target=rml` | the mapping configuration and one `cst:ImportDocument`, an RML mapping as Turtle or N-Triples | `202`, as for any job. `422` without exactly one document. The worker reads it into a MORK scheme with `tools/mork/src/rml2mork.py`, named under the base its subject templates share, returned as an artefact grouped `mapping`, with what MORK cannot say as warnings (`RmlNotRead`). One naming a node the workspace holds is refused |
| `POST /api/workspaces/{ws}/jobs?kind=propose&target=mapping-language-model` | the mapping configuration, with one `cst:ImportDocument` of `cst:documentRole` `cst:SourceVocabulary`, its `cst:sourceNamespace` optional, and at most one of role `cst:SampleSource`, each Turtle or N-Triples | `202`, as for any job. `422` otherwise. See Mapping proposals |
| `POST /api/workspaces/{ws}/jobs?kind=dry-run&target=meaning` | the configurations and a `cst:DryRun`, which is never saved | `202`, as for any job. See Dry run |
| `POST /api/workspaces/{ws}/jobs?kind=dry-run&target=mapping` | the mapping configuration and one `cst:ImportDocument`, its sample source in Turtle or N-Triples | `202`, as for any job. `422` without exactly one document with content and a media type. See Dry run |
| `POST /api/workspaces/{ws}/transforms?job={job}` | a sample source in XML or JSON, `Content-Type` `application/xml`, `text/xml` or `application/json` | `200`, the run as a `cst:Transform`. `404` for a job the workspace does not hold, `409` for one that is not a finished compilation of the mapping part, `415` for another media type, `413` over 5 MiB, `504` when no transforms worker answered within 30 seconds. See Transforms |
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
    cst:target cst:Persistence ;                # or cst:Vocabulary, cst:Quantification, cst:Eligibility, cst:Surface
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
- for a successful compilation, one `cst:artefact` per file, with `cst:path`, `cst:mediaType`, `cst:content` and `cst:group`. For persistence these are `compiled-profile.ttl` and each SPARQL file `instantiate` writes, grouped by target. For surface, each file `compile` writes, grouped by contract.
- for a mapping compilation, two files per scheme, `{scheme}.compiled.ttl`, the compiled mapping as RDF, and `{scheme}.rq`, its queries in the order a run takes them, grouped by the scheme's IRI. Where a representation scheme's format is JSON, XML, CSV or YAML, which `mork_rdf` leaves to another backend, `mapping.rml.ttl` too, the part compiled to RML by `tools/mork/src/mork2rml.py` under the namespace of its scheme.
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

A transform runs a finished compile job's stylesheets or chains over a sample source in the transforms worker and answers at once. Nothing is stored, since a run is derived and can be repeated. The service checks the request and publishes the sample as the message body, with `content_type` the sample's media type, header `job` the compile job's IRI, a correlation id, RabbitMQ's direct reply-to and an expiration of 30 seconds, routed with `lattice.studio.transforms` on exchange `lattice.studio`. The worker reads the compile job from the store, checks it as the service did, and replies with a Turtle graph. A request without a reply queue, a correlation id or a job IRI is dropped.

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

`workspace` and `job` are the ids, `at` an `xsd:dateTime`. The service publishes with confirms and sets `reply_to` to `amq.rabbitmq.reply-to` and `correlation_id` to the command's id, and the writer answers with headers alone. The stream keeps `reply_to` as an AMQP 1.0 address, `/queues/` and the percent-encoded queue name, which the writer decodes. The reply's headers are `status` (200 applied, 400 refused, 404 no such workspace or job, 412 a stale `expect`), `revision` (the new one, or the current one for 412) and `message`. The worker publishes with confirms and no reply.

The writer checks every command, whatever its sender checked: the ids, that a command carries only the graphs its kind may, part membership by the rule of `PUT`, that a job names its workspace, its own input, the workspace's baseline and `cst:Queued`, that a `job-update` carries the job graph, and for an `assemble` job also its record graph, whose terms are Wording's, PROV's, Foundation's, RDF's and RDFS's only, and that it changes nothing on the job node but `cst:status`, `cst:startedAt`, `cst:finishedAt`, `cst:failureMessage`, `cst:conforms`, `cst:report`, `cst:artefact`, `cst:gap`, `cst:resolution`, `cst:expansion` and `cst:testResult`, compared by value. A `job-update` for a deleted job is dropped. A refused command is logged by the writer and passed over, since a stream has no dead letters, and its absent receipt records that it did not apply. A writer stores each partition's offset after a batch, so a writer that takes a partition over resumes after the last batch applied.

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
| `fence` | the import created, which writes nothing when it exists since it is stored by its digest, then the description replaced. An import is never tombstoned, since a tombstoned root cannot be created again |
| `publish` | the version created, then the lineage created or replaced, guarded on the lineage's version row, and the receipt guarded on the lineage's claim. A version that is already current writes nothing |
| `submit-job`, `job-update`, `delete-job` | jobs are coordination data (PRI-52) and are written outside the profiles. The command's receipt is its first operation, only where its precondition holds, and its other operations require that receipt |

A batch the store refuses is retried whole.

| Receipt graph | Holds |
|---|---|
| `urn:lattice:studio:ws:{ws}:receipts` | the receipts of the workspace's own writes and of its jobs' deletions, deleted with the workspace |
| `urn:lattice:studio:job:{job}:receipts` | the receipts of a job's submission and updates, deleted with the job |
| `urn:lattice:studio:receipts` | the receipt of each workspace's deletion |

A receipt, `urn:lattice:studio:receipt:{id}`, has `cst:commandId`, `cst:command` (the cause), `cst:sender`, `cst:workspace`, `cst:job` where there is one, `cst:requestedAt` where the command has a time, `cst:committedAt` (the transaction time), `cst:wrote` for each graph and `cst:receiptRevision` for a save or a creation. No principal is recorded, since the studio authenticates no one. An export holds no receipt.

