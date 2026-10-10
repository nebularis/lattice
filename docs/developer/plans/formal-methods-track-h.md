<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track H: Persistence

**Unit ID:** `formal-methods-track-h`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md) (rung T4,
the centrepiece), [formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md)
(the specification registry and the typed IR, the enabling move),
[persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md) (aggregate
ownership, normative for the HO slices of [§3.5](#35-ho-aggregate-ownership))
**Aggregate ownership:** the exploration note [persistence-aggregate-ownership.md](../notes/persistence-aggregate-ownership.md),
its spike [`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md),
and the review [persistence-aggregate-ownership-review.md](../notes/persistence-aggregate-ownership-review.md),
which holds the decisions (H-D14)
**Status record:** [formal-methods-track-h.md](../status/formal-methods-track-h.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(Proposed: home and scope. Tracks A-FM2's and A-FM3's conventions for mechanised theories and
design-time models, excludes all relational/SQL work)
**Source:** [persistence-fml.md](../notes/rdf-engine/persistence-fml.md), an independent,
exhaustive review of the Persistence layer against this epic's own techniques
**Status:** Proposed. Not started. Needs nothing from tracks A-G to begin: it reuses their
methods (Isabelle, Alloy, the claim/gate discipline) but has its own capability-record,
specification-registry and protocol-model work with no cross-track blocker

## 1. Scope

Formal methods applied to the `dal:` configuration vocabulary, `tools/persistence`'s compiler and
its generated SPARQL, and the pluggable RDF-store backends it targets — the **RDF and SPARQL side
of Persistence only** (sketch §2). **Explicitly, permanently out of scope for this entire track:
any relational or SQL-compilation work**, which is a separate review
([sql-feedback.md](../notes/rdf-engine/sql-feedback.md)) naming its own, different formal-methods
programme, not read as this track's scope (ADR-A-FM4 decision 1).

This plan details **H1** (static hygiene: the cheapest, no-new-toolchain fixes, startable
immediately) in full, and **H2, H3** (the typed IR and the specification registry — the enabling
move) in enough detail to begin, since both are natural, low-risk follow-ons to H1 using tools
already in the repository (Python, no new install). **H4 onward stay at outline level** (§4) until
H1-H3 land, per the Epic Decomposition Model's rolling-wave rule, the same discipline every other
track in this epic already follows for its own later slices.

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| `tools/persistence`'s existing compiler, templates, shapes and examples | exist, stable (ADR-A78, ADR-A79, ADR-A80) | nothing — H1 reads and checks what exists today |
| an ADR for this track's home and scope | [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md), drafted 2026-10-08, **accepted 2026-10-10** (H-D1) | nothing blocking for H1 (pure analysis and additive checks, no new top-level directory needed yet); H5's protocol models should wait for ADR-A-FM4's acceptance, since they are the one place the ADR's own "marginally widens an existing convention" point (decision 3) matters |
| track E's Isabelle pattern (`tools/proofs/<layer>/`) | established (ADR-A-FM2) | H6 only — reused, not re-decided |
| track C's Alloy pattern (`tools/models/<topic>/`) | established (its own plan §4) | H5, H7 — reused, not re-decided |
| a TLA+ or Quint toolchain | **not installed, not chosen** | H5's protocol models only. H1-H4 need no new toolchain at all |
| track A (the ledger and the harness) | not started (epic status) | nothing — this track's own claims and Validation Packs are the interim record, same arrangement tracks B and C already use |
| CCS | CCS slice HQ-6b depends on this track (2026-10-10) | nothing here. HQ-6b binds ADR-A105's closures to the store: a closure's cut to the per-root sequence (AO-Q6) and its completeness to `dal:BlockingContiguityCheck`. HQ-6a holds no Persistence content |
| insurml-alignment | no direct dependency either way | nothing. Persistence's own compiler and layer are not gated by its slices |

## 3. H1: static hygiene — ready to start

The cheapest items in the review, needing no new toolchain, each tied to a specific, named finding
(review §18, priority items 1-4; §12; §7.4; §8.1).

### H1.1: the prefix antichain and overlap check

- A static check over every declared `dal:graphPrefix` and `dal:iriPrefix` value: do the declared
  prefixes form an antichain (no one a proper prefix of another) or, if a longest-prefix rule is
  intended, is it actually implemented? Reports a counterexample IRI when it is not.
- **Closes:** the main sketch's L3 gap, specifically the finding that `dal:GraphPatternScope`'s
  "unscoped fallback for instances outside any of them" is only well-defined if the declared
  prefixes form an antichain, which nothing checks today (review §6.2, finding #2).
- **Validation:** a fixture with two overlapping prefixes (for example `urn:g:lending/` and
  `urn:g:lending/behaviour/`) must fail the check with the overlapping pair named; a fixture with
  a genuine antichain must pass.

### H1.2: witness coverage for every rule, shape, warning and audit

- A harness that, for every refusal rule, warning, SHACL shape and always-on audit query in
  `tools/persistence`, requires at least one fixture that **triggers** it (a non-vacuity check,
  review §7.4) — not only a fixture that satisfies it. Missing coverage is a build failure, listed
  by rule/shape/audit name, mirroring `tools/check_formal_freshness.py`'s own existing discipline
  for Eligibility's laws.
- **Closes:** the review's own calibration-table defects D.3 A6 (a shape that could never fire)
  and D.1's `sh:prefixes` defect (a constraint that silently targeted nothing), both vacuity
  failures a non-vacuity check would have caught in seconds.
- **Validation:** seed one deliberately-vacuous rule (a refusal condition that can never be true
  given the other rules) and confirm the harness reports it as uncovered; confirm every existing
  rule, shape and audit in `tools/persistence` today either has a witness or is listed as a gap.

### H1.3: static template checks (S-3, S-4)

- Two checks over every generated SPARQL template and its parameter-binding list, run per compile:
  **S-3**, every variable in an INSERT template is bound in every solution, or is on an explicit,
  named allow-list of deliberately-optional positions; **S-4**, no blank nodes appear in any
  INSERT template at all (a SPARQL fact: blank nodes in an INSERT template are fresh per solution
  per execution, so a retry is not a no-op, and blank nodes are illegal in DELETE templates
  outright).
- **Closes:** the review's own judgement that these are "the two I would implement first," given
  their severity (a silently missing triple reintroducing a confirmation-outcome defect; a retry
  that silently inserts a second set of fresh blank nodes) and the fact that both are statically,
  fully checkable from the template text alone, today, without any new toolchain.
- **Validation:** run against every template `tools/persistence` currently generates; a template
  violating S-3 or S-4 (seeded deliberately in a copy, not the real templates, unless a real
  violation is found) must fail with the specific variable or blank node named.

### H1.4: enumerate the declaration/implementation gap, as data

- A report, generated per compile, listing every resolved `dal:` dimension whose value the
  generated SPARQL does **not** actually implement: declared shard counts not honoured,
  infrastructure graph IRIs that are compiler constants regardless of configuration, retention and
  epoch bumps delegated to housekeeping, a composite boundary that binds only the first property
  its shape reaches. Each entry names whether it is a caller obligation, a housekeeping
  obligation, or genuinely unimplemented.
- **Closes:** the main sketch's L6 gap directly — review finding #9, which treats the composite-
  boundary case specifically as a soundness bug (an unswept closure member leaves exactly the
  dangling triple whole-replace exists to prevent), not a mere limitation. **This report should
  flag that specific case as a refusal, not a documented limitation**, pending H2/H3 or a direct
  fix to the composite-boundary templates (this track reports the gap; fixing
  `tools/persistence`'s own templates is that package's own follow-up, same division of labour
  track B already uses for defects it finds in `tools/mork_compilers`).
- **Validation:** run against `tools/persistence`'s current examples; the composite-boundary gap
  must appear in the report, named, with the specific shape and property it was found against.

### H1.5: stable compiled-profile labels

- Fix blank-node labelling in compiled profiles so that re-compiling the same configuration twice
  produces byte-identical output, closing the determinism gap the review names (§16.4) that
  currently prevents compiled profiles from being committed and diffed the way generated SPARQL
  already is.
- **Validation:** compile one example twice, confirm byte-for-byte identity of the compiled
  profile (not only the rendered `.rq` files, which already have this property per `tools/
  persistence`'s own existing determinism test, if one exists — confirm it covers the compiled
  profile too, not only the final SPARQL text).

**H1's overall validation:** one command runs all five checks across every example
`tools/persistence` ships today, and the report is read by a maintainer before any of H2 onward
starts, since H1.4's gap enumeration in particular may change what H2/H3 treat as urgent.

### H1.4b and H1.5 after the aggregate-ownership review (2026-10-10)

Both proceed now (AO-Q11). They do not wait for the HO slices.

- **H1.4b** reports today's implementation, and its composite entries are these, each naming the
  register row and the HO slice that removes it: the bound property is assumed owned and nothing
  declares it (TD-35, HO5), the replace sweep is quadratic (TD-36, HO1), an inverse path is
  misread (TD-37, HO5), the payload lands in the log graph (TD-39, HO1), no composite create or
  tombstone (TD-04, HO7), named graphs named from the root's local name (TD-38, HO8), and composite
  operations that rely on the default graph against static check S-1 (TD-40, HO5). Write the
  report's test so it asserts the entries present at the time it runs. Each HO slice that closes a
  gap removes its entry from that test in the same commit, and says so in its Validation Pack.
  If H1.4b runs after HO1, omit the TD-39 and TD-36 entries.
- **H1.5** is unchanged, and waits for nothing. The maintainer's merge of the branch is the sign-off for
  every slice on it, including H1.4a (`validation/LOG.md` is retired on `main`). Stable labelling does not depend on what a
  compiled profile contains, so HO slices that change compiled output regenerate H1.5's golden
  files, if it has any, in the same commit.

## 3.5 HO: aggregate ownership

**Why.** The composite boundary does not model an aggregate correctly. The exploration note
[persistence-aggregate-ownership.md](../notes/persistence-aggregate-ownership.md) and its spike
[`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md)
found it, and the review [persistence-aggregate-ownership-review.md](../notes/persistence-aggregate-ownership-review.md)
corrected and extended the findings (S1 to S6, F1 to F9). We decided AO-Q1 to AO-Q12 on
2026-10-10 (H-D14).
**What to build.** The design sketch [persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md)
is normative. Every slice below cites its sections, and a slice that finds the sketch wrong stops and
asks.
**Compatibility.** None is kept (sketch header). Remove, do not deprecate.
**Order.** HO0, HO1, then HO3 to HO9 in order, end to end. HO2 is done: ADR-A122 was drafted on
2026-10-10 with the plan, and stays Proposed. The slices are built against it, and the maintainer accepts
it, with the rest of the work package, when verifying at the close. HO8 may run at any point after HO3. H1.4b and H1.5 run alongside, as above.

| Slice | Delivers | Modules | Tests | Closes | Blocked on |
|---|---|---|---|---|---|
| HO0 | the note and the spike corrected | the note, the spike | 18 spike checks | S1, S2, S5 in the documents | nothing |
| HO1 | composite replace writes the payload to the default graph and sweeps in linear time | two templates | 7 | TD-39, TD-36 | nothing |
| HO2 | ADR-A122 drafted, Proposed | documents only | none | | **done** 2026-10-10 |
| HO3 | `dal:` vocabulary 0.3.0 (`dal:ownership`, reference data), two shapes, examples | `ontology/persistence` | 8 | | HO1 |
| HO4 | ownership tree and path compiler, added beside the old walk | `boundary.py`, new `paths.py` (and one class in `terms.py`) | 10 | | HO3 |
| HO5 | the compiler switches to the tree. Several owned edges sweep correctly | `resolver.py`, `operations.py`, `validator.py`, `boundary.py` (see H-D16) | 10 | TD-03, TD-35, TD-37, TD-40 | HO4, H-D16 |
| HO6 | the refusals and the warning of sketch §5 | `validator.py` | 13 | | HO5 |
| HO7 | composite create and tombstone delete | `operations.py`, four templates | 8 | TD-04 | HO6 |
| HO8 | injective graph naming, within and across families | `operations.py`, `validator.py`, the named-graph templates | 6 | TD-38 | HO3 |
| HO9 | documentation and close-out | documents | none | | HO7, HO8 |

Every slice that adds a refusal, warning, shape or template adds its witness in the same commit, or
`mise run check:persistence` fails (H1.2, H1.3). Every slice ends with `mise run check:persistence`
passing, and reports the passed and xfailed counts it saw in its Validation Pack. Validation Packs are
`docs/developer/validation/FMH-HO<n>.md`, in the form of [FMH-H1-4a](../validation/FMH-H1-4a.md).

**Non-weakening.** HO5 deletes the H1.4a refusal, its witness, and tests H1.4a-T3, T4, T5 and T9, and
rewrites T1, T2, T6, T7, T8, T10 and T11 for the tree. Each removal is justified by ADR-A122 decision
1, and the HO5 Validation Pack lists every removed or rewritten test with its replacement, for the
maintainer to countersign at the gate.

### HO0: correct the note and the spike

**Files.** `docs/developer/notes/persistence-aggregate-ownership.md`,
`spikes/persistence-aggregate-ownership/{placement.py,test_spike.py,README.md}`.

**The note.** The header pointer to the review already exists (added 2026-10-10). Rewrite the note's
references to "the maintainer" in the team voice (`AGENTS.md`, Writing), as the rest of the repository now
is. Then:

| Where | Change to make |
|---|---|
| §1 item 1, and §3 row "Delete the outgoing triples of the root and of every owned node" | the "today" verdict describes the compiler before H1.4a. Since H1.4a the placement shape is refused as `CompositeBoundaryMultipleProperties` (review S1) |
| §3 row "Never delete a referenced entity" | Today: "a reference is swept when it is the shape's only `sh:node` (review F1, TD-35)". Verdict: "not supported, and a live hazard" |
| §4.5, the two sentences beginning "Today this is limited" | replace with "This already happens when a shape's only `sh:node` is a reference (review F1, TD-35)." |
| §4.1, "walking it gives the expected 12 nodes" | "11 nodes, since a policy is a reference (AO-Q1)" |
| §4.3 | the run-time single-owner example becomes a document owned by layers of two placements. The inbound quote example is deleted, since `Pol1` is outside the aggregate. Point to the warning `ReferenceToOwnedClass` (sketch §5) |
| §9.1 table, "ownership by construction" | append ", though a writer still needs the classified tree to decide what goes in the graph (review F6)" |
| §10 | "TD-26" becomes "TD-34". "add the payload-graph defect" becomes "TD-39, added 2026-10-10" |
| §11 heading line | add "Answered 2026-10-10. See the review §6." |

**`placement.py`.**

- `OWNED_TREE[EX.LayerContractBinding]` becomes `{EX.hasShare: EX.Quant}`.
- Remove `EX.connectsPolicy` from `FLAT_OWNED`. Add it to `REFERENCES`.
- `first_property_path`'s docstring becomes "What the compiler did before H1.4a: the first node
  property, in path order, followed with `+`. Since H1.4a the compiler refuses this shape
  (CompositeBoundaryMultipleProperties). Review S1."
- `placement_graph` gains `shared_document: bool = False`. When true, add
  `P2 a Placement ; definedProgramme T2`, `T2 a Tower ; hasLayer L9`, `L9 a Layer ; attachment DocOwned`.
  If `shared_policy` is also true, reuse the same `P2`, `T2` and `L9` nodes.

**`test_spike.py`.** Seventeen checks become eighteen.

| Test | Change |
|---|---|
| `test_the_first_property_alone_reaches_only_the_tower` | comment: "the compiler before H1.4a (review S1)". Assertion unchanged |
| `test_the_per_class_tree_takes_...` | subset `{"T","L1","L2","L3","LCB1","S1","Mc1","Mc2","DocOwned"}`. Add `"Pol1"` to the disjoint set. Add `assert len(pl.unrolled_paths(g).members) == 11` |
| `test_a_vocabulary_guard_catches_a_forgotten_vocabulary_link` | `forgot = pl.REFERENCES - {EX.marketType, EX.status, EX.connectsPolicy}` |
| `test_a_node_with_two_owners_is_found_and_an_outside_reference_is_listed` | rename to `test_a_shared_policy_is_a_reference_so_it_has_no_second_owner`. With `shared_policy=True, inbound_quote=True`, assert `pl.owners(g, [EX.P, EX.P2]) == {}` and `pl.inbound_from_outside(g, pl.unrolled_paths(g)) == set()` |
| new `test_a_document_owned_by_layers_of_two_placements_has_two_owners` | `g = pl.placement_graph(shared_document=True)`, assert `pl.owners(g, [EX.P, EX.P2]) == {EX.DocOwned: {EX.P, EX.P2}}` |

**`README.md`.** Add to "What it does not show": "A store that runs writers one at a time. On such a
store, a removal that computes its closure inside the update sees a concurrent write, and D1's orphan
does not occur (review S5)." And: "`first_property_path` simulates the compiler before H1.4a (review S1)."

**One command.** From the repository root, `python -m pytest spikes/persistence-aggregate-ownership -q`.
Pass: `18 passed`.

### HO1: fix the composite replace (TD-39, TD-36)

**Files.** `tools/persistence/src/persistence/templates/cas-replace-composite-property.mustache` and
`-dataset-guard.mustache`, a new `tools/persistence/tests/test_composite_sweep.py`,
`spikes/persistence-aggregate-ownership/test_spike.py`.

**Change.** Exactly sketch §7.1's HO1 text, in both templates, and their header comments.

**Tests** (`test_composite_sweep.py`, on rdflib's `Dataset`, using the shipped composite example and
the instantiation pattern of `test_composite_boundary.py`'s `_replace_and_count_left`).

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO1-T1 | an order (root with `status "open"`, two line items) and a version row at seq 1 / replace with a payload holding `status "paid"` and the line items / `"paid"` is in the default graph and in no named graph | L5 | + |
| HO1-T2 | as T1 / after the replace / `"open"` is in no graph, and no payload triple is in any `urn:g:txlog/` graph | L5 | + |
| HO1-T3 | as T1 / after the replace / one `pat:Revision` for seq 2 is in `urn:g:txlog/<YYYY-MM>` | L5 | + |
| HO1-T4 | the dataset-guard variant, with the dataset epoch row / as T1 / as T1 | L5 | + |
| HO1-T5 | a root with 5 triples and 3 line items of 4 triples each / evaluate the update's `WHERE` as `SELECT (COUNT(*) AS ?n)` with the same bindings / `n == 17`, not 60 | L2 | + |
| HO1-T6 | as T1 with `expectedSeq` 7 / replace / the dataset is unchanged, quad for quad | L5 | − |
| HO1-T7 | both templates / `python -m persistence hygiene` over the shipped composite example / no S-3 or S-4 finding | L1 | + |

For T5, take the instantiated update text, keep everything from the line that starts `WHERE {` to
the end, and prefix the template's `PREFIX` lines and `SELECT (COUNT(*) AS ?n)`. Pass the
request-time values as `initBindings`.

**Spike.** In `test_spike.py`, rename
`test_the_composite_replace_writes_the_new_payload_to_the_log_graph_not_the_default_graph` to
`test_the_composite_replace_writes_the_new_payload_to_the_default_graph`, asserting
`list(found) == [str(rdflib.graph.DATASET_DEFAULT_GRAPH_ID)]`. Update note §2.3's last sentence to "Fixed in
HO1." Run `python spikes/persistence-oxigraph/rdflib_comparison.py` if `pyoxigraph` is installed. That run
is **not mandatory** (decided 2026-10-10): the Oxigraph spike is a second-engine cross-check, and a
slice may skip it where the package cannot be installed, saying so in its Validation Pack. If its
composite scenarios report different counts, the payload move explains it. Update their expectations
and say so in the Validation Pack.

**Existing tests.** H1.4a-T10 and T11 must pass with their assertions unchanged. They did not at first
(predicted, then seen): their helper ran the update with `templatecheck`'s stand-in for the payload
slot, which the replace now writes to the default graph. The fix is to the test input and not to the
expected results. The helper removes the stand-in from the rendered text (taken from
`templatecheck._SLOT_STAND_INS`, so it cannot drift), so the replace runs with an empty payload, as
the tests always meant. Filtering the stand-in's subject out of the result instead was rejected,
since it makes the assertion skip something. HO5 rewrites both tests for the tree.

**Register.** Remove TD-39 and TD-36, naming HO1.

**One command.** `mise run check:persistence && python -m pytest spikes/persistence-aggregate-ownership -q`.

### HO2: draft ADR-A122

**Files.** `docs/architecture/decisions/ADR-A122-aggregate-ownership.md`, the catalogue
`docs/architecture/decisions/README.md`.

**Done 2026-10-10**, while planning: [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md),
Proposed, listed in the catalogue. A122 was free on `main` and every remote branch that day. The
agent does not change its status. If a slice finds the ADR wrong, it records the deviation in
that slice's Validation Pack and in the status record, and proposes a dated addendum, rather than
editing the decision text. Before the branch merges, re-check that no other branch has taken A122.

### HO3: the vocabulary, persistence 0.3.0

**The data graph (AO-Q14, decided 2026-10-10: option a).** Also add `dal:dataGraph` (sketch §3.1),
the shape `dal:CompositePropertyBoundaryRequiresDataGraphShape` (sketch §3.3) with its witness
`shape-CompositePropertyBoundaryRequiresDataGraphShape.ttl`, and `dal:dataGraph` on every composite
example and fixture. HO5 and HO7 then wrap every composite pattern and payload in
`GRAPH {{{dataGraph}}}` (sketch §7).

**Files.** `ontology/persistence/spec/persistence.ttl`, `shapes/constraints.ttl`, `README.md`,
`docs/aggregate-boundaries.md` (the terms only, the full rewrite is HO9), `examples/*.ttl`, the
catalog, and every current-version pin found by `git grep -n "persistence/0.2.1"` (not release
history). Load skill `lattice-ontology-authoring` first.

**Change.** Sketch §3: add the terms of §3.1, remove `dal:maxTraversalDepth` (§3.2) from the spec,
the shape and every example, and add the shapes of §3.3. Add `dal:ownership dal:Owned` to the
`ex:lineItem` property shape of `composite-property-boundary-shacl.ttl`, and to the node property
of every composite witness fixture under `tools/persistence/tests/witnesses/`. Add the two shape
witnesses `shape-BoundaryOwnershipShape.ttl` and `shape-ReferenceDataShape.ttl`, each with data the
shape reports and data it accepts (H1.2c rule). Then `mise run build:ontology-catalog` and
`mise run build:ontology-releases`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO3-T1 | a property shape with `dal:ownership ex:Other` / validate / `BoundaryOwnershipShape` reports it | L3 | − |
| HO3-T2 | a property shape with two `dal:ownership` values / validate / reported | L3 | − |
| HO3-T3 | sketch §10.1's configuration / validate / no `dal:` shape reports | L3 | + |
| HO3-T4 | a `dal:ReferenceData` without `dal:coversClass` / validate / `ReferenceDataShape` reports it | L3 | − |
| HO3-T5 | `ex:Currencies a dal:ReferenceData ; dal:coversClass ex:Currency` / validate / accepted | L3 | + |
| HO3-T6 | `dal:ownsReferenceData "yes"` / validate / `AggregateBoundaryProfileShape` reports it | L3 | − |
| HO3-T7 | the repository / `check:ontology-versioning` / passes, with 0.3.0 current | L0 | + |
| HO3-T8 | a composite profile without `dal:dataGraph` / validate / `CompositePropertyBoundaryRequiresDataGraphShape` reports it, and the same profile with one is accepted | L3 | +/− |

Put T1 to T6 and T8 in a new `tools/persistence/tests/test_ownership_vocabulary.py`.

**One command.** `mise run check:persistence && mise run check:ontology-catalog && mise run check:ontology-versioning`.
End the handoff with 🔴 RELEASE TAGS REQUIRED for `persistence/0.3.0`, as skill `lattice-lifecycle` says.

### HO4: the ownership tree and the path compiler

**Files.** `tools/persistence/src/persistence/boundary.py` (add `Step`, `Edge`, `OwnershipTree`,
`walk_ownership`. Leave `walk_boundary_shape` and `Closure` untouched), a new
`tools/persistence/src/persistence/paths.py` (sketch §6.2 and §6.3), `terms.py` (`PropertyPath`,
sketch §6.4, no change to `render.py`), and the fixtures of sketch §10:
`ontology/persistence/examples/composite-project-ownership.ttl` and
`tools/persistence/tests/fixtures/project-data.ttl`. Nothing calls the new code from the compiler yet.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO4-T1 | §10.1's shape / `walk_ownership` / `shapes == [Project, Milestone, Plan, Task, Document, Comment]` shapes, in that order | L1 | + |
| HO4-T2 | as T1 / owned edges / six: `hasMilestone`, `hasPlan`, `hasTask`, `attachment` from Task, `hasSubtask`, `^onTask` | L1 | + |
| HO4-T3 | as T1 / `member_classes()` / `{Milestone, Plan, Task, Document, Comment}` | L1 | + |
| HO4-T4 | §10.1's shape with its triples written in three different orders, and its blank nodes relabelled / walk and render / identical trees and identical path strings | L2 | + |
| HO4-T5 | §10.2's data / `SELECT ?s WHERE { ex:p1 <path> ?s }` / exactly `p1` and §10.3's 8 members | L4 | + |
| HO4-T6 | 200 random shape graphs (seeded `random.Random(n)`, n from 0 to 199, at most 5 shapes and 8 owned edges, inverse steps, self and mutual recursion, owned leaves) and random data (at most 12 nodes, 30 triples, predicates from the shapes plus one other) / members by the path, against a breadth-first search of (node, shape) pairs over owned edges / equal every time | L2 | + |
| HO4-T7 | a predicate IRI containing `>` / `PropertyPath.encode` / `SparqlTermError` | L8 | − |
| HO4-T8 | a single self-recursive owned edge / render and evaluate on `t1 hasSubtask t2 . t2 hasSubtask t3` / the string contains `)*`, and members are `t2, t3` | L1 | + |
| HO4-T9 | a shape with only value and reference properties / `owned_path()` / `None` | L1 | + |
| HO4-T10 | a property shape with a sequence path, and one without `dal:ownership` / walk / recorded in `complex_paths` and `unclassified`, nothing raised | L1 | + |

T5 also pins the rendered string as a golden value, taken from the first run and reviewed by eye
against §6.5. Put the tests in a new `tools/persistence/tests/test_ownership_tree.py`. No new
dependency. The random test uses the standard library only.

**One command.** `mise run check:persistence`.

### HO5: switch the compiler to the tree

**Files.** `resolver.py`, `operations.py`, `validator.py`, `boundary.py`, the two composite
templates, `tools/persistence/tests/test_composite_boundary.py`, `test_boundary.py`,
`test_validator.py`, `test_compiler_integration.py`, `test_template_alignment.py`, the witnesses,
`spikes/persistence-aggregate-ownership/payload_graph.py`, and
`spikes/persistence-oxigraph/{scenarios.py,rdflib_comparison.py}`.

**Change.** Sketch §4.3 and §7.1 (HO5 paragraph):

- the resolver stores `ownershipTree` and stops writing `compositeProperties`,
  `compositeEdgeProperties` and `maxTraversalDepth`
- operations bind `ownedPath` (`PropertyPath`) and `dataGraph` (`Iri`), and stop binding
  `compositeProperty`. The templates use `{{{ownedPath}}}` inside `GRAPH {{{dataGraph}}}` (sketch §7.1)
- the validator refuses a composite profile without `dal:dataGraph` as `MissingDataGraph`, with the
  witness `refusal-MissingDataGraph.ttl`, checked first among the boundary rules
- the validator's `UniquenessOutsideBoundary` reads `tree.predicates()`, `BoundaryConflict` reads
  `tree.member_classes()` at every depth, and `CompositeBoundaryMultipleProperties` is deleted with
  its witness
- `boundary.py` loses `walk_boundary_shape`, `Closure`, `reachable_properties` and
  `BoundaryCycleError`, with `refusal-BoundaryCycleError.ttl`
- until HO6, an unclassified edge is simply not followed. Neither does a reference edge

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO5-T1 | §10's fixture compiled / replace with a payload equal to the current aggregate except `ex:t3 ex:status ex:InProgress` / exactly the 28 delete-set triples are removed and the payload's triples are present, and every triple of `acme, alice, docShared, InProgress, Done, TaskStatuses, report1, p2, m9` is unchanged | L5 | + |
| HO5-T2 | as T1 with an empty payload / replace / no triple has `p1` or a member as subject. Everything outside is unchanged | L5 | + |
| HO5-T3 | F1: `ex:placedBy sh:node ex:CustomerShape ; dal:ownership dal:Reference` beside an owned `lineItem` / replace / the customer's triples are unchanged | L5 | − |
| HO5-T4 | F4: the comment linked by `^onTask` / replace dropping it / `c1`'s triples, including `c1 onTask t1`, are gone | L5 | + |
| HO5-T5 | the shipped composite example / compile and replace / as H1.4a-T10 (nothing left behind) | L5 | + |
| HO5-T6 | two owned edges from the root (rewritten H1.4a-T11) / replace / both members' old triples gone | L5 | + |
| HO5-T7 | every declaration order of §10.1 (rewritten H1.4a-T7) / compile / byte-identical `ownedPath` | L2 | + |
| HO5-T8 | a uniqueness key on `ex:title` (a value property of an owned shape) / compile / accepted. A key on `ex:name` of `ex:Organisation` / compile / `UniquenessOutsideBoundary` | L3 | +/− |
| HO5-T9 | a member class at depth 3 that declares its own named-graph boundary / compile / `BoundaryConflict` | L3 | − |
| HO5-T10 | a composite profile without `dal:dataGraph` / compile / `MissingDataGraph`. And with §10.2's data also copied into the default graph / replace / the default-graph copy is untouched | L3, L5 | − |

List every removed or rewritten H1.4a test in the Validation Pack with its replacement (see
Non-weakening above). Run both spikes and update them to the new binding name. The aggregate-ownership
spike's 18 checks must still pass. Remove TD-03, TD-35, TD-37 and TD-40 from the register, naming HO5.

**One command.** `mise run check:persistence && python -m pytest spikes/persistence-aggregate-ownership -q`.

### HO6: the refusals and the warning

**Files.** `validator.py`, one witness per kind under `tools/persistence/tests/witnesses/`, a new
`tools/persistence/tests/test_ownership_refusals.py`.

**Change.** Sketch §5, rules 2 to 6 and 9 and the warning, in the order given there.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO6-T1 | an `sh:path ( ex:a ex:b )` property shape / compile / `ComplexBoundaryPath` | L3 | − |
| HO6-T2 | a node property with no `dal:ownership` / compile / `UnclassifiedBoundaryEdge`, naming the shape and the predicate | L3 | − |
| HO6-T3 | F1's shape with `placedBy` unclassified / compile / `UnclassifiedBoundaryEdge` | L3 | − |
| HO6-T4 | `dal:ownership` on an `sh:datatype` property / compile / `OwnershipOnValueProperty` | L3 | − |
| HO6-T5 | a composite shape with value and reference properties only / compile / `CompositeBoundaryWithoutOwnedEdges` | L3 | − |
| HO6-T6 | `ex:status` classified `dal:Owned` with `sh:class skos:Concept` / compile / `OwnedReferenceData` | L3 | − |
| HO6-T7 | as T6 with `dal:ownsReferenceData true` / compile / accepted | L3 | + |
| HO6-T8 | an owned edge to `ex:Currency`, declared `dal:ReferenceData`, and to a subclass of it / compile / `OwnedReferenceData` both times | L3 | − |
| HO6-T9 | two composite profiles owning `ex:Document` / compile / `OverlappingOwnership`, naming both shapes | L3 | − |
| HO6-T10 | a profile owning another composite profile's root class / compile / `BoundaryConflict`, since sketch §5 runs rule 8 before rule 9, and the same refusal on every run | L3 | − |
| HO6-T11 | §10's fixture plus `ex:InvoiceShape` with `[ sh:path ex:forMilestone ; sh:class ex:Milestone ]` / compile / warning `ReferenceToOwnedClass`, and the compile succeeds | L3 | − |
| HO6-T12 | §10's fixture / compile / no refusal and no `ReferenceToOwnedClass` warning | L4 | + |
| HO6-T13 | each new witness / the witness check / triggers exactly its own rule | L4 | + |

**One command.** `mise run check:persistence`. The witness count rises by seven: six refusals and one
warning.

### HO7: composite create and tombstone delete (TD-04)

**Files.** `operations.py`, new templates `create-if-absent-composite.mustache`,
`create-if-absent-composite-dataset-guard.mustache`, `tombstone-delete-composite.mustache`,
`tombstone-delete-composite-dataset-guard.mustache` (sketch §7.2 and §7.3), `templatecheck.py`'s
allowance list, `test_template_alignment.py`, template witnesses where no example reaches a
template, and a new `tools/persistence/tests/test_composite_lifecycle.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO7-T1 | §10's configuration with `dal:firstWrite dal:AbsentRow` / compile / both create templates generated | L4 | + |
| HO7-T2 | an empty dataset / create `p1` with §10.2's `p1` aggregate as payload / the payload in the default graph, a version row at seq 1, one revision | L5 | + |
| HO7-T3 | as T2, run twice with different transaction ids / second create / changes nothing | L5 | − |
| HO7-T4 | the root has a triple in the default graph but no version row / create / changes nothing | L5 | − |
| HO7-T5 | §10's data with a version row at seq 1 / tombstone delete / the 28 delete-set triples gone, `pat:deleted true`, seq 2, a `pat:Deletion` revision, everything outside unchanged | L5 | + |
| HO7-T6 | as T5 with `expectedSeq` 7 / tombstone / nothing changes | L5 | − |
| HO7-T7 | after T5 / replace / refused by the tombstone guard (no change) | L5 | − |
| HO7-T8 | all four new templates / `hygiene` / no S-3 or S-4 finding beyond the reviewed previous-revision allowance on the tombstone | L1 | + |

Remove TD-04 from the register, and the composite `AbsentRow` limitation from
`tools/persistence/README.md`. Update the H1.4b entries.

**One command.** `mise run check:persistence`.

### HO8: injective graph naming (TD-38)

AO-Q13 was answered with option a (H-D15). Build sketch §9 with these tests. Every named-graph
template changes, so re-run every named-graph test and witness, and update any expectation that names
a graph IRI.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO8-T1 | roots `https://example.org/a/1` and `https://example.org/b/1` in one named-graph family / create both / two different graphs, each with its own payload | L5 | + |
| HO8-T2 | `dal:graphIriTemplate "urn:g:orders/{id}/data"` / create / the graph IRI ends in `/data` | L5 | + |
| HO8-T3 | a template without `{id}` / compile / `GraphIriTemplateInvalid` | L3 | − |
| HO8-T4 | a template `urn:g:orders/{id}data` (suffix with no separator) / compile / `GraphIriTemplateInvalid` | L3 | − |
| HO8-T5 | two families with templates `urn:g:{id}` and `urn:g:orders/{id}` / compile / `GraphIriTemplateOverlap`, naming both profiles | L3 | − |
| HO8-T6 | the two new witnesses / the witness check / each triggers exactly its own rule | L4 | + |

Remove TD-38 from the register. **One command.** `mise run check:persistence`.

### HO9: documentation and close-out

Rewrite `ontology/persistence/docs/aggregate-boundaries.md` and the aggregate-boundary sections of
`ontology/persistence/README.md` from the sketch (§1, §2, §5, §7, §8, §11), in the domain-neutral
terms of §10. Recommend named graphs for new deployments. Update `tools/persistence/README.md`
(subcommands, known limitations, the `ownedPath` slot), and add a pointer to ADR-A122 at the top of
the legacy sketch `docs/developer/sketches/persistence-profile-substrate.md` §4. Do not rewrite that
sketch. Close the HO rows in the status record, update `docs/developer/INDEX.md` and
`docs/traceability/matrix.csv` where they name the removed terms, and re-run H1.4b's report. Its
composite and graph-naming entries should all be gone.

## 4. H2, H3: the typed IR and the specification registry

Detailed in [their own sketch](../sketches/formal-methods-track-h-specification.md). Two slices,
H2 first (the typed IR, since it is the smaller, more self-contained change and several of H1's
own checks — S-3, S-4, the term/value divergence — become structural guarantees once it exists
rather than external checks running against untyped template text) and H3 second (the
specification registry, which generates the rules, the selection table and the README's own
tables from one source, closing the review's finding #3 drift and enabling the exhaustive
cross-axis validation H4 needs as its input).

**H2 (typed IR), outline:**
- Give `tools/persistence`'s compiler an intermediate representation for a generated operation:
  typed parameters, a declared read/write set per operation (direct input to H5's protocol
  models), guards tagged `Term`/`Value`, template variables tagged `Bound`/`OptionalAllowed`.
- Rewrite the emitter to render from this IR, not from ad hoc string templates.
- **Validation:** every hazard in the specification sketch's own table (§3) becomes a type error
  rather than a runtime or static-check finding; re-run H1.3's checks against the new emitter's
  output and confirm they now pass by construction, not by a separate pass.
- **From aggregate ownership (H-D14, [sketch §12](../sketches/persistence-aggregate-ownership.md#12-what-h2-inherits)):**
  the `OwnershipTree` and its compiled `PropertyPath` become typed IR values. The IR states the
  payload check (every payload subject is the root or reached from it through owned steps), for the
  runtime caller to enforce. The required-parameter guard of H-D12 option D closes TD-34. H2's typing
  of the closure starts after HO5. The rest of H2 does not wait for the HO slices. A composite
  operation's declared read set is the closure its path computes at execution, and its write set is
  the delete set, the payload and the version row ([ownership sketch §15](../sketches/persistence-aggregate-ownership.md#15-effect-on-the-later-track-h-slices)).
- This is an **addendum to ADR-A79** (persistence compiler toolchain), dated, when this slice is
  detailed for real — not decided here, and not a new formal-methods ADR (ADR-A-FM4 decision 4).

**H3 (specification registry), outline:**
- One machine-readable registry (syntax not yet chosen, specification sketch §2) generating:
  `shapes/constraints.ttl`'s cross-axis rules, the compiler's own validation predicate and
  selection table, the README's own rule tables, a new obligation-set field per generated
  operation (review's PV-D2), a new laws-held field per compiled target (PV-D5).
- **Validation:** the generated shapes and the generated compiler predicate are checked against
  each other for agreement (closing finding #3's drift, review §7.3's V2/V3), and against the
  pre-existing hand-written versions for a one-time migration diff, reviewed by a maintainer before
  the hand-written versions are retired.
- **From aggregate ownership:** the boundary rules of the ownership sketch §5 and HO8's two
  graph-naming rules join the rule inventory as structural rules, recorded as their own kind, not as
  cross-axis predicates. The selection table gains composite create and composite tombstone delete,
  so the L5 totality check covers them ([ownership sketch §15](../sketches/persistence-aggregate-ownership.md#15-effect-on-the-later-track-h-slices)).
- Also an **ADR-A79 addendum** when detailed, per ADR-A-FM4 decision 4.

## 5. H4 onward, outline only

| Slice | Delivers | Rung | Depends on |
|---|---|---|---|
| H4 | exhaustive cross-axis validation (BDD/SMT) over the registry's own rule data: V1-V10 (review §7.3), most valuably V2 (no shape/compiler disagreement, checked universally) and V10 (every guarantee-forfeiting combination is warned, naming the law). **From aggregate ownership** (ownership sketch §15): C10 path-language equality by automata over the shape graph, graph-IRI-template injectivity across families (Z3 strings, review F11), C14's request bound with the largest aggregate, and the source review's `ClosuresDisjoint` Alloy model restated over classified edges | T3 | H3 |
| H5 | **the capability-record extension** (full `StoreCapabilities`, three-valued, `unknown` pessimistic, bound to a TCK report digest — review's PV-D1), **the TLA+/Quint toolchain spike**, and **protocol models A-D** (guarded CAS, append form, first-write/create race, key claim) — the main sketch's matrix idea, first four cells. **From aggregate ownership** (ownership sketch §15): model A parametrised by boundary strategy (the composite delete set is read at execution), model C covering composite create, and a capability field for whether inserting an identical statement is a write-write conflict | T4 (first use anywhere in this epic) | H2 (read/write sets from the IR), nothing else |
| H6 | Isabelle theories: `Resolution.thy` (determinism, locality, winner dominance, the capability-monotonicity-fails negative lemma), `Positions.thy` (order agreement of zero-padded positions, injectivity of revision IRIs), `Encoding.thy` (injectivity of the request-digest encoding, with the canonicalisation gap named as an explicit hypothesis, not assumed away), `Outcomes.thy` (totality, disjointness and soundness of the confirmation procedure, relative to an abstract history predicate H5's models discharge). **From aggregate ownership** (ownership sketch §15): `Encoding.thy` gains graph-IRI injectivity, `prefix · enc(r) · suffix`, under review F11's two rules | T5 | H1 (resolver as currently specified), H5 (for `Outcomes.thy`'s history predicate) |
| H7 | protocol models E-J (outcome classification, epoch bump/restore, retention/pruning, global read, fencing, infrastructure-graph writers — expected to be the single richest source of new findings, nothing there is guarded today) | T4 | H5, H6 |
| (deferred) | protocol model O, aggregate units: the removal rule, the parent-level create rule and the invariant row of the [ownership sketch §11](../sketches/persistence-aggregate-ownership.md#11-deferred-units-and-level-operations), seeded from the spike's `concurrency_model.py`. Built only if units are revived (AO-Q5) | T4 | H5 |
| H8 | protocol models K-N (erasure, multi-aggregate writes, bulk load/cutover, shard migration), plus grounding every model built so far against at least one real MVCC-style backend (isolation probes, history checking, predicted-anomaly reproduction). **From aggregate ownership** (ownership sketch §15): K's store list includes composite members, L adds references across aggregates under the roots-only rule, M adds an out-of-band load that makes a node a member of two aggregates | T4/T7 | H7 |
| H9 | detection-coverage closure: generate the nine missing audits the review names (L11's gap) from the same invariants H4's registry states, Alloy detection-completeness/soundness obligations per invariant, applicability labelling so a not-applicable audit cannot be read as "clean". **From aggregate ownership** (ownership sketch §15): four more audits, instance overlap, orphan member, reference into a member, and payload outside the tree for named-graph families with a boundary shape | T2/T0 | H3, H4 |
| H10 | runtime monitors from the same invariants (T7): housekeeping evidence, capability drift, declaration drift, an erasure audit, a position-reuse audit, feeding track A's ledger once it exists. The four ownership audits of H9 become monitors with the rest | T7 | H9 |

## 6. Milestones

| # | Outcome | Slice |
|---|---|---|
| FMH1 | every rule, shape, warning and audit in `tools/persistence` has a witness fixture or is listed as a gap; S-3/S-4 pass on every shipped template; the declaration/implementation gap is enumerated as data, not prose | H1 |
| FMH2 | the compiler's emitter cannot produce an untyped, unbound-variable, blank-node-bearing or term/value-confused operation, by construction | H2 |
| FMH3 | the cross-axis rules exist in exactly one hand-written place, with the shapes, the compiler and the README all generated from it and checked to agree | H3 |
| FMH4 | the first capability × strategy matrix cell exists, generated by a protocol model, not hand-written, with a named counterexample for at least one known-unsafe baseline | H5 |
| FMH5 | the resolver's capability-monotonicity-fails negative lemma is proved, mirroring Eligibility's own De Morgan negative lemma | H6 |
| FMH6 | at least one real backend has been grounded against a model's prediction, with a reproduced or a model-correcting result | H8 |
| FMH7 | every invariant the review names has a detector, with applicability correctly labelled | H9 |
| FMH-O | the composite strategy deletes exactly the declared aggregate: on the reference fixture (HO5), by the path property test (HO4), and by the automata check once H4 lands. No reference or reference data is ever swept | HO, H4 |

## 7. Metrics and abandonment conditions

Following the epic's own §6 discipline, declared now rather than discovered mid-track:

| Metric | Measures |
|---|---|
| vacancy rate closed | the fraction of H1.2's witness-coverage gaps closed per slice |
| matrix cells populated | how many (strategy, capability-profile) cells have a generated, grounded guarantee, out of the total the compiler's own strategy/profile space implies |
| grounding agreement rate | the fraction of a model's predicted counterexamples that reproduce on a real backend, versus corrections needed to the model |
| static-check false-positive rate | for H1-H4's checks specifically, since a check too eager to refuse a legitimate configuration is as costly as one that misses a real defect |

| Signal | Action |
|---|---|
| the TLA+/Quint spike (H5) cannot carry model A to a result (pass or counterexample) within a budget comparable to track D's own prover spike | do not proceed past models A-D. H1-H4, H6 and H9-H10 do not depend on protocol models at all and continue regardless |
| grounding (H8) finds a model's prediction does not reproduce on any real backend across two consecutive attempts | the model's own assumptions are wrong; revise or retire that specific model before building on it further, do not accumulate unverified models |
| the witness-coverage check (H1.2) finds more than half of `tools/persistence`'s existing rules lack a witness | this is itself the finding, not a reason to stop — it means H1 is doing its job |

## 8. Decisions for the maintainer

None of these is taken without the maintainer.

| # | Decision | Recommendation | State |
|---|---|---|---|
| H-D1 | accept, revise or reject [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md) | accept, including its point 3 (TLA+/Quint models share `tools/models/` with Alloy) | **decided 2026-10-10**: accepted as recommended |
| H-D2 | TLA+ or Quint, for protocol models | undecided; H5's own toolchain spike decides it on measured evidence, the same discipline track D used for Rocq vs Isabelle | open, deferred to H5 |
| H-D3 | whether the specification registry's and typed IR's design (H2, H3) are recorded as an ADR-A79 addendum or a fresh ADR | recommend an addendum, dated, per ADR-A-FM4 decision 4 and this repository's own practice for a decision found while building | open, deferred to H2/H3 |
| H-D4 | whether the composite-boundary soundness gap (H1.4's flagged finding) is fixed immediately as a `tools/persistence` defect, or left as a documented, refused combination until H2's typed IR makes the fix structural | recommend: refuse the combination now (cheap, one line in the existing validation predicate), fix properly once H2 lands | **decided 2026-10-09**: left as a documented, refused combination until H2's typed IR makes the fix structural. H1.4 carries the refusal |
| H-D5 | whether track H's claims feed track A's ledger once it exists, or keep their own interim Validation-Pack record permanently | recommend: feed track A once it starts, per ADR-A-FM4 decision 7 | open, not urgent |

Decisions H-D6 to H-D10 were taken as H1 progressed and are recorded, with their reasons, in the
[status record](../status/formal-methods-track-h.md). Two, H-D11 and H-D12, are explained in
[§13](#13-walkthrough-the-two-assumptions-behind-check-s-3-h-d11-and-h-d12). H-D13 to H-D16 come
from H1.4a and the aggregate-ownership review, H-D17 from tracing that design through the later
phases ([ownership sketch §15](../sketches/persistence-aggregate-ownership.md#15-effect-on-the-later-track-h-slices)).

| # | Decision | State |
|---|---|---|
| H-D11 | how check S-3 knows which variables the caller supplies | **decided 2026-10-09**: keep option A (the `$name` convention) and let H2's typed IR settle it. Walkthrough in §13.3 |
| H-D12 | whether a `BIND` counts as giving its variable a value | **decided 2026-10-09**: keep option A, record the limitation in this plan and in TD-34, and take option D (a required-parameter guard) in H2. Walkthrough in §13.4 |
| H-D13 | what H1.4a binds for a shape with one node property, and whether the closure is walked in path order ([H1.4a Validation Pack](../validation/FMH-H1-4a.md)) | **decided 2026-10-10**: Option 1 (C1, C2 and C3), as a stop-gap. Its precondition, that the bound property is owned, is unchecked (review F1, TD-35) and is listed in H1.4b's report. HO5 replaces C1 and C2. C3's path order carries into the tree walk |
| H-D14 | the aggregate-ownership questions AO-Q1 to AO-Q12 | **decided 2026-10-10**, by agreeing with every leaning in the [review §6](../notes/persistence-aggregate-ownership-review.md#6-the-twelve-questions-answered). Built by the HO slices ([§3.5](#35-ho-aggregate-ownership)) from the [sketch](../sketches/persistence-aggregate-ownership.md). Also decided: no compatibility is kept, since nobody else uses `persistence` |
| H-D15 | AO-Q13, how a named graph is named from its root ([review §7](../notes/persistence-aggregate-ownership-review.md#7-one-new-question-ao-q13)) | **decided 2026-10-10**: option a, `ENCODE_FOR_URI` of the whole root IRI, since no standard limits IRI length, minted roots are short ASCII (about 1.2 times longer once encoded), and an over-long IRI would fail loudly where option c fails silently ([review §7](../notes/persistence-aggregate-ownership-review.md#7-one-new-question-ao-q13)) |
| H-D16 | HO5 touches four Python modules (`resolver`, `operations`, `validator`, `boundary`) and HO4 three, more than the slice-sizing rule allows when read per file | **decided 2026-10-10: option A**, accept HO4 and HO5 as planned, one slice each. The resolver's extras, the operations' binding and the validator's checks read one structure, and most of the change is deletion. A split into two slices of two modules each is possible, with a temporary shim in the resolver that the second slice deletes. HO4 also touches three Python files (`boundary`, `paths`, `terms`), so the same question applies to it |
| H-D17 | AO-Q14, which graph a composite aggregate lives in ([review §7.1](../notes/persistence-aggregate-ownership-review.md#71-a-further-question-ao-q14), F10) | **decided 2026-10-10: option a**, a mandatory named data graph (`dal:dataGraph`). LATTICE's patterns guide already requires every graph to be named (S-1), SPARQL leaves the default graph's contents to the store, and holding application data in named graphs is ordinary practice |

## 9. Alignment with other work

| Unit | Item | Relationship |
|---|---|---|
| this epic, track A | the ledger and the harness | track H's claims feed it once it exists (H-D5); until then, Validation Packs are the interim record |
| this epic, track B | the reference semantics and the oracle | no direct dependency; track H does not need a Python reference oracle in track B's sense (there is no independent "meaning" of `dal:` configuration beyond the compiler itself, unlike Eligibility's laws). B2.1's hardening work (seed a compiler-side fault) is a methodological sibling to H1.2's witness-coverage work, not a dependency |
| this epic, track C | the design-time models | H5/H7's protocol models reuse track C's `tools/models/` home (ADR-A-FM4 decision 3) and its "bounded scope, never read as a proof" discipline directly |
| this epic, track E | the prover programme | H6 reuses track E's `tools/proofs/` home (ADR-A-FM2) and gate discipline unchanged, including the hardening items E1.4 queues (digest transitive definitions, characterising lemmas) — H6's own Isabelle work should apply E1.4's fixes from the start, not repeat the gaps it found |
| CCS | HQ-6b, the store binding of ADR-A105 closures | CCS depends on this track. A closure's cut binds to the per-root sequence and receipt stream (AO-Q6), and its completeness to the blocking contiguity audit. This track owns both, and a change to either is agreed with HQ-6b first |
| insurml-alignment | — | no direct dependency either way |
| the platform, `workers/` | housekeeping jobs, the outbox, the store SPI | H9/H10's generated monitors extend `tools/persistence`'s own existing housekeeping boundary (ADR-A80), not a new runtime |

## 10. Risks

- **The cross-axis rule space (1.3×10⁸ combinations) may strain a naive BDD encoding** before
  one-hot consistency constraints and shard-count/identity-role multiplicities are added (review
  §7.2's own caveat). H4's own first action is a size check before committing to exhaustive
  checking as stated.
- **TLA+/Quint authoring cost for a protocol as detailed as the guarded-write path (model A) may
  exceed the toolchain spike's own budget**, the same risk track D's prover spike carried for
  Isabelle/Rocq. The spike's own abandonment condition (§7) is stated for exactly this reason.
- **Grounding (H8) needs a real MVCC-style backend available to this project's own CI/development
  environment.** If none is practically available, grounding stays a manual, off-CI activity,
  recorded as such rather than silently skipped.
- **The declaration/implementation gap (H1.4) may be larger than this sketch assumes** once
  enumerated — if so, that is itself the most important finding this track could produce, not a
  reason to narrow its scope.

## 11. Out of scope

Everything named in the sketch's §2 and §6: any relational/SQL-compilation work, full SPARQL or
store-engine mechanisation, verifying third-party engines, replacing `tools/persistence`'s Python
compiler wholesale, any ontology change ahead of a specific slice's own ADR, building a second TCK
from scratch (the existing one is extended, not replaced).

## 12. Documentation deltas

At each HO slice's gate, as listed in [§3.5](#35-ho-aggregate-ownership): the register rows it
closes, `ontology/persistence` (HO3, HO9), `tools/persistence/README.md` (HO7, HO9), the ADR
catalogue (HO2). At H1's gate: `tools/persistence/README.md` (the new checks and how to run them),
`docs/developer/plans/formal-methods.md` and `docs/developer/status/formal-methods.md` (track H
added to the track board). At H5's gate: root `README.md` (the new TLA+/Quint toolchain, if a
native install or image route is added), `mise.toml` (new `check:persistence-formal-*` tasks),
`docs/architecture/ontology-architecture.md` (the capability-matrix idea, once it has its first
populated row). At H9/H10's gate: `docs/architecture/semantic-platform.md` (new monitor job
families), the ADR catalogue (the ADR-A79 addenda from H2/H3, if taken).


## 13. Walkthrough: the two assumptions behind check S-3 (H-D11 and H-D12)

This section is for a reader who has not worked in `tools/persistence`. It explains what check S-3
([H1.3](../validation/FMH-H1-3.md)) does, then the two assumptions it makes that the maintainer is asked
to confirm. Everything marked "demonstrated" was run against the real generated templates on
2026-10-09. The code is `tools/persistence/src/persistence/templatecheck.py`.

### 13.1 Five facts about a generated update

The compiler generates SPARQL updates from templates. Each looks like this, with a real, shortened
example below it.

```sparql
INSERT { GRAPH <g> { ?doc pat:title ?title .  ?doc pat:author ?author } }
WHERE  { ?doc a pat:Doc .  ?doc pat:title ?title .
         OPTIONAL { ?doc pat:author ?author } }
```

1. The database finds every **solution** of the `WHERE` clause. A solution is one assignment of
   values to the variables, for example one document with its title and perhaps its author.
2. For each solution it fills in the `INSERT` template and writes the triples.
3. **If a variable in an `INSERT` triple has no value in that solution, that one triple is skipped.
   There is no error.** In the example, a document with no author gets its title triple and no author
   triple. This is how the SPARQL 1.1 Update specification describes it and how the demonstration
   in §13.4 behaves.
4. `?x` and `$x` are the same variable to the database. The `$` is only a hint from the author of
   the template that the **caller** fills this one in before running the update, for example `$root`,
   the aggregate being changed. The compiler cannot know such values, so they are not part of the
   generated text.
5. `BIND(expression AS ?v)` gives `?v` a value. If the expression raises an error, for example
   `STR` of a variable that has no value, `?v` is left without one, the solution is kept, and
   fact 3 then applies to every triple that uses `?v`.

Fact 3 is the hazard. A field can go missing from a record that the system treats as complete, and
nothing reports it. The review behind this track ([§12](../notes/rdf-engine/persistence-fml.md))
ranked a check for it first (S-3).

### 13.2 What check S-3 does

For every generated update, the check does the following (`analyse`, `templatecheck.py:207`).

1. Fill in the values the compiler knows, as `python -m persistence instantiate` does. Replace the
   two request-time slots (`payloadTriples`, `logGraphs`) with harmless stand-ins so the text parses.
2. Parse it with rdflib into its algebra, a tree describing the `WHERE` clause.
3. List the variables used in the `INSERT` template.
4. Work out which variables have a value in **every** solution (`definitely_bound`, line 131).
5. Report any `INSERT` variable that is neither in that set, nor a `$parameter`, nor excused by a
   reviewed allowance in `OPTIONAL_INSERT_VARIABLES`.

How step 4 decides:

| Part of the `WHERE` clause | Variables counted as having a value |
|---|---|
| a triple pattern | every variable in it |
| two patterns joined | those of both |
| `OPTIONAL { ... }` | only those of the part outside it |
| `UNION` | only those present in **both** branches |
| `VALUES` | those given in every row (an `UNDEF` row does not count) |
| `FILTER`, `MINUS` | no change to what the main pattern gave |
| `BIND(e AS ?v)` | `?v`, **if every variable in `e` already counts** (this is H-D12) |
| a group-by sub-select | its grouping keys and aggregates |
| anything else | the check reports that it cannot analyse it, and never passes it |

Step 5's `$parameter` exemption is H-D11. On the real templates the check finds one thing, the
previous revision, left unbound on the first write to a row or stream. That is correct behaviour and
is recorded as eight allowances. The check finds no defect in the shipped templates.

### 13.3 H-D11: how does the check know which variables the caller supplies?

**The question.** The check must not flag `$root` as "unbound", because the caller supplies it. What
should define "a variable the caller supplies"?

**What it does today.** It reads the template text, removes comments, strings and IRIs, and treats
every name written with a `$` as a caller parameter (`_PARAMETER`, line 74, used at line 220).

**Why the text.** The compiled profile does list parameter bindings, but every one of them is a
compile-time value already substituted into the text (for example `metaGraphPrefix` or `txnGraph`).
Nothing in the compiled output says which names are left for the caller. The `$` is the only record.

**What the convention covers in practice.** Demonstrated: 17 of the 24 templates use at least one
`$parameter`, and the 7 that use none are the five audits and two key-claim reconcilers.

| Template family | Request-time parameters |
|---|---|
| `cas-replace-named-graph` and its dataset-guard variant | `$root $epoch $expectedSeq $nextSeq $newRev $txnId $requestDigest $assertGraph $retractGraph` |
| `cas-replace-composite-property` and its variant | the same, without the two graph parameters |
| `cas-replace-value-guard`, `unconditional-write` | `$root $oldValue $newValue`, and `$root` |
| `append-event` and its variant | `$stream $epoch $event $eventType $opSeq $occurredAt $txnId $requestDigest $revBase` |
| `tombstone-delete-named-graph` and its variant | the CAS set without the graphs, plus `$actor $cause` |
| `create-if-absent-named-graph` and its variant | `$root $epoch $newRev $txnId $requestDigest` |
| `bootstrap-version-row` and its variant | `$target $epoch` |
| `key-claim-write`, `-write-dual`, `-retire` | `$claim $owner` (and `$now`, or the two claim names) |

**The two ways the convention can be wrong.**

| The author writes | Meaning intended | What the check does | Consequence |
|---|---|---|---|
| `?x` | a caller parameter | reports it as unbound | safe, because it is loud |
| `$x` | a variable the `WHERE` clause should bind | **exempts it** | silent, the defect S-3 exists to catch |

The second row is real. Demonstrated: in the real `cas-replace` update, writing `$prevRev` in place
of `?prevRev` in the `INSERT` makes the finding disappear.

**Options.**

| Option | What it means | Consequence |
|---|---|---|
| **A. Keep the `$` convention** (current) | Read the parameters from the text | No change to compiler output. Has the second row above |
| **B. The compiler lists them** | Emit each operation's request-time parameters into the compiled profile, and have the check require the text's `$` names to equal that list | Closes the second row, and gives readers an explicit caller obligation list. Needs a new term in the `dal:` compiled-profile vocabulary under `ontology/persistence`, so a modelling decision and probably an ADR-A79 addendum |
| **C. Keep `$`, add a guard** | Also refuse a `$` name that a `BIND` assigns or a sub-select projects | Cheap, catches nonsense like `BIND(... AS $x)`, but does not catch the realistic row-two slip above |

**Recommendation, as a hypothesis.** Keep A for now and let the typed IR of H2 settle it. H2 gives
every generated operation a declared parameter list in its intermediate representation
([§4](#4-h2-h3-the-typed-ir-and-the-specification-registry)), which is option B arriving as part of
work already planned, without a separate ontology change today. The row-two risk is narrow while the
library is 24 reviewed files edited by the maintainers. It would grow if templates were authored
outside this repository, and that would change the recommendation to B.

**To try it yourself.** Edit a copy of a template so an `INSERT` variable becomes `$name`, then run
`python -m persistence hygiene ontology/persistence/spec/persistence.ttl ontology/persistence/examples/baseline-single-class.ttl`
against a build that reads your copy. The unit test `test_h1_3_t3` shows the exemption and
`test_h1_3_t2` shows the loud case.

### 13.4 H-D12: does a `BIND` count as giving its variable a value?

**The question.** `BIND(expression AS ?v)` can fail (fact 5). When the check sees one, should it
assume `?v` has a value?

**What it does today.** It assumes yes, provided every variable inside the expression itself
counts as having a value (`templatecheck.py:147-149`). Without that assumption, nearly every template
would be reported.

**What the real templates contain.** Demonstrated: 13 distinct `BIND` shapes across the 24
templates. Ignoring four that are artefacts of how rdflib rewrites aggregates and aliases, they fall
into three groups.

| Group | `BIND` | Can it fail? |
|---|---|---|
| No inputs | `?now` from `NOW()`, `?month`, `?logGraph` from `NOW()`, and values built from them (21 uses across templates) | Not by design |
| Inputs are caller parameters only | `?txnKey` from `STR($txnId)` (10 templates), `?g` from `$root` (7) | Yes, if the caller omits or mis-types the parameter |
| Inputs include stored data | `?n1` from the stored sequence counter (2 templates), `?rev` from `$revBase` and `?n1` (2) | Yes, if the parameter is missing, **or** if the stored counter is not a number |

**What a failure looks like. Demonstrated** with the real `append-event` update on a small
in-memory dataset. It was run on rdflib and on Oxigraph 0.5.11, an independent engine, and
the two agree. The code is in [`spikes/persistence-oxigraph`](../../../spikes/persistence-oxigraph/README.md).

| Request | Result |
|---|---|
| every `$parameter` supplied | 15 triples. The counter advances to 1, the event, the transaction claim, the revision record and the head pointer are all written |
| the caller forgets `$revBase` | 6 triples. **The counter still advances to 1** and the event is partly written, the transaction claim is recorded with its digest, but there is **no revision record, no head pointer, and the claim has no `pat:rev`** |
| then the caller retries with the same transaction id and every parameter | The transaction guard does not stop it, because it looks for a claim with a `pat:rev`. The counter advances to **2** and one revision record is written, for sequence 2. **Sequence 1 has no revision record, permanently** |

No error was raised at any step. The gap scan audit would report the missing receipt for sequence 1
afterwards (its witness shows it fires on a version row with receipts missing), so the damage is
detectable but not prevented.
This is a caller error, and it is recorded as TD-34 (numbered TD-26 until 2026-10-10) because the template offers no all-or-nothing
protection against it.

**What this means for the check.** S-3 counted `?rev` as having a value. That holds only while the
caller supplies `$revBase`. The two decisions are therefore one underlying trust:
**the check assumes the caller honours the parameter list**. H-D11 decides how the list is known.
H-D12 decides how far the assumption extends into computed values.

**Options.**

| Option | Rule | Consequence |
|---|---|---|
| **A. Trust a `BIND` over bound inputs** (current) | counts as having a value | Quiet. Misses the failure shown above |
| **B. Distrust any `BIND` with inputs** | counts only a `BIND` that has none | Rough trial: about half the templates (12 of 24) would be reported, mostly noise, because every template that uses `?txnKey` or `?g` is caller-dependent. The trial also counted a few values derived from `NOW()` through a middle variable, so read 12 as an upper bound |
| **C. Trust caller-dependent, distrust data-dependent** | a `BIND` over `$parameters` or constants counts. One over stored data does not | Reports the two append templates (`?n1`, `?rev`). The same trial also flagged three other templates through aggregate and alias artefacts that a real implementation would not. It is a defensible line (the caller contract is a separate obligation, stored data going wrong is an integrity hazard) but it needs an allowance or a guard to pass |
| **D. Fix the templates, not the check** | add a required-parameter guard so a missing parameter writes **nothing** | The real remedy for the demonstration above. Belongs to H2, where each parameter is declared and a guard can be generated |

**Recommendation, as a hypothesis.** Keep A for now, record the limitation here and in TD-34, and
take D in H2. Option C is the one to pick if you want the stored-counter case surfaced before H2.

**To try it yourself.** `python spikes/persistence-oxigraph/run.py` prints this table, after
`pip install -r spikes/persistence-oxigraph/requirements.txt`. `rdflib_comparison.py` in the same
folder runs it on both engines and compares.

### 13.5 Outcome

Both decisions were taken on 2026-10-09 in favour of option A, with the remedy deferred to H2.

| Decision | Outcome | What it commits H2 to |
|---|---|---|
| **H-D11** | Keep the `$name` convention. The check reads the caller's parameters from the template text | The typed IR declares each operation's request-time parameters. When it does, the lexical convention is replaced by the declared list, and the check reads that |
| **H-D12** | Keep trusting a `BIND` over bound inputs. The limitation is recorded here and as TD-34 | The typed IR declares required parameters and generates a guard so that an update with a missing parameter writes **nothing**, which is option D. TD-34 closes then |

**The limitation stands until H2.** Check S-3 does not detect an update run with a missing
parameter, a stored counter that is not a number, or a template author who writes `$x` where the
`WHERE` clause should bind `?x`. The first two are caller or data faults, and the third is a review
matter while the library is 24 maintained files. The assumptions are also stated at the top of
`persistence/templatecheck.py`.
