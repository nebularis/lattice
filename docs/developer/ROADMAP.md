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

| Epic or unit | Kind | State | Next |
|---|---|---|---|
| [Computable contract substrate](plans/computable-contract-substrate.md) (CCS) | epic | 🚧 tranche D. C0 to CCS-9b.2 and HQ-6a merged and tagged | CCS-9b.3, then CCS-9b.4, C9d, C9c, C8a |
| [Applied insurance reference](plans/applied-insurance-reference.md) (AIR) | epic | 🚧 phases 0 and 1 done, 2 to 4 largely built, round 3 | AIR-3.3, the remaining trip slices, Phase 7 proposed on a branch |
| [Formal methods](plans/formal-methods.md) (FM) | epic | 🚧 tracks B, C, D, E in part, H well advanced | merge Track H's 0.19.0, then H3 onward |
| [Improved ontology documentation](plans/improved-ontology-documentation.md) (IOD) | unit | 🚧 most slices merged by squash 2026-10-20 | release tags for 0.18.0, OD-8 onward, OD-RC4 onward |
| Ensemble (plan on branch) | proposed unit | 📝 ADR-A130 Proposed | review of the plan and ADR |
| Ledger (plan on branch) | proposed unit | 📝 ADR-A131 Proposed | review of the plan and ADR |
| [InsurML alignment](plans/insurml-alignment.md) (IMA) | epic | 📝 proposed, nothing built | the maintainer's review and gate-0 decisions |
| [Normative rule substrate](plans/normative-rule-substrate.md) (NRS) | unit | 📝 most slices moved to CCS | the rule-language work, D1, D4, D5 |
| LATTICE tutorial (on `tutorial/guide`) | unit | 🟡 all four chapter slices written | the maintainer reads TUT-4 and accepts |
| [Identity minting](plans/identity-minting.md) | unit | 🚧 M0 to M3 done | M4, the walk-through from the specification |
| [Word authoring proof of concept](plans/word-authoring-poc.md) | unit | 🟡 WA-0 to WA-11 done | the manual Word checklist |
| [XSLT sidecar](plans/xslt-sidecar.md) | unit | 🔵 drafted | decisions XS-D1 to XS-D7 |
| [Documentation link repair](plans/documentation-link-repair.md) | unit | ⏳ not started | scheduling |
| [Platform programme](plans/lattice-platform-agentic-development-v0.2.md), phases 0 to 4 | epic | ⏳ Phase 0 decision pack Proposed | ratifying 17 Proposed ADRs |
| [Surface and MORK unified projection](plans/surface-mork-unified-projection-plan.md) | programme | ✅ phases 0 to 8. Phases 9 and 10 planned | not scheduled |

```mermaid
pie showData
    title Units by state, 2026-10-21
    "In progress" : 5
    "Awaiting review or acceptance" : 4
    "Proposed, nothing built" : 5
    "Planned, not started" : 3
    "Complete" : 15
```

The counts treat each epic as one unit and include the completed units of [section 11](#11-completed-units). In progress are CCS, AIR, FM, IOD and identity minting. Awaiting review are the tutorial, Word authoring, the Eligibility compiler and the governance surfaces. Proposed are Ensemble, Ledger, IMA, NRS and the platform programme. Planned are the XSLT sidecar, documentation link repair and the housekeeping first cut.


<!-- BEGIN GENERATED work-board-glance. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Built from the status records on 28 branches, the newest board day 2026-11-02.

| Unit | Kind | State | Next | Slices | Moved on |
|---|---|---|---|---|---|
| DESIGN_SKETCHES_INDEX | unit | ? |  | no board |  |
| [applied-insurance-reference](plans/applied-insurance-reference.md) | epic | ? |  | 6 planned, 2 merged, 1 ? | docs/work-board |
| [applied-ontology-readiness](plans/applied-ontology-readiness.md) | unit | ? |  | 18 built | docs/work-board |
| [computable-contract-substrate](plans/computable-contract-substrate.md) | multi-slice unit | ? | C16c | 35 merged, 7 blocked, 6 ?, 5 briefed, 3 planned, 3 verified | claude/config-studio-shape-forms, claude/config-studio-showcase-sample, claude/fix-topology-links, claude/nice-bohr-pmj43u-wwhgle, claude/ontology-config-authoring-cc050f, cs12b-authoring-domain, cs9-studio-operations, docs/work-board, spikes/pol-map, tutorial/guide, worktree-agent-a2c0b17126baf153a, worktree-agent-a410b8a2fd5d06b1a, worktree-agent-aa238440e880a9443, worktree-agent-ab5d87ccfb6876dee |
| [config-studio](plans/config-studio.md) | unit | ? |  | no board |  |
| design-sketches-validation-summary | unit | ? |  | no board |  |
| [documentation-link-repair](plans/documentation-link-repair.md) | unit | ? |  | no board |  |
| [eligibility-compiler](plans/eligibility-compiler.md) | unit | ? |  | no board |  |
| [formal-methods](plans/formal-methods.md) | epic | ? |  | 6 ?, 6 built | docs/work-board |
| [formal-methods-track-b](plans/formal-methods-track-b.md) | phase | ? |  | 7 ?, 5 built, 1 planned, 1 building | docs/work-board |
| [formal-methods-track-c](plans/formal-methods-track-c.md) | phase | ? |  | 6 ?, 3 built, 3 planned | docs/work-board |
| [formal-methods-track-e](plans/formal-methods-track-e.md) | phase | ? |  | 6 ?, 5 planned, 3 built, 1 dropped | docs/work-board |
| [formal-methods-track-h](plans/formal-methods-track-h.md) | phase | ? | H2.1 | 31 ?, 25 built, 15 merged, 14 planned, 5 verified, 2 briefed, 1 building | claude/persistence-delta-replace, claude/persistence-linear-replace, docs/work-board, realign/config-authoring-studio |
| [git-hooks](plans/git-hooks.md) | unit | ? | GH-0 | 5 built | docs/work-board |
| governance-surfaces | unit | ? |  | no board |  |
| [identity-minting](plans/identity-minting.md) | unit | ? |  | 5 ?, 4 built, 1 planned | docs/work-board |
| implementation-handover-historical | unit | ? |  | no board |  |
| [improved-ontology-documentation](plans/improved-ontology-documentation.md) | unit | ? | OD2 | 13 built, 11 ?, 10 planned, 10 verified, 1 merged | docs/work-board |
| [insurml-alignment](plans/insurml-alignment.md) | epic | ? |  | 8 planned | docs/work-board |
| iri-patterns-post-3866b21-remediation | unit | ? |  | no board |  |
| knowledge-index | unit | ? |  | no board |  |
| [ledger](plans/ledger.md) | unit | ? |  | no board |  |
| llm-training-mtp | unit | ? |  | no board |  |
| mork-package-split | unit | ? |  | no board |  |
| [mork-transforms](plans/mork-transforms.md) | multi-slice unit | ? |  | no board |  |
| mtp-execution | unit | ? |  | no board |  |
| [multi-store-conformance](plans/multi-store-conformance.md) | unit | ? | MSC-1 | 5 built |  |
| [normative-rule-substrate](plans/normative-rule-substrate.md) | multi-slice unit | ? |  | 13 ?, 7 blocked, 4 planned, 2 dropped | docs/work-board |
| [ontology-remediation](plans/ontology-remediation.md) | phase | ? | OR-1 | 21 built | docs/work-board |
| ontology-root-relocation | unit | ? |  | no board |  |
| [ontology-semantic-versioning](plans/ontology-semantic-versioning.md) | unit | ? |  | no board |  |
| [persistence-compiler-iri-sync](plans/persistence-compiler-iri-sync.md) | unit | ? |  | 7 ?, 6 built | docs/work-board, persistence-mbt |
| [persistence-delta-replace](plans/persistence-delta-replace.md) | multi-slice unit | ? |  | 3 built, 1 ? | claude/persistence-delta-replace, realign/config-authoring-studio |
| phase-0-1-handoff | unit | ? |  | no board |  |
| phase-0-status | unit | ? |  | 16 ?, 13 built, 3 planned | docs/work-board |
| phase-1-status | unit | ? |  | no board |  |
| phase-2-handoff | unit | ? |  | no board |  |
| phase-2-status | unit | ? |  | no board |  |
| phase-3-handoff | unit | ? |  | no board |  |
| phase-3-status | unit | ? |  | no board |  |
| phase-4-handoff | unit | ? |  | no board |  |
| phase-4-status | unit | ? |  | no board |  |
| phase-5-handoff | unit | ? |  | no board |  |
| phase-6-handoff | unit | ? |  | no board |  |
| platform-continuation | unit | ? |  | no board |  |
| [projection-maintenance](plans/projection-maintenance.md) | multi-slice unit | ? |  | no board |  |
| [python-test-melting](plans/python-test-melting.md) | unit | ? |  | no board |  |
| [rdf-sparql-patterns-remediation](plans/rdf-sparql-patterns-remediation.md) | plan | ? |  | no board |  |
| rdf-sparql-patterns-status | unit | ? |  | 3 ?, 2 built, 1 planned | docs/work-board |
| repository-topology-a77 | unit | ? |  | no board |  |
| spc-package-split | unit | ? |  | no board |  |
| [studio-publication](plans/studio-publication.md) | multi-slice unit in four phases | ? |  | no board |  |
| [studio-quality](plans/studio-quality.md) | multi-slice unit | ? |  | no board |  |
| surface-mork-unified-projection | unit | ? |  | no board |  |
| surface-outstanding-items | unit | ? |  | no board |  |
| [temporal-binding-consumer-hardening](plans/temporal-binding-consumer-hardening.md) | unit | ? |  | no board |  |
| [toolchain-jdk25-python314](plans/toolchain-jdk25-python314.md) | unit | ? |  | no board |  |
| validation-pause-handover | unit | ? |  | no board |  |
| validation-status | unit | ? |  | no board |  |
| vocabulary-temporal-binding | unit | ? |  | 4 ?, 2 built, 2 verified | docs/work-board |
| [word-authoring-poc](plans/word-authoring-poc.md) | multi-slice unit | ? |  | 13 built, 13 ? | docs/work-board |
| [xslt-sidecar](plans/xslt-sidecar.md) | multi-slice unit | ? |  | no board |  |

```mermaid
gantt
    title Dated slices, newest day 2026-11-02
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section applied-insurance-reference
    AIR-3.1 :done, air31, 2026-10-14, 2026-10-15
    AIR-3.2 :done, air32, 2026-10-14, 2026-10-15
    section computable-contract-substrate
    C9b0 Eligibility sources legal act :done, c9b0, 2026-10-10, 2026-10-11
    CCS-0 A-112 A-113 A-01 and ADR-A-C :active, ccs0, 2026-10-29, 2026-10-30
    CCS-1 A-104 :active, ccs1, 2026-10-29, 2026-10-30
    CCS-10 Behaviour split and layer flip :done, ccs10, 2026-10-10, 2026-10-11
    CCS-10a import guard :done, ccs10a, 2026-10-29, 2026-10-30
    CCS-11 runtime records occasions in :done, ccs11, 2026-10-10, 2026-10-11
    CCS-11a nested states history concur :done, ccs11a, 2026-10-10, 2026-10-11
    CCS-2 A-106 :active, ccs2, 2026-10-29, 2026-10-30
    CCS-3 Wording spec vocab and shapes :done, ccs3, 2026-10-10, 2026-10-11
    CCS-4 Wording tables assembly vari :done, ccs4, 2026-10-10, 2026-10-11
    CCS-5 Wording amendments law shapes :done, ccs5, 2026-10-10, 2026-10-11
    CCS-6 instrument terms the five re :done, ccs6, 2026-10-10, 2026-10-11
    CCS-7a regimes and gating split from :done, ccs7a, 2026-10-05, 2026-10-06
    CCS-7b terms in time :done, ccs7b, 2026-10-06, 2026-10-07
    CCS-7c what terms are and who they b :done, ccs7c, 2026-10-27, 2026-10-28
    CCS-8 values in stated meaning Word :done, ccs8, 2026-10-10, 2026-10-11
    CCS-8a set comparisons qualifying ru :active, ccs8a, 2026-10-27, 2026-10-28
    CCS-8b values in stated meaning Word :done, ccs8b, 2026-10-10, 2026-10-11
    CCS-9a amendments assents and taking :done, ccs9a, 2026-10-10, 2026-10-11
    CCS-9b.0 Eligibility sources legal act :done, ccs9b0, 2026-10-10, 2026-10-11
    CCS-9b.1 Eligibility sources legal act :done, ccs9b1, 2026-10-10, 2026-10-11
    CCS-9b.2 Eligibility sources legal act :done, ccs9b2, 2026-10-10, 2026-10-11
    CCS-9b.3 set comparisons qualifying ru :active, ccs9b3, 2026-10-27, 2026-10-28
    CCS-9b.4 set comparisons qualifying ru :active, ccs9b4, 2026-10-27, 2026-10-28
    CCS-9c set comparisons qualifying ru :active, ccs9c, 2026-10-27, 2026-10-28
    CCS-9d set comparisons qualifying ru :active, ccs9d, 2026-10-27, 2026-10-28
    CCS-F1 external and natural keys ADR :done, ccsf1, 2026-10-10, 2026-10-11
    HQ-6a.1 untimed closures ADR-A105 t :done, hq6a1, 2026-10-27, 2026-10-28
    HQ-6a.2 untimed closures ADR-A105 t :done, hq6a2, 2026-10-27, 2026-10-28
    section formal-methods
    FM-D0 environments :active, fmd0, 2026-10-06, 2026-10-07
    FM-D1 brief :active, fmd1, 2026-10-06, 2026-10-07
    FM-D2 Rocq track :active, fmd2, 2026-10-06, 2026-10-07
    FM-D3 Isabelle track :active, fmd3, 2026-10-06, 2026-10-07
    FM-D4 report :active, fmd4, 2026-10-10, 2026-10-11
    FM-PF1 fixes :active, fmpf1, 2026-10-07, 2026-10-08
    section formal-methods-track-b
    FMB-1 kernel and denotation :active, fmb1, 2026-10-09, 2026-10-10
    FMB-2 differential tests against the :active, fmb2, 2026-10-09, 2026-10-10
    FMB-2.1 harden the differential harnes :active, fmb21, 2026-10-09, 2026-10-10
    FMB-2.2 verify fix the scheme-less hie :active, fmb22, 2026-10-09, 2026-10-10
    FMB-3 Surface regeneration propert :active, fmb3, 2026-10-09, 2026-10-10
    FMB-5 measured mutation score :active, fmb5, 2026-10-09, 2026-10-10
    section formal-methods-track-c
    FMC-1 Alloy skeleton :active, fmc1, 2026-10-08, 2026-10-09
    FMC-2 scheme composition :active, fmc2, 2026-10-07, 2026-10-08
    FMC-2.1 well-formedness facts re-run :active, fmc21, 2026-10-08, 2026-10-09
    FMC-2.2 model the composed scheme dec :active, fmc22, 2026-10-08, 2026-10-09
    FMC-2.3 model ADR-A116 own rule ag :active, fmc23, 2026-10-08, 2026-10-09
    section formal-methods-track-e
    FME-1.0 home generation tooling :active, fme10, 2026-10-09, 2026-10-10
    FME-1.1 the kernel for real :active, fme11, 2026-10-06, 2026-10-07
    FME-1.2 rounding and residual theorem :active, fme12, 2026-10-07, 2026-10-08
    FME-1.4 harden the gate and the kernel :active, fme14, 2026-10-09, 2026-10-10
    section formal-methods-track-h
    FMH-1.1 prefix antichain and overlap c :active, fmh11, 2026-10-09, 2026-10-10
    FMH-1.2a witness harness audit witness :active, fmh12a, 2026-10-09, 2026-10-10
    FMH-1.2b witnesses for the refusals and :active, fmh12b, 2026-10-09, 2026-10-10
    FMH-1.2c witnesses for the 13 remaining :active, fmh12c, 2026-10-09, 2026-10-10
    FMH-1.2d refuse a multi-valued single-v :done, fmh12d, 2026-10-10, 2026-10-11
    FMH-1.3 static template checks S-3 and :done, fmh13, 2026-10-10, 2026-10-11
    FMH-1.4a refuse a composite boundary wi :done, fmh14a, 2026-10-10, 2026-10-11
    FMH-1.4b the declaration implementation :done, fmh14b, 2026-10-10, 2026-10-11
    FMH-1.4c a declaration the compiler can :done, fmh14c, 2026-10-10, 2026-10-11
    FMH-1.5 stable labels :done, fmh15, 2026-10-10, 2026-10-11
    FMH-2.0 ADR-A123 :active, fmh20, 2026-10-10, 2026-10-11
    FMH-2.1 the typed IR and its renderer :active, fmh21, 2026-10-12, 2026-10-13
    FMH-2.11a the Persistence README as a li :active, fmh211a, 2026-10-21, 2026-10-22
    FMH-2.11b the narrative the pictures t :active, fmh211b, 2026-10-21, 2026-10-22
    FMH-2.2 equivalence harness bootstra :active, fmh22, 2026-10-12, 2026-10-13
    FMH-2.3 named-graph row writers :active, fmh23, 2026-10-12, 2026-10-13
    FMH-2.4a the composite ports :active, fmh24a, 2026-10-13, 2026-10-14
    FMH-2.4b Oxigraph probes benchmark :active, fmh24b, 2026-10-13, 2026-10-14
    FMH-2.5 key claims audits guard D t :active, fmh25, 2026-10-23, 2026-10-24
    FMH-2.6 expected compiled profiles pa :active, fmh26, 2026-10-13, 2026-10-14
    FMH-2.6b event slots patch-log half he :active, fmh26b, 2026-10-14, 2026-10-15
    FMH-2.6c write disciplines :active, fmh26c, 2026-10-20, 2026-10-21
    FMH-2.6d patch log for in-place familie :active, fmh26d, 2026-10-20, 2026-10-21
    FMH-2.8c edges once faster members :active, fmh28c, 2026-10-20, 2026-10-21
    FMH-2.9 Mustache retired D-12 a go :active, fmh29, 2026-10-21, 2026-10-22
    FMH-HO0 correct the ownership note and :done, fmhho0, 2026-10-10, 2026-10-11
    FMH-HO1 composite replace payload to :done, fmhho1, 2026-10-10, 2026-10-11
    FMH-HO2 draft ADR-A122 Proposed :active, fmhho2, 2026-10-10, 2026-10-11
    FMH-HO3 dal vocabulary 0.3.0 dal :done, fmhho3, 2026-10-10, 2026-10-11
    FMH-HO4 ownership tree and path compil :done, fmhho4, 2026-10-10, 2026-10-11
    FMH-HO5 switch the compiler to the tre :done, fmhho5, 2026-10-10, 2026-10-11
    FMH-HO6 ownership refusals and the roo :done, fmhho6, 2026-10-10, 2026-10-11
    FMH-HO7 composite create and tombstone :done, fmhho7, 2026-10-10, 2026-10-11
    FMH-HO8 injective graph naming within :done, fmhho8, 2026-10-10, 2026-10-11
    FMH-HO9 ownership documentation and cl :done, fmhho9, 2026-10-10, 2026-10-11
    H2.11a :active, h211a, 2026-10-21, 2026-10-22
    H2.11b :active, h211b, 2026-10-21, 2026-10-22
    H2.12 :active, h212, 2026-11-01, 2026-11-02
    H2.6 :active, h26, 2026-10-13, 2026-10-14
    H2.6c :active, h26c, 2026-10-20, 2026-10-21
    H2.6d :active, h26d, 2026-10-20, 2026-10-21
    H2.9 :active, h29, 2026-10-21, 2026-10-22
    section git-hooks
    GH-0 :active, gh0, 2026-10-24, 2026-10-25
    GH-1 :active, gh1, 2026-10-24, 2026-10-25
    GH-2 :active, gh2, 2026-10-24, 2026-10-25
    GH-3 :active, gh3, 2026-10-24, 2026-10-25
    GH-4 :active, gh4, 2026-10-24, 2026-10-25
    section improved-ontology-documentation
    OD-0 ADRs the AGENTS.md rule the :active, od0, 2026-10-17, 2026-10-18
    OD-1 scanner and markers :active, od1, 2026-10-17, 2026-10-18
    OD-2 sections 1 to 3 :active, od2, 2026-10-18, 2026-10-19
    OD-3 section 6 to OWL :active, od3, 2026-10-18, 2026-10-19
    OD-4 section 6 to SHACL :active, od4, 2026-10-18, 2026-10-19
    OD-5 generated regions :active, od5, 2026-10-18, 2026-10-19
    OD-6 Eligibility pilot :active, od6, 2026-10-20, 2026-10-21
    OD-7 Vocabulary :active, od7, 2026-10-20, 2026-10-21
    OD-DOC1 published decisions :active, oddoc1, 2026-10-19, 2026-10-20
    OD-DOC2 site sections :done, oddoc2, 2026-10-20, 2026-10-21
    OD-DOC2b working documents out of publi :active, oddoc2b, 2026-10-20, 2026-10-21
    OD-ELC composition operation :active, odelc, 2026-10-19, 2026-10-20
    OD-MC1 migration check labels :active, odmc1, 2026-10-20, 2026-10-21
    OD-RC1 catalogue and reader :active, odrc1, 2026-10-17, 2026-10-18
    OD-RC2 consumers use the reader :active, odrc2, 2026-10-18, 2026-10-19
    OD-RC3 roots AGENTS.md table bypass :active, odrc3, 2026-10-19, 2026-10-20
    OD-REL first release 0.18.0 :active, odrel, 2026-10-20, 2026-10-21
    OD-VER1 one release for the substrate :active, odver1, 2026-10-20, 2026-10-21
    section insurml-alignment
    IMA-0.7 alignment edits :active, ima07, 2026-10-05, 2026-10-06
    section multi-store-conformance
    MSC-1 :active, msc1, 2026-10-27, 2026-10-28
    MSC-2 :active, msc2, 2026-10-27, 2026-10-28
    MSC-3 :active, msc3, 2026-10-27, 2026-10-28
    MSC-4 :active, msc4, 2026-10-27, 2026-10-28
    MSC-5 :active, msc5, 2026-10-27, 2026-10-28
    section normative-rule-substrate
    NRS-5 Closure declarations A-105 R :active, nrs5, 2026-10-10, 2026-10-11
    section ontology-remediation
    OR-0 :active, or0, 2026-10-28, 2026-10-29
    OR-1 :active, or1, 2026-10-28, 2026-10-29
    OR-10 :active, or10, 2026-10-28, 2026-10-29
    OR-11 :active, or11, 2026-10-28, 2026-10-29
    OR-12 :active, or12, 2026-10-28, 2026-10-29
    OR-13 :active, or13, 2026-10-28, 2026-10-29
    OR-14 OR-14 :active, or14, 2026-10-28, 2026-10-29
    OR-15 :active, or15, 2026-10-28, 2026-10-29
    OR-16 :active, or16, 2026-10-28, 2026-10-29
    OR-17 :active, or17, 2026-10-28, 2026-10-29
    OR-18 :active, or18, 2026-10-28, 2026-10-29
    OR-19 :active, or19, 2026-10-28, 2026-10-29
    OR-2 :active, or2, 2026-10-28, 2026-10-29
    OR-3 :active, or3, 2026-10-28, 2026-10-29
    OR-4 :active, or4, 2026-10-28, 2026-10-29
    OR-5 :active, or5, 2026-10-28, 2026-10-29
    OR-6 :active, or6, 2026-10-28, 2026-10-29
    OR-7 :active, or7, 2026-10-28, 2026-10-29
    OR-7b :active, or7b, 2026-10-28, 2026-10-29
    OR-8 OR-14 :active, or8, 2026-10-28, 2026-10-29
    OR-9 :active, or9, 2026-10-28, 2026-10-29
    section persistence-delta-replace
    DR1 :active, dr1, 2026-11-02, 2026-11-03
    DR2 :active, dr2, 2026-11-02, 2026-11-03
    section phase-0-status
    PLT-0.1.3 :active, plt013, 2026-10-10, 2026-10-11
    section word-authoring-poc
    WA-11 Documentation and close-out :active, wa11, 2026-10-10, 2026-10-11
    section work-board
    WB-0 the sketch the plan this rec :active, wb0, 2026-11-02, 2026-11-03
    WB-1 tools work board.py work b :active, wb1, 2026-11-02, 2026-11-03
    WB-2 the slice grammar work renam :active, wb2, 2026-11-02, 2026-11-03
    WB-3 INDEX.md replaced ROADMAP.md :active, wb3, 2026-11-02, 2026-11-03
```

<!-- END GENERATED work-board-glance -->

## 2. How the epics depend on one another

Arrows point from the work that must come first. A dashed arrow is a dependency that is planned or proposed, not yet in force.

```mermaid
flowchart LR
    FM["Formal methods"]
    CCS["Computable contract substrate"]
    AIR["Applied insurance reference"]
    NRS["Normative rule substrate"]
    IMA["InsurML alignment"]
    IOD["Ontology documentation"]
    ENS["Ensemble"]
    LDG["Ledger"]
    PLAT["Platform programme"]
    TUT["Tutorial"]
    CBAA["Open CBAA, downstream"]

    FM -->|"Eligibility pass for CCS-9b.3"| CCS
    CCS -->|"HQ-6a closures for AIR-3.3"| AIR
    CCS -->|"C12 evaluator for track B4"| FM
    NRS -->|"N1 for C12 and C13"| CCS
    CCS -->|"C9 for phase 3"| IMA
    AIR -->|"phases 1 to 4"| CBAA
    CBAA -.->|"integration gates AIR phase 5"| AIR
    CCS -.->|"hands over HQ-2, HQ-7, HQ-12"| ENS
    ENS -.->|"programmes and vehicles for phase 7"| AIR
    LDG -.->|"accounts for Behaviour, PDD-07"| CCS
    LDG -.->|"allocation for phase 7"| AIR
    IOD -->|"literate layout and one release"| CCS
    IOD -->|"literate layout and one release"| AIR
    IOD -->|"OD-DOC3 reviews it"| TUT
```

## 3. The layers, now and proposed

The substrate's import order on `main` (ADR-A01 and its addenda, ADR-A106, ADR-A112), with the two layers proposed on `docs/placement-vehicles-structure` drawn dashed. Where the new layers sit is taken from their plans (Ensemble imports Instrument and Behaviour's runtime, Ledger is imported by Behaviour's configuration). ADR-A01's addenda of 2026-10-18 and 2026-10-19 on that branch settle the order, and both are Proposed.

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
    LDG["Ledger, proposed"] -.-> BC
    I -.-> ENS["Ensemble, proposed"]
    BR -.-> ENS
    I --> APP["Applied modules"]
    ENS -.-> APP
```

Persistence, Surface and MORK sit beside the substrate. They are versioned on their own and consumed by the toolchains.

## 4. Active epics

### 4.1 Computable contract substrate (CCS)

**Documents.** [plan](plans/computable-contract-substrate.md), [status](status/computable-contract-substrate.md), [sketch](sketches/computable-contract-substrate.md). ADRs A-104 to A-106 and A-112 to A-115 and A-120 accepted.

**Where it is.** Gate A passed on 2026-10-01. Tranches B (Wording) and C (Behaviour split, nested states) are merged and tagged. In tranche D, C6 to CCS-9b.2 and the closures work HQ-6a.1 and HQ-6a.2 (ADR-A105) are merged, and `executable-v0.7.0` is tagged. The status record's own header still names the HQ-6a.2 merge as the next action. Its branch has no commit left that `main` lacks, so that action is done.

```mermaid
flowchart LR
    subgraph A["Tranche A, decisions"]
        C0["C0 to C2"]
    end
    subgraph B["Tranche B, Wording"]
        C3["C3 to C5"]
    end
    subgraph C["Tranche C, Behaviour"]
        C10["C10, C10a, C11, C11a"]
    end
    subgraph D["Tranche D, Instrument"]
        C6["C6 to C8b"] --> C9a["C9a"] --> C9b["CCS-9b.0 to CCS-9b.2"] --> HQ6["HQ-6a.1, HQ-6a.2"]
        HQ6 --> CCS-9b.3["CCS-9b.3"] --> CCS-9b.4["CCS-9b.4"]
        CCS-9b.4 --> C9rest["C9d, C9c, C8a"]
    end
    subgraph E["Tranche E, evaluation"]
        C12["C12, C13"]
        C13a["C13a"]
    end
    subgraph F["Tranche F, close"]
        C16c["C16c"]
        C14["C14 to C17"]
    end
    A --> B --> C --> D
    C9rest --> C12
    CCS-9b.4 --> C16c
    C12 --> C14

    classDef done fill:#d8f0d8,stroke:#3a7d3a
    classDef next fill:#fff1c2,stroke:#a07800
    classDef wait fill:#eeeeee,stroke:#888888
    class C0,C3,C10,C6,C9a,C9b,HQ6 done
    class CCS-9b.3 next
    class CCS-9b.4,C9rest,C12,C13a,C16c,C14 wait
```

**What it waits on.** CCS-9b.3 waits on HQ-6 (NRS N5, ADR-A105), and the formal-methods Eligibility pass it named is built. C12 and C13 wait on C9, C11a, AIR-3.3 and NRS N1. C13a waits on C5 and NRS N1. C16c, removing Party's shares, must land before the epic closes.

**Held questions.** HQ-1 to HQ-12, in the plan. Three are proposed for hand-over to the Ensemble unit (HQ-2's second case, HQ-7, HQ-12) once ADR-A130 is accepted.

### 4.2 Applied insurance reference (AIR)

**Documents.** [epic plan](plans/applied-insurance-reference.md), [status](status/applied-insurance-reference.md), [lanes](plans/applied-insurance-reference-lanes.md), [claims plan](plans/applied-insurance-reference-claims.md), [substrate plan](plans/applied-insurance-reference-substrate.md), [leftovers](plans/air-leftovers.md).

**How it runs.** Two machines (lanes §2 to §4). Machine R verifies and merges, and also builds CCS. Machine S builds the slices in one trip on one branch, `air/applied-reference`, which is merged into `main`. Its only commits not on `main` are two merges and one attribution fix.

**Where it is.**

| Phase | Plan | State |
|---|---|---|
| 0 Decisions | [plan](plans/applied-insurance-reference-phase-0.md) | ✅ complete |
| 1 Module split | [plan](plans/applied-insurance-reference-phase-1.md) | ✅ AIR-1.1 and AIR-1.2 merged |
| 2 Peril vocabulary | [plan](plans/applied-insurance-reference-phase-2.md) | 🚧 AIR-2.0 to 2.4 and 2.6 built, the cause scheme at 287 concepts in eight families. 2.5 and 2.7 ready |
| 3 Readings and crosswalks | [plan](plans/applied-insurance-reference-phase-3.md) | 🚧 AIR-3.1 and 3.2 merged. 3.3 waits on AIR-3.3-Q1. 3.4 and 3.5 ready |
| 4 Exposure | [plan](plans/applied-insurance-reference-phase-4.md) | 🚧 AIR-4.1 to 4.4 built. 4.5 and 4.6 ready |
| 5 Contract module | [plan](plans/applied-insurance-reference-phase-5.md) | 🅿️ deferred until Open CBAA integrates phases 1 to 4 (decision D2) |
| 6 Submission, claims | [plan](plans/applied-insurance-reference-phase-6.md), [claims](plans/applied-insurance-reference-claims.md) | ⏳ AIR-6.1 ready |
| 7 Placement and capital | on `docs/placement-vehicles-structure` | 📝 proposed 2026-10-18, no slice briefed |

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

**Phase 7, proposed.** A programme data model (towers, layers, lines and their formation state), market responses from decline to binding quote, risk-capital vehicles, and the London market's MRC form as a specialisation. It rests on Ensemble (ADR-A130) and Ledger (ADR-A131), both Proposed. It records and evaluates programmes. It does not advise on them.

### 4.3 Formal methods (FM)

**Documents.** [epic plan](plans/formal-methods.md), [epic status](status/formal-methods.md), [lifecycle guide](formal-methods-lifecycle.md). ADR-A-FM1 to ADR-A-FM4 accepted. The prover is Isabelle/HOL, with Haskell and Scala as code-generation targets.

| Track | Subject | State |
|---|---|---|
| D | prover spike | ✅ done, two Gate D criteria open |
| A | ledger and harness | ⏳ not started, waits on Gate D and its ADR |
| B | reference semantics and oracle | 🚧 B1 to B3, FMB-2.1, FMB-2.2 done. B4 waits on CCS C12. B5 blocked |
| C | design-time models | 🚧 C1, C2, FMC-2.1 done. C3 is next. ADR-A116 Proposed |
| E | prover programme | 🚧 FME-1.0, FME-1.1, FME-1.4 done. FME-1.3 waits on track C2's overlap-rule ADR |
| F | native tooling | ⏳ not started |
| G | instrument assurance | ⏳ waits on B4 and C3 |
| H | Persistence | 🚧 H1, FMH-HO0 to FMH-HO9, FMH-2.0 to FMH-2.6b on `main`. Every other planned H2 slice built on `claude/nice-bohr-pmj43u` |

```mermaid
flowchart LR
    D["D prover spike"] --> A["A ledger and harness"]
    D --> E["E prover programme"]
    B["B reference semantics"] --> B4["B4 evaluation context"]
    CCS12["CCS C12"] --> B4
    C["C design-time models"] --> C3["C3 slot exclusivity"]
    B4 --> G["G instrument assurance"]
    C3 --> G
    F["F native tooling"]
    H["H Persistence"] --> H3["H3 onward"]

    classDef done fill:#d8f0d8,stroke:#3a7d3a
    classDef doing fill:#fff1c2,stroke:#a07800
    classDef todo fill:#eeeeee,stroke:#888888
    class D done
    class B,C,E,H doing
    class A,B4,C3,G,F,H3,CCS12 todo
```

**Track H, the release branch.** `claude/nice-bohr-pmj43u` holds 54 commits beyond `main`: FMH-2.6c to H2.6g, FMH-2.7, H2.8a to FMH-2.8c, FMH-2.9, FMH-2.11a and FMH-2.11b (the Persistence README in the literate layout), the test-suite work FMH-TS-1 and FMH-TS-2, a new `packages/persistence/python`, Oxigraph as the Persistence tests' default engine, and the release prepared as 0.19.0 with the applied modules re-pinned. Six review items (Q1 to Q6 in its status record) wait on the maintainer before the merge. `claude/nice-bohr-pmj43u-wwhgle` is an earlier point of the same line, with nothing the release branch lacks.

### 4.4 Improved ontology documentation (IOD)

**Documents.** [plan](plans/improved-ontology-documentation.md), [status](status/improved-ontology-documentation.md). ADR-A126 and ADR-A129 published, ADR-A127 accepted.

**Where it is.** `docs/literate-v2` was squash-merged into `main` on 2026-10-20 (`cf1b8eb`). That brought the repository catalogue and its reader (OD-RC1 to OD-RC3), the literate README layout and its compilers to OWL and SHACL (OD-1 to OD-5), the Eligibility and Vocabulary pilots (OD-6, OD-7), published decisions and the site sections (OD-DOC1, OD-DOC2, OD-DOC2b), and one release number for the substrate and standalone ontologies, 0.18.0 (VER1, OD-REL). `GOVERNANCE.md` and the validation and test plan were retired in the same change.

**Next.** The tag `ontologies-v0.18.0` and the applied modules' ten tags do not exist on the remote yet. OD-8 onward migrates the remaining layers one at a time. OD-RC4 to OD-RC6 extend the catalogue downstream, promote packages and fold in the XML catalogue (OD-RC6 needs a new ADR on ADR-A88). OD-DOC3 reviews the tutorial once it is merged.

### 4.5 Ensemble and Ledger, proposed substrate layers

Both are on `docs/placement-vehicles-structure`, with their sketches, for the maintainer's review. No slice is briefed.

| | Ensemble | Ledger |
|---|---|---|
| Prefix and home | `ens:`, `ontology/ensemble/` | `ldg:`, `ontology/ledger/` |
| ADR | A-130, Proposed | A-131, Proposed |
| Holds | identities naming member instruments by role, reified relations between instruments (kinds K1 to K8), judgements across an ensemble, confidentiality between members, evaluation by composition | account definitions and their tree, postings and balance records, allocation with conservation, Behaviour's migration from allowances to accounts |
| Takes over | CCS HQ-2 (second case), HQ-7, HQ-12 | PDD-07 and the ledger part of PDD-08 |
| Serves | AIR Phase 7, AIR-6.8's cross-instrument reads | AIR Phase 7, Behaviour's threshold regimes |

### 4.6 InsurML alignment (IMA)

**Documents.** [epic plan](plans/insurml-alignment.md), [phase 0](plans/insurml-alignment-phase-0.md), [status](status/insurml-alignment.md), [vision](../architecture/insurml-alignment-vision.md).

Nothing is built. Nine phases are planned, from decisions (Phase 0) through the InsurML profile, lift and lower kits, Wording changes, an assembly interface, meaning over components, authoring and exchange, library ingestion, to continuous standards engagement. Phase 3 waits on CCS C9. One slice, IMA-3.3, already moved into CCS as C8b. PDD-01 to PDD-03 hold its ownership and tooling questions.

### 4.7 Normative rule substrate (NRS)

**Documents.** [plan](plans/normative-rule-substrate.md), [status](status/normative-rule-substrate.md).

Nothing is built in this unit. CCS took N1, N2, N4, N5 and the Behaviour part of N8, and absorbed N6 and N8 into C12 and C13 (NQ-1 to NQ-4, 2026-10-10). NRS keeps the rule-language integration work (LegalRuleML), with decisions D1, D4 and D5 open and ADRs A-107 to A-111 reserved, not drafted. N9 changes Foundation and must wait for AIR Phase 2 to finish.

## 5. Smaller units

| Unit | Documents | State | Next |
|---|---|---|---|
| LATTICE tutorial | `docs/developer/plans/lattice-tutorial.md` on `tutorial/guide` | TUT-0 to TUT-3 committed on the branch, TUT-4 written | the maintainer reads chapters 10 to 13 and the tutorial end to end, adds the AI disclosure trailer to the branch's commits, and pushes |
| Identity minting | [plan](plans/identity-minting.md), [status](status/identity-minting.md) | M0 to M3 complete (Python and Java libraries, anchor vectors) | M4, the specification completed and walked through by hand. ADR-A84 Proposed |
| Word authoring proof of concept | [plan](plans/word-authoring-poc.md), [status](status/word-authoring-poc.md) | WA-0 to WA-11 done | the manual Word checklist M1 to M14. ADR-A118 Proposed |
| XSLT sidecar | [plan](plans/xslt-sidecar.md), [status](status/xslt-sidecar.md) | drafted | XS-D1 to XS-D7. ADR-A119 Proposed |
| Documentation link repair | [plan](plans/documentation-link-repair.md), [status](status/documentation-link-repair.md) | not started. Baseline 419 broken links, 290 in ignored site output | scheduling. The IOD site work may have moved the baseline |
| Eligibility compiler | [plan](plans/eligibility-compiler.md), [status](status/eligibility-compiler.md) | implemented, awaiting validation in a networked environment | validation |
| Governance surfaces | [plan](plans/governance-surfaces-integration.md), [status](status/governance-surfaces.md) | fixture-backed UI shells | backend integration, three slices |
| Housekeeping first cut | [RDF/SPARQL phase plan](plans/rdf-sparql-patterns-phase-plan.md) slice 3 | not started | scheduling. ADR-A80 accepted |
| MORK shared reader | `tools/mork_rdf/README.md` §19, TD-124 | not started. `mork_rdf` (on `claude/config-authoring-studio`) and `mork2rml` read MORK separately | once `mork2rml` moves to W3C RML, one reader for both backends, which also holds the logical run plan ([sketch](sketches/mork-run-planner.md) §9) |
| MORK run planner | [sketch](sketches/mork-run-planner.md) | options A and B agreed, MP-Q3 proposed | the benchmark (MP-Q1), then release by count and a pluggable sink |
| MORK runtime of our own | [sketch](sketches/mork-run-planner.md) options E and F | not started, low priority | PDD-06's SPARQL IR first. A partitioned and possibly native runtime, `Flux.IO` a candidate base |
| MORK transform backends | [plan](plans/mork-transforms.md), [status](status/mork-transforms.md) | in progress | XSLT and JOLT from a mapping graph, run by an existing engine as RML output is (ADR-A148, Proposed). An ingress endpoint that writes to the graph SPI is not planned |
| MORK studio module | none yet | not started, after the MORK compiler | a mapping editor in the studio, placed as an ETL tool: a schema or data on the left, the pipeline of mappings drawn on the right, compilation to each backend, a step function that simulates a payload through the mappings, and `propose`, which asks a language model for mappings with MCN and MTP, hypotheses to accept or reject and uncertain mappings to complete by hand |
| MORK proposals by an agent | none yet | not started, after the studio module | the studio's MORK proposals offered to Claude Desktop through the studio's MCP server, first tried on the ODRL mapping scheme with a sub-agent given MCN and MTP, and MTP refined from what it gets right and wrong |
| Studio API path review | `contracts/config-studio/README.md`, the API table | not started, asked for by the maintainer on 2026-10-29 | review every path of the studio's HTTP API for naming and shape together, starting from `GET /api/features`, which reads oddly, before the API is relied on outside the studio |
| Policy mapping spike | `spikes/policy-mapping/` on `spikes/pol-map` | spike, two commits | the maintainer's decision whether to keep it |

## 6. The platform programme

**Documents.** [epic plan](plans/lattice-platform-agentic-development-v0.2.md), phase plans [0](plans/phase-0-plan.md) to [4](plans/phase-4-plan.md), status records [0](status/phase-0-status.md) to [4](status/phase-4-status.md), [continuation status](status/platform-continuation.md).

The first platform build (the earlier phases 0 to 6: Surface lifecycle and ledger, workers, release integration, OCI adapter, projection lowering, MORK review and governance queue) is authored and accepted with recorded residuals. The new programme's phases are sequential, and none has started a code slice.

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

Phase 0's decision pack drafted 17 ADRs on 2026-09-23 (A-48, A-50, A-51, A-54, A-57, A-59, A-62, A-63, A-65 to A-69, A-71, A-74, A-75, A-81). All are Proposed, and A-51 is superseded by A-82, also Proposed. Phase 1 cannot start until Phase 0's exit gate passes. Phases 2 and 3 are rolling-wave placeholders, and Phase 4 is sized only after Phase 3's measurements.

## 7. Branches

Branches with commits that `main` does not have, as of 2026-10-21.

| Branch | Commits ahead | Behind `main` | Holds | Disposition |
|---|---|---|---|---|
| `claude/nice-bohr-pmj43u` | 54 | 0 | FM Track H, release 0.19.0 prepared | review Q1 to Q6, then merge and tag |
| `claude/nice-bohr-pmj43u-wwhgle` | 45 | 0 | an earlier point of the same line | retire after the release branch merges |
| `docs/placement-vehicles-structure` | 8 | 1 | AIR Phase 7, Ensemble and Ledger plans, ADR-A130, ADR-A131, four sketches | review |
| `docs/literate-v2` | 27 | 2 | the original commits of IOD, squash-merged as `cf1b8eb` | retire, or keep for history |
| `tutorial/guide` | 5 | 75 | the tutorial, TUT-0 to TUT-4 | acceptance, then merge |
| `air/applied-reference` | 3 | 17 | two merges and one attribution fix | merge the fix or retire |
| `spikes/pol-map` | 2 | 39 | the policy mapping spike | decide |
| `architecture-principles` | 1 and this roadmap | 17 | the draft architecture principles | review |
| `ccs/c7a-regimes` | 3 | 331 | C7a's pre-merge commits. C7a reached `main` as `c6e5853` | retire |
| `persistence-mbt` | 1 | 451 | a sketch for a model-based testing utility | decide |

```mermaid
flowchart RL
    MAIN(["main, a19e6dd"])
    H["claude/nice-bohr-pmj43u, Track H 0.19.0"] -->|"to merge"| MAIN
    PV["docs/placement-vehicles-structure, AIR 7, Ensemble, Ledger"] -->|"to review"| MAIN
    TUT["tutorial/guide"] -->|"to accept"| MAIN
    AP["architecture-principles"] -->|"to review"| MAIN
    SP["spikes/pol-map"] -.->|"to decide"| MAIN
    LIT["docs/literate-v2"] -.->|"squash-merged"| MAIN
```

About 30 further branches have no commit that `main` lacks. They are merged slice branches (the AIR round 1 and 2 branches, the CCS slice branches, the FM branches, `test/slow-py`, `ux/auth-le`, `poc/word-ux`, `agents/private-overlay`, `cloud-setup-apt-fix`) or older experiments, and can be deleted when the maintainer chooses.


<!-- BEGIN GENERATED work-board-branches. Written by `mise run build:roadmap` from the status records on every branch. Edit a status record, never this region. -->

Branches with a commit `main` lacks, from the same reading.

| Branch | Tip | Ahead of main | Upstream | Moves |
|---|---|---|---|---|
| `ccs-trunk` | 2026-10-29 | 53 | pushed | no mark |
| `claude/config-authoring-studio` | 2026-11-02 | 151 | pushed | no mark |
| `claude/config-studio-shape-forms` | 2026-10-28 | 18 | local only | C9b3 |
| `claude/config-studio-showcase-sample` | 2026-10-28 | 18 | local only | C9b3 |
| `claude/fix-topology-links` | 2026-10-23 | 1 | pushed | C9b3 |
| `claude/nice-bohr-pmj43u-wwhgle` | 2026-10-20 | 45 | pushed | C9b3 |
| `claude/persistence-delta-replace` | 2026-11-02 | 137 | pushed | DR1, DR2, DR3, H2.12 |
| `claude/persistence-linear-replace` | 2026-11-01 | 135 | pushed | H2.12 |
| `cs12b-authoring-domain` | 2026-10-28 | 7 | local only | C9b3 |
| `cs9-studio-operations` | 2026-10-28 | 8 | local only | C9b3 |
| `docs/placement-vehicles-structure` | 2026-11-02 | 113 | pushed | no mark |
| `docs/work-board` | 2026-11-02 | 8 | local ahead 1, not pushed | AIR-3.1, AIR-3.2, AIR-3.3, AIR-S1, AIR-S2, AIR-S4, AIR-S5, AIR-S7, AOR-1, AOR-10, AOR-11, AOR-12, AOR-13, AOR-14, AOR-15, AOR-16, AOR-17, AOR-2, AOR-3, AOR-3b, AOR-4, AOR-5, AOR-6, AOR-7, AOR-8, AOR-9, CCS-0, CCS-1, CCS-10, CCS-10a, CCS-11, CCS-11a, CCS-12, CCS-13, CCS-13a, CCS-14, CCS-15, CCS-16, CCS-16c, CCS-17, CCS-2, CCS-3, CCS-4, CCS-5, CCS-6, CCS-7a, CCS-7b, CCS-7c, CCS-8, CCS-8a, CCS-8b, CCS-9a, CCS-9b.0, CCS-9b.1, CCS-9b.2, CCS-9b.3, CCS-9b.4, CCS-9c, CCS-9d, CCS-F1, FM-D0, FM-D1, FM-D2, FM-D3, FM-D4, FM-PF1, FMB-1, FMB-2, FMB-2.1, FMB-2.2, FMB-3, FMB-4, FMB-5, FMC-1, FMC-2, FMC-2.1, FMC-2.2, FMC-2.3, FMC-3, FME-1.0, FME-1.1, FME-1.2, FME-1.3, FME-1.4, FME-2, FME-3, FME-4, FME-5, FMH-1.1, FMH-1.2a, FMH-1.2b, FMH-1.2c, FMH-1.2d, FMH-1.3, FMH-1.4a, FMH-1.4b, FMH-1.4c, FMH-1.5, FMH-10, FMH-2, FMH-2.0, FMH-2.1, FMH-2.11a, FMH-2.11b, FMH-2.2, FMH-2.3, FMH-2.4a, FMH-2.4b, FMH-2.5, FMH-2.6, FMH-2.6b, FMH-2.6c, FMH-2.6d, FMH-2.7, FMH-2.8, FMH-2.8c, FMH-2.9, FMH-3, FMH-4, FMH-5, FMH-6, FMH-7, FMH-8, FMH-9, FMH-HO0, FMH-HO1, FMH-HO2, FMH-HO3, FMH-HO4, FMH-HO5, FMH-HO6, FMH-HO7, FMH-HO8, FMH-HO9, GH-0, GH-1, GH-2, GH-3, GH-4, HQ-6a.1, HQ-6a.2, IM-0, IM-1, IM-2, IM-3, IM-4, IMA-0.1, IMA-0.2, IMA-0.3, IMA-0.4, IMA-0.5, IMA-0.6, IMA-0.7, IMA-0.8, NRS-1, NRS-10, NRS-11, NRS-12, NRS-13, NRS-2, NRS-3, NRS-4, NRS-5, NRS-6, NRS-7, NRS-8, NRS-9, OD-0, OD-1, OD-2, OD-3, OD-4, OD-5, OD-6, OD-7, OD-8, OD-DOC1, OD-DOC2, OD-DOC2b, OD-DOC3, OD-ELC, OD-MC1, OD-RC1, OD-RC2, OD-RC3, OD-RC4, OD-RC5, OD-RC6, OD-REL, OD-VER1, OR-0, OR-1, OR-10, OR-11, OR-12, OR-13, OR-14, OR-15, OR-16, OR-17, OR-18, OR-19, OR-2, OR-3, OR-4, OR-5, OR-6, OR-7, OR-7b, OR-8, OR-9, PCI-1, PCI-2, PCI-3, PCI-4, PCI-5, PCI-6, PLT-0.1.1, PLT-0.1.10, PLT-0.1.11, PLT-0.1.12, PLT-0.1.13, PLT-0.1.14, PLT-0.1.15, PLT-0.1.2, PLT-0.1.3, PLT-0.1.4, PLT-0.1.5, PLT-0.1.6, PLT-0.1.7, PLT-0.1.8, PLT-0.1.9, PLT-0.2r, RSP-1, RSP-2, RSP-3, VTB-1, VTB-2, VTB-3, VTB-4, WA-0, WA-1, WA-10, WA-11, WA-2, WA-3, WA-4, WA-5, WA-6, WA-7, WA-8, WA-9, WA-9a, WB-0, WB-1, WB-2, WB-3, WB-4, WB-5, WB-6, WB-7 |
| `fml/isabelle-layers` | 2026-11-01 | 31 | pushed | no mark |
| `main-xg1czj` | 2026-10-31 | 1 | remote only | no mark |
| `persistence-mbt` | 2026-09-23 | 1 | pushed | 7 |
| `realign/config-authoring-studio` | 2026-11-02 | 154 | pushed | DR1, DR2, DR3, DR4, H2.12 |
| `spikes/pol-map` | 2026-10-16 | 2 | pushed | C9b3 |
| `tutorial/guide` | 2026-10-16 | 5 | remote only | C9b3 |

<!-- END GENERATED work-board-branches -->

## 8. The critical path

The longest chain of dependencies now runs through CCS's tranche D into its evaluator, and from there into formal methods and AIR's later phases.

```mermaid
flowchart LR
    Q1["AIR-3.3-Q1 decided"] --> AIR33["AIR-3.3 readings in SWRL and OWL"]
    CCS-9b.3["CCS-9b.3 set comparisons"] --> CCS-9b.4["CCS-9b.4 qualifying rules"]
    CCS-9b.4 --> C9["C9d, C9c, C8a"]
    N1["NRS N1, now in CCS"] --> C12["CCS C12 and C13 evaluator"]
    C9 --> C12
    AIR33 --> C12
    C12 --> B4["FM track B4"]
    B4 --> G["FM track G instrument assurance"]
    C12 --> C14["CCS C14 to C17, epic close"]
    CCS-9b.4 --> C16c["C16c Party shares removed"]
    C16c --> C14
    C9 --> IMA3["IMA phase 3"]
    A130["ADR-A130 and ADR-A131 accepted"] --> AIR7["AIR phase 7"]
    CBAA["Open CBAA integrates AIR 1 to 4"] --> AIR5["AIR phase 5"]
    EC["evaluation context planned, PDD-08"] --> AIR5
```

**Reading it.**

- **CCS-9b.3 and CCS-9b.4** gate the most work. Every CCS slice after them, the evaluator, the epic's close, FM tracks B4 and G, and IMA Phase 3 sit downstream.
- **AIR-3.3** is ready once AIR-3.3-Q1 is answered, since HQ-6a.2 has merged. It must land before CCS C12.
- **ADR-A130 and ADR-A131** gate AIR Phase 7 and the three CCS held questions they take over.
- **AIR Phase 5** waits on two things outside this repository's slices: Open CBAA's integration of phases 1 to 4, and a plan for the evaluation context (PDD-08), which the Ledger plan partly supplies.

## 9. Decisions waiting

### 9.1 Proposed ADRs

| ADRs | Subject | Raised by |
|---|---|---|
| A-48, A-50, A-54, A-57, A-59, A-62, A-63, A-65 to A-69, A-71, A-74, A-75, A-81 | the platform's Phase 0 decision pack | platform programme |
| A-82, A-84 | identity patterns and standalone minting libraries | identity minting |
| A-116 | Vocabulary scheme composition, which CCS HQ-4 and IMA-D4a wait on | FM track C |
| A-118, A-119 | Word authoring, XSLT sidecar | their units |
| A-128 | efficient queries and shapes | Track H |
| A-130, A-131, and ADR-A01's addenda of 2026-10-18 and 2026-10-19 | Ensemble and Ledger | on `docs/placement-vehicles-structure` |
| A-CAP1, A-CAP2 | capacity runtime profile and promotion criteria | applied capacity |

### 9.2 Pending design decisions

[pending-design-decisions.md](pending-design-decisions.md) holds PDD-01 to PDD-10. Two are proposed for hand-over: PDD-07 (Behaviour's allowance contract) and part of PDD-08 (the evaluation context) to the Ledger unit. PDD-01 to PDD-03 belong with IMA. PDD-09 (negotiation over a placement) is close to AIR Phase 7's market responses. PDD-10 (more than one language) has no home.

### 9.3 Held questions in CCS

HQ-1 to HQ-12 in the [CCS plan](plans/computable-contract-substrate.md). Among them, HQ-4 (context roles from several sources) waits on ADR-A116. HQ-10 (a deployment configuration layer) has no unit yet.

### 9.4 Technical debt

[technical-debt.md](technical-debt.md) lists 40 open rows on `main`. Track H's release branch adds and closes several (TD-63 closed, TD-64 the branch's versioning rule).

## 10. The maintainer's queue

In the order that unblocks the most work.

1. **Tag release 0.18.0.** `ontologies-v0.18.0` and the applied modules' ten tags, listed by `mise exec -- python tools/ontology_releases.py check` on `main`.
2. **Answer Track H's review items Q1 to Q6**, then merge `claude/nice-bohr-pmj43u` and create the 0.19.0 tags.
3. **Answer AIR-3.3-Q1**, so that AIR-3.3 can be built ahead of CCS C12.
4. **Review the Ensemble and Ledger proposals**, ADR-A130, ADR-A131 and ADR-A01's two addenda, then AIR Phase 7.
5. **Accept the tutorial**, TUT-4, and push `tutorial/guide`.
6. **Review the architecture principles draft** on `architecture-principles`.
7. **Ratify or reject the platform's Phase 0 ADRs**, the oldest Proposed decisions in the catalogue.
8. **Decide the small units.** The XSLT sidecar's XS-D1 to XS-D7, the Word checklist, the policy mapping spike, the model-based testing sketch.
9. **Retire merged branches.** Section 7 lists them.

## 11. Completed units

| Unit | Closed |
|---|---|
| [Toolchain JDK 25 and Python 3.14](status/toolchain-jdk25-python314.md) | 2026-09-23 |
| [Persistence compiler and IRI patterns sync](status/persistence-compiler-iri-sync.md) | 2026-09-25 |
| [IRI patterns post-3866b21 remediation](status/iri-patterns-post-3866b21-remediation.md) | 2026-09-23 |
| [RDF and SPARQL patterns remediation](status/rdf-sparql-patterns-remediation.md) | 2026-09-23 |
| [Vocabulary temporal binding](status/vocabulary-temporal-binding.md) | 2026-09-25 |
| [Temporal binding consumer hardening](status/temporal-binding-consumer-hardening.md) | 2026-09-25 |
| [Ontology semantic versioning](status/ontology-semantic-versioning.md) | slices 2026-09-25, ADR-A86 since accepted |
| [Applied ontology readiness](status/applied-ontology-readiness.md) | 2026-09-25 |
| [Python test speed](status/python-test-melting.md) | 2026-10-09 |
| [LLM training and the MORK Teaching Pack](status/llm-training-mtp.md) | 2026-09-20 |
| [Repository topology](status/repository-topology-a77.md), [ontology root relocation](status/ontology-root-relocation.md), [MORK split](status/mork-package-split.md), [SPC split](status/spc-package-split.md) | 2026-09-20 |
| [Surface and MORK unified projection](status/surface-mork-unified-projection.md), phases 0 to 8 | 2026-09-22 |
| Agent skills (ADR-A117) | built, with the private overlay addendum Proposed |

## 12. Observations

These are findings from building this roadmap, offered as hypotheses for the maintainer to check.

- **The coordination index is stale.** [INDEX.md](INDEX.md) was last updated on 2026-09-25 and does not list CCS's tranche D, Track H's progress since then, the documentation epic's merge, the tutorial, or the Ensemble and Ledger proposals. The lifecycle skill says it changes whenever a unit or slice changes state. Either it is refreshed, or this roadmap takes over its overview role and the index keeps only the per-unit links.
- **Several status records lag their branches.** CCS's next action names a merge that has happened, and IOD's record on `main` predates its own squash merge. AIR's record on `main` is older than its copy on the Track H branch.
- **Two branches hold the same line of work.** `claude/nice-bohr-pmj43u-wwhgle` is contained in `claude/nice-bohr-pmj43u`.
- **Release tags lag merges.** Release 0.18.0 is merged and untagged. Track H prepares 0.19.0 on top of it, so the 0.18.0 tags should exist before 0.19.0 merges, or the register's order will not match the tags'.
- **Machine R carries three streams.** AIR verification, CCS and, through CCS, most of NRS. CCS-9b.3 and CCS-9b.4 are on the critical path of all three.
- **This page will go stale.** Under the lifecycle skill, `docs/developer/` holds durable guidance only. A roadmap is a snapshot. Options are to regenerate it from the status records with a tool, to keep it as a dated snapshot and replace it on each refresh, or to fold its overview into `INDEX.md`.
