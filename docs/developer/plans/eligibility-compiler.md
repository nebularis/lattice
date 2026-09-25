<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Eligibility Executable Compiler — Verification and Test-Infrastructure Plan

**Unit ID:** `eligibility-compiler`
**Status record:** [eligibility-compiler.md](../status/eligibility-compiler.md)
**Sketch:** [mork-eligibility-compiler.md](../sketches/mork-eligibility-compiler.md)
**Governing ADRs:** [ADR-A23](../../architecture/decisions/ADR-A23-mork-compiler-family-completion-policy.md) (compiler family completion policy), [ADR-A24](../../architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md) (backend strategy — SPARQL/SHACL native-and-first, SHACL readiness second, SWRL positive-only third)
**New ADR proposed by this plan:** ADR-A83 (below). Renumbered from A81 on 2026-09-23: A81 is the Control Plane HTTP runtime ADR, filed first

## 0. Why this plan exists

The status record's "Verification Plan (not yet executed)" lists five steps. Steps 1–4 are ordinary test execution against dependencies the repository already has (`rdflib`, `pyshacl`) or none at all. Step 5 is not:

> 5. Load generated SWRL into Drools/Pellet and confirm inference

Pulling a JVM-based OWL/SWRL reasoner (Pellet) and a JVM rules engine (Drools) onto the path anyone runs to build or test the eligibility compiler — or worse, onto the path anyone runs to build or test *anything* in this repository — is not acceptable. Neither tool is needed to compile a SWRL artefact, only to independently verify one, and that verification need is legitimate and recurring: this is the first compiler backend that emits SWRL, but ADR-A19's staged-compiler-architecture and ADR-A23's completion policy both anticipate more backends across more compiler families, and the platform epic's own P2.2.5 ("SHACL report equivalence across engines") names exactly this kind of cross-engine verification need again in a completely different component.

This plan therefore has two parts, not one. **Part A** executes the five-step verification plan as slices. **Part B** — the important part — designs a shared, test-only, reasoning/rules-engine dependency so Part A's step 5 (and every future need like it) never touches the main dependency graph.

## Part A — Execute the verification plan

| Slice | Scope | Depends on |
|---|---|---|
| **A1** | Run `python -m unittest mork_compilers.test_mork_compilers -v` in a real Python 3.14 environment (the repository floor since 2026-09-23); fix anything that fails | None |
| **A2** | Parse `ontology/mork/spec/Executable.ttl` with Eligibility imported, under plain `rdflib`/`riot`-equivalent parsing first (syntax), then under an OWL DL reasoner for consistency (semantics) — see Part B for which reasoner | Part B's reasoner choice (for the DL-consistency half only; plain parsing has no dependency) |
| **A3** | Execute `sparql_backend.compile_query_template()`'s generated SPARQL against `ontology/eligibility/examples/interval-containment.ttl` using `rdflib`'s own SPARQL engine (already a normal dependency of `tools/mork_compilers`, no new dependency of any kind) | None |
| **A4** | Validate generated SHACL with `pyshacl` (already precedented as a `test`-extra dependency in `tools/persistence`, pure Python, no licensing or JVM concern) against two new fixtures this slice authors: a missing-candidate case and an out-of-range-candidate case | None |
| **A5** | Load generated SWRL into the chosen reasoner (Part B) and confirm inference fires for a positive case and correctly does *not* fire for a case outside the required interval | Part B complete |

Each slice follows the mandatory shape from copilot-instructions: code (or in A1–A4's case, fixtures and a fixed/confirmed test run), a Validation Pack at `docs/developer/validation/eligibility-compiler-<slice>.md`, a traceability update in `docs/developer/INDEX.md`, and a doc delta to [eligibility-compiler.md](../status/eligibility-compiler.md) recording the result.

A2's OWL-reasoner half and A5 do not start until Part B's shared harness exists and its engine choice is ratified.

## Part B — Test-only reasoning/rules-engine dependency strategy

### B.1 Constraints

1. No product package (`tools/mork_compilers`, any future compiler family, any `platform/*` module) may declare a runtime or default dependency on an OWL/SWRL reasoner or a rules engine.
2. The dependency must be **shared**, not re-solved per compiler family. The user has flagged that other units will need reasoning/rules engines for testing — building a second bespoke Pellet-wrangling harness the next time this comes up is the failure mode this part exists to prevent.
3. It must be usable from Python test suites (`tools/mork_compilers` today) and from Java test suites (the platform epic's `platform/reasoning-validation`, `P2.2.5`'s SHACL-engine-equivalence work, tomorrow) without forcing either ecosystem to adopt the other's package manager.
4. It must respect "own dependency authority per ecosystem" (copilot-instructions: "Maven, Yarn 4, Python project tooling... remain their own dependency authorities") — so the shared piece cannot be a Python package that vendors a JVM under the hood as its only integration method, which is what libraries like `owlready2` do (they bundle or silently fetch a Java reasoner at import time, outside Maven's or `mise`'s visibility).

### B.2 Why this needs an ADR, not just a plan decision

This establishes a repeatable pattern for how the repository isolates any future test-only dependency with licensing, weight, or ecosystem-crossing concerns, not just this one. That is exactly the kind of decision the Design First rule reserves for an ADR. **ADR-A83 (proposed, drafted as Slice B1 below)** — working title: "Test-only reasoning and rules engine isolation." A81 is free (A45–A76 are reserved by the platform epic's own decision slate per its Part 4 P0.1, A77–A80 are filed).

### B.3 Design

**A new Maven module, `platform/reasoning-testkit`, Java 25, `<scope>test</scope>`-only dependencies.** JVM-native tools belong with JVM tooling — Pellet (or its actively maintained fork, see B.4) and Drools are both Java libraries; wrapping them in a thin Java module, rather than reaching for them through a Python-side JVM bridge, keeps the engine versions pinned in exactly one `pom.xml`, keeps them declared with Maven's own `<scope>test</scope>` (so `mvn package` for any real artifact never pulls them in), and gives Java test suites (present and future) a direct, ordinary test-scope dependency with no extra indirection.

The module ships two things:

1. **A library JAR** any Java test suite can add as a `<scope>test</scope>` Maven dependency directly — e.g. a future `platform/reasoning-validation` (C-13, per the platform epic) or `platform/reasoning-testkit`'s own self-tests.
2. **A packaged CLI** (`reasoning-testkit infer --ontology <ttl> [--rules <swrl-or-drl>] --format json`, `reasoning-testkit shacl-check ...`) built as a shaded/executable JAR, so any *non-JVM* test suite — `tools/mork_compilers` today — invokes it as a subprocess and parses JSON off stdout. This is the only integration path Python needs: no Python package ever declares a dependency on Pellet, Drools, or a JVM bridge library. It only needs a JVM on the machine (already true — this repository's own `mise.toml` already pins `java = "21"`) and the built CLI jar.

```
platform/reasoning-testkit/
├── README.md              # states plainly: test-only, never a runtime dependency, see ADR-A83
├── pom.xml                 # Pellet/Openllet + Drools declared <scope>test</scope>, nowhere else
└── src/
    ├── main/java/.../      # the CLI + library surface itself has NO dependency on the reasoners —
    │                       # see B.5, the reasoners are wired in as pluggable engine adapters so the
    │                       # CLI's own compile-scope stays clean and only its test/runtime classpath,
    │                       # assembled at package time for the shaded CLI jar, pulls them in
    └── test/java/.../      # the module's own self-tests, which DO exercise real Pellet/Drools calls
```

### B.4 Engine choice and licence compatibility (researched 2026-09-23, confirm at the ADR-A83 slice)

Per "Pause for Architectural Guidance," the specific engine choice is still a decision for the ADR-A83 slice, not something this plan pre-empts — but the licence question below was resolved by checking primary sources (Openllet's own `LICENSE.txt`, its README, and its published Maven Central POM metadata), not assumed, since an assumption here was wrong in an earlier draft of this plan.

- **Openllet's actual licence is AGPL-3.0**, with a commercial-alternative option, inherited unchanged from Pellet — Openllet is a maintenance fork of Pellet, not a relicense, and carries the identical dual-licence text forward. An earlier draft of this plan stated Openllet was "Apache-2.0-licensed"; that was incorrect and is corrected here.
- **AGPL-3.0 is not directly compatible with MPL-2.0 for a combined/distributed work.** MPL-2.0 §3.3's secondary-licence mechanism reaches GPL/LGPL/AGPL only where the licensor marks a file "Not Incompatible With Secondary Licenses," and that does not change what AGPL itself requires once code is linked or distributed together — including AGPL §13's network-use clause, which extends the copyleft obligation to running the program as a network-accessible service, not just to distributing it.
- **The isolation design in B.3 is what makes Openllet usable here, not incidental to it.** Because Openllet is confined to `platform/reasoning-testkit`, declared in a scope no other module may reference, and reached by every other component (Python or Java) only through an out-of-process CLI subprocess — never linked, compiled against, or bundled into any released artifact — no combined or derivative work is created, and the subprocess/pipe boundary is the paradigm case the FSF's own GPL-family compatibility guidance treats as separate programs. AGPL §13 does not trigger, because nothing here runs Openllet as a network-facing service. **Conclusion: Openllet is usable, conditional on the B.5 guardrail actually being enforced** — the licence leaves no margin for a module quietly acquiring a direct dependency on it later.
- **Lower-risk alternative for the OWL/SWRL half: HermiT (LGPL-3.0).** LGPL is materially weaker copyleft than AGPL — it permits linking from differently-licensed code without extending copyleft to the caller, so HermiT would not strictly need the subprocess-isolation boundary at all. HermiT supports **DL-safe SWRL rules only**, not the full SWRL language. Before choosing between Openllet and HermiT, confirm whether ADR-A24's positive-only, monotonic SWRL subset (the only subset the eligibility compiler ever emits) is DL-safe — if it is, HermiT removes the AGPL question entirely for A2/A5; if it is not, Openllet under the B.3 isolation design is the correct choice.
- **Drools is Apache-2.0.** No compatibility question of any kind. The question of whether Drools is needed at all (a general rules engine, not an OWL/SWRL reasoner) is unchanged from the original assessment: defer its adapter until a real second consumer exists, per YAGNI.

### B.5 Guardrail

**New rule, enforced the same way the platform epic enforces its G-series guardrails:** no `pom.xml` outside `platform/reasoning-testkit` itself may declare a dependency on it in any scope other than `test`, and no `pyproject.toml` anywhere may declare a dependency on an OWL/SWRL/rules-engine package directly (Python test suites reach `reasoning-testkit` only through its CLI subprocess, per B.3, so this is enforceable by grep, not just convention). A CI check (Slice B2, below) makes this real rather than aspirational, following the same "positive fixture / violating fixture, build fails" pattern copilot-instructions already mandates for guardrail slices.

### B.6 Slices

| Slice | Scope | Depends on |
|---|---|---|
| **B1** | Draft and ratify ADR-A83 (engine choice, licence check, isolation pattern). Human validation focus: is the isolation boundary (test-scope Maven + subprocess CLI for non-JVM consumers) actually sufficient, or does some future consumer need direct in-process access this design does not offer? | None |
| **B2** | `platform/reasoning-testkit` module skeleton: `pom.xml` with the ratified engine(s) at `<scope>test</scope>`, CLI entry point, no-op self-test, plus the guardrail CI check (grep-based: no other `pom.xml`/`pyproject.toml` may reference the chosen engine artifacts) | B1 |
| **B3** | Wire the OWL/SWRL engine adapter behind the CLI's `infer` command; self-tests using a trivial fixture ontology, not yet the eligibility compiler's own output | B2 |
| **B4** | `tools/mork_compilers` test suite calls the CLI as a subprocess for A2 (OWL-reasoner consistency half) and A5 (SWRL inference); document the subprocess-invocation pattern in `tools/mork_compilers/README.md` so the next Python package needing this copies a documented pattern, not a bespoke one | B3, A1–A4 |

## Documentation obligations

| Document | Change | Producing slice |
|---|---|---|
| `docs/architecture/decisions/ADR-A83-*.md` | New | B1 |
| `platform/reasoning-testkit/README.md` | New — states test-only status prominently, per B.5 | B2 |
| Root `README.md` | New row/mention for `platform/reasoning-testkit` under whatever module-tree listing already documents `platform/*`, explicit "test-only, not a runtime dependency" note | B2 |
| `tools/mork_compilers/README.md` | New — did not exist as a documented convention before; add install/test commands (`mise run bootstrap:mork-compilers`, `mise run check:mork-compilers` — both proposed new `mise.toml` tasks, mirroring the `tools/persistence` precedent) and the subprocess-invocation pattern from B4 | B4 |
| `mise.toml` | New tasks: `bootstrap:reasoning-testkit` (builds the shaded CLI jar), `check:reasoning-testkit` (module self-tests), `bootstrap:mork-compilers` / `check:mork-compilers` (did not exist before this plan) | B2, B4 |
| [eligibility-compiler.md](../status/eligibility-compiler.md) status record | Updated per-slice as A1–A5 and B1–B4 land, per the Doc Delta rule (edited in the same slice, not deferred) | Each slice |
| `docs/developer/INDEX.md` | Traceability rows for each slice; unit 4's entry updated as Part A/B complete | Each slice, batch-updated now for the plan's existence (see below) |

## Test taxonomy

Per copilot-instructions' L0–L8 table: A1 (L1, unit), A2 syntax half (L1), A2 semantic half and A5 (**L4**, component integration with real infrastructure — the reasoner is exactly the kind of "real infrastructure" Testcontainers-style tests already model elsewhere in this repository, so these run in CI, not on every local fast pass), A3 (L1, `rdflib` in-process), A4 (L1, `pyshacl` in-process), B2's guardrail check (L1, lint-style). None of Part B's slices are L0 build-smoke only — the module's own self-tests genuinely exercise the chosen reasoner.

## Phase gate / acceptance

This unit closes when: all of A1–A5 pass with their VPs signed off; ADR-A83 is ratified; the guardrail check (B2) is green and has a demonstrated violating fixture that fails, per copilot-instructions' adversarial-probe step; [eligibility-compiler.md](../status/eligibility-compiler.md)'s state line changes from "awaiting validation" to a dated, evidenced "Verified."

## Progress (2026-09-25)

B1 to B4 are done. ADR-A83 is Accepted with HermiT as the first engine, and
Drools and Openllet deferred. A2's reasoner half passes after the Mork repairs of
ADR-A97. A5 is verified for the builtin-free rules
([VP](../validation/eligibility-compiler-part-b.md)). Interval rules wait on
an Openllet adapter. The CLI commands differ from B.3's sketch: see the
[module README](../../../platform/reasoning-testkit/README.md).

## Open questions requiring human decision (summary)

1. ~~Openllet vs. HermiT~~: HermiT first (ADR-A83).
2. ~~Drools now or later~~: deferred (ADR-A83).
3. If Openllet is chosen: confirm the B.5 guardrail is treated as load-bearing, not advisory, given AGPL leaves no margin for a module quietly acquiring a direct dependency later (B.4).

## Next steps

1. Human resolves the three open questions above, or delegates that resolution to the ADR-A83 slice (B1) itself.
2. Begin A1–A4 in parallel with B1 — none of the four depend on Part B.
3. B2–B4 and A2/A5 follow once B1 is ratified.
