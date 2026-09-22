⚠️ **DEPRECATED** — This document has been migrated to the LATTICE documentation governance structure.

**New locations:**
- Plan: [docs/developer/plans/surface-mork-unified-projection-plan.md](../../../docs/developer/plans/surface-mork-unified-projection-plan.md) (Phase 5 section)
- Status: [docs/developer/status/surface-mork-unified-projection.md](../../../docs/developer/status/surface-mork-unified-projection.md) (Phase 5 section)

**Reason:** Content integrated into Phase 5 (MORK compiler backends) planning and status.

**Migration date:** 2026-09-22

For current MORK compiler backend details, refer to the links above. This file is retained for historical reference.

---

Yes. **Mork is designed to support this direction**, but the repository currently contains the ontology vocabulary and an RML compiler, not a completed eligibility-to-SWRL, SHACL, or SPARQL compiler.

## What Mork already provides

The Mork model has a generative layer:

- `mork:GenerativeMapping`
- `mork:ShapeMapping`
- `mork:RuleMapping`
- `mork:generatesShapeDefinition`
- `mork:generatesRuleDefinition`
- `mork:QueryTemplate`
- parameter bindings, targeting specifications, provenance, jurisdiction, and effective dates

The ontology defines `RuleMapping` as a mapping that generates a structured `swrl:Imp` rule. The rule is represented as RDF with antecedent and consequent atom lists, rather than only as a serialized SWRL string. `mork:swrlCompactSyntax` is explicitly described as a human-readable annotation, not the canonical rule representation.

This is consistent with the Mork architecture documentation, which describes deterministic generation of SHACL shapes, SPARQL queries, SWRL rules, and RML mappings from a validated mapping graph.

The existing `tools/mork2rml.py` compiler confirms that this is intended as a compiler family. It identifies `ShapeMapping` and `RuleMapping`, but currently skips them because that compiler targets RML:

```python
if spec.role not in (
    MappingRole.SHAPE_MAPPING,
    MappingRole.RULE_MAPPING,
)
```

So the current situation is:

| Capability | Mork vocabulary | Compiler implementation |
|---|---:|---:|
| RML mappings | Yes | Partially implemented |
| SHACL generation | Yes | Not identified in the current compiler |
| SWRL generation | Yes | Not identified in the current compiler |
| SPARQL query templates | Yes | Vocabulary support, compiler not identified |
| Eligibility rule compilation | Modelable | Not yet implemented |

## How the eligibility example fits

The interval example is currently a **declarative eligibility instance**, not an executable rule.

It declares:

- a credit-score value space
- a required range from `700` to `850`
- an interval containment condition
- a question using that required range as its candidate range
- a permitted decision

The relevant semantics are represented by:

```turtle
elg:matchStrategy elg:IntervalContainment ;
elg:compatibilityOperation elg:AllRequired ;
elg:requiredRangeSet ex:required-rangeset .
```

The intended executable interpretation would be something like:

```text
A candidate is permitted when its credit-score range is contained by
the required range [700, 850].
```

That interpretation requires a compiler or evaluator to understand the Eligibility and Quantification vocabularies. OWL reasoning alone will not calculate interval containment.

## Recommended separation of concerns

I would separate the system into three layers.

### 1. Eligibility declaration

This is the existing `ontology/eligibility/examples/interval-containment.ttl` style.

It describes the business rule in a stable, domain-oriented vocabulary:

```text
condition → strategy → required range
question → candidate range
decision → permitted, denied, or undetermined
```

### 2. Mork executable mapping

A Mork mapping would connect the eligibility condition to the target data and executable artefact.

For example, conceptually:

```turtle name=SWRL.ttl url=https://github.com/nebularis/lattice/blob/main/mork/spec/Mork.ttl
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix ex:   <https://example.org/lattice/eligibility/> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ex:credit-eligibility-rule
    a mork:RuleMapping ;
    mork:mappingScheme ex:eligibility-mapping-scheme ;
    mork:hasTargetingSpec ex:credit-eligibility-target ;
    mork:hasParameterBinding ex:lower-bound-parameter,
                            ex:upper-bound-parameter ;
    mork:hasRuleProvenance ex:credit-eligibility-provenance ;
    mork:generatesRuleDefinition ex:credit-eligibility-swrl .

ex:credit-eligibility-target
    a mork:TargetingSpec ;
    sh:targetClass ex:Applicant .

ex:lower-bound-parameter
    a mork:ParameterBinding ;
    mork:paramName "lowerBound" ;
    mork:paramType "Numeric" ;
    mork:paramValue "700"^^xsd:decimal .

ex:upper-bound-parameter
    a mork:ParameterBinding ;
    mork:paramName "upperBound" ;
    mork:paramType "Numeric" ;
    mork:paramValue "850"^^xsd:decimal .

ex:credit-eligibility-swrl
    a swrl:Imp .
```

The compiler would populate `ex:credit-eligibility-swrl` with structured SWRL atoms derived from the Eligibility graph and the target ontology mapping.

The exact property names for target data would depend on the ontology being checked. For example, the rule might eventually evaluate a normalized candidate value:

```text
Applicant(?a)
hasCreditScore(?a, ?score)
swrlb:greaterThanOrEqual(?score, 700)
swrlb:lessThanOrEqual(?score, 850)
→ elg:eligible(?a, true)
```

The output could instead be an RDF decision individual, depending on the desired runtime model.

### 3. Runtime execution

A runtime engine would execute one of the generated artefacts:

- a SWRL reasoner derives an eligibility classification
- a SHACL engine returns validation results
- a SPARQL query returns a decision and diagnostic bindings
- a native evaluator executes a compiled intermediate representation

## SWRL versus SHACL versus SPARQL

For this use case, I would not make SWRL the only target.

### SWRL

SWRL is suitable when the rule should **derive facts**:

```text
Applicant(?a) and score within range
→ EligibleApplicant(?a)
```

It is less suitable for:

- returning detailed failure reasons
- representing `Permitted`, `Denied`, and `Undetermined` cleanly
- interval structures with open and closed bounds
- absent or incomplete data
- complex aggregation across several conditions

SWRL built-ins can perform numeric comparisons, but interval containment involving `qnt:Range`, `qnt:Bound`, `qnt:Quantity`, closure, density, and space compatibility would require either:

1. a normalization step that exposes comparable values as direct datatype properties, or
2. custom SWRL built-ins supplied by the execution environment.

### SHACL

SHACL is a good target for **validation and diagnostics**.

A generated shape could validate that:

- a candidate has a credit score
- the score is in the permitted interval
- the value belongs to the correct value space
- required fields are present

SHACL also provides validation reports, which are useful for explaining why a candidate was denied.

However, SHACL validation results are not automatically the same thing as an eligibility decision. A small decision adapter would still be needed to map conforming or non-conforming results to `elg:Permitted`, `elg:Denied`, or `elg:Undetermined`.

### SPARQL

SPARQL is likely the most direct target for an initial eligibility evaluator.

It can:

- inspect the condition and candidate graphs
- compare numeric values
- distinguish missing data from failed constraints
- return decision status and diagnostic bindings
- combine multiple conditions using `FILTER`, `EXISTS`, `NOT EXISTS`, and aggregates

For example, a generated query could return:

```text
Permitted     if every required condition matches
Denied        if at least one condition is known to fail
Undetermined  if no condition fails but at least one required fact is missing
```

That maps naturally to the three-valued Eligibility vocabulary.

## Suggested compiler design

A useful design would introduce a shared intermediate representation rather than compiling Eligibility directly into each target syntax.

```text
Eligibility graph
        ↓
Mork mapping graph
        ↓
Validated executable IR
        ↓
 ┌──────────────┬──────────────┬──────────────┐
 │              │              │              │
SHACL          SPARQL         SWRL        Native evaluator
```

The intermediate representation could contain operations such as:

```text
IntervalContains(
    candidatePath = "creditScore",
    lower = 700,
    lowerClosed = true,
    upper = 850,
    upperClosed = true,
    valueSpace = "credit-score"
)
```

Each backend would then implement the same semantics:

- SHACL backend generates constraints
- SPARQL backend generates a decision query
- SWRL backend generates inference atoms
- native backend generates direct application code

This avoids encoding interval semantics independently in three different generators.

## Proposed Mork mapping categories

The existing Mork classes map reasonably well to this design:

| Mork construct | Eligibility use |
|---|---|
| `mork:DataMapping` | General link between an eligibility concept and target data |
| `mork:ShapeMapping` | Structural and value validation |
| `mork:RuleMapping` | Inference or classification rules |
| `mork:QueryTemplate` | Parameterized eligibility evaluation queries |
| `mork:TargetingSpec` | Target applicant, policy, quote, or other subject |
| `mork:ParameterBinding` | Bounds, thresholds, codes, dates, and jurisdiction values |
| `mork:hasConstraintProvenance` | Provenance for SHACL constraints |
| `mork:hasRuleProvenance` | Provenance for SWRL rules |
| `mork:dependsOnMapping` | Dependencies on mapped target properties or classes |
| `mork:generatesTransformDefinition` | RML or other graph-construction artefacts |

One change I would consider is introducing a more explicit executable semantics vocabulary, for example:

```turtle
mork:hasExecutableSemantics
mork:usesEligibilityOperator
mork:inputPath
mork:outputDecision
mork:diagnosticMessage
mork:threeValuedEvaluation
```

Those properties would make the mapping intention clearer than relying only on general `DataMapping` and `ParameterBinding` structures.

## Important limitation in the current Mork model

The Mork ontology describes generated rule and shape artefacts, but the current repository evidence does not show a completed compiler for them. The RML compiler explicitly recognizes these mapping roles and excludes them from RML compilation. That is a clean extension point for implementing:

- `MorkToSwrlCompiler`
- `MorkToShaclCompiler`
- `MorkToSparqlCompiler`
- possibly a shared `MorkEligibilityCompiler`

The first implementation should probably target **SPARQL plus SHACL**, then add SWRL for classifications that genuinely benefit from inference.

A practical first milestone would be:

1. Normalize an Eligibility condition into an executable intermediate representation.
2. Compile `IntervalContainment` into a SPARQL query.
3. Compile the same condition into a SHACL-SPARQL constraint.
4. Add a `RuleMapping` backend only for simple positive classifications.
5. Preserve a provenance link from the generated artefact back to the `elg:Condition`, `elg:Question`, and `elg:EligibilityDecision`.

So, in short: **yes, the proposed architecture fits Mork well**. The ontology already provides the required generative concepts. What is missing is the compiler implementation and, likely, a small shared executable semantics layer for Eligibility and Quantification.


Below is a proposed design specification. It treats Eligibility as the declarative source model, Mork as the validated compilation model, and an executable intermediate representation as the shared source for SPARQL, SHACL, SWRL, and native evaluators.

````markdown name=ontology/eligibility/docs/executable-semantics.md
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Executable Eligibility Semantics Layer

## 1. Purpose

This specification defines an executable semantics layer for LATTICE Eligibility declarations.

The layer compiles declared `elg:Condition` and `elg:AdmissionProfile` resources into deterministic evaluation plans and executable artefacts. It supports:

- native evaluation for operational decision services
- SPARQL queries for graph-native evaluation and reporting
- SHACL shapes for input readiness validation and diagnostic reporting
- SWRL rules for monotonic positive inferences where their semantics are sufficient

The layer preserves a traversable provenance path from every executable result and generated artefact back to:

1. the generated executable plan or artefact
2. the Mork mapping that generated it
3. the Eligibility condition and profile it implements
4. the source Quantification ranges, bounds, values, and value spaces
5. the original source nodes and, where available, the natural-language source and extraction provenance

The layer does not make OWL reasoning responsible for interval arithmetic, three-valued decision calculation, or missing-data handling. Those operations are defined by this specification and performed by a compiler or evaluator.

---

## 2. Scope

### 2.1 In scope

- Compilation of Eligibility conditions into an implementation-neutral intermediate representation.
- Three-valued condition and profile evaluation.
- Interval containment over `qnt:RangeSet`, `qnt:Range`, `qnt:Bound`, and `qnt:Value`.
- Compilation of the intermediate representation into SPARQL, SHACL, SWRL, and native evaluator artefacts.
- Provenance for plans, artefacts, evaluation results, and diagnostics.
- Deterministic compilation after validation of the Eligibility and Mork graphs.

### 2.2 Out of scope

- Ontology alignment from arbitrary external schemas to Eligibility input nodes.
- Unit conversion and contextual conversion algorithms.
- Cyclic ranges, recurrence, fuzzy quantities, and uncertain numerical values beyond their classification as unsupported or indeterminate inputs.
- Non-monotonic negation in SWRL.
- Selection of a particular SHACL engine, SWRL reasoner, SPARQL implementation, or native runtime language.

---

## 3. Architectural Position

The executable semantics layer is positioned after Eligibility and Mork validation.

```text
Eligibility declaration graph
        +
Quantification declaration graph
        +
Mork mapping graph
        ↓
Structural and semantic validation
        ↓
Executable Eligibility Plan
        ↓
 ┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
 │ Native evaluator │ SPARQL query    │ SHACL shape     │ SWRL rule       │
 └─────────────────┴─────────────────┴─────────────────┴─────────────────┘
        ↓
Evaluation result, decision, diagnostics, and provenance
```

Eligibility remains the authority for business semantics. Mork remains the authority for compilation metadata, target bindings, parameterisation, dependencies, generated artefacts, and provenance. The executable plan is the authority for runtime evaluation semantics.

---

## 4. Design Principles

### 4.1 Declaration-first

The source Eligibility graph remains unchanged by compilation. Generated plans and artefacts refer to source nodes but do not replace them.

### 4.2 Deterministic compilation

A validated input graph and a fixed compiler version produce the same executable plan and artefacts. Generated resources should therefore be named or content-addressed deterministically.

### 4.3 Shared semantic core

SPARQL, SHACL, SWRL, and native implementations are backends of one executable plan. Backends must not independently reinterpret Eligibility strategy semantics.

### 4.4 Three-valued decisions

Runtime evaluation distinguishes:

- `elg:Permitted`
- `elg:Denied`
- `elg:Undetermined`

Missing evidence, incompatible value spaces, unsupported comparison features, absent conversion context, and malformed runtime data do not silently become denials.

### 4.5 Provenance by graph links

Every generated resource and evaluation result must expose direct RDF links to its source nodes. Provenance must be queryable without parsing logs or serialized rule text.

### 4.6 Artifact-specific responsibility

- **Native evaluator** is the reference implementation for all supported semantics.
- **SPARQL** is the preferred graph-native decision backend.
- **SHACL** validates data readiness and reports failed constraints.
- **SWRL** derives positive, monotonic facts only.

---

## 5. Namespaces and Core Vocabulary

This specification introduces an executable semantics namespace.

```turtle
@prefix exe:  <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

The `exe:` vocabulary is a compiler-facing vocabulary. It represents normalised executable semantics rather than a replacement Eligibility ontology.

### 5.1 Classes

```turtle
exe:ExecutablePlan a owl:Class ;
    rdfs:comment "A deterministic, implementation-neutral executable representation compiled from an Eligibility declaration and associated Mork mappings." .

exe:ProfilePlan a owl:Class ;
    rdfs:subClassOf exe:ExecutablePlan ;
    rdfs:comment "An executable plan for one AdmissionProfile." .

exe:ConditionPlan a owl:Class ;
    rdfs:subClassOf exe:ExecutablePlan ;
    rdfs:comment "An executable plan for one Eligibility condition." .

exe:IntervalContainmentPlan a owl:Class ;
    rdfs:subClassOf exe:ConditionPlan ;
    rdfs:comment "A condition plan that evaluates whether a candidate range set is contained by a required range set." .

exe:EvaluationRun a owl:Class ;
    rdfs:comment "One execution of an executable plan against supplied candidate evidence." .

exe:ConditionResult a owl:Class ;
    rdfs:comment "The result of evaluating one ConditionPlan." .

exe:ProfileResult a owl:Class ;
    rdfs:comment "The aggregate result of evaluating one ProfilePlan." .

exe:Diagnostic a owl:Class ;
    rdfs:comment "A structured explanation of an indeterminate or denied evaluation outcome." .

exe:GeneratedArtefact a owl:Class ;
    rdfs:comment "A compiler output such as a SPARQL query, SHACL shape, SWRL rule, or native evaluator module." .

exe:SparqlArtefact a owl:Class ;
    rdfs:subClassOf exe:GeneratedArtefact .

exe:ShaclArtefact a owl:Class ;
    rdfs:subClassOf exe:GeneratedArtefact .

exe:SwrlArtefact a owl:Class ;
    rdfs:subClassOf exe:GeneratedArtefact .

exe:NativeArtefact a owl:Class ;
    rdfs:subClassOf exe:GeneratedArtefact .
```

### 5.2 Plan properties

```turtle
exe:implementsProfile a owl:ObjectProperty ;
    rdfs:domain exe:ProfilePlan ;
    rdfs:range elg:AdmissionProfile .

exe:implementsCondition a owl:ObjectProperty ;
    rdfs:domain exe:ConditionPlan ;
    rdfs:range elg:Condition .

exe:hasConditionPlan a owl:ObjectProperty ;
    rdfs:domain exe:ProfilePlan ;
    rdfs:range exe:ConditionPlan .

exe:requiredRangeSet a owl:ObjectProperty ;
    rdfs:domain exe:IntervalContainmentPlan ;
    rdfs:range qnt:RangeSet .

exe:candidateRangeSetPath a owl:ObjectProperty ;
    rdfs:domain exe:IntervalContainmentPlan ;
    rdfs:comment "Identifies the graph path, mapped property, or input binding through which candidate range evidence is obtained." .

exe:usesEvaluationStrategy a owl:ObjectProperty ;
    rdfs:domain exe:ConditionPlan ;
    rdfs:range elg:MatchStrategy .

exe:usesCompatibilityOperation a owl:ObjectProperty ;
    rdfs:domain exe:ProfilePlan ;
    rdfs:range elg:CompatibilityOperation .

exe:usesWildcardSemantics a owl:ObjectProperty ;
    rdfs:domain exe:ConditionPlan ;
    rdfs:range elg:WildcardSemantics .

exe:compiledFromMapping a owl:ObjectProperty ;
    rdfs:domain exe:ExecutablePlan ;
    rdfs:range mork:GenerativeMapping .

exe:dependsOnPlan a owl:ObjectProperty ;
    rdfs:domain exe:ExecutablePlan ;
    rdfs:range exe:ExecutablePlan .

exe:producesArtefact a owl:ObjectProperty ;
    rdfs:domain exe:ExecutablePlan ;
    rdfs:range exe:GeneratedArtefact .
```

### 5.3 Result properties

```turtle
exe:forPlan a owl:ObjectProperty ;
    rdfs:domain exe:EvaluationRun ;
    rdfs:range exe:ExecutablePlan .

exe:hasConditionResult a owl:ObjectProperty ;
    rdfs:domain exe:EvaluationRun ;
    rdfs:range exe:ConditionResult .

exe:hasProfileResult a owl:ObjectProperty ;
    rdfs:domain exe:EvaluationRun ;
    rdfs:range exe:ProfileResult .

exe:forConditionPlan a owl:ObjectProperty ;
    rdfs:domain exe:ConditionResult ;
    rdfs:range exe:ConditionPlan .

exe:forProfilePlan a owl:ObjectProperty ;
    rdfs:domain exe:ProfileResult ;
    rdfs:range exe:ProfilePlan .

exe:resultValue a owl:ObjectProperty ;
    rdfs:domain [
        a owl:Class ;
        owl:unionOf ( exe:ConditionResult exe:ProfileResult )
    ] ;
    rdfs:range elg:Decision .

exe:hasDiagnostic a owl:ObjectProperty ;
    rdfs:domain [
        a owl:Class ;
        owl:unionOf ( exe:ConditionResult exe:ProfileResult )
    ] ;
    rdfs:range exe:Diagnostic .

exe:evaluatedEvidence a owl:ObjectProperty ;
    rdfs:domain exe:EvaluationRun ;
    rdfs:comment "Links an evaluation run to the Question, candidate value, candidate range set, or other observed evidence used at runtime." .
```

### 5.4 Diagnostic vocabulary

```turtle
exe:diagnosticCode a owl:DatatypeProperty ;
    rdfs:domain exe:Diagnostic ;
    rdfs:range xsd:string .

exe:diagnosticMessage a owl:DatatypeProperty ;
    rdfs:domain exe:Diagnostic ;
    rdfs:range xsd:string .

exe:MissingCandidateEvidence a exe:DiagnosticCode .
exe:CandidateRangeMalformed a exe:DiagnosticCode .
exe:RequiredRangeMalformed a exe:DiagnosticCode .
exe:ValueSpaceMismatch a exe:DiagnosticCode .
exe:UnsupportedRangeKind a exe:DiagnosticCode .
exe:ConversionContextAbsent a exe:DiagnosticCode .
exe:GranularityInsufficient a exe:DiagnosticCode .
exe:NoContainingRequiredRange a exe:DiagnosticCode .
exe:NoSatisfiedCondition a exe:DiagnosticCode .
```

`exe:DiagnosticCode` may be modelled as an `owl:Class`, a SKOS concept scheme, or an application enumeration. A SKOS concept scheme is recommended if diagnostic codes will be governed and versioned.

---

## 6. Provenance Model

### 6.1 Required provenance chain

Every generated plan and artefact must expose the following provenance links:

```text
Generated artefact
    → executable plan
    → Mork generative mapping
    → Eligibility condition or profile
    → Quantification range set, range, bounds, values, and value space
    → source declaration graph nodes
```

The following properties are required:

```turtle
exe:compiledFrom a owl:ObjectProperty ;
    rdfs:domain exe:GeneratedArtefact ;
    rdfs:range exe:ExecutablePlan .

exe:derivedFromEligibilityNode a owl:ObjectProperty ;
    rdfs:domain [
        a owl:Class ;
        owl:unionOf ( exe:ExecutablePlan exe:GeneratedArtefact
                      exe:EvaluationRun exe:ConditionResult
                      exe:ProfileResult exe:Diagnostic )
    ] ;
    rdfs:comment "Links a generated or runtime resource directly to an Eligibility declaration node." .

exe:derivedFromQuantificationNode a owl:ObjectProperty ;
    rdfs:domain [
        a owl:Class ;
        owl:unionOf ( exe:ExecutablePlan exe:GeneratedArtefact
                      exe:EvaluationRun exe:ConditionResult
                      exe:ProfileResult exe:Diagnostic )
    ] ;
    rdfs:comment "Links a generated or runtime resource directly to a Quantification node such as a RangeSet, Range, Bound, Value, or ValueSpace." .

exe:derivedFromMorkNode a owl:ObjectProperty ;
    rdfs:domain [
        a owl:Class ;
        owl:unionOf ( exe:ExecutablePlan exe:GeneratedArtefact
                      exe:EvaluationRun exe:ConditionResult
                      exe:ProfileResult exe:Diagnostic )
    ] ;
    rdfs:range mork:DataMapping .

exe:sourceGraphNode a owl:ObjectProperty ;
    rdfs:comment "Generic direct source-node relationship. This property is suitable for all RDF source nodes and is a subproperty of prov:wasDerivedFrom." ;
    rdfs:subPropertyOf prov:wasDerivedFrom .
```

`exe:derivedFromEligibilityNode`, `exe:derivedFromQuantificationNode`, and `exe:derivedFromMorkNode` should each be declared as subproperties of `exe:sourceGraphNode`.

### 6.2 Provenance requirements

A compiler must produce direct source links, not only transitive or narrative provenance.

For an interval-containment plan, provenance must include at least:

- the `elg:IntervalCondition`
- its `elg:requiredRangeSet`
- every `qnt:Range` in that required range set
- each lower and upper `qnt:Bound` used by the compiled comparison
- each `qnt:Value` used as a bound value
- the common `qnt:ValueSpace`
- the `elg:AdmissionProfile`, where compiling at profile scope
- the source Mork `mork:RuleMapping`, `mork:ShapeMapping`, or equivalent generative mapping
- the Mork parameter bindings that supplied or overrode executable parameters

A runtime result must include:

- its executable plan
- the evidence node or nodes evaluated
- the condition and profile declarations
- the generated artefact when one was executed
- diagnostics and the exact source nodes relevant to each diagnostic

### 6.3 Mork provenance integration

Mork already provides:

- `mork:hasRuleProvenance`
- `mork:hasConstraintProvenance`
- `mork:generatesRuleDefinition`
- `mork:generatesShapeDefinition`
- `mork:hasParameterBinding`
- `mork:dependsOnMapping`

The executable layer uses, but does not duplicate, Mork provenance records. It adds source-node tracing specific to the Eligibility and Quantification declarations used by an executable plan.

Where a natural-language source exists through `mork:IntentNode` and `mork:hasNaturalLanguageSource`, the compiler must propagate a `prov:wasDerivedFrom` path from the plan to the relevant intent node. It may also copy an immutable input hash into compiler provenance.

---

## 7. Compilation Inputs

A compiler accepts:

1. an Eligibility graph
2. a Quantification graph
3. a Mork mapping graph
4. an optional target-ontology graph
5. an optional source-schema or representation graph
6. compiler configuration, including target backends and supported value-space operations

The compiler must reject or report a non-compilable plan when required semantics are absent or ambiguous.

### 7.1 Eligibility source requirements

For an `elg:IntervalCondition`, compilation requires:

```text
- exactly one match strategy
- exactly one compatibility operation
- exactly one wildcard semantics value
- a requiredRangeSet
- a supported range kind
- a candidate evidence binding
```

The existing Eligibility shapes establish the first four structural requirements. The executable compiler adds semantic checks for range compatibility and backend support.

### 7.2 Candidate evidence binding

Eligibility declares what must be evaluated through `elg:candidateValue` or `elg:candidateRangeSet`. Mork must declare how the evaluator obtains that evidence from the target graph or input representation.

A generated mapping should therefore include one target binding for each executable input. The specific binding mechanism may be:

- an `mork:DataMapping` whose target is an Eligibility candidate property
- an `mork:ParameterBinding` with `paramType "Path"`
- a future explicit `mork:QueryTemplate` binding
- a native input adapter identified in deployment configuration

The compiler must resolve this binding before generating an executable artefact.

---

## 8. Normalised Executable Semantics

### 8.1 Condition outcomes

Every condition evaluation returns exactly one of:

| Outcome | Meaning |
|---|---|
| `elg:Permitted` | Available evidence demonstrates that the condition is satisfied. |
| `elg:Denied` | Available evidence demonstrates that the condition is not satisfied. |
| `elg:Undetermined` | Available evidence is absent, malformed, incompatible, ambiguous, or insufficient to decide. |

A compiler or evaluator must not map `Undetermined` to `Denied` unless a deployment-specific policy explicitly performs that conversion after evaluation.

### 8.2 IntervalContainment direction

For this specification, `elg:IntervalContainment` has the following normative meaning:

```text
The candidate range set is permitted when every candidate range is
contained by at least one required range in the declared required range set.
```

Formally, for candidate range set `C` and required range set `R`:

```text
Permitted if ∀ c ∈ C, ∃ r ∈ R such that c ⊆ r
Denied if C and R are comparable and ∃ c ∈ C such that no r ∈ R contains c
Undetermined if comparability or evidence is insufficient
```

This direction makes `elg:requiredRangeSet` the allowed domain and `elg:candidateRangeSet` the observed or proposed domain.

An application that requires the inverse relation, where a candidate capability must cover a required interval, must use a separate strategy value such as `elg:RequiredIntervalCoverage`. The compiler must not infer direction from labels such as “minimum” or “required”.

### 8.3 Range comparability

Two ranges are comparable only when all of the following hold:

1. Both ranges have the same `qnt:onSpace`, or the compiler can prove a supported conversion to a common value space.
2. The value space has a supported order kind.
3. Each compared endpoint is resolvable to a numeric or otherwise comparable value.
4. The compiler supports the range form, which for the first implementation is a non-cyclic linear `qnt:Range`.
5. Bound closure is declared or resolved according to the value-space default.

If any precondition fails, the result is `elg:Undetermined`.

### 8.4 Closed and open boundary semantics

For candidate range `c` and required range `r`, lower-bound containment is satisfied when:

```text
c.lower > r.lower
or
c.lower = r.lower and not (c.lower is Closed and r.lower is Open)
```

Upper-bound containment is satisfied when:

```text
c.upper < r.upper
or
c.upper = r.upper and not (c.upper is Closed and r.upper is Open)
```

Unbounded required endpoints impose no restriction on that side. An unbounded candidate endpoint is not contained by a bounded required endpoint.

The first compiler release may require both lower and upper bounds. If so, a missing bound must produce `elg:Undetermined` with `exe:UnsupportedRangeKind`, rather than silently treating the range as unbounded.

### 8.5 Point values

A `qnt:Value` may be treated as a degenerate closed range `[v, v]` only when:

- the condition accepts `elg:candidateValue`
- the value has a compatible `qnt:onSpace`
- the value does not represent a granularity interval requiring finer comparison

Otherwise, the result is `elg:Undetermined`.

---

## 9. Profile Aggregation Semantics

A profile plan evaluates its child condition plans and aggregates results according to its declared `elg:compatibilityOperation`.

### 9.1 AllRequired

```text
Denied        if any child condition is Denied
Undetermined  if no child is Denied and at least one child is Undetermined
Permitted     if every child condition is Permitted
```

### 9.2 AnySufficient

```text
Permitted     if any child condition is Permitted
Undetermined  if no child is Permitted and at least one child is Undetermined
Denied        if every child condition is Denied
```

### 9.3 DimensionConsistent

`DimensionConsistent` requires all relevant conditions to resolve against compatible dimensions, value spaces, or declared dimension keys before applying the chosen policy.

The first executable release should support this operation only where a deployment supplies an explicit dimension relation. Otherwise, it must return `elg:Undetermined` with `exe:UnsupportedRangeKind` or a dedicated `exe:DimensionResolutionAbsent` diagnostic.

---

## 10. Compilation Products

### 10.1 Executable plan

Every compilable Eligibility condition produces an `exe:ConditionPlan`. Every compilable profile produces an `exe:ProfilePlan`.

The plan is the backend-neutral, canonical compiled representation. It must record:

- source condition or profile
- strategy
- compatibility operation
- wildcard semantics
- required ranges and value space
- candidate evidence binding
- Mork mapping and parameter bindings
- compiler identity and version
- compiler input hash
- direct provenance links to all relevant source nodes

### 10.2 SPARQL artefact

The SPARQL backend produces one or more parameterised query resources.

A condition query should bind:

- candidate evidence
- required range endpoints
- bound closures
- value space
- evaluation outcome
- diagnostic code, where applicable

A profile query should aggregate condition outcomes according to Section 9.

SPARQL is the preferred generated representation for reporting a complete result set and diagnostics.

### 10.3 SHACL artefact

The SHACL backend produces:

1. readiness shapes that validate the existence and structure of required runtime evidence
2. value or SPARQL constraints that identify failed containment checks
3. diagnostic links to source condition and range nodes

SHACL conformance alone does not define `elg:Permitted`. A decision adapter must map SHACL reports into Eligibility outcomes according to the executable plan.

### 10.4 SWRL artefact

The SWRL backend produces positive, monotonic inferences only.

A SWRL rule may derive an assertion such as:

```text
ex:hasEligibilityStatus(?subject, elg:Permitted)
```

only when the relevant condition is demonstrably satisfied.

A SWRL backend must not derive `elg:Denied` merely from failure to infer permission. Open-world reasoning makes that inference invalid. Denial and indeterminacy remain responsibilities of the native or SPARQL evaluator.

### 10.5 Native artefact

The native backend produces a typed evaluator module, decision table, or serialised executable plan for a runtime service.

The native evaluator is the normative backend for:

- three-valued aggregation
- detailed diagnostics
- unsupported feature detection
- conversion context handling
- evaluation over non-RDF source data after mapping or adaptation

---

## 11. Mork Mapping Pattern

A Mork mapping graph should contain a generative mapping for every generated executable artefact.

For the interval-containment example, the compiler may receive a mapping structured as follows.

```turtle
@prefix exe:  <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix ex:   <https://example.org/lattice/eligibility/> .
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ex:credit-eligibility-rule-mapping
    a mork:RuleMapping ;
    mork:mappingScheme ex:eligibility-executable-mapping-scheme ;
    mork:hasTargetingSpec ex:credit-applicant-target ;
    mork:hasParameterBinding ex:credit-candidate-range-path ;
    mork:hasRuleProvenance ex:credit-rule-provenance ;
    mork:generatesRuleDefinition ex:credit-eligibility-rule ;
    exe:implementsCondition ex:minimum-credit-condition ;
    exe:sourceGraphNode ex:minimum-credit-condition,
                         ex:required-rangeset,
                         ex:required-range,
                         ex:lower-bound,
                         ex:upper-bound,
                         ex:lower-value,
                         ex:upper-value,
                         ex:credit-score-space .

ex:credit-applicant-target
    a mork:TargetingSpec ;
    sh:targetClass ex:Applicant .

ex:credit-candidate-range-path
    a mork:ParameterBinding ;
    mork:paramName "candidateRangeSetPath" ;
    mork:paramType "Path" ;
    mork:paramValue "https://www.nebularis.org/neuro-semantic/lattice/eligibility#candidateRangeSet" .

ex:credit-rule-provenance
    a mork:RuleProvenance ;
    mork:provenanceCreator "eligibility-compiler" ;
    mork:provenanceCreated "2026-09-17T00:00:00Z"^^xsd:dateTime ;
    mork:reviewStatus "DRAFT" ;
    mork:inputHash "sha256:..." ;
    mork:llmModelId "not-applicable" ;
    mork:llmConfidence "1.0"^^xsd:decimal ;
    mork:impactScope "advisory" .
```

`exe:implementsCondition` is introduced by this specification. It may be declared as a subproperty of `exe:sourceGraphNode`.

The matching `mork:ShapeMapping` and `mork:QueryTemplate` resources should use the same source-node set and compiler input hash.

---

## 12. Example Executable Plan

The following plan is derived from `ex:minimum-credit-condition` and `ex:profile-a`.

```turtle
@prefix exe:  <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix ex:   <https://example.org/lattice/eligibility/> .
@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

ex:minimum-credit-condition-plan
    a exe:IntervalContainmentPlan ;
    exe:implementsCondition ex:minimum-credit-condition ;
    exe:usesEvaluationStrategy elg:IntervalContainment ;
    exe:usesWildcardSemantics elg:NoWildcard ;
    exe:requiredRangeSet ex:required-rangeset ;
    exe:candidateRangeSetPath elg:candidateRangeSet ;
    exe:compiledFromMapping ex:credit-eligibility-rule-mapping ;
    exe:derivedFromEligibilityNode ex:minimum-credit-condition ;
    exe:derivedFromQuantificationNode ex:required-rangeset,
                                      ex:required-range,
                                      ex:lower-bound,
                                      ex:upper-bound,
                                      ex:lower-value,
                                      ex:upper-value,
                                      ex:credit-score-space ;
    exe:derivedFromMorkNode ex:credit-eligibility-rule-mapping ;
    prov:wasDerivedFrom ex:minimum-credit-condition,
                         ex:required-rangeset,
                         ex:required-range,
                         ex:lower-bound,
                         ex:upper-bound,
                         ex:lower-value,
                         ex:upper-value,
                         ex:credit-score-space,
                         ex:credit-eligibility-rule-mapping .

ex:profile-a-plan
    a exe:ProfilePlan ;
    exe:implementsProfile ex:profile-a ;
    exe:usesCompatibilityOperation elg:AllRequired ;
    exe:hasConditionPlan ex:minimum-credit-condition-plan ;
    exe:derivedFromEligibilityNode ex:profile-a,
                                   ex:minimum-credit-condition ;
    exe:derivedFromQuantificationNode ex:required-rangeset,
                                      ex:required-range,
                                      ex:lower-bound,
                                      ex:upper-bound,
                                      ex:lower-value,
                                      ex:upper-value,
                                      ex:credit-score-space ;
    exe:derivedFromMorkNode ex:credit-eligibility-rule-mapping .
```

---

## 13. Example Runtime Result

A runtime evaluation records both its decision and the evidence used to reach it.

```turtle
@prefix exe:  <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix ex:   <https://example.org/lattice/eligibility/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ex:evaluation-run-1
    a exe:EvaluationRun ;
    exe:forPlan ex:profile-a-plan ;
    exe:evaluatedEvidence ex:question-1,
                          ex:required-rangeset ;
    exe:hasConditionResult ex:minimum-credit-result-1 ;
    exe:hasProfileResult ex:profile-a-result-1 ;
    exe:derivedFromEligibilityNode ex:profile-a,
                                   ex:minimum-credit-condition,
                                   ex:question-1 ;
    prov:wasDerivedFrom ex:profile-a-plan,
                         ex:question-1 .

ex:minimum-credit-result-1
    a exe:ConditionResult ;
    exe:forConditionPlan ex:minimum-credit-condition-plan ;
    exe:resultValue elg:Permitted ;
    exe:derivedFromEligibilityNode ex:minimum-credit-condition,
                                   ex:question-1 ;
    prov:wasDerivedFrom ex:minimum-credit-condition-plan,
                         ex:question-1 .

ex:profile-a-result-1
    a exe:ProfileResult ;
    exe:forProfilePlan ex:profile-a-plan ;
    exe:resultValue elg:Permitted ;
    exe:derivedFromEligibilityNode ex:profile-a,
                                   ex:minimum-credit-condition,
                                   ex:question-1 ;
    prov:wasDerivedFrom ex:profile-a-plan,
                         ex:minimum-credit-result-1 .
```

For a failed evaluation, the relevant result must have `elg:Denied` and a diagnostic identifying the range that did not satisfy containment.

For an indeterminate evaluation, the result must have `elg:Undetermined` and a diagnostic such as `exe:MissingCandidateEvidence` or `exe:ValueSpaceMismatch`.

---

## 14. Compiler Algorithm

### 14.1 Compilation phases

1. Load and validate the Eligibility, Quantification, Mork, and target graphs.
2. Locate `elg:AdmissionProfile` and reachable `elg:Condition` nodes.
3. Resolve the condition strategy, compatibility operation, wildcard policy, required inputs, and candidate evidence bindings.
4. Validate strategy-specific semantic requirements.
5. Create canonical `exe:ConditionPlan` resources.
6. Create `exe:ProfilePlan` resources that aggregate condition plans.
7. Record direct provenance links to all source nodes.
8. Generate requested target artefacts.
9. Validate generated artefacts.
10. Persist compiler provenance, input hash, compiler version, and generated artefact links.

### 14.2 IntervalContainment compilation

For an `elg:IntervalCondition` with `elg:matchStrategy elg:IntervalContainment`:

1. Resolve exactly one `elg:requiredRangeSet`.
2. Resolve all `qnt:hasRange` members.
3. Resolve the `qnt:onSpace` of the range set and every member range.
4. Resolve lower and upper bounds, endpoint values, closure, and numeric values.
5. Resolve a candidate range-set or candidate-value binding.
6. Ensure the selected backend supports the value space and range form.
7. Emit an `exe:IntervalContainmentPlan`.
8. Attach source-node provenance for every traversed declaration resource.
9. Generate backend artefacts from the plan.

### 14.3 Deterministic identifiers

Generated identifiers should be stable for equivalent compilation inputs.

The recommended identifier basis is:

```text
hash(
  compiler name and version,
  canonicalised source declaration identifiers,
  canonicalised semantic parameters,
  backend target,
  target ontology version,
  source graph content hash
)
```

A change to a bound closure, numeric endpoint, value-space hash, candidate path, strategy, or compatibility operation must produce a distinct generated plan or artefact identifier.

---

## 15. Backend Requirements

### 15.1 Native evaluator requirements

The native evaluator must implement the full semantics in Sections 8 and 9.

It must:

- return one of the three Eligibility decisions
- emit structured diagnostics
- include evidence and plan provenance
- expose an evaluation trace suitable for audit
- reject unsupported semantics as `elg:Undetermined`
- avoid interpreting absent data as a failed constraint

### 15.2 SPARQL requirements

The SPARQL generator must:

- generate parameterised queries or query templates
- bind source condition and plan identifiers into result rows
- distinguish `Denied` from `Undetermined`
- return diagnostic code and source-node bindings where possible
- avoid relying on absent triples as proof of logical negation outside a closed evaluation dataset

SPARQL queries may assume a closed, explicitly designated evaluation graph. The evaluation graph identity must be recorded in `exe:EvaluationRun`.

### 15.3 SHACL requirements

The SHACL generator must produce separate constraints for:

- required candidate evidence is present
- candidate evidence has the expected range structure
- candidate and required values share a compatible value space
- candidate ranges are contained by required ranges

Every generated SHACL shape and SPARQL constraint must link to:

- the source ConditionPlan
- the source Eligibility condition
- the source required range set
- the source Mork `ShapeMapping`

### 15.4 SWRL requirements

The SWRL generator must only emit rules for cases expressible in the target reasoner.

For a scalar credit-score representation, a supported rule may use `swrlb:greaterThanOrEqual` and `swrlb:lessThanOrEqual`.

For the full `qnt:RangeSet` representation, SWRL generation requires either:

- custom built-ins for range containment, or
- prior normalisation into direct comparable scalar facts

The generated rule must be linked through:

```text
mork:RuleMapping
    mork:generatesRuleDefinition
        swrl:Imp
```

The `swrl:Imp` must also link back to its `exe:ConditionPlan` and all relevant source nodes.

---

## 16. Validation Rules

The compiler must reject compilation, or produce a non-executable plan with explicit diagnostics, for the following cases:

| Condition | Required compiler response |
|---|---|
| Missing required range set | Compilation failure. |
| Multiple conflicting strategy values | Compilation failure. |
| Candidate binding absent | Non-executable plan with `MissingCandidateEvidence` capability diagnostic. |
| Required and candidate value spaces incompatible | Runtime `Undetermined` with `ValueSpaceMismatch`, unless statically knowable at compile time. |
| Unsupported cyclic range | Non-executable plan or runtime `Undetermined` with `UnsupportedRangeKind`. |
| Missing required endpoint in a backend requiring bounded intervals | Non-executable plan with `UnsupportedRangeKind`. |
| Unresolved numeric endpoint | Runtime `Undetermined` with `GranularityInsufficient` or `CandidateRangeMalformed`. |
| Required unit conversion without context | Runtime `Undetermined` with `ConversionContextAbsent`. |
| Generated artefact does not retain required source links | Compilation failure. |

---

## 17. Conformance Levels

### Level 1. Interval-native evaluation

Supports linear, non-cyclic numeric ranges in one declared value space. Produces native evaluation results and provenance.

### Level 2. SPARQL and SHACL generation

Adds SPARQL decision queries and SHACL readiness and failure constraints derived from Level 1 plans.

### Level 3. SWRL classification

Adds positive SWRL inference for scalar or normalised interval cases supported by the selected reasoner.

### Level 4. Extended Quantification

Adds unit conversions, contextual conversion resolution, cyclic ranges, recurrence, and value granularity semantics.

A deployment claiming conformance must declare the highest supported level and the supported `qnt:ValueSpace` operation set.

---

## 18. Initial Implementation Plan

1. Define `exe:` vocabulary in a new executable-semantics specification.
2. Implement plan extraction for `elg:IntervalCondition`.
3. Implement the Level 1 native evaluator.
4. Add direct provenance materialisation for plans, results, and diagnostics.
5. Generate SPARQL `SELECT` and `ASK` artefacts from the same plans.
6. Generate SHACL readiness and containment constraints.
7. Add SWRL generation for scalar normalised credit-score conditions.
8. Add tests using `ontology/eligibility/examples/interval-containment.ttl`.

The initial test suite should cover:

- exact equality at closed endpoints
- equality at an open required endpoint
- candidate fully inside the required range
- candidate partially outside the required range
- missing candidate evidence
- mismatched value spaces
- a profile containing permitted, denied, and undetermined child conditions
- complete provenance traversal from a decision result to every source Eligibility and Quantification node
````

The key addition is the explicit `exe:sourceGraphNode` provenance relation, with specialised subproperties for Eligibility, Quantification, and Mork. That makes the provenance requirement concrete for plans, generated artefacts, decisions, and diagnostics, rather than leaving it only in compiler logs or annotations.


**There is a missing author-facing abstraction between a domain ontology’s projection contracts and Mork’s executable mappings.** Requiring a loans ontology author to write `mork:RuleMapping`, targeting specifications, parameter bindings, structured SWRL atoms, and provenance records exposes compiler internals at the wrong architectural level.

I suggest adding a **Compilation Projection Contract** layer:

```text
Domain ontology
    ↓ authored
Domain-to-LATTICE projection contracts
    ↓ deterministic expansion, optionally completed by an LLM
Mork mappings
    ↓ validation
Executable semantics plans
    ↓ deterministic compilation
SPARQL, SHACL, SWRL, or native artefacts
```

## 1. The architectural gap

The repository already establishes two relevant boundaries:

1. LATTICE substrates are domain-neutral.
2. Applied ontologies connect to substrates through `projection/` contracts.

Mork currently addresses a different boundary:

```text
source material or intent
    → target ontology mappings
    → generated artefacts
```

The proposed executable semantics layer would add:

```text
Eligibility declarations
    → executable plans
    → generated artefacts
```

What remains missing is a declaration of **how a domain ontology uses an abstract substrate operationally**.

For a loans ontology, this includes questions such as:

- Which class is the subject of an eligibility evaluation?
- Which property supplies a candidate credit score?
- Is the property value already a `qnt:Quantity`, or must a decimal literal be lifted into one?
- Which domain property should receive a resulting decision?
- Should the result be materialised as a class assertion, an object-property assertion, or an `elg:EligibilityDecision`?
- Which artefacts should be generated?
- Does missing evidence mean `Undetermined`, or should a later deployment policy reject the application?
- Is the evaluation graph treated as closed for this operation?
- Which Mork templates and compiler capabilities are allowed?

These are stable domain integration choices. They should be authored once in a domain `projection/` file, rather than repeated in every Mork mapping.

## 2. Three distinct kinds of knowledge

The design should distinguish three graph layers.

### 2.1 Domain projection knowledge

Authored and governed by the domain ontology author.

It says:

> In the loans domain, `loans:creditScore` supplies the candidate value for an Eligibility interval condition evaluated against `loans:LoanApplication`.

This layer should be concise, declarative, reusable, and independent of SWRL or SPARQL syntax.

### 2.2 Mork compilation knowledge

Generated or proposed from the projection contract and the concrete eligibility declarations.

It says:

> Generate this `mork:RuleMapping`, with these target bindings, parameters, dependencies, provenance records, and structured output definitions.

This layer contains compiler-oriented details. Domain authors may inspect or override it, but should not normally author it from scratch.

### 2.3 Executable semantics

Generated deterministically from validated Mork.

It contains:

- executable plans
- SPARQL query templates
- SHACL shapes and rules
- SWRL rules
- native evaluator plans
- runtime result and diagnostic vocabulary

Conflating these layers would make domain projections backend-specific and make Mork mappings unnecessarily repetitive.

## 3. Proposed abstraction

A useful name would be **Executable Projection Contract**.

The term “projection” fits the repository convention, while “executable” distinguishes it from purely ontological alignment. An executable projection contract binds domain ontology elements to named roles in a LATTICE semantic operation.

The contract should answer four questions:

1. **What substrate operation is being used?**
2. **Which domain resources fill its semantic roles?**
3. **How should its result appear in the domain graph?**
4. **Which compilation capabilities are requested or permitted?**

The contract is not itself a Mork mapping. It is input from which Mork mappings can be generated.

## 4. Recommended conceptual model

The executable layer could define a small projection vocabulary.

```turtle name=executable-projection-vocabulary.ttl
@prefix exp:  <https://www.nebularis.org/neuro-semantic/lattice/executable-projection#> .
@prefix exe:  <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

exp:ExecutableProjectionContract
    a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Governable ;
    rdfs:comment "A governed declaration of how a domain ontology binds its classes and properties to an executable LATTICE substrate operation." .

exp:OperationBinding
    a owl:Class ;
    rdfs:comment "A binding between a semantic role in an executable operation and a domain ontology resource." .

exp:ResultBinding
    a owl:Class ;
    rdfs:comment "A declaration of how an evaluation result is represented in the domain ontology." .

exp:usesOperation
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:range exe:ExecutableOperation .

exp:targetClass
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:range owl:Class .

exp:hasBinding
    a owl:ObjectProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:range exp:OperationBinding .

exp:bindsRole
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:OperationBinding ;
    rdfs:range exe:OperationRole .

exp:bindsProperty
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:OperationBinding ;
    rdfs:range rdf:Property .

exp:hasResultBinding
    a owl:ObjectProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:range exp:ResultBinding .

exp:resultProperty
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:ResultBinding ;
    rdfs:range rdf:Property .

exp:resultClass
    a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain exp:ResultBinding ;
    rdfs:range owl:Class .

exp:requestsBackend
    a owl:ObjectProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:range exe:Backend .

exp:allowsTemplate
    a owl:ObjectProperty ;
    rdfs:domain exp:ExecutableProjectionContract ;
    rdfs:comment "Identifies a governed Mork shape, rule, query, or transform template that may be instantiated." .
```

This is deliberately smaller than Mork. It describes a domain projection onto an executable operation without reproducing the complete Mork vocabulary.

## 5. Operations need named roles

A reusable operation must advertise the roles a projection contract can bind.

For interval containment, the operation signature could be:

```text
IntervalContainment(
    subject,
    candidateEvidence,
    requiredRangeSet,
    decisionTarget
) → Decision
```

The executable semantics layer can represent that signature explicitly:

```turtle name=eligibility-executable-operations.ttl
@prefix exe: <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .

exe:IntervalContainment
    a exe:ExecutableOperation ;
    exe:implementsStrategy elg:IntervalContainment ;
    exe:requiresRole exe:EvaluationSubject,
                     exe:CandidateEvidence ;
    exe:acceptsRole exe:DecisionTarget ;
    exe:readsDeclarationProperty elg:requiredRangeSet .

exe:EvaluationSubject
    a exe:OperationRole .

exe:CandidateEvidence
    a exe:OperationRole ;
    exe:expectedValueClass qnt:Value ;
    exe:alternativeValueClass qnt:RangeSet .

exe:DecisionTarget
    a exe:OperationRole ;
    exe:expectedValueClass elg:Decision .
```

The required range set is usually supplied by the Eligibility declaration itself. The domain author therefore does not need to bind it repeatedly.

The domain projection primarily supplies the domain-facing roles, such as subject, candidate evidence, and result representation.

## 6. Example loans projection

A loans ontology could contain:

```turtle name=loans/projection/eligibility.ttl
@prefix loans: <https://example.org/loans#> .
@prefix exp:   <https://www.nebularis.org/neuro-semantic/lattice/executable-projection#> .
@prefix exe:   <https://www.nebularis.org/neuro-semantic/lattice/executable#> .
@prefix fnd:   <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .

loans:CreditScoreEligibilityProjection
    a exp:ExecutableProjectionContract ;
    exp:usesOperation exe:IntervalContainment ;
    exp:targetClass loans:LoanApplication ;
    exp:hasBinding loans:CreditScoreCandidateBinding ;
    exp:hasResultBinding loans:EligibilityDecisionBinding ;
    exp:requestsBackend exe:SparqlBackend,
                        exe:ShaclBackend ;
    fnd:governanceState fnd:Approved .

loans:CreditScoreCandidateBinding
    a exp:OperationBinding ;
    exp:bindsRole exe:CandidateEvidence ;
    exp:bindsProperty loans:creditScore .

loans:EligibilityDecisionBinding
    a exp:ResultBinding ;
    exp:resultProperty loans:hasEligibilityDecision .
```

This is much closer to what a domain ontology author knows and controls:

- loan applications carry credit scores
- credit scores are candidate evidence
- decisions are attached using a domain property
- SPARQL and SHACL artefacts are wanted

The author does not need to understand:

- `swrl:Imp` RDF lists
- Mork rule provenance structure
- compiler parameters
- target query serialization
- generated variable names
- Mork precedence nodes
- the exact shape of a SHACL-SPARQL constraint

## 7. Projection contracts should be ontology-level and reusable

A projection contract is normally about a **domain schema**, not one condition instance.

For example:

```text
loans:creditScore
    → candidate evidence for interval eligibility
```

can support many concrete conditions:

- credit score between 700 and 850
- credit score at least 650
- credit score within a product-specific range
- different profiles for different loan products

The condition instances supply the bounds and strategy. The projection supplies the domain access path.

This gives the compiler two complementary inputs:

```text
Projection:
    Candidate evidence comes from loans:creditScore

Eligibility declaration:
    Required range is [700, 850]
```

From these, it can produce a concrete Mork mapping and executable plan.

## 8. Projection expansion into Mork

The projection compiler should lower a domain contract into one or more Mork mappings.

For example:

```text
loans:CreditScoreEligibilityProjection
        +
ex:minimum-credit-condition
        ↓
generated Mork ShapeMapping
generated Mork RuleMapping
generated Mork QueryTemplate
```

The generated Mork graph may contain more detail than the source contract:

- `mork:hasTargetingSpec`
- `mork:hasParameterBinding`
- `mork:dependsOnMapping`
- `mork:hasShapeTemplate`
- `mork:hasRuleTemplate`
- `mork:generatesShapeDefinition`
- `mork:generatesRuleDefinition`
- constraint or rule provenance
- target ontology matches
- execution precedence

This is appropriate because Mork is the compilation graph. The projection contract is the domain integration graph.

## 9. Template selection

Mork’s existing `ShapeTemplate` and `RuleTemplate` concepts provide a useful connection point.

The executable substrate could publish governed templates such as:

```text
IntervalContainmentSparqlTemplate
IntervalContainmentShaclTemplate
ScalarIntervalSwrlTemplate
AllRequiredAggregationTemplate
AnySufficientAggregationTemplate
```

A projection contract may:

- explicitly select an allowed template
- accept the substrate’s default template
- constrain the permitted template catalog
- prohibit a backend it cannot represent safely

For example:

```turtle name=loans/projection/eligibility.ttl
loans:CreditScoreEligibilityProjection
    exp:allowsTemplate exe:IntervalContainmentSparqlTemplate,
                       exe:IntervalContainmentShaclTemplate .
```

The generated Mork mapping would then instantiate these as `mork:QueryTemplate` or `mork:ShapeMapping` resources with the concrete domain and condition parameters.

This gives domain authors controlled extensibility without requiring them to author compiler internals.

## 10. Type adaptation

A major concern is that domain properties will not always use the substrate’s preferred representation.

For example:

```turtle
loans:creditScore
    rdfs:range xsd:decimal .
```

while the executable operation expects a `qnt:Value` or `qnt:RangeSet`.

The projection layer should therefore support an optional adapter declaration.

```turtle name=loans/projection/eligibility.ttl
loans:CreditScoreCandidateBinding
    a exp:OperationBinding ;
    exp:bindsRole exe:CandidateEvidence ;
    exp:bindsProperty loans:creditScore ;
    exp:usesAdapter exe:DecimalToPointValue ;
    exp:usesValueSpace loans:CreditScoreValueSpace .
```

`exe:DecimalToPointValue` would mean:

```text
decimal literal v
    ↦ qnt:Quantity {
          qnt:numericValue v
          qnt:onSpace loans:CreditScoreValueSpace
      }
```

Adapters must be declared operations with defined input and output types. They should not be arbitrary code referenced by string.

Some adapters could compile into RML, SPARQL `BIND`, SHACL functions, or native code. Their use would become another generated Mork dependency.

## 11. Result projection

The executable layer returns an abstract Eligibility decision. A domain ontology may want to represent the result in several ways.

### 11.1 Eligibility decision individual

```text
LoanApplication
    → loans:hasEligibilityDecision
    → elg:EligibilityDecision
```

This retains evidence, diagnostics, profile, and provenance.

### 11.2 Direct status property

```text
LoanApplication
    → loans:eligibilityStatus
    → elg:Permitted
```

This is simpler but loses detail unless the complete evaluation result remains elsewhere.

### 11.3 Classification

```text
LoanApplication rdf:type loans:CreditEligibleApplication
```

This works for positive monotonic inference. It does not represent denial or indeterminacy well.

The projection contract should state which representation is desired. A compiler should prefer generating an `elg:EligibilityDecision` and optionally materialise a domain convenience projection from it.

## 12. LLM participation

The LLM should operate as a proposal mechanism over incomplete projection contracts, rather than being the only way to create Mork mappings.

A useful generation hierarchy is:

### 12.1 Fully deterministic

The projection contract explicitly identifies:

- operation
- target class
- evidence property
- value space
- adapter
- result binding
- backends or templates

The system generates Mork without an LLM.

### 12.2 Deterministic bootstrap with bounded selection

The contract supplies the semantic bindings but omits a template or adapter. The compiler selects from a governed catalog using type compatibility and declared defaults.

No LLM is needed.

### 12.3 LLM-assisted completion

The contract identifies the target operation and class but omits a candidate property or result property. The LLM proposes bindings using:

- ontology labels and definitions
- domains and ranges
- restrictions
- existing projection contracts
- approved prior Mork mappings
- substrate operation signatures

The proposal is written as a candidate projection amendment or candidate Mork graph and passed through validation.

### 12.4 Discovery without a projection contract

The LLM attempts to infer the whole projection from the domain ontology. This may bootstrap adoption, but the result must be treated as a proposed projection contract requiring review.

The reviewed projection should then become the durable source. Future Mork generation should use it deterministically.

This avoids making the LLM repeat the same ontology-alignment decision for every eligibility rule.

## 13. Provenance

The provenance chain should be extended to include the domain projection contract.

```text
Original domain and Eligibility nodes
        ↓
Executable Projection Contract
        ↓
Generated or completed Mork mapping
        ↓
Executable plan
        ↓
SPARQL, SHACL, SWRL, or native artefact
        ↓
Evaluation result and diagnostics
```

Every generated Mork mapping should have direct provenance to:

- the executable projection contract
- each operation binding used
- the source Eligibility condition
- the source AdmissionProfile
- the relevant Quantification nodes
- any adapter or template selected
- any LLM proposal activity, where one occurred

Conceptually:

```turtle name=generated-mork-provenance.ttl
ex:GeneratedCreditScoreRuleMapping
    a mork:RuleMapping ;
    prov:wasDerivedFrom
        loans:CreditScoreEligibilityProjection,
        loans:CreditScoreCandidateBinding,
        loans:EligibilityDecisionBinding,
        ex:minimum-credit-condition,
        ex:required-rangeset ;
    exe:derivedFromProjection
        loans:CreditScoreEligibilityProjection ;
    exe:derivedFromEligibilityNode
        ex:minimum-credit-condition ;
    exe:derivedFromQuantificationNode
        ex:required-rangeset,
        ex:required-range,
        ex:lower-bound,
        ex:upper-bound .
```

This adds the missing explanation:

> The generated rule reads `loans:creditScore` because the loans ontology’s approved projection contract binds that property to the candidate-evidence role.

Without that link, provenance could explain which condition produced a rule but not why a particular domain property was used to implement it.

## 14. Governance and versioning

Projection contracts should be first-class governed and versioned resources.

A change such as:

```text
loans:creditScore
    → loans:assessment/credit/score
```

is a domain integration change. It should trigger regeneration of affected Mork mappings and artefacts without modifying the source Eligibility declarations.

The dependency model becomes:

| Change | Required response |
|---|---|
| Eligibility bounds change | Regenerate plans and artefacts for affected conditions. |
| Domain evidence property changes | Version projection contract and regenerate dependent Mork mappings. |
| Mork vocabulary changes | Migrate or regenerate Mork mappings. |
| Compiler backend changes | Regenerate artefacts from validated mappings. |
| Domain ontology refactors unrelated terms | No eligibility recompilation. |
| Template is superseded | Regenerate mappings or artefacts using the replacement template after review. |

Projection contracts should have stable identifiers, governance state, effective dates, and supersession links through Foundation.

## 15. Validation responsibilities

A projection contract validator should check:

### Structural validity

- exactly one executable operation
- exactly one target class where the operation requires one
- required operation roles are bound
- no role is multiply bound unless declared multi-valued
- requested backends are recognized

### Ontological validity

- target class exists
- bound property exists
- property domain is compatible with the target class
- property range is compatible with the operation role
- any adapter accepts the bound range and produces the expected role type
- result property range is compatible with the result representation

### Compilation validity

- a supported template exists for the operation and backend
- required Mork parameters can be derived
- dependencies are acyclic
- all generated Mork nodes can satisfy their shapes and completeness requirements

### Governance validity

- projection contract is approved for production compilation
- selected templates are approved
- domain ontology and substrate versions are within declared compatibility ranges
- LLM-generated bindings have the required review state

## 16. Relationship to ordinary ontology axioms

Some simple projections may look expressible with:

```turtle
loans:creditScore rdfs:subPropertyOf elg:candidateValue .
```

That should not be the general mechanism.

A subproperty assertion changes entailment semantics throughout the graph. It cannot conveniently express:

- target class scoping
- property-path bindings
- literal-to-quantity adaptation
- value-space selection
- result materialisation
- backend selection
- missing-data policy
- template constraints
- governance and effective dates
- different roles for the same property in different operations

A reified projection contract provides these details without asserting that two properties are globally equivalent or hierarchical.

OWL property alignment can still be used where it is semantically true. It may allow the projection compiler to infer a binding, but it should not replace the contract for operational compilation.

## 17. Repository placement

There are two reasonable ownership locations.

### Substrate definitions

The executable semantics layer defines:

- executable operations
- operation roles
- backend capabilities
- adapter signatures
- template contracts
- projection vocabulary and validation shapes

For example:

```text
executable/
├── README.md
├── spec/executable.ttl
├── shapes/
│   ├── structural.ttl
│   └── constraints.ttl
├── vocab/executable-vocab.ttl
└── projection/
    ├── eligibility.ttl
    └── quantification.ttl
```

### Domain declarations

The loans ontology authors:

```text
loans/
├── README.md
├── spec/loans.ttl
├── shapes/
├── vocab/
└── projection/
    ├── eligibility.ttl
    ├── quantification.ttl
    └── executable.ttl
```

I would put substrate semantic alignment in `loans/projection/eligibility.ttl` and operational compiler preferences in `loans/projection/executable.ttl`. A small ontology might combine them.

## 18. Revised end-to-end model

The complete pipeline would have five conceptual stages:

```text
1. DOMAIN
   loans:LoanApplication
   loans:creditScore

2. PROJECTION
   creditScore binds CandidateEvidence
   LoanApplication binds EvaluationSubject

3. MORK
   generated RuleMapping, ShapeMapping, QueryTemplate
   target specifications, parameters, dependencies, provenance

4. EXECUTABLE PLAN
   IntervalContainmentPlan
   AllRequired aggregation
   three-valued decision semantics

5. ARTEFACTS AND RESULTS
   SPARQL, SHACL, SWRL, native checks
   decisions, diagnostics, complete provenance
```

This preserves Mork’s existing `Intent → Mapping → Artefact` architecture while adding a durable source of domain-specific mapping knowledge:

```text
Domain Projection → Mork Mapping → Artefact
```

The projection is effectively a reusable, governed **mapping generator specification**.

## 19. Recommendation

The executable semantics design should be revised to introduce two related abstractions:

1. **Executable operation signatures**, owned by the substrate. These declare semantic roles, accepted types, results, and supported compilation capabilities.
2. **Executable projection contracts**, owned by domain ontologies. These bind domain classes and properties to those roles.

Mork then becomes the expanded, validated compilation form rather than the normal authoring surface.

This supports three adoption modes:

- hand-authored projection and deterministic Mork generation
- partial projection with compiler-driven template selection
- LLM-proposed projection or Mork completion followed by validation and review

The key architectural principle is:

> **Domain authors declare how their ontology participates in LATTICE operations. Mork records how a particular declaration is compiled.**

That boundary reduces authoring effort, improves reuse across many conditions, provides a stable review surface, and adds the missing provenance explanation between abstract Eligibility semantics and concrete domain properties.
