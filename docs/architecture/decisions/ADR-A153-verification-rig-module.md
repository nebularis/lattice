<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A153: A standalone module for the verification rig's intermediate representation

**Status:** Proposed
**Date:** 2026-11-08 (proposed)
**Described in:** [the verification rig module](../../../ontology/v-rig/README.md)
**Related:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (`ontology/` as the one root for semantic assets), [ADR-A129](ADR-A129-one-release-for-the-substrate.md) (a standalone module is released on its own), [ADR-A121](ADR-A121-repository-catalogue.md) (the catalogue entry and the import guard), [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (the literate layout), [ADR-A147](ADR-A147-skolem-rule-for-mapped-sources.md) (a versioned deterministic naming rule), [ADR-A143](ADR-A143-one-canonicalisation.md) (SHA-256 in lowercase hex), [ADR-A112](ADR-A112-wording-layer.md) (the layer the body nodes project onto), [ADR-A-C2](ADR-A-C2-clean-room-authoring-procedure.md) (examples from generic premises)
**Unit:** [`v-rig`](../../developer/plans/v-rig.md)

## Context

A verification rig is a directory of invented documents in a stated format, held outside the repository and named at run time, that two evaluations read. The first asks whether the layers' encodings can state what the documents say, whether what they state is consistent, and where no term exists to say a thing. The second asks whether the evaluation of one contract from stated facts behaves lawfully on realistic structures and whether independent implementations agree. A tool reads a rig into one intermediate representation of each case and generates every projection from it, the graph over the layers, a theory, test vectors and findings.

That representation needs a vocabulary and shapes of its own, for three reasons. A consumer outside the repository reads the findings, writes a representation of its own as a read case for comparison, and diffs two runs by finding id, so it must be able to pin the vocabulary at a tag. The representation must carry what the format states without interpreting it, which no layer does, since a layer gives meaning and the format's keys and tokens are open and meaningless until a mapping reads them. And the shapes that say what a well-formed representation is run by the same checks every module's do only if the module sits under `ontology/`, which ADR-A77 makes the sole root for semantic assets.

The representation sits between a format and the layers, so it is neither a substrate layer in ADR-A01's order nor an applied module over one. The catalogue already has a kind for that, the standalone module, released on its own under ADR-A129's addendum.

## Decision

1. **A standalone module, `ontology/v-rig/`.** Literate (ADR-A126), namespace `https://www.nebularis.org/neuro-semantic/lattice/v-rig#`, prefix `vrig:`, catalogue kind `standalone`, released on its own by `v-rig-vX.Y.Z` tags, with its shapes versioned by their own `.version`.
2. **It imports nothing and models no domain.** A key of the rig's format is a fact with its key as a string, a token is an uninterpreted literal, a reading of a legal concept is a fact whose value is a token, and the body of a document is lifted to nodes with a kind token of the format's layout conventions. Meaning is given by a mapping that reads the representation and writes the layers, never by a term here. A new key, token or reading in a rig adds no term to the module. The module's examples are written from generic premises (ADR-A-C2) and hold no text of any rig.
3. **Three states for a fact.** A fact is stated with a value, stated as not known, or stated with nothing, by one or more values or items, the unknown marker or the empty marker, and exactly one of these holds. A fact that is not stated is absent. The constraint of the module's section 7 refuses any other combination, so no projection can collapse not known or absent into false or zero.
4. **Every node is located and digested.** Each node carries exactly one locator, naming the document, programme or events file by id, the view it was read in and its position, and a digest the tool computes over the normalised text it was read from. The views are the declared view, the blind view and one view per rendering, and the view is a field of the locator.
5. **Identifiers follow versioned deterministic rules.** Node, locator, view and finding IRIs are derived by the rules of the module's section 9, versioned `v1` in the manner of ADR-A147, with SHA-256 in lowercase hex (ADR-A143) and the identity minting specification's length-prefixed tuple encoding. Two runs of one rig revision give the same identifiers, and a finding that is resolved disappears from a diff by id.
6. **Findings are nodes of the representation.** A finding has a kind from a closed set, the locator of what it concerns, the key where one applies, and a message in generic words that names no text of a rig. The report a run writes is rendered from the findings graph and never written by hand.

## Consequences

The catalogue gains a standalone module with no imports, which the import guard holds to that. The release register gains three documents released by their own tags. The tool that reads a rig, its mapping scheme and its projections depend on this module and on nothing in the module depends on them, so a consumer can read a representation with the vocabulary and the shapes alone. The format's keys, structures and view names appear in the module only as the generic words the vocabulary needs, document, programme, event, layer, placement, and the rest are strings in a representation. A change to the rig format that adds a structure the vocabulary cannot carry as a fact is a change to this module, under its own version.

## Alternatives considered

- **The tool's own schema under `tools/`.** Versioned with the package and tagged with the repository. Rejected because a vocabulary and shapes a consumer pins are a published semantic asset, and ADR-A77 gives those one root. The module's shapes then run by the checks every module's do, at the cost of one ADR and one catalogue entry.
- **The Wording layer as the representation.** Body nodes are close to Wording's elements. Rejected because the representation must carry the format's keys, views, three fact states, readings and findings, none of which is Wording's to state, and because a representation written by a consumer outside the repository would then have to satisfy a substrate layer's shapes to be compared at all. Wording is where the body nodes are projected to, by a mapping.
- **Facts as properties.** One property per key of the format. Rejected because the set of keys is open and every new key would then be a term and a version, where a fact with a key string is no change at all.
