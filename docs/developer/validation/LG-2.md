<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ledger LG-2, the runtime document

**Unit:** `ledger` ([plan](../plans/ledger.md)). Its status record is created with LG-0.
**Machine:** as the maintainer assigns. **Branch:** `ledger/lg-2-runtime`. Commits are the maintainer's.
**Plan and test cases:** [Ledger plan](../plans/ledger.md) (LG-2 in detail)
**Decisions:** ADR-A131 decisions 4 and 6, LG-Q3 to LG-Q8

## Invariant

Postings, balance records and merge records are derived artefacts with natural keys, and their recorded values satisfy Ledger's laws (the fold, availability along the path, the credit ceiling, conservation after rounding), checked as shapes over the records (ADR-A131).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ledger/spec/ledger-runtime.ttl`, the runtime shapes, persistence's record families, the triple-store discovery entry for `owl:rational`, `tools/test_ledger.py`.

## Deliberate non-coverage

Computing postings and the two phases' order independence (B4a, CCS C12). Behaviour's migration (LG-3). Allocation (LG-4). Throughput (LG-5).

## Handoff

Built on machine S, 2026-11-08, after LG-7 and on the same branch, `pvs-fml-foo`, rather than `ledger/lg-2-runtime`, under the maintainer's go-ahead to build LG-7 and then LG-2 and commit locally only. Nothing was pushed.

**What was built.**

- **The runtime document.** `ontology/ledger/README.md` section 6 gains `output-file` regions that extract `spec/ledger-runtime.ttl`, importing the configuration document at one version: `ldg:Account`, `ldg:Pass`, `ldg:Posting`, `ldg:BalanceRecord`, `ldg:MergeRecord`, `ldg:Grant` and `ldg:Checkpoint`, with their properties and restrictions. An account instance is a node identified by definition, owner, key and period (LF-Q19). A posting carries an effective position, a recorded position and a micro-position, and names its pass, which carries the position it was recorded at (LF-Q11, STD-294). A draw is posted at the drawn account only (LF-Q18).
- **PDD-15.** `ldg:periodRecurrence` and `ldg:closingRecurrence` on the definition, at most one each. `ldg:resetRecurrence` is deprecated.
- **TD-98.** `ldg:keyDimension`'s range is `skos:ConceptScheme` or `qnt:ValueSpace`.
- **The runtime laws.** Sixteen SHACL-SPARQL shapes in section 7.3, extracted to `shapes/runtime.ttl`, with a table naming the LG-7 theorem each checks on one dataset.
- **The examples.** The five accepted examples and `refusal-overdraw.ttl` now carry account instances, passes and the new positions. `licence-seats.ttl` is rewritten under PDD-15, one account per site and licence year with no reset credit, which pays TD-97. The insurance example's reinstatement is also debited at the pool (LG-Q10).
- **The probe** (LG-Q6), recorded as TSD-70 in the triple-stores domain and in the discovery page, with LG2-01 running it on each engine.
- **Tests.** `tools/test_ledger.py` loads the runtime document and shapes, and gains LG2-01, LG2-03 to LG2-10 and ten more mutations, one per remaining law.

**What was run, in full.**

- `mise exec -- python -m pytest tools/test_ledger.py`: 35 passed in 77 s. LG2-10's generated pass, a root, 4,999 sections and 5,000 leaves with 5,000 postings and 10,000 balance records, validates in 56.6 s. LG1-09's cycle test takes 16.8 s with the runtime shapes loaded.
- `check:site-sections`, `check:tutorial-snippets`, `check:published-decisions`, `check:identifiers`, `check:deny-terms`, `check:catalogue`, `check:owl-profile`, `check:formal-freshness`, `check:import-guard`, `check:ontology-releases`, `check:vyvid-binding` and `check:portability`: exit 0.
- `check:ontology-catalog`: exit 0 after `tools/ontology_catalog.py write` added the runtime document's two entries.
- `check:ontology-versioning -- --base-ref main`: exit 1, `UNBUMPED`, as it should be, since versions are bumped at release and not mid-branch. The release notes are under **Unreleased**, each classed. The same run asks for the tag `persistence-store-v0.19.0`, which this slice did not cause.

| Row | Result |
|---|---|
| LG2-01 | pass on rdflib 7.6.0, Oxigraph 0.5.13 and Jena ARQ 5.1.0. All three keep the literal, and none compares it by value |
| LG2-02 | pass, the five accepted examples conform with their records |
| LG2-03 to LG2-06, LG2-08, LG2-09 | pass, each mutation fails the shape the row names |
| LG2-07 | pass, `refusal-overdraw.ttl` conforms with no posting, no grant and a refusal reason |
| LG2-10 | pass, 56.6 s |
| LG2-11 | pass, extraction `--check` and `check:published-decisions` |

**Deviations from the brief, with reasons.**

- **The building mark came late.** It was committed after the README's first runtime edits rather than before them.
- **An exact share is two integers**, `ldg:proportionNumerator` and `ldg:proportionDenominator`, as LG-Q6 allows where stores do not handle `owl:rational`. The codec gains no rational form.
- **No running balance on a posting** (LF-Q17). Under LF-Q18's post-once rule a posting's running balance is ambiguous for an account with descendants, so the record stays a balance record per account per pass, which LG-Q5 asked for, and LG-Q9 is raised in the plan.
- **The insurance example's reinstatement now debits the pool.** A credit rolls up under post-once, so restoring the aggregate also restored the pool, and the example's own reading, that a reinstatement does not raise total capacity, needed a debit at the pool. That is a posting at an ancestor, which LF-Q18 (c) allows only for purposes, so LG-Q10 is raised.
- **`ldg:resetRecurrence` is deprecated, not renamed.** PDD-15's row says renamed, and a new term beside a deprecated one keeps data that states the old one valid until a breaking release.
- **The shapes target the class, not each record.** A shape per record ran one query per record, which took over a minute and a half for 250 postings on rdflib, so each shape reads its class's instances in one query, and a result's focus node is the class with the record as its value.
- **The fold applies the ceiling once, to the total**, which is exact unless a credit was cut by the ceiling before a later debit in the same subtree. Section 13 records it.
- **Persistence's record families are not declared.** Section 13 records them as open, since the storage shape they take is what LG-6 measures.
- **`test_literate_extraction_matches_committed_turtle` was failing on this branch since LG-7**, because LG-7 put an `isabelle-spec` block in the README and the test did not pass `--proofs-root`. It passes it now.

**Deliberate non-coverage, beyond the brief's.** The double count of a draw naming a purpose where the purpose-counting account shares an ancestor with the drawn account (section 13). A draw whose effective position cannot be binned, which PDD-15 makes Undetermined, is the evaluator's to compute and has no shape. Speculative passes in a droppable graph (LF-Q21) need nothing in the T-Box.

**Also changed.** `docs/_includes/tutorial/10-drawing-down.md` quotes the converted revolving-facility records. The technical debt register loses TD-97 and TD-98. The plan's questions gain LG-Q9 and LG-Q10. The triple-stores domain's TSD-70 is committed on a local branch of that domain, `tsd-70-owl-rational`, not pushed.

**What to check first.** The fold and availability shapes against LG-7's LC2 and LD2, the insurance example's position 4, and LG-Q9 and LG-Q10.

## Results

Written at verification.
