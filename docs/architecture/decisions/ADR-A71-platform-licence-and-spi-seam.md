<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A71: Platform Licence (MPL-2.0) and SPI Seam

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.11, G-14
**Drafted by:** Agent, autonomous session (P0.1.12). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

The platform needs a stated open-source/commercial boundary before third-party or commercial adapters are written against any SPI, so the boundary is not discovered by accident during an engagement (a named risk in the review).

## Decision

- Platform code is licensed **MPL-2.0** (file-level copyleft): a commercial adapter implemented in a new file carries no obligation to open its own source.
- **SPI interface modules are the sanctioned extension boundary**, documented explicitly as the seam where OSS and commercial implementations meet.
- The OSS/commercial seam is published as an inventory of every extension point:

  `ScopedDataset`, `ChangeFeedSource`, `ReasonerProvider`, `ShaclEngine`, `LlmProvider`, `IdentityProvider`, `ArtifactStore`, `SecretProvider`, `UsageSink`, `PackSigner`/`TrustStore`, `PartitionedWorkQueue`, `DocumentExtractor`, `NotificationSink`.

LATTICE does not force a choice of backend for any of these; each SPI ships at least one reference (often in-process) implementation under MPL-2.0.

## Consequences

- Every new SPI module introduced by Phase 0 (`graph-spi`, `coordination-spi`, `partitioned-queue-spi`) is added to this inventory as it lands.
- P1.11.2 publishes the SPI inventory table with TCK coverage per SPI and the OSS/commercial boundary document, cross-referencing this ADR.
- File headers across `platform/` carry the MPL-2.0 SPDX identifier from this point forward; this is a lint-enforced convention (G9-adjacent), not just documentation.
