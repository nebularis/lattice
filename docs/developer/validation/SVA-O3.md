<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-O3, the axiom forms of the baseline

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-O3 of the [plan](../plans/studio-visual-authoring.md), from section 6 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-12.

## Invariant

Selecting a class, a property or an individual of the baseline shows every statement the graph holds about it. A statement of a construct the reader knows is in its own section, as a nested structure and never as a line of text, and every other statement is in a table headed "Other statements", so nothing is hidden. The forms only read. They never edit the graph (decision SVA-Q9, the studio renders axioms and does not edit them). The reading is the same for any order of the graph's triples and for any labels its blank nodes carry.

## What changed

- **The reader.** `rdf/axioms.ts` turns the OWL, SHACL and annotation statements about one element into `classAxioms`, `propertyAxioms` and `individualAxioms`. A class expression is a tree of a named class, a restriction, an intersection, a union, a complement, an enumeration, a datatype restriction or an `unknown` node that carries its triples. RDF lists are read once with a visited set, blank nodes are followed to a depth of 32, and a cycle through blank nodes stops at the node it returns to.
- **The forms.** `ui/AxiomForms.tsx` renders those structures read-only with the kit's sections, tables and chips. Each section has an accessible name. A named term the baseline declares is a link that selects it in the baseline view.
- **The baseline view.** `BaselineView.tsx` shows the class form below what the view showed before, and a selected property or any other subject the baseline states something about opens its own form.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| O3-T1 | a class with `owl:someValuesFrom` and with `owl:allValuesFrom` / read / a restriction row with its property, quantifier `some` or `only`, and the named filler | L1 | |
| O3-T2 | `owl:hasValue` with an individual and with a language literal, and `owl:hasSelf` / read / quantifier `value` with the term, and `self` | L1 | |
| O3-T3 | `owl:minCardinality`, `owl:maxCardinality` and `owl:cardinality` / read / `min`, `max` and `exactly` with the number and no filler | L1 | |
| O3-T4 | `owl:minQualifiedCardinality`, `owl:maxQualifiedCardinality` and `owl:qualifiedCardinality` with `owl:onClass`, and one with `owl:onDataRange` / read / the same quantifiers with the number and the filler | L1 | |
| O3-T5 | a restriction on `[ owl:inverseOf ex:p ]` / read / the property is `ex:p` marked inverse | L1 | |
| O3-T6 | `owl:intersectionOf`, `owl:unionOf`, `owl:complementOf` and `owl:oneOf` with individuals and literals / read / each kind with its members in list order | L1 | |
| O3-T7 | `owl:onDatatype` with `owl:withRestrictions` / read / a datatype restriction with its facets sorted | L1 | |
| O3-T8 | an intersection of a named class and a restriction whose filler is a union / read / the nesting is kept to the depth the data has | L1 | |
| O3-T9 | a restriction with no recognised quantifier, and a literal where an expression belongs / read / an `unknown` node with its triples, nothing dropped | L1, negative | |
| O3-T10 | a statement on a restriction's own node that no part of the tree uses / read / it is the expression's `extra` rows | L1, negative | |
| O3-T11 | a cyclic RDF list, and a list cell with no `rdf:rest` / read / terminates and returns an `unknown` node marked malformed | L1, negative | |
| O3-T12 | blank nodes that point to each other through `owl:complementOf` / read / terminates, with an `unknown` node marked as a cycle | L1, negative | |
| O3-T13 | a chain of 40 blank nodes / read / 32 nested levels, then an `unknown` node marked as the depth cap | L1, negative | |
| O3-T14 | a class with labels in two languages, a comment, `skos:definition`, `skos:example` and a typed literal / `classAxioms` / annotations grouped by property and language, the known properties first, values sorted | L1 | |
| O3-T15 | a class with a named superclass and an equivalent class that is an intersection / `classAxioms` / each as an expression tree | L1 | |
| O3-T16 | `owl:disjointWith` stated from either class, and an `owl:AllDisjointClasses` / `classAxioms` of the first, of a member and of the other side / each lists the others, from both directions | L1 | |
| O3-T17 | `owl:hasKey` with two properties, and one holding a literal / `classAxioms` / the first is a key, the second stays in `other` | L1, negative | |
| O3-T18 | properties whose domain is the class, its superclass and its grandparent, and one whose domain is unrelated / `classAxioms` / the three are listed, the inherited ones with the superclass, the unrelated one is not | L1 | |
| O3-T19 | a node shape with `sh:targetClass`, holding property shapes with each constraint of the brief, and a class typed `sh:NodeShape` / `classAxioms` / a shape row for each, a row of path and constraints for each property shape, an `sh:in` list read in order | L1 | |
| O3-T20 | individuals typed with the class / `classAxioms` / each listed once, sorted | L1 | |
| O3-T21 | a class whose every statement is understood / `classAxioms` / `other` is empty | L1 | |
| O3-T22 | a class with an unrecognised type, `rdfs:seeAlso`, a blank node object and `owl:disjointUnionOf` / `classAxioms` / each is in `other` and the label and the superclass, which a section used, are not | L1, negative | |
| O3-T23 | an object property with the five characteristics and a datatype annotation property with the other three / `propertyAxioms` / kinds and characteristics named | L1 | |
| O3-T24 | a property with a domain, a union range and a super-property / `propertyAxioms` / domain and range as expressions, the super-property named | L1 | |
| O3-T25 | `owl:inverseOf` stated on either side / `propertyAxioms` of each / both read the other | L1 | |
| O3-T26 | `owl:propertyChainAxiom` with an inverse member / `propertyAxioms` / the chain with the inverse marked | L1 | |
| O3-T27 | property shapes with `sh:path` of the property, held by a named node shape, by a class and by none / `propertyAxioms` / each with its node shape and target class | L1 | |
| O3-T28 | `owl:equivalentProperty` and a super-property that is a blank node / `propertyAxioms` / both in `other`, and nothing in `other` where all was understood | L1, negative | |
| O3-T29 | an individual with two types, annotations and assertions of two values on one property / `individualAxioms` / types, annotations and assertions grouped by property, values sorted | L1 | |
| O3-T30 | a property declared `owl:AnnotationProperty` / `individualAxioms` / its literal values are annotations, not assertions | L1 | |
| O3-T31 | the same graph with its triples shuffled five ways / the three readers / the JSON of the results is identical | L1 | |
| O3-T32 | the same statements written in reverse order, so blank labels differ / the three readers / the JSON of the results is identical | L1 | |
| O3-T33 | `contracts/config-studio/samples/facility-baseline.ttl` / `classAxioms` of `ex:Facility` / its label, the shape `ex:FacilityShape` that targets it, seven property shape rows, and the extra `dal:ownership` statement of a property shape in that row's `other` | L1 | |
| O3-T34 | the Lending sample's Guarantor selected in the browser / the baseline view opens / a region named "Superclasses" names Party | L6 | |

O3-T1 to O3-T33 are in `apps/config-studio/src/rdf/axioms.test.ts`, 47 tests. O3-T34 is one assertion added to the palette test in `apps/config-studio/e2e/studio.spec.ts`.

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/axioms.test.ts`, then `mise run test:config-studio-browser` for O3-T34.

## Artefacts to inspect

- `apps/config-studio/src/rdf/axioms.ts`, for the types of the tree and the rule that a statement is consumed only when a section understood it.
- `apps/config-studio/src/ui/AxiomForms.tsx`, for the sections and their accessible names, among them Annotations, Superclasses, Equivalent classes, Disjoint classes, Keys, Properties by domain, Shapes that target it, Individuals and Other statements.
- The baseline view with a class, a property and an individual of a sample selected, checking that no statement the Turtle download shows is missing from the form.

## Deliberate non-coverage

- Editing axioms is out by SVA-Q9. The forms hold no input and write nothing.
- Drawing the ontology as a diagram is SVA-O2.
- The terms of imported ontologies arrive with SVA-B3. The forms read the baseline's own graph, so an imported term shows as plain text until then.
- A domain or range written as an expression does not place the class in another class's "Properties by domain". Only a named domain does. The expression is in the property's own form.
- A SHACL path that is not an IRI is shown as an anonymous node with its triples and is not matched to a property.
- Rendering the forms in a browser is covered by one assertion. No component test of the layout exists.

## Results

To be filled at verification.

Run while building, on 2026-11-12, in the working tree of the unit's branch with other slices' edits in the same tree:

- `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/axioms.test.ts` printed `Test Files  1 passed (1)` and `Tests  47 passed (47)`.
- `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` printed nothing and found no type error.
- The Playwright suites were not run, so O3-T34 is authored, not yet run.
