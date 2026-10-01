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

This release (`0.1.0`) holds structure, text parts, references, document objects and variables.
Tables, assembly and variable values follow in `0.2.0`, amendments and the shapes for the
layer's laws in `0.3.0` (the computable contract substrate plan, slices C4 and C5).

## 2. Namespace and prefixes

```turtle-spec
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
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
| [`trial-protocol.ttl`](examples/trial-protocol.ttl) | a schedule, an embedded variable with admissible values, a governing variable never shown in text, a reference to an external regulation, a clause classification |

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
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/wording/0.1.0> ;
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
	owl:members ( wrd:Text wrd:Table wrd:Variable wrd:Reference wrd:Metadata ) .
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
	owl:members ( wrd:Wording wrd:Element wrd:TextPart wrd:DocumentObject wrd:ExternalDocument wrd:PopulationMethod ) .
```

### 5.9 Variables

A variable declares a value an instance supplies. An embedded variable is shown in the text. A
governing variable is never shown, and decides which parts of a library wording an instance
includes. A value is a concept (drawn under a scheme contract), a quantity (in a value space,
optionally within admissible ranges), a literal, a party or another instrument. The value itself
is recorded per instance, from `0.2.0`.

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

## 6. Vocabulary

Three scheme contracts govern the typing properties. Element types have a baseline scheme bound
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

<https://www.nebularis.org/neuro-semantic/wording-vocab>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/wording-vocab/0.1.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/wording/0.1.0> .

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
```

## 7. Shapes

The following shapes check the same intent in SHACL Core, with no reasoning. Validate with the spec in the data graph (or passed as the ontology graph), so that `sh:class` sees the subclass hierarchy.

Each `…SubjectShape` checks that a property is used on the kind of node it belongs to. Each class shape checks the values and cardinalities on that kind of node. The laws W1 to W7 (a single tree, contiguous part indices, assembly) are SHACL-SPARQL and follow in `0.3.0`.

```turtle-shapes
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
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
```

## 8. Laws and how-to

The layer's laws (W1 to W7), their SHACL-SPARQL shapes and a how-to guide are added in `0.3.0`.
