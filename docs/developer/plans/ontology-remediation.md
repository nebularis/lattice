<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: ontology remediation

**Unit ID:** `ontology-remediation`
**Unit type:** Phase, three groups of slices under one plan
**Review:** [ontology-design-review.md](../review/ontology-design-review.md), the design review of 2026-10-28 whose findings this plan remediates
**ADRs:** none yet. OR-1 adds an addendum to [ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md). OR-6, OR-7, OR-9 and OR-15 each propose one
**Status record:** [ontology-remediation.md](../status/ontology-remediation.md), created by OR-0
**Status:** built on `main` 2026-10-28 through OR-18 in one autonomous session, committed slice by slice, never pushed or merged by the unit. What each slice left undone is in the status record. OR-Q12 and the release bump (OR-19) are the maintainer's. Answered questions carry their date in the last section. The rest take the recommended option unless the maintainer says otherwise.

## Scope

Every finding of the review that is not already a slice of another unit, taken in the order the review's §7 gives, with the two cross-cutting pieces the landing analysis (review Addendum A) showed were missing: a check that stops register identifiers colliding across branches, and the guidance for working across branches, worktrees and repositories.

Out of scope: the review's §2.12 (platform authority outside the graph, TD-85), the growth hazards of §4 (TD-47, TD-48), Ledger's own slices (LG-2 takes the account definition, LG-3 takes Behaviour's import), and anything the review confirmed as an existing debt row, which stays with its own unit.

## Principles

- **Mechanical before design.** A slice that needs no decision lands first, on `main`, and `main` is merged into every live branch while they are paused. A slice that changes a design waits for its question's answer.
- **One rule, enforced once.** A modelling rule this plan adds is stated in Foundation, read by one check, and the index can find it. A rule nothing checks is marked Unchecked because.
- **Register first.** Every finding has a row before its fix, so the index can find it (STD-272). The thirteen rows of the review's Addendum B land in OR-0.
- **Measure by content.** A branch is merged when its lines are in `main`, whatever its ancestry says, since branches here are squash-merged.
- **Nothing private.** Every file this unit writes is public. A change made for a reason the repository does not hold is explained by its public rule.

## Decisions taken

| # | Decision | Date |
|---|---|---|
| 1 | the review's §2.1 is remedied by removing and rewording the text in ordinary commits, not by rewriting history | 2026-10-28 |
| 2 | a register identifier defined twice fails a check, at a commit and at a merge, and the earlier row keeps its number ("first in wins"). No provisional identifiers, no reserved ranges, since a long-lived branch must keep its own index fresh | 2026-10-28 |
| 3 | the index is rebuilt after every merge | 2026-10-28 |
| 4 | the thirteen debt rows of the review's Addendum B land on `main` directly after the index remediation, numbered TD-101 to TD-113 | 2026-10-28 |
| 5 | working across branches, worktrees and repositories gets its own skill, `lattice-branching`, rather than sections in `lattice-lifecycle` | 2026-10-28, proposed here, OR-Q2 |
| 6 | `fnd:Version` is renamed `fnd:Versioned` (TD-20) in this unit, and the substrate re-releases once at the merge | 2026-10-28 |
| 7 | `voc:SchemeBinding` stays unversioned. Its ending is a fact of its own, a closure record (OR-Q8 b) | 2026-10-28 |
| 8 | `dal:ProvidedConcurrency` is intentional. It means the store or the application around it serialises writes to an aggregate, so Persistence does not solve for it. OR-10 changes no concurrency baseline and only downgrades overstated claims and settles the epoch guard baseline | 2026-10-28 |
| 9 | the mutable-parts remedy is the recommended one, OR-Q6 (a) and OR-Q7 (a) | 2026-10-28 |
| 10 | the namespaces (§2.2) and canonicalisation (§2.4) are fixed in this unit as recommended, and every law of §2.6 is verified by formal methods, a shape or another mechanism, or owes a debt row | 2026-10-28 |
| 11 | no history rewrite in this unit | 2026-10-28 |
| 12 | the namespaces: SPC moves under the lattice root as `.../lattice/spc#` with its version IRI under it, the store vocabulary `pat:` becomes a second document inside Persistence under its own root, the applied insurance root gains the lattice segment, MORK's http root stays, and the three-roots-per-module pattern is documented and left | 2026-10-28 |
| 13 | the release bump at OR-19 is the maintainer's to run. The unit's last handoff reminds them | 2026-10-28 |
| 14 | the bump happens once, at the end of the unit, not after each slice, so `check:ontology-versioning` reports the changed members unbumped until then | 2026-10-28 |
| 15 | `dct:creator` names the organisation, `https://github.com/nebularis`, in every spec and vocab document (OR-Q13) | 2026-10-28 |

## Landing against the live branches

Measured on 2026-10-28, by content, in the review's Addendum A. The live branches are the ledger branch (`docs/placement-vehicles-structure`, no ontology files), the Oxigraph branch (`claude/jolly-turing-lttm91`, one commit), CCS trunk (`ccs-trunk`, which changes the eligibility spec, its two shapes, its README and `mork/spec/Executable.ttl`) and the studio (`claude/config-authoring-studio` and its four sub-branches, which change `surface/README.md`). FML track H, `docs/literate-v2` and `py-test-xtra` are on `main` by squash.

| Group | Lands | Merges into |
|---|---|---|
| 1, mechanical | a branch from `main` after the index remediation commit, then `main` | every live branch, by merging `main` into each, with register renumbering as the only recurring cost |
| 2, design | one branch per slice, each after its question is answered | the ledger and Oxigraph branches cleanly. CCS trunk and the studio take OR-7, OR-11, OR-15 and OR-17 by rework if they are still open, since those slices change the files they change |
| 3, release | `main`, at the merge of the last group 2 slice | n/a |

Group 1 is the moment to make the broad mechanical change OR-4, since every live branch is paused and a rename by substitution conflicts least before the branches resume.

## Slices

| Group | Slice | Delivers | Validation |
|---|---|---|---|
| 1 | **OR-0** | this plan, the status record, the review moved to `docs/developer/review/`, TD-101 to TD-113 in the register, the index rebuilt | `check:identifiers`, `check:knowledge`, the hooks on the commit |
| 1 | **OR-1** | `tools/knowledge/identifiers.py` reports an identifier defined twice, with each site and its commit date, and fails. `tools/hooks.py` runs it at a commit and at a merge, blocking. A `post-merge` hook rebuilds the index. An addendum to ADR-A133 for the new hook | `test_identifiers.py` with a duplicate in two registers and in two decision filenames, `check:hooks` |
| 1 | **OR-2** | the skill `lattice-branching`, listed in `AGENTS.md`, rebuilt into the Copilot copy | `check:agent-guidance` |
| 1 | **OR-3** | the publication cleanup: the §2.1 text removed or reworded, the eleven deprecated `surface/docs` files and two stray copies deleted, working-document links and slice codes out of READMEs and extracted strings, prompt residue out of two documents, the duplicate capacity performance addendum removed, the vendor model identifier out of the MCN example, the creator names per OR-Q13 | `check:published-decisions`, the link check, `check:literate --check`, `check:deny-terms --all` |
| 1 | **OR-4** | `fnd:Version` renamed `fnd:Versioned` everywhere (TD-20), with the breaking-change line in Foundation's release notes (ADR-A113), the compiler's by-IRI check updated, and no alias (OR-Q3) | `check:ontology-catalog`, `check:persistence`, `check:import-guard`, `check:literate` |
| 1 | **OR-5** | drift: `ontology-architecture.md` retired or regenerated (OR-Q4), the version lines in four READMEs, the ledger row in `ontology-releases.md`, the superseded sections of `ontology-versioning-policy.md` marked, Party's unused import, MORK's SPDX header, figures, formula and `morked` flag | `check:ontology-versioning`, the link check, `check:mork` |
| 2 | **OR-6** | one namespace decision (ADR) for SPC, `pat:`, MORK's http root, the applied insurance root and the three roots per module, then `spc.ttl`, Persistence's README, vectors and benchmark, and the one applied README | `check:spc`, `check:persistence`, `check:ontology-catalog` |
| 2 | **OR-7** | meaning-bearing edges from a versioned node, detailed below: the Foundation annotation and rule, the Persistence compiler refusal, Eligibility's conditions, Behaviour's components, Vocabulary's bindings, Foundation's governance state and Party's occupancy. Ledger's definition is LG-2's | the Foundation shape over every layer's examples, `check:persistence` for the refusal, `check:reference-eligibility`, `check:vocabulary` |
| 2 | **OR-8** | an acyclicity shape on `fnd:supersededBy`, one Foundation paragraph on what a versioned thing's chain is relative to the identity guide, Instrument's two content-addressing sentences corrected, Wording's element hash stated or the claim withdrawn | the Foundation shape against a three-cycle, `check:literate` |
| 2 | **OR-9** | one canonicalisation decision (ADR) adopting Persistence's digest vocabulary, Surface and Quantification stating which triples form the content, MCN's canonical bytes aligned, `qnt:spaceHash` defined | a vector per layer, computed twice, `check:minting` |
| 2 | **OR-10** | Persistence's claims: the uniqueness sentences reworded to what the store's isolation decides, the lost-update example tied to `dal:ProvidedConcurrency` stating that the environment serialises writes, the closing patterns marked as not generated, and the epoch guard baseline per OR-Q15 | `check:persistence`, the resolution-table tests |
| 2 | **OR-11** | laws: an operation and a zero-floor property for Q8, a shape requiring `baseRole` for Q13, law individuals Q1 to Q13 declared, Surface's X5 and X6 wording, SPC's `owl:hasKey` sentences and a uniqueness shape, a register row per law still unrealised | `check:spc`, Quantification's shapes over its examples, `check:formal-freshness` |
| 2 | **OR-12** | Behaviour: `bhv:AllowanceAccount` and `bhv:AllowanceDefinition` deprecated with a shape warning (OR-Q10), the unordered stimuli and layer inversion recorded as debt where not already | Behaviour's shapes over its examples |
| 2 | **OR-13** | the minting specification: five rules and five vectors (dot segments, format characters, surrogate patterns, null against empty scope, width overflow), and the NFC question answered | `check:minting` |
| 2 | **OR-14** | time: zone required, half-open intervals, an estimate marker or an optional `validFrom` (OR-Q14) in Foundation, month arithmetic on positions as a Quantification law with a conformance row | the Foundation shapes, Quantification's conformance table |
| 2 | **OR-15** | one ADR placing `Law`, `OperationalProfile` and `Undetermined` once each, the moves, an OWL 2 DL profile check task over every spec, the `rdf:Property` and `rdfs:Datatype` redeclarations resolved | the new `check:owl-profile`, `check:reference-eligibility` |
| 2 | **OR-16** | Capacity: withdrawn from the release register or marked pre-release (OR-Q11), the `_Version2` file names renamed at the next version, its runtime routed through Persistence or the performance note corrected | `check:ontology-versioning` |
| 2 | **OR-17** | shapes: the seven empty files filled or deleted (OR-Q5), Quantification's twelve obligations realised or marked, Surface's parity shapes under the extraction contract, the vacuous shapes fixed (Wording's date sampling, Persistence's `STRBEFORE` and transitive path, Vocabulary's fallback shape), Eligibility's `owl:AllDifferent` and its double-valued rule | every module's check task, pySHACL over every example |
| 2 | **OR-18** | Instrument pruned (the §4 essay, PREFIX blocks, counts), the binder rename finished, who encoded a clause recorded | `check:literate`, `check:import-guard` |
| 3 | **OR-19** | the release notes listing the breaking rename and the deprecations. `mise run release:prepare` and the tags are the maintainer's, reminded at the last handoff | `check:ontology-versioning`, `check:full-sweep` |

## Slices in detail

### OR-1, the identifier check and the merge hook

`identifiers.py` collects definitions per family with `defined.setdefault(...)`, so a second row with the same identifier is silently dropped. The slice keeps every site per identifier and fails when a family defines one twice, for table-row, heading and filename families alike. Each report names both sites with the date of the commit that introduced the line, from `git blame`, so the rule "first in wins" is decidable from the output: the later row is renumbered, and every citation of it with it, which the resolution check then verifies.

The hook registers the check in `tools/hooks.py`'s registry over the registers and the decisions directory, blocking at a commit and at a merge. A merge commit into any branch runs `pre-merge-commit`, and a resolved or squashed merge runs `pre-commit`, so the duplicate is caught at the merge whichever way it is made. A `post-merge` hook runs `build:knowledge`, about two seconds, so the index is never stale after a merge. ADR-A133 names the hooks it installs, so the new one is an addendum.

### OR-2, the skill `lattice-branching`

Sections. The hooks and what each moment runs, and that a push is never refused. Merging: measure a branch by content, merge `main` into a paused branch rather than rebasing it, renumber register rows by first in wins, resolve `knowledge.ttl` by taking `main`'s and re-adding the branch's own relations, rebuild the index, and run `mise run hooks:merge` before a merge on GitHub. Worktrees: `hooks:install` covers every worktree, `.local/` is per worktree and git-ignored, and a cloud agent's branch is pushed and must not be rebased. Several repositories: a task decides for each repository it writes to which guidance applies, the repository's `AGENTS.md` and the maintainer's private guidance where it exists, never copies between a public and a private repository, and links to a tag instead. The umbrella rules the lifecycle skill already states are linked, not restated.

### OR-7, meaning-bearing edges from a versioned node

The review's §2.3 found four layers where a versioned owner points at parts edited in place, so that a past judgement's inputs change under it. The maintainer asked whether the defect evaporates when the owner is an aggregate under a Persistence configuration, whether nested composition is then needed, how the rule would be enforced, what making `voc:SchemeBinding` versioned entails, and whether to rename `fnd:Version`. The answers, with the index's entries.

**Under an aggregate, the owned parts are covered and the shared parts are not.** An aggregate is a root and the nodes its classified boundary shape owns, written as one unit (MEC-58, ADR-A122). Three conditions make a judgement reproducible from the store. The parts are owned edges of the owner's boundary shape. The family's discipline keeps old state, `dal:AppendVersions` or an in-place write with receipt delta graphs for the as-of read, since under a plain in-place replace the old state goes (MEC-66). Every edge that leaves the aggregate to a node the meaning depends on is `dal:Pinned`, which the compiler already refuses when the target class is not versioned (`PinnedReferenceToUnversionedClass`). So for an owned part no ontology change is needed, and the defect becomes a configuration one: an adopter who compiles the family in place without delta graphs. For a shared part the one-owner rule (ADR-A122 decision 5) means it cannot be owned by two profiles, so it is a reference, so it must be pinned, so its class must be versioned or a content revision. That is the review's rule, restated as Persistence's existing refusal.

**Nested composition is not needed.** A boundary shape is already a tree with nested and recursive components. What Persistence refuses by design is a root inside another root. An account definition inside an instrument's configuration aggregate is a component with an IRI minted under its parent (identity guide §9), and the posting aggregate that uses it pins the configuration aggregate's version. The one gap is that a pin to an owned component rather than a root warns today, and the pin names the root's version, since a component has no chain of its own. OR-Q6 asks which of two small changes closes it, and neither is nested aggregates.

**Enforcement.** The rule has three arms, and in Persistence's terms they are one sentence: a meaning-bearing edge from a versioned node is owned or pinned. What is missing is the mark that says which edges bear meaning, since today only `fnd:Evidence`, `fnd:DerivedArtefact` and record classes get the by-identity warning. The options are in OR-Q7. The recommended one puts an annotation on the object property in the owning layer, a Foundation SHACL rule reads it over data, and the Persistence compiler reads it over configuration, so one mark is checked twice, on examples at validation and on every compiled family.

**`voc:SchemeBinding`.** Today it is `fnd:TemporallyScoped`, and its own utility text says to end a binding's validity and add a new one, which is the `validTo` write the review flagged. Making it versioned adds a second axis to ADR-A85's resolution, which version of each binding as of when, and that is ADR-A108's open ground. The alternative keeps a binding immutable and makes its ending a fact of its own, which is what a binding is in reality, a governance act followed later by another. OR-Q8 had both with their consequences, and the maintainer chose the closure record on 2026-10-28.

**Rename.** TD-20 already records that `fnd:Version` reads wrongly, with the rename to `fnd:Versioned`, and the writing rule says "versioned" already. One substitution over every spec, vocab, shape, example, README, tool and test, the `owl:members` list, and the compiler's by-IRI check: 307 uses in 100 tracked files on 2026-10-28, 26 of them in the Persistence compiler and its tests, against 199 in 66 when TD-20 was written. A breaking change at major version zero is a minor bump marked in Foundation's release notes (ADR-A113), and under one release (ADR-A129) every substrate module and the applied modules that import Foundation move together at the merge by `release:prepare`, which is the re-versioning asked for. It is OR-4, in group 1, since it is mechanical and the branches are paused.

## Effects on other units

| Unit | Effect |
|---|---|
| ledger (LG-2) | takes the account definition's instance of OR-7, as the slice is briefed. OR-7 lands the rule and the shape first, or LG-2 states the definition as versioned under the rule's text and the shape follows |
| computable contract substrate (CCS) | OR-7's Eligibility conditions, OR-15's `Law` and `OperationalProfile` and OR-11's `Executable.ttl` change files CCS trunk changes, so those land after CCS trunk merges or CCS takes them |
| the studio | OR-9 and OR-11 change `surface/README.md`, which the studio changes |
| formal methods | Q8, Q13 and the acyclicity shape become proof targets, and `check:formal-freshness` is in OR-11's validation |
| applied insurance reference (AIR) | OR-6 moves the applied root, OR-16 withdraws or marks Capacity, and the peril and exposure provenance is recorded in its own unit |
| git hooks | OR-1 extends the registry and adds a hook |
| knowledge index | OR-0 adds thirteen rows, OR-1 rebuilds after every merge, and OR-7's annotation becomes a term the index can find |

## Releases

One release at OR-19, with a breaking line for the rename and deprecation lines for Behaviour's allowance classes and for whatever OR-6 renames. No bump mid-branch (lifecycle skill). Tags are the maintainer's.

## Done when

Every row TD-101 to TD-113 and TD-20 is closed or re-pointed at a slice of another unit, no register identifier is defined twice on `main`, a duplicate fails at a commit and at a merge, the seven shape files are gone or non-empty, no `example.org` IRI is released, no public document names what the project does not, `mise run check` and `check:full-sweep` pass on `main`, and the release register has one new row per substrate module.

## Questions

Answers go in the table and in the status record's history. The maintainer is working through them.

| # | Question | Options and consequences | Recommended | Answer |
|---|---|---|---|---|
| OR-Q1 | Does a `post-merge` hook rebuild the index? | (a) yes, two seconds after every merge, an ADR-A133 addendum. (b) no, the skill says to run it, and a stale index after a merge is the agent's fault | (a) | (a), 2026-10-28 |
| OR-Q2 | A skill of its own for branches, worktrees and repositories, or sections in `lattice-lifecycle`? | (a) `lattice-branching`, routed by task from the skill table, so an agent merging or working in a worktree loads one short skill. (b) sections in the lifecycle skill, which is already long and is loaded for status and plans | (a) | (a), 2026-10-28 |
| OR-Q3 | Keep `fnd:Version` as a deprecated alias for one release? | (a) no alias, since no adopter has pinned a tag, one breaking line in the release notes. (b) `owl:equivalentClass` for one release, which keeps old data valid and makes the two names rank together in every tool for a release | (a) | (a), 2026-10-28 |
| OR-Q4 | `ontology-architecture.md`: retire or regenerate? | (a) retire, with its surviving claims moved to the layer READMEs and the catalogue, and the site section updated. (b) regenerate from the catalogue and the READMEs by a tool, which is a new tool to keep | (a) | (a), 2026-10-28 |
| OR-Q5 | The seven empty shape files | (a) fill each from its README's stated rules, Foundation's first, which lets Vocabulary stop restating them. (b) delete Party's and Quantification's until their rules are realised, marking each README claim Unchecked because, and fill Foundation's | (b) | (b), 2026-10-28 |
| OR-Q6 | A pin to an owned component of a versioned root | (a) allow it, the pin naming the root's version and the component's IRI, the warning becoming a check that the root is versioned. (b) lift the classes that other aggregates cite, the account definition among them, to roots of their own aggregates | (a) | (a), 2026-10-28 |
| OR-Q7 | How is "meaning-bearing" marked and enforced? | (a) an annotation property in Foundation on the object property, read by a Foundation SHACL rule over data and by the Persistence compiler over configuration, refusing a by-identity edge to an unowned, unversioned target. (b) Persistence only, a profile-level list of such edges, so the ontology says nothing and the check runs only where a family is compiled. (c) ontology only, a shape per layer, so configuration can still compile it away | (a) | (a), 2026-10-28 |
| OR-Q8 | `voc:SchemeBinding` | (a) versioned, chained by `fnd:supersededBy`, resolution gaining a transaction-time axis per ADR-A108, the resolver tool and both binding shapes walking versions. (b) immutable, with its ending a fact of its own, a closure record naming the binding and the instant, which the resolver reads as `validTo`. A correction is a closure and a new binding. One class, one property, one resolver change. (c) leave it, relying on transaction time (ADR-A67, Proposed) and receipt delta graphs in every deployment | (b) | (b), 2026-10-28 |
| OR-Q9 | Canonicalisation | (a) RDFC-1.0 and SHA-256 everywhere, Persistence's digest vocabulary adopted, each layer naming its content triples. (b) per layer, each stating its own, with a mapping table | (a) | (a), 2026-10-28 |
| OR-Q10 | Behaviour's allowance classes | (a) deprecate now with a shape warning, as `AcceptanceRecord` was. (b) wait for LG-3 and deprecate when Behaviour imports Ledger | (a) | (a), 2026-10-28 |
| OR-Q11 | Capacity's release state | (a) withdraw from the release register until its source ontology exists and its examples pass. (b) mark pre-release in the register and the README | (a) | (a), 2026-10-28 |
| OR-Q12 | Where `Law`, `OperationalProfile` and `Undetermined` live | (a) a law register and discharge vocabulary in Foundation, with each layer's laws as individuals, `OperationalProfile` in Foundation as the versioned conformance profile, and `Undetermined` as Foundation's one three-valued individual. (b) Quantification owns laws and the three-valued vocabulary, since it defines three-valued comparison, and Behaviour and Eligibility import it | open | deferred to the end of the unit, 2026-10-28 |
| OR-Q13 | The person and the handle in `dct:creator` | (a) keep, since the handle is the project's own remote. (b) replace with the project's name | maintainer's | (b) `https://github.com/nebularis`, 2026-10-28 |
| OR-Q14 | An estimated `validFrom` | (a) an `fnd:estimated` marker on the scope. (b) `validFrom` optional with a stated default, the earliest evidence. (c) both | (a) | (a), 2026-10-28 |
| OR-Q15 | The epoch guard baseline is `dal:RowLevelGuardOnly`, which §5.6.8 discourages and the README keeps so that no existing deployment's generated operations change | (a) make `dal:DatasetLevelGuard` the baseline now, since no deployment exists, and drop the compatibility sentence and the baseline warning. (b) keep it, the warning being the witness of the baseline | (a) | (a) chosen, then found blocked: the no-receipt builder families have no dataset-guard variant, so the baseline stays and TD-118 records the work (OR-10) |
| OR-Q16 | MORK's http namespace root | (a) rename with the others in OR-6, one breaking line. (b) keep, since MORK is standalone and its root is the project's own domain | (b) | (b), 2026-10-28 |

## Index misses from this plan

| Question | Best answer | What would have carried it |
|---|---|---|
| a versioned thing whose meaning depends on parts edited in place | MEC-01 at 0.71 | a "Does not cover" column on MEC-01 naming parts and references, and OR-7's annotation once it exists |
| renaming a Foundation class and re-releasing every layer | TD-20 at 0.70 | a `bearsOn` edge from TD-20 to ADR-A113 and ADR-A129 |
| content-addressed parts | PAT-46 at 0.74, right | nothing |
| an aggregate owns its components, nested aggregates | MEC-58 and ADR-A122 at 0.77, right | nothing. The one-owner rule answered the nesting question outright |
