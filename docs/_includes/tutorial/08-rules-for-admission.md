<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 8. Rules for admission
{: #eligibility}

A credit policy decides who may borrow. A covenant decides whether the borrower is within its
limits. In most systems such rules live in application code, a rules engine or a `CASE` expression,
and their answer is a boolean someone stores. Eligibility states the rule as data, asks a question
of it, and gets one of three answers: **Permitted**, **Denied** or **Undetermined**.

### A condition is a rule, stated once

The lender's credit policy admits borrowers in manufacturing or retail, but not textiles.

<!-- source: ontology/eligibility/examples/flat-scheme-lending.ttl -->
```turtle
ex:eligible-sector a elg:Condition ;
    elg:matchStrategy elg:HierarchicalMatch ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:constrainedByContract ex:sector-contract ;
    elg:requiredConcept ex:manufacturing , ex:retail ;
    elg:excludedConcept ex:textiles .
```

- **`elg:requiredConcept`** and **`elg:excludedConcept`** are the admitted and refused values.
- **`elg:matchStrategy`** says how a candidate is compared with them. `elg:HierarchicalMatch` lets a
  narrower concept count as its broader one, so a food processor counts as manufacturing. The other
  strategies are an exact match, membership of a set, containment in a numeric interval, and a
  wildcard.
- **`elg:constrainedByContract`** ties the condition to a Vocabulary scheme contract from chapter 7,
  so which code list it reads is decided by binding, not written into the rule.

The code list here is a small industry classification.

<!-- source: ontology/eligibility/examples/flat-scheme-lending.ttl -->
```turtle
ex:manufacturing a skos:Concept ; skos:prefLabel "Manufacturing"@en ;
    skos:inScheme ex:industry-classification .
ex:food-processing a skos:Concept ; skos:prefLabel "Food processing"@en ;
    skos:broader ex:manufacturing ;
    skos:inScheme ex:industry-classification , ex:lender-b-sectors .
ex:textiles a skos:Concept ; skos:prefLabel "Textiles"@en ;
    skos:broader ex:manufacturing ;
    skos:inScheme ex:industry-classification , ex:lender-b-sectors .
ex:retail a skos:Concept ; skos:prefLabel "Retail"@en ;
    skos:inScheme ex:industry-classification , ex:lender-b-sectors .
ex:wholesale a skos:Concept ; skos:prefLabel "Wholesale"@en ;
    skos:inScheme ex:industry-classification , ex:lender-b-sectors .
```

`skos:broader` is the parent link of a hierarchy, the counterpart of a parent column in a
self-referencing reference table. Food processing and textiles sit under manufacturing. Several of
the concepts are also members of a second list, lender B's own flat list of sector codes, which has
no hierarchy.

### A question asks the condition about one candidate

<!-- source: ontology/eligibility/examples/flat-scheme-lending.ttl -->
```turtle
ex:q-food-processing a elg:Question ;
    elg:forCondition ex:eligible-sector ; elg:candidateConcept ex:food-processing .
```

The condition is the rule. The question is one application of it. Its answer is not authored here.
It is evaluated.

### Same rule, two code lists, different answers

For lender B, the sector contract resolves to lender B's flat list, through a scoped binding.

<!-- source: ontology/eligibility/examples/flat-scheme-lending.ttl -->
```turtle
ex:lender-b-binding a voc:SchemeBinding ;
    voc:forContract ex:sector-contract ;
    voc:bindsScheme ex:lender-b-sectors ;
    voc:bindingScope ex:lender-b ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime
    ] .
```

The example records what evaluation gives for each candidate under each list.

| Candidate | Under the classification | Under lender B's flat list |
|---|---|---|
| food processing | Permitted, as it sits below manufacturing | **Undetermined**, the list has no hierarchy |
| textiles | Denied, it is excluded | Denied, it is excluded |
| retail | Permitted, it is required | Permitted, it is required |
| wholesale | Denied, outside both required concepts | **Undetermined**, the list has no hierarchy |

Read the two undetermined answers carefully. Lender B's list cannot say whether food processing is a
kind of manufacturing, because the list asserts no hierarchy. The classification's own parent links
are still in the graph, but a hierarchical match reads only the ordering among the bound list's own
members. A two-valued system would have to guess, and would usually guess "no". Eligibility reports
that the rule cannot be decided with the data given, and the reason. That answer can be routed to a
person rather than silently refusing a borrower.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/eligibility/examples/flat-scheme-lending.ttl).

### Numeric rules: the leverage covenant

The facility's leverage covenant from chapter 6 maintained a condition called `ex:leverage-ok`. It
is an interval condition over a range, built from Quantification's bounds.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:leverage-space a qnt:ValueSpace ;
    qnt:spaceKey "leverage-ratio" ; qnt:orderKind qnt:TotalOrder ; qnt:densityKind qnt:Dense ;
    qnt:spaceHash "leverage-ratio-v1" .
ex:three a qnt:Quantity ; qnt:onSpace ex:leverage-space ; qnt:numericValue "3.0"^^xsd:decimal .
ex:at-most-three a qnt:Bound ;
    qnt:onSpace ex:leverage-space ; qnt:boundValue ex:three ; qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed .
ex:up-to-three a qnt:Range ; qnt:onSpace ex:leverage-space ; qnt:upperBound ex:at-most-three ; qnt:hasBound ex:at-most-three .
ex:permitted-leverage a qnt:RangeSet ; qnt:onSpace ex:leverage-space ; qnt:hasRange ex:up-to-three .

ex:leverage-ok a elg:IntervalCondition ;
    elg:conditionKey "leverage-within-covenant" ;
    elg:matchStrategy elg:IntervalContainment ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:requiredRangeSet ex:permitted-leverage .
```

Read from the bottom up. The condition admits a value contained in the permitted range set. The set
holds one range, whose upper bound is 3.0 and closed, so "at most 3.0". It is the `CHECK (leverage
<= 3.0)` of a relational design, with two differences. The ceiling is a value with its own space, so
in a facility drawn from a form it can come from a blank, as Halden's 3.5 did in chapter 5. And a
leverage figure that has not been reported yields Undetermined, not a failed check.

### Where the candidate comes from, and who evaluates

The examples here author their questions by hand. In practice a condition is usually bound to a class
of your own with an **evidence binding**, which says which property path supplies the candidate, so
every borrower or employee is evaluated without a question being written for each.
[Eligibility's evidence binding example](https://github.com/nebularis/lattice/blob/main/ontology/eligibility/examples/evidence-binding.ttl)
does this for a relocation benefit.

The layer itself never computes anything. Evaluation is done by code. LATTICE ships compilers that
turn conditions into SPARQL queries and SHACL shapes (`tools/mork_compilers`), and an independent
reference evaluator written in Python (`tools/reference/eligibility`). The two are tested against each
other, so the same question gives the same answer whichever way it is run.
