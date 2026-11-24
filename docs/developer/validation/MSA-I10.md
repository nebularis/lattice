<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I10, two families in one mapping vocabulary

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I10
**Brief:** [machine S brief of 2026-11-19, the multi-store half](../notes/machine-s-brief-2026-11-19-multi-store.md), sections 4.5, 6 and 7, with the [handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md), sections 3 and 4, and the [ledger's note of 2026-11-23](../notes/ledger-to-multi-store-2026-11-23.md), sections 3, 5, 6 and 7.
**Decisions:** the plan's decision of 2026-11-17 on MSA-I1's threshold (a mapping written for a family and checked against it, closure declared by the mapping), the plan's decision of 2026-11-18 and ADR-A131's addendum of the same day (the owner's ledger is the unit that is consistent), PM-Q1 (a′) and PM-Q9 (iii) of the projection maintenance sketch.
**Machine:** machine S, Windows, Python 3.14.7 from the worktree's `.venv` through mise, rdflib 7.6.0. **Placement:** T0, public. Platform configuration and a spike, nothing domain-specific.
**Status:** built 2026-11-24, not verified.

## Invariant

One mapping vocabulary holds both families: R2RML, with twenty terms of the spike's own beside it for what R2RML cannot say about a table. Each family's relational place, the table, its key columns, and the logical resource and key part or the field each column holds, is emitted from its mapping and never from SQL. Every record the ledger's runtime vocabulary declares is mapped but the supersession, which is held until LG-Q58 is answered. On every example, the records encoded to rows by inverting the mapping decode by R2RML's rules to the same triples, and the rows keep every key and constraint of their places.

## What changed

- `docs/developer/notes/multi-store/MSA-I10-two-families-one-mapping.md`, the note. The two families and their places, the round trip, what R2RML and RML-Core can and cannot say, what a relational place needs beyond a graph place's role and name template, MSA-Q19 and MSA-Q20, ten findings and the verdict.
- `spikes/multi-store-mapping/`, a spike of its own beside the other investigations' spikes:
  - `ledger.r2rml.ttl`, the ledger's records in nine tables, and `promotion.r2rml.ttl`, the derived family of the promotion in Surface's example `saas-subscription-currency.ttl`, in one table. Each logical table carries its place in the spike's terms.
  - `place.ttl`, the twenty place terms, under an example.org namespace.
  - `mapping.py`, which reads both mappings, emits their places to `results/places.md`, and checks the vocabulary, the columns, the ledger's coverage and the round trip on every example. It interprets the subset of R2RML the mappings use and refuses the rest.
  - `test_mapping.py`, 15 tests.
  - `results/places.md`, generated.
  - `README.md`.
- Nothing under `ontology/`, `tools/persistence`, `tools/proofs/`, the port or the store SPI. No term was added to `ontology/persistence`. `mise.toml` is not touched, so the spike has no task and runs through `mise exec`.

## The falsifier, and whether it fired

**The sketch's falsifier for MSA-I10 is that the two need different vocabularies. It did not fire.** The ledger's mapping uses 32 mapping terms and the promotion's 21, and neither uses a term outside R2RML and the place terms. The terms only the ledger uses are the constraints, the foreign keys and derivation by path, and the one term only the promotion uses is a derived column equal to another. The test I10-T7 shows the check firing when one map gains a term of RML-Core.

The mapping holds besides. Every column of the ten tables holds a key part, a field or a derived value, every key column holds a key part, the ledger's coverage misses nothing and holds seven entries for LG-Q58, and every round trip returns the same triples with every constraint kept.

## Tests

| ID | Given, when, then | Level | Positive or negative | Pass criterion |
|---|---|---|---|---|
| I10-T1 | both mappings, the ledger's 24 examples and the promotion's | L1 | positive | `test_one_vocabulary_and_the_mapping_holds`: no term outside the vocabulary, the mapping holds, at least 10 examples with records, each the same triples with no lexical change, and every ledger table holds a row in some example |
| I10-T2 | the emitted places | L1 | positive | `test_every_column_holds_a_key_part_a_field_or_a_derived_value`, and every key column holds a key part |
| I10-T3 | the promotion's example | L1 | positive | `test_the_promotion_reads_both_ways`: 2 triples, 2 rows, the same triples back |
| I10-T4 | the supersession's example | L1 | positive | `test_the_supersession_is_held_and_named`: 7 triples held, the round trip holds, and the record and `ldg:supersedingVersion` are listed as held |
| I10-T5 | the ledger's mapping with the column of `ldg:runningBalance` removed | L1 | negative | `test_a_dropped_column_is_reported_missing`: coverage names it, and the encode finds a triple no column holds |
| I10-T6 | the posting's record column with its key part removed | L1 | negative | `test_a_key_column_with_no_key_part_is_reported` |
| I10-T7 | the promotion's object map typed `rml:UnsafeIRI` | L1 | negative | `test_a_term_outside_the_vocabulary_fires_the_falsifier`: one vocabulary is false, naming the term |
| I10-T8 | an `rr:sqlQuery` added to a logical table | L1 | negative | `test_an_unsupported_construct_is_refused`: the mapping is refused, never half read |
| I10-T9 | an R2RML template `{ledger}/pass/{key}` over a ledger IRI | L1 | negative | `test_an_r2rml_template_percent_encodes_an_iri_it_inserts`: the IRI is percent-encoded and is not the example's pass |
| I10-T10 | a posting's amount written `5.0` | L1 | positive | `test_a_non_canonical_decimal_comes_back_canonical`: the round trip holds by value and reports `5.0` became `5` |
| I10-T11 | one account moved to another owner and its ledger | L1 | negative | `test_a_record_derived_into_another_ledger_fails_a_foreign_key`: the posting's pass and the account's parent have no row in the derived ledger |
| I10-T12 | a posting's amount given twice | L1 | negative | `test_a_property_given_twice_is_not_functional` |
| I10-T13 | a posting's running balance removed | L1 | negative | `test_an_exactly_one_field_left_empty_fails` |
| I10-T14 | `results/places.md` as committed | L1 | positive | `test_the_committed_places_are_the_ones_the_mapping_emits` |
| I10-T15 | a second run | L1 | positive | `test_two_runs_emit_the_same_places` |

## One command

From the root of a bootstrapped checkout:

```bash
mise exec -- python -m pytest spikes/multi-store-mapping -q -p no:cacheprovider
```

A pass prints `15 passed`. The report itself is `mise exec -- python spikes/multi-store-mapping/mapping.py`, which ends `falsifier (the two need different vocabularies): did not fire` and `mapping holds (every column held, coverage, every round trip): yes`, exits 0 and writes `spikes/multi-store-mapping/results/places.md` unchanged. In PowerShell quote the separator, `mise exec '--' ...`.

## What was run, in full

Run on machine S on 2026-11-24, from the worktree, with `PYTHONUTF8=1` and the mirror's constraint files set. Another sub-agent ran TLC jobs and edited `tools/models/` and `mise.toml` in the same tree throughout.

- `mise run work:here`, run after the build and not before the first edit: one row, `you`, in the role `build`. The board's row for MSA-I10 was marked `building` on machine S by the coordinating session before the first edit, commit `1a1442f3`.
- `mise exec -- python spikes/multi-store-mapping/mapping.py`, the last run: `ledger: 32 mapping terms, 0 outside R2RML and the place terms`, `promotion: 21 mapping terms, 0 outside R2RML and the place terms`, `ledger places: 9 tables, 64 columns, 0 column problems`, `promotion places: 1 tables, 3 columns, 0 column problems`, `ledger coverage: 0 missing, 7 held for LG-Q58`, then the key parts against the persistence compiler's logical keys, `dal:Aggregate: holds record, root, value. Named by the logical keys and not held: none. Held and not named: record, value`, `dal:Receipt: holds seq, target. Named by the logical keys and not held: epoch`, and TransactionClaim and VersionRow with nothing apart. Then one line for each example. The 12 with records hold 72, 108, 133, 85, 47, 79, 24, 55, 75, 70, 38 and 39 triples, 825 together, in 201 rows, each `round trip holds` with `lexical changes 0`, with 18 `rdfs:comment` triples left out as annotations in 9 of them and `held 7` in `supersession-raised-amount.ttl`. The 12 others hold no records. `promotion saas-subscription-currency.ttl: 2 triples, 2 rows in 1 tables, round trip holds`. It ends `falsifier (the two need different vocabularies): did not fire` and `mapping holds (every column held, coverage, every round trip): yes`, exit 0.
- The first run printed the same verdicts and, on standard error, one rdflib warning for each annotation, `... does not look like a valid URI, trying to serialize this will break`, from showing a literal through the namespace manager. The report now shows a literal as itself, and the warning is gone.
- `mise exec -- python -m pytest spikes/multi-store-mapping -q -p no:cacheprovider`: `15 passed, 1 warning in 3.32s`, exit 0. The warning is `Unknown config option: cache_dir`, as in every run outside `tools/`.
- `mise exec -- python tools/writing_rules.py` on the note, this pack, the spike's README and `results/places.md`: `writing rules: 0 failure(s), 0 warning(s)`.
- `mise run check:identifiers`: `identifier check passed: 2438 identifiers mentioned in 1050 files, 0 unresolved, 0 defined twice. Reported, never failed: 2 written under another spelling, 167 removable no longer defined, 3 stale exceptions (--all lists them)`.
- `mise run check:catalogue`: thirteen `bypass scan, known` lines, none for this spike, then `repository catalogue: 22 module(s) and 19 tool package(s) agree with the tree. Bypass scan: 13 known file(s)`, exit 0.
- `mise run check:portability`: `portability: 0 problem(s)`, then its own tests, `25 passed in 11.31s`, exit 0.

## Deliberate non-coverage

- **The supersession.** Held until LG-Q58 is answered, as the handover says. The note's section 7 says where it lives under our leaning whatever LG-Q58 decides, and what of its mapping depends on it.
- **SQL.** No DDL is generated or run. The constraints are checked on the encoded rows in Python. MSA-I8 runs the ledger's family on PostgreSQL behind the port.
- **A conforming R2RML or RML processor.** The interpreter is the spike's own, for the subset the mappings use. No third-party engine was installed or run.
- **The graph places of the ledger's family.** Persistence declares no record families for the ledger yet, so no graph map names a period's unit or the ledger's own graph.
- **GQL, and a target in a language's own idiom (MSA-Q18).** Not written.
- **Index and projection contracts.** One promotion only, as the sketch's row asks. An index contract mints symbols under its naming policy, which is not maintained in the write yet (TD-138).
- **Hash agreement (MSA-Q12).** Only the canonical form of a decimal is shown, in I10-T10.
- **The pass's guard on the ledger's revision, and concurrency.** MSA-I8.

## Doc delta

- The note and the spike, above. This pack.
- No ontology README, no release note and no version. No status record, board, `INDEX.md`, `ROADMAP.md` or sketch section 8 edited.

## Index report

- **Asked.** `find mapping vocabulary relational layout graph place compiled profile` answered with MEC-74 and ADR-A78 at 0.77, ADR-A16 and MSA-Q19 at 0.75, and ADR-A13 and ADR-A123 at 0.74. MSA-Q19 and MEC-74 were read, MEC-74 being MORK, the repository's own mapping vocabulary compiled to RML, which question 4 raises. The first two attempts of this query failed with `RuntimeError: Corruption ... store/000024.sst: The system cannot find the file specified`, while the index was being rebuilt, and the third answered. `find landing place of a write access` answered weakly, VR-Q3 at 0.71 and ADR-A149 at 0.68, none about a place, since the studio's place is on a branch this one does not hold. `find R2RML RML mapping rows to graph and back` answered with WF-Q1 at 0.73 and MEC-74, CAP-69 and CAP-70 at 0.70, and named no R2RML entry. `find Surface promotion derived family target table` answered with ADR-A17 at 0.72 and ADR-A34 and STD-256 at 0.71, with MEC-71, a projection contract lowered to MORK, linked. `find the logical resource and key an access names in a compiled profile --kind term` answered with `dal:access` at 0.78 and `dal:ResourceKind` and `dal:ResourceAccess` at 0.75 and 0.74, each read in the persistence specification. `find the record that later versions of a definition are in force for an owner --kind term` answered with `ldg:Supersession` at 0.79 and `ldg:supersedingVersion` and `ldg:forOwner` at 0.72. `find where a supersession lives in a partitioned store` answered with MSA-Q20 at 0.75 and nothing else on the point.
- **Gaps recorded.** Against MSA-Q19 at `tools/persistence/src/persistence/contract.py:54`: the logical key of an Aggregate is its root alone, so a relational place of its records needs a record part and a value part the logical keys do not name. Against MSA-Q19 at `docs/developer/plans/multi-store-architecture.md:74`: the plan's decisions of 2026-11-18 use MSA-Q19, MSA-Q20 and MSA-Q21 for other questions than the sketch's MSA-Q19 and MSA-Q20. Each printed `gap recorded`. A `measured by` or `realised by` edge from `dal:ResourceKind` to the logical keys would carry the first, and a check that an identifier is defined once across plans and sketches the second.
- **`misses --near`.** Three of this slice's questions are among the near answers: `find landing place of a write access` at 0.71, `find R2RML RML mapping rows to graph and back` at 0.73 and `find Surface promotion derived family target table` at 0.72. The first would be carried by an entry for the studio's graph place, which is on a branch this one does not hold. The second by an entry that names R2RML and RML-Core as the standards MSA-Q5 weighs, with a `bears on` edge to MEC-74. The third by PM-Q9's answer, (iii) as the default, as an entry with a `decided by` edge from the derived family's placement. The 16 misses listed are none of this slice's.

## Questions for the maintainer

1. **The root of the ledger's tables.** (a) the owner's ledger, a derived column on every table held by composite foreign keys, which places a supersession in its ledger's partition whatever LG-Q58 decides and keeps a balance read and the supersessions it needs in one partition. (b) the root account and the close, as the RDF realisation names a period's unit, which leaves the ledger's row, every pass and, under LG-29 as built, every supersession without a unit, so a family keyed by the owner is needed beside it. (c) no root column, the record's IRI alone, leaving partition to the store, which states no unit of placement in the place. Built: (a), and we lean to it.
2. **An annotation on a runtime record.** 18 `rdfs:comment` triples on records in the examples have no column. (a) dropped on encode, since the mapping declares the family closed. (b) refused at write, since no writer of the ledger states a comment on a record. (c) kept in a table of facts beside the family. Built: (a) for the round trip, counted and left out of both sides. We lean to (b), with the examples' comments read as documentation.
3. **The ledger's receipt.** A pass is a Receipt keyed by target and seq, and the ledger has no epoch. (a) the Receipt's epoch is optional for a target that is never restored into a live epoch space. (b) the ledger's pass is a resource of its own when Persistence declares the ledger's record families. (c) the ledger gains an epoch. We lean to (b), since a pass is also the ledger's transaction claim and its record.
4. **The mapping module (MSA-Q5).** Both families needed R2RML and the place terms, and RML-Core would add three terms. MORK is the repository's own mapping vocabulary, compiled to RML (MEC-74), and Surface lowers a projection contract to it (MEC-71). (a) RML-Core as the mapping's vocabulary, with the place terms in Persistence's module or a new one. (b) MORK, lowered to RML-Core. (c) R2RML alone, refusing what it cannot say. We lean to (a), for the relational target, and have not read MORK against these two families.
5. **The identifiers MSA-Q19 to MSA-Q21.** The plan's decisions of 2026-11-18 use them for the shared types, a position and the number type, and the sketch uses MSA-Q19 and MSA-Q20 for the place of a relational realisation and the supersession. `check:identifiers` does not count it, since only the sketch's table defines them. Renumber the plan's three, or the sketch's two.
6. **The date of this pack.** The brief asked for `built 2026-11-23`. The slice was built on 2026-11-24, and the pack says so.
