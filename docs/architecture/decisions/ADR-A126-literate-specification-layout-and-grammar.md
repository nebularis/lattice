---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A126: Literate specification layout and grammar

**Status:** Published, 2026-10-19. Accepted 2026-10-17.
**Described in:** [Literate specifications](../literate-specifications.md)
**Date:** 2026-10-16
**Supersedes:** none. Adds addenda to ADR-A120 and to ADR-A01's convention note (2026-10-17)
**Related:** [ADR-A01](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A01-layer-dependency-order.md), [ADR-A86](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A86-ontology-semantic-versioning.md)
and the [versioning policy](../ontology-versioning-policy.md),
[ADR-A97](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A97-mork-order-relations-in-owl-2-dl.md) (OWL 2 DL), [ADR-A120](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A120-literate-specs-with-several-documents.md),
[ADR-A121](ADR-A121-repository-catalogue.md), [ADR-A127](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A127-published-architecture-decisions.md),
[ADR-A-C2](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-AC2-clean-room-authoring-procedure.md) (examples first), [conventions document](../literate-specifications.md)

## Context

A layer's `README.md` is its authoritative specification, and its Turtle is extracted from fenced blocks in
document order. Three problems have grown with the layers.

- **Facts are written more than once, and the copies drift.** A term's Definition and Utility are written
  in prose and again as `rdfs:comment` and `fnd:utility` strings in its block, and for `fnd:Version` the two
  already read differently. Vocabulary states `voc:ConceptScheme`'s superclass `skos:ConceptScheme` in an
  alignment block, in a Utility paragraph and in an axiom index row, and not in the class's own block.
- **Practice differs by layer.** READMEs order and name their sections differently. Instrument checks 91
  counts in SHACL that no OWL restriction states, and Quantification asserts 50 in OWL that no shape checks.
- **Blocks make READMEs hard to read.** Many `turtle-spec` blocks exist only for the extractor, and a reader
  who wants the Turtle can open the generated file.

About 2,700 axiom statements make up the literate layers' spec and vocab documents (measured 2026-10-15).
Fewer than 30 of them need more than a label, a short list of class expressions or a restriction table to
state.

## Decision

1. **One layout for every module README.**

   | § | Section | Required | Normative | Extracted to |
   |---|---|---|---|---|
   | 1 | Purpose and Scope | yes | yes | the ontology's `dct:description` |
   | 2 | Namespace and Prefixes | yes | yes | prefixes, the ontology header, creators and contributors |
   | 3 | Extraction Contract | yes | yes | the module's repository catalogue entry (ADR-A121) |
   | 4 | Overview | yes | no | nothing. Holds a generated class diagram |
   | 5 | Detailed Design | yes | no | nothing |
   | 6 | Description Logic Encoding | yes | yes | spec and vocab documents |
   | 7 | Shapes | yes | yes | shape files |
   | 8 | Examples | yes | no | nothing. Examples stay hand-written files |
   | 9 | Canonicalisation | no | yes | nothing |
   | 10 | Formalisation | no | yes | `isabelle-spec` blocks and what is generated from them |
   | 11 | Dependencies | yes | no | nothing |
   | 12 | Release Notes | yes | yes | nothing. Checked |
   | 13 | Open Issues | yes | no | nothing |

   Section 6 has the subsections 6.1 Classes, 6.2 Object Properties, 6.3 Datatype Properties, 6.4
   Individuals, 6.5 Disjointness and Keys, 6.6 Other Axioms and 6.7 Axiom Index. Numbers are fixed. An absent
   optional section keeps its heading and says "Not applicable.", and an empty subsection says "None." A
   layer adds no top-level section of its own. Other material goes into a subsection of Detailed Design or of
   Open Issues. The extractor finds a section by its title and warns when its number differs from the layout.
2. **Normative sections win.** Where a non-normative section disagrees with a normative one, the normative
   section is the specification. Overview and Detailed Design never introduce an axiom.
3. **Section 6 is written in a grammar, and is the only source of a term's axioms.** An entry is a level-4
   heading holding one CURIE, followed by labelled paragraphs and tables, for example `**Definition.**` for
   `rdfs:comment`, `**Utility.**` for `fnd:utility`, `**Label.**` for `rdfs:label`, `**Subclass of.**`,
   `**Equivalent to.**`, `**Domain.**`, `**Range.**`, `**Characteristics.**`, `**Inverse of.**`,
   `**Subproperty of.**`, `**Key.**` and `**Restrictions.**`. A further label adds a further annotation, for
   example `**Scope note.**` for `skos:scopeNote`. An unknown label is an error. `rdfs:label` comes only from
   a `**Label.**` line.
4. **Class expressions are OWL Manchester syntax with CURIEs**, wherever one appears: superclasses,
   equivalent classes, domains, ranges and the values of a restriction. Literals use Turtle's forms.
5. **A restriction row states where it is asserted:** in OWL and SHACL (the default), in OWL only, or in
   SHACL only. Some OWL restrictions are hints to the reasoner for design-time tooling, so an OWL restriction
   is also checked in SHACL unless the row says otherwise. SHACL is generated only for the flat forms
   (`exactly`, `min`, `max`, their qualified forms, `only`, `some` and `value`), and a nested expression is
   refused unless its row says OWL only. A qualified restriction maps to SHACL's qualified form, never to
   `sh:class` with counts, since the two say different things. Generated SHACL goes into one shape per class
   in the module's structural shapes file. Hand-written shapes stay in blocks in section 7.
6. **What the grammar cannot say stays a block.** Section 6.6 holds `turtle-spec` blocks for the rest, for
   example property chains.
7. **Generated regions.** The Axiom Index and the Overview's class diagram are generated from section 6 into
   marked regions of the README, written in place and kept current by the extractor's check. A hand edit
   inside a region is reported by the check and lost at the next extraction.
8. **HTML comment markers do four things.** They exclude text from an extracted region, hide a fenced block
   that is still extracted, send a region of entries to another file, and mark a generated region. A region
   opens with `<!-- start: {...} -->` and closes with `<!-- end -->`, which closes the innermost open region.
   A hidden block is one comment wrapped round a fence. The keys are `exclude`, `output-file` and
   `generated`, and any other key is an error. A marker inside a fenced block is text. A hidden block may not
   contain `-->`, and mermaid is never hidden.
9. **One name, `output-file`, in two forms.** It is the `# @output-file` first line of a fenced block, as
   ADR-A120 defines it, or the JSON key of a marker. A block that carries both is refused. Both forms apply to
   every extracted block kind.
10. **Extraction rules.**
    - Extracted markdown becomes plain text. Links become their text and an absolute URL at the release tag
      that the section 2 version names.
    - Generated Turtle is sorted by subject and then by a fixed predicate order, so reorganising a README
      changes no generated file. A document's fenced blocks follow its generated statements, ordered by
      their own text, and declare no prefix, since section 2's prefix table is the one source of prefixes
      (clarified 2026-10-18).
    - Dublin Core terms are declared in each document as annotation properties, with the `dct:` prefix, and
      never imported, so every document stays in OWL 2 DL.
    - Creators and contributors come from a table in section 2 that the maintainers keep. Each is
      identified by an IRI, an ORCID iD where the person has one and their GitHub profile otherwise. No legal
      name appears in a README or a generated artefact without that person's express permission.
11. **Release notes are checked, not extracted.** Every version named in section 2, and every released
    version, has an entry. An entry says what changed and cites only published ADRs (ADR-A127).
12. **Versioning is unchanged.** Generated Turtle stays tracked and versioned under ADR-A86. A layer's first
    regeneration under this layout is one PATCH release, checked to be the same graph as before except for
    reconciliations the maintainer approves.
13. **One conventions document.** `docs/architecture/literate-specifications.md` describes the layout, the
    grammar, the markers and the extraction rules. Each README's section 3 links to it and states only what
    is specific to its module. The tool documentation, the ontology architecture document, the glossary and
    the ontology authoring skill link to it rather than restating it.

## Consequences

- ADR-A120 has an addendum for decision 9, and ADR-A01 one for its convention note, which placed the ontology
  header in a README's first `turtle-spec` block (both 2026-10-17).
- Each layer is migrated in its own change, with its own PATCH release. Until a layer is migrated, its
  README keeps today's conventions and `literate_extract.py --check` keeps testing it as now.
- The 76 restrictions asserted in OWL with no shape today migrate as OWL only, so migration adds no shape
  and no new violation.
- A layer with no release notes today gets them rebuilt from its history when it migrates. Existing notes
  that cite delivery slices are rewritten to say what changed.
- Foundation, Vocabulary and Party are not yet the source of their documents. Each is reconciled before or
  during its migration, with every difference listed for the maintainer.
- The extractor stays standard-library only. The grammar is line-based so that a small parser suffices,
  including a recursive-descent parser for the Manchester subset in use.
- Persistence, MORK, the applied modules and Governance are not literate today. They take the layout when
  they become literate.

## Provenance

Proposed in the [improved ontology documentation sketch](../../developer/sketches/improved-ontology-documentation.md)
and settled in design discussion on 2026-10-15 and 2026-10-16, recorded as decisions OD-D1 to OD-D27 in the
[`improved-ontology-documentation` plan](../../developer/plans/improved-ontology-documentation.md) (slices OD1
to OD8 onward). The measurements cited in the context are in that unit's status record.
