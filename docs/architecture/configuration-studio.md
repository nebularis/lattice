<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio

The Configuration Studio is a web application for authoring an applied ontology's configuration against its baseline: vocabulary bindings (`voc:`), quantification (`qnt:`), eligibility (`elg:`), persistence profiles (`dal:`) and surface contracts (`srf:`). It checks each configuration with its layer's own shapes and compilers as the author edits, and compiles persistence and surface configuration into the artefacts a deployment runs. It is a supported part of LATTICE, built from a browser application in [`apps/config-studio`](../../apps/config-studio/README.md), a service in [`platform/config-studio-service`](../../platform/config-studio-service/README.md), a worker in [`workers`](../../workers/README.md#configuration-studio-jobs-adr-a136), and its contracts in [`contracts/config-studio`](../../contracts/config-studio/README.md). How to run and operate it is in the [operations guide](../operator/configuration-studio-operations.md) and the [runbook](../operator/configuration-studio-runbook.md).

## Components

```mermaid
flowchart LR
    subgraph Browser
        SPA["Studio (React, n3)"]
    end
    subgraph Service["config-studio-service (Java, Helidon, Jena)"]
        API["HTTP API, Turtle or RDF/XML"]
    end
    subgraph Store["Fuseki dataset studio"]
        WS["workspace graphs"]
        JOB["job graphs"]
    end
    MQ["RabbitMQ queue lattice.studio.jobs"]
    subgraph Worker["Python worker"]
        V["validate: pySHACL and the layers' tools"]
        C["compile: tools/persistence, tools/surface"]
    end
    SPA -- "RDF over HTTP" --> API
    API -- "SPARQL Update, Graph Store Protocol" --> Store
    API -- "job IRI" --> MQ
    MQ -- "job IRI" --> Worker
    Worker -- "read inputs, write result" --> Store
```

| Component | Owns | Never does |
|---|---|---|
| browser application | the editors, derived from the vocabularies it is served, and the sorting of an imported graph into a workspace's parts | interpret a finding or compile |
| service | HTTP, the store, revisions, and the publication of jobs | interpret `dal:`, `srf:` or the other layers' terms |
| worker | validation and compilation, with the engines `mise run check` uses | take a path, a command or a graph of its own choosing from a message |
| Fuseki | every workspace and job, as named graphs | hold state the service or worker keeps elsewhere |
| RabbitMQ | delivery of job IRIs to the worker | carry a job's content |

**Java owns HTTP and storage, Python owns meaning.** Validation and compilation run where pySHACL and the repository's compilers are, so the studio answers as `mise run check` would. A validation of persistence configuration also compiles it, because the `dal:` shapes target the dimension classes and do not see a `dal:DataAccessProfile` that declares several dimensions at once.

**The store is the only state.** The service keeps no registry. A workspace's revisions are triples in its own graph, and a job's status is read from the job's graph, which the worker writes (PRI-52).

**A job message is a job IRI and nothing else.** The worker reads the job graph, which names its input graphs by reference ([ADR-A30](decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md)). A job's input graph is written once under its IRI, and each baseline revision is a new graph, so a job's inputs never change under it.

## Forms are read from the ontology

The layers' specifications and shapes already say what a form needs. A class's SHACL shapes name its properties and constrain them, each property has an `rdfs:comment`, and each closed set of values is a class whose individuals are typed with it. The studio derives every field and option from the vocabulary and shapes it is served, and states only what an ontology cannot: how an editor groups classes into sections, and which properties pick a baseline term. When a layer adds a property, a constraint or a value, the studio offers it without a change.

Shapes are read first, and `rdfs:domain` and `rdfs:range` only where no shape says anything. A node shape with `sh:targetClass C`, or a class that is itself a shape, places each property its `sh:property` shapes name by a plain IRI `sh:path` on C and on C's subclasses. Several shapes for one property merge conservatively, so the highest `sh:minCount` and the lowest `sh:maxCount` hold. A property no shape names is placed by its `rdfs:domain` as before, and a property a shape names without saying what it holds takes its control from its `rdfs:range`. For each class and property, a studio override beats the shape, and the shape beats the domain and range. The staging step adds only the node shapes and property shapes to the served vocabulary. SHACL-SPARQL constraints, messages and complex paths are not staged or read.

| Shape constraint | Effect on the field |
|---|---|
| `sh:datatype xsd:integer`, `xsd:long`, `xsd:decimal` | number |
| `sh:datatype xsd:boolean` | switch |
| any other `sh:datatype` | text |
| `sh:class` of a class with individuals in the vocabulary | a select, or chips when the property takes several values, each option with its comment |
| `sh:class` of a class whose members the author creates, for example `dal:UniquenessConstraint` | a reference to a node of that type in the configuration, or a new one |
| `sh:in` of IRIs | a select over the listed values |
| `sh:nodeKind sh:IRI` | an IRI, unless the property's range gives a more specific control |
| `sh:maxCount 1` | one value. A larger count means several, and no count leaves the ontology's own rule (`owl:FunctionalProperty`, and every `dal:` property) |
| `sh:minCount` of 1 or more | marked required with an asterisk |
| `sh:name`, `sh:description` | the label and comment, where the property has none |

Without a shape, the range of the property picks the control.

| Range of the property | Control |
|---|---|
| `xsd:string`, `xsd:anyURI` | text |
| `xsd:integer`, `xsd:long`, `xsd:decimal` | number |
| `xsd:boolean` | switch |
| a class with individuals in the vocabulary | a select, or chips when the property is not functional, each option with its comment |
| a class whose members the author creates | a reference to a node of that type in the configuration, or a new one |
| a property listed as a baseline pick, for example `dal:targetClass` or `srf:carrier` | a picker over the baseline's classes or properties |

The read path of a surface contract is the one control that is not generic. It starts at the carrier and offers, at each hop, the properties whose domain is the current class, and writes `srf:readProperty` for one hop and `srf:hasPathStep` for more, never both.

## Workspaces and their graphs

A workspace is a baseline and the five configurations authored against it. Each is a named graph, and each has its own revision.

| Graph IRI | Written by | Holds |
|---|---|---|
| `urn:lattice:studio:ws:{ws}` | service | the `cst:Workspace`, its label, its current baseline graph and each configuration's revision |
| `urn:lattice:studio:ws:{ws}:baseline:{n}` | service, once | baseline revision n |
| `urn:lattice:studio:ws:{ws}:{part}` | service | the saved configuration of one part: `vocabulary`, `quantification`, `eligibility`, `persistence` or `surface` |
| `urn:lattice:studio:job:{job}` | service, then the worker | the `cst:Job`, its references, status, report and artefacts |
| `urn:lattice:studio:job:{job}:input` | service, once | the configurations as submitted |

A save carries the revision it expects in `If-Match`. The service compares it with the stored revision and, in one SPARQL Update request, replaces the configuration and moves its revision, so the two never disagree ([optimistic concurrency](optimistic-concurrency-in-rdf.md)). The comparison and the update run under a lock per workspace, so the studio runs one service instance.

**Which part a subject belongs to** is decided by one rule, which the browser applies when it sorts an imported graph and the service applies again to every graph it saves. A named subject belongs to the first of persistence, surface, eligibility, quantification and vocabulary whose namespace its `rdf:type` or its predicates use, a SKOS concept or scheme belongs to vocabulary, anything else to the baseline, and a blank node to the subject that refers to it. So an eligibility question that names a quantification range set stays with eligibility.

## A validation, end to end

```mermaid
sequenceDiagram
    participant UI as Studio
    participant S as Service
    participant F as Fuseki
    participant Q as RabbitMQ
    participant W as Worker
    UI->>S: POST /api/workspaces/{ws}/jobs?kind=validate&target=persistence
    S->>F: write the input graph and the job graph, status Queued
    S->>Q: publish the job IRI
    S-->>UI: 202, Location /api/jobs/{job}
    Q->>W: job IRI
    W->>F: read the job, its input and its baseline
    W->>W: the layer's shapes, and its compiler where it has one
    W->>F: write the job graph, Succeeded, with an sh:ValidationReport
    loop until finished
        UI->>S: GET /api/jobs/{job}
        S-->>UI: the job graph
    end
    UI->>S: DELETE /api/jobs/{job}
```

Findings of every engine are `sh:ValidationResult`s, so the browser reads one shape of finding and shows each on the field that caused it. A failure inside a job is written as `cst:Failed` with a message, and the message is acknowledged. A malformed message is refused without being requeued. A worker that stops mid-job leaves its message unacknowledged, so it is redelivered, and the job, which overwrites its own graph, runs again.

A vocabulary validation also resolves every scheme contract for every time segment and set of scopes its bindings draw. An eligibility validation also compiles every condition, expands each concept condition over its resolved scheme, and decides each `elg:Question` with the condition's compiled SPARQL against the decision the author expects of it. A compilation writes the generated artefacts into the job graph, with the gaps the compiler reports.

## On the wire

Every body is RDF: Turtle by default, or RDF/XML, which an XSLT can read, when the request's `Accept` ranks it higher or its `Content-Type` names it. RDF/XML is written plain, one description per subject. The routes, graphs, messages and every status code are in the [contract](../../contracts/config-studio/README.md).

## Security

Each component validates what it receives, whatever its client has checked, since it cannot know the input was not forged or altered on the way (PRI-75).

| Component | Validates |
|---|---|
| service | the body's size (5 MiB), media type and syntax, that an RDF/XML body declares no DTD, that a saved graph holds only its own part's subjects, every identifier in a path, the slug, the job's kind and target, and the revision a save expects |
| worker | that a message is a studio job IRI, that the job names a known kind and target, and that it names only its own input graph and a workspace baseline |
| browser | what an author types, so a finding appears before a save, never in place of the service's checks |

The service has no authentication. It binds to the loopback address, and a write needs `Content-Type` Turtle or RDF/XML, or a `DELETE`, none of which a page of another origin can send without a preflight that the service never answers. Every graph and update is built with Jena's typed API, never by joining strings (PRI-55). Static files are served from one directory with a normalised path check. Responses carry `nosniff`, `no-store` for the API, and a `default-src 'self'` content security policy. The worker runs one fixed operation per job kind and takes no path or command from a message ([ADR-A35](decisions/ADR-A35-trusted-surface-worker-execution-boundary.md)). So the studio is a tool for one author on one machine. A shared deployment needs authentication first.

## Costs

| Operation | Round trips | Data |
|---|---|---|
| open a workspace | one read each of the workspace, the baseline, the configurations and the vocabulary, which is cached by its ETag | the baseline and its configuration, typically under 2,000 triples |
| an edit | none | a copy of the browser's store, under 1 ms for 2,000 triples |
| a validation | one submission, a few polls and one deletion. The worker makes three reads and one write | two graphs written and dropped |
| a save | one write and one SPARQL Update | the configuration graph |

Validation dominates, at about a second on a laptop. A burst of typing yields one job, because edits are debounced and the browser keeps at most one validation in flight per graph. A response in RDF/XML is rewritten from Turtle, which costs about 60 ms for the 640 KB vocabulary against 3 ms as Turtle.

## Decisions

The studio rests on the shared semantic platform's boundary between runtimes ([ADR-A30](decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md)), the trusted worker boundary ([ADR-A35](decisions/ADR-A35-trusted-surface-worker-execution-boundary.md)), the Surface Contract Studio's authoring boundary ([ADR-A38](decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md)), and the persistence profiles and their compiler ([ADR-A78](decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md), [ADR-A79](decisions/ADR-A79-persistence-compiler-toolchain.md)).
