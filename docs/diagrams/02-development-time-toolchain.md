<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# 2. Development-Time Toolchain

What runs when a layer's README changes, a law changes, or a compiler changes — the full chain
`mise run check` exercises, and what each piece catches that the others cannot. See the
[Developer Guide](../developer/developer-guide.md) for the commands and
[Formal Methods in the Development Lifecycle](../developer/formal-methods-lifecycle.md) for the
decision of which parts apply to a given change.

```mermaid
flowchart TB
    README["Layer README.md<br/>the one normative, literate source"]

    subgraph EXTRACT["tools/literate_extract.py"]
        direction TB
        TSPEC["turtle-spec blocks"] --> SPEC["spec/&lt;layer&gt;.ttl"]
        TVOC["turtle-vocab blocks"] --> VOCF["vocab/&lt;layer&gt;-vocab.ttl"]
        TSHP["turtle-shapes blocks"] --> SHP["shapes/structural.ttl<br/>shapes/constraints.ttl"]
        TEX["turtle-example blocks"] -.->|illustrative only, never extracted| NONE[" "]
        ISP["isabelle-spec blocks"] --> KTHY["tools/proofs/&lt;layer&gt;/Kernel.thy<br/>(datatype only, generated)"]
    end

    README --> TSPEC & TVOC & TSHP & TEX & ISP

    CHECK1["--check: compares current files<br/>against what would be written,<br/>exits non-zero on drift"]
    SPEC & VOCF & SHP & KTHY -.-> CHECK1

    subgraph PROOFS["Track E: tools/proofs/&lt;layer&gt;/ (Isabelle/HOL, ADR-A-FM1/A-FM2)"]
        direction TB
        KTHY --> LAWS["&lt;Layer&gt;Laws.thy<br/>hand-written theorems on the generated datatype"]
        LAWS --> BUILD["isabelle build -d tools/proofs/&lt;layer&gt;"]
        BUILD --> GATE["gate.py: statement digests,<br/>banned-marker scan, claim records"]
    end

    subgraph REFERENCE["Track B: tools/reference/&lt;layer&gt;/ (hand-written Python)"]
        direction TB
        REFCODE["kernel.py / denotation.py<br/>restates an already-accepted law independently"]
        REFCODE --> DIFF["differential tests vs. the real compilers<br/>(check:reference-eligibility)"]
    end

    LAWS -.->|statements ported, not copied| REFCODE

    subgraph COMPILERS["tools/mork_compilers/ and friends"]
        direction TB
        IR["shared IR (ADR-A89)"]
        IR --> SPARQLB["SPARQL backend"]
        IR --> SHACLB["SHACL backend"]
        IR --> SWRLB["SWRL backend"]
        IR --> OWLB["OWL backend (design-time)"]
    end

    README --> IR
    SPARQLB & SHACLB --> DIFF

    subgraph MODELS["Track C: tools/models/&lt;name&gt;/ (Alloy/SMT)"]
        direction TB
        ALS["hand-written model of a *proposed* law"]
        ALS --> RUNCHECK["run / check (Alloy Analyzer, Z3/cvc5)"]
        RUNCHECK --> EVIDENCE["evidence for an ADR"]
    end

    EVIDENCE --> ADR["ADR, Proposed then Accepted<br/>(docs/architecture/decisions/)"]
    ADR -.->|once accepted, the law is stable enough to prove| LAWS
    ADR -.->|once accepted, a compiler can read it| IR

    subgraph FRESH["tools/check_formal_freshness.py"]
        direction TB
        F1["Kernel.thy freshness:<br/>re-extract, compare byte for byte"]
        F2["Law coverage:<br/>every SemanticLaw named in the reference,<br/>covered or explicitly out of scope"]
    end

    KTHY -.-> F1
    README -.-> F2
    REFCODE -.-> F2

    subgraph MISE["mise run check"]
        direction LR
        M1["check:python-root"]
        M2["check:vocabulary / persistence / mork-compilers"]
        M3["check:reference-eligibility"]
        M4["check:formal-freshness"]
        M5["check:ontology-catalog / -versioning / import-guard"]
        M6["check:proofs (manual, native Isabelle)"]
        M7["check:java / check:frontend / check:workers / check:spc"]
    end

    CHECK1 -.-> M1
    DIFF -.-> M3
    F1 & F2 -.-> M4
    GATE -.-> M6

    subgraph CI["GitHub Actions (workflow_dispatch, manual until activated)"]
        direction LR
        CI1["platform.yml: ontology-and-tools, workers, java, frontend, spc, minting"]
        CI2["formal-methods.yml: proofs (Isabelle), models (Alloy)"]
    end

    MISE -.->|same tasks, no YAML duplication| CI1
    PROOFS -.-> CI2
    MODELS -.-> CI2
```
