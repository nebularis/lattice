<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A149: Publication from the Configuration Studio

**Status:** Proposed
**Date:** 2026-10-31 (proposed)
**Related:** ADR-A136 (the studio), ADR-A51 (IRIs and identity), ADR-A142 (meaning-bearing edges), ADR-A143 (one canonicalisation), ADR-A122 (aggregate ownership), ADR-A38 (the Surface output publisher), ADR-A13 (graph roles)
**Unit:** [`studio-publication`](../../developer/plans/studio-publication.md)

## Context

The studio keeps an adopter's configuration in workspaces, each part a named graph read only by that part's jobs. Nothing a workspace holds is versioned, no workspace reads another's content, and the service authenticates nobody. A deployment that takes a compiled artefact cannot say which configuration it came from, two workspaces that need one vocabulary each copy it, and a mapping cannot read the source codes another part holds.

Foundation's versions (MEC-01), the IRI policy's lineage, content revision and promotion IRIs (ADR-A51), one digest (ADR-A143) and the rule for meaning-bearing edges (ADR-A142) already say what a version is. The studio does not yet use them.

## Decision

1. **Publication is explicit.** A unit is published only when a user publishes it. Nothing is published by saving, compiling, importing or exporting.
2. **A unit is an aggregate, published on its own.** A concept scheme, a scheme contract, a binding set, a quantification declaration, an eligibility profile, a persistence profile, a surface contract, a mapping scheme, a form or a form's stated meaning is published as a version of its own lineage. Its references to other units are pinned to their versions. Publishing never copies another unit's content into it.
3. **A version's IRIs follow ADR-A51.** The lineage is the draft root's IRI. The version is `{lineage}/rev/1-{digest}`, the digest the first 16 hexadecimal digits of the RDFC-1.0 SHA-256 of its content, so unchanged content names the same version. The publication is a `prov:Activity` at `{lineage}/evt/e{epoch}/{seq}` with its principal, its time and every version it read, chained to the one before. A current pointer names the latest version. The root is rewritten to the version's IRI with `fnd:hasIdentity` to the lineage, and the nodes it owns keep their IRIs inside the version's own immutable graph.
4. **A registry holds the versions, and a port gives them out.** The registry is part of the studio's store, readable by every signed-in user from every workspace. A deployment takes a version through the port's adapters: the registry's read API, a bundle export of a version with everything it pins, and an adapter that writes into a deployment's store through the deployment's own write path. A version's graph name inside the studio is never part of its identity.
5. **A draft follows or pins.** A draft that names a lineage follows its latest version, and one that names a version is pinned to it. Publishing resolves every followed reference to the current version and rewrites the edge to it. A draft that refers to anything unpublished cannot be published.
6. **Imports are fenced.** What an import leaves in the graph is stored once by the digest of its content, read only, and can be referred to. It is unpublished until a user publishes it.
7. **A part decides where a statement is saved, never what is read.** A job reads its target part, the workspace's other parts, its fenced imports and the closure of its dependencies, and reports findings about the target part's subjects. A workspace's dependencies are published versions or lineages from any workspace. When an import is sorted, a concept goes with its scheme.
8. **Authentication is pluggable.** The default, `local`, offers named developer principals and refuses to start on any address but loopback. `oidc` validates the bearer tokens of an OpenID Connect provider against its published keys and reads administrators from a configured claim. Every command carries its principal.
9. **A workspace has an owner and a mode.** Its creator owns it. A locked workspace is read and written by its owner and administrators, a read-only one is read by everyone signed in and written by its owner and administrators, and a shared one is read and written by everyone signed in. A workspace from before this decision has no owner and is shared. The revision check holds in every mode.
10. **Artefacts name their sources.** A compiled artefact is a `fnd:DerivedArtefact` whose `fnd:DerivationRun` used the versions, or the draft revisions, it was compiled from.
11. **The studio moves onto its own substrate after publication.** Its working store's layout is then declared as persistence profiles and its write path generated, in a later phase with its own questions.
12. **The writer calls generated operations through a Java caller library.** `packages/persistence/java` ports ADR-A132's caller library, held to the same vectors, and the writer binds the operations the persistence compiler generates for the studio's profiles instead of building SPARQL Update by hand. The writer keeps what is not persistence, such as the access gate, the modes and the refusals of a publication.
13. **The studio's aggregates.** The workspace description, each part of a workspace and each document are named-graph aggregates under optimistic concurrency, every part keeping its history in the patch log. A published version is created once and never replaced, and a lineage is replaced under the guard of its current version. A command that writes several aggregates orders its operations so that a guard failing part way leaves nothing a reader acts on: a version before its lineage, the parts before the description on creation, the description first on deletion. Jobs are coordination data (PRI-52), so they are written outside the profiles.
14. **The studio reads through projections.** The registry listing, the workspace summaries, the jobs of each workspace, the holders of each lineage and import, and the terms of every published version are surface contracts over the store, derived and rebuilt from it, never authoritative. A write that changes a projection's source queues a refresh job, which the worker runs with the surface compiler over the aggregates the write changed, so a projection lags its source by a job, and a reader that must see its own write waits for the job. The registry listing, the jobs of each workspace, the holders and the terms are surface promotions. The workspace summary joins a workspace to its parts' version rows by their roots, which no surface read path expresses, so it is a query kept beside the promotions in the contract, run by the same job.

## Consequences

- A deployment can pin and fetch exactly what it runs, by IRI, and store it in its own layout.
- One published vocabulary serves every workspace, and a workspace that edits it holds one working copy until it publishes an edition.
- A job's input grows by the other parts and the dependency closure, and a cached compile is keyed on all of their revisions, not on one part's.
- The service needs an identity provider in production. The `local` provider keeps development free of one.
- Rewriting a root's IRI and its pinned edges makes a published version differ from its draft by those terms, which a reader of both must expect.
- Large drafts are stored whole. A draft held as a change over its base waits for a measured need.
- Each save also reads the part it replaces, to write the patch log's delta, and confirms its write by reading the transaction's claim, so a save costs two reads and one update where it cost one read and one update.
- Graph names change to the profiles' templates, so a store written before decision 13 is migrated once.
- A part's payload holds no blank node, so the store skolemises on write and reads a skolem IRI back as a blank node.

## Addendum, 2026-10-31

**Narrows decision 12.** The generated named-graph replace builds its payload once per stored triple, which took 28 s on Jena for a 3,000-triple part. Until a linear form is settled, the writer replaces a part and a document through a hand-written request that guards on the same version row and writes the same receipt and patch-log delta. It relies, as the writer did before this decision, on Fuseki applying one request in one transaction, and on the writer applying one command at a time. The writer runs the generated operations for every other family and every other operation (TD-136). From the same day the hand-written replace writes only the delta, the generated replace with its sweep taken out, the retracted triples deleted and the asserted inserted, so a save writes what changed.

## Addendum, 2026-10-31, the cost of a refresh

**Narrows decision 14.** Measured after phase D, each refresh cost the writers four commits, about 55 ms each on TDB2, so a save was followed by four more commits that the next save queued behind. A refresh is now two commits: the worker no longer marks a refresh job running, and the update that succeeds it deletes the job and its receipts. A refresh that no reply waits for starts half a second after the first write that asked for it, so a burst of writes shares one, while a reply that must see its write starts one at once. A projection therefore lags its source by a job and up to half a second.

## Addendum, 2026-11-01, the delta replace and promotions kept by the write

**Narrows decisions 12 and 14.** The writer replaces a part and a document through the generated replace again, the delta replace of a family under `dal:ChangedTriples`, so no write of the studio is hand-written any more (TD-136 closed). A browser that holds the part it read sends what it changed as a patch, which the writer applies to the stored part and writes by the same delta.

The studio's derived data is no longer five graphs rebuilt by a job after writes. Each promotion reads one family of aggregates, a workspace description, a lineage, a published version or a job, and keeps its rows for each source in that source's own partition. The write of a source keeps its partition in the same request, by clearing it and filling it from the source as the request leaves it, so a reader sees a write's derived data as soon as the write, and a publish is one commit. The workspace summaries are not stored and are evaluated as they are read. A rebuild of every partition remains, run at start when the promotions grew since the last rebuild, which records the digests of the contracts it read, or when an administrator asks. A promotion that changed or went since is not rebuilt, since that would lose its old rows, and the studio shows the start's warning.

## Addendum, 2026-11-01 (PM-0)

**Renames the derived data of decisions 12 and 14.** The derived data those decisions call projections is named promotions from PM-0, after the kind of contract that produces it, `srf:PromotionContract` (PM-Q8 (a)). The word projection is kept for the output of an `srf:ProjectionContract` and for unrelated meanings. The contract file is `contracts/config-studio/promotions.ttl`, its target namespace ends `config-studio/promotion#`, each source's promoted rows lie in the partition `urn:lattice:studio:promoted:{source graph}`, and the job that rebuilds them is of kind `cst:Rebuild`. The decisions stand as accepted.

## Addendum, 2026-11-19, a deletion wins over a write of what it deletes

**Proposed 2026-11-19, for the maintainer. Narrows decision 13.** Decision 13 orders a deletion so that the description's mention goes first, and guards each tombstone on the revision it expects. It did not say what happens when a write of the same part or document moves that revision first. The tombstone then wrote nothing, and the row and its graph stayed live with nothing reaching them.

1. **A deletion wins.** A deletion removes the part or document it names whatever write of it was applied first. The write that came first committed and was answered as applied, and the deletion then removes what it wrote, which is the order the two were applied in.
2. **The tombstone stays guarded, and is planned again.** A tombstone is still the generated operation, guarded on the revision it expects (decision 12). Where a write moved a row's revision first, the writer plans the tombstone again at the revision the row then has, in a request after the command's own, until the row is gone or three attempts have failed.
3. **The receipt follows the description's step.** A deletion's receipt is guarded on the step that removes the description's mention, since after it no reader finds what is deleted. So a deletion is answered as applied once that step commits, whether or not every tombstone has landed.
4. **A deletion delivered again finishes the removal.** A deletion answered from its receipt still removes a row its tombstone lost, so a writer that stopped between the command's request and the later one leaves nothing behind once the command is delivered again.
5. **An id whose row exists is never created again.** A save that creates a document refuses an id that has a version row, live or tombstoned. A document whose removal is not finished has a live row the description does not list, and a creation under its id would otherwise write nothing, list the document again and show what the deletion removed. Point 4 relies on this rule, since it removes whatever row a deleted id still has.

**What it costs.** A deletion that lost no tombstone reads the revision of each row it retired once more, and one that lost a tombstone makes up to three more requests. A write answered as applied can be removed a moment later by a deletion already under way, and its sender is not told.

**What it admits.** This addendum does not give a design free of inconsistent states. It bounds two, and each needs a second writer on the partition first, which a single active consumer does not prevent.

- **Between the command's request and the last tombstone,** a deletion is answered as applied while the row and graph it deletes are still in the store. No reader reaches them through the description.
- **After the third attempt, or where the command is never delivered again,** the row is logged and left. That is a deletion we confirmed and did not carry out, and the content stays in the store until something removes it. A sweep of the rows no description reaches would, and is not built.

A command that applies whole or not at all, with the writer that lost its partition fenced, would admit neither. That design is not decided here.

## Addendum, 2026-11-25, a command applies whole or not at all

**Accepted 2026-11-25. Narrows decision 13.** It replaces the addendum of 2026-11-19, a deletion wins over a write of what it deletes, except that addendum's points 1 and 5, which it keeps. Decision 13 lets a command that writes several aggregates apply in part and orders its steps so that no reader acts on what is left. The addendum of 2026-11-19 bounded two states that follow and did not remove them. This one removes them.

1. **A command applies whole or not at all.** A command is sent as one unit, in one request. The unit's first operation writes the command's receipt, and only where every row the command writes is at the revision it was planned from, every row it creates is absent, the command has no receipt, and the writer holds its partition's token. Every other operation of the unit keeps its own guard and applies only where that receipt exists.
2. **The unit is generated.** The persistence compiler builds a unit and its receipt from the command's description, as it builds each operation today, and the studio's writer sends what it builds and writes no operation by hand.
3. **A refused batch is planned again.** A unit whose receipt was not written wrote nothing. The writer reads again and plans the batch again. How many times it does so, and how long it waits between them, is a deployment's configuration and not part of this decision. Once it stops, it answers that the workspace changed.
4. **A deletion wins,** as point 1 of the addendum of 2026-11-19 has it, by being planned again at the revisions it finds. It is answered as applied only when everything it deletes is gone, and it makes no later request.
5. **An id whose row exists is never created again,** as point 5 of that addendum has it, and now by the unit's guard. A creation applies whole, so none is left half applied for a resend to complete, and the exception the writer makes today for a row that is the command's own first step goes when the writer sends units.
6. **A writer holds its partition's token.** The store keeps one row for each partition, with a number that a writer raises when it starts on the partition. Every unit's guard requires the writer's own number, so a writer that another has replaced writes nothing. The read a batch is planned from takes the batch's receipts and the token with the rows.
7. **A writer starts from the offset the store holds and takes the stream in order.** The token keeps a replaced writer from answering wrongly. It does not put commands back in order, so the partition's order rests on this rule.
8. **No command removes a receipt.** A deletion leaves the receipts of what it deletes. Receipts are removed by retention, by age, once no resend can arrive.
9. **Only an answer of applied is final.** A command refused by its own check leaves nothing. A command answered as applied was applied, and no command is answered as not applied once it has applied. A resend of a refused command is checked again, and applies where its check then passes.
10. **What a command erases, it erases under its receipt.** A deletion's drop of the patch log of what it deletes becomes an operation of the unit and requires the receipt, so a refused deletion drops nothing. The rule that a job which succeeded keeps its status is part of the guard of the job update's receipt, which is built.
11. **The order of a command's operations no longer carries safety.** Decision 13's order stays as the order they are written in.

**What it costs.** A unit's guard reads one row for each row the command writes and one for the token. A batch that loses a plan costs a read and a request. A writer's start costs one guarded write. A deleted workspace's receipts stay until retention, about ten triples and one for each graph written for each command. A sender that resends a refused command can see it apply.

**What it admits.** On a store that applies a request as one transaction and makes a second writer wait, nothing outside a sequence of whole commands, each applied once and answered as point 9 says. Two limits remain.

- **The partition's order is not kept by the store.** A writer that starts from anywhere but the stored offset can apply a command ahead of an earlier one, with the token too. Point 7 is a rule the writer keeps, and nothing in the store refuses its breach.
- **A store that lets two concurrent updates both commit is not covered.** Each operation's own guard and the token narrow what two writers can do there, and no model or probe of ours says they close it.

**What it rests on.** Models of the writer, checked for one to three writers, crashes, resends, batches of two, a workspace with a part, and delivery in and out of stream order, and probes of the unit's lowering on three engines in memory. The compiler's unit is not built, and the lowering is not probed over HTTP or on a store on disk. Probed on 2026-11-25, after acceptance: it holds on Fuseki over TDB2 by HTTP at Jena 5.1.0 and 6.2.0, and on Oxigraph on disk by one client.

## Provenance

Raised by the maintainer on 2026-10-31, while deciding how a source's codes reach a mapping (TD-133). The maintainer answered PB-Q1 to PB-Q3, PB-Q6 and PB-Q7 the same day, asked for authentication now, and left PB-Q4's timing of modes and PB-Q5 to the unit, which chose decisions 9 and 11. They answered PB-Q8 to PB-Q11 the same day, which became decisions 12 to 14, and accepted three projections beyond the two first proposed in decision 14. The [sketch](../../developer/sketches/studio-publication.md) holds the questions.

The addendum of 2026-11-19 was raised by a test of decision 13's ordering for every command that writes several aggregates (MSA-F6 of the multi-store unit), which found a deletion whose tombstone lost to a save and left the row live. The maintainer answered on 2026-11-18 that the deletion wins. Points 1 to 3 are as built by MSA-F7. Point 4 comes from the review of 2026-11-19 and is built by MSA-F11. Point 5 and the paragraph on what the addendum admits come from the maintainer's question of 2026-11-20 on whether it can leave the store inconsistent. The maintainer accepted both that day and asked for a design that admits no such state, which is MSA-I14 of the multi-store unit, with the states recorded as TD-166 to TD-171. Point 5 is built by MSA-F15.

The addendum of 2026-11-25 is the design the maintainer asked for on 2026-11-20, MSA-I14 of the multi-store unit. The maintainer answered MSA-Q23 on 2026-11-24, which is point 8, MSA-Q21 the same day, which is points 1 and 2, and MSA-Q22 and MSA-Q29 on 2026-11-25, which are points 6 and 9. Point 7 states a condition the models found the order to rest on. The maintainer asked on 2026-11-25 that point 3 name no count, since it is a deployment's to set. Point 10 pays TD-180 and TD-181, the second of which is built, and the addendum as a whole is meant to pay TD-166 to TD-172. The models are X5, X7, X8 and X9 of `tools/models/multi-store-protocols`, and the probes are recorded as TSD-80. Oxigraph on disk is the store of the second limit (TSD-73). Point 2 rests on the addendum of 2026-11-25 to ADR-A123 for the unit construct, and MSA-Q24, on the exception MSA-F15 makes to point 5, was answered (c) on 2026-11-25. MSA-F17 makes the attempts and waits of point 3 a deployment's configuration.
