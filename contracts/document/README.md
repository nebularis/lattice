<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Document markup

LATTICE's own markup for a document's structure and marks, major version 1, in the namespace `https://www.nebularis.org/neuro-semantic/lattice/document/1` ([ADR-A137](../../docs/architecture/decisions/ADR-A137-document-markup-vocabulary.md)). It records structure, never meaning. What the marked text means is the Wording layer's RDF, which the [`document-to-wording`](../xml/README.md) kit produces from it.

| File | What it is |
|---|---|
| [`document.rnc`](document.rnc) | the schema, in RELAX NG compact syntax. The source we write and review |
| [`document.xsd`](document.xsd) | XSD 1.0 generated from it by Trang with `mise run build:document-schema`, for tools that validate with XSD. Never edited by hand |
| [`samples/`](samples) | a facility agreement and a software licence |
| [`fixtures/valid/`](fixtures/valid), [`fixtures/invalid/`](fixtures/invalid) | documents each schema must accept or refuse |

## The structure

A `document` carries its `id` and holds `meta`, its title, the template it was drafted from and the variables it declares, and `body`, its sections. A `section` holds clauses, definitions and text no element marks (`unmarked`). A `clause` or a `definition` is mixed content, whose text may carry two inline marks, a `var` that shows a declared variable's value and a `ref` to another element by its identifier. A definition names the term it defines in `term`.

The text of a clause or a definition is read exactly, so a document keeps no indentation inside one, and each run of text between marks is one part of the element's text.

## The check

The authoring service's tests check that `document.xsd` is Trang's output from `document.rnc`, and that the two schemas give the same verdict on every document here, the valid fixtures and the samples accepted and the invalid fixtures refused. A verdict on which they differ fails the check, which also keeps the RELAX NG within what XSD 1.0 can express.

```bash
mise run check:authoring-service
```

What neither schema states, such as the number of sections a document may hold, the service limits where it receives a document.
