<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# IRI and RDF Patterns, Post-3866b21 Remediation — Status

**Unit ID:** `iri-patterns-post-3866b21-remediation`
**Status:** ✅ Complete. Every review finding is dispositioned, and the compiler templates are aligned. Follow-on work lives in other units (see "Is this unit complete?")
**Last updated:** 2026-09-23
**Review:** [iri-patterns-post-3866b21-review.md](../review/iri-patterns-post-3866b21-review.md)
**Documents changed:** [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) (summary in its Appendix D.3), [iri-identity-patterns.md](../../architecture/iri-identity-patterns.md), [iri-policy.md](../../architecture/iri-policy.md), `ontology/persistence/spec/persistence.ttl` (comments), `ontology/persistence/shapes/` (`StoreLocalEpochWarningShape` message)

## Is this unit complete?

**Yes.** All 47 findings of the review (A1–A7, B1–B14, C1–C9, D1–D7, E ×10) are fixed in the documents, and the compiler templates generate the corrected shapes (471 tests at the end of this unit, 526 after the follow-on Slice 2 of `persistence-compiler-iri-sync`).

What the corrected documents specify but this unit did not build, and where it is tracked:

| Follow-on | Tracked in |
|---|---|
| Retention job (low-water marks, pinned-head copies, prefix-only drops), epoch-bump quiesce, erasure-register replay on restore | Housekeeping first cut, [rdf-sparql-patterns-phase-plan.md Slice 3](../plans/rdf-sparql-patterns-phase-plan.md#13-slice-3--housekeeping-first-cut); erasure bindings also in `persistence-compiler-iri-sync` Slice 4 |
| `dal:firstWrite dal:PreCreatedRow` in the compiler | ✅ Done in [`persistence-compiler-iri-sync`](persistence-compiler-iri-sync.md) Slice 2 |
| Identity, privacy and claim-scheme profiles in the compiler | [`persistence-compiler-iri-sync`](persistence-compiler-iri-sync.md) Slices 3–5 |
| Request-time execution: `$requestDigest`, confirmation reads, outcome classification | The store SPI and the ingestion gateway (epic P2.3.1, P2.3.6). The caller contract is documented in `tools/persistence/README.md`, "Using the generated SPARQL directly" |
| TCK tests T-12 to T-17, S-suite, R-suite | Written into guide Chapter 27 as specifications. Executable tests belong to the store SPI TCK (epic P0.5.6) |
| Ratification of `iri-identity-patterns.md` and ADR-A82 | [phase-0-status.md](phase-0-status.md), P0.1.3 |
| `pat:Revision` alignment (`prov:Activity` or `fnd:Evidence`) | Guide Appendix E item 3 |
| `dal:` terms for the YAML-only declaration keys | Guide Appendix E item 10 |

The review record [iri-patterns-post-3866b21-review.md](../review/iri-patterns-post-3866b21-review.md) is closed against this status.

## Design decisions taken in this pass

These resolve the review's findings where more than one fix was possible. Each is recorded once, here, and applied in the documents.

| Decision | Chosen | Rejected alternative, and why |
|---|---|---|
| Epoch semantics after a bump (A1) | Guard on the dataset epoch only. Rebase the row's `pat:epoch` on its next write, continue `pat:seq`, let the receipt chain cross the epoch boundary | Bulk rewrite of every row at bump time: a long transaction over every row, not portable. Restarting `seq` per epoch: breaks the chain and S3 |
| Idempotency binding (A5) | `pat:requestDigest`, SHA-256 over `enc([operationKind, target, expected, *sorted canonical N-Triples])` | Hashing the SPARQL text: changes with template versions and parameter rendering |
| Dormant live heads under retention (A7) | Copy into `urn:g:txlog/pinned` before a drop (recommended), or pin the bucket | Relaxing prefix-only retention: breaks the as-of floor |
| Retention low-water mark (B7) | Lowest `seq` guaranteed retained, default 1, advanced before the drop. S3 driven from version rows | Receipts-only check: misses suffix and total loss |
| Canonical text pipeline (B10) | `trim(NFKC_Casefold(x))` via ICU. The non-ICU fallback is declared as its own pipeline | A hand-maintained ignorable list: incomplete (soft hyphen, variation selectors) |
| Store-local epoch (D1) | Unsafe, warned not refused, with the stated acceptance conditions | Prohibited: contradicts the SHACL warning shape and ADR-A82's warn-not-refuse stance |
| `iri-policy.md` (D7) | Body removed, defects listed, git pointer to the historical text | Fencing the body: still read as guidance |
| `urn:g:people` in Part II (C5) | Kept as a flagged simplification, with the production design in guide §24.5 | Rewriting every Part II example to per-subject graphs: a large diff for no pedagogical gain |

## Finding disposition

| Finding | Disposition | Where |
|---|---|---|
| A1 epoch bump wedges rows | Fixed | guide §10.1, §19.1, §24.1, §24.4, T-12 |
| A2 external sequencers not dense | Fixed | guide S8, §21.2, §25.4, §26.1, §26.2 |
| A3 unbounded global HLC read | Fixed | guide §21.3, `dal:LagWindowRead` comment |
| A4 txn-claim TTL unsafe for append | Fixed | guide §10.1, §15.2, §24.2 (receipt-side audits), T-15 |
| A5 idempotency key not bound to content | Fixed | guide §15.2, §19.1–§19.4, §30.2, Appendices A and B, T-14 |
| A6 Appendix B contradicts body | Fixed | guide §19.7, Appendix B (`pat:TxnCardinalityShape`, `pat:VersionRow`, `pat:RetentionShape`) |
| A7 live head not always newest bucket | Fixed | guide §24.2, T-16 |
| B1 weak ETags | Fixed | guide F3, F4, §15.4, §30.2, Glossary |
| B2 firstWrite / optional head | Fixed | guide §14.2, §19.3, §24.1 |
| B3 create path unguarded | Fixed | guide §14.2, §19.3, T-13 |
| B4 deadlock contradiction | Fixed | guide §25.7 |
| B5 target IRIs | Fixed | guide S2, S4 |
| B6 store tables disagree | Fixed | guide §21.2, §26.1, §26.2 |
| B7 low-water mark semantics | Fixed | guide §2.3, S3, §24.2, Appendix A |
| B8 outcome classification | Fixed | guide §15.2, §19.4, §19.5, §25.1, §25.5, §25.7 |
| B9 HLC never merged | Fixed | guide S7, §19.4 |
| B10 normalization specified four ways | Fixed | guide §8.1, §25.3, §29.3, QP4, K-6; iri-identity §7.3; `dal:NfkcTrim*` comments |
| B11 delimiter concatenation | Fixed | guide Chapter 5, §6.1, §7.4; iri-identity §7.4 |
| B12 placeholder example values | Fixed, recomputed by running the code | guide §2.1, §2.3, Chapters 5–7, D.1 |
| B13 fence datatypes | Fixed | guide §7.4, §16.2, bootstraps in §10.1, §14.2, §19.3 |
| B14 unbound graph, unpadded epochs, mixed widths | Fixed, every example IRI regenerated at 19 digits | guide §2.1, §10.1, S5, Chapter 13, §19.4 |
| C1 arbitrary graph writes | Fixed | guide §25.1, S-2 |
| C2 destructive TCK at registration | Fixed | guide §25.2, Chapter 27 intro |
| C3 TCK over-claimed | Fixed | guide §27.5 (R-suite), §27.6, D.2 |
| C4 quiesce writers for a bump | Fixed | guide §24.4 step 1, iri-identity §10.3 |
| C5 erasure conflicts | Fixed | guide §2.2, §6.1, §6.2, §24.0, §24.1, §24.4, new §24.5 |
| C6 recreate path | Fixed | guide §24.1, T-17 |
| C7 keys-graph access control | Fixed | guide §6.1, §25.2, S-1 |
| C8 unregistered URN namespaces | Fixed | guide §2.1 |
| C9 YAML versus `dal:` | Fixed | guide §29.3, Appendix E item 10 |
| D1 store-local epoch | Fixed | iri-identity §10.3, `dal:StoreLocalEpoch` comment, warning shape message, guide §24.4 |
| D2 key rotation dual-write | Fixed | iri-identity §6.4 |
| D3 revision class alignment | Fixed, left as the one open decision | iri-identity §10.1, guide Appendix E item 3 |
| D4 status contradiction | Fixed | iri-identity §1 |
| D5 missing ADR-A82 | Fixed | iri-identity header |
| D6 rendering defect | Fixed | iri-identity §17 |
| D7 iri-policy.md | Fixed, body removed | iri-policy.md |
| E (all ten) | Fixed | guide §1.3, §2.3, §6.2, §10.2, S6, F5, §24.2, §24.3, Appendix A, Appendix B, §25.2, S-3 |

## Compiler and template alignment (Phase 2)

Run in autonomous mode, 2026-09-23. `mise run check:persistence`: **471 passed** (290 before this unit. The rise is new templates multiplying the parametrized injection corpus, plus `tests/test_template_alignment.py`).

| Behaviour now generated | Templates | Review finding |
|---|---|---|
| Dataset-guard variants guard on the dataset epoch only and rebase the row's `pat:epoch` on write | `cas-replace-named-graph-dataset-guard`, `cas-replace-composite-property-dataset-guard`, `tombstone-delete-named-graph-dataset-guard`, new `append-event-dataset-guard` | A1 |
| `pat:requestDigest $requestDigest` on every txn claim | every row-writing template | A5 |
| `pat:head` read in `OPTIONAL` | all CAS and tombstone templates | B2 |
| `a pat:VersionRow` on row creation, dataset guard on create | `create-if-absent-named-graph`, new `create-if-absent-named-graph-dataset-guard`, new `bootstrap-version-row` and its dataset-guard variant | A6, B3 |
| Append maintains `pat:head`/`pat:prevRev`, uses `STRDT` typing, pads `seq` to 19 digits, writes events to `urn:g:events/{family}/{month}` | `append-event`, `append-event-dataset-guard` | B14, C1 |
| Fork audit counts txn claims per revision | `fork-detection-audit` | A6 |
| Receipt-side duplicate audits | new `revision-multi-txn-audit`, `txn-multi-revision-audit` | A4 |
| Row-driven, cross-epoch gap scan with low-water mark and pinned heads | `gap-scan-audit` | B7, A7 |
| Registry-listed log buckets via a request-time slot (originally `#LOG_GRAPHS#`, now the Mustache slot `{{{logGraphs}}}` after `persistence-compiler-iri-sync` Slice 2), never `STRSTARTS` | all audits | S3, F6 |
| `pat:txn` written as a string, not the claim IRI | all receipt-writing templates | Appendix B datatype |

A pre-existing defect was fixed on the way: `key-claim-write` and `key-claim-retire` wrote claims into the txn graph (`urn:g:txn`). They now write `urn:g:keys`.

**Tests added** (`tools/persistence/tests/test_template_alignment.py`): every template parses with a complete context (the "markers unsubstituted" test was later replaced by a fail-closed test when the markers became Mustache slots); dataset-guard row writers rebase rather than guard the row epoch; heads are optional; every txn claim carries the digest; row creation is typed; key claims use the keys graph; no template scans by prefix; the gap scan is row-driven; append typing and padding; template selection for the new fixture `ontology/persistence/examples/append-stream-dataset-guard.ttl`. The injection corpus context in `test_terms.py` now binds every slot.

**Adversarial probe:** reverting `cas-replace-named-graph-dataset-guard` to guard the row epoch and require `pat:head` fails `test_dataset_guard_rebases_row_epoch_instead_of_guarding_it` and `test_head_is_read_optionally`. The template was restored and the full suite re-run green.

**Not in scope for this unit:** see "Is this unit complete?" above. `pat:hlc` on receipts and configurable infrastructure graph IRIs are recorded in `tools/persistence/README.md` "Known limitations".

## Commands to reproduce

```bash
mise run check:persistence
```
