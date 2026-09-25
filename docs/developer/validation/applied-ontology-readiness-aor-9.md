<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-9, candidate evidence bindings

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [Phase B](../plans/applied-ontology-readiness.md#phase-b-executable-coverage)
**Decision:** [ADR-A91](../../architecture/decisions/ADR-A91-eligibility-candidate-evidence-binding.md), Proposed, with implementation notes

## Invariant

A condition bound by an `elg:EvidenceBinding` is evaluated for every instance
of the subject class (subclasses included) along the binding's path over the
applied ontology's own properties, with no question authored. SPARQL and
SHACL agree on every subject. SWRL derives a sound subset.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR9-01 | the example plus four employees / bound hierarchical condition, two-step path / eight subjects as expected, `AboveExclusion` for the family above the exclusion, `SeveralCandidates` for two roles | L1 | + and - |
| AOR9-02 | same / bound interval condition / literal tenure read on the declared space, a quantity on the condition's space read, a quantity on another space `ValueSpaceMismatch`, no tenure `MissingCandidate` | L1 | + and - |
| AOR9-03 | same / bound profile / each subject decided by strong Kleene logic, a diagnostic exactly when `Undetermined` | L2 | + |
| AOR9-04 | same / concept, interval and profile shapes via pySHACL / each agrees with SPARQL, including the subclass instance | L2 | + |
| AOR9-05 | same, one role each / condition and profile SWRL applied / every derived outcome agrees with SPARQL, exactly `alice` Permitted and `bob` Denied | L2 | + |
| AOR9-06 | a second binding for one condition / compiled / refused | L1 | - |
| AOR9-07 | a gap in step indexes / compiled / refused | L1 | - |
| AOR9-08 | a binding reading on another value space / compiled / refused (`exe:ValueSpaceMismatch`) | L1 | - |
| AOR9-09 | a profile mixing bound and question-read conditions / compiled / refused | L1 | - |
| AOR9-10 | an inverse first step (team membership) / compiled and executed / steps recorded with direction, a contractor team `Denied`, no team `Undetermined` | L1 | + |
| AOR9-11 | bound condition and profile / three backends compiled twice / isomorphic | L2 | + |
| AOR9-12 | `evidence-binding.ttl` / Eligibility shapes / no results (in `check:eligibility-examples`) | L1 | + |

## One command

```bash
mise run check:mork-compilers
```

Pass: `74 passed`. Also `mise run check:eligibility-examples` (12 passed).

## Artefacts to inspect

- Eligibility: `elg:EvidenceBinding`, `elg:EvidenceStep`, `elg:StepDirection`
  with `elg:Forward` and `elg:Inverse`, `elg:bindsCondition`,
  `elg:subjectClass`, `elg:evidenceStep`, `elg:stepIndex`, `elg:stepProperty`,
  `elg:stepDirection`, `elg:readOnSpace`, two structural shapes, and the
  README §4 paragraph. Within this change set Eligibility stays at 0.4.0
  (MINOR against the committed 0.3.0).
- `ontology/eligibility/examples/evidence-binding.ttl`.
- Executable: `exe:permittedUnder`, `exe:deniedUnder`,
  `exe:ValueSpaceMismatch`, and `exe:impliesProfileDecision` without a domain,
  so it applies to records and to bound subjects.
- Compiler: `EvidencePath`, `read_evidence`, `evidence_path`,
  `_bound_interval_select`, `render_bound_interval_selects`, `_path_atoms`,
  `_bound_interval_rule`.
- ADR-A91's implementation notes.

## Adversarial probe (run by the agent)

| Mutation | Tests failed |
|---|---|
| inverse steps walked forward | AOR9-10 |
| subclass instances not selected | AOR9-01, AOR9-02, AOR9-03, AOR9-04 (profile) |
| literals never read | AOR9-02, AOR9-03, AOR9-04 (interval, profile), AOR9-05 |
| bound concept rule heads use `exe:impliesDecision` | AOR9-05 |

## Deviations and known limits

- `elg:aboutSubject` is not declared. No artefact mints a question or record,
  so it has no producer (ADR-A91 implementation notes).
- A bound interval SWRL rule reads one terminal form, so `hal`'s quantity is
  read by SPARQL and SHACL but not by the literal-reading SWRL rule.
- SWRL, like the question form, assumes one value per subject.

## Deliberate non-coverage

- The OWL backend's use of bindings (AOR-10).
- Alternation and zero-or-more paths.
