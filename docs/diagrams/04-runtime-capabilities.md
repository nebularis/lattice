<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# 4. Runtime Capabilities

What actually executes once an instrument is deployed and real data arrives, split clearly
between what exists today and what the architecture has designed but not yet built (dashed edges,
labelled "planned"). Conflating the two is worse than a gap in the picture — see
[`docs/architecture/data-architecture.md`](../architecture/data-architecture.md) for the three
data realms in full and
[`docs/developer/plans/computable-contract-substrate.md`](../developer/plans/computable-contract-substrate.md)
for C12, the runtime evaluator this diagram marks as planned.

```mermaid
flowchart TB
    subgraph INPUT["Real-world input"]
        STIM["A stimulus: an act, a notice, a fact, a date arriving"]
    end

    subgraph EXISTS["Exists today"]
        direction TB

        subgraph ELIGRT["Eligibility: compiled decisions, run against data"]
            direction TB
            SPARQLQ["Generated SPARQL,<br/>executed against a real store"]
            SHACLQ["Generated SHACL shapes,<br/>validated against real data"]
            SWRLQ["Generated SWRL rules,<br/>forward-chained (where supported)"]
            DECISION["Permitted / Denied / Undetermined,<br/>with a diagnostic when Undetermined"]
            SPARQLQ & SHACLQ & SWRLQ --> DECISION
        end

        subgraph SURFACEGEN["Surface's generated artefacts"]
            direction TB
            PROMOTED["Promoted views, indices, projections<br/>— read by anything downstream"]
        end

        subgraph WORKERRT["workers/: asynchronous job processing"]
            direction TB
            JOB["Job intake, idempotent delivery (ADR-A36)"]
            DURABLE["Durable state transitions (ADR-A37)"]
            JOB --> DURABLE
        end

        subgraph PLATRT["Platform services, running"]
            direction TB
            SWFRT["surface-workflow: revision lifecycle execution"]
            RELRT["release-integration: ledger, OCI export/restore"]
            OBXRT["platform-outbox: outbound event publishing"]
            FUSRT["Fuseki: the live semantic graph"]
        end

        STIM --> SPARQLQ
        STIM --> SHACLQ
        STIM --> JOB
        SWFRT --> FUSRT
        SWFRT --> JOB
        RELRT --> OBXRT --> JOB
        SURFACEGEN --> FUSRT
    end

    subgraph PLANNED["Designed, not yet built"]
        direction TB

        subgraph EVALCTX["The evaluation context (reference-evaluator.md)"]
            direction TB
            DESIGNENV["DesignEnv: case facts, pinned scheme editions,<br/>conversion contexts, a hypothetical state"]
            RUNENV["RunEnv: DesignEnv + positions + records"]
            MONAD["The monadic evaluator: reader / state / writer<br/>over a three-valued outcome"]
            DESIGNENV --> RUNENV --> MONAD
        end

        subgraph C12["CCS C12: the runtime evaluator"]
            direction TB
            REGIMES["Regimes and gating, evaluated over real positions"]
            OCCASIONS["Occasion derivation, with evidence (B6)"]
            RECORDS["Runtime records: act, breach, exercise,<br/>determination, deemed fact, acceptance"]
            REGIMES --> OCCASIONS --> RECORDS
        end

        subgraph C13["CCS C13: relation plans, in SPARQL"]
            PLANS["Compiled relation plans, run on a store"]
        end

        MONAD --> C12
        C12 --> C13
    end

    STIM -.->|planned| REGIMES
    DECISION -.->|feeds a gate's condition| REGIMES
    RECORDS -.->|planned: recorded in| FUSRT

    subgraph KIT["The conformance kit (track B4, planned)"]
        KITDATA["Generated event logs → expected outcomes,<br/>checked against both C12 and track E's mechanised reference"]
    end

    C12 -.->|planned| KITDATA
```
