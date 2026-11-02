<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE roadmap

**As of** 2026-10-21. **Read from** `main` at `a19e6dd` and every branch on the remote with commits not yet on `main`.

**What this is.** One view across every epic, unit and branch: what is done, what is in flight, what waits on what, and what the maintainer is asked to do next. It summarises and links. It decides nothing. The status record of each unit stays its one authoritative live state (skill `lattice-lifecycle`). Where this roadmap and a status record disagree, the status record is right and this page is stale.

**How it was built.** From the status records and plans under `docs/developer/`, the ADR catalogue, the remote's branches and its release tags. A unit's state on an unmerged branch is reported with the branch named, since `main` does not have it yet.

## Contents

1. [The programme at a glance](#1-the-programme-at-a-glance)
2. [How the epics depend on one another](#2-how-the-epics-depend-on-one-another)
3. [The layers, now and proposed](#3-the-layers-now-and-proposed)
4. [Active epics](#4-active-epics)
5. [Smaller units](#5-smaller-units)
6. [The platform programme](#6-the-platform-programme)
7. [Branches](#7-branches)
8. [The critical path](#8-the-critical-path)
9. [Decisions waiting](#9-decisions-waiting)
10. [The maintainer's queue](#10-the-maintainers-queue)
11. [Completed units](#11-completed-units)
12. [Observations](#12-observations)

## 1. The programme at a glance

<!-- BEGIN GENERATED work-board-glance. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Built from the status records on 12 branches, the units' own state from this tree, the newest board day 2026-11-02.

| Unit | Kind | State | Next | Slices | Moved on |
|---|---|---|---|---|---|
| [applied-insurance-reference](plans/applied-insurance-reference.md) | epic | planned | AIR-3.3 | 55 planned, 10 built, 5 merged, 1 ? | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [applied-ontology-readiness](plans/applied-ontology-readiness.md) | unit | built 2026-09-25 | AOR-1 | 18 built |  |
| [computable-contract-substrate](plans/computable-contract-substrate.md) | multi-slice unit | verified 2026-10-29 | CCS-0 | 35 merged, 15 planned, 7 blocked, 6 ?, 5 briefed, 3 verified, 2 built | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [documentation-link-repair](plans/documentation-link-repair.md) | unit | planned |  | no board |  |
| [eligibility-compiler](plans/eligibility-compiler.md) | unit | built 2026-09-25 |  | no board |  |
| [formal-methods-track-b](plans/formal-methods-track-b.md) | phase | built 2026-10-09 | FMB-1 | 7 ?, 5 built, 1 planned, 1 building | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [formal-methods-track-c](plans/formal-methods-track-c.md) | phase | built 2026-10-08 | FMC-1 | 6 ?, 3 built, 3 planned | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [formal-methods-track-e](plans/formal-methods-track-e.md) | phase | built 2026-10-09 | FME-1.0 | 6 ?, 5 planned, 3 built, 1 dropped | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [formal-methods-track-h](plans/formal-methods-track-h.md) | phase | verified 2026-10-09 | FMH-2.12 | 32 built, 31 ?, 15 merged, 14 planned, 5 verified, 2 briefed, 1 building | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [formal-methods](plans/formal-methods.md) | epic | built 2026-10-06 | FM-D0 | 8 built, 6 ? | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [git-hooks](plans/git-hooks.md) | unit | built 2026-10-24 | GH-0 | 5 built |  |
| [identity-minting](plans/identity-minting.md) | unit | built 2026-09-24 | IM-0 | 5 ?, 4 built, 1 planned | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [improved-ontology-documentation](plans/improved-ontology-documentation.md) | unit | verified 2026-10-17 | OD-0 | 13 built, 12 ?, 10 planned, 10 verified, 1 merged | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio |
| [insurml-alignment](plans/insurml-alignment.md) | epic | planned | IMA-0.1 | 24 planned |  |
| knowledge-index | unit | building 2026-10-26 |  | no board |  |
| [ledger](plans/ledger.md) | unit | building 2026-10-29 | LG-0 | 3 built, 3 planned |  |
| [mork-transforms](plans/mork-transforms.md) | multi-slice unit | built 2026-10-30 |  | no board |  |
| [multi-store-conformance](plans/multi-store-conformance.md) | unit | built 2026-10-27 | MSC-1 | 5 built |  |
| [normative-rule-substrate](plans/normative-rule-substrate.md) | multi-slice unit | blocked | NRS-2 | 13 ?, 7 blocked, 4 planned, 2 dropped | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [ontology-remediation](plans/ontology-remediation.md) | phase | built 2026-10-28 | OR-0 | 21 built |  |
| [ontology-semantic-versioning](plans/ontology-semantic-versioning.md) | unit | built 2026-09-25 |  | no board |  |
| [persistence-compiler-iri-sync](plans/persistence-compiler-iri-sync.md) | unit | built 2026-09-23 | PCI-1 | 7 ?, 6 built | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, persistence-mbt, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [persistence-delta-replace](plans/persistence-delta-replace.md) | multi-slice unit | built 2026-11-02 | DR-1 | 3 built, 1 ? | claude/persistence-delta-replace, realign/config-authoring-studio |
| phase-0-status | unit | built 2026-09-23 | PLT-0.1.1 | 16 ?, 13 built, 3 planned | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, persistence-mbt, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| phase-1-status | unit | blocked 2026-09-22 |  | no board |  |
| phase-2-status | unit | planned |  | no board |  |
| phase-3-status | unit | planned |  | no board |  |
| phase-4-status | unit | planned |  | no board |  |
| [projection-maintenance](plans/projection-maintenance.md) | multi-slice unit | building 2026-11-01 | PM-0 | no board |  |
| [python-test-melting](plans/python-test-melting.md) | unit | built 2026-10-27 |  | no board |  |
| rdf-sparql-patterns-status | unit | built 2026-09-22 | RSP-1 | 3 ?, 2 built, 1 planned | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, persistence-mbt, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [studio-publication](plans/studio-publication.md) | multi-slice unit in four phases | built 2026-10-31 | PB-1 | no board |  |
| [studio-quality](plans/studio-quality.md) | multi-slice unit | building 2026-10-31 | SQ-1 | no board |  |
| [temporal-binding-consumer-hardening](plans/temporal-binding-consumer-hardening.md) | unit | built 2026-09-25 |  | no board |  |
| vocabulary-temporal-binding | unit | built 2026-09-25 | VTB-1 | 4 ?, 2 built, 2 verified | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [word-authoring-poc](plans/word-authoring-poc.md) | multi-slice unit | built 2026-10-02 | WA-0 | 13 built, 13 ? | ccs-trunk, claude/persistence-delta-replace, claude/persistence-linear-replace, config_studio_GD, docs/placement-vehicles-structure, fml/isabelle-layers, realign/config-authoring-studio, spikes/pol-map, tutorial/guide |
| [work-board](plans/work-board.md) | multi-slice unit | built 2026-11-02 | WB-0 | 7 built, 1 briefed |  |
| [xslt-sidecar](plans/xslt-sidecar.md) | multi-slice unit | planned |  | no board |  |

One chart per epic, or per unit outside an epic with five dated slices or more, from the first day it has to the newest, every dated slice in the state its board gives.

```mermaid
flowchart LR
    K1["building"]:::active --- K2["built or verified"]:::open --- K3["merged or tagged"]:::done --- K4["blocked"]:::crit
    classDef active fill:#4e9af1,stroke:#1f5fbf,color:#000
    classDef open fill:#f2c14e,stroke:#b8860b,color:#000
    classDef done fill:#8fcf8f,stroke:#2f7d32,color:#000
    classDef crit fill:#f28b82,stroke:#b23a30,color:#000
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title The applied-insurance-reference epic
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section applied-insurance-reference
    AIR-1.1 set by R. No version bumps no :done, air11, 2026-11-02, 2026-11-03
    AIR-1.2 set by R. Tags applied-classi :done, air12, 2026-11-02, 2026-11-03
    AIR-2.0 insurance common and insura :air20, 2026-11-02, 2026-11-03
    AIR-2.1 set by R three shape defects :done, air21, 2026-11-02, 2026-11-03
    AIR-2.2 peril spec 0.4.0 0.5.0 co :air22, 2026-11-02, 2026-11-03
    AIR-2.3 peril-vocab cause-N caus :air23, 2026-11-02, 2026-11-03
    AIR-2.4 peril-vocab cause-H to ca :air24, 2026-11-02, 2026-11-03
    AIR-2.6 common-vocab 0.5.0 0.6.0 :air26, 2026-11-02, 2026-11-03
    AIR-3.1 :done, air31, 2026-10-14, 2026-10-15
    AIR-3.2 :done, air32, 2026-10-14, 2026-10-15
    AIR-4.1 new module ontology applied i :air41, 2026-11-02, 2026-11-03
    AIR-4.2 zones pool participation ass :air42, 2026-11-02, 2026-11-03
    AIR-4.2a TD-49 fixed scope widened by :air42a, 2026-11-02, 2026-11-03
    AIR-4.3 dependencies peril metrics m :air43, 2026-11-02, 2026-11-03
    AIR-4.4 insurance common 0.5.0 0.6.0 :air44, 2026-11-02, 2026-11-03
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title The formal-methods epic
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section formal-methods
    FM-0 :fm0, 2026-10-06, 2026-10-07
    FM-4 :fm4, 2026-10-27, 2026-10-28
    FM-D0 environments :fmd0, 2026-10-06, 2026-10-07
    FM-D1 brief :fmd1, 2026-10-06, 2026-10-07
    FM-D2 Rocq track :fmd2, 2026-10-06, 2026-10-07
    FM-D3 Isabelle track :fmd3, 2026-10-06, 2026-10-07
    FM-D4 report :fmd4, 2026-10-10, 2026-10-11
    FM-PF1 fixes :fmpf1, 2026-10-07, 2026-10-08
    section formal-methods-track-b
    FMB-1 kernel and denotation :fmb1, 2026-10-09, 2026-10-10
    FMB-2 differential tests against the :fmb2, 2026-10-09, 2026-10-10
    FMB-2.1 harden the differential harnes :fmb21, 2026-10-09, 2026-10-10
    FMB-2.2 verify fix the scheme-less hie :fmb22, 2026-10-09, 2026-10-10
    FMB-3 Surface regeneration propert :fmb3, 2026-10-09, 2026-10-10
    FMB-5 measured mutation score :active, fmb5, 2026-10-09, 2026-10-10
    section formal-methods-track-c
    FMC-1 Alloy skeleton :fmc1, 2026-10-08, 2026-10-09
    FMC-2 scheme composition :fmc2, 2026-10-07, 2026-10-08
    FMC-2.1 well-formedness facts re-run :fmc21, 2026-10-08, 2026-10-09
    FMC-2.2 model the composed scheme dec :fmc22, 2026-10-08, 2026-10-09
    FMC-2.3 model ADR-A116 own rule ag :fmc23, 2026-10-08, 2026-10-09
    section formal-methods-track-e
    FME-1.0 home generation tooling :fme10, 2026-10-09, 2026-10-10
    FME-1.1 the kernel for real :fme11, 2026-10-06, 2026-10-07
    FME-1.2 rounding and residual theorem :done, fme12, 2026-10-07, 2026-10-08
    FME-1.4 harden the gate and the kernel :fme14, 2026-10-09, 2026-10-10
    section formal-methods-track-h
    FMH-1.1 prefix antichain and overlap c :fmh11, 2026-10-09, 2026-10-10
    FMH-1.2 :fmh12, 2026-10-09, 2026-10-10
    FMH-1.2a witness harness audit witness :fmh12a, 2026-10-09, 2026-10-10
    FMH-1.2b witnesses for the refusals and :fmh12b, 2026-10-09, 2026-10-10
    FMH-1.2c witnesses for the 13 remaining :fmh12c, 2026-10-09, 2026-10-10
    FMH-1.2d refuse a multi-valued single-v :done, fmh12d, 2026-10-10, 2026-10-11
    FMH-1.3 static template checks S-3 and :done, fmh13, 2026-10-10, 2026-10-11
    FMH-1.4a refuse a composite boundary wi :done, fmh14a, 2026-10-10, 2026-10-11
    FMH-1.4b the declaration implementation :done, fmh14b, 2026-10-10, 2026-10-11
    FMH-1.4c a declaration the compiler can :done, fmh14c, 2026-10-10, 2026-10-11
    FMH-1.5 stable labels :done, fmh15, 2026-10-10, 2026-10-11
    FMH-2.0 ADR-A123 :fmh20, 2026-10-10, 2026-10-11
    FMH-2.1 the typed IR and its renderer :fmh21, 2026-10-12, 2026-10-13
    FMH-2.11a the Persistence README as a li :fmh211a, 2026-10-21, 2026-10-22
    FMH-2.11b the narrative the pictures t :fmh211b, 2026-10-21, 2026-10-22
    FMH-2.2 equivalence harness bootstra :fmh22, 2026-10-12, 2026-10-13
    FMH-2.3 named-graph row writers :fmh23, 2026-10-12, 2026-10-13
    FMH-2.4a the composite ports :fmh24a, 2026-10-13, 2026-10-14
    FMH-2.4b Oxigraph probes benchmark :fmh24b, 2026-10-13, 2026-10-14
    FMH-2.5 key claims audits guard D t :fmh25, 2026-10-23, 2026-10-24
    FMH-2.6 expected compiled profiles pa :fmh26, 2026-10-13, 2026-10-14
    FMH-2.6b event slots patch-log half he :active, fmh26b, 2026-10-14, 2026-10-15
    FMH-2.6c write disciplines :fmh26c, 2026-10-20, 2026-10-21
    FMH-2.6d patch log for in-place familie :fmh26d, 2026-10-20, 2026-10-21
    FMH-2.6e :fmh26e, 2026-10-23, 2026-10-24
    FMH-2.6f :fmh26f, 2026-10-23, 2026-10-24
    FMH-2.6g :fmh26g, 2026-10-23, 2026-10-24
    FMH-2.8a :fmh28a, 2026-10-23, 2026-10-24
    FMH-2.8b :fmh28b, 2026-10-23, 2026-10-24
    FMH-2.8c edges once faster members :fmh28c, 2026-10-20, 2026-10-21
    FMH-2.9 Mustache retired D-12 a go :fmh29, 2026-10-21, 2026-10-22
    FMH-HO0 correct the ownership note and :done, fmhho0, 2026-10-10, 2026-10-11
    FMH-HO1 composite replace payload to :done, fmhho1, 2026-10-10, 2026-10-11
    FMH-HO2 draft ADR-A122 Proposed :fmhho2, 2026-10-10, 2026-10-11
    FMH-HO3 dal vocabulary 0.3.0 dal :done, fmhho3, 2026-10-10, 2026-10-11
    FMH-HO4 ownership tree and path compil :done, fmhho4, 2026-10-10, 2026-10-11
    FMH-HO5 switch the compiler to the tre :done, fmhho5, 2026-10-10, 2026-10-11
    FMH-HO6 ownership refusals and the roo :done, fmhho6, 2026-10-10, 2026-10-11
    FMH-HO7 composite create and tombstone :done, fmhho7, 2026-10-10, 2026-10-11
    FMH-HO8 injective graph naming within :done, fmhho8, 2026-10-10, 2026-10-11
    FMH-HO9 ownership documentation and cl :done, fmhho9, 2026-10-10, 2026-10-11
    FMH-W65 :fmhw65, 2026-10-23, 2026-10-24
    H2.11a :h211a, 2026-10-21, 2026-10-22
    H2.11b :h211b, 2026-10-21, 2026-10-22
    H2.12 :h212, 2026-11-01, 2026-11-02
    H2.6 :h26, 2026-10-13, 2026-10-14
    H2.6c :h26c, 2026-10-20, 2026-10-21
    H2.6d :h26d, 2026-10-20, 2026-10-21
    H2.9 :h29, 2026-10-21, 2026-10-22
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title The insurml-alignment epic
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section insurml-alignment
    IMA-0.7 alignment edits :ima07, 2026-10-05, 2026-10-06
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Applied-ontology-readiness
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section applied-ontology-readiness
    AOR-1 :aor1, 2026-09-25, 2026-09-26
    AOR-10 AOR-11 :aor10, 2026-09-25, 2026-09-26
    AOR-11 AOR-11 :aor11, 2026-09-25, 2026-09-26
    AOR-12 :aor12, 2026-09-25, 2026-09-26
    AOR-13 :aor13, 2026-09-25, 2026-09-26
    AOR-14 to AOR-16 :aor14, 2026-09-25, 2026-09-26
    AOR-15 to AOR-16 :aor15, 2026-09-25, 2026-09-26
    AOR-16 to AOR-16 :aor16, 2026-09-25, 2026-09-26
    AOR-17 :aor17, 2026-09-25, 2026-09-26
    AOR-2 to AOR-4 :aor2, 2026-09-25, 2026-09-26
    AOR-3 to AOR-4 :aor3, 2026-09-25, 2026-09-26
    AOR-3b :aor3b, 2026-09-25, 2026-09-26
    AOR-4 to AOR-4 :aor4, 2026-09-25, 2026-09-26
    AOR-5 to AOR-9 :aor5, 2026-09-25, 2026-09-26
    AOR-6 to AOR-9 :aor6, 2026-09-25, 2026-09-26
    AOR-7 to AOR-9 :aor7, 2026-09-25, 2026-09-26
    AOR-8 to AOR-9 :aor8, 2026-09-25, 2026-09-26
    AOR-9 to AOR-9 :aor9, 2026-09-25, 2026-09-26
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Computable-contract-substrate
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section computable-contract-substrate
    C9b0 Eligibility sources legal act :done, c9b0, 2026-10-10, 2026-10-11
    CCS-0 A-112 A-113 A-01 and ADR-A-C :ccs0, 2026-10-29, 2026-10-30
    CCS-1 A-104 :ccs1, 2026-10-29, 2026-10-30
    CCS-10 Behaviour split and layer flip :done, ccs10, 2026-10-10, 2026-10-11
    CCS-10a import guard :done, ccs10a, 2026-10-29, 2026-10-30
    CCS-11 runtime records occasions in :done, ccs11, 2026-10-10, 2026-10-11
    CCS-11a nested states history concur :done, ccs11a, 2026-10-10, 2026-10-11
    CCS-2 A-106 :ccs2, 2026-10-29, 2026-10-30
    CCS-3 Wording spec vocab and shapes :done, ccs3, 2026-10-10, 2026-10-11
    CCS-4 Wording tables assembly vari :done, ccs4, 2026-10-10, 2026-10-11
    CCS-5 Wording amendments law shapes :done, ccs5, 2026-10-10, 2026-10-11
    CCS-6 instrument terms the five re :done, ccs6, 2026-10-10, 2026-10-11
    CCS-7a regimes and gating split from :done, ccs7a, 2026-10-05, 2026-10-06
    CCS-7b terms in time :done, ccs7b, 2026-10-06, 2026-10-07
    CCS-7c what terms are and who they b :done, ccs7c, 2026-10-27, 2026-10-28
    CCS-8 values in stated meaning Word :done, ccs8, 2026-10-10, 2026-10-11
    CCS-8a set comparisons qualifying ru :ccs8a, 2026-10-27, 2026-10-28
    CCS-8b values in stated meaning Word :done, ccs8b, 2026-10-10, 2026-10-11
    CCS-9a amendments assents and taking :done, ccs9a, 2026-10-10, 2026-10-11
    CCS-9b.0 Eligibility sources legal act :done, ccs9b0, 2026-10-10, 2026-10-11
    CCS-9b.1 Eligibility sources legal act :done, ccs9b1, 2026-10-10, 2026-10-11
    CCS-9b.2 Eligibility sources legal act :done, ccs9b2, 2026-10-10, 2026-10-11
    CCS-9b.3 set comparisons qualifying ru :ccs9b3, 2026-10-27, 2026-10-28
    CCS-9b.3a :ccs9b3a, 2026-10-29, 2026-10-30
    CCS-9b.3c :ccs9b3c, 2026-10-29, 2026-10-30
    CCS-9b.4 set comparisons qualifying ru :ccs9b4, 2026-10-27, 2026-10-28
    CCS-9c set comparisons qualifying ru :ccs9c, 2026-10-27, 2026-10-28
    CCS-9d set comparisons qualifying ru :ccs9d, 2026-10-27, 2026-10-28
    CCS-F1 external and natural keys ADR :done, ccsf1, 2026-10-10, 2026-10-11
    HQ-6a.1 untimed closures ADR-A105 t :done, hq6a1, 2026-10-27, 2026-10-28
    HQ-6a.2 untimed closures ADR-A105 t :done, hq6a2, 2026-10-27, 2026-10-28
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Git-hooks
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section git-hooks
    GH-0 :gh0, 2026-10-24, 2026-10-25
    GH-1 :gh1, 2026-10-24, 2026-10-25
    GH-2 :gh2, 2026-10-24, 2026-10-25
    GH-3 :gh3, 2026-10-24, 2026-10-25
    GH-4 :gh4, 2026-10-24, 2026-10-25
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Improved-ontology-documentation
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section improved-ontology-documentation
    OD-0 ADRs the AGENTS.md rule the :od0, 2026-10-17, 2026-10-18
    OD-1 scanner and markers :od1, 2026-10-17, 2026-10-18
    OD-2 sections 1 to 3 :od2, 2026-10-18, 2026-10-19
    OD-3 section 6 to OWL :od3, 2026-10-18, 2026-10-19
    OD-4 section 6 to SHACL :od4, 2026-10-18, 2026-10-19
    OD-5 generated regions :od5, 2026-10-18, 2026-10-19
    OD-6 Eligibility pilot :od6, 2026-10-20, 2026-10-21
    OD-7 Vocabulary :od7, 2026-10-20, 2026-10-21
    OD-DOC1 published decisions :oddoc1, 2026-10-19, 2026-10-20
    OD-DOC2 site sections :done, oddoc2, 2026-10-20, 2026-10-21
    OD-DOC2b working documents out of publi :oddoc2b, 2026-10-20, 2026-10-21
    OD-ELC1 composition operation :odelc1, 2026-10-19, 2026-10-20
    OD-MC1 migration check labels :odmc1, 2026-10-20, 2026-10-21
    OD-RC1 catalogue and reader :odrc1, 2026-10-17, 2026-10-18
    OD-RC2 consumers use the reader :odrc2, 2026-10-18, 2026-10-19
    OD-RC3 roots AGENTS.md table bypass :odrc3, 2026-10-19, 2026-10-20
    OD-REL1 first release 0.18.0 :odrel1, 2026-10-20, 2026-10-21
    OD-VER1 one release for the substrate :odver1, 2026-10-20, 2026-10-21
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Multi-store-conformance
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section multi-store-conformance
    MSC-1 :msc1, 2026-10-27, 2026-10-28
    MSC-2 :msc2, 2026-10-27, 2026-10-28
    MSC-3 :msc3, 2026-10-27, 2026-10-28
    MSC-4 :msc4, 2026-10-27, 2026-10-28
    MSC-5 :msc5, 2026-10-27, 2026-10-28
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Ontology-remediation
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section ontology-remediation
    OR-0 :or0, 2026-10-28, 2026-10-29
    OR-1 :or1, 2026-10-28, 2026-10-29
    OR-10 :or10, 2026-10-28, 2026-10-29
    OR-11 :or11, 2026-10-28, 2026-10-29
    OR-12 :or12, 2026-10-28, 2026-10-29
    OR-13 :or13, 2026-10-28, 2026-10-29
    OR-14 OR-14 :or14, 2026-10-28, 2026-10-29
    OR-15 :or15, 2026-10-28, 2026-10-29
    OR-16 :or16, 2026-10-28, 2026-10-29
    OR-17 :or17, 2026-10-28, 2026-10-29
    OR-18 :or18, 2026-10-28, 2026-10-29
    OR-19 :or19, 2026-10-28, 2026-10-29
    OR-2 :or2, 2026-10-28, 2026-10-29
    OR-3 :or3, 2026-10-28, 2026-10-29
    OR-4 :or4, 2026-10-28, 2026-10-29
    OR-5 :or5, 2026-10-28, 2026-10-29
    OR-6 :or6, 2026-10-28, 2026-10-29
    OR-7 :or7, 2026-10-28, 2026-10-29
    OR-7b :or7b, 2026-10-28, 2026-10-29
    OR-8 OR-14 :or8, 2026-10-28, 2026-10-29
    OR-9 :or9, 2026-10-28, 2026-10-29
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Persistence-compiler-iri-sync
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section persistence-compiler-iri-sync
    PCI-1 Dataset-level epoch guard G1 :pci1, 2026-09-23, 2026-09-24
    PCI-2 Ordering receipt concurrency a :pci2, 2026-09-23, 2026-09-24
    PCI-3 Identity minting profile resol :pci3, 2026-09-23, 2026-09-24
    PCI-4 Privacy erasure profile cros :pci4, 2026-09-25, 2026-09-26
    PCI-5 Uniqueness onViolation recon :pci5, 2026-09-25, 2026-09-26
    PCI-6 Documentation close-out :pci6, 2026-09-25, 2026-09-26
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Phase-0-status
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section phase-0-status
    PLT-0.1.1 :plt011, 2026-09-23, 2026-09-24
    PLT-0.1.10 :plt0110, 2026-09-23, 2026-09-24
    PLT-0.1.11 :plt0111, 2026-09-23, 2026-09-24
    PLT-0.1.12 :plt0112, 2026-09-23, 2026-09-24
    PLT-0.1.13 :plt0113, 2026-09-23, 2026-09-24
    PLT-0.1.2 :plt012, 2026-09-23, 2026-09-24
    PLT-0.1.3 :plt013, 2026-10-10, 2026-10-11
    PLT-0.1.4 :plt014, 2026-09-23, 2026-09-24
    PLT-0.1.5 :plt015, 2026-09-23, 2026-09-24
    PLT-0.1.6 :plt016, 2026-09-23, 2026-09-24
    PLT-0.1.7 :plt017, 2026-09-23, 2026-09-24
    PLT-0.1.8 :plt018, 2026-09-23, 2026-09-24
    PLT-0.1.9 :plt019, 2026-09-23, 2026-09-24
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Word-authoring-poc
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section word-authoring-poc
    WA-0 Preflight :wa0, 2026-10-02, 2026-10-03
    WA-1 Contracts templates and sampl :wa1, 2026-10-02, 2026-10-03
    WA-10 Compose stack :wa10, 2026-10-02, 2026-10-03
    WA-11 Documentation and close-out :wa11, 2026-10-10, 2026-10-11
    WA-2 Service model mapping and sha :wa2, 2026-10-02, 2026-10-03
    WA-3 Detection templates and confo :wa3, 2026-10-02, 2026-10-03
    WA-4 API and HTTP adapter :wa4, 2026-10-02, 2026-10-03
    WA-5 Fuseki RabbitMQ and the runna :wa5, 2026-10-02, 2026-10-03
    WA-6 Logical English reading :wa6, 2026-10-02, 2026-10-03
    WA-7 Worker runtime :wa7, 2026-10-02, 2026-10-03
    WA-8 Add-in domain :wa8, 2026-10-02, 2026-10-03
    WA-9 Add-in task pane and harness :wa9, 2026-10-02, 2026-10-03
    WA-9a Ribbon and right-click command :wa9a, 2026-10-02, 2026-10-03
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title Work-board
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section work-board
    WB-0 the sketch the plan this rec :wb0, 2026-11-02, 2026-11-03
    WB-1 tools work board.py work b :wb1, 2026-11-02, 2026-11-03
    WB-2 the slice grammar work renam :wb2, 2026-11-02, 2026-11-03
    WB-3 INDEX.md replaced ROADMAP.md :wb3, 2026-11-02, 2026-11-03
    WB-4 the work check and the post- :wb4, 2026-11-02, 2026-11-03
    WB-5 AGENTS.md the skills the sta :wb5, 2026-11-02, 2026-11-03
    WB-6 work here :wb6, 2026-11-02, 2026-11-03
    WB-7 the branches marked or deleted :wb7, 2026-11-02, 2026-11-03
```

```mermaid
%%{init: {"themeVariables": {"taskBkgColor": "#f2c14e", "taskBorderColor": "#b8860b", "taskTextColor": "#000000", "activeTaskBkgColor": "#4e9af1", "activeTaskBorderColor": "#1f5fbf", "activeTaskBorderColor": "#1f5fbf", "doneTaskBkgColor": "#8fcf8f", "doneTaskBorderColor": "#2f7d32", "critBkgColor": "#f28b82", "critBorderColor": "#b23a30", "taskTextDarkColor": "#000000", "taskTextLightColor": "#000000"}}}%%
gantt
    title The smaller units
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section identity-minting
    IM-0 ADR-A82 amendment ADR-A84 li :im0, 2026-09-24, 2026-09-25
    IM-1 Vocabulary compiler recipe em :im1, 2026-09-24, 2026-09-25
    IM-2 Pinned Unicode 16.0 tables Py :im2, 2026-09-24, 2026-09-25
    IM-3 Java library vector coverage :im3, 2026-09-24, 2026-09-25
    section ledger
    LG-0 :lg0, 2026-10-27, 2026-10-28
    LG-1 :lg1, 2026-10-27, 2026-10-28
    LG-2 :lg2, 2026-10-27, 2026-10-28
    section normative-rule-substrate
    NRS-4 Deontic extension of Instrumen :done, nrs4, 2026-09-30, 2026-10-01
    NRS-5 Closure declarations A-105 R :done, nrs5, 2026-10-10, 2026-10-11
    section persistence-delta-replace
    DR1 :dr1, 2026-11-02, 2026-11-03
    DR2 :dr2, 2026-11-02, 2026-11-03
    section rdf-sparql-patterns-status
    RSP-1 Core patterns :rsp1, 2026-09-22, 2026-09-23
    RSP-2 Substrate and compiler :rsp2, 2026-09-22, 2026-09-23
    section vocabulary-temporal-binding
    VTB-1 ADR-A85 proposal architecture :vtb1, 2026-09-25, 2026-09-26
    VTB-2 12 fixtures 11 positive negat :vtb2, 2026-09-25, 2026-09-26
    VTB-3 tools vocabulary resolver :vtb3, 2026-09-25, 2026-09-26
    VTB-4 Surface resolves scoped bindin :vtb4, 2026-09-25, 2026-09-26
```

<!-- END GENERATED work-board-glance -->

## 2. How the epics depend on one another

Arrows point from the work that must come first. A dashed arrow is a dependency that is planned or not yet in force. Ledger's layer is on `main` and ADR-A131 is Accepted, so its dashed edges are the imports and slices still to come (LG-3, LG-4). Ensemble is still Proposed.

```mermaid
flowchart LR
    FM["Formal methods"]
    CCS["Computable contract substrate"]
    AIR["Applied insurance reference"]
    NRS["Normative rule substrate"]
    IMA["InsurML alignment"]
    IOD["Ontology documentation"]
    ENS["Ensemble, proposed"]
    LDG["Ledger"]
    PLAT["Platform programme"]
    TUT["Tutorial"]
    CBAA["Open CBAA, downstream"]

    FM -->|"Eligibility pass for CCS-9b.3"| CCS
    CCS -->|"HQ-6a closures for AIR-3.3"| AIR
    AIR -->|"AIR-3.3 gates CCS-12"| CCS
    CCS -->|"CCS-12 evaluator for FMB-4"| FM
    NRS -->|"NRS-1 for CCS-12, CCS-13 and CCS-13a"| CCS
    CCS -->|"Instrument tranche for IMA phase 3"| IMA
    AIR -->|"phases 1 to 4"| CBAA
    CBAA -.->|"integration gates AIR phase 5"| AIR
    CCS -.->|"hands over HQ-2, HQ-7, HQ-12"| ENS
    ENS -.->|"ES-4 and ES-5 for AIR-7.1"| AIR
    LDG -.->|"LG-3 gates AIR phase 5 and AIR-6.8"| AIR
    LDG -.->|"LG-3 accounts for Behaviour, PDD-07"| CCS
    LDG -.->|"LG-4 allocation for AIR phase 7"| AIR
    IOD -->|"literate layout and one release"| CCS
    IOD -->|"literate layout and one release"| AIR
    IOD -->|"OD-DOC3 reviews it"| TUT
```

The arrow from NRS into CCS is NRS-1. The NRS log (NQ-2, 2026-10-10) moved NRS-1 to CCS, while the CCS board still names NRS-1 as the blocker of CCS-12, CCS-13 and CCS-13a, and the NRS board still lists it, so the records disagree.

## 3. The layers, now and proposed

The substrate's import order on `main` (ADR-A01 and its addenda, ADR-A106, ADR-A112). Ledger is on `main` with ADR-A131 Accepted, so it is drawn solid, and Ensemble is still proposed on `docs/placement-vehicles-structure` and drawn dashed. Where the new layers sit is taken from their plans (Ensemble imports Instrument and Behaviour's runtime, Ledger is imported by Behaviour's configuration once LG-3 migrates it, so that edge is dashed). ADR-A01's addenda of 2026-10-18 (Ensemble) and 2026-10-19 (Ledger) settle the order and both stay Proposed.

```mermaid
flowchart BT
    F["Foundation"] --> V["Vocabulary"]
    V --> Q["Quantification"]
    Q --> P["Party"]
    P --> E["Eligibility"]
    E --> W["Wording"]
    E --> BC["Behaviour configuration"]
    BC --> BR["Behaviour runtime"]
    W --> I["Instrument"]
    BC --> I
    LDG["Ledger"] -.-> BC
    I -.-> ENS["Ensemble, proposed"]
    BR -.-> ENS
    I --> APP["Applied modules"]
    ENS -.-> APP
```

Persistence, Surface and MORK sit beside the substrate. They are versioned on their own and consumed by the toolchains.

## 4. Active epics

### 4.1 Computable contract substrate (CCS)

**Documents.** [plan](plans/computable-contract-substrate.md), [status](status/computable-contract-substrate.md), [sketch](sketches/computable-contract-substrate.md). ADRs A-104, A-106, A-112 to A-115 and A-120 accepted, A-105 and A-145 published.

**Where it is.** The status record reads verified, in progress. Gate A passed on 2026-10-01 (CCS-0 to CCS-2). Tranche B (CCS-3 to CCS-5, Wording) and tranche C (CCS-10, CCS-10a, CCS-11, CCS-11a, the Behaviour split and nested states) are merged and tagged, and so is CCS-F1. In tranche D, CCS-6, CCS-7a to CCS-7c, CCS-8, CCS-8b, CCS-9a, CCS-9b.0 to CCS-9b.2, HQ-6a.1 and HQ-6a.2 (ADR-A105) are merged, and HQ-6a.2's `executable-v0.7.0` is tagged. CCS-9b.3 is briefed (2026-10-27) and delivered on `ccs-trunk`, which `main` does not yet have. The profile union fix, CCS-9b.3c (the hierarchy relation) and CCS-9b.3a (set comparisons, ADR-A145) are merged into `ccs-trunk`, and so is the multi-store conformance unit. CCS-9b.3b, aggregate bindings, is next to brief and has no board row yet. HQ-6b, closures over a period, follows before CCS-12.

```mermaid
flowchart LR
    subgraph A["Tranche A, decisions"]
        A1["CCS-0 to CCS-2"]
    end
    subgraph B["Tranche B, Wording"]
        B1["CCS-3 to CCS-5"]
    end
    subgraph C["Tranche C, Behaviour"]
        C1["CCS-10, CCS-10a, CCS-11, CCS-11a"]
    end
    subgraph D["Tranche D, Instrument"]
        D1["CCS-6 to CCS-8b"] --> D2["CCS-9a"] --> D3["CCS-9b.0 to CCS-9b.2"] --> D4["HQ-6a.1, HQ-6a.2"]
        D4 --> D5["CCS-9b.3"] --> D6["CCS-9b.4"]
        D6 --> D7["CCS-9d, CCS-9c, CCS-8a"]
    end
    subgraph E["Tranche E, evaluation"]
        E1["CCS-12, CCS-13"]
        E2["CCS-13a"]
    end
    subgraph F["Tranche F, close"]
        F1["CCS-16c"]
        F2["CCS-14 to CCS-17"]
    end
    A --> B --> C --> D
    D7 --> E1
    D6 --> F1
    E1 --> F2

    classDef done fill:#d8f0d8,stroke:#3a7d3a
    classDef next fill:#fff1c2,stroke:#a07800
    classDef wait fill:#eeeeee,stroke:#888888
    class A1,B1,C1,D1,D2,D3,D4 done
    class D5 next
    class D6,D7,E1,E2,F1,F2 wait
```

**What it waits on.** CCS-9b.4 waits on CCS-9b.3. CCS-12 and CCS-13 are blocked on the rest of the Instrument tranche (CCS-9b.3, CCS-9b.4, CCS-9d, CCS-9c, CCS-8a), AIR-3.3 and NRS N1. CCS-13a is blocked on NRS N1. CCS-14 to CCS-17 are blocked on CCS-8a, the Instrument tranche and CCS-12. CCS-16c, removing Party's shares, is planned and must land before the epic closes. It follows CCS-9b.4.

**Held questions.** HQ-1 to HQ-12, in the plan, each a planned row on the board. Three are proposed for hand-over to the Ensemble unit (HQ-2's second case, HQ-7, HQ-12) once ADR-A130 is accepted. ADR-A130 is still Proposed.

### 4.2 Applied insurance reference (AIR)

**Documents.** [epic plan](plans/applied-insurance-reference.md), [status](status/applied-insurance-reference.md), [lanes](plans/applied-insurance-reference-lanes.md), [claims plan](plans/applied-insurance-reference-claims.md), [substrate plan](plans/applied-insurance-reference-substrate.md), [leftovers](plans/air-leftovers.md).

**How it runs.** Two machines (lanes §2 to §4). Machine R verifies and merges, and also builds CCS. Machine S builds the slices in one trip on one branch, which comes to R once the trip is done. S became unavailable on 2026-10-14 and R built AIR-4.2a to AIR-4.4. The epic is in round 3, the trip's commits up to AIR-4.4 are on `main`, and AIR-4.5 is next on the trip. The record's Status line still reads planned.

**Where it is.** The board rows are the state. AIR-1.1, AIR-1.2, AIR-2.1, AIR-3.1 and AIR-3.2 are merged. AIR-2.0, AIR-2.2, AIR-2.3, AIR-2.4, AIR-2.6, AIR-4.1, AIR-4.2, AIR-4.2a, AIR-4.3 and AIR-4.4 are built.

| Phase | Plan | State |
|---|---|---|
| 0 Decisions | [plan](plans/applied-insurance-reference-phase-0.md) | ✅ complete |
| 1 Module split | [plan](plans/applied-insurance-reference-phase-1.md) | ✅ AIR-1.1 and AIR-1.2 merged |
| 2 Peril vocabulary | [plan](plans/applied-insurance-reference-phase-2.md) | 🚧 AIR-2.1 merged. AIR-2.0, AIR-2.2 to AIR-2.4 and AIR-2.6 built, the cause scheme at 287 concepts in eight families. AIR-2.5 and AIR-2.7 planned, briefed |
| 3 Readings and crosswalks | [plan](plans/applied-insurance-reference-phase-3.md) | 🚧 AIR-3.1 and AIR-3.2 merged. AIR-3.3 planned, its brief blocked on AIR-3.3-Q1. AIR-3.4 and AIR-3.5 planned, briefed |
| 4 Exposure | [plan](plans/applied-insurance-reference-phase-4.md) | 🚧 AIR-4.1 to AIR-4.4 and AIR-4.2a built. AIR-4.5 and AIR-4.6 planned, briefed. AIR-4.2b planned, its change built on the Track H line and to bring across |
| 5 Contract module | [plan](plans/applied-insurance-reference-phase-5.md) | 🅿️ AIR-5.1 to AIR-5.9 planned, deferred until Open CBAA integrates phases 1 to 4 (decision D2) |
| 6 Submission, claims | [plan](plans/applied-insurance-reference-phase-6.md), [claims](plans/applied-insurance-reference-claims.md) | ⏳ AIR-6.1 planned, briefed. The claims slices AIR-6.2 to AIR-6.12 and AIR-6.W0 to AIR-6.W7 planned, none briefed |
| 7 Placement and capital | [plan](plans/applied-insurance-reference-phase-7.md) | 📝 proposed 2026-10-18. AIR-7.0 to AIR-7.10 planned, no slice briefed |

```mermaid
flowchart LR
    P0["0 Decisions"] --> P1["1 Module split"]
    P1 --> P2["2 Peril vocabulary"]
    P1 --> P4["4 Exposure"]
    P2 --> P3["3 Readings"]
    P4 --> P3
    P4 --> P6["6 Submission and claims"]
    P2 --> P5["5 Contract module"]
    P4 --> P5
    P5 -.-> P7["7 Placement and capital"]
    P6 --> P7

    classDef done fill:#d8f0d8,stroke:#3a7d3a
    classDef doing fill:#fff1c2,stroke:#a07800
    classDef parked fill:#e6e0f5,stroke:#6a55a0
    classDef todo fill:#eeeeee,stroke:#888888
    class P0,P1 done
    class P2,P3,P4 doing
    class P5 parked
    class P6,P7 todo
```

**Milestones** (epic plan §4). M1 (the reference cause scheme decides open-perils conditions) and M3 (exposure units derived on demand) are the nearest. M4 and M5 are deferred with Phase 5. M6 to M8 are the claims milestones, ending with a coverholder's bordereau lifted, reconciled and emitted again.

**Phase 7, proposed.** A programme data model (towers, layers, lines and their formation state), market responses from decline to binding quote, risk-capital vehicles, and the London market's MRC form as a specialisation. It rests on Ensemble (ADR-A130, Proposed) and Ledger (ADR-A131, Accepted). It records and evaluates programmes. It does not advise on them.

### 4.3 Formal methods (FM)

**Documents.** [epic plan](plans/formal-methods.md), [epic status](status/formal-methods.md), [lifecycle guide](formal-methods-lifecycle.md). ADR-A-FM1 to ADR-A-FM4 accepted. The prover is Isabelle/HOL, with Haskell and Scala as code-generation targets (FM-D1 and FM-D10, decided 2026-10-06).

| Track | Subject | State |
|---|---|---|
| D | prover spike | ✅ FM-D0 to FM-D4 and FM-PF1 built, two Gate D criteria open |
| A | ledger and harness | ⏳ not started, waits on Gate D and its ADR |
| B | reference semantics and oracle | 🚧 FMB-1 to FMB-3, FMB-2.1 and FMB-2.2 built. FMB-4 planned, waits on CCS-12. FMB-5 building, blocked on a package-mirror gap |
| C | design-time models | 🚧 FMC-1, FMC-2 and FMC-2.1 built. FMC-2.2, FMC-2.3 and FMC-3 planned, FMC-3 next. ADR-A116 Proposed. FM-4, a design model of ADR-A130, reads built on the epic board and briefed in track C's record |
| E | prover programme | 🚧 FME-1.0, FME-1.1 and FME-1.4 built. FME-1.2 dropped. FME-1.3 planned, waits on the overlap-rule ADR (ADR-A116). FME-2 to FME-5 planned |
| F | native tooling | ⏳ not started |
| G | instrument assurance | ⏳ waits on FMB-4 and FMC-3 |
| H | Persistence | 🚧 FMH-1.1 to FMH-1.5, FMH-HO0 to FMH-HO9 and FMH-2.0 to FMH-2.3 merged. FMH-2.4a to FMH-2.6g (except FMH-2.6d), FMH-2.8a to FMH-2.8c, FMH-2.9, FMH-2.11a, FMH-2.11b, FMH-2.12 and FMH-W65 built or verified. FMH-2.6d, FMH-2.7 and FMH-2.8 still read planned. FMH-3 to FMH-10 planned |

```mermaid
flowchart LR
    D["D prover spike"] --> A["A ledger and harness"]
    D --> E["E prover programme"]
    B["B reference semantics"] --> B4["FMB-4 evaluation context"]
    CCS12["CCS-12"] --> B4
    C["C design-time models"] --> C3["FMC-3 slot exclusivity"]
    B4 --> G["G instrument assurance"]
    C3 --> G
    F["F native tooling"]
    H["H Persistence"] --> H3["FMH-3 onward"]

    classDef done fill:#d8f0d8,stroke:#3a7d3a
    classDef doing fill:#fff1c2,stroke:#a07800
    classDef todo fill:#eeeeee,stroke:#888888
    class D done
    class B,C,E,H doing
    class A,B4,C3,G,F,H3,CCS12 todo
```

**Track H, the release.** Track H's Next action lists every planned FMH-2 slice built: FMH-2.6c to FMH-2.6g, FMH-2.7, FMH-2.8a to FMH-2.8c, FMH-2.9, FMH-2.11a and FMH-2.11b (the Persistence README in the literate layout), the test-suite work FMH-TS-1 and FMH-TS-2, a new `packages/persistence/python`, Oxigraph as the Persistence tests' default engine, and the release prepared as 0.19.0 with the applied modules re-pinned. The maintainer answered the review items Q1 to Q6 on 2026-10-21 and approved the second review's follow-ups on 2026-10-23, so nothing on the line awaits review. The tags `persistence-v0.19.0` and `ontologies-v0.19.0` exist, so the line is on `main`, although the record still lists the merge as the maintainer's and its board rows have not moved.

**Isabelle models.** `fml/isabelle-layers` carries Isabelle/HOL models of the layers' laws and a code-generation spike, with Haskell and Scala exports run and Eligibility's decision table executed. The spike has no slice on the epic board yet.

### 4.4 Improved ontology documentation (IOD)

**Documents.** [plan](plans/improved-ontology-documentation.md), [status](status/improved-ontology-documentation.md). ADR-A121, ADR-A126 and ADR-A129 published, ADR-A127 accepted.

**Where it is.** The record reads verified, in progress. OD-0, OD-RC2, OD-RC3, OD-1, OD-7, OD-DOC1, OD-ELC1, OD-MC1, OD-VER1 and OD-REL1 are verified on its board, OD-RC1, OD-2 to OD-6 and OD-DOC2b are built, and OD-DOC2 is merged. `docs/literate-v2` was squash-merged into `main` on 2026-10-20 (`cf1b8eb`). That brought the repository catalogue and its reader (OD-RC1 to OD-RC3), the literate README layout and its compilers to OWL and SHACL (OD-1 to OD-5), the Eligibility and Vocabulary pilots (OD-6, OD-7), published decisions and the site sections (OD-DOC1, OD-DOC2, OD-DOC2b), and one release number for the substrate and standalone ontologies, 0.18.0 (OD-VER1, OD-REL1). `GOVERNANCE.md` and the validation and test plan were retired in the same change.

**Next.** The tag `ontologies-v0.18.0` is on the merge commit and the line has since reached `ontologies-v0.21.0`, but the board rows have not moved to merged. OD-8 onward is planned and migrates the remaining layers one at a time, after OD-7 and, for Foundation and Party, their part of TD-16. OD-RC4 to OD-RC6 are planned and extend the catalogue downstream, promote packages and fold in the XML catalogue (OD-RC6 needs a new ADR on ADR-A88). OD-DOC3 is planned and reviews the tutorial once it is merged.

### 4.5 Ensemble and Ledger, substrate layers

Ensemble is proposed on `docs/placement-vehicles-structure`, with its sketch and plan, for the maintainer's review. No Ensemble slice is briefed and it has no status record. Ledger's layer is on `main` with ADR-A131 Accepted. LG-0 (examples) and LG-1 (the configuration document) are built, verified and committed, LG-2 (the runtime document) is briefed and not started, and LG-3 to LG-5 are planned. LG-5, the benchmark, is part built ahead of LG-2.

| | Ensemble | Ledger |
|---|---|---|
| Prefix and home | `ens:`, `ontology/ensemble/` | `ldg:`, `ontology/ledger/` |
| ADR | A-130, Proposed | A-131, Accepted |
| Holds | identities naming member instruments by role, reified relations between instruments (kinds K1 to K8), judgements across an ensemble, confidentiality between members, evaluation by composition | account definitions and their tree, postings and balance records, allocation with conservation, Behaviour's migration from allowances to accounts |
| Takes over | CCS HQ-2 (second case), HQ-7, HQ-12 | PDD-07 and the ledger part of PDD-08 |
| Serves | AIR Phase 7, AIR-6.8's cross-instrument reads | AIR Phase 7, Behaviour's threshold regimes |

### 4.6 InsurML alignment (IMA)

**Documents.** [epic plan](plans/insurml-alignment.md), [phase 0](plans/insurml-alignment-phase-0.md), [status](status/insurml-alignment.md), [vision](../architecture/insurml-alignment-vision.md).

Nothing is built, and every slice on the board is planned (IMA-0.1 to IMA-4.5). The record reads Proposed, awaiting the maintainer's review of the vision, the sketches and the plans. Nine phases are planned, from decisions (Phase 0) through the InsurML profile, lift and lower kits, Wording changes, an assembly interface, meaning over components, authoring and exchange, library ingestion, to continuous standards engagement. Phase 3 waits on Phase 2 and the Instrument tranche of CCS. One slice, IMA-3.3, moved into CCS as CCS-8b, which is merged. PDD-01 to PDD-03 hold its ownership and tooling questions.

### 4.7 Normative rule substrate (NRS)

**Documents.** [plan](plans/normative-rule-substrate.md), [status](status/normative-rule-substrate.md).

Nothing is built in this unit, and the record reads blocked. CCS took NRS-1, NRS-2, NRS-4, NRS-5 and the Behaviour part of NRS-8, and absorbed NRS-6 and NRS-8 into CCS-12 and CCS-13 (NQ-1 to NQ-4, 2026-10-10). The board still lists NRS-1 and NRS-2 here, as blocked. NRS keeps the rule-language integration work (LegalRuleML), with decisions D1, D4 and D5 open. ADR-A108 and ADR-A109 are drafted and Proposed, and A-107, A-110 and A-111 are reserved. NRS-9 changes Foundation and must wait for AIR Phase 2 to finish. The contract builder's ODRL import took NRS-12's import half on 2026-10-29 (ADR-A144, Proposed), and export, interchange and the conformance measurement stay here.

## 5. Smaller units

The units outside an epic are rows of section 1's generated table, with their state, next slice and the branches that move them, and their own charts there once they have five dated slices. Nothing is listed twice.

## 6. The platform programme

**Documents.** [epic plan](plans/lattice-platform-agentic-development-v0.2.md), phase plans [0](plans/phase-0-plan.md) to [4](plans/phase-4-plan.md), status records [0](status/phase-0-status.md) to [4](status/phase-4-status.md), [continuation status](status/platform-continuation.md).

The first platform build (the earlier phases 0 to 6: Surface lifecycle and ledger, workers, release integration, OCI adapter, projection lowering, MORK review and governance queue) is merged and accepted, as the continuation status and the six phase handoffs record (2026-09-20), with the verification gaps each handoff lists. The new programme's phases are sequential, and none has started a code slice.

```mermaid
flowchart LR
    P0["Phase 0, decisions and foundations"] --> P1["Phase 1, graph-primary core"]
    P1 --> P2["Phase 2, ingestion and query"]
    P2 --> P3["Phase 3, operation plane"]
    P3 --> P4["Phase 4, maturity"]

    classDef doing fill:#fff1c2,stroke:#a07800
    classDef todo fill:#eeeeee,stroke:#888888
    class P0 doing
    class P1,P2,P3,P4 todo
```

**Phase 0** reads built (2026-09-23), with its decision pack drafted and pending ratification. PLT-0.1.1 to PLT-0.1.13 are built, PLT-0.1.3 on 2026-10-10 and the rest on 2026-09-23, and PLT-0.1.14 (threat model), PLT-0.1.15 (NFR catalogue) and PLT-0.2r (build skeleton) are planned. The pack drafted 17 ADRs on 2026-09-23 (A-48, A-50, A-51, A-54, A-57, A-59, A-62, A-63, A-65 to A-69, A-71, A-74, A-75, A-81). Sixteen are Proposed, and A-51 is superseded by A-82, also Proposed. A-76 (Maven or Gradle) is not drafted, the `graph-spi` and `semantic-dataset-spi` decision is open, and the A-44 and A-81 renumbering awaits the maintainer's confirmation. Milestones M0 and M1 are not demonstrated.

**Phases 1 to 4.** Phase 1 reads blocked (2026-09-22) on Phase 0's exit gate. Phases 2 and 3 are planned rolling-wave placeholders, expanded at P1.11.3 and P2.11.4 respectively. Phase 4 is planned and sized only after Phase 3's measurements.

## 7. Branches

<!-- BEGIN GENERATED work-board-branches. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Branches with a commit `main` lacks, from the same reading.

| Branch | Tip | Ahead of main | Upstream | Moves |
|---|---|---|---|---|
| `ccs-trunk` | 2026-10-29 | 53 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `claude/persistence-delta-replace` | 2026-11-02 | 137 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, DR1, DR2, DR3, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.12, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `claude/persistence-linear-replace` | 2026-11-01 | 135 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.12, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `docs/placement-vehicles-structure` | 2026-11-02 | 113 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `fml/isabelle-layers` | 2026-11-01 | 31 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `persistence-mbt` | 2026-09-23 | 1 | pushed | 1, 1., 2, 2., 3, 3., 4, 5, 6, 7, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+ |
| `realign/config-authoring-studio` | 2026-11-02 | 154 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, DOC1, DOC2, DOC2b, DOC3, DR1, DR2, DR3, DR4, E1.0, E1.1, E1.2, E1.3, E1.4, E2, ELC, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.11a, H2.11b, H2.12, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.6c, H2.6d, H2.7, H2.8, H2.8c, H2.9, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, MC1, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, OD-REL, OD0, OD1, OD2, OD3, OD4, OD5, OD6, OD7, OD8, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, RC1, RC2, RC3, RC4, RC5, RC6, VER1, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `spikes/pol-map` | 2026-10-16 | 2 | pushed | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, E1.0, E1.1, E1.2, E1.3, E1.4, E2, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H2.6b, H2.7, H2.8, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |
| `tutorial/guide` | 2026-10-16 | 5 | remote only | 1, 1., 1., 2, 2., 2., 3, 3., 3., 4, 4., 5, 6, B1, B2, B2.1, B2.2, B3, B4, B5, C0, C1, C1, C10, C10a, C11, C11a, C12, C13a, C14, C16c, C2, C2, C2.1, C2.2, C2.3, C3, C3, C4, C5, C6, C7a, C7b, C7c, C8, C9a, C9b0, C9b3, D0, D1, D2, D3, D4, E1.0, E1.1, E1.2, E1.3, E1.4, E2, F1, H1.1, H1.2a, H1.2b, H1.2c, H1.2d, H1.3, H1.4a, H1.4b, H1.4c, H1.5, H10, H2, H2.0, H2.1, H2.2, H2.3, H2.4a, H2.4b, H2.5, H2.6, H3, H4, H5, H6, H7, H8, H9, HO0, HO1, HO2, HO3, HO4, HO5, HO6, HO7, HO8, HO9, M0, M1, M2, M3, M4, N1, N10, N11, N12, N13, N2, N3, N4, N5, N6, N7, N8, N9, P0.1.1, P0.1.10, P0.1.11, P0.1.12, P0.1.13, P0.1.14, P0.1.15, P0.1.2, P0.1.3, P0.1.4, P0.1.5, P0.1.6, P0.1.7, P0.1.8, P0.1.9, P0.2+, PF1/PF4, WA0, WA1, WA10, WA11, WA2, WA3, WA4, WA5, WA6, WA7, WA8, WA9, WA9a, substrate |

<!-- END GENERATED work-board-branches -->

## 8. The critical path

The longest chain of dependencies now runs through AIR-3.3 and NRS-1 and CCS's tranche D into its evaluator, and from there into formal methods and AIR's later phases.

```mermaid
flowchart LR
    Q1["AIR-3.3-Q1 decided"] --> AIR33["AIR-3.3 readings in SWRL and OWL"]
    AIR33 --> NRS1["NRS-1 condition composition acyclicity"]
    AIR33 --> CCS12["CCS-12 and CCS-13 evaluator"]
    NRS1 --> CCS12
    NRS1 --> CCS13a["CCS-13a joint satisfiability"]
    K93["CCS-9b.3 set comparisons"] --> K94["CCS-9b.4 qualifying rules"]
    K94 --> REST["CCS-9d, CCS-9c, CCS-8a"]
    REST --> CCS12
    K94 --> K16c["CCS-16c Party shares removed"]
    CCS12 --> FMB4["FMB-4 evaluation context"]
    FMB4 --> G["FM track G instrument assurance"]
    FMC3["FMC-3 slot exclusivity"] --> G
    CCS12 --> CLOSE["CCS-14 to CCS-17, epic close"]
    K16c --> CLOSE
    REST --> IMA3["IMA phase 3"]
    A130["ADR-A130 accepted"] --> ES45["Ensemble ES-4 and ES-5"]
    ES45 --> AIR71["AIR-7.1 programme module"]
    LG23["Ledger LG-2 and LG-3"] --> AIR71
    CBAA["Open CBAA integrates AIR 1 to 4"] --> AIR5["AIR phase 5"]
    LG23 --> AIR5
```

**Reading it.**

- **CCS-9b.3 and CCS-9b.4** gate the most work. CCS-9b.4, CCS-9d, CCS-9c, CCS-8a and CCS-16c, the evaluator, the epic's close, FMB-4 and FM track G, and IMA Phase 3 sit downstream. CCS-13a does not, since it is blocked on NRS-1 only.
- **AIR-3.3** is ready once AIR-3.3-Q1 is answered, since HQ-6a.2 has merged. It gates CCS-12 on the CCS board and NRS-1 on the NRS board, so the evaluator waits on it twice over.
- **ADR-A130** alone takes the three CCS held questions HQ-2 (second case), HQ-7 and HQ-12, and it is still Proposed. ADR-A131 is Accepted and Ledger's layer is on `main`, and Ledger takes PDD-07, not a CCS held question.
- **AIR-7.1** waits on Ensemble ES-4 and ES-5 and on Ledger LG-2 and LG-3, along with AIR-7.0, P7-Q5 and CCS's Instrument tranche. The ADRs are not the gate, the slices are.
- **AIR Phase 5** waits on Open CBAA's integration of phases 1 to 4 and on Ledger LG-3, which is planned. PDD-08, the evaluation context, is split and unowned per `status/ledger.md`, with its pieces going to a Quantification slice, LG-2 and PDD-13.

## 9. Decisions waiting

<!-- BEGIN GENERATED work-board-decisions. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Read from the registers in this tree: 34 Proposed decisions, 18 pending design decisions, 94 rows of [technical debt](technical-debt.md), and 35 slices named only in prose, listed by unit in the identifier exceptions baseline.

### 9.1 Proposed decisions

| Decision | Subject | Status |
|---|---|---|
| [A-48](../architecture/decisions/ADR-A48-transaction-boundary-catalogue.md) | Transaction boundary catalogue (replaces CAP framing) | Proposed |
| [A-50](../architecture/decisions/ADR-A50-role-profiled-deployment.md) | Role-profiled deployment | Proposed |
| [A-54](../architecture/decisions/ADR-A54-dataset-topology.md) | Dataset topology and named-graph layout | Proposed |
| [A-57](../architecture/decisions/ADR-A57-change-feed.md) | Change feed via write-side emission and reconciliation | Proposed |
| [A-59](../architecture/decisions/ADR-A59-partitioned-work-queue-abstraction.md) | `PartitionedWorkQueue` abstraction | Proposed |
| [A-62](../architecture/decisions/ADR-A62-spc-namespace-harmonisation.md) | SPC namespace harmonisation and integration deferral | Proposed |
| [A-63](../architecture/decisions/ADR-A63-project-vs-environment-scoping.md) | Project vs environment scoping | Proposed |
| [A-65](../architecture/decisions/ADR-A65-provenance-model.md) | Provenance model (named-graph-per-batch) | Proposed |
| [A-66](../architecture/decisions/ADR-A66-principal-model.md) | Principal model extension | Proposed |
| [A-67](../architecture/decisions/ADR-A67-bi-temporal-model.md) | Bi-temporal model | Proposed |
| [A-68](../architecture/decisions/ADR-A68-pii-and-erasure.md) | PII and erasure | Proposed |
| [A-69](../architecture/decisions/ADR-A69-pack-trust-and-safe-sparql-subset.md) | Pack trust model and safe SPARQL subset | Proposed |
| [A-71](../architecture/decisions/ADR-A71-platform-licence-and-spi-seam.md) | Platform licence (MPL-2.0) and SPI seam | Proposed |
| [A-74](../architecture/decisions/ADR-A74-graph-primary-realm-model.md) | One declared authority per kind of state | Proposed |
| [A-75](../architecture/decisions/ADR-A75-three-tier-store-spi.md) | Three-tier store SPI (Core/Extended/Native) | Proposed |
| [A-81](../architecture/decisions/ADR-A81-control-plane-http-runtime.md) | Control Plane HTTP runtime | Proposed |
| [A-82](../architecture/decisions/ADR-A82-framework-neutral-identity-pattern-selection.md) | Framework-neutral identity pattern selection | Proposed |
| [A-84](../architecture/decisions/ADR-A84-standalone-minting-libraries.md) | Standalone minting libraries | Proposed |
| [A-101](../architecture/decisions/ADR-A101-term-parameters.md) | Term parameters | Proposed |
| [A-108](../architecture/decisions/ADR-A108-multi-axis-temporal-scope.md) | Multi-axis temporal scope | Proposed |
| [A-109](../architecture/decisions/ADR-A109-importable-rule-body-fragment.md) | The importable rule-body fragment | Proposed |
| [A-116](../architecture/decisions/ADR-A116-vocabulary-scheme-composition.md) | Vocabulary scheme composition | Proposed |
| [A-118](../architecture/decisions/ADR-A118-word-authoring-proof-of-concept.md) | Word authoring proof of concept | Proposed |
| [A-119](../architecture/decisions/ADR-A119-xslt-transformation-sidecar.md) | Bidirectional XSLT transformation sidecar | Proposed |
| [A-128](../architecture/decisions/ADR-A128-efficient-queries-and-shapes.md) | Efficient queries and shapes | Proposed, 2026-10-17 |
| [A-130](../architecture/decisions/ADR-A130-ensemble-layer.md) | Ensemble, a substrate layer for relations between instruments | Proposed |
| [A-133](../architecture/decisions/ADR-A133-git-hooks.md) | Git hooks check what a change touches, never block a push, and gate the merge into `main` | Proposed, 2026-10-23 |
| [A-135](../architecture/decisions/ADR-A135-contract-first-wire-types.md) | Contract-first wire types | Proposed, 2026-10-26 |
| [A-144](../architecture/decisions/ADR-A144-odrl-import-through-mork.md) | The contract builder imports ODRL policies as proposals, through a MORK mapping | Proposed, 2026-10-29 |
| [A-147](../architecture/decisions/ADR-A147-skolem-rule-for-mapped-sources.md) | How a MORK run names a source's blank nodes: from the node that reaches each and its descr | Proposed, 2026-10-29 |
| [A-148](../architecture/decisions/ADR-A148-mork-transform-backends.md) | MORK mappings over XML and JSON compiled to an XSLT stylesheet writing N-Triples and a JOL | Proposed, 2026-10-30 |
| [A-149](../architecture/decisions/ADR-A149-publication-from-the-studio.md) | Explicit publication from the studio: each aggregate a version under ADR-A51's IRIs in a r | Proposed, 2026-10-31 |
| [A-151](../architecture/decisions/ADR-A151-the-work-board.md) | The work board: a slice's state written once on its home unit's board as a word and a day, | Proposed, 2026-11-02 |
| [A-150](../architecture/decisions/ADR-A150-performance-integration-and-load-testing.md) | Benchmark reports kept in git, components measured alone, topologies started isolated from | Proposed, 2026-10-31 |

### 9.2 Pending design decisions

Every row of [pending-design-decisions.md](pending-design-decisions.md), which loses a row when a sketch, plan or ADR settles it.

| Decision | Question |
|---|---|
| PDD-01 | Ownership, versioning and verification of InsurML components are not settled. |
| PDD-02 | Where the vocabulary and definition layers, with their SHACL rules, belong is not decided. |
| PDD-03 | How InsurML maps to InsurLE, and which tool checks that wording and code agree, is not decided. |
| PDD-04 | How one limit qualifies several relations. |
| PDD-05 | How meaning stated across several clauses is owned. |
| PDD-06 | Whether the persistence compiler gains a second IR that models SPARQL's semantics, between the configuration IR and the text. |
| PDD-08 | The rest of the evaluation context has no plan. |
| PDD-09 | A negotiation over a placement has no model. |
| PDD-10 | How LATTICE supports more than one language. |
| PDD-11 | Entry into force per holder, and the life of an offer before agreement. |
| PDD-12 | What mints a partitioned graph's IRI, and how a reader still knows its graph role. |
| PDD-13 | Whether the evaluation context gains a Datalog backend. |
| PDD-14 | Where a posting effective inside a sealed period goes. |
| PDD-15 | Whether a periodic amount is one account that resets or one account per period. |
| PDD-16 | A breaking change's release note must cite its decision (ADR-A113), and a README may cite only Accepted decisions (ADR-A127), so a note written while the decisi |
| PDD-17 | How the persistence compiler's default graph naming should answer Oxigraph reading every graph for the named-graph sweep. |
| PDD-18 | How a proposing agent, and a mapping, reach reference data the applied layers hold as `skos:Concept`s, such as an activity, a peril or a line of business. |
| PDD-19 | Whether generated code from the proofs becomes the evaluator itself, on several platforms, which PRI-47 and ADR-A-FM3 refuse as they stand. |

<!-- END GENERATED work-board-decisions -->

## 10. The maintainer's queue

In the order that unblocks the most work, proposed by the agent at each handoff and ordered by the maintainer. Rewritten 2026-11-02.

1. **WB-7 on the other live branches**: each merges `main`, runs `work:normalise`, `work:rename` and `build:work`, and marks its slices. `realign/config-authoring-studio` has done so.
2. **Review `realign/config-authoring-studio`**, the consolidated studio and persistence-delta work, with its regenerated expected profiles, the two ADR-A123 addenda of 2026-11-02 and its standards STD-308 to STD-316, then merge it and delete the two persistence replace branches.
3. **Bring `ccs-trunk` onto `main`** once its agent has the conflicts worked out.
4. **Accept or reject ADR-A151**, and the Proposed decisions section 9 lists, oldest first.
5. **Decide `persistence-mbt`**, its sections 5.5 and 5.6 against the conformance suite, and place H3.1, the code-generation spike, under the formal-methods epic or track H.
6. **Write the 34 board rows** section 9 counts as slices named only in prose, the ensemble's ten first, which needs a status record for the ensemble.
7. **Delete `config_studio_GD`** on the remote, which holds nothing `main` lacks.

## 11. Completed units

<!-- BEGIN GENERATED work-board-completed. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Every unit whose Status line reads merged, tagged or dropped and that no branch moves, with its slices, and a chart per group of their merged, tagged or dropped slices with a day, whatever its age.

| Unit | Kind | State | Slices | Last day |
|---|---|---|---|---|
| DESIGN_SKETCHES_INDEX | unit | dropped 2026-09-20 | 0 | 2026-09-20 |
| [config-studio](plans/config-studio.md) | unit | merged 2026-10-30 | 0 | 2026-10-30 |
| design-sketches-validation-summary | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| governance-surfaces | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| implementation-handover-historical | unit | dropped 2026-09-20 | 0 | 2026-09-20 |
| iri-patterns-post-3866b21-remediation | unit | merged 2026-09-23 | 0 | 2026-09-23 |
| llm-training-mtp | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| mork-package-split | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| mtp-execution | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| ontology-root-relocation | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-0-1-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-2-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-3-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-4-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-5-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| phase-6-handoff | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| platform-continuation | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| [rdf-sparql-patterns-remediation](plans/rdf-sparql-patterns-remediation.md) | plan | merged 2026-09-25 | 0 | 2026-09-25 |
| repository-topology-a77 | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| spc-package-split | unit | merged 2026-09-20 | 0 | 2026-09-20 |
| surface-mork-unified-projection | unit | merged 2026-09-22 | 0 | 2026-09-22 |
| surface-outstanding-items | unit | merged 2026-09-22 | 0 | 2026-09-22 |
| [toolchain-jdk25-python314](plans/toolchain-jdk25-python314.md) | unit | merged 2026-09-23 | 0 | 2026-09-23 |
| validation-pause-handover | unit | dropped 2026-09-20 | 0 | 2026-09-20 |
| validation-status | unit | merged 2026-09-20 | 0 | 2026-09-20 |

```mermaid
flowchart LR
    K1["building"]:::active --- K2["built or verified"]:::open --- K3["merged or tagged"]:::done --- K4["blocked"]:::crit
    classDef active fill:#4e9af1,stroke:#1f5fbf,color:#000
    classDef open fill:#f2c14e,stroke:#b8860b,color:#000
    classDef done fill:#8fcf8f,stroke:#2f7d32,color:#000
    classDef crit fill:#f28b82,stroke:#b23a30,color:#000
```

<!-- END GENERATED work-board-completed -->

## 12. Observations

These are findings from building this roadmap, offered as hypotheses for the maintainer to check. Rewritten 2026-11-02, when sections 1, 7, 9 and 11 became generated.

- **A slice named only in prose is invisible to the board.** 34 remain after `work:adopt`, listed by unit in the identifier exceptions baseline, and the git log names none of them as built. The ensemble's ten have no status record to carry a board at all.
- **Two branches numbered the same standards.** `docs/work-board` and `realign/config-authoring-studio` both took STD-300 upward on 2026-11-02, and both held a TD-137. `check:identifiers` dates a row by its day, so first in wins found a tie, and at the realign branch's merge of `main` the work board's rows kept their numbers and the realign rows became STD-308 to STD-316 and TD-139. A branch cannot know what another numbers until a fetch, and the board's `--fetch` is the moment to look.
- **The historic ids were the real cost.** Four of the five branch analyses asked for on 2026-11-02 were answered by content measurement in minutes, but the 34 track H ids took three passes to recognise as the packs' own spelling of boarded slices. A pack named by its slice closes that gap for new work.
- **H3.1 is not track H's H3.** The code-generation spike on `fml/isabelle-layers` is the formal-methods epic's FM-D10 decision at work, and the plan's H3 is the specification registry. A slice that borrows a number from a plan it does not belong to is read as that plan's.
- **The hand-written sections age with the epics.** Sections 2, 3, 4, 6 and 8 describe the epics' dependencies, layers, state and critical path as prose and diagrams, and each is refreshed at the events the lifecycle skill names, never by the tool. Where one disagrees with section 1, section 1 is right.
