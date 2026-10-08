<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# 5. Compiler Backends and Pluggable Surfaces

One semantics, several targets: how Eligibility's shared IR fans out to SPARQL, SHACL, SWRL and a
design-time OWL check, how Persistence's SPI boundary makes the storage backend itself pluggable,
and where you would add a new one — SQL, a different triple store, or an implementation surface
nobody here has built yet. See
[`tools/mork_compilers/README.md`](../../tools/mork_compilers/README.md),
[`tools/persistence/README.md`](../../tools/persistence/README.md) and
[`docs/architecture/rdf-sparql-patterns-guide.md`](../architecture/rdf-sparql-patterns-guide.md).

```mermaid
flowchart TB
    subgraph SOURCE["One normative source"]
        LAW["A law, stated once in a layer's README<br/>(epic principle E1)"]
    end

    subgraph ELIGIR["Eligibility: the shared IR (ADR-A23, ADR-A24, ADR-A89)"]
        direction TB
        COND2["elg:Condition / elg:AdmissionProfile"]
        PLAN2["ConceptPlan / IntervalPlan / ProfilePlan<br/>(required, excluded, scheme, expansion, hierarchy, evidence)"]
        COND2 --> PLAN2
    end

    LAW --> COND2

    subgraph BACKENDS["Pluggable backends, same IR in, different artefact out"]
        direction LR
        SPARQLB2["SPARQL backend<br/>(the reference, ADR-A28)"]
        SHACLB2["SHACL backend<br/>(readiness/determinacy/admission shapes)"]
        SWRLB2["SWRL backend<br/>(forward-chaining rules, one candidate per question)"]
        OWLB2["OWL backend<br/>(design-time: subsumption, satisfiability)"]
    end

    PLAN2 --> SPARQLB2 & SHACLB2 & SWRLB2 & OWLB2

    subgraph ORACLE["The independent check: track B's reference semantics"]
        REF2["tools/reference/eligibility<br/>never generated from the IR, never reads it"]
    end

    SPARQLB2 -.->|differential test| REF2
    SHACLB2 -.->|differential test| REF2
    LAW -.->|restated independently| REF2

    subgraph YOUROWN["Write your own backend"]
        NEWB["A new module implementing the same ConceptPlan/ProfilePlan contract<br/>e.g. a Datalog, Prolog, or native-code target"]
    end

    PLAN2 -.->|the contract a new backend must honour| NEWB
    NEWB -.->|checked the same way| REF2

    subgraph PERSISTENCE["Persistence: pluggable storage (data-architecture.md)"]
        direction TB
        PROFILE2["A Persistence profile<br/>(aggregate boundaries, patterns)"]
        PCOMP["Persistence compiler"]
        PROFILE2 --> PCOMP

        subgraph SPI2["semantic-dataset-spi: the pluggable boundary"]
            direction TB
            CORE["Core tier<br/>minimal operations every backend must support"]
            EXT["Extended tier<br/>optional, richer operations"]
            NATIVE["Native tier<br/>a backend-specific escape hatch"]
        end

        PCOMP --> CORE
        PCOMP -.->|where supported| EXT
        PCOMP -.->|where needed| NATIVE
    end

    subgraph STORES["Concrete backends behind the SPI"]
        direction LR
        FUSEKI2["Fuseki<br/>(RDF, built today)"]
        SQLSTORE["A SQL store<br/>(not built, the SPI is the extension point)"]
        OTHERSTORE["Your own store<br/>(same extension point)"]
    end

    CORE --> FUSEKI2
    CORE -.->|implement Core, you have a backend| SQLSTORE
    CORE -.-> OTHERSTORE

    subgraph SURFACEOUT["Surface: backend-neutral promotion"]
        SFOUT["Promoted views and projections<br/>read through the same SPI, not SPARQL-specific"]
    end

    SFOUT --> CORE

    subgraph MORKOUT["MORK: cross-ontology mapping, same pattern"]
        MOUT["A mapping targets any layer,<br/>compiled the same shared-IR-then-backend way"]
    end

    MOUT -.-> COND2
```
