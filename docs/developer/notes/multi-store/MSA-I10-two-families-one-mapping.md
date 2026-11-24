<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MSA-I10: two families in one mapping vocabulary, and where a relational realisation's data lands

**Unit:** [`multi-store-architecture`](../../status/multi-store-architecture.md), investigation MSA-I10 of the [sketch](../../sketches/multi-store-architecture.md) §6
**Written:** 2026-11-24, on machine S, against the ledger's runtime vocabulary after LG-28, LG-30 and LG-29 and against Surface's example `saas-subscription-currency.ttl`, with a spike that runs the mapping both ways on every ledger example
**Placement:** T0, public. Platform configuration, nothing domain-specific
**Builds on:** the sketch's §4.5, MSA-Q5, MSA-Q18, MSA-Q19 and MSA-Q20, [MSA-I4](MSA-I4-four-operations-lowered.md) §4.4, the plan's decision of 2026-11-17 on MSA-I1's threshold, the [ledger's note of 2026-11-23](../ledger-to-multi-store-2026-11-23.md) §3, §5 and §6, and the [projection maintenance sketch](../../sketches/projections-maintained-in-the-write.md)'s PM-Q1 and PM-Q9
**Artefacts:** [spikes/multi-store-mapping](../../../../spikes/multi-store-mapping/README.md), with the places it emits in [results/places.md](../../../../spikes/multi-store-mapping/results/places.md)

## 1. The question

The sketch's §4.5 leans towards a mapping with no direction that says how a family is laid out in a store, shared by SQL and GQL. Its row for MSA-I10 asks for one ledger family and one promotion's derived family written in one mapping vocabulary, each read in both directions, with what R2RML and RML can and cannot say. The falsifier is that the two need different vocabularies.

The brief of 2026-11-19 adds MSA-Q19. The studio's unit gives each write access of a compiled profile a place, a graph or a family of graphs with its role. So each family's relational layout is written here in a form a compiled profile could state as a place beside a graph place, the table, its key columns, and which logical resource and key part each column holds, taken from the mapping and never from lowered SQL. The handover of 2026-11-23 adds MSA-Q20, where a supersession lives in a partitioned store.

**What is held.** The supersession, `ldg:Supersession`, is not mapped. The ledger's LG-Q58 decides whether it names its owner or an account, and its option (c) would replace `ldg:forOwner` and `ldg:periodKey` on it with `ldg:onAccount`. Section 7 says what of MSA-Q20 can be answered before that.

**The vocabulary.** R2RML, the W3C recommendation, for every map. RML-Core is the community group's superset of R2RML, its draft of 2026-03-16 read for this note, and section 4 names the three of its terms that would replace something R2RML cannot say. Beside R2RML, twenty terms of the spike's own state what a place needs and R2RML has no word for. They live under an example.org namespace in the spike's `place.ttl`. No term was added to `ontology/persistence`.

## 2. The two families

### 2.1 The ledger's records

Every record the ledger's runtime vocabulary declares but the supersession, in nine tables: `ledger`, `account`, `pass`, `posting`, `posting_source` for a posting's read set, `cut`, `merge_record`, `request` and `checkpoint`. The configuration, the account definitions, profiles, policies and value spaces, stays in RDF as pinned versions, as MSA-I8 plans. A record names a configuration node by its IRI, held in a text column.

**The root of every table is the owner's ledger.** It is the unit that is consistent, serialised and placed in one store (the plan's decision of 2026-11-18, ADR-A131's addendum of the same day), and a pass is one request guarded on its revision. No record names its ledger in a triple, so each table has a `ledger` column that decodes to nothing and is derived when the graph is encoded: from the pass's IRI for a pass, and through the account's owner for every other record. Composite foreign keys, for example a posting's `(ledger, pass)` to the pass's `(ledger, pass)` and its `(ledger, on_account)` to the account's `(ledger, account)`, hold the derived column to the records it is derived through, so a record whose account and pass are in two ledgers is refused at commit. This root is our leaning, and question 1 of the pack puts it to the maintainer.

**Each table is keyed by its root and the record.** The ledger row is keyed by the ledger alone. A field that holds several values, a posting's `prov:wasDerivedFrom`, has a table of its own keyed by the root, the record and the value. A request is part of its merge record, so `ldg:request` is a column of the request's row, read by a second map whose subject is that column.

**Every IRI is stored whole.** Section 4 says why.

**The constraints the vocabulary states, and no more.** A column is not null where its property is exactly one or at least one on the record's class, and where it is a key column or a derived one. A ledger's owner is unique, since an owner has at most one ledger. A pass's revision is unique in its ledger, and a pass's IRI is unique, since it is the replay's key. A checkpoint is unique for its account and close. An account is unique for its definition's identity, its owner, its key and its period, with two empty keys or periods counted the same, which needs `NULLS NOT DISTINCT` (PostgreSQL 15 and later, and the fixture is 16.15). The account's definition identity is a derived column too, section 5 item 5.

### 2.2 The promotion's derived family

The promotion of Surface's example restates a subscription's currency, read along plan, pricing and currency, as `exec:subscriptionCurrency` on the subscription. Its derived family is placed apart from its source, a partition for each source aggregate, with each row keyed to the carrier it derives from (PM-Q9 (iii) and PM-Q1 (a′)). One table, `subscription_currency`, keyed by the source root, the carrier and the value. The source root is derived. The example declares no persistence profile, so the spike takes each subscription as the root of its own aggregate.

The path's last step is an object property, so the value is an IRI. Section 4 says what a path ending elsewhere needs.

### 2.3 What the place states

Each table's place is emitted from the mapping. Its columns come from the term maps that read them, typed by the term map, an IRI as text, `xsd:decimal` as numeric, `xsd:nonNegativeInteger` as bigint at least 0 and `xsd:integer` as numeric. Its key, its unique constraints, its foreign keys, its key parts and its derived columns come from the place terms on the R2RML logical table. One example, the pass:

| Column | SQL type | Null | Holds |
|---|---|---|---|
| `ledger` | text | no | Aggregate root, Receipt target, derived from the pass's IRI |
| `pass` | text | no | Aggregate record, TransactionClaim transaction id, the `ldg:Pass` record |
| `position` | bigint, at least 0 | no | `ldg:passPosition` |
| `revision` | bigint, at least 0 | no | Receipt seq, `ldg:passRevision` |

The other nine are in [results/places.md](../../../../spikes/multi-store-mapping/results/places.md), generated.

## 3. Read both ways

**Decode, rows to triples**, follows R2RML's rules for the subset the mappings use. **Encode, triples to rows**, inverts the mapping, which R2RML does not define. Each triple goes to the one column whose predicate and subject class match, in the row that the record, and the value where a field holds several, identify. A type triple opens the record's row. The derived columns are filled after, and the rows are then checked against every key, unique constraint, foreign key and not-null column of their places, as a store would at commit.

The inverse exists here because every term map the two mappings use reads a column whole. A template is invertible only where its parts can be told apart again, and a function of several columns is not invertible at all, so a mapping that is to be read both ways is held to columns and to templates that parse.

The spike ran the ledger's mapping on all 24 ledger examples, 12 of which hold records, and the promotion's on its example.

| Family | Examples with records | Triples | Rows | Round trip | Left out |
|---|---|---|---|---|---|
| ledger | 12 | 825 | 201 | every example the same triples, every constraint held | 18 `rdfs:comment` on records, and 7 triples of the one supersession |
| promotion | 1 | 2 | 2 | the same triples | none |

The 12 examples with no records are cases of configuration, most of them refusals, with nothing to map. Every table of the ledger's family holds a row in at least one example. No literal changed its lexical form, since every amount in the examples is written in canonical form. The spike's tests show each check failing on its break, section 6 of the pack.

## 4. What R2RML and RML can and cannot say

| Need | R2RML | RML-Core | Here |
|---|---|---|---|
| a table, its subject, its class, a column for each property, a datatype for a column | yes | yes | used |
| a multi-valued property, as a table of its own whose subject is the parent's key | yes | yes | used, a posting's read set |
| a property of the parent held on the child's row | yes, a second map whose subject is the column | yes | used, `ldg:request` |
| a key, a unique constraint, a foreign key, a not-null column, a check | no, R2RML maps an existing database | no | the place terms |
| which logical resource and key part a column holds | no | no | the place terms |
| a column that decodes to nothing, with the rule that fills it | no. An unused column is ignored, but nothing states its rule | no | the place terms |
| the inverse, rows from triples | not defined | not defined | derived by the spike, for column term maps |
| an IRI built from an IRI column and a constant | no. A template percent-encodes every value it inserts, so `{ledger}/pass/{key}` gives `https%3A%2F%2F…/pass/debit-1` | yes, `rml:UnsafeIRI` | IRIs stored whole |
| a datatype or a language tag that varies by row | no, one constant for each map | yes, `rml:datatypeMap` and `rml:languageMap` | not needed |
| an IRI on one row and a literal on another, in one column | no, one term type for each map. One map for each kind over a filtered view, which writes SQL into the mapping | no, one term type for each map | not needed, section 2.2 |
| a list, an `rdf:List` | no | no, RML-CC's gather is a module beside it | not needed |
| the named graph of a row, from its columns | yes, a graph map, with the same encoding limit as any template | yes | not written, since the ledger's graph places are not declared |

Neither family needed a construct the other could not use. What the ledger uses and the promotion does not is constraints and derivation by path. What the promotion uses and the ledger does not is one rule, a derived column equal to another column.

## 5. What a relational place needs that a graph place's role and name template do not give

A graph place names a graph, or a family of graphs with a template, and its role says what the graph holds. Triples carry their own predicates, types and keys, and the graph's name carries the root. A relational place needs each of these stated.

1. **A table and not a name.** One table holds every root. The root is a key value in a column, never part of the table's name, so the name template has no counterpart. What partitions the table by root is a layout choice of the store, a list or hash partition, and not a name.
2. **Ordered key columns, and which logical resource and key part each holds.** A graph place's template carries the root in its slot. A table states its key columns, and one column may hold parts of several resources, the pass's `ledger` holding the Aggregate's root and the Receipt's target.
3. **A key below the resource's logical key.** The persistence compiler's logical key of an Aggregate is its root alone, since a graph holds its triples with no key of their own. A table of an aggregate's records needs the record, and the value where a field holds several. The logical keys name neither, finding MSAI10-02.
4. **A column for each property, with its SQL type and its RDF datatype or term kind.** A triple says its own predicate and datatype. A column has to be given both, and the mapping gives them.
5. **Derived columns, which decode to nothing, and their rules.** The ledger's root on every record, and the account's definition identity, which its natural key needs and which lives in the configuration in RDF. That copy is of a pinned version, which the sketch's leaning on MSA-Q4, option (b), allows on the correctness path.
6. **Constraints.** Not null for an exactly-one property, unique for a natural key, a receipt and a transaction claim, a foreign key for each reference inside the family, checked at commit, and a check for a non-negative integer. A graph place needs none, since the shapes or the generated guard hold them.
7. **A table for each multi-valued property,** whose key includes the value.
8. **The rules of the inverse.** Which column a triple goes to, and how an IRI that holds parts, MSA-I4's MSAI4-07, is split again. Here every IRI is stored whole, so only the pass's ledger is read back out of an IRI.
9. **Several resources in one table.** The SPARQL realisation puts a receipt in the log graph and a transaction claim in the transaction graph. The ledger's pass row holds the Aggregate's record, the Receipt and the TransactionClaim at once. So a relational place answers an access with the table and the columns that key its resource, and more than one access lands in one table.

What it does not need, as far as these two families go, is anything of the access itself. Every fact above is a fact of the table or its columns.

## 6. MSA-Q19, how a compiled profile states where a relational realisation's data lands

Option (a), the maintainer's leaning, a place of another class beside the graph place under one general class, holds as far as the mapping can show. The place of each table was emitted from the mapping alone, with no SQL read, and it states the table, its key columns and the resource and key part each holds, as (a) asks. Its properties are the nine items of section 5, and none of them is a property of the access, so the access stays as it is.

Two things the option's wording does not yet carry, for the maintainer.

- **The link from an access lands on a table and a set of key columns,** not on the table alone, since one table holds several resources (item 9). Under (a), the place a pass's Receipt access names is the `pass` table with `ledger` as target and `revision` as seq, and its TransactionClaim access names the same table with `pass` as transaction id.
- **The logical keys gain a record part and a value part** for an aggregate held in rows (MSAI10-02), and a Receipt of the ledger has no epoch (MSAI10-03).

Option (b), no place and the mapping alone, would serve the decode, but a reader asking where an access lands would read R2RML and the place terms beside it, which is (a) by another route. Option (c), one place class with the properties of both, would carry a name template and a table on every place, one of them always empty.

## 7. MSA-Q20, where a supersession lives in a partitioned store

**Under our leaning, the owner's ledger as the root, a supersession lives in its ledger's partition, beside the pass that wrote it,** keyed by the ledger and the supersession, with its later versions in a table of their own as a posting's read set is. This is the sketch's option (a). The ledger's note gives the reason that holds here, a pass and its supersession are written in one request, and the mapping adds one. A balance read needs the owner's supersessions for the account's definition, and under this root they are in the account's own partition, so the read of the ledger's note §6 stays in one partition.

**Where it lives does not depend on LG-Q58.** As LG-29 built it, a supersession names its owner, and its ledger column is derived through `ldg:forOwner` as the ledger's own is. Under LG-Q58's option (c) it names an account, and its ledger column is derived through the account's owner as a posting's is. Either way it is in the same partition.

**What depends on LG-Q58** is its columns and its keys: an owner column with a foreign key to `ledger (ledger, owner)` and an optional period key, or an account column with a foreign key to `account (ledger, account)` and no period key. So is the index a balance read uses to find it, by owner and definition identity or by account. The mapping of a supersession is written when LG-Q58 is answered.

**Under the other root, the root account and the close, as the RDF realisation names a period's unit,** the answer waits wholly on LG-Q58. As built, a supersession has no root account, as the ledger's note §5 says, and under option (c) it would sit in its account's root's unit open when its pass is recorded. The same root leaves the ledger's row and every pass without a unit too, since a pass writes records under several roots. Those need a family keyed by the owner whichever root the accounts' records take, and that family is where the sketch's option (a) puts a supersession.

The periods' two axes, which the ledger's note §5 corrects, do not move it. A partition's period is on the recorded axis and a supersession's period key on the effective one. In a table keyed by ledger, a closed period is a range of pass revisions or positions within the partition, not a key, so nothing about a supersession's own period places it.

## 8. Findings

| ID | Finding | Consequence |
|---|---|---|
| MSAI10-01 | Both families are written in R2RML with the same twenty place terms. The ledger uses 32 mapping terms, the promotion 21, and none is outside R2RML and the place terms | the falsifier does not fire |
| MSAI10-02 | The persistence compiler's logical key of an Aggregate is its root. A table of an aggregate's records needs a part below it, the record, and a value where a field holds several | the logical keys, or the place, gain the two parts. A graph place needs neither |
| MSAI10-03 | A pass is the ledger's Receipt, keyed by target and seq, and its TransactionClaim. The ledger has no epoch, so the Receipt's epoch has no column | the ledger's receipt is a resource of its own, or the epoch is optional for a target that is never restored into a live epoch space. For the maintainer, question 3 |
| MSAI10-04 | No ledger record names its ledger in a triple. The root column is derived on every table, and composite foreign keys hold it to the records it is derived through | the store refuses a record whose account and pass are in two ledgers, which the RDF realisation's shapes hold today |
| MSAI10-05 | The ledger's rules for an IRI, a ledger's from its owner's and a checkpoint's from its account and close, are prose, and the examples' IRIs follow no template for either. A pass's IRI is its ledger's with `/pass/` and the caller's key in every example | every IRI is stored whole. Building a pass's from its ledger's needs RML-Core's `rml:UnsafeIRI`, since an R2RML template percent-encodes the ledger's IRI |
| MSAI10-06 | An account's natural key includes its definition's identity, which the account's own triples do not hold | a derived column read from the configuration in RDF, a copy of a pinned version, with a unique constraint whose nulls are not distinct |
| MSAI10-07 | 18 `rdfs:comment` triples on records in 9 of the examples have no column. The mapping declares the family closed, which the plan's decision of 2026-11-17 puts in the mapping | an annotation on a runtime record is dropped, refused or kept apart. For the maintainer, question 2 |
| MSAI10-08 | `dal:MergeRecord`, the adopter's merge relation keyed by owner, and `ldg:MergeRecord`, the merge of requests at one account, share a local name | a place or a report names a resource by its IRI, never its local name |
| MSAI10-09 | A position is an `xsd:nonNegativeInteger`, which has no upper bound. The place holds it as bigint, which bounds it at 2⁶³ − 1. An `xsd:integer` share is held as numeric | a position past the bound is refused by a rule the ledger states, or held as numeric. Left as found |
| MSAI10-10 | A promotion's value takes its term kind from the path's last step. A path that ends in IRIs and literals, or in literals of several datatypes, needs one map for each kind over a filtered view in R2RML, which writes SQL into the mapping. RML-Core covers the datatypes and not the kinds | the derived family of such a path is refused, or its place gains a term-kind column and the mapping one map for each kind |

## 9. Verdict

The falsifier does not fire. One vocabulary, R2RML with twenty place terms beside it, holds the ledger's records, every one but the supersession, and the promotion's derived family. Each was read both ways on every example, with the same triples back and every constraint of its place held. R2RML says the layout's decode. It says nothing of keys, key parts, derived columns or the inverse, which is what a relational place has to add, and RML-Core adds only the three term-level constructs of section 4.

The mapping here was written by hand for each family and checked against the ledger's vocabulary and examples, as the plan's decision of 2026-11-17 asks. It was not derived from the shapes. It ran no SQL.

## 10. What follows

- **For MSA-I8.** The ledger's place, run on PostgreSQL with its foreign keys deferred to commit, the pass's guard on the ledger's revision, and the supersession once LG-Q58 is answered.
- **For the persistence unit, at MSA-Q19.** Section 5's nine items, and the record and value parts of MSAI10-02.
- **For the maintainer.** The pack's questions, the root of the ledger's tables first.
