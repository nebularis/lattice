# Tenant + project lineage scoping: assessment and required follow-on changes

I agree with tenant + project for lineage. It is the right choice, and it closes the F-1 regression cleanly. It also exposes three places where A51 and A63 still don't fit together:

- the entity `{base}`;
- the lineage-level `pat:current` pointer versus per-environment activation;
- event IRIs and their epoch.

Details below.

## 1. Why tenant + project over tenant-only

A tenant-only lineage makes sharing easier, but you pay for it elsewhere:

- **`localName` becomes a tenant-wide namespace.** The F-3 allocation claim then contends across every project in the tenant. Two teams naming an artefact `policy-eligibility` collide.
- **Authorship becomes ambiguous.** A63's premise is that a project is the authoring context. A tenant-only lineage loses the one place that context would be recorded structurally.
- **Tenant + project doesn't prevent sharing.** It only requires sharing *by reference*. Project Q imports or activates project P's content revision IRI and never copies it. That is the correct RDF behaviour anyway, because one artefact should have one name.

For tenant + project to stay sound, A51 needs to state:

1. **`{projectId}` is immutable and opaque, like `{tenantId}`.** Renaming a project never touches IRIs.
2. **Re-homing an artefact to another project creates a new lineage.** It records `prov:wasDerivedFrom` (or `fnd:replacedBy` at the lineage level) pointing at the old one. The old lineage is not rewritten. This makes the F-10 "brittle segment" risk explicit and bounded.
3. **Cross-project and cross-tenant use is by reference to the original lineage or content revision IRI.** Customer-side modifications are a new lineage under the customer's tenant and project, derived from the vendor's revision.

Rename `{scope}` to `{projectId}` in both documents. The word "scope" is what allowed "project or environment" to creep back in.

## 2. The entity `{base}` is a separate decision, and it should be tenant-only

Lineages are authored; most entities are runtime data. In A63's model, environments sit under the tenant, not under a project. A customer, claim or order ingested into environment E therefore has no authoring project to put in its IRI. Distinguish three things:

| Kind | Base | Rationale |
|---|---|---|
| Runtime entities (ingested, operational) | `urn:lattice:{tenantId}` | Belongs to the tenant's data realm. Environment isolation comes from the dataset. The same real-world entity in prod and in a prod→test clone correctly has the same IRI. |
| Nodes minted *inside* authored content (shape nodes, mapping rules, skolemized nodes) | `{lineageIri}/n/{…}` | They travel with the artefact and are shared wherever the artefact is activated. They also make skolemization (review F-16) naturally lineage-scoped. |
| Shared reference data | `urn:lattice:{reservedTenantId}` | Per F-15. Name the reserved id in the policy. |

A consequence to state explicitly: two environments of the same tenant share the entity namespace. With `natural-key` or `derived-hash`, the same key yields the same IRI in dev and prod, which is correct. With `surrogate-claimed`, claims are per dataset, so independent ingestion into dev and prod mints different UUIDs for the same person. That is acceptable only because those datasets never merge. Document it, so no one later builds a cross-environment join on entity IRIs.

## 3. Where environment still leaks into A51

Your statement that "environment remains only in `RuntimeGraphReference` and dataset binding" is the right target. As A51 is written, two mechanisms quietly assume a single environment.

### 3.1 `pat:current` is on the lineage, but "what is in force" is per environment

A lineage is now environment-independent, so a single `pat:current` on its version row cannot mean "what is running". Otherwise dev and prod share one pointer, and promoting in dev changes prod. You need two pointers with different owners:

- **Lineage `pat:current`** (authoring registry): the latest approved or published content revision of the artefact. It is optional; call it `pat:latestApproved` if that is clearer.
- **`ActivationBinding`** (per environment, A63/C-02): which content revision is in force in environment E. This is the thing readers in E resolve, and it lives in E's dataset.

A51's "current pointer" row should say which one it means. I'd say the lineage-level one, with activation delegated to A63.

### 3.2 Event IRIs and their epoch

`{lineageIri}/evt/e{epoch}/{seq}` borrows the *dataset* epoch. A lineage now spans datasets, so it is unclear whose epoch that is. There are two kinds of event, and they have different answers:

- **Authoring events** (a revision was approved or published in project P). These live in the authoring registry. Use the registry's epoch, and the current form works.
- **Activation events** (revision R was activated in environment E). These are inherently environment occurrences with per-environment sequences. If minted as `{lineage}/evt/e{epoch}/{seq}` in each environment's dataset, dev's `e3/42` and prod's `e3/42` are the same IRI string for different occurrences. They will collide the first time they meet in exports, logs, CDC sinks or promotion evidence carried from staging to prod.

For activation events, I'd pick one of two options:

- **(a) Allow the environment id in runtime occurrence IRIs.** The form would be something like `urn:lattice:{tenantId}:env:{environmentId}/act/e{epoch}/{seq}`. Rule 3 would be reworded to "no environment component in lineage, content revision or entity IRIs; environment ids (immutable, opaque, never rewritten) may appear only in runtime occurrence IRIs". This is not the F-1 problem. F-1 was about *rewriting* identity on clone, whereas this names an event that genuinely happened in one environment.
- **(b) Mint activation events as UUIDv4 surrogates** and carry `(environment, epoch, seq)` as properties. This keeps Rule 3 absolute, but you lose the readable, range-scannable position in the IRI.

I prefer (a). Either way, A51 must stop implying that one event grammar covers both kinds.

## 4. Comments on A63 itself

**Cross-tenant packs.** The Context section says a pack built in project P may be activated into environments "possibly belonging to different tenants". Under tenant + project lineage, the customer's runtime graphs therefore reference IRIs carrying the *vendor's* tenant id. That is correct, because the artefact is the vendor's, but A63 should state three things:

- the lineage tenant segment means the authoring owner, never the consuming tenant;
- lineage IRIs are never rewritten on cross-tenant activation;
- tenant-scoped access control must permit reading a foreign-tenant lineage that an `ActivationBinding` references.

Otherwise someone will "fix" the foreign tenant id by re-minting, which is F-1 again.

**`AuthoredGraphReference(tenant, project, revisionIri, hash)`:**

- `tenant` and `project` are derivable from `revisionIri`. Either drop them or require that they match, and have the validator check this. Redundant fields that can disagree are the F4 "two sources of truth" bug.
- `revisionIri` should be specified as the *content revision* IRI, not an event IRI.
- `hash` is the full verification hash from A51/iri-policy §2. The Decision text calls it `revisionHash` while the record calls it `hash`, so pick one.

**`RuntimeGraphReference(tenant, environment, graphIri, generation)`:**

- `graphIri` is a dataset-local graph name under ADR-A54's grammar, not an identity IRI. Say so. Say whether it can carry environment (it doesn't need to, because the dataset is already environment-isolated).
- `generation` should be defined as the A51/guide dataset `epoch`, or explicitly distinguished from it. A third generation-like counter would be a mistake.
- It needs a link to what it materializes, such as `materializes: AuthoredGraphReference` or at least the content revision IRI and hash. Otherwise nothing can verify that the graph running in prod is the artefact that was approved. That link is the whole point of the split.

**Consequences.** Add that `ActivationBinding` is the per-environment current pointer (§3.1), and that activation events follow whichever grammar you choose in §3.2.

## 5. Concrete edits

**ADR-A51:**

- Lineage: `urn:lattice:{tenantId}:{projectId}:{family}:{localName}`, where `{tenantId}` is the authoring owner and `{projectId}` is immutable and opaque, per A63.
- Define `{base} = urn:lattice:{tenantId}` for runtime entities, and `{lineageIri}/n/` for nodes minted within authored content.
- Current pointer: lineage-level only. Environment activation is A63's `ActivationBinding`.
- Split event IRIs into authoring events (registry epoch) and activation events (the §3.2 choice). Reword Rule 3 if you take option (a).
- Add a rule: re-homing or forking creates a new lineage with `prov:wasDerivedFrom`, never a rewrite.

**iri-policy.md:**

- Rename `{scope}` to `{projectId}` and delete "or environment".
- Replace every `…:prod/…` example with `urn:lattice:t7f3a2/…` (runtime entity) or a `{lineage}/n/…` form.

**ADR-A63:**

- State the authoring-owner semantics for foreign-tenant lineage references.
- Make `AuthoredGraphReference` fields derivable from `revisionIri` or validated against it.
- Define `generation` as the epoch.
- Add the materialization link to `RuntimeGraphReference`.

With these changes, A51 governs names for things that exist independently of where they run, and A63 governs where and when they run. Environment then appears only where it is genuinely part of what happened.