<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger supersession read

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md), slice LG-32 of the ledger unit. The ledger layer is about to let an account come under a later version of its account definition, and the record of that is to be called a supersession. Design question LG-Q52 of the [definition versions sketch](../../docs/developer/sketches/ledger-definition-versions-in-force.md) asks what the record is written on. Its cost is a lookup on every read of a balance, which was argued and not measured. This benchmark measures it, for four ways of writing the record, on three engines, and for the two ways the layer built on PostgreSQL, as the section below describes.

The layer declared no supersession term when the benchmark was written, so it declares its own under the prefix `b:` (`https://example.org/ledger-supersession-read#`): `b:Supersession`, `b:supersedingVersion`, `b:account` and `b:owner`. Every other term is the layer's (`ldg:`, with `fnd:supersededBy` and `fnd:hasIdentity` from Foundation and `qnt:numericValue` from Quantification), and a record names its pass with `ldg:inPass` and its effective position with `ldg:effectivePosition`. The data is fictional.

## The corpus

One owner and its ledger. The account tree has 15 definitions: an annual cap, an aggregate under it, 3 sections under the aggregate and 10 sublimits under the sections (4, 3 and 3). The first sublimit is keyed by site, with 1,000 sites, so it has 1,000 accounts, each part of its section's account. Every other definition has one account, which is 1,014 accounts. Each definition is versioned, with a version node, a persistent identity, a stated amount and, except for the cap, a parent version, and each account names the version it opened under with `ldg:ofDefinition`.

N events fall on random leaf accounts, a site account or a plain sublimit's, from a fixed seed. Four in five are a debit and one in five a credit, with amounts of 1 to 1,000 against stated amounts of at least 10^9, so nothing is refused and no credit is cut. Each event is one pass with a revision one more than the last and a position equal to its index, and writes one posting of 9 triples with the running balance of its account, as `ldg:runningBalance` does.

K changes of terms fall at evenly spaced events. Each raises the stated amount of the aggregate and of the 13 definitions below it by 1,000,003, which is 14 later versions. Each later version names the later version of its parent, or the cap's one version where the parent is the cap, and is linked from the version before by `fnd:supersededBy`. A change is written in a pass of its own, which moves the revision by one, and its versions are in force from the position after the event it follows. A change writes 159 triples of configuration and 3 of its pass under every variant. The same history is held four ways.

| Variant | What a change of terms writes at runtime | Triples a change writes in its records |
|---|---|---|
| per-account | one record for each account reached (1,013), with its type, account, pass, effective position and later version | 5 for each account, 5,065 |
| per-account-with-balance | as per-account, and each record states the account's balance after it, so the latest record or posting on an account gives its balance | 6 for each account, 6,078 |
| per-version | one record for each later version (14), with its type, owner, pass, effective position and later version | 5 for each version, 70 |
| per-pass | one record, with its type, owner, pass, effective position and one edge for each of the 14 later versions | 4 and 1 for each version, 18 |

K = 0 is the baseline. No variant writes anything and every read must equal today's.

## The reads

Each read is timed over a fixed sample of accounts, as the median and the 95th percentile of at least 30 repetitions, after one repetition that is checked and not timed. The sample is a site account with a posting after the last change, one whose postings all came before it, one with no posting at all, the busiest site, and two plain sublimits. V also reads the section with the keyed sublimit, the aggregate and the cap.

| Read | What it is | How each variant finds it |
|---|---|---|
| V | the stated amount in force for one account at the latest revision | per-account, the latest record on the account by pass revision, and the account's own version where there is none. Per-version and per-pass, from the account's definition to its identity, to the later versions of that identity that the owner's records name, taking the one written at the greatest revision, and the account's own version where there is none |
| R1 | a leaf's balance now | the running balance on the account's latest posting, plus V now, less V at the revision that posting was written. Under per-account-with-balance, the balance on the latest of the account's postings and records |
| R2 | a leaf's balance as of a quarter, a half and three quarters of the stream's revisions | as R1 with the revision in place of now |
| R3 | an ancestor's balance now, for a section, the aggregate and the cap | V now, less the debits and plus the credits of every posting in its subtree, reached by `ldg:partOfAccount*`. Only V differs between variants |
| B | the stated amount in force now for every account, in one query | per-account, the greatest revision of each account's records, joined back to the record. Per-version and per-pass, the greatest revision of each identity, joined to the accounts whose identity has a record, and the accounts whose identity has none taken by `MINUS` |

A record's name is not computable from what a reader holds, since a reader does not know which passes carried a change, so a record is found by the account as an object (per-account) or by the version as an object (per-version and per-pass). Those sets are small, K records for an account and K + 1 versions of an identity. The same holds for a posting, found by its account. [TSD-36](../../docs/architecture/triple-store-discovery.md) says a bound object does not give the seek a bound subject gives, so the cost of these reads grows with the records an account or a version has, and the figures say by how much. Every other step starts from a bound subject.

## The PostgreSQL arm

Slice MSA-I7 of the multi-store unit adds a fourth engine, PostgreSQL, on the server of the [PostgreSQL test fixture](../../tools/testing/postgres/README.md), pinned at 16.15 and run with PostgreSQL's defaults apart from its address, port and socket. It holds the same history, from the same triples, in a relational layout of the benchmark's own, and is checked against the same model.

**Which variants.** The layer now declares the record, as `ldg:Supersession` with `ldg:forOwner`, `ldg:inPass`, `ldg:effectivePosition` and `ldg:supersedingVersion`. Per-version and per-pass are two ways of writing it, one record for each later version or one for the pass. The arm runs those two and not the per-account variants, since the layer has no supersession on an account. The RDF arms still write the benchmark's stand-in terms, and the arm gives the triples the layer's terms before it decodes them: `b:Supersession`, `b:owner` and `b:supersedingVersion` become `ldg:Supersession`, `ldg:forOwner` and `ldg:supersedingVersion`.

**The layout.** Each subject is a row of the table its `rdf:type` names, keyed by its IRI as text, and each other predicate is a column of that row. A predicate that may hold several values, or that a later write states of an earlier write's subject, is a link table of two columns. Every reference is a foreign key, checked at commit, every predicate the layer requires exactly once is `NOT NULL`, every position and revision is at least 0, and a posting's direction is debit or credit.

| Table | Rows | Columns |
|---|---|---|
| `persistent_identity` | `fnd:PersistentIdentity` | none |
| `merge_policy` | `ldg:MergePolicy` | `identity`, `merge_rule` |
| `quantity` | `qnt:Quantity` | `on_space`, `numeric_value` (numeric) |
| `account_definition` | `ldg:AccountDefinition`, one row for each version | `identity`, `stated_amount`, `unit_of_account`, `admits_owner_kind`, `merge_policy`, and where stated `part_of`, `comment`, `credit_ceiling` |
| `ledger` | `ldg:Ledger` | `for_owner`, `ledger_profile`, `revision` |
| `account` | `ldg:Account` | `of_definition`, `for_owner`, and where stated `part_of_account`, `account_key` |
| `ledger_pass` | `ldg:Pass` | `pass_position`, `pass_revision` (unique) |
| `posting` | `ldg:Posting` | `on_account`, `in_pass`, `effective_position`, `recorded_position`, `micro_position`, `direction`, `amount_value`, `running_balance` |
| `supersession` | `ldg:Supersession` | `for_owner`, `in_pass`, `effective_position`, and where stated `period_key`, `refusal_reason` |
| `supersession_version` | `ldg:supersedingVersion` | `supersession`, `version` |
| `definition_succession` | `fnd:supersededBy` | `version`, `superseded_by` |

The indexes beyond the keys are on a definition's identity, an account's parent, a posting's account and a superseding version. The history is copied in with `COPY` in one transaction and the tables are analysed before the reads. The last change of terms is decoded and copied in one transaction of its own, which is the timed write, and the report gives the decode's share of it.

**The reads.** Each is one SQL statement with bound parameters, which psycopg prepares on the server after its fifth use, so the timed repetitions run prepared statements over a local TCP connection.

| Read | The statement |
|---|---|
| V | from the account to its definition's identity, to every version of that identity that a supersession for the account's owner names, written at or before the revision, taking the one at the greatest revision, and the account's own version where there is none |
| R1, R2 | the running balance and the revision of the account's latest posting at or before the revision, by a lateral join, with V at the revision and V at that posting's revision, in one row, and the balance is the first plus the second less the third |
| R3 | V now, and the signed sum of the postings of the subtree, reached by a recursive query over `part_of_account` |
| B | every account with its version's stated amount, left joined to the latest version of each owner and identity, taken with `DISTINCT ON` over the supersessions written at or before the revision |

**The stored count.** The rows of the entity tables, their filled cells and the rows of the link tables. Each triple is a row's type, one cell or one link row, so the count is the triples' and is held to `expected_stored`. The decode fails on a subject it cannot place, a predicate its table has no column for, a functional predicate stated twice or a term of the wrong kind.

No figure of the PostgreSQL arm is recorded here yet. The measured results below are the RDF engines' alone.

## What it tests

| Claim | Test |
|---|---|
| Every way of writing a supersession gives the model's balance at every read | every read of every variant, on every engine, at every sampled account and point, against a plain model, and B for all 1,014 accounts |
| A change of terms writes the triples the arithmetic gives | the stored triples after the history, and the triples of the last change (its records, its configuration and its pass), against `expected_stored` and `expected_change_triples` |
| A lookup on each read has a cost that depends on how the record is written | median and 95th percentile of V, R1, R2, R3 and B for each variant at K = 0, 1 and 10 |
| A change of terms costs a write that depends on how the record is written | the time to write the last change of terms, as one batch, into the history before it |
| PostgreSQL reads the model's values from the layer's record | every read of per-version and per-pass on PostgreSQL against the same model, the stored facts against `expected_stored`, and the decode's share of the timed write |

## Pass criterion

A plain Python model computes every stated amount and balance from the event stream alone. Every read, under every variant, on every engine, at every sampled account and point, equals the model, so all four variants agree. The stored triples and the triples one change writes have the count the arithmetic gives. **A wrong value or count fails the check, and names the variant, the engine, the account and the two values. Time never does.** The results go to `report.md` and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5).

## Run it

```bash
mise run check:ledger-supersession-read
```

```bash
LEDGER_SUPERSESSION_QUICK=1 mise run check:ledger-supersession-read
```

The sizes are 2,000 and 20,000 events, each with K = 0, 1 and 10 and 1,000 sites. `LEDGER_SUPERSESSION_MAX` caps the events, `LEDGER_SUPERSESSION_QUICK` runs the smallest size alone, `LEDGER_SUPERSESSION_ENGINES` takes a comma list of `oxigraph`, `jena`, `rdflib` and `postgresql`, and `LEDGER_SUPERSESSION_REPS` sets the repetitions, 30 by default. It is never a dependency of `check`. Oxigraph, through `pyoxigraph`, is persisted to a temporary directory that is removed when the run ends, including on failure, and nothing is written into the repository except the two report files. Jena and rdflib are in memory. Jena runs where its [test-support package](../../tools/testing/jena/README.md) is installed and its test kit jar is built (`mise run bootstrap:sparql-testkit`), and the report says so where it did not. The task installs the PostgreSQL fixture and its server first (`bootstrap:testing-postgres`). The run starts one server, gives each history a database of its own and drops it after, and stops the server and removes its directory at the end, including on failure. Where the server cannot be imported, the run prints `postgresql not run:` with the package it needs, and the arm's tests skip naming it. The run prints the server version it ran on, and the report records it.

## Measured results

Run of 2026-11-23 on a laptop (Python 3.14.7, pyoxigraph 0.5.13, Jena ARQ 5.1.0, rdflib 7.6.0), 1,000 sites, 30 repetitions of each read. The report holds the 95th percentiles as well.

Every read matched the model on every engine, and every stored and written count matched the arithmetic. The triples are the same on every engine. Write ms is the time to write the last change of terms, as one batch, into the history before it, on Oxigraph.

| Variant | K | Stored, 2,000 events | Stored, 20,000 events | Records a change writes | A change in all | Write ms, 2,000 | Write ms, 20,000 |
|---|---|---|---|---|---|---|---|
| per-account | 0 | 29,232 | 245,232 | 0 | 0 | - | - |
| per-account | 1 | 34,459 | 250,459 | 5,065 | 5,227 | 38.2 | 42.3 |
| per-account | 10 | 81,502 | 297,502 | 5,065 | 5,227 | 38.2 | 39.4 |
| per-account-with-balance | 0 | 29,232 | 245,232 | 0 | 0 | - | - |
| per-account-with-balance | 1 | 35,472 | 251,472 | 6,078 | 6,240 | 44.7 | 46.8 |
| per-account-with-balance | 10 | 91,632 | 307,632 | 6,078 | 6,240 | 46.2 | 45.6 |
| per-version | 0 | 29,232 | 245,232 | 0 | 0 | - | - |
| per-version | 1 | 29,464 | 245,464 | 70 | 232 | 2.7 | 3.1 |
| per-version | 10 | 31,552 | 247,552 | 70 | 232 | 2.7 | 3.5 |
| per-pass | 0 | 29,232 | 245,232 | 0 | 0 | - | - |
| per-pass | 1 | 29,412 | 245,412 | 18 | 180 | 3.8 | 3.0 |
| per-pass | 10 | 31,032 | 247,032 | 18 | 180 | 2.7 | 3.1 |

Median ms of each read on oxigraph, 20,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 0.087 | 0.388 | 0.383 | 104.6 | 7.277 |
| per-account | 1 | 0.076 | 0.444 | 0.475 | 145.5 | 35.1 |
| per-account | 10 | 0.230 | 0.721 | 0.641 | 144.8 | 256.9 |
| per-account-with-balance | 0 | 0.087 | 0.218 | 0.223 | 103.8 | 7.227 |
| per-account-with-balance | 1 | 0.071 | 0.318 | 0.310 | 143.2 | 34.1 |
| per-account-with-balance | 10 | 0.227 | 0.379 | 0.365 | 143.8 | 251.8 |
| per-version | 0 | 0.123 | 0.459 | 0.455 | 103.5 | 9.505 |
| per-version | 1 | 0.112 | 0.495 | 0.529 | 134.1 | 12.9 |
| per-version | 10 | 0.285 | 0.823 | 0.809 | 136.6 | 25.3 |
| per-pass | 0 | 0.123 | 0.460 | 0.454 | 103.5 | 9.534 |
| per-pass | 1 | 0.112 | 0.494 | 0.531 | 135.3 | 12.4 |
| per-pass | 10 | 0.283 | 0.818 | 0.805 | 135.7 | 24.2 |

Median ms of each read on oxigraph, 2,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 0.083 | 0.223 | 0.219 | 13.8 | 7.271 |
| per-account | 1 | 0.068 | 0.215 | 0.224 | 18.7 | 33.7 |
| per-account | 10 | 0.220 | 0.495 | 0.416 | 19.1 | 260.6 |
| per-account-with-balance | 0 | 0.083 | 0.078 | 0.080 | 13.7 | 7.282 |
| per-account-with-balance | 1 | 0.068 | 0.082 | 0.099 | 18.4 | 33.3 |
| per-account-with-balance | 10 | 0.221 | 0.178 | 0.171 | 18.9 | 260.7 |
| per-version | 0 | 0.120 | 0.303 | 0.293 | 13.9 | 10.1 |
| per-version | 1 | 0.108 | 0.298 | 0.310 | 17.6 | 13.2 |
| per-version | 10 | 0.278 | 0.616 | 0.610 | 18.0 | 24.2 |
| per-pass | 0 | 0.120 | 0.297 | 0.293 | 13.9 | 10.1 |
| per-pass | 1 | 0.108 | 0.299 | 0.308 | 17.5 | 12.6 |
| per-pass | 10 | 0.275 | 0.612 | 0.605 | 17.9 | 23.2 |

Median ms of each read on jena, 20,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 0.391 | 1.238 | 1.165 | 146.0 | 36.2 |
| per-account | 1 | 0.257 | 0.993 | 1.180 | 148.7 | 67.8 |
| per-account | 10 | 0.370 | 1.162 | 1.028 | 143.0 | 160.9 |
| per-account-with-balance | 0 | 0.391 | 0.495 | 0.424 | 146.1 | 36.2 |
| per-account-with-balance | 1 | 0.257 | 0.514 | 0.434 | 143.9 | 67.8 |
| per-account-with-balance | 10 | 0.384 | 0.579 | 0.493 | 144.1 | 161.2 |
| per-version | 0 | 0.427 | 1.313 | 1.241 | 146.0 | 25.1 |
| per-version | 1 | 0.297 | 1.043 | 1.244 | 144.5 | 26.0 |
| per-version | 10 | 0.432 | 1.296 | 1.177 | 146.5 | 30.5 |
| per-pass | 0 | 0.427 | 1.317 | 1.241 | 146.6 | 25.1 |
| per-pass | 1 | 0.301 | 1.053 | 1.245 | 143.9 | 25.9 |
| per-pass | 10 | 0.417 | 1.270 | 1.145 | 141.3 | 29.6 |

Median ms of each read on jena, 2,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 0.396 | 1.017 | 0.984 | 16.2 | 35.9 |
| per-account | 1 | 0.242 | 0.771 | 0.858 | 15.9 | 66.7 |
| per-account | 10 | 0.366 | 0.949 | 0.876 | 16.4 | 161.5 |
| per-account-with-balance | 0 | 0.384 | 0.301 | 0.303 | 16.0 | 35.7 |
| per-account-with-balance | 1 | 0.242 | 0.280 | 0.282 | 15.9 | 66.7 |
| per-account-with-balance | 10 | 0.371 | 0.359 | 0.334 | 16.2 | 160.2 |
| per-version | 0 | 0.418 | 1.074 | 1.050 | 16.0 | 24.8 |
| per-version | 1 | 0.281 | 0.852 | 0.938 | 15.9 | 25.6 |
| per-version | 10 | 0.408 | 1.052 | 0.985 | 16.1 | 29.7 |
| per-pass | 0 | 0.431 | 1.114 | 1.084 | 16.7 | 25.1 |
| per-pass | 1 | 0.280 | 0.846 | 0.940 | 15.9 | 25.6 |
| per-pass | 10 | 0.410 | 1.057 | 0.988 | 16.1 | 29.3 |

Median ms of each read on rdflib, 20,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 5.098 | 15.2 | 15.0 | 887.5 | 111.9 |
| per-account | 1 | 4.133 | 13.0 | 14.9 | 888.6 | 194.1 |
| per-account | 10 | 4.667 | 14.1 | 13.8 | 890.3 | 701.0 |
| per-account-with-balance | 0 | 5.114 | 5.635 | 5.475 | 888.7 | 112.1 |
| per-account-with-balance | 1 | 4.146 | 5.731 | 5.582 | 889.8 | 194.2 |
| per-account-with-balance | 10 | 4.666 | 6.361 | 5.997 | 890.6 | 699.8 |
| per-version | 0 | 5.672 | 16.3 | 16.2 | 888.6 | 32.7 |
| per-version | 1 | 5.004 | 14.9 | 16.8 | 889.9 | 68.9 |
| per-version | 10 | 8.551 | 21.6 | 21.5 | 893.9 | 1543.6 |
| per-pass | 0 | 5.683 | 16.4 | 16.4 | 890.5 | 32.8 |
| per-pass | 1 | 4.889 | 14.6 | 16.6 | 889.9 | 60.1 |
| per-pass | 10 | 7.326 | 19.4 | 19.2 | 892.1 | 180.7 |

Median ms of each read on rdflib, 2,000 events.

| Variant | K | V | R1 | R2 | R3 | B |
|---|---|---|---|---|---|---|
| per-account | 0 | 5.088 | 14.0 | 14.0 | 101.4 | 110.8 |
| per-account | 1 | 4.077 | 12.1 | 13.0 | 100.7 | 196.8 |
| per-account | 10 | 4.592 | 12.9 | 12.7 | 101.4 | 697.2 |
| per-account-with-balance | 0 | 5.103 | 4.546 | 4.725 | 101.1 | 110.8 |
| per-account-with-balance | 1 | 4.117 | 4.259 | 4.741 | 100.3 | 196.0 |
| per-account-with-balance | 10 | 4.586 | 4.978 | 4.927 | 101.2 | 698.1 |
| per-version | 0 | 5.662 | 15.3 | 15.2 | 103.2 | 32.5 |
| per-version | 1 | 4.960 | 14.0 | 14.6 | 101.7 | 68.3 |
| per-version | 10 | 8.432 | 20.5 | 20.4 | 105.0 | 1528.1 |
| per-pass | 0 | 5.636 | 15.2 | 15.1 | 101.9 | 32.3 |
| per-pass | 1 | 4.847 | 13.7 | 14.4 | 101.0 | 59.3 |
| per-pass | 10 | 7.270 | 18.2 | 18.1 | 103.7 | 179.2 |

What the run shows. Each figure is a median, from the tables above and the report.

1. **The variants agree.** All four read the model's value at every sampled account and point on all three engines, and B equals the model for all 1,014 accounts. The stored triples and the triples a change writes equal the arithmetic, 5,065, 6,078, 70 and 18 for the records and 159 and 3 more for the configuration and the pass.
2. **A change of terms writes 5,227 or 6,240 triples under the per-account variants and 232 or 180 under per-version and per-pass.** On Oxigraph the batch took 38 to 47 ms for the first two and 2.7 to 3.8 ms for the others.
3. **V grows with the changes under every variant, and by about the same factor on Oxigraph.** At 20,000 events it is 0.087 ms with no change and 0.230 ms at K = 10 under per-account, and 0.123 and 0.283 ms under per-pass. Per-pass against per-account is 1.48 at K = 1 and 1.23 at K = 10. On Jena V is 0.39 to 0.43 ms at K = 0 and 0.37 to 0.43 ms at K = 10 under all four. On rdflib per-pass against per-account is 1.18 and 1.57.
4. **R1 and R2 are V twice and a posting lookup, and per-account-with-balance replaces both with the lookup.** On Oxigraph at 20,000 events and K = 10, R1 is 0.721 ms under per-account, 0.379 under per-account-with-balance, 0.823 under per-version and 0.818 under per-pass.
5. **R3 is set by the subtree fold, and V adds little.** On Oxigraph R3 is 104 ms at 20,000 events and 13.8 ms at 2,000, and differs between variants at the same K by less than 10%. It is 135 to 145 ms at K = 1 and 10 under every variant, per-account included, where V costs 0.08 to 0.23 ms. A probe of an Oxigraph store loaded with no change, then given one unrelated triple by `extend` as the timed write is, read R3 at 122.6 ms against 106.3 ms before it, and a K = 1 history loaded wholly in bulk read 108.9 ms. So most of that rise comes from the way the last change is written and not from the records. Jena and rdflib show no such rise.
6. **B depends on the variant more than any other read.** On Oxigraph at K = 10, B is 257 ms under per-account, 252 under per-account-with-balance, 25 under per-version and 24 under per-pass, against 7.3 and 9.5 ms with no change. Per-account's B reads K records for each of 1,013 accounts, and the others read K records for each of 14 versions. On rdflib at K = 10 it is 701 ms under per-account, 1,544 under per-version and 181 under per-pass. On Jena it is 161, 31 and 30 ms.
7. **The form of B mattered more than the variant on two engines.** An optional part around the subquery for the greatest revision took 27 s on rdflib under per-version, and `FILTER NOT EXISTS` took 40.7 s on Oxigraph in an optional part, and 8.5 s on rdflib for the accounts with no record alone. The forms that finished returned the model's answer. The `MINUS` form used here takes 0.03 s on Oxigraph, 0.13 s on Jena and 1.6 s on rdflib in the same history, so the figures above say what that form costs and are not a limit.
8. **The reads are not flat in K, which is the TSD-36 effect.** A record is found by an object, so a read of V, R1, R2 and B grows with the records an account or a version has. The figures give the growth for K = 1 and 10 only, and K = 100 was not run.

## Files

| File | Role |
|---|---|
| `check.py` | the tree, the stream, the model, the four variants, the reads on three engines, the PostgreSQL arm's layout, decode and statements, the pass criterion and the report |
| `test_check.py` | the check's own tests, including that a wrong value, a wrong count and a record too many fail it, that time does not, that each variant reads the model's values, and on PostgreSQL that the decode places every triple once and each read is held to the model |
| `conftest.py` | makes a folder's removal fail while an Oxigraph store in it is open, as Windows does |
