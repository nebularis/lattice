<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Compiler Family

Compiles Eligibility conditions into SPARQL, SHACL and SWRL artefacts through
one shared IR (ADR-A23, ADR-A24, ADR-A89).

| Condition | IR plan | Backends |
|---|---|---|
| `elg:IntervalContainment` | `IntervalPlan` | SPARQL, SHACL, SWRL |
| `elg:ExactMatch`, `elg:SetMembership`, `elg:HierarchicalMatch` | `ConceptPlan` | SPARQL, SHACL, SWRL |
| `elg:AdmissionProfile` (`AllRequired`, `AnySufficient`) | `ProfilePlan` | SPARQL, SHACL, SWRL |

Concept plans follow the decision table in `ontology/eligibility/README.md`
§4 (ADR-A87). A question with no `elg:candidateConcept`, or more than one, is
`Undetermined`.

Hierarchical match, and a condition with exclusions only, need the scheme
bound to the condition's `elg:constrainedByContract`. The IR resolves it with
the Vocabulary reference resolver (`tools/vocabulary`, ADR-A85). When the
contract has any `voc:SchemeBinding`, pass the resolution instant and scope
explicitly:

```python
from datetime import datetime, timezone
from mork_compilers import ResolutionContext, compile_concept_condition

plan = compile_concept_condition(graph, condition, ResolutionContext(at=datetime(2026, 6, 1, tzinfo=timezone.utc)))
```

Such a plan also carries `expansion`, the decision for every member of the
resolved scheme ("Expanded" in ADR-A89). The SPARQL backend walks the
hierarchy at query time instead ("QueryTime"). The tests check that the two
agree on every member.

SHACL and SWRL read the expansion. SHACL emits readiness, determinacy and
admission shapes: the first to report a question gives `Undetermined`,
`Undetermined` or `Denied`, and a question none reports is `Permitted`. SWRL
emits `exe:admittedBy` and `exe:deniedBy` facts and one rule for each, so it
derives `Permitted` and `Denied` from positive facts only and never
`Undetermined` (ADR-A24). SWRL assumes one candidate per question. A question
with several can derive both outcomes.

A profile plan decides each `elg:EligibilityDecision` record of the profile
by strong Kleene logic over its conditions' outcomes, with a condition the
record asks no question of counted as `Undetermined`. `DimensionConsistent`
is refused. The profile's SHACL shapes target the record and wrap the profile
query. Its SWRL rules derive `exe:impliesProfileDecision` from the questions'
`exe:impliesDecision` facts. The shared conformance corpus runs every
Eligibility case through SPARQL and SHACL (`python -m tools.phase8_conformance`).

A condition bound by an `elg:EvidenceBinding` (ADR-A91) is evaluated for
every instance of the binding's subject class, reading the candidate along
the binding's path. Its SPARQL rows are keyed by the subject, its shapes
target the subject class, and its SWRL rules derive `exe:permittedUnder` or
`exe:deniedUnder` on the subject. A profile whose conditions are all bound to
one class decides each subject. See `ontology/eligibility/examples/evidence-binding.ttl`.

Every SPARQL row carries `?diagnostic`, an `exe:Diagnostic` individual, exactly
when its decision is `Undetermined`.

From the command line:

```bash
python -m mork_compilers.cli compile-condition \
    --declarations ontology/eligibility/examples/hierarchical-match.ttl \
    --condition https://example.org/lattice/eligibility/hierarchical-condition
```

Add `--at <ISO 8601 instant>` and `--scope <IRI>` when the condition's
contract has scheme bindings.

Install the editable package from the repository root with:

```bash
mise exec -- python -m pip install -e ./tools/mork_compilers
```

Run the compiler tests with:

```bash
mise run check:mork-compilers
```
