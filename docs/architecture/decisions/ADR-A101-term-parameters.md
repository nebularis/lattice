<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A101: Term parameters

**Status:** Proposed
**Date:** 2026-10-26
**Related:** [ADR-A104](ADR-A104-instrument-terms-and-legal-relations.md) (Instrument, whose qualifier this decision's parameters specialise), [ADR-A112](ADR-A112-wording-layer.md) (Wording), [ADR-A131](ADR-A131-ledger-layer.md) (amounts consumed and restored), [ADR-A95](ADR-A95-quantification-alternative-bounds.md) and [ADR-A93](ADR-A93-quantification-derived-rate-spaces.md) (amounts and rates), [ADR-A98](ADR-A98-applied-layout-and-insurance-modules.md) (applied layout), [ADR-A99](ADR-A99-reference-vocabularies-and-peril-structure.md) (reference vocabularies), [ADR-A-C1](ADR-A-C1-applied-layer-theorem-restatement.md) (restatement boundary), [ADR-A-C2](ADR-A-C2-clean-room-authoring-procedure.md) (authoring order)
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md)

## Context

A contract term states what a party must, may or must not do. Many terms also state how much, how long, how often or on what basis. A limit, a retention, an aggregate counted per occurrence or per claim, a window that groups occurrences into one event, a number of reinstatements and a premium basis are all values that qualify a term and differ for each instrument that uses it. We call these values the parameters of a term.

ADR-A104 gave Instrument a qualifier that constrains or refines a term or a legal relation, and left what a qualifier carries to this decision. Until then three things have nowhere settled to live.

- The applied insurance contract module is not built. Its first design predates the Instrument rewrite and was dropped, so any parameter written today is written against a model that no longer exists.
- Amounts that are consumed and restored are now ledger accounts (ADR-A131), and amounts, bounds and rates come from Quantification. Nothing states how a parameter on a term reaches either.
- Applied modules and Open CBAA each state parameters in their own shape. The restatement boundary (ADR-A-C1) exists to stop a layer inventing locally what a lower layer should state once.

ADR-A104, the contract amounts work and the evaluation context work all cite this decision as the place the question is answered, and none of them can be completed without it. We draft it now, before the module that implements it, so that the questions below are fixed in one place and the dependent work can name them.

## Decision

We record only what other accepted decisions and plans already settle. Every modelling question is open and is listed below.

1. **Subject.** This decision covers the parameters of a contract term, meaning the values a term's stated meaning takes for one instrument, and the relations between terms that those values depend on. It also covers whether the parameters are evaluated directly or may be compiled, as optional routes.
2. **Where parameters attach.** A parameter is a qualifier in Instrument's sense (ADR-A104). It qualifies a term or a legal relation. Instrument keeps the qualifier for this purpose and does not define the kinds of parameter.
3. **Owner.** The kinds of parameter for insurance belong to the applied insurance contract module, not to the substrate. Whether any part of the pattern is general enough to move into a substrate layer is open (question 1).
4. **What it builds on.** Amounts, bounds and alternative bounds come from Quantification (ADR-A95, ADR-A93). Caps consumed over a period and restored belong to the Ledger (ADR-A131). Parameters do not restate either.
5. **Evaluation.** The declarative form of a parameter is always evaluable directly, and any compiled form is derived from it and never edited, as the applied insurance plan's routes R1 to R3 state. This decision does not choose which checks are compiled.
6. **Order of work.** The Instrument rewrite (ADR-A104) and the Wording layer (ADR-A112) are merged first. The contract module is built in applied insurance Phase 5, which starts only after Phases 1 to 4 are wired into Open CBAA. This ADR is drafted before that point so that the dependent designs can cite it. Its content is confirmed or revised at Phase 5 start.
7. **Direction of dependency.** This decision depends on ADR-A104, ADR-A112, ADR-A131, ADR-A95 and ADR-A93. Applied insurance Phase 5, the contract amounts design, the Open CBAA binding authority capacity work and the claims work that imports Instrument depend on it.

## Open questions

- **TP-1.** Is the pattern of a basis (counting unit, window and grouping rule) a substrate qualifier pattern that insurance specialises, or an insurance concept only?
- **TP-2.** How does one limit qualify several relations, when a qualifier today qualifies exactly one term or relation and a policy limit spans several?
- **TP-3.** Which kinds of parameter exist, and which are required together?
- **TP-4.** What separates a parameter of one term from a relation between terms, and which relations change structure before evaluation rather than behaviour during it?
- **TP-5.** How does a parameter reach a ledger account, and how are the combinators that read several parameters (for example the highest of several retentions) stated, given that combinators have no owner yet?
- **TP-6.** What is the target of a calculated value, which Instrument admits but leaves undefined?
- **TP-7.** What are the names ("term parameter", "term relation" and the corresponding Open CBAA term), and do they collide with the vocabulary of ADR-A99?
- **TP-8.** Which checks, if any, are compiled by default, and what does a parity test between the two routes require?
- **TP-9.** Is this a substrate decision under ADR-A-C2 or an applied one, and what version change does it cause in the modules it touches?
- **TP-10.** How are parameters in an Open CBAA statement mapped to and from term parameters?

## Consequences

- The contract amounts design, the evaluation context design and the Phase 5 plan can cite a decision that exists, and the identifier check no longer needs an exception for it.
- ADR-A104's statement that Phase 5 builds on this decision becomes a reference to a Proposed decision.
- Nothing is modelled. No class, property, shape or vocabulary is fixed here, and the applied insurance contract module remains unbuilt.
- Undecided until accepted and then revised at Phase 5 start are the ten questions above, the home of the basis pattern, and the names.

## Provenance

Drafted on 2026-10-26 at the maintainer's request, from the citations to this number collected across the repository. It is Proposed and the maintainer has not accepted it.

It draws on ADR-A104 (Consequences and decision 2), the applied insurance reference plan (§5.1 decision D2, the ADR table and §6), the term parameters sketch (§1, §4, §5, §9 and §10), the contract amounts sketch (the header, §1 and §2), the evaluation context sketch (the Phase 5 row), the instrument terms sketch (the qualifier paragraph), the computable contract substrate plan (§7), the normative rule substrate plan (§1 and §4.5), and pending design decisions PDD-04 and PDD-08.
