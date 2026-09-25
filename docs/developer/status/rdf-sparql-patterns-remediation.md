<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF & SPARQL Patterns Guide — Remediation Status

**Unit ID:** `rdf-sparql-patterns-remediation`
**State:** ✅ Complete and closed. Executed on 2026-09-23. Several of its fixes were later found incomplete or wrong by a further review and corrected by [`iri-patterns-post-3866b21-remediation`](iri-patterns-post-3866b21-remediation.md) (see "Later corrections", below). All three deferred items are now dispositioned (see Deferred, below). Nothing further is owed by this unit.
**Plan:** [rdf-sparql-patterns-remediation.md](../plans/rdf-sparql-patterns-remediation.md) — superseded in execution by [docs/developer/review/IRI-patterns-remediation.md](../review/IRI-patterns-remediation.md), which the human designated authoritative when comparing it against this plan
**Sketch:** None
**Governing review:** [docs/developer/review/IRI-patterns-remediation.md](../review/IRI-patterns-remediation.md), executed against `iri-identity-patterns.md`/ADR-A82 as the identity authority
**Primary target document:** [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)

## What changed and why this status supersedes the pre-execution plan below

The original plan (still preserved unmodified for its analysis) treated several findings as blocked on a human design decision (B1(b), B3, B8, B9, B11). The human's execution instruction changed the resolution strategy for all of them: LATTICE does not mandate a single answer to a genuine deployment trade-off, so every one of those "open decisions" was resolved by adding a `dal:` property or class to `ontology/persistence/spec/persistence.ttl` (and, where the trade-off has a discouraged-but-valid option, a `sh:severity sh:Warning` shape in `ontology/persistence/shapes/constraints.ttl`) and repointing the guide's prose at the configuration choice instead of a mandated fix. No design decision was made unilaterally on the framework's behalf; each became a documented, adopter-facing choice.

## Findings disposition (post-execution)

| ID | Disposition |
|---|---|
| B1 | Fixed. Dataset-level epoch guard added to §10.1, §19.1, §24.1; §24.4 rewritten around `dal:EpochProfile`'s `dal:epochAuthority` (`dal:ExternalHighWaterMark` / `dal:RestoreControlledEpoch` / `dal:WriterStartRefusal` / `dal:StoreLocalEpoch`, the last discouraged) and `dal:epochGuardScope` (`dal:DatasetLevelGuard` / `dal:RowLevelGuardOnly`, the latter discouraged) |
| B2 | Fixed. Fork detection moved from `pat:prevRev`-grouping (impossible once revision IRIs are deterministic) to `pat:txn`-cardinality-per-revision, in §15.3, Chapter 18 F5, and Appendix A/D |
| B3 | Fixed. `?stream`/target IRI unified to `<urn:g:orders/1>` form everywhere it had drifted (§10.1, §10.2, Chapter 11 S6) |
| B4 | Fixed. `xsd:long(...)` (non-portable) replaced with `STRDT(STR(...), xsd:long)` (SPARQL 1.1 §17.5-portable) in §7.1 and §10.1 |
| B5 | Fixed. §19.1's CAS guard wraps `pat:head` in `OPTIONAL`; §14.2/§19.3 cross-reference `dal:firstWrite` (`dal:PreCreatedRow` / `dal:AbsentRow`) so a family declares which shape it uses rather than the guide asserting one universal shape |
| B6 | Fixed. §10.1's counter form maintains `pat:head`/`pat:prevRev`, matching the CAS form |
| B7 | Fixed. All `W/"..."` weak ETags replaced with strong `"..."` tags (§15.4, §19.1, §19.2, §19.4, §19.5), with an RFC 9110 §13.1.1 note; `dal:etagForm`/`dal:etagRepresentation` added for the representation-Vary case |
| B8 | Fixed. `resolve()`'s post-timeout path no longer collapses to `CONFLICT`; returns `UNKNOWN` and documents the poll-vs-resubmit choice as a declared, not mandated, resolution |
| B9 | Fixed. §24.2 retention table corrected to `dal:PrefixOnlyRetention` (contiguous-prefix pruning keeps the live head's bucket safe by construction) vs `dal:BucketAnyRetention` (flagged incompatible with as-of replay by `dal:AsOfFloorRetentionCompatibilityShape`); `pat:RevisionShape`'s `pat:prevRev` is confirmed not to require `sh:class`, so pruning does not break it |
| B10 | Fixed. Fencing-token snippets in §7.4 and §16.2 now advance the token in the same operation, with `<=` |
| B11 | Fixed. §21.3 rewritten around `dal:GlobalReadStrategy` (`dal:WatermarkedRead` / `dal:LagWindowRead` / `dal:DenseFeedRead` / `dal:NoGlobalRead`) and `dal:ContiguityCheckMode` (`dal:BlockingContiguityCheck` default / `dal:AdvisoryContiguityCheck`) |
| B12 | Fixed. §17.3 extended: sharding the meta graph alone is insufficient; `dal:txnShards`/`dal:logShards`/`dal:keyShards` must shard the other three graph kinds too |
| B13 | Fixed. False "sorted IRI order prevents deadlock" claim removed from §10.1 and §19.6; replaced with `dal:deadlockPolicy` (`dal:EngineDetectAndRetry` default / `dal:SortedAcquisition` / `dal:PartitionedWriter`) |
| C1 | Fixed. ULID/ADR-A51 citations in §19.4 and Appendix E item 5 repointed to `iri-identity-patterns.md` §6.3/§10.6 and `dal:ClaimScheme`/`dal:schemeState` |
| C2 | Fixed. Confirmed `fnd:replacedBy` does not exist in `ontology/foundation/` (verified by search); P7's merge policy now uses `dal:mergeRelation`, a family-declared property, never an assumed Foundation term |
| C3 | Fixed as a wording correction, not a digit-count regeneration (see Deliberate scope reduction, below) |
| A-7 | Fixed. Chapter 11 S3/S4/F5's unbound `GRAPH ?log` + `STRSTARTS` prefix scans (which scan every graph in the dataset, F6) replaced with `VALUES ?log { ... }` enumeration and a note that production forms enumerate `dal:registryGraph`'s bucket list |
| A-8 | Fixed. §7.3 and §7.5's raw-literal `GROUP BY` shapes/queries annotated as a cheap first pass only; primary duplicate detection is application-side, using the frozen normalization pipeline, per §8.1 |
| A-9 | Addressed conservatively. The exact OPTIONAL-adjacent unbound-sort bug described was not reproducible against the guide's current S5 query (`pat:opSeq` is mandatory there, not optional); added a note describing the correct `COALESCE` pattern for the case where a family's grain is genuinely mixed (`dal:orderingGrain`) |
| A-11 | Fixed. `Hlc.send()`/`Hlc.receive()` clamp the logical counter and borrow from the physical component instead of overflowing past 9999 |
| A-12 | Fixed. Appendix A's `pat:opSeq` comment clarifies it is authoritative on the event and valid on the revision only for a single-event revision |
| A-13 | Fixed. Appendix A's `pat:occurredAt` comment clarifies the revision-level default vs event-level override relationship |
| A-14 | Fixed. `pat:stableWatermark`'s format corrected from a per-target-looking `{epoch}:{seq}` to a dataset-wide `{epoch}:{position}`; missing `pat:retentionLowWaterMark` and deprecated `pat:etag` added to Appendix A |

## Later corrections (2026-09-23, `iri-patterns-post-3866b21-remediation`)

The rows above record what this unit did. Where a later review found the fix incomplete or wrong, the current position is:

| This unit's finding | Later finding | Current position |
|---|---|---|
| B1 dataset-level guard added *alongside* the row guard | A1, B3, C4 | The dual guard wedged every row after an epoch bump. Writes now guard on the dataset epoch only and rebase the row epoch; create paths are guarded too; writers are quiesced for a bump |
| B5 `OPTIONAL pat:head` tied to `dal:AbsentRow` | B2 | Inverted: the pre-created row is the one with no head on its first CAS. Delete also reads the head optionally |
| B7 weak ETags replaced | B1 | Four weak forms had survived (F3, F4, glossary, §30.2); now strong everywhere, with deterministic serialisation required |
| B8 poll-versus-resubmit left as a declared choice | B8 | Every transport failure is `Unknown`, resolved by resending the identical request then confirming on the primary; the outcome set is split further |
| B9 prefix-only retention "keeps the live head safe by construction" | A7, B7 | False for dormant streams: live heads are now copied into a pinned-head graph before a drop, and the retention low-water mark has defined semantics |
| B11 global-read strategies | A3 | The read now requires an upper bound, with a lag budget and a late-arrival audit |
| B2 fork detection by txn cardinality | A6 | Appendix B still shipped the old shape; replaced by `pat:TxnCardinalityShape`, plus receipt-side audits |
| C3 width contradiction fixed by wording only | B14 | Every example regenerated at 19 digits, epoch included (see Deliberate scope reduction, below) |

## Deliberate scope reduction

The guide's worked examples use a 16-digit zero-padded revision-IRI width throughout as an illustrative simplification, while several places also claimed "19 digits in production" — a self-contradiction (C3/A-1). Mechanically regenerating every worked example in this ~3000-line guide to a consistent width was judged disproportionate to the defect: the actual bug is the guide asserting two widths are both normative. The fix applied throughout (§10.1, §19.4, Chapter 13) states the width is a per-deployment profile decision (`dal:DigestScheme`, [iri-identity-patterns.md §10.2](../../architecture/iri-identity-patterns.md#102-fixed-width-positions)), fixed once and never mixed, and stops presenting 16 or 19 as competing recommendations. A follow-up slice can regenerate every example to a single width if a consistent visual convention is wanted; this pass did not do that. **Done later** by `iri-patterns-post-3866b21-remediation` (B14): every example is now 19 digits.

## Deferred (not attempted in this pass)

1. **Compiler wiring.** Handed over to [`persistence-compiler-iri-sync`](persistence-compiler-iri-sync.md), which owns it from here. **Closed 2026-09-25**: that unit's Slices 1–5 are complete, 774/774 tests passing, human-validated; Slice 6 (documentation close-out) is its own final pass.
2. **New TCK test bodies.** Written as specifications in guide Chapter 27 by `iri-patterns-post-3866b21-remediation` (T-12 to T-17, the S-suite and the R-suite). The note above that "T-1 through T-13" existed was wrong: only T-1 to T-11 existed then. Executable TCK code belongs to the store SPI TCK (epic P0.5.6).
3. **Fixture file for Worked example 4** (`examples/identity-epoch-privacy-profile.ttl`). Handed over to [`persistence-compiler-iri-sync`](persistence-compiler-iri-sync.md) and authored in its Slice 3 (2026-09-23); its privacy part is exercised by Slice 4.

## Validation performed

All edits were verified with the editor's `get_errors` check (Markdown lint only) after each batch, with no errors reported at any point. No SHACL, SPARQL, or build/test command was run, per this repository's Default Mode (`.github/copilot-instructions.md`): build, test, and validation commands are for the human to run and report back on.

## Commands to run

From the repository root:

```
mise run check:persistence
```

Expected: the Turtle in `ontology/persistence/spec/persistence.ttl` and the shapes in `ontology/persistence/shapes/constraints.ttl` parse and validate cleanly, and no naming collision is reported against the pre-existing `dal:` vocabulary. If a Markdown link checker or prose linter is part of the standard `mise` task set, run that too, since this pass added several new internal cross-references (`iri-identity-patterns.md` anchors, `dal:` shape names) that a linter would catch faster than manual review.

A pass is: no parse errors, no validation errors, no broken internal links. A failure in `mise run check:persistence` most likely means a `dal:` name used in the guide's prose does not exactly match the vocabulary (this pass cross-checked every reference against `persistence.ttl` directly via `grep_search` and corrected three mismatches found that way — `dal:HardDeleteReplay`, `dal:AbortAndRetry`/`dal:ExternalLockOrder`/`dal:SinglePartitionedWriter`, and `dal:PruneWithLiveHeadGuard`/`dal:NoPruning` were all invented names not present in the vocabulary and have been corrected to the real ones, but a residual mismatch elsewhere is the most likely remaining failure mode).

---

## Pre-execution plan (preserved for reference; superseded by the disposition above)


## Findings disposition

| ID | Severity | Disposition |
|---|---|---|
| B1 | Blocking | Planned. Part (a) mechanical, part (b) is an open decision (Part F item 1) |
| B2 | Blocking | Planned. Single valid fix identified; no open decision |
| B3 | Blocking | Planned. Open decision (Part F item 2) |
| B4 | Blocking | Planned. Single valid fix identified; no open decision |
| B5 | Blocking | Planned. Single valid fix identified; no open decision |
| B6 | Blocking | Planned. Single valid fix identified; no open decision |
| B7 | Blocking | Planned. Single valid fix identified; no open decision |
| B8 | Blocking | Planned. Open decision (Part F item 3) |
| B9 | Blocking | Planned. Open decision (Part F item 4) |
| B10 | Blocking | Planned. Single valid fix identified; no open decision |
| B11 | Blocking | Planned. Open decision (Part F item 5) |
| B12 | Blocking | Planned. Single valid fix identified; no open decision |
| B13 | Blocking | Planned. Single valid fix identified; no open decision |
| C1 | Cross-doc | Planned. Mechanical repointing; no open decision |
| C2 | Cross-doc | Planned. Blocked on a factual check (Part F item 6) |
| C3 | Cross-doc | Planned as far as the source review permits. Blocked on the review's own completion (Part F item 7) |

## Pre-execution blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| Five design decisions open | B1(b) epoch-allocation source, B3 target-IRI unification, B8 timeout-outcome policy, B9 retention/shape trade-off, B11 HLC-pagination safeguard | Human — see plan Part F items 1-3, 4, 5 |
| One factual verification open | C2: whether `fnd:replacedBy` exists in `ontology/foundation/` | Whoever implements the slice, before touching §7.5/§23.3 |
| One incomplete source document | C3: the governing review's own text ends mid-sentence at this finding | Review's author — plan Part F item 7 |

Nothing else blocks starting the mechanical (Decision required: NO) fixes listed in the plan's ledger, but Part D's sequencing notes mean several mechanical and decision-gated fixes share the same source blocks (notably §19.1, §10.1, and §19.4) and should not be edited twice — implementation should wait for all decisions touching a given block before editing it once.

## Next steps

1. Human resolves the five open design decisions in Part F items 1-5.
2. Implementer confirms the `fnd:replacedBy` question in `ontology/foundation/` (Part F item 6).
3. Review's author completes finding C3, or the human explicitly accepts this plan's independent cross-check as sufficient to proceed on a stated width choice without it.
4. Once resolved, decompose the plan into one or more implementation slices per copilot-instructions' mandatory slice shape (code/doc change, Validation Pack, traceability update, doc delta), following the sequencing order in the plan's Part D.
5. Each slice's Validation Pack must include at least one adversarial case per Blocking finding it closes, per the human validation gate's mutation-check step, given several of these defects (B2, B8 in particular) are exactly the kind of "test passes while the system is corrupt" bug that discipline exists to catch.
