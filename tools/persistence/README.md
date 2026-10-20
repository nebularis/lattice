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

**`instantiate`** is entirely optional. It reads a compiled profile and the checked-in template library, and mixes each generated operation's parameters into its named template to produce generic, portable SPARQL text. It writes one directory per target, `<Class>` or `<Class>.<deployment scope>`, since every target has its own operations, the audits included, under the same names. `mise run build:persistence-execution` runs it over every example in `ontology/persistence/examples`, writing to `ontology/persistence/execution`, which is generated and ignored by git (the [Persistence README](../../ontology/persistence/README.md) §11.5).

```bash
python -m persistence instantiate compiled-profile.ttl --out ./rq
```

**`export-recipes`** reads a compiled profile and writes each identity minting recipe it contains as a JSON file, for the [minting libraries](../../docs/architecture/decisions/ADR-A84-standalone-minting-libraries.md) or any implementation of the [identity minting specification](../../docs/architecture/identity-minting-specification.md).

```bash
python -m persistence export-recipes compiled-profile.ttl --out ./recipes
```

Neither subcommand assumes you will ever run the other, or run any further LATTICE component at all. An adopter who wants only the ontology and the generated SPARQL can run both once and walk away with the `.rq` files.

**`hygiene`** runs the static checks of formal-methods track H, slice H1, over a configuration without compiling it. It exits 1 on a violation and 0 otherwise, printing warnings. So far it checks the prefix antichain: two `dal:GraphPatternScope` nodes with nested `dal:graphPrefix` values over a shared class are a violation (one instance would belong to two targets, and the resolver has no longest-prefix rule), and nested `dal:iriPrefix` values on `dal:NamespaceScope` nodes are a warning (the resolver ranks by `dal:priority`). Each finding names the scopes and a graph or resource IRI that both match. It also compiles the configuration and checks the SPARQL it generates, in [`persistence.templatecheck`](src/persistence/templatecheck.py). Every INSERT variable must be a `$parameter`, bound in every solution, or a reviewed allowance (S-3), and no template may contain a blank node (S-4). Implemented in [`persistence.hygiene`](src/persistence/hygiene.py).

```bash
python -m persistence hygiene \
    ontology/persistence/spec/persistence.ttl \
    path/to/your-config.ttl
```

**`witness`** checks that every refusal, warning, SHACL shape and always-on audit query has a fixture that triggers it, or is listed with a reason in [`tests/witnesses/known-gaps.txt`](tests/witnesses/known-gaps.txt). A rule nothing can trigger may be dead, and nothing would notice. An audit counts as witnessed only when a violating dataset (`tests/witnesses/audits/<audit>.violation.trig`) makes it return rows and a clean one makes it return none. It exits 1 on an unwitnessed rule, a listed gap that now has a witness, or an audit that misbehaves on its datasets. Add `--verbose` to see which fixture witnesses each rule. A fixture in `tests/witnesses/` named `refusal-X.ttl` or `warning-X.ttl` must trigger `X`. It may be a patch on a shipped example, with `# base: <example>.ttl` and `# remove: <subject> <predicate> [<object>]` lines before its own Turtle, and a `remove:` that matches nothing is an error. A `shape-X.ttl` must make shape `X` report, and a shape is witnessed only if some fixture also has data it applies to and accepts (an `ok-X.ttl` supplies one where no shipped example does), because a shape that reports on everything detects nothing. A file starting with `_` is a shared base, not a witness. Implemented in [`persistence.witness`](src/persistence/witness.py).

```bash
python -m persistence witness --verbose
```

**`gaps`** lists, for each compiled target, what the configuration declares that the generated SPARQL does not implement, and whose obligation each entry is: `unimplemented` (a register row is named), `caller` (the SPARQL assumes something it cannot enforce), or `housekeeping` (ADR-A80). It is informational and exits 0 once the configuration compiles, and 1 if it does not. It lists what is true of nearly every configuration, and a declaration the compiler cannot honour is not in it: that is a compile warning or a refusal, so a profile is never produced that quietly drops one. `--json` prints the report as data. Each rule lives in `persistence.gaps.RULES`, and a slice that closes a gap removes its rule there.

```bash
python -m persistence gaps \
    ontology/persistence/spec/persistence.ttl \
    path/to/your-config.ttl
```

## What `compile` actually does

| Stage | Input | Output | Failure mode |
|---|---|---|---|
| Load | ontology graphs, an optional `dal:CapabilitySpec` | an in-memory RDF graph | malformed Turtle |
| Resolve | the loaded graph | one resolved profile per target, one value per dimension (`persistence.model.DIMENSIONS`), with provenance | `ProfileAmbiguityError` |
| Validate | resolved profiles | a diagnostics list | `CrossAxisViolation`, `BoundaryConflict`, `MissingBoundaryShapeError` |
| Select | validated profiles | one named template per generated operation | none — a lookup table |
| Emit | selected templates + reified parameter bindings | a `dal:CompiledProfile` graph | an encoder rejection (see below) |

Every one of these is a real, tested Python module: [`persistence.resolver`](src/persistence/resolver.py) (the precedence algorithm, sketch §3.4), [`persistence.scopes`](src/persistence/scopes.py) (scope matching and the `Target` = class + deployment model, sketch §3.4.3), [`persistence.boundary`](src/persistence/boundary.py) (walking a `dal:boundaryShape` closure, sketch §4.3), [`persistence.validator`](src/persistence/validator.py) (every cross-axis check in sketch §3.5 plus boundary conflicts in §4.6, each a named exception type), [`persistence.capability`](src/persistence/capability.py) (the requirement/spec/check triad, sketch §3.6), [`persistence.operations`](src/persistence/operations.py) (template selection), [`persistence.compiler`](src/persistence/compiler.py) (orchestration and RDF emission).

A property the compiler reads as single-valued, such as `dal:priority` or `dal:concurrencyProfile`, is read through [`persistence.functional`](src/persistence/functional.py). A subject that gives it two values is refused as `MultiValuedFunctionalProperty`, because the winner would otherwise depend on the order the triples were written in. A scope or profile that nothing refers to is never read, so it is not checked.

## Identity is resolved per resource role

A `dal:IdentityProfile` names exactly one `dal:ResourceRole`, and one class often needs a different minting strategy per role: an entity's own IRI may be a claimed surrogate while its event occurrences are position-derived. Each role is therefore its own dimension, `identity:<Role>` (for example `identity:EntityRole`), resolved per target by the same precedence algorithm as every other dimension, among the `dal:IdentityProfile` nodes naming that role. The winning node wins as a unit, so its digest scheme and event settings always come from the node whose strategy they qualify. A role no profile declares is absent from the compiled profile: there is no default identity strategy (ADR-A82).

Identity generates no SPARQL. For each resolved role the compiled profile records the strategy and the winning profile node, and a self-contained **minting recipe** (`dal:MintingRecipe`, built by [`persistence.recipes`](src/persistence/recipes.py), `identity-minting` M1). The recipe is stored as its RFC 8785 canonical JSON (a literal of datatype `rdf:JSON`) with a SHA-256 digest, and `export-recipes` writes it out unchanged. Building a recipe validates it: anything a recipe would lack is refused by name (`MintedIriTemplateRequired`, `KeyConstraintRequired`, `KeyConstraintNotApplicable`, `TuplePrefixRequired`, `ClaimedIdentityWithoutKey`, `ClaimSchemeIncomplete`, `SurrogateKindRequired`, `CallerSuppliedPatternRequired`, `PositionWidthsRequired`, `ContentAddressedMembersRequired`, `AcceptedPatternRequired`, `DigestFunctionUnsupported`, `NormalizePipelineRequired`, and others). A content-addressed recipe also raises a `ContentAddressedCallerObligations` warning, because its correctness rests on how the caller canonicalizes RDF (specification §7). Minting needs the normalization pipeline and, for claims, the HMAC secret, which live in the application (guide §6.1, §8.1). The compiler refuses a derived-hash or content-addressed identity without a well-formed digest scheme, a position-derived occurrence identity without a uniqueness witness or an occurrence-namespace derivation, and a claimed surrogate whose `dal:claimsConstraint` is missing, applies to another target, or has no complete claim scheme. It warns when position-derived occurrence identity runs under a row-level epoch guard or a store-local epoch.

## Privacy and erasure are resolved and checked

`dal:PrivacyProfile`'s three properties (`dal:privacyClass`, `dal:erasureStrategy`, `dal:erasurePrecedence`) each resolve as their own dimension, matching the extension-property style of Slice 2 rather than Slice 3's whole-node-wins identity model: this is a new profile class in the same shape as `dal:EpochProfile`, not a resource-role situation. `dal:ReceiptProfile`'s `dal:perSubjectScoped` resolves the same way. `dal:epochAuthority` is promoted out of `dal:epochGuardScope`'s extras into its own dimension for the identical reason Slice 2 gave every other extension property its own dimension: an extra is silently dropped if declared on a node other than the one that wins the dimension it used to ride on.

The compiler refuses two configurations, both raised as `CrossAxisViolation` because neither mirrored SHACL shape declares `sh:severity sh:Warning` (the SHACL default, `sh:Violation`, is a hard failure, not a discouraged trade-off):

- `dal:privacyClass dal:PersonalData` with `dal:erasureStrategy dal:NoErasure` (mirrors `dal:PersonalDataRequiresErasureShape`): there is no lawful erasure path.
- `dal:privacyClass dal:PersonalData` with a replay-capable receipt model (`dal:PatchLog`/`dal:SnapshotPerRevision`) and neither `dal:perSubjectScoped true` nor `dal:erasureStrategy dal:CryptoShred` (mirrors `dal:PersonalDataReceiptCompatibilityShape`): the delta or snapshot graphs are a second, immutable copy of the personal data that per-subject graph drop cannot reach. This is the first check in this compiler to join two dimensions from genuinely different profile classes rather than two properties of one profile class, and it runs on resolved values, so it also catches the two profiles declared on separate individuals that only share a `dal:appliesTo` scope, which the node-local SHACL shape's SPARQL join also catches but a node-local Python check could not.

`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding` and `dal:erasureReplayOnRestore` resolve as extras of `dal:epochAuthority` and are emitted, but carry no cross-axis check of their own yet: they inform the restore runbook (guide §24.4) and housekeeping (ADR-A80), not this compiler's generated SPARQL. `dal:erasurePrecedence` resolves and is emitted for the same reason `dal:namingAuthority` is (Slice 3): a declared, adopter-facing choice a runtime component reads, not something this compiler validates on its own.

## Uniqueness violations select a reconciler, not a different guarded write

`dal:onViolation` (Reject/Merge/Quarantine) never changes the guarded write itself: `key-claim-write` always prevents the race at write time, regardless of policy. What it selects is which **reconciler** operation `select_operations()` generates for that constraint (guide §7.5, P7), since a bulk load, an administrative `LOAD`, or a restore can all create a duplicate the guarded write never saw. Undeclared `dal:onViolation` defaults to `dal:Reject`, the same explicit-baseline-default convention as every other dimension in this compiler.

| `dal:onViolation` | Template | Behaviour |
|---|---|---|
| `dal:Reject` (baseline default) | `key-claim-duplicate-audit.mustache` | Read-only: reports every over-claimed key, scoped to the one constraint |
| `dal:Merge` | `key-claim-merge-rewrite.mustache` | Records `dal:mergeRelation` (required — `MergeRelationRequired`) from every non-canonical owner to the lexicographically lowest owner IRI. Idempotent. Records the merge edge only: rewriting payload references, and retiring the losing claim, stay with the caller |
| `dal:Quarantine` | `key-claim-quarantine.mustache` | Copies every over-claimed key's owners into `urn:g:key-quarantine` with a timestamp. Idempotent per owner. Deletes nothing |

`dal:ClaimScheme` rotation (guide §6.1) is a second, independent axis, resolved as `dualClaimScheme` (true when a constraint's active schemes — state `dal:Accepting` or `dal:Dual` — number exactly two, mirroring `persistence.recipes`' own filter rather than a second, potentially divergent rule). It selects the guarded write's own template: `key-claim-write-dual.mustache` guards and inserts both scheme versions' claim IRIs for the same owner in one operation, so no window opens where the key is claimed under only one version while the secret rotates. `key-claim-retire.mustache` is unaffected either way: retiring is always per claim IRI, one version at a time.

A derived-hash or content-addressed identity's `dal:digestScheme` is required unless the identity is a `dal:PositionDerivedEvent` whose `dal:occurrenceNamespaceDerivation` is `dal:RegistryTokenDerivation`: the namespace is then a registry-allocated token, not digest-derived, so the digest is never used (`dal:DigestSchemeRequiredShape`, narrowed by persistence-compiler-iri-sync Slice 5). A scheme declared anyway is still checked for well-formedness, never merely ignored.

## A `Target` is a class, plus a deployment when there is more than one

A class alone cannot distinguish "`beh:Behaviour` as lending deploys it" from "`beh:Behaviour` as credit deploys it" (sketch §3.4.3's worked conflict): that distinction lives in which graph the instances are written to, which is exactly what a `dal:GraphPatternScope` declares via `dal:coversClass`. `discover_targets()` therefore yields one `Target` per distinct `GraphPatternScope` deployment a class has, plus one unscoped/fallback target — a class with no graph-pattern deployment at all gets exactly one target. This is an implementation-level refinement not spelled out explicitly in the sketch's prose; see `persistence.scopes.Target`'s docstring for the full reasoning.

## Using the generated SPARQL directly

This section is for a caller that runs the instantiated `.rq` files. The checks a store cannot make, and the digest, are done by the caller library ([`lattice-persistence`](../../packages/persistence/README.md), [ADR-A132](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md)). A caller in another language does the same steps itself, held to the vectors in [`contracts/persistence`](../../contracts/persistence/README.md). What follows names each step, then lists the values of each operation.

### With the caller library

```python
from rdflib import Graph
from lattice_persistence import Iri, Lit, Payload, Triple, check_request, read_contracts, request_digest

profile = Graph().parse("compiled-profile.ttl")
replace = next(o for o in read_contracts(profile) if o.template_id == "cas-replace-composite-property-patch-log")
payload = Payload.of(Triple(Iri.encode("urn:ex:p1"), Iri.encode("urn:ex:name"), Lit("Alpha")))
values = {"root": Iri.encode("urn:ex:p1"), "epoch": 1, "expectedSeq": 3, "nextSeq": 4, "newRev": Iri.encode("urn:rev:4"),
          "txnId": Iri.encode("urn:txn:1"), "payloadTriples": payload, "assertTriples": Payload.of(), "retractTriples": Payload.of()}
values["requestDigest"] = request_digest(replace, values)
check_request(replace, values)           # raises CallerCheckError, naming every reason, before anything is sent
text = payload.sparql()                  # the value of {{{payloadTriples}}}
```

`check_request` refuses a request, with the operation and parameter named, since a guard that fails in the store reads as a lost race.

| Step | What the library does | Without the library |
|---|---|---|
| The payload | `Payload` holds ground triples of typed terms, with no blank node, and renders the slot text from the encoders. A literal holding `} } ; DROP ALL` stays one literal | Encode every term as `persistence.terms` does. Never build the slot from a string |
| The digest | `request_digest` follows the profile's digest contract. Each content part is one component | The vectors in `contracts/persistence` are the definition |
| Every parameter | present, and of its kind. A `Long` or `Position` is exactly `xsd:long`, on any store, so an `xsd:integer` epoch is refused where a store's guard might pass it. A literal is not an IRI | The contract of the operation in the compiled profile lists each parameter and its kind |
| A caller-named `$g` | equal to the naming rule (prefix, `ENCODE_FOR_URI` of the root, suffix) | The `graphPrefix` and `graphSuffix` bindings of the operation |
| `logGraphs` | non-empty and every member an IRI. An audit over no graph examines nothing | An audit reports `NothingExamined` and never clean (below) |
| The payload's subjects | every subject is the root or reached from it by the owned edges. A family that names no boundary shape has the form checks only (`UnboundedPayload`) | Run the `payload-check` operation of the profile over a local graph holding the payload |
| The events of an append | at least one row, each event IRI and each `opSeq` distinct, and every subject of the event triples an event of the batch or a node minted under one (`{event}/part/...`), so an event may name an aggregate and never describe it | the vectors `eventChecks` |
| Reference modes | with `version_of`, an object on a pinned edge is a version and an object on an identity edge is not (H2.6e). Without it the modes are not checked | the vectors `referenceChecks` |
| A checkpoint | with `membership`, a checkpoint version of a family under `dal:DeltaMembership` states `pat:checkpoint true` and lists every member | the vectors `checkpointChecks` |

**The payload-check query.** `instantiate` writes `payload-check.rq` for each family that has a payload operation and a `dal:boundaryShape`. It returns the subjects outside the aggregate. Load the payload into the graph `urn:g:payload` of a store of your own, substitute `$root` (for a new version, `$newVersion`, the contract's `dal:payloadRoot`), and run it. An empty result passes. It never goes to the store that holds the data. The library runs the same walk without an engine, and the tests hold the two equal on rdflib and Oxigraph.

**The outcome of an audit.** An audit selects the rows that violate an invariant, so no row cannot say whether it read anything. The contract of an audit declares the outcomes `dal:Clean`, `dal:Failed` and `dal:NothingExamined`, and the parameter it examines (`dal:examinedParameter`). `run_audit(client, operation, query, log_graphs)` fills the `logGraphs` slot, runs the query through the `select` method of your client (the one thing the library asks of it), counts the receipts the listed graphs hold when no row came back, and reports one of the three.

**With the guards off.** `compile --no-parameter-guards` reports `ParameterGuardsOff` as information, naming the obligation. The library does every test the guard would. A request that leaves out `$root` can otherwise write every aggregate whose version row matches. `compile --warn-unbounded-payload` raises `UnboundedPayload` to a warning.

### Three kinds of value

| Kind | Filled by | Syntax in the `.rq` file | Examples |
|---|---|---|---|
| Compile-time slot | `persistence instantiate`, from the compiled profile's parameter bindings | already rendered, nothing left | graph IRIs, shard number, the composite owned path and data graph |
| Request-time slot | you, with any Mustache library, per request | `{{{payloadTriples}}}`, `{{{logGraphs}}}` | the payload, the registry's log buckets |
| SPARQL variable | you, as initial bindings (or a prepared query's parameters), per request | `$root`, `$epoch`, … | the target IRI, positions, txn id |

**Request-time slots** hold values that are neither known at compile time nor bindable as one SPARQL term: a set of triples, or a list of graph IRIs. Render them with a Mustache library, triple-brace (unescaped), before submitting the request. The values are trusted, already-serialised SPARQL text, so the trust boundary is yours: never place untrusted input in them without encoding it as RDF terms first. An instantiated operation contains no other `{{` or `}}` sequence, and an unrendered slot makes the request a syntax error, so a forgotten slot fails closed.

- `{{{payloadTriples}}}`: the aggregate's full new state as Turtle-style triples (no `GRAPH` wrapper, skolemized, no blank nodes). Used by `create-if-absent`, `cas-replace`, `unconditional-write` and, for `append-version`, the new version's own triples only (the members it does not restate are shared by reference, so they are not in the payload).
- `{{{logGraphs}}}`: the IRIs of every log bucket the family's registry lists, space-separated, each in `<…>`. Used by `gap-scan-audit`, `revision-multi-txn-audit` and `txn-multi-revision-audit`. When the family declares `dal:registryGraph`, those operations carry a `registryGraph` parameter binding naming the graph to read the bucket list from. The pinned-head graph `urn:g:txlog/pinned` is already in the query.

### SPARQL variables per operation

| Operation | Variables |
|---|---|
| `bootstrap-version-row` | `$target`, `$epoch` |
| `create-if-absent` | `$root`, `$epoch`, `$newRev`, `$txnId`, `$requestDigest`, and the request-time slot `{{{payloadTriples}}}`. Under `dal:PatchLog` the same slot also fills the add graph |
| `cas-replace` | `$root`, `$epoch`, `$expectedSeq`, `$nextSeq`, `$newRev`, `$txnId`, `$requestDigest`, and the request-time slot `{{{payloadTriples}}}`. Under `dal:PatchLog` also the slots `{{{assertTriples}}}` and `{{{retractTriples}}}`, the caller's delta, written into the graphs named from the receipt (`$newRev` followed by `/add` and `/del`) |
| `tombstone-delete` | `$root`, `$epoch`, `$expectedSeq`, `$nextSeq`, `$newRev`, `$txnId`, `$requestDigest`, `$cause`, `$actor`. Under `dal:PatchLog` the del graph is copied from the sweep, so there is no slot. Under `dal:NoReceipt` there is no `$cause` and no `$actor`, which only a receipt records |
| `append` | `$stream`, `$epoch`, `$revBase`, `$txnId`, `$requestDigest`, and the request-time slots `{{{eventRows}}}` and `{{{eventTriples}}}` |
| `append-version` (`dal:AppendVersions`, H2.6c) | `$root`, `$epoch`, `$expectedSeq`, `$nextSeq`, `$newRev`, `$txnId`, `$requestDigest`, `$newVersion`, and the request-time slot `{{{payloadTriples}}}` |
| `cas-replace` (value guard) | `$root`, `$oldValue`, `$newValue` |
| `unconditional-write` | `$root` |
| `key-claim-write` (single scheme) | `$claim`, `$owner` |
| `key-claim-write-dual` (`dal:Dual` scheme state) | `$claimCurrent`, `$claimNext`, `$owner` |
| `key-claim-retire` | `$claim`, `$owner`, `$now` |
| audits, including `key-claim-duplicate-audit`, `key-claim-merge-rewrite`, `key-claim-quarantine` | none |

- **Parameter guards.** An operation rendered from its builder starts `WHERE` with one group holding one `FILTER` of a type test per required parameter, such as `ISIRI($stream)` or `DATATYPE($epoch) = DATATYPE("0"^^xsd:long)`, which compares the parameter's datatype with what the store makes of an `xsd:long` constant, so it passes on a store that keeps datatypes only for an `xsd:long` and on one that turns every integer into `xsd:integer` for any integer (ADR-A123, addendum of 2026-10-13). An operation with no required parameter has no guard group. An unbound or mistyped parameter makes the filter fail, so the request writes nothing. The guard is in its own group so that no pattern of the query can bind a missing parameter from the data first. Turn the guards off with `persistence compile --no-parameter-guards` only if your own code checks every parameter. The profile records the choice for each operation (`dal:guardStatus`), and `instantiate`, which has no flags of its own, renders what the profile says. Every operation is built with its guard. With guards off, a named-graph write that leaves out `$root` writes nothing on a store that follows SPARQL 1.1 Update, but on rdflib it puts the payload into a new blank-node graph (TD-44).
- **Naming a named graph.** By default a named-graph operation computes the root's graph, `?g`, in the query, from `$root` by the rule of ADR-A122 decision 8. `persistence compile --caller-graph-names` (recorded as `dal:graphNaming`, which `instantiate` follows) makes the operations that name a graph (create, replace, tombstone, unconditional write) take the graph as a parameter, `$g`, so a caller that substitutes text puts a constant graph in the query and no sweep can range over other graphs. With the guards on, the guard also checks `$g` against the naming rule with `sameTerm`, so a wrong `$g` writes nothing. With the guards off as well, naming the graph correctly is your obligation alone, and a wrong `$g` writes into whichever graph it names.
- `$epoch` is the dataset epoch read at the start of the request, typed `xsd:long`. So are `$expectedSeq` and `$nextSeq`, and the `opSeq` of each row of `eventRows`. An untyped integer is a different RDF term and never matches (guide Chapter 13).
- **`{{{eventRows}}}` and `{{{eventTriples}}}`** (append only, H2.6b) are filled by the caller before the request is sent. `eventRows` is one or more rows `(<event> <eventType> "opSeq"^^xsd:long "occurredAt"^^xsd:dateTime)`, and `eventTriples` is the data written into the events bucket beside them, possibly empty. One request steps the seq once and writes one receipt and one claim, whatever the number of rows. An empty `eventRows` writes nothing, and rdflib raises where Oxigraph gives no solution ([TSD-21](../../docs/architecture/triple-store-discovery.md#tsd-21-an-empty-values-block-in-an-update)), so refuse it before sending.
- `$txnId` is the transaction claim IRI (`urn:txn:{id}`). Receipts record its string form in `pat:txn`.
- `$requestDigest` is the lower-case hex SHA-256 of the tuple-encoded operation kind, target, expected `seq` (empty for create and append) and the sorted canonical N-Triples lines of the skolemized payload and events (guide §15.2). It is recorded on the txn claim, and your confirmation read compares it.
- `$revBase` (append only) is the revision IRI prefix including the zero-padded epoch, as a string, for example `"urn:rev:orders/1/e0000000000000000003/"`. The template pads the sequence to 19 digits. For CAS, tombstone and create you mint `$newRev` yourself in the same format.
- `$claim` is the HMAC claim IRI you compute over the tuple-encoded version, constraint id, scope and normalized key (guide §6.1).

### Obligations the SPARQL cannot enforce for you

1. **Create the version row before the first write** where the compiled profile contains `bootstrap-version-row`. That is every append stream, every aggregate declared `dal:firstWrite dal:PreCreatedRow`, which gets no `create-if-absent`, and every family declared `dal:writeDiscipline dal:AppendVersions`, whose first version is an `append-version` at seq 0. Run `bootstrap-version-row` when you allocate the aggregate or stream id, binding `$target` to the IRI you will later bind as `$root` or `$stream`. The first `cas-replace` then expects `seq 0`, and finds no head. Skipping this step makes every write a no-op that looks like a lost race.
2. **Check every request** with the caller library, or the steps of its table, before it is sent.
3. **Confirm every write** with a read of the txn claim's `pat:rev` and `pat:requestDigest` on the primary, and classify the outcome as guide §15.2 describes. A `204` from the endpoint does not mean the guard matched.
4. **Treat every transport failure as unknown**: resend the identical request with the same `$txnId` and payload, then confirm.
5. **Keep txn claims at least as long as the longest redelivery horizon** before pruning them (guide §24.2).
6. **Quiesce writers when you bump the dataset epoch** (guide §24.4).

## The typed operation IR (in progress, ADR-A123)

`persistence.ir` and `persistence.ir_render` are the replacement for the Mustache templates, built in slices H2.1 to H2.9 of formal-methods track H. An `Operation` is a frozen value. Its parameters are declared, every pattern sits in a graph block with a role, no blank node can be written, a property path appears only in `WHERE`, the variables of a `DELETE` or `INSERT` template are tagged `Bound` or `OptionalAllowed`, guards are tagged by term or value, `NOW()` is kept out of every guard, and the required-parameter guard is derived from the parameter list: one type test per parameter (`isIRI`, `DATATYPE` or `LANG`) in its own group at the top of `WHERE`, on by default and removable when the caller checks the parameters itself (ADR-A123 addendum, 2026-10-12). `render` refuses an operation that breaks one of these (`persistence.ir_render.RULES` names each refusal) and `access_sets` derives the graphs and subjects it reads and writes. `persistence.builders` ports the templates one at a time. `bootstrap-version-row`, `append-event`, `append-version` (H2.6c), the create, replace and tombstone of a named graph and of a composite family, each with its dataset-guard variant, and `unconditional-write` are ported (H2.2 to H2.4a), and `instantiate` renders them from the typed value with the required-parameter guard. `persistence compile --no-parameter-guards` leaves the guards out for a caller whose own code checks every parameter, and `instantiate` follows the profile. The five key-claim operations (`key-claim-write`, `-write-dual`, `-retire`, `-quarantine` and `-merge-rewrite`) and the five audits (`key-claim-duplicate-audit`, `fork-detection-audit`, `gap-scan-audit`, `revision-multi-txn-audit` and `txn-multi-revision-audit`) are ported too (H2.5), and `cas-replace-value-guard` is ported too (H2.7, TD-43), with every pattern in the family's `dal:dataGraph`, so every operation has a builder, and H2.9 retires the templates. A query operation is a `Select`, and a `SubSelect` is a pattern element. The fragment is closed (projection of variables and aggregates, `GROUP BY` over variables, and `HAVING`), and the checker refuses a projected variable that is neither grouped nor aggregated, a `HAVING` term that is neither, an inner variable of a sub-select used outside it without being projected, and `ORDER BY`, `LIMIT`, `OFFSET`, `DISTINCT` inside a sub-select and nested sub-selects. The renderer writes the parentheses of every nested arithmetic operand, since Oxigraph 0.5.11 groups a chain from the right ([TSD-17](../../docs/architecture/triple-store-discovery.md#tsd-17-a-chain-of-additions-and-subtractions)).

## Known limitations (first cut, honestly scoped)

- **`unconditional-write`** only knows how to target a `dal:NamedGraphBoundary`'s graph. A target combining `dal:ProvidedConcurrency` or `dal:LockingConcurrency`, outside event grain, with `dal:CompositePropertyBoundary` or `dal:NoBoundary` is refused (`UnconditionalWriteRequiresNamedGraph`, TD-02) until a second variant is added.
- **`dal:writeDiscipline`** (H2.6c, draft) picks how a family writes. `dal:InPlace` is the baseline, the operations above. `dal:AppendVersions` gives a composite family, or a family with no boundary and a `dal:dataGraph`, under `dal:Optimistic`, `bootstrap-version-row` and `append-version` and no create, replace or tombstone, so no version is deleted and the new version is linked to the prior one with `pat:previousVersion`. A named-graph family has no `append-version` variant (a graph per version is not built) and is refused with `AppendVersionsUnsupported`, as is a concurrency that is not `dal:Optimistic` and a no-boundary family with no data graph. A family that appends versions has no tombstone, so deleting one is left to housekeeping. `dal:AppendRecords` selects the append form for any family. Both append disciplines lift the refusal of a composite family with `dal:ReceiptOnly`, since the history is in the data. `compile` warns `VersionedClassWrittenInPlace` for a subclass of `fnd:Version` (by IRI, with no import) written in place. The guidance on which discipline fits is in the [ontology README, §7.10](../../ontology/persistence/README.md#710-write-discipline).
- **`dal:membershipEncoding`** (H2.6f, draft) picks how a family that appends versions states each version's members. `dal:FullMembership` is the baseline. Under `dal:DeltaMembership` the compiler selects `append-version-delta`, which takes two more request-time slots, `{{{addedMembers}}}` and `{{{droppedMembers}}}`, and adds the `members` read, which takes `$version` and `$membershipProperty` and returns `?member` from the chain back to the nearest checkpoint. `dal:checkpointEvery` (default 16) sets the interval, and `persistence.members` holds `is_checkpoint` and `materialise`, the scratch graph a domain shape runs over. The guidance is in the [ontology README, §7.10.1](../../ontology/persistence/README.md#7101-membership-encoding).
- **`dal:referenceMode`** (H2.6e) on a property shape of a boundary shape, beside `dal:ownership`, is `dal:ByIdentity` (absent means this) or `dal:Pinned`. `compile` records the mode of each edge that leads to a node as a `dal:ReferenceEdge` of the profile, and `contract_of` carries them on the payload contract, given the family's `edge_contracts`. It refuses `dal:Pinned` on an edge whose target class is not a subclass of `fnd:Version` (`PinnedReferenceToUnversionedClass`), refuses a value that is neither individual (`ReferenceModeUnknown`), and warns `EvidenceEdgeByIdentity` for an edge by identity from a subclass of `fnd:Evidence` or `fnd:DerivedArtefact` to a versioned class. No operation changes, and no check of a payload against the modes is built until the caller check (H2.8). The guidance on when to pin is in the [ontology README, §7.1](../../ontology/persistence/README.md#71-aggregate-boundary).
- **`dal:receiptModel`** (H2.6d) selects what an in-place write records. `dal:PatchLog` selects the patch-log variants of create, replace and tombstone, for both families and both guards, which write the delta graphs named from the receipt in the same update. `dal:NoReceipt` selects the variants that write no receipt, no log bucket and no head, and keep the transaction claim, and leaves out the audits that read receipts. It is refused with an append discipline, an append-only concurrency or a stream (`NoReceiptWithAppendDiscipline`). `dal:ReceiptOnly` and `dal:SnapshotPerRevision` select the receipt-only writes, and `compile` warns `ReceiptModelNotHonoured` for the snapshot, which no template writes (TD-46).
- **`cas-replace-composite-property`** sweeps the root and every member of the aggregate in one pattern, inside the profile's `dal:dataGraph` (ADR-A122). The members are the nodes reached by the owned edges of the boundary shape, compiled to one property path (`ownedPath`), with recursion as `*` and an edge from child to parent as an inverse step. An edge that leads to a node and is not classified is refused (`UnclassifiedBoundaryEdge`), as are a composite profile with no `dal:dataGraph` (`MissingDataGraph`) and one whose shape owns no edge (`CompositeBoundaryWithoutOwnedEdges`). A composite family also has `create-if-absent-composite` (it also asks that nothing of the root is in the data graph) and `tombstone-delete-composite`, which sweeps with the same path and tombstones the version row.
- **`dal:EquivalentClassScope` matching** is a syntactic approximation (does the target class appear inside the equivalence expression's `owl:intersectionOf`), not full OWL entailment. No reasoner dependency is introduced anywhere in this compiler, by design (sketch non-goals).
- **The log-bucket month** (`urn:g:txlog/{month}`) is computed at request time via `NOW()`, inside the generated `WHERE` clause, not baked in as a compile-time constant — this differs from an earlier, since-corrected version of the worked example in the sketch, which would have hard-coded a single month into a template meant to be reused across many months.
- **Infrastructure graph IRIs are fixed constants, not per-deployment configurable.** `urn:g:dataset` (dataset epoch graph and node), `urn:g:txn`, `urn:g:keys`, `urn:g:key-quarantine`, `urn:g:txlog/` (log bucket prefix), `urn:g:txlog/pinned`, `urn:g:retention`, `urn:g:events/{class-local-name}/` and `urn:g:meta/{shard}` match `rdf-sparql-patterns-guide.md` §2.3. No `dal:` property names them yet.
- **A named graph is named from the whole root IRI** (ADR-A122 decision 8): `dal:graphIriTemplate` with `{id}` replaced by the root IRI percent-encoded as `ENCODE_FOR_URI` does, and the text after `{id}` kept. A template holds `{id}` exactly once and any text after it begins with a character the encoding never emits, or it is refused (`GraphIriTemplateInvalid`). The text before `{id}` of every named-graph family, declared or defaulted to `urn:g:<family token>/{id}`, must not be a prefix of another's (`GraphIriTemplateOverlap`). The templates bind `graphPrefix` and `graphSuffix`.
- **`dal:epochGuardScope`** selects between a `-dataset-guard` template variant and the original for every row-writing operation: `create-if-absent`, `cas-replace` (named graph and composite property), `tombstone-delete`, `append` and `bootstrap-version-row`. The dataset-guard variants guard on the dataset epoch only and rebase the row's own `pat:epoch` on write, continuing `pat:seq` (guide §10.1). `unconditional-write` and `cas-replace-value-guard` write no version row, so they have no epoch guard.
- **Not generated:** the retention job (low-water marks, pinned-head copies, bucket drops) and the epoch bump belong to housekeeping (ADR-A80), not to this compiler. `pat:hlc` is not written by any template.
- **Declared shard counts are recorded, not applied.** `dal:txnShards`, `dal:logShards` and `dal:keyShards` resolve into the compiled profile, and a value above 1 raises a `ShardingNotHonoured` warning, because every template still writes one txn, keys and log-bucket graph.
- **`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding` and `dal:erasureReplayOnRestore`** (Slice 4) resolve and are emitted as extras of `dal:epochAuthority`, but no cross-axis check reads them yet: they describe the restore runbook (guide §24.4), which this compiler does not generate or execute.
- **`key-claim-merge-rewrite` records the merge edge only** (Slice 5): it never rewrites payload references to the canonical IRI, and never retires the losing claim, since only a claim's own owner may retire it (guide §6.2) and a background reconciler has no such authority. The canonical owner is the lexicographically lowest IRI among a claim's owners — an arbitrary but deterministic and total choice, the same convention as the dataset-guard graph IRI's own documented arbitrariness.

## Development

```bash
mise exec -- python -m pytest tools/persistence/tests -v
```

The test suite includes:

- **`test_terms.py`** — the injection corpus (ADR-A79 point 5): adversarial IRIs and literals fed through every encoder and every checked-in template, parsed by `rdflib`'s own SPARQL parser to assert exactly one operation ever results.
- **`test_resolver.py`**, **`test_validator.py`**, **`test_capability.py`**, **`test_boundary.py`** — unit coverage for each module, including the lending/credit worked conflict from the sketch, reproduced as an executable test.
- **`test_determinism.py`** — compiling the same configuration twice (including with triples loaded in shuffled order) produces isomorphic output.
- **`test_ownership_tree.py`** — the classified boundary tree and the property path compiled from it (HO4): the reference fixture's members, a golden path, and 200 seeded random shapes and datasets whose members by the path equal a breadth-first search of the automaton. The compiler does not use it yet.
- **`test_ir.py`**, **`test_ir_render.py`** — the typed IR (H2.1): one refusal test per rule, a parse test for every renderable form, 150 seeded random valid operations that each render to exactly one parsed operation, adversarial literals and IRIs that stay what they were, the required-parameter guard run on rdflib, and a pinned rendering.
- **`test_write_disciplines.py`** — the write disciplines (H2.6c): resolution and selection, the refusal and the warning, the relaxed composite refusal, the contract of `append-version`, and on each engine a second version that leaves the first in place and linked, the row's current version, members shared by reference, a retry, a stale seq and the dataset guard.
- **`test_composite_builders.py`** — the composite family's builders (H2.4a): the read and write sets with the sweep as a closure read, the guard's case for the family, the engine rules the sweep relies on, and the stored-IR rules SI-1 and SI-2 (every operation encodes structurally and back, builds equal twice, reads no file, clock or environment).
- **`test_named_graph_builders.py`** — the named-graph row writers (H2.3) run on rdflib: create, replace, tombstone and unconditional write with their dataset-guard variants, the join that restricts an inner `GRAPH ?g` to the graph an enclosing group binds, the caller-named graph, and the role of every graph written down apart from the table that assigns it.
- **`test_builders.py`** — the first ported builders (H2.2): the equivalence harness holds each builder to its template apart from the guard, three seeded mutations are caught, the guard is exactly one group of type tests, the ported operations run on rdflib (append, retry, chain, dataset guard, bootstrap), and a missing or mistyped parameter writes nothing where the unguarded query writes a partial record.
- **`test_compiled_profile_stable.py`** — a compiled profile serialises to byte-identical Turtle: across two compiles, across the order the configuration was loaded in, and across processes with different hash seeds. Every blank node's label is derived from its target (H1.5).
- **`test_compiler_integration.py`** — full compile → instantiate → parse round trips for every positive example fixture, `CompileError` assertions for every negative one, and SHACL self-validation of `ontology/persistence`'s own shapes against every fixture.
- **`test_template_alignment.py`** — the template contract from the post-3866b21 review: epoch rebase, request digests, optional heads, typed rows, key-claim graph, audits, and the request-time slot rules.
- **`test_slice_2_extensions.py`** — per-property resolution of the extension properties, baseline defaults, every Slice 2 check with a positive and negative case, `dal:firstWrite` and `dal:registryGraph` behaviour.
- **`test_slice_3_identity.py`** — role-qualified identity resolution, whole-node winners, no default role, emission, and every identity check with a positive and negative case.
- **`test_identity_minting_m1.py`** — the compiler reproduces the hand-authored anchor recipes of `contracts/identity/anchor-vectors.json` byte for byte; every recipe satisfies the published schema; digests are recomputed independently and invariant under triple order; emission, export, rotation, and one refusal per missing recipe member.
- **`test_slice_4_privacy.py`** — per-property resolution of `dal:PrivacyProfile` and `dal:perSubjectScoped`, `dal:epochAuthority`'s promotion out of `dal:epochGuardScope`'s extras, and both privacy/erasure checks with a positive and negative case, including the two profile classes declared on separate individuals.
- **`test_slice_5_uniqueness.py`** — `dal:onViolation` defaulting to `dal:Reject`, the three reconciler templates selected and bound, `MergeRelationRequired` positive and negative, `dualClaimScheme` mirroring `persistence.recipes`' active-scheme filter and selecting the dual-guard write template, and the registry-token digest-scheme exemption's positive case plus its `dal:HashedTargetDerivation` boundary negative case.
- **`test_architecture.py`** — the Python equivalent of an ArchUnit rule: only `persistence.render` may import `chevron`, no wall-clock call exists in any resolution-critical module, and `chevron.render`'s template argument is never dynamically assembled.

### The contract of an operation (formal-methods H2.6 and H2.7)

`persistence.contract.contract_of` reads an operation and returns its logical kind, its builder version, whether its parameter guard is on, its
parameters, the logical resources it accesses with the mode and key of each access (`PointRead`, `AbsenceRead`, `ScanRead`,
`WholeAggregateRead`, `Insert`, `Delete`), the columns an audit returns, and its payload and request-digest contracts. It holds no SPARQL
text. The tables behind it are `OPERATION_KINDS`, `resource_of` (a graph role, and for the keys graph the predicate, to a logical resource) and
`BUILDER_VERSIONS`, which `tests/test_builder_versions.py` ties to the text each builder renders. `HAND_DECLARED` is empty, since every operation has a
builder, and is kept for an operation that has none.

`compile` writes the contract of every operation into the profile (`persistence.contract_emit.emit_contract`), with the run's choices
(`compile --no-parameter-guards`, `compile --caller-graph-names`), and `instantiate` follows them. Every declaration node has an IRI minted from the
target, the deployment, the operation and the part (`contract_emit.mint`), and `dal:templateId` is the builder's identity, which `instantiate` finds
the builder by. The vocabulary is in `ontology/persistence/spec/persistence.ttl` §10a, and the shapes that check a compiled profile in
`ontology/persistence/shapes/constraints.ttl`.

`tests/expected_profiles.py` writes the reviewed compiled profile of each example into `ontology/persistence/test/expected-profiles/`, and
`tests/test_expected_profiles.py` holds the files to `compile` by graph isomorphism, so an editor may lay a file out as it likes. The same files are the
positive fixtures of the shapes (`tests/test_contract_shapes.py` makes each rule fail with a witness, and the witness check reads the files as conforming
fixtures). After a change to a builder or to `compile` output, regenerate
them in the same commit with `mise run build:persistence-expected-profiles`, and after a change to the text a builder renders, bump its version in
`BUILDER_VERSIONS` and run `mise run build:persistence-builder-goldens`. `mise run check:persistence-expected-profiles`, part of `check:persistence`, fails with the
names of the files that are not isomorphic to what `compile` emits.
