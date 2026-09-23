<!-- SPDX-License-Identifier: MPL-2.0 -->

# Persistence Compiler

Design-time toolchain for the LATTICE persistence profile substrate (`ontology/persistence`), per [ADR-A78](../../docs/architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) and [ADR-A79](../../docs/architecture/decisions/ADR-A79-persistence-compiler-toolchain.md). Turns an adopter's `dal:` configuration into a canonical `dal:CompiledProfile` graph, and optionally that graph into portable SPARQL text. Requires no live backend and no store SPI anywhere in the pipeline.

Full design: [persistence-profile-substrate.md](../../docs/developer/sketches/persistence-profile-substrate.md) and [rdf-sparql-patterns-guide.md](../../docs/architecture/rdf-sparql-patterns-guide.md).

## Install

```bash
mise exec -- python -m pip install -e ./tools/persistence[test]
```

## Two stages, two subcommands

**`compile`** loads `ontology/persistence` graphs plus an adopter's applied ontology, resolves every discovered target, validates it, selects operations, and emits a `dal:CompiledProfile` graph in Turtle. It never produces SPARQL text, never reads a template body, and needs no live backend, so its output does not depend on knowing what backend, if any, will eventually run it.

```bash
python -m persistence compile \
    ontology/persistence/spec/persistence.ttl \
    path/to/your-config.ttl \
    [--capability-spec path/to/your-capability-spec.ttl] \
    --out compiled-profile.ttl
```

**`instantiate`** is entirely optional. It reads a compiled profile and the checked-in template library, and mixes each generated operation's parameters into its named template to produce generic, portable SPARQL text.

```bash
python -m persistence instantiate compiled-profile.ttl --out ./rq
```

**`export-recipes`** reads a compiled profile and writes each identity minting recipe it contains as a JSON file, for the [minting libraries](../../docs/architecture/decisions/ADR-A84-standalone-minting-libraries.md) or any implementation of the [identity minting specification](../../docs/architecture/identity-minting-specification.md).

```bash
python -m persistence export-recipes compiled-profile.ttl --out ./recipes
```

Neither subcommand assumes you will ever run the other, or run any further LATTICE component at all. An adopter who wants only the ontology and the generated SPARQL can run both once and walk away with the `.rq` files.

## What `compile` actually does

| Stage | Input | Output | Failure mode |
|---|---|---|---|
| Load | ontology graphs, an optional `dal:CapabilitySpec` | an in-memory RDF graph | malformed Turtle |
| Resolve | the loaded graph | one resolved profile per target, one value per dimension (`persistence.model.DIMENSIONS`), with provenance | `ProfileAmbiguityError` |
| Validate | resolved profiles | a diagnostics list | `CrossAxisViolation`, `BoundaryConflict`, `MissingBoundaryShapeError` |
| Select | validated profiles | one named template per generated operation | none — a lookup table |
| Emit | selected templates + reified parameter bindings | a `dal:CompiledProfile` graph | an encoder rejection (see below) |

Every one of these is a real, tested Python module: [`persistence.resolver`](src/persistence/resolver.py) (the precedence algorithm, sketch §3.4), [`persistence.scopes`](src/persistence/scopes.py) (scope matching and the `Target` = class + deployment model, sketch §3.4.3), [`persistence.boundary`](src/persistence/boundary.py) (walking a `dal:boundaryShape` closure, sketch §4.3), [`persistence.validator`](src/persistence/validator.py) (every cross-axis check in sketch §3.5 plus boundary conflicts in §4.6, each a named exception type), [`persistence.capability`](src/persistence/capability.py) (the requirement/spec/check triad, sketch §3.6), [`persistence.operations`](src/persistence/operations.py) (template selection), [`persistence.compiler`](src/persistence/compiler.py) (orchestration and RDF emission).

## Identity is resolved per resource role

A `dal:IdentityProfile` names exactly one `dal:ResourceRole`, and one class often needs a different minting strategy per role: an entity's own IRI may be a claimed surrogate while its event occurrences are position-derived. Each role is therefore its own dimension, `identity:<Role>` (for example `identity:EntityRole`), resolved per target by the same precedence algorithm as every other dimension, among the `dal:IdentityProfile` nodes naming that role. The winning node wins as a unit, so its digest scheme and event settings always come from the node whose strategy they qualify. A role no profile declares is absent from the compiled profile: there is no default identity strategy (ADR-A82).

Identity generates no SPARQL. For each resolved role the compiled profile records the strategy and the winning profile node, and a self-contained **minting recipe** (`dal:MintingRecipe`, built by [`persistence.recipes`](src/persistence/recipes.py), `identity-minting` M1). The recipe is stored as its RFC 8785 canonical JSON (a literal of datatype `rdf:JSON`) with a SHA-256 digest, and `export-recipes` writes it out unchanged. Building a recipe validates it: anything a recipe would lack is refused by name (`MintedIriTemplateRequired`, `KeyConstraintRequired`, `KeyConstraintNotApplicable`, `TuplePrefixRequired`, `ClaimedIdentityWithoutKey`, `ClaimSchemeIncomplete`, `SurrogateKindRequired`, `CallerSuppliedPatternRequired`, `PositionWidthsRequired`, `ContentAddressedMembersRequired`, `AcceptedPatternRequired`, `DigestFunctionUnsupported`, `NormalizePipelineRequired`, and others). A content-addressed recipe also raises a `ContentAddressedCallerObligations` warning, because its correctness rests on how the caller canonicalizes RDF (specification §7). Minting needs the normalization pipeline and, for claims, the HMAC secret, which live in the application (guide §6.1, §8.1). The compiler refuses a derived-hash or content-addressed identity without a well-formed digest scheme, a position-derived occurrence identity without a uniqueness witness or an occurrence-namespace derivation, and a claimed surrogate whose `dal:claimsConstraint` is missing, applies to another target, or has no complete claim scheme. It warns when position-derived occurrence identity runs under a row-level epoch guard or a store-local epoch.

## Privacy and erasure are resolved and checked

`dal:PrivacyProfile`'s three properties (`dal:privacyClass`, `dal:erasureStrategy`, `dal:erasurePrecedence`) each resolve as their own dimension, matching the extension-property style of Slice 2 rather than Slice 3's whole-node-wins identity model: this is a new profile class in the same shape as `dal:EpochProfile`, not a resource-role situation. `dal:ReceiptProfile`'s `dal:perSubjectScoped` resolves the same way. `dal:epochAuthority` is promoted out of `dal:epochGuardScope`'s extras into its own dimension for the identical reason Slice 2 gave every other extension property its own dimension: an extra is silently dropped if declared on a node other than the one that wins the dimension it used to ride on.

The compiler refuses two configurations, both raised as `CrossAxisViolation` because neither mirrored SHACL shape declares `sh:severity sh:Warning` (the SHACL default, `sh:Violation`, is a hard failure, not a discouraged trade-off):

- `dal:privacyClass dal:PersonalData` with `dal:erasureStrategy dal:NoErasure` (mirrors `dal:PersonalDataRequiresErasureShape`): there is no lawful erasure path.
- `dal:privacyClass dal:PersonalData` with a replay-capable receipt model (`dal:PatchLog`/`dal:SnapshotPerRevision`) and neither `dal:perSubjectScoped true` nor `dal:erasureStrategy dal:CryptoShred` (mirrors `dal:PersonalDataReceiptCompatibilityShape`): the delta or snapshot graphs are a second, immutable copy of the personal data that per-subject graph drop cannot reach. This is the first check in this compiler to join two dimensions from genuinely different profile classes rather than two properties of one profile class, and it runs on resolved values, so it also catches the two profiles declared on separate individuals that only share a `dal:appliesTo` scope, which the node-local SHACL shape's SPARQL join also catches but a node-local Python check could not.

`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding` and `dal:erasureReplayOnRestore` resolve as extras of `dal:epochAuthority` and are emitted, but carry no cross-axis check of their own yet: they inform the restore runbook (guide §24.4) and housekeeping (ADR-A80), not this compiler's generated SPARQL. `dal:erasurePrecedence` resolves and is emitted for the same reason `dal:namingAuthority` is (Slice 3): a declared, adopter-facing choice a runtime component reads, not something this compiler validates on its own.

## A `Target` is a class, plus a deployment when there is more than one

A class alone cannot distinguish "`beh:Behaviour` as lending deploys it" from "`beh:Behaviour` as credit deploys it" (sketch §3.4.3's worked conflict): that distinction lives in which graph the instances are written to, which is exactly what a `dal:GraphPatternScope` declares via `dal:coversClass`. `discover_targets()` therefore yields one `Target` per distinct `GraphPatternScope` deployment a class has, plus one unscoped/fallback target — a class with no graph-pattern deployment at all gets exactly one target. This is an implementation-level refinement not spelled out explicitly in the sketch's prose; see `persistence.scopes.Target`'s docstring for the full reasoning.

## Using the generated SPARQL directly

This section is for a caller that runs the instantiated `.rq` files without LATTICE's query layer. Everything the query layer would otherwise do for you is listed here.

### Three kinds of value

| Kind | Filled by | Syntax in the `.rq` file | Examples |
|---|---|---|---|
| Compile-time slot | `persistence instantiate`, from the compiled profile's parameter bindings | already rendered, nothing left | graph IRIs, shard number, composite property |
| Request-time slot | you, with any Mustache library, per request | `{{{payloadTriples}}}`, `{{{logGraphs}}}` | the payload, the registry's log buckets |
| SPARQL variable | you, as initial bindings (or a prepared query's parameters), per request | `$root`, `$epoch`, … | the target IRI, positions, txn id |

**Request-time slots** hold values that are neither known at compile time nor bindable as one SPARQL term: a set of triples, or a list of graph IRIs. Render them with a Mustache library, triple-brace (unescaped), before submitting the request. The values are trusted, already-serialised SPARQL text, so the trust boundary is yours: never place untrusted input in them without encoding it as RDF terms first. An instantiated operation contains no other `{{` or `}}` sequence, and an unrendered slot makes the request a syntax error, so a forgotten slot fails closed.

- `{{{payloadTriples}}}`: the aggregate's full new state as Turtle-style triples (no `GRAPH` wrapper, skolemized, no blank nodes). Used by `create-if-absent`, `cas-replace` and `unconditional-write`.
- `{{{logGraphs}}}`: the IRIs of every log bucket the family's registry lists, space-separated, each in `<…>`. Used by `gap-scan-audit`, `revision-multi-txn-audit` and `txn-multi-revision-audit`. When the family declares `dal:registryGraph`, those operations carry a `registryGraph` parameter binding naming the graph to read the bucket list from. The pinned-head graph `urn:g:txlog/pinned` is already in the query.

### SPARQL variables per operation

| Operation | Variables |
|---|---|
| `bootstrap-version-row` | `$target`, `$epoch` |
| `create-if-absent` | `$root`, `$epoch`, `$newRev`, `$txnId`, `$requestDigest` |
| `cas-replace` | `$root`, `$epoch`, `$expectedSeq`, `$nextSeq`, `$newRev`, `$txnId`, `$requestDigest`, and for the patch-log model `$assertGraph`, `$retractGraph` |
| `tombstone-delete` | `$root`, `$epoch`, `$expectedSeq`, `$nextSeq`, `$newRev`, `$txnId`, `$requestDigest`, `$cause`, `$actor` |
| `append` | `$stream`, `$epoch`, `$revBase`, `$txnId`, `$requestDigest`, `$event`, `$eventType`, `$opSeq`, `$occurredAt` |
| `cas-replace` (value guard) | `$root`, `$oldValue`, `$newValue` |
| `unconditional-write` | `$root` |
| `key-claim-write`, `key-claim-retire` | `$claim`, `$owner`, and `$now` for retire |
| audits | none |

- `$epoch` is the dataset epoch read at the start of the request, typed `xsd:long`. So are `$expectedSeq`, `$nextSeq` and `$opSeq`. An untyped integer is a different RDF term and never matches (guide Chapter 13).
- `$txnId` is the transaction claim IRI (`urn:txn:{id}`). Receipts record its string form in `pat:txn`.
- `$requestDigest` is the lower-case hex SHA-256 of the tuple-encoded operation kind, target, expected `seq` (empty for create and append) and the sorted canonical N-Triples lines of the skolemized payload and events (guide §15.2). It is recorded on the txn claim, and your confirmation read compares it.
- `$revBase` (append only) is the revision IRI prefix including the zero-padded epoch, as a string, for example `"urn:rev:orders/1/e0000000000000000003/"`. The template pads the sequence to 19 digits. For CAS, tombstone and create you mint `$newRev` yourself in the same format.
- `$claim` is the HMAC claim IRI you compute over the tuple-encoded version, constraint id, scope and normalized key (guide §6.1).

### Obligations the SPARQL cannot enforce for you

1. **Create the version row before the first write** where the compiled profile contains `bootstrap-version-row`. That is every append stream, and every aggregate declared `dal:firstWrite dal:PreCreatedRow`, which gets no `create-if-absent`. Run `bootstrap-version-row` when you allocate the aggregate or stream id, binding `$target` to the IRI you will later bind as `$root` or `$stream`. The first `cas-replace` then expects `seq 0`, and finds no head. Skipping this step makes every write a no-op that looks like a lost race.
2. **Confirm every write** with a read of the txn claim's `pat:rev` and `pat:requestDigest` on the primary, and classify the outcome as guide §15.2 describes. A `204` from the endpoint does not mean the guard matched.
3. **Treat every transport failure as unknown**: resend the identical request with the same `$txnId` and payload, then confirm.
4. **Keep txn claims at least as long as the longest redelivery horizon** before pruning them (guide §24.2).
5. **Quiesce writers when you bump the dataset epoch** (guide §24.4).

## Known limitations (first cut, honestly scoped)

- **`unconditional-write`** only knows how to target a `dal:NamedGraphBoundary`'s graph. A target combining `dal:ProvidedConcurrency`/`dal:LockingConcurrency` with `dal:CompositePropertyBoundary` or `dal:NoBoundary` will fail to render (a missing `graphPrefix` binding) until a second variant is added.
- **`cas-replace-composite-property`** uses only the *first* composite property found by walking a target's `dal:boundaryShape`, with `+` (one-or-more) traversal. A shape with several sibling composite properties at the same level needs a property-path alternation (`p1|p2|...`) this first cut does not yet generate.
- **`dal:EquivalentClassScope` matching** is a syntactic approximation (does the target class appear inside the equivalence expression's `owl:intersectionOf`), not full OWL entailment. No reasoner dependency is introduced anywhere in this compiler, by design (sketch non-goals).
- **The log-bucket month** (`urn:g:txlog/{month}`) is computed at request time via `NOW()`, inside the generated `WHERE` clause, not baked in as a compile-time constant — this differs from an earlier, since-corrected version of the worked example in the sketch, which would have hard-coded a single month into a template meant to be reused across many months.
- **Infrastructure graph IRIs are fixed constants, not per-deployment configurable.** `urn:g:dataset` (dataset epoch graph and node), `urn:g:txn`, `urn:g:keys`, `urn:g:txlog/` (log bucket prefix), `urn:g:txlog/pinned`, `urn:g:retention`, `urn:g:events/{class-local-name}/` and `urn:g:meta/{shard}` match `rdf-sparql-patterns-guide.md` §2.3. No `dal:` property names them yet.
- **`dal:epochGuardScope`** selects between a `-dataset-guard` template variant and the original for every row-writing operation: `create-if-absent`, `cas-replace` (named graph and composite property), `tombstone-delete`, `append` and `bootstrap-version-row`. The dataset-guard variants guard on the dataset epoch only and rebase the row's own `pat:epoch` on write, continuing `pat:seq` (guide §10.1). `unconditional-write` and `cas-replace-value-guard` write no version row, so they have no epoch guard.
- **Not generated:** the retention job (low-water marks, pinned-head copies, bucket drops) and the epoch bump belong to housekeeping (ADR-A80), not to this compiler. `pat:hlc` is not written by any template.
- **Declared shard counts are recorded, not applied.** `dal:txnShards`, `dal:logShards` and `dal:keyShards` resolve into the compiled profile, and a value above 1 raises a `ShardingNotHonoured` warning, because every template still writes one txn, keys and log-bucket graph.
- **`dal:firstWrite dal:AbsentRow` with `dal:CompositePropertyBoundary`** generates no create operation: there is no composite-boundary create template yet. `dal:PreCreatedRow` works for both boundaries.
- **`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding` and `dal:erasureReplayOnRestore`** (Slice 4) resolve and are emitted as extras of `dal:epochAuthority`, but no cross-axis check reads them yet: they describe the restore runbook (guide §24.4), which this compiler does not generate or execute.

## Development

```bash
mise exec -- python -m pytest tools/persistence/tests -v
```

The test suite includes:

- **`test_terms.py`** — the injection corpus (ADR-A79 point 5): adversarial IRIs and literals fed through every encoder and every checked-in template, parsed by `rdflib`'s own SPARQL parser to assert exactly one operation ever results.
- **`test_resolver.py`**, **`test_validator.py`**, **`test_capability.py`**, **`test_boundary.py`** — unit coverage for each module, including the lending/credit worked conflict from the sketch, reproduced as an executable test.
- **`test_determinism.py`** — compiling the same configuration twice (including with triples loaded in shuffled order) produces isomorphic output.
- **`test_compiler_integration.py`** — full compile → instantiate → parse round trips for every positive example fixture, `CompileError` assertions for every negative one, and SHACL self-validation of `ontology/persistence`'s own shapes against every fixture.
- **`test_template_alignment.py`** — the template contract from the post-3866b21 review: epoch rebase, request digests, optional heads, typed rows, key-claim graph, audits, and the request-time slot rules.
- **`test_slice_2_extensions.py`** — per-property resolution of the extension properties, baseline defaults, every Slice 2 check with a positive and negative case, `dal:firstWrite` and `dal:registryGraph` behaviour.
- **`test_slice_3_identity.py`** — role-qualified identity resolution, whole-node winners, no default role, emission, and every identity check with a positive and negative case.
- **`test_identity_minting_m1.py`** — the compiler reproduces the hand-authored anchor recipes of `contracts/identity/anchor-vectors.json` byte for byte; every recipe satisfies the published schema; digests are recomputed independently and invariant under triple order; emission, export, rotation, and one refusal per missing recipe member.
- **`test_slice_4_privacy.py`** — per-property resolution of `dal:PrivacyProfile` and `dal:perSubjectScoped`, `dal:epochAuthority`'s promotion out of `dal:epochGuardScope`'s extras, and both privacy/erasure checks with a positive and negative case, including the two profile classes declared on separate individuals.
- **`test_architecture.py`** — the Python equivalent of an ArchUnit rule: only `persistence.render` may import `chevron`, no wall-clock call exists in any resolution-critical module, and `chevron.render`'s template argument is never dynamically assembled.
