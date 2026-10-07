<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# 1. The Whole Architecture

Every axis of the repository in one picture: the ontology's own dependency order, the tools that
compile and validate it, the formal-methods artefacts layered on top, the platform services and
applications that run against it, and the three data realms everything ultimately lands in.
Read [Development-time toolchain](02-development-time-toolchain.md),
[Design-time authoring](03-design-time-authoring.md), [Runtime capabilities](04-runtime-capabilities.md)
and [Compiler backends](05-compiler-backends-pluggable-surfaces.md) for a closer look at one slice
of this at a time.

```mermaid
flowchart TB
    subgraph ONTOLOGY["ontology/ — semantic assets (one README per layer, the normative source)"]
        direction TB
        FND["Foundation<br/>identity, versioning, provenance, evidence, temporal scope"]
        VOC["Vocabulary<br/>scoped/temporal concept-scheme binding (ADR-A85, ADR-A116)"]
        QNT["Quantification<br/>value spaces, quantities, ranges, conversion"]
        PTY["Party<br/>actors, roles, occupancy, groups"]
        ELG["Eligibility<br/>conditions, questions, decisions (K3 logic)"]
        BHV["Behaviour<br/>state, transition, trigger, guard, effect"]
        WRD["Wording<br/>contract text structure and variables"]
        INS["Instrument<br/>legal relations: obligation/prohibition/permission/power"]
        SRF["Surface<br/>promotion, index, projection"]
        MRK["MORK<br/>cross-ontology mapping (SKOS-based)"]
        PST["Persistence<br/>cross-cutting RDF patterns, aggregate boundaries"]
        APL["applied/<br/>capacity, classification, insurance"]
        SPC["SPC<br/>session-typed process calculus (standalone)"]

        FND --> VOC --> QNT --> PTY --> ELG
        ELG --> BHV
        ELG --> WRD
        BHV --> INS
        WRD --> INS
        INS --> APL
        FND -.-> PST
        FND -.-> SRF
        MRK -.->|targets any layer| ONTOLOGY
    end

    subgraph FORMAL["formal-methods epic — tracks A-G, layered on the ontology"]
        direction TB
        TRC["Track C<br/>design-time models (Alloy/SMT)<br/>tools/models/"]
        TRE["Track E<br/>mechanised theories (Isabelle/HOL)<br/>tools/proofs/"]
        TRB["Track B<br/>reference semantics<br/>tools/reference/"]
        TRA["Track A<br/>ledger & assurance harness<br/>(not started)"]
        TRF["Track F<br/>native tooling, per job family<br/>(not started)"]
        TRG["Track G<br/>instrument assurance<br/>(not started)"]
    end

    VOC -.->|ADR-A116 evidence| TRC
    ELG -.->|L9-L16, TA1/TA2| TRE
    ELG -.->|L9-L12,L14-L16| TRB
    TRB -.->|feeds| TRA
    TRE -.->|feeds| TRA
    TRC -.->|feeds| TRA
    TRB -.->|proved templates| TRG
    TRC -.->|proved templates| TRG

    subgraph TOOLS["tools/ — compilers, resolvers, validators"]
        direction TB
        MC["mork_compilers<br/>SPARQL/SHACL/SWRL/OWL backends"]
        VR["vocabulary<br/>binding resolver"]
        SFC["surface<br/>promotion/projection compiler"]
        PSC["persistence<br/>profile → SPARQL compiler"]
        MKT["mork<br/>MORK package + Teaching Pack"]
    end

    ELG --> MC
    VOC --> VR
    SRF --> SFC
    PST --> PSC
    MRK --> MKT

    subgraph PLATFORM["platform/ — runtime services (Java/Maven)"]
        direction TB
        AUTH["authoring-service<br/>design-time control plane"]
        SWF["surface-workflow<br/>revision lifecycle, worker coordination"]
        REL["release-integration<br/>ledger, OCI export/restore"]
        SPI["semantic-dataset-spi<br/>pluggable store boundary"]
        FUS["semantic-dataset-fuseki<br/>RDF triple store backend"]
        POL["semantic-policy<br/>access control, governance"]
        RTK["reasoning-testkit<br/>test-only OWL harness (ADR-A83)"]
        OBX["platform-outbox<br/>outbound event publishing"]
    end

    SFC --> SWF
    SWF --> SPI --> FUS
    SWF --> AUTH
    SWF --> REL
    MC -.->|test-only, never runtime| RTK

    subgraph WORKERS["workers/ — async runtime"]
        WRK["job processing, idempotent delivery<br/>(ADR-A36, ADR-A37)"]
    end

    SWF --> WRK
    REL --> OBX --> WRK

    subgraph APPS["apps/ — web applications (Yarn workspace)"]
        direction LR
        MRW["MORK Review Workbench"]
        SCS["Surface Contract Studio"]
        WAI["Word authoring add-in"]
    end

    AUTH --> MRW
    AUTH --> SCS
    SFC --> WAI

    subgraph PACKAGES["packages/ — standalone libraries"]
        MINT["minting<br/>identity-minting, Python + Java, no LATTICE dependency"]
    end

    FND -.->|identity patterns| MINT

    subgraph DATA["Three data realms (data-architecture.md)"]
        direction LR
        SEM["Semantic graph<br/>Fuseki"]
        OPS["Operational state<br/>PostgreSQL"]
        ART["Artifact bytes<br/>filesystem / OCI"]
    end

    FUS --> SEM
    WRK --> OPS
    REL --> ART

    subgraph CONTRACTS["contracts/ — inter-component data contracts (JSON Schema)"]
        CTR["events, identity, MORK, release, Surface"]
    end

    SWF -.->|validated against| CTR
    WRK -.->|validated against| CTR

    subgraph DEPLOY["deployment/ — local reference environment"]
        CMP["Docker Compose: Fuseki, Postgres, platform services"]
    end

    PLATFORM -.->|mise run services:up| CMP
```
