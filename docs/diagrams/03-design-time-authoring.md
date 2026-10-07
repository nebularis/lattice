<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# 3. Design-Time Authoring

The moving parts behind authoring a contract or a template: drafting wording, mapping external
schemes, defining eligibility conditions, and everything that checks the result *before* it is
ever evaluated against a real case. See
[`docs/architecture/ux-design.md`](../architecture/ux-design.md) for the two products' own UX
specification and [`docs/architecture/surface-workflow.md`](../architecture/surface-workflow.md)
for the revision lifecycle in full.

```mermaid
flowchart TB
    subgraph AUTHOR["Authoring surfaces"]
        direction LR
        SCS["Surface Contract Studio<br/>Portfolio / Editor / Inspector / Release views"]
        MRW["MORK Review Workbench<br/>six-verb decision model, six surfaces"]
        WAI["Word authoring add-in<br/>drafting inside the document itself"]
    end

    subgraph DRAFT["Drafting a wording"]
        direction TB
        TXT["Text, elements, variables<br/>(ontology/wording)"]
        TMPL["Templates and library elements<br/>(ontology/instrument/templates, CCS C8a)"]
        ASSM["Assembly: form + settings + choices + model<br/>→ a deterministic record (WA1-WA7)"]
    end

    WAI --> TXT
    SCS --> TXT
    TXT --> TMPL --> ASSM

    subgraph ELIG["Defining eligibility conditions"]
        direction TB
        COND["elg:Condition<br/>ExactMatch / SetMembership / HierarchicalMatch / IntervalContainment"]
        PROF["elg:AdmissionProfile<br/>AllRequired / AnySufficient"]
        IR2["Shared IR (ADR-A89)"]
    end

    SCS --> COND --> PROF --> IR2

    subgraph DESIGNCHECK["Design-time checks, before anything runs"]
        direction TB
        SHACL1["SHACL structural validation<br/>(every layer's shapes/, as you author)"]
        OWLDT["OWL backend (tools/mork_compilers)<br/>subsumption, satisfiability, disjointness<br/>of condition classes (ADR-A90)"]
        ALLOY2["Track C design-time models<br/>(a proposed law, checked before its ADR)"]
        REASON["reasoning-testkit (test-only)<br/>confirms SWRL/OWL agree, never a runtime dependency"]
    end

    IR2 --> OWLDT
    TXT -.-> SHACL1
    COND -.-> SHACL1
    OWLDT -.-> REASON

    subgraph MAPPING["Mapping external schemes (MORK)"]
        direction TB
        INTENT["Intent nodes<br/>(mork:IntentNode, refinement order)"]
        COOCCUR["Co-occurrence constraint verification"]
        SIXVERB["Six-verb decision model<br/>(accept / reject / defer / …)"]
    end

    MRW --> INTENT --> COOCCUR --> SIXVERB

    subgraph COMPILE["Compilation (design-time, no live data yet)"]
        direction TB
        SFCOMP["Surface compiler<br/>promotion, index, projection"]
        READSET["Read-set recorded<br/>(ReadSetRecord, canonical digests)"]
        REGEN["Minimal regeneration planning<br/>(ADR-A27, impacted_surfaces)"]
    end

    ASSM --> SFCOMP
    SIXVERB -.->|a mapping Surface promotes| SFCOMP
    SFCOMP --> READSET --> REGEN

    subgraph LIFECYCLE["Revision lifecycle (surface-workflow)"]
        direction LR
        L1["draft"] --> L2["preview generation"] --> L3["compiler execution"] --> L4["generated"] --> L5["publish"] --> L6["released"]
    end

    SFCOMP --> L1
    REGEN -.->|triggers a scoped re-run| L3

    subgraph CONTROL["authoring-service: the design-time control plane"]
        CTRL["HTTP API: Surface authoring, MORK review, release"]
    end

    L6 --> CTRL
    CTRL --> SCS
    CTRL --> MRW
```
