<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A01: Layer Dependency Order and Import Direction

**Status:** Accepted
**Date:** 2026-09-17

## Context

The repository's own documents have stated more than one dependency order at different times. The root README and `docs/architecture/ontology-architecture.md` describe a six-layer picture with Instrument and Eligibility as independent siblings under Party. The Quantification layer's own README states a seven-layer order with Quantification third, between Vocabulary and Party. Neither `ontology/party/spec/party.ttl` nor `ontology/quantification/spec/quantification.ttl` declares the imports needed to make either version machine-checkable: Quantification's compiled ontology carries no `owl:Ontology` header at all, and Party imports only Foundation.

A layer dependency order is not cosmetic. It determines which layer may name which other layer's terms, what a `projection/` file is allowed to reference, and what an import-closure check in CI is checking against. Leaving it inconsistently stated means every future contribution has to guess which of several stated orders is current.

## Decision

The dependency order is:

```
Foundation
  └── Vocabulary
        └── Quantification
              └── Party
                    ├── Eligibility
                    │     └── Instrument
                    └── Behaviour   (imports Instrument, Eligibility, Party, Quantification)
```

Concretely:

- Quantification imports Foundation and Vocabulary. It is imported by Party, Eligibility, Instrument, and Behaviour. It imports none of them and references none of their terms.
- Party imports Foundation, Vocabulary, and Quantification.
- Eligibility imports Foundation, Vocabulary, Quantification, and Party.
- Instrument imports Foundation, Vocabulary, Party, and Eligibility directly. Instrument does not sit behind a separate composition module — an Instrument element may carry an Eligibility condition without an intermediate layer.
- Behaviour imports Foundation, Vocabulary, Quantification, Party, Eligibility, and Instrument. Behaviour is the top substrate layer. Nothing in the substrate imports Behaviour.
- No layer imports upward. A lower layer never names a term from a higher one; cross-layer composition that a lower layer needs is declared from the higher layer's own `projection/` directory.

**Rejected alternative.** An independent Instrument layer with a separate composition module mediating its relationship to Eligibility was considered and rejected. It adds an indirection with no demonstrated benefit over Instrument importing Eligibility directly, and it would leave two ways to attach a condition to a document element rather than one.

**SPC is not part of this dependency chain.** `spc/` contains a substantial, independently developed ontology (`ontology/spc/spec/spc.ttl`, `ontology/spc/README.md`) under a placeholder namespace (`http://example.org/spc#`), with no populated `projection/` directory. It is not imported by, and does not import, any layer in the order above. Integrating it — namespace harmonisation, projection contracts to Party and Behaviour — is out of scope for this ADR and is left as separate, future work.

**Convention note.** A layer's ontology header is authored inside its README's `turtle-spec` fence, as the first block, and extracted into `spec/<layer>.ttl` like the rest of the T-box.

## Consequences

- `ontology/quantification/spec/quantification.ttl` gains an `owl:Ontology` header importing Foundation and Vocabulary, matching what its own README already claimed.
- `ontology/party/spec/party.ttl` gains an `owl:imports` of Quantification.
- The root README and `docs/architecture/ontology-architecture.md` are corrected to state this same seven-link order, so the layer table, the dependency diagram, and the compiled imports agree.
- A future CI check (documented in [../../validation-and-test-plan.md](../../validation-and-test-plan.md), not yet built) can verify import closure mechanically once Eligibility, Instrument, and Behaviour exist and declare their own imports.
