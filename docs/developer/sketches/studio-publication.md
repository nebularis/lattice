<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Publication from the Configuration Studio, a sketch

**Unit ID:** `studio-publication` (PB)
**Plan:** [studio-publication.md](../plans/studio-publication.md)
**Status record:** [studio-publication.md](../status/studio-publication.md)
**ADR:** [A-149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md), Proposed

## 1. The scene

The studio authors an adopter's configuration: vocabularies, quantification, eligibility, persistence and surface configurations, mappings, forms and stated meaning. Today all of it lives in workspaces, and nothing leaves a workspace except an export of the whole workspace as TriG and the artefacts a compile job writes.

Four facts about the current model constrain the design.

- **A part sees only itself.** A workspace keeps each part as its own named graph, and a job reads one part with the baseline and the layers (`workers/src/lattice_workers/config_studio_jobs.py`, `_SPECS`). The rule that sorts a subject into a part (MEC-94) also decides what a job can see, so a mapping cannot read the source codes the vocabulary part holds, and the `policies` sample's `Peril` writes nothing (TD-133). The assemble job already merges every part, in the browser (`apps/config-studio/src/ui/BuilderView.tsx`), so sharing exists, but undeclared.
- **A workspace is the only container.** No workspace reads another's content, so two workspaces that need one vocabulary each hold a copy. The insurance vocabularies are 10,048 triples, 2.1 MiB as N-Triples, and every copy is another thing to keep consistent.
- **Nothing is versioned.** A workspace part has a revision for optimistic concurrency, but a revision is a save counter, not a version anyone can pin. An artefact a deployment takes, a compiled RML mapping for example, names no version of the configuration it came from.
- **Nobody is anyone.** The service has no authentication and binds to loopback (`docs/architecture/configuration-studio.md`). A command's sender is unauthenticated (TD-99), and PRI-54 asks every write to carry its principal.

The substrate already has most of what publication needs, unused by the studio.

| Need | Mechanism |
|---|---|
| a thing with versions | `fnd:Versioned`, `fnd:PersistentIdentity`, `fnd:supersededBy` (MEC-01, PRI-02) |
| the IRIs of a lineage, a content revision, a promotion and the current pointer | [ADR-A51](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md) |
| one digest of RDF content | RDFC-1.0 with SHA-256 ([ADR-A143](../../architecture/decisions/ADR-A143-one-canonicalisation.md)) |
| a meaning-bearing edge from a version is owned, pinned or content-addressed | [ADR-A142](../../architecture/decisions/ADR-A142-meaning-bearing-edges.md) |
| a unit written whole, edges leaving it by identity or pinned | aggregates and boundary shapes ([ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md)) |
| fixed or ambulatory reliance on an edition | `wrd:reliesOnEdition` and `wrd:reliesAsAmended` (MEC-38) |
| a scheme versioned in editions, an edition selected per scope and period | `voc:ConceptScheme` (MEC-08) and `voc:SchemeBinding` (MEC-10) |
| a product derived from declared sources | `fnd:DerivedArtefact` and `fnd:DerivationRun` with `prov:used` |
| a port that publishes compiled output by digest | the Surface output publisher ([ADR-A38](../../architecture/decisions/ADR-A38-surface-output-publication-and-studio-authoring-boundary.md)) |

## 2. Where the boundaries are

The studio is an authoring tool in front of a deployment's own services. A deployment runs its own pipeline, for example an RML mapping inside an integration framework, and its own evaluator, and reads its data where its own persistence profiles put it. It never calls the studio to do its work. What crosses from the studio to a deployment is a published version, named by its IRI and never by the graph the studio keeps it in.

```mermaid
flowchart LR
  subgraph Studio
    W[Workspaces: drafts and fenced imports]
    R[Registry: published versions]
  end
  subgraph Port[Publisher port]
    A1[Registry read API]
    A2[Bundle export]
    A3[Deployment store adapter]
  end
  subgraph Deployment
    S[Its own store and graph layout]
    P[Its own pipeline and evaluator]
  end
  W -- explicit publish --> R
  R --> A1
  R --> A2
  R --> A3
  A1 --> S
  A2 --> S
  A3 --> S
  S --> P
```

So a vocabulary built in the studio is published as scheme editions, and a deployment loads each edition into whichever graph its persistence profile names. The studio's own graph names stay internal, as ADR-A136 decision 7 already has them.

## 3. Publication

**What is published.** A unit of publication is an aggregate: a root and the nodes it owns. The units are a concept scheme, a scheme contract, a scheme binding set, a quantification declaration, an eligibility profile, a persistence profile, a surface contract, a mapping scheme, a form and the stated meaning of a form. Each is published on its own, as a version of its own lineage, and its references to other units are pinned to their versions (PB-Q1).

**When.** Only when a user publishes it. A unit nobody has published is unpublished, however long it has existed (PB-Q6).

**Its IRIs** follow ADR-A51. The lineage is the draft root's own IRI, which is its persistent identity. A version is minted at `{lineage}/rev/1-{digest}`, its digest the first 16 hexadecimal digits of the RDFC-1.0 SHA-256 of its content, so publishing unchanged content again names the same version and stores nothing new. The act of publishing is an event, `{lineage}/evt/e{epoch}/{seq}`, a `prov:Activity` with its principal, its time and the revisions it read, chained to the event before it. A current pointer names the lineage's latest version.

```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Draft: save, revision n+1
  Draft --> Published: publish
  Published --> Draft: keep editing
  state Published {
    v1: rev 1-a1b2
    v2: rev 1-c3d4
    v1 --> v2: supersededBy
  }
```

**Its content.** The root is rewritten to the version's IRI and carries `fnd:hasIdentity` to the lineage. The nodes it owns keep their IRIs and are read inside the version's own immutable graph, as a concept keeps its IRI across a scheme's editions (MEC-08). An edge from the unit to another unit's lineage is rewritten to the version it was pinned to, which ADR-A142 asks of a meaning-bearing edge.

**References while drafting** (PB-Q3). A draft refers to another unit either by its lineage, which follows the latest published version, or by a version's IRI, which is pinned. Publishing resolves each followed reference to the version current at that moment and records it, as a lockfile does. A draft that refers to something never published cannot be published until that is.

```mermaid
sequenceDiagram
  participant D as Draft mapping
  participant R as Registry
  D->>R: refers to lineage ex:Perils, follows
  Note over R: ex:Perils current is rev 1-c3d4
  D->>R: publish
  R-->>D: ex:Perils pinned to rev 1-c3d4, recorded in prov:used
  Note over R: ex:Perils later moves to rev 1-e5f6
  Note over D: the published mapping still names rev 1-c3d4
```

**Where versions live** (PB-Q2). A registry inside the studio's store holds every published version, readable by any signed-in user from any workspace. The publisher port gives a deployment its copy: the registry's read API, a bundle export of a version with everything it pins, and later an adapter that writes into a deployment's store through that deployment's own generated write path.

## 4. Fenced imports and dependencies

**An import is fenced.** What an import leaves in the graph, such as ODRL's vocabulary, an uploaded SKOS hierarchy or the nodes a document import produces, is stored once, by the digest of its content, read only, and referred to like anything else in the graph. Editing it means drafting a new unit from it. A fenced import is unpublished until a user publishes it. Uploaded files that are not graph data, such as an XML or JSON sample, wait for their own design (BL-08).

**A workspace declares its dependencies.** A dependency is a published version or a lineage to follow, from any workspace. Its content is fenced in the workspace that depends on it, never copied.

**A large vocabulary.** An uploaded SKOS hierarchy is a fenced import. Published, it is a scheme edition (MEC-08), stored once. A workspace that only refers to it depends on it. A workspace that edits it drafts a new edition from it, which holds one working copy until the edition is published. Bindings (MEC-10) then select an edition per scope and period, so the vocabulary-specific form of a dependency carries the scope and the time a plain dependency lacks.

| Peril taxonomy, 10,048 triples | Triples stored |
|---|---|
| 20 workspaces and 50 mapping releases, each with its own copy | 703,360 |
| one copy in a registry, each workspace and release pinning it | 10,048 for each edition published |
| a workspace editing it | 10,048 more until it publishes its edition |

## 5. What a job reads

A part decides only where a statement is saved, for the revision check. A job reads its target part, the workspace's other parts, its fenced imports and the closure of its dependencies, and reports findings about the target part's own subjects. The rule that sorts an import sends a concept with its scheme, so a representation scheme's codes stay with the mapping part.

```mermaid
flowchart TB
  T[Target part] --> J[Job input]
  O[The other parts] --> J
  F[Fenced imports] --> J
  D[Dependency closure from the registry] --> J
  J --> K[Validate or compile]
  K --> X[Findings on the target part's subjects]
```

## 6. Who may do what

Authentication is pluggable. The default, `local`, needs no provider. It offers a few named developer principals and is allowed only on a loopback address. A deployment configures `oidc` instead, which validates the bearer tokens of any OpenID Connect provider, for example Okta, Microsoft Entra ID or AWS Cognito, and reads an administrator from a configured claim. Every command carries its principal (PRI-54).

A workspace's creator is its owner and chooses its mode.

| Mode | Who reads | Who writes |
|---|---|---|
| locked | the owner and administrators | the owner and administrators |
| read only | everyone signed in | the owner and administrators |
| shared | everyone signed in | everyone signed in |

The revision check stays in every mode, since one person in two tabs, or an agent and its user, still race (PB-Q7).

## 7. The studio on its own substrate

The studio's working store is shaped by its own needs: per-part revisions, one writer per workspace, receipts and job graphs. Those are what persistence profiles declare. Once publication exists, the studio's own graph layout is declared as persistence profiles and its write path generated (PRI-60), so the studio is a deployment of the substrate like any other, while what it publishes leaves in the form a deployment chooses (PB-Q5).

## 8. Questions

| ID | Question | Answer |
|---|---|---|
| PB-Q1 | The unit of publication | Answered 2026-10-31, an aggregate published per unit with its dependencies pinned (P3), now ADR-A149 decision 2 |
| PB-Q2 | Where published versions live | Answered 2026-10-31, a registry in the studio with a publisher port's adapters, now ADR-A149 decision 4 |
| PB-Q3 | References while drafting | Answered 2026-10-31, follow a lineage until publishing, then pin, now ADR-A149 decision 5 |
| PB-Q4 | When authentication and workspace modes come | Answered 2026-10-31, now, the maintainer asking for pluggable authentication with a simple default and leaving the timing of modes to the unit, now ADR-A149 decisions 8 and 9 |
| PB-Q5 | When the studio's own store moves onto persistence and surface profiles | Answered 2026-10-31, after publication, as phase D, chosen by the unit at the maintainer's request, now ADR-A149 decision 11 |
| PB-Q6 | Whether anything is published implicitly | Answered 2026-10-31, never. Publication is explicit, now ADR-A149 decision 1 |
| PB-Q7 | Which modes need optimistic concurrency | Answered 2026-10-31, every mode, now ADR-A149 decision 9 |
