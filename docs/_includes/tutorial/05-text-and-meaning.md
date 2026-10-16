<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 5. Text and meaning
{: #wording}

A contract's legal force comes from its words. A court reads the wording the parties signed, not a
database. So LATTICE keeps two things side by side and ties every piece of meaning back to the words
that create it.

- **Wording** (`wrd:`) holds the text exactly as written, and how it is built: sections, clauses,
  definitions, blanks to fill in, and documents it relies on.
- **Instrument** (`ins:`) holds what the text means in law, the subject of chapter 6.

If the two ever disagree, the words win and the data is wrong. This chapter covers the words, and how
one lender's form becomes the text of one signed facility.

### A document is an ordered tree

<!-- source: ontology/wording/examples/facility-agreement.ttl -->
```turtle
ex:facility-wording a wrd:Wording ;
    fnd:hasIdentity ex:facility-wording-identity ;
    fnd:hasGovernanceState fnd:Active ;
    wrd:directlyComprises ex:sec-1 , ex:sec-4 , ex:annex-1 .
```

The wording comprises sections, which comprise clauses, much as a bill of materials comprises
assemblies and parts. Every element, down to a single clause, has its own persistent identity from
chapter 4. A clause can therefore be reused in several forms, or survive a revision of its form
unchanged, as one version of one thing.

<!-- source: ontology/wording/examples/facility-agreement.ttl -->
```turtle
ex:sec-4 a wrd:Element ;
    fnd:hasIdentity ex:sec-4-identity ;
    fnd:hasGovernanceState fnd:Active ;
    wrd:elementType wrd-voc:Section ;
    wrd:objectId "4" ;
    wrd:rankKey "d0" ;
    wrd:directlyComprises ex:cl-4-1 , ex:cl-4-2 , ex:var-margin .
```

Two properties do jobs that a relational design often gives to one column.

- **`wrd:objectId`** is the number a reader sees, "4" or "4.1". It is a label, and never identity.
- **`wrd:rankKey`** orders siblings, compared as strings. Because `"a0"` sorts before `"b0"`, a new
  clause can be slotted between two others with a key such as `"a5"`, and nothing is renumbered.
  Inserting a clause before 4.1 changes what a reader sees, never the clause's identity.

If you have suffered a `sequence_no` column that has to be rewritten on every insert, this is the
fix.

### A clause is a sequence of parts

Clause 4.1 reads "The Borrower shall pay interest at {margin} per annum." Wording stores it as five
parts.

<!-- source: ontology/wording/examples/facility-agreement.ttl -->
```turtle
ex:cl-4-1-p0 a wrd:TextPart ; 
    wrd:partIndex 0 ; wrd:partText "The " .
ex:cl-4-1-p1 a wrd:TextPart ; 
    wrd:partIndex 1 ; wrd:refersToObject ex:def-borrower-identity ;
    wrd:displayText "Borrower" .
ex:cl-4-1-p2 a wrd:TextPart ; 
    wrd:partIndex 2 ; wrd:partText " shall pay interest at " .
ex:cl-4-1-p3 a wrd:TextPart ; 
    wrd:partIndex 3 ; wrd:refersToVariable ex:var-margin-identity .
ex:cl-4-1-p4 a wrd:TextPart ; 
    wrd:partIndex 4 ; wrd:partText " per annum." .
```

Three parts are plain text. Part 1 is a reference to the definition of "Borrower", so a tool can
follow it to clause 1.1. Part 3 is the blank, a reference to a variable. The references name
persistent identities, not versions. The wording that holds the clause fixes which version each one
means, which is how a definition can be widened in a new edition of the form without touching
clause 4.1.

### Blanks are typed

<!-- source: ontology/wording/examples/facility-agreement.ttl -->
```turtle
ex:var-margin a wrd:EmbeddedVariable ;
    fnd:hasIdentity ex:var-margin-identity ;
    fnd:hasGovernanceState fnd:Active ;
    wrd:variableKey "margin" ;
    wrd:rankKey "z0" ;
    wrd:valueSpace ex:annual-rate-space ;
    wrd:multiValued false .
```

The margin is not a free-text field. It has a value space, a declared kind of value from the
Quantification layer (chapter 7), and it is single-valued. A form's blanks are its parameters,
declared with their types as a stored procedure declares its arguments.

### Text the wording relies on but does not hold

Clause 4.2 relies on a repayment plan attached as an annex, a scanned document rather than digitised
text. Wording records the document as a thing with its own identity, and says which edition the
wording relies on.

<!-- source: ontology/wording/examples/facility-agreement.ttl -->
```turtle
# The attachment's first edition. An attachment is part of what the parties
# agreed, so the wording relies on one edition of it (static).
ex:repayment-plan a wrd:DocumentObject ;
    fnd:hasIdentity ex:repayment-plan-identity ;
    wrd:documentKind ex:repayment-schedule .
ex:facility-wording wrd:reliesOnEdition ex:repayment-plan .
```

A wording can also rely on a document "as amended from time to time", such as a regulation. Then the
edition is whichever is in force when a question is asked, and only the moment of asking can
resolve it. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/wording/examples/facility-agreement.ttl).

### From the lender's form to one facility's text

A lender signs many facilities on one form. Each facility's text is an **assembled wording**: the
form's clauses this facility includes, with this facility's values in the blanks. The Instrument
example shows the assembly for Acme.

<!-- source: ontology/instrument/examples/facility-agreement.ttl -->
```turtle
ex:acme-wording-v1 a wrd:AssembledWording ;
    fnd:hasIdentity ex:acme-wording-identity ; fnd:hasGovernanceState fnd:Active ;
    wrd:assembledFrom ex:form ;
    wrd:includes ex:sec-6 , ex:cl-6-1 , ex:sec-7 , ex:cl-7-1 , ex:sec-8 , ex:cl-8-1 , ex:sec-10 , ex:cl-10-1 .
```

The clauses are included, not copied. Clause 6.1 is the same node in the form and in Acme's
facility. Another example, a facility for Halden Foods plc, shows where the filled-in blanks are
stored.

<!-- source: ontology/instrument/examples/facility-parameters.ttl -->
```turtle
ex:halden-wording-v1 a wrd:AssembledWording ;
    fnd:hasIdentity ex:halden-wording-identity ; fnd:hasGovernanceState fnd:Active ;
    wrd:assembledFrom ex:form ;
    wrd:includes ex:sec-1 , ex:cl-1-1 , ex:sec-6 , ex:cl-6-1 , ex:sec-7 , ex:cl-7-1 , ex:cl-7-2 , ex:sec-10 , ex:cl-10-1 ;
    wrd:hasValue ex:v-commitment , ex:v-repay-days , ex:v-leverage .

ex:v-commitment a wrd:VariableValue ;
    wrd:forVariable ex:var-commitment ;
    wrd:value [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue "25000000"^^xsd:decimal ; qnt:inUnit ex:gbp ] .
ex:v-repay-days a wrd:VariableValue ;
    wrd:forVariable ex:var-repay-days ;
    wrd:literalValue "10"^^xsd:decimal .
ex:v-leverage a wrd:VariableValue ;
    wrd:forVariable ex:var-leverage ;
    wrd:literalValue "3.5"^^xsd:decimal .
```

The commitment is 25,000,000 GBP, held as an amount with its unit. The repayment period is 10
business days, and the leverage ceiling 3.5 to 1. The values belong to Halden's assembled wording,
so the text Halden signed and the numbers in it are one record.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/instrument/examples/facility-parameters.ttl).

### Instantiation, in one picture

Meaning is written once per clause, against the form's roles ("the Borrower", "the Lenders"). For
each facility, **instantiation** combines three inputs into that facility's own meaning, naming its
own parties and values.

<div class="mermaid">
flowchart LR
  SM["stated meaning<br/>written once per clause<br/>names roles"] --> I(("instantiation"))
  AW["assembled wording<br/>which clauses, which values"] --> I
  PA["the facility's parties<br/>who holds each role"] --> I
  I --> BM["bound meaning<br/>for one facility<br/>names parties and values"]
</div>

The result, **bound meaning**, is derived. It can be rebuilt from its three inputs at any time and is
never the source of truth, much as a fact table can be rebuilt from its sources. A relational
counterpart is a view over a template and a parameter table, materialised per contract. Chapter 6
shows both sides of the picture for Acme's facility.
