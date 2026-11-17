<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Rig agent brief, 2026-11-16: competency questions on dates and on the ledger's decided design

**For:** an agent new to this work, running under Copilot in VS Code. **Written on** `docs/placement-vehicles-structure` at the maintainer's request. **Slice:** VR-8 of the unit `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)), briefed 2026-11-16. The maintainer creates your branch from the commit that holds this brief.

You add competency questions to the verification rig's projection P1 and ask them of the synthetic mini-rig. Nothing else. No rig other than the mini-rig is read in this slice, and no layer gains a term.

## 1. Before anything else

Copilot loads `.github/copilot-instructions.md`, which is generated from [AGENTS.md](../../../AGENTS.md). Read AGENTS.md itself once, in full. Its contract governs this slice, and four parts of it catch a new agent out.

- **The index comes first.** Section 2 below.
- **Mark before you touch.** Your first edit sets VR-8's row on the board of [status/v-rig.md](../status/v-rig.md) to `building <day>`, adds a history line, runs `mise run build:work` and is committed alone. Before that, run `mise run work:here -- --role build --model <your model>`.
- **Design decisions are the maintainer's.** Declaring a term, changing a layer, or changing the mini-rig's content is a decision. Present the options and wait.
- **`mise` is the only entry point.** Every command is `mise run <task>` or `mise exec -- <command>`, never a bare `python` or `pytest`. A new worktree needs `mise run bootstrap` once, then `mise run bootstrap:v-rig`.

Copilot does not load skills by itself. A skill is a file, `.claude/skills/<name>/SKILL.md`, and you open it when its task comes up.

| Skill | Open it when |
|---|---|
| `lattice-lifecycle` | first, before the mark. It has the board, the Validation Pack, the handoff and the release rules |
| `lattice-query-writing` | before writing any `SELECT` |
| `lattice-probing` | before relying on what an engine does with a query |
| `lattice-ontology-modelling` and `lattice-architecture` | when judging which layer a missing term would belong to |
| `lattice-testing` | when changing the tool's tests |
| `lattice-publication-hygiene` | before every commit |
| `lattice-mise`, `lattice-branching` | when a task, a hook or a worktree misbehaves |

AGENTS.md's section on private overlays applies to you as it is written there.

## 2. Ask the index, every time

The repository has a knowledge index over its decisions, mechanisms, standards, store findings, questions and declared ontology terms. It is more current than anything you remember and much cheaper than searching files. **Ask it before every decision and before every search with grep or the editor.** A weak answer is itself a result to report.

```bash
mise run graph:ask -- find <the problem in your own words>
mise run graph:ask -- read <ID>
mise run graph:ask -- find <what the term means> --kind term
mise run graph:ask -- exists <word>
```

- Ask every modelling question twice, once with no kind and once with `--kind term`. Terms are searched only when asked for.
- Read the flags on each row and the line under it. AGENTS.md's section "Asking the knowledge index" says what each flag means.
- An empty answer never proves that nothing exists. Fall back to the documents, and where they hold an answer the index did not, record it at once with `mise run graph:ask -- gap "<what you found>" <ID> <path:line>`.
- At the handoff, report the output of `mise run graph:ask -- misses --near` and say which entry or column would have carried each miss.

For this slice the index decides, for every candidate question, whether a term exists to ask it with. Do not take the tables below on trust. They were drawn up on 2026-11-16 by listing the Ledger layer's declared terms, and each row is to be confirmed.

## 3. Background reading, in order

1. The [rig's plan](../plans/v-rig.md), for what a rig is, the four projections and the eleven principles. Principles 1, 2, 9 and 10 are the ones a mistake here would break.
2. The [rig's status record](../status/v-rig.md) and the Validation Packs [VR-3](../validation/VR-3.md) and [VR-4](../validation/VR-4.md), for the mapping scheme and how P1 is checked.
3. The module's [README](../../../ontology/v-rig/README.md), the tool's [README](../../../tools/v_rig/README.md) and the [competency queries' README](../../../ontology/v-rig/projection/competency/README.md), for the question format.
4. The [sketch on dates, periods and reporting](../sketches/v-rig-dates-periods-and-reporting.md), which is part A's source.
5. [ADR-A131](../../architecture/decisions/ADR-A131-ledger-layer.md), its decisions 3, 4 and 6 and its four addenda from 2026-11-09 onward, which are part B's source. `mise run graph:ask -- read ADR-A131` lists what links to it, and MEC-107 to MEC-112 state the mechanisms one at a time.
6. The Ledger layer's [README](../../../ontology/ledger/README.md), for what its terms mean today. It is behind the addenda, which is the point of part B.

## 4. Part A, the five questions that can be asked today

The sketch's section 2.1 names five questions, four of them with a draft query. Add them to their files under `ontology/v-rig/projection/competency/`.

| File | Name | Note |
|---|---|---|
| `ledger.rq` | `closing` | confirm `ldg:closingRecurrence` with the index |
| `ledger.rq` | `period` | confirm `ldg:periodRecurrence`, which states a recurring period only |
| `instrument.rq` | `amendment-effect` | confirm the path to the time an effect holds from |
| `instrument.rq` | `amendment-source` | confirm `ins:statedIn` |
| `foundation.rq` | `recorded-and-effective` | has no draft. Read Foundation's shapes first, since the two properties have different domains |

Then run the tool on the mini-rig and record, for each, the row count or the finding. The sketch's section 2.2 lists eight more questions with no term. Leave them as they are.

## 5. Part B, questions for the ledger's decided design

The addenda to ADR-A131 decided what an account declares and what a request carries. Most of it has no term yet, because the layer's vocabulary is reworked in a later slice of the ledger unit. Each question below is therefore one of two things, a query where a term exists and a recorded gap where none does. The gaps are the result that matters, since they are the requirements that rework has to meet.

**Changed on 2026-11-17, before the slice started.** What an account declares for a merge is moving from the account definition to a merge policy node, in slice LG-24 of the ledger unit, and its terms are decided or being decided as LG-Q30 to LG-Q36 of the [ledger plan](../plans/ledger.md). So do part A now, and in part B take only the rows whose terms do not move: `ceiling` and `purposes` in 5.1, and `whole-or-nothing`, `held-rank`, `restoring-kinds` and `floor` in 5.2. Leave `merge-rule`, `residual-rule`, `rounding`, `order-criterion`, `tie-rule`, `refuse-or-cut`, `order-check`, `residual-allowed`, `mixed-position` and `rounding-treatment` until LG-24 is built, and ask the maintainer then. One is already answered: the rule for requests of one rank is what `ldg:mergeRule` states, so `tie-rule` is no gap.

### 5.1 A term appears to exist

| Name | Question | Term to confirm |
|---|---|---|
| `merge-rule` | Which account definitions state the rule that merges requests competing for what is available? | `ldg:mergeRule` |
| `residual-rule` | Which account definitions state how a unit left after a division is placed? | `ldg:residualAllocation` |
| `rounding` | Which account definitions state how a share is rounded? | `ldg:roundingMethod` |
| `ceiling` | Which account definitions state a ceiling that a credit may not raise the balance above? | `ldg:creditCeiling` |
| `purposes` | Which account definitions state the purposes they count? | `ldg:countsPurpose` |

For each, check that the term's published definition still says what the addenda decided. Where the definition and an addendum disagree, that is a finding for the ledger unit and never something to correct here.

### 5.2 No term was found

| Name | Question | Decided in |
|---|---|---|
| `order-criterion` | Which account definitions state the criterion that orders requests, for example the order of notification or of size? | second addendum of 2026-11-16, MEC-108 |
| `tie-rule` | Which account definitions state the rule for requests of one rank? | second addendum of 2026-11-16, MEC-110 |
| `refuse-or-cut` | Which account definitions state whether requests beyond what is available are refused whole or cut to it? | second addendum of 2026-11-16, STD-336 |
| `order-check` | Which account definitions state that the order is checked before any rule runs? | second addendum of 2026-11-09 |
| `residual-allowed` | Which account definitions state that a rule may leave a residual, and name the account that takes it? | second addendum of 2026-11-16, MEC-109 |
| `whole-or-nothing` | Which requests are stated to be of no use in part? | second addendum of 2026-11-16, MEC-109 |
| `mixed-position` | Which account definitions state that a position of more than one purpose is refused? | second addendum of 2026-11-16, MEC-112 |
| `held-rank` | Which accounts under a fund hold an amount for one rank of requests? | second addendum of 2026-11-16, MEC-110 |
| `restoring-kinds` | Which account definitions state the kinds of credit that restore them? | first addendum of 2026-11-16 |
| `rounding-treatment` | Which account definitions state how a unit over or a unit short after rounding to the nearest is treated? | second addenda of 2026-11-09 and 2026-11-16 |
| `floor` | Which agreements state a floor on a share and what follows where a share falls below it? | second addendum of 2026-11-16, MEC-111. The floor is decided before the ledger, so its home is not Ledger |

`tie-rule` may turn out to be what `ldg:mergeRule` already states, and `rounding-treatment` may have a value in the rounding vocabulary. Check both before recording them as gaps.

For each row the index confirms as a gap, record the question, what the index returned instead, and the layer you judge the term would belong to with one sentence of reason. Do not write a query against a term that does not exist, and do not declare one.

### 5.3 Left out on purpose

Questions about runtime records, such as the kind and the amount applied on a credit, the cuts, or the rank on a request, wait for the ledger's runtime document to be reworked. The writer of a ledger, ADR-A131's third addendum of 2026-11-16, is a rule for a runtime and nothing a document states.

## 6. Rules for the question files

- A question is `# question <name>: <the question in words>` and one `SELECT`, in the file of the layer it asks. The file's `PREFIX` lines apply to every query in it.
- The words are about the layer and name no domain beyond the layer's own. The files are published with the module, so a question's text carries no slice, no register entry and no decision number.
- Before a query is written, ask `mise run graph:ask -- find <what the query does> --kind standard --activity query-writing` and read what answers. Every query here runs over one small projected graph, so say that in the Validation Pack as its cost.
- The question files are versioned by `ontology/v-rig/projection/.version`. Make no version bump on the branch. Add a release note under `- **Unreleased**.` in section 12 of the module's README, in words a reader of the module needs, and expect `mise run check:ontology-versioning -- --base-ref main` to report the projection as unbumped until the merge.

## 7. What you do not touch

- `ontology/ledger/` and every other layer. Another agent is rewriting the Ledger README's formal statement, and the vocabulary's rework is a slice of the ledger unit.
- `tools/proofs/`, `spikes/` and `benchmark/`.
- Projections P2 and P3, `p2.py` and `p3.py`. P2 copies a ledger theory that is being replaced, and pointing it at the new one waits for the ledger's LG-9.
- The mini-rig's documents, programme and events. Whether the mini-rig should state more, so that a new question has an answer, is a question for the maintainer. Raise it as VR-Q12 in the plan, with the options, if the results make it worth asking.
- Anything under `.local/`. The tool writes its outputs there, and none of it is ever committed.

## 8. Commands, and what a pass looks like

AGENTS.md's default is to write and hand off without running checks. This slice's result is a run, so ask the maintainer at the start whether you run these yourself. Either way the handoff lists each command with its real result, or says it was not run.

```bash
mise run check:v-rig
```

A pass is every test passing. `tools/v_rig/tests/test_p1_checks.py` holds the questions the mini-rig answers and the ones it does not, so it gains an expectation for each new name. Adding expectations is not a weakening. Loosening an existing one is, and needs the maintainer.

```bash
mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl
```

A pass is a run that prints its rig digest and writes `p1/competency.json` with a count for every question, the new names among them, and `report.md` with an empty-query finding for each that returned nothing. Read the whole output. Every figure in your handoff comes from output you read in full.

```bash
mise run check:identifiers
```

A pass says no identifier is unresolved.

The commit hook runs the quick checks. Never bypass it. A commit that touches `ontology/v-rig/` carries a `Placement:` trailer, `T0` for these files, and the trailers [GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md) requires. Commit, push, merge and tag only at the maintainer's word.

## 9. What you hand back

1. The questions added, in their files, with the tests that hold them.
2. A Validation Pack, `docs/developer/validation/VR-8.md`, in the shape of [VR-4](../validation/VR-4.md)'s, with the table of every question of sections 4 and 5: asked or a gap, the row count on the mini-rig, and for each gap what the index returned and the layer the term would belong to.
3. In that pack, a list headed as requirements for the ledger's vocabulary, one line a confirmed gap, and a second list of any definition that disagrees with an addendum. The ledger unit picks both up from there.
4. The status record's history line and VR-8's row at `built <day>`, with `mise run build:work` run, and the roadmap attended to as AGENTS.md says.
5. The index report of section 2.

End the handoff with the commands to run and what a pass looks like, as section 8 does.
