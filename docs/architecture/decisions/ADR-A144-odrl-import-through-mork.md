<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A144: The contract builder imports ODRL policies as proposals, through a MORK mapping

**Status:** Proposed 2026-10-29
**Date:** 2026-10-29
**Related:** [ADR-A138](ADR-A138-contract-builder.md) (every template enters stated meaning through a proposal), [ADR-A146](ADR-A146-skolem-rule-for-mapped-sources.md) (how the run names the policy's blank nodes)
**Described in:** [Configuration Studio contract](../../../contracts/config-studio/README.md), "Importing an ODRL policy", and [`tools/mork_rdf`](../../../tools/mork_rdf/README.md)

## Context

Rules already written in ODRL, the W3C's policy language, describe permissions, prohibitions and duties over assets, which is much of what a licence or a data-sharing agreement states. The contract builder should be able to start from them. ODRL's vocabulary is not Instrument's: ODRL's permission is a grant, where Instrument's permission is an exception to a prohibition, ODRL's duty on a permission is a precondition, and ODRL names parties and assets by IRI where stated meaning names roles. A translation therefore makes modelling choices, and those choices should be data a reviewer can read, not code.

## Decision

1. **Through MORK.** The translation is a MORK mapping scheme, compiled to SPARQL by `tools/mork_rdf` and run over the policy, so the choices below are mappings a reviewer reads and the studio's own MORK module can edit.
2. **Proposals, never meaning.** Each rule becomes a proposed stated term with its relation, waiting for review like any proposal (ADR-A138). The import writes no bound meaning.
3. **Parties are roles,** one for each party, named from it and labelled with its name.
4. **A permission excepts an implied prohibition.** In licence law a licence is a defence against the owner's exclusive rights, so each permission excepts a prohibition of the same act on the same asset between the same parties, under a term implied by those rights and proposed on the permission's clause. The prohibition's scope is the asset alone.
5. **A duty on a permission is what the permission arises on,** an act of the duty's action by its party, since ODRL requires the duty done before the permission is used. No separate obligation is written.
6. **A remedy or a consequence is an obligation arising on the breach** of its prohibition or duty, under the same term.
7. **Constraints are the scope.** A rule's scope is a profile requiring the asset and each constraint, the operator choosing the condition's kind: equality exact, `isAnyOf` set membership, `isA` and `isPartOf` hierarchical, the comparisons an interval. A comparison's range set, any other operator, and a literal where a concept is needed are reported for the reviewer to complete.
8. **Actions are the activity scheme.** ODRL's own action concepts form a scheme bound to Instrument's activity contract, ODRL's `includedIn` giving `skos:broader`.
9. **Every policy type imports,** a Set, an Offer or an Agreement alike, as proposals.
10. **The clause is the author's choice,** one picked from the library, else a generated form with one clause for each term, its text the rule in plain words.
11. **The policy says what it is** (STD-292): its media type and its profile travel with it in the job's input, and the worker refuses one that does not say it is ODRL 2.2. JSON-LD is read with ODRL's context bundled in the repository, and no remote context is fetched.
12. **Behind a flag.** The service offers the import only when `LATTICE_STUDIO_FEATURES` names `odrl`.

## Consequences

- A reviewer sees ODRL's rules as stated meaning in Instrument's terms, with the implied prohibitions that make the permissions coherent, and decides each one.
- The mapping writes into several configurations, so the job returns one artefact for each, and the browser adds each to its part.
- A comparison constraint gets an interval condition whose range set the reviewer writes. MORK cannot yet make a mapping apply to some source values only, which building the range set from the constraint would need. Whether MORK gains such a guard is an open question for its maintainers.
- When a rule and its policy both name a party, both become roles, since a property path cannot say that the rule's own party wins. The reviewer removes the policy's.
- Other ODRL constructs, refinements of actions, assets and parties, policy inheritance from `inheritFrom`, conflict strategies and asset and party collections, are not mapped yet, and a policy that uses them imports without them.

## Provenance

The maintainer chose ODRL first and compiling MORK over interpreting it on 2026-10-29, and accepted the recommended answers to the ten modelling questions of decisions 2 to 10 the same day. Built as CB5a of the contract builder.
