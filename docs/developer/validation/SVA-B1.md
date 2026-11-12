<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B1, resolving an import closure in the browser

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B1 of the [plan](../plans/studio-visual-authoring.md), from section 5.1 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-12 in autonomous mode.

## Invariant

An import is resolved only from what the author dropped, what the workspace holds or what the service stages, in one fixed order, which is the dropped catalog, a dropped file that declares the IRI, a held import, then a staged document. What none of them gives is reported missing and is never guessed, and nothing is fetched from the web (ADR-A88, SVA-Q5). The same input in any order gives the same plan, and a cycle of imports ends.

## What changed

- **`rdf/catalog.ts`.** `parseCatalog` reads an OASIS XML catalog, with `uri`, `nextCatalog`, `group`, `xml:base` on the root and on a group, and ignores every other element. It returns each target as a path relative to the dropped root, or as written when it has a scheme. `buildCatalogLookup` follows `nextCatalog` chains among the dropped files with a visited set and returns one merged lookup, the chained catalogs that were not dropped and the catalogs that could not be read.
- **`rdf/imports.ts`.** `ontologyHeader` reads an ontology IRI, a version IRI and the `owl:imports` of a Turtle document with n3 and of an RDF/XML document from its header alone with the browser's XML parser. `resolveImports` walks the closure breadth first and returns the plan, which holds the nodes sorted by IRI with how each resolved, the edges, the roots and the problems.
- **Nothing else.** No UI file, no service change and no new dependency. The tests use the per-file directive `// @vitest-environment jsdom`, and `jsdom` is already in the root lockfile.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| B1-T1 | `uri` entries with relative, `..` and percent-escaped targets / `parseCatalog` / each target is a path relative to the dropped root, decoded | L1, positive | Targets equal the expected paths |
| B1-T2 | a root `xml:base`, nested groups with `xml:base`, and a `system` element / `parseCatalog` / bases compose, and the other element gives no entry | L1, positive | Targets carry the composed bases |
| B1-T3 | a target with a scheme / `parseCatalog` / it is kept as written, never turned into a path | L1, negative | The web location is unchanged |
| B1-T4 | text that is not XML, and XML that is not a catalog / `parseCatalog` / an error is returned and no entry | L1, negative | `error` is set, the lists are empty |
| B1-T5 | a stub catalog chaining to a root catalog that chains on, with a duplicate IRI / `buildCatalogLookup` / one lookup, the first catalog wins the duplicate | L1, positive | The lookup holds the first target and every chained entry |
| B1-T6 | two catalogs that chain to each other / `buildCatalogLookup` / it ends, each read once | L1, negative | Both catalogs' entries, no hang |
| B1-T7 | a `nextCatalog` target not dropped, a start catalog not dropped, a catalog that is not XML / `buildCatalogLookup` / each is listed, and the rest is read | L1, negative | `missingCatalogs` and `errors` name them |
| B1-T8 | paths with `.`, `..`, doubled slashes and backslashes / `normalisePath` / one normal form, and a climb above the root kept | L1, positive | Equal to the expected strings |
| B1-T9 | Turtle with a version IRI and imports / `ontologyHeader` / the three parts | L1, positive | Equal to the expected header |
| B1-T10 | RDF/XML with `rdf:about`, and one with an empty or relative `rdf:about` and a relative import under `xml:base` / `ontologyHeader` / the IRIs, resolved against the base, and no body read | L1, positive | Equal to the expected headers |
| B1-T11 | a document with no `owl:Ontology`, in each syntax / `ontologyHeader` / no IRI and no imports | L1, negative | `{ imports: [] }` |
| B1-T12 | Turtle and RDF/XML that do not parse / `ontologyHeader` / `HeaderError` | L1, negative | It throws |
| B1-T13 | an import for each way and one for none / `resolveImports` / the statuses `catalog`, `file`, `held`, `staged` and `missing`, a held node with its digest | L1, positive | Each node has its status, and no problem is raised |
| B1-T14 | an IRI both mapped by the catalog and declared by a dropped file, one held and dropped, one held and staged / `resolveImports` / the earlier step wins each time | L1, positive | The catalog path, `file`, and `held` |
| B1-T15 | a chain of three documents / `resolveImports` / each document's own imports are walked, edges listed | L1, positive | Nodes and edges equal the expected |
| B1-T16 | two documents importing each other / `resolveImports` / it ends and raises no problem | L1, negative | Both nodes, each importing the other |
| B1-T17 | two documents importing a third / `resolveImports` / `importedBy` lists both | L1, positive | Both importers, sorted |
| B1-T18 | a catalog entry whose file was not dropped / `resolveImports` / a problem, the import missing, and a dropped file that declares the IRI still resolves it | L1, negative | `catalog-file-not-dropped` and the two statuses |
| B1-T19 | a catalog entry with a web location / `resolveImports` / a problem, the import missing, nothing fetched | L1, negative | `catalog-web-location` |
| B1-T20 | a catalog entry whose file declares another IRI / `resolveImports` / resolved through the catalog with a problem | L1, negative | `catalog-iri-mismatch` |
| B1-T21 | a file that does not parse, a root not dropped and a root with no ontology / `resolveImports` / one problem each | L1, negative | `unparseable`, `root-not-dropped`, `root-without-ontology` |
| B1-T22 | two files declaring one IRI / `resolveImports` / the first path by name is used, and a problem | L1, negative | `ambiguous-declaration` |
| B1-T23 | the same input with the files and roots permuted, and repeated / `resolveImports` / the same plan | L1 | The plans are equal |
| B1-T24 | the real `ontology/catalog-v001.xml` and the files it names for three roots, `foundation.ttl`, `persistent-foundation.ttl` and `ledger.ttl` / `resolveImports` / every import in a LATTICE namespace resolves with status `catalog` and raises no problem | L2, positive | No LATTICE node is missing |
| B1-T25 | a per-directory stub catalog as the start / `buildCatalogLookup` with `resolveImports` / the stub's `nextCatalog` reaches the root catalog | L2, positive | The foundation import resolves with `catalog` |
| B1-T26 | the same closure / `resolveImports` / an import outside LATTICE, such as PROV-O, is missing | L2, negative | Every non-LATTICE import is `missing` |
| B1-T27 | `foundation.ttl` removed from the dropped files / `resolveImports` / the foundation import is missing and its catalog entry is a problem | L2, negative | `catalog-file-not-dropped` with the file's path |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/catalog.test.ts src/rdf/imports.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types.

## Artefacts to inspect

- `apps/config-studio/src/rdf/catalog.ts` and `imports.ts`, and their two test files.
- The plan `resolveImports` returns for the real closure, which B1-T24 asserts on and which a reviewer can print from the test.

## Deliberate non-coverage

- **The UI.** The import dialog, the drawn import graph and Replace resolving again are SVA-B3.
- **Holding the closure.** Fencing each resolved document and holding every import in one write are SVA-B2a.
- **Staged documents.** What the service stages, and the set of IRIs it gives the browser, are SVA-B2b. Here the set is an input.
- **Held imports.** The digests are inputs. A held import's own imports are not walked, since the workspace does not give them to this function.
- **Size.** The 5 MiB body limit and reporting a document's size belong to the slice that sends the document.
- **A catalog the service reads.** A catalog directory a deployment configures is BL-22.

## Results

The results are filled at verification. What the builder ran on 2026-11-12, in autonomous mode:

- `vitest run src/rdf/catalog.test.ts src/rdf/imports.test.ts`, 2 files and 33 tests passed, none failed.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- Not run: `mise run check:config-studio`, the browser suites and any mutation probe of the order of precedence.
