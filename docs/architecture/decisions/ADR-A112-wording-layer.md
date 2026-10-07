<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A112: Wording layer

**Status:** Accepted
**Date:** 2026-10-01 (proposed), 2026-10-01 (accepted, Gate A)
**Related:** ADR-A01 (amended by the addendum there), ADR-A07b, ADR-A86, ADR-A104, ADR-A106,
ADR-A113, ADR-A-C2
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)
(C0, decisions CC-D1, CC-D2, CC-D6, CC-D8)

## Context

**Premise.** A contract's text has a structure of its own, independent of what it means in law.
Parts nest and are ordered. Text embeds values supplied per instance. Tables fix their rows in a
standard form and take their columns from the instance. A library form offers variants and
conditional clauses, and an instance is assembled from it. Later documents change the text by
inserting, deleting or replacing parts. None of this says who owes what to whom.

**Examples.**

1. *Facility agreement.* Clause 4.1 reads "The Borrower shall pay interest at {margin} per
   annum". The margin is supplied when the facility is signed. A later amendment letter
   substitutes clause 4.1. The clause is the same clause in every facility drawn from the form,
   and its number changes if a clause is inserted before it.
2. *Clinical trial protocol.* The protocol's schedule of assessments is a table whose rows (visits)
   are fixed by the sponsor's template and whose columns (study arms) are set per trial. An
   optional pharmacokinetic sub-study section is included only when the trial has one.

**The problem.** Instrument holds no wording. Its `ins:Provision` (ADR-A07b) is a node with no
text, structure or variables, so the examples above cannot be stated, and a term's meaning cannot
be traced to the words that state it. The one consumer that needed wording, Open CBAA, built its
own model (`wim:`), nothing in which is specific to its domain. The design and its tests against
four instruments are in the [sketch](../../developer/sketches/computable-contract-substrate.md)
§1 and §4.

## Decision

1. **A Wording layer**, namespace prefix `wrd:`, holds what a contract's documents say and how
   they are built. "Computable contract" names the composition of Wording, Instrument and
   Behaviour. The names are argued in the sketch §1.1.
2. **The layer order.** Wording sits above Eligibility and below Instrument. Behaviour moves below
   Instrument (ADR-A106 splits it into configuration and runtime documents). The order replaces
   the diagram of ADR-A01, whose addendum restates it:

   | Layer | Imports |
   |---|---|
   | Wording | Foundation, Vocabulary, Quantification, Eligibility |
   | Behaviour | Foundation, Vocabulary, Quantification, Party, Eligibility. No longer Instrument |
   | Instrument | Foundation, Vocabulary, Quantification, Party, Eligibility, Wording, Behaviour configuration |

   ADR-A01's rule stands: no layer imports, or names a term of, a layer above it.
3. **Contents.** The sketch §4 is the design. In summary:

   | Part | Sketch |
   |---|---|
   | wordings and versioned elements in a tree, ordered by rank key, numbered by a derived object id | §4.1 |
   | content classes: text as ordered text parts (literal, variable reference, object reference), table, variable, reference, metadata | §4.1 |
   | variables, embedded and governing, with value contracts, spaces and admissible values | §4.2 |
   | tables: fields in the wording, entries at the instance or in the wording, in either orientation, long lists as multi-valued variables (CC-D6, amended 2026-10-02) | §4.3 |
   | assembly: inclusion modes, variation slots, inclusion conditions over governing variables | §4.4 |
   | the assembled wording of an instance, with its variable values | §4.5 |
   | textual amendments | §4.6 |

   Laws W1 to W7 (sketch §4.7) are the layer's laws.
4. **What Wording does not hold.** Legal meaning (Instrument, ADR-A104). The London market's
   typing schemes (an applied profile under `applied/insurance/wording/`, CC-D3). Identifiers
   (Foundation, CCS slice F1).

**Rejected.** A layer named Contract, which would claim the whole while holding only its text
(sketch §1.1). Wording inside Instrument, which would merge the two strata Open CBAA's design
principle DP3 keeps apart (sketch §3.1).

## Consequences

- `ontology/wording/` is created, under this ADR, by CCS slice C3 at `0.1.0`. Nothing imports it
  until the Instrument rewrite (C6), so its first releases cascade nowhere.
- The import-closure check ADR-A01 promised is built as CCS slice C10a.
- The root README, `ontology/README.md`, `ontology-architecture.md` and the solution design
  specification are updated when the layer lands (C3) and when the unit closes (C16).
- Open CBAA's `wim:` migrates to this layer (CCS plan §7).

## Addendum (2026-10-06): references by identity

**Status:** Proposed 2026-10-06 (CCS slice C8b, C8b-Q1 to C8b-Q4). Takes over insurml-alignment
IMA-3.3 and the identity half of IMA-D8. The [CCS plan's C8b section](../../developer/plans/computable-contract-substrate.md)
sets out the problem and each option's consequences. The examples are `reused-clause.ttl`,
`facility-agreement.ttl`, `facility-form.ttl` and `trial-protocol.ttl` in
`ontology/wording/examples/`, and Instrument's `facility-parameters.ttl`, `framework-lots.ttl` and
`services-schedule.ttl`.

1. **A reference names what it refers to, never which version** (C8b-Q1 (c)).
   `wrd:refersToObject`, `wrd:refersToVariable` and `wrd:linksTo` name a persistent identity: an
   element's, a variable's, a wording's, or a document's outside the wording. A revised definition
   or a redeclared variable therefore leaves every clause mentioning it at the same version, with
   the same hash and the same stated meaning.
2. **The wording fixes the version.** Inside the wording, the version is the one the wording holds:
   in a form, the version it comprises. In an assembled wording, the version it includes, or for a
   variable the version an included element declares (law W5).
3. **Outside documents have editions.** An external document or a document object has a persistent
   identity and an edition for each text in force, each a version under Foundation's versioning. A
   wording relies on an outside document either at one edition (`wrd:reliesOnEdition`, static: "as
   in force on 1 January 2027") or as amended (`wrd:reliesAsAmended`, ambulatory: "as amended from
   time to time"). An ambulatory reliance names no edition. The edition in force when a case is
   evaluated is a value the evaluation context supplies, which CCS C12 and C13 resolve. An
   attachment is part of what the parties agreed, and is relied on at one edition.
4. **Resolution is derived, and checked** (C8b-Q2 (a)). Law W8: within a form and within an
   assembled wording, every reference to something inside the wording finds exactly one version,
   and every reference to an outside document finds exactly one reliance, in the wording holding the
   clause or the form it was assembled from. No resolution is stored per instance. A resolution
   record (the assembly interface sketch's H5) remains available should a resolution policy appear
   that the graph does not determine.
5. **Display text** (C8b-Q3 (a)). `wrd:displayText` on a referring text part holds the words shown,
   as the drafter wrote them: an inflected form ("Lessee's") or a variable's printed name.
6. **Code** (C8b-Q4 (a)). W8 is a shape. Instrument's reference binder finds a variable's version
   from its identity at both tiers. No renderer exists yet: the assembly interface's `render`
   (IMA-4.1) will resolve references the same way.
7. **Breaking at major version zero** (ADR-A113). Wording 0.6.0 → 0.7.0, and Instrument re-pinned.
8. **Deferred.** One element version in two different forms needs transclusion (IMA-3.1), since law
   W1 places an element version in versions of one wording only. Resolving an ambulatory reliance
   at evaluation time (C12, C13).
