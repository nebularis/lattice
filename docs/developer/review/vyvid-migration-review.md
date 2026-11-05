<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review request: vyvid-migration, the merge into `main`

**Unit:** [vyvid-migration](../plans/vyvid-migration.md), status [vyvid-migration](../status/vyvid-migration.md), the Validation Packs [VM-1](../validation/VM-1.md) to [VM-6](../validation/VM-6.md).

## Scope

LATTICE's knowledge index, work board and agent skills are Вивід's ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md), Accepted), pinned at v0.2.8 in `mise.toml` and bound by `vyvid.toml` at the root. The branch holds 30 commits on `main` as of 2026-11-05, 122 files, about 4,800 lines added and 12,100 removed, the old index and board tooling and the ten hand-written skills among them. Every slice VM-0 to VM-6 is built, and VM-1 and VM-3 to VM-6 verified at their gates by the maintainer. The addenda of 2026-11-05 on ADR-A117 and ADR-A134 are Accepted.

## What ran before this request

- `mise run check` at v0.2.8, on the tree of the last commit, written unfiltered to a file and read in full: exit 0 from `mise` in 447 s with the node suites running beside it, every task passing, its 3,447 lines compared line by line with the log of the check after VM-6, which was compared the same way back to the VM-3 log the agent read whole, and differing only in one more identifier, 2096 in 859 files, the order of two parallel suites' progress lines, and timings.
- The suites `check` leaves out, each run to a file and read in full: `check:conformance`, which is persistence on rdflib, Oxigraph and Jena at 5686 passed and 16 skipped, the MORK compilers on rdflib and on Jena at 195 passed each, Eligibility on rdflib and on Jena at 81 passed each, and the engine probes at 55 passed with 1160 subtests. `check:authoring`, the add-in and the authoring domain, 65 and 21 passed and 15 end-to-end. `check:testing-jena` 14 passed, `check:testing-mem-check` 6 passed, `check:sparql-testkit` and `check:reasoning-testkit` built and passed under `-q`. `test:frontend`, the three frontend suites and the studio's browser journeys, 20, 2 and 3 passed and 15 end-to-end, `test:authoring-addin` 21, 65 and 15 passed, and `test:config-studio` 20 passed. Every one exited 0.
- Not run, and why: the benchmarks under `check:ledger-*`, `check:persistence-*-cost`, `check:persistence-membership`, `check:persistence-replace-forms*`, `check:persistence-store-probes`, `check:mork-rdf-run-cost`, `check:mork-candidate-ranking` and `check:sparql-constraint-query-cost` measure and fail on a wrong result only, run on demand (ADR-A124), and the branch touched nothing they measure. `check:proofs`, `check:formal-smoke` and `check:formal-network` build Isabelle sessions or probe tool sources, the branch touched no proof, and an Isabelle build is run one at a time on this machine by agreement. `check:full-sweep` and `check:literate-migration` are for an ontology change, and the branch made none. `check:minting-tables` regenerates the Unicode tables from the UCD, untouched here.
- `mise exec -- python tools/ontology_version_check.py --base-ref main`: 50 documents, no unbumped change. The task form AGENTS.md names, `mise run check:ontology-versioning -- --base-ref main`, hands the argument to the wrong command and exits 2, recorded as TD-147.
- `mise run hooks:merge`, the merge gate against `main`: 102 files, 11 checks, every one `ok`, with a wrapping warning on two paragraphs the renames had touched, joined in the commit that carries this request, and rerun clean after it.
- `main` has not moved since the branch merged it at 9e5b5798, so nothing is merged in first. `git log HEAD..main` is empty.

## ROADMAP.md

Refreshed: the four generated regions by `mise run build:roadmap -- --fetch`, and section 10, the maintainer's queue, whose first item is this merge. Checked and left: sections 2 and 8, the dependency and critical-path diagrams, which name no tooling this unit replaced, section 12, whose observation on the index tooling never being LATTICE's stands, and sections 3, 4 and 6, which this unit does not touch.

## The merge, step by step

1. In `~/work/lattice`, on `main`, with a clean tree: `git fetch origin-ssh` and `git merge --no-ff vyvid-migration` (or `origin-ssh/vyvid-migration` once pushed). The pre-merge-commit hook runs the merge checks. A pass prints every check `ok`.
2. If the hook refuses on a register row numbered twice, first in wins (skill `lattice-branching`), but no branch has merged into `main` since this one left it, so none is expected.
3. After the merge, in `~/work/lattice`:

```bash
vyd trust
```

The merged `vyvid.toml` is new to that checkout, and an untrusted file gives knowledge alone, no extractor, no skills check and no board writes. `vyd trust` prints the two things the file declares, the extractor command and the skills folder, and asks for `yes`.

```bash
mise run bootstrap
```

It installs the hooks and, where `vyd` does not already report 0.2.8, the pinned tool. On this machine `vyd` is an editable install of the Вивід checkout and reports 0.2.8 already.

```bash
mise run build:knowledge
mise run check:knowledge
mise run check:identifiers
mise run check:hooks
vyd check skills
mise run check:agent-guidance
```

A pass is a build ending `knowledge index built at <path>` with the extractor's finding line and no note but the claim-length, whole-file and moved-entries notes, 38 passed, an identifier check with 0 unresolved, 48 passed, `skills check passed: 15 composed, 0 problem(s)`, and `agent guidance: 0 problem(s)` with 9 passed. `mise run work:board` then answers from `vyd`.

4. The post-merge hook rebuilds the index and regenerates INDEX.md's region and ROADMAP.md's regions on `main`, left in the tree for you to commit. Commit them.
5. Push `main` and delete the branch when you are ready. Nothing on the branch is pushed by the agent.

## What the paused branches do when work resumes

Each merges `main` in, never rebasing, then in that checkout runs `vyd trust`, `mise run bootstrap`, `mise run work:normalise -- --apply`, `mise run work:rename -- --apply` and `mise run build:work`, each idempotent, so its boards and INDEX.md's region agree with `main`, then `mise run build:knowledge`. A branch that edited one of the ten old skills under `.claude/skills/` conflicts with their deletion, and the edit goes into the source under `.vyvid/` or the domain, with `vyd install --project` composing the skill again. A branch that added a row to the old facet register or the triple-store record puts the value or the finding in Вивід's scheme or domain through its side. A branch that cited `lattice-toolchain` or `lattice-triple-stores` renames the citation by what its sentence is about, as VM-5 did. Register rows numbered on the branch from before the merge may collide with none here, since this unit added STD-319, PRI-79, TD-146 and TD-147 only.

## Open questions

None. The maintainer's decision is the merge itself.
