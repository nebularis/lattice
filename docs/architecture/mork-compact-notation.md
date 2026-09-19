<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MCN: MORK Compact Notation

**Status:** Draft specification, version 0.1
**Scope:** A token-minimal, machine-oriented text encoding of MORK graphs ([../../mork/spec/Mork.ttl](../../mork/spec/Mork.ttl)) with a deterministic decoding algorithm to OWL 2.
**Related:** [ADR-A18](../adr/ADR-A18-surface-to-mork-lowering-boundary.md) (lowering boundary), [ADR-A19](../adr/ADR-A19-staged-compiler-architecture-and-backend-fanout.md) (staged compiler), [ADR-A22](../adr/ADR-A22-mork-governance-and-versioning-foundation-alignment.md) (governance and versioning), [ADR-A25](../adr/ADR-A25-llm-participation-and-deterministic-production-gate.md) (LLM participation), [ADR-A26](../adr/ADR-A26-provenance-chain-completeness-across-surface-mork-artefacts.md) (provenance chain).

---

## 1. Purpose

MORK records mapping intent as first-class graph objects so that mappings can be reviewed, versioned, governed, compiled deterministically and audited back to evidence. The graph is the product. Its *serialisation* is not, and every standard serialisation of OWL — Turtle, RDF/XML, OWL/XML, functional syntax, Manchester syntax, JSON-LD — is expensive when a language model must generate it: long prefixed names are repeated on every triple, every individual is re-typed as `owl:NamedIndividual`, every mapping restates its scheme membership, and reified `owl:Axiom` annotations cost fifty tokens to say "this match is lexical".

MCN is a notation in which an LLM (or any mapping agent) emits MORK content with the minimum number of tokens that still permits *lossless, deterministic* decoding to an OWL 2 ontology document. It is not designed to be read by people, though it is legible enough to debug. Its design rules are:

1. **Say each fact once.** Scheme membership, individual typing and inverse edges are supplied by context or by the decoder, never repeated per node.
2. **Every MORK term has a one-to-three character code.** The codebook in §8 is the whole vocabulary of `Mork.ttl` plus the SKOS, SHACL-targeting and Foundation terms MORK data actually uses.
3. **Structure is positional, not named, wherever the ontology fixes the structure.** Targeting specs, parameter bindings, provenance records and template bindings have positional inline forms.
4. **Nothing needs quoting unless it contains whitespace or a delimiter.** Literal datatypes come from the codebook, never from `^^xsd:…` suffixes.
5. **Annotations bind to the triple they annotate.** The `{…}` form replaces the `owl:Axiom` reification pattern and makes dangling annotations syntactically impossible (§16 records a real instance of that bug in the repository's own examples).
6. **Anything not covered by a code is still expressible.** CURIEs are accepted wherever a code is, and `!` lines carry arbitrary OWL axioms and raw triples, so completeness never depends on the codebook.
7. **Decoding is a pure function of the text.** Minted IRIs, blank-node labels and triple order are all determined by the document, so decoded output can be hashed, diffed and cached (this matters for `mork:inputHash` and the invalidation policy in ADR-A27).

MCN is the *proposal wire format* in the sense of ADR-A25: an LLM emits MCN, a deterministic decoder produces the RDF graph, and everything downstream (OWL DL checking, SHACL validation with [mork/shapes/constraints.ttl](../../mork/shapes/constraints.ttl), compilation) operates on the graph exactly as it does today. No compiler, shape or reasoner needs to know MCN exists.

### 1.1 Measured effect

Two example files from the repository were hand-encoded in MCN and decoded with a prototype decoder; the decoded graphs were compared to the originals with an isomorphism-aware diff (rdflib `graph_diff`). Token counts use the `o200k_base` BPE vocabulary as a proxy for current frontier tokenizers.

| Document | Triples | MCN | Turtle (as written, comments stripped) | JSON-LD (compacted) | RDF/XML | N-Triples |
|---|---|---|---|---|---|---|
| [mork/examples/Mork2RML/loan_mapping.ttl](../../mork/examples/Mork2RML/loan_mapping.ttl) | 40 | **219** | 614 (2.8×) | 1418 (6.5×) | 1383 (6.3×) | 1881 (8.6×) |
| [mork/examples/Zoo/UncertainMappings.ttl](../../mork/examples/Zoo/UncertainMappings.ttl) | 160 | **1366** | 2674 (2.0×) | 5308 (3.9×) | 5929 (4.3×) | 10235 (7.5×) |

The Zoo document is dominated by prose (`mappingNote`, `mappingRecommendation`, a 200-token `skos:example`), which no notation can shrink. Separating that irreducible literal content from structural overhead:

| Document | Literal prose | MCN structural | Turtle structural | Structural ratio | Structural tokens per triple (MCN / Turtle) |
|---|---|---|---|---|---|
| loan_mapping | 11 | 208 | 603 | 2.9× | 5.2 / 15.1 |
| UncertainMappings | 710 | 656 | 1964 | 3.0× | 4.1 / 12.3 |

Per construct, the savings are larger where Turtle is most verbose:

| Construct | MCN | Turtle | Ratio |
|---|---|---|---|
| A `Datum` node with scheme, `mappingFor`, `deferredMapping`, `conceptName`, `dataRef` | 18 | 73 | 4.1× |
| One annotated match (`exactTBoxMatch` + `mappingNote` on the axiom) | 9 | 54 | 6.0× |
| Prefix/base header of the loan example | 50 | 118 | 2.4× |

The loan example's 219 tokens include 50 tokens of prefix IRIs; §6.1 describes a profile mechanism that removes those from documents exchanged inside a known deployment.

Both round-trips were exact: 40/40 triples for the loan example; 140 of 143 triples for the Zoo example (counting after removing the `owl:NamedIndividual` typing both sides assert), where the three differences are a defect in the original Turtle — three `owl:annotatedTarget` values are in the wrong namespace and so annotate nothing — not in the encoding.

### 1.2 Non-goals

- MCN does not replace Turtle as the *storage* or *interchange* format for governed artefacts. Decoded RDF is what is stored, hashed, validated and compiled.
- MCN does not encode arbitrary RDF efficiently. It encodes MORK efficiently and everything else adequately.
- MCN does not attempt to make LLM output *correct*; it makes it *cheap and decodable*. Validation remains the job of OWL DL checking, SHACL and the production gate (ADR-A22, ADR-A25, ADR-A28).
- Human readability is not a goal. Where legibility and token count conflict, token count wins.

---

## 2. Document model

An MCN document denotes an RDF graph. The graph, when it contains an `owl:Ontology` header (directive `@o`) and only OWL 2 DL-compatible constructs, is an OWL 2 ontology document under the OWL 2 RDF-based mapping and can be serialised in any OWL syntax by any conformant tool. Decoding is a total function from well-formed MCN text to a graph; ill-formed text is rejected with an error, never silently repaired.

The decoded graph consists of four kinds of contribution:

| Source | Contributes |
|---|---|
| Directives (`@`) | ontology header, imports, prefix bindings, base IRI, decoder options |
| Block headers (`%`) | one scheme individual (`mork:MappingScheme` etc.) plus a *context* applied to following node lines |
| Node lines | one named individual per line: typing, scheme membership, property assertions, annotated assertions, inline reified nodes, artefact payloads |
| Expression lines (`=`) | a `mork:TemplateExpression` tree |
| Axiom lines (`!`) | OWL declarations, class/property axioms, GCIs, disjointness axioms, raw triples |

A document is processed top to bottom in a single pass. Later lines may reference IRIs introduced by earlier or later lines; references are never checked for existence by the decoder (an IRI is an IRI). Repeated node lines for the same subject merge, exactly as repeated subjects merge in Turtle.

---

## 3. Lexical structure

### 3.1 Encoding and lines

- UTF-8 text. Line terminator is `LF`; `CR LF` is accepted.
- A **logical line** is a physical line, plus any immediately following physical lines that begin with `;` (continuation; the `;` is dropped and the remainder appended with one space).
- Blank lines are ignored. A physical line whose first non-blank character is `#` is a comment and is ignored. Comments are for humans editing MCN by hand; generators SHOULD NOT emit them.
- Leading whitespace on a line has no meaning and SHOULD NOT be emitted (it costs tokens).

### 3.2 Line kinds

The first character of a logical line determines its kind:

| First char | Kind | Section |
|---|---|---|
| `@` | directive | §6 |
| `%` | block header | §7 |
| `!` | OWL axiom line | §11 |
| anything else | node line, or expression line if the second token is `=` | §9, §10.1 |

### 3.3 Tokens

Within a logical line, tokens are separated by one or more spaces or tabs. The following token classes exist:

| Class | Form | Notes |
|---|---|---|
| bare | run of characters containing no whitespace and none of `, { } [ ]` | identifiers, codes, unquoted literals, CURIEs |
| quoted | `"…"` with escapes `\"` `\\` `\n` `\t` `\uXXXX` | optionally followed *without a space* by `@lang` or `^prefix:dt` |
| iri | `<…>` | absolute IRI |
| inline | `[ … ]` | nested node, §9.6 |
| annotation | `{ … }` | attaches to the immediately preceding value, no space, §9.7 |
| list | value `,` value `,` … | no spaces around commas, §9.5 |

Brackets and braces nest; a quoted string inside them may contain any bracket character.

### 3.4 Identifiers and IRIs

An **identifier** in subject or object position resolves to an IRI by these rules, tried in order:

1. `<…>` → the IRI as written.
2. A reserved token beginning with `.` (table in §8.4) → its fixed IRI.
3. A token beginning with `:` → the **default target prefix** declared by `@t` plus the local name. Error if no `@t` is in force.
4. A token containing `:` → a CURIE against the prefix table (§6). Error if the prefix is unbound.
5. A token beginning with `_:` → a blank node with that label (only meaningful in `!T` lines).
6. Otherwise → a **local id**: the base IRI declared by `@b` concatenated with the token. Error if no `@b` is in force.

Local ids match `[A-Za-z_][A-Za-z0-9_.\-]*`. They are opaque: a decoder never interprets an id's spelling. Generators SHOULD use short ids; ids need to be memorable *to the generator* (a model recalls `Map_Loan` more reliably than `m7`), so brevity is a recommendation, not a rule.

Predeclared prefixes (never need `@p`): `mork`, `owl`, `rdf`, `rdfs`, `xsd`, `skos`, `sh`, `swrl`, `swrlb`, `rr`, `rml`, `fnd`, `dct` — bound to the IRIs used in `Mork.ttl` and `Executable.ttl` (`rml` is `http://semweb.mmlab.be/ns/rml#`).

### 3.5 Literals

A value in a **data-kind** slot (§8) is a literal. Its lexical form and datatype are determined as follows:

| Written as | Result |
|---|---|
| `"text"` | `xsd:string` (plain literal) |
| `"text"@en` | language-tagged |
| `"text"^xsd:date` | typed with the given datatype (note the single `^`) |
| bare token, code has a fixed datatype | that datatype (e.g. `w 85` → `"85"^^xsd:integer`) |
| bare token, code's datatype is *inferred* | `t`/`f` → `xsd:boolean`; `-?[0-9]+` → `xsd:integer`; `-?[0-9]+\.[0-9]+` → `xsd:decimal`; else `xsd:string` |
| bare token, code has no datatype | `xsd:string` |

So `c #Species` is the string `"#Species"`, `v t` is boolean true, `v "t"` is the string `"t"`, and `ef 2026-10-01T00:00:00Z` is a typed `xsd:dateTime` without any annotation. A bare token that must contain a space, comma, bracket or brace is written quoted.

---

## 4. Codes

Every property and class has a **code**. Codes are the entire reason MCN is cheap, so their design is constrained:

- **Type codes** are uppercase, one or two letters (`MD`, `RA`, `GT`). The first letter names the family (M mapping, C concept, R representation, X ontology proxy, I intent, G generative support, E expression, S scheme).
- **Property codes** are lowercase, one to three characters, or a single punctuation mark for the SKOS hierarchy (`>` broader, `<` narrower, `~` related, `s=` `s~` `s>` `s<` `s-` for the SKOS mapping relations).
- Frequency drives length: the ten most common assertions in real MORK data (`f`, `xt`, `xr`, `cn`, `df`, `w`, `n`, `c`, `r`, `v`) are one or two characters.
- Codes are mnemonic where possible (`xt` exact T-Box, `bt` broad T-Box, `nt` narrow T-Box; `lx` lexical, `sx` semantic, `tx` structural) so a model can generate them reliably from a short system-prompt codebook.
- **Kind** is fixed per code: *object* (value is an IRI or inline node), *data* (value is a literal), or *polymorphic* (the property is chosen by the subject's type — `pb`, `pv`, `tl`). Because kind is fixed, bare tokens are never ambiguous: `c Loan` is a string, `xt Loan` is an IRI.
- A **CURIE in code position** (`dct:created 2026-01-01`, `ex:myProp foo`) is accepted everywhere a code is, as an escape for properties without codes. Its kind is object unless the value is quoted, so literals for CURIE properties are always written quoted (`dct:created "2026-01-01"^xsd:date`).

The full codebook is in §8.

---

## 5. Implicit content supplied by the decoder

The decoder adds the following without them being written. Generators MUST NOT write them (doing so is legal but wasteful).

| Implicit fact | Rule |
|---|---|
| `rdf:type owl:NamedIndividual` | on every node-line subject, block header, inline node and minted expression node |
| Scheme membership | every node line inside a `%M` block gets `mork:mappingScheme <scheme>`; `%T` → `mork:conceptScheme`; `%R` → `mork:representationScheme`; `%O` → `mork:ontologicalScheme`; `%I` → `mork:intentScheme`; `%K` and `%U` → `skos:inScheme` |
| Default type | a node line with no type token gets the block's default type (`%M` → `mork:DataMapping`, `%T` → `mork:DataConcept`, `%R` → `mork:Representation`, `%O` → `mork:OwlAxiom`, `%I` → `mork:IntentNode`, `%K` → `sh:NodeShape`, `%U` → `swrl:Imp`). In `%X` there is no default. |
| Implied generative types | a subject with `gs` becomes `mork:ShapeMapping`; `gr` → `mork:RuleMapping`; `gt` → `mork:TransformMapping`; `gc` → `mork:ProjectionMapping`. These mirror the `owl:equivalentClass` definitions in `Mork.ttl`; asserting them explicitly costs one token and is optional. |
| Inline node typing | a positional inline node (§9.6) gets the class its parent code implies (`tg` → `TargetingSpec`, `pb` → `ParameterBinding`, `pv` → the provenance class matching the subject's generative type, `hb` → `TemplateBinding`) |
| `swrlCompactSyntax` | a `gr` payload string is also asserted verbatim as `mork:swrlCompactSyntax` on the mapping, as the ontology recommends |
| Datatypes | per code, §3.5 |
| Inverses | **not** materialised by default. The loan example in the repository documents why: emitting both directions of `compositeNarrowerMapping`/`compositeBroaderMapping` double-counts edges in the dependency analyser. `@opt inv` asks the decoder to add the inverse of every asserted edge whose property has a declared `owl:inverseOf`. |

What the decoder never adds: `mappingScheme` for nodes in `%X`, `Datum` typing from the presence of `df` (that is the reasoner's job and generators should write `MD` when they mean it), or any GCI-derived consequence.

---

## 6. Directives

| Directive | Form | Effect |
|---|---|---|
| `@b` | `@b <iri>` | Base IRI for local ids. The author includes the trailing `#` or `/`. May appear more than once; each occurrence applies to subsequent lines. |
| `@o` | `@o <ontology-iri> [<version-iri>]` | Asserts `<ontology-iri> a owl:Ontology` (and `owl:versionIRI`). Required for the output to be an OWL ontology *document*; optional for a bare graph. |
| `@i` | `@i <iri>,<iri>,…` | `owl:imports` on the ontology declared by `@o`. Error if no `@o` precedes it. |
| `@p` | `@p prefix=<iri>` | Binds a prefix. Rebinding a predeclared prefix is an error. |
| `@t` | `@t prefix` | Names the **default target prefix**: tokens of the form `:Local` resolve against it. Intended for the target ontology, which is referenced from almost every mapping. |
| `@u` | `@u name` | Loads a named **profile** (§6.1). |
| `@opt` | `@opt flag …` | Decoder options: `inv` (materialise inverses), `strict` (treat lint warnings in §14.2 as errors), `bnode-shapes` (emit SHACL property shapes as blank nodes instead of minted IRIs). |
| `@v` | `@v 0.1` | MCN version the document was written against. Optional; defaults to the decoder's version. |

Directive lines are processed where they occur; a `@b` or `@t` can change mid-document, which allows one document to carry several schemes with different bases.

### 6.1 Profiles

A profile is a named, out-of-band bundle of `@b`, `@p`, `@t` and `@opt` settings maintained by a deployment (for example one per target ontology). `@u lattice-insure-o` replaces the ~50 tokens of prefix IRIs that would otherwise head every document. Profiles are resolved by the decoder from a registry it is configured with; a document that uses `@u` is only decodable with that registry, and the decoder MUST record the profile's content hash in the decoded graph as `mork:inputHash` on the ontology node (so decoded output remains reproducible). Profiles are RECOMMENDED for agent-to-decoder traffic inside a deployment and NOT RECOMMENDED for MCN that is stored or exchanged.

---

## 7. Blocks

A block header opens a scheme and a context that lasts until the next block header or end of file.

```
%M id (code value)*        MappingScheme          members: mork:mappingScheme          default type M
%T id (code value)*        TaxonomyScheme         members: mork:conceptScheme          default type C
%R id [.fmt] (code value)* RepresentationScheme   members: mork:representationScheme   default type R
%O id (code value)*        OntologicalScheme      members: mork:ontologicalScheme      default type X
%I id (code value)*        IntentScheme           members: mork:intentScheme           default type I
%K id (code value)*        ConstraintScheme       members: skos:inScheme               default type SH
%U id (code value)*        RuleScheme             members: skos:inScheme               default type SW
%X                         no scheme, no membership, no default type
```

The header is itself a node line for the scheme individual: `%M MS md .prod mv 1.2` declares `MS` as a `MappingScheme` in `ProductionMode` with version `1.2`. In `%R` a reserved format token immediately after the id (`.json`, `.xml`, `.yaml`) is shorthand for `fm`.

A node that belongs to two schemes (a `DataConcept` that is also a `Representation`, as in the `Rep_Issuer` example in `Mork.ttl`) is written once inside one block with the second membership given explicitly (`rs Rep_Scheme`), or written as two node lines in two blocks; both produce the same graph.

`%X` is for content that has no scheme: shadow property declarations, external T-Box fragments, standalone template expressions, artefacts referenced from several mappings.

---

## 8. Codebook

The tables in this section are normative and complete with respect to `Mork.ttl` at the commit this document was written against: every class, object property, datatype property, annotation property and named individual in the ontology has a code or a reserved token. The `Notes` column records defaults and inference behaviour.

### 8.1 Type codes

Multiple types are joined with `+`: `M+MD`, `C+RE`. A CURIE whose local name begins with an uppercase letter may be used as a type (`ex:Widget`). A leading `+` forces type interpretation of any identifier regardless of spelling — a lowercase CURIE (`+ex:widget`) or a local id (`+CompilationMode`, needed when the base is the ontology's own namespace).

**Mapping**

| Code | Class | Notes |
|---|---|---|
| `M` | `mork:DataMapping` | default type inside %M |
| `MD` | `mork:Datum` |  |
| `MU` | `mork:UncertainMapping` |  |
| `MX` | `mork:DeferredContext` |  |
| `ML` | `mork:Lookup` |  |
| `MW` | `mork:WeightedMatch` |  |
| `MI` | `mork:Interpolation` | a skos:OrderedCollection, not a DataMapping |
| `MH` | `mork:Hypothesis` | normally inferred; rarely asserted |
| `MN` | `mork:IndexedMapping` |  |
| `MG` | `mork:GenerativeMapping` | abstract; prefer MS/MR/MT/MP |
| `MS` | `mork:ShapeMapping` | implied by `gs` |
| `MR` | `mork:RuleMapping` | implied by `gr` |
| `MT` | `mork:TransformMapping` | implied by `gt` |
| `MP` | `mork:ProjectionMapping` | implied by `gc` |

**Concept**

| Code | Class | Notes |
|---|---|---|
| `C` | `mork:DataConcept` | default type inside %T |
| `CO` | `mork:Objectification` |  |

**Representation**

| Code | Class | Notes |
|---|---|---|
| `R` | `mork:Representation` | default type inside %R |
| `RE` | `mork:Entity` |  |
| `RA` | `mork:Attribute` |  |
| `RY` | `mork:Array` |  |
| `RS` | `mork:Association` |  |
| `RC` | `mork:Composition` |  |
| `RH` | `mork:Chaining` |  |
| `RL` | `mork:Collection` |  |
| `RO` | `mork:OrderedCollection` |  |
| `RU` | `mork:UnorderedCollection` |  |
| `RT` | `mork:SetListing` |  |
| `RM` | `mork:Membership` | abstract by convention |
| `RN` | `mork:AnonymousElement` |  |
| `RV` | `mork:ScalarValueElement` |  |
| `RX` | `mork:CollectionElement` |  |
| `RF` | `mork:Referencing` |  |
| `RI` | `mork:IdentifiableElement` |  |

**Ontology proxy** (members of an `OntologicalScheme`)

| Code | Class | Notes |
|---|---|---|
| `X` | `mork:OwlAxiom` | default type inside %O |
| `XC` | `mork:OwlClass` |  |
| `XO` | `mork:OwlObjectProperty` |  |
| `XD` | `mork:OwlDataProperty` |  |
| `XG` | `mork:Digraph` | deprecated in Mork.ttl |
| `XI` | `mork:DeferredConceptIRI` | the class; the punned individual is `.dci` |

**Intent**

| Code | Class | Notes |
|---|---|---|
| `I` | `mork:IntentNode` | default type inside %I |
| `IQ` | `mork:QualitativeIntent` |  |
| `IN` | `mork:QuantitativeConstraint` |  |
| `IS` | `mork:SpatialScope` |  |
| `IT` | `mork:TemporalScope` |  |
| `IX` | `mork:ExclusionIntent` |  |
| `II` | `mork:InclusionIntent` |  |
| `IR` | `mork:NormativeReferenceItent` | IRI spelling preserved exactly as declared in Mork.ttl |

**Generative support**

| Code | Class | Notes |
|---|---|---|
| `GT` | `mork:TargetingSpec` | positional form `[mode target]` |
| `GP` | `mork:ParameterBinding` | positional form `[name type value]` |
| `GC` | `mork:ConstraintProvenance` | positional form `[creator model conf status]` |
| `GR` | `mork:RuleProvenance` | positional form `[creator model conf status]` |
| `GF` | `mork:TransformProvenance` | positional form `[creator model conf status]` |
| `GJ` | `mork:ProjectionProvenance` | positional form `[creator model conf status]` |
| `GS` | `mork:ShapeTemplate` |  |
| `GU` | `mork:RuleTemplate` |  |
| `GQ` | `mork:QueryTemplate` |  |

**Template expression**

| Code | Class | Notes |
|---|---|---|
| `E` | `mork:TemplateExpression` | normally produced by `id = expr` lines |
| `EL` | `mork:LiteralExpression` |  |
| `ER` | `mork:RefExpression` |  |
| `EC` | `mork:ConcatExpression` |  |
| `EI` | `mork:InterpolationExpression` |  |
| `EK` | `mork:LookupExpression` |  |
| `EB` | `mork:TemplateBinding` | positional form `[name expr]` |

**Scheme** (normally introduced by block headers; usable as explicit types in `%X`)

| Code | Class | Notes |
|---|---|---|
| `SM` | `mork:MappingScheme` | block header %M |
| `ST` | `mork:TaxonomyScheme` | block header %T |
| `SR` | `mork:RepresentationScheme` | block header %R |
| `SO` | `mork:OntologicalScheme` | block header %O |
| `SI` | `mork:IntentScheme` | block header %I |
| `SK` | `mork:ConstraintScheme` | block header %K |
| `SU` | `mork:RuleScheme` | block header %U |

**Miscellaneous and external artefact types**

| Code | Class | Notes |
|---|---|---|
| `CM` | `mork:CompilationMode` |  |
| `SF` | `mork:SerializationFormat` |  |
| `SH` | `sh:NodeShape` | payload form `SH "<shacl-compact>"`, §10.3 |
| `SP` | `sh:PropertyShape` |  |
| `SW` | `swrl:Imp` | payload form `SW "<swrl-compact>"`, §10.2 |
| `TM` | `rr:TriplesMap` | payload form `TM "<rml-compact>"`, §10.4 |
| `PI` | `fnd:PersistentIdentity` |  |

### 8.2 Property codes

Kind: *object* takes an IRI, inline node or payload; *data* takes a literal typed per the last column (*inferred* per §3.5); *polymorphic* is resolved by subject type per §8.3.

**Scheme membership** (normally implicit via block headers)

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `ms` | `mork:mappingScheme` | object |  |
| `cs` | `mork:conceptScheme` | object |  |
| `rs` | `mork:representationScheme` | object |  |
| `os` | `mork:ontologicalScheme` | object |  |
| `is` | `mork:intentScheme` | object |  |
| `in` | `skos:inScheme` | object |  |

**Mapping selection**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `f` | `mork:mappingFor` | object |  |
| `hm` | `mork:hasMapping` | object |  |
| `iv` | `mork:indicativeMapping` | object |  |

**Exact match**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `xt` | `mork:exactTBoxMatch` | object |  |
| `xr` | `mork:exactRBoxMatch` | object |  |
| `xa` | `mork:exactABoxMatch` | object |  |
| `xi` | `mork:inverseRBoxMatch` | object |  |
| `xm` | `mork:intransitiveExactMatch` | object |  |

**Category match**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `bt` | `mork:broadTBoxCategoryMatch` | object |  |
| `br` | `mork:broadRBoxCategoryMatch` | object |  |
| `ba` | `mork:broadABoxCategoryMatch` | object |  |
| `nt` | `mork:narrowTBoxCategoryMatch` | object |  |
| `nr` | `mork:narrowRBoxCategoryMatch` | object |  |
| `na` | `mork:narrowABoxCategoryMatch` | object |  |
| `bc` | `mork:broadCategoryMatch` | object |  |
| `nc` | `mork:narrowCategoryMatch` | object |  |

**Possible match**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `px` | `mork:possibleMatch` | object |  |
| `lx` | `mork:lexicalMatch` | object |  |
| `sx` | `mork:semanticMatch` | object |  |
| `tx` | `mork:structuralMatch` | object |  |
| `pt` | `mork:pathMatch` | object |  |
| `rp` | `mork:referenceDataPath` | object |  |
| `pm` | `mork:partialMatch` | object | equivalent to `px` |
| `mum` | `mork:missingOrUnrelatedMatch` | object | deprecated |
| `dgm` | `mork:digraphMatch` | object | deprecated |
| `dgo` | `mork:digraphOf` | object | deprecated |

**Mapping composition**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `cn` | `mork:compositeNarrowerMapping` | object |  |
| `cb` | `mork:compositeBroaderMapping` | object |  |
| `cnt` | `mork:compositeNarrowerTemplate` | object |  |
| `cbt` | `mork:compositeBroaderTemplate` | object |  |
| `nrm` | `mork:narrowerMapping` | object |  |
| `brm` | `mork:broaderMapping` | object |  |
| `wn` | `mork:weightedNarrower` | object |  |
| `wb` | `mork:weightedBroader` | object |  |
| `ap` | `mork:broaderApplicative` | object |  |

**Mapping relation**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `rm` | `mork:relatedMapping` | object |  |
| `cm` | `mork:closeMapping` | object |  |
| `em` | `mork:exactMapping` | object |  |
| `sg` | `mork:siblingMapping` | object |  |

**Deferral and templates**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `df` | `mork:deferredMapping` | object |  |
| `dp` | `mork:dependentMapping` | object |  |
| `hy` | `mork:hypothesisMapping` | object |  |
| `tp` | `mork:templateMapping` | object |  |
| `it` | `mork:identityTemplateMapping` | object |  |
| `rd` | `mork:referenceDataMapping` | object |  |
| `tc` | `mork:templateClassMapping` | object |  |
| `y` | `mork:yieldConcept` | object |  |

**Placeholder**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `ph` | `mork:placeholderMapping` | object |  |
| `cc` | `mork:concatenation` | object |  |
| `ic` | `mork:interpolationComponent` | object |  |

**Property assertion**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `ad` | `mork:assertsPropertyDomains` | object |  |
| `ar` | `mork:assertsPropertyRanges` | object |  |
| `pma` | `mork:propertyMappingAssertions` | object |  |

**Concept and representation structure**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `kn` | `mork:compositeNarrower` | object |  |
| `kb` | `mork:compositeBroader` | object |  |
| `an` | `mork:associativeNarrower` | object |  |
| `ab` | `mork:associativeBroader` | object |  |
| `brl` | `mork:broadConceptRole` | object |  |
| `nrl` | `mork:narrowConceptRole` | object |  |
| `bnr` | `mork:broadNavigableConceptRole` | object |  |
| `nnr` | `mork:narrowNavigableConceptRole` | object |  |
| `mp` | `mork:memberProperty` | object |  |
| `mo` | `mork:memberOf` | object |  |
| `et` | `mork:elementType` | object |  |
| `rl` | `mork:relatedProperty` | object |  |
| `ro` | `mork:representationOf` | object |  |
| `ra` | `mork:representedAs` | object |  |
| `hc` | `mork:hasConcept` | object |  |
| `fm` | `mork:format` | object |  |

**SKOS**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `>` | `skos:broader` | object |  |
| `<` | `skos:narrower` | object |  |
| `~` | `skos:related` | object |  |
| `s=` | `skos:exactMatch` | object |  |
| `s~` | `skos:closeMatch` | object |  |
| `s>` | `skos:broadMatch` | object |  |
| `s<` | `skos:narrowMatch` | object |  |
| `s-` | `skos:relatedMatch` | object |  |
| `sm` | `skos:member` | object |  |

**Precedence** (normally derived, not asserted)

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `pr` | `mork:precedes` | object |  |
| `sp` | `mork:softPrecedes` | object |  |
| `rif` | `mork:resolvesIdentityFor` | object |  |
| `tb` | `mork:templateBinding` | object |  |

**Intent**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `ri` | `mork:refinesIntent` | object |  |
| `im` | `mork:intentMapping` | object |  |
| `sv` | `mork:scopeValue` | object |  |
| `cu` | `mork:constraintUnit` | object |  |
| `cd` | `mork:constraintDimension` | object |  |
| `src` | `mork:hasNaturalLanguageSource` | data | xsd:string |
| `cf` | `mork:hasIntentConfidence` | data | xsd:decimal |
| `op` | `mork:constraintOperator` | data | xsd:string |
| `cv` | `mork:constraintValue` | data | xsd:decimal |
| `cuv` | `mork:constraintUpperValue` | data | xsd:decimal |
| `sty` | `mork:scopeType` | data | xsd:string |
| `sin` | `mork:scopeInclusion` | data | xsd:string |
| `td` | `mork:temporalDuration` | data | xsd:dayTimeDuration |
| `tu` | `mork:temporalUnit` | data | xsd:string |
| `rid` | `mork:referenceIdentifier` | data | xsd:string |

**Template expression** (normally produced by expression lines, §10.1)

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `cl` | `mork:concatLeft` | object |  |
| `cr` | `mork:concatRight` | object |  |
| `hb` | `mork:hasBinding` | object |  |
| `ls` | `mork:lookupSource` | object |  |
| `lk` | `mork:lookupScheme` | object |  |
| `lp` | `mork:lookupProperty` | object |  |
| `pe` | `mork:placeholderExpression` | object |  |
| `ts` | `mork:templateString` | data | xsd:string |
| `phn` | `mork:placeholderName` | data | xsd:string |

**Generative**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `tg` | `mork:hasTargetingSpec` | object | bare IRI value ⇒ `[c IRI]`, §9.6 |
| `pb` | `mork:hasParameterBinding` / `mork:paramBinding` | polymorphic |  |
| `do` | `mork:dependsOnMapping` | object |  |
| `gs` | `mork:generatesShapeDefinition` | object | string value ⇒ SHACL payload |
| `gr` | `mork:generatesRuleDefinition` | object | string value ⇒ SWRL payload |
| `gt` | `mork:generatesTransformDefinition` | object | string value ⇒ RML payload |
| `gc` | `mork:generatesClassDefinition` | object |  |
| `tl` | `mork:hasShapeTemplate` / `mork:hasRuleTemplate` | polymorphic |  |
| `st` | `mork:hasShapeTemplate` | object |  |
| `rt` | `mork:hasRuleTemplate` | object |  |
| `pv` | `mork:hasConstraintProvenance` / `mork:hasRuleProvenance` / `mork:hasTransformProvenance` / `mork:hasProjectionProvenance` | polymorphic |  |
| `pvc` | `mork:hasConstraintProvenance` | object |  |
| `pvr` | `mork:hasRuleProvenance` | object |  |
| `pvt` | `mork:hasTransformProvenance` | object |  |
| `pvp` | `mork:hasProjectionProvenance` | object |  |
| `se` | `mork:hasSeverity` | object |  |
| `aj` | `mork:appliesInJurisdiction` | object |  |
| `bq` | `mork:bindsToCriteria` | object |  |
| `ju` | `mork:jurisdiction` | data | xsd:string |
| `ef` | `mork:effectiveFrom` | data | xsd:dateTime |
| `eu` | `mork:effectiveUntil` | data | xsd:dateTime |
| `kv` | `mork:constraintVersion` | data | xsd:string |
| `mv` | `mork:mappingVersion` | data | xsd:string |
| `dr` | `mork:deprecationReason` | data | xsd:string |
| `pnm` | `mork:paramName` | data | xsd:string |
| `pty` | `mork:paramType` | data | xsd:string |
| `pvl` | `mork:paramValue` | data | inferred |
| `ql` | `mork:queryLanguage` | data | xsd:string |
| `qt` | `mork:queryText` | data | xsd:string |
| `swt` | `mork:swrlText` | data | xsd:string (deprecated) |
| `to` | `mork:targetsOntology` | data | xsd:anyURI |
| `ih` | `mork:inputHash` | data | xsd:string |
| `mid` | `mork:llmModelId` | data | xsd:string |
| `lc` | `mork:llmConfidence` | data | xsd:decimal |
| `rv` | `mork:reviewStatus` | data | xsd:string |
| `pc` | `mork:provenanceCreator` | data | xsd:string |
| `pd` | `mork:provenanceCreated` | data | xsd:dateTime |
| `isc` | `mork:impactScope` | data | xsd:string |

**Versioning and Foundation**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `ss` | `mork:supersedes` | object |  |
| `eg` | `mork:egressProjection` | object |  |
| `md` | `mork:compilationMode` | object |  |
| `gv` | `fnd:hasGovernanceState` | object |  |
| `fi` | `fnd:hasIdentity` | object |  |
| `sby` | `fnd:supersededBy` | object |  |

**Core data**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `w` | `mork:weighting` | data | xsd:integer |
| `n` | `mork:mappingNote` | data | xsd:string |
| `c` | `mork:conceptName` | data | xsd:string |
| `ci` | `mork:conceptIRI` | data | xsd:anyURI |
| `cid` | `mork:conceptId` | data | xsd:string |
| `i` | `mork:individualName` | data | xsd:string |
| `ii` | `mork:individualIRI` | data | xsd:anyURI |
| `id` | `mork:identifier` | data | xsd:string |
| `p` | `mork:path` | data | xsd:string |
| `rf` | `mork:reference` | data | xsd:string |
| `r` | `mork:dataRef` | data | xsd:string |
| `v` | `mork:dataInline` | data | inferred |
| `dt` | `mork:data` | data | inferred |
| `ix` | `mork:mappingIndex` | data | xsd:integer |
| `mr` | `mork:mappingRecommendation` | data | xsd:string |
| `nme` | `mork:name` | data | xsd:string |
| `tt` | `mork:template` | data | xsd:string |
| `ct` | `mork:conceptNameTemplate` | data | xsd:string |
| `cft` | `mork:conceptFQNameTemplate` | data | xsd:string |
| `cst` | `mork:conceptShortNameTemplate` | data | xsd:string |
| `ip` | `mork:interpolationTemplate` | data | xsd:string |
| `inc` | `mork:incompleteMapping` | data | xsd:boolean |
| `icn` | `mork:itemsConstrained` | data | xsd:boolean |
| `ord` | `mork:orderedItems` | data | xsd:boolean |
| `unq` | `mork:uniqueItems` | data | xsd:boolean |
| `iri` | `mork:iri` | data | xsd:string |
| `ud` | `mork:userDeclined` | data | xsd:string |
| `sw` | `mork:swrlCompactSyntax` | data | xsd:string |
| `cev` | `mork:collectionElementScalarValue` | data | inferred (internal) |
| `epv` | `mork:externalPropertyValue` | data | inferred (internal) |

**Annotation**

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `nn` | `skos:note` | data | xsd:string |
| `sd` | `skos:definition` | data | xsd:string |
| `lb` | `rdfs:label` | data | xsd:string |
| `rc` | `rdfs:comment` | data | xsd:string |
| `ex` | `skos:example` | data | xsd:string |
| `sco` | `skos:scopeNote` | data | xsd:string |
| `al` | `skos:altLabel` | data | xsd:string |
| `en` | `skos:editorialNote` | data | xsd:string |
| `hn` | `skos:historyNote` | data | xsd:string |
| `sa` | `rdfs:seeAlso` | object |  |
| `db` | `rdfs:isDefinedBy` | data | xsd:string |
| `sas` | `owl:sameAs` | object |  |
| `dep` | `owl:deprecated` | data | xsd:boolean |
| `dcc` | `dct:creator` | data | xsd:string |
| `dct` | `dct:title` | data | xsd:string |
| `dcd` | `dct:description` | data | xsd:string |
| `dco` | `dct:contributor` | data | xsd:string |

**SHACL targeting** (on `GT` nodes; usually written positionally)

| Code | Property | Kind | Literal type |
|---|---|---|---|
| `tcl` | `sh:targetClass` | object |  |
| `tob` | `sh:targetObjectsOf` | object |  |
| `tsb` | `sh:targetSubjectsOf` | object |  |
| `tnd` | `sh:targetNode` | object |  |

### 8.3 Polymorphic codes

Resolution uses the subject's asserted types *at the point the code is decoded* — including the block default type and any type implied by an earlier code on the same line. Generators SHOULD put the type token, or the payload code (`gs`/`gr`/`gt`/`gc`) that implies it, before any polymorphic code.

| Code | Subject type | Property |
|---|---|---|
| `pb` | `mork:QueryTemplate` | `mork:paramBinding` |
| `pb` | anything else | `mork:hasParameterBinding` |
| `tl` | `mork:ShapeMapping` | `mork:hasShapeTemplate` |
| `tl` | `mork:RuleMapping` | `mork:hasRuleTemplate` |
| `pv` | `mork:ShapeMapping` | `mork:hasConstraintProvenance` (inline node typed `ConstraintProvenance`) |
| `pv` | `mork:RuleMapping` | `mork:hasRuleProvenance` (inline typed `RuleProvenance`) |
| `pv` | `mork:TransformMapping` | `mork:hasTransformProvenance` (inline typed `TransformProvenance`) |
| `pv` | `mork:ProjectionMapping` | `mork:hasProjectionProvenance` (inline typed `ProjectionProvenance`) |

An unresolvable polymorphic code is an error; the explicit codes (`pvc`, `st`, …) are always available.

### 8.4 Reserved value tokens

Reserved tokens begin with `.` and are valid only in object position.

| Token | Resolves to |
|---|---|
| `.T` | `owl:Thing` |
| `.N` | `owl:Nothing` |
| `.top` | `owl:topObjectProperty` |
| `.dtop` | `owl:topDataProperty` |
| `.dci` | `mork:DeferredConceptIRI` |
| `.dcd` | `mork:DeferredClassDefinition` |
| `.dop` | `mork:DeferredObjectPropertyDefinition` |
| `.ddp` | `mork:DeferredDataPropertyDefinition` |
| `.did` | `mork:DeferredIndividualDefinition` |
| `.dab` | `mork:DeferredABoxReference` |
| `.mos` | `mork:MorkOntologyScheme` |
| `.bot` | `mork:Bottom` |
| `.nothing` | `mork:OwlNothing` |
| `.json` | `mork:JSON` |
| `.xml` | `mork:XML` |
| `.yaml` | `mork:YAML` |
| `.draft` | `mork:DraftMode` |
| `.review` | `mork:ReviewMode` |
| `.prod` | `mork:ProductionMode` |
| `.viol` | `sh:Violation` |
| `.warn` | `sh:Warning` |
| `.info` | `sh:Info` |
| `.gD` | `fnd:Draft` |
| `.gR` | `fnd:Reviewed` |
| `.gA` | `fnd:Active` |
| `.gS` | `fnd:Superseded` |

---

## 9. Node lines

```
subject [types] (code value-list)*
```

### 9.1 Subject

An identifier per §3.4. Local ids are the norm; a CURIE or `<iri>` subject lets a document assert facts about external individuals (for example `owl:sameAs` on an `OwlAxiom` proxy).

### 9.2 Types

The token immediately after the subject is a type list if it begins with `+`, or if every `+`-separated part is a type code or a CURIE whose local name starts with an uppercase letter. Otherwise it is the first property code and the block default type applies. This rule means a CURIE property with an uppercase local name cannot appear first on a line; put any code before it. In `!I` lines the `:` type list additionally accepts bare local ids without the `+` (§11).

### 9.3 Property pairs

The rest of the line is a sequence of `code value-list` pairs. Codes may repeat. Order is not significant except for polymorphic resolution (§8.3) and IRI minting of inline nodes (§12), both of which depend on left-to-right order.

### 9.4 Values

A value is one of: a bare token, a quoted literal, an `<iri>`, or an inline node `[…]`. Its interpretation depends on the code's kind (§4).

### 9.5 Lists

`code a,b,c` asserts three triples with the same predicate. There are no spaces around commas. A quoted string may appear as a list member. A bare string value containing a comma must be quoted.

### 9.6 Inline nodes

`[ … ]` in value position creates a node, links it as the object of the current code, and asserts the contents on the new node. Three forms exist; the first token inside the brackets selects the form:

| First token | Form | Meaning |
|---|---|---|
| `#id` | explicit identity | the node is the local id `id` (or CURIE/`<iri>`); following tokens are interpreted as one of the two forms below |
| a type list (§9.2) | **typed** | the node gets those types, then `code value` pairs as on a node line |
| anything else | **positional** | only permitted under codes with a positional table (below); the first *k* tokens fill the slots in order (`_` skips a slot), after which `code value` pairs may follow |

Positional tables:

| Under code | Node type | Slots | Notes |
|---|---|---|---|
| `tg` | `TargetingSpec` | `mode target` | mode ∈ `c` (`sh:targetClass`), `o` (`sh:targetObjectsOf`), `s` (`sh:targetSubjectsOf`), `n` (`sh:targetNode`). A bare IRI directly as the value of `tg` is shorthand for `[c IRI]`. |
| `pb` | `ParameterBinding` | `name type value` | type ∈ `N`umeric, `C`oncept, `P`ath, `S`tring, `D`uration, or the full word; value is inferred-typed per §3.5 |
| `pv` | provenance class per §8.3 | `creator model confidence status` | status is the `reviewStatus` string (`DRAFT`, `APPROVED`, `DEPRECATED`) |
| `hb` | `TemplateBinding` | `name expr` | expr is a template expression (§10.1) |

Inline nodes without `#id` receive minted IRIs (§12.2), not blank nodes, so that generated provenance and targeting records are addressable by SHACL reports and audit queries. Inline nodes nest to any depth.

### 9.7 Annotations on assertions

A `{ … }` immediately following a value (no intervening space) annotates *that* assertion. The braces contain `code value` pairs exactly as on a node line. The decoder emits the OWL 2 annotated-axiom pattern:

```
xt :Loan{n "Close lexical match on 'loan'" w 90}
```
decodes to
```
:m mork:exactTBoxMatch fin:Loan .
[] a owl:Axiom ; owl:annotatedSource :m ; owl:annotatedProperty mork:exactTBoxMatch ;
   owl:annotatedTarget fin:Loan ; mork:mappingNote "Close lexical match on 'loan'" ; mork:weighting 90 .
```

In a list, the braces bind to the preceding member: `cn a{n "x"},b`. Annotations on annotations are not supported (OWL 2 does not permit them either).

### 9.8 Artefact payloads

The codes `gs`, `gr`, `gt` and the types `SH`, `SW`, `TM` accept a **payload string**: a quoted literal written in the corresponding sub-notation (§10.2–10.4). The decoder mints an artefact node (§12.2), parses the payload into structured RDF (a `sh:NodeShape`, `swrl:Imp` or `rr:TriplesMap` graph), and links it. The payload text itself is *not* stored, except that a `gr` payload is additionally asserted as `mork:swrlCompactSyntax` on the mapping, as `Mork.ttl` recommends.

Three ways to supply an artefact, from cheapest to most explicit:

```
r1 MR gr "Applicant(?a)^hasCreditScore(?a,?s)^swrlb:greaterThanOrEqual(?s,700)->Eligible(?a)"
r1 MR gr [#eligRule SW "Applicant(?a)^…->Eligible(?a)" lb "Eligibility rule"]
r1 MR gr eligRule
eligRule SW "Applicant(?a)^…->Eligible(?a)"
```

Whether the artefact is LLM-authored or compiler-generated is a governance question (ADR-A25), not a syntactic one; both are written the same way.

---

## 10. Sub-notations

### 10.1 Template expressions

An **expression line** defines a `mork:TemplateExpression` tree (Foundations §3.9):

```
id = expr
```

Expression grammar (whitespace insignificant except inside quotes):

```
expr    := term ( '+' term )*                    concatenation, left-associative
term    := "'" chars "'"                         LiteralExpression   (dataInline)
         | '$' path                              RefExpression       (dataRef; path is bare or "quoted")
         | '%' '"' template '"' '(' bind (',' bind)* ')'   InterpolationExpression
         | '?' scheme '.' property '(' expr ')'  LookupExpression    (lookupScheme, lookupProperty, lookupSource)
         | '(' expr ')'
         | identifier                            reference to an existing expression node
bind    := name '=' expr                          TemplateBinding     (placeholderName, placeholderExpression)
```

Examples and their decoded structure:

```
loanIri = 'http://ex.org/loan/'+$loanId
```
→ `loanIri` a `ConcatExpression`; `concatLeft loanIri_l` (a `LiteralExpression`, `dataInline "http://ex.org/loan/"`); `concatRight loanIri_r` (a `RefExpression`, `dataRef "loanId"`).

```
fullName = %"{l}, {f}"(l=$last,f=$first)
```
→ `fullName` a `InterpolationExpression`, `templateString "{l}, {f}"`, two `hasBinding` nodes `fullName_b1`, `fullName_b2` each a `TemplateBinding` with `placeholderName` and `placeholderExpression` (`fullName_b1_e` …).

```
lob = ?LobScheme.skos:notation($lineOfBusiness)
```
→ `lob` a `LookupExpression` with `lookupScheme LobScheme`, `lookupProperty skos:notation`, `lookupSource lob_s` (a `RefExpression`).

`a+b+c` decodes as `(a+b)+c`, i.e. a left-nested `ConcatExpression` chain, matching the monoid structure the ontology describes. The same expression syntax is accepted as the value of `pe`, `ls`, `cl` and `cr`, and inside the positional `hb` form.

### 10.2 SWRL compact payload

The payload for `gr` and `SW` is the compact rule syntax already used by `mork:swrlCompactSyntax`:

```
rule    := atoms '->' atoms
atoms   := atom ( '^' atom )*
atom    := Class '(' arg ')'                       swrl:ClassAtom
         | Prop '(' arg ',' arg ')'                swrl:IndividualPropertyAtom or swrl:DatavaluedPropertyAtom (chosen by the second argument: literal ⇒ datavalued)
         | 'swrlb:' name '(' arg (',' arg)* ')'    swrl:BuiltinAtom
         | 'sameAs' '(' arg ',' arg ')'            swrl:SameIndividualAtom
         | 'differentFrom' '(' arg ',' arg ')'     swrl:DifferentIndividualsAtom
         | Datatype '(' arg ')'                    swrl:DataRangeAtom (when the name resolves to an xsd: datatype)
arg     := '?' name                                variable
         | number | '"' chars '"'                  literal (integer, decimal, or string; typed strings as "…"^xsd:t)
         | identifier                              individual
```

Names resolve per §3.4, so `Applicant` is a local id, `:Applicant` uses the target prefix and `ex:Applicant` is a CURIE. Whitespace around `^` and `->` is permitted and SHOULD be omitted.

Decoding produces the standard SWRL RDF vocabulary: `swrl:body` and `swrl:head` are `swrl:AtomList`s (RDF collections); variables are IRIs minted as `<rule-iri>_v_<name>` and typed `swrl:Variable`; atom nodes and list cells are blank nodes numbered in document order.

### 10.3 SHACL compact payload

The payload for `gs` and `SH` is a subset of SHACL Core sufficient for the shapes a `ShapeTemplate` instantiates. It is deliberately not the W3C SHACL Compact Syntax, which spends tokens on prefixes and braces; anything outside this subset is written with `!T` lines against the minted shape IRI.

```
shape     := targets ( ';' clause )*
targets   := target ( ',' target )*
target    := ('c' | 'o' | 's' | 'n') IRI              sh:targetClass | sh:targetObjectsOf | sh:targetSubjectsOf | sh:targetNode
clause    := propshape
           | '!' severity                              sh:severity on the node shape (.viol .warn .info)
           | 'msg' string                              sh:message on the node shape
           | 'closed'                                  sh:closed true
           | 'ignore' IRI (',' IRI)*                   sh:ignoredProperties
           | 'nd' IRI                                  sh:node
propshape := path constraint*                          one sh:property with sh:path
path      := elem ( '/' elem )*                        sequence path (rdf:List) when more than one elem
elem      := IRI | '^' IRI                             inverse path
constraint:= 'dt' IRI                                  sh:datatype
           | 'cls' IRI                                 sh:class
           | 'nd' IRI                                  sh:node
           | 'nk' ('iri'|'bnode'|'lit'|'biri'|'blit'|'ilit')   sh:nodeKind
           | '[' n '..' m? ']'                         sh:minCount n, sh:maxCount m (m omitted ⇒ no max)
           | '>=' num | '<=' num | '>' num | '<' num   sh:minInclusive sh:maxInclusive sh:minExclusive sh:maxExclusive
           | 'in' '{' value (',' value)* '}'           sh:in
           | 're' string                               sh:pattern
           | 'len' '[' n '..' m ']'                    sh:minLength sh:maxLength
           | '=' value                                 sh:hasValue
           | 'eq' IRI | 'lt' IRI | 'lte' IRI | 'disj' IRI   sh:equals sh:lessThan sh:lessThanOrEquals sh:disjoint
           | '!' severity | 'msg' string | 'name' string
```

Example:

```
cs MS tg :Applicant pb [min N 700] pv [MappingAgent claude-opus-5 0.93 DRAFT] gs "c :Applicant; :hasCreditScore dt xsd:integer >=700 <=850 [1..1] !viol msg \"credit score out of range\""
```

decodes to a `sh:NodeShape` (`cs_gs1`) with `sh:targetClass ex:Applicant` and one `sh:property` (`cs_gs1_p1`) carrying `sh:path`, `sh:datatype`, `sh:minInclusive`, `sh:maxInclusive`, `sh:minCount`, `sh:maxCount`, `sh:severity` and `sh:message`. Property shapes are minted IRIs by default and blank nodes under `@opt bnode-shapes`.

### 10.4 RML compact payload

The payload for `gt` and `TM` covers the triples-map structure `mork2rml` emits: one logical source, one subject map, any number of predicate-object maps including parent joins.

```
tm      := 'src' string ( 'ref' ('json'|'csv'|'xml') )? ( 'it' string )?     rml:logicalSource: rml:source, rml:referenceFormulation (default json ⇒ ql:JSONPath), rml:iterator
           ';' 'sm' template ( 'cls' IRI )*                                   rr:subjectMap: rr:template, rr:class
           ( ';' pom )*
pom     := IRI objmap ( 'dt' IRI | 'lang' tag )?                             rr:predicateObjectMap with rr:predicate
objmap  := '=' string                                                         rr:objectMap [ rml:reference ]
         | ':' value                                                          rr:objectMap [ rr:constant ]  (IRI or literal)
         | '@' template                                                       rr:objectMap [ rr:template ]
         | '^' IRI ( '[' child '=' parent (',' child '=' parent)* ']' )?      rr:objectMap [ rr:parentTriplesMap ; rr:joinCondition [ rr:child ; rr:parent ] ]
```

Example:

```
tm_loan MT gt "src loan.json it $ ; sm http://ex.org/loan/{loanId} cls fin:Loan ; fin:principal ^tm_principal_gt1[loanId=loanId]"
```

Blank nodes are used for logical source, subject map, predicate-object maps and object maps, exactly as R2RML/RML conventionally does; the triples map itself is a minted IRI.

### 10.5 OWL class expressions

Used by `!` lines (§11). Precedence from loosest to tightest: `|` union, `&` intersection, `~` complement, restriction operators.

```
CE      := IE ( '|' IE )*                          owl:unionOf
IE      := AE ( '&' AE )*                          owl:intersectionOf
AE      := '~' AE                                  owl:complementOf
         | '(' CE ')'
         | '{' ind (',' ind)* '}'                  owl:oneOf
         | PE '>' AE                               owl:someValuesFrom
         | PE '<' AE                               owl:allValuesFrom
         | PE '=' value                            owl:hasValue
         | PE '@'                                  owl:hasSelf
         | PE '#' card ( '/' AE )?                 cardinality; '/' makes it qualified (owl:onClass / owl:onDataRange)
         | identifier                              named class or datatype
PE      := identifier | '^' identifier             property or its inverse (owl:inverseOf blank node)
card    := n | n '..' | '..' m | n '..' m          exactly n | min n | max m | min n and max m
```

The qualifier separator is `/` rather than `:` because `:Name` already denotes the default target prefix (§3.4); `p#1../:Loan` is a qualified cardinality over `fin:Loan` when `@t fin` is in force.

Data ranges use the same grammar with datatype identifiers and literal enumerations `{"a","b"}`; facet restrictions are written as `!T` triples.

Examples from `Mork.ttl`, as they would be written in MCN:

```
!C mork:Datum = mork:deferredMapping>mork:DataMapping < mork:DataMapping
!C mork:Objectification = mork:broadConceptRole#1../skos:Concept & mork:narrowConceptRole#1../skos:Concept < mork:DataConcept
!C mork:Attribute = (^mork:memberProperty>mork:Association | ^mork:memberProperty>mork:Entity) & mork:memberProperty#0/mork:Representation < mork:IdentifiableElement
!G mork:broaderApplicative>mork:DataMapping & ~mork:exactRBoxMatch>.T < .N
```

The last line is GCI Axiom 2.14a verbatim: `∃broaderApplicative.DataMapping ⊓ ¬∃exactRBoxMatch.⊤ ⊑ ⊥`.

---

## 11. Axiom lines

Axiom lines carry OWL content that is not an individual's property assertion. They make MCN complete for the T-Box of `Mork.ttl` itself and for the shadow declarations mapping data routinely needs (`Rep_Falcon_Eggs a owl:DatatypeProperty`).

| Line | Meaning |
|---|---|
| `!C id clause*` | `owl:Class` declaration. Clauses: `= CE` equivalentClass, `< CE` subClassOf, `! CE` disjointWith, or any `code value` pair (annotations). |
| `!O id clause*` | `owl:ObjectProperty`. Clauses: `< PE` subPropertyOf, `= PE` equivalentProperty, `inv PE` inverseOf, `dom CE`, `rng CE`, `+F` `+IF` `+S` `+AS` `+T` `+R` `+IR` characteristics (combinable: `+T+AS+IR`), `chain PE,PE,…` propertyChainAxiom, or `code value` pairs. |
| `!D id clause*` | `owl:DatatypeProperty`. Clauses as `!O` minus `inv`/`chain`, plus `rng` taking a data range. |
| `!A id clause*` | `owl:AnnotationProperty`. Clauses: `< id`, `dom`, `rng`, `code value` pairs. |
| `!I id (: types)? (code value)*` | `owl:NamedIndividual` outside any block: `: type+type` gives class assertions, where each type is a type code or any identifier (local ids allowed without `+`); the rest as a node line. |
| `!G CE < CE` | general class inclusion. |
| `!DC a,b,c` | `owl:AllDisjointClasses`. |
| `!DP a,b,c` | `owl:AllDisjointProperties`. |
| `!DI a,b,c` | `owl:AllDifferent`. |
| `!SA a,b,c` | pairwise `owl:sameAs`. |
| `!T s p o` | one raw triple. Each term is an identifier, `_:label` blank node, `<iri>` or quoted literal (with `@lang`/`^dt`). The escape hatch of last resort; a decoder MUST accept any triple this way. |

Ids in `!` lines are identifiers per §3.4, so external terms are declared with CURIEs (`!C fin:Loan`) and local terms with bare ids.

---

## 12. Identity, minting and determinism

### 12.1 Named nodes

A local id `x` under base `B` is the IRI `B + x`. The generator owns these names; the decoder never rewrites them.

### 12.2 Minted IRIs

Nodes the generator does not name receive deterministic IRIs derived from their parent and position:

| Node | IRI |
|---|---|
| inline node, *n*-th under code `k` on subject `S` (counting per subject and code, in document order) | `S` + `_` + `k` + *n* — e.g. `cs_shape_tg1`, `cs_shape_pb2` |
| artefact payload under `gs`/`gr`/`gt` on `S` | `S_gs1`, `S_gr1`, `S_gt1` |
| expression root from line `id = …` | `id` |
| concat operands of expression node `E` | `E_l`, `E_r` |
| interpolation binding *n* of `E`, and its expression | `E_bn`, `E_bn_e` |
| lookup source of `E` | `E_s` |
| SWRL variable `?x` of rule `R` | `R_v_x` |
| SHACL property shape *n* of node shape `N` | `N_pn` (unless `@opt bnode-shapes`) |

The separator `_` and the code names cannot collide with generator-chosen ids in practice; a generator that wants to be certain avoids ids ending in `_` + code + digits.

### 12.3 Blank nodes

Only OWL class expressions, RDF lists, SWRL atoms, R2RML term maps, `owl:Axiom` reifications and `!T` blank nodes are blank. The decoder labels them `_:b1`, `_:b2`, … (`_:a1`, … for axiom reifications) in the order they are created during the single left-to-right pass. Two decoders conforming to this specification therefore produce byte-identical canonical N-Triples for the same input, which is what makes `mork:inputHash` over decoded output meaningful.

### 12.4 Canonical output

The **canonical decoding** of a document is: the N-Triples serialisation of the decoded graph, one triple per line, sorted by the byte order of (subject, predicate, object) after blank-node labelling as in §12.3, with no trailing whitespace and a final newline. Hashes, diffs and cache keys SHOULD be computed over the canonical decoding rather than over the MCN text, since two MCN texts can denote the same graph (different line order, quoted versus bare literals, `M+MD` versus `MD`).

---

## 13. Decoding algorithm

The algorithm is presented as the decoder's obligations, in order. A conforming decoder may be implemented in any way that produces the same graph.

**D1. Line assembly.** Split into physical lines; drop blank lines and comment lines; join `;`-continuations. Number logical lines for error reporting.

**D2. Directive pass is not separate.** Directives take effect when reached. Initialise: prefix table = predeclared prefixes; base = none; target prefix = none; block = `%X`; options = {}.

**D3. For each logical line, dispatch on its first character.**

**D4. Block header** `%K id …`: resolve `id`; assert `id a owl:NamedIndividual`, `id a <scheme class>`; if `%R` and the next token is a reserved format token, assert `mork:format`; decode the remaining `code value` pairs with `id` as subject; set the current block context (membership property, scheme IRI, default type). `%X` clears the context.

**D5. Node line.**
1. Resolve the subject `S`. Assert `S a owl:NamedIndividual`.
2. If the second token is `=`, this is an expression line: decode the expression (§10.1) rooted at `S` and stop.
3. Determine the type list (§9.2). If empty and the block has a default type, use it. Assert `S a T` for each.
4. If the block has a membership property, assert `S <membership> <scheme>`.
5. If the first type is `SH`, `SW` or `TM` and the next token is a quoted string, decode it as a payload (§10.2–10.4) *onto `S`* (no minting).
6. Decode the remaining `code value-list` pairs (D6).

**D6. Property pair** `k v1{a1},v2{a2},…` on subject `S`:
1. Resolve `k` to a predicate `P` and kind (§4, §8.3). A CURIE is resolved directly.
2. For each value `v`:
   - inline `[…]` → create node `N` (§9.6, §12.2), assert its type(s), decode its contents with `N` as subject; object = `N`.
   - `k` is `tg` and `v` is a bare identifier → as if `[c v]`.
   - `k` ∈ {`gs`,`gr`,`gt`} and `v` is quoted → mint the artefact node, decode the payload onto it; object = that node; if `gr`, also assert `S mork:swrlCompactSyntax "v"`.
   - kind data → object = literal per §3.5.
   - otherwise → object = identifier per §3.4 (quoted strings in object-kind slots are an error).
3. Assert `S P object`.
4. If `k` ∈ {`gs`,`gr`,`gt`,`gc`}, assert the implied type (§5).
5. If an annotation `{…}` followed `v`: create `_:a`, assert `_:a a owl:Axiom`, `owl:annotatedSource S`, `owl:annotatedProperty P`, `owl:annotatedTarget object`, then decode the braces' pairs with `_:a` as subject.

**D7. Axiom line** per §11, using the class-expression parser of §10.5. `!T` asserts exactly one triple.

**D8. Options.** If `inv` is set, after the pass add `o P⁻ s` for every asserted `s P o` where `P` has a known `owl:inverseOf` in `Mork.ttl` (the decoder ships this table; it is not read from the data). If `strict` is set, run the lint rules of §14.2 and fail on any hit.

**D9. Output.** The decoded graph. For OWL tooling, serialise as Turtle/RDF-XML or hand the graph to an OWL API; the graph conforms to the OWL 2 RDF mapping so long as the generator has not used `!T` to write something outside OWL 2 DL (a decoder does not police that; the DL checker does).

### 13.1 Correspondence to OWL 2 structural axioms

For readers who prefer to think in functional syntax, the constructs MCN emits map as follows:

| MCN | OWL 2 axiom |
|---|---|
| node line subject, type `T` | `ClassAssertion(T s)` (plus `Declaration(NamedIndividual s)`) |
| object-kind pair | `ObjectPropertyAssertion(P s o)` |
| data-kind pair | `DataPropertyAssertion(P s "v"^^dt)` — or `AnnotationAssertion` when `P` is an annotation property in `Mork.ttl` (`n`, `nn`, `sd`, `lb`, `rc`, `ex`, `sco`, `al`, `en`, `hn`, `sa`, `db`, `dep`, `dcc`, `dct`, `dcd`, `dco`, `ud`, `sw`) |
| `{…}` on a pair | the same axiom with an annotation set |
| `!C id = CE` / `< CE` / `! CE` | `EquivalentClasses`, `SubClassOf`, `DisjointClasses` |
| `!O` clauses | `SubObjectPropertyOf`, `EquivalentObjectProperties`, `InverseObjectProperties`, `ObjectPropertyDomain/Range`, `Functional…`, `SubObjectPropertyOf(ObjectPropertyChain …)` |
| `!G` | `SubClassOf` between anonymous class expressions |
| `!DC` / `!DP` / `!DI` | `DisjointClasses`, `DisjointObjectProperties`, `DifferentIndividuals` |
| `@o`, `@i` | ontology IRI, `Import` |

Because MCN emits the RDF graph rather than structural axioms directly, the OWL 2 RDF-to-structural mapping performs this translation; the table only documents what to expect.

---

## 14. Validation

### 14.1 Decoder errors

A decoder MUST reject the document, naming the logical line, on:

- unknown directive, block kind, type code or property code (a CURIE with an unbound prefix is "unknown");
- a `:Local` token without `@t`, or a local id without `@b`;
- a quoted literal in an object-kind slot, or an inline node in a data-kind slot;
- an unresolvable polymorphic code;
- a positional inline form under a code with no positional table, or with too few slots;
- unbalanced quotes, brackets or braces; a `{…}` not directly attached to a value;
- an `@i` before `@o`; rebinding a predeclared prefix;
- a malformed payload (SWRL, SHACL, RML) or expression;
- a `!` line with an unknown kind or clause.

A decoder MUST NOT reject a document because a referenced IRI is not defined in it, because a GCI of `Mork.ttl` is violated, or because a mapping is incomplete. Those are graph-level judgements made after decoding.

### 14.2 Lint rules

Decoders SHOULD offer the following warnings (errors under `@opt strict`). Each mirrors an axiom in `Mork.ttl` and is checked on the decoded graph, so a model's mistakes surface before an OWL reasoner or SHACL engine is involved. They are heuristics, not the source of truth — [mork/shapes/constraints.ttl](../../mork/shapes/constraints.ttl) and the reasoner are.

| Lint | Mirrors |
|---|---|
| `MD` node without `df` | `Datum ≡ ∃deferredMapping.DataMapping`; Axiom 2.7a |
| `ap` without `xr` or `xi` on the same subject | GCI 2.14a |
| `ba` together with `cb` but no `xr`/`xi` | GCI 2.14b |
| `br` together with `cb` but neither `xa` nor `ba` | GCI 2.14d |
| `ss` without `ef` | GCI 5.10a |
| `MS`/`MR`/`MP` without `tg`, without at least one `pb`, or without `pv` | GenerativeMapping completeness GCIs (§5.6, §6.13.6) |
| `MT` without `pv` | TransformMapping completeness |
| `GT` node with none of `tcl`/`tob`/`tsb`/`tnd` | Axiom 5.6h-i |
| provenance node without `pc` and `pd` | Axiom 6.13.7c |
| both `gs` and `gr` on one subject | ShapeMapping/RuleMapping disjointness |
| both `cn` and `ap` pointing at the same node | the double-counting hazard documented in the loan example |
| a node in `%M` with `gv` beyond `.gD` but no `fi` | ADR-A22 production gate |
| `MU` with neither `hy` nor `mr` | `UncertainMapping` equivalence |

### 14.3 Downstream

After decoding, the graph goes through exactly the existing pipeline: OWL 2 DL profile check, SHACL validation with `mork/shapes/constraints.ttl` (including the mode-conditional `GenerativeMappingProductionGovernanceShape`), the parity and conformance gate (ADR-A28) and compilation (ADR-A19). MCN adds nothing to and removes nothing from that pipeline.

---

## 15. Encoding algorithm (RDF → MCN)

Decoding is the required direction. Encoding is specified so that existing Turtle can be placed in an LLM context at MCN cost (a mapping scheme fed back for revision, a taxonomy handed to a mapping agent, the MORK T-Box itself as a reference). Encoding is lossless for any graph; it is *compact* for MORK-shaped graphs.

**E1. Partition subjects.** Every named subject with `mork:mappingScheme`, `mork:conceptScheme`, `mork:representationScheme`, `mork:ontologicalScheme`, `mork:intentScheme` or `skos:inScheme` pointing at a `ConstraintScheme`/`RuleScheme` is assigned to that scheme's block (a subject with two memberships goes to the first in the order just given and carries the other explicitly). Everything else goes to `%X`.

**E2. Header.** Emit `@b` for the most common namespace among local subjects, `@p` for every other namespace used, `@t` for the most-referenced namespace in object position that is not the base, `@o`/`@i` from the `owl:Ontology` node.

**E3. Per block,** emit the header with the scheme's own properties, then one node line per subject:
- types: drop `owl:NamedIndividual`; drop the block default type if present; map the rest to type codes (unknown classes as CURIEs); omit a type implied by a payload code that will be emitted;
- properties: drop the membership property of the block; for each remaining predicate use its code, else a CURIE; group objects of the same predicate into a list; literals bare when their lexical form has no whitespace or delimiter and their datatype equals the code's default, else quoted with `^dt`/`@lang` as needed;
- inverse pairs: if both `s P o` and `o P⁻ s` are present, emit only the one whose subject is being written first and set `@opt inv` — or emit both (always correct, sometimes wasteful);
- `owl:Axiom` reifications whose source/property/target match an emitted pair become `{…}` on that value; unmatched reifications (the Zoo example's defect) are emitted as `!T` lines with `_:` labels;
- `TargetingSpec`, `ParameterBinding`, provenance and `TemplateBinding` nodes referenced from exactly one subject and having only the positional properties collapse into positional inline nodes; other single-parent helper nodes become typed inline nodes; multi-parent nodes stay as their own lines;
- `TemplateExpression` trees whose root is referenced from elsewhere become expression lines; `swrl:Imp`, `sh:NodeShape` and `rr:TriplesMap` graphs that fit the payload sub-notations become payload strings, otherwise `SW`/`SH`/`TM` node lines with `!T` for the rest.

**E4. T-Box.** `owl:Class`, property and GCI content is emitted as `!` lines, using §10.5 for class expressions; anything unrepresentable falls back to `!T`.

**E5. Verify.** Decode the result and check graph isomorphism with the input. An encoder that cannot make this check pass MUST fall back to `!T` for the offending triples rather than emit an approximation.

---

## 16. Worked examples

### 16.1 The loan mapping (repository example, complete)

MCN, 219 tokens, decoding to exactly the 40 triples of [loan_mapping.ttl](../../mork/examples/Mork2RML/loan_mapping.ttl):

```
@b <http://example.org/mapping#>
@p fin=<http://example.org/fin#>
@p qnt=<https://www.nebularis.org/neuro-semantic/lattice/quantification#>
@t fin
!D qnt:numericValue
!O qnt:onSpace
!O qnt:inUnit
!C :Loan
!O :principal dom :Loan rng qnt:Quantity
!I :LoanPrincipalSpace : qnt:ValueSpace
!I :USD : qnt:Unit
%R Scheme_Loan_Source .json id loan.json
%X
Concept_Loan C cs MS rs Scheme_Loan_Source p $
%M MS
Map_Loan_Class xt :Loan
Map_Loan M+MD f Concept_Loan df Map_Loan_Class c Loan r loanId
Map_Principal ap Map_Loan cb Map_Loan xi :principal c LoanPrincipal r loanId cn Map_PrincipalValue
Map_PrincipalValue cb Map_Principal xr qnt:numericValue r principal
```

Reading the mapping block: `Map_Loan_Class` is a `DataMapping` (block default) whose T-Box match is `fin:Loan`. `Map_Loan` is a `Datum` for `Concept_Loan`, deferred on the class mapping, individuated as `Loan` keyed by `loanId`. `Map_Principal` applies in the context of `Map_Loan` (`ap`), composes into it (`cb`), and reaches the quantity through the inverse of `fin:principal` (`xi`); its component `Map_PrincipalValue` asserts `qnt:numericValue` from the `principal` field. `M+MD` reproduces the original's redundant double typing; `MD` alone would be the normal spelling.

### 16.2 Uncertain mappings (repository example, excerpt)

From [UncertainMappings.ttl](../../mork/examples/Zoo/UncertainMappings.ttl), showing annotated matches, multi-valued matches to deferred definitions, `DeferredContext` yields and a shadow property declaration:

```
@b <http://www.nebularis.org/ontologies/UncertainMappings#>
@o <http://www.nebularis.org/ontologies/UncertainMappings>
@i <http://www.nebularis.org/ontologies/Mork>,<http://www.w3.org/2004/02/skos/core>,<http://www.nebularis.org/ontologies/Zoo>,<http://www.nebularis.org/ontologies/Petstore>
@p zoo=<http://www.nebularis.org/ontologies/Zoo#>
@p pets=<http://www.nebularis.org/ontologies/Petstore#>
@t zoo
!C OviparousBase = :laysEggs=t
!D Map_EggSize_Hypothesis rng xsd:string
%M Mappings
Map_EggSize MU hy Map_EggSize_Hypothesis lx :laysEggs{n "Close lexical match on conceptName 'EggSize' and DataProperty name 'eggSize'."} mr "Create a new datatype property in the output ontology to represent the size of Eggs." w 40
Map_EggSize_Hypothesis ad Map_Yield_Oviparous br .top f EggSize c #eggSize n "Mapping the concept 'EggSize' to a new data property 'eggSize' in the target ontology."
Map_Falcon_Hypothesis MD cn Map_Lays_Eggs df Map_Gen_Bird_Class{n "Falcon is a bird, birds lay eggs, however birds are not reptiles."} xt .dcd,Map_Yield_Oviparous,Map_Yield_Pet i #Falcon n "Hypothesis mapping for 'Falcon' is Pet, Bird."
Map_Lays_Eggs MD cn Map_Eggs xr :laysEggs v t n "Asserts the property `Falcon laysEggs true`"
Map_Oviparity MX bt .T tc OviparousBase c #Oviparous mr "Recommend introducing a notional construct to model reproductive modes, with 'Oviparity' as a member/individual."
Map_Yield_Oviparous MX y .dci c #Oviparous n "Yields the axiom <BaseIRI>#Oviparous at processing time."
```

The full encoding (1366 tokens against 2674 for the Turtle) decodes to a graph differing from the original in exactly three `owl:annotatedTarget` triples, where the original's reified annotations reference `mork:Map_Falcon_Hypothesis`, `mork:Map_Gen_Bird_Class` and `mork:Map_Platypus_Hypothesis` — IRIs that do not exist — instead of the local individuals. In MCN the `{…}` form cannot express that mistake.

### 16.3 A generative mapping with intent, provenance and artefacts

```
@u lattice-insure-o
%I Intents ju US ef 2026-01-01T00:00:00Z
i1 IN src "credit score at least 700" cf 0.93 op GreaterThanOrEqual cv 700 cd :creditScore
i2 IS src "in US states" sty State sin Include sv :US ri i1
%M MS md .prod mv 1.2
cs_shape MS im i1 tg :Applicant pb [min N 700] pv [MappingAgent claude-opus-5 0.93 DRAFT pd 2026-09-19T10:00:00Z] tl :RangeTemplate se .viol gv .gA fi [PI] gs "c :Applicant; :hasCreditScore dt xsd:integer >=700 <=850 [1..1]"
cs_rule MR im i1 tg [o :hasCreditScore aj :US] pb [threshold N 700] pv [MappingAgent claude-opus-5 0.9 DRAFT pd 2026-09-19T10:00:00Z] gr "Applicant(?a)^hasCreditScore(?a,?s)^swrlb:greaterThanOrEqual(?s,700)->Eligible(?a)"
v2 MS ss cs_shape ef 2026-10-01T00:00:00Z fi cs_shape_fi1 gv .gA tg :Applicant pb [min N 720] pv [reviewer _ _ APPROVED pd 2026-10-01T00:00:00Z] gs "c :Applicant; :hasCreditScore >=720"
loanIri = 'http://ex.org/loan/'+$loanId
```

Decoded, `cs_shape` is a `ShapeMapping` with `hasTargetingSpec cs_shape_tg1` (`sh:targetClass ex:Applicant`), `hasParameterBinding cs_shape_pb1` (`paramName "min"`, `paramType "Numeric"`, `paramValue 700`), `hasConstraintProvenance cs_shape_pv1` (creator, model id, confidence, review status, created), `hasShapeTemplate`, `hasSeverity sh:Violation`, `fnd:hasGovernanceState fnd:Active`, `fnd:hasIdentity cs_shape_fi1` (a `PersistentIdentity`), and `generatesShapeDefinition cs_shape_gs1` (a structured `sh:NodeShape`). `cs_rule` is a `RuleMapping` whose `generatesRuleDefinition` is a structured `swrl:Imp` with body and head atom lists and minted variables `cs_rule_gr1_v_a`, `cs_rule_gr1_v_s`; the compact text is retained as `swrlCompactSyntax`. `v2` supersedes `cs_shape`, shares its persistent identity and carries the `effectiveFrom` GCI 5.10a requires.

### 16.4 A representation scheme and taxonomy (from the `Mork.ttl` examples)

```
@b <http://www.nebularis.org/hyperthunk/Mapping#>
%R Scheme_Rep_Contracts .json
JS_Array_ContractingParties RY et JS_Elem_ContractingParties id contractingParties p contract.signatories.contractingParties ro DC_ContractingParties
JS_Elem_ContractingParties RN id "" mp JS_Attr_FirstName,JS_Attr_LastName p "contract.signatories.contractingParties[n]" ro DC_ContractingParties_Party
JS_Attr_FirstName RA id firstName
JS_Attr_LastName RA id lastName
%T Taxa_Contracts
DC_ContractingParties cid ContractingParties kn DC_ContractingParties_Party
DC_ContractingParties_Party cid Party
Concept_Contract_Signatories CO brl Rep_Contract nrl Rep_Signatories nn "Models the association between contract and signatories"
```

`id ""` is the empty identifier that marks an `AnonymousElement`; the empty string must be quoted, as must the path containing `[n]`, since `[` is a delimiter (§3.3).

### 16.5 The MORK T-Box in MCN

MCN can carry `Mork.ttl` itself, which is useful for placing the vocabulary's formal structure (though not its prose) in a model's context. Representative lines:

```
@b <http://www.nebularis.org/ontologies/Mork#>
@o <http://www.nebularis.org/ontologies/Mork>
@i <http://www.w3.org/2004/02/skos/core>,<http://www.w3.org/ns/shacl>,<http://www.w3.org/2003/11/swrl>,<https://www.nebularis.org/neuro-semantic/foundation/0.0.7>
!A mappingNote < skos:note lb "mapping note"
!O compositeNarrowerMapping < narrowerMapping lb "has composite narrower mapping"
!O compositeBroaderMapping < broaderMapping inv compositeNarrowerMapping
!O broaderApplicative < broaderMapping +AS
!O precedes +T+AS+IR dom DataMapping rng DataMapping
!O ^compositeBroaderMapping < precedes
!D weighting rng xsd:integer sd "confidence score out of 100"
!C DataMapping < skos:Concept & mappingScheme>MappingScheme
!C Datum = deferredMapping>DataMapping < DataMapping
!C UncertainMapping = hypothesisMapping>DataMapping | mappingRecommendation>xsd:string < DataMapping
!C ShapeMapping = DataMapping & generatesShapeDefinition>sh:Shape < GenerativeMapping
!C ShapeMapping < hasTargetingSpec>TargetingSpec & hasParameterBinding#1.. & hasConstraintProvenance>ConstraintProvenance
!DC OrderedCollection,SetListing,UnorderedCollection
!DP broaderMapping,closeMapping,deferredMapping,hypothesisMapping,narrowerMapping
!G broaderApplicative>DataMapping & ~exactRBoxMatch>.T < .N
!G broadABoxCategoryMatch>.T & compositeBroaderMapping>DataMapping & ~exactRBoxMatch>.T < .N
!I DraftMode : CompilationMode lb "draft mode"
```

`!O ^compositeBroaderMapping < precedes` is Axiom P1 (`SubObjectPropertyOf(ObjectInverseOf(compositeBroaderMapping) precedes)`), written with the inverse-property form of §10.5.

---

## 17. Authoring guidance for generators

These are recommendations for the system prompt of a mapping agent that emits MCN; they are not part of the notation.

1. **Ship the codebook, not the ontology.** §8 is about 2,500 tokens and is the entire vocabulary. `Mork.ttl` is ~45,000 tokens; its definitions and scope notes belong in a retrieval store the agent consults when it needs the *meaning* of a term, not in every prompt.
2. **Prefer structure to prose.** A `mappingNote` that restates what `lx :laysEggs` already says wastes tokens twice (in generation and in every later read). Notes should carry the *evidence* — the reasoning, the source excerpt, the alternative rejected.
3. **Name nodes, don't number them.** `Map_Loan` costs a few more tokens than `m3` but is far less likely to be mis-referenced three hundred tokens later.
4. **Type once.** Write `MD`, not `M+MD`; write `gs …` and let `MS` be implied unless a polymorphic code precedes it.
5. **Use profiles inside a deployment** (`@u`) and full headers when the MCN will be stored.
6. **One direction per inverse pair.** Emit `cn` from the parent or `cb` from the child, not both (§5).
7. **Emit the lint set.** Run §14.2 on every decode and feed the warnings back to the agent; they are cheap and catch the errors reasoners report expensively.
8. **Never escape what has a code.** A CURIE in code position is a signal that the codebook is incomplete; treat it as a change request against §8.

---

## 18. Conformance

| Level | Requirements |
|---|---|
| **MCN-Core** | §3, §5, §6 (except `@u`), §7, §8, §9 (except payload strings), §11 `!I` and `!T`, §12, §13 (except payloads), §14.1 |
| **MCN-Full** | Core plus §10.1 (expressions), §10.5 and all of §11 (axiom lines), `@u` profiles, `@opt inv` |
| **MCN-Artefacts** | Full plus §10.2 (SWRL), §10.3 (SHACL), §10.4 (RML) payloads |

A decoder states which level it implements. A generator targets a level and MUST NOT emit constructs above it. This document's examples in §16.1, §16.2 and §16.4 are Core; §16.3 and §16.5 are Artefacts.

Versioning of the notation follows the codebook: adding codes is a minor version; changing or removing the meaning of a code is a major version, and `@v` lets a decoder refuse a document written against a codebook it does not have.

---

## 19. Grammar

EBNF for the line-level syntax. Sub-notation grammars are in §10.

```
document    := line*
line        := directive | block | axiom | exprline | nodeline | comment | empty
comment     := '#' any*
directive   := '@b' IRI | '@o' IRI IRI? | '@i' IRI (',' IRI)* | '@p' NAME '=' IRI
             | '@t' NAME | '@u' NAME | '@opt' NAME+ | '@v' VERSION
block       := ('%M' | '%T' | '%R' | '%O' | '%I' | '%K' | '%U') ident (RESERVED)? pair*
             | '%X'
nodeline    := ident typelist? pair*
exprline    := ident '=' expr
typelist    := typetok ('+' typetok)*
typetok     := TYPECODE | CURIE | '+' ident
pair        := code valuelist
code        := PROPCODE | CURIE
valuelist   := value annotation? (',' value annotation?)*
value       := BARE | QUOTED ('@' LANG | '^' CURIE)? | IRI | inline
inline      := '[' ( '#' ident )? ( typelist pair* | positional ) ']'
positional  := slot+ pair*                       ; slot count fixed by the enclosing code
slot        := value | '_'
annotation  := '{' pair* '}'                     ; no whitespace before '{'
axiom       := '!C' ident cclause* | '!O' ident oclause* | '!D' ident dclause* | '!A' ident aclause*
             | '!I' ident (':' typelist)? pair* | '!G' CE '<' CE
             | '!DC' ident (',' ident)* | '!DP' ident (',' ident)* | '!DI' ident (',' ident)* | '!SA' ident (',' ident)*
             | '!T' term term term
cclause     := '=' CE | '<' CE | '!' CE | pair
oclause     := '<' PE | '=' PE | 'inv' PE | 'dom' CE | 'rng' CE | CHARS | 'chain' PE (',' PE)* | pair
dclause     := '<' ident | '=' ident | 'dom' CE | 'rng' CE | '+F' | pair
aclause     := '<' ident | 'dom' ident | 'rng' ident | pair
term        := ident | BNODE | IRI | QUOTED ('@' LANG | '^' CURIE)?
ident       := IRI | RESERVED | ':' NAME | CURIE | LOCALID
continuation: a physical line beginning with ';' is appended to the previous logical line

TYPECODE    := [A-Z][A-Z]?
PROPCODE    := [a-z][a-z]{0,2} | '>' | '<' | '~' | 's' [=~><-]
CHARS       := '+' ('F'|'IF'|'S'|'AS'|'T'|'R'|'IR') ('+' ('F'|'IF'|'S'|'AS'|'T'|'R'|'IR'))*
LOCALID     := [A-Za-z_][A-Za-z0-9_.-]*
CURIE       := NAME ':' [^ \t,{}\[\]]+
RESERVED    := '.' [A-Za-z]+
BNODE       := '_:' [A-Za-z0-9]+
IRI         := '<' [^>]* '>'
QUOTED      := '"' ( [^"\\] | '\\' ["\\ntu] )* '"'
BARE        := [^ \t,{}\[\]"<]+  [^ \t,{}\[\]]*
```

---

## 20. Open questions

- **Streaming.** Because a node line is self-contained given the block context, a decoder can process MCN incrementally as a model streams it and surface lint warnings mid-generation. Whether the agent loop should exploit that (stop-and-correct) is an architecture question for ADR-A25's bounded-completion mode.
- **A JSON envelope for tool use.** Structured-output APIs constrain models to JSON schemas; `mork_schemas.py` already exists for that path. An MCN document can be carried as a single string field in such a schema, which keeps token cost low while retaining the schema-level validation of the envelope; whether to retire the per-field Pydantic schema in favour of `{"mcn": "…"}` should be decided by measuring error rates, not assumed.
- **Numeric auto-ids.** A `@opt autoid` that lets a bare integer subject mint `B + "n" + digits` would shave tokens further; §17 argues against it on reliability grounds, but the measurement has not been made.
- **Codebook governance.** The codebook must track `Mork.ttl`. The practical mechanism is a machine-readable codebook file (the tables in §8 were generated from one) checked by a test that every declared term in `Mork.ttl` has a code, with the spec tables regenerated from the same file.
