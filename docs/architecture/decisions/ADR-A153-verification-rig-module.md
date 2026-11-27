<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A153: A standalone module for the verification rig's intermediate representation

**Status:** Accepted 2026-11-16
**Date:** 2026-11-08 (proposed), 2026-11-16 (accepted)
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

## Addendum (2026-11-26): a scheme declares the keys of the format it reads, a fact may be written with qualifiers, and a rig declares its parties once

**Status of this addendum:** Accepted by the maintainer on 2026-11-27. It was drafted on 2026-11-26 from the maintainer's decisions of that day on the format's next version. Nothing in it is built, and the property it names is added to the module by the change that builds it, under the module's own version.

The first format carries eleven keys the tracked scheme maps. Its next version carries a key for every kind of fact a rig is asked to state, whether or not a layer has a term for it, and many have none. Three rules follow, and decision 2 holds through each. A key is still a string, a token is still an uninterpreted literal, and a new key adds no term.

**A scheme declares the keys of the format it reads.** A tracked scheme lists each key of the format version it maps, with a property of the module, as it lists its reading keys with `vrig:readingKey`, and with a statement in generic words of the fact the key carries. A run then tells three things apart, a key the scheme maps, a key of the format that no layer term states, and a key the format does not know. The second is expected wherever a layer has no term, and is reported once for the key, never once for each place a rig writes it. The third is the one a reader acts on. A key a rig adds of its own is declared by its extension the same way.

**A fact written with qualifiers is the fact its bare form states.** A format may let a fact be written as its value alone or as a mapping that holds the value under the key `value` beside what is said about it, for example its unit and the provision that states it. The tool carries both forms as one fact of that value, with the rest as a record on the fact, so one mapping row serves both, and a rig written in the first format is read unchanged. `value` is reserved in the format for this. Decision 3 holds as written, since a fact stated with a value may also hold an item.

**A rig declares its parties once.** A party is declared in one file the rig's manifest names, and every other mention is its id, so a party named in two programmes is one node of the representation. How the representation carries that node is not decided here.

**Consequences.** The module gains one property and moves its version when the first rule is built. A consumer that pinned the first release reads a run of the first format as before. Two runs of rigs in different format versions compare key by key wherever a key is in both, since no key of the first format changes its meaning.

## Addendum (2026-11-27): a rig states where a party's identity holds

**Status of this addendum:** Accepted by the maintainer on 2026-11-27, and drafted the same day from the maintainer's decision. Nothing in it is built.

The addendum of 2026-11-26 has a rig declare a party once, so that one party is one node. A rig's writer does not always know whether two mentions are one party. A rig that gives them one id, or two, then states more than its writer knows, and a question that counts parties answers with a confidence the rig does not have. Whether two parties are one is a fact, and decision 3 gives a fact three states.

**A party states where its identity holds, and which parties it may be.** A party may list the documents and programmes within which it has its id and no other, so that two ids listed for one of them are two parties there. It may list the parties it may be, where the writer cannot tell. A writer who knows two ids are one party gives them one id, so the format has no key that states sameness.

**Where no carrier lists two ids together, the rig does not say whether they are one party.** No mapping and no question takes them for two. A question that counts parties, or joins on one, says which of its rows rest on a doubtful pair or on a pair no carrier lists together.

**Consequences.** Both statements are lists of ids, so the tool carries them by resolving an id, as it does for any other. A party's name is never required, and a rig may state it as not known. A party may be given an identity within one document only, by listing that document alone. A count of parties is exact only within a carrier every counted party lists and where no counted party names another as doubtful.

## Addendum (2026-11-27): a party is a carrier of the representation

**Status of this addendum:** Accepted by the maintainer on 2026-11-27, and drafted the same day from the maintainer's decision. Nothing in it is built.

The addendum of 2026-11-26 has a rig declare a party once and leaves open how the representation carries it. The module has a carrier for a document, a programme and an event, each with the id the rig gives it, and none for a party.

**A party declared for the rig is a carrier.** The module gains a class for a party, a carrier with the id the rig gives it, as an event is, and disjoint from a document, a programme, an event and a record. Its locator names the parties file, as an event's names the events file, so decision 4 holds with one more file a node is read from. Decision 2 holds, since party is a word as generic as programme, and the class says nothing of what a party is or does. What a rig states of a party, its kind among the rest, is a fact of it.

**Consequences.** The module gains one class and moves its version when the class is built. A count of parties is a count of nodes, read with what the addendum of this day on a party's identity says of a doubtful pair. A second file of things a rig declares at its own level would need a class of its own.

