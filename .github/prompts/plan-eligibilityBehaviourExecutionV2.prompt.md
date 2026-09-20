# Plan: Agentic Execution Roadmap for Eligibility & Behaviour (v2)

This supersedes the earlier draft. Two repo-state changes and two user clarifications materially change the sequencing:

1. **Quantification (`qnt:`) is no longer green-field.** [quantification/README.md](quantification/README.md) (1277 lines), quantification/spec/quantification.ttl (561 lines), quantification/vocab/, and quantification/shapes/ are fully authored — value spaces, quantities, ordinal values, bounds, ranges, cyclic ranges, range sets, anchor bindings, recurrence, conversion, ordering. This is exactly the mechanism Eligibility's `IntervalContainment` strategy and Behaviour's extent profile were previously blocked on. **There is nothing left to scaffold or bootstrap** — the work is *wiring it in*, not building it.
2. **SPC also has substantial content** (spc/spec/spc.ttl, 1227 lines; spc/README.md, 1393 lines; spc/docs/ has an architecture note and a paper), but under a placeholder namespace (`http://example.org/spc#`) and with an empty spc/projection/. It is not a dependency of Eligibility or Behaviour, so it's out of scope for this plan beyond one documentation-accuracy fix in Gate 1.
3. **Containment posture is lighter than previously planned.** Generating MERIDIAN-facing applied-layer content (dimension sets, worked examples, projection axioms) *inside this repo* is fine — the user decides what gets committed. The only standing rule is that the public substrate (eligibility/, behaviour/, instrument/, their vocab/spec/) never names a closed brand or encodes closed inventory. This removes the "physical repo split" and "two-role clean-room" machinery as execution tasks — WINGMAN is already a local, non-committed symlink, which satisfies the separation concern by construction.
4. **ADR A-C1/A-C2 are authored as real files in this repo** (per the user's explicit confirmation), just without naming MERIDIAN — generic procedural content only.

**Repo-state findings (re-verified this pass):**
- [foundation](foundation), [vocabulary](vocabulary), [party](party), **[quantification](quantification)** are complete T-Boxes. [spc](spc) is complete but architecturally unintegrated (own namespace, no projections, not part of the documented dependency graph).
- [eligibility/README.md](eligibility/README.md), [behaviour/README.md](behaviour/README.md), [instrument/README.md](instrument/README.md) are all still genuinely empty (0 bytes) — clean-room authoring is straightforward, no adversarial procedure needed.
- **quantification/spec/quantification.ttl declares no `owl:imports`** despite its own README stating it imports Foundation and Vocabulary (§2) — the axioms haven't caught up with the design prose. **[party/spec/party.ttl](party/spec/party.ttl) imports only Foundation**, not Quantification, despite Quantification's README claiming Party imports it. This mismatch is a Gate 1 fix, not a new design decision.
- [README.md](README.md) and [docs/architecture/ontology-architecture.md](docs/architecture/ontology-architecture.md) both still describe a **six-layer** picture with no Quantification or SPC row, and both still state the old three-tier dependency order (Foundation → Vocabulary → Party → {Instrument, Eligibility, Behaviour}) with no Quantification link. ontology-architecture.md still asserts "SPC has no implementation in this repository at all," which is now false.
- [docs/adr](docs/adr), [docs/validation-and-test-plan.md](docs/validation-and-test-plan.md), and [docs/operational-guidance.md](docs/operational-guidance.md) are all empty — no conflicting content to reconcile, just files to author.
- Instrument is still entirely unauthored, and Behaviour's effect contract (C.7 in the consolidated plan) writes into `ins:Element`/`ins:Obligation`/`ins:Qualifier`, so a minimal Instrument shape remains a hard prerequisite for Gate 3 (kept as Gate 2.5).
- CI checks remain **documented, not built**, per your earlier decision — no GitHub Actions are added in this pass.

---

**Steps**

**Decisions to record first**
1. ADR convention: docs/adr/ADR-{id}-{slug}.md, MADR-lite shape (Status/Context/Decision/Consequences), indexed by docs/adr/README.md.
2. A-C1 (three-region gap/region analysis restated privately) and A-C2 (clean-room re-authoring procedure) **are** authored as real files in this repo, generic and MERIDIAN-unnamed — A-C2 records the *lightweight* posture (finding 3 above), not the heavier two-role/physical-split version from the original consolidated plan.
3. Containment rule, stated once in docs/GOVERNANCE.md rather than repeated per-gate: public substrate directories stay domain-neutral and closed-brand-free; applied/deployment-specific content (e.g. a MERIDIAN dimension set) may be authored anywhere in the repo the user designates and is committed only at the user's discretion.

**Gate 1 — Architecture baseline and wiring (no new mechanism content)**
4. Author ADR-A01 (layer dependency order): `Foundation → Vocabulary → Quantification → Party → Eligibility → Instrument → Behaviour`, matching what Quantification's own README already claims. Record SPC as a present-but-unintegrated ninth participant, explicitly out of this dependency chain until a separate integration effort addresses its namespace and projection gap.
5. **Fix the import graph to match the documented order:** add `owl:imports` for Vocabulary to quantification.ttl; add `owl:imports` for Quantification to party.ttl; record that Eligibility/Instrument/Behaviour will import Quantification once authored.
6. Update README.md: layer table gains Quantification, dependency diagram corrected.
7. Update docs/architecture/ontology-architecture.md: layer table, dependency-order fence, and Implementation Status table gain Quantification (fully specified) and correct SPC's status.
8. Author ADR-A12 (identity/derivation model), ADR-A13 (dataset/graph-role model, flagging the open sub-question of new `fnd:` properties), ADR-A14 (conformance levels, + companion doc), ADR-A15 (realisation-strategy neutrality).
9. Create docs/GOVERNANCE.md per decision 3 — tiers/postures, the lightweight naming rule, pointer to the conformance ladder, no repo-split or two-role procedure.
10. Populate docs/validation-and-test-plan.md with documented (not built) checks: import-closure/no-upward-reference, substrate-inventory-emptiness, reuse-lint reference, placeholders for Gate 2+ checks.

**Gate 2 — Eligibility core correction**
11. Author ADR-A03 through A07 (condition taxonomy, interval-overlap/law split, compatibility vocabulary, wildcard semantics, authoring direction).
12. Author non-domain worked examples in eligibility/examples/ before mechanism prose.
13. Author eligibility/README.md: imports now include **Quantification directly**; match-strategy algebra with **`IntervalContainment` included** (using `qnt:Range`/`qnt:RangeSet`) and `IntervalOverlap` excluded (a law-coherence defect, independent of Quantification's existence); three-valued `Decision`; three named compatibility operations; wildcard rules; canonicalisation; `AdmissionProfile ⊑ Condition`; operational profiles E1–E6; laws L1–L8.
14. Extract eligibility/spec/eligibility.ttl, vocab, shapes via fence tags.
15. Populate eligibility/projection/party.ttl; consider eligibility/projection/quantification.ttl for the `IntervalContainment` binding.
16. Build E1/E2 conformance fixtures under eligibility/test/, including one exercising `IntervalContainment`.
17. Verify Gate 2 exit criteria — including `IntervalContainment` usable end-to-end, no exemption needed.

**Gate 2.5 — Minimal Instrument authoring (blocks Gate 3)**
18. Author ADR-A07b (minimal Instrument shape): `ins:Element`/`Provision`/`Obligation`/`Qualifier`, disjointness, R-B7 versioning/supersession contract.
19. Author instrument/README.md, spec, vocab, shapes.
20. Populate instrument/projection/party.ttl.

**Gate 3 — Behaviour declaration model (including extent, no longer deferred)**
21. Author ADR-A08 through A11 (four-tier model, selection, activation, effect/target binding).
22. Author non-domain worked examples in behaviour/examples/ first.
23. Author behaviour/README.md: four tiers, TriggerDefinition split, authority/activation/selection policies, StateOccupancy with hypothetical-graph separation, effect payload contract, cascade/queue semantics.
24. **Extent profile (3b):** author `bhv:AllowanceDefinition`/`AllowanceAccount` directly against `qnt:ValueSpace`/`Range`/`RangeSet`/`Recurrence`, `Sequential` absorption only. `Proportional` stays deferred (its blocker is independent of Quantification's existence).
25. Extract behaviour/spec, vocab, shapes.
26. Populate behaviour/projection/{eligibility,instrument,party,quantification}.ttl.
27. Populate behaviour/execution/{invalidation-policy,benchmark-pack,split-plan}.md.
28. Build B-P1/B-P2 fixtures including `Sequential` absorption.
29. Verify Gate 3 exit criteria, extent scoped to `Sequential` only, `Proportional` visibly (not silently) unusable.

**Gate 4 — Derivation, validation, optional compilation**
30. Derivation-product model + doc. Static checks as SPARQL/SHACL reference realisations with deliberate-defect fixtures. Targeted invalidation demonstrated.

**Gate 5 — Multi-profile evaluator conformance**
31. Shared semantic conformance corpus at root test/conformance/, ≥2 profiles per layer, semantic-output projection documented.

**Gate 6 — Residual extent completeness (light, formerly the blocking half of old Gate 6)**
32. Revisit `Proportional` absorption once two non-domain examples exist; complete reset-semantics edge cases. Scope-completion, not foundations-blocked.

**Gate 7 — Applied-layer validation (optional, user-directed)**
33. Out of formal scope. MERIDIAN-facing applied content may be generated in this repo on request (e.g. under WINGMAN/); user decides what's committed.

**Gate 9 — SPC integration (flagged only, out of scope)**
34. Noted in Gate 1's doc fix only; namespace harmonisation and projection authoring are future work.

---

**Verification**
- Each gate's exit criteria is the acceptance test before advancing.
- After Gate 1: README.md, ontology-architecture.md, and the ADRs state the same seven-link dependency graph, and party.ttl/quantification.ttl imports match it.
- After Gates 2/3: fence-tag extraction is byte-consistent with README fenced blocks.
- reuse lint passes on every new file.

**Decisions**
- Quantification/SPC are already-delivered repo state to wire in and document, not content to author — removes "scaffold qty/" entirely.
- `IntervalContainment` moves into Gate 2 (blocker resolved); `IntervalOverlap` stays removed regardless (law defect, not data-availability).
- Extent profile moves into Gate 3 as sub-phase 3b, `Sequential`-only; `Proportional` and full reset-edge-cases deferred to a lighter Gate 6.
- Containment/clean-room machinery simplified: no repo split, no two-role procedure, one governance doc states the naming rule once.
- A-C1/A-C2 authored as real files (reversing prior "do not author" stance), generic and MERIDIAN-unnamed.
- SPC integration explicitly out of scope beyond one doc fix.
