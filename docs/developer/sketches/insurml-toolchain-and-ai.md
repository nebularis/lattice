<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# From drafting to reading: the InsurML and LATTICE toolchain

**Unit:** [insurml-alignment](../plans/insurml-alignment.md) (epic). **Status:** sketch, 2026-10-05.
Nothing here is ratified. New directories and apps each need an ADR.
**Reads with:** [the vision](../../architecture/insurml-alignment-vision.md) (AV1 to AV10),
[the bridge sketch](insurml-bridge.md) (the profile, lift, lower, parity and substrate changes this
sketch builds on), the [ingestion vision](../../architecture/ingestion-vision.md) (IV1 to IV13,
stages S0 to S9),
the [XML egress](xml-egress-and-transformation-kits.md) and [wire protocol](normative-wire-protocol.md)
sketches, and Open DARE's proof-of-concept notes (`open-dare/docs/discovery/poc-ideas.md`, §4 and §5).

Examples are clean-room and use `.example` hosts (AV8).

---

## Contents

1. [Premise](#1-premise)
2. [Authoring](#2-authoring)
3. [The compiler](#3-the-compiler)
4. [Libraries](#4-libraries)
5. [Placement](#5-placement)
6. [Execution](#6-execution)
7. [Exchange](#7-exchange)
8. [Mixing standards](#8-mixing-standards)
9. [Reading documents](#9-reading-documents)
10. [Platform placement](#10-platform-placement)
11. [Open questions](#11-open-questions)

---

## 1. Premise

The bridge makes InsurML and LATTICE data one graph. This sketch follows that graph through its
life: drafted in Word or a web studio, compiled, kept in libraries, assembled into products,
placed for a risk, run, exchanged, and read back from documents with AI. At each step it says what
exists, what each standard contributes, and what is new.

## 2. Authoring

### 2.1 Word

Market drafters work in Word. An Office.js task pane add-in, chosen in Open DARE's notes because it
runs on Windows, Mac and the web without an installer, keeps InsurML identity in the document:

| Word construct | Carries | InsurML |
|---|---|---|
| a content control per component, with a custom XML part | component IRI, type, optionality, alternative set, dependency | `component` with `iri`, metadata, markup attributes |
| a content control per fragment | `xml:id`, paragraph type, printed label | `para` with `xml:id`, `type`, `label` |
| a content control bound to a variable IRI | an embedded variable, or its printed name | `variable` |
| a content control around words with a condition | optional words, or one of a set of alternatives | `optionalPhrase` |
| a tagged table | static or dynamic table | CALS `table`, `dataTable` |

```mermaid
sequenceDiagram
    participant D as Drafter in Word
    participant A as Add-in
    participant K as Lower and lift kits
    participant S as Library service
    D->>A: open component
    A->>S: fetch InsurML component
    S->>K: InsurML to DOCX with content controls
    K-->>A: document
    D->>A: edit and save
    A->>K: DOCX to InsurML (XSLT 3.0 over OOXML)
    K->>K: RELAX NG, Schematron
    K-->>A: errors by paragraph, or a valid component
    A->>S: write intent: new component version
    S-->>A: accepted, with the new version IRI
```

Numbering is never read from Word's list numbering. Identity travels in the tags, and numbers are
generated after assembly (DP10, W7). A tracked change in a placed contract maps naturally to a
strike-and-substitute amendment, so the add-in can offer an endorsement as a proposed
`wrd:Amendment` with its struck and substituted words, reviewed before it applies.

### 2.2 The web studio

Library curators, product owners and reviewers work in a web studio over the same components:

| View | Does |
|---|---|
| Component editor | edits a component's XML through a structured editor, validating as it goes |
| Product editor | edits a contract form's inclusion entries or transclusions, conditions as Eligibility profiles, alternatives, governing variables and their schemes |
| Meaning review | shows a meaning proposal beside its source fragment, with the review workbench's six decisions (Confirm, Retarget, Reshape, Decline, Teach, Defer) |
| Release | publishes a library edition, records governance states, shows impact (§4) |

### 2.3 One write path

Both front ends send the same write intents (Open DARE notes §5.2), so validation, persistence and
events have one code path whatever the client. Validation in the client uses the same schemas the
compilers use. Schematron compiles to XSLT, which can run in the browser and in the add-in, so a
drafter sees the same assertion ids as the server.

## 3. The compiler

One intermediate graph, many passes, many outputs, as ADR-A19's staged compiler already does for
conditions.

```mermaid
flowchart LR
    subgraph FE["Front ends"]
        F1["InsurML XML<br/>and manifests"]
        F2["DOCX from the add-in"]
        F3["LATTICE-native<br/>wordings"]
    end
    IR[("Co-typed graph<br/>Wording, profile,<br/>Instrument")]
    subgraph PS["Passes"]
        P1["Validate"]
        P2["Verify"]
        P3["Optimise"]
    end
    subgraph BE["Back ends"]
        B1["Assembled InsurML,<br/>DOCX, PDF"]
        B2["SPARQL, SHACL,<br/>OWL classes"]
        B3["JSON skins,<br/>LegalRuleML"]
        B4["Surface read paths"]
    end
    F1 --> IR
    F2 --> F1
    F3 --> IR
    IR --> P1 --> P2 --> P3
    P3 --> B1
    P3 --> B2
    P3 --> B3
    P3 --> B4
```

| Pass | Checks or produces | State |
|---|---|---|
| **Validate** | InsurML's grammar, Schematron and SHACL. Wording laws. Profile shapes (bridge §14) | built on both sides, profile shapes new |
| **Verify** alternatives | every set of alternatives exclusive and exhaustive over the governing variables' admissible values, for every product | intervals built (CCS C5), every kind CCS C13a |
| **Verify** dependencies | the clause dependency graph is acyclic, and every `dependsOn` target can be included | new, profile |
| **Verify** references | every reference resolves to exactly one target in every reachable configuration | new, generalising InsurML's per-policy check to all policies |
| **Verify** meaning | no obligation and prohibition over overlapping scopes, and a revision's widening or narrowing of criteria | NRS N3, ADR-A90 |
| **Optimise** questions | an order for the governing questions in which each answer removes the most undecided inclusions, as a question plan per product | new |
| **Optimise** configurations | dead components (never included), conditions that always hold (made mandatory), alternatives never chosen | new, on C13a's satisfiability |
| **Optimise** specialisation | a product partially evaluated over answers fixed for a market or a programme, giving a smaller form | new |
| **Optimise** conditions | inclusion conditions compiled to SPARQL and SHACL | built (`tools/mork_compilers`) |
| **Optimise** read paths | inherited attributes per placed contract, a usage index from component to live placements | Surface promotions, new contracts |
| **Optimise** rendering | a cache keyed by the component digest and the settings it reads | new |

Every pass is a pure function of hashed inputs. Each output is a derived artefact with its read set
(ADR-A92), regenerated in the smallest scope when an input changes (ADR-A27).

## 4. Libraries

| Library | Holds | Published by |
|---|---|---|
| Wording | InsurML component versions with their reviewed meaning templates | a market body, an insurer, a broker, each under its own prefix |
| Product | InsurML contract forms with governing variables and conditions | an insurer or a programme owner |
| Template | Instrument meaning templates, and regime templates for notice, suspension, non-renewal and run-off (CCS C8a) | LATTICE for neutral templates, the insurance profile for market ones |

A library is published in editions, as a vocabulary is. Each component version carries a
governance state (`fnd:GovernanceState`), and a withdrawn version is never reused. Questions the
graph answers:

| Question | Read path |
|---|---|
| Which live placed contracts include this component version? | usage index, `wrd:includes` |
| What would change if version 2 replaced version 1 in this product? | text difference, plus the meaning template's difference: same relation with changed parameters, a different relation, or criteria widened or narrowed (ADR-A90) |
| Which components are near duplicates? | fingerprints from ingestion stage S1, proposed to a curator as variants or merges |
| Which components have no reviewed meaning? | `ins:encodingStatus` |

## 5. Placement

A placement tailors a product for a risk, a client or a scenario. Each step writes data, never a
copy of the document.

```mermaid
sequenceDiagram
    participant B as Broker
    participant U as Underwriter
    participant G as Graph
    B->>G: submission, governing answers
    G-->>B: question plan, then the assembled draft
    U->>G: quote: values, chosen alternatives, bespoke clauses
    G->>G: verify, report deviation from the library
    B->>G: firm order
    U->>G: bind
    G->>G: assembled wording and instrument versioned, meaning bound
    G-->>B: InsurML contract, contract package
    U->>G: endorsement as amendments
    G->>G: new assembled wording, amendment records, regimes re-evaluated
```

| What placement records | LATTICE | InsurML |
|---|---|---|
| answers to governing questions | `wrd:VariableValue` on the `wrd:AssembledWording` | the instance contract's settings |
| chosen alternatives and optional clauses | `wrd:includes` | the instance contract's manifest, and its assembled contract |
| values for embedded variables and schedule tables | `wrd:VariableValue`, per table entry for a table field | `variable` values |
| a bespoke clause revising a library clause | a bespoke element, `prov:wasRevisionOf` the library element, which may be proposed back to the library | a component in the placement's own publisher space |
| a manuscript clause with no library origin | a bespoke element with no derivation | the same |
| an endorsement | `wrd:Amendment`s, and `ins:Amendment` for its legal effect (CCS C9) | a new version of the instance contract |

**Deviation from standard wording** is a derived report for every placed contract:

| Category | Test |
|---|---|
| standard | library element version included unchanged |
| standard with values | as above, with values for its variables |
| standard alternative | one alternative of a library set chosen |
| modified | a bespoke element that revises a library element, with the text difference |
| manuscript | a bespoke element with no library origin |
| removed | a mandatory library element deleted by amendment |

Each category is paired with the meaning delta of §4: same meaning, changed parameters, changed
relation, or meaning not yet reviewed. A renewal carries the settings forward, lists library
components with newer versions, and shows the impact of moving to them before anyone agrees.

## 6. Execution

Reviewed meaning is bound per instrument and run by LATTICE alone. InsurML's component types route
review to the likely reading (integration §8.5), and the bridge's §13 gives limits and excesses
their parameters.

| Runs | Where | Slice |
|---|---|---|
| due ranges, windows, survival | Instrument | CCS C7b |
| definitions per section | Instrument | CCS C7c |
| schedule values into relations | parameter bindings | CCS C8 |
| notice, suspension, non-renewal, run-off | regime templates | CCS C8a, AIR Phase 5 |
| endorsements in law | amendments | CCS C9 |
| regimes and occasions over events | runtime evaluator | CCS C12 |
| obligations, permissions, exclusions, powers | relation plans | CCS C13 |
| limits, retentions, aggregates | term parameters and ledgers | AIR-5.1 to AIR-5.3, evaluation context |
| authority at bind | Eligibility, capacity | AIR Phase 3, Open CBAA |

A decision carries its explanation: the relation, the evidence, and the fragment IRI of the words
that state it.

## 7. Exchange

### 7.1 Kits

Every exchange form is a published kit (AV9): a query, a stylesheet or generator, a schema and
examples, versioned in `contracts/` as the XML egress sketch proposes.

| Kit | Direction | Query or source | Output and schema |
|---|---|---|---|
| `insurml-components` | out | a form's elements | component files and a manifest, InsurML's RELAX NG and SHACL |
| `insurml-assembled-contract` | out | a placed contract | an assembled contract, InsurML's RELAX NG |
| `insurml-lift` | in | component files and manifests | the co-typed graph, Wording laws and profile shapes |
| `docx` | both | a component, or a placed contract | DOCX with content controls |
| `settings-json` | both | `wrd:VariableValue` records | JSON generated from the shapes (ingestion vision §7) |
| `market-profile` | both | terms, relations, decisions | the wire protocol's plain JSON |
| `lattice-instrument` | out | terms, relations, parties, conditions | LATTICE instrument XML (XML egress sketch) |
| `legalruleml` | both | relations | LegalRuleML XML or its JSON form (§8) |

An API serves a placed contract in any of these forms by content negotiation (wire protocol §11),
so any system that wants InsurML can have it, whatever authored the contract.

### 7.2 The contract package

```mermaid
flowchart TB
    PKG["Contract package<br/>manifest with media types,<br/>digests, provenance"]
    PKG --> A["assembled contract<br/>InsurML XML"]
    PKG --> B["settings<br/>JSON or Turtle"]
    PKG --> C["instrument graph<br/>Turtle or JSON-LD"]
    PKG --> D["companion LegalRuleML<br/>optional"]
    PKG --> E["rendered document<br/>PDF"]
    PKG --> F["component files<br/>by digest, optional"]
```

A recipient takes the parts it understands and verifies the rest by digest. A package is a derived
artefact of one placed contract version. The release assembly and OCI export of ADR-A39 and
ADR-A40 are a candidate container format (IT-Q5).

### 7.3 Ingesting exchanged data

Anything that arrives in a kit's form runs through that kit's lift, the same validation, and the
same execution as data authored in LATTICE. Identity is preserved. InsurML IRIs are adopted, and
keys (a policy number, a unique market reference) resolve to existing identities rather than
minting new ones (ADR-A114). Running a lift twice on the same input yields the same graph.

## 8. Mixing standards

### 8.1 LegalRuleML

Three ways to put LegalRuleML beside InsurML:

| Option | How | For | Against |
|---|---|---|---|
| Companion document | a LegalRuleML document whose legal sources are InsurML fragment IRIs, tied to statements by LegalRuleML's associations | no change to InsurML. The published words are untouched. LegalRuleML's own mechanism for source links is used as designed | two documents to keep together |
| In the contract package | the companion document inside the package | one delivery, verified by digest | needs a package reader |
| Inside InsurML | LegalRuleML within `foreign`, marked informational | one document | needs InsurML's owner to accept it (P-14). A statement marked contractual would put meaning into the published words, which AV4 forbids |

The companion document is the default. Its legal sources are the fragments the meaning was reviewed
against:

```xml
<lrml:LegalRuleML xmlns:lrml="http://docs.oasis-open.org/legalruleml/ns/v1.0/">
  <lrml:LegalSources>
    <lrml:LegalSource key="src-flood"
        sameAs="https://insurer.example/id/component/flood-exclusion/2026-01-01#p1"/>
  </lrml:LegalSources>
  <lrml:Associations>
    <lrml:Association>
      <lrml:appliesSource keyref="#src-flood"/>
      <lrml:toTarget keyref="#stmt-flood"/>
    </lrml:Association>
  </lrml:Associations>
  <!-- statements, including #stmt-flood, generated from the bound relations -->
</lrml:LegalRuleML>
```

The statements are generated from bound relations by the LegalRuleML mapping, and lifted back by
the runtime pipeline, whose refiner refuses what LATTICE cannot hold. The JSON form of the wire
protocol carries the same structure for consumers without XML.

### 8.2 Other standards

| Standard | Attaches as | Notes |
|---|---|---|
| InsurLE and Logical English | a controlled-English rendering per component version | three views of one clause: the InsurML words, the controlled rendering and the reviewed meaning. Agreement raises confidence and disagreement goes to review (ingestion vision §3, logical English alignment sketch) |
| ODRL | a projection of duties, prohibitions and permissions | CCS sketch §8.2 |
| ACORD | an egress kit from the placed contract's values and terms | XML egress sketch §13, for policy administration systems |
| MathML | a formula inside a component, read as `ins:computedBy` | the formula's meaning waits for contract amounts (CCS C7b) |

## 9. Reading documents

The ingestion vision reads a document into LATTICE through a structure stage, recognition, fact
extraction and meaning proposals. InsurML gives the structure stage a published target with a
grammar, a vocabulary and validators, and gives recognition exact identifiers and digests.

| Document | Structure target | Facts | Meaning |
|---|---|---|---|
| policy wording | InsurML components and a form | none | reused from the library, proposed for novel text |
| schedule | a schedule component and its tables | settings and table values | none, already bound to the wording |
| quote, market reform contract slip | components for its conditions, settings for its particulars | values, parties, shares | reused or proposed |
| binding authority agreement | modules and components | particulars, authority tables | authority grants and obligations, reused or proposed |
| endorsement | amendments against the placed contract | effective date, values | the amendment's legal effect (CCS C9) |
| certificate | an assembled contract of a known form | values | none |
| bordereau | not a wording. A MORK structure mapping per layout | rows | none |

## 10. Platform placement

Integration §8.18 places each concern. In short, component files and rendered documents live in
the artefact realm, addressed by digest, while manifests, the lifted graph, meaning and values live
in the semantic graph realm through the store SPI. Run records live in the operational realm.
Lifts, assembly, rendering and compilation run as worker jobs with idempotent
delivery (ADR-A36), and the egress kits run in the planned semantic XML egress module.

## 11. Open questions

| # | Question | Leaning |
|---|---|---|
| IT-Q1 | Which authoring front end first? | the Word add-in for drafters, since market wording lives in Word. The web studio follows for curation and review |
| IT-Q2 | Where do the add-in and the studio live? | `apps/`, each under an ADR. The studio may grow from the review workbench's design |
| IT-Q5 | What container does a contract package use? | the release assembly's manifest and digests (ADR-A39), with OCI export where a recipient wants it (ADR-A40) |
| IT-Q6 | Does a question plan belong in the profile, or in the builder? | in the compiler's output, as a derived artefact a builder reads |
| IT-Q7 | Can tracked changes in Word round-trip as amendments? | yes for strike and substitute within one fragment, which is the common endorsement. Others become a new component version |
