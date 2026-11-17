<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store shape census (MSA-I1)

This spike counts the SHACL shapes the ontology tree declares and asks how many of them could be read as a description of a table row. It answers the falsifier of investigation MSA-I1 in the multi-store sketch: the share that maps is too small to be worth a mapping.

The proposed threshold is closed and bounded shapes covering at least 80% of the subjects in the sample graphs, per family. The census reports the share whatever it is. It does not decide the threshold.

## Run

From inside the repository:

```
mise exec -- python spikes/multi-store-shape-census/census.py
```

On Windows PowerShell the `mise` command is a function that drops a bare `--`, so quote it as `mise exec '--' python ...`. The script needs rdflib and nothing else. It does not run pyshacl and does not validate any graph.

The script prints the summary and writes two files under `results/`:

- `census.json` has the full record, one entry per node shape and per sample graph, with sorted keys and no timestamps. It is over a megabyte and is not committed, so run the script to read it.
- `summary.md` has the tables.

Two runs on the same checkout produce identical files.

## Where the root and the ontology directory come from

The script asks the repository catalogue reader, `tools/lattice_repo_catalogue.py` (STD-273), for the repository root with `find_root()`, loads the catalogue with `load()`, and takes the `ontology` and `spikes` areas, the module list and the generated-path test from it. It writes no ontology path itself.

The reader is a stand-alone file in `tools/` and not an importable package, so the script has to find the file before it can ask. It walks up from the directory named in `LATTICE_ROOT` or, when that is unset, from the working directory, to the first directory that contains `tools/lattice_repo_catalogue.py`. Run it from inside the repository or set `LATTICE_ROOT`.

## What is read

The script walks `ontology/` and parses every `.ttl`, `.trig`, `.owl`, `.rdf` and `.nt` file. Each file is put in one of four groups by its path.

| Group | Rule | Use |
|---|---|---|
| Generated | The catalogue names the path as generated | Excluded and listed |
| Test fixture | The file is under a directory called `test` | Excluded and listed, because the fixtures hold deliberately invalid shapes and data |
| Sample graph | The file is under a directory called `examples` or `cases` | Measured for coverage |
| Shapes estate | Anything else | Read for shapes, classes and `rdfs:subClassOf` |

The module of a file is the longest catalogue module path that prefixes its path. A file under `ontology/` with no module, such as the loose files in `ontology/examples/`, is reported under its own label. The role is the directory directly below the module.

TriG files are flattened, so the named graphs are merged and subjects are counted once per file. A file that does not parse is recorded with its error and the run continues.

## What is counted as a shape

A node shape is a subject that is typed `sh:NodeShape` or that carries any of the target, `sh:property`, `sh:closed`, `sh:sparql`, `sh:and`, `sh:or`, `sh:xone`, `sh:not`, `sh:node` or `sh:rule` predicates, and that has no `sh:path`. An anonymous shape counts only when it has a target, so the shapes nested inside `sh:or`, `sh:node` or `sh:property` are not counted a second time. A stand-alone property shape is a shape with a `sh:path` and a target, and is listed but not classified.

A shape that is declared in several files is read from the union of the files. The module and file given for it are those of the file that types it as a shape, or the first file by name.

For each node shape the census records the targets (`sh:targetClass`, `sh:targetNode`, `sh:targetSubjectsOf`, `sh:targetObjectsOf`, `sh:target` and the implicit class target of an IRI that is also declared a class), `sh:closed` and `sh:ignoredProperties`, the counts of `sh:and`, `sh:or`, `sh:xone`, `sh:not`, `sh:sparql` and `sh:rule`, and each property shape with its path kind and string, `sh:minCount`, `sh:maxCount`, `sh:datatype`, `sh:class`, `sh:nodeKind` and `sh:node`.

The members of a `sh:and` and the values of `sh:node` are read as part of the shape, because they constrain the same focus node. The count of property shapes and the classification include them.

## Classification

A node shape fails a criterion when:

| Criterion | The shape fails it when |
|---|---|
| `not_closed` | It does not have `sh:closed true` |
| `non_simple_path` | Any property path is not a single predicate or the inverse of a single predicate |
| `unbounded_property` | Any property shape has no `sh:maxCount` |
| `has_or` | The shape or one of its property shapes has `sh:or` |
| `has_xone` | The same for `sh:xone` |
| `has_not` | The same for `sh:not` |
| `has_sparql` | The same for `sh:sparql` |

The classes are:

- Row-mappable fails no criterion.
- Bounded but open fails `not_closed` and no other criterion.
- Other is everything else.

The summary gives, per module, how many shapes fail each criterion and, overall, how many fail only that criterion. A criterion with a high sole-blocker count is the cheapest to change.

## Coverage

Sample graphs are the files in the `examples` and `cases` role directories. For each sample graph the census takes every subject that has an `rdf:type`, blank nodes included, and asks which shapes target it. A subject is targeted when one of these holds:

- a shape has `sh:targetNode` set to the subject
- a shape has `sh:targetClass`, or is itself a class, for a type of the subject, or for a superclass of one of them in the subclass-following variant
- a shape has `sh:targetSubjectsOf` for a predicate the subject uses
- a shape has `sh:targetObjectsOf` for a predicate that points at the subject

The shapes that count are those from the shapes estate. A sample graph that declares shapes of its own is listed, and its own shapes are not used.

Each module gets these shares, as a percentage of subjects summed over its sample graphs:

- Row-mappable, direct, with no subclass followed
- Row-mappable, with `rdfs:subClassOf` followed
- Bounded or better, with subclasses followed, which counts row-mappable and bounded-but-open shapes
- Bounded or better again, leaving out shapes that have no property shapes
- Any shape, direct and with subclasses followed
- No shape, with subclasses followed

Subclass following walks `rdfs:subClassOf` upward over the subclass triples of the shapes estate and of the sample graph itself, and takes the best classification found on the way. The census reports both variants so that the effect of the walk is visible. For each module it also lists the types of the subjects that no shape reaches.

Where several shapes target the same class, the subject gets the best classification among them. A subject is counted as row-mappable when some row-mappable shape targets it, not when all the shapes that target it are.

## Limits

- The census reads shapes and not behaviour. It does not run any validation, so it cannot say whether the sample data conforms.
- Targets given by a SPARQL `sh:target` are recorded and not evaluated. The no-shape share is an upper bound where such targets exist. The run reports how many there are.
- Subjects without an `rdf:type` are not counted at all. A sample graph with no typed subject adds nothing, and the summary counts these graphs.
- Subjects are summed per file, so a subject that appears in two sample graphs is counted twice. Larger graphs weigh more than smaller ones.
- The sample graphs are fixtures written to show a feature. They are not a sample of production data, and the shares say how much of the fixtures the shapes reach.
- A node shape with no property shapes passes the bounded criterion without constraining any row. The second bounded-or-better column leaves these out.
- `sh:maxCount 0` counts as bounded. Alternative, sequence and zero-or-more paths, and an inverse of a complex path, are not simple. The nested content of `sh:or`, `sh:xone` and `sh:not` is not analysed beyond their presence.
- A shape with a `sh:deactivated true` flag is listed and left out of the counts and the coverage.
- RDF/XML is parsed with rdflib. A file that rdflib rejects is reported and skipped. Its triples, including any classes and subclass links, are missing from the run.
- Test fixtures are excluded. Their shapes, valid or not, are not in the counts.
- Closed means `sh:closed true`. The census does not check that the closed shape's `sh:ignoredProperties` list is sensible, and it records the list without using it.
