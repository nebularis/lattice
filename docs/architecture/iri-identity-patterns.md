<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# IRI and Identity Patterns

**Status:** Proposed architecture patterns guide
**Purpose:** Framework-neutral identity and IRI design guidance
**Related:** [RDF & SPARQL Patterns Guide](rdf-sparql-patterns-guide.md), [ADR-A51](decisions/ADR-A51-iri-and-identity-policy.md), [ADR-A54](decisions/ADR-A54-dataset-topology.md), [ADR-A63](decisions/ADR-A63-project-vs-environment-scoping.md), [ADR-A68](decisions/ADR-A68-pii-and-erasure.md), [ADR-A78](decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md)
**Supersedes in scope:** [iri-policy.md](iri-policy.md). That document records one proposed platform profile. This guide is the complete pattern catalogue from which an adopter, or a future LATTICE platform profile, selects a compatible configuration.

## 1. Purpose and boundary

An IRI is not merely a string format. It can denote a domain entity, an aggregate, an authored artefact, a content state, an operational graph, a claim index entry, or an event occurrence. These things have different stability, privacy, ordering, and portability requirements. A single framework-mandated grammar cannot meet all of them without either leaking policy into adopter data or hiding material trade-offs.

LATTICE is a framework. It provides ontology assets, configuration vocabulary, compiler tooling, and runtime components. It does not own an adopter's existing identifiers, tenant model, projects, environments, graph-store layout, or public identifier policy. This document therefore defines patterns, compatibility rules, and a configuration target. It does not require an adopter to mint `urn:lattice:` IRIs, encode tenancy in an IRI, use a content hash, or adopt a particular graph naming scheme.

The framework has three responsibilities:

1. Explain the consequences of each identity pattern, including where it fails.
2. Make an adopter's selected combination explicit and machine-checkable.
3. Generate and validate only the minting behaviour configured for that deployment, without changing an adopted identifier behind its back.

A future extension to `ontology/persistence` is the configuration surface for these choices. Until then, no generic runtime component may assume an IRI grammar merely because it is convenient for a reference deployment.

## 2. Core distinctions

The following distinctions are non-negotiable. A configuration may choose different concrete forms, but it must not collapse the concepts.

| Concept | Question answered | Typical stability | Examples |
|---|---|---|---|
| Domain identity | What real or conceptual thing is this? | Long-lived | customer, policy, product, person |
| Authored lineage | Which enduring artefact family is this? | Long-lived | a mapping, policy, shape set, contract |
| Content revision | Which exact immutable content state is this? | Immutable and replayable | canonical RDF dataset digest |
| Operational graph locator | Where is a graph stored or materialised? | Deployment-local | a dataset graph name, cache graph |
| Aggregate root | Which unit is read or written consistently? | Domain-defined | order, case, claim, dossier |
| Component node | Which node belongs to an aggregate or artefact? | Depends on containment and lifecycle | order line, shape property, mapping step |
| Key claim | Which owner has claimed a normalized key? | Retirable, access-controlled | email uniqueness claim |
| Event occurrence | What happened, where, and at which position? | Immutable and append-only | approval, activation, receipt, write |
| Scope dimension | Under which organizational or operational boundary is this interpreted? | Independent of identity | authoring tenant, project, environment, dataset |

A string can name more than one of these only if the configuration explicitly declares the punning or locator convention. In particular, a graph name is not automatically a domain identity, and a content revision is not automatically an event occurrence.

### 2.1 Identity is not storage location

Changing the endpoint, dataset, repository, physical graph, shard, cache, or materialised projection must not silently change a domain entity or authored artefact IRI. A runtime graph locator can be deployment-local when its purpose is only to locate data. It must not be treated as a globally portable identifier unless its profile declares it so.

### 2.2 Identity is not classification

An IRI segment that looks like `customer`, `policy`, or `claim` is a minting namespace token, not an `rdf:type` assertion. OWL classification can be multiple, inferred, and later refactored. An implementation must never infer type from an IRI segment. A token may be permanently allocated for routing or readability, but it is not ontology semantics.

### 2.3 Distinct IRIs are not `owl:differentFrom`

RDF and OWL do not apply a unique-name assumption. A minting system can create two distinct IRIs that later resolve to the same real-world entity. The system must use an explicit merge or equivalence policy. It must not infer inequality merely from different IRI strings.

## 3. Configuration model

Identity configuration is a set of independently selectable dimensions. It follows the same design principle as the persistence profiles: a profile applies at a declared scope, the compiler resolves it deterministically, and a conflicting or incomplete configuration is a refusal rather than an unstated default.

| Dimension | Selection question | Examples |
|---|---|---|
| Naming authority | Who owns and may mint the identifier? | adopter, LATTICE subsystem, external registry, source system |
| Identifier status | Is the identifier adopted, derived, random, or content-addressed? | adopted IRI, UUID, hash, content digest |
| Resource role | What is being named? | entity, aggregate root, component, lineage, graph, event |
| Scope dimensions | Which dimensions participate in the name? | none, tenant, project, environment, source system |
| Namespace/base | Which absolute prefix owns the name? | adopter `https`, `urn:uuid:`, internal URN, lineage-relative |
| Encoding and normalization | How are key components represented? | restricted ASCII token, percent encoding, length-prefixed tuple, binary digest |
| Privacy class | May the name expose a natural key or correlation data? | public, internal, confidential, personal-data-prohibited |
| Lifecycle and merge | How are replacement, retirement, and erasure handled? | immutable, alias index, tombstone, deletion |
| Revision model | Is a state identified by its content or its position? | digest revision, event receipt, graph generation |
| Ordering model | Is an event sequence required and at what grain? | none, per aggregate, per lineage, per dataset |
| Store topology | How are graph locators constructed? | adopter-defined, template, dataset-local, portable |

The eventual vocabulary should support identity profiles at the same deployment-sensitive scopes already supported by `dal:GraphPatternScope`, `dal:NamespaceScope`, `dal:ClassScope`, and `dal:ShapeScope`. Identity profile resolution must not require a reasoner unless an adopter explicitly configures a reasoning-dependent scope.

## 4. Scope dimensions: authority, tenant, project, environment, and dataset

These dimensions often coexist. They must not be presumed interchangeable.

### 4.1 Naming authority

The naming authority is the party or system entitled to mint, maintain, and publish a class of names. It may be an adopter, an external master-data system, an authoring tenant, a registry, or a LATTICE runtime service.

An adopted identifier retains its original authority. A wrapper IRI or local key claim can index it, but the framework must not re-mint it merely to fit a configured local grammar.

### 4.2 Tenant

A tenant is an isolation, ownership, billing, or legal boundary. Some deployments have no tenants. Others have tenant-specific entity namespaces, dataset partitions, encryption keys, or key-claim registries. A tenant identifier is useful in an IRI only when the adopter requires the name itself to be tenant-local or globally disambiguated by tenant.

When encoded, a tenant token must be immutable and opaque. A name, domain, or personal identifier is unsuitable because tenants rename, merge, split, and can themselves reveal personal data.

A reserved shared-reference tenant is a possible profile choice for reference data owned outside ordinary tenants. Its token is deployment configuration, not a framework literal.

### 4.3 Project or authoring context

A project is normally an authoring boundary. It is appropriate in an authored-lineage IRI when two authoring teams require independent local-name allocation. It is not automatically appropriate for a runtime entity such as a customer, order, or case.

A useful authored-lineage profile is:

```text
{authoringBase}:{tenantToken}:{projectToken}:{familyToken}:{localToken}
```

Here the tenant denotes the authoring owner. The project token is immutable and opaque. Re-homing or forking the artefact creates a new lineage which records derivation from the original, instead of rewriting the original IRI. Cross-project use is by reference to the original lineage or revision. Cross-tenant activation keeps the source owner in the IRI and must be authorized as an explicit foreign reference.

### 4.4 Environment

An environment represents where a runtime occurrence happens: development, test, staging, production, a regional deployment, or another operational context. It is not inherently part of a domain entity or authored artefact.

Environment can safely participate in an identifier only when the resource itself is an environment-scoped occurrence or locator. For example, an activation event occurring in environment E is not the same occurrence as a promotion in environment F, even if both activate the same content revision. A runtime graph locator can similarly be environment-local.

Environment must not be inserted into a portable entity, lineage, content-revision, vocabulary, or shape IRI merely because the resource is deployed there. Cloning a dataset must not rewrite portable identity. Synthetic data needs a distinct tenant or other declared namespace, not an environment string substitution.

### 4.5 Dataset and graph store location

A dataset, repository, endpoint, or store shard is a deployment locator. It can be bound to `(tenant, environment)` or to an adopter-specific arrangement. It can be selected at the gateway, adapter, or runtime binding layer without appearing in any portable IRI.

If a graph IRI contains deployment components, it is a graph locator under a declared topology profile. It is not automatically a domain identity. Moving it requires an explicit migration or locator mapping, not a general IRI rewrite.

### 4.6 Scope selection matrix

| Named thing | Tenant normally relevant | Project normally relevant | Environment normally relevant | Dataset normally relevant |
|---|---:|---:|---:|---:|
| Public vocabulary term | No | No | No | No |
| External adopted entity | Only if source says so | No | No | No |
| Runtime entity | Sometimes | Rarely | No | No |
| Authored lineage | Often | Often | No | No |
| Content revision | Inherits lineage if embedded | Inherits lineage if embedded | No | No |
| Aggregate graph locator | Sometimes | Sometimes | Sometimes | Yes, as binding not identity |
| Key claim | Usually | Sometimes | Depends on uniqueness scope | Often, because claims are stored per dataset |
| Authoring approval event | Often | Often | No | Registry location only |
| Runtime activation event | Often | Indirectly through lineage | Yes | Yes |
| Write receipt | Depends on stream | Depends on stream | If runtime occurrence | Yes |

## 5. Resource-role patterns

### 5.1 Adopted or external identifiers

**Use when:** the source system, standards body, customer, or authoritative registry has already assigned the identifier.

**Pattern:** preserve the IRI or source identifier as the domain identity. A local mapping records provenance, authority, validation status, and any local graph location.

**Benefits:** no duplication of authority, easier integration, original references remain valid.

**Risks:** source may change its identifier policy, strings may not meet local grammar, and foreign IRI access may be unavailable offline.

**Rules:** do not normalize, lowercase, URL-escape, hash, or rewrite the adopted IRI. If a local stable form is required, mint a separate local identifier and record an explicit relationship selected by the adoption profile.

### 5.2 Runtime entity identity

A runtime entity exists independently of one aggregate write, one authoring project, or one environment. Use one of the minting patterns in Section 6. The entity namespace can be tenant-scoped, global, source-scoped, or externally adopted. The correct choice depends on the entity-resolution and data-sharing model.

A tenant-only base is often appropriate for runtime entities in a tenant data realm:

```text
{entityBase}/{namespaceToken}/...
```

This means cloned environments may contain the same IRI for the same entity. Independent environments can still mint separate `surrogate-claimed` UUIDs for the same person because their claim registries are not shared. That is acceptable only when the configuration declares that those datasets never merge or join by entity IRI.

### 5.3 Aggregate roots

An aggregate root is the unit of consistency selected by an adopter. It needs a stable identity for CAS routing, receipt chaining, and graph lookup. It may be the same IRI as a domain entity, or it may be a distinct technical resource that represents a bounded state machine.

The aggregate-root profile must state:

- whether the root uses an adopted, natural, derived, or surrogate identifier;
- whether the aggregate root has a dedicated named graph, a composite-property closure, or no aggregate boundary;
- which graph-locator template applies when a named graph boundary is selected;
- whether the root is the stream identity for ordering and receipts.

A graph locator derived from an aggregate root is not a reason to encode a revision, environment, or mutable classification into the root IRI.

### 5.4 Component nodes and contained parts

Component nodes include order lines, mapping rules, condition clauses, shape property declarations, and other nodes whose meaning depends on an aggregate or authored artefact.

| Pattern | Form | Best fit | Consequence |
|---|---|---|---|
| Direct identity | independent entity IRI | part has lifecycle and references outside parent | requires its own merge and authority policy |
| Parent-relative key | `{parentIri}/part/{encodedImmutableKey}` | component key is immutable within parent | moving the part to another parent creates a new IRI |
| Parent-local ordinal | `{parentIri}/part/{ordinal}` | immutable authored sequence, not reorderable | ordinal must never be reused or renumbered |
| Random child surrogate | `{parentIri}/part/{uuid4}` | identity is needed but no stable key exists | retry requires claim or external correlation |
| Blank node | RDF-local structure with no cross-request identity | sealed documents and no external reference | cannot be used by multi-request updates or stable provenance |

A component must not receive a semantic identity merely because it appears in a graph. If its parent is content-addressed, a component IRI that embeds a content digest will change when the parent changes. This is appropriate only for immutable revision-local nodes.

### 5.5 Composite and subgraph identity

A composite aggregate boundary is a set of triples selected by a SHACL-declared traversal. It is not automatically a new identity for every member. The `dal:CompositePropertyBoundary` profile decides write and read containment, while the identity profile decides whether members are independently addressable.

If a component is shared across two aggregates, it cannot belong to both composite closures under the same write model without an explicit ownership rule. Either it becomes an independent aggregate/entity, or one aggregate references it without owning it.

### 5.6 Authored lineages

An authored lineage identifies an enduring policy, mapping, shape set, contract, or other artefact family. It is distinct from its immutable revisions and from where a revision is activated.

An authored-lineage allocation claim should be keyed by the configured authoring namespace, family token, and local token. The registry records an owner. The allocator must use a concurrency mechanism appropriate for the backend: serializable isolation, P3 materialised write conflict, a single writer, or P6 external allocation. A structural string alone does not answer ownership conflict.

When the same authorized owner registers identical content for the same lineage, the configuration may define it as an idempotent no-op. A different owner attempting to use the lineage is an allocation conflict, even if the content bytes are identical.

### 5.7 Content revisions

A content revision identifies an immutable content state. It is suited to evidence, reproducible imports, cache keys, and idempotent registration. It is not a history event.

A portable profile can derive it as:

```text
{lineageIri}/rev/{contentSchemeToken}-{identityDigest}
```

The exact separator and base are configurable. What matters is that the scheme token and digest parameters are fixed for a declared profile. A future profile must not reinterpret existing identifiers.

A revert from state B to state A points a new event at existing revision A. It does not create another content identity for A, and content revisions must not be chained with `fnd:supersededBy` or an equivalent history relation.

### 5.8 Operational graph locators

Graph names can be immutable content-revision graphs, mutable aggregate graphs, append-only log buckets, staging graphs, projection generations, or temporary working graphs. Their grammar belongs to the selected topology profile, not to a global identity grammar.

A graph-locator profile needs to declare:

- whether a graph name is portable across datasets;
- the graph role and mutability;
- the mapping from a logical resource to a dataset binding;
- whether the graph is a source of truth, a sealed revision, or a materialised projection;
- retention and citation rules;
- whether a reader may name it directly or must resolve a pointer first.

### 5.9 Key claims

A key claim is a deterministic index resource for a normalized key. It is not the entity it points to. For sensitive keys, the claim IRI must use a keyed derivation and live in a restricted graph or external index.

Claims can be tenant-scoped, project-scoped, source-scoped, dataset-scoped, or global, depending on the uniqueness requirement. The configured scope must be part of the claim input, never merely an incidental graph location.

### 5.10 Event occurrences

An event occurrence names something that happened. It may be an authoring approval, publication, activation, runtime write receipt, domain event, deletion, or re-key operation. Event identity is not content identity.

There are at least three common event classes:

| Event class | Natural scope | Identity pattern | Notes |
|---|---|---|---|
| Authoring event | lineage and authoring registry | position under lineage, or registry UUID | approval or publication of a revision |
| Activation event | environment and activation binding | environment-qualified position or UUID | in-force revision changes per environment |
| Runtime receipt | aggregate or stream and dataset | `(epoch, seq[, opSeq])` occurrence IRI | CAS or append outcome |

The event profile must state whether the event IRI is position-derived or a random surrogate. Position-derived events make range scans and diagnostics easy but require a collision-safe scope including the stream or environment where needed. Random event UUIDs avoid grammar coupling but require indexed properties for ordering and range scans.

## 6. Entity minting patterns

### 6.1 Natural-key pattern

**Form:** `{base}/{namespaceToken}/{encodedKeyTuple}`.

**Use when:** the key is immutable forever, non-sensitive, and accepted as the actual identity by the adopting domain.

**Benefits:** deterministic, idempotent, readable, no lookup for key-to-IRI derivation.

**Costs:** changing a key changes identity. Natural keys can leak personal data, business secrets, or correlation identifiers. Case-sensitive source keys cannot be casually lowercased.

**Compatibility:** works with P0 deterministic identity and does not need an allocation registry. It can still use a P1 claim to detect source errors or constrain a broader business key.

### 6.2 Derived-hash pattern

**Form:** `{base}/{namespaceToken}/h/{digestPrefix}`.

**Use when:** an immutable, non-sensitive composite key has unsuitable characters or would be too long to expose directly.

**Benefits:** deterministic, fixed length, does not expose the literal key directly.

**Costs:** an unkeyed hash of a low-entropy personal or confidential key is reversible by enumeration and remains personal data. Hash algorithm, input encoding, scheme version, and width are all identity-bearing and must be fixed.

**Compatibility:** P0. A separate restricted key-to-IRI support index may be needed for diagnosis. The entity IRI must not be recomputed under a new scheme version and treated as the same identity.

### 6.3 Random surrogate pattern

**Form:** `{base}/{namespaceToken}/s/{uuid4}` or an adopter-selected opaque identifier.

**Use when:** the node has no stable natural identity or retry convergence is not required.

**Benefits:** no key disclosure, no time embedded by UUIDv4, stable once assigned.

**Costs:** independently repeated ingestion mints duplicates unless a separate correlation mechanism exists. UUIDv4 lacks text-index locality, so relational ledgers should store the UUID in a native UUID column where available.

**Prohibition:** do not silently substitute ULID or UUIDv7 when timestamps in identifiers are disallowed. These formats embed time. A profile may choose them only after explicitly accepting the privacy and correlation consequence.

### 6.4 Surrogate-claimed pattern

**Form:** opaque entity surrogate plus a keyed P1 claim for each natural or correlation key.

**Use when:** keys are mutable, sensitive, or unsuitable for the entity IRI. This is the recommended general-purpose pattern for systems that require private, durable entity identity and convergent ingestion.

**Benefits:** entity IRI stays stable through key changes. The claim provides deterministic lookup and uniqueness enforcement. The key can be private and access-controlled.

**Costs:** claim allocation needs P2 plus P3, P5, P6, or another backend-appropriate concurrency guarantee. Cross-environment convergence is absent unless the claim registry is shared or an external authority coordinates allocation.

**Key rotation:** rotation changes the claim derivation, not the entity IRI. The profile must declare a key identifier and claim scheme version. Rotate by writing a new claim under the new key, backfilling eligible records, and retaining an authorized mapping long enough to resolve old claims. A compromised key demands a rotation path. Never define a secret as unrotatable.

**Erasure:** tombstoning a claim preserves a pseudonymous personal-data artifact. A privacy profile may require physical deletion of the claim node and restricted audit evidence that contains no reversible or pseudonymous key derivative. This can break strict ownership monotonicity, so the configuration must declare the erasure precedence and reconciliation behavior.

### 6.5 External registry or allocator pattern

**Use when:** a source-of-truth registry, database unique index, identity provider, or external allocator owns the identifier.

**Benefits:** high contention and global coordination are handled where they are supported.

**Costs:** introduces an availability and reconciliation boundary. The RDF representation is a projection and must be idempotently repairable.

**Compatibility:** P6. The configuration must identify the authoritative allocator and failure behavior. An external allocation result must be represented as evidence, not replaced by a locally derived value.

### 6.6 Content-addressed entity pattern

**Use when:** the resource is immutable by definition, such as a statement bundle, immutable artefact, released vocabulary package, or fully sealed snapshot.

**Benefits:** deduplicates identical content, supports verification and caching.

**Costs:** unsuitable for mutable domain entities. References to a changed state must target a new content identity, which is why a stable lineage or domain identity is commonly paired with it.

### 6.7 Comparison

| Pattern | Deterministic | Key can change | Suitable for PII key | Re-ingestion converges | Needs claim or registry |
|---|---:|---:|---:|---:|---:|
| Natural key | Yes | No | No | Yes | No |
| Derived hash | Yes | No | No, if unkeyed | Yes | No |
| Random surrogate | No | Yes | Yes | No | No |
| Surrogate-claimed | Entity: no, claim: yes | Yes | Yes | Yes | Yes |
| External registry | Depends | Depends | Depends | Yes if registry available | External |
| Content-addressed | Yes | Not applicable | Only if content permits | Yes | Registration verification |

## 7. Encoding, grammar, and normalization

A profile that derives an identifier from components must specify bytes, not only illustrative strings. Two independent implementations must derive the same result for the same profile.

### 7.1 Component token pattern

For structural components such as tenant tokens, project tokens, family tokens, namespace tokens, and local allocation names, the conservative portable profile is ASCII lowercase `[a-z0-9-]+`, with a declared maximum length. It avoids ambiguity around `:`, `/`, `?`, `#`, percent encoding, Unicode normalization, and Turtle prefixed-name escaping.

A profile that permits a wider component alphabet must state:

- Unicode normalization form, normally NFC;
- whether case is significant;
- percent-encoding production and parsing rules;
- uppercase hexadecimal for percent escapes;
- rejection of percent encoding for unreserved characters;
- segment delimiters and maximum encoded length.

Lowercasing is not a generic solution. It can merge source keys that are case-sensitive. Only lower or casefold a key when the configured normalization pipeline explicitly establishes that equivalence for that constraint.

### 7.2 Tuple encoding pattern

Delimited concatenation is unsafe. `("a|b", "c")` and `("a", "b|c")` must not produce the same bytes.

A portable tuple encoding is UTF-8 length-prefixing:

```text
enc([c1, c2, ...]) = decimal-byte-length(c1) ":" c1 decimal-byte-length(c2) ":" c2 ...
```

The number is the byte length of the normalized UTF-8 component. The parser reads exactly that many bytes before reading the next length. There is no delimiter ambiguity. A profile can select a different self-delimiting encoding, such as canonical CBOR, but must name its version and byte order.

`urlsafe(keyTuple)` is not an algorithm. A profile must select either restricted-token encoding, percent encoding, base64url of a canonical tuple encoding, or another reversible scheme. A nonreversible digest is a different pattern and must not be described as URL-safe tuple encoding.

### 7.3 Key normalization pattern

Each uniqueness or derived-identity constraint declares a frozen, versioned normalization pipeline. The write path, audit, backfill, and claim issuer use the same pipeline.

A Unicode-aware baseline for human text is:

```text
NFKC(strip-default-ignorable(NFKC(input)).casefold())
```

This is only a candidate. Email local parts, identifiers, legal names, and product codes have domain-specific case and whitespace semantics. The profile must state each transformation and may choose no case transformation at all.

Use the Unicode `Default_Ignorable_Code_Point` property rather than a hand-maintained subset. The implementation must version the Unicode data source used by the pipeline or otherwise demonstrate stable behavior across supported runtimes.

### 7.4 Digest derivation pattern

A hash-derived identifier profile must specify all of:

- hash function, for example `SHA-256`;
- input bytes, including literals such as a scheme label and separators;
- tuple encoding and normalization pipeline version;
- output encoding, for example lowercase hexadecimal or unpadded RFC 4648 base32;
- exact output width in bits and characters;
- whether the full digest is retained for verification.

For example:

```text
SHA-256(UTF-8("iri-v1|" + namespaceToken + "|" + enc(normalizedTuple)))
```

A 128-bit, lowercase-hex prefix is exactly 32 characters. "At least 128 bits" is not a valid interoperable rule because it allows different implementations to mint different IRIs. A profile either fixes its width or defines a versioned transition.

### 7.5 Canonical lexical form

A profile must state whether the canonical lexical form applies to the whole generated IRI or only to structural components. The safe default is:

- scheme and NID use lowercase;
- generated structural tokens use the configured token normalization;
- hexadecimal digests use lowercase;
- percent escapes use uppercase hexadecimal;
- opaque source keys retain the case and bytes established by their own encoding profile.

No generated IRI may rely on relative reference resolution against a URN base. Store and compare the full absolute IRI.

## 8. Content-addressed revision patterns

### 8.1 Exact-RDF-term hashing

**Rule:** apply RDFC-1.0 to the dataset and hash the resulting canonical N-Quads bytes without semantic or literal value normalization.

**Benefits:** the hashed graph is exactly the graph stored. RDF terms such as `"1"^^xsd:integer` and `"01"^^xsd:integer` remain distinct, which preserves content-addressing integrity.

**Costs:** semantically equivalent lexical forms do not deduplicate. Producers must normalize before writing if they want equivalence.

This is the simplest and safest default for a content-addressed storage profile.

### 8.2 Canonicalize-on-write hashing

**Rule:** canonicalize selected lexical forms before storage, then apply RDFC-1.0 and hash the canonical stored dataset.

**Benefits:** selected syntactic variants converge to one stored content state.

**Costs:** canonicalization becomes a write-time semantic policy. It must fully define each affected datatype, language-tag case, date and time zone behavior, numeric forms, error handling, and provenance of the transformation. A system must not canonicalize only for hashing while storing the original RDF terms, because two different stored graphs would share one content IRI.

### 8.3 Self-reference pattern

A content revision may occur inside its own graph, for example as an ontology `owl:versionIRI` or provenance value. Directly hashing the final IRI is circular.

A profile can either:

1. disallow self-referential identifier triples in hashed payload;
2. exclude a declared header subgraph from content identity; or
3. replace exact self references with a fixed placeholder before canonicalization and hashing.

The chosen rule must identify every substituted position. It must also state how an `owl:Ontology` IRI and `owl:versionIRI` relate to the lineage and content revision: they can be equal by convention, explicitly linked, or deliberately distinct. The implementation must not infer this relationship from string prefix alone.

### 8.4 Complexity and blank-node cost

RDFC-1.0 canonicalization of adversarial blank-node graphs can be expensive. A profile must declare a work budget and behavior on exhaustion, normally rejection with a machine-readable diagnostic. A legitimate large artefact must either remain within the declared budget, use pre-ingestion skolemization, or select a profile designed for chunking or Merkle hashing.

A Merkle or chunked hash is a separate content identity algorithm. It must declare chunk boundaries, ordering, tree fanout, empty-node behavior, and verification procedure. It must not be represented as an ordinary RDFC digest.

### 8.5 Registration verification

A truncated digest in an IRI is not sufficient collision protection. On re-registering an existing content revision IRI, compare a stored full verification digest and reject a mismatch. This is an O(1) assertion.

## 9. Blank nodes, skolemization, and RDF 1.2 alternatives

Blank nodes are scoped to an RDF serialization or dataset operation. They cannot reliably be targeted by a later request, used as stable provenance subjects, or merged across independently produced graphs. Select one pattern per resource role.

### 9.1 Retained blank-node pattern

**Use when:** a graph is sealed, no external reference or multi-request update is required, and canonicalization can safely handle the graph.

**Benefits:** faithful RDF modeling with no artificial identifier.

**Costs:** no stable external identity, expensive canonicalization for some graphs, and no direct update addressing.

### 9.2 Source-local deterministic skolem pattern

**Use when:** the source exposes a stable record identifier plus an immutable path or local key.

**Form:** a derived-hash or natural-key identity from the source authority, source record identifier, path, and selected scheme version.

**Benefits:** stable across re-ingestion and graph edits. Avoids canonical-label churn.

**Costs:** the source-local key can be personal or confidential, so use the privacy-appropriate entity pattern. A path must be treated as a versioned source-model contract.

### 9.3 Random skolem surrogate pattern

**Use when:** a node needs a persistent IRI but has no stable key and does not need independent re-ingestion convergence.

**Form:** UUIDv4 or another configured random surrogate, ideally recorded with ingestion provenance.

**Benefits:** simple and avoids canonical-label circularity.

**Costs:** retries need a transaction claim or retained allocation mapping to avoid duplicate nodes.

### 9.4 Revision-local canonical-label pattern

**Use when:** a node only needs an address inside one immutable content revision.

**Form:** `{contentRevisionIri}/bnode/{canonicalLabel}` after the content revision has been determined by a non-circular procedure.

**Benefits:** deterministic for a sealed graph revision, useful for diagnostics and generated views.

**Costs:** labels recur across graphs and change when the graph changes. These are not durable entity identities. Do not use them for nodes intended to be updated across revisions.

**Ordering rule:** if canonical labels are used, first establish the immutable revision identity by a declared hash procedure that does not depend on the eventual skolem IRI, then generate revision-local display or access IRIs. Never replace blank nodes with labels before a hash if the labels themselves depend on that hash.

### 9.5 Triple terms and annotations

For statement-level annotations, RDF 1.2 triple terms can avoid inventing a reified node. Use only where the selected store capability and serialization toolchain support them. A triple term is not a substitute for an entity identity when the annotated assertion needs independent lifecycle, provenance, or access control.

## 10. Aggregates, graphs, CAS, ordering, and receipt crosswalk

Identity choices must fit the RDF and SPARQL patterns selected for persistence. The following crosswalk is normative guidance for configuration validation.

| Identity pattern | CAS and aggregate implication | Ordering implication | Receipt implication | Primary hazard |
|---|---|---|---|---|
| Stable aggregate root | version row may key on root or graph locator | stream can be root | receipt targets root or graph | mutable root IRI breaks routing |
| Named graph boundary | graph locator may derive from root | per-aggregate stream natural | receipt names target graph | graph locator mistaken for portable entity |
| Composite property boundary | one root owns closure | stream is root, not each member | one receipt covers bounded update | shared component creates two owners |
| No boundary | value-based CAS only | choose a separate stream key | receipt must identify property-level operation | cannot safely whole-graph replace |
| Content revision | no mutable CAS on revision itself | no history order by revision | events point to revision | revert cycle if revisions are chained |
| Authoring lineage | CAS protects registry pointer | per-lineage authoring sequence possible | approval/publication events point to revision | lineage current confused with environment activation |
| Surrogate-claimed entity | claim write needs P2/P3/P5/P6 | entity events can stream by entity | receipt records claim and owner | key rotation or erasure unspecified |
| Position-derived event | CAS or append allocates position in transaction | requires epoch and fixed width | event IRI is receipt | collision if scope omits environment or stream |
| Random event | CAS still needs metadata position | query uses properties and indexes | receipt links UUID to position | no lexical range scan |

### 10.1 Content state versus occurrence history

Content revision IDs name states. Event IDs name occurrences. A history chain uses event relations such as `pat:prevRev` or a configured successor property. The event points to its resulting content revision. It must never use `fnd:supersededBy` between content revisions because A -> B -> A would create a cycle.

If the profile uses `pat:Revision`, it should declare `pat:Revision rdfs:subClassOf prov:Activity` or an equivalent alignment. It must not alternate between two unrelated event classes in different documents.

### 10.2 Fixed-width positions

A position-derived event IRI needs one exact width per profile when lexical ordering or prefix-range scans are relied on. For signed 64-bit sequences, 19 decimal digits is sufficient. A profile may select another width or a base encoding, but it must enforce the choice in validators and examples. A documentation-only distinction such as "16 for examples, 19 in production" is not valid for identity-bearing strings.

### 10.3 Epoch durability

An epoch protects occurrence identifiers across restore, rebuild, migration, re-key, or any rollback of an allocation counter. It is only safe if the post-restore writer cannot reuse an epoch from restored data.

Select one durable-epoch strategy:

| Pattern | Mechanism | Strength | Cost |
|---|---|---|---|
| External high-water mark | writer compares the dataset epoch with durable state outside the restored store | fail-safe | requires coordination store or restore service |
| Restore-controlled epoch | restore tooling allocates and records a new epoch before writers start | strong operational control | depends on runbook enforcement |
| Writer-start refusal | writer will not start until it sees a new externally acknowledged epoch | fail-safe | availability impact during recovery |
| Store-local epoch only | epoch stored only in restored dataset metadata | unsafe by itself | must not be selected for collision safety |

An as-of query across a restore boundary must state whether it is limited to one epoch, returns a stitched multi-epoch history, or reports the earlier segment as non-reproducible. It must not silently treat sequence numbers from distinct epochs as one continuous history.

### 10.4 Current pointers and activation bindings

A pointer is an RDF triple, not a graph alias. A pointer profile identifies the pointer subject, property, storage graph, concurrency guard, and retention rule.

There are two distinct patterns:

1. **Lineage latest-approved pointer:** an authoring registry points from a lineage to its latest approved or published content revision.
2. **Environment activation binding:** an environment-local binding points to the revision currently in force in that environment.

A single lineage-level `current` pointer must not stand for environment activation. Dev and production may activate different revisions. Readers resolve the appropriate pointer and payload in one snapshot or query, for example by reading a metadata graph and the target graph within the same transaction context.

Retention must never remove a target reachable from an active pointer or from a still-valid reader grace window. A materialised `current` graph is a full copy or projection and should be used only when its freshness, atomic promotion behavior, storage cost, and recovery behavior are explicitly accepted.

### 10.5 Detailed crosswalk to the RDF and SPARQL patterns

The identity profile compiler must treat the following relationships as explicit inputs and requirements. None may be inferred merely from an IRI prefix.

| RDF and SPARQL pattern | Identity and IRI consequence | Configuration or generated artifact |
|---|---|---|
| P0 deterministic IRI | An immutable, non-sensitive key can determine an entity, component, claim, or stream identity. The derivation bytes and scheme version are identity-bearing. | Natural-key or derived-hash strategy, tuple encoder, normalization pipeline, digest scheme, test vector |
| P1 key-claim registry | The claim is a distinct resource from its owner. Its scope determines whether a key is tenant, source, project, or global unique. | Claim namespace, key-scope dimensions, restricted graph or external-index binding, owner relation |
| P2 guarded write | An idempotent claim retry requires a stable claim IRI and a stable transaction or allocation correlation identifier. | Generated guarded operation, transaction-claim policy, resolve-after-unknown operation |
| P3 materialised write conflict | Concurrent allocations for the same or sharded claim space need a declared conflict subject. This is unrelated to the entity IRI itself. | Key-shard function, shard count, backend concurrency requirement |
| P4 functional-property upsert | Changing a key must atomically retire or replace the old claim and acquire the new claim. The stable entity IRI does not change under `surrogate-claimed`. | Mutable-key workflow, old-to-new claim mapping, retry and conflict behavior |
| P5 SHACL validation | A claim IRI gives a local node on which `sh:maxCount 1` can be enforced. SHACL does not turn an unconfigured identifier grammar into an identity scheme. | Claim shape, commit-validation requirement, audit fallback |
| P6 external allocator | The allocator result, not a local format preference, is authoritative. Generated RDF writes are projections and need idempotency. | Allocator binding, fencing or transaction semantics, reconciliation contract |
| P7 reconciliation | Duplicate identities need a merge policy. Sealed revisions are retained and aliases resolve at read time. | Duplicate scan, quarantine/merge policy, alias resolver and evidence model |
| O1 replay and sync | A resumable event IRI needs an unambiguous stream and collision-safe position. | Event scope, epoch policy, position width, cursor shape |
| O2 causal order | Aggregate or lineage identity supplies the stream affinity for `prevRev` or successor relations. | Stream-key derivation, event-chain relation, fork audit |
| O3 valid-time order | A valid-time fact must not derive identity from commit position unless the domain declares that relationship. | Fact identity or n-ary relation pattern, valid-time datatype and comparator |
| O4 as-of read | Content revisions, event positions, and graph locators must be separately addressable. | Receipt model, retention rule, cross-epoch as-of policy |
| O5 ordered collection | A component's domain ordering key is not an event sequence and must not be used as a mutable identity component unless immutable. | Component identity strategy, rank/index profile |
| S1 in-transaction counter | Position-derived occurrence identity can be minted only when allocation is in the same transaction as the event write. | Counter scope, transaction boundary, exact event IRI formatter |
| S2 keyset pagination | Cursor identity is a value position, not an IRI prefix. | Composite cursor schema using epoch, sequence, and optional operation sequence |
| S3 gap detection | Dense sequences require declared retention low-water marks. | Retention metadata and audit query binding |
| S4 head pointer | The head is a mutable pointer to an event or revision, never an alias graph. | Version-row location, pointer property, CAS guard |
| S5 valid-time ordering | Event position supplies a stable tie-breaker, not domain-time semantics. | Query planner ordering rule |
| S6 as-of replay | Event and delta graph identities must identify one target and one position. | Patch-log graph template, target relation, epoch-aware replay constraint |
| S7 hybrid logical clock | HLC may label an event but is not a dense identity or uniqueness source. | HLC property and optional event suffix, never a replacement for epoch/sequence when completeness is required |
| S8 external sequencer | External `(epoch, offset)` can form a position-derived event identity if its retention and reset behavior are declared. | Sequencer authority, offset grammar, epoch ownership |
| CAS guarded replace | Aggregate root or graph locator supplies a stable mutation target. | Boundary profile and expected-version parameter binding |
| Txn-claim outcome resolution | A receipt IRI alone cannot prove that this caller's request applied. | Client transaction identifier policy and resolver API |
| Receipt-only model | Event identity is available for audit, but content or graph history cannot be reconstructed from it. | Receipt relation set and retention policy |
| Patch-log model | Delta graph locators must be immutable and event-specific. | Add/delete graph templates, target, asserts/retracts relations |
| Snapshot-per-revision model | A content revision can name a sealed snapshot or map to one explicitly. | Snapshot locator template, content verification, retention and citation policy |
| QP1 prepared queries | User-controlled identity components are values or validated templates, never concatenated into SPARQL text. | Typed identifier parameters and formatter library |
| QP2 time-agnostic guards | Wall-clock values never decide identity, ordering, or content bytes. | Static lint rule and profile validation |
| QP3 cursors | Identifier scans and alias resolution must support bounded, explicit cursors. | Cursor contract and canonical ordering fields |
| QP4 determinism | Any derived identifier must have repeat and permutation test vectors across implementations. | Generated conformance fixtures |
| QP5 isolation verification | The configured claim and position strategies are valid only for stores whose observed behavior meets their requirements. | Capability requirement and TCK gate |

### 10.6 Runtime occurrence identifier choices

An authoring event and a runtime activation are different occurrences even when they reference the same lineage and content revision. Choose one of these patterns for runtime occurrences:

| Pattern | Form | Strength | Trade-off |
|---|---|---|---|
| Environment-qualified position | `{runtimeOccurrenceBase}:{environmentToken}/act/e{epoch}/{seq}` | readable and range-scannable; collision-safe across environments | environment becomes part of an occurrence identifier and must be immutable, opaque, and never rewritten |
| Stream-qualified position | `{streamIri}/evt/e{epoch}/{seq}` | compact where stream identity already includes the occurrence authority | collides if two independent environments can mint the same stream position |
| Random occurrence surrogate | `{eventBase}/s/{uuid4}` with environment, epoch, and position as properties | avoids environment in the string and avoids grammar coupling | queries need an index over properties; no lexical position scan |
| External event identifier | adopted producer event ID | preserves external authority | requires an authority and collision policy across sources |

The framework does not choose among these. A profile must choose one separately for authoring, activation, and write-receipt events.

## 11. Merge, alias, replacement, and erasure patterns

### 11.1 Read-time alias resolution

When two entity IRIs are resolved to one canonical entity, retain the alias-to-canonical relation in an alias index. Resolve it at read time.

**Benefits:** preserves sealed content revisions and avoids a system-wide cascade of re-hashing content merely because an entity merge occurred.

**Costs:** readers need an alias-resolution policy. Queries that require canonicalized results must request it explicitly or use a resolver layer.

### 11.2 Lazy rewrite

Rewrite an alias to the canonical IRI only when a mutable lineage or aggregate naturally receives its next revision. Never rewrite sealed content revisions solely to perform an entity merge.

### 11.3 `owl:sameAs` avoidance

`owl:sameAs` is strong, difficult to retract under reasoning, and can create expensive sameAs cliques. It is not the default operational merge mechanism. A profile may choose it only for genuinely logical identity with suitable reasoner and retraction semantics.

### 11.4 Replacement relation selection

A relation such as `fnd:replacedBy` must exist in the selected ontology or configuration vocabulary before use. If Foundation does not define it, the framework must not write it as though it were available. The profile can instead define an adopter relation with explicit direction, transitivity, revocability, and provenance rules.

### 11.5 Erasure precedence

Erasure can require deletion or crypto-shredding of personal data, including HMAC-derived key claims. A retention or immutability policy cannot overrule a legal erasure policy. The configuration must name which evidence survives, whether it is structurally anonymized, and how allocation or ownership reconciliation reacts when a claim is removed.

## 12. Topology, imports, and graph grammar

### 12.1 No global graph grammar

LATTICE must not force every adopter graph to use a framework URN. The topology profile selects graph naming templates for that deployment. Templates must be validated for injection safety, component encoding, and collision behavior, but may preserve an adopter's established scheme.

### 12.2 Import catalog pattern

Ontology imports resolve ontology IRIs, not storage graph locators. Any deployment that stores ontology revisions in internal graphs must provide an import catalog or resolver mapping ontology and version IRIs to retrievable documents or graph locations. The mapping is deployment metadata, not a replacement for ontology identity.

### 12.3 Explicit links, not prefix scans

Use explicit relationships such as `hasVersion`, `hasContentRevision`, `targets`, `materializes`, and `previousEvent` to traverse identity structures. Do not rely on `STRSTARTS` scans of IRI prefixes to find all revisions, events, or components. Prefix scans are a convenience for diagnostics, not a primary integrity mechanism.

### 12.4 Registry artifacts

An identity configuration needs registries or declarations for any closed token set it expects tooling to validate: namespace tokens, family tokens, allocated tenants, project identifiers, scope dimensions, content-hash schemes, and graph templates. These can be versioned RDF resources, declarative configuration, or an authoritative external registry. A prose statement that tokens are "registered" is insufficient.

## 13. Scenario profiles

The following are examples, not framework defaults.

### 13.1 Existing enterprise master data

- Adopt source-system entity IRIs or identifiers.
- Maintain local provenance and key claims only when a local uniqueness constraint is required.
- Use a source-local deterministic skolem pattern for imported nested records where source record ID plus path is stable.
- Keep graph locators deployment-specific.
- Do not re-mint identifiers to add tenant or environment segments.

### 13.2 Single-tenant application with one controlled store

- Choose a simple application base and opaque UUIDv4 entities.
- Use `surrogate-claimed` only for keys requiring lookup or uniqueness.
- Use per-aggregate graph templates and optional CAS/receipt patterns as selected by the persistence profile.
- Tenant scope may be absent.
- Environment can appear in deployment configuration and runtime occurrence IDs, not domain entity identities.

### 13.3 Multi-tenant shared-store SaaS

- Choose tenant-scoped entity and claim namespaces if tenant-local identity is intended.
- Declare whether claim registries are tenant-local or global.
- Bind tenant and environment to datasets or repositories through server-side access control.
- Use opaque immutable tenant tokens if included in portable identifiers.
- Do not assume a shared graph store makes graph name a security boundary.

### 13.4 Vendor-authored packs activated by customers

- Use an authoring lineage scoped to vendor authority and project where local allocation is required.
- Customer activation references the vendor content revision directly.
- Customer modifications fork into a customer lineage with `prov:wasDerivedFrom` or the configured derivation relation.
- Store an explicit `ActivationBinding` in the customer environment which materializes the source content revision.
- Never rewrite vendor lineage IRIs into customer tenant identifiers.

### 13.5 Immutable governed artefacts

- Use a stable lineage plus content-addressed revisions.
- Use a registry latest-approved pointer for authoring state.
- Use authoring events for approval and publication history.
- Configure exact-RDF-term hashing or canonicalize-on-write before any content is persisted.
- Store full verification digest and resolve self-reference by an explicit profile rule.

### 13.6 High-volume operational aggregates

- Use an aggregate-root identity with a named-graph or composite boundary profile.
- Select per-stream dense position only where replay completeness is required.
- Select `ReceiptOnly`, `PatchLog`, or `SnapshotPerRevision` based on replay and as-of requirements.
- Use environment-qualified activation and receipt occurrence identifiers if events leave the dataset.
- Keep entity merge handling at read time to avoid rewriting sealed snapshots.

### 13.7 Sensitive-person data with erasure obligations

- Use UUIDv4 `surrogate-claimed` entities.
- Put HMAC claims in a restricted store or graph, with declared key scope and rotation plan.
- Separate personal payload into per-subject graphs where required by the erasure design.
- Select physical deletion or crypto-shredding for claims and payload according to legal policy.
- Never use an unkeyed email, phone, national identifier, or low-entropy person-derived hash in a public or broadly replicated IRI.

## 14. Future `dal:` identity profile extension

This guide specifies the design target, not an immediate ontology change. A subsequent bounded slice may extend `ontology/persistence` with an identity dimension. It should be additive, independently scoped, and compiled into explicit minting plans.

### 14.1 Candidate configuration concepts

| Candidate concept | Purpose |
|---|---|
| `dal:IdentityProfile` | Composite profile for a resource role at one scope |
| `dal:IdentityStrategy` | Adopted, NaturalKey, DerivedHash, Surrogate, SurrogateClaimed, ContentAddressed |
| `dal:ResourceRole` | Entity, AggregateRoot, Component, Lineage, ContentRevision, GraphLocator, KeyClaim, EventOccurrence |
| `dal:NamingAuthority` | Authority and authority-specific base or resolver |
| `dal:ScopeDimension` | Tenant, Project, Environment, Dataset, SourceSystem, None |
| `dal:ComponentEncoding` | Restricted token, percent encoded, base64url tuple, canonical binary tuple |
| `dal:NormalizationPipeline` | Frozen pipeline reference and version |
| `dal:DigestScheme` | Function, input format, encoding, exact width, verification-digest policy |
| `dal:SkolemizationStrategy` | RetainBlankNode, SourceLocalDeterministic, RandomSurrogate, RevisionLocalCanonicalLabel, TripleTerm |
| `dal:EventIdentityStrategy` | PositionDerived, RandomOccurrence, ExternalEventId |
| `dal:AliasResolutionStrategy` | ReadTime, LazyRewrite, ExternalResolver |
| `dal:ErasurePolicy` | Tombstone, DeleteClaim, CryptoShred, retained evidence shape |

### 14.2 Compilation responsibilities

The compiler should:

1. Resolve one identity profile per target and resource role.
2. Refuse incompatible selections, such as a mutable-key strategy without alias policy, a position-derived event without epoch durability, or a derived hash without exact digest parameters.
3. Generate minting functions, validators, test vectors, claim templates, and structured metadata bindings.
4. Preserve adopted identifiers and emit adapters rather than transforming them.
5. Emit explicit requirements for store capabilities, allocation services, key management, and retention behavior.

The compiler must not infer a profile from a string prefix, ontology class name, or current storage location.

### 14.3 Validation requirements

A configured profile requires at least:

- golden test vectors for every digest, encoding, and normalization pipeline;
- property tests proving tuple encoding injectivity for generated inputs;
- determinism tests across supported runtimes and Unicode versions;
- collision verification tests for truncated content identifiers;
- concurrency tests for key-claim allocation at the declared enforcement level;
- restore and epoch tests for position-derived occurrence identifiers;
- privacy tests that reject prohibited data classes in generated identifiers;
- migration tests for key rotation, alias resolution, project forking, and erasure.

## 15. Composition rules and refusal conditions

The following combinations require explicit refusal or an additional selected pattern.

| Selection | Required companion | Refuse when absent |
|---|---|---|
| `natural-key` or `derived-hash` entity | immutable-key declaration and normalization pipeline | key can change or privacy class is sensitive |
| `surrogate` where re-ingestion must converge | claim, allocator, or durable correlation map | none selected |
| `surrogate-claimed` | claim scope, key scheme, rotation, erasure policy, enforcement level | any omitted |
| content-addressed revision | exact digest scheme, full verification digest, self-reference policy | any omitted |
| canonicalize-on-write hash | storage canonicalization contract | hash-only normalization |
| revision-local skolem | immutable revision identity and no cross-revision identity use | node is mutable or externally referenced |
| position-derived event | stream scope, epoch strategy, exact position width, allocation mechanism | any omitted |
| environment activation | environment binding and event identity strategy | lineage pointer used as activation state |
| named graph boundary | graph-locator template and dataset binding | graph name treated as portable entity without declaration |
| merge alias | existing replacement relation, read policy, retention policy | sealed revisions must be rewritten |

## 16. Migration and adoption sequence

1. Inventory existing identifier authorities and resource roles. Do not start from a desired string format.
2. Identify which identifiers are adopted and therefore outside LATTICE minting authority.
3. Select aggregate boundaries, concurrency, ordering, receipt, and topology through the persistence profile model.
4. Select an identity pattern independently for each resource role and deployment scope.
5. Define bytes for every derived identifier, including normalization, tuple encoding, digest scheme, and exact width.
6. Define privacy, key rotation, merge, erasure, and restore behavior before production data is written.
7. Generate test vectors and run cross-runtime conformance checks.
8. Introduce new identifiers only behind migration mappings. Never bulk-rewrite existing IRIs as a formatting exercise.

## 17. Open design work

This guide intentionally does not decide the following for every adopter:

- whether a public `https` identity, internal URN, or external scheme is appropriate;
- whether an unregistered URN NID is acceptable or a `tag:` URI or controlled HTTPS authority is required;
- the final namespace and Foundation alignment for the illustrative `pat:` vocabulary;
- a universal graph-name grammar;
- whether RDF 1.2 triple terms are supported by a selected store profile;
- the exact `dal:` vocabulary names and shapes for the future identity-profile extension.

These are configuration or follow-on ADR decisions, not defaults the framework should silently make.

## 18. Summary

Good identity design starts by asking what is being named and who owns that name. It then selects a narrowly suitable pattern for entities, aggregate roots, component nodes, lineages, content states, graph locators, claims, and occurrences. Tenancy, projects, environments, and datasets are independent dimensions, not interchangeable string segments.

LATTICE supplies the patterns, validation model, and future configuration surface. Adopters choose the compatible combination that matches their domains, stores, legal duties, and existing identifier authorities.
