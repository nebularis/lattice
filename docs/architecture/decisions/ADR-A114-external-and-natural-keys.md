<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A114: External and natural keys

**Status:** Proposed
**Date:** 2026-10-02 (proposed), revised 2026-10-03
**Related:** ADR-A12 (identity and derivation), ADR-A51 (IRI and identity policy), ADR-A82, ADR-A83,
ADR-A84 (minting libraries), ADR-A86 (versioning), ADR-A01 (layer order), ADR-A104, ADR-A112
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md)
(decision CC-D9, slice F1)

## Context

**Premise.** The things a contract is about already have names the world gives them: a company has
a registration number and a legal entity identifier, a coverholder has a market PIN, an agreement
has its own number and a unique market reference, a standard form has a form number. People and
other systems find, cite and match things by these names. Some names pick out exactly one thing.
Others are carried by many things that relate to one: every endorsement, declaration, bordereau row
and claim on a Lloyd's contract carries the contract's unique market reference.

**Examples.**

1. *A facility agreement.* "Facility Agreement No. FA-2027-0412 dated 1 January 2027 between Acme
   Holdings plc (company number 01234567, LEI 5493001KJTIIGC8Y1R12) and the Lenders." An amendment
   letter cites the agreement by its number. The agent's systems hold the borrower by its LEI.
2. *A Lloyd's contract.* The broker allocates a unique market reference at firm order, which
   "uniquely identifies a contract and remains constant on subsequent related business
   transactions" (MRC data dictionary 2.0). Each declaration under a binding authority "should
   specify the unique market reference of the contract to which the declaration in question
   attaches". Each insurer also gives the contract its own reference, unique only within that
   insurer.

**Identity is not a key.** LATTICE already names everything it holds: every versioned thing has a
persistent identity, an IRI minted under ADR-A51 and never reused. That is LATTICE's name for the
thing, and RDF's notion of identity. A key is a name some authority outside LATTICE gives it:

| | Identity (ADR-A51) | Key (this ADR) |
|---|---|---|
| issued by | LATTICE, when the thing is first recorded | a registry, a market, a party |
| how many | exactly one per thing | any number, from different schemes |
| changes | never | a thing may gain keys, and a key may be withdrawn |
| readable | opaque by design (a surrogate, or a hash of a key) | the value people quote |
| may be personal data | never, by construction | sometimes (a national ID, a tax number) |

The word "identifier" is avoided for keys: it is too close to "identity" for a reader to keep the
two apart.

**The gap.** The graph cannot hold a key today. Minting may use one as an input, but minting is
one-way: a surrogate or a hash does not give the value back, and readers must never parse an IRI
(ADR-A51). So a thing cannot be listed, shown, cited or matched by the value people quote, and two
records of one coverholder under two spellings of its address (the CCS scenario S98) cannot be
joined on the PIN they share. Layers that met the gap built their own: Open CBAA's `agr:umr`, and
the exposure ontology's planned `aeo:Identifier` (AIR-4.1).

**Why Foundation.** Actors (Party), instruments (Instrument), standard forms (Wording), assets and
locations (applied exposure) all carry keys. Only Foundation is below all of them (ADR-A01, CC-D9).

## Decision

1. **A key is a node.** `fnd:Key` holds exactly one `fnd:keyValue` (a string, as issued) and exactly
   one `fnd:keyScheme`. Its IRI is minted from its scheme and value (decision 6), so one value of one
   scheme is one node wherever it is recorded, and it can carry evidence and governance of its own.
2. **A scheme is declared once.** `fnd:KeyScheme` is a class whose individuals are the schemes: the
   LEI, a company register, a market's PIN, the unique market reference, one insurer's own
   references. A scheme states `fnd:reissuesValues` (whether a value it withdrew may later name
   something else) and `fnd:personalDataScheme` (whether its values are personal data), and may
   state `fnd:valuePattern` (a regular expression its values match, checked by a shape) and
   `fnd:keyNormalisation` (decision 6). Foundation declares no scheme. Whoever uses one declares it.
3. **An external key locates.** `fnd:externalKey` links anything to a key it carries: the contract,
   its declarations, its bordereau rows and its claims each carry the unique market reference. It is
   neither functional nor inverse-functional. Many things may share one key, and one thing may carry
   many.
4. **A natural key identifies.** `fnd:naturalKey ⊑ fnd:externalKey` links a thing to a key that picks
   it out and nothing else: the contract, and only the contract, has the unique market reference as
   its natural key. An object property, not functional: a company may have an LEI and a company
   number, each identifying it. Its domain is `fnd:NaturallyKeyed`. Only a scheme that never reissues
   values supplies natural keys: reuse would make two things share one.
5. **Keys belong to what persists.** On a versioned thing, keys attach to its
   `fnd:PersistentIdentity`, since an agreement number names the agreement across all its versions.
   On an unversioned thing, an actor for example, they attach to the thing itself. The path
   `fnd:hasIdentity?/fnd:naturalKey` reaches a key from either.

   ```turtle
   ex:facility-v2 a ins:Instrument ;
       fnd:hasIdentity ex:facility-identity .            # ex:facility-v1 fnd:supersededBy ex:facility-v2

   ex:facility-identity a fnd:PersistentIdentity , fnd:NaturallyKeyed ;
       fnd:naturalKey key:umr-B0123ABC20261234 .

   key:umr-B0123ABC20261234 a fnd:Key ;
       fnd:keyScheme ex:umr ;
       fnd:keyValue "B0123ABC20261234" .

   ex:acme a pty:Actor , fnd:NaturallyKeyed ;
       fnd:naturalKey key:lei-5493001KJTIIGC8Y1R12 .

   ex:declaration-17 fnd:externalKey key:umr-B0123ABC20261234 .
   ```

   ```sparql
   # The current version of the contract with this reference
   SELECT ?version WHERE {
     ?key fnd:keyScheme ex:umr ; fnd:keyValue "B0123ABC20261234" .
     ?version fnd:hasIdentity/fnd:naturalKey ?key .
     FILTER NOT EXISTS { ?version fnd:supersededBy ?later }
   }
   ```

6. **Key IRIs are minted per scheme**, under ADR-A51's strategies, so that two systems recording one
   key reach one node:

   | Scheme | Strategy | Two sources reach one node |
   |---|---|---|
   | not personal data (UMR, LEI, a company number) | natural key or derived hash of scheme and value | by computation, within one tenant. Across tenants only where the recipe declares no scope |
   | personal data (`fnd:personalDataScheme true`) | a surrogate with a keyed claim (HMAC under a tenant secret) | by looking up the claim, within one tenant only |

   ADR-A51 forbids putting personal data in an IRI and forbids an unkeyed hash of a low-entropy
   personal value, which can be reversed by trying every value. A keyed claim can be computed only
   by the tenant that holds the secret, so records of one person never correlate across tenants.
   The constraint is the scheme's, never the natural key's. Persistence's `dal:PrivacyProfile` decides
   what a deployment does with personal-data keys. The flag states the fact for adopters without
   Persistence.

   **Normalisation and valid IRIs.** A key's value is held as issued in `fnd:keyValue`. Matching
   uses a normalised form: a scheme names one of the minting specification's pipelines with
   `fnd:keyNormalisation` (`NfkcTrimCasefold`, `NfkcTrimUppercase`, `NfkcTrimLowercase`, §3.2), and
   the minting recipe and the uniqueness constraint for its keys must both use it. Validity of the
   minted IRI is the recipe's encoding step, never the scheme's: the natural-key strategy
   percent-encodes every byte outside RFC 3986's unreserved characters, and the hash strategies
   emit hex or base32 (§5, §6.2). A normalisation outside the three pipelines (removing inner
   spaces, a check digit) is a change to the minting specification, out of this ADR's scope.
7. **Uniqueness has two homes, by intent** (decision 8, option (c) of the review, 2026-10-03):
   - **`fnd:NaturallyKeyed`** is the common mixin: the domain of `fnd:naturalKey`, the target of
     Foundation's SHACL shapes. Two different things never share a natural key, a key has one scheme
     and one value, a natural key's scheme never reissues values, and a value matches its scheme's
     pattern.
   - **`fnd:MergedOnNaturalKey ⊑ fnd:NaturallyKeyed`** adds `owl:hasKey ( fnd:naturalKey )`. To an OWL
     reasoner, two named members sharing a natural key are the same individual.
   - **`dal:PersistenceKeyed ⊑ fnd:NaturallyKeyed`**, in a new optional document of Persistence,
     `persistent-foundation`, adds no key axiom. Uniqueness is enforced at write time by a
     `dal:UniquenessConstraint` on `fnd:naturalKey`, through Persistence's guarded key-claim write,
     and a violation is rejected, quarantined or recorded by an explicit, reviewable
     `dal:mergeRelation`, never `owl:sameAs`.
8. **Why two mixins.** Persistence is optional. An adopter who uses LATTICE's ontologies alone, with
   a reasoner and without the compiler or runtime services, still needs a natural key to mean
   something: `fnd:MergedOnNaturalKey` gives it OWL's meaning. An adopter who uses Persistence must
   not have a reasoner silently merge what Persistence keeps apart for review: `dal:PersistenceKeyed`
   leaves the merge to Persistence. **LATTICE recommends Persistence** for any deployment that writes
   keyed data: `owl:hasKey` merges on any collision, including a mistaken one, and nothing in OWL can
   undo a merge or say why it happened.

   ```mermaid
   flowchart TB
       NK["fnd:NaturallyKeyed<br/>domain of fnd:naturalKey<br/>SHACL: uniqueness, scheme, pattern"]
       MK["fnd:MergedOnNaturalKey<br/>owl:hasKey ( fnd:naturalKey )<br/>for ontology-only adopters"]
       PK["dal:PersistenceKeyed<br/>persistent-foundation (optional)<br/>enforced by dal:UniquenessConstraint"]
       MK -- "⊑" --> NK
       PK -- "⊑" --> NK
   ```

9. **How `owl:hasKey` behaves**, for the record. `C owl:hasKey (P)` makes two named individuals of
   `C` the same when they share at least one value of `P`. It applies only to named individuals and
   to asserted values, it infers `owl:sameAs` rather than rejecting the data, and it is reported as
   an error only when the merge contradicts something else (an `owl:differentFrom`, a disjointness).
   A key on `( fnd:hasVersion fnd:naturalKey )` would be vacuous: two different identities never
   share a version (`fnd:hasIdentity` is functional), so it would never fire on two contracts
   claiming one reference.
10. **Layers adopt keys.** Instrument records an instrument's numbers on its identity (CCS slice C6).
    Party's actors carry registry and market keys. The exposure ontology uses `fnd:Key` directly in
    place of `aeo:Identifier` (AIR-4.1). Open CBAA's `agr:umr` becomes a key scheme. Surface may index
    `fnd:externalKey` for retrieval by key, and promote an identity's natural key onto its versions
    for one-step lookup, with its existing contracts.

**Rejected.**

- *A literal property, as `dcterms:identifier`.* It cannot say which scheme issued a value, one
  value valid in two schemes is ambiguous, and it carries nothing of its own.
- *A datatype `naturalKey`.* A key node, minted once per scheme and value, is the same node in every
  record, and can carry evidence, governance and its scheme.
- *W3C ADMS.* Its identifier pattern is close, but it brings a notation and agency model this does
  not need.
- *Keys in Party.* Instruments, forms and assets are not parties.
- *One construct per layer.* Scheme handling and uniqueness would be repeated, and a thing keyed in
  two layers would carry two.
- *The key as the identity.* Keys are withdrawn and may be personal data. Identity must not be
  (ADR-A51).
- *A single mixin with `owl:hasKey`.* It forces OWL's silent merge on Persistence's adopters.
- *No `owl:hasKey` at all.* It leaves an ontology-only adopter's natural keys with no formal meaning.

**Answered at review, 2026-10-03.** Sensitivity is a Foundation flag, `fnd:personalDataScheme`
(A114-Q1). Normalisation is named by the scheme from the minting specification's closed set, and
IRI validity stays with the recipe's encoding (A114-Q2, decision 6).

## Consequences

- Foundation takes an additive MINOR (`0.3.0` to `0.4.0`). Twenty-four documents import it directly
  (15) or through another (9), and each takes a MINOR with its own release row and tag (ADR-A86), in
  one cascade. The [impact analysis](../../developer/sketches/keys-impact.md) §4 lists them.
- The cascade must not run while another branch edits a Foundation importer. On 2026-10-03 none
  does: `air/2.2-characteristics`, `air/3.3-readings-swrl-owl` and `air/4.1-exposure-core` exist
  without commits. F1 runs now, and those branches start from the `main` it merges into. CCS risk R6
  is retired for F1.
- Persistence gains its first document that imports Foundation, `persistent-foundation`, optional and
  separate from the `dal:` configuration ontology, which still imports no layer. It ships the mixin,
  a default `dal:UniquenessConstraint` on `fnd:naturalKey` an adopter may adopt or replace, and an
  identity profile per strategy of decision 6 as examples.
- F1 writes an impact analysis for Persistence and Surface before this ADR is accepted (CCS plan,
  F1): uniqueness constraints and merge policy, identity profiles and recipes for key nodes,
  normalisation, privacy, and Surface's index and promotion contracts over keys.
- NRS N9 (ADR-A108), planned to share this cascade, keeps its own later window.
- CCS C6 starts after F1 and records keys from its first examples. AIR-4.1's brief drops
  `aeo:Identifier`. Open CBAA migrates `agr:umr` (CCS plan §7).
