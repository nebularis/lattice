<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Shape census results

Produced by `census.py`. The README states what is measured and what the method cannot show. Percentages are of subjects with an `rdf:type`, summed over the example graphs of a module.

## Estate

| Item | Count |
|---|---|
| RDF files scanned under ontology | 302 |
| Files read as shapes estate (not test, not sample) | 102 |
| Files that declare at least one shape | 37 |
| Test fixture files excluded | 33 |
| Example graphs used as samples | 166 |
| Sample graphs with no typed subject | 5 |
| Example graphs that also declare shapes | 7 |
| Parse failures | 1 |
| Node shapes counted | 505 |
| Stand-alone property shapes (not classified) | 0 |
| Deactivated node shapes skipped | 0 |

## Classification of node shapes

| Module | Shapes | Row-mappable | Bounded but open | Other | Closed | Not closed | Non-simple path | Unbounded property | or | xone | not | sparql |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| applied/asset-class | 4 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| applied/capacity | 8 | 0 | 4 | 4 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 4 |
| applied/insurance/exposure | 50 | 0 | 0 | 50 | 0 | 50 | 0 | 0 | 0 | 0 | 0 | 50 |
| applied/insurance/peril | 9 | 0 | 0 | 9 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 9 |
| behaviour | 48 | 0 | 21 | 27 | 0 | 48 | 1 | 7 | 2 | 0 | 2 | 17 |
| eligibility | 21 | 0 | 5 | 16 | 0 | 21 | 0 | 5 | 2 | 0 | 0 | 9 |
| examples/insure-o | 2 | 0 | 1 | 1 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| foundation | 13 | 0 | 3 | 10 | 0 | 13 | 1 | 2 | 1 | 0 | 0 | 7 |
| instrument | 104 | 0 | 12 | 92 | 0 | 104 | 9 | 42 | 19 | 4 | 5 | 37 |
| ledger | 30 | 0 | 7 | 23 | 0 | 30 | 0 | 1 | 0 | 0 | 0 | 22 |
| mork | 6 | 0 | 0 | 6 | 0 | 6 | 0 | 1 | 0 | 0 | 0 | 5 |
| persistence | 69 | 0 | 21 | 48 | 1 | 68 | 0 | 21 | 2 | 0 | 0 | 27 |
| quantification | 13 | 0 | 7 | 6 | 0 | 13 | 0 | 0 | 0 | 0 | 1 | 5 |
| spc | 3 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| surface | 45 | 0 | 10 | 35 | 0 | 45 | 0 | 3 | 0 | 0 | 0 | 32 |
| v-rig | 19 | 0 | 17 | 2 | 0 | 19 | 0 | 1 | 0 | 1 | 0 | 0 |
| vocabulary | 8 | 0 | 3 | 5 | 0 | 8 | 0 | 1 | 0 | 0 | 0 | 4 |
| wording | 53 | 0 | 23 | 30 | 0 | 53 | 2 | 13 | 2 | 1 | 0 | 15 |
| all | 505 | 0 | 134 | 371 | 1 | 504 | 13 | 98 | 28 | 6 | 8 | 250 |

The criterion columns count the shapes that fail that criterion, so a shape that fails two is counted in both.

Shapes whose only failing criterion is the one named:

| Criterion | Shapes failing it | Shapes failing only it |
|---|---|---|
| not_closed | 504 | 134 |
| non_simple_path | 13 | 0 |
| unbounded_property | 98 | 1 |
| has_or | 28 | 0 |
| has_xone | 6 | 0 |
| has_not | 8 | 0 |
| has_sparql | 250 | 0 |

## Property shapes

| Path kind | Property shapes | With maxCount |
|---|---|---|
| alternative | 5 | 0 |
| inverse | 7 | 2 |
| predicate | 591 | 446 |
| sequence | 11 | 4 |

Of 614 property shapes inside node shapes, 452 carry a `sh:maxCount`. 292 node shapes have no property shapes, and 34 of the bounded-but-open shapes are among them. Those carry no constraint on the shape of a row, so a second coverage figure below leaves them out.

## Coverage of example subjects

The columns give the share of subjects targeted by a shape of the class named. Subclass following uses the `rdfs:subClassOf` triples of the ontology files and of the example graph itself. The direct columns do not follow subclasses.

| Module | Graphs | Subjects | Row-mappable, direct % | Row-mappable, subclass % | Bounded or better, subclass % | Bounded or better, with properties, subclass % | Any shape, direct % | Any shape, subclass % | No shape, subclass % |
|---|---|---|---|---|---|---|---|---|---|
| applied/asset-class | 2 | 6 | 0.0 | 0.0 | 33.3 | 33.3 | 100.0 | 100.0 | 0.0 |
| applied/insurance/exposure | 6 | 252 | 0.0 | 0.0 | 27.4 | 27.4 | 66.7 | 71.0 | 29.0 |
| applied/insurance/peril | 1 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| behaviour | 12 | 609 | 0.0 | 0.0 | 39.6 | 29.7 | 77.5 | 81.4 | 18.6 |
| eligibility | 13 | 231 | 0.0 | 0.0 | 35.1 | 33.8 | 61.5 | 65.4 | 34.6 |
| examples/insure-o | 8 | 14 | 0.0 | 0.0 | 78.6 | 78.6 | 100.0 | 100.0 | 0.0 |
| foundation | 1 | 41 | 0.0 | 0.0 | 14.6 | 14.6 | 65.9 | 65.9 | 34.1 |
| instrument | 24 | 1914 | 0.0 | 0.0 | 43.7 | 36.8 | 69.5 | 69.9 | 30.1 |
| ledger | 10 | 217 | 0.0 | 0.0 | 53.5 | 53.5 | 75.1 | 78.3 | 21.7 |
| mork | 15 | 254 | 0.0 | 0.0 | 2.4 | 2.4 | 15.4 | 72.8 | 27.2 |
| ontology/examples (no module) | 4 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| persistence | 38 | 220 | 0.0 | 0.0 | 73.6 | 73.6 | 91.8 | 91.8 | 8.2 |
| quantification | 2 | 106 | 0.0 | 0.0 | 17.9 | 17.9 | 39.6 | 41.5 | 58.5 |
| surface | 6 | 80 | 0.0 | 0.0 | 40.0 | 40.0 | 56.2 | 56.2 | 43.8 |
| v-rig | 6 | 89 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| vocabulary | 12 | 76 | 0.0 | 0.0 | 64.5 | 64.5 | 92.1 | 92.1 | 7.9 |
| wording | 6 | 321 | 0.0 | 0.0 | 62.9 | 34.9 | 66.4 | 66.4 | 33.6 |
| all | 166 | 4430 | 0.0 | 0.0 | 43.4 | 36.9 | 68.2 | 72.9 | 27.1 |

The proposed threshold is 80% of subjects covered by row-mappable shapes, per module. No module reaches it with subclasses followed.

## Limits seen in this run

Counts for the run, each of which bears on how far the figures can be trusted:

| Item | Count |
|---|---|
| Node shapes with no target of their own, reached only through other shapes | 4 |
| Node shapes with a SPARQL target, not evaluated, so no-shape shares are upper bounds | 0 |
| Node shapes declared in more than one file, analysed as the union of the declarations | 1 |
| Node shapes declared across more than one module | 0 |
| References through sh:and or sh:node to an IRI with no triples in any file read | 0 |

Files that did not parse:

- `ontology/mork/spec/Mork.owl`, ParserError: ontology/mork/spec/Mork.owl:505:16: Repeat node-elements inside property elements: http://www.w3.org/2002/07/owl#ObjectSomeValuesFrom

Example graphs that declare shapes of their own, counted as sample data and not as shapes estate:

- `ontology/mork/examples/Governance/GovernanceAndVersioning.ttl`, 9 shapes
- `ontology/persistence/examples/composite-project-ownership.ttl`, 6 shapes
- `ontology/persistence/examples/composite-property-boundary-shacl.ttl`, 2 shapes
- `ontology/persistence/examples/invalid-compositeboundary-receiptonly.ttl`, 2 shapes
- `ontology/persistence/examples/invalid-uniqueness-outside-boundary.ttl`, 2 shapes
- `ontology/persistence/examples/write-discipline-composite-append-versions.ttl`, 2 shapes
- `ontology/persistence/examples/write-discipline-delta-membership.ttl`, 2 shapes
