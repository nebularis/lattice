<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A18: Surface-to-MORK lowering boundary

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A17 (Surface unified projection authoring model), ADR-A16 (Surface projection mechanism), ADR-A19 (staged compiler architecture)
**Unit:** [`surface-mork-unified-projection`](../../developer/plans/surface-mork-unified-projection-plan.md) (epic)
**Source plan:** the Surface-MORK Unified Projection Program plan

## Context

MORK is the machine-facing, provenance-rich mapping graph. It already models `mork:DataMapping`, `mork:ShapeMapping`, `mork:RuleMapping`, `mork:QueryTemplate`, and `mork:ProjectionMapping`, with parameter bindings, targeting specs, and provenance records. The Surface outstanding items record (§3.7) confirms `mork:ProjectionMapping` already exists in `ontology/mork/spec/Mork.ttl` and that `tools/surface/mork.py` lowers in both directions against it.

Authoring MORK's mapping graph by hand — parameter bindings, targeting specs, dependency edges — is exactly the complexity ADR-A16's Surface layer was created to spare domain authors from for Promotion and Index. Projection needs the same relief.

## Decision

**A `srf:ProjectionContract` lowers deterministically into one or more MORK mapping nodes**, drawn from `mork:DataMapping`, `mork:ShapeMapping`, `mork:RuleMapping`, `mork:QueryTemplate`, and `mork:ProjectionMapping` as the contract's intent requires. MORK remains the canonical mapping graph: dependency edges, parameter bindings, and provenance live there, not duplicated in Surface. Surface never emits an executable artefact (SPARQL, SHACL, SWRL, RML) directly for a Projection contract — only a validated MORK graph, which downstream compilers (ADR-A19, ADR-A23) then target.

## Consequences

- A new lowering stage is required in the Surface compiler, distinct from Promotion/Index's direct-emit path.
- Lowered output must satisfy MORK's own completeness and validation checks before any backend compiles it — MORK validation is an acceptance gate for Surface's Projection output, not a downstream concern.
- The namespace and toolchain assumptions recorded as unverified in the Surface outstanding items record §5 (the `mork:` prefix binding, the exact term names `tools/surface/mork.py` assumes) must be confirmed against `ontology/mork/spec/Mork.ttl` as it stands, not re-guessed, before lowering is relied on in production.
- Promotion and Index keep their existing direct-emit path. This ADR does not require routing them through MORK.

## Addendum (2026-11-23): a derivation's expression is carried across, and a lowered derivation is a scheme with a source node root

**Status of this addendum:** Proposed.

The decision above lowers a projection into mapping nodes without saying what a derivation computes, so the operation of a derivation was written nowhere and a backend had to supply it. Surface now has a vocabulary to state it, and MORK has typed value expressions and an identity rule that writes on the source node.

1. **A derivation states its operation in the contract.** A derivation projection states an expression on its result-target role binding, over its evidence role bindings, in a closed vocabulary of typed expressions: sum, difference, product, quotient, a literal of a stated datatype, rounding to a stated scale, and a choice of two values on a comparison of two operands. The contract states and the compiler executes, so the operation is in the contract, where its laws are checked (`srf:P6` to `srf:P9`), and never in a backend's text.
2. **The lowering carries the expression across.** Each node of the expression becomes the MORK value expression of the same kind, with each evidence role binding it reads a typed reference to the property it binds. The lowering stays deterministic. Each node is named by its place in the contract's expression and each role by its place among the contract's role bindings, so the same contract gives the same graph in whatever order its triples were read.
3. **A lowered derivation is a mapping scheme.** Its root datum iterates the carrier class and takes the source node as its identity, so the assertion beneath it writes the result property on the carrier instance and no datum is minted or typed. The assertion's value is the lowered expression. The root also carries the targeting spec and a parameter binding for each role binding and each backend-policy field, as the bare mapping did. The lowered node is never typed `mork:ProjectionMapping`, which means lookup-class generation.
4. **The other kinds keep the bare mapping.** A graph construction, a join and an expansion lower as before until each has an expression of its own to carry. Surface still emits no executable artefact.
5. **A lowered scheme names its contract by a link.** The lowering writes `srf:producesMapping` from the contract to the root of its scheme, and from the contract to the bare mapping of the other kinds. The link is structure a reader follows, so a note carries no contract IRI, and the domain of the property is widened from a generated surface to a generated surface or a projection contract. A bare mapping keeps `mork:mappingFor`, which it already wrote. A backend reads the scheme with no knowledge of the contract, and a tool that needs the contract follows the link.

**Rejected.** The operation added to the lowered mapping by hand, which makes the lowering depend on a person and leaves the contract without its meaning. An approved template that names a query fragment, which holds query text where the contract states meaning. A datum minted for each carrier and linked to it, which changes what the contract states, a property of the carrier.

**Consequences.** A derivation that states no expression is refused, and so is one whose expression does not satisfy the laws, so a contract written before this addendum may need its operation added. MORK's shapes, with the new ones for value expressions and the source node identity, are the acceptance gate this decision's consequences name. A backend that reads a derivation's scheme can compile it with no knowledge of the Surface contract it came from.
