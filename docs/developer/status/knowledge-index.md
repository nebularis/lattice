<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Knowledge index: status

**Unit ID:** `knowledge-index`
**Sketch:** [knowledge-index.md](../sketches/knowledge-index.md)
**ADR:** [ADR-A134](../../architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md), Accepted 2026-10-24, with addenda of 2026-10-25 and 2026-10-26
**Branch:** `docs/placement-vehicles-structure`, not merged into `main`
**Mode:** autonomous on the branch, at the maintainer's request

## Position

Built, and instructed on this branch only. The index derives in about two seconds once the model is fetched, `mise run graph:ask -- find` ranks its entries by meaning in about half a second, and `check:knowledge` and `check:identifiers` pass. `AGENTS.md` tells an agent to ask it first and to fall back to the documents, but nothing outside this branch can reach it until it is merged.

The tasks below are what remains. Owner says who acts: **maintainer** for a decision or a judgement only the maintainer makes, **agent drafts** where an agent prepares the change and the maintainer approves it, **agent** where it needs no judgement.

## Activation

Without these, no agent uses the index. In order.

| # | Task | Owner | Why it blocks |
|---|---|---|---|
| A1 | Done 2026-10-26. `AGENTS.md` says to ask `find` first, to ask more than once, to fall back to the documents on a weak answer, and to report a register gap (STD-272). The design and lifecycle skills point at it | agent drafts | |
| A2 | Done 2026-10-26, approved by the maintainer. Seven corpus-wide reading instructions in `AGENTS.md` and the design, ontology-authoring and triple-store skills now ask the index first, and fall back to the whole document when it answers weakly | agent drafts | |
| A3 | Decide whether the commit hooks run `check:identifiers` and `check:knowledge` on a change to a register or a working document, under [ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md) | maintainer | today a row an agent writes, with a dangling identifier or a tag outside the scheme, is caught only by a manual `mise run check` |
| A4 | Done 2026-10-26. `mise run bootstrap` builds the index through `bootstrap:knowledge`, after the Python packages, and fetches the model on first run | agent | |
| A5 | Merge into `main`, or have the knowledge-index commits taken onto a branch of their own first. 18 of the branch's 44 commits are this unit's, interleaved with the Ledger and Ensemble work. Run `mise run hooks:merge` before merging on GitHub | maintainer | every other branch and every cloud agent works from `main` |

## Ratification

The index is useful before this is done, and a row is found by its own words even unratified. Ratifying makes it trustworthy. Sketch §8 states the row shapes and the estimate of about 21 maintainer hours.

| # | Task | Owner | Note |
|---|---|---|---|
| R1 | Done 2026-10-26. STD-004, STD-016 and STD-024 ratified by the maintainer | maintainer | |
| R2 | Done 2026-10-26. All 320 facet values ratified by the maintainer | maintainer | |
| R3 | Done 2026-10-26. The maintainer spot-checked the quality tags and the mechanism register and approved all the facet tags | maintainer | |
| R4 | Done 2026-10-26. The maintainer ratified every row of the mechanism, capability, pattern, principle and standard registers | maintainer | |
| R5 | Re-source the principles that rest on the platform plan v0.2, PRI-51, PRI-52, PRI-53, PRI-54, PRI-60, which is no longer where the guardrails for agentic development are kept | maintainer | ratifying a principle is now its grounding, and a principle citing no decision is found by query rather than failed |
| R7 | Review the scope each entry was given from where its text lives. Standards, principles and patterns now state an audience and a phase, and those values were not part of the ratification | maintainer | 184 of the 235 practice standards are internal and development-only, so a query for runtime design leaves them out |
| R6 | Deferred to TD-82 by the maintainer, to be done as the architectural fitness functions are brought to life | maintainer | |

## Decisions

| # | Task | Owner |
|---|---|---|
| D1 | PDD-12: whether MORK, Persistence, SPC and Surface leave the substrate's release | maintainer |
| D2 | The process view: which artefacts define a process quantum, so it can be derived | maintainer |
| D3 | Which characteristics warrant a holistic or a continual fitness function. All 18 checks that enforce a standard are atomic and triggered | maintainer |
| D4 | Which of the 14 extrapolated standards get a check, and which record why they cannot, as STD-002 requires | maintainer |
| D5 | Drafted 2026-10-26. PRI-63 to PRI-74 state testing, naming, writing, reporting and publication principles the repository already holds, unratified. The standards they sit above do not yet point to them through `Supports` | agent drafts |
| D6 | TSD-37: whether `ontology/mork/test/data/Contracts.ttl` is live input or an orphan | maintainer |

## Clean-up the index has found

None blocks activation. Each is a defect the index surfaced, recorded where it belongs.

| # | Task | Owner |
|---|---|---|
| C1 | Done 2026-10-26. The seven decisions' `## Status` sections became `**Status:**` header fields, so each has its status in the index | agent |
| C2 | Partly done 2026-10-26. 27 decisions gained a `**Unit:**` line where the evidence names one unit. 57 are left because their evidence names several units or none, and 11 Published decisions found a unit but may not link a working document outside their Provenance section (C12) | agent drafts |
| C3 | Done 2026-10-26 except two. Non-breaking hyphens, spaced spellings and old-style titles corrected, except in one review record whose lines carrying them also carry its own semicolons. `ADR-A-C1` and `ADR-A-C2` are left, since those decisions' own titles write them so and only their filenames say `ADR-AC1` and `ADR-AC2`. Which spelling is canonical is the maintainer's choice (C11) | agent |
| C4 | Deferred to TD-83 by the maintainer | maintainer | |
| C5 | Done 2026-10-26. ADR-A101, ADR-A108 and ADR-A109 drafted as Proposed, at a high level with every modelling question left open | maintainer | |
| C6 | Done 2026-10-26 except TD-80, which stays open by the maintainer's decision. TD-78 paid, so `repo_files` lists files from git and refuses a checkout without `.git`. TD-79 paid, with the duplicate compiler removed. `morkSC_Test.py` revived as `test_morkSC.py`, 15 tests | agent drafts |
| C7 | Done 2026-10-26. The eight components have READMEs and capability rows CAP-73 to CAP-80, unratified | agent drafts |
| C8 | Done 2026-10-26. The root package's `knowledge` extra declares PyYAML, pyoxigraph, numpy, tokenizers and onnxruntime, and `bootstrap:python` installs it | agent |
| C9 | Done 2026-10-26. The seven registers moved from `docs/developer/plans/` to `docs/developer/`, with every reference updated | agent |
| C10 | Kept as they are by the maintainer, and recorded as TD-84 for the Ensemble unit | maintainer | |
| C11 | Done 2026-10-26. The maintainer chose `ADR-A-C1` and `ADR-A-C2`, as the decisions title themselves and as the other epic blocks are written. Their files were renamed to match | maintainer |
| C12 | Done 2026-10-26. The 11 Published decisions name their unit in their Provenance section, which ADR-A127 allows. STD-070 and PRI-20 now state that exception, which they had left out | maintainer | |
| C13 | Done 2026-10-26. `check:mork` runs tools/mork's 361 tests in about 3 seconds alone and joins the `check` aggregate, which took 139 seconds without it and 157 with it, an upper bound of 13% since other checks ran during the second timing | maintainer | |

## History

- 2026-10-24. Unit started. Identifier check, sketch, ADR-A134, T-Box, extractor, query surface, the mechanism register and the design-shape scheme built. The resident server was dropped on a measurement (TSD-38).
- 2026-10-25. Standards and principles ratified by the maintainer, with seven standards and one principle held for rewording or scope. Every entry now states its scope.
- 2026-10-25. Capability, pattern, principle and standard registers built. Pointers became anchors resolved at every build, and a query rebuilds a stale index. Architectural quanta derived per view (ADR-A134 addendum). This record written, with the tasks that remain.
- 2026-10-26. Two embedding models compared on 47 questions and five held out. `find` built on `BAAI/bge-small-en-v1.5`, reversing ADR-A134 decision 8 (addendum of 2026-10-26). Every capability, pattern, principle and standard given a problem shape, and the unnamed standards a name. The Java minting library given its capability row, CAP-72, after a held-out question found the gap. `AGENTS.md` instructs asking first and falling back, and a register gap is technical debt (STD-272).
- 2026-10-26. The design-shape scheme retired, replaced by facets in SKOS with several broader values allowed (ADR-A134 decision 24). Every register entry tagged with Activity, Quality and Technology. Facets raise matching entries rather than filter them, measured over the bake-off questions (decision 25). The scheme enriched to 274 values from SWEBOK, DAMA-DMBOK, TOGAF and ISO/IEC 25010 and 25012, for review.
- 2026-10-26. The facet scheme ratified (R2). Store findings take their technology from their Evidence lines and headings, derived rather than authored, so all 39 carry one. The clean-room decisions renamed to ADR-A-C1 and ADR-A-C2 (C11). A2 approved and done.
- 2026-10-26. The facet tags approved after a spot-check (R3). Confusable facet values given scope notes, and the pairs most often confused related, so a question naming one raises entries tagged with the other.
- 2026-10-26. Every register row ratified (R1, R4). ADR-A101, ADR-A108 and ADR-A109 drafted (C5). `check:mork` added to `check` (C13). TD-82, TD-83 and TD-84 hold R6, C4 and C10. `AGENTS.md` and every skill now ask the index first, look for related entries, and report misses at each handoff through `graph:ask -- misses`.
- 2026-10-26. TD-81 paid. The facets are authored in the facet register, `docs/developer/facets.md`, one table per scheme, and `tools/knowledge/facets.py` generates `.build/knowledge/facets.ttl` on every build, never committed (ADR-A134 decision 26, approved by the maintainer). The generated graph was isomorphic to the hand-written file, 1,757 triples, less its version, which is dropped. The embedding model could not be fetched in the cloud environment, so `find` did not rank during this work.
- 2026-10-26. Paths from the catalogue, at the maintainer's request. A ranked question about building a path to a repository directory found no standard, since the rule lived only in ADR-A121. STD-273 now states it, pointing at the toolchain skill's new Finding paths section, and CAP-09 says the reader resolves names. The reader gives every root and documentation area a `name` and resolves it with `Catalogue.area` and `area <name>` (ADR-A121 addendum of 2026-10-26). The knowledge tools take the root and their areas from it. TD-87 holds the nine tools that still count `__file__`'s parents, and TD-88 the scan that cannot see them. `AGENTS.md`, the developer guide, and the toolchain, testing and lifecycle skills say how to ask. The embedding model was fetched once `huggingface.co` and its content host were allowed.
