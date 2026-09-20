<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Teaching Pack (MTP): Implementation Plan

Date: 2026-09-20
Status: Implementation in progress. Structural scaffold authored, generated pack and validation pending a working environment.
Owner: MORK maintainers
Decision class: Build roadmap (implements [LLM Training.md](LLM%20Training.md), [MTP-L0 Generator Sketch](MTP-L0%20Generator%20Sketch), [MTP L2 Generator Sketch.md](MTP%20L2%20Generator%20Sketch.md))

---

## 1. Executive summary

This plan turns three design documents — the "LLM Training" essay, the MTP-L0 generator sketch, and the MTP L2/L3 generator sketch — into a phased, buildable roadmap for the **MORK Teaching Pack (MTP)**: a versioned, hash-pinned, machine-generated curriculum that teaches an LLM to emit valid MCN, instead of asking it to hold 45k tokens of `Mork.ttl` in its head.

The three source documents already agree with each other almost everywhere they overlap (the L2 sketch explicitly reuses `mtp.facts`/`mtp.codebook` from L0; the reconciliation section at the end of the L2 document resolves the few places it disagreed with the essay). This plan does not re-litigate those decisions. It sequences the work, fixes the repository layout, locks the interfaces the generator needs from `mcn_decoder.py`/`mcn_codebook.py` (already extended for exactly this purpose in the prior session — see §6), and states plainly what is being deferred and why.

**Backend-dependent model-quality evaluation is explicitly out of scope for this plan.** A separate effort is designing a configurable interface to different LLM backends, and the eval harness for *model output quality* depends on that interface existing. §2.2 draws the line precisely: structural verification that generated MCN decodes, lints, validates, round-trips, remains pinned, and fits its budget is required infrastructure; scoring what a model produces from a prompt is the deferred part.

> **Repository integration update, 2026-09-20:** this plan follows the repository delivery model introduced by the broader Surface and MORK programme. `mise` selects toolchains and runs repository tasks. Python, Maven, Yarn, and Mix remain dependency authorities. Work is authoring complete only when source, contracts, fixtures, tests, CI wiring, ADRs, architecture documentation, and a validation handoff are present. It is validated complete only after a network-enabled environment records command results. See [the consolidated implementation handover](../../docs/developer/implementation-handover.md), [the toolchain guide](../../docs/developer/toolchain.md), and [the offline handoff procedure](../../docs/developer/offline-phase-handoff.md).

## 1.1 Repository delivery and documentation rules

MTP is a MORK subprogramme, not a standalone codebase. It preserves the existing MORK vocabulary, MCN decoder, codebook, examples, and shapes as authoritative sources. It integrates with current repository boundaries:

- **Toolchains:** root [mise.toml](../../mise.toml) pins Python 3.11 and will invoke scoped MTP tasks. [mork/pyproject.toml](../pyproject.toml) remains the MORK package authority. Do not introduce a second Python lock strategy without an ADR.
- **Code:** generator code belongs under `mork/src/python/mtp/`, using the established pure-Python package style. Optional MTP worker wrappers belong under `workers/src/lattice_workers/` and accept only immutable graph or artifact references.
- **Curated and generated content:** curated MTP inputs live under `mork/mtp/data/`; generated, committed teaching-pack output lives under `mork/mtp/out/`. Do not manually edit `out/`.
- **Contracts:** only cross-runtime, UI, worker, or release-boundary payloads belong under root `contracts/mork/` or `contracts/events/`. Internal Python dataclasses remain in the package.
- **Documentation:** normative MORK and MCN semantics remain in MORK specifications and existing design documents. Durable ownership, curation, pinning, or backend boundaries require an ADR under `docs/adr/`. Explanatory implementation material belongs under `docs/architecture/` or `mork/docs/`.
- **Validation evidence:** CI and phase handoffs record outcomes. Plans and architecture documents must distinguish authored artifacts from unrun validation.

## 1.2 Completion model

Every MTP phase has two states:

1. **Authoring complete:** source, curated inputs, generated outputs where applicable, fixtures, structural tests, CI task wiring, ADRs, architecture documentation, and a phase handoff are present and statically coherent.
2. **Validated complete:** a network-enabled environment resolves dependencies, runs the command matrix, reviews generated-file and lockfile changes, and records results as CI or release evidence.

MTP model-quality evaluation remains deferred to the backend-interface effort. Structural verification of generated MCN, pins, partitions, cassette fidelity, mutation reports, budgets, and stale output remains in scope and is required for authoring completion.

---

## 2. Scope and non-goals

### 2.1 In scope

- The full L0 kernel generator: `facts.py`, `ce.py`, `codebook.py`, `doctrine.py`, `template.py`, `budget.py`, `render.py`, `lock.py`, `cli.py`, and the curated `doctrine.yaml`.
- The full L2/L3 pipeline: corpus statistics, partitioning, the mutation engine and its silent-set report, cassette fidelity/minimisation, lens rendering, routing, and the repair-loop diagnostics table.
- The `mcnio.py` adapter boundary, built directly against the `mcn` package (§6) — this is verification infrastructure (does this MCN text decode, lint clean, validate against `constraints.ttl`?), not model evaluation.
- The kernel-wording and doctrine changes named in the L2 document's reconciliation section (R1, R2, R3's kernel clause) that are pure text/doctrine content, not test design.
- CI gates that check the *pack's own* internal consistency (codebook coverage, pin drift, axiom ownership, partition completeness, cassette fidelity, silent-mutation detection, budget limits, output staleness).

### 2.2 Out of scope (deferred)

| Deferred item | Why | Where it resumes |
|---|---|---|
| `mtp/evalset.py`, `out/eval/*.json`, the held-out task suite | Scoring model output requires invoking a model through some backend | Phase 7, gated on the backend-interface work |
| `eval-report` CI step, `eval.leakage` / `eval.thin` gates | Same | Phase 7 |
| First-pass lint-clean rate, unsafe-confidence rate, ρ(t) stratification by `mtp-version` (LLM Training.md §7, L2 reconciliation R4/R5) | These are eval metrics scored against real model runs | Phase 7 |
| Any decision about *which* LLM backend(s) a generation run uses | Belongs entirely to the other effort | N/A — consumed, not designed, here |

**The one thing this plan does *not* defer, despite living next to "eval":** `mtp/mcnio.py`'s `MCNTool` adapter (decode/lint/SHACL) is required by S4 (cassette fidelity), S6 (mutation verdicts), and the L0 build's own `axiom.unowned` gate. None of that involves a language model — it is the same decode-then-isomorphism-diff technique already proven out for `loan_mapping.ttl`/`UncertainMappings.ttl` in `test_mcn_decoder.py`. Losing it would mean shipping a pack with no way to know if its own cassettes are valid MCN, which is a correctness bar, not a test regime. §9 names the gates this plan keeps and the two it drops.

---

## 3. What already exists

| Component | Status | Location |
|---|---|---|
| MCN decoder (spec §13, D1-D9) | **Built** | [mork/src/python/mcn_decoder.py](../src/python/mcn_decoder.py) |
| MCN codebook (spec §8) | **Built**, includes `code_for`/`codes_for` reverse lookup | [mork/src/python/mcn_codebook.py](../src/python/mcn_codebook.py) |
| `import mcn` package (decode/lint/canonical_ntriples) | **Built** | [mork/src/python/mcn/__init__.py](../src/python/mcn/__init__.py) |
| Stable, namespaced error/finding codes (`McnSyntaxError.code`, `LintFinding.code`/`.severity`/`.line`) | **Built** | same modules |
| Decoder test suite (337 tests, incl. round-trip proofs for `loan_mapping.ttl`/`UncertainMappings.ttl`) | **Built** | [mork/src/python/test_mcn_decoder.py](../src/python/test_mcn_decoder.py) |
| MCN encoder (spec §15, RDF → MCN) | **Not built** | — |
| MTP package scaffold, CLI, facts, MCN adapter, corpus, partition, mutation, cassette, lens, routing, pin, and budget surfaces | **Authored, unvalidated** | [mork/src/python/mtp](../src/python/mtp) |
| Curated starter doctrine, partition, lenses, cassettes, routing, and configuration | **Authored, unvalidated** | [mork/mtp/data](../mtp/data) |
| Generated teaching pack | **Not generated in this restricted environment** | [mork/mtp/out](../mtp/out) |

This matters for sequencing: the L0/L2 sketches were written assuming a decoder might not exist yet (hence `NullTool` and `"provisional": true`). It exists now. `NullTool` is retained only for the one thing still genuinely absent — `encode()`. The authored MTP scaffold uses real decoder and codebook interfaces, but its generated pack, pin file, cassette fidelity report, mutation matrix, and CI results remain unvalidated until a working environment runs the command matrix in the MTP handoff.

---

## 4. Architecture: the merged pipeline

The L0 and L2 pipelines are two stages of one build, not two separate tools. Merged, in dependency order:

```
                    Mork.ttl ─────┐
                                  ▼
                        S1  mtp.facts          terms, axioms, logical fingerprints
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                    ▼
        L0 doctrine.yaml   S3 partition.yaml     S2 corpus (mork/examples/**)
        (anchors, pairs,   (term -> lens,              │
         ladder)           exhaustive/disjoint)         │ predicate frequency,
              │                   │                     │ co-occurrence, unused codes
              ▼                   │                     │
        L0 render  ──► out/l0.*   │                     │
        (kernel, pairs,           │                     │
         output contract)        │                     │
                                  ▼                     │
                    S4 cassette fidelity ◄───────────────┘
                    (real mork/examples/*.ttl → hand-written MCN,
                     decode ≅ source, via mcn.decode + isomorphism)
                                  │
                                  ▼
                    S5 minimise (ddmin to teaching core, lint-clean)
                                  │
                                  ▼
                    S6 mutate (drop/swap/retype/both-directions operators)
                                  │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                caught-by-decode/     silent (nothing downstream
                lint/shacl/owl         catches it -- teaching priority)
                        │                   │
                        ▼                   ▼
              S12 diagnostics.json    lens SMELLS + constraints.ttl gap report
              (repair-loop table)             │
                        │                     ▼
                        │             S8 lens render ──► out/lenses/L-*.txt
                        │                     │
                        │                     ▼
                        │             S9 cassette render ──► out/cassettes/C-*.txt
                        │                     │
                        └──────────┬──────────┘
                                   ▼
                         S10 routing.yaml (task/signal -> lens+cassette)
                                   │
                                   ▼
                         S13 manifest (hashes, budgets, mtp-version)
```

`S7 select`, `S11 eval`, and the eval half of `S12`/`S13` from the L2 sketch's own pipeline table are the parts this plan defers (§2.2); everything else is in scope.

---

## 5. Repository layout

Following the existing convention in this repository (`mork_communities/` is a pure-code package; `mork/test/data/` sits beside the code that consumes it, not inside it):

```
mork/
  src/python/
    mtp/                        # pure code, mirrors mork_communities/ layout
      __init__.py
      facts.py
      ce.py
      codebook.py                # thin: imports mcn_codebook, does not parse a YAML
      doctrine.py
      template.py
      budget.py
      render.py
      lock.py
      corpus.py
      partition.py
      mcnio.py
      mcnline.py
      mutate.py
      minimise.py
      cassette.py
      lens.py
      routing.py
      cli.py
      evalset.py                 # stubbed only; real implementation is Phase 7
  mtp/                          # generated + curated non-code artefacts
    data/
      config.yaml
      doctrine.yaml               # curated
      partition.yaml              # curated
      lenses/L-*.yaml              # curated
      cassettes/C-*.yaml           # curated
      routing.yaml                 # curated (src)
      pins.lock.json               # generated, committed
    out/                         # generated, committed -- the shipped pack
      l0.txt  l0.json  pairs.md  output_contract.txt
      lenses/L-*.txt  lenses/L-*.json
      cassettes/C-*.txt
      routing.yaml
      diagnostics.json
      manifest.json  coverage.md  partition.md  stats.md
```

The current root layout adds these integration surfaces around that MORK-local layout:

```text
lattice/
    mise.toml                       # tool versions, shared environment, MTP task aliases
    .github/workflows/platform.yml  # repository CI, extended with MTP structural checks
    workers/                        # optional graph-reference worker wrappers only
    contracts/mork/                 # only cross-runtime MTP payload schemas, if introduced
    docs/adr/                       # MTP boundary and curation decisions
    docs/architecture/              # cross-programme MTP integration explanation
    docs/developer/                 # MTP validation handoff and consolidated handover
    mork/
        src/python/mtp/               # MTP generator implementation
        mtp/data/                     # curated inputs
        mtp/out/                      # generated and committed pack output
        docs/                         # MTP domain and implementation guides
```

Do not move existing `mork/src/python/mcn_decoder.py`, `mcn_codebook.py`, `mcn/`, `Mork.ttl`, examples, or shapes into the MTP package. The MTP package consumes them through the interfaces named in this plan.

**Decision, not open question:** `mtp/codebook.py` does **not** parse a standalone `codebook.yaml`. The L0 sketch proposed one specifically so that "codes never diverge from the notation" — but `mcn_codebook.py` already *is* that single source of truth for the notation (it generates MCN spec §8 directly), and it was extended in the prior session with exactly the reverse-lookup surface (`code_for`, `codes_for`) the sketch's own `Codebook.code_for`/`codes_for` re-implement. `mtp/codebook.py` becomes a thin adapter:

```python
# mtp/codebook.py
import mcn_codebook as _cb

def code_for(iri: str) -> str | None: return _cb.code_for(iri)
def codes_for(iris) -> list[str]: return _cb.codes_for(iris)
def expand(curie: str) -> str: return _cb._expand(curie)
prefixes = _cb.PREDECLARED_PREFIXES
```

This removes one whole input (I2 in the L2 sketch's table, and `data/codebook.yaml` in L0's layout) and one whole class of drift (YAML vs. `Mork.ttl` vs. MCN spec — now just `mcn_codebook.py` vs. `Mork.ttl`, which `TestCodebookCoverage` already guards in the decoder's own test suite). `config.yaml` drops its `codebook:` key accordingly.

---

## 6. Interfaces already locked

These were built specifically so this plan would not need to design an adapter layer. `mtp/mcnio.py`'s `InProcessTool` becomes a direct, no-impedance wrapper:

```python
import mcn

class InProcessTool:
    def __init__(self, shapes_path):
        self._shapes = Graph().parse(shapes_path, format="turtle")

    def decode(self, text: str) -> DecodeResult:
        try:
            g = mcn.decode(text)
        except mcn.McnSyntaxError as e:
            return DecodeResult(False, None, (Diagnostic("decode", e.code, e.line_no, str(e)),))
        return DecodeResult(True, g, ())

    def lint(self, g) -> tuple[Diagnostic, ...]:
        return tuple(Diagnostic("lint", f.code, f.line, f.message, f.severity) for f in mcn.lint(g))

    def shacl(self, g) -> tuple[Diagnostic, ...]:
        ...  # pyshacl against mork/shapes/constraints.ttl, unchanged from the sketch

    def encode(self, g, hints):
        return None  # not implemented; callers already check via getattr
```

No `_err_code(e)` message-sniffing (the sketch's own placeholder for a problem that didn't have a real answer yet): `McnSyntaxError.code` is a stable slug on every one of the decoder's 127 raise sites, namespaced by sub-parser (`lex-*`, `ce-*`, `swrl-*`, `shacl-*`, `rml-*`, `expr-*`, `core-*`). `LintFinding.code`/`.severity`/`.line` mirror the same shape. `graphs_equal()` (the sketch's isomorphism-modulo-`NamedIndividual` helper) is the exact technique `test_mcn_decoder.py` already uses for the two seed cassettes.

What is **not** locked, because it is genuinely new surface this plan introduces:

- `diagnostics.json`'s schema (one row per `code`, populated from `mcn.McnSyntaxError.code` and `mcn.LintFinding.code` values plus a doctrine fragment) — defined in Phase 5.
- The naming-policy extension to `@u` profiles that LLM Training.md §6c asks for. **Recommendation:** keep this at the MTP tooling layer as a sidecar YAML keyed by profile name (`mtp/data/config.yaml` or a `naming-policies.yaml`), not as a new field on `mcn_decoder.Profile`. It is prompt-engineering metadata (id conventions, minted-name patterns) with no decode-time meaning; growing the core `Profile` dataclass for it would blur a boundary the decoder currently keeps clean. If a future need makes this awkward, revisit.

---

## 7. Doctrine content carried over from the reconciliation section

The L2 document's "Verdict" section resolves five conflicts between the essay and a separate convergence-theorem design. Three are pure doctrine/kernel-wording changes with no dependency on the deferred testing work, and belong in this plan's Phase 1:

- **R1, confidence-channel contamination.** `weighting`/`llmConfidence` stay reserved for domain confidence. Notation uncertainty ("I don't know if this is `ap` or `cb`") is expressed only through the CURIE escape plus a note, never by lowering `weighting`. Add this as an explicit invariant-8-style line in `doctrine.yaml`, distinct from invariant 6.
- **R2, budget and prompt-cache ordering.** The resident prefix order is `[frozen pack][profile][lenses][cassettes][task]`, retrieved context always last. This is already L0's design; state it as a hard constraint in `render.py`'s section ordering and in `cli.py`'s output, so a future retrieval integration cannot quietly interleave.
- **R3a, three typed emission positions.** Replace the kernel's single CURIE-escape clause with the code-position / reference-position / minting-position distinction (§ "Remediation" 3a in the sketch). This is a `doctrine.yaml` wording change only.

R3b–e (retrieval manifest, the two new Meta-SHACL shapes for reference-groundedness and minting-hygiene) belong to the *other* system (the domain/community-detection side that owns retrieval), not to MTP's build — noted here so the dependency is visible, not designed. R4 and R5 are eval-metric design and are deferred with the rest of §2.2.

---

## 8. Full implementation plan

### Cross-phase delivery requirements

Apply these requirements to every phase below:

- Add a concise ADR when the phase creates a durable package, ownership, curation, pinning, backend, or cross-runtime boundary.
- Add or update an architecture guide explaining data flow, generated-file ownership, trust boundaries, failure modes, and deferred dependencies.
- Add a phase handoff under `docs/developer/` that names sources, curated inputs, generated outputs, exact `mise`, Python, CI, and any worker commands, expected results, lockfile impact, and unverified assumptions.
- Add tests that do not invoke an LLM backend. Model-output scoring remains deferred, but generator correctness and generated-pack consistency are not optional.
- Preserve the repository SPDX convention for all new files.

### Phase 0 repository integration

Phase 0 must add scoped MTP task aliases to root `mise.toml`, for example `check:mtp` and `build:mtp`, once the package exposes a CLI. It must add a MTP CI job or step to `.github/workflows/platform.yml` after the package is importable. Do not run dependency installation, code generation, or CI commands in a restricted authoring environment and claim success.

## Phase 0, foundation

Deliverables:

1. `mork/src/python/mtp/` package scaffold (`__init__.py`, empty modules per §5).
2. `mtp/facts.py` — ontology extraction from L0 sketch §3: `Term`/`Axiom`/`Facts` dataclasses, `term_hash` (logical-predicate fingerprinting), `graph_hash`, axiom extraction (GCIs, `AllDisjointClasses`/`Properties`, equivalences, completeness axioms, the P1–P10 inverse-subproperty pattern).
3. `mtp/ce.py` — OWL class expression → MCN §10.5 rendering, from L0 sketch §4, with `install_abbrev()` fed by `mtp.codebook.code_for`.
4. `mtp/codebook.py` — the thin adapter over `mcn_codebook` described in §5, **not** a YAML loader.
5. `mtp/template.py`, `mtp/budget.py` — unchanged from L0 sketch §8.
6. `mtp/lock.py` — `pins.lock.json` read/write/diff.
7. `mtp/mcnio.py` — the adapter from §6, `InProcessTool` only (no `NullTool` fallback needed for decode/lint/shacl since the decoder is not hypothetical; retain a minimal `NullTool` shape purely for `encode()`'s absence).
8. `mork/mtp/data/config.yaml` (no `codebook:` key; ontology file points at `mork/spec/Mork.ttl`; shapes at `mork/shapes/constraints.ttl`).

Exit criteria:

- `python -m mtp.cli facts-report` (or equivalent smoke entry point) prints term/axiom counts against the live `Mork.ttl` with no errors.
- `mtp.facts.term_hash` is stable across two runs and changes only when a logical predicate changes (add a fixture: touch `skos:definition` on a term, confirm the hash is unchanged; touch `rdfs:domain`, confirm it changes).
- `mtp.mcnio.InProcessTool().decode(...)` round-trips the loan example exactly as `test_mcn_decoder.py` already proves — this is a smoke check that the adapter is wired correctly, not new proof of decoder correctness.
- Root `mise.toml`, CI, MTP architecture documentation, and the Phase 0 MTP handoff name the authoritative command path and generated-file rules.

## Phase 1, L0 kernel generator

Deliverables:

1. `mork/mtp/data/doctrine.yaml` — curated: preamble, 7 essay invariants plus the R1/R3a additions from §7, the 6-question decision ladder, the 12-row minimal-pair table, the output contract (including R3a's three emission positions), and `deferrals:` entries pointing generative/collection/objectification completeness axioms at their lenses.
2. `mtp/doctrine.py` — anchor resolution, pin checking, axiom-coverage checking, from L0 sketch §7.
3. `mtp/render.py` — `build_context` (derived slots: box families, exact/category code lists, annotation/deprecated code lists, inverse-pair count, generative mandatory-parts summary) and `render_l0`, from L0 sketch §9.
4. `mtp/cli.py` commands `build`, `check`, `update-pins` (L0 sketch §10), **without** the `eval-report` step.
5. CI wiring: `check` (drift + budget + staleness) then `build` then `git diff --exit-code out/`.
6. ADR and architecture documentation for MTP pin ownership, doctrine curation, and generated output boundaries.

Exit criteria:

- `mtp build` produces `out/l0.txt` within the 900-token budget, byte-identical on a second run with no ontology change.
- Every anchor in `doctrine.yaml` resolves and is pinned; `mtp check` exits 0 against the current `Mork.ttl`.
- Every GCI, `AllDisjointClasses`/`Properties`, mapping-class equivalence, and completeness axiom in `Mork.ttl` is claimed by a `covers:` entry or a `deferrals:` glob — `axiom.unowned` produces zero findings.
- Manually verify the failure-mode table in L0 sketch §12 against this repository's actual `Mork.ttl`: pick one real term, deprecate it in a scratch copy, confirm `anchor.deprecated` fires naming the right pair.

## Phase 2, corpus and partition

Deliverables:

1. `mtp/corpus.py` — frequency/co-occurrence/unused-code statistics over `mork/examples/**/*.ttl`, from L2 sketch §5.3.
2. `mork/mtp/data/partition.yaml` — curated term→lens assignment rules (subtree/glob/explicit/overrides), from L2 sketch §5.4, covering the nine lenses named in LLM Training.md §4.
3. `mtp/partition.py` — `build()`/`check_pins()`.
4. `out/stats.md`, `out/partition.md` generation wired into `cli.py`.

Exit criteria:

- Every `mork:`-namespaced term in `Mork.ttl` is assigned to exactly one lens; `partition.empty`/`partition.unknown-lens` produce zero findings.
- `stats.md` correctly identifies the corpus's most- and least-frequent predicates (spot-check against a manual count on 2–3 example files).
- The "never used in corpus" list is non-empty and plausible (expect entries like `narrowNavigableConceptRole`, `collectionElementScalarValue`) — this list directly drives lens/cassette budget decisions in Phase 4.

## Phase 3, mutation-derived ground truth

Deliverables:

1. `mtp/mcnline.py` — structural (non-semantic) tokeniser/mutator for MCN node lines, from L2 sketch §5.2. Deliberately independent of `mcn_decoder.py`'s `_Lexer`.
2. `mtp/mutate.py` — `Mutation`/`MutantOutcome`, and the six seed operators named in L2 sketch §8 build order: `drop:df`, `drop:xr`, `swap:cb->ap`, `swap:df->dp`, `retype:MU->M`, `both:cb+cn`.
3. `mtp/minimise.py` — ddmin-to-teaching-core, from L2 sketch §5.6.
4. `mtp/cassette.py` — fidelity check (real corpus file → hand-written MCN → `mcn.decode` → isomorphic to source), minimisation, rendering. First three cassettes come directly from `mork/examples/Mork2RML/loan_mapping.ttl` and `mork/examples/Zoo/UncertainMappings.ttl` — files this plan already has machine-checked gold MCN for (§3), so Phase 3 starts with zero fidelity-proof debt on those two.

Exit criteria:

- Running the six seed operators against the three seed cassettes produces a mutation matrix with at least one `caught-*` and, per the L2 document's own expectation, likely at least one `silent` verdict.
- The silent-set report (L2 sketch: "the most valuable output in the whole design") is generated and reviewed by a human before Phase 4 starts — per L2 §8, this step alone will likely surface a real gap in `mork/shapes/constraints.ttl` and should be filed as a follow-up against that file rather than silently absorbed into a lens.
- `cassette.not-isomorphic` and `cassette.decode-failed` gates both produce a genuine failure when deliberately fed a broken fixture, confirming the gate actually fires.

## Phase 4, lenses

Deliverables:

1. `mork/mtp/data/lenses/L-*.yaml` for all nine lenses (`L-REP`, `L-TAX`, `L-IND`, `L-GEN`, `L-TPL`, `L-INT`, `L-EGR`, `L-UNC`, `L-TBX`), each following the fixed template from LLM Training.md §4: Question → Rules → Mandatory co-occurrences → Smell tests → Lint codes it prevents → cassette pointer.
2. `mtp/lens.py` — rendering, deriving `MUST CO-OCCUR` rows from completeness axioms and `CAUGHT`/`NOT CAUGHT` lines from the Phase 3 mutation matrix.
3. Write order: `L-IND` and `L-GEN` first (highest corpus frequency and highest error surface per L2 §8 point 6), then the remaining seven, each backed by the corpus frequency data from Phase 2.

Exit criteria:

- Every lens has at least one cassette (`lens.no-cassette` produces zero findings).
- `lens.silent-unaddressed` produces zero findings: every mutation the Phase 3 matrix marked `silent` is either addressed by a `SMELLS` entry in some lens or has a filed gap report against `constraints.ttl` (not both silently dropped).
- Each lens fits its per-lens budget (300–800 tokens).

## Phase 5, routing and repair table

Deliverables:

1. `mork/mtp/data/routing.yaml` (src) — the static task/signal → lens+cassette table sketched in LLM Training.md §4.
2. `mtp/routing.py` — compiles src routing into `out/routing.yaml`, reachability check.
3. `out/diagnostics.json` (S12) — one row per `code` value observed from `mcn.McnSyntaxError`/`mcn.LintFinding` across the Phase 3 mutation runs and the L0 axiom-coverage report, each paired with a ≤40-token doctrine fragment per LLM Training.md §5's table.

Exit criteria:

- `routing.unreachable` produces zero findings: every lens is reachable from at least one task/signal combination.
- `diagnostics.json` has an entry for every lint `code` currently defined in `mcn_decoder.py` (`lint()`'s twelve rules) and for the decode-time `code`s that showed up as `caught-decode` verdicts in Phase 3 — not necessarily every one of the 127 raise-site codes, since most of those are basic well-formedness the CURIE-escape/grammar already prevents a disciplined generator from hitting; prioritise by what Phase 3's mutations actually produced.
- Hand-verify 2–3 `diagnostics.json` rows read naturally as the LLM Training.md §5 table's own worked examples (`ap` without `xr`/`xi`, `MD` without `df`, `MS` missing `pv`).

## Phase 6, errata pipeline and deployment profile

Deliverables:

1. Errata card (L4 tier) governed as its own artefact: creator/created/review-status/`supersedes`, per LLM Training.md §6d and the L2 reconciliation section's "errata card is structurally the projection matrix" point. Format: a small MORK-shaped record (reuse `fnd:` governance vocabulary already in `Mork.ttl`'s Foundation import), capped at 600 tokens, human- or offline-LLM-compacted from lint/SHACL telemetry.
2. Naming-policy sidecar (§6) keyed by `@u` profile name: id conventions, minted-name patterns, chosen `@t` — the mechanism that keeps `Map_Loan` spelled `Map_Loan` across runs, which LLM Training.md §6c calls out as a real requirement no amount of model memory satisfies.
3. Provenance record shape: `mtp-version`, `profile-hash`, `model-id`, `lenses-loaded` — one record per proposal, per LLM Training.md §7. Defined here as a data shape; **not** wired into any live pipeline yet, since that requires the backend interface (§2.2).

Exit criteria:

- A worked example: hand-construct one errata entry from a hypothetical recurring mistake, show it renders into L4 within budget, and show it is reviewable/revertible (has a governance state, is not silently auto-applied).
- The naming-policy sidecar format is documented with one example profile.

## Phase 7, deferred (not built now — recorded so the handoff is clean)

This phase is intentionally left as a stub. It resumes once the LLM-backend interface exists:

1. `mtp/evalset.py` and `out/eval/*.json` — the held-out task suite (LLM Training.md §7).
2. `eval-report` CI step; `eval.leakage`/`eval.thin` gates.
3. First-pass lint-clean rate, tokens-per-decoded-triple, semantic F1, unsafe-confidence rate scoring.
4. ρ(t) stratification by `mtp-version` (L2 reconciliation R4) and the human-Stage-5-decision companion metric for repair-loop investment (R5).
5. Grammar/tool-schema compilation target (GBNF or structured-output schema, generated from `mcn_codebook.py`) — technically backend-independent, but sequenced here because it is only useful once there is an eval harness to prove it "kills the syntax error class outright" (LLM Training.md §6e).
6. Retrieval index and SFT/LoRA corpus compilation targets (LLM Training.md §6e) — explicitly named as optional accelerants in the source design; both depend on decisions the backend-interface effort owns.
7. R3b–e (retrieval manifest, Meta-SHACL groundedness/minting-hygiene shapes) — owned by the domain/community-detection system, tracked here only as a dependency.

No exit criteria: this phase is not started by this plan. It is scoped here purely so whoever picks it up does not have to re-derive the boundary in §2.2.

---

## 9. Gates: in scope vs. deferred

| Gate | Phase | In scope |
|---|---|---|
| `codebook` term-not-declared / deprecated | 0 | yes |
| `anchor.missing` / `anchor.deprecated` | 1 | yes |
| `pin.absent` / `pin.changed` | 1 | yes |
| `axiom.unowned` / `axiom.unlabelled` | 1 | yes |
| `budget` (L0 total, per-section) | 1 | yes |
| `output.stale` | 1 | yes |
| `partition.empty` / `unknown-lens` / `unpinned` / `membership-changed` | 2 | yes |
| `cassette.not-isomorphic` / `decode-failed` | 3 | yes |
| `cassette.minimise-broke-focus` / `mutation-inapplicable` | 3 | yes |
| `cassette.silent-mutation` / `lens.silent-unaddressed` | 3–4 | yes |
| `lens.no-cassette` / `cassette.claim-uncovered` | 4 | yes |
| `routing.unreachable` | 5 | yes |
| `budget.lens` / `budget.cassette` | 4 | yes |
| `adapter.absent` | — | not needed; `InProcessTool` is unconditional now |
| `eval.leakage` / `eval.thin` | 7 | **deferred** |
| eval-report regression check | 7 | **deferred** |

---

## 10. Repository change plan by area

### 10.1 `mork/src/python/mtp/` (new package)

All files listed in §5 and §8. Depends on `mcn_decoder.py`/`mcn_codebook.py` only through the `mcn` package and `mtp/codebook.py`'s thin adapter — no changes to those modules are required by this plan.

### 10.2 `mork/mtp/` (new top-level directory)

`data/` (curated, hand-authored + generated `pins.lock.json`) and `out/` (fully generated, committed) as laid out in §5.

### 10.3 `mork/shapes/constraints.ttl`

Not modified by this plan directly, but Phase 3's silent-set report is very likely to file follow-up items against it (per L2 §2's own framing: "it will very likely surface gaps in `constraints.ttl` on first run"). Track those as separate, ordinary issues against that file — this plan does not pre-authorize changes to it.

### 10.4 CI

Add scoped steps to the existing repository workflow [platform.yml](../../.github/workflows/platform.yml), preserving the existing MORK decoder and compiler checks. The final commands are invoked through `mise` locally and may run directly in CI after Python setup:

```yaml
- run: python -m mtp.cli check --out mork/mtp/out
- run: python -m mtp.cli lens-check --out mork/mtp/out
- run: python -m mtp.cli build --pack-version ${{ github.ref_name }} --out mork/mtp/out
- run: git diff --exit-code mork/mtp/out/
```

No `eval-report` step (§2.2).

Add these only after the relevant MTP phase creates the command. CI must install the MORK package or set the package import path explicitly. No `eval-report` step is added (§2.2). Any dependency or generated-output lockfile change is reported and reviewed, not silently committed by CI.

### 10.5 `mise` tasks

When the MTP CLI exists, add tasks equivalent to:

```toml
[tasks."check:mtp"]
run = "python -m mtp.cli check --out mork/mtp/out"

[tasks."build:mtp"]
run = "python -m mtp.cli build --out mork/mtp/out"
```

`check:mtp` becomes a dependency of the root `check` task only after all required curated data and generated output exist. `build:mtp` is intentionally separate from generic bootstrap because it changes committed generated content.

---

## 11. Acceptance criteria (structural, not model-quality)

Per §2.2, these criteria are about the pack's own internal consistency, not about how well a model performs against it — that is Phase 7's concern.

- `mtp build` succeeds with zero errors against the current `Mork.ttl` and produces a pack within all stated token budgets.
- `mtp check` in CI catches: a term added to `Mork.ttl` with no code, a logical-axiom change to an anchored term with a stale pin, a new GCI with no owner, a new lens-eligible term with no partition rule, a corpus example edited such that its cassette is no longer isomorphic.
- Every cassette's MCN, decoded via `mcn.decode`, is graph-isomorphic (modulo `owl:NamedIndividual`) to its cited source.
- `diagnostics.json` and the lenses' `CAUGHT`/`NOT CAUGHT` lines are derived from the same mutation matrix (no hand-maintained duplication that can drift).

---

## 12. Risk register

| Risk | Mitigation |
|---|---|
| `doctrine.yaml` curation (Phase 1) is the one genuinely human-judgement-heavy step and could stall the whole plan | Scope it to the essay's existing draft (LLM Training.md §2) plus the three §7 additions; do not open-endedly rewrite it during Phase 1 |
| Corpus (`mork/examples/**`) is small; frequency stats and "never used" lists may be noisy | Explicit in L2 §5.3 already; treat early stats as provisional, re-run once more real mapping schemes exist |
| Mutation operators (Phase 3) might find far more `silent` findings than anticipated, each implying a `constraints.ttl` follow-up | Time-box Phase 3 to the six seed operators only; do not expand the operator set until the resulting silent-set backlog is triaged |
| `mtp/codebook.py`'s thin-adapter decision (§5) assumes `mcn_codebook.py`'s reverse index never needs per-consumer customisation | If a real need for divergent behaviour appears, revisit — but do not pre-build flexibility for a need that has not materialised |
| Phase 6 (errata governance) has no concrete deployment yet to draw real telemetry from | Deliverable is the *shape* and one worked example, not a populated card; this is intentional |

---

## 13. Sequencing and immediate next actions

Phases 0–2 have no dependency on each other's outputs beyond Phase 0's shared infrastructure, and could run in parallel if more than one person is available; Phases 3–6 are strictly sequential as written (each depends on the previous phase's output).

Immediate next actions:

1. Read [the consolidated repository handover](../../docs/developer/implementation-handover.md), [toolchain guide](../../docs/developer/toolchain.md), [implementation map](../../docs/architecture/implementation-map.md), and the MORK ADR catalogue before adding MTP code.
2. Create the Phase 0 MTP ADR, architecture guide, and validation handoff alongside the `mork/src/python/mtp/` scaffold and `mork/mtp/data/config.yaml`.
3. Add scoped `mise` and CI wiring only when the first importable MTP command exists. Do not claim that `mise run check:mtp` passed until the network-enabled validation environment has installed dependencies.
4. Build `mtp/facts.py`, `mtp/ce.py`, and `mtp/mcnio.py` against the live MORK sources. Keep decoder and codebook changes out of scope unless a separately documented interface gap is discovered.
5. Draft `doctrine.yaml` only after `facts.py` can resolve and fingerprint anchors. Record the curation and generated-output rules in the phase ADR and architecture guide.

---

## 14. Definition of done for this plan's scope

- Phases 0 through 6 complete, all exit criteria in §8 met.
- `mork/mtp/out/` is committed, current, and reproducible byte-for-byte from a clean `mtp build`.
- Phase 7 is recorded as an explicit stub with its dependency on the backend-interface effort stated, not silently dropped or half-started.
- No change made to `mcn_decoder.py` or `mcn_codebook.py` in the course of this work beyond what already exists (§6) — if Phase 0 or 1 discovers a genuine gap in that interface, it is raised as its own decision, not patched in passing.
- Each implemented MTP phase has an ADR where it establishes a durable boundary, an architecture guide, a developer handoff, structural tests, CI wiring, and explicit authoring-complete versus validated-complete status.
- The final MTP handover is linked from [docs/developer/implementation-handover.md](../../docs/developer/implementation-handover.md) and identifies Phase 7's dependency on the LLM backend interface.
