<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.11a, the Persistence README as a literate specification

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.11a,
[plan §4.19](../plans/formal-methods-track-h.md#419-h211-the-persistence-readme-as-a-literate-specification-planned-2026-10-20),
[sketch](../sketches/persistence-readme-literate.md) (RL-Q1 to RL-Q7). Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved and `check:ontology-versioning` fails with `UNBUMPED`, as expected.
It is not run here.

**Awaiting the maintainer's review.** Fifteen decisions were taken alone (D-50 to D-64), 85 definitions were drafted
(RL-Q7 (a)), 21 comments were rewritten, and the reconciliation file lists every difference from `f25008b2`. No test was
changed, added or removed.

## Invariant

`ontology/persistence/README.md` is in the 13-section layout of ADR-A126 and is the one source of `spec/persistence.ttl`,
`spec/persistent-foundation.ttl`, `shapes/constraints.ttl` and `shapes/persistent-foundation.ttl`. Every one of them is the same graph as at
`f25008b2` except for the 137 differences in [FMH-H2-11a-reconciliations.txt](FMH-H2-11a-reconciliations.txt). Each is one of
10 header lines, 85 drafted definitions or 42 lines for the 21 rewritten comments.
No class, property, individual, domain, range, shape or SPARQL constraint changed. The README cites only published decisions and no working document,
and neither does any file it generates.

## What changed

1. **`ontology/persistence/README.md`**, rewritten in place from 1797 to 5072 lines, of which about 700 are the Axiom Index and the class diagram, which
   the extractor writes.
   - **§1** is new and short, two paragraphs, and is each spec document's `dct:description`. **§2** holds the header table (two rows), the prefix table
     (`dal:`, `fnd:`) and the creators table, with Eligibility's creator row copied exactly. **§3** holds the contract and the catalogue entry, with
     `[module.extract]` naming the two spec documents and the two shape files.
   - **§4 Overview** takes today's §1 and the namespace note, and the class diagram, generated, in a collapsed `<details>` block (RL-Q6 (b)).
   - **§5 Detailed Design** takes today's §2 to §10, §12, §13 and §14 as subsections 5.1 to 5.12, and a cross references subsection, 5.13.
   - **§6** has 253 entries (252 in `spec/persistence.ttl`, one in `spec/persistent-foundation.ttl` inside an `output-file` region), 43 individuals
     tables in one `output-file` region, two 6.6 blocks, and the Axiom Index.
   - **§7** has two hidden blocks, one for each shapes file, with the file's text as it was, apart from the comments listed below.
   - **§8 Examples** takes today's §11 and §14.3. **§9 and §10** say "Not applicable.". **§11** states the dependencies. **§12** is rewritten, see below.
     **§13** lists seven open issues.
2. **Generated, by `tools/literate_extract.py`:** `spec/persistence.ttl`, `spec/persistent-foundation.ttl`, `shapes/constraints.ttl`,
   `shapes/persistent-foundation.ttl`, and the README's two generated regions. No `shapes/structural.ttl` is generated, since section 6 states no restriction, and
   the extractor did not insist on one.
3. **Documents.** `docs/developer/validation/FMH-H2-11a-reconciliations.txt`, plan §4.19, the status record, `docs/developer/technical-debt.md`
   (TD-01 removed) and the status line of `docs/architecture/literate-specifications.md`.
4. **Not changed:** every tool, every test, every example, every other README.

## The mapping, old section to new

| Old section | New section |
|---|---|
| title, "This README is meant to be read on its own" | the title block, before §1 |
| 1 Purpose and scope | §4 Overview (all of it, the flowchart included) and §4.1 Namespace. §1 is new text, a shorter statement of the same purpose |
| 2 Why persistence in RDF is hard | 5.1 |
| 3 The infrastructure the patterns add | 5.2 |
| 4 One write, end to end | 5.3 |
| 5 The configuration model | 5.4 |
| 6 Scopes, targets and resolution (6.1 to 6.3) | 5.5 (5.5.1 to 5.5.3) |
| 7 The dimensions, one by one (7.1 to 7.10) | 5.6 (5.6.1 to 5.6.10) |
| 7.10.1 Membership encoding | 5.6.11 |
| 8 Capability self-checks | 5.7 |
| 9 What the compiler produces (9.1) | 5.8 (5.8.1) |
| 10 Choosing a profile | 5.9 |
| 11 Worked examples (11.1 to 11.5) | §8 Examples (8.1 to 8.5) |
| 12 Validation | 5.10 Refusals and warnings. Its paragraph on the shapes over a compiled profile is in 7.2 |
| 13 Repository layout | 5.12 |
| 14 Keys: `persistent-foundation` (14.1, 14.2) | 5.11 (5.11.1, 5.11.2), and the `persistent-foundation` shapes in 7.3 |
| 14.3 Worked example | 8.6 |
| 15 Cross references | 5.13, without the sketch row and the two proposed decisions |
| Repository catalogue entry | §3 |
| the Turtle excerpts of every section | gone. Every statement they held is in §6 or §7 |
| (new) | §6, §7, §9 to §13 |

Every `§` reference of the text is mapped by one table, and a reference to a guide keeps the guide's number. The text of the sections is otherwise
today's, with the working-document references removed (below) and "Foundation 0.4.0" corrected.

## Decisions taken alone

Numbered on from D-49 of the status record, which was the last (checked).

| # | Decision | Reason | To ratify |
|---|---|---|---|
| D-50 | **No Utility paragraph is added** where none exists. One term, `dal:PersistenceKeyed`, has one, and it is kept | the brief, and Eligibility's migration added none. About 320 new utilities are authoring work for H2.11b or later, not conformance | keep, or ask for utilities |
| D-51 | **The 18 individuals with no comment keep none**: the seven levels and policies (`dal:Advisory`, `dal:Transactional`, `dal:Strong`, `dal:Linearizable`, `dal:BestEffort`, `dal:Merge`, `dal:Reject`), the eight resource roles (`dal:EntityRole`, `dal:AggregateRootRole`, `dal:ComponentRole`, `dal:LineageRole`, `dal:ContentRevisionRole`, `dal:GraphLocatorRole`, `dal:KeyClaimRole`, `dal:EventOccurrenceRole`), and `dal:PublicData`, `dal:InternalData` and `dal:ErasureWins` | RL-Q7 (a) covered the terms with an `**Definition.** TODO` entry, as OD6's covered classes and properties. The README's §13 lists them | draft them, a short addition |
| D-52 | **The catalogue entry has no `imports` line**, though the brief names Foundation | `tools/test_lattice_repo_catalogue.py::test_rc1_t4` asserts that only substrate modules declare `imports` (ADR-A121), and the first run of `check:ontology-catalog` failed on it. The tests are not mine to change. The import is stated in §2's header row, §3 and §11, and `check:import-guard` passes | keep, or widen the rule |
| D-53 | **Two comments lose their backticks**: `dal:CompiledProfile` (`persistence compile`) and `dal:recipeDocument` (`persistence export-recipes`) | the plain-text rules remove backticks, so the text cannot be written as it is. A Turtle literal is read as one only with a language tag or a datatype, and `"x"^^xsd:string` is a different RDF term from `"x"` in rdflib, so the migration check would report it. Listed with the rewritten comments | keep |
| D-54 | **§12 Validation goes to Detailed Design** (5.10), not to Examples, and its paragraph on the shapes over a compiled profile goes to 7.2 | none of it is about examples. The paragraph describes shapes, which §7 holds | keep |
| D-55 | **Old §1 is the Overview whole, and the new §1 is shorter, new text** | §1 becomes the `dct:description` of both documents, so it holds only plain text. The description is the same text in both, though it says that the `persistent-foundation` document imports a layer | keep, or reword |
| D-56 | **Section numbers move by one table.** Old 7.10.1 is 5.6.11, a sibling of 5.6.10, old §11 is §8, and old 14.3 is 8.6 | a fourth level of heading for one subsection would be the only one in the README | keep |
| D-57 | **6.4 is 43 tables, one for each type, in one `output-file` region** that sends them to `spec/persistence.ttl`. The 15 individuals with a `dal:logicalKey` or a `dal:unicodeVersion` are two 6.6 blocks | Persistence has no vocabulary document, and the grammar sends individuals there unless a region says otherwise. The tables cannot hold those two properties | keep |
| D-58 | **6.1 to 6.3 follow the order in which the old spec first mentions each term**, not the alphabet, and long paragraphs are wrapped | the old file grouped terms by topic, and the generated order does not depend on the README's | keep |
| D-59 | **The class diagram is kept whole, collapsed, and is too wide to read.** Rendered with the repository's mermaid in Chromium, its natural size is 16,210 by 1,460 pixels, 94 boxes and 74 arrows. At the width of a page it is unreadable without zooming | RL-Q6 (b) asked to stop and propose a split, a generator filter, which is a tool change for the maintainer. A proposal is to draw only the classes that have a member or an arrow, and list the enumeration classes and their individuals in a table, or split by dimension, which §6's order allows. No tool was changed | decide the split |
| D-60 | **Two proposed decisions and the sketch leave the cross references.** ADR-A82's sentence loses its citation, the minting libraries link to `packages/minting/README.md` in place of ADR-A84, and ADR-A67's clause names the version chain | the sources check, ADR-A127. The meaning of each sentence is kept | keep |
| D-61 | **Comments in the two hidden shape blocks are edited**, which changes no graph. The generated shapes files now open with the SPDX header, which `shapes/constraints.ttl` lacked | working-document references, ADR-A51 and ADR-A128 would fail the sources check, since every generated file is read. Listed below | keep |
| D-62 | **The release notes class each change as the versioning policy does, by its effect on a graph valid under the previous release.** Removing a term is "changes meaning", adding a shape is "may invalidate", adding a term or removing a domain is "no effect". `dal:SharedClassProfileWarningShape` gaining a target is "no effect", since it only warns. The branch's changes are one "Unreleased" entry | the policy, and Eligibility's notes. The older entries come from the tags and `git log` | check the classes |
| D-63 | **Section 13 lists seven open issues**, each a statement of what is not built, and none names a debt row or a working document | the brief | keep |
| D-64 | **`docs/precedence-and-resolution.md` and `docs/aggregate-boundaries.md` still link the sketches**, and the README links both | outside the brief, and the sources check does not read them. They are in the module's `docs/` role | clean them, a small change |

## The drafted definitions, for review (RL-Q7 (a))

Each is an added `rdfs:comment`, one line of group 2 in the reconciliation file. Drafted from the README's prose and `tools/persistence`.

| Term | Definition |
|---|---|
| `dal:AggregateBoundaryProfile` | A profile that declares how a target's aggregate is bounded and how its first write creates the version row. |
| `dal:AggregateBoundaryStrategy` | How the triples that change together are delimited, one of a closed set of named strategies. |
| `dal:ConcurrencyProfile` | A profile that declares how concurrent writers to one aggregate are kept apart, with the deadlock policy and the ETag form and representation. |
| `dal:ConcurrencyStrategy` | The mechanism that keeps concurrent writers to one aggregate from overwriting each other, one of a closed set of named strategies. |
| `dal:ContiguityCheckMode` | What a consumer does when the sequence numbers it has seen for a stream have a gap, one of a closed set of named modes. |
| `dal:DatasetTierModel` | How a total order across streams is derived, for a family that declares one, one of a closed set of named models. |
| `dal:DeadlockPolicy` | Who is responsible for avoiding deadlock when a write touches several version rows, one of a closed set of named policies. |
| `dal:Diagnostic` | A warning the compiler recorded for a target in its compiled profile, with its kind and its message. |
| `dal:EpochProfile` | A profile that declares where a dataset's epoch comes from and what every write guards on. |
| `dal:ErasureStrategy` | How one subject's data is erased, one of a closed set of named strategies. |
| `dal:EtagForm` | Whether the ETag derived for an aggregate is a strong or a weak validator. |
| `dal:EtagRepresentation` | Whether conditional requests are served one representation or the tag names the representation. |
| `dal:FirstWriteMode` | How the first write of an aggregate creates its version row, one of a closed set of named modes. |
| `dal:MetaTopology` | How version rows are spread over meta graphs, one of a closed set of named topologies. |
| `dal:MetaTopologyProfile` | A profile that declares a family's meta topology, its shard counts and its registry graph. |
| `dal:OrderingGrain` | The grain at which a family assigns positions, one of a closed set of named grains. |
| `dal:OrderingProfile` | A profile that declares a family's ordering grain, dataset tier, global read and contiguity check. |
| `dal:PrivacyClass` | The class of data a profile governs for erasure, one of a closed set of named classes. |
| `dal:PrivacyProfile` | A profile that declares the class of a family's data, how a subject is erased and what wins when erasure meets the monotonicity of claims. |
| `dal:ReceiptProfile` | A profile that declares a family's receipt model and how its receipts are retained. |
| `dal:RetentionMode` | How receipt buckets may be pruned, one of a closed set of named modes. |
| `dal:SchemeState` | A state of a claim scheme in its rotation, one of a closed set of named states. |
| `dal:UniquenessConstraint` | One keyed uniqueness constraint on a target, with its key properties, scope, normalisation and policy on violation. |
| `dal:appliedUniquenessConstraint` | A uniqueness constraint the compiler applied to the target. |
| `dal:candidateCount` | How many candidate values the resolution of a dimension had. |
| `dal:capabilityCheck` | The check of the target's capability requirement against a supplied capability spec. |
| `dal:capabilityRequirement` | The capability requirement the compiler computed for the target. |
| `dal:checkedAgainst` | The capability spec a capability check compared the requirement with. |
| `dal:claimScheme` | A claim scheme in use for a uniqueness constraint, which fixes the form of its claim IRIs. |
| `dal:concurrencyProfile` | The concurrency strategy a concurrency profile declares. |
| `dal:constraintId` | The stable name of a uniqueness constraint, part of every claim IRI. |
| `dal:contiguityCheckMode` | The contiguity check mode an ordering profile declares. |
| `dal:datasetTierModel` | The dataset tier model an ordering profile declares. |
| `dal:deadlockPolicy` | The deadlock policy a concurrency profile declares. |
| `dal:diagnostic` | A diagnostic the compiler recorded in a compiled profile. |
| `dal:diagnosticKind` | The kind of a diagnostic, the name of the warning. |
| `dal:diagnosticMessage` | The message of a diagnostic. |
| `dal:digestScheme` | The digest scheme an identity profile mints with, when an identifier or a namespace is a digest. |
| `dal:dimension` | The name of a resolved dimension. |
| `dal:edgeOwnership` | The ownership kind of a reference edge, owned, a reference or vocabulary. |
| `dal:epochAuthority` | Where a new epoch comes from, as an epoch profile declares it. |
| `dal:epochGuardScope` | Whether each write compares the dataset's epoch or only its row's, as an epoch profile declares it. |
| `dal:equivalentTo` | The class an equivalent-class scope matches through owl:equivalentClass or another OWL entailment. |
| `dal:erasurePrecedence` | Which wins when erasure meets the monotonicity of key claims, as a privacy profile declares it. |
| `dal:erasureStrategy` | How a subject's data is erased, as a privacy profile declares it. |
| `dal:etagForm` | Whether the ETag derived for an aggregate is strong or weak. |
| `dal:etagRepresentation` | Whether a store serves one representation for conditional requests or folds the representation into the tag. |
| `dal:eventIdentityStrategy` | How the IRI of an event occurrence is chosen, as an identity profile declares it. |
| `dal:firstWrite` | How the first write of an aggregate creates its version row. |
| `dal:forOperation` | The id of the operation a generated operation is, for example cas-replace. |
| `dal:forRole` | The resource role a minting recipe mints for. |
| `dal:forTarget` | The target class a compiled profile was resolved for. |
| `dal:generatedOperation` | An operation the compiler generated for a compiled profile's target. |
| `dal:globalReadStrategy` | How a consumer of the dataset tier reads across streams without skipping a write that commits late. |
| `dal:graphPrefix` | The prefix of the IRIs of the graphs a graph pattern scope matches. |
| `dal:hasParameterBinding` | A parameter binding of a generated operation. |
| `dal:identityStrategy` | The identity strategy an identity profile declares for its resource role. |
| `dal:includeSubclasses` | Whether a class scope also matches the asserted subclasses of its target class. |
| `dal:iriPrefix` | The prefix a namespace scope matches against the IRIs of resources. |
| `dal:metaShards` | The number of meta graphs the version rows are spread over, by hash. |
| `dal:metaTopology` | The meta topology a meta topology profile declares. |
| `dal:minEnforcementLevel` | The weakest enforcement level a uniqueness constraint accepts, one of dal:Advisory, dal:Transactional and dal:Strong. |
| `dal:mintingRecipe` | A minting recipe the compiler emitted in a compiled profile. |
| `dal:occurrenceNamespaceDerivation` | How the namespace of a position-derived event identity is derived from its target. |
| `dal:onViolation` | What a uniqueness constraint does with a violation, one of dal:Reject, dal:Merge and dal:Quarantine, which selects the reconciler. |
| `dal:orderingGrain` | The grain at which positions are assigned, per commit or per event. |
| `dal:paramName` | The name of the parameter a binding sets. |
| `dal:paramValue` | The encoded value a binding gives its parameter. |
| `dal:privacyClass` | The class of the data a privacy profile governs. |
| `dal:providesReasoning` | Whether the supplied environment provides reasoning. |
| `dal:providesSingleWriter` | Whether the supplied environment provides a single writer per partition. |
| `dal:providesStatementLevelConflictDetection` | Whether the supplied environment detects write conflicts per statement. |
| `dal:receiptModel` | The receipt model a receipt profile declares. |
| `dal:requiresCas` | The level of compare-and-set the resolved configuration requires, as a name. |
| `dal:requiresUniquenessLevel` | The highest enforcement level that any uniqueness constraint of the target asks for. |
| `dal:resolvedDimension` | A dimension the compiler resolved for the target, with its value and its provenance. |
| `dal:resolvedValue` | The individual a dimension resolved to. |
| `dal:resourceRole` | The resource role an identity profile names. |
| `dal:retentionMode` | How receipts are pruned, as a receipt profile declares it. |
| `dal:schemeState` | The state of a claim scheme in its rotation. |
| `dal:schemeVersion` | The version label of a claim scheme, part of every claim IRI. |
| `dal:strategy` | The aggregate boundary strategy a boundary profile declares. |
| `dal:targetClass` | The class a class scope matches by asserted type. |
| `dal:usesTemplate` | The template, that is the builder, a generated operation is rendered from. |
| `dal:wonBy` | The profile whose value won the resolution of a dimension. |

## The rewritten comments

Each is two lines of group 3, the old text only at the ref and the new text only in the tree. Of the 21, 17 refer to a working document (a slice, a
sketch, a debt row, a question or a Validation Pack), two cite ADR-A68, which is not published, and two carry backticks (D-53).

| Term | Before | After |
|---|---|---|
| `dal:CompiledProfile` | The canonical output of `persistence compile`. Never contains literal SPARQL text. | The canonical output of persistence compile. Never contains literal SPARQL text. |
| `dal:DigestContract` | What the request digest of an operation is taken over. Its IRI is minted from the target and the operation. The algorithm and the encoding are fixed here, and the code that computes it is H2.8's. | What the request digest of an operation is taken over. Its IRI is minted from the target and the operation. The algorithm and the encoding are fixed here, and the caller library computes it (ADR-A132). |
| `dal:HandDeclared` | Written by hand, for an operation that has no builder. None has, since H2.7 gave the value-based guard a builder (TD-43). | Written by hand, for an operation that has no builder. None has, since the value-based guard has a builder. |
| `dal:NoBoundary` | No coherent aggregate. Concurrency, if any, is value-based CAS on individual properties, which live in the profile's dal:dataGraph, mandatory for a family that has one (H2.7-Q1). | No coherent aggregate. Concurrency, if any, is value-based CAS on individual properties, which live in the profile's dal:dataGraph, mandatory for a family that has one. |
| `dal:NoReceipt` | No receipt and no head for a write, which still records its transaction claim, so a retry after a lost reply is confirmed. For a dal:InPlace family that wants no history, such as a derived artefact that can be regenerated (formal-methods H2.6d, VH-Q5a). Refused with dal:AppendVersions, dal:AppendRecords and a stream, whose versions and records take their position and transaction time from the receipt. | No receipt and no head for a write, which still records its transaction claim, so a retry after a lost reply is confirmed. For a dal:InPlace family that wants no history, such as a derived artefact that can be regenerated. Refused with dal:AppendVersions, dal:AppendRecords and a stream, whose versions and records take their position and transaction time from the receipt. |
| `dal:NothingExamined` | The audit returned no row and read nothing: the graphs it examines are not listed, or hold no receipt. This is not a clean result (FMH-H2-5, non-coverage). | The audit returned no row and read nothing: the graphs it examines are not listed, or hold no receipt. This is not a clean result. |
| `dal:PatchLog` | asserts/retracts delta graphs alongside each receipt, written in the same update as the write (formal-methods H2.6d). A create's add graph holds its payload, a replace's add and del graphs hold the delta the caller computed, and a tombstone's del graph holds what the sweep removed. The graphs are named from the receipt. Enables replay and CDC, and an as-of read backward from the current state. Honoured for the in-place writes of dal:NamedGraphBoundary and dal:CompositePropertyBoundary families. | asserts/retracts delta graphs alongside each receipt, written in the same update as the write. A create's add graph holds its payload, a replace's add and del graphs hold the delta the caller computed, and a tombstone's del graph holds what the sweep removed. The graphs are named from the receipt. Enables replay and CDC, and an as-of read backward from the current state. Honoured for the in-place writes of dal:NamedGraphBoundary and dal:CompositePropertyBoundary families. |
| `dal:PerSubjectGraphDrop` | Drop the per-subject graph and record a tombstone (ADR-A68). Requires every graph holding this subject's payload, including patch-log deltas and snapshots, to be per-subject and enumerable. | Drop the per-subject graph and record a tombstone. Requires every graph holding this subject's payload, including patch-log deltas and snapshots, to be per-subject and enumerable. |
| `dal:PersonalData` | Subject to erasure obligations (ADR-A68). | Subject to erasure obligations. |
| `dal:PropertyValue` | The value of one property of a root, in the data graph of a family with no boundary (H2.7, TD-43). Read and written by the value-based guard. | The value of one property of a root, in the data graph of a family with no boundary. Read and written by the value-based guard. |
| `dal:ReferenceMode` | What an edge's reference names, when its target class is versioned (formal-methods H2.6e). One of dal:ByIdentity, dal:Pinned. | What an edge's reference names, when its target class is versioned. One of dal:ByIdentity, dal:Pinned. |
| `dal:ResourceKind` | A logical resource an operation reads or writes, with its logical key and its realisation in SPARQL. The relational realisation of each is in the paper check of the formal-methods H2.6 Validation Pack. | A logical resource an operation reads or writes, with its logical key and its realisation in SPARQL. |
| `dal:checkpointEvery` | Under dal:DeltaMembership, the interval of full lists: a version whose seq is a multiple of it, and the first version, lists every member. Absent means 16. compile refuses a value that is not an integer of at least 1 (CheckpointEveryInvalid). The caller decides which version is a checkpoint, and H2.8's caller check verifies it. | Under dal:DeltaMembership, the interval of full lists: a version whose seq is a multiple of it, and the first version, lists every member. Absent means 16. compile refuses a value that is not an integer of at least 1 (CheckpointEveryInvalid). The caller decides which version is a checkpoint, and the caller library's check verifies it (ADR-A132). |
| `dal:dataGraph` | The named graph that holds the aggregates of a dal:CompositePropertyBoundary family, and the values of a dal:NoBoundary family. Mandatory for the composite strategy, for dal:NoBoundary under dal:Optimistic with a dal:valueGuardProperty (the refusal is MissingDataGraph, H2.7-Q1, TD-43), and for dal:AppendVersions. Every operation of such a family reads and writes this graph only, never the default graph, whose contents differ between stores (static check S-1). | The named graph that holds the aggregates of a dal:CompositePropertyBoundary family, and the values of a dal:NoBoundary family. Mandatory for the composite strategy, for dal:NoBoundary under dal:Optimistic with a dal:valueGuardProperty (the refusal is MissingDataGraph), and for dal:AppendVersions. Every operation of such a family reads and writes this graph only, never the default graph, whose contents differ between stores (static check S-1). |
| `dal:digestAlgorithm` | The hash, SHA-256, over the parts in dal:partOrder, encoded as the patterns guide §15.2 says. The code that computes it is H2.8's. | The hash, SHA-256, over the parts in dal:partOrder, encoded as the patterns guide §15.2 says. The caller library computes it (ADR-A132). |
| `dal:epochBumpAcknowledged` | Required alongside a dal:metaShards value that differs from a declared dal:priorMetaShards, for a scope with committed history (sketch §3.5, guide §24.4). | Required alongside a dal:metaShards value that differs from a declared dal:priorMetaShards, for a scope with committed history (guide §24.4). |
| `dal:forDeployment` | The dal:GraphPatternScope this compiled profile was resolved for, when the target class has more than one disjoint graph-pattern deployment (sketch §3.4.3: lending and credit both deploy beh:Behaviour, each into its own graph family, each getting its own compiled profile). Absent for the unscoped/fallback deployment and for targets with no graph-pattern deployment at all. | The dal:GraphPatternScope this compiled profile was resolved for, when the target class has more than one disjoint graph-pattern deployment (for example lending and credit both deploying beh:Behaviour, each into its own graph family, each getting its own compiled profile). Absent for the unscoped/fallback deployment and for targets with no graph-pattern deployment at all. |
| `dal:opSeqRequired` | Meaningless (and rejected, sketch §3.5) at dal:CommitGrain. | Meaningless, and rejected, at dal:CommitGrain. |
| `dal:priority` | Explicit precedence, higher wins. Default 0. The sole tiebreak input the resolver uses; scope kind itself is never treated as a specificity ladder (sketch §3.4.2). | Explicit precedence, higher wins. Default 0. The sole tiebreak input the resolver uses. Scope kind itself is never treated as a specificity ladder. |
| `dal:recipeDocument` | The recipe as RFC 8785 canonical JSON, a literal of datatype rdf:JSON. The canonical form of the recipe: `persistence export-recipes` extracts it, and the other properties of dal:MintingRecipe only make it queryable. | The recipe as RFC 8785 canonical JSON, a literal of datatype rdf:JSON. The canonical form of the recipe: persistence export-recipes extracts it, and the other properties of dal:MintingRecipe only make it queryable. |
| `dal:valueGuardProperty` | For dal:NoBoundary targets choosing dal:Optimistic: the single property a value-based guard compares the old value of (guide §14.2). Without one, Optimistic concurrency on a NoBoundary target has nothing coherent to replace and is rejected (sketch §3.5). | For dal:NoBoundary targets choosing dal:Optimistic: the single property a value-based guard compares the old value of (guide §14.2). Without one, Optimistic concurrency on a NoBoundary target has nothing coherent to replace and is rejected. |

## Comments of the shapes files, rewritten without a graph change

| File | Before | After |
|---|---|---|
| `shapes/constraints.ttl` | "per sketch §3.9" and "sketch §3.7", twice | removed |
| `shapes/constraints.ttl` | "(formal-methods H2.6c to H2.6f, shapes added in H2.7)" | "(the write disciplines, the receipt models, the membership encodings and the reference modes)" |
| `shapes/constraints.ttl` | "(formal-methods H2.7, plan 4.7)" | "(the typed operation IR)" |
| `shapes/constraints.ttl` | "(ADR-A128)", not published | removed, the document is still named |
| `shapes/constraints.ttl` | "H2.8c: the profile states each edge once" | "The profile states each edge once" |
| `shapes/constraints.ttl` | "(SI-5 of the typed IR sketch, review 2.6)" and "(design review 2.6, NQ4)" | removed |
| `shapes/persistent-foundation.ttl` | "(ADR-A114, CCS F1, keys impact analysis P2 to P5)", "(keys impact P3)", "(keys impact P5)" | "(ADR-A114)" and removed |
| `shapes/persistent-foundation.ttl` | "(ADR-A51)", superseded and not published | removed |

## The reconciliation file

| Group | Lines | Why it exists |
|---|---|---|
| 1, the header | 10 | each spec document gains `dct:description` (§1) and `dct:creator` (§2) and the declarations of the two Dublin Core properties, as in OD6, and the ontology node of `spec/persistence.ttl` loses `rdfs:label` and `rdfs:comment`, which the description replaces. The foundation document had neither |
| 2, the drafted definitions | 85 | RL-Q7 (a), the terms that had no `rdfs:comment` |
| 3, the rewritten comments | 42 | the sources check, ADR-A127, and D-53. 21 comments, an old line and a new one each |

Nothing else differs. In particular the shapes files and `spec/persistent-foundation.ttl`'s statements are graph-identical, and no domain, range, subclass or
individual changed.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| FMH-H2-11a-T1 | the migrated README / `check:literate-migration -- persistence f25008b2` with the reconciliations / passes with 137 reconciled differences | L5 | + |
| FMH-H2-11a-T2 | `dal:priority`'s **Domain.** changed from `dal:ProfileScope` to `dal:ClassScope` in §6.2 and re-extracted / the same check / fails, naming `dal:priority rdfs:domain dal:ProfileScope` only at the ref and `dal:ClassScope` only in the tree | L5 | − |
| FMH-H2-11a-T3 | the migrated README / the extractor with `--check` / four extracted artefacts and the generated regions consistent | L4 | + |
| FMH-H2-11a-T4 | the README and the four generated files / `check:published-decisions` / no citation of an unpublished decision and no working document | L3 | + |
| FMH-H2-11a-T5 | the catalogue and the module / `check:catalogue`, `check:ontology-catalog`, `check:import-guard` / agree | L3 | + |
| FMH-H2-11a-T6 | the regenerated spec / `check:persistence` and `check:persistence-expected-profiles` / pass, with the expected profiles unchanged | L4 | + |
| FMH-H2-11a-T7 | the same / `check:persistence-oxigraph` / pass | L4 | + |

The spec has no restriction row, so T2 changes a domain, which is the same kind of difference.

## Commands

Run from the repository root. A pass is each command exiting 0, except the last, which reports `UNBUMPED` for the changed files and nothing else.

```bash
mise exec -- python tools/literate_extract.py ontology/persistence/README.md --layer persistence --root . --check
```

```bash
mise run check:literate-migration -- persistence f25008b2 --reconciliations docs/developer/validation/FMH-H2-11a-reconciliations.txt
```

```bash
mise run check:published-decisions
mise run check:catalogue
mise run check:import-guard
mise run check:deny-terms
mise run check:site-sections
```

```bash
rm -rf ontology/persistence/execution && mise run check:ontology-catalog
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:persistence-expected-profiles
```

```bash
mise run check:ontology-versioning
```

## Results

2026-10-21, run while building, from this worktree:

- **T1:** passes, `persistence: every generated graph is the same as at f25008b2, with 137 reconciled difference(s)`, 10 header lines, 85 drafted definitions and 42 lines for 21 rewritten comments.
- **T2:** fails as expected, 2 problems, `only-at-ref` the domain `dal:ProfileScope` of `dal:priority` and `only-in-tree` the domain `dal:ClassScope`. The README was restored from a copy and re-extracted, and T1 and T3 passed again.
- **T3:** 4 extracted artefacts consistent with the README, its generated regions included.
- **T4:** `check:published-decisions` passes. `sources: 0 failure(s), 545 report(s) for READMEs not yet migrated`, and `tools/test_published_decisions.py` 6 passed. Its first run found ADR-A51, in a comment of `shapes/persistent-foundation.ttl`, which D-61 removed.
- **T5:** `check:catalogue` agrees (19 modules, 8 tool packages). `check:ontology-catalog` 1137 passed, 7 skipped. Its first run failed on `test_rc1_t4`, because of an `imports` line (D-52). `check:import-guard` reports 0 violations.
- **T6:** `check:persistence` **4258 passed, 1 xfailed** (5 minutes 8 seconds), and `check:persistence-expected-profiles` reports the expected profiles current, none regenerated.
- **T7:** `check:persistence-oxigraph` **368 passed**.
- **Also:** `check:deny-terms` 0 findings, with its default scope and with `--all`. `check:site-sections` 9 sections, 1 copy current. `check:agent-guidance` 9 passed.
- **`check:ontology-versioning`:** fails with `UNBUMPED` for the 4 changed release member files, as TD-64 expects, and nothing else.

## Not covered, and for the maintainer

- **The class diagram was not read on GitHub.** It was rendered with the repository's mermaid 10 in headless Chromium and found too wide (D-59).
  The other diagrams are today's and are redone in H2.11b.
- **The README was not read against a site build.** `check:site-sections` passes, and the README is not one of its sources.
- **The release notes' classes are ours** (D-62), and the entries before 0.18.0 are from the tags and `git log`, not from earlier notes, since there were none.
- **`check:ontology-versioning`** was not run, as TD-64 says. Every changed generated file will need the one bump at the merge.
