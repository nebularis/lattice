<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Release Integration Security

Release contracts are references, not secret containers. `ReleaseIntent` and `ReleaseReceipt` must never include access tokens, browser state, raw credentials, private keys, or RDF payloads.

Artifact integrity relies on immutable SHA-256 digests. Tags may support discovery but must not identify a promoted, restored, or rolled-back release. A release stack must verify signatures and provenance using its own identity and key-management controls before it promotes an artifact.

LATTICE semantic gate evidence is distinct from signature verification. A valid signature does not prove parity, approval, or graph compatibility. A passed semantic gate does not prove artifact provenance. Promotion requires both classes of evidence where policy requires them.

The reference registry profile has no transport security or authentication. It exists only to validate OCI interoperability in an isolated development environment.
