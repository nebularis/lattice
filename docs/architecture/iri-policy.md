<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# IRI and Identity Policy

**Normative for:** [ADR-A51](decisions/ADR-A51-iri-and-identity-policy.md)
**Status:** Proposed, pending human ratification alongside ADR-A51

This document is the operational reference for minting and interpreting IRIs across the LATTICE platform. ADR-A51 records the decision; this document records the grammar and worked examples so implementers and the graph-name validator (P0.3.7) share one source.

## 1. Graph-lineage identity

| Kind | Grammar | Example |
|---|---|---|
| Lineage IRI | `urn:lattice:{tenant}:{scope}:{family}:{localName}` | `urn:lattice:acme:project-42:surface:policy-eligibility` |
| Revision IRI | `{lineageIri}/rev/{profileVersion}-{semanticHash[0:16]}` | `urn:lattice:acme:project-42:surface:policy-eligibility/rev/2-9f3a1c2b7e4d5601` |
| Alias graph | `{lineageIri}/current` | `urn:lattice:acme:project-42:surface:policy-eligibility/current` |

- `{tenant}` and `{scope}` (project or environment, per ADR-A63) form the environment-scoped base. Cloning an environment rewrites this segment only; the `{family}:{localName}` suffix is portable across environments.
- `{semanticHash}` is the canonical content hash under the active canonicalisation profile (`ontology-architecture.md` §10). Hashes are never compared across different `profileVersion` values.
- The alias graph is the only promotion/rollback mechanism. Consumers never name a generation directly (see ADR-A54).

## 2. Entity identity

| Strategy | Grammar | Example |
|---|---|---|
| `natural-key` | `{base}/{class}/{urlsafe(keyTuple)}` | `urn:lattice:acme:prod:party/Policy/POL-000123` |
| `derived-hash` | `{base}/{class}/h/{sha256(canonical(keyTuple))[0:24]}` | `urn:lattice:acme:prod:party/Claimant/h/3fa1e9c0b6d8425719ac0e77` |
| `surrogate` | `{base}/{class}/s/{ULID}` | `urn:lattice:acme:prod:eligibility/ExtractionCandidate/s/01J9Z8Q3K4M5N6P7Q8R9S0T1U2` |

## 3. Rules (normative)

1. No IRI contains personal data. Use `derived-hash` or a per-subject reference node (ADR-A68) instead of embedding names, dates of birth, or identifiers that are themselves personal data.
2. No IRI contains a version number, generation number, or timestamp. Versioning is exclusively `fnd:Version` nodes; generations are exclusively suffixes on projection graph IRIs (ADR-A54), never on entity IRIs.
3. The base segment of every IRI is environment-scoped. An environment clone operation rewrites only the base segment; `{class}/{localName}` suffixes are preserved so lineage survives cloning.
4. `surrogate` minting must be declared explicitly in the ingestion plan that uses it, with a stated justification. It is forbidden for any node that re-ingestion must converge onto — using it there produces duplicate nodes on every re-run.
5. Registry uniqueness is structural at the revision-IRI level (ADR-A51): two different contents cannot collide on one IRI by construction. No runtime conflict-rejection check is needed or should be added.

## 4. Validator

A graph-name validator library (P0.3.7) implements this grammar and is the single source of truth for parsing and formatting these forms — `ontology/persistence`'s `dal:graphIriTemplate` and `dal:graphPrefix` values must be well-formed instances of this same grammar, not a competing one.
