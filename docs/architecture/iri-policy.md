<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# IRI and Identity Policy (historical)

**Status:** Historical record. Not normative, not a reference profile, and not guidance.
**Superseded by:** [IRI and Identity Patterns](iri-identity-patterns.md) and [ADR-A82](decisions/ADR-A82-framework-neutral-identity-pattern-selection.md), which supersedes [ADR-A51](decisions/ADR-A51-iri-and-identity-policy.md)
**Body removed:** 2026-09-23, following [iri-patterns-post-3866b21-review.md](../developer/review/iri-patterns-post-3866b21-review.md) finding D7. The disposition is in [iri-patterns-post-3866b21-remediation.md](../developer/status/iri-patterns-post-3866b21-remediation.md).

## What this document was

The P0.1.3 deliverable: one proposed platform IRI profile for LATTICE, reviewed under ADR-A51. It specified a `urn:lattice:{tenantId}:{scope}:{family}:{localName}` lineage grammar, content revision and event IRIs beneath it, four entity minting strategies (`natural-key`, `derived-hash`, `surrogate-claimed`, `surrogate`), a content-hash procedure, a skolemization rule and a graph-name validator. The review history showed that a framework cannot mandate one identifier scheme for every adopter, and ADR-A82 replaced the profile with the framework-neutral pattern catalogue in [iri-identity-patterns.md](iri-identity-patterns.md).

The body was removed rather than kept as "historical context" because it still read as guidance, and parts of it contradict the current catalogue. Section numbers cited by ADR-A51 and by the ADR-A51 review records refer to the removed body, which remains in version control:

```bash
git show 3323b85:docs/architecture/iri-policy.md
```

## Known defects in the removed body

Anyone reading the historical body should treat these as errors, not as options:

- **Hash-only literal canonicalisation.** Its §3 canonicalised literal lexical forms before hashing while storing the original terms. Two different stored graphs could then share one content IRI. [iri-identity-patterns.md §8.2](iri-identity-patterns.md#82-canonicalize-on-write-hashing) forbids this.
- **Contradictory skolemization.** Its §5 said skolem IRIs are deterministic within a content revision while prescribing random UUIDv4 `surrogate` IRIs for nodes without a natural key.
- **Lowercase rule versus its own example.** Rule 7 made the canonical lexical form all-lowercase, while the `natural-key` example `…/Policy/POL-000123` is mixed case.
- **Invalid UUID example.** The `surrogate` example `01j9z8q3-k4m5-n6p7-…` is not a UUID: it contains non-hexadecimal characters.
- **Delimiter concatenation.** The `derived-hash` form hashed `v{schemeVersion}|{ns}|enc(keyTuple)`, a separator join around an undefined `enc`. [iri-identity-patterns.md §7.2](iri-identity-patterns.md#72-tuple-encoding-pattern) requires a self-delimiting tuple encoding for the whole input.
- **"At least 128 bits".** An open-ended digest width lets two implementations mint different IRIs for one key. [iri-identity-patterns.md §7.4](iri-identity-patterns.md#74-digest-derivation-pattern) requires an exact width.
- **Status claims.** The body described its rules as "normative", `surrogate-claimed` as the "Recommended default", and its validator as the "single source of truth". None of these hold.
