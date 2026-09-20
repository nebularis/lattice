<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Quantification Rework — Migration Report

*What surfaced while resolving the critical review that belongs somewhere other than `ontology/quantification/spec/quantification.md`.*

---

## 1. A genuine blocking gap in Foundation, not just a documentation note

`quantification.md` §12 references `fnd:DerivedArtefact` repeatedly — `RecurrenceBin`, materialised `RangeSet`s, projection records, and the authority-declaration obligation (§11, P5) all assume it exists. It does not. Foundation's own delivered specification (`ontology/foundation/spec/foundation.md`) has `fnd:Version`, `fnd:Evidenced`, `fnd:TemporallyScoped`, and `fnd:Governable` — no derived-artefact mixin.

This was flagged as a forward requirement in the original sketch (`R-Q4`, itself citing an earlier `R-B4`), so it isn't a new discovery — but it's worth restating plainly now that Quantification's own document depends on it directly: **`spec/quantification.ttl` will not fully validate against a complete import chain until Foundation ships `fnd:DerivedArtefact`.** The shape it needs, based on how this document uses it: a mixin (likely alongside `fnd:Evidenced` in the four-mixin family) carrying at minimum a `derivedFrom` relation to its source declarations, a producing-profile reference, and — per P5 below — an authority-level property.

**Recommendation:** treat this as the next piece of Foundation work, ahead of anything else that depends on it. Party's document didn't need it; Quantification does, immediately.

## 2. The authority-declaration property is Quantification-local only as a stopgap

`qnt:derivationAuthority` (used in the examples, §17) is asserted here because `fnd:DerivedArtefact` doesn't exist yet to host it properly. The requirement itself (P5 in the critical review) is explicitly general — "every derived product," not a Quantification-specific concern — and Behaviour's own derived artefacts (compiled evaluators, materialised state) will need the identical property.

**Recommendation:** once `fnd:DerivedArtefact` is built, move `derivationAuthority` (and its four-value vocabulary — advisory, cached-reproducible, operationally authoritative, externally authoritative-and-synchronised) onto it in Foundation, and have Quantification's `qnt:derivationAuthority` become a documented alias or be retired in favour of the Foundation property directly. Don't let two authority-declaration properties coexist once Foundation has the real one.

## 3. SHACL that shouldn't live where a first instinct would put it

The critical review's D3 flagged `ex:`-versus-`qnt:`-named shapes as a documentation defect; working through the fix surfaced a structural point worth stating explicitly rather than leaving implicit in the examples file.

**The four illustrative SHACL shapes in `quantification.md` §11** (`RangeShape`, `CyclicRangeShape`, `RecurrenceShape`, `OperationCapabilityMeetShape`) are genuinely substrate shapes — they check structural conditions the T-box's own cardinality restrictions can't fully express (the `sh:sparql` check that a `Contains`/`Overlaps` capability sets `rangeSemanticsKind`, for instance, needs a property-existence check OWL restrictions alone don't give you as cleanly). These belong in `shapes/constraints.ttl`, exactly where they're extracted to — no migration needed, this is already correctly placed.

**What does need to move**, and wasn't in the original document as a distinct artefact at all: the **period-space compatibility check** (§6, §10 — a `Recurrence`'s `period` must be extent-compatible with its `anchor`'s position space) is described in prose as "a SHACL-level check" but no actual shape was ever written for it, in either the original draft or this rework. It's real, load-bearing content (S5 in the review) that exists today only as a sentence. **Recommend authoring this as an actual `sh:sparql` constraint in `shapes/constraints.ttl`**, following the same pattern as `OperationCapabilityMeetShape`, before this specification is treated as complete.

**The self-consistency check between `rangeSemanticsKind` and `participatesInMeet`** (§7 — the two should agree, `ExactRangeSemantics` implying `true`) is stated as a correctness expectation in prose but not enforced anywhere. Same recommendation: a `sh:sparql` shape in `shapes/constraints.ttl`, not attempted here.

**The `same-identity` and `no-self-delegation` pattern** established for Foundation and Party respectively has a Quantification analogue that was never written: nothing checks that a `Range`'s `lowerBound` and `upperBound` (where both are present) are actually on the same `ValueSpace` as the `Range` itself, beyond governance obligation 4's prose statement. Worth a shape.

## 4. Precision and rounding policy need real vocabulary, not `rdfs:Literal`

`qnt:precisionPolicy` and `qnt:roundingPolicy` (§7) are declared with `rdfs:Literal` range as a deliberate placeholder — flagged as Open Question 5 in the README itself, not hidden. This isn't a migration so much as unfinished business: these two properties are the least-specified part of the whole rework, present because the review required them to exist (S6) but without enough guidance in either source document to design their actual vocabulary responsibly. Worth a dedicated pass once a real implementation profile needs to interpret rather than merely record them, per the open question's own framing.

## 5. What did *not* need to move — confirmed, not just assumed

Worth stating plainly, since the exercise of checking is as valuable as the exercise of finding problems: the four SHACL shapes, the mechanism-intrinsic vocabulary (§8), and the law register (§10) are all correctly scoped to Quantification's own document. Nothing in Part 1 of the critical review's "what's right" table needed relocating, and the automated consistency checks run against this rework (every referenced class and property declared somewhere; every `qnt:` term used in the examples declared in the TTL) found no further drift beyond what's listed above.

## 6. Two items from the critical review deliberately not resolved in this pass

Named explicitly so they aren't mistaken for oversights:

- **P2 (the shared multi-profile conformance test corpus)** needs an actual executable test suite, not README content. §24–25 of the examples document seed the table the review asked for, but building the corpus itself is a testing-artefact deliverable, not a specification one — out of scope for these three documents.
- **P4's clean-room authoring procedure** is referenced in §15 rather than re-implemented, per the review's own recommendation to defer to the established procedure by reference. Whether the public premise ADR it calls for has actually been published is outside what this rework can confirm or produce.
