<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Vocabulary temporal-binding consumer hardening

**Unit ID:** `temporal-binding-consumer-hardening`
**Status:** Planned. No implementation started.
**Trigger:** Cross-reference of the closed `vocabulary-temporal-binding` unit's
Surface/Eligibility consumer integration against
[docs/architecture/rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md),
performed 2026-09-25.
**Predecessor unit:** [vocabulary-temporal-binding](vocabulary-temporal-fixes.md)
(closed; see its [status record](../status/vocabulary-temporal-binding.md)).
**Status record:** [temporal-binding-consumer-hardening.md](../status/temporal-binding-consumer-hardening.md)

## Problem

The `vocabulary-temporal-binding` unit's own closure review found no defect
that blocked closing it, but the cross-reference against the guide's temporal
model (valid time / transaction time / logical time, Ch. 3.2 and Ch. 23)
surfaced four items worth carrying forward under their own unit, plus one item
explicitly accepted as-is. None of the four are regressions in currently
exercised behaviour: the only fixture exercising a scoped binding
(`employment-job-family-scoped.ttl`) uses an open-ended binding, so none of
findings 1–2 have manifested in CI. They are latent until a deployment declares
a `SchemeBinding` with a real handover date.

This plan scopes four independent-enough work items, two of them as design
proposals requiring a decision before implementation, one as a documentation
task, and one as a test-implementation task. It does not implement any of
them — implementation is scheduled separately, as agreed with the human.

## Finding 5 — explicitly out of scope

"Scope" is used for three unrelated concepts across the guide (`ex:tenant`
uniqueness scoping), Surface (`srf:closureScope`), and Vocabulary/Surface
(`voc:BindingScope`/`srf:activeBindingScope`). No namespace or semantic
collision exists; the term is broad enough to carry distinct meanings by
prefix. No action is planned against this finding.

## Finding 1 — resolution plan: `produced_at` as an undeclared semantic input

### Problem restated

`tools/surface/src/surface/compile.py`'s module docstring states that
`produced_at` "sits outside the artefact hash" because it is "the only
non-reproducible value emitted." `SurfaceCompiler._compile_index` now passes
`at=self.produced_at` into `enumerate_population`, which calls
`vocabulary.resolve()` for a `ContractBoundPopulation`. For a contract with an
active `SchemeBinding`, the resolved scheme — and therefore `self.population`,
`core.ttl`/`closure.ttl`/`assertions.ttl`, `artefact_hash`, and (via the
`BoundSchemeSource` read-set digest) `semantic_hash` — now depends on
`produced_at`. `cli.py`'s `_now(None)` defaults `produced_at` to real
wall-clock time. Two compiler runs against an identical source graph, run
before and after a binding's handover date, can therefore produce different
output with no change to the source graph, contradicting the compiler's own
stated invariant and its "R1: Regeneration determinism" law
(`ontology/surface/README.md`).

### Candidate resolutions (decide before implementing)

- **Option A — Explicit, hashed resolution instant.** Introduce a distinct
  `srf:` property for the resolution instant, separate from `srf:producedAt`,
  required whenever a `ContractBoundPopulation` might resolve a scoped
  binding. Fold it into `semantic_hash`'s inputs explicitly (it already does
  so implicitly via the read-set digest; this makes it a named, visible
  component instead of an incidental one).
- **Option B — Require explicit pinning for scoped contracts.** Change
  `enumerate_population`/`SurfaceCompiler` to raise `CompileError` when a
  contract-bound population declares `srf:activeBindingScope` or its contract
  has any reachable `voc:SchemeBinding`, and `produced_at` was not explicitly
  supplied by the caller (i.e. refuse the CLI's wall-clock default for that
  case only). Unscoped contracts keep today's default ergonomics unchanged.
- **Option C — Document and audit, don't prevent.** Accept the semantic
  dependency as intentional (a deployment always wants "whichever scheme is in
  force as of generation"), and rely on Finding 2's resolution trace to make
  the choice auditable after the fact, rather than changing compiler
  behaviour. Weakest option: does not restore the R1 invariant's letter.

**Recommendation for the human decision:** Option B as the primary mechanical
fix (cheapest, preserves current behaviour for the common unscoped case, makes
divergence impossible by construction rather than merely observable), with
Option A's explicit-hash-input framing folded in as a documentation
correction to `compile.py`'s docstring and `ontology/surface/README.md`'s R1
law text (state the invariant holds for unscoped populations; a scoped
population's resolution instant is a required, explicit input instead).

### Governance note

This changes Surface's stated determinism contract and CLI ergonomics.
Per the Agentic Development Contract, implementation must not start before
this option choice is confirmed with the human, and the accepted option's
effect on `ontology/surface/README.md`'s law register (R1, S2) should be
reflected in the same slice that implements it.

## Finding 2 — resolution plan: no resolution trace in Surface's provenance

### Problem restated

`enumerate_population` discards `vocabulary.resolve()`'s `Resolution` object
(`candidates`, `used_fallback`, `winning_binding`) once it extracts `.scheme`.
The manifest's `BoundSchemeSource` read-set entry records only the resolved
scheme IRI. An auditor cannot later reconstruct which `activeBindingScope`,
resolution time, or winning binding produced a given compiled surface — a gap
against the guide's insistence (Ch. 15, Ch. 19.1) that a consequential
resolution decision leave evidence of *why*, not only *what*.

### Candidate resolution

- Extend the read-set/manifest model with the resolution context: the
  `activeBindingScope` values used, the resolution instant (tying into
  Finding 1's chosen option), and the `winning_binding` IRI or an explicit
  fallback marker. Represent this as new `srf:` properties on the existing
  `ReadSetEntry` for the `BoundSchemeSource` kind, or as a new
  `srf:BindingResolutionRecord` class referenced from it — the exact shape is
  a design decision for the implementing slice, not this plan.
- Thread the full `Resolution` object (not just `.scheme`) from
  `enumerate_population` through `_compile_index` into `_manifest()`.
- Add the new property declarations to `ontology/surface/README.md` and
  regenerate `spec/surface.ttl`/`shapes/constraints.ttl` via
  `tools/literate_extract.py`, mirroring how this session added
  `srf:activeBindingScope`.
- Consider a structural SHACL check requiring a `BoundSchemeSource` entry for
  a scoped population to also carry its resolution context, mirroring this
  session's Surface parity-shape work.

### Governance note

Adds new Surface ontology terms — same governance requirement as this
session's `srf:activeBindingScope` addition. Depends on Finding 1's option
choice for what "resolution instant" means before it can be recorded.

## Finding 3 — documentation improvement: `vvp:resolvedAt` naming

`vvp:resolvedAt` (in `ontology/vocabulary/shapes/constraints.ttl`) is compared
against a `SchemeBinding`'s `validFrom`/`validTo` — the same valid-time axis as
`resolve()`'s `at` parameter — but its name reads like the guide's
transaction-time convention (`fnd:recordedAt`/`pat:recordedAt`), not its
valid-time convention (`fnd:validFrom`/`ex:occurredAt`, guide §23.3). This is
already flagged in Vocabulary's own docs as a validation-profile-only
placeholder pending a real consuming layer's own timestamp property, so this
is a clarification, not a correctness defect.

**Scoped documentation task (no functional change):**

- Update `constraints.ttl`'s header comment and `vvp:resolvedAt`'s
  `rdfs:comment` to state explicitly that it represents a valid-time "as-of"
  query point, not a transaction-time "recorded when" timestamp, and to name
  the guide's `recordedAt`/`occurredAt` convention as the naming precedent a
  future real property should follow instead.
- Update `tools/vocabulary/README.md`'s "What this package deliberately does
  not check" section and the validation pack's description of VTB-13 to match.
- No shape, resolver, or test changes.

## Finding 4 — implement a test case: `tools/vocabulary` architecture policy

`tools/persistence` has `test_architecture.py` asserting (via AST scan) that no
resolution-critical module calls a wall-clock function. `tools/vocabulary` has
no equivalent test; `resolve()` happens not to call one today, but nothing
would catch a future regression the way persistence's test would.

**Scoped implementation task:**

- Add `tools/vocabulary/tests/test_architecture.py`, asserting that no module
  under `tools/vocabulary/src/vocabulary/` imports or calls `datetime.now()`,
  `time.time()`, or equivalent wall-clock sources. No carve-out is needed
  today (unlike persistence's HLC module), so the exemption list starts empty.
- No `mise.toml` changes needed: `check:vocabulary` already runs
  `pytest tools/vocabulary/tests`.

## Slice plan

| Slice | Scope | Depends on | Gate |
|---|---|---|---|
| 1 | Finding 3 (documentation only) | none | Human review of the wording |
| 2 | Finding 4 (test implementation) | none | Test passes and demonstrably fails against a deliberately introduced `datetime.now()` call (mutation probe) |
| 3 | Finding 1 (Surface compiler + CLI + ontology law text) | Human decision between Options A/B/C above | Existing Surface suite stays green; a new test proves two runs with different wall-clock time and an identical source graph now either produce identical output (if the fallback default is used) or the same `CompileError` in both directions (Option B) |
| 4 | Finding 2 (Surface ontology + compiler + manifest) | Slice 3 (needs the resolution-instant decision) | Manifest for a scoped-binding compile records the winning binding/context; a mutation probe on the recorded trace demonstrates it changes when the context does |

Slices 3 and 4 require human sign-off on the design option before their own
implementation starts, consistent with the Agentic Development Contract's
"Pause For Architectural Guidance."

## Deliberate non-coverage

- Finding 5 (terminology overload of "scope") — accepted, no action.
- No change to `ontology/vocabulary`'s resolver or SHACL package; all four
  items are Surface-side (1, 2), Vocabulary-doc-side (3), or
  Vocabulary-test-side (4).
- No change to Eligibility; the cross-reference found no equivalent gap there.
