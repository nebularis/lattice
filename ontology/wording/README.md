<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Wording Ontology: what a contract's documents say, and how they are built

Literate specification for the Wording layer ([ADR-A112](../../docs/architecture/decisions/ADR-A112-wording-layer.md)).

---

## 1. Purpose and scope

A contract's text has a structure of its own, independent of what it means in law. Parts nest and
are ordered. Text embeds values supplied per instance and refers to defined words, other parts and
documents outside the text. Wording models that structure. What the text means in law (terms,
legal relations, parties) is the Instrument layer's, which states each term's meaning against the
wording element that expresses it ([ADR-A104](../../docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md)
decision 2).

Wording imports Foundation, Vocabulary, Quantification and Eligibility, and is imported by
Instrument. It names no term of a higher layer.

This release (`0.2.0`) holds structure, text parts, references, document objects and variables
(since `0.1.0`), and tables, assembly and the values an instance supplies. Amendments and the shapes
for the layer's laws follow in `0.3.0` (the computable contract substrate plan, slice C5).

## 2. Namespace and prefixes

```turtle-spec
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Extraction contract

- `turtle-spec` blocks generate `spec/wording.ttl`.
- `turtle-vocab` blocks generate `vocab/wording-vocab.ttl`.
- `turtle-shapes` blocks generate `shapes/structural.ttl`.
- `turtle-example` blocks are illustrative only. The worked examples live in `examples/`.

```bash
python3 tools/literate_extract.py ontology/wording/README.md --layer wording --root . \
    --shapes shapes/structural.ttl --check
```

## 4. Worked examples

Authored before this specification ([ADR-A-C2](../../docs/architecture/decisions/ADR-AC2-clean-room-authoring-procedure.md)).
Each file opens with its premise.

| Example | Shows |
|---|---|
| [`facility-agreement.ttl`](examples/facility-agreement.ttl) | a wording tree ordered by rank key, a clause as five text parts with a reference to a definition and to a variable, an annex that refers to a scanned document |
| [`trial-protocol.ttl`](examples/trial-protocol.ttl) | a schedule, an embedded variable with admissible values, a governing variable never shown in text, a reference to an external regulation, a clause classification, a table whose rows the form declares and whose columns (study arms) one trial supplies, and that trial's assembled protocol |
| [`facility-form.ttl`](examples/facility-form.ttl) | a library form with a mandatory clause, a variation slot of two variants, an optional clause and a conditional clause reading a governing variable, and a facility assembled from it, with a multi-valued list of jurisdictions |

Clause 4.1 of the facility agreement, "The Borrower shall pay interest at {margin} per annum", is
five text parts:

```turtle-example
ex:cl-4-1-p0 a wrd:TextPart ; wrd:partIndex 0 ; wrd:partText "The " .
ex:cl-4-1-p1 a wrd:TextPart ; wrd:partIndex 1 ; wrd:refersToObject ex:def-borrower .
ex:cl-4-1-p2 a wrd:TextPart ; wrd:partIndex 2 ; wrd:partText " shall pay interest at " .
ex:cl-4-1-p3 a wrd:TextPart ; wrd:partIndex 3 ; wrd:refersToVariable ex:var-margin .
ex:cl-4-1-p4 a wrd:TextPart ; wrd:partIndex 4 ; wrd:partText " per annum." .
```

## 5. Model

### 5.1 The ontology

```turtle-spec
<https://www.nebularis.org/neuro-semantic/wording>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/wording/0.2.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.5.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.7.0> .
```

### 5.2 Wordings and elements

A wording is the root of one document's tree: an agreement, policy, form, protocol, or endorsement issued as a document of its own. An element is any part beneath it. Any new text is a new version superseding the old, under the same persistent identity. What kind of part an element is (a section, a clause, a schedule) is modelled as a concept, 
rather than a class.

The equivalence assertion on `WordingNode` also says something the reduntant subclass triples alone cannot: that every `WordingNode` is a `Wording` or an `Element`, and nothing else. Used for `rdfs:range` assertions.

```turtle-spec
wrd:Wording a owl:Class ;
	rdfs:subClassOf fnd:Version , fnd:Governable , wrd:WordingNode ;
	rdfs:label "Wording"@en ;
	rdfs:comment "The root of one document's wording tree." ;
	fnd:utility "One should exist per document. Changed text leads to a new wording version with the same fnd:hasIdentity superseding the old." .

wrd:Element a owl:Class ;
	rdfs:subClassOf fnd:Version , fnd:Governable , wrd:WordingNode ;
	rdfs:label "Element"@en ;
	rdfs:comment "A nestable part of a wording." ;
	fnd:utility "Typed with wrd:elementType. Use one of the content classes of §5.6 where the part carries content of its own. A changed element requires a new element version." .

wrd:WordingNode a owl:Class ;
	owl:equivalentClass [ a owl:Class ; owl:unionOf ( wrd:Wording wrd:Element ) ] ;
	rdfs:label "Wording node"@en ;
	rdfs:comment "Anything in a wording tree: a wording or one of its elements." ;
	fnd:utility "WordingNode is NOT meant to be used to make assertions. It names the subject of properties that apply to a whole wording and to its parts alike." .
```

### 5.3 Part and whole

`wrd:directlyComprises` is the only part-whole edge intended for making assertions, whilst `wrd:comprises` provides its transitive closure. The direct edge has no transitive sub-property, so that OWL 2 DL allows it be irreflexive and asymmetric.

```turtle-spec
wrd:comprises a owl:ObjectProperty , owl:TransitiveProperty ;
	rdfs:label "comprises"@en ;
	rdfs:domain wrd:WordingNode ;
	rdfs:range wrd:Element ;
	rdfs:comment "The transitive part-whole relation of a wording tree. Subject: a wording node. Value: an element at any depth below it." ;
	fnd:utility "wrd:comprises is NOT intended to be used for making assertions. Instead, wrd:directlyComprises should be used, whilst a reasoner or a compiled closure can supply skip-level containment." .

wrd:isComprisedBy a owl:ObjectProperty , owl:TransitiveProperty ;
	rdfs:label "is comprised by"@en ;
	rdfs:comment "Subject: an element. Value: a wording node at any depth above it." ;
	owl:inverseOf wrd:comprises .

wrd:directlyComprises a owl:ObjectProperty , owl:IrreflexiveProperty , owl:AsymmetricProperty ;
	rdfs:label "directly comprises"@en ;
	rdfs:subPropertyOf wrd:comprises ;
	rdfs:domain wrd:WordingNode ;
	rdfs:range wrd:Element ;
	rdfs:comment "A direct edge of a wording tree. Subject: a wording node. Value: one of its immediate parts, an element." .

wrd:isDirectlyComprisedBy a owl:ObjectProperty , owl:IrreflexiveProperty , owl:AsymmetricProperty ;
	rdfs:label "is directly comprised by"@en ;
	rdfs:subPropertyOf wrd:isComprisedBy ;
	rdfs:comment "Subject: an element. Value: the wording node immediately above it." ;
	owl:inverseOf wrd:directlyComprises .
```

### 5.4 Order and identity

Identity is not position. A rank key orders siblings lexicographically, so a part can be inserted between two others without renumbering anything. An object id is the number or label a reader sees ("4.1", "Schedule 1"), derived after assembly. The object id should not be used as an identity.

```turtle-spec
wrd:rankKey a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "rank key"@en ;
	rdfs:domain wrd:Element ; rdfs:range xsd:string ;
	rdfs:comment "A lexicographic key placing an element among its siblings. Subject: an element. Value: a string, at most one." ;
	fnd:utility "Choose keys that leave room between them (a0, b0), so an insertion takes a key in between and no sibling changes." .

wrd:objectId a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "object id"@en ;
	rdfs:domain wrd:WordingNode ; rdfs:range xsd:string ;
	rdfs:comment "The number or label a reader sees: 4.1, 4.B(2), Schedule 1. Subject: a wording node. Value: a string, at most one." ;
	fnd:utility "Presentation only. Two versions of a clause may carry different object ids and remain the same clause." .
```

### 5.5 Typing

What kind of part an element is, and how it is classified, are concepts drawn under scheme contracts. A deployment typically binds its own schemes. A basic set of element types ship with this layer.

```turtle-spec
wrd:elementType a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "element type"@en ;
	rdfs:domain wrd:WordingNode ;
	rdfs:range skos:Concept ;
	rdfs:comment "What kind of part a wording or element is: a section, a clause, a schedule. Subject: a wording node. Value: a concept under wrd-voc:ElementTypeContract, at most one." ;
	fnd:utility "Drawn under wrd-voc:ElementTypeContract. A section is a part with a determined meaning of its own (its parties, authority or capacity), as the Instrument layer reads it." .

wrd:classification a owl:ObjectProperty ;
	rdfs:label "classification"@en ;
	rdfs:domain wrd:WordingNode ;
	rdfs:range skos:Concept ;
	rdfs:comment "A classification of a wording or element, beside its type: safety reporting, governing law, data protection. Subject: a wording node. Value: a concept under wrd-voc:ClassificationContract, any number." ;
	fnd:utility "Drawn under wrd-voc:ClassificationContract. An element may carry several." .
```

### 5.6 Content classes

Kinds of content that differ in their properties. Each is an element.

```turtle-spec
wrd:Text a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Text"@en ;
	rdfs:comment "An element whose content is an ordered sequence of text parts." .

wrd:Table a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Table"@en ;
	rdfs:comment "An element whose content is rows and columns. Rows are declared in the wording, columns are supplied per instance." .

wrd:Variable a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Variable"@en ;
	rdfs:comment "A declaration of a value an instance supplies." .

wrd:Reference a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Reference"@en ;
	rdfs:comment "An element linking to another part, a document object or an external document." .

wrd:Metadata a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Metadata"@en ;
	rdfs:comment "Descriptive or system metadata carried in the wording." .

[] a owl:AllDisjointClasses ;
	owl:members ( wrd:Text wrd:Table wrd:Variable wrd:Reference wrd:Metadata wrd:Row wrd:VariationSlot ) .
```

### 5.7 Text parts

Text is represented as a sequence of parts, with each part being one of three forms: literal text, a reference to a variable, or a reference to another part or document. Parts are indexed from 0 without gaps, which gives a closed-world order without an RDF list. A part belongs to one text and is not a version. Changed text is a new text version with new parts. 

```turtle-spec
wrd:TextPart a owl:Class ;
	rdfs:label "Text part"@en ;
	rdfs:comment "One inline piece of a text: literal text, a variable reference or an object reference." ;
	rdfs:subClassOf [ a owl:Restriction ; owl:onProperty wrd:partIndex ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	fnd:utility "Give each part exactly one of wrd:partText, wrd:refersToVariable or wrd:refersToObject, and index the parts of one text 0 to n-1." .

wrd:hasTextPart a owl:ObjectProperty , owl:InverseFunctionalProperty ;
	rdfs:label "has text part"@en ;
	rdfs:domain wrd:Text ; rdfs:range wrd:TextPart ;
	rdfs:comment "A part of a text. Each part belongs to exactly one text. Subject: a text. Value: a text part, which belongs to no other text." .

wrd:partIndex a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "part index"@en ;
	rdfs:domain wrd:TextPart ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The part's position in its text, from 0. Subject: a text part. Value: a non-negative integer, exactly one." .

wrd:partText a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "part text"@en ;
	rdfs:domain wrd:TextPart ; rdfs:range xsd:string ;
	rdfs:comment "The literal text of a part, spaces included. Subject: a text part. Value: a string, at most one." .

wrd:refersToVariable a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "refers to variable"@en ;
	rdfs:domain wrd:TextPart ; rdfs:range wrd:Variable ;
	rdfs:comment "The variable whose value the part shows. Subject: a text part. Value: a variable, at most one." .

wrd:refersToObject a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "refers to object"@en ;
	rdfs:domain wrd:TextPart ;
	rdfs:range wrd:ReferenceTarget ;
	rdfs:comment "The part, wording or document the part names: a defined word's definition, another clause, an annex, a regulation. Subject: a text part. Value: a reference target, at most one." .
```

### 5.8 References and documents

A document object is an attachment whose content is not digitised: a scanned plan, a certificate. An external document sits outside the contract altogether: a regulation, a separate agreement. Both are outside the wording tree, reached by a reference element or a text part.

```turtle-spec
wrd:DocumentObject a owl:Class ;
	rdfs:subClassOf prov:Entity , wrd:LinkedDocument ;
	rdfs:label "Document object"@en ;
	rdfs:comment "An attachment the wording relies on whose content is not digitised." .

wrd:ExternalDocument a owl:Class ;
	rdfs:subClassOf prov:Entity , wrd:LinkedDocument ;
	rdfs:label "External document"@en ;
	rdfs:comment "A document outside the contract, that its wording relies on." .

wrd:LinkedDocument a owl:Class ;
	owl:equivalentClass [ a owl:Class ; owl:unionOf ( wrd:DocumentObject wrd:ExternalDocument ) ] ;
	rdfs:label "Linked document"@en ;
	rdfs:comment "A document outside the wording tree that the wording relies on." ;
	fnd:utility "Assertions should NOT be made using this class. Its subclasses are declared explicitly. For use by SHACL validators." .

wrd:ReferenceTarget a owl:Class ;
	owl:equivalentClass [ a owl:Class ; owl:unionOf ( wrd:WordingNode wrd:LinkedDocument ) ] ;
	rdfs:label "Reference target"@en ;
	rdfs:comment "Anything a text part or a reference element may point to (e.g., a wording, element, or linked document." ;
	fnd:utility "Assertions should NOT be made using this class. Its subclasses are declared explicitly. For use by SHACL validators." .

wrd:WordingNode rdfs:subClassOf wrd:ReferenceTarget .
wrd:LinkedDocument rdfs:subClassOf wrd:ReferenceTarget .

wrd:documentKind a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "document kind"@en ;
	rdfs:domain wrd:LinkedDocument ;
	rdfs:range skos:Concept ;
	rdfs:comment "What kind of document it is, drawn under wrd-voc:DocumentKindContract. Subject: a linked document. Value: a concept under wrd-voc:DocumentKindContract, at most one." .

wrd:linksTo a owl:ObjectProperty ;
	rdfs:label "links to"@en ;
	rdfs:domain wrd:Reference ;
	rdfs:range wrd:ReferenceTarget ;
	rdfs:comment "What a reference element points to. Subject: a reference element. Value: a reference target." .

[] a owl:AllDisjointClasses ;
	owl:members ( wrd:Wording wrd:Element wrd:TextPart wrd:DocumentObject wrd:ExternalDocument wrd:PopulationMethod wrd:InclusionMode wrd:VariableValue ) .
```

### 5.9 Variables

A variable declares a value an instance supplies. An embedded variable is shown in the text. A
governing variable is never shown, and decides which parts of a library wording an instance
includes. A value is a concept (drawn under a scheme contract), a quantity (in a value space,
optionally within admissible ranges), a literal, a party or another instrument. The value itself
is recorded per instance (§5.12).

```turtle-spec
wrd:EmbeddedVariable a owl:Class ;
	rdfs:subClassOf wrd:Variable ;
	rdfs:label "Embedded variable"@en ;
	rdfs:comment "A variable shown within text." .

wrd:GoverningVariable a owl:Class ;
	rdfs:subClassOf wrd:Variable ;
	rdfs:label "Governing variable"@en ;
	rdfs:comment "A variable never shown in text, read by inclusion conditions." .

[] a owl:AllDisjointClasses ;
	owl:members ( wrd:EmbeddedVariable wrd:GoverningVariable ) .

wrd:PopulationMethod a owl:Class ;
	rdfs:label "Population method"@en ;
	rdfs:comment "How a variable's value is obtained: entered, picked from a list, looked up, taken from another variable, derived by rule." .

wrd:variableKey a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "variable key"@en ;
	rdfs:domain wrd:Variable ; rdfs:range xsd:string ;
	rdfs:comment "The variable's stable key within its wording. Subject: a variable. Value: a string, at most one." .

wrd:populationMethod a owl:ObjectProperty ;
	rdfs:label "population method"@en ;
	rdfs:domain wrd:Variable ; rdfs:range wrd:PopulationMethod ;
	rdfs:comment "Subject: a variable. Value: a population method." .

wrd:populatedFrom a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "populated from"@en ;
	rdfs:domain wrd:Variable ; rdfs:range wrd:Variable ;
	rdfs:comment "Another variable, often in another part, whose value this one takes. Subject: a variable. Value: another variable, at most one." .

wrd:valueContract a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "value contract"@en ;
	rdfs:domain wrd:Variable ; rdfs:range voc:SchemeContract ;
	rdfs:comment "For a concept-valued variable, the scheme contract its values are drawn under. Subject: a variable. Value: a scheme contract, at most one." .

wrd:valueSpace a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "value space"@en ;
	rdfs:domain wrd:Variable ; rdfs:range qnt:ValueSpace ;
	rdfs:comment "For a quantity-valued variable, the value space its values are in. Subject: a variable. Value: a value space, at most one." .

wrd:admissibleValues a owl:ObjectProperty ;
	rdfs:label "admissible values"@en ;
	rdfs:domain wrd:Variable ; rdfs:range qnt:RangeSet ;
	rdfs:comment "A range set every value must fall in. Subject: a variable. Value: a range set." .

wrd:multiValued a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "multi-valued"@en ;
	rdfs:domain wrd:Variable ; rdfs:range xsd:boolean ;
	rdfs:comment "True when an instance may supply several values, as for a list of territories. Single-valued when absent. Subject: a variable. Value: a boolean, at most one." .
```

### 5.10 Tables

A table's rows are declared in the wording, each with what it means and the variable its cells
take a value for. Its columns exist only in an instance: a section, a party's occupancy, a study
arm, a lot. So a cell is the value of a row's variable for one column (§5.12), and one row yields
one value per column. A long list whose rows are only values, such as a list of territories, is a
multi-valued variable, not a table.

```turtle-spec
wrd:Row a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Row"@en ;
	rdfs:comment "A row of a table, declared in the wording." ;
	fnd:utility "A table directly comprises its rows, in rank order. A row usually comprises its own variable too, so the variable has a place in the tree." .

wrd:rowKey a owl:DatatypeProperty , owl:FunctionalProperty ;
	rdfs:label "row key"@en ;
	rdfs:domain wrd:Row ; rdfs:range xsd:string ;
	rdfs:comment "What the row means, as its label reads: Maximum limits, Screening sample volume. Subject: a row. Value: a string, at most one." .

wrd:rowVariable a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "row variable"@en ;
	rdfs:domain wrd:Row ; rdfs:range wrd:Variable ;
	rdfs:comment "The variable every column supplies a value for in this row. Subject: a row. Value: a variable, exactly one." .
```

### 5.11 Assembly

Assembly happens at design time: an instance is drawn from a library form once, and its wording is
then fixed. Nothing here is evaluated per event. Each element of a form comes into an instance in
one of four ways, its inclusion mode: always (Mandatory, the default), as the one chosen variant
of a variation slot (Variation), at the drafter's choice (Optional), or when an inclusion
condition over the instance's governing variables holds (Conditional).

A variation slot is an element in its own right, ranked among its siblings and carrying the number
its variants share ("1.4"). Its variants sit beneath it, unranked, each lettered ("1.4A") in the
form only. An instance includes exactly one of them, numbered as the slot. An inclusion condition is
an Eligibility admission profile, each of whose conditions reads one governing variable. Assembly
poses the instance's value for that variable as an `elg:Question`.

```turtle-spec
wrd:InclusionMode a owl:Class ;
	rdfs:label "Inclusion mode"@en ;
	rdfs:comment "How an element comes to be in an instance: Mandatory, Variation, Optional or Conditional (wrd-voc)." .

wrd:inclusionMode a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "inclusion mode"@en ;
	rdfs:domain wrd:Element ; rdfs:range wrd:InclusionMode ;
	rdfs:comment "How the element comes to be in an instance. Mandatory when absent. Subject: an element. Value: one of the four inclusion modes, at most one." .

wrd:VariationSlot a owl:Class ;
	rdfs:subClassOf wrd:Element ;
	rdfs:label "Variation slot"@en ;
	rdfs:comment "A position in a form that holds exactly one of several variants in any instance." ;
	fnd:utility "Give the slot the shared object id (1.4) and a rank key. Its variants carry inclusion mode Variation and a lettered object id (1.4A), and no rank key: they are alternatives, not siblings. The slot's variants' conditions are checked as a set, no two overlapping and together covering every case (wording 0.3.0)." .

wrd:hasVariant a owl:ObjectProperty ;
	rdfs:label "has variant"@en ;
	rdfs:subPropertyOf wrd:directlyComprises ;
	rdfs:domain wrd:VariationSlot ; rdfs:range wrd:Element ;
	rdfs:comment "One of the slot's variants. A variant is part of the slot, so it is in the tree. Subject: a variation slot. Value: an element, the variant of no other slot." ;
	fnd:utility "Assert wrd:hasVariant, not wrd:directlyComprises, from a slot to its variants. A reasoner derives the part-whole edge. Shapes read both." .

wrd:variantOf a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "variant of"@en ;
	owl:inverseOf wrd:hasVariant ;
	rdfs:comment "The slot an element is a variant of. Subject: an element. Value: a variation slot, at most one." .

wrd:includedWhen a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "included when"@en ;
	rdfs:domain wrd:Element ; rdfs:range elg:AdmissionProfile ;
	rdfs:comment "The inclusion condition of a conditional element or a variant, over the instance's governing variables. Subject: an element. Value: an admission profile, at most one." .

wrd:readsVariable a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "reads variable"@en ;
	rdfs:domain elg:Condition ; rdfs:range wrd:GoverningVariable ;
	rdfs:comment "The governing variable whose instance value an inclusion condition is decided against. Subject: an Eligibility condition. Value: a governing variable, at most one." .
```

### 5.12 The assembled wording and its values

An assembled wording is one instance's text: the elements it includes, and the values it supplies.
It is asserted as such, never inferred, since a contract written from scratch is assembled from no
form at all. An instrument version is expressed in exactly one assembled wording
([ADR-A104](../../docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md)).
Library elements are included, not copied: many instances include the same element version.

A variable value records an instance's value for one variable, and for one column when the
variable is a table row's. A multi-valued variable's values all sit on its one value record, so a
single-valued variable is a variable whose record holds one value.

```turtle-spec
wrd:AssembledWording a owl:Class ;
	rdfs:subClassOf wrd:Wording ;
	rdfs:label "Assembled wording"@en ;
	rdfs:comment "The wording of one instance, drawn from forms or written for it alone." ;
	fnd:utility "Assert it on every instance's wording. A wording not so typed is a library form. A changed instance text is a new assembled wording version with the same fnd:hasIdentity." .

wrd:assembledFrom a owl:ObjectProperty ;
	rdfs:label "assembled from"@en ;
	rdfs:domain wrd:AssembledWording ; rdfs:range wrd:Wording ;
	rdfs:comment "A library form the instance was drawn from. Subject: an assembled wording. Value: a wording, any number, none for a contract written from scratch." .

wrd:includes a owl:ObjectProperty ;
	rdfs:label "includes"@en ;
	rdfs:domain wrd:AssembledWording ; rdfs:range wrd:Element ;
	rdfs:comment "An element version the instance includes. Recorded at assembly, never recomputed. Subject: an assembled wording. Value: an element." .

wrd:hasValue a owl:ObjectProperty , owl:InverseFunctionalProperty ;
	rdfs:label "has value"@en ;
	rdfs:domain wrd:AssembledWording ; rdfs:range wrd:VariableValue ;
	rdfs:comment "A value the instance supplies. Each value record belongs to one assembled wording. Subject: an assembled wording. Value: a variable value." .

wrd:VariableValue a owl:Class ;
	rdfs:label "Variable value"@en ;
	rdfs:comment "An instance's value or values for one variable, and for one column when the variable is a table row's." ;
	rdfs:subClassOf [ a owl:Restriction ; owl:onProperty wrd:forVariable ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	fnd:utility "Not a version: it is part of its assembled wording, and changes only with it." .

wrd:forVariable a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "for variable"@en ;
	rdfs:domain wrd:VariableValue ; rdfs:range wrd:Variable ;
	rdfs:comment "The variable the record supplies a value for. Subject: a variable value. Value: a variable, exactly one." .

wrd:value a owl:ObjectProperty ;
	rdfs:label "value"@en ;
	rdfs:domain wrd:VariableValue ;
	rdfs:comment "A value that is a resource: a concept, a quantity, a party's occupancy, an instrument. Subject: a variable value. Value: any resource, several for a multi-valued variable." ;
	fnd:utility "Deliberately has no range: what a value is depends on the variable's declaration, which a shape checks (wording 0.3.0, law W6)." .

wrd:literalValue a owl:DatatypeProperty ;
	rdfs:label "literal value"@en ;
	rdfs:domain wrd:VariableValue ;
	rdfs:comment "A value that is a literal: a number, a date, a string. Subject: a variable value. Value: a literal, several for a multi-valued variable." .

wrd:forColumn a owl:ObjectProperty , owl:FunctionalProperty ;
	rdfs:label "for column"@en ;
	rdfs:domain wrd:VariableValue ;
	rdfs:comment "The column a table cell's value is for: a section, a party's occupancy, a study arm. Only for a table row's variable. Subject: a variable value. Value: any resource, at most one." .
```

## 6. Vocabulary

The inclusion modes and population methods are closed sets of named individuals. Three scheme
contracts govern the typing properties. Element types have a baseline scheme bound
as each contract's fallback. It holds every element type this layer's documentation and examples
use, and is not closed: a deployment binds a scheme of its own, which may extend it, through a
`voc:SchemeBinding`. Classifications and document kinds have no baseline.

```turtle-vocab
@prefix wrd:     <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix wrd-voc: <https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#> .
@prefix fnd:     <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:     <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .

<https://www.nebularis.org/neuro-semantic/wording-vocab>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/wording-vocab/0.2.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/wording/0.2.0> .

wrd-voc:ElementTypeContract a voc:SchemeContract ;
	fnd:hasIdentity wrd-voc:ElementTypeContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Element type scheme contract"@en ;
	voc:constrainsProperty wrd:elementType ;
	voc:boundScheme wrd-voc:ElementTypes .

wrd-voc:ClassificationContract a voc:SchemeContract ;
	fnd:hasIdentity wrd-voc:ClassificationContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Classification scheme contract"@en ;
	voc:constrainsProperty wrd:classification .

wrd-voc:DocumentKindContract a voc:SchemeContract ;
	fnd:hasIdentity wrd-voc:DocumentKindContract-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Document kind scheme contract"@en ;
	voc:constrainsProperty wrd:documentKind .

wrd-voc:ElementTypes a voc:ConceptScheme ;
	fnd:hasIdentity wrd-voc:ElementTypes-identity ;
	fnd:hasGovernanceState fnd:Active ;
	skos:prefLabel "Baseline element types"@en ;
	skos:definition "The element types every wording may use. A baseline, not a closed set."@en .

wrd-voc:Section a skos:Concept ;
	skos:inScheme wrd-voc:ElementTypes ;
	skos:prefLabel "Section"@en ;
	skos:definition "A part with a determined meaning of its own, which may state its own parties, authority, classes or capacity."@en .

wrd-voc:Clause a skos:Concept ;
	skos:inScheme wrd-voc:ElementTypes ;
	skos:prefLabel "Clause"@en ;
	skos:definition "A numbered or titled unit of text stating one or more provisions."@en .

wrd-voc:Definition a skos:Concept ;
	skos:inScheme wrd-voc:ElementTypes ;
	skos:prefLabel "Definition"@en ;
	skos:definition "A unit of text giving the meaning of a word used elsewhere in the wording."@en .

wrd-voc:Schedule a skos:Concept ;
	skos:inScheme wrd-voc:ElementTypes ;
	skos:prefLabel "Schedule"@en ;
	skos:definition "A part holding the particulars of an instance, often as tables, read with the body of the wording."@en .

wrd-voc:Annex a skos:Concept ;
	skos:inScheme wrd-voc:ElementTypes ;
	skos:prefLabel "Annex"@en ;
	skos:altLabel "Appendix"@en ;
	skos:definition "A part attached to the body of the wording, often referring to a document object."@en .

# ---- Inclusion modes: a closed set -------------------------------------------

wrd-voc:Mandatory a owl:NamedIndividual , wrd:InclusionMode ;
	rdfs:label "Mandatory"@en ;
	rdfs:comment "Always in an instance that includes its parent. The default when an element states no mode." .

wrd-voc:Variation a owl:NamedIndividual , wrd:InclusionMode ;
	rdfs:label "Variation"@en ;
	rdfs:comment "One variant of a variation slot. An instance includes exactly one variant of each slot it includes." .

wrd-voc:Optional a owl:NamedIndividual , wrd:InclusionMode ;
	rdfs:label "Optional"@en ;
	rdfs:comment "In an instance only when the drafter chooses it." .

wrd-voc:Conditional a owl:NamedIndividual , wrd:InclusionMode ;
	rdfs:label "Conditional"@en ;
	rdfs:comment "In an instance only when its inclusion condition (wrd:includedWhen) holds over the instance's governing variables." .

[] a owl:AllDifferent ;
	owl:distinctMembers ( wrd-voc:Mandatory wrd-voc:Variation wrd-voc:Optional wrd-voc:Conditional ) .

# ---- Population methods: a closed set ----------------------------------------

wrd-voc:FreeEntry a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Free entry"@en ;
	rdfs:comment "Entered by the drafter, within the variable's value space and admissible values." .

wrd-voc:PickList a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Pick list"@en ;
	rdfs:comment "Chosen from the concepts the variable's value contract allows." .

wrd-voc:ReferenceTableLookup a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Reference table lookup"@en ;
	rdfs:comment "Looked up from reference data held outside the wording, such as a party register." .

wrd-voc:TablePopulated a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Populated from a table"@en ;
	rdfs:comment "Filled from a table of the same wording." .

wrd-voc:SignatureProcess a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "From the signature process"@en ;
	rdfs:comment "Supplied when the instance is signed or accepted, such as the date of acceptance." .

wrd-voc:DerivedByRule a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Derived by rule"@en ;
	rdfs:comment "Computed from other values by a declared rule." .

wrd-voc:DefaultedOverridable a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "Defaulted, overridable"@en ;
	rdfs:comment "Defaulted from other facts, and changeable by the drafter within the admissible values." .

wrd-voc:FromAnotherVariable a owl:NamedIndividual , wrd:PopulationMethod ;
	rdfs:label "From another variable"@en ;
	rdfs:comment "Takes the value of the variable named by wrd:populatedFrom." .

[] a owl:AllDifferent ;
	owl:distinctMembers ( wrd-voc:FreeEntry wrd-voc:PickList wrd-voc:ReferenceTableLookup wrd-voc:TablePopulated
		wrd-voc:SignatureProcess wrd-voc:DerivedByRule wrd-voc:DefaultedOverridable wrd-voc:FromAnotherVariable ) .
```

## 7. Shapes

The following shapes check the same intent in SHACL Core, with no reasoning. Validate with the spec in the data graph (or passed as the ontology graph), so that `sh:class` sees the subclass hierarchy.

Each `…SubjectShape` checks that a property is used on the kind of node it belongs to. Each class shape checks the values and cardinalities on that kind of node. The laws W1 to W7 (a single tree, contiguous part indices, one variant per slot, mandatory parts included, values matching their declarations) are SHACL-SPARQL and follow in `0.3.0`. A slot asserts `wrd:hasVariant`, so the shapes check its variants on that property, without deriving `wrd:directlyComprises`.

```turtle-shapes
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix wrd-voc: <https://www.nebularis.org/neuro-semantic/lattice/wording/vocab#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

# ---- Wording nodes ----------------------------------------------------------

wrd:WordingNodeSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:directlyComprises , wrd:comprises , wrd:objectId , wrd:elementType , wrd:classification ;
	sh:class wrd:WordingNode ;
	sh:message "Only a wording or an element has parts, an object id, an element type or a classification." .

wrd:WordingNodeShape a sh:NodeShape ;
	sh:targetClass wrd:WordingNode ;
	sh:property [ sh:path wrd:directlyComprises ; sh:class wrd:Element ;
		sh:message "A wording node's parts are elements." ] ;
	sh:property [ sh:path wrd:objectId ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
	sh:property [ sh:path wrd:elementType ; sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
	sh:property [ sh:path wrd:classification ; sh:nodeKind sh:IRI ] .

wrd:ElementSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:rankKey ;
	sh:class wrd:Element ;
	sh:message "Only an element has a rank key: it orders siblings, and a wording has none." .

wrd:ElementShape a sh:NodeShape ;
	sh:targetClass wrd:Element ;
	sh:property [ sh:path wrd:rankKey ; sh:maxCount 1 ; sh:datatype xsd:string ] .

# ---- Texts and text parts ---------------------------------------------------

wrd:TextSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:hasTextPart ;
	sh:class wrd:Text ;
	sh:message "Only a text has text parts." .

wrd:TextShape a sh:NodeShape ;
	sh:targetClass wrd:Text ;
	sh:property [ sh:path wrd:hasTextPart ; sh:class wrd:TextPart ] .

wrd:TextPartSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:partIndex , wrd:partText , wrd:refersToVariable , wrd:refersToObject ;
	sh:class wrd:TextPart ;
	sh:message "Only a text part has a part index, text or a reference." .

wrd:TextPartShape a sh:NodeShape ;
	sh:targetClass wrd:TextPart ;
	sh:property [ sh:path [ sh:inversePath wrd:hasTextPart ] ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A text part belongs to exactly one text." ] ;
	sh:property [ sh:path wrd:partIndex ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:Literal ; sh:minInclusive 0 ;
		sh:message "A text part has exactly one index, from 0." ] ;
	sh:property [ sh:path wrd:partText ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
	sh:property [ sh:path wrd:refersToVariable ; sh:maxCount 1 ; sh:class wrd:Variable ] ;
	sh:property [ sh:path wrd:refersToObject ; sh:maxCount 1 ; sh:class wrd:ReferenceTarget ] ;
	sh:xone (
		[ sh:path wrd:partText ; sh:minCount 1 ]
		[ sh:path wrd:refersToVariable ; sh:minCount 1 ]
		[ sh:path wrd:refersToObject ; sh:minCount 1 ]
	) ;
	sh:message "A text part is exactly one of literal text, a variable reference or an object reference." .

# ---- References and linked documents ------------------------------------------

wrd:ReferenceSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:linksTo ;
	sh:class wrd:Reference ;
	sh:message "Only a reference element links to a target." .

wrd:ReferenceShape a sh:NodeShape ;
	sh:targetClass wrd:Reference ;
	sh:property [ sh:path wrd:linksTo ; sh:class wrd:ReferenceTarget ] .

wrd:LinkedDocumentSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:documentKind ;
	sh:class wrd:LinkedDocument ;
	sh:message "Only a document object or an external document has a document kind." .

wrd:LinkedDocumentShape a sh:NodeShape ;
	sh:targetClass wrd:LinkedDocument ;
	sh:property [ sh:path wrd:documentKind ; sh:maxCount 1 ; sh:nodeKind sh:IRI ] .

# ---- Variables ----------------------------------------------------------------

wrd:VariableSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:variableKey , wrd:populationMethod , wrd:populatedFrom , wrd:valueContract ,
		wrd:valueSpace , wrd:admissibleValues , wrd:multiValued ;
	sh:class wrd:Variable ;
	sh:message "Only a variable has a key, a population method, a value contract, space or admissible values." .

wrd:VariableShape a sh:NodeShape ;
	sh:targetClass wrd:Variable ;
	sh:property [ sh:path wrd:variableKey ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
	sh:property [ sh:path wrd:populationMethod ; sh:class wrd:PopulationMethod ] ;
	sh:property [ sh:path wrd:populatedFrom ; sh:maxCount 1 ; sh:class wrd:Variable ] ;
	sh:property [ sh:path wrd:valueContract ; sh:maxCount 1 ; sh:class voc:SchemeContract ] ;
	sh:property [ sh:path wrd:valueSpace ; sh:maxCount 1 ; sh:class qnt:ValueSpace ] ;
	sh:property [ sh:path wrd:admissibleValues ; sh:class qnt:RangeSet ] ;
	sh:property [ sh:path wrd:multiValued ; sh:maxCount 1 ; sh:datatype xsd:boolean ] .

# ---- Tables -------------------------------------------------------------------

wrd:RowSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:rowKey , wrd:rowVariable ;
	sh:class wrd:Row ;
	sh:message "Only a row has a row key or a row variable." .

wrd:RowShape a sh:NodeShape ;
	sh:targetClass wrd:Row ;
	sh:property [ sh:path wrd:rowKey ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
	sh:property [ sh:path wrd:rowVariable ; sh:minCount 1 ; sh:maxCount 1 ; sh:class wrd:Variable ;
		sh:message "A row declares exactly one variable, which every column supplies a value for." ] .

# ---- Assembly -----------------------------------------------------------------

wrd:AssemblySubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:inclusionMode , wrd:includedWhen ;
	sh:class wrd:Element ;
	sh:message "Only an element has an inclusion mode or an inclusion condition." .

wrd:AssemblyShape a sh:NodeShape ;
	sh:targetClass wrd:Element ;
	sh:property [ sh:path wrd:inclusionMode ; sh:maxCount 1 ;
		sh:in ( wrd-voc:Mandatory wrd-voc:Variation wrd-voc:Optional wrd-voc:Conditional ) ;
		sh:message "An element has at most one inclusion mode, one of the four." ] ;
	sh:property [ sh:path wrd:includedWhen ; sh:maxCount 1 ; sh:class elg:AdmissionProfile ] ;
	sh:property [ sh:path [ sh:inversePath wrd:hasVariant ] ; sh:maxCount 1 ;
		sh:message "An element is the variant of at most one slot." ] .

wrd:VariationSlotSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:hasVariant ;
	sh:class wrd:VariationSlot ;
	sh:message "Only a variation slot has variants." .

wrd:VariationSlotShape a sh:NodeShape ;
	sh:targetClass wrd:VariationSlot ;
	sh:property [ sh:path wrd:hasVariant ; sh:minCount 1 ; sh:class wrd:Element ;
		sh:message "A variation slot has at least one variant, an element." ] .

wrd:ReadsVariableSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:readsVariable ;
	sh:class elg:Condition ;
	sh:property [ sh:path wrd:readsVariable ; sh:maxCount 1 ; sh:class wrd:GoverningVariable ;
		sh:message "An inclusion condition reads at most one variable, a governing one." ] .

# ---- The assembled wording and its values -------------------------------------

wrd:AssembledWordingSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:assembledFrom , wrd:includes , wrd:hasValue ;
	sh:class wrd:AssembledWording ;
	sh:message "Only an assembled wording is drawn from forms, includes elements or supplies values." .

wrd:AssembledWordingShape a sh:NodeShape ;
	sh:targetClass wrd:AssembledWording ;
	sh:property [ sh:path wrd:assembledFrom ; sh:class wrd:Wording ] ;
	sh:property [ sh:path wrd:includes ; sh:class wrd:Element ] ;
	sh:property [ sh:path wrd:hasValue ; sh:class wrd:VariableValue ] .

wrd:VariableValueSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:forVariable , wrd:value , wrd:literalValue , wrd:forColumn ;
	sh:class wrd:VariableValue ;
	sh:message "Only a variable value has a variable, a value or a column." .

wrd:VariableValueShape a sh:NodeShape ;
	sh:targetClass wrd:VariableValue ;
	sh:property [ sh:path wrd:forVariable ; sh:minCount 1 ; sh:maxCount 1 ; sh:class wrd:Variable ;
		sh:message "A variable value is for exactly one variable." ] ;
	sh:property [ sh:path [ sh:inversePath wrd:hasValue ] ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A variable value belongs to exactly one assembled wording." ] ;
	sh:property [ sh:path wrd:forColumn ; sh:maxCount 1 ] ;
	sh:property [ sh:path wrd:value ; sh:nodeKind sh:BlankNodeOrIRI ] ;
	sh:property [ sh:path wrd:literalValue ; sh:nodeKind sh:Literal ] ;
	sh:or (
		[ sh:path wrd:value ; sh:minCount 1 ]
		[ sh:path wrd:literalValue ; sh:minCount 1 ]
	) ;
	sh:message "A variable value holds at least one value." .

wrd:ForColumnShape a sh:NodeShape ;
	sh:targetSubjectsOf wrd:forColumn ;
	sh:property [ sh:path ( wrd:forVariable [ sh:inversePath wrd:rowVariable ] ) ; sh:minCount 1 ;
		sh:message "A column applies only to a table row's variable." ] .
```

## 8. Laws and how-to

The layer's laws (W1 to W7), their SHACL-SPARQL shapes and a how-to guide are added in `0.3.0`.
