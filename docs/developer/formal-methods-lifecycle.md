<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods in the Development Lifecycle

How the `formal-methods` epic's tracks hook into every change, at every stage the Epic
Decomposition Model names (`.github/copilot-instructions.md`): sketch, plan, implementation,
validation. For what each track's own tool does mechanically, see the
[Developer Guide](developer-guide.md) §4-§5. For the epic's own scope and tracks, see
[`docs/developer/plans/formal-methods.md`](plans/formal-methods.md).

**Read this before changing a law, wherever it lives** — an ontology's normative prose, a
compiler's behaviour, or a platform service's own protocol guarantee. Not every change needs
every track's attention (§4 is the decision table), but every change should at least ask the
question.

## 1. The four kinds of formal-methods artefact, and what each is for

| Artefact | Home | Answers | When it runs |
|---|---|---|---|
| **Design-time model** (track C) | `tools/models/<name>/` | Does a *proposed* law admit the property an ADR is about to claim, checked over generated instances up to a stated scope? | Before the ADR is accepted — evidence for a decision, not proof of one already made |
| **Mechanised theory** (track E) | `tools/proofs/<layer>/` | Does an *already-accepted* law hold for every instance, proved, not merely checked at a bound? | After the ADR is accepted and the law is stable enough to be worth proving |
| **Reference semantics** (track B) | `tools/reference/<layer>/` | Do every compiler backend's outputs agree with an independent, hand-written restatement of the same already-accepted law? | Continuously — differential tests run in `check`, the same as any other test suite |
| **Ledger and harness** (track A) | `docs/developer/*` (assurance records) | What is every law's current assurance level, and is the release gate's own law report complete? | At release-gate time, across every layer at once |

The difference that matters most: a **design-time model** is evidence for a decision not yet
made; a **mechanised theory** and a **reference semantics** both assume the decision is already
made, and check the *implementation* of it from two different angles (proved once and for all, or
checked empirically against every compiler that reads it).

## 2. The lifecycle, stage by stage

### Sketch

If the sketch proposes a **new** law, or changes an existing one, in a layer with any design
complexity (more than one interacting constraint, a precedence or conflict rule, a relation that
could be read two ways) — **write the design-time model before the sketch is finished**, not
after. Track C exists precisely because a prose sketch can look sound and still admit a
counterexample a relational model finds in seconds: track C2's own model found exactly this (an
undisclosed overlap case in a proposed Vocabulary composition rule), and the finding changed what
the eventual ADR had to decide. A sketch that proposes a law without having tried to break it with
a model is incomplete, not merely informal.

If the sketch does **not** touch a law's substance (a new example, a documentation clarification,
a structural-only constraint SHACL already checks), no track C model is needed — say so in the
sketch, so a reviewer does not have to re-derive that conclusion.

### Plan

A plan that adds or changes a law names, explicitly, in its own dependency table:

- which design-time model (track C) the ADR's evidence rests on, if any, and whether it already
  exists or is a slice of this plan;
- whether the layer already has a mechanised theory (`tools/proofs/<layer>/`) that the change
  must also update, or whether this plan is the first law in that layer worth proving at all
  (most layers are not mechanised yet — that is a track E decision made once per layer, not
  assumed);
- whether the layer has a reference semantics (`tools/reference/<layer>/`) whose law-coverage
  the change will need to extend (the new law must be named there, covered or explicitly
  disclaimed as out of scope — `check:formal-freshness`, §3, enforces this, not merely requests
  it).

A plan that is silent on all three is implicitly claiming none apply — a reviewer should be able
to check that claim, not have to ask for it.

### Implementation

What actually has to change, by what kind of source is being touched:

**An ontology change** (`ontology/<layer>/README.md` and its generated `spec`/`vocab`/`shapes`):
follow `docs/architecture/ontology-versioning-policy.md` in full, as always. If the layer has a
`tools/proofs/<layer>/` directory and the README's `isabelle-spec` block changed, regenerate
`Kernel.thy` (`tools/literate_extract.py --proofs-root tools/proofs`) and re-run that layer's
Isabelle session before committing — a stale `Kernel.thy` is caught by `check:formal-freshness`,
but catching it yourself first is cheaper than a second round trip. If the layer has a
`tools/reference/<layer>/` directory and the README added or changed a semantic law, update the
reference (or its own README's stated scope) in the same change — not a follow-up, since a
generated check already fails the build otherwise.

**A tools codebase change** (a compiler backend, a resolver, any package under `tools/`): if the
package reads a layer with a reference semantics (today, Eligibility's `tools/mork_compilers`),
the differential tests (`check:reference-eligibility`) are the primary formal-methods hook — a
behaviour change that disagrees with the independent reference fails there, not silently. If the
disagreement is the compiler's bug, fix the compiler. If it is a finding that the reference itself
was wrong or incomplete, fix the reference, with the same differential evidence recorded (track
B2's own two findings, in `docs/developer/status/formal-methods-track-b.md`, are the worked
examples of exactly this).

**A platform service change** (`platform/`, workers, apps): **not covered by any track today.**
This is a real gap, not an oversight to paper over — the epic's own track G (instrument assurance)
and the protocol-level verification named in `sketches/formal-methods.md` §8.9 (TLA+/Quint models
for the outbox, idempotent delivery, optimistic concurrency) are both still at the sketch level,
unbuilt. A platform change today is validated the way it always was (`check:java`, `check:workers`,
`check:frontend`), with no additional formal-methods hook yet. If you are the one building track G
or the protocol models, this section is what you are closing.

### Validation

A slice's Validation Pack (`docs/developer/validation/<slice-id>.md`) that touches a law states,
in its own invariant paragraph, which of the three artefacts above it engages, and cites the
actual command (`mise run check:formal-freshness`, `mise run check:proofs <layer>`, `mise run
check:reference-eligibility`) a human can re-run — the same "one command to run everything"
discipline every Validation Pack already requires, not a formal-methods exception to it.

## 3. The one command that catches drift automatically

`mise run check:formal-freshness` (`tools/check_formal_freshness.py`) runs in the default `check`
aggregate (unlike the heavier `check:proofs`, which needs a native Isabelle install) and checks,
for every layer that has the relevant artefact:

- its mechanised theory's `Kernel.thy` still matches the README's `isabelle-spec` block, byte for
  byte;
- every semantic law the README declares is named somewhere in that layer's reference semantics,
  covered or explicitly disclaimed.

This is the automatic half of §2's implementation discipline — it catches a README changed
without its downstream artefact, but it cannot catch a *new* law that should have had a
design-time model and didn't, or a platform change that should have started track G. Those are
review-time judgements this document exists to prompt, not something a script can enforce.

## 4. Decision table: does this change need which track?

| The change | Track C (model) | Track E (proof) | Track B (reference) |
|---|---|---|---|
| A new or changed law, any layer, with any interacting constraint | **Yes, before the ADR** | Only if that layer already has a mechanised theory, or this is the law that starts one | Only if that layer already has a reference semantics, or this is the law that starts one |
| A structural-only constraint SHACL already checks fully | No | No | No |
| A compiler backend change, same layer's existing laws unchanged | No | No | Differential tests re-run regardless — no plan action needed beyond `check` passing |
| A platform service or protocol change | Not yet — track G's own job, unbuilt | No track exists | No track exists |
| A new ontology layer's very first formalised law | Track C first if the law is non-trivial | Track E's own decision, once per layer (not every layer needs one) | Track B's own decision, once per layer |

## 5. Where each track actually is today

Concrete, not aspirational — check `docs/developer/status/formal-methods.md` for the current
state before assuming a track covers a layer it does not yet:

- **Track E**: Eligibility only (`tools/proofs/eligibility/`), laws TA1/TA2 (the kernel) and
  TL1-TL3 (set readings and negation).
- **Track B**: Eligibility only (`tools/reference/eligibility/`), laws L9-L12 and L14-L16.
- **Track C**: one model, `tools/models/vocabulary-scheme-composition/` (Vocabulary scheme
  composition, ADR-A116).
- **Track A, F, G**: not started.

Every other layer's laws are checked today exactly as they were before this epic: SHACL shapes,
example fixtures, and review. That is not a weaker guarantee by default — it is today's actual
assurance level, and track A's own law report (once built) is where that level is stated for
every law explicitly, rather than left to be inferred.
