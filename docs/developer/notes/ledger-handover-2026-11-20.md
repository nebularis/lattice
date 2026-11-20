<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Handover to the ledger's session, 2026-11-20

For the session that owns the ledger on `docs/placement-vehicles-structure`. Machine S's first bundle holds the ledger's rework. It was run again on macOS and merged into `spi/multi-store-architecture`. Its checks pass. Its content has not been reviewed, and that review is yours.

## 1. What is where

| | |
|---|---|
| The rework | LG-11, LG-25, LG-26, LG-27, LG-28 and LG-12, built on machine S in that order, each with a Validation Pack in `docs/developer/validation/` |
| Where to read it | `spi/multi-store-architecture`, which holds the merge of `spi/worktree-s` at `07109dee`. The bundle's own tree is the worktree `lattice-wt/worktree-s` |
| Its rows | `built 2026-11-19` on the ledger's board. They were not moved here |
| Your branch | `docs/placement-vehicles-structure` at `5f537ead` when this was written, one commit past the tip merged here, with LG-3's sketch and BHL-Q1 to BHL-Q7 |

## 2. What ran on macOS, and what did not

Run on the bundle's tree, 2026-11-20.

| Check | Result |
|---|---|
| `mise run check:proofs` | `Ledger` 73 claims passed, `LatticeShared` 10, `Eligibility` 33. Every gate passes and every assumption audit is clean |
| `mise exec -- python -m pytest tools/test_ledger.py -q` | 154 passed, the count LG-12's pack gives |
| `benchmark/ledger-posting-cost/test_shape_scale.py` | 2 passed in 45 s |
| tutorial snippets and writing rules | 28 passed |
| `mise run check:owl-profile` | 5 passed |
| `mise run check:ontology-catalog` with the reasoner installed | 1439 passed, none skipped |
| `mise run check:full-sweep -- --base-ref origin/main` | 16 of 17. Versioning fails, as the branch defers it |

- **The reasoner's tests had not seen the rework before.** Machine S has no reasoning testkit, so each pack reports 79 skipped. They pass here.
- **Not run here.** The ledger's benchmarks other than the shape-scale test, and the verification rig's cases. No timing in a pack was measured again.
- **Not read.** The ledger README's changes, the shapes, the examples, the proofs' statements and the packs' arguments. A passing check says the artefacts agree with one another, not that the model is the one we decided.

## 3. What the review has to settle

- **Each pack's questions for the maintainer,** which the ledger's status record lists in its next action: the order of one pass's postings on one path and a credit with no kind (LG-25), the five reason names, the rule's name and the addendum to ADR-A131 proposed for the request (LG-26), where the refusal of a ceiling above a stated amount lives and the name `ldg:passRevision` (LG-27), the pin's name, `ldg:residualAccount` as meaning-bearing, the editions of the purpose and key schemes and a definition's new version under postings (LG-28), and whether a draw's unit is read from what it cites (LG-12).
- **WPG-Q2 was open when LG-28 was built.** It asks where a declared ceiling lives, with a leaning to the account definition, which LG-28 made a versioned thing. Say whether LG-28 as built leaves room for each answer, or whether the answer changes it.
- **LG-Q45 and LG-Q46 against LG-27.** The pass's revision and the pass's name were decided on 2026-11-19 while machine S was building. Check LG-27 states them as the second addendum of that day does.
- **Three debts the packs propose as closed,** TD-102, TD-158 and TD-159. One of the two heavy shapes TD-159 names went with the balance record in LG-25. Close a row only where its cause is gone.
- **Whether each row moves to verified** is the maintainer's word, on your review.

## 4. Merging

- **Merge `spi/multi-store-architecture` into your branch, never the reverse here.** A trial merge of your tip into this branch conflicts in two files, `docs/developer/ROADMAP.md` and `docs/developer/status/ledger.md`. The ledger's record is joined by the furthest row, then the later day, and its hand-written head is yours. The roadmap's generated regions are regenerated, and its ledger paragraphs are yours.
- **You wrote nothing under `ontology/ledger/` or its proofs while machine S held the rework,** as agreed, so the layer itself should merge clean. If it does not, stop and tell the maintainer.
- **Numbers taken here since your tip.** TD-165 to TD-174, PDD-24, MSA-F10 to MSA-F16, MSA-I14 and the unit `component-administration` with ADM-0 to ADM-2. Your branch's last debt was TD-164 and its last pending decision PDD-23. A row you add before merging takes the next free number after these, or is renumbered at the merge, the earlier commit keeping the number.
- **Then tell the maintainer,** so this branch takes your merge and machine S takes it from here. Machine S cannot push, and starts no ledger slice before your review reports.

## 5. What is owed at the merge into `main`

- **Two version bumps.** The substrate release is still 0.22.0 with six changed members, the ledger's among them. Persistence, a standalone module, is still 0.23.0 after a change to its specification from the multi-store unit. `mise run check:ontology-versioning -- --base-ref main` names both and the command for each.
- **The two units reach `main` in one merge,** as agreed on 2026-11-19.

## 6. What bears on the ledger from the multi-store side

- **MSA-I14, urgent.** A design in which no write leaves a state that some sequence of whole commands does not give. Its leading hypothesis is the rule the ledger already has from LG-Q45, a request that applies whole or is refused and made again. MSA-I8, the first ledger family behind the port, waits on it.
- **PDD-24 and MSA-F16.** The maintainer leans to RDFC-1.0 for every digest of RDF content. If the ledger stores or plans a digest, a pass's receipt for example, it takes that form.
- **TD-174.** The PostgreSQL fixture stays on 16.15 until machine S is decommissioned, then moves to 18 with compose. MSA-I7's ledger benchmark arm is measured on 16 and run again after the move.
