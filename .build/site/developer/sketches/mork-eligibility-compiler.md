<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Eligibility executable compiler: scope and design record

Date: 2026-09-18
Status: Accompanies [ADR-A23](../../docs/architecture/decisions/ADR-A23-mork-compiler-family-completion-policy.md) and [ADR-A24](../../docs/architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md)
Verification: [plans/eligibility-compiler.md](../plans/eligibility-compiler.md) (2026-09-23)
Source design note: [ontology/surface/docs/MorkEnhancements.md](../../ontology/surface/docs/MorkEnhancements.md)

## What this is

`tools/mork_compilers/` and `ontology/mork/spec/Executable.ttl` implement delivery-plan Phase 5 (the MORK compiler family) narrowed to what MorkEnhancements.md's proposal and ADR-A24 actually call for first: a shared executable IR for Eligibility's `elg:IntervalCondition`, and three backend compilers reading it — SPARQL, SHACL, and SWRL.

```text
elg:IntervalCondition (+ its elg:requiredRangeSet, qnt:Range, qnt:Bound, qnt:Value chain)
        ↓  tools/mork_compilers/eligibility_ir.py
IntervalPlan  (backend-neutral: value space, required intervals with closure)
        ↓                    ↓                    ↓
sparql_backend.py     shacl_backend.py      swrl_backend.py
        ↓                    ↓                    ↓
mork:QueryTemplate    mork:DataMapping       mork:DataMapping
(exe:SparqlArtefact)  + 2 sh:NodeShape       + one swrl:Imp per
                      (exe:ShaclArtefact)     required interval
                                              (exe:SwrlArtefact)
```

Every artefact carries provenance back to the condition and every Quantification node it was compiled from, via `exe:IntervalContainmentPlan`'s `implementsCondition`/`derivedFromEligibilityNode`/`derivedFromQuantificationNode`/`producesArtefact`.

## What was deliberately left out, and why

**No "native" backend.** The user requested this explicitly: there is no stated definition anywhere in this repository of what a native artefact would be (the delivery plan lists one, but never defines it), so nothing was invented to fill the gap. `mork_compilers/namespaces.py`'s module docstring records this as a decision, not an oversight.

**No "Executable Projection Contract" layer.** MorkEnhancements.md's final, longest section proposes a further abstraction — `exp:ExecutableProjectionContract` — so a *domain* ontology (its own example: a loans ontology) can declare "my `loans:creditScore` property supplies candidate evidence" without authoring MORK internals directly. That is a real gap the design note identifies correctly, but it is also a new architectural layer on the scale of ADR-A17's Surface Projection decision — it needs its own ADR-level sign-off, not silent adoption as a side effect of implementing Phase 5. This compiler package sidesteps the gap for now by reading candidate evidence directly from `elg:Question`'s own `elg:candidateRangeSet` — the shape `ontology/eligibility/examples/interval-containment.ttl` already uses — rather than from an arbitrary domain property. That is a real limitation: a deployment whose candidate evidence lives on a domain property (a `loans:creditScore`) has no declared way to tell this compiler where to find it. Building `exp:` properly is future work, gated on that sign-off.

**No profile-level aggregate artefact.** `eligibility_ir.py::compile_profile` computes the IR for a whole `elg:AdmissionProfile` (its aggregation operation and its condition plans), and `ontology/mork/spec/Executable.ttl` declares `exe:ProfilePlan` for it — but no backend in this package emits RDF for a `ProfilePlan`, or a combined SPARQL/SHACL/SWRL artefact that aggregates several conditions' outcomes into one profile-level decision. Only per-condition artefacts exist. Combining them (per MorkEnhancements.md §9's `AllRequired`/`AnySufficient` aggregation rules) is real, separate work, named here so it is not mistaken for done.

**No runtime result tracking.** The design note's §6 provenance model includes `exe:EvaluationRun`, `exe:ConditionResult`, `exe:ProfileResult`, and `exe:Diagnostic` — a record of what happened when an artefact actually ran. None of that is implemented, and none of it is declared in `ontology/mork/spec/Executable.ttl` either (deliberately: an unused vocabulary term is worse than a documented gap). This package compiles artefacts; it does not run them.

**Only `elg:IntervalContainment` is compiled.** `elg:ExactCondition`, `elg:SetMembershipCondition`, and `elg:WildcardCondition` are not. A condition with `elg:wildcardSemantics` other than `elg:NoWildcard` is refused outright by the IR rather than silently compiled with unaccounted-for semantics.

## Backend-specific limitations

- **SPARQL** (`sparql_backend.py`): one `SELECT` per condition, returning `?question ?decision` with `decision` bound to the literal string `"Permitted"`/`"Denied"`/`"Undetermined"`. Multiple required ranges become an `||` of per-range containment clauses (a legitimate union-of-intervals reading of one `qnt:RangeSet`).
- **SHACL** (`shacl_backend.py`): a readiness shape (candidate evidence exists for this condition) and a containment shape (evidence is contained by some required interval), both SPARQL-based and scoped to the specific condition via `elg:forCondition` — not a blanket `elg:Question` check, since a Question for a different condition may legitimately carry different evidence. SHACL conformance is not itself a decision; a runtime adapter mapping a validation report to `elg:Permitted`/`elg:Denied`/`elg:Undetermined` is not built here, per MorkEnhancements.md's own point that this gap exists regardless of who generates the shape.
- **SWRL** (`swrl_backend.py`): positive-only, per ADR-A24. One `swrl:Imp` per required interval (each independently sufficient to derive the same consequent, a valid Horn-clause disjunction expressed as several rules), asserting `exe:impliesDecision(?question, elg:Permitted)` — never `elg:Denied` or `elg:Undetermined`, which open-world reasoning cannot support deriving. `mork:swrlCompactSyntax` is not populated (it is documented in `ontology/mork/spec/Mork.ttl` as a human-readable annotation with no logical role, and adding it is a straightforward follow-up, not a correctness gap).

## Verification plan (not yet run)

No Python interpreter and no SHACL/SWRL/SPARQL engine were available in the environment this was written in.

1. Run `python -m unittest mork_compilers.test_mork_compilers -v` and treat the first pass as part of review, exactly as `surface`'s own test suite documents for itself.
2. Parse `ontology/mork/spec/Executable.ttl` and confirm it is consistent with `ontology/mork/spec/Mork.ttl` under a real OWL reasoner — the punned references to `elg:Condition`, `elg:Question`, `elg:Decision` etc. should resolve once Eligibility's own ontology is loaded alongside it, even though this file does not import Eligibility formally.
3. Execute the generated SPARQL query from `sparql_backend.compile_query_template` against `ontology/eligibility/examples/interval-containment.ttl` and confirm `ex:question-1` resolves to `"Permitted"`.
4. Validate the generated SHACL shapes from `shacl_backend.compile_shapes` with a real SHACL engine against the same example, and against a fixture with a missing `elg:candidateRangeSet` and one with an out-of-range candidate.
5. Load the generated SWRL rule from `swrl_backend.compile_rules` into a SWRL-capable reasoner (e.g. Drools, Pellet) and confirm it derives `exe:impliesDecision(ex:question-1, elg:Permitted)`.
