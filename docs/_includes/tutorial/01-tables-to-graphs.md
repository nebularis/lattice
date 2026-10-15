<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 1. From tables to graphs
{: #graphs}

You already model data. Most of what an ontology does has a counterpart in a relational or
dimensional model, and the quickest way in is to start from those counterparts. This chapter maps
them, then spends as long on where the mapping misleads, because that is where data architects new
to ontologies usually go wrong.

### Everything is a statement

A relational row holds several facts at once. A graph holds one fact per statement, called a
**triple**: a subject, a property (also called a predicate) and an object. "Acme Holdings plc has the
company number 01234567" is one triple. A row with ten columns becomes ten triples about the same
subject.

Every subject, every property and most objects are named by an **IRI**, a web-style identifier such
as `https://www.nebularis.org/neuro-semantic/lattice/foundation#Key`. An IRI is a global name. Two
datasets that use the same IRI are talking about the same thing, with no join key to agree first.
An object can also be a **literal**, a plain value such as a string, a number or a date.

The standards involved are RDF for the statements, OWL for describing classes and properties, SHACL
for validating data against constraints, SKOS for code lists and taxonomies, and SPARQL for queries.

### The concept map

| You know | LATTICE uses | Notes |
|---|---|---|
| a schema | an **ontology**, one per layer, in that layer's `spec/` folder | the classes and properties a layer offers |
| an entity type or table | a **class** (`owl:Class`) | a set of things. A thing can belong to several |
| a row | an **individual**, a node with an IRI | |
| an attribute | a **datatype property**, whose object is a literal | |
| a foreign key or relationship | an **object property**, whose object is another node | direct, with no join table |
| a primary key | the node's **IRI** | natural keys are separate statements (chapter 4) |
| constraints (`NOT NULL`, `CHECK`, cardinality) | **SHACL shapes**, in each layer's `shapes/` folder | they report violations, they do not block writes |
| reference data, code lists | **SKOS concept schemes**, in `vocab/` folders | hierarchies included |
| a schema version | an ontology's **version IRI** | LATTICE versions every document semantically |
| a database or partition | a **named graph** | a set of triples that can be addressed as one |
| SQL | **SPARQL** | pattern matching over triples |
| a materialised view or denormalised column | a **Surface** promotion or index | chapter 11 |

Here is a real schema statement, the header of LATTICE's applied classification module. It names the
ontology, gives it a version, and states which versions of two other ontologies it depends on.

<!-- source: ontology/applied/classification/spec/classification.ttl -->
```turtle
<https://www.nebularis.org/neuro-semantic/lattice/applied/classification>
    rdf:type owl:Ontology ;
    owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/applied/classification/0.2.0> ;
    rdfs:label "Cross-domain classification properties"@en ;
    rdfs:comment "Territory, asset class and industry: classifications more than one applied domain needs (ADR-A98 decision 1, epic D8). Domain-neutral: no domain vocabulary anywhere in this document. A domain declares its own sub-properties to specialise these once it needs to (for example a lending module's collateralTerritory rdfs:subPropertyOf cls:territory)." ;
    owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0> ,
                <https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0> .
```

The `owl:imports` lines pin exact versions, much as a schema migration targets a known baseline.
[Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/applied/classification/spec/classification.ttl).

The same file declares a property that points at a code list, the counterpart of a foreign key to a
reference table.

<!-- source: ontology/applied/classification/spec/classification.ttl -->
```turtle
cls:industry a owl:ObjectProperty ;
    rdfs:range skos:Concept ;
    rdfs:label "industry"@en ;
    rdfs:comment "A classification by industry or economic activity." ;
    fnd:utility "Link anything needing an industry classification to a concept in an industry scheme. Declared with no domain, for the same reason as cls:territory." .
```

Its range is `skos:Concept`, any entry in any concept scheme. Which scheme a given contract uses
is decided later, per contract, by the Vocabulary layer (chapter 7). A relational design would have
fixed the reference table at design time.

### Constraints live beside the schema

In a relational database, `NOT NULL` and `UNIQUE` sit in the table definition and the database
refuses bad rows. In LATTICE the class definitions are in `spec/` and the constraints are SHACL shapes
in `shapes/`. A validator runs the shapes over the data and returns a report. This shape from the
Foundation layer says every key has exactly one value, which must be a string, and exactly one
scheme.

<!-- source: ontology/foundation/shapes/constraints.ttl -->
```turtle
fnd:KeyShape a sh:NodeShape ;
    sh:targetClass fnd:Key ;
    sh:targetSubjectsOf fnd:keyValue , fnd:keyScheme ;
    sh:property [
        sh:path fnd:keyValue ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ;
        sh:message "A key has exactly one fnd:keyValue, a string as issued."
    ] ;
    sh:property [
        sh:path fnd:keyScheme ; sh:minCount 1 ; sh:maxCount 1 ; sh:class fnd:KeyScheme ;
        sh:message "A key has exactly one fnd:keyScheme, a declared fnd:KeyScheme."
    ] .
```

`sh:minCount 1` is `NOT NULL`. `sh:maxCount 1` makes the property single-valued, which a column
always is and a property is not, unless a shape says so. `sh:class` plays the part of a foreign key
constraint. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/foundation/shapes/constraints.ttl).

### Where the analogy misleads

**Missing is not false.** A relational query treats an absent row as "no". OWL makes the
*open-world assumption*: a statement that is not in the graph is unknown, since another dataset may
supply it. That is why LATTICE needs SHACL at all. A shape is how you say "in this dataset, I expect
this to be present". It is also why Eligibility can answer "undetermined" when a fact is missing
(chapter 8).

**Two names can mean one thing.** A database assumes two different keys are two different rows. OWL
makes no such *unique-name assumption*. Two IRIs may name the same thing until something says
otherwise, and a reasoner can conclude that they are the same individual. Foundation's own example
states outright that its key schemes are different from one another, for exactly this reason
(chapter 2 shows the statement).

**Properties are many-valued by default.** A node can have two values for a property without
anything being wrong, unless a shape caps it. A lender can hold several roles, and a facility can be
classified under several industries, with no extra table.

**Class membership can be worked out.** A row belongs to one table, fixed when it is inserted. A node
can belong to many classes, and an OWL reasoner can add memberships the data never stated, from
class definitions. Chapter 2 shows a class defined as "every key whose scheme is the market
reference scheme", which any key with that scheme joins automatically.

**Schema and data share one format.** The ontology and the facts it describes are both triples, and
can sit in the same graph. A query can ask about the schema as easily as about the data, for example
"which properties of this class are single-valued".

None of these differences is exotic once named. Keep them in mind as you read the excerpts in the
rest of the tutorial.
