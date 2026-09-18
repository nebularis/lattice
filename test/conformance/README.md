<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Shared Semantic Conformance Corpus

This corpus defines the Gate 5 comparison surface for Eligibility and Behaviour profiles.

## Purpose

The corpus does not assume a compiled evaluator. It defines a profile-neutral semantic-output projection so different realisation strategies can be compared on meaning rather than on serialisation details, evidence-node identity, timestamps, or other non-semantic metadata.

## Profiles covered

- Eligibility: `elg:E1`, `elg:E2`
- Behaviour: `bhv:B-P1`, `bhv:B-P2`
- Surface: employment index, multi-hop promotion, and crosswalk promotion

## Semantic-output projection

A conforming evaluator projects its result to one of the following tuples before comparison.

### Eligibility projection

Compare only:

- decision IRI
- profile IRI
- question IRI
- decision value IRI

Ignore:

- evidence node identity
- recording timestamp
- validation-report wrapper nodes
- storage graph name

### Behaviour transition projection

Compare only:

- execution IRI
- transition IRI
- applied effect IRI
- profile IRI

Ignore:

- evidence node identity
- execution timestamp
- engine-specific queue identifiers
- materialisation graph name

### Behaviour allowance projection

Compare only:

- account IRI
- allowance definition IRI
- opening balance literal
- consumed amount literal
- expected remaining balance literal
- absorption policy IRI
- profile IRI

Ignore:

- cache identifiers
- generated node identity for intermediate calculations
- materialisation timestamps
- projection graph name

## Cases

- [cases/eligibility-e1-undetermined.ttl](cases/eligibility-e1-undetermined.ttl)
- [cases/eligibility-e2-contained.ttl](cases/eligibility-e2-contained.ttl)
- [cases/behaviour-bp1-transition.ttl](cases/behaviour-bp1-transition.ttl)
- [cases/behaviour-bp2-sequential-allowance.ttl](cases/behaviour-bp2-sequential-allowance.ttl)

Surface cases are declared in [manifest.ttl](manifest.ttl) with
`ex:surfaceContractFile` and `ex:surfaceContractKey`. They use the Surface
source graph as the oracle and compare generated assertions through the R2
parity harness.

## Expected outputs

- [expected/eligibility-e1-undetermined.ttl](expected/eligibility-e1-undetermined.ttl)
- [expected/eligibility-e2-contained.ttl](expected/eligibility-e2-contained.ttl)
- [expected/behaviour-bp1-transition.ttl](expected/behaviour-bp1-transition.ttl)
- [expected/behaviour-bp2-sequential-allowance.ttl](expected/behaviour-bp2-sequential-allowance.ttl)

## Interpretation

Gate 5 is satisfied when every accepted evaluator profile for a case produces a semantic-output projection identical to the expected output for that case, modulo the excluded non-semantic metadata listed above. The current automated Surface gate is:

```bash
python3 -m tools.phase8_conformance
```

This corpus fixes the comparison contract so later automation does not invent it implicitly.
