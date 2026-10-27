<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A134: A knowledge index over the working documents, and a design-shape vocabulary to retrieve it by

**Status:** Accepted 2026-10-24
**Date:** 2026-10-24
**Related:** [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (the extraction contract this generalises), [ADR-A121](ADR-A121-repository-catalogue.md) (where things live, stated once), [ADR-A117](ADR-A117-agent-guidance-and-skill-library.md) (the agent guidance this shrinks), [ADR-A127](ADR-A127-published-architecture-decisions.md) (a published document never cites a working one), [ADR-A128](ADR-A128-efficient-queries-and-shapes.md) (the rules a generated query obeys), [ADR-A129](ADR-A129-one-release-for-the-substrate.md) (the release this sits outside), [ADR-A125](ADR-A125-test-support-tooling.md) (Oxigraph as the default engine)
**Unit:** [`knowledge-index`](../../developer/sketches/knowledge-index.md) (sketch)

## Context

An agent making a design decision here has to know what the project already decided, found out, forbade and built. Today it finds out by reading documents, and the documents are large. A live view of the `applied-insurance-reference`, `computable-contract-substrate` and `formal-methods` epics is 89 files, 1.85 MB and about 463,000 tokens, which is two and a half context windows to answer one question about one decision. The same bill is paid again for coding standards, a layer's design principles, the literate-specification requirements, and what we know about each triple store. Agent guidance has grown a note for each of those telling an agent which directory to scan, and each note is a reading bill rather than an answer.

Two failures follow. Retrieval is unaffordable, so it is skipped, and an agent works from what is in front of it. Worse, **recall is impossible rather than merely expensive**: an agent designing an append-only log does not know the identifier of the thing it should read, so it cannot look up what it cannot name. An agent once proposed building a versioning system although Foundation already models one. That error costs a slice, not a context window.

The collateral measures 700 tracked Markdown files and 9.7 MB, holding some 950 distinct stable identifiers across 9,645 mention sites, in seven families. Alongside it sit 270 Turtle documents, about 41,330 triples and 3,049 declared terms.

Three things already in the repository decide the shape of the answer. `tools/literate_extract.py` and `tools/literate_grammar.py`, 2,061 lines under [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md), already compile fenced blocks in a layer README into Turtle, a Python module and Isabelle theory, on the stated principle that the prose is authoritative and the compiled artefact is derived so the two cannot drift. `tools/published_decisions.py` already parses the decision headers. `pyoxigraph`, `rdflib` and `pySHACL` are already installed, so the work adds no dependency.

A survey of open-source alternatives found none that indexes knowledge collateral with semi-structured headers, RDF artefacts and multi-language code behind one typed, permissively licensed, offline query surface. The closest candidates each fail on a different axis, and the only attempts at the intersection are unmaintained prototypes. Two otherwise capable code indexers were rejected on a stronger ground than their licence or maintenance risk: they index symbols, and the failure we actually suffered was at the altitude of a design concept, which no call graph would have caught.

## Decision

**1. The knowledge index is a new extraction contract over working documents, not a new subsystem.** It generalises [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) from layer READMEs to the registers, plans, sketches and decisions. Markdown stays the source of truth, the graph is derived, and the index holds no content of its own. Deleting it loses nothing but speed.

**2. Derived facts only, each keeping exactly one source.** Decision metadata comes from the decision headers, module and path facts from `repository-catalogue.md` (read, never restated), layer edges from `owl:imports`, slice-to-file edges from git history. A fact authored only in the graph makes the graph a second thing to maintain by hand, and it will drift as `docs/developer/INDEX.md` has, at 1,005 hand-maintained lines last updated four weeks before this decision.

**3. The claim is extracted, never authored twice.** Each node carries one sentence, at most 200 characters, taken from the bolded lead sentence of its Markdown entry in the shape `pending-design-decisions.md` already uses.

**4. Two artefacts, both under `tools/knowledge/`.** An OWL T-Box for the node kinds and their relations, and a SKOS scheme for the design shapes. They describe this repository rather than the domain, and a published document may not cite a working one ([ADR-A127](ADR-A127-published-architecture-decisions.md)), so they sit outside `ontology/` and outside the substrate release of [ADR-A129](ADR-A129-one-release-for-the-substrate.md). Namespace `https://www.nebularis.org/neuro-semantic/lattice/dev/knowledge#`, prefix `ki:`, where the `dev` segment marks it as not part of the release.

**5. A real T-Box, not SKOS alone, because SHACL cannot check what has no domain and range.** "No Accepted decision depends on a Proposed one" needs `ki:dependsOn` to have a stated domain and range and `ki:status` to point at a typed individual rather than one of fifteen freeform strings. SKOS is kept for the design shapes alone, where `broader` and `narrower` are what the taxonomy needs, and `ki:tagged` has range `skos:Concept`.

**6. A class or property enters the T-Box only when a query or a check needs it.** Only this repository consumes the T-Box, so changes are additive and there is no compatibility promise to keep. This decision is what stops that freedom becoming a modelling hobby.

**7. A declared edge and a derived edge are different properties.** An edge a document states, such as a register's "Waits for" column, is trusted. An edge inferred from two identifiers appearing on one line is a hint, and is a separate property. **SHACL constraints read only declared edges**, because mixing them would make every check as reliable as a co-mention.

**8. Recall matches on the controlled vocabulary, not on embeddings.** The vocabulary makes recall exact, deterministic and checkable, and maintaining a SKOS scheme with SHACL validation is work this project already does. The cost is that an untagged node is invisible. The decision is not irreversible: the query surface records every query that returns nothing, and that miss log is the only admissible evidence for later adding vectors, which would then be built over the claim sentences and not over 9.7 MB of prose.

**9. A design shape is phrased as a problem, never as a technique**, because an agent matches against it before knowing the solution. Target size is 40 to 70 concepts in at most three levels. A node carries two to four shapes. An unknown tag fails the check, so the vocabulary cannot fork silently.

**10. Three new registers, beside the five that exist.** Principles, patterns and mechanisms, each a Markdown table whose row shape is the schema and whose authoring interface is a table row, never Turtle. The mechanism register is the one with no home today and the clearest payback, because it is what answers "does this already exist".

**11. Enumeration is from `git ls-files`, never a filesystem walk.** A checkout can hold ignored directories of confidential third-party material. The same rule excludes any third-party indexer pointed at this checkout, whatever its capability, and it excludes a tool with a hosted tier for the same reason.

**12. A design shape never names private work.** Shapes are substrate-neutral problem statements. A shape naming work that belongs to a private project would carry that work into a public vocabulary. A private project's own index is a separate graph with no link to this one.

**13. The store is Oxigraph on disk under `.build/`, built on bootstrap, refreshed when a source changes, and never committed.** A reader opens it read-only, which is both the faster mode and the one that cannot write by accident.

**14. There is no resident server process.** Measured and recorded as TSD-38 in [the discovery record](../triple-store-discovery.md): over 72,832 quads and 23.7 MB, a read-only open costs 23.8 ms against 141 ms read-write, queries cost 0.1 to 0.9 ms, and a whole process is 50 ms end to end. Twenty queries in a prompt cost one second, against which a server must be supervised, has a lifecycle to get wrong, and cannot be relied on where a process does not persist. The open is a fixed cost while the queries are not, so this is re-measured if the corpus grows by an order of magnitude.

**15. A family is extracted and checked only once its definition rule is written.** A family without one is counted and never failed, so nothing is reported broken on the strength of a rule nobody has written, and nothing is silently half-indexed. The load is per document and reports which failed, because one unparseable fixture would otherwise lose the whole corpus (TSD-37).

## Consequences

**What this buys.** A design lookup costs about 4,000 tokens against the ~463,000 of reading three epics. Recall becomes possible at all, which is the point rather than the saving. Each "go and scan directory X" note in the agent guidance is replaced by one query, so the guidance shrinks instead of growing. And a class of check becomes writable that is not writable today, listed in the sketch §12: a decision resting on something unratified, a slice with no epic, a principle with no supporting evidence, a pattern recommended without its cost, a register row that has drifted from the code it names.

**What it costs.** About twenty hours of maintainer time for the backfill, almost all of it ratifying rows an agent drafted rather than authoring them, and most of it in the three new registers. The sketch §8 states the row shape, the tagging rules and the per-register estimate. The work is forward-only first and backfilled by demand, with the miss log deciding the depth, so the index is useful from the first register rather than after the last.

**The main risk is tagging discipline.** An untagged node is invisible, and a half-tagged corpus looks complete while being partial, which is worse than an empty one. The mitigations are that an unknown tag fails the check, that the vocabulary stays small enough to hold in mind, and that the miss log turns an invisible gap into a named next row. A second risk is vocabulary drift into near-synonyms, which is why a new concept is ratified as a decision is.

**What this does not do.** It does not replace the existing checks that already read Turtle, such as the import guard, and rewriting those as SHACL would be a lateral move. It indexes no code symbols, on the ground that the failure we suffered was conceptual. It holds no narrative, so an agent still reads the document once the graph says which one.

## Addendum of 2026-10-25: architectural quanta, derived per view

The maintainer clarified the term the architecture skill used without defining it, following *Building Evolutionary Architectures* (Ford, Parsons, Kua and Sadalage). **An architectural quantum is the smallest set that must change and be released together because of its coupling, so its size is the lower bound on incremental change.** It grows with every dependency. It is also the scope that architectural characteristics, and the checks that test them, apply to. The term is distinct from the claims ontology's `clm:Quantum`.

**16. A quantum is derived from coupling, never declared, and separately in each view.** One module or component falls into different quanta in different views. The data view reads imports among the ontology modules and the catalogue's kinds. The substrate layers are one quantum, and any other module is its own unless the substrate imports it, in which case the substrate's quantum grows to take it in. The software view is per deployment, read from what each component's configuration points at. Components sharing a store, or calling one another synchronously, are one quantum. A broker separates components only where nothing else couples them. The process view is modelled and not yet derived. `tools/knowledge/quanta.py` holds the rules.

**17. A standard is scoped by the quantum it governs**, `ki:governs`, replacing `Owner` on the standard register. A standard with none applies to every quantum. Ownership, where something lives, stays `ki:ownedBy` on the other registers, since it is a different fact.

**18. A check that enforces a standard is a fitness function, classified by scope and cadence.** Atomic or holistic, triggered or continual. Every check today is atomic and triggered. Nothing assesses characteristics in combination and nothing runs continually, and the classification makes that a query rather than an impression.

**19. The design standards are rules about connascence, and bind hardest across a quantum boundary.** Addressing by name rather than position, closed values rather than free text, and one record per thing each weaken a form of connascence. Inside a quantum a stronger form is tolerable. Across a boundary it is not, and every failure that led to those standards crossed one.

Two findings were derived on the day. MORK, Persistence, SPC and Surface share the substrate's release number although nothing in the substrate imports them, so ADR-A129 places them across a quantum boundary. Whether they should leave that release was not decided here, and ADR-A129's addendum of 2026-10-26 took them out of it. And in the authoring deployment the service and its worker talk through RabbitMQ yet share Fuseki, so they are one quantum, and the broker does not separate them.

## Addendum of 2026-10-26: ranking by meaning, and falling back

Decision 8 held that recall matches on the controlled vocabulary and not on embeddings, with the miss log as the evidence that could reverse it. The log showed questions phrased in words no entry used, "tracking state" among them, and tagging 540 rows to the scheme had not begun. We measured instead. Two embedding models ranked all 580 register entries and store findings against 47 questions mapped by hand to their expected answers, and against five more the maintainer wrote without reading the registers.

| Model, over name, claim and problem shape | an expected answer in the top 5 | mean reciprocal rank | a question, cold, process to answer |
|---|---|---|---|
| `minishlab/potion-retrieval-32M`, static | 0.72 | 0.76 | 0.29 s |
| `BAAI/bge-small-en-v1.5`, ONNX on onnxruntime | 0.91, and 0.95 with problem shapes | 0.82, and 0.93 | 0.20 s |

Embedding a section's first prose with each entry made both measures worse, because a section that serves several entries gives each the same unrelated text. On the five unseen questions, every one had a right answer in its top five whether or not the entries had problem shapes, so the rise from 0.91 to 0.95 is probably fitted to questions the problem shapes were written alongside.

**20. Recall ranks by meaning, after filtering exactly.** `graph:ask -- find` filters on the facets an entry states, then ranks what remains by the cosine of its embedded name, claim and problem shape against the question. This reverses decision 8. The model is `BAAI/bge-small-en-v1.5` (MIT licence) at a pinned revision, checked by SHA-256, fetched into `.build/knowledge/model/` on first build and never committed. The vectors sit beside the store, keyed by a digest of each text, so a rebuild embeds only what changed. A process costs about 0.5 s end to end, so decision 14 stands. The design-shape scheme of decisions 9 and 12 is to be replaced by facets, recorded when they are built.

**21. A downstream index that ranks LATTICE's entries with its own embeds with the same model and revision.** Vectors from two models do not share a space, so a score between them means nothing. The model is part of what the index publishes, as its T-Box is.

**22. The index never proves an absence.** When `find` has no entry close to a question, it says so, and the agent falls back to reading the documents and the code as it would without the index. A single threshold separates answerable questions from unanswerable ones only roughly, and a filter changes which entries compete, so the threshold is advice to look further, never a verdict.

**23. A register gap is technical debt.** An answer the fallback finds in the repository that no register entry holds, such as the Java minting library that had no capability row, is reported to the maintainer and closed by adding the entry, or recorded in the technical-debt register until it is. STD-272 states the practice, and `AGENTS.md` instructs it.

**24. Facets replace the design-shape scheme.** The scheme of decisions 9 and 12 is removed with its `Shapes` column. Six tags in all had been written against it, and ranking by meaning now does the work its synonyms did. In its place, `tools/knowledge/facets.ttl` holds three SKOS concept schemes, Activity, Quality and Technology, each value with a definition, read from three register columns. A value may have several broader values, as SKOS allows, so Java is both a language and a platform, and a filter on a broader value reaches every value under it. SKOS rather than OWL classes, because these are values the maintainer amends, not facts a check reasons over. Decision 12's rule carries over, so a facet value never names private work. Each facet follows a published division of its field, so it needs few additions. Activity follows SWEBOK v4, DAMA-DMBOK 2, TOGAF's architecture domains and the DevOps loop, Quality follows ISO/IEC 25010:2023 and ISO/IEC 25012, and Technology covers what this repository uses and what an agent is likely to ask about. A value that only organises others is marked as a group and never tagged. Two values in different facets may be related, as UX design is to interaction capability, and naming one raises entries tagged with the other.

**25. Kind, phase and audience filter. Activity, quality and technology raise.** This refines decision 20. Kind, phase and audience are closed facts an agent states on purpose, so they filter exactly. Activity, quality and technology are judgements that two reasonable taggers disagree on, such as whether recording valid time is ontology design or query writing, so a match adds 0.02 to an entry's score for each facet and a mismatch hides nothing. A question's value matches an entry's when one lies on the other's broader chain, never through a shared group. The test that an answer is weak reads the meaning score alone. Over the same questions, run with the facets an agent would name, a hard filter on every facet lowered the held-out questions with an expected answer in their top five from 1.0 to 0.8, because an answer tagged with a neighbouring activity was removed. The boost kept them at 1.0 and raised the 47 questions from 0.91 to 0.98. A weight of 0.05 began to override meaning. A filter on kind still removes an answer of another kind, which is why an agent is told to widen a filter that answers weakly.

## Addendum of 2026-10-26: the facets are authored as a register

Decision 24 placed the facet schemes in `tools/knowledge/facets.ttl`, edited by hand. Every other register, the decisions and the layer READMEs are Markdown that a tool reads or generates Turtle from, so the facets were the one register a contributor could not amend as a table row, and the index had two authoring forms to keep in step (TD-81).

**26. The facets are authored in the facet register, and their Turtle is generated on every build.** [`docs/developer/facets.md`](../../developer/facets.md) holds a table of the three schemes and a table per scheme, one row per value, whose columns are the SKOS properties that state their meaning. `tools/knowledge/facets.py` writes them into `.build/knowledge/facets.ttl` at the start of every build, and the Turtle is never committed, as STD-003 requires of anything a tool can derive. A malformed register, such as a broader value defined nowhere or one in another scheme, fails the build with its line rather than loading a forked scheme. The graph generated from the register was isomorphic to the hand-written file, 1,757 triples each, less its version, which is dropped since nothing outside this repository imports the facets. Decision 24 stands in every other respect.

## Addendum of 2026-10-26: the environments under runtime

Phase had three values, development, authoring and runtime. A rule that binds only while tests or benchmarks run, such as how to change a shape safely, had none of its own, so it carried runtime, and an agent designing a live service who filtered on runtime was handed it.

**27. Testing, benchmarking and production are phases under runtime, and a phase matches along its broader chain.** Each is a `ki:Phase` with `skos:broader ki:Runtime` in `knowledge.ttl`. A rule that binds in every environment, such as one for generated code, stays tagged runtime, and one that binds in only some is tagged with each. A question's phase matches an entry's when one lies on the other's broader chain, as a facet value does under decision 25, so a question about production finds a rule tagged runtime, a question about runtime finds a rule tagged testing, and testing never finds production. Phase still filters exactly in every other respect. Another environment, such as user acceptance testing, joins as one more phase under runtime. We chose this over adding testing and benchmarking beside runtime, which left no value for a rule that binds in every environment, such as fixing a vulnerability wherever the code runs. Applying it moved 25 register rows from runtime to the phases they bind in, and left every other runtime row as it was.

## Provenance

The design was presented to the maintainer in session on 2026-10-24, over four exchanges that narrowed it from a blast-radius index to this, and was approved in writing, including the T-Box split of decision 5 and the store choice of decision 13, both of which the maintainer proposed. The maintainer authorised recording the decisions as accepted without separate countersignature, and authorised the work on the `docs/placement-vehicles-structure` branch. Decision 14 replaced an earlier proposal for an optional long-running server after the measurement in TSD-38 was taken. The alternatives considered, the survey of open-source tools behind the Context section, and the costs are in the [sketch](../../developer/sketches/knowledge-index.md).

The addendum on the facet register (decision 26) was approved by the maintainer on 2026-10-26 before it was drafted, with its four choices: a register table per scheme, the file beside the other registers, the version dropped, and an addendum rather than a change to decision 24.

The addendum on phases (decision 27) was approved by the maintainer on 2026-10-26, who chose phases under runtime over phases beside it, so that a rule can bind in every environment and new environments can join.

## Addendum (2026-10-27): a decision is embedded by its sections as well as its claim

Decision 20 ranks an entry by the cosine of its embedded name, claim and problem shape. For a decision that holds several numbered decisions, that text is its title and the first 200 characters of its Decision section, so ADR-A122's embedded claim was its decision 1 in thirty-four characters. A question about its decision 8, that a named graph's IRI is injective in its root, returned a superseded policy and two adjacent entries and never ADR-A122. The same held for every later numbered decision and for all 68 addenda across 33 decision files, where ADR-A77 holds 20 numbered decisions and ADR-A104 holds 16.

**A decision node now carries one vector per numbered decision and per addendum, besides its own.** An entry is scored by the best of them, and where a section wins, the row reports that section's line range instead of the whole file, so the reader lands on the part that answered. The node keeps its single identifier, its claim, its kind and its status, and the candidate set that facets filter is unchanged. Section nodes carry only `ki:sectionOf`, `ki:claim` and `ki:pointer`, with no identifier and no type, so they are never entries in their own right.

**This is not the negative result above.** Embedding a section's first prose with each entry made both measures worse, because one section serving several entries gave each the same unrelated text. Here a section belongs to exactly one decision and holds that decision's own words, which is the opposite arrangement.

**Measured on the corpus, 2026-10-27.** 430 numbered items and 68 addenda give 498 sections. Vectors rise from 817 to 1,315 and the store from 82,985 to 84,484 quads. A cold build goes from 12.7 s to 37.5 s, which is 2.95 times, and every later build is unchanged at 2.3 s because the per-text digest cache is untouched. A section's text is capped at 600 characters, chosen because a larger cap was expected to take the cold build past three times the old one.

The two questions that prompted this now answer. ADR-A122 returns at 0.82 pointing at decision 8, and ADR-A123 at 0.82 pointing at its addendum on who names a named graph, where neither was in the top five before. A decision's own main subject is unaffected: ADR-A122 still returns at 0.85 for a question about classified boundary shapes, with its whole-file pointer, because its own vector wins.

**What it costs.** Decisions rise against other kinds in general, because a narrow section matches a specific question more closely than a 200-character claim. Over the four questions above and eleven from the miss log, the top five changed in 13 of 15 and the top answer in three. One of those three now puts a grounding decision above the principle it grounds, with the principle third, which the guidance on asking for what is related already anticipates. The other two were weak matches before and after. Where an entry should outrank a decision at equal meaning, a small bias against section-derived scores is the lever, and it was not applied.

**What it does not fix.** A decision whose Decision section is prose rather than a numbered list gets no sections, so its rules retrieve only through the truncated claim. ADR-A74 is the instance, recorded as TD-91.
