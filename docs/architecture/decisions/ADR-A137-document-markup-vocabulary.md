<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A137: A document markup vocabulary of LATTICE's own, in XML

**Status:** Proposed
**Date:** 2026-10-28
**Related:** [ADR-A118](ADR-A118-word-authoring-proof-of-concept.md) (the Word add-in, whose document model this records), [ADR-A119](ADR-A119-xslt-transformation-sidecar.md) (the XSLT sidecar the mappings run in), [ADR-A136](ADR-A136-configuration-studio.md) (the studio the add-in joins), [ADR-A86](ADR-A86-ontology-semantic-versioning.md) (versioning)
**Unit:** [`config-studio`](../../developer/plans/config-studio.md), step CS12c

## Context

The Word add-in marks a governing instrument's text with content controls (sections, clauses, definitions, defined terms, variables and cross-references) and keeps its metadata in a custom XML part. It sends the service a JSON snapshot of that structure, which the service maps to the Wording layer's RDF. The JSON is a third form between Word's OOXML and the RDF, with its own schemas, and nothing outside LATTICE reads it.

The studio and the add-in are becoming one deployable, and we decided how they speak (CS-Q4). A document travels as XML and what it means as RDF, so that a document can be transformed with XSLT, validated with standard XML tools, and exchanged with markup standards. Akoma Ntoso is the established markup for legal documents, and InsurML is a markup for insurance documents. LATTICE reads governing instruments of any domain, so tying its base form to either would import a domain's structure and a third party's change control.

## Decision

1. **Our own vocabulary.** A document is marked up in an XML vocabulary of LATTICE's own, domain-neutral, defined in `contracts/document`. It records structure and marks, never meaning: a section, a clause, a definition, a defined term, a variable with its value type, and a reference to another element, each with the identifier the add-in already gives it. What the marked text means is the Wording layer's RDF, produced from the markup.
2. **Drawn from Akoma Ntoso, not bound to it.** Its structure follows Akoma Ntoso where the two meet: a document of `meta` and `body`, a hierarchy of containers holding elements, inline marks within an element's text, and a stable identifier on every element that a reference names. It takes only what LATTICE's documents use, and adds nothing Akoma Ntoso would need to read it.
3. **Other markups are targets.** Akoma Ntoso and InsurML are reached by XSLT from our vocabulary, run in the transformation sidecar, and never form the base. A mapping that loses information says what it loses.
4. **Meaning by transformation.** An XSLT maps a document to Wording RDF, so the mapping is one declarative artefact that any XSLT 3.0 processor runs, and the service and the add-in share it rather than each holding a mapper.
5. **Two schema languages, one source.** The schema is written in RELAX NG compact syntax, the source we review. An XSD 1.0 schema is generated from it with Trang, for tools that validate with XSD, such as the JDK's validator, Word's schema library and schema-aware XSLT. A check validates a corpus of valid and invalid documents against both and fails where their verdicts differ, which also keeps the RELAX NG within what XSD 1.0 can express. Neither schema is edited by hand except the source.
6. **Validated where it is received.** The service validates every document against the schema before it maps it, whatever the add-in has checked (PRI-75, STD-279), and refuses a document that declares a DTD.
7. **Versioned by its namespace.** The namespace names the major version. A change that would invalidate a document valid before is a new major version, and the service reads every major version it supports.

**Rejected.** Akoma Ntoso as the base form, which would bind LATTICE's documents to a legislative structure and to its change control. InsurML as the base form, for the same reason and because it is a domain markup. Keeping the JSON snapshot, a third form that nothing outside LATTICE reads. RDF/XML as the document form, which carries meaning, not a document's order and text, and which an XSLT reads poorly without a canonical form. XSD as the source, which is longer to read and review. Schematron for rules XSD cannot state, which nothing yet needs.

## Consequences

- The add-in converts between OOXML and the markup, the one conversion only Word needs. The shared domain package holds the markup's reader and writer for both clients.
- The authoring JSON Schemas and the hand-written mapper are retired when the add-in sends markup (CS12d).
- An XSLT to Wording RDF has to reproduce what the Java mapper does today, which its tests pin.
- A third party can read a LATTICE document with XML tools and convert it to Akoma Ntoso or InsurML without reading LATTICE's code.
- The schema needs Trang and a RELAX NG validator at build time, both Java, run through mise.

## Open questions for the maintainer

| ID | Question | Recommendation |
|---|---|---|
| DM-Q1 | The namespace IRI: an HTTP IRI under the project's domain, as the RDF namespaces are, or a URN beside the add-in's `urn:nebularis:lattice:authoring:1` | an HTTP IRI, `https://www.nebularis.org/neuro-semantic/lattice/document/1`, so it resolves to its documentation |
| DM-Q2 | The media type on the wire: `application/xml`, or a registered-style `application/vnd.lattice.document+xml` | `application/xml`, read by the root element's namespace, until a client needs to tell documents apart by type alone |
| DM-Q3 | Where the custom XML part's metadata goes: into the markup's `meta`, or kept in Word alone | into `meta`, so a document carries its template and identifiers wherever it travels |

## Provenance

**Unit:** [`config-studio`](../../developer/plans/config-studio.md) (plan, CS12 and CS-Q5), drafted 2026-10-28 under the maintainer's delegation. The maintainer decided CS-Q4 (the document is XML and its meaning RDF, a vocabulary of our own drawn from Akoma Ntoso, Akoma Ntoso and InsurML as XSLT targets) and CS-Q5 (an ADR of its own, both schema languages), and delegated the choice of source schema, which decision 5 records. The maintainer has not accepted it.
