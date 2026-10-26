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
| R1 | Re-read the three extrapolated standards rewritten on review, STD-004, STD-016 and STD-024. The other eleven are ratified | maintainer | rewritten 2026-10-25 from the maintainer's notes, so the new wording is not yet ratified |
| R2 | Done 2026-10-26. All 320 facet values ratified by the maintainer | maintainer | |
| R3 | Review the facet tags on the 543 register entries. 347 were retagged on 2026-10-26 with the most specific value the enriched scheme offers, such as physical data modelling, identity design, performance testing, parallelism and readability | maintainer | a wrong tag lowers an entry's rank for the questions that name the right one. A tag that is too broad still matches, so a review sharpens rather than repairs |
| R4 | Ratify mechanisms (83), capabilities (71) and patterns (54). Standards and principles are ratified, except STD-004, STD-016, STD-021, STD-024, STD-038, STD-040, STD-043 and PRI-02 | maintainer | STD-021 is linked as refining STD-016 rather than repeating STD-007. STD-038, STD-040 and STD-043 are now scoped as internal and development-only |
| R5 | Re-source the principles that rest on the platform plan v0.2, PRI-51, PRI-52, PRI-53, PRI-54, PRI-60, which is no longer where the guardrails for agentic development are kept | maintainer | ratifying a principle is now its grounding, and a principle citing no decision is found by query rather than failed |
| R7 | Review the scope each entry was given from where its text lives. Standards, principles and patterns now state an audience and a phase, and those values were not part of the ratification | maintainer | 184 of the 235 practice standards are internal and development-only, so a query for runtime design leaves them out |
| R6 | Scope standards to the quanta they govern. 256 of 270 have no `Governs`, which means they apply to every quantum | maintainer | a standard that binds one quantum and is read as binding all of them over-constrains the rest |

## Decisions

| # | Task | Owner |
|---|---|---|
| D1 | PDD-12: whether MORK, Persistence, SPC and Surface leave the substrate's release | maintainer |
| D2 | The process view: which artefacts define a process quantum, so it can be derived | maintainer |
| D3 | Which characteristics warrant a holistic or a continual fitness function. All 18 checks that enforce a standard are atomic and triggered | maintainer |
| D4 | Which of the 14 extrapolated standards get a check, and which record why they cannot, as STD-002 requires | maintainer |
| D5 | Add the method and naming principles the principle register left out, such as testing methodology and coding style, which were scoped out by mistake | agent drafts |
| D6 | TSD-37: whether `ontology/mork/test/data/Contracts.ttl` is live input or an orphan | maintainer |

## Clean-up the index has found

None blocks activation. Each is a defect the index surfaced, recorded where it belongs.

| # | Task | Owner |
|---|---|---|
| C1 | Done 2026-10-26. The seven decisions' `## Status` sections became `**Status:**` header fields, so each has its status in the index | agent |
| C2 | Add a `**Unit:**` line to the 96 decisions without one | agent drafts |
| C3 | Done 2026-10-26 except two. Non-breaking hyphens, spaced spellings and old-style titles corrected, except in one review record whose lines carrying them also carry its own semicolons. `ADR-A-C1` and `ADR-A-C2` are left, since those decisions' own titles write them so and only their filenames say `ADR-AC1` and `ADR-AC2`. Which spelling is canonical is the maintainer's choice (C11) | agent |
| C4 | Review the 26 citations of register entries since removed, `identifiers.py --rehomed`. A document citing one may be stale | maintainer |
| C5 | Draft ADR-A101, ADR-A108 and ADR-A109, or remove the references to them. They are in `tools/knowledge/identifier-exceptions.txt` as planned and never drafted | maintainer |
| C6 | TD-78, TD-79 and TD-80 | agent drafts |
| C7 | Give six platform components and two apps a README, so they have a capability row: `platform-outbox`, `release-integration`, `semantic-dataset-fuseki`, `semantic-dataset-spi`, `semantic-policy`, `surface-workflow`, `mork-review-workbench` and `surface-contract-studio` | agent drafts |
| C8 | Done 2026-10-26. The root package's `knowledge` extra declares PyYAML, pyoxigraph, numpy, tokenizers and onnxruntime, and `bootstrap:python` installs it | agent |
| C9 | Done 2026-10-26. The seven registers moved from `docs/developer/plans/` to `docs/developer/`, with every reference updated | agent |
| C10 | Give the Ensemble principles, PRI-38 to PRI-42, an owner. They name every ontology, and the Ensemble module they govern has no catalogue entry yet | maintainer |
| C11 | Done 2026-10-26. The maintainer chose `ADR-A-C1` and `ADR-A-C2`, as the decisions title themselves and as the other epic blocks are written. Their files were renamed to match | maintainer |

## History

- 2026-10-24. Unit started. Identifier check, sketch, ADR-A134, T-Box, extractor, query surface, the mechanism register and the design-shape scheme built. The resident server was dropped on a measurement (TSD-38).
- 2026-10-25. Standards and principles ratified by the maintainer, with seven standards and one principle held for rewording or scope. Every entry now states its scope.
- 2026-10-25. Capability, pattern, principle and standard registers built. Pointers became anchors resolved at every build, and a query rebuilds a stale index. Architectural quanta derived per view (ADR-A134 addendum). This record written, with the tasks that remain.
- 2026-10-26. Two embedding models compared on 47 questions and five held out. `find` built on `BAAI/bge-small-en-v1.5`, reversing ADR-A134 decision 8 (addendum of 2026-10-26). Every capability, pattern, principle and standard given a problem shape, and the unnamed standards a name. The Java minting library given its capability row, CAP-72, after a held-out question found the gap. `AGENTS.md` instructs asking first and falling back, and a register gap is technical debt (STD-272).
- 2026-10-26. The design-shape scheme retired, replaced by facets in SKOS with several broader values allowed (ADR-A134 decision 24). Every register entry tagged with Activity, Quality and Technology. Facets raise matching entries rather than filter them, measured over the bake-off questions (decision 25). The scheme enriched to 274 values from SWEBOK, DAMA-DMBOK, TOGAF and ISO/IEC 25010 and 25012, for review.
- 2026-10-26. The facet scheme ratified (R2). Store findings take their technology from their Evidence lines and headings, derived rather than authored, so all 39 carry one. The clean-room decisions renamed to ADR-A-C1 and ADR-A-C2 (C11). A2 approved and done.
