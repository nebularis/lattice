<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 7. Amounts and reference data
{: #amounts}

Two kinds of value fill a contract's blanks: amounts, such as a 25,000,000 GBP commitment, and codes
from a list, such as an industry sector. A warehouse handles the first with measure definitions and
the second with reference tables, and keeps the rules for each in documentation or BI tooling.
LATTICE puts those rules in the data. Quantification covers amounts, and Vocabulary covers code
lists.

### Every amount lives in a value space

A **value space** declares a kind of value: how its values are ordered, whether they need a unit,
which units, and which operations make sense. Here is money, from Quantification's example of a
multicurrency facility.

<!-- source: ontology/quantification/examples/additivity.ttl -->
```turtle
ex:money a qnt:ValueSpace ;
    qnt:spaceKey "money" ; qnt:orderKind qnt:TotalOrder ; qnt:densityKind qnt:Dense ;
    qnt:spaceHash "money-v1" ;
    qnt:additivity qnt:Extensive ;
    qnt:unitContract [ a qnt:UnitContract ; qnt:requiresUnit true ;
                       qnt:unitFamily ex:currencies ; qnt:canonicalUnit ex:EUR ] ;
    qnt:hasOperationCapability ex:money-compare , ex:money-sum .

ex:money-compare a qnt:OperationCapability ; qnt:operationKind qnt:Compare .
ex:money-sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ;
    qnt:hasOperand [ a qnt:OperationOperand ; qnt:operandIndex 0 ; qnt:operandSpace ex:money ] ,
                   [ a qnt:OperationOperand ; qnt:operandIndex 1 ; qnt:operandSpace ex:money ] ;
    qnt:resultSpace ex:money .
```

- **`qnt:additivity`** is the rule a dimensional modeller knows as additive or non-additive measures.
  `qnt:Extensive` means the measure of a whole is the sum of its parts, as money is.
  `qnt:Intensive` means values may be compared and counted but never added, as with ratios or a
  severity grade.
- **The unit contract** says every money value must carry a currency from one family, and names the
  euro as the canonical unit.
- **Operation capabilities** list what may be done with the values. Money may be compared and summed,
  and a sum of two money values is money.

A **quantity** is then a number on a space, in a unit.

<!-- source: ontology/quantification/examples/additivity.ttl -->
```turtle
ex:commitment-1 a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 60000000 ; qnt:inUnit ex:EUR .
ex:commitment-2 a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 30000000 ; qnt:inUnit ex:EUR .
ex:commitment-3 a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 22000000 ; qnt:inUnit ex:USD .
```

### Adding needs a context, and sometimes the answer is "undetermined"

The first two commitments add to EUR 90m at any time. Adding the third needs an exchange rate, and a
rate is an observation on a date. Quantification records conversions as **contextual**, valid only
with a rate for the moment of evaluation.

<!-- source: ontology/quantification/examples/additivity.ttl -->
```turtle
# Exchange rates are observations at a date, so each conversion is Contextual.
ex:fx-spot a qnt:ConversionFunction ; rdfs:label "spot exchange rate on the context's date" .
ex:usd-to-eur a qnt:Conversion ; qnt:fromUnit ex:USD ; qnt:toUnit ex:EUR ;
    qnt:conversionKind qnt:Contextual ; qnt:conversionFunction ex:fx-spot .
```

The example records a rate of 0.9 for 31 March 2027 and none for 30 April. So the total of all three
commitments is EUR 109.8m as at 31 March, and **undetermined** as at 30 April, with the reason that
no conversion context exists. A SQL `SUM` over a currency column would have returned a number either
way, and a wrong one on both days.

### A limit stated two ways

Facility agreements often state a limit in two currencies. Quantification keeps both statements and
does not infer a rate from them.

<!-- source: ontology/quantification/examples/additivity.ttl -->
```turtle
# The limit is one bound stated in two currencies. Neither statement implies a
# rate, so a candidate is compared with the statement in its own unit (ADR-A95).
ex:limit-eur a qnt:Bound ; qnt:onSpace ex:money ; qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed ;
    qnt:boundValue [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 110000000 ; qnt:inUnit ex:EUR ] ;
    qnt:alternativeBound ex:limit-usd .
ex:limit-usd a qnt:Bound ; qnt:onSpace ex:money ; qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed ;
    qnt:boundValue [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 120000000 ; qnt:inUnit ex:USD ] .
```

A **bound** is one end of a range, upper here and closed, meaning "at most". EUR 109.8m is within the
EUR statement of the limit. A total reported as GBP 95m is undetermined, because the limit is not
stated in sterling, even though a sterling rate is on file. The contract never set a sterling limit,
and the model does not invent one.

Every outcome in the example's header, with its reason, is
[on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/quantification/examples/additivity.ttl).

### Code lists: which list, for which contract, from when

A property such as `cls:industry`, from chapter 1, ranges over `skos:Concept`, any entry in any code
list. Vocabulary decides which list applies, in three steps.

1. A **scheme contract** says, structurally, what a property's list must satisfy, such as which
   property it serves and what governance state the list must be in. It never says what the list
   is about.
2. A **scheme binding** names the list that meets the contract, with a validity period and,
   optionally, a scope such as one lender or one region.
3. At evaluation, a **resolver** picks the binding that applies to the context and the moment.

The classification module declares the first step for industry.

<!-- source: ontology/applied/classification/vocab/classification-vocab.ttl -->
```turtle
cls-voc:IndustryContract a voc:SchemeContract ;
    fnd:hasIdentity cls-voc:IndustryContract-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Industry scheme contract"@en ;
    voc:constrainsProperty cls:industry .
```

Here is the second step, a code list handed over to its next edition at midnight on 1 July 2026.

<!-- source: ontology/vocabulary/examples/temporal-handover.ttl -->
```turtle
ex:handover-binding-v1 a voc:SchemeBinding ;
    voc:forContract ex:handover-contract ;
    voc:bindsScheme ex:handover-scheme-v1 ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ;
        fnd:validTo   "2026-07-01T00:00:00Z"^^xsd:dateTime
    ] .

ex:handover-binding-v2 a voc:SchemeBinding ;
    voc:forContract ex:handover-contract ;
    voc:bindsScheme ex:handover-scheme-v2 ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-07-01T00:00:00Z"^^xsd:dateTime
    ] .
```

One binding ends exactly where the next begins, so a question asked at any instant sees exactly one
list. A data architect would recognise an effective-dated mapping table from attribute to code set,
with a tenant or region column for scope. The difference is that the mapping is governed data with
its own shapes and resolution rules, rather than configuration each application reads its own way.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/vocabulary/examples/temporal-handover.ttl).

Two consequences follow. A substrate layer never names a business code, so the same Eligibility
rule can run against one lender's sector list and another's industry classification. Chapter 8 does
exactly that. And a code list is itself versioned under chapter 4's rules, so "which edition of the
sector list applied when this facility was approved" has an answer.
