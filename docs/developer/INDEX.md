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
| applied-insurance-reference | epic | AIR | built 2026-11-02 | AIR-3.3 | [plan](plans/applied-insurance-reference.md), [status](status/applied-insurance-reference.md), [review](review/applied-insurance-reference-review.md), 24 Validation Packs |
| applied-ontology-readiness | unit | AOR | built 2026-09-25 | AOR-1 | [plan](plans/applied-ontology-readiness.md), [status](status/applied-ontology-readiness.md), [review](review/applied-ontology-readiness-review.md), 12 Validation Packs |
| computable-contract-substrate | multi-slice unit | CCS, HQ | verified 2026-10-29 | CCS-0 | [plan](plans/computable-contract-substrate.md), [status](status/computable-contract-substrate.md), 22 Validation Packs |
| config-studio | unit |  | merged 2026-10-30 |  | [plan](plans/config-studio.md), [status](status/config-studio.md) |
| design-sketches-validation-summary | unit |  | merged 2026-09-20 |  | [status](status/design-sketches-validation-summary.md) |
| documentation-link-repair | unit |  | planned |  | [plan](plans/documentation-link-repair.md), [status](status/documentation-link-repair.md) |
| eligibility-compiler | unit |  | built 2026-09-25 |  | [plan](plans/eligibility-compiler.md), [status](status/eligibility-compiler.md) |
| ensemble | unit | ES | briefed | ES-0 | [plan](plans/ensemble.md), [status](status/ensemble.md), 2 Validation Packs |
| formal-methods-track-b | phase | FMB | building 2026-10-09 | FMB-1 | [plan](plans/formal-methods-track-b.md), [status](status/formal-methods-track-b.md) |
| formal-methods-track-c | phase | FMC | built 2026-10-27 | FMC-1 | [plan](plans/formal-methods-track-c.md), [status](status/formal-methods-track-c.md), 1 Validation Packs |
| formal-methods-track-e | phase | FME | built 2026-10-09 | FME-1.0 | [plan](plans/formal-methods-track-e.md), [status](status/formal-methods-track-e.md) |
| formal-methods-track-h | phase | FMH | built 2026-11-01 | FMH-2.12 | [plan](plans/formal-methods-track-h.md), [status](status/formal-methods-track-h.md), 45 Validation Packs |
| formal-methods | epic | FM | built 2026-11-02 | FM-D0 | [plan](plans/formal-methods.md), [status](status/formal-methods.md), 1 Validation Packs |
| git-hooks | unit | GH | built 2026-11-03 | GH-0 | [plan](plans/git-hooks.md), [status](status/git-hooks.md) |
| governance-surfaces | unit |  | merged 2026-09-20 |  | [status](status/governance-surfaces.md) |
| identity-minting | unit | IM | built 2026-09-24 | IM-0 | [plan](plans/identity-minting.md), [status](status/identity-minting.md), 4 Validation Packs |
| implementation-handover-historical | unit |  | dropped 2026-09-20 |  | [status](status/implementation-handover-historical.md) |
| improved-ontology-documentation | unit | OD | built 2026-10-20 | OD-0 | [plan](plans/improved-ontology-documentation.md), [status](status/improved-ontology-documentation.md), 17 Validation Packs |
| insurml-alignment | epic | IMA | planned | IMA-0.1 | [plan](plans/insurml-alignment.md), [status](status/insurml-alignment.md) |
| iri-patterns-post-3866b21-remediation | unit |  | merged 2026-09-23 |  | [status](status/iri-patterns-post-3866b21-remediation.md) |
| knowledge-index | unit |  | building 2026-10-26 |  | [status](status/knowledge-index.md) |
| lattice-tutorial | multi-slice unit |  | building 2026-11-06 | TUT-0 | [plan](plans/lattice-tutorial.md), [status](status/lattice-tutorial.md) |
| ledger | unit | LG | built 2026-11-08 | LG-2 | [plan](plans/ledger.md), [status](status/ledger.md), 4 Validation Packs |
| llm-training-mtp | unit |  | merged 2026-09-20 |  | [status](status/llm-training-mtp.md) |
| mork-package-split | unit |  | merged 2026-09-20 |  | [status](status/mork-package-split.md) |
| mork-transforms | multi-slice unit |  | built 2026-10-30 |  | [plan](plans/mork-transforms.md), [status](status/mork-transforms.md) |
| mtp-execution | unit |  | merged 2026-09-20 |  | [status](status/mtp-execution.md) |
| multi-store-conformance | unit | MSC | merged 2026-10-29 |  | [plan](plans/multi-store-conformance.md), [status](status/multi-store-conformance.md), 5 Validation Packs |
| normative-rule-substrate | multi-slice unit | NRS | blocked | NRS-2 | [plan](plans/normative-rule-substrate.md), [status](status/normative-rule-substrate.md) |
| ontology-remediation | phase | OR | built 2026-10-28 | OR-0 | [plan](plans/ontology-remediation.md), [status](status/ontology-remediation.md) |
| ontology-root-relocation | unit |  | merged 2026-09-20 |  | [status](status/ontology-root-relocation.md), [review](review/ontology-root-relocation-review.md) |
| ontology-semantic-versioning | unit |  | built 2026-11-03 |  | [plan](plans/ontology-semantic-versioning.md), [status](status/ontology-semantic-versioning.md) |
| persistence-compiler-iri-sync | unit | PCI | built 2026-09-25 | PCI-1 | [plan](plans/persistence-compiler-iri-sync.md), [status](status/persistence-compiler-iri-sync.md), 5 Validation Packs |
| persistence-delta-replace | multi-slice unit | DR | building 2026-11-01 | DR-1 | [plan](plans/persistence-delta-replace.md), [status](status/persistence-delta-replace.md), 4 Validation Packs |
| phase-0-1-handoff | unit |  | merged 2026-09-20 |  | [status](status/phase-0-1-handoff.md) |
| phase-0-status | unit |  | built 2026-10-10 | PLT-0.1.1 | [status](status/phase-0-status.md) |
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
| projection-maintenance | multi-slice unit | PM | built 2026-11-02 | PM-0 | [plan](plans/projection-maintenance.md), [status](status/projection-maintenance.md), 4 Validation Packs |
| python-test-melting | unit |  | built 2026-10-27 |  | [plan](plans/python-test-melting.md), [status](status/python-test-melting.md) |
| rdf-sparql-patterns-remediation | plan |  | merged 2026-09-25 |  | [plan](plans/rdf-sparql-patterns-remediation.md), [status](status/rdf-sparql-patterns-remediation.md) |
| rdf-sparql-patterns-status | unit |  | built 2026-09-22 | RSP-1 | [status](status/rdf-sparql-patterns-status.md) |
| repository-topology-a77 | unit |  | merged 2026-09-20 |  | [status](status/repository-topology-a77.md), [review](review/repository-topology-a77-review.md) |
| spc-package-split | unit |  | merged 2026-09-20 |  | [status](status/spc-package-split.md) |
| studio-publication | multi-slice unit in four phases | PB | built 2026-10-31 | PB-1 | [plan](plans/studio-publication.md), [status](status/studio-publication.md) |
| studio-quality | multi-slice unit | SQ | built 2026-10-31 | SQ-1 | [plan](plans/studio-quality.md), [status](status/studio-quality.md) |
| studio-worker-liveness | multi-slice unit | WL | built 2026-11-06 | WL-0 | [plan](plans/studio-worker-liveness.md), [status](status/studio-worker-liveness.md) |
| surface-mork-unified-projection | unit |  | merged 2026-09-22 |  | [status](status/surface-mork-unified-projection.md) |
| surface-outstanding-items | unit |  | merged 2026-09-22 |  | [status](status/surface-outstanding-items.md) |
| temporal-binding-consumer-hardening | unit |  | built 2026-09-25 |  | [plan](plans/temporal-binding-consumer-hardening.md), [status](status/temporal-binding-consumer-hardening.md) |
| toolchain-jdk25-python314 | unit |  | merged 2026-09-23 |  | [plan](plans/toolchain-jdk25-python314.md), [status](status/toolchain-jdk25-python314.md) |
| v-rig | unit | VR | building 2026-11-07 | VR-1 | [plan](plans/v-rig.md), [status](status/v-rig.md) |
| validation-pause-handover | unit |  | dropped 2026-09-20 |  | [status](status/validation-pause-handover.md) |
| validation-status | unit |  | merged 2026-09-20 |  | [status](status/validation-status.md) |
| vocabulary-temporal-binding | unit |  | built 2026-09-25 | VTB-1 | [status](status/vocabulary-temporal-binding.md) |
| vyvid-migration | multi-slice unit | VM | building 2026-11-08 | VM-0 | [plan](plans/vyvid-migration.md), [status](status/vyvid-migration.md), [review](review/vyvid-migration-review.md), 9 Validation Packs |
| windows-portability | unit | XP | built 2026-11-07 | XP-0 | [plan](plans/windows-portability.md), [status](status/windows-portability.md) |
| word-authoring-poc | multi-slice unit | WA | built 2026-10-10 | WA-0 | [plan](plans/word-authoring-poc.md), [status](status/word-authoring-poc.md), 12 Validation Packs |
| work-board | multi-slice unit | WB | built 2026-11-04 | WB-0 | [plan](plans/work-board.md), [status](status/work-board.md) |
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
| AIR-0.1 | AIR-0.1 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-1.1 | set by R. No version bumps, no tags | applied-insurance-reference | merged 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-1.2 | set by R. Tags `applied-classification-v0.1.0`, `applied-classification-vocab-v0.1.0`, `insurance-common-v0.1.0`, `insurance-common-vocab-v0.1.0` | applied-insurance-reference | merged 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.0 | `insurance/common` and `insurance/peril` converted to literate READMEs, the extractor extended (nested `--layer` paths, `@output-file` on `turtle-vocab`), `prl:DocumentationShape` added (sha | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.1 | set by R: three shape defects fixed at verification. Tags `applied-insurance-peril-shapes-v0.1.0`, `insurance-peril-v0.1.0`, `insurance-peril-vocab-v0.1.0` | applied-insurance-reference | merged 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.2 | peril spec `0.4.0`→`0.5.0` (common import, four sub-property axioms), peril-vocab `0.4.0`→`0.5.0` (70 characteristic/companion concepts, four `voc:boundScheme` bindings). Lists amended beyon | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.3 | peril-vocab's `cause-N`, `cause-T` and `cause-E` regions filled: 90 N concepts, 71 T, 15 E, 176 in total, each with its characteristics, mechanisms, in-family cross-links and, for 16 concept | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.4 | peril-vocab's `cause-H` to `cause-L` regions and `cross-group-links` filled: 37 H concepts, 36 P, 17 C, 10 F, 11 L, bringing the cause scheme to 287 concepts in eight families. Eleven cross- | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.5 | brief written 2026-10-13 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.6 | `common-vocab` `0.5.0`→`0.6.0` (QUDT-aligned units across nine families, four exact conversions, ISO 4217 currencies on `icm-voc:Money`). New document `vocab/peril-intensity.ttl` (own ontolo | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-2.7 | brief written 2026-10-13 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-3.4 | brief written 2026-10-13, AIR-3.4-Q1 and Q2 decided 2026-10-14 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-3.5 | moved from R on 2026-10-13 (lanes §2). Brief written the same day | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.1 | new module `ontology/applied/insurance/exposure/` (`aeo:`), literate from the start: exposure set, location, legal entity, control, asset, interest, valuation, seven scheme contracts, nine p | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.2 | zones, pool participation, assessments and attribute values: six zone contracts, designation source/assessment kind/profile family contracts and schemes, value forms and spaces, and an attri | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.2a | TD-49 fixed, scope widened by the maintainer to every inverse-functional property of the module: eight properties made plain, `aeo:MembershipShape` withdrawn, `examples/versions.ttl` added.  | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.2b | **built on the formal-methods Track H branch `claude/nice-bohr-pmj43u` as AIR-66 (TD-66), to bring across** (see "Handover from formal-methods Track H" below): an exposure version is never e | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.3 | dependencies, peril metrics, metric comparisons and exposure units in the exposure module: spec, six schemes and contracts, two contracts with no reference scheme, four value spaces, nine sh | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.4 | `insurance/common` 0.5.0→0.6.0 (loss event, class of business, GLIDE key scheme) with importers re-pinned, and the exposure module's losses, cause chains with effective and defaulted charact | applied-insurance-reference | built 2026-11-02 |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.5 | brief written 2026-10-13 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-4.6 | brief written 2026-10-13 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.1 | `ctr:TermParameter ⊑ ins:Qualifier`, parameter kind scheme with governed admission (an unadmitted kind is carried but not evaluated) | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.2 | limit, retention, defence cost, claims basis, waiting, indemnity and extended reporting parameters | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.3 | aggregate, occurrence grouping, reinstatement, trigger, collateral, pool share, premium and declaration parameters | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.4 | term relations and bundle shapes per term function | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.5 | party role parameters and direction derivation over roles and the exposure relationship graph, with the D&O example | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.6 | defect catalogue as shapes | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.7 | route R2: compile one check family into Capacity runtime forms, parity suite against R1, no write-back | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.8 | insurance renderings of the policy scenarios of the CCS sketch §10 (the PKG rows: S10 to S14, S18 to S26, S28, S29, S33, S34, S37, S42 and the shared rows), as examples with expected decisio | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-5.9 | the LMA WIM profile in `applied/insurance/wording/` (CCS decision CC-D3): the four levels as element types, their containment rules as shapes, the LMA typing schemes and `applicableTo`. Open | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.1 | brief written 2026-10-13, AIR-6.1-Q1 decided 2026-10-14 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.10 | AIR-6.10 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.11 | AIR-6.11 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.12 | AIR-6.12 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.2 | AIR-6.2 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.3 | AIR-6.3 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.4 | AIR-6.4 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.5 | AIR-6.5 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.6 | AIR-6.6 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.7 | AIR-6.7 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.8 | AIR-6.8 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.9 | AIR-6.9 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W0 | AIR-6.W0 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W1 | the CRS v5.2 claims bordereau: representation scheme with field codes confirmed against Lloyd's user guide, mapping graph, spreadsheet-to-CSV conversion, source graph, golden fixtures we aut | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W2 | reconciliation rules as data: identity by keys, movements from snapshots with the inconsistency check (G1), statuses as the sender's assertions (G4), code lifting (G5), image differences (G2 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W3 | the bordereau's egress kit on the sidecar, on record time, with its lowering report and per-recipient minimisation. Milestone M8 | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W4 | ACORD `ClaimsNotificationAddRq` ingress and its response message, kept where WF-Q5 decides | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W5 | ISO 20022 `pain.001` egress from payment movements, `pain.002` and `camt.054` ingress as facts on movements | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W6 | HL7 FHIR `Claim` ingress and `ClaimResponse` egress for health claims | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-6.W7 | the S.19.01 xBRL-XML instance as a sidecar kit over AIR-6.11's cells | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.0 | examples first: one programme (a primary and two excess layers, one excess on two lines, a follow-form and a drop-down) placed on MRC-style contracts, with the layers as sections of one MRC, | applied-insurance-reference | planned | P7-Q1 to P7-Q3 answered | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.1 | the programme module, `ontology/applied/insurance/programme/`: programme, tower, layer, the instruments on a layer, lines with written and signed shares and a role, each line's formation sta | applied-insurance-reference | planned | AIR-7.0, P7-Q5, Ensemble ES-4 and ES-5, Ledger LG-2 and LG-Q3, CCS C9 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.10 | interim cover and policy intake: the concepts "interim cover" (altLabels "binder"@en-US, "policy binder"@en-US) and "binding authority" (altLabel "binder"@en-GB), each with a scope note nami | applied-insurance-reference | planned | AIR-7.1, Ensemble ES-9, CCS C16b | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.2 | market responses: the four kinds, commitment, precision and completeness, a response provisionally placed on a layer, the lifecycle as regimes, and a worked view of a programme's placed capa | applied-insurance-reference | planned | AIR-7.1, CCS HQ-1 decided, SPC for the choreography | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.3 | substrate: conditions over observed values (vehicles sketch §4.1, RV-1) | applied-insurance-reference | planned | AIR-7.0, an ADR | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.4 | substrate: allocation with conservation (vehicles sketch §4.2, RV-2), built as Ledger slice LG-4 | applied-insurance-reference | planned | AIR-7.0, Ledger LG-2 and LG-Q3 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.5 | the vehicle module (RV-3), a vehicle as an ensemble | applied-insurance-reference | planned | AIR-7.3, Ledger LG-4, Ensemble ES-6 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.6 | vehicles evaluated end to end (RV-4) | applied-insurance-reference | planned | AIR-7.5, CCS C12 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.7 | Capacity's future (P7-Q4), if the answer changes the module | applied-insurance-reference | planned | P7-Q4 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.8 | optional: a synthetic data generator for MORK whose ground truth targets the public applied modules (exposure, peril, programme) | applied-insurance-reference | planned | AIR-7.1 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-7.9 | the MRC module, `ontology/applied/insurance/mrc/` (P7-Q6): the unique market reference, the MRC's sections (risk details, information, security details with each insurer's or panel's own pag | applied-insurance-reference | planned | AIR-7.1, Ensemble ES-5 and ES-7 (which follows ES-6), P7-Q6 | docs/developer/status/applied-insurance-reference.md#machine-r |
| AIR-DT1 | the tests for slices built while testing is deferred, from AIR-4.2a. Test plans collected in the Phase 4 plan | applied-insurance-reference | planned |  | docs/developer/status/applied-insurance-reference.md#machine-r |
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
| CCS-7c | what terms are, and who they bind (split from CCS-7b) | computable-contract-substrate | merged 2026-10-27 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8 | values in stated meaning, Wording references by identity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8b | values in stated meaning, Wording references by identity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9a | amendments, assents and taking effect | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.0 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.1 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.2 | Eligibility sources, legal acts, additivity | computable-contract-substrate | merged 2026-10-10 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-6a.1 | untimed closures (ADR-A105): the model and reference semantics | computable-contract-substrate | tagged 2026-10-12 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-6a.2 | untimed closures (ADR-A105): the compilers (`executable-v0.7.0`) | computable-contract-substrate | tagged 2026-10-16 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.3 | set comparisons, aggregate bindings, the two kinds of deferral, hierarchical match over a named relation, as CCS-9b.3a, CCS-9b.3b and CCS-9b.3c | computable-contract-substrate | blocked | CCS-9b.3b | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.3a | set comparisons, law L18 (ADR-A145) | computable-contract-substrate | tagged 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.3b | aggregate bindings, with `qnt:Count` for existence and quorums by number | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.3c | hierarchical match over a named relation, no applicable binding Undetermined | computable-contract-substrate | tagged 2026-10-29 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9b.4 | qualifying rules | computable-contract-substrate | planned | CCS-9b.3b | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9d | materiality | computable-contract-substrate | planned | CCS-9b.4 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-9c | incorporation | computable-contract-substrate | planned | CCS-9d | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-8a | template library | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-16c | remove Party's shares | computable-contract-substrate | planned | CCS-9b.4 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-7a | regimes and gating, split from C7 | computable-contract-substrate | merged 2026-10-05 |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-12 | runtime evaluator | computable-contract-substrate | blocked | CCS-9c, LG-3, ES-3 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-13 | relation plans | computable-contract-substrate | blocked | CCS-9c, AIR-3.3, NRS-1 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-13a | design-time joint satisfiability: slot conditions by reasoner, the task NRS N3 reuses (deferred from CCS-5) | computable-contract-substrate | blocked | NRS-1 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-14 | neutral examples E1 to E4 | computable-contract-substrate | blocked | CCS-8a, CCS-9c, CCS-12 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-15 | neutral examples E5 to E8, and the scenario coverage test | computable-contract-substrate | blocked | CCS-14 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-16 | how-to guides and architecture documents | computable-contract-substrate | blocked | CCS-15 | docs/developer/status/computable-contract-substrate.md#slice-board |
| CCS-17 | handoff: insurance renderings and Open CBAA migration notes | computable-contract-substrate | blocked | CCS-16 | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-1 | HQ-1 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-10 | HQ-10 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-11 | HQ-11 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-12 | HQ-12 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-2 | HQ-2 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-3 | HQ-3 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-4 | HQ-4 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-5 | HQ-5 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-6 | HQ-6 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-7 | HQ-7 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-8 | HQ-8 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| HQ-9 | HQ-9 | computable-contract-substrate | planned |  | docs/developer/status/computable-contract-substrate.md#slice-board |
| ES-0 | examples first, as data the model must accept or refuse | ensemble | briefed 2026-10-21 | ADR-A130 accepted | docs/developer/status/ensemble.md#board |
| ES-1 | the layer, its README, ens:Ensemble, ens:Relation and endpoints | ensemble | briefed 2026-10-21 | ES-0 | docs/developer/status/ensemble.md#board |
| ES-2 | the Instrument hook, a measured value or evidence as a recorded fact | ensemble | planned | ES-1 | docs/developer/status/ensemble.md#board |
| ES-3 | K2 and K3, dependency and priority, evaluation units below the instrument | ensemble | planned | ES-2, Ledger LG-2 | docs/developer/status/ensemble.md#board |
| ES-4 | K6, shared resources, the derivation from the terms that draw on an account | ensemble | planned | ES-3, Ledger LG-2, LG-Q3, LG-Q4 | docs/developer/status/ensemble.md#board |
| ES-5 | K4, portions and shares | ensemble | planned | ES-3, LG-Q6 | docs/developer/status/ensemble.md#board |
| ES-6 | K5 and the ensemble's life, formation, membership by rule | ensemble | planned | ES-3, ES-Q5 | docs/developer/status/ensemble.md#board |
| ES-7 | K8, representation, authorities one per subject | ensemble | planned | ES-6, CCS C9's consent rules (HQ-5), the terms digest (evaluator plan EV-9) | docs/developer/status/ensemble.md#board |
| ES-8 | K7, contribution, by addendum to ADR-A130 | ensemble | planned | ES-4, Ledger LG-4 | docs/developer/status/ensemble.md#board |
| ES-9 | comparison between instruments, where one replaces or completes another | ensemble | planned | ES-2, CCS C16b | docs/developer/status/ensemble.md#board |
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
| FMC-4 | a design model of ADR-A130, the Ensemble, in Alloy | formal-methods-track-c | built 2026-10-27 |  | docs/developer/status/formal-methods-track-c.md#slices |
| FME-1.0 | home, generation tooling | formal-methods-track-e | built 2026-10-09 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.1 | the kernel, for real | formal-methods-track-e | built 2026-10-06 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.2 | rounding and residual theorem | formal-methods-track-e | dropped 2026-10-07 | track B's B4, which waits on CCS's C12 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.3 | binding resolution | formal-methods-track-e | planned | track C's C2 is **done**, but the overlap-rule decision it surfaced, and the Vocabulary ADR IMA-D4a names, are not yet made/drafted (track C's own status) | docs/developer/status/formal-methods-track-e.md#slices |
| FME-1.4 | harden the gate and the kernel theory | formal-methods-track-e | built 2026-10-09 |  | docs/developer/status/formal-methods-track-e.md#slices |
| FME-2 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-3 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-4 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FME-5 | to FME-5 | formal-methods-track-e | planned | E1 | docs/developer/status/formal-methods-track-e.md#slices |
| FMH-2.12 | the rows replace, selected by capability, LR-Q1 to LR-Q4 | formal-methods-track-h | built 2026-11-01 |  | docs/developer/status/formal-methods-track-h.md#slices |
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
| FMH-2.6b | event slots, patch-log half held, H-D33 | formal-methods-track-h | verified 2026-10-14 | the merge | docs/developer/status/formal-methods-track-h.md#slices |
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
| FMH-1.2 | FMH-1.2 | formal-methods-track-h | built 2026-10-09 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6e | FMH-2.6e | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6f | FMH-2.6f | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.6g | FMH-2.6g | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.8a | FMH-2.8a | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-2.8b | FMH-2.8b | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FMH-W65 | FMH-W65 | formal-methods-track-h | built 2026-10-23 |  | docs/developer/status/formal-methods-track-h.md#slices |
| FM-D0 | environments | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D1 | brief | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D2 | Rocq track | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D3 | Isabelle track | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-D4 | report | formal-methods | built 2026-10-10 |  | docs/developer/status/formal-methods.md#track-d |
| FM-PF1 | fixes | formal-methods | built 2026-10-07 |  | docs/developer/status/formal-methods.md#track-d |
| FM-0 | track D, the prover spike, the pack that covers FM-D0 to FM-D4 | formal-methods | built 2026-10-06 |  | docs/developer/status/formal-methods.md#track-d |
| FM-CG1 | code generation from the layer models, `spikes/isabelle-layers`: thirteen proved layer theories, two code-generation theories, Haskell, SML and Scala exports, Eligibility's decision table ex | formal-methods | merged 2026-11-02 |  | docs/developer/status/formal-methods.md#track-d |
| FM-CG2 | the generated Haskell as a differential oracle beside the Python reference, under the four conditions the spike's README states | formal-methods | planned | PDD-19 | docs/developer/status/formal-methods.md#track-d |
| GH-0 | GH-0 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-1 | GH-1 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-2 | GH-2 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-3 | GH-3 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-4 | GH-4 | git-hooks | built 2026-10-24 |  | docs/developer/status/git-hooks.md#position |
| GH-5 | test suites leave the hooks: the studio's browser gate runs by convention before a merge, and a hook runs quick static checks only | git-hooks | built 2026-11-03 |  | docs/developer/status/git-hooks.md#position |
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
| OD-ELC1 | composition operation | improved-ontology-documentation | verified 2026-10-19 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-MC1 | migration check labels | improved-ontology-documentation | verified 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-VER1 | one release for the substrate | improved-ontology-documentation | verified 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-DOC2b | working documents out of published pages | improved-ontology-documentation | built 2026-10-20 |  | docs/developer/status/improved-ontology-documentation.md#slices |
| OD-REL1 | first release, 0.18.0 | improved-ontology-documentation | verified 2026-10-20 | the tags, on `main` after the merge | docs/developer/status/improved-ontology-documentation.md#slices |
| IMA-0.1 | engagement brief | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.2 | licence and publication record | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.3 | ADR, profile | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.4 | ADR, bridge tooling and kits | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.5 | ADR, transclusion | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.6 | ADR, inline parts | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.8 | ADR, assembly interface | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-0.7 | alignment edits | insurml-alignment | planned 2026-10-05 |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-1.1 | module skeleton, element type scheme, scheme binding in an insurance binding scope, key schemes for identifiers and LWR codes | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-1.2 | containment shapes generated from InsurML's rules held as data, builder properties | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-1.3 | alignment document, the collision table as fixtures, clean-room component library | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-2.1 | lift kit: XSLT 3.0 normalisation, emission, minted IRIs, identities and keys, provenance | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-2.2 | lower kit: component files, manifests, derived variables for richer conditions | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-2.3 | fidelity table as tests, golden round trips, the MORK record of the structure mapping | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-3.1 | transclusion, law W8, W3 and W5 read through transclusions | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-3.2 | inline parts, W2's fourth form | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-3.3 | references to a persistent identity with display text: **moved to CCS C8b** (2026-10-06), since CCS C8's stated meaning names variables by identity and the text should too. This epic's lift  | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.1 | assembly models, the record's new terms (`wrd:assembledUnder`, resolution and numbering records), diagnostics for each stage, laws WA-1 to WA-7 | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.1a | assembler interface and the baseline adapter: Eligibility-decided inclusion with three values and declared treatments, alternatives, transclusions, resolution records | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.1b | InsurML assembly model in the profile, and the InsurML adapter over the lifted graph | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.2 | parity suite: baseline against InsurML adapter, and InsurML adapter against InsurML's processor, over every fixture configuration | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.3 | renderer and numbering, with the rule chosen for Q32 | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.4 | verification passes: references in every configuration, dependency acyclicity. Alternatives for every condition kind join when CCS C13a lands | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| IMA-4.5 | optimisation passes: question plans, dead components, specialisation | insurml-alignment | planned |  | docs/developer/status/insurml-alignment.md#phase-0 |
| TUT-0 | the page, its layout, the home page links and `check:tutorial-snippets` | lattice-tutorial | verified 2026-10-14 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-1 | chapters 0 to 3 | lattice-tutorial | built 2026-10-15 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-2 | chapters 4 to 6 | lattice-tutorial | built 2026-10-15 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-3 | chapters 7 to 9 | lattice-tutorial | built 2026-10-16 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-4 | chapters 10 to 13 | lattice-tutorial | built 2026-10-16 | the maintainer's end-to-end reading (TUT4-05) | docs/developer/status/lattice-tutorial.md#position |
| TUT-5 | the tutorial refreshed onto `main`: excerpts, the site's rules, Ledger in chapter 10. Validation Pack | lattice-tutorial | built 2026-11-05 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-6 | the Configuration Studio guide's groundwork: the studio run, the routes in and out tested, the page, layout and site section, the worked sample and its test, the screenshot task (plan §9) | lattice-tutorial | building 2026-11-06 |  | docs/developer/status/lattice-tutorial.md#position |
| TUT-7 | the guide's modules 1 to 4 | lattice-tutorial | briefed 2026-11-06 | TUT-6 | docs/developer/status/lattice-tutorial.md#position |
| TUT-8 | the guide's modules 5, 6 and 11 | lattice-tutorial | briefed 2026-11-06 | TUT-6 | docs/developer/status/lattice-tutorial.md#position |
| TUT-9 | the guide's modules 7 to 10 | lattice-tutorial | briefed 2026-11-06 | TUT-6 | docs/developer/status/lattice-tutorial.md#position |
| TUT-10 | the guide's modules 12, 13 and the quick reference | lattice-tutorial | briefed 2026-11-06 | TUT-6 | docs/developer/status/lattice-tutorial.md#position |
| LG-0 | examples, as data the model must accept or refuse, from licensing, lending and grants | ledger | merged 2026-10-27 |  | docs/developer/status/ledger.md#board |
| LG-1 | the configuration document, the README in ADR-A126's layout with account definitions, the tree, owner kinds and the merge rule scheme | ledger | merged 2026-10-27 |  | docs/developer/status/ledger.md#board |
| LG-2 | the runtime document, postings, balance records, their keys and PROV, the two phases at one position | ledger | built 2026-11-08 |  | docs/developer/status/ledger.md#board |
| LG-3 | Behaviour's migration, the import, effects onto accounts, threshold regimes over a balance | ledger | planned | LG-2 | docs/developer/status/ledger.md#board |
| LG-4 | allocation with conservation, one amount split into postings by a merge rule, the conservation law as a shape | ledger | planned | LG-3 | docs/developer/status/ledger.md#board |
| LG-5 | a benchmark, a generated corpus of account trees and draws at the performance section's volumes, part built ahead of LG-4 | ledger | blocked | LG-4 | docs/developer/status/ledger.md#board |
| LG-6 | the fold investigation of the ledger-folds-and-stores sketch, probes P1 to P6, arms A, B, B0 and C, sharing LG-5's corpus | ledger | planned | LG-5 | docs/developer/status/ledger.md#board |
| LG-7 | the ledger laws mechanised in `tools/proofs/ledger/`, ahead of LG-2 | ledger | built 2026-11-08 |  | docs/developer/status/ledger.md#board |
| MSC-1 | `platform/sparql-testkit`, `tools/testing/jena`, `tools/testing/sparql_probes` with the aggregate matrix executed on Jena (352 cells as recorded), `check:conformance`, CAP-91 to CAP-94, an A | multi-store-conformance | merged 2026-10-29 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-2 | Jena in the persistence engines, `check:persistence-conformance` on rdflib, Oxigraph and Jena (4727 passed), nine Jena failures triaged into TSD-50 to TSD-53 with expectations per engine, on | multi-store-conformance | merged 2026-10-29 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-3 | Jena in the compilers' engines, conformance per engine for the compilers and Eligibility's reference tests, all passing on Jena first time. TSD-60, TSD-61 (rdflib departures), TD-105 (the pr | multi-store-conformance | merged 2026-10-29 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-4 | `benchmark/persistence-store-probes`, P3 out of `check:persistence`, TSD-42 rerun with rdflib, STD-290, CAP-97. Jena's column added in MSC-5 | multi-store-conformance | merged 2026-10-29 |  | docs/developer/status/multi-store-conformance.md#position |
| MSC-5 | TSD-42 and TSD-43 on Jena, TSD-Q12, Q18, Q19 narrowed to Fuseki, Q21's `MAX` left to the specification's authors, TSD-54 to TSD-57, `sparql-constraint-query-cost` runs Jena, thirteen upstrea | multi-store-conformance | merged 2026-10-29 |  | docs/developer/status/multi-store-conformance.md#position |
| NRS-2 | Declare the importable rule-body fragment (A-109), revised for stratified state reads (ADR-A104 decision 15) | normative-rule-substrate | blocked | D1, NQ-2 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-4 | Deontic extension of Instrument (A-104, R1) | normative-rule-substrate | dropped 2026-09-30 | CCS C1, C6 to C9 | docs/developer/status/normative-rule-substrate.md#slice-board |
| NRS-1 | Condition composition acyclicity (R4). CCS-13 and CCS-13a wait on it, and CCS does the work (NQ-2) | normative-rule-substrate | blocked | AIR-3.3 | docs/developer/status/normative-rule-substrate.md#slice-board |
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
| DR-1 | the vocabulary, the delta builders, the kind and the selection | persistence-delta-replace | built 2026-11-02 | the review | docs/developer/status/persistence-delta-replace.md#slices |
| DR-2 | both caller libraries' checks and vectors, the caller obligations as standards | persistence-delta-replace | built 2026-11-02 | the review | docs/developer/status/persistence-delta-replace.md#slices |
| DR-3 | the studio's writer on the generated delta replace | persistence-delta-replace | building 2026-11-01 |  | docs/developer/status/persistence-delta-replace.md#slices |
| DR-4 | `replace-whole`, `load-whole` and the state digest, carried over from the studio line | persistence-delta-replace | built 2026-11-02 | the review | docs/developer/status/persistence-delta-replace.md#slices |
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
| PM-0 | the rename of PM-Q8 across the studio | projection-maintenance | built 2026-11-01 |  | docs/developer/status/projection-maintenance.md#slices |
| PM-1 | the surface backend, a clear and a fill for each promotion | projection-maintenance | built 2026-11-01 |  | docs/developer/status/projection-maintenance.md#slices |
| PM-2 | the writer keeps each source's promotions in its own request | projection-maintenance | built 2026-11-01 |  | docs/developer/status/projection-maintenance.md#slices |
| PM-3 | CloudEvents for the writers' and workers' job updates | projection-maintenance | built 2026-11-01 |  | docs/developer/status/projection-maintenance.md#slices |
| PM-3a | the probes of the broker's Web MQTT and HTTP auth backend | projection-maintenance | built 2026-11-02 |  | docs/developer/status/projection-maintenance.md#slices |
| PM-3b | PM-Q20 (d), the broker's checks of identity and the relay | projection-maintenance | built 2026-11-02 | the review | docs/developer/status/projection-maintenance.md#slices |
| PM-3c | the proxy run of PM-Q22 in the browser gate | projection-maintenance | planned | PM-Q22 | docs/developer/status/projection-maintenance.md#slices |
| PM-4 | the tier 2 maintainer | projection-maintenance | planned | PM-Q13 to PM-Q17 | docs/developer/status/projection-maintenance.md#slices |
| RSP-1 | Core patterns | rdf-sparql-patterns-status | built 2026-09-22 |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| RSP-2 | Substrate and compiler | rdf-sparql-patterns-status | built 2026-09-22 |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| RSP-3 | Housekeeping first cut | rdf-sparql-patterns-status | planned |  | docs/developer/status/rdf-sparql-patterns-status.md#slice-status |
| PB-1 | a job's input and its findings | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-2 | the `Authenticator` seam, `local` and `oidc` | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-3 | a workspace's owner and mode | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-4 | the `cst:` publication terms and the `publish` job | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-5 | the registry's read API and browser | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-6 | a workspace's dependencies, followed or pinned | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-7 | fenced imports stored once by digest | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-8 | artefacts naming their sources, the bundle export | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-9 | vocabulary bindings that select a published edition | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-10 | a brief, the working store as persistence profiles | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-11 | the Java caller library | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-12 | the studio's persistence profile | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-13 | the operations layer, `StudioOperations` | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-14 | the writer's workspace commands on PB-13 | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-15 | the registry on PB-13 | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-16 | the migration of a store written before phase D | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| PB-17 | the projections of ADR-A149 decision 14 | studio-publication | built 2026-10-31 |  | docs/developer/status/studio-publication.md#slices |
| SQ-1 | the harness, a topology from a declared configuration | studio-quality | built 2026-10-31 |  | docs/developer/status/studio-quality.md#slices |
| SQ-2 | reports in git, the compare task, the `studio-api` scenario | studio-quality | built 2026-10-31 |  | docs/developer/status/studio-quality.md#slices |
| SQ-3 | component benchmarks | studio-quality | planned |  | docs/developer/status/studio-quality.md#slices |
| SQ-4 | the model and the Hypothesis state machine | studio-quality | planned |  | docs/developer/status/studio-quality.md#slices |
| SQ-5 | a Jepsen test against the Compose topology | studio-quality | planned |  | docs/developer/status/studio-quality.md#slices |
| SQ-6 | Locust load runs with reports | studio-quality | planned |  | docs/developer/status/studio-quality.md#slices |
| WL-0 | the plan, this record, the board | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-1 | reproductions that fail today, the view's fate on remount, a worker's idle memory | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-2 | the job on its own thread, the publisher and acknowledgement across threads | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-3 | the check on delivery, a job that cannot run marked `Failed`, each job logged | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-4 | the held result, reconnecting with a backoff | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-5 | short jobs past long ones | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-6 | a view that attaches to its running job, no stacked validations | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-7 | the status warning, `studio:status`, the operations guide, the ADR addendum | studio-worker-liveness | built 2026-11-05 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-8 | a run that leaves no process behind when its test process is killed | studio-worker-liveness | built 2026-11-06 |  | docs/developer/status/studio-worker-liveness.md#position |
| WL-9 | a late `Failed` never replaces a `Succeeded` | studio-worker-liveness | built 2026-11-06 |  | docs/developer/status/studio-worker-liveness.md#position |
| VR-1 | the module `ontology/v-rig/`, its vocabulary, shapes, Proposed ADR and catalogue entry | v-rig | building 2026-11-07 |  | docs/developer/status/v-rig.md#board |
| VR-2 | the synthetic mini-rig, then the lifter with the declared and blind views | v-rig | planned | VR-1 | docs/developer/status/v-rig.md#board |
| VR-3 | the tracked mapping scheme and the extension seam | v-rig | planned | VR-2 | docs/developer/status/v-rig.md#board |
| VR-4 | P1, the layer graph against shapes, reasoner and competency queries | v-rig | planned | VR-3 | docs/developer/status/v-rig.md#board |
| VR-5 | P2 and P3, the generated theory and the test vectors | v-rig | planned | VR-3 | docs/developer/status/v-rig.md#board |
| VR-6 | P4, findings as RDF with stable ids and the report rendered from them | v-rig | planned | VR-4 | docs/developer/status/v-rig.md#board |
| VR-7 | the seam for a read case | v-rig | planned | VR-2 | docs/developer/status/v-rig.md#board |
| VTB-1 | ADR-A85 proposal, architecture mirror, fixture/test/traceability skeleton | vocabulary-temporal-binding | built 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-2 | 12 fixtures (11 positive/negative + 1 consumer), `structural.ttl`, `constraints.ttl` | vocabulary-temporal-binding | verified 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-3 | `tools/vocabulary` resolver + determinism/precedence/conflict tests | vocabulary-temporal-binding | verified 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VTB-4 | Surface resolves scoped bindings via `vocabulary.resolve` (`tools/surface/src/surface/compile.py`), Eligibility's `HierarchyWellFoundednessShape` checks every scheme a contract could resolve | vocabulary-temporal-binding | built 2026-09-25 |  | docs/developer/status/vocabulary-temporal-binding.md#planned-slices |
| VM-0 | the sketch rewritten, the plan, this record, the INDEX.md region | vyvid-migration | verified 2026-11-06 |  | docs/developer/status/vyvid-migration.md#position |
| VM-1 | the binding, `bootstrap:vyvid`, the comparison | vyvid-migration | verified 2026-11-06 |  | docs/developer/status/vyvid-migration.md#position |
| VM-2 | the index tasks and hooks over `vyd`, AGENTS.md's index section, the addenda | vyvid-migration | verified 2026-11-06 |  | docs/developer/status/vyvid-migration.md#position |
| VM-3 | the quanta and owners extractor, the tests against Вивід, the deletions | vyvid-migration | verified 2026-11-05 |  | docs/developer/status/vyvid-migration.md#position |
| VM-4 | the board tasks and the `work` check over `vyd`, the old tools removed | vyvid-migration | verified 2026-11-05 |  | docs/developer/status/vyvid-migration.md#position |
| VM-5 | the fifteen composed skills, the coverage proven, the citations and pointers | vyvid-migration | verified 2026-11-05 |  | docs/developer/status/vyvid-migration.md#position |
| VM-6 | the moves, the page at the old path, TD-2 cleared | vyvid-migration | verified 2026-11-05 |  | docs/developer/status/vyvid-migration.md#position |
| VM-7 | cloud sessions: the pin at `v0.2.14`, the setup script and its pasted lines, the hook | vyvid-migration | verified 2026-11-06 |  | docs/developer/status/vyvid-migration.md#position |
| VM-8 | cloud setup within its limit: the index first, the rest if time allows, a hook finishes what was skipped | vyvid-migration | verified 2026-11-06 |  | docs/developer/status/vyvid-migration.md#position |
| VM-9 | the quanta by Вивід's own kind, the pin at v0.2.23 | vyvid-migration | building 2026-11-08 |  | docs/developer/status/vyvid-migration.md#position |
| XP-0 | plan, status record, STD-322, STD-323, TD-153 | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-1 | the `mise` skill split between the domain and LATTICE | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-2 | the small fixes: a task dependency, line endings, junctions, the hook's interpreter | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-3 | skips for a missing capability, and `LATTICE_REQUIRE_ALL` | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-4 | `check:vyvid-binding` under Git Bash | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-5 | the shell tasks as Python scripts | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-6 | the portability check | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
| XP-7 | ratification, `skills:link` by junction or copy, the directory links page | windows-portability | built 2026-11-07 |  | docs/developer/status/windows-portability.md#position |
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
| WB-4 | the `work` check and the post-merge regeneration | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-5 | AGENTS.md, the skills, the standards, the ADR | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-6 | `work:here` | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-7 | the branches marked or deleted | work-board | briefed 2026-11-02 | the merge of this branch into `main` | docs/developer/status/work-board.md#position |
| WB-8 | a register collision dated to the second, and the check naming the row that keeps the number | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-9 | `work:rename` keeps an exception whose old spelling is still mentioned | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-10 | a unit's state joined across branches, rolled up from its board, and the Status word held to the roll-up | work-board | built 2026-11-02 |  | docs/developer/status/work-board.md#position |
| WB-11 | a branch whose boards are not on the grammar is read as such, never as moving every old id | work-board | built 2026-11-04 |  | docs/developer/status/work-board.md#position |

<!-- END GENERATED work-board -->
