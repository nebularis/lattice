<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 2. Reading Turtle
{: #turtle}

LATTICE's ontologies and examples are written in **Turtle**, a plain-text notation for triples. You
need perhaps a dozen rules to read every excerpt in this tutorial. This chapter teaches them on one
file, the Foundation layer's
[keys example](https://github.com/nebularis/lattice/blob/main/ontology/foundation/examples/keys.ttl),
which records the identifiers of the facility agreement and its parties. Chapter 4 explains what
the file *means*. Here we only read it.

### Prefixes shorten IRIs

A file starts by declaring short prefixes for long IRI stems.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
@prefix fnd:     <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:      <https://example.org/lattice/foundation/keys#> .
```

After this, `fnd:Key` means `https://www.nebularis.org/neuro-semantic/lattice/foundation#Key`.
Each LATTICE layer has its own prefix, `fnd:` for Foundation, `ins:` for Instrument and so on.
`owl:`, `rdfs:` and `xsd:` are W3C standards. `ex:` is the example's own namespace, standing in for
the namespace your project would use. A full IRI written out in angle brackets, `<…>`, means the same
as its prefixed form.

### A statement, then more statements about the same subject

A triple is written subject, property, object, and ends with a full stop.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
key-mr:MR-2027-000412 a fnd:Key , ex:MarketReferenceKey ;
    fnd:keyScheme ex:market-reference ;
    fnd:keyValue "MR-2027-000412" .
```

Read it as four statements about one subject, the market reference key.

- `a` is shorthand for `rdf:type`, "is an instance of". The key is a `fnd:Key`.
- A **comma** repeats the subject and property with another object. The key is also an
  `ex:MarketReferenceKey`.
- A **semicolon** repeats the subject with a new property. Its scheme is `ex:market-reference`.
- The **full stop** ends the group. Its value is the string `"MR-2027-000412"`.

Indentation is only for people. Text in double quotes is a literal, and an IRI is a link to another
node. Following the links from node to node is how you navigate the graph.

### Comments, booleans and typed values

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:agreement-number a fnd:KeyScheme ;                    # issued by the facility agent
    rdfs:label "Facility agent's agreement numbers" ;
    fnd:reissuesValues false ;
    fnd:sensitiveDataScheme false ;
    fnd:keyNormalisation "NfkcTrimUppercase" .
```

Everything after `#` on a line is a comment. `false` and `true` are booleans, and bare numbers are
numbers. Other typed values carry their datatype after `^^`, for example `"2027-03-31"^^xsd:date`. A
string can carry a language tag instead, as in `"industry"@en` in chapter 1.

### Classes and subclasses

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:Agreement a owl:Class ; rdfs:subClassOf fnd:Version .
ex:AgreementIdentity a owl:Class ; rdfs:subClassOf fnd:PersistentIdentity , fnd:NaturallyKeyed .
```

The project declares its own class `ex:Agreement` and says every agreement is a `fnd:Version`, a
Foundation class. This is how you extend LATTICE. You subclass its classes, and your data picks up
everything the layer says about the parent. `ex:AgreementIdentity` has two parents, which a
class may.

### Nodes without names

Square brackets make a node with no IRI of its own, a **blank node**, described in place. Round
brackets make an ordered list.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
[] a owl:AllDifferent ;
    owl:distinctMembers ( ex:agreement-number ex:market-reference ex:company-number
                          ex:lei ex:account-number ex:national-id ) .
```

This is the statement chapter 1 promised. With no unique-name assumption, nothing would stop a
reasoner from concluding two of these schemes are one. The statement rules it out, so a key typed
with one scheme's key class but carrying another scheme makes the data inconsistent, rather than
merging the two schemes.

A blank node can also carry properties inside its brackets. Here one defines a class by a condition
rather than by a list of members.

<!-- source: ontology/foundation/examples/keys.ttl -->
```turtle
ex:MarketReferenceKey a owl:Class ;
    rdfs:subClassOf fnd:Key ;
    owl:equivalentClass [ a owl:Restriction ; owl:onProperty fnd:keyScheme ; owl:hasValue ex:market-reference ] .
```

Read the bracket as "anything whose `fnd:keyScheme` is `ex:market-reference`". The class *is* that
set. A key that has the scheme belongs to the class whether or not anyone wrote `a
ex:MarketReferenceKey` against it. That is the class membership that is worked out, from chapter 1.

### What you can now read

With prefixes, `a`, commas, semicolons, literals, comments, blank nodes and lists, you can read
nearly every line of LATTICE's examples. Two more things appear later and are explained where they
do. One is SHACL shapes, which you met in chapter 1. The other is SPARQL queries, which some files
include in comments.
