<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE Developer Coordination Index

**Purpose:** the register of every unit of work and every slice, for agents and for the knowledge index. The two tables below are written by `mise run build:work` from the status records in the working tree, each slice's row from the slice board of its home unit's status record, which is the one place a slice's state is written (plan [work-board](plans/work-board.md)). Edit a status record, run `mise run build:work`, and commit both, since the `work` check refuses a commit whose records and region disagree.

**Across branches:** this file holds the state of the tree it was built from. `mise run work:board` reads every local and remote branch and says where each unit and slice is, which branch moves it, and which branch marks nothing. [ROADMAP.md](ROADMAP.md) carries the maintainer's summary, regenerated on `main` after a merge.

**Reading a row:** a state opens with a word of the ladder `planned`, `briefed`, `building`, `built`, `verified`, `merged`, `tagged`, or `blocked` or `dropped` aside, and the day it was reached from `building` on. `graph:ask -- read <slice id>` prints a slice's row and its record. A slice's id follows `PREFIX-segment(.segment)*`, the prefix declared on its plan, and the historic ids are in [the crosswalk](notes/slice-crosswalk-2026-11.md).

The registers hold entries that are not units of work. [Pending design decisions](pending-design-decisions.md), [technical debt](technical-debt.md) and the [backlog](backlog.md) are removable, each row leaving when a document takes it on. [Capabilities](capabilities.md), [mechanisms](mechanisms.md), [patterns](patterns.md), [principles](principles.md) and [standards](standards.md) are kept. All are read by the knowledge index.

The hand-written index that stood here until 2026-11-02 is archived as [coordination-index-2026-10.md](notes/coordination-index-2026-10.md).

<!-- BEGIN GENERATED work-board. Written by `mise run build:work` from the status records. Edit a status record, never this region. -->

## Units

Every unit with a status record, its state from the record's Status line, and its documents where they exist.

| ID | Kind | Prefix | State | Next | Documents |
|---|---|---|---|---|---|
| DESIGN_SKETCHES_INDEX | unit |  | dropped 2026-09-20 |  | [status](status/DESIGN_SKETCHES_INDEX.md) |
| applied-insurance-reference | epic | AIR | planned | AIR-3.3 | [plan](plans/applied-insurance-reference.md), [status](status/applied-insurance-reference.md), [review](review/applied-insurance-reference-review.md), 24 Validation Packs |
| applied-ontology-readiness | unit | AOR | built 2026-09-25 | AOR-1 | [plan](plans/applied-ontology-readiness.md), [status](status/applied-ontology-readiness.md), [review](review/applied-ontology-readiness-review.md), 12 Validation Packs |
| computable-contract-substrate | multi-slice unit |  | verified 2026-10-29 | CCS-0 | [plan](plans/computable-contract-substrate.md), [status](status/computable-contract-substrate.md) |
| config-studio | unit |  | built 2026-10-30 |  | [plan](plans/config-studio.md), [status](status/config-studio.md) |
| design-sketches-validation-summary | unit |  | merged 2026-09-20 |  | [status](status/design-sketches-validation-summary.md) |
| documentation-link-repair | unit |  | planned |  | [plan](plans/documentation-link-repair.md), [status](status/documentation-link-repair.md) |
| eligibility-compiler | unit |  | built 2026-09-25 |  | [plan](plans/eligibility-compiler.md), [status](status/eligibility-compiler.md) |
| formal-methods-track-b | phase | FMB | built 2026-10-09 | FMB-1 | [plan](plans/formal-methods-track-b.md), [status](status/formal-methods-track-b.md) |
| formal-methods-track-c | phase | FMC | built 2026-10-08 | FMC-1 | [plan](plans/formal-methods-track-c.md), [status](status/formal-methods-track-c.md) |
| formal-methods-track-e | phase | FME | built 2026-10-09 | FME-1.0 | [plan](plans/formal-methods-track-e.md), [status](status/formal-methods-track-e.md) |
| formal-methods-track-h | phase | FMH | verified 2026-10-09 | FMH-1.1 | [plan](plans/formal-methods-track-h.md), [status](status/formal-methods-track-h.md), 44 Validation Packs |
| formal-methods | epic | FM | built 2026-10-06 | FM-D0 | [plan](plans/formal-methods.md), [status](status/formal-methods.md), 2 Validation Packs |
| git-hooks | unit | GH | built 2026-10-24 | GH-0 | [plan](plans/git-hooks.md), [status](status/git-hooks.md) |
| governance-surfaces | unit |  | merged 2026-09-20 |  | [status](status/governance-surfaces.md) |
| identity-minting | unit | IM | built 2026-09-24 | IM-0 | [plan](plans/identity-minting.md), [status](status/identity-minting.md), 4 Validation Packs |
| implementation-handover-historical | unit |  | dropped 2026-09-20 |  | [status](status/implementation-handover-historical.md) |
| improved-ontology-documentation | unit | OD | verified 2026-10-17 | OD-0 | [plan](plans/improved-ontology-documentation.md), [status](status/improved-ontology-documentation.md), 16 Validation Packs |
| insurml-alignment | epic | IMA | planned | IMA-0.1 | [plan](plans/insurml-alignment.md), [status](status/insurml-alignment.md) |
| iri-patterns-post-3866b21-remediation | unit |  | merged 2026-09-23 |  | [status](status/iri-patterns-post-3866b21-remediation.md) |
| knowledge-index | unit |  | building 2026-10-26 |  | [status](status/knowledge-index.md) |
| ledger | unit | LG | building 2026-10-29 |  | [plan](plans/ledger.md), [status](status/ledger.md), 3 Validation Packs |
| llm-training-mtp | unit |  | merged 2026-09-20 |  | [status](status/llm-training-mtp.md) |
| mork-package-split | unit |  | merged 2026-09-20 |  | [status](status/mork-package-split.md) |
| mork-transforms | multi-slice unit |  | built 2026-10-30 |  | [plan](plans/mork-transforms.md), [status](status/mork-transforms.md) |
| mtp-execution | unit |  | merged 2026-09-20 |  | [status](status/mtp-execution.md) |
| multi-store-conformance | unit | MSC | built 2026-10-27 | MSC-1 | [plan](plans/multi-store-conformance.md), [status](status/multi-store-conformance.md), 5 Validation Packs |
| normative-rule-substrate | multi-slice unit | NRS | blocked | NRS-2 | [plan](plans/normative-rule-substrate.md), [status](status/normative-rule-substrate.md) |
| ontology-remediation | phase | OR | built 2026-10-28 | OR-0 | [plan](plans/ontology-remediation.md), [status](status/ontology-remediation.md) |
| ontology-root-relocation | unit |  | merged 2026-09-20 |  | [status](status/ontology-root-relocation.md), [review](review/ontology-root-relocation-review.md) |
| ontology-semantic-versioning | unit |  | built 2026-09-25 |  | [plan](plans/ontology-semantic-versioning.md), [status](status/ontology-semantic-versioning.md) |
| persistence-compiler-iri-sync | unit | PCI | built 2026-09-23 | PCI-1 | [plan](plans/persistence-compiler-iri-sync.md), [status](status/persistence-compiler-iri-sync.md), 5 Validation Packs |
| persistence-delta-replace | multi-slice unit |  | planned |  | [plan](plans/persistence-delta-replace.md), [status](status/persistence-delta-replace.md) |
| phase-0-1-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-0-1-handoff.md) |
| phase-0-status | unit |  | built 2026-09-23 | PLT-0.1.1 | [status](status/phase-0-status.md) |
| phase-1-status | unit |  | blocked 2026-09-22 |  | [status](status/phase-1-status.md) |
| phase-2-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-2-handoff.md) |
| phase-2-status | unit |  | planned |  | [status](status/phase-2-status.md) |
| phase-3-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-3-handoff.md) |
| phase-3-status | unit |  | planned |  | [status](status/phase-3-status.md) |
| phase-4-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-4-handoff.md) |
| phase-4-status | unit |  | planned |  | [status](status/phase-4-status.md) |
| phase-5-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-5-handoff.md) |
| phase-6-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-6-handoff.md) |
| platform-continuation | unit |  | merged 2026-09-20 |  | [status](status/platform-continuation.md), [review](review/platform-continuation-review.md) |
| projection-maintenance | multi-slice unit |  | planned |  | [plan](plans/projection-maintenance.md), [status](status/projection-maintenance.md) |
| python-test-melting | unit |  | built 2026-10-27 |  | [plan](plans/python-test-melting.md), [status](status/python-test-melting.md) |
| rdf-sparql-patterns-remediation | plan |  | merged 2026-09-25 |  | [plan](plans/rdf-sparql-patterns-remediation.md), [status](status/rdf-sparql-patterns-remediation.md) |
| rdf-sparql-patterns-status | unit |  | built 2026-09-22 | RSP-1 | [status](status/rdf-sparql-patterns-status.md) |
| repository-topology-a77 | unit |  | merged 2026-09-20 |  | [status](status/repository-topology-a77.md), [review](review/repository-topology-a77-review.md) |
| spc-package-split | unit |  | merged 2026-09-20 |  | [status](status/spc-package-split.md) |
| studio-publication | multi-slice unit in four phases |  | built 2026-10-31 |  | [plan](plans/studio-publication.md), [status](status/studio-publication.md) |
| studio-quality | multi-slice unit |  | building 2026-10-31 |  | [plan](plans/studio-quality.md), [status](status/studio-quality.md) |
| surface-mork-unified-projection | unit |  | merged 2026-09-22 |  | [status](status/surface-mork-unified-projection.md) |
| surface-outstanding-items | unit |  | merged 2026-09-22 |  | [status](status/surface-outstanding-items.md) |
| temporal-binding-consumer-hardening | unit |  | built 2026-09-25 |  | [plan](plans/temporal-binding-consumer-hardening.md), [status](status/temporal-binding-consumer-hardening.md) |
| toolchain-jdk25-python314 | unit |  | merged 2026-09-23 |  | [plan](plans/toolchain-jdk25-python314.md), [status](status/toolchain-jdk25-python314.md) |
| validation-pause-handover | unit |  | dropped 2026-09-20 |  | [status](status/validation-pause-handover.md) |
| validation-status | unit |  | merged 2026-09-20 |  | [status](status/validation-status.md) |
| vocabulary-temporal-binding | unit |  | built 2026-09-25 | VTB-1 | [status](status/vocabulary-temporal-binding.md) |
| word-authoring-poc | multi-slice unit | WA | built 2026-10-02 | WA-0 | [plan](plans/word-authoring-poc.md), [status](status/word-authoring-poc.md), 12 Validation Packs |
| work-board | multi-slice unit | WB | building 2026-11-02 | WB-0 | [plan](plans/work-board.md), [status](status/work-board.md) |
| xslt-sidecar | multi-slice unit |  | planned |  | [plan](plans/xslt-sidecar.md), [status](status/xslt-sidecar.md) |

## Work

Every slice on a board, keyed by its id, with the record and section it was read from.

| ID | Claim | Unit | State | Blocked on | Pointer |
|---|---|---|---|---|---|
| AIR-3.1 | AIR-3.1 | applied-insurance-reference | merged 2026-10-14 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-3.2 | AIR-3.2 | applied-insurance-reference | merged 2026-10-14 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-3.3 | AIR-3.3 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-S1 | substrate ADRs, S1 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-S2 | substrate ADRs, S2 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-S4 | substrate ADRs, S4 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-S5 | substrate ADRs, S5 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-S7 | substrate ADRs, S7 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AOR-1 | AOR-1 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-2 | to AOR-4 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-3 | to AOR-4 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-4 | to AOR-4 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-5 | to AOR-9 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-6 | to AOR-9 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-7 | to AOR-9 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-8 | to AOR-9 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-9 | to AOR-9 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-3b | AOR-3b | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-12 | AOR-12 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-13 | AOR-13 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-10 | AOR-11 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-11 | AOR-11 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-14 | to AOR-16 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-15 | to AOR-16 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-16 | to AOR-16 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| AOR-17 | AOR-17 | applied-ontology-readiness | built 2026-09-25 |  | docs/developer/status/applied-ontology-readiness.md#slices |
| CCS-0 | A-112, A-113, A-01 and ADR-A-C2 addenda | computable-contract-substrate | verified 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-1 | A-104 | computable-contract-substrate | verified 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-2 | A-106 | computable-contract-substrate | verified 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-3 | Wording spec, vocab and shapes | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-4 | Wording tables, assembly, variable values | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-5 | Wording amendments, law shapes, how-to | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-10 | Behaviour split and layer flip | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-10a | import guard | computable-contract-substrate | merged 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-11 | runtime records, occasions, initial states | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-11a | nested states, history, concurrent regimes | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-F1 | external and natural keys (ADR-A114) | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-6 | instrument, terms, the five relations, parties, content | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-7b | terms in time | computable-contract-substrate | merged 2026-10-06 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-7c | what terms are, and who they bind (split from CCS-7b) | computable-contract-substrate | merged 2026-10-27 | done | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8 | values in stated meaning, Wording references by identity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8b | values in stated meaning, Wording references by identity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9a | amendments, assents and taking effect | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.0 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.1 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.2 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-6a.1 | untimed closures (ADR-A105): the model and reference semantics, then the compilers | computable-contract-substrate | merged 2026-10-27 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-6a.2 | untimed closures (ADR-A105): the model and reference semantics, then the compilers | computable-contract-substrate | merged 2026-10-27 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.3 | set comparisons, qualifying rules, materiality, incorporation, template library | computable-contract-substrate | briefed 2026-10-27 | CCS-9b.4 on CCS-9b.3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.4 | set comparisons, qualifying rules, materiality, incorporation, template library | computable-contract-substrate | briefed 2026-10-27 | CCS-9b.4 on CCS-9b.3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9d | set comparisons, qualifying rules, materiality, incorporation, template library | computable-contract-substrate | briefed 2026-10-27 | CCS-9b.4 on CCS-9b.3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9c | set comparisons, qualifying rules, materiality, incorporation, template library | computable-contract-substrate | briefed 2026-10-27 | CCS-9b.4 on CCS-9b.3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8a | set comparisons, qualifying rules, materiality, incorporation, template library | computable-contract-substrate | briefed 2026-10-27 | CCS-9b.4 on CCS-9b.3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-16c | remove Party's shares | computable-contract-substrate | planned | CCS-9b.4 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-7a | regimes and gating, split from C7 | computable-contract-substrate | merged 2026-10-05 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-12 | runtime evaluator, relation plans | computable-contract-substrate | blocked | C9, CCS-11, CCS-11a, AIR-3.3, NRS N1 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-13 | runtime evaluator, relation plans | computable-contract-substrate | blocked | C9, CCS-11, CCS-11a, AIR-3.3, NRS N1 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-13a | design-time joint satisfiability: slot conditions by reasoner, the task NRS N3 reuses (deferred from CCS-5) | computable-contract-substrate | blocked | CCS-5, NRS N1 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-14 | examples, docs, handoff | computable-contract-substrate | blocked | CCS-8a, C9, CCS-12 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-15 | examples, docs, handoff | computable-contract-substrate | blocked | CCS-8a, C9, CCS-12 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-16 | examples, docs, handoff | computable-contract-substrate | blocked | CCS-8a, C9, CCS-12 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-17 | examples, docs, handoff | computable-contract-substrate | blocked | CCS-8a, C9, CCS-12 | docs/developer/status/computable-contract-substrate.md#slice-board |
| FMB-1 | kernel and denotation | formal-methods-track-b | built 2026-10-09 |  | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-2 | differential tests against the compilers | formal-methods-track-b | built 2026-10-09 |  | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-2.1 | harden the differential harness, seed a compiler-side fault | formal-methods-track-b | built 2026-10-09 |  | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-2.2 | verify/fix the scheme-less hierarchical-match branch | formal-methods-track-b | built 2026-10-09 |  | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-3 | Surface's regeneration property test, MORK and MCN deferred | formal-methods-track-b | built 2026-10-09 |  | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-4 | evaluation context, CCS C12's conformance kit | formal-methods-track-b | planned | CCS's C12, not yet briefable | docs/developer/status/formal-methods-track-b.md#slices |
| FMB-5 | measured mutation score | formal-methods-track-b | building 2026-10-09 | the mirror gap, or a hand-seeded fallback | docs/developer/status/formal-methods-track-b.md#slices |
| FMC-1 | Alloy skeleton | formal-methods-track-c | built 2026-10-08 |  | docs/developer/status/formal-methods-track-c.md#slices |
| FMC-2 | scheme composition | formal-methods-track-c | built 2026-10-07 | nothing — the overlap-rule *decision* is the maintainer's, not a blocker on this slice's own completion | docs/developer/status/formal-methods-track-c.md#slices |
| FMC-2.1 | well-formedness facts, re-run | formal-methods-track-c | built 2026-10-08 |  | docs/developer/status/formal-methods-track-c.md#slices |
| FMC-2.2 | model the composed scheme, decision-level check | formal-methods-track-c | planned 2026-10-08 |  | docs/developer/status/formal-methods-track-c.md#slices |
| FMC-2.3 | model `ADR-A116`'s own rule against HQ-4/IMA-D4a | formal-methods-track-c | planned 2026-10-08 |  | docs/developer/status/formal-methods-track-c.md#slices |
| FMC-3 | slot exclusivity, SMT | formal-methods-track-c | planned | FMC-2 (done) | docs/developer/status/formal-methods-track-c.md#slices |
| FME-1.0 | home, generation tooling | formal-methods-track-e | built 2026-10-09 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.1 | the kernel, for real | formal-methods-track-e | built 2026-10-06 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.2 | rounding and residual theorem | formal-methods-track-e | dropped 2026-10-07 | track B's B4, which waits on CCS's C12 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.3 | binding resolution | formal-methods-track-e | planned | track C's C2 is **done**, but the overlap-rule decision it surfaced, and the Vocabulary ADR IMA-D4a names, are not yet made/drafted (track C's own status) | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.4 | harden the gate and the kernel theory | formal-methods-track-e | built 2026-10-09 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-2 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-3 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-4 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-5 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FMH-1.1 | prefix antichain and overlap check | formal-methods-track-h | verified 2026-10-09 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.2a | witness harness, audit witnesses, measured gap list | formal-methods-track-h | verified 2026-10-09 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.2b | witnesses for the refusals and warnings | formal-methods-track-h | verified 2026-10-09 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.2c | witnesses for the 13 remaining shapes | formal-methods-track-h | verified 2026-10-09 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.2d | refuse a multi-valued single-valued property, TD-25 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.3 | static template checks S-3 and S-4 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.4a | refuse a composite boundary with several node properties, H-D4 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.4b | the declaration/implementation gap report | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.4c | a declaration the compiler cannot honour is a warning or a refusal | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-1.5 | stable labels | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO0 | correct the ownership note and its spike | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO1 | composite replace: payload to the default graph, linear sweep, TD-39, TD-36 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO2 | draft ADR-A122, Proposed | formal-methods-track-h | built 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO3 | `dal:` vocabulary 0.3.0: `dal:ownership`, reference data | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO4 | ownership tree and path compiler, added beside the old walk | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO5 | switch the compiler to the tree, TD-03, TD-35, TD-37, TD-40 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO6 | ownership refusals and the roots-only warning | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO7 | composite create and tombstone delete, TD-04 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO8 | injective graph naming within and across families, TD-38 | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-HO9 | ownership documentation and close-out | formal-methods-track-h | merged 2026-10-10 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.0 | ADR-A123 | formal-methods-track-h | built 2026-10-10 | merged and signed off 2026-10-12 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.1 | the typed IR and its renderer | formal-methods-track-h | built 2026-10-12 | merged and signed off 2026-10-12 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.2 | equivalence harness, `bootstrap-version-row` and `append-event` ported | formal-methods-track-h | built 2026-10-12 | merged and signed off 2026-10-12 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2 | typed IR | formal-methods-track-h | briefed |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.3 | named-graph row writers | formal-methods-track-h | built 2026-10-12 | merged and signed off 2026-10-12 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.4a | the composite ports | formal-methods-track-h | built 2026-10-13 | the maintainer's merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.4b | Oxigraph, probes, benchmark | formal-methods-track-h | built 2026-10-13 | the maintainer's merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.5 | key claims, audits, guard D, the `SELECT` fragment | formal-methods-track-h | built 2026-10-23 | the maintainer's merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6 | expected compiled profiles, paper check | formal-methods-track-h | built 2026-10-13 | the maintainer's merge. FMH-2.7 waits for RQ4 to RQ6 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6b | event slots, patch-log half held, H-D33 | formal-methods-track-h | building 2026-10-14 | the merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6c | write disciplines | formal-methods-track-h | built 2026-10-20 | the review tranche below | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6d | patch log for in-place families | formal-methods-track-h | planned 2026-10-20 | FMH-2.6c's review | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.8c | edges once, faster `members`, record classes, member parts | formal-methods-track-h | verified 2026-10-20 | the merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.9 | Mustache retired, D-12 (a), goldens keyed by operation | formal-methods-track-h | built 2026-10-21 | the review | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.11a | the Persistence README as a literate specification, graph for graph | formal-methods-track-h | built 2026-10-21 | the review | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.11b | the narrative, the pictures, the gotchas | formal-methods-track-h | built 2026-10-21 | the review, and D-59's split | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.7 | vocabulary and emission | formal-methods-track-h | planned | H2.7-Q1 to Q4, and FMH-2.6b's merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.8 | typed payload, caller checks | formal-methods-track-h | planned | H2.8-Q1 to Q3, and FMH-2.7's merge | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-3 | specification registry | formal-methods-track-h | planned | FMH-2 preferred first (smaller, more self-contained), not a hard blocker | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-4 | exhaustive cross-axis validation, BDD/SMT | formal-methods-track-h | planned | FMH-3 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-5 | capability-record extension, TLA+/Quint toolchain spike, protocol models A-D | formal-methods-track-h | planned | FMH-2 (read/write sets from the IR). ADR-A-FM4 is accepted | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-6 | Isabelle theories: Resolution, Positions, Encoding, Outcomes | formal-methods-track-h | planned | H1, FMH-5 for `Outcomes.thy` | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-7 | protocol models E-J | formal-methods-track-h | planned | FMH-5, FMH-6 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-8 | protocol models K-N, grounding | formal-methods-track-h | planned | FMH-7 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-9 | detection-coverage closure, generated audits | formal-methods-track-h | planned | FMH-3, FMH-4 | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-10 | runtime monitors | formal-methods-track-h | planned | FMH-9 | docs/developer/status/formal-methods-track-h.md#slices |
| FM-D0 | environments | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D1 | brief | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D2 | Rocq track | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D3 | Isabelle track | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D4 | report | formal-methods | built 2026-10-10 |  | docs/developer/status/formal-methods.md#track-d |
| FM-PF1 | fixes | formal-methods | built 2026-10-07 |  | docs/developer/status/formal-methods.md#track-d |
| GH-0 | GH-0 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-1 | GH-1 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-2 | GH-2 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-3 | GH-3 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-4 | GH-4 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| IM-0 | ADR-A82 amendment, ADR-A84, licence tracking, contracts and schemas, anchor vectors, specification skeleton | identity-minting | built 2026-09-24 |  | docs/developer/status/identity-minting.md#is-this-unit-complete |
| IM-1 | Vocabulary, compiler recipe emission, `dal:claimsConstraint` checks, `export-recipes` | identity-minting | built 2026-09-24 |  | docs/developer/status/identity-minting.md#is-this-unit-complete |
| IM-2 | Pinned Unicode 16.0 tables, Python library, vector generation | identity-minting | built 2026-09-24 |  | docs/developer/status/identity-minting.md#is-this-unit-complete |
| IM-3 | Java library, vector coverage of every recipe feature | identity-minting | built 2026-09-24 |  | docs/developer/status/identity-minting.md#is-this-unit-complete |
| IM-4 | Specification completion, READMEs, human walk-through | identity-minting | planned |  | docs/developer/status/identity-minting.md#is-this-unit-complete |
| OD-0 | ADRs, the AGENTS.md rule, the conventions document | improved-ontology-documentation | verified 2026-10-17 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC1 | catalogue and reader | improved-ontology-documentation | built 2026-10-17 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC2 | consumers use the reader | improved-ontology-documentation | verified 2026-10-18 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC3 | roots, AGENTS.md table, bypass scan | improved-ontology-documentation | verified 2026-10-19 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-1 | scanner and markers | improved-ontology-documentation | verified 2026-10-17 | the maintainer's merge | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-2 | sections 1 to 3 | improved-ontology-documentation | built 2026-10-18 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-3 | section 6 to OWL | improved-ontology-documentation | built 2026-10-18 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-4 | section 6 to SHACL | improved-ontology-documentation | built 2026-10-18 | the maintainer's review of six decisions taken alone | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-5 | generated regions | improved-ontology-documentation | built 2026-10-18 | the maintainer's review of six decisions taken alone | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-6 | Eligibility pilot | improved-ontology-documentation | built 2026-10-20 | the maintainer's review of seven decisions, 32 definitions and two changed tests | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-7 | Vocabulary | improved-ontology-documentation | verified 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-8 | onward, one per layer | improved-ontology-documentation | planned | OD-7, and for Foundation and Party their part of TD-16 | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-DOC1 | published decisions | improved-ontology-documentation | verified 2026-10-19 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-DOC2 | site sections | improved-ontology-documentation | merged 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-DOC3 | tutorial and Field Guide review | improved-ontology-documentation | planned | OD-DOC2, `lattice-tutorial` merged | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC4 | downstream extension | improved-ontology-documentation | planned | OD-RC3 | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC5 | package promotion | improved-ontology-documentation | planned | OD-RC4 | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-RC6 | XML catalogue folded in | improved-ontology-documentation | planned | OD-RC5, a new ADR on ADR-A88 | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-ELC | composition operation | improved-ontology-documentation | verified 2026-10-19 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-MC1 | migration check labels | improved-ontology-documentation | verified 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-VER1 | one release for the substrate | improved-ontology-documentation | verified 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-DOC2b | working documents out of published pages | improved-ontology-documentation | built 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-REL | first release, 0.18.0 | improved-ontology-documentation | verified 2026-10-20 | the tags, on `main` after the merge | docs/developer/status/improved-ontology-documentation.md#slices |
| IMA-0.1 | engagement brief | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.2 | licence and publication record | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.3 | ADR, profile | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.4 | ADR, bridge tooling and kits | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.5 | ADR, transclusion | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.6 | ADR, inline parts | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.8 | ADR, assembly interface | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.7 | alignment edits | insurml-alignment | planned 2026-10-05 |  | docs/developer/status/insurml-alignment.md#phase-0 |
| MSC-1 | MSC-1 | multi-store-conformance | built 2026-10-27 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-2 | MSC-2 | multi-store-conformance | built 2026-10-27 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-3 | MSC-3 | multi-store-conformance | built 2026-10-27 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-4 | MSC-4 | multi-store-conformance | built 2026-10-27 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-5 | MSC-5 | multi-store-conformance | built 2026-10-27 |  | docs/developer/status/multi-store-conformance.md#position |
| NRS-2 | Declare the importable rule-body fragment (A-109), revised for stratified state reads (ADR-A104 decision 15) | normative-rule-substrate | blocked | D1, NQ-2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-4 | Deontic extension of Instrument (A-104, R1) | normative-rule-substrate | dropped 2026-09-30 | CCS C1, C6 to C9 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-1 | Condition composition acyclicity (R4). CCS C13 and C13a wait on it | normative-rule-substrate | blocked | AIR-3.3 merge, NQ-2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-6 | Scheduled triggers as positioned stimuli (R3), built with CCS C12 | normative-rule-substrate | blocked | CCS C12, NQ-3 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-3 | Self-contradiction design-time check | normative-rule-substrate | blocked | CCS C13a, NQ-2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-5 | Closure declarations (A-105, R2) | normative-rule-substrate | dropped 2026-10-10 | CCS HQ-6a before CCS-9b.3, HQ-6b before C12 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-7 | Measure the OASIS conformance corpus | normative-rule-substrate | blocked | CCS C9, NRS-1 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-8 | Breach-chain checks (Behaviour records and evaluator moved to CCS C11, C12) | normative-rule-substrate | blocked | CCS HQ-6b, C12, C13, NQ-3 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-9 | Multi-axis temporal scope (A-108) | normative-rule-substrate | blocked | **D4, Phase 2 complete** | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-10 | Norm priority and defeasibility (A-107) | normative-rule-substrate | planned | D5 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-11 | Controlled-English rendering (R5) | normative-rule-substrate | planned | ingestion vision Phase 2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-12 | LegalRuleML and ODRL interchange (A-111) | normative-rule-substrate | planned | a trigger from the plan's §2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-13 | US Code §504 acceptance milestone | normative-rule-substrate | planned | all of the above | docs/developer/status/normative-rule-substrate.md#slice-board |
| OR-0 | OR-0 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-1 | OR-1 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-2 | OR-2 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-4 | OR-4 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-3 | OR-3 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-5 | OR-5 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-7 | OR-7 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-6 | OR-6 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-8 | OR-14 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-14 | OR-14 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-9 | OR-9 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-12 | OR-12 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-18 | OR-18 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-7b | OR-7b | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-10 | OR-10 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-11 | OR-11 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-13 | OR-13 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-15 | OR-15 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-16 | OR-16 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-17 | OR-17 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| OR-19 | OR-19 | ontology-remediation | built 2026-10-28 |  | docs/developer/status/ontology-remediation.md#position |
| PCI-1 | Dataset-level epoch guard (G1 — correctness) | persistence-compiler-iri-sync | built 2026-09-23 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PCI-2 | Ordering/receipt/concurrency/aggregate-boundary extension properties + meta-topology sharding (G5, G6) | persistence-compiler-iri-sync | built 2026-09-23 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PCI-3 | Identity minting profile resolution (G2) | persistence-compiler-iri-sync | built 2026-09-23 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PCI-4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | persistence-compiler-iri-sync | built 2026-09-25 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PCI-5 | Uniqueness `onViolation` reconciler operations, `mergeRelation`, `ClaimScheme` `dal:Dual` rotation, registry-token digest relaxation (G7) | persistence-compiler-iri-sync | built 2026-09-25 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PCI-6 | Documentation close-out | persistence-compiler-iri-sync | built 2026-09-25 |  | docs/developer/status/persistence-compiler-iri-sync.md#slice-status |
| PLT-0.1.1 | PLT-0.1.1 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.2 | PLT-0.1.2 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.3 | PLT-0.1.3 | phase-0-status | built 2026-10-10 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.4 | PLT-0.1.4 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.5 | PLT-0.1.5 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.6 | PLT-0.1.6 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.7 | PLT-0.1.7 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.8 | PLT-0.1.8 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.9 | PLT-0.1.9 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.10 | PLT-0.1.10 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.11 | PLT-0.1.11 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.12 | PLT-0.1.12 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.13 | PLT-0.1.13 | phase-0-status | built 2026-09-23 |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.14 | PLT-0.1.14 | phase-0-status | planned |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.1.15 | PLT-0.1.15 | phase-0-status | planned |  | docs/developer/status/phase-0-status.md#slice-status |
| PLT-0.2r | PLT-0.2r | phase-0-status | planned |  | docs/developer/status/phase-0-status.md#slice-status |
| RSP-1 | Core patterns | rdf-sparql-patterns-status | built 2026-09-22 |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| RSP-2 | Substrate and compiler | rdf-sparql-patterns-status | built 2026-09-22 |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| RSP-3 | Housekeeping first cut | rdf-sparql-patterns-status | planned |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| VTB-1 | ADR-A85 proposal, architecture mirror, fixture/test/traceability skeleton | vocabulary-temporal-binding | built 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-2 | 12 fixtures (11 positive/negative + 1 consumer), `structural.ttl`, `constraints.ttl` | vocabulary-temporal-binding | verified 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-3 | `tools/vocabulary` resolver + determinism/precedence/conflict tests | vocabulary-temporal-binding | verified 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-4 | Surface resolves scoped bindings via `vocabulary.resolve` (`tools/surface/src/surface/compile.py`), Eligibility's `HierarchyWellFoundednessShape` checks every scheme a contract could resolve to, both proven against dedicated fixtures | vocabulary-temporal-binding | built 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| WA-0 | Preflight | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-1 | Contracts, templates and samples | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-2 | Service model, mapping and shapes | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-3 | Detection, templates and conformance | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-4 | API and HTTP adapter | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-5 | Fuseki, RabbitMQ and the runnable service | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-6 | Logical English reading | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-7 | Worker runtime | word-authoring-poc | built 2026-10-02 |  | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-8 | Add-in domain | word-authoring-poc | built 2026-10-02 | WA-1 | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-9 | Add-in task pane and harness | word-authoring-poc | built 2026-10-02 | WA-8 | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-9a | Ribbon and right-click commands | word-authoring-poc | built 2026-10-02 | WA-9, WA-D13 | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-10 | Compose stack | word-authoring-poc | built 2026-10-02 | WA-5, WA-7, WA-9a | docs/developer/status/word-authoring-poc.md#slice-board |
| WA-11 | Documentation and close-out | word-authoring-poc | built 2026-10-10 | WA-10 | docs/developer/status/word-authoring-poc.md#slice-board |
| WB-0 | the sketch, the plan, this record, the INDEX.md entry | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-1 | `tools/work_board.py`, `work:board`, `build:work` | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-2 | the slice grammar, `work:rename`, `work:normalise`, the sweep, the `slice` family | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-3 | INDEX.md replaced, ROADMAP.md's generated regions, `build:roadmap` | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-4 | the `work` check and the post-merge regeneration | work-board | planned | WB-3 | docs/developer/status/work-board.md#position |
| WB-5 | AGENTS.md, the skills, the standards, the ADR | work-board | planned | WB-4 | docs/developer/status/work-board.md#position |
| WB-6 | `work:here` | work-board | planned | WB-1 | docs/developer/status/work-board.md#position |
| WB-7 | the branches marked or deleted | work-board | planned | WB-4, WB-Q9 | docs/developer/status/work-board.md#position |

<!-- END GENERATED work-board -->
