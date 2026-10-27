<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A135: Contract-first wire types

**Status:** Proposed
**Date:** 2026-10-26
**Related:** [ADR-A118](ADR-A118-word-authoring-proof-of-concept.md) (the Word authoring proof of concept, the first code to exchange contract types), [ADR-A81](ADR-A81-control-plane-http-runtime.md) (the control-plane HTTP runtime), [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (repository topology), [ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (the toolchain boundary)
**Unit:** [`lattice-platform-agentic-development`](../../developer/plans/lattice-platform-agentic-development-v0.2.md)

## Context

A message that crosses a process boundary, between a Java service, a Python worker and a TypeScript client, has one meaning that each side must read the same way. If each side writes its own type for it, the types drift apart and nothing notices until a message fails at runtime.

The platform plan states, as its guardrail G3, that Java and Python wire types are generated from `contracts/**/*.schema.json` and that a hand-written duplicate fails the build. AGENTS.md carries it as a platform guardrail and the principle register as PRI-53. No decision states it, so the principle rests on the plan and AGENTS.md alone.

What exists today is as follows.

- 45 JSON Schema files under `contracts/`, in authoring, events, identity, mork, openapi, persistence, release and surface.
- The authoring service loads 14 of them from its classpath (`ContractSchemas.java`) and validates JSON against them at runtime. Its Java types, such as `JobView`, are written by hand.
- The Word add-in's TypeScript types are written by hand and say so, and it validates with Ajv against the same schemas.
- The workers' tests validate their messages against the schemas.
- No task generates a type from a schema, and no check looks for a hand-written duplicate.

So the schemas are already the source of what a message may contain, and validation at runtime already enforces it at the boundary. What is missing is the generation that PRI-53 asks for, and a decision on whether validation is enough without it.

## Decision

We record only what the plan, PRI-53 and the code already settle. Every design question is open and is listed below.

1. **Subject.** This decision covers the types a platform service, worker or application uses for a message defined by a schema under `contracts/`.
2. **Source.** The JSON Schema under `contracts/` is the one source of a message's structure. A type in any language that disagrees with it is wrong.
3. **Scope.** It binds code under `platform/`, `workers/`, `packages/` and `apps/`. Tools under `tools/` and proofs of concept that ADR-A118 places outside the platform are not bound until a decision brings them in.
4. **Enforcement.** Whatever the open questions settle, a check run through mise holds it, so that a reviewer does not have to.

## Open questions

- **CF-1.** Does validation at runtime against the schema meet the principle, with hand-written types allowed beside it, or must every type be generated? The plan says generated. The authoring service shows that validation alone catches a malformed message at the boundary but not a type that omits a field the schema allows.
- **CF-2.** Which generator for each language, and does it handle the schema features the contracts use, such as `oneOf`, `$ref` across files and draft 2020-12?
- **CF-3.** Is TypeScript in scope? PRI-53 names Java and Python only, and the add-in is the one TypeScript consumer.
- **CF-4.** Where do generated types live, and are they committed? STD-003 says a derived file is not tracked, so the build would generate them each time, which the Java and TypeScript builds would need to do before compiling.
- **CF-5.** How is a hand-written duplicate detected? By name, by structure, or by forbidding any type in a package reserved for generated code?
- **CF-6.** What becomes of the existing hand-written types, and in what order are they replaced?

## Consequences

- PRI-53 and TD-86 cite a decision that exists, though a Proposed one.
- Nothing is generated and no code changes.
- Undecided are whether runtime validation is enough, the generators, the languages, where the types live and how a duplicate is caught.

## Provenance

Drafted on 2026-10-26 at the maintainer's request, to pay the debt recorded as TD-86. It is Proposed and the maintainer has not accepted it.

It draws on the platform plan's guardrail G3 and slices P0.2.5 and P0.7.3, the principle PRI-53, the guardrail in AGENTS.md, the 45 schemas under `contracts/`, `ContractSchemas.java` and `JobView.java` in the authoring service, the add-in's `types.ts` and `schemas.ts`, and the workers' `test_authoring_contracts.py`.
