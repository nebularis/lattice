<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A96: Instrument provision attachment

**Status:** Proposed
**Date:** 2026-09-25
**Related:** ADR-A07b (minimal Instrument shape), ADR-A86
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md) (AOR-17)

## Context

`ins:inProvision` is functional, so an obligation is attached to at most one
provision. Governing documents routinely express one obligation in several
provisions: a bilingual subscription agreement whose two language versions
are both authoritative, a consolidated policy that restates a clause in a
schedule, an amendment that repeats an obligation in its new wording. Under
the functional axiom, a reasoner given two provisions for one obligation
infers the two provisions are the same individual, merging distinct
provisions without error.

## Decision

1. **`ins:inProvision` is no longer functional.** An obligation may be
   attached to several provisions. `ins:hasObligation`, its inverse, is
   unchanged.
2. **Single attachment stays available as an option.** Instrument's shapes
   gain `ins:SingleProvisionShape` (`sh:maxCount 1` on `ins:inProvision`),
   declared in a separate optional shapes file that a deployment loads when
   its documents attach each obligation once.

## Consequences

- Instrument takes a MINOR bump under ADR-A86: a cardinality is widened and no
  conformant graph stops conforming. One entailment is removed (two
  provisions of one obligation are no longer inferred equal). That is a
  judgement call recorded here, since a graph relying on the inferred equality
  changes meaning. It is classified MINOR, not MAJOR, because the removed
  inference merged provisions their authors had named separately.
- Examples: a bilingual subscription agreement and a consolidated employment
  policy.
